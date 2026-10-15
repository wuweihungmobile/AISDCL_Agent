import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

/**
 * 設計系統硬規則的靜態守衛（RTM：UI-DS-03 扁平無陰影、UI-DS-04 只用 Lucide、UI-DS-06 動效、UI-DS-01 只引用 token、UI-DS-05 焦點環）。
 * 掃描自家原始碼（去掉註解後）；Tremor Raw 是複製進來的上游原始碼，列為例外（但 dark: 與灰階已另行處理，見 ADR-002 D6）。
 */
const ROOT = process.cwd();
const VENDORED = "components/charts/tremor/";

function walk(dir: string, exts: RegExp, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) {
      if (["node_modules", ".next", "tests", "test-results", "coverage", "playwright-report"].includes(name)) continue;
      walk(full, exts, out);
    } else if (exts.test(name) && !/\.test\.tsx?$/.test(name) && name !== "schema.d.ts") {
      out.push(full);
    }
  }
  return out;
}
const rel = (f: string) => path.relative(ROOT, f).split(path.sep).join("/");
const stripComments = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`])\/\/.*$/gm, "$1");

const code = ["app", "components", "lib", "hooks"].flatMap((d) => walk(path.join(ROOT, d), /\.(ts|tsx)$/)).map((f) => ({ file: rel(f), text: stripComments(readFileSync(f, "utf-8")) }));
const own = code.filter((c) => !c.file.startsWith(VENDORED));
const css = ["app", "styles"].flatMap((d) => walk(path.join(ROOT, d), /\.css$/)).map((f) => ({ file: rel(f), text: stripComments(readFileSync(f, "utf-8")) }));

function offenders(files: Array<{ file: string; text: string }>, re: RegExp): string[] {
  return files.filter((f) => re.test(f.text)).map((f) => f.file);
}

describe("設計系統硬規則（靜態守衛）", () => {
  it("UI-DS-03 扁平：沒有 shadow／drop-shadow 工具類別，CSS 的 box-shadow 只允許 none", () => {
    expect(offenders(code, /(^|[\s"'`:])(drop-)?shadow(-[a-z0-9[\]/_.-]+)?(?=[\s"'`])/)).toEqual([]);
    // 取出每個 box-shadow 宣告的值，只允許 none（用 (?!none) 前瞻會因 \s* 回溯而誤判）
    const shadowed = css.filter((f) => [...f.text.matchAll(/box-shadow\s*:\s*([^;}]+)/g)].some((m) => m[1].trim() !== "none")).map((f) => f.file);
    expect(shadowed).toEqual([]);
    expect(offenders(css, /drop-shadow\s*\(/)).toEqual([]);
  });

  it("UI-DS-03 沒有漸層", () => {
    expect(offenders(own, /\b(bg-gradient-|bg-linear-|bg-radial-|linear-gradient|radial-gradient)/)).toEqual([]);
    expect(offenders(css, /(linear|radial|conic)-gradient\s*\(/)).toEqual([]);
  });

  it("UI-DS-06 動效只改顏色／透明度：沒有 hover／active 位移或縮放", () => {
    expect(offenders(code, /(hover|active|focus|group-hover):-?(translate|scale|rotate)/)).toEqual([]);
  });

  it("UI-DS-01 只用設計 token：元件程式碼內沒有寫死的色碼", () => {
    expect(offenders(own, /#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b(?![0-9a-fA-F])/)).toEqual([]);
    expect(offenders(own, /\b(rgb|rgba|hsl|oklch)\(/)).toEqual([]);
  });

  it("UI-DS-04 圖示只用 Lucide：沒有其他圖示庫、沒有手寫 <svg>、沒有 emoji", () => {
    expect(offenders(own, /from\s+["'](@remixicon|react-icons|@heroicons|@radix-ui\/react-icons|@tabler)/)).toEqual([]);
    expect(offenders(own, /<svg[\s>]/)).toEqual([]);
    expect(offenders(own, /\p{Extended_Pictographic}/u)).toEqual([]);
  });

  it("UI-DS-05 不得 outline-none／outline:none：焦點環一律由全域 :focus-visible 提供", () => {
    expect(own.filter((f) => /(^|[\s"'`:])outline-(none|hidden)(?=[\s"'`])/.test(f.text)).map((f) => f.file)).toEqual([]);
    expect(offenders(css, /outline\s*:\s*(none|0)\b/)).toEqual([]);
    // 搜尋框在 overflow-hidden 的圓角容器內：環改畫在內側（負 offset），而不是移除
    const top = readFileSync(path.join(ROOT, "components/layout/TopRegion.tsx"), "utf-8");
    expect(top).toContain("focus-visible:outline-offset-[-2px]");
  });

  it("全站只有淺色：沒有 dark: 工具類別、沒有 prefers-color-scheme: dark", () => {
    expect(offenders(own, /(^|[\s"'`:])dark:/)).toEqual([]);
    expect(offenders(css, /prefers-color-scheme\s*:\s*dark/)).toEqual([]);
  });
});
