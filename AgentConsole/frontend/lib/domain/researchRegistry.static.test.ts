import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

/**
 * 研究來源單一化前端的靜態掃描（TCS-ResearchRegistry-20261110 AT-965-8-E-1；NFR-RR-6）：
 * 追蹤來源區與純函式模組的原始碼不得含 `dangerouslySetInnerHTML`、不得內嵌決定者名單或帳號名字面、不得為抓取上限寫數值預設。
 * 判定指令：npx vitest run lib/domain/researchRegistry.static.test.ts -t AT_965_8_E_1
 */
const ROOT = process.cwd();
const FILES = ["components/domain/research/WatchSourcesSection.tsx", "lib/domain/researchRegistry.ts"];

/** 掃描判準（純函式，才能對樣本做負控）：回傳違規描述清單。 */
function violations(source: string): string[] {
  const out: string[] = [];
  if (source.includes("dangerouslySetInnerHTML")) out.push("含 dangerouslySetInnerHTML");
  if (/CONSOLE_SI_DECIDERS|deciders/i.test(source)) out.push("含決定者名單常數或字面");
  if (/["'`](admin|operator|viewer)["'`]/.test(source)) out.push("含帳號名字面");
  if (/research_fetch_max|researchFetchMax\s*(\?\?|\|\|)\s*\d+|researchFetchMax\s*=\s*\d+/.test(source)) out.push("含抓取上限的數值預設");
  return out;
}

describe("AT_965_8_E_1 靜態掃描", () => {
  it("AT_965_8_E_1 範圍非空：兩個檔都存在", () => {
    for (const file of FILES) expect(existsSync(path.join(ROOT, file)), file).toBe(true);
  });

  it("AT_965_8_E_1 兩檔皆無違規", () => {
    for (const file of FILES) expect(violations(readFileSync(path.join(ROOT, file), "utf-8")), file).toEqual([]);
  });

  it("AT_965_8_E_1 負控：對違規樣本必須回報（掃描器本身沒有失明）", () => {
    expect(violations("<div dangerouslySetInnerHTML={{ __html: x }} />")).toHaveLength(1);
    expect(violations('const CONSOLE_SI_DECIDERS = ["a"];')).toHaveLength(1);
    expect(violations('const who = "admin";')).toHaveLength(1);
    expect(violations("const cap = researchFetchMax ?? 10;")).toHaveLength(1);
    expect(violations("const ok = researchFetchMax;")).toEqual([]);
  });
});
