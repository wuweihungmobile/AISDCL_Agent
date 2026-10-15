/**
 * 專案 6／目標 5／任務 11／匯入記錄 6 個狀態的中文標籤與顏色——全站單一出處（設計稿 README〈狀態 enum〉；
 * 匯入記錄的六態在設計稿沒有定稿，標籤與顏色由本檔決定，契約 §1.1 只定義狀態值）。
 * 顏色一律引用設計 token（styles/tokens.css），不寫死色碼：
 *   #7A8775＝--color-text-muted　#80B155＝--color-secondary　#498428＝--color-primary
 *   #D35B58＝--color-error　#A6B0A1＝--color-disabled-text　#F5A623＝--color-warning　#E55B3C＝--color-accent
 * （lib/domain/status.test.ts 解析 tokens.css 後逐一核對成設計稿的色碼。）
 */
import type { GoalStatus, ImportStatus, ProjectStatus, TaskStatus } from "@/lib/api/types";

export type StatusMeta = {
  /** 繁體中文標籤 */
  label: string;
  /** CSS 顏色（token 的 var() 引用），可直接用在 style.background／color */
  color: string;
};

const MUTED = "var(--color-text-muted)";
const SECONDARY = "var(--color-secondary)";
const PRIMARY = "var(--color-primary)";
const ERROR = "var(--color-error)";
const DISABLED = "var(--color-disabled-text)";
const WARNING = "var(--color-warning)";
const ACCENT = "var(--color-accent)";

export const PROJECT_STATUS: Record<ProjectStatus, StatusMeta> = {
  DRAFT: { label: "草稿", color: MUTED },
  READY: { label: "就緒", color: SECONDARY },
  EXECUTING: { label: "執行中", color: PRIMARY },
  COMPLETED: { label: "完成", color: PRIMARY },
  FAILED: { label: "失敗", color: ERROR },
  ARCHIVED: { label: "封存", color: DISABLED },
};

export const GOAL_STATUS: Record<GoalStatus, StatusMeta> = {
  PENDING: { label: "待處理", color: DISABLED },
  IN_PROGRESS: { label: "進行中", color: PRIMARY },
  COMPLETED: { label: "完成", color: PRIMARY },
  FAILED: { label: "失敗", color: ERROR },
  SKIPPED: { label: "跳過", color: DISABLED },
};

export const TASK_STATUS: Record<TaskStatus, StatusMeta> = {
  PENDING: { label: "待處理", color: DISABLED },
  QUEUED: { label: "排程中", color: SECONDARY },
  BLOCKED: { label: "阻塞", color: WARNING },
  RUNNING: { label: "執行中", color: PRIMARY },
  VALIDATING: { label: "驗證中", color: SECONDARY },
  COMPLETED: { label: "完成", color: PRIMARY },
  FAILED: { label: "失敗", color: ERROR },
  ESCALATED: { label: "待人工", color: ACCENT },
  PAUSED: { label: "暫停", color: MUTED },
  SKIPPED: { label: "跳過", color: DISABLED },
  CANCELLED: { label: "取消", color: DISABLED },
};

/**
 * 匯入記錄（契約 §1.1 狀態機）：UPLOADED→PARSING→PARSED→REVIEWING→IMPORTED／REJECTED；解析失敗退回 UPLOADED。
 * 顏色語意：灰＝還沒動作；淺綠＝進行中；黃＝等人工審核；主色＝完成；淡灰＝已放棄。
 */
export const IMPORT_STATUS: Record<ImportStatus, StatusMeta> = {
  UPLOADED: { label: "已上傳", color: MUTED },
  PARSING: { label: "解析中", color: SECONDARY },
  PARSED: { label: "已解析", color: WARNING },
  REVIEWING: { label: "審核中", color: WARNING },
  IMPORTED: { label: "已匯入", color: PRIMARY },
  REJECTED: { label: "已放棄", color: DISABLED },
};

const FALLBACK: StatusMeta = { label: "未知", color: MUTED };

/** 後端若新增狀態值，前端不至於崩潰：顯示原值、用灰點。 */
function lookup<K extends string>(table: Record<K, StatusMeta>, status: string): StatusMeta {
  return (table as Record<string, StatusMeta>)[status] ?? { ...FALLBACK, label: status || FALLBACK.label };
}

export const projectStatus = (status: string): StatusMeta => lookup(PROJECT_STATUS, status);
export const goalStatus = (status: string): StatusMeta => lookup(GOAL_STATUS, status);
export const taskStatus = (status: string): StatusMeta => lookup(TASK_STATUS, status);
export const importStatus = (status: string): StatusMeta => lookup(IMPORT_STATUS, status);

/** 專案列表的狀態 tab（設計稿：全部／草稿／就緒／執行中／完成／失敗；封存不列） */
export const PROJECT_STATUS_TABS: ReadonlyArray<{ id: "ALL" | ProjectStatus; label: string }> = [
  { id: "ALL", label: "全部" },
  { id: "DRAFT", label: "草稿" },
  { id: "READY", label: "就緒" },
  { id: "EXECUTING", label: "執行中" },
  { id: "COMPLETED", label: "完成" },
  { id: "FAILED", label: "失敗" },
];

/** 只有 FAILED／ESCALATED 的任務可以手動重試（後端同規則，其餘回 409）。 */
export function isRetryable(status: string): boolean {
  return status === "FAILED" || status === "ESCALATED";
}

/** 狀態點需要「呼吸」動畫的狀態（進行中的工作） */
export function isLive(status: string): boolean {
  return status === "EXECUTING" || status === "IN_PROGRESS" || status === "RUNNING" || status === "PARSING";
}

/**
 * 匯入記錄可以從歷史列表「重新開啟審核」的狀態（契約 §1.1 表）：
 * UPLOADED（尚未解析或解析失敗）、PARSED、REVIEWING 仍有下一步可做；
 * PARSING 進行中不開、IMPORTED／REJECTED 是終態。
 */
export function isImportReopenable(status: string): boolean {
  return status === "UPLOADED" || status === "PARSED" || status === "REVIEWING";
}
