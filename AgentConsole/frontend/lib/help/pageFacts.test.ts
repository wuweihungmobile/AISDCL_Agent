import { describe, expect, it } from "vitest";

import { splitSentences } from "./lint";
import { factProblems, pageCorpus, SORTABLE_HELP_PAGES, SORTABLE_TABLE_PAGES, stepProblems, type PageFact } from "./readability";
import { HELP_PAGES } from "./registry";
import type { HelpId, PageHelp } from "./types";

/**
 * 各頁說明的內容事實鎖（TCS-ConsoleUxSortHelp-20261108 AC-963-7；§3.4；R-UX-H9；載具 H）。
 * 「事實」以關鍵詞組判定：同一事實的每個詞組都要在該頁全文出現（kind=words）；標「同句」者要在同一句內（kind=sentence）；
 * 步驟次序用 kind=order（只看 steps，各自第一次出現的位置要遞增）。詞組以陣列表示「任選其一」。
 * 判定指令：npx vitest run lib/help/pageFacts.test.ts -t "<AT 底線形>"。
 */

const page = (id: HelpId): PageHelp => {
  const found = HELP_PAGES[id];
  if (found === undefined) throw new Error(`說明頁 ${id} 不存在`);
  return found;
};

/** §3.4 專案管理 P1～P6。 */
const PROJECT_FACTS: readonly PageFact[] = [
  { id: "P1", label: "草案審批前不能執行", kind: "words", words: ["未審批", "審批", ["不能執行", "無法執行", "才能執行"]] },
  { id: "P2", label: "唯讀角色不能新建", kind: "sentence", words: ["唯讀", "新建專案", "不能"] },
  { id: "P3", label: "已刪除專案保留期限內可復原", kind: "words", words: ["已刪除", "復原", "保留"] },
  { id: "P4a", label: "排序可選建立順序", kind: "sentence", words: ["排序", "建立順序"] },
  { id: "P4b", label: "排序可選名稱", kind: "words", words: ["名稱"] },
  { id: "P5", label: "匯入入口", kind: "words", words: ["匯入"] },
  { id: "P6", label: "完整走一遍的次序", kind: "order", words: [["新建專案", "匯入"], "目標", "任務", ["審批", "簽核"], "執行", "監控"] },
];

/** §3.4 研發工作流清單 R1～R6。 */
const RESEARCH_FACTS: readonly PageFact[] = [
  { id: "R1", label: "命題必填", kind: "sentence", words: ["研究命題", "必填"] },
  { id: "R2", label: "五步名稱", kind: "words", words: ["研究", "規格工作室", "分流", "拆解與執行", "交付"] },
  { id: "R3", label: "封存可復原", kind: "words", words: ["封存", "復原"] },
  { id: "R4", label: "初始化失敗要重試", kind: "words", words: ["初始化失敗", "重試初始化"] },
  { id: "R5", label: "排序", kind: "words", words: ["排序", "編號"] },
  { id: "R6", label: "唯讀不能新建", kind: "sentence", words: ["唯讀", "不能"] },
];

/** §3.4 研發工作流工作區 W1～W5。 */
const WORKSPACE_FACTS: readonly PageFact[] = [
  { id: "W1", label: "規格由 ADMIN 核准後凍結", kind: "sentence", words: ["ADMIN", "核准", "凍結"] },
  { id: "W2", label: "分流只有 ADMIN 能確認", kind: "sentence", words: ["分流", "ADMIN", "確認"] },
  { id: "W3", label: "五步依序出現", kind: "order", words: ["研究", "規格工作室", "分流", "拆解與執行", "交付"] },
  { id: "W4", label: "可退回修改", kind: "words", words: ["退回"] },
  {
    id: "W5",
    label: "卡住時的去處",
    kind: "sentence",
    words: [
      ["卡住", "出錯", "找不到"],
      ["對帳", "本頁說明", "重試"],
    ],
  },
];

describe("AT_963_7 各頁說明的內容事實（§3.4）", () => {
  it("AT_963_7_1 專案管理頁命中 P1～P6", () => {
    expect(factProblems(page("projects"), PROJECT_FACTS)).toEqual([]);
  });

  it("AT_963_7_2 研發工作流清單頁命中 R1～R6，且不含「目前開放前兩步」", () => {
    expect(factProblems(page("research"), RESEARCH_FACTS)).toEqual([]);
    expect(pageCorpus(page("research"))).not.toContain("目前開放前兩步");
  });

  it("AT_963_7_3 研發工作流工作區頁命中 W1～W5", () => {
    expect(factProblems(page("research-workspace"), WORKSPACE_FACTS)).toEqual([]);
  });

  it("AT_963_7_4 有可排序表的頁：表頁有一步同句含「欄位標題」與「排序」；控制列頁有一步含「排序」；議題頁的「排序」只指表頭排序", () => {
    expect([...SORTABLE_HELP_PAGES].sort()).toEqual(["import", "issues", "projects", "research", "research-workspace", "self-improving", "sysadmin-backup"]);
    const problems: string[] = [];
    for (const id of SORTABLE_HELP_PAGES) {
      const steps = page(id as HelpId).steps;
      if (SORTABLE_TABLE_PAGES.includes(id)) {
        if (!steps.some((step) => step.includes("欄位標題") && step.includes("排序"))) problems.push(`${id}：steps 沒有同一句含「欄位標題」與「排序」`);
      } else if (!steps.some((step) => step.includes("排序"))) problems.push(`${id}：steps 沒有含「排序」的步驟`);
    }
    expect(problems).toEqual([]);
    // 議題頁（QA F15，主控裁決 E-4）：至少一句同句含「優先順序」「排序」（優先順序鈕，引畫面字樣），且至少一句同句含「欄位標題」「排序」（表頭句）
    const issuesSentences = splitSentences(pageCorpus(page("issues")));
    expect(issuesSentences.some((s) => s.includes("優先順序") && s.includes("排序"))).toBe(true);
    expect(issuesSentences.some((s) => s.includes("欄位標題") && s.includes("排序"))).toBe(true);
  });

  it("AT_963_7_5 入口頁 execute-entry、monitor-entry 的 steps 各 5～10 步，每步通過步驟規則", () => {
    for (const id of ["execute-entry", "monitor-entry"] as const) {
      const steps = page(id).steps;
      expect(steps.length, id).toBeGreaterThanOrEqual(5);
      expect(steps.length, id).toBeLessThanOrEqual(10);
      expect(
        steps.flatMap((s) => stepProblems(s)),
        id,
      ).toEqual([]);
    }
  });

  it("AT_963_7_E_1 負控：缺 P1 詞組、缺 W2、steps 次序顛倒的合成頁各回非空；完整合成頁回空", () => {
    const base: PageHelp = {
      id: "projects",
      title: "合成頁",
      purpose: ["甲。", "乙。"],
      steps: [],
      fields: [],
      states: [],
      sourceFiles: [],
    };
    const full: PageHelp = {
      ...base,
      purpose: ["草案未審批時，審批後才能執行。", "唯讀的角色不能新建專案。"],
      steps: ["按「新建專案」。", "新增目標。", "新增任務。", "按審批。", "按執行。", "看監控。"],
    };
    const p1: readonly PageFact[] = [PROJECT_FACTS[0]];
    expect(factProblems(full, p1)).toEqual([]);
    expect(factProblems({ ...full, purpose: ["草案未審批時，審批後才能用。", "乙。"] }, p1).join()).toContain("事實");
    // 缺 W2：沒有 ADMIN 與分流與確認同句
    const w2 = WORKSPACE_FACTS[1];
    const wsFull: PageHelp = { ...base, id: "research-workspace", purpose: ["分流只有 ADMIN 能確認。", "乙。"], steps: ["第三步「分流」：僅 ADMIN 可確認。"] };
    expect(factProblems(wsFull, [w2])).toEqual([]);
    expect(factProblems({ ...wsFull, purpose: ["分流要確認。", "乙。"], steps: ["第三步「分流」。"] }, [w2]).join()).toContain("事實");
    // 次序顛倒
    const order = PROJECT_FACTS[PROJECT_FACTS.length - 1];
    expect(factProblems(full, [order])).toEqual([]);
    expect(factProblems({ ...full, steps: ["按審批。", "按執行。", "看監控。", "新增任務。", "新增目標。", "按「新建專案」。"] }, [order]).join()).toContain("事實");
    // 同句要求：詞分散在兩句不算命中
    const sentenceFact = PROJECT_FACTS[1];
    expect(factProblems({ ...full, purpose: ["唯讀的角色不能新建專案。", "乙。"] }, [sentenceFact])).toEqual([]);
    expect(factProblems({ ...full, purpose: ["唯讀的角色只能看。", "新建專案按右上角。不能遺漏。"] }, [sentenceFact]).join()).toContain("事實");
  });
});
