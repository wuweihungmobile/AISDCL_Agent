import { readFileSync } from "node:fs";
import path from "node:path";

/**
 * 讀 styles 的 `--name: #hex;` 宣告，把 var(--name) 解析成色碼（測試用）。
 * 兩個檔案的載入順序與 app/globals.css 相同：tokens.css（設計稿逐字）→ tokens.console.css（Console 延伸＋無障礙覆寫）；
 * 同名變數以後者為準，所以解析出來的是瀏覽器實際套用的值。
 */
const HEX = new Map<string, string>();
for (const file of ["tokens.css", "tokens.console.css"]) {
  const css = readFileSync(path.join(process.cwd(), "styles", file), "utf-8");
  for (const m of css.matchAll(/--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})\b/g)) {
    HEX.set(m[1], m[2].toUpperCase());
  }
}

export function resolveVar(value: string): string | undefined {
  const m = /^var\(--([a-z0-9-]+)\)$/.exec(value);
  return m ? HEX.get(m[1]) : undefined;
}

export function tokenHex(name: string): string | undefined {
  return HEX.get(name);
}

/** WCAG 2.1 對比度（相對亮度比）；兩個 #RRGGBB。 */
export function contrastRatio(fg: string, bg: string): number {
  const channel = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  const luminance = (hex: string) => {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
  };
  const [hi, lo] = [luminance(fg), luminance(bg)].sort((a, b) => b - a);
  return (hi + 0.05) / (lo + 0.05);
}
