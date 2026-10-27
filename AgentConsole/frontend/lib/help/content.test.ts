import { existsSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, expectTypeOf, it } from "vitest";

import { HELP_COMMON, SHARED } from "./common";
import { codePointLength, forbiddenFindings, splitSentences, unlistedEnglishWords } from "./lint";
import { HELP_PAGES, NO_STATE_PAGES, PENDING_HELP_PAGES } from "./registry";
import { STATE_HELP } from "./states";
import type { FieldSource, HelpField, HelpStateGroup, PageHelp, StateTableId } from "./types";

/**
 * 說明內容品質（TCS-PageHelp-20261027 R-PH-06、R-PH-16、R-PH-17；載具 HL，輪 1a 建；頁從 PENDING_HELP_PAGES 移進 HELP_PAGES 的那一輪起自動納入迴圈）：
 *  - AT-PH-03-5-1、3-5-2、3-5-E-1：已寫頁的結構界線（purpose 1～3 句、steps 2～8 步、fields ≥ 1、sourceFiles 存在、states 與 NO_STATE_PAGES 雙向、title 為固定頁名）、
 *    頁→狀態表矩陣（PRD §4 十六頁各頁的狀態表 id 與名稱模式，D-PH-15）；
 *  - AT-PH-05-1-1、5-2-1、5-3-1：全部說明文字（頁的 purpose、steps、欄位 meaning 與 sourceNote、STATE_HELP 每列、HELP_COMMON、SHARED）逐筆過 lint；
 *  - AT-PH-05-4-1（含型別等式）、5-4-E-1：欄位 source 屬六類、sourceNote ≤ 30 個字。
 * 語料只取 HELP_PAGES（pending 頁豁免，且豁免清單在此印出，不是靜默略過）。欄位名與狀態名是畫面字樣的逐字引用，不受英文詞限制，所以不在語料內。
 * 判定指令：npx vitest run lib/help/content.test.ts -t "<AT 底線形>"；AT-PH-05-4-1 另跑 npx tsc --noEmit。
 */

const ROOT = process.cwd();

/** 必備的十六頁（PRD §4；只准增不准減）：HELP_PAGES 的鍵 ∪ PENDING_HELP_PAGES 要涵蓋它。 */
const REQUIRED_PAGE_IDS = [
  "dashboard",
  "projects",
  "project-detail",
  "goals",
  "goal-detail",
  "tasks",
  "task-detail",
  "project-form",
  "goal-form",
  "task-form",
  "execute",
  "monitor",
  "import",
  "settings",
  "self-improving",
  "issues",
] as const;

/** 必備的 18 張狀態表（PRD §8.2；只准增不准減）。 */
const REQUIRED_TABLE_IDS = [
  "projectStatus",
  "goalStatus",
  "taskStatus",
  "stepStatus",
  "importStatus",
  "runStatus",
  "runTransition",
  "reviewKind",
  "reviewDecision",
  "alertSeverity",
  "alertRule",
  "gateName",
  "sddPhase",
  "sddFsmState",
  "serviceState",
  "obsClass",
  "propClass",
  "propState",
] as const satisfies readonly StateTableId[];

/** 欄位資料來源的六類（PRD §8.1；單一出處）。 */
const FIELD_SOURCES = ["您填寫或選擇", "系統自動產生", "執行引擎回報", "自我進化帳本", "系統參數", "其他頁面帶入"] as const;

/** PRD §4「狀態表」欄的逐頁釘值（TCS §5.3 PAGE_STATES）：「表 id:名稱模式」，`legend:issues` 是議題中心的 API 詞表群；集合要相等，順序不鎖。 */
const PAGE_STATES: Readonly<Record<(typeof REQUIRED_PAGE_IDS)[number], readonly string[]>> = {
  dashboard: ["projectStatus:label"],
  projects: ["projectStatus:label"],
  "project-detail": ["projectStatus:label", "goalStatus:label", "sddPhase:label", "sddFsmState:raw"],
  goals: ["goalStatus:label"],
  "goal-detail": ["goalStatus:label", "taskStatus:label"],
  tasks: ["taskStatus:label"],
  "task-detail": ["taskStatus:label", "stepStatus:raw"],
  "project-form": [],
  "goal-form": ["goalStatus:label"],
  "task-form": [],
  execute: ["runStatus:label", "runTransition:label", "reviewKind:label", "reviewDecision:label", "taskStatus:label"],
  monitor: ["runStatus:label", "runTransition:label", "stepStatus:label", "alertSeverity:label", "alertRule:label", "sddPhase:label", "sddFsmState:raw"],
  import: ["importStatus:label", "gateName:label"],
  settings: [],
  "self-improving": ["obsClass:label", "propClass:label", "propState:raw"],
  issues: ["legend:issues"],
};

const writtenPages = (): PageHelp[] => Object.values(HELP_PAGES).filter((page): page is PageHelp => page !== undefined);

// ── 語料 ────────────────────────────────────────────────────────────────────────────

type Kind = "purpose" | "step" | "fieldMeaning" | "sourceNote" | "stateMeaning" | "stateNext";
type Entry = { where: string; kind: Kind; text: string };

/** 全部說明文字（pending 頁不在語料內）：欄位 meaning 與 sourceNote、狀態 meaning 與 next 逐筆一列。 */
function allHelpTexts(): Entry[] {
  const out: Entry[] = [];
  const pushField = (where: string, field: HelpField) => {
    out.push({ where: `${where} 欄位「${field.name}」`, kind: "fieldMeaning", text: field.meaning });
    if (field.sourceNote !== undefined) out.push({ where: `${where} 欄位「${field.name}」的 sourceNote`, kind: "sourceNote", text: field.sourceNote });
  };
  for (const page of writtenPages()) {
    page.purpose.forEach((text, i) => out.push({ where: `${page.id} purpose[${i}]`, kind: "purpose", text }));
    page.steps.forEach((text, i) => out.push({ where: `${page.id} steps[${i}]`, kind: "step", text }));
    for (const field of page.fields) pushField(page.id, field);
  }
  for (const field of HELP_COMMON.fields) pushField("HELP_COMMON", field);
  for (const [key, field] of Object.entries(SHARED)) pushField(`SHARED.${key}`, field);
  for (const [table, rows] of Object.entries(STATE_HELP)) {
    for (const [key, row] of Object.entries(rows)) {
      out.push({ where: `STATE_HELP.${table}.${key}.meaning`, kind: "stateMeaning", text: row.meaning });
      out.push({ where: `STATE_HELP.${table}.${key}.next`, kind: "stateNext", text: row.next });
    }
  }
  return out;
}

/** 每種文字的句數界線（PRD AC-PH-05-1）；purpose 另有「每頁合計 ≤ 3 句」。 */
const SENTENCE_LIMITS: Readonly<Record<Kind, { min: number; max: number }>> = {
  purpose: { min: 1, max: 3 },
  step: { min: 1, max: 1 },
  fieldMeaning: { min: 1, max: 2 },
  sourceNote: { min: 1, max: 1 },
  stateMeaning: { min: 1, max: 2 },
  stateNext: { min: 1, max: 1 },
};

// ── 測試內的純函式（各有負控）─────────────────────────────────────────────────────────

/** 欄位：source 屬六類之一；sourceNote 選填且不超過 30 個 code point。 */
function fieldProblems(field: HelpField): string[] {
  const out: string[] = [];
  if (!(FIELD_SOURCES as readonly string[]).includes(field.source)) out.push(`source 不是六類之一：${String(field.source)}`);
  if (field.sourceNote !== undefined && codePointLength(field.sourceNote) > 30) out.push(`sourceNote 超過 30 個字：${codePointLength(field.sourceNote)}`);
  return out;
}

function listSourceFiles(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) {
      if (name !== "node_modules" && name !== "tests") listSourceFiles(full, out);
    } else if (/\.(ts|tsx)$/.test(name) && !/\.test\.tsx?$/.test(name) && !/\.d\.ts$/.test(name) && !/\.fixtures\.ts$/.test(name)) out.push(full);
  }
  return out;
}

/** sourceFiles 的一條路徑是否存在：檔案存在，或 `dir/**` 的 dir 存在且展開後至少一個檔；含 `..` 一律不算。 */
function sourcePathExists(entry: string): boolean {
  if (entry.split("/").includes("..")) return false;
  if (entry.endsWith("/**")) {
    const dir = path.join(ROOT, entry.slice(0, -"/**".length));
    return existsSync(dir) && statSync(dir).isDirectory() && listSourceFiles(dir).length >= 1;
  }
  const file = path.join(ROOT, entry);
  return existsSync(file) && statSync(file).isFile();
}

/** 已寫頁的結構界線（AC-PH-03-5；R-PH-06）：回報全部違反的條文。 */
function pageShapeProblems(page: PageHelp, noStatePages: readonly string[]): string[] {
  const out: string[] = [];
  const sentences = page.purpose.flatMap(splitSentences);
  if (page.purpose.length === 0 || page.purpose.some((item) => splitSentences(item).length === 0)) out.push("purpose 至少一項，且每項非空");
  if (sentences.length < 1 || sentences.length > 3) out.push(`purpose 合計 ${sentences.length} 句，須 1～3 句`);
  if (page.steps.length < 2 || page.steps.length > 8) out.push(`steps 有 ${page.steps.length} 步，須 2～8 步`);
  if (page.fields.length < 1) out.push("fields 至少 1 個");
  if (page.sourceFiles.length < 1) out.push("sourceFiles 至少 1 條");
  for (const entry of page.sourceFiles) if (!sourcePathExists(entry)) out.push(`sourceFiles 的路徑不存在：${entry}`);
  const listed = noStatePages.includes(page.id);
  if (page.states.length === 0 && !listed) out.push("states 為空的頁必須登記在 NO_STATE_PAGES");
  if (page.states.length > 0 && listed) out.push("登記在 NO_STATE_PAGES 的頁，states 必須為空");
  if (typeof page.title !== "string" || page.title.trim() === "" || /[・{}]/.test(page.title) || page.title.includes("${"))
    out.push(`title 必須是非空的固定頁名（不含「・」與樣板）：${String(page.title)}`);
  return out;
}

/** 一頁的狀態群→「表 id:名稱模式」集合。 */
const stateGroupKeys = (groups: readonly HelpStateGroup[]): string[] => groups.map((group) => ("legend" in group ? `legend:${group.legend}` : `${group.table}:${group.name ?? "label"}`)).sort();

// ── AC-PH-03-5：已寫頁的結構界線 ────────────────────────────────────────────────────

describe("AT_PH_03_5 已寫頁的結構界線（R-PH-06）", () => {
  it("AT_PH_03_5_1 已寫頁逐頁：purpose 每項非空且合計 1～3 句、steps 2～8 步、fields ≥ 1、sourceFiles ≥ 1 且路徑存在、states 為空⇔在 NO_STATE_PAGES、title 為固定頁名；pending 頁豁免並印出清單", () => {
    const pages = writtenPages();
    expect(pages.length, "防反空轉：已寫頁數（輪 1a 起至少三頁）").toBeGreaterThanOrEqual(3);
    for (const page of pages) expect(pageShapeProblems(page, NO_STATE_PAGES), `${page.id}`).toEqual([]);
    // NO_STATE_PAGES 內的已寫頁其 states 必為空（雙向的另一半，逐頁在 pageShapeProblems 內已判；這裡對名單本身再判一次）
    for (const id of NO_STATE_PAGES) {
      const page = HELP_PAGES[id];
      if (page !== undefined) expect(page.states, `${id} 在 NO_STATE_PAGES，states 必須為空`).toEqual([]);
    }
    // 豁免是明列的，不是靜默略過
    console.info(`[page-help] 內容類檢查豁免的待寫頁（${PENDING_HELP_PAGES.length}）：${PENDING_HELP_PAGES.join("、") || "（無）"}`);
    for (const id of PENDING_HELP_PAGES) expect(HELP_PAGES[id], `${id} 是待寫頁，不在語料內`).toBeUndefined();
  });

  it("AT_PH_03_5_2 頁→狀態表矩陣：已寫頁中屬於 PRD 十六頁者，states 的表 id 集合與名稱模式（label 預設／raw）等於 PRD §4 的狀態表欄；十六頁都已登記（已寫或待寫）", () => {
    const registered = new Set<string>([...Object.keys(HELP_PAGES), ...PENDING_HELP_PAGES]);
    for (const id of REQUIRED_PAGE_IDS) expect(registered.has(id), `PRD 十六頁之一 ${id} 沒有登記`).toBe(true);
    expect(Object.keys(PAGE_STATES).sort()).toEqual([...REQUIRED_PAGE_IDS].sort());
    let checked = 0;
    for (const page of writtenPages()) {
      const expected = PAGE_STATES[page.id as (typeof REQUIRED_PAGE_IDS)[number]];
      if (expected === undefined) continue; // 矩陣外的頁（姊妹案）不受此鎖
      expect(stateGroupKeys(page.states), `${page.id} 的狀態群`).toEqual([...expected].sort());
      checked += 1;
    }
    expect(checked, "防反空轉：逐頁比對的頁數").toBeGreaterThanOrEqual(3);
    // 矩陣自身的不變式：execute 不含 stepStatus；monitor 的 stepStatus 是 label、task-detail 的是 raw
    expect(PAGE_STATES.execute.some((key) => key.startsWith("stepStatus"))).toBe(false);
    expect(PAGE_STATES.monitor).toContain("stepStatus:label");
    expect(PAGE_STATES["task-detail"]).toContain("stepStatus:raw");
  });

  it("AT_PH_03_5_E_1 pageShapeProblems 負控：purpose 4 句（四項各一句，或一項四句）、purpose 空、steps 1 項與 9 項、fields 空、sourceFiles 含不存在路徑或為空、states 與 NO_STATE_PAGES 不一致、title 含樣板各回非空；邊界合規頁回空", () => {
    const base: PageHelp = {
      id: "settings",
      title: "測試頁",
      purpose: ["第一句。"],
      steps: ["步驟一。", "步驟二。"],
      fields: [{ name: "欄位甲", meaning: "意思。", source: "系統自動產生" }],
      states: [],
      sourceFiles: ["lib/help/types.ts"],
    };
    const noState = ["settings"];
    expect(pageShapeProblems(base, noState), "基準合規頁").toEqual([]);
    // 邊界合規：purpose 一項一句、一項三句；steps 2 項、8 項；sourceFiles 用 dir/**
    expect(pageShapeProblems({ ...base, purpose: ["甲。乙。丙。"] }, noState)).toEqual([]);
    expect(pageShapeProblems({ ...base, steps: Array.from({ length: 8 }, (_, i) => `步驟${i}。`) }, noState)).toEqual([]);
    expect(pageShapeProblems({ ...base, sourceFiles: ["lib/help/**"] }, noState)).toEqual([]);

    const bad: Array<[string, PageHelp]> = [
      ["purpose 四項各一句", { ...base, purpose: ["甲。", "乙。", "丙。", "丁。"] }],
      ["purpose 一項四句", { ...base, purpose: ["甲。乙。丙。丁。"] }],
      ["purpose 空", { ...base, purpose: [] }],
      ["purpose 有空項", { ...base, purpose: ["甲。", "  "] }],
      ["steps 一項", { ...base, steps: ["只有一步。"] }],
      ["steps 九項", { ...base, steps: Array.from({ length: 9 }, (_, i) => `步驟${i}。`) }],
      ["fields 空", { ...base, fields: [] }],
      ["sourceFiles 空", { ...base, sourceFiles: [] }],
      ["sourceFiles 不存在的檔", { ...base, sourceFiles: ["components/nope/Missing.tsx"] }],
      ["sourceFiles 不存在的目錄", { ...base, sourceFiles: ["components/nope/**"] }],
      ["sourceFiles 含 ..", { ...base, sourceFiles: ["lib/../lib/help/types.ts"] }],
      ["states 空而不在 NO_STATE_PAGES", { ...base, id: "projects" }],
      ["在 NO_STATE_PAGES 卻有 states", { ...base, states: [{ table: "projectStatus" }] }],
      ["title 空", { ...base, title: "" }],
      ["title 含樣板", { ...base, title: "專案執行：${name}" }],
      ["title 含間隔點", { ...base, title: "專案・本頁說明" }],
    ];
    expect(bad).toHaveLength(16);
    for (const [name, page] of bad) expect(pageShapeProblems(page, noState), name).not.toEqual([]);
  });
});

// ── AC-PH-05-1～05-3：全部文字逐筆過 lint ─────────────────────────────────────────────

describe("AT_PH_05 說明文字的白話檢查（R-PH-16）", () => {
  it("AT_PH_05_1_1 每句 ≤ 60 個字；每頁 purpose 合計 ≤ 3 句；steps 每項恰 1 句；欄位與狀態 meaning ≤ 2 句、next 恰 1 句、sourceNote ≤ 1 句；每筆至少一句", () => {
    const texts = allHelpTexts();
    const stateRows = texts.filter((e) => e.kind === "stateMeaning").length;
    expect(stateRows, "防反空轉：STATE_HELP 的列數").toBeGreaterThanOrEqual(REQUIRED_TABLE_IDS.length);
    expect(
      texts.some((e) => e.kind === "purpose"),
      "語料含至少一個已寫頁",
    ).toBe(true);
    for (const id of REQUIRED_TABLE_IDS) expect(Object.keys(STATE_HELP), `必備的表 ${id}`).toContain(id);

    for (const entry of texts) {
      const sentences = splitSentences(entry.text);
      const limit = SENTENCE_LIMITS[entry.kind];
      expect(sentences.length >= limit.min && sentences.length <= limit.max, `${entry.where}：${sentences.length} 句，界線 ${limit.min}～${limit.max}`).toBe(true);
      for (const sentence of sentences) expect(codePointLength(sentence), `${entry.where} 的句子過長：${sentence}`).toBeLessThanOrEqual(60);
    }
    for (const page of writtenPages()) {
      const total = page.purpose.flatMap(splitSentences).length;
      expect(total, `${page.id} 的 purpose 合計句數`).toBeLessThanOrEqual(3);
    }
    // pending 頁不在語料內（它們的佔位 purpose 是空的，納入反而會誤紅）
    const ids = new Set(texts.map((e) => e.where.split(" ")[0]));
    for (const id of PENDING_HELP_PAGES) expect(ids.has(id), `${id} 是待寫頁，不該在語料內`).toBe(false);
  });

  it("AT_PH_05_2_1 每筆說明文字都沒有白名單外的英文詞（欄位名與狀態名是畫面字樣的逐字引用，不在語料內）；失敗訊息列出頁／表、位置與詞", () => {
    const problems = allHelpTexts().flatMap((e) => {
      const words = unlistedEnglishWords(e.text);
      return words.length > 0 ? [`${e.where}：${words.join("、")}`] : [];
    });
    expect(problems).toEqual([]);
  });

  it("AT_PH_05_3_1 每筆說明文字都沒有禁用字元（emoji、色碼、Markdown 記號、HTML 標籤、://、磁碟機或家目錄路徑、連續 3 位以上數字；ID 形態先剔除）", () => {
    const problems = allHelpTexts().flatMap((e) => {
      const found = forbiddenFindings(e.text);
      return found.length > 0 ? [`${e.where}：${found.join("、")}`] : [];
    });
    expect(problems).toEqual([]);
  });
});

// ── AC-PH-05-4：欄位來源 ────────────────────────────────────────────────────────────

describe("AT_PH_05_4 欄位資料來源（R-PH-17）", () => {
  it("AT_PH_05_4_1 已寫頁欄位、HELP_COMMON.fields 與 SHARED 的每個欄位：source 屬六類之一、sourceNote 缺或不超過 30 個字；型別 FieldSource 等於這六類（tsc 判定）", () => {
    expectTypeOf<FieldSource>().toEqualTypeOf<(typeof FIELD_SOURCES)[number]>();
    const fields: Array<[string, HelpField]> = [
      ...writtenPages().flatMap((page) => page.fields.map((field): [string, HelpField] => [`${page.id}.${field.name}`, field])),
      ...HELP_COMMON.fields.map((field): [string, HelpField] => [`HELP_COMMON.${field.name}`, field]),
      ...Object.entries(SHARED).map(([key, field]): [string, HelpField] => [`SHARED.${key}`, field]),
    ];
    expect(fields.length, "防反空轉：欄位數").toBeGreaterThanOrEqual(10);
    for (const [where, field] of fields) {
      expect(fieldProblems(field), where).toEqual([]);
      expect(field.name.trim() !== "" && field.meaning.trim() !== "", `${where} 的欄位名與意思都要非空`).toBe(true);
    }
    // 六類在實際內容中至少用到兩類（防止全部寫成同一類而鎖被架空）
    expect(new Set(fields.map(([, field]) => field.source)).size).toBeGreaterThanOrEqual(2);
  });

  it("AT_PH_05_4_E_1 fieldProblems 負控：source「手動」回非空；sourceNote 恰 30 字回空、31 字回非空；sourceNote 缺回空；六類各一個合規欄位回空", () => {
    const base: HelpField = { name: "欄位甲", meaning: "意思。", source: "系統自動產生" };
    expect(fieldProblems({ ...base, source: "手動" as FieldSource })).not.toEqual([]);
    expect(fieldProblems({ ...base, sourceNote: "字".repeat(30) })).toEqual([]);
    expect(fieldProblems({ ...base, sourceNote: "字".repeat(31) })).not.toEqual([]);
    expect(fieldProblems({ ...base, sourceNote: String.fromCodePoint(0x20bb7).repeat(30) }), "以 code point 計，不用 String.length").toEqual([]);
    expect(fieldProblems({ ...base, sourceNote: undefined })).toEqual([]);
    expect(FIELD_SOURCES).toHaveLength(6);
    for (const source of FIELD_SOURCES) expect(fieldProblems({ ...base, source }), source).toEqual([]);
  });
});
