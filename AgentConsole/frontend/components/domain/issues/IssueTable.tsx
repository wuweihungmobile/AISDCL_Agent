"use client";

/**
 * 議題清單表（TCS-IssueCenter-20261027 R-IC-65、R-IC-66、R-IC-70、R-IC-71；PRD §7）：固定八欄——編號、來源、標題、嚴重度、狀態（已結案者併列結果）、
 * 優先順序（只對可排的列顯示）、最後更新、下一步（有動作的列，按鈕放在此欄尾）。列序由呼叫端依分頁規則排好（`displayOrder`），這裡不排序、不篩選。
 *
 * 設計要點（為什麼這樣做）：
 *  - 編號是按鈕（鍵盤可開詳情）；整列不是按鈕，避免巢狀互動元素。置頂標記（`data-testid="issue-top-pinned"`、`aria-label="置頂"`）每個置頂列恰一個。
 *  - 寫入入口只對 ADMIN 渲染：可排的列有「排序」鈕；提案列「決定」、觀察列「關閉並裁決」（依資料自帶的 `action`，前端不自己判斷是哪一類）。
 *    非 ADMIN 看得到順位與備註、沒有任何編輯控制項；有動作的列在下一步欄顯示「需要 ADMIN 角色才能操作」且沒有按鈕。
 *    動作列的狀態只跟帳本走：簽章成功只代表稽核檔已落地，列不樂觀移動（入帳後重新載入才換狀態）。
 *  - 順位欄只看「可排」：不可排的列即使帶著遺留順位也空白（`effectivePriority`）。備註是使用者輸入，純文字顯示。
 *  - 純文字：帳本字串（標題、下一步、備註）一律以 React 文字節點渲染。
 */
import { Pin } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Issue } from "@/lib/api/types";
import { SortableHeader } from "@/components/domain/common/SortableHeader";
import { EMPTY_VALUE, effectivePriority, isPinned, orDash, sortIssues, statusText, type IssueTabId } from "@/lib/domain/issues";
import { sortRows, type SortColumn, type SortState } from "@/lib/domain/sorting";
import { cn } from "@/lib/utils";

/** 表頭排序欄位（TCS-ConsoleUxSortHelp §2.1 T2；欄位定義放元件內，`lib/domain/issues.ts` 的兩條顯示序一字不動）。「下一步」是動作欄，不可排。 */
export const ISSUE_SORT_COLUMNS: ReadonlyArray<SortColumn<Issue>> = [
  { key: "id", kind: "id", get: (i) => i.id },
  { key: "source", kind: "text", get: (i) => i.source },
  { key: "title", kind: "text", get: (i) => i.title },
  { key: "severity", kind: "rank", get: (i) => (i.severityRank === null || i.severityRank === undefined ? null : String(i.severityRank)), rank: (v) => Number(v) },
  { key: "status", kind: "text", get: (i) => statusText(i) },
  { key: "priority", kind: "number", get: (i) => effectivePriority(i) },
  { key: "updatedAt", kind: "iso", get: (i) => i.updatedAt },
];

/**
 * 使用者排序後的列序（D-UX-16）：「全部」分頁的置頂列（待您決定狀態）仍留頂端、其內依佇列序，排序只作用於其下清單；
 * 其餘分頁整張依欄排序。`sort` 為 null＝呼叫端自己的預設序（displayOrder），不經這裡。
 */
export function applyIssueSort(items: ReadonlyArray<Issue>, tab: IssueTabId, pinned: ReadonlySet<string>, sort: NonNullable<SortState>): Issue[] {
  if (tab === "all") {
    const top = sortIssues(
      items.filter((i) => pinned.has(i.status)),
      "decide",
    );
    return [
      ...top,
      ...sortRows(
        items.filter((i) => !pinned.has(i.status)),
        ISSUE_SORT_COLUMNS,
        sort,
      ),
    ];
  }
  return sortRows(items, ISSUE_SORT_COLUMNS, sort);
}

const HEADERS: ReadonlyArray<{ key: string; label: string }> = [
  { key: "id", label: "編號" },
  { key: "source", label: "來源" },
  { key: "title", label: "標題" },
  { key: "severity", label: "嚴重度" },
  { key: "status", label: "狀態" },
  { key: "priority", label: "優先順序" },
  { key: "updatedAt", label: "最後更新" },
];

export type IssueTableProps = {
  /** 已依分頁規則排好序的列 */
  items: ReadonlyArray<Issue>;
  tab: IssueTabId;
  /** 全部分頁置頂的狀態名（取自圖例） */
  pinned: ReadonlySet<string>;
  isAdmin: boolean;
  /** 使用者排序狀態；null＝預設序（四分頁的預設序都不是任一欄，起始 aria-sort 全 none） */
  sort: SortState;
  onSort: (key: string) => void;
  onResetSort: () => void;
  selectedId: string | null;
  /** 正在取提案快照的議題編號（該列的「決定」鈕標 aria-busy 並改字；連點由呼叫端擋住，只取一次） */
  snapshotId: string | null;
  onOpen: (id: string, trigger: HTMLElement) => void;
  onRank: (issue: Issue) => void;
  onDecide: (issue: Issue) => void;
  onCloseObservation: (issue: Issue) => void;
};

function PriorityCell({ issue, isAdmin, onRank }: { issue: Issue; isAdmin: boolean; onRank: (issue: Issue) => void }) {
  if (!issue.rankable) return null;
  const priority = effectivePriority(issue);
  return (
    <div className="flex flex-col items-start gap-1">
      {priority === null ? (
        <span className="text-wg-muted">{EMPTY_VALUE}</span>
      ) : (
        <>
          <span data-testid={`issue-priority-${issue.id}`} className="font-medium tabular-nums">
            {priority}
          </span>
          {issue.priorityNote ? (
            <span data-testid={`issue-priority-note-${issue.id}`} className="text-xs break-words text-wg-muted">
              {issue.priorityNote}
            </span>
          ) : null}
        </>
      )}
      {isAdmin ? (
        <Button variant="ghost" size="sm" aria-label={`排序 ${issue.id}`} data-testid={`issue-priority-open-${issue.id}`} onClick={() => onRank(issue)}>
          排序
        </Button>
      ) : null}
    </div>
  );
}

function ActionCell({ issue, isAdmin, snapshotId, onDecide, onCloseObservation }: Pick<IssueTableProps, "snapshotId" | "onDecide" | "onCloseObservation"> & { issue: Issue; isAdmin: boolean }) {
  if (issue.action === null) return null;
  if (!isAdmin) {
    return (
      <span data-testid={`issue-admin-only-${issue.id}`} className="mt-1.5 block text-xs text-wg-muted">
        需要 ADMIN 角色才能操作
      </span>
    );
  }
  return (
    <div className="mt-1.5">
      {issue.action === "decide-proposal" ? (
        // 取快照期間**不停用**按鈕（停用會讓鍵盤焦點掉出去，對話框關閉後就沒有地方可還）：連點由呼叫端的 snapshotId 擋住，這裡只標 aria-busy 並改字
        <Button variant="ghost" size="sm" aria-label={`決定 ${issue.id}`} aria-busy={snapshotId === issue.id || undefined} data-testid={`issue-decide-${issue.id}`} onClick={() => onDecide(issue)}>
          {snapshotId === issue.id ? "取得提案中…" : "決定"}
        </Button>
      ) : null}
      {issue.action === "close-observation" ? (
        <Button variant="ghost" size="sm" aria-label={`關閉並裁決 ${issue.id}`} data-testid={`issue-close-${issue.id}`} onClick={() => onCloseObservation(issue)}>
          關閉並裁決
        </Button>
      ) : null}
    </div>
  );
}

export function IssueTable({ items, tab, pinned, isAdmin, sort, onSort, onResetSort, selectedId, snapshotId, onOpen, onRank, onDecide, onCloseObservation }: IssueTableProps) {
  return (
    <div className="relative overflow-x-auto">
      {sort ? (
        <div className="mb-2">
          <Button variant="ghost" size="sm" data-testid="sort-reset" onClick={onResetSort}>
            還原預設排序
          </Button>
        </div>
      ) : null}
      <table data-testid="issues-table" className="w-full min-w-[64rem] border-collapse text-left text-sm">
        <caption className="sr-only">議題清單</caption>
        <thead>
          <tr className="border-b border-wg-line text-xs text-wg-muted">
            {HEADERS.map((h) => (
              <SortableHeader key={h.key} column={h.key} label={h.label} state={sort} onSort={onSort} />
            ))}
            <th scope="col" className="py-2 pr-3">
              下一步
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((issue) => (
            <tr
              key={issue.id}
              data-testid={`issue-row-${issue.id}`}
              aria-current={issue.id === selectedId ? "true" : undefined}
              className={cn("border-b border-wg-line align-top", issue.id === selectedId && "bg-wg-base")}
            >
              <td className="py-2 pr-3 whitespace-nowrap">
                <span className="inline-flex items-center gap-1.5">
                  {isPinned(issue, tab, pinned) ? <Pin size={14} role="img" aria-label="置頂" data-testid="issue-top-pinned" className="shrink-0 text-wg-accent" /> : null}
                  <button
                    type="button"
                    data-testid={`issue-open-${issue.id}`}
                    onClick={(e) => onOpen(issue.id, e.currentTarget)}
                    className="cursor-pointer font-mono text-xs text-wg-primary-strong underline underline-offset-2"
                  >
                    {issue.id}
                  </button>
                </span>
              </td>
              <td className="py-2 pr-3">{orDash(issue.source)}</td>
              <td data-testid={`issue-title-${issue.id}`} className="max-w-[22rem] py-2 pr-3 break-words">
                {issue.title}
              </td>
              <td className="py-2 pr-3 whitespace-nowrap">{orDash(issue.severity)}</td>
              <td className="py-2 pr-3 whitespace-nowrap">{statusText(issue)}</td>
              <td className="py-2 pr-3">
                <PriorityCell issue={issue} isAdmin={isAdmin} onRank={onRank} />
              </td>
              <td className="py-2 pr-3 whitespace-nowrap tabular-nums">{orDash(issue.updatedAt)}</td>
              <td className="max-w-[24rem] py-2">
                <span data-testid={`issue-next-${issue.id}`} className="break-words">
                  {issue.nextStep}
                </span>
                <ActionCell issue={issue} isAdmin={isAdmin} snapshotId={snapshotId} onDecide={onDecide} onCloseObservation={onCloseObservation} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
