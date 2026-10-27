/**
 * 每頁說明的資料型別（純文字；TCS-PageHelp-20261027 C1；PRD §8.1 逐字，加上兩個字面值聯集 `HelpId`、`StateTableId`）。
 * 不 import 任何元件、hooks 或其他模組：說明內容全在 lib/help/**，經 PR 修改；名稱解析（需要引用既有常數表）放在 components/domain/help/stateSources.ts。
 */

/** 說明項 id（PRD §4 的十六頁）；姊妹案日後加成員（PRD D-12）。 */
export type HelpId =
  | "dashboard"
  | "projects"
  | "project-detail"
  | "goals"
  | "goal-detail"
  | "tasks"
  | "task-detail"
  | "project-form"
  | "goal-form"
  | "task-form"
  | "execute"
  | "monitor"
  | "import"
  | "settings"
  | "self-improving"
  | "issues";

/** 狀態表 id（PRD §8.2 的十八張）。 */
export type StateTableId =
  | "projectStatus"
  | "goalStatus"
  | "taskStatus"
  | "stepStatus"
  | "importStatus"
  | "runStatus"
  | "runTransition"
  | "reviewKind"
  | "reviewDecision"
  | "alertSeverity"
  | "alertRule"
  | "gateName"
  | "sddPhase"
  | "sddFsmState"
  | "serviceState"
  | "obsClass"
  | "propClass"
  | "propState";

/** 欄位資料的來源，恰六類（AC-PH-05-4）。 */
export type FieldSource = "您填寫或選擇" | "系統自動產生" | "執行引擎回報" | "自我進化帳本" | "系統參數" | "其他頁面帶入";

/** 一個欄位的白話釋義；`sourceNote` 選填、不超過 30 個字。 */
export type HelpField = { name: string; meaning: string; source: FieldSource; sourceNote?: string };

/** 一個狀態的白話釋義。刻意沒有 label／name：狀態名稱只取自既有常數表，說明不自持。 */
export type StateRow = { meaning: string; next: string };

/** 一頁引用哪張狀態表；`name` 只決定「狀態」欄印什麼（預設 "label"＝既有常數表的中文標籤，"raw"＝畫面上的原值），不改釋義。 */
export type HelpStateGroup = { table: StateTableId; name?: "label" | "raw" } | { legend: "issues" };

/** 一頁的說明項。`title` 是固定頁名（不含專案名等動態名稱）；`sourceFiles` 是欄位名出處鎖要掃的檔（相對 AgentConsole/frontend/）。 */
export type PageHelp = {
  id: HelpId;
  title: string;
  purpose: readonly string[];
  steps: readonly string[];
  fields: readonly HelpField[];
  states: readonly HelpStateGroup[];
  sourceFiles: readonly string[];
};

/** 全站共通段（每個對話框底部、預設收合）：公告列、搜尋、通知、連線點等每頁都有的東西。 */
export type CommonHelp = Pick<PageHelp, "fields" | "states" | "sourceFiles">;
