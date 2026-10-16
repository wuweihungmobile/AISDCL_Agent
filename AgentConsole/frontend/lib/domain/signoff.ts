/**
 * 待簽核草案（Dashboard「待人工審批」卡；契約 §1.8.1、§4.5 G-10；v1.4 D-18）的顯示規則：
 * 種類中文標籤、副標、連結落點，以及對應 SignoffDialog 的目標。純函式、不依賴 React。
 */
import type { PendingSignoffItem, PendingSignoffKind } from "@/lib/api/types";

/** 四種草案的中文標籤（與 SignoffDialog 的對話框標題「審批 signoff：○○」一致）。 */
export const PENDING_KIND_LABEL: Record<PendingSignoffKind, string> = {
  PROJECT: "專案",
  GOAL: "目標",
  TASK: "任務",
  IMPORT: "匯入草案",
};

/** 後端日後若新增種類，退回原值、不崩潰（同 lib/domain/status.ts 的處理）。 */
export function pendingKindLabel(kind: string): string {
  return (PENDING_KIND_LABEL as Record<string, string>)[kind] ?? kind;
}

/**
 * 副標（契約 G-10，由前端組字）：專案草案／目標草案・{projectName}／任務草案・{projectName}／匯入草案。
 * 目標與任務帶所屬專案名，讓「同名的目標出現在不同專案」分得開；匯入草案還沒有專案。
 */
export function pendingMeta(item: Pick<PendingSignoffItem, "kind" | "projectName">): string {
  if (item.kind === "IMPORT") return "匯入草案";
  if (item.kind === "PROJECT") return "專案草案";
  const base = `${pendingKindLabel(item.kind)}草案`;
  return item.projectName ? `${base}・${item.projectName}` : base;
}

/**
 * 連結（契約 G-10）：PROJECT→/projects/{id}、GOAL→/projects/{projectId}/goals/{id}、
 * TASK→/projects/{projectId}/goals/{parentId}/tasks/{id}（parentId＝目標 id）、IMPORT→/import（匯入頁目前沒有以 id 深連結某筆記錄的路由）。
 * 欄位缺漏（契約保證 GOAL／TASK 有 projectId、TASK 有 parentId；防禦性）退回專案列表，不產生 `/projects/null/…`。
 */
export function pendingHref(item: Pick<PendingSignoffItem, "kind" | "id" | "projectId" | "parentId">): string {
  switch (item.kind) {
    case "PROJECT":
      return `/projects/${item.id}`;
    case "GOAL":
      return item.projectId ? `/projects/${item.projectId}/goals/${item.id}` : "/projects";
    case "TASK":
      return item.projectId && item.parentId ? `/projects/${item.projectId}/goals/${item.parentId}/tasks/${item.id}` : "/projects";
    case "IMPORT":
      return "/import";
    default:
      return "/projects";
  }
}

export type PendingSignoffTarget = { kind: "project" | "goal" | "task" | "import"; id: string; name: string };

/** 「審批」鈕開 SignoffDialog 的目標（對話框已支援 project／goal／task／import 四種）。 */
export function pendingSignoffTarget(item: Pick<PendingSignoffItem, "kind" | "id" | "title">): PendingSignoffTarget {
  return { kind: item.kind.toLowerCase() as PendingSignoffTarget["kind"], id: item.id, name: item.title };
}

/** 清單被 limit 截斷時卡片底部的說明（契約 G-10）：counts.total 大於清單長度才有。 */
export function pendingTruncatedNote(shown: number, total: number): string | null {
  return total > shown ? `僅列出最早的 ${shown} 筆，共 ${total} 筆` : null;
}
