import { readFileSync } from "node:fs";
import path from "node:path";

/** 讀 styles/tokens.css 的 `--name: #hex;` 宣告，把 var(--name) 解析成色碼（測試用）。 */
const css = readFileSync(path.join(process.cwd(), "styles", "tokens.css"), "utf-8");
const HEX = new Map<string, string>();
for (const m of css.matchAll(/--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})\b/g)) {
  HEX.set(m[1], m[2].toUpperCase());
}

export function resolveVar(value: string): string | undefined {
  const m = /^var\(--([a-z0-9-]+)\)$/.exec(value);
  return m ? HEX.get(m[1]) : undefined;
}

export function tokenHex(name: string): string | undefined {
  return HEX.get(name);
}
