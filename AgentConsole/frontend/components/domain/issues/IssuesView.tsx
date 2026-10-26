"use client";

/**
 * 議題中心頁（TCS-IssueCenter-20261027 R-IC-62～71、R-IC-74；PRD §7）：把 SelfImproving 的觀察、缺陷與提案聚合成「議題」，用中文列出「該先處理什麼」。
 * 頁面資料＝根層 `issues` 匯出，經 Bridge 子行程與 console-api 原樣（只改欄名、每筆加 Console 自有的優先順序）轉到這裡；Console 是顯示面，不是資料來源，
 * 也不寫帳本——唯一自有的寫入是 ADMIN 設定的優先順序，以及兩個既有的自我進化對話框（簽成稽核檔、待主機入帳）。
 *
 * 版面（上到下）：標題列（「狀態說明」「重新整理」）→ 摘要列（三個可點數字，取 `summary.byTab`，量不到顯示「—」）→ 四個分頁（預設待處理；沿用 `PillTabs`）→
 * 篩選列（來源下拉、關鍵字；已完成分頁多結果快篩、全部分頁多狀態 pill）→ 提示條（`ne`、`problems` 非空時）→ 清單。詳情是同頁的側面板，不換路由。
 *
 * 設計要點（為什麼這樣做）：
 *  - **前端不持有狀態詞清單**：分頁只認三個分頁名並原樣當 `status` 傳給 API（由根層展開成員）；狀態 pill、結果快篩、來源下拉、說明與提示條的文字一律取自回應的 `legend`。
 *  - **量不到絕不顯示成 0 件**：整頁讀取失敗（Bridge 503、504 等）＝整片顯示原因（reason、cause、detail 逐字）與「重試」，摘要列三格顯示「—」，不渲染空表也不渲染過期資料；
 *    某本帳讀不到＝依賴它的摘要格（`byTab` 為 null）顯示「—」，提示條明說，清單照常。
 *  - **逐頁自動載完**（沿 `SI_AUTO_LOAD_MAX_PAGES`）：篩選只作用於已載入的項目，不載完會把「沒有符合」讀成「帳本沒有」；載到上限仍有未載入者明說「結果不完整」並顯示已載入件數，人仍可按「載入更多」。
 *  - 不留快取：每次進頁與「重新整理」都重取（SI 查詢選項：不重試、gcTime 為 0）；切分頁即卸載舊分頁的資料。
 *  - 寫入入口只對 ADMIN 渲染；三個寫入對話框掛在這一層（列重繪或換分頁不會讓開著的對話框消失）。決定按鈕先取點擊當下的提案快照再開對話框（對話框綁快照的卡面 digest，
 *    不取清單項）；簽章成功只代表稽核檔已落地，列不樂觀移動，入帳後重新載入才換狀態。
 *  - 純文字：帳本與備註文字一律以 React 文字節點渲染，不經 HTML 或 Markdown。
 */
import { useQueryClient } from "@tanstack/react-query";
import { Info, ListChecks, RefreshCw } from "lucide-react";
import { useMemo, useRef, useState, type ReactNode } from "react";

import { SiDecideDialog, type DecideTarget } from "@/components/domain/si/SiDecideDialog";
import { SiObsCloseDialog, type CloseTarget } from "@/components/domain/si/SiObsCloseDialog";
import { FilterSelect, useAutoLoadRemaining } from "@/components/domain/si/siParts";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { pillPanelId, pillTabId, PillTabs } from "@/components/ui/pill-tabs";
import { ErrorState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { describeError } from "@/lib/api/client";
import { getSiProposal } from "@/lib/api/endpoints";
import { qk, useIssues } from "@/lib/api/queries";
import type { Issue, IssueLegend as Legend, IssueSummary, SiNeEntry, SiProblem } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  EMPTY_ISSUE_FILTERS,
  ISSUE_TABS,
  SEVERITY_KEYS,
  countText,
  displayOrder,
  filterIssues,
  hintLines,
  hintTitle,
  issuesErrorSummary,
  pinnedStatuses,
  resultOptions,
  severityCounts,
  severityLabels,
  sourceOptions,
  statusPillNames,
  summaryCount,
  tabStatus,
  type IssueFilters,
  type IssueTabId,
} from "@/lib/domain/issues";
import { mergeNotes, mergePages, siErrorParts } from "@/lib/domain/si";
import { cn } from "@/lib/utils";
import { IssueDetail } from "./IssueDetail";
import { IssueLegend } from "./IssueLegend";
import { IssuePriorityDialog, type PriorityTarget } from "./IssuePriorityDialog";
import { IssueTable } from "./IssueTable";

const ID_BASE = "issues-tab";
const SUMMARY_CELLS = [
  { tab: "pending", testId: "issues-summary-pending" },
  { tab: "decide", testId: "issues-summary-decide" },
  { tab: "done", testId: "issues-summary-done" },
] as const;

/** 摘要列：三個分頁的件數（取 `summary.byTab`；量不到、載入中、失敗＝「—」），點了切到對應分頁。 */
function SummaryBar({ summary, onPick }: { summary: IssueSummary | undefined; onPick: (tab: IssueTabId) => void }) {
  return (
    <div data-testid="issues-summary" className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-2">
      {SUMMARY_CELLS.map(({ tab, testId }) => (
        <button
          key={tab}
          type="button"
          data-testid={testId}
          onClick={() => onPick(tab)}
          className="cursor-pointer rounded-md border border-wg-line bg-wg-surface px-4 py-2 text-sm transition-colors hover:text-wg-primary"
        >
          {tabStatus(tab)} <strong className="text-lg tabular-nums">{countText(summaryCount(summary, tab))}</strong>
        </button>
      ))}
      <span className="text-xs text-wg-muted">現存帳本內的件數</span>
    </div>
  );
}

/** 整頁讀取失敗：只顯示原因與重試，不渲染資料（reason、cause、detail 逐字，方便對照 Bridge 日誌）。 */
function IssuesError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const { reason, cause, detail } = siErrorParts(error);
  return (
    <div data-testid="issues-error-panel" className="flex flex-col gap-2">
      <ErrorState error={error} title="議題資料無法取得" />
      <div className="flex flex-col gap-1.5 rounded-md border border-wg-line bg-wg-surface px-4 py-3 text-sm">
        <p data-testid="issues-error-summary" className="font-medium text-wg-text">
          {issuesErrorSummary(error)}
        </p>
        {reason ? (
          <p className="text-wg-muted">
            {"reason："}
            <code data-testid="issues-error-reason" className="font-mono text-wg-text">
              {reason}
            </code>
          </p>
        ) : null}
        {cause ? (
          <p className="text-wg-muted">
            {"cause："}
            <code data-testid="issues-error-cause" className="font-mono text-wg-text">
              {cause}
            </code>
          </p>
        ) : null}
        {detail ? (
          <p className="text-wg-muted">
            {"detail："}
            <code data-testid="issues-error-detail" className="font-mono break-all whitespace-pre-wrap text-wg-text">
              {detail}
            </code>
          </p>
        ) : null}
        <div>
          <Button variant="ghost" size="sm" data-testid="issues-retry" onClick={onRetry}>
            重試
          </Button>
        </div>
      </div>
    </div>
  );
}

/** 提示條：`ne`、`problems` 非空才出現（件數＋圖例的中文說明；帳本讀不到時明說哪一本），不阻擋清單。 */
function HintBar({ ne, problems, legend }: { ne: ReadonlyArray<SiNeEntry>; problems: ReadonlyArray<SiProblem>; legend: Legend }) {
  const title = hintTitle(ne, problems);
  if (title === null) return null;
  return (
    <div role="note" data-testid="issues-hint-bar" className="mb-3 rounded-md border border-wg-alert-border bg-wg-alert-bg px-3 py-2 text-sm">
      <p className="font-medium text-wg-warning-text">{title}</p>
      <ul className="mt-1 list-disc pl-5">
        {hintLines(ne, problems, legend).map((line) => (
          <li key={line.key} className="break-words">
            {line.text}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** 待處理上方的計件條：緊急、高、中、低、—、未歸類六格，加總＝目前顯示的列數（不篩選時＝待處理件數）。 */
function SeverityBar({ items, legend }: { items: ReadonlyArray<Issue>; legend: Legend }) {
  const counts = severityCounts(items);
  const labels = severityLabels(legend);
  return (
    <div role="group" aria-label="嚴重度計件" data-testid="issues-severity-bar" className="mb-3 flex flex-wrap gap-x-5 gap-y-1 text-sm">
      {SEVERITY_KEYS.map((key) => (
        <span key={key} data-testid={`issues-sev-${key}`} className="whitespace-nowrap">
          {labels[key]} <strong className="tabular-nums">{counts[key]}</strong>
        </span>
      ))}
    </div>
  );
}

/** 全部分頁的狀態快篩：圖例的每個狀態加表外值；再按一次已選的那顆＝取消（按鈕式單選，`aria-pressed` 標示目前選的）。 */
function StatusPills({ names, value, onChange }: { names: ReadonlyArray<string>; value: string; onChange: (value: string) => void }) {
  return (
    <div role="group" aria-label="狀態快篩" className="mb-3 flex flex-wrap gap-1.5">
      {names.map((name) => (
        <button
          key={name}
          type="button"
          aria-pressed={name === value}
          data-testid={`issues-status-pill-${name}`}
          onClick={() => onChange(name === value ? "" : name)}
          className={cn(
            "inline-flex cursor-pointer items-center rounded-md border px-3 py-1 text-sm font-medium whitespace-nowrap transition-colors",
            name === value ? "border-wg-primary bg-wg-primary text-white" : "border-wg-line bg-wg-surface text-wg-text hover:text-wg-primary",
          )}
        >
          {name}
        </button>
      ))}
    </div>
  );
}

export function IssuesView() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { role } = useAuth();
  /** 寫入入口只對 ADMIN 渲染；非 ADMIN 看得到順位與備註，沒有任何編輯控制項。 */
  const isAdmin = role === "ADMIN";

  const [tab, setTab] = useState<IssueTabId>("pending");
  const [filters, setFilters] = useState<IssueFilters>(EMPTY_ISSUE_FILTERS);
  const [legendOpen, setLegendOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [rankTarget, setRankTarget] = useState<PriorityTarget | null>(null);
  const [decideTarget, setDecideTarget] = useState<DecideTarget | null>(null);
  const [closeTarget, setCloseTarget] = useState<CloseTarget | null>(null);
  /** 正在取提案快照的議題編號（同一時間只取一個；該列的「決定」鈕停用） */
  const [snapshotId, setSnapshotId] = useState<string | null>(null);
  /** 開啟詳情的那個編號按鈕：關閉詳情時把焦點還給它 */
  const opener = useRef<HTMLElement | null>(null);

  const q = useIssues(tabStatus(tab));
  const pages = q.data?.pages;
  const last = pages?.[pages.length - 1];
  // 逐頁自動載完（上限 SI_AUTO_LOAD_MAX_PAGES；必須在 early return 之前呼叫）
  const autoLoading = useAutoLoadRemaining({
    active: true,
    hasNext: q.hasNextPage,
    fetching: q.isFetching,
    failed: q.isError,
    loadedPages: pages?.length ?? 0,
    fetchNextPage: q.fetchNextPage,
  });

  const items = useMemo(
    () =>
      pages
        ? mergePages(
            pages.map((p) => p.items),
            (issue) => issue.id,
          )
        : [],
    [pages],
  );
  const legend = last?.legend;
  // 失敗與載入中都沒有摘要：三格顯示「—」，不拿快取或上一次的數字頂替
  const summary = q.isError ? undefined : last?.summary;
  const pinned = useMemo(() => pinnedStatuses(legend), [legend]);
  // 狀態 pill 只屬於全部分頁、結果快篩只屬於已完成分頁：其他分頁不受殘留的選值影響
  const active = useMemo<IssueFilters>(() => ({ ...filters, status: tab === "all" ? filters.status : "", result: tab === "done" ? filters.result : "" }), [filters, tab]);
  const visible = useMemo(() => displayOrder(filterIssues(items, active, legend), tab, pinned), [items, active, legend, tab, pinned]);

  function changeTab(next: IssueTabId) {
    setTab(next);
    setFilters((f) => ({ ...f, status: "", result: "" }));
  }
  const setFilter = <K extends keyof IssueFilters>(key: K, value: IssueFilters[K]) => setFilters((f) => ({ ...f, [key]: value }));

  function openDetail(id: string, trigger: HTMLElement) {
    opener.current = trigger;
    setSelectedId(id);
  }
  function closeDetail() {
    setSelectedId(null);
    if (opener.current?.isConnected) opener.current.focus();
  }

  /** 決定：先取點擊當下的提案快照再開對話框（對話框綁快照的卡面 digest，不取清單項）；取不到＝不開對話框、顯示原因。 */
  async function startDecide(issue: Issue) {
    if (snapshotId !== null) return;
    setSnapshotId(issue.id);
    try {
      const proposal = (await getSiProposal(issue.id)).items[0];
      if (!proposal) throw new Error(`查無提案 ${issue.id}`);
      setDecideTarget({ kind: "prop", proposal });
    } catch (error) {
      toast.error(`無法取得提案快照：${describeError(error)}`);
    } finally {
      setSnapshotId(null);
    }
  }

  let body: ReactNode;
  if (q.isError) {
    body = <IssuesError error={q.error} onRetry={() => void q.refetch()} />;
  } else if (!pages || !last || !legend) {
    body = (
      <div role="status" data-testid="issues-loading" className="px-1 py-6 text-sm text-wg-muted">
        議題載入中…
      </div>
    );
  } else {
    const empty = items.length === 0 && !q.hasNextPage;
    const incomplete = !autoLoading && (q.hasNextPage || last.truncated);
    body = (
      <>
        <div className="mb-3 flex flex-wrap items-center gap-x-5 gap-y-2">
          <FilterSelect label="來源" testId="issues-filter-source" value={filters.source} options={sourceOptions(legend)} onChange={(v) => setFilter("source", v)} />
          {tab === "done" ? <FilterSelect label="結果" testId="issues-filter-result" value={filters.result} options={resultOptions(legend)} onChange={(v) => setFilter("result", v)} /> : null}
          <div className="flex items-center gap-2 text-sm">
            <span aria-hidden className="text-wg-muted">
              關鍵字
            </span>
            <Input
              aria-label="關鍵字"
              placeholder="編號或標題"
              value={filters.keyword}
              onChange={(e) => setFilter("keyword", e.target.value)}
              data-testid="issues-filter-keyword"
              className="min-h-9 w-56 py-1.5"
            />
          </div>
          <span data-testid="issues-filter-count" className="text-xs text-wg-muted">{`符合 ${visible.length}／已載入 ${items.length}`}</span>
        </div>
        {tab === "all" ? <StatusPills names={statusPillNames(legend)} value={filters.status} onChange={(v) => setFilter("status", v)} /> : null}

        <HintBar ne={mergeNotes(pages.map((p) => p.ne))} problems={mergeNotes(pages.map((p) => p.problems))} legend={legend} />
        {tab === "pending" ? <SeverityBar items={visible} legend={legend} /> : null}

        {autoLoading ? <p role="status" data-testid="issues-loading-more" className="mb-2 text-xs text-wg-muted">{`議題載入中（已載入 ${items.length} 件）…`}</p> : null}
        {incomplete ? (
          <div role="status" data-testid="issues-incomplete" className="mb-3 flex flex-wrap items-center gap-3 text-sm text-wg-warning-text">
            <span>{`結果不完整：已載入 ${items.length} 件，尚有未載入的議題；篩選只作用於已載入的項目`}</span>
            {q.hasNextPage ? (
              <Button variant="ghost" size="sm" data-testid="issues-load-more" disabled={q.isFetchingNextPage} onClick={() => void q.fetchNextPage()}>
                載入更多
              </Button>
            ) : null}
          </div>
        ) : null}

        {empty ? (
          <p data-testid="issues-empty" className="py-4 text-sm text-wg-muted">
            這個分頁目前沒有議題
          </p>
        ) : visible.length === 0 ? (
          autoLoading ? null : (
            <p data-testid="issues-no-match" className="py-3 text-sm text-wg-muted">
              沒有符合目前篩選的議題
            </p>
          )
        ) : (
          <IssueTable
            items={visible}
            tab={tab}
            pinned={pinned}
            isAdmin={isAdmin}
            selectedId={selectedId}
            snapshotId={snapshotId}
            onOpen={openDetail}
            onRank={(issue) => setRankTarget({ id: issue.id, priority: issue.priority, note: issue.priorityNote })}
            onDecide={(issue) => void startDecide(issue)}
            onCloseObservation={(issue) => setCloseTarget({ obsId: issue.id })}
          />
        )}
      </>
    );
  }

  return (
    <div data-testid="issues-page">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2.5 text-[30px] font-bold max-md:text-2xl">
            <ListChecks size={26} className="shrink-0 text-wg-primary" aria-hidden />
            議題中心
          </h1>
          <p className="mt-1 text-[15px] text-wg-muted">鏡像：畫面內容逐欄來自根層議題匯出，Console 不寫入帳本；唯一自有的資料是您設定的優先順序。</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" iconLeft={Info} data-testid="issues-legend-open" disabled={!legend} onClick={() => setLegendOpen(true)}>
            狀態說明
          </Button>
          <Button variant="ghost" iconLeft={RefreshCw} data-testid="issues-refresh" onClick={() => void queryClient.refetchQueries({ queryKey: qk.issuesAll, type: "active" })}>
            重新整理
          </Button>
        </div>
      </div>

      <SummaryBar summary={summary} onPick={changeTab} />

      <PillTabs label="議題分頁" idBase={ID_BASE} tabs={ISSUE_TABS.map(({ id, label }) => ({ id, label }))} value={tab} onChange={changeTab} className="mb-4" />

      <div className="flex flex-col gap-4 xl:flex-row xl:items-start">
        <Card role="tabpanel" id={pillPanelId(ID_BASE, tab)} aria-labelledby={pillTabId(ID_BASE, tab)} data-testid={`issues-panel-${tab}`} className="min-w-0 flex-1 px-5 py-4">
          {body}
        </Card>
        {selectedId !== null ? (
          <div className="min-w-0 xl:w-[26rem] xl:shrink-0">
            <IssueDetail id={selectedId} legend={legend} onClose={closeDetail} onOpenIssue={setSelectedId} />
          </div>
        ) : null}
      </div>

      <IssueLegend legend={legend} open={legendOpen} onClose={() => setLegendOpen(false)} />
      {isAdmin ? (
        <>
          <IssuePriorityDialog target={rankTarget} onClose={() => setRankTarget(null)} />
          <SiDecideDialog target={decideTarget} onClose={() => setDecideTarget(null)} />
          <SiObsCloseDialog target={closeTarget} onClose={() => setCloseTarget(null)} />
        </>
      ) : null}
    </div>
  );
}
