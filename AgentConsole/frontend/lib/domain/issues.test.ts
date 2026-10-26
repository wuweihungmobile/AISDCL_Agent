import { readFileSync } from "node:fs";
import path from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import * as api from "@/lib/api/endpoints";
import type { Issue, IssueLegend, IssueSummary } from "@/lib/api/types";
import { clearSession, resetSessionCache } from "@/lib/auth/store";
import { LEGEND, makeIssue } from "@/components/domain/issues/tests/issues.fixtures";
import {
  EMPTY_ISSUE_FILTERS,
  ENGLISH_STATE_WORDS,
  ISSUE_REASONS,
  ISSUE_TABS,
  SEVERITY_KEYS,
  buildPriorityRequest,
  countText,
  displayOrder,
  effectivePriority,
  englishStateWords,
  filterIssues,
  foldAscii,
  hintLines,
  hintTitle,
  isPinned,
  issueWriteErrorText,
  issuesErrorSummary,
  matchesKeyword,
  orDash,
  pinnedStatuses,
  resultOptions,
  severityCounts,
  severityLabels,
  sortIssues,
  sourceOptions,
  statusPillNames,
  statusText,
  summaryCount,
  tabStatus,
  validatePriorityForm,
  type SortableIssue,
} from "./issues";

const ids = (items: ReadonlyArray<{ id: string }>) => items.map((i) => i.id);
/** 排序夾具：只填排序用的欄位，其餘取預設。 */
const sortable = (id: string, severityRank: number | null, updatedAt: string | null, patch: Partial<Issue> = {}): Issue => makeIssue(id, { severityRank, updatedAt, ...patch });

// ── §5.5 範例排序表（D-R12：根層與前端各嵌一份相同的表與預期序）──────────────────────────────
const RULE_ONE = (): Issue[] => [
  sortable("DEF-999-001", 1, "2026-10-10"),
  sortable("DEF-999-002", 1, "2026-10-05"),
  sortable("DEF-999-003", 2, "2026-10-01"),
  sortable("DEF-999-004", null, "2026-10-02"),
  sortable("DEF-999-005", 3, null),
  sortable("DEF-999-006", 3, "2026-10-20"),
  sortable("DEF-999-007", 1, "2026-10-05"),
];
const ORDER_ONE = ["DEF-999-002", "DEF-999-007", "DEF-999-001", "DEF-999-003", "DEF-999-006", "DEF-999-005", "DEF-999-004"];
const RULE_TWO = (): Issue[] => [
  sortable("DEF-999-011", null, "2026-10-20"),
  sortable("DEF-999-012", null, "2026-10-20"),
  sortable("DEF-999-013", null, "2026-10-25"),
  sortable("DEF-999-014", null, null),
  sortable("DEF-999-015", null, "2026-09-30"),
];
const ORDER_TWO = ["DEF-999-013", "DEF-999-011", "DEF-999-012", "DEF-999-015", "DEF-999-014"];
/** 含順位：003＝1、002＝2、001＝2、005＝非可排卻有遺留順位 1（不參與排序）。 */
const WITH_PRIORITY = (): Issue[] =>
  RULE_ONE().map((i) => {
    const rank: Record<string, number> = { "DEF-999-003": 1, "DEF-999-002": 2, "DEF-999-001": 2, "DEF-999-005": 1 };
    return i.id in rank ? { ...i, priority: rank[i.id], priorityNote: "備註", rankable: i.id !== "DEF-999-005" } : i;
  });
const ORDER_THREE = ["DEF-999-003", "DEF-999-002", "DEF-999-001", "DEF-999-007", "DEF-999-006", "DEF-999-005", "DEF-999-004"];

describe("AT_IC_05_1 顯示序：兩條規則與範例排序表", () => {
  it("AT_IC_05_1_2 sortIssues：待處理與待您決定依第一條（順位→severityRank→updatedAt→id），已完成與全部依第二條；無順位子集與根層預期序相同", () => {
    expect(ids(sortIssues(RULE_ONE(), "pending"))).toEqual(ORDER_ONE);
    expect(ids(sortIssues(RULE_ONE(), "decide"))).toEqual(ORDER_ONE);
    expect(ids(sortIssues(RULE_TWO(), "done"))).toEqual(ORDER_TWO);
    expect(ids(sortIssues(RULE_TWO(), "all"))).toEqual(ORDER_TWO);
    // 含順位：順位升冪在最前、無順位最後；非可排的遺留順位（005）不參與
    expect(ids(sortIssues(WITH_PRIORITY(), "pending"))).toEqual(ORDER_THREE);
    // 無順位子集（沒有任何順位）的結果與預期序一相同；輸入不被改動（回傳新陣列）
    const input = RULE_ONE();
    const before = ids(input);
    sortIssues(input, "pending");
    expect(ids(input)).toEqual(before);
    // 第二條不看順位與嚴重度：同一批資料換成已完成規則，只依日期與編號
    expect(ids(sortIssues(WITH_PRIORITY(), "done"))).toEqual(["DEF-999-006", "DEF-999-001", "DEF-999-002", "DEF-999-007", "DEF-999-004", "DEF-999-003", "DEF-999-005"]);
  });

  it("AT_IC_05_1_E_2 遺留順位不參與排序（視為無順位）；順位相同者回到 severityRank、updatedAt、id", () => {
    // 非可排卻有遺留順位 1：不得因此排到最前
    const legacy = [sortable("DEF-999-021", 4, "2026-10-01", { rankable: false, priority: 1 }), sortable("DEF-999-022", 1, "2026-10-02", { rankable: true, priority: null })];
    expect(effectivePriority(legacy[0])).toBeNull();
    expect(ids(sortIssues(legacy, "pending"))).toEqual(["DEF-999-022", "DEF-999-021"]);
    // 同順位：依 severityRank（小者先）→ updatedAt（舊者先）→ id
    const tied = [
      sortable("DEF-999-033", 2, "2026-10-01", { priority: 5 }),
      sortable("DEF-999-031", 3, "2026-10-01", { priority: 5 }),
      sortable("DEF-999-032", 2, "2026-10-01", { priority: 5 }),
      sortable("DEF-999-034", 2, "2026-09-01", { priority: 5 }),
    ];
    expect(ids(sortIssues(tied, "pending"))).toEqual(["DEF-999-034", "DEF-999-032", "DEF-999-033", "DEF-999-031"]);
    // 順位 1 先於順位 9999；有順位者先於無順位者（即使無順位者的嚴重度更高）
    const extremes = [sortable("DEF-999-041", 1, "2026-10-01"), sortable("DEF-999-042", 4, "2026-10-01", { priority: 9999 }), sortable("DEF-999-043", 4, "2026-10-01", { priority: 1 })];
    expect(ids(sortIssues(extremes, "pending"))).toEqual(["DEF-999-043", "DEF-999-042", "DEF-999-041"]);
  });

  it("AT_IC_09_10_E_1 遺留順位與排序：非可排的列沒有有效順位、不參與排序；可排的列照常", () => {
    const legacy: SortableIssue = { id: "DEF-999-051", severityRank: 1, updatedAt: null, rankable: false, priority: 3 };
    const live: SortableIssue = { ...legacy, rankable: true };
    expect(effectivePriority(legacy)).toBeNull();
    expect(effectivePriority(live)).toBe(3);
    expect(effectivePriority({ ...live, priority: null })).toBeNull();
    // 遺留順位 1 的列不會壓過有真順位 2 的列
    const rows = [
      { ...legacy, id: "DEF-999-052", priority: 1 },
      { ...live, id: "DEF-999-053", priority: 2 },
    ];
    expect(ids(sortIssues(rows, "decide"))).toEqual(["DEF-999-053", "DEF-999-052"]);
  });

  it("全部分頁置頂：置頂狀態（圖例中專屬分頁為待您決定的狀態）先於其他列、其內依第一條，其餘依第二條；置頂只改順序、不改件數", () => {
    const pinned = pinnedStatuses(LEGEND);
    expect([...pinned]).toEqual(["待您決定"]);
    const rows = [
      sortable("DEF-999-061", 2, "2026-10-30", { status: "已完成" }),
      sortable("DEF-999-062", 3, "2026-10-01", { status: "待您決定" }),
      sortable("DEF-999-063", 1, "2026-10-02", { status: "待您決定" }),
      sortable("DEF-999-064", 2, "2026-10-29", { status: "待解" }),
    ];
    const ordered = displayOrder(rows, "all", pinned);
    expect(ids(ordered)).toEqual(["DEF-999-063", "DEF-999-062", "DEF-999-061", "DEF-999-064"]);
    expect(ordered).toHaveLength(rows.length);
    // 其他分頁沒有置頂行為
    expect(ids(displayOrder(rows, "done", pinned))).toEqual(["DEF-999-061", "DEF-999-064", "DEF-999-063", "DEF-999-062"]);
    expect(isPinned(rows[1], "all", pinned)).toBe(true);
    expect(isPinned(rows[0], "all", pinned)).toBe(false);
    expect(isPinned(rows[0], "decide", pinned)).toBe(true);
    expect(isPinned(rows[1], "pending", pinned)).toBe(false);
    expect(isPinned(rows[1], "done", pinned)).toBe(false);
    expect(pinnedStatuses(undefined).size).toBe(0);
  });
});

// ── 契約 reason 表的雙向鎖（AC-IC-07-9；比照 lib/api/reasons.test.ts）──────────────────────────
const COLUMNS = ["reason", "狀態碼", "details", "中文訊息", "意義"];
type ReasonTable = { header: string[]; rows: Map<string, string[]> };

/** 一列的各欄（去頭尾 `|`、逐欄去空白；欄內以 `\|` 跳脫的豎線保留成 `|`）。 */
function cellsOf(line: string): string[] {
  const body = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  const out: string[] = [];
  let current = "";
  for (let i = 0; i < body.length; i++) {
    if (body[i] === "\\" && body[i + 1] === "|") {
      current += "|";
      i++;
    } else if (body[i] === "|") {
      out.push(current.trim());
      current = "";
    } else current += body[i];
  }
  out.push(current.trim());
  return out;
}

/** 以標題 `issue 類 reason 表` 起頭的第一張表為準（標題之前的他表、標題之後的第二張表都不影響）；找不到標題或表就丟錯（鎖不得因缺表而空過）。 */
function parseReasonTable(markdown: string): ReasonTable {
  const lines = markdown.split(/\r?\n/);
  const heading = lines.findIndex((l) => /^#{1,6}\s*issue 類 reason 表/.test(l));
  if (heading < 0) throw new Error("找不到標題「issue 類 reason 表」");
  const start = lines.findIndex((l, i) => i > heading && l.startsWith("|"));
  if (start < 0) throw new Error("標題「issue 類 reason 表」之後沒有表格");
  const table: string[][] = [];
  for (let i = start; i < lines.length && lines[i].startsWith("|"); i++) table.push(cellsOf(lines[i]));
  if (table.length < 2) throw new Error("表格缺標題列或分隔列");
  const rows = new Map<string, string[]>();
  for (const row of table.slice(2)) rows.set(row[0].replace(/^`(.*)`$/, "$1"), row);
  return { header: table[0], rows };
}

/** 契約表對前端常數的比對：欄序、reason 集合（雙向）、每個 reason 的中文訊息逐字相同；回問題清單（空＝一致）。 */
function reasonTableProblems(table: ReasonTable, code: Readonly<Record<string, string>>): string[] {
  const problems: string[] = [];
  if (JSON.stringify(table.header) !== JSON.stringify(COLUMNS)) problems.push(`欄序不符：${JSON.stringify(table.header)}`);
  for (const reason of table.rows.keys()) if (!(reason in code)) problems.push(`契約表有、前端沒有：${reason}`);
  for (const reason of Object.keys(code)) if (!table.rows.has(reason)) problems.push(`前端有、契約表沒有：${reason}`);
  for (const [reason, message] of Object.entries(code)) {
    const cell = table.rows.get(reason)?.[3];
    if (cell !== undefined && cell !== message) problems.push(`中文訊息不符（${reason}）：契約表「${cell}」，前端「${message}」`);
  }
  return problems;
}

const CONTRACT = path.join(process.cwd(), "..", "docs", "02_architecture", "API_Contract_IssueCenter.md");

describe("AT_IC_07_9 ISSUE_REASONS 與契約 reason 表雙向相等", () => {
  it("AT_IC_07_9_1 契約表（只列 issue 類）與 ISSUE_REASONS 的 reason 鍵集合與中文訊息逐字雙向相等；訊息就是 409 要顯示的那句", () => {
    const table = parseReasonTable(readFileSync(CONTRACT, "utf-8"));
    expect(table.rows.size, "防反空轉：契約表至少有一個 reason").toBeGreaterThan(0);
    expect(reasonTableProblems(table, ISSUE_REASONS)).toEqual([]);
    expect([...table.rows.keys()]).toEqual(["issue_not_rankable"]);
    expect(ISSUE_REASONS.issue_not_rankable).toBe("此議題目前的狀態不能設定優先順序");
  });

  const HEADER = "| reason | 狀態碼 | details | 中文訊息 | 意義 |\n|---|---|---|---|---|\n";
  const ROW = "| `issue_not_rankable` | 409 | `id`、`status` | 此議題目前的狀態不能設定優先順序 | 不可排 |\n";
  const doc = (before: string, table: string, after: string) => `# 契約\n\n${before}### issue 類 reason 表（C5.1）\n\n${table}\n${after}`;

  it("AT_IC_07_9_E_1 合成契約字串：多一列、少一列、訊息差一字、欄序對調各回非空；標題之前的他表與之後的第二張表不影響結果", () => {
    const broken: Record<string, string> = {
      多一列: doc("", `${HEADER}${ROW}| \`issue_extra\` | 409 | | 多出的 | x |\n`, ""),
      少一列: doc("", HEADER, ""),
      訊息差一字: doc("", HEADER + ROW.replace("優先順序", "優先順位"), ""),
      欄序對調: doc("", "| 狀態碼 | reason | details | 中文訊息 | 意義 |\n|---|---|---|---|---|\n| 409 | `issue_not_rankable` | `id`、`status` | 此議題目前的狀態不能設定優先順序 | 不可排 |\n", ""),
    };
    for (const [label, markdown] of Object.entries(broken)) expect(reasonTableProblems(parseReasonTable(markdown), ISSUE_REASONS), label).not.toEqual([]);
    const decoys = doc("## 他表\n\n| a | b |\n|---|---|\n| x | y |\n\n", HEADER + ROW, `### 第二張表\n\n${HEADER}| \`bogus\` | 500 | | 不該被讀到 | x |\n`);
    expect(reasonTableProblems(parseReasonTable(decoys), ISSUE_REASONS)).toEqual([]);
    // 缺標題或缺表要大聲失敗，不能空過
    expect(() => parseReasonTable(`# 沒有標題\n\n${HEADER}${ROW}`)).toThrow();
    expect(() => parseReasonTable("### issue 類 reason 表\n\n沒有表格\n")).toThrow();
  });
});

// ── 英文詞偵測（AC-IC-08-1；§5.4）──────────────────────────────────────────────────────
const TCS_WORDS = [
  "open",
  "deferred",
  "fixed",
  "decided",
  "retired",
  "merged",
  "proposed",
  "routed",
  "wontfix",
  "closed-by-decision",
  "no_action_needed",
  "partial",
  "workaround",
  "verified",
  "approved",
  "returned",
  "sandboxed",
  "promoted",
  "measuring",
  "closed",
  "rejected",
  "handed-off",
];

describe("AT_IC_08_1_E_1 英文詞偵測函式的負控", () => {
  it("AT_IC_08_1_E_1 含 open、fixed@abc、handed-off 者回非空；含 PROP-SI-004、中文、「P1」者回空；詞表與 §5.4 的 22 詞逐字相同", () => {
    expect([...ENGLISH_STATE_WORDS]).toEqual(TCS_WORDS);
    expect(ENGLISH_STATE_WORDS).toHaveLength(22);
    expect(englishStateWords("狀態是 open")).toEqual(["open"]);
    expect(englishStateWords("fixed@abc1234")).toEqual(["fixed"]);
    expect(englishStateWords("轉交 handed-off 給別人")).toEqual(["handed-off"]);
    for (const clean of ["PROP-SI-004", "OBS-SI-001 與 DEF-200-101", "已完成・已修復", "P1", "等掌舵者決定：核准、否決或退回", ""]) expect(englishStateWords(clean), clean).toEqual([]);
    // 22 詞逐一能被抓到
    for (const word of TCS_WORDS) expect(englishStateWords(`前 ${word} 後`), word).toContain(word);
  });

  it("AT_IC_08_1_E_1 整詞比對：前後字元屬英數或 - 者不算（reopens、opened、unclosed），ID 形態先剔除；大小寫不拘；連字號詞整個比對", () => {
    for (const notWord of ["reopens", "opened", "unclosed", "prefixed", "re-open", "open-ended", "partially"]) expect(englishStateWords(notWord), notWord).toEqual([]);
    expect(englishStateWords("Open")).toEqual(["open"]);
    expect(englishStateWords("(closed)")).toEqual(["closed"]);
    expect(englishStateWords("closed-by-decision")).toEqual(["closed-by-decision"]);
    expect(englishStateWords("open、deferred 與 closed")).toEqual(["open", "deferred", "closed"]);
    // 議題 ID 形態先剔除：緊鄰的詞仍照常判斷
    expect(englishStateWords("OBS-SI-001 open")).toEqual(["open"]);
  });
});

// ── 嚴重度計件（AC-IC-08-9）───────────────────────────────────────────────────────────

/** 固定種子的亂數（mulberry32）：生成式夾具要可重現。 */
function prng(seed: number): () => number {
  let a = seed;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

describe("AT_IC_08_9_E_1 嚴重度計件函式表驅動", () => {
  const POOL: Array<[severity: string | null, rank: number | null]> = [
    [null, null],
    ["緊急", 1],
    ["高", 2],
    ["中", 3],
    ["低", 4],
    ["未歸類：P5", null],
    ["未歸類：P7", 7],
    ["中", 9],
    ["高", 0],
    ["低", null],
    ["高", 2.5],
  ];

  it("AT_IC_08_9_E_1 severity 為 null 計「—」、「未歸類：P5」類計「未歸類」、未知 rank 不計入前四格；固定種子的生成式夾具上加總不變式恆成立", () => {
    expect(severityCounts([])).toEqual({ urgent: 0, high: 0, mid: 0, low: 0, none: 0, unmapped: 0 });
    // 逐列表驅動：每一種組合各落入預期的一格
    const expected: Record<string, string> = {
      "null|null": "none",
      "緊急|1": "urgent",
      "高|2": "high",
      "中|3": "mid",
      "低|4": "low",
      "未歸類：P5|null": "unmapped",
      "未歸類：P7|7": "unmapped",
      "中|9": "unmapped",
      "高|0": "unmapped",
      "低|null": "unmapped",
      "高|2.5": "unmapped",
    };
    for (const [severity, rank] of POOL) {
      const counts = severityCounts([{ severity, severityRank: rank }]);
      const key = expected[`${String(severity)}|${String(rank)}`];
      expect(counts[key as keyof typeof counts], `${String(severity)}／${String(rank)}`).toBe(1);
      expect(Object.values(counts).reduce((a, b) => a + b, 0)).toBe(1);
    }
    // 生成式：500 筆、三種子；各格與獨立的算法逐格相等，加總恆等於輸入件數
    for (const seed of [1, 20261027, 99]) {
      const next = prng(seed);
      const items = Array.from({ length: 500 }, () => {
        const [severity, severityRank] = POOL[Math.floor(next() * POOL.length)];
        return { severity, severityRank };
      });
      const counts = severityCounts(items);
      const oracle = { urgent: 0, high: 0, mid: 0, low: 0, none: 0, unmapped: 0 };
      for (const { severity, severityRank } of items) oracle[expected[`${String(severity)}|${String(severityRank)}`] as keyof typeof oracle] += 1;
      expect(counts).toEqual(oracle);
      expect(Object.values(counts).reduce((a, b) => a + b, 0)).toBe(items.length);
    }
    expect([...SEVERITY_KEYS]).toEqual(["urgent", "high", "mid", "low", "none", "unmapped"]);
  });

  it("六格的文字：前四格取自圖例（依 rank），「—」固定，未歸類取圖例的前綴字串；圖例缺某個 rank 時退回「—」", () => {
    expect(severityLabels(LEGEND)).toEqual({ urgent: "緊急", high: "高", mid: "中", low: "低", none: "—", unmapped: "未歸類" });
    const renamed: IssueLegend = { ...LEGEND, unmappedLabel: "其他", severities: LEGEND.severities.map((s) => ({ ...s, name: `${s.name}級` })).filter((s) => s.rank !== 3) };
    expect(severityLabels(renamed)).toEqual({ urgent: "緊急級", high: "高級", mid: "—", low: "低級", none: "—", unmapped: "其他" });
  });
});

// ── 其餘純函式 ──────────────────────────────────────────────────────────────────────

describe("分頁、摘要與列內文字", () => {
  it("四個分頁依序為待處理、待您決定、已完成、全部；全部不帶 status，其餘三個把分頁名原樣當 status（前端不展開成員清單）", () => {
    expect(ISSUE_TABS.map((t) => [t.id, t.label, t.status])).toEqual([
      ["pending", "待處理", "待處理"],
      ["decide", "待您決定", "待您決定"],
      ["done", "已完成", "已完成"],
      ["all", "全部", null],
    ]);
    expect(tabStatus("all")).toBeNull();
    expect(tabStatus("pending")).toBe("待處理");
  });

  it("摘要格：數字原樣；null、缺鍵、沒有摘要（載入中、失敗）一律是量不到，顯示「—」而不是 0", () => {
    const summary: IssueSummary = { total: 3, byStatus: {}, byTab: { 待處理: 2, 待您決定: 0, 已完成: null }, unmapped: 0 };
    expect(summaryCount(summary, "pending")).toBe(2);
    expect(summaryCount(summary, "decide")).toBe(0);
    expect(summaryCount(summary, "done")).toBeNull();
    expect(summaryCount({ ...summary, byTab: {} }, "pending")).toBeNull();
    expect(summaryCount(undefined, "pending")).toBeNull();
    expect(countText(0)).toBe("0");
    expect(countText(null)).toBe("—");
  });

  it("列內文字：已結案者狀態併列結果；null 與空字串顯示「—」", () => {
    expect(statusText({ status: "已完成", result: "已修復" })).toBe("已完成・已修復");
    expect(statusText({ status: "待解", result: null })).toBe("待解");
    expect(orDash(null)).toBe("—");
    expect(orDash("")).toBe("—");
    expect(orDash("x")).toBe("x");
  });
});

describe("篩選（來源、狀態 pill、結果、關鍵字取交集）", () => {
  const rows: Issue[] = [
    makeIssue("DEF-999-071", { source: "系統缺陷", status: "待解", title: "Alpha 與 beta" }),
    makeIssue("DEF-999-072", { source: "研究提案", status: "已完成", result: "已採納", title: "只有標題含關鍵字 KeyWord" }),
    makeIssue("DEF-999-073", { source: "未歸類：later", status: "未歸類：later", title: "表外值" }),
    makeIssue("DEF-999-074", { source: null, status: "待您決定", title: "來源讀不到" }),
  ];

  it("關鍵字：不分大小寫（ASCII）的子字串、比對編號與標題；前後空白去掉、空白＝不篩；非 ASCII 字元不做折疊", () => {
    expect(foldAscii("PROP-SI-004 Ａ")).toBe("prop-si-004 Ａ");
    expect(matchesKeyword(rows[0], "def-999-071")).toBe(true);
    expect(matchesKeyword(rows[0], "ALPHA")).toBe(true);
    expect(matchesKeyword(rows[1], "keyword")).toBe(true);
    expect(matchesKeyword(rows[0], "gamma")).toBe(false);
    expect(matchesKeyword(rows[0], "   ")).toBe(true);
    expect(matchesKeyword(rows[0], "")).toBe(true);
    expect(matchesKeyword(rows[0], "  beta  ")).toBe(true);
    expect(matchesKeyword(rows[0], "ａlpha")).toBe(false);
  });

  it("來源與狀態：空字串＝不篩；等於圖例前綴字串（未歸類）＝篩表外值；其餘全等；結果只比結果欄；四者取交集", () => {
    const f = (patch: Partial<typeof EMPTY_ISSUE_FILTERS>) => ids(filterIssues(rows, { ...EMPTY_ISSUE_FILTERS, ...patch }, LEGEND));
    expect(f({})).toEqual(ids(rows));
    expect(f({ source: "系統缺陷" })).toEqual(["DEF-999-071"]);
    expect(f({ source: "未歸類" })).toEqual(["DEF-999-073"]);
    expect(f({ status: "未歸類" })).toEqual(["DEF-999-073"]);
    expect(f({ status: "待您決定" })).toEqual(["DEF-999-074"]);
    expect(f({ result: "已採納" })).toEqual(["DEF-999-072"]);
    expect(f({ source: "研究提案", result: "已採納", keyword: "keyword" })).toEqual(["DEF-999-072"]);
    expect(f({ source: "研究提案", keyword: "alpha" })).toEqual([]);
    // 沒有圖例（載入前）：只剩全等比對，不認前綴字串
    expect(ids(filterIssues(rows, { ...EMPTY_ISSUE_FILTERS, status: "未歸類" }, undefined))).toEqual([]);
  });

  it("下拉與 pill 的選項取自圖例：來源＝全部＋四來源＋前綴字串；結果＝全部＋八結果；狀態 pill＝七狀態＋前綴字串", () => {
    expect(sourceOptions(LEGEND).map((o) => o.label)).toEqual(["全部", "使用者提案", "系統缺陷", "研究提案", "系統改善", "未歸類"]);
    expect(resultOptions(LEGEND).map((o) => o.label)).toEqual(["全部", "已修復", "已採納", "已否決", "已退役", "已裁決", "已轉交", "已合併", "已回滾"]);
    expect(statusPillNames(LEGEND)).toEqual(["候選", "待您決定", "待解", "進行中", "觀察中", "延後", "已完成", "未歸類"]);
    expect(sourceOptions(LEGEND)[0]).toEqual({ value: "", label: "全部" });
  });
});

describe("提示條文字（說明取自圖例）", () => {
  it("標題：ne、problems 各自非空才帶；兩者皆空沒有提示條", () => {
    expect(hintTitle([], [])).toBeNull();
    expect(hintTitle([{ field: "ledger.defect", reason: "DEFECT-LEDGER-UNAVAILABLE" }], [])).toBe("提示：1 項資料量不到");
    expect(hintTitle([], [{ subject: "OBS-SI-012", code: "ROW-ARITY", detail: "欄數與表頭不符" }])).toBe("提示：1 筆帳本問題");
    expect(hintTitle([{ field: "a", reason: "x" }], [{ subject: "s", code: "c", detail: "" }])).toBe("提示：1 項資料量不到、1 筆帳本問題");
  });

  it("逐行：ne 依理由、problems 依問題碼分組；說明取自圖例，圖例沒有的碼退回原碼；帳本讀不到時由圖例的釋義明說是哪一本；對象過多以「等共 N 項」收尾", () => {
    const lines = hintLines(
      [
        { field: "ledger.defect", reason: "DEFECT-LEDGER-UNAVAILABLE" },
        { field: "ledger.sibling.AutoSDD_External_Blocked_Log.md", reason: "SIBLING-LEDGER-UNAVAILABLE" },
        { field: "ledger.sibling.AutoSDD_Structural_Debt_Log.md", reason: "SIBLING-LEDGER-UNAVAILABLE" },
        { field: "issues.PROP-SI-004.severity", reason: "SEVERITY-UNAVAILABLE" },
        { field: "head_sha", reason: "git-unavailable" },
        { field: "ledger.x", reason: "NOT-IN-LEGEND" },
      ],
      [
        { subject: "OBS-SI-012", code: "ROW-ARITY", detail: "欄數與表頭不符" },
        { subject: "OBS-SI-013", code: "ROW-ARITY", detail: "" },
        { subject: "PROP-SI-004", code: "UNMAPPED", detail: "來源：x" },
      ],
      LEGEND,
    );
    const text = Object.fromEntries(lines.map((l) => [l.key, l.text]));
    expect(text["ne:DEFECT-LEDGER-UNAVAILABLE"]).toBe("缺陷帳本讀不到");
    expect(text["ne:SIBLING-LEDGER-UNAVAILABLE"]).toBe("姊妹軌檔讀不到：AutoSDD_External_Blocked_Log.md、AutoSDD_Structural_Debt_Log.md");
    expect(text["ne:SEVERITY-UNAVAILABLE"]).toBe("嚴重度量不到：PROP-SI-004");
    expect(text["ne:git-unavailable"]).toBe("git 取不到版本");
    expect(text["ne:NOT-IN-LEGEND"]).toBe("NOT-IN-LEGEND");
    expect(text["problem:ROW-ARITY"]).toContain("OBS-SI-012（欄數與表頭不符）、OBS-SI-013");
    expect(text["problem:UNMAPPED"]).toBe("帳本值不在對照表：PROP-SI-004（來源：x）");
    const many = Array.from({ length: 8 }, (_, i) => ({ subject: `DEF-999-${String(i).padStart(3, "0")}`, code: "ID-DUP", detail: "" }));
    expect(hintLines([], many, LEGEND)[0].text).toContain("等共 8 項");
    // 沒有圖例（載入前）：退回原碼，不丟例外
    expect(hintLines([{ field: "a", reason: "R" }], [{ subject: "s", code: "C", detail: "" }], undefined).map((l) => l.text)).toEqual(["R", "C：s"]);
  });
});

describe("優先順序表單（B-22）", () => {
  const ok = (rank: string, note = "") => validatePriorityForm({ rank, note });

  it("順位：去前後空白後須為半形數字（至多 4 位）且 1～9999；0、10000、1.5、全形數字、1e3、空白、負號一律不合", () => {
    for (const good of ["1", "9999", " 12 ", "\t7\n", "0012"]) expect(ok(good), good).toEqual({});
    for (const bad of ["", "   ", "0", "0000", "10000", "99999", "00001", "1.5", "１２", "1e3", "-1", "+5", "a", "1 2", "12a"]) expect(ok(bad).rank, JSON.stringify(bad)).toBeTruthy();
    expect(ok("").rank).toContain("必填");
  });

  it("備註：至多 200 個 code point（全形與表情符號各算 1）；不含換行與控制字元；缺省（空字串）通過", () => {
    expect(ok("1", "")).toEqual({});
    expect(ok("1", "字".repeat(200))).toEqual({});
    expect(ok("1", "😀".repeat(200))).toEqual({});
    expect(ok("1", "字".repeat(201)).note).toContain("201");
    expect(ok("1", "😀".repeat(201)).note).toContain("201");
    for (const bad of ["a\nb", "\nab", "ab\n", "a\tb", "a\u007fb", "a\u0000b"]) expect(ok("1", bad).note, JSON.stringify(bad)).toContain("控制字元");
    // 兩欄各自回報、互不掩蓋
    expect(Object.keys(ok("0", "x\ny")).sort()).toEqual(["note", "rank"]);
  });

  it("本文：順位去空白後轉數字、備註原樣（缺省以空字串送出）", () => {
    expect(buildPriorityRequest({ rank: " 12 ", note: "先做" })).toEqual({ rank: 12, note: "先做" });
    expect(buildPriorityRequest({ rank: "0007", note: "" })).toEqual({ rank: 7, note: "" });
    expect(buildPriorityRequest({ rank: "5", note: " 前後空白保留 " }).note).toBe(" 前後空白保留 ");
  });
});

describe("議題中心的四個 API 函式（網址、查詢、id 編碼與錯誤封包）", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");
    resetSessionCache();
    clearSession();
  });

  const okJson = (data: unknown = {}, status = 200) => new Response(JSON.stringify({ code: status, message: "success", data }), { status, headers: { "content-type": "application/json" } });
  /** 取代全域 fetch：回傳每次呼叫的 [網址, init]。 */
  function stubFetch(reply: () => Response = () => okJson()) {
    const fetchMock = vi.fn(async () => reply());
    vi.stubGlobal("fetch", fetchMock);
    return () => fetchMock.mock.calls.map((c) => c as unknown as [string, RequestInit]);
  }

  it("getIssues：undefined 與空字串的選項不進網址（全部分頁不帶 status）；since 為 0 是合法游標、原樣送出；中文別名與逗號逐字編碼；一律 GET、無本文", async () => {
    const calls = stubFetch();
    await api.getIssues();
    await api.getIssues({ status: undefined, source: "", since: undefined, limit: undefined });
    await api.getIssues({ since: 0, limit: 5 });
    await api.getIssues({ status: "待處理" });
    await api.getIssues({ status: "待您決定,已完成", source: "研究提案", since: 12, limit: 100 });
    expect(calls().map(([url]) => url)).toEqual([
      "/api/v1/issues",
      "/api/v1/issues",
      "/api/v1/issues?since=0&limit=5",
      `/api/v1/issues?status=${encodeURIComponent("待處理")}`,
      `/api/v1/issues?status=${encodeURIComponent("待您決定,已完成")}&source=${encodeURIComponent("研究提案")}&since=12&limit=100`,
    ]);
    for (const [, init] of calls()) {
      expect(init.method ?? "GET").toBe("GET");
      expect(init.body).toBeUndefined();
    }
  });

  it("getIssue、putIssuePriority、deleteIssuePriority：id 以 encodeURIComponent 編成單一路徑段；PUT 本文原樣 JSON；DELETE 的 204 回 undefined；signal 原樣傳給 fetch", async () => {
    const calls = stubFetch();
    const ids = ["a/b", "PROP SI 004", "議題", "PROP-SI-004?x=1", "50%"];
    for (const id of ids) {
      await api.getIssue(id);
      await api.putIssuePriority(id, { rank: 1, note: "" });
    }
    const urls = calls().map(([url]) => url);
    expect(urls.filter((_, i) => i % 2 === 0)).toEqual(ids.map((id) => `/api/v1/issues/${encodeURIComponent(id)}`));
    expect(urls.filter((_, i) => i % 2 === 1)).toEqual(ids.map((id) => `/api/v1/issues/${encodeURIComponent(id)}/priority`));
    for (const url of urls) expect(url.includes("#") || url.includes("?"), url).toBe(false);
    expect(JSON.parse(String(calls()[1][1].body))).toEqual({ rank: 1, note: "" });

    const controller = new AbortController();
    await api.getIssue("PROP-SI-004", { signal: controller.signal });
    await api.getIssues({ signal: controller.signal });
    expect(
      calls()
        .slice(-2)
        .every(([, init]) => init.signal === controller.signal),
    ).toBe(true);

    stubFetch(() => new Response(null, { status: 204 }));
    await expect(api.deleteIssuePriority("PROP-SI-004")).resolves.toBeUndefined();
  });

  it("錯誤封包：409 issue_not_rankable 帶 reason 與 details（id、status）；404 si_not_found 帶 details.id；皆丟 ApiError", async () => {
    const failure = (status: number, reason: string, details: Record<string, unknown>) => () =>
      new Response(JSON.stringify({ code: status, message: "x", reason, errors: [], details }), { status, headers: { "content-type": "application/json" } });
    stubFetch(failure(409, "issue_not_rankable", { id: "OBS-SI-001", status: "已完成" }));
    await expect(api.putIssuePriority("OBS-SI-001", { rank: 1 })).rejects.toMatchObject({ status: 409, reason: "issue_not_rankable", details: { id: "OBS-SI-001", status: "已完成" } });
    stubFetch(failure(404, "si_not_found", { id: "DEF-999-404" }));
    await expect(api.getIssue("DEF-999-404")).rejects.toMatchObject({ status: 404, reason: "si_not_found", details: { id: "DEF-999-404" } });
  });
});

describe("錯誤文案", () => {
  const apiError = (status: number, init: { reason?: string; message?: string; details?: Record<string, unknown> } = {}) =>
    new ApiError({ status, message: init.message ?? "錯誤", reason: init.reason, details: init.details });

  it("寫入失敗：409 的 issue_not_rankable 用逐字訊息（不論伺服器 message 寫什麼）；422 列出輸入閘的逐項說明；其餘沿 describeError", () => {
    expect(issueWriteErrorText(apiError(409, { reason: "issue_not_rankable", message: "伺服器另一句話" }))).toBe(ISSUE_REASONS.issue_not_rankable);
    expect(issueWriteErrorText(apiError(409, { reason: "other", message: "衝突" }))).toBe("衝突：other");
    expect(
      issueWriteErrorText(
        apiError(422, {
          reason: "invalid_request",
          details: {
            violations: [
              { field: "rank", message: "rank 必須是 1～9999" },
              { field: "note", message: "note 太長" },
            ],
          },
        }),
      ),
    ).toBe("輸入不合：rank 必須是 1～9999；note 太長");
    expect(issueWriteErrorText(apiError(422, { reason: "invalid_request", message: "請求無效" }))).toBe("請求無效：invalid_request");
    expect(issueWriteErrorText(apiError(422, { details: { violations: "not-an-array" } }))).toBe("錯誤");
    expect(issueWriteErrorText(apiError(403, { reason: "ACCESS_DENIED", message: "沒有權限" }))).toBe("沒有權限：ACCESS_DENIED");
    expect(issueWriteErrorText(new Error("網路斷了"))).toBe("網路斷了");
    expect(issueWriteErrorText("奇怪的值")).toBe("發生未知錯誤");
  });

  it("讀取失敗摘要：503 加 si_unavailable＝資料暫時無法取得；404 加 si_not_found＝查無此議題；其餘沿 describeError", () => {
    expect(issuesErrorSummary(apiError(503, { reason: "si_unavailable" }))).toBe("議題資料暫時無法取得");
    expect(issuesErrorSummary(apiError(404, { reason: "si_not_found" }))).toBe("查無此議題");
    expect(issuesErrorSummary(apiError(503, { reason: "other", message: "別的" }))).toBe("別的：other");
    expect(issuesErrorSummary(new Error("x"))).toBe("x");
  });
});
