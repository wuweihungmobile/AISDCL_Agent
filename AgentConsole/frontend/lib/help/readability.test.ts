import { describe, expect, it } from "vitest";

import { HELP_COMMON, SHARED } from "./common";
import { codePointLength, splitSentences } from "./lint";
import {
  ACTION_WORDS,
  bannedFindings,
  fieldProblems,
  IMPLEMENTATION_WORDS,
  JARGON_BANNED,
  longSentences,
  MUST_EXPLAIN,
  pageCorpus,
  shapeProblems,
  STALE_PHRASES,
  stepProblems,
  unexplainedTerms,
} from "./readability";
import { HELP_PAGES } from "./registry";
import { STATE_HELP } from "./states";
import type { HelpField, PageHelp } from "./types";

/**
 * 說明文案可讀性鎖（TCS-ConsoleUxSortHelp-20261108 AC-963-6；R-UX-H1～H8；載具 H）。
 * 語料＝全部已登記頁的 purpose、steps、欄位 meaning 與 sourceNote、STATE_HELP 每列 meaning 與 next、HELP_COMMON、SHARED；欄位名與狀態名不入語料。
 * 判定指令：npx vitest run lib/help/readability.test.ts -t "<AT 底線形>"。
 */

const writtenPages = (): PageHelp[] => Object.values(HELP_PAGES).filter((page): page is PageHelp => page !== undefined);

type Entry = { where: string; text: string };

/** 全語料逐筆（句長、行話判定用）。 */
function allTexts(): Entry[] {
  const out: Entry[] = [];
  const pushField = (where: string, field: HelpField) => {
    out.push({ where: `${where} 欄位「${field.name}」`, text: field.meaning });
    if (field.sourceNote !== undefined) out.push({ where: `${where} 欄位「${field.name}」的 sourceNote`, text: field.sourceNote });
  };
  for (const page of writtenPages()) {
    page.purpose.forEach((text, i) => out.push({ where: `${page.id} purpose[${i}]`, text }));
    page.steps.forEach((text, i) => out.push({ where: `${page.id} steps[${i}]`, text }));
    for (const field of page.fields) pushField(page.id, field);
  }
  for (const field of HELP_COMMON.fields) pushField("HELP_COMMON", field);
  for (const [key, field] of Object.entries(SHARED)) pushField(`SHARED.${key}`, field);
  for (const [table, rows] of Object.entries(STATE_HELP)) {
    for (const [key, row] of Object.entries(rows as Record<string, { meaning: string; next: string }>)) {
      out.push({ where: `STATE_HELP.${table}.${key}.meaning`, text: row.meaning });
      out.push({ where: `STATE_HELP.${table}.${key}.next`, text: row.next });
    }
  }
  return out;
}

/** 術語語料：每頁一份、HELP_COMMON 一份、SHARED 一份；STATE_HELP 每張表也單獨當一份（頁引用到它時另已併入該頁語料）。 */
function termCorpora(): Array<{ where: string; corpus: string }> {
  const out: Array<{ where: string; corpus: string }> = writtenPages().map((page) => ({ where: page.id, corpus: pageCorpus(page) }));
  out.push({ where: "HELP_COMMON", corpus: HELP_COMMON.fields.flatMap((f) => [f.meaning, ...(f.sourceNote ? [f.sourceNote] : [])]).join("\n") });
  out.push({
    where: "SHARED",
    corpus: Object.values(SHARED)
      .flatMap((f) => [f.meaning, ...(f.sourceNote ? [f.sourceNote] : [])])
      .join("\n"),
  });
  for (const [table, rows] of Object.entries(STATE_HELP)) {
    out.push({
      where: `STATE_HELP.${table}`,
      corpus: Object.values(rows as Record<string, { meaning: string; next: string }>)
        .flatMap((r) => [r.meaning, r.next])
        .join("\n"),
    });
  }
  return out;
}

describe("AT_963_6 說明文案可讀性（R-UX-H1～H8）", () => {
  it("AT_963_6_1 全語料每句 ≤ 40 個字（code point）；失敗訊息列出頁、位置與該句", () => {
    const texts = allTexts();
    expect(texts.length, "防反空轉：語料筆數").toBeGreaterThan(200);
    const problems = texts.flatMap((e) => longSentences(e.text).map((s) => `句長 ${codePointLength(s)}：${e.where}：${s}`));
    expect(problems).toEqual([]);
  });

  it("AT_963_6_2 每頁 purpose 合計 2～3 句、steps 5～10 項且每項恰 1 句", () => {
    const pages = writtenPages();
    expect(pages.length, "防反空轉：已寫頁數").toBe(22);
    const problems = pages.flatMap((page) => shapeProblems(page).map((p) => `${page.id}：${p}`));
    expect(problems).toEqual([]);
  });

  it("AT_963_6_3 每頁每個 step 不以「這」「此」「系統」開頭，且含動作詞", () => {
    const problems = writtenPages().flatMap((page) => page.steps.flatMap((step, i) => stepProblems(step).map((p) => `${page.id} steps[${i}]：${p}`)));
    expect(problems).toEqual([]);
  });

  it("AT_963_6_4 每頁每個欄位與 HELP_COMMON、SHARED 的每個欄位，meaning 去空白後 ≥ 10 個字", () => {
    const fields: Array<[string, HelpField]> = [
      ...writtenPages().flatMap((page) => page.fields.map((field): [string, HelpField] => [`${page.id}.${field.name}`, field])),
      ...HELP_COMMON.fields.map((field): [string, HelpField] => [`HELP_COMMON.${field.name}`, field]),
      ...Object.entries(SHARED).map(([key, field]): [string, HelpField] => [`SHARED.${key}`, field]),
    ];
    expect(fields.length, "防反空轉：欄位數").toBeGreaterThan(100);
    const problems = fields.flatMap(([where, field]) => fieldProblems(field).map((p) => `${where}：${p}`));
    expect(problems).toEqual([]);
  });

  it("AT_963_6_5 每個語料（每頁、HELP_COMMON、SHARED）中，MUST_EXPLAIN 詞第一次出現後緊接「（白話解釋）」", () => {
    const corpora = termCorpora();
    expect(corpora.length).toBeGreaterThan(22);
    const problems = corpora.flatMap((c) => unexplainedTerms(c.corpus).map((p) => `${c.where}：${p}`));
    expect(problems).toEqual([]);
  });

  it("AT_963_6_6 全語料沒有 JARGON_BANNED、IMPLEMENTATION_WORDS、STALE_PHRASES；research 頁沒有「目前開放前兩步」、全語料沒有「本步驟於後續階段提供」", () => {
    const problems = allTexts().flatMap((e) => bannedFindings(e.text).map((p) => `${e.where}：${p}`));
    expect(problems).toEqual([]);
    const research = HELP_PAGES.research;
    expect(research).toBeDefined();
    expect(pageCorpus(research as PageHelp)).not.toContain("目前開放前兩步");
    expect(allTexts().some((e) => e.text.includes("本步驟於後續階段提供"))).toBe(false);
  });

  it("AT_963_6_E_1 負控：句長、結構、步驟、欄位、術語釋義、行話與過時句的邊界", () => {
    // 句長：41 個 code point 非空、40 個空
    expect(longSentences("字".repeat(41))).not.toEqual([]);
    expect(longSentences("字".repeat(40))).toEqual([]);
    // purpose 1／4 句非空，2／3 句空；steps 4／11 項非空，5／10 項空；每項恰 1 句
    const steps = (n: number) => Array.from({ length: n }, (_, i) => `按下按鈕${i}。`);
    const purpose = (n: number) => [Array.from({ length: n }, (_, i) => `句子${i}。`).join("")];
    expect(shapeProblems({ purpose: purpose(1), steps: steps(5) }).join()).toContain("結構");
    expect(shapeProblems({ purpose: purpose(4), steps: steps(5) }).join()).toContain("結構");
    expect(shapeProblems({ purpose: purpose(2), steps: steps(5) })).toEqual([]);
    expect(shapeProblems({ purpose: purpose(3), steps: steps(10) })).toEqual([]);
    expect(shapeProblems({ purpose: purpose(2), steps: steps(4) }).join()).toContain("結構");
    expect(shapeProblems({ purpose: purpose(2), steps: steps(11) }).join()).toContain("結構");
    expect(shapeProblems({ purpose: purpose(2), steps: [...steps(4), "按甲。按乙。"] }).join()).toContain("結構");
    // 步驟：開頭與動作詞（QA F5）
    expect(stepProblems("這個按鈕可以按")).not.toEqual([]);
    expect(stepProblems("此頁可以按")).not.toEqual([]);
    expect(stepProblems("系統會自動儲存")).not.toEqual([]);
    expect(stepProblems("看看清單")).toEqual([]);
    expect(stepProblems("等待結果出現")).toEqual([]);
    expect(stepProblems("結果會出現在右邊").join()).toContain("動作");
    // 欄位：9 字非空、10 字空
    expect(fieldProblems({ meaning: "字".repeat(9) })).not.toEqual([]);
    expect(fieldProblems({ meaning: "字".repeat(10) })).toEqual([]);
    expect(fieldProblems({ meaning: "字字 字字 字字 字字 字" })).not.toEqual([]);
    // 術語：首次出現無括號非空；有括號空；括號 1 字非空；第二次出現不需括號
    expect(unexplainedTerms("FSM 會跑").join()).toContain("釋義");
    expect(unexplainedTerms("FSM（流程狀態機，記錄做到哪一步）")).toEqual([]);
    expect(unexplainedTerms("FSM（機）")).not.toEqual([]);
    expect(unexplainedTerms("FSM（流程狀態機）會跑。FSM 又跑。")).toEqual([]);
    expect(unexplainedTerms("Tokens 很多")).toEqual([]);
    expect(unexplainedTerms("Token 很多").join()).toContain("術語");
    // 行話與過時句
    expect(bannedFindings("看游標").join()).toContain("行話");
    expect(bannedFindings("連 JDBC").join()).toContain("行話");
    expect(bannedFindings("本步驟於後續階段提供").join()).toContain("過時");
    expect(bannedFindings("按下按鈕就會開始")).toEqual([]);
  });

  it("詞表自我檢查：數量不降、MUST_EXPLAIN 與 JARGON_BANNED 沒有重複、切句與 lint 同口徑", () => {
    expect(ACTION_WORDS.length).toBeGreaterThanOrEqual(57);
    expect(MUST_EXPLAIN).toHaveLength(16);
    expect(JARGON_BANNED).toHaveLength(17);
    expect(IMPLEMENTATION_WORDS).toHaveLength(10);
    expect(STALE_PHRASES).toHaveLength(7);
    expect(new Set([...ACTION_WORDS, ...MUST_EXPLAIN, ...JARGON_BANNED]).size).toBe(ACTION_WORDS.length + MUST_EXPLAIN.length + JARGON_BANNED.length);
    expect(splitSentences("甲。乙！丙？丁；戊")).toHaveLength(5);
  });
});
