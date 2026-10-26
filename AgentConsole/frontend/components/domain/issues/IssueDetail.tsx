"use client";

/**
 * 議題詳情側面板（TCS-IssueCenter-20261027 R-IC-65；PRD §7）：同頁、不換路由。由上到下：頭部（編號、來源、狀態與結果、嚴重度、順位、最後更新）→ 下一步 →
 * 原列（`raw`，中文標籤；**唯一可見英文原值的地方**）→ 事件時間線（`timeline`）→ 關聯（`links`，可點）。
 *
 * 設計要點（為什麼這樣做）：
 *  - 資料是單筆端點（含 `raw`、`timeline`、`priority`），**沒有 `legend`**：圖例由清單那一頁傳進來。已結案議題（`result` 有值）的日期是「最後已知動靜」而非結案日，
 *    註記取自 `legend.updatedAtNote`（不寫死；圖例沒帶就不顯示）。日期元素本身只含 `updatedAt`，註記在它旁邊的獨立元素。
 *  - 關聯各查一次單筆（`useIssueLookups`）：查無（404）＝顯示「不在議題中心（可能已歸檔）」且不可點；查得到＝按鈕，點了換成該議題的詳情；
 *    確認中不可點（避免點到查無的）；其他失敗（例：資料面暫時不可用）無法證明查無，所以仍給按鈕，點開後由詳情自己顯示原因。
 *  - 純文字：帳本與備註文字一律以 React 文字節點渲染，不經 HTML 或 Markdown。
 *  - 鍵盤：開啟時焦點移到面板、Esc 關閉（焦點還給開它的元素由呼叫端處理）。
 */
import { X } from "lucide-react";
import { useEffect, useRef, type KeyboardEvent } from "react";

import { IconButton } from "@/components/ui/icon-button";
import { ApiError } from "@/lib/api/client";
import { useIssue, useIssueLookups } from "@/lib/api/queries";
import type { Issue, IssueLegend } from "@/lib/api/types";
import { effectivePriority, issuesErrorSummary, orDash, statusText } from "@/lib/domain/issues";
import { siErrorParts } from "@/lib/domain/si";

function Section({ title, testId, children }: { title: string; testId?: string; children: React.ReactNode }) {
  return (
    <section aria-label={title} data-testid={testId} className="border-t border-wg-line pt-3">
      <h3 className="mb-1.5 text-sm font-semibold">{title}</h3>
      {children}
    </section>
  );
}

function Links({ ids, onOpenIssue }: { ids: ReadonlyArray<string>; onOpenIssue: (id: string) => void }) {
  const lookups = useIssueLookups(ids);
  if (ids.length === 0) return <p className="text-sm text-wg-muted">沒有關聯的議題</p>;
  return (
    <ul className="flex flex-col gap-1 text-sm">
      {ids.map((id, i) => {
        const lookup = lookups[i];
        const missing = lookup?.error instanceof ApiError && lookup.error.status === 404;
        return (
          <li key={id} data-testid={`issue-link-${id}`} className="flex flex-wrap items-center gap-x-2">
            {missing || lookup?.isPending ? (
              <span className="font-mono text-xs">{id}</span>
            ) : (
              <button type="button" onClick={() => onOpenIssue(id)} className="cursor-pointer font-mono text-xs text-wg-primary-strong underline underline-offset-2">
                {id}
              </button>
            )}
            {missing ? <span className="text-wg-muted">不在議題中心（可能已歸檔）</span> : null}
          </li>
        );
      })}
    </ul>
  );
}

function Body({ issue, legend, onOpenIssue }: { issue: Issue; legend: IssueLegend | undefined; onOpenIssue: (id: string) => void }) {
  const priority = effectivePriority(issue);
  return (
    <div className="flex flex-col gap-3">
      <header className="flex flex-col gap-1.5">
        <h2 className="font-mono text-base font-semibold break-all">{issue.id}</h2>
        <p data-testid="issue-detail-title" className="text-sm break-words">
          {issue.title}
        </p>
        <dl className="grid grid-cols-[5.5rem_1fr] gap-x-3 gap-y-1 text-sm">
          <dt className="text-wg-muted">來源</dt>
          <dd>{orDash(issue.source)}</dd>
          <dt className="text-wg-muted">狀態</dt>
          <dd>{statusText(issue)}</dd>
          <dt className="text-wg-muted">嚴重度</dt>
          <dd>{orDash(issue.severity)}</dd>
          <dt className="text-wg-muted">順位</dt>
          <dd data-testid="issue-detail-priority">{priority === null ? "—" : `${priority}${issue.priorityNote ? `：${issue.priorityNote}` : ""}`}</dd>
          <dt className="text-wg-muted">最後更新</dt>
          <dd>
            <span data-testid="issue-detail-date" className="tabular-nums">
              {orDash(issue.updatedAt)}
            </span>
            {issue.result !== null && legend?.updatedAtNote ? (
              <span data-testid="issue-detail-date-note" className="mt-0.5 block text-xs text-wg-muted">
                {legend.updatedAtNote}
              </span>
            ) : null}
          </dd>
        </dl>
      </header>

      <Section title="下一步">
        <p className="text-sm break-words">{issue.nextStep}</p>
      </Section>

      <Section title="原列" testId="issue-detail-raw">
        {issue.raw && issue.raw.length > 0 ? (
          <dl className="grid grid-cols-[6rem_1fr] gap-x-3 gap-y-1 text-sm">
            {issue.raw.map((field, i) => (
              <div key={`${field.label}-${i}`} className="contents">
                <dt className="text-wg-muted">{field.label}</dt>
                <dd className="break-all whitespace-pre-wrap">{field.value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="text-sm text-wg-muted">沒有原列資料</p>
        )}
      </Section>

      <Section title="事件時間線" testId="issue-detail-timeline">
        {issue.timeline && issue.timeline.length > 0 ? (
          <ol className="flex flex-col gap-1 text-sm">
            {issue.timeline.map((entry) => (
              <li key={entry.seq} className="break-words">
                <span className="tabular-nums text-wg-muted">{`#${entry.seq}　${entry.t}`}</span>
                {`　${entry.by}　${entry.action}`}
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-wg-muted">沒有事件紀錄</p>
        )}
      </Section>

      <Section title="關聯" testId="issue-detail-links">
        <Links ids={issue.links} onOpenIssue={onOpenIssue} />
      </Section>
    </div>
  );
}

export function IssueDetail({ id, legend, onClose, onOpenIssue }: { id: string; legend: IssueLegend | undefined; onClose: () => void; onOpenIssue: (id: string) => void }) {
  const q = useIssue(id);
  const root = useRef<HTMLElement>(null);
  const issue = q.data?.items[0];

  // 開啟（或換到另一個議題）時把焦點移進面板：鍵盤使用者按下編號後不必再從頁首 Tab 過來
  useEffect(() => {
    root.current?.focus();
  }, [id]);

  function onKeyDown(e: KeyboardEvent<HTMLElement>) {
    if (e.key === "Escape") {
      e.stopPropagation();
      onClose();
    }
  }

  const { reason, cause, detail } = siErrorParts(q.error);
  return (
    <aside
      ref={root}
      tabIndex={-1}
      aria-label={`議題 ${id} 詳情`}
      data-testid="issue-detail"
      onKeyDown={onKeyDown}
      className="flex min-w-0 flex-col gap-3 rounded-lg border border-wg-line bg-wg-surface px-5 py-4"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-wg-muted">議題詳情</p>
        <IconButton icon={X} label="關閉詳情" size={32} iconSize={16} onClick={onClose} data-testid="issue-detail-close" />
      </div>

      {q.isError ? (
        <div role="alert" data-testid="issue-detail-error" className="flex flex-col gap-1.5 text-sm">
          <p className="font-medium">{issuesErrorSummary(q.error)}</p>
          {reason ? <p className="text-wg-muted">{`reason：${reason}`}</p> : null}
          {cause ? <p className="text-wg-muted">{`cause：${cause}`}</p> : null}
          {detail ? <p className="font-mono text-xs break-all whitespace-pre-wrap text-wg-muted">{detail}</p> : null}
        </div>
      ) : issue ? (
        <Body issue={issue} legend={legend} onOpenIssue={onOpenIssue} />
      ) : (
        <p role="status" data-testid="issue-detail-loading" className="text-sm text-wg-muted">
          {q.isPending ? "議題詳情載入中…" : "查無此議題"}
        </p>
      )}
    </aside>
  );
}
