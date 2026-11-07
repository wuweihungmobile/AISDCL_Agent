"use client";

/**
 * 內環看板（FR-R2P-15；TCS-ResearchToPRD-P2-20261107 AT-962-11-*；IFACE-P2 §1）：Task 拆解→測試規格產生→程式碼實作→自癒修復→回歸驗收五欄，資料全來自 `GET …/kanban`（唯讀聚合）。
 *
 * 設計要點（為什麼這樣做）：
 *  - **串流只是通知、畫面以 REST 為準**：訂研究專案串流（`research.step`／`research.gate`／`research.delivery`）與最新 run 的日誌串流（`status-change`／`review-request`／`alert`）；
 *    任一幀 → `invalidateQueries(["research","kanban",id])`，**100 ms 去抖**（同窗內多幀合併為一次；窗從第一幀起算、不順延）。
 *    `replay_gap` 或斷線重連（出過錯再開啟）→ 立刻 REST 全量重抓；瀏覽器自己重連時會帶 `Last-Event-ID`（同一個連線實例）。
 *    「≤500 ms」＝幀到瀏覽器至看板 DOM commit，不含後端讀 FSM 的延遲（D-138 Q-9）；常數與去抖共用 `lib/domain/research.ts` 的單一出處。
 *  - **Bridge 不可達不假裝即時**：`bridgeReachable=false` ⇒ 橫幅「Engine Bridge 無法連線，以下為 <時間> 的 DB 快照」＋ `data-stale=true`、FSM 衍生欄「未知」徽章；仍顯示 DB 欄位，**不渲染空看板**。
 *  - **只連結、不控制**：本元件不呼叫任何執行控制端點、不直接送網路請求；動作鈕只連既有路徑（執行中心／監控中心，帶 `?researchId=<uuid>`）。
 *    決定一律由 {@link DecisionCenter}（唯一彈窗殼）走既有審核端點。
 *  - 權限：VIEWER 可讀；「登錄 SCG」「發起 SCR」停用且 `title` 為唯讀說明。規格變更中（`scrOpen`）執行中心連結停用並顯示登記文案（`BUILD_DISABLED_TEXT`）。
 */
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { DecisionCenter, type DecisionTrigger } from "@/components/domain/research/DecisionModal";
import { GateRegisterDialog } from "@/components/domain/research/GateRegisterDialog";
import { KanbanColumn, type KanbanFact, type KanbanLink } from "@/components/domain/research/KanbanColumn";
import { ScrLaunchButton } from "@/components/domain/research/ScrRequestDialog";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { apiBase, getFreshAccessToken } from "@/lib/api/client";
import { qk, useResearchKanban } from "@/lib/api/queries";
import { DEFAULT_MAX_FAILURES, READY_CLOSED, buildStreamUrl, defaultBackoffMs, type EventSourceCtor, type EventSourceLike } from "@/lib/api/sse";
import type { ResearchKanban } from "@/lib/api/types";
import {
  BUILD_DISABLED_TEXT,
  KANBAN_DEBOUNCE_MS,
  RESEARCH_REPLAY_GAP_EVENT,
  buildResearchStreamUrl,
  consoleCenterHref,
  decisionKey,
  kanbanColumns,
  kanbanStaleBanner,
  type KanbanColumnKey,
} from "@/lib/domain/research";

const RESEARCH_FRAME_NAMES = ["research.step", "research.gate", "research.delivery"] as const;
const RUN_FRAME_NAMES = ["status-change", "review-request", "alert"] as const;
const GAP_NAMES = [RESEARCH_REPLAY_GAP_EVENT, "replay_gap"] as const;

const DECOMPOSE_STATUS_LABEL: Readonly<Record<string, string>> = {
  NONE: "尚未拆解",
  DRAFTED: "草稿",
  SCG_PASSED: "規格審查通過",
  FROZEN: "已凍結",
  SIGNED_OFF: "已簽核",
  REJECTED: "已退回",
  STALE: "已過期",
};

/** 一條串流：連線、重連、gap 與「重連後再開啟」都在這裡；幀只通知上層，不在這裡解讀成畫面狀態。 */
function openStream(
  Source: EventSourceCtor,
  buildUrl: (token: string) => string,
  names: readonly string[],
  on: { frame: (name: string, message: MessageEvent) => void; resync: () => void },
): () => void {
  let stopped = false;
  let source: EventSourceLike | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let failures = 0;
  let everOpened = false;
  let erroredSinceOpen = false;

  async function connect(rebuilt: boolean) {
    if (stopped) return;
    const token = await getFreshAccessToken({ force: rebuilt });
    if (stopped) return;
    if (token === null) {
      retryLater();
      return;
    }
    const es = new Source(buildUrl(token));
    source = es;
    es.onopen = () => {
      if (stopped || source !== es) return;
      // 新連線沒有 Last-Event-ID，出過錯的連線也可能漏幀：以 REST 全量重抓補齊
      if ((rebuilt && everOpened) || erroredSinceOpen) on.resync();
      everOpened = true;
      failures = 0;
      erroredSinceOpen = false;
    };
    for (const name of names) es.addEventListener(name, (message) => !stopped && source === es && on.frame(name, message));
    for (const name of GAP_NAMES) es.addEventListener(name, () => !stopped && source === es && on.resync());
    es.onerror = () => {
      if (stopped || source !== es) return;
      if (es.readyState === READY_CLOSED) {
        source = null;
        failures += 1;
        retryLater();
      } else {
        erroredSinceOpen = true; // 瀏覽器自己帶 Last-Event-ID 重連：同一個實例
      }
    };
  }
  function retryLater() {
    if (stopped || failures > DEFAULT_MAX_FAILURES || timer !== null) return;
    timer = setTimeout(() => {
      timer = null;
      void connect(true);
    }, defaultBackoffMs(failures));
  }
  void connect(false);
  return () => {
    stopped = true;
    if (timer !== null) clearTimeout(timer);
    source?.close();
    source = null;
  };
}

function parseData(message: MessageEvent): unknown {
  try {
    return JSON.parse(String(message.data));
  } catch {
    return null;
  }
}

/** review-request／alert 幀 → 決策觸發（形狀不合就回 null；去重鍵由 {@link decisionKey} 決定）。 */
export function triggerFromFrame(name: string, data: unknown): DecisionTrigger | null {
  if (typeof data !== "object" || data === null) return null;
  const d = data as Record<string, unknown>;
  if (name === "review-request") {
    const r = d.review;
    if (typeof r !== "object" || r === null) return null;
    const review = r as Record<string, unknown>;
    const reviewId = typeof review.id === "string" ? review.id : null;
    const key = decisionKey({ reviewId });
    if (key === null) return null;
    return {
      key,
      reviewId,
      runId: typeof review.runId === "string" ? review.runId : null,
      kind: typeof review.kind === "string" ? review.kind : "REVIEW",
      taskId: typeof review.taskId === "string" ? review.taskId : null,
      reason: typeof review.reason === "string" ? review.reason : "",
      allowedDecisions: Array.isArray(review.allowedDecisions) ? review.allowedDecisions.filter((x): x is string => typeof x === "string") : [],
    };
  }
  if (name === "alert" && d.code === "ESCALATION") {
    const key = decisionKey({ alertSeq: typeof d.seq === "number" ? d.seq : null });
    if (key === null) return null;
    return { key, reviewId: null, runId: null, kind: "ALERT", taskId: null, reason: typeof d.message === "string" ? d.message : "引擎回報升級事件", allowedDecisions: [] };
  }
  return null;
}

export function KanbanBoard({ researchId, EventSourceCtor }: { researchId: string; EventSourceCtor?: EventSourceCtor }) {
  const qc = useQueryClient();
  const query = useResearchKanban(researchId);
  const kanban = query.data;
  const runId = kanban?.latestRunId ?? null;
  const [triggers, setTriggers] = useState<DecisionTrigger[]>([]);

  // 去抖：窗從第一幀起算、不順延；窗內後來的幀合併進同一次重抓
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const refetchNow = useCallback(() => void qc.invalidateQueries({ queryKey: qk.researchKanban(researchId) }), [qc, researchId]);
  const schedule = useCallback(() => {
    if (debounce.current !== null) return;
    debounce.current = setTimeout(() => {
      debounce.current = null;
      refetchNow();
    }, KANBAN_DEBOUNCE_MS);
  }, [refetchNow]);
  useEffect(
    () => () => {
      if (debounce.current !== null) clearTimeout(debounce.current);
      debounce.current = null;
    },
    [],
  );

  const addTrigger = useCallback((t: DecisionTrigger) => setTriggers((cur) => (cur.some((c) => c.key === t.key) ? cur : [...cur, t])), []);

  useEffect(() => {
    const found = EventSourceCtor ?? (typeof EventSource === "undefined" ? null : (EventSource as unknown as EventSourceCtor));
    if (found === null) return;
    return openStream(found, (token) => buildResearchStreamUrl(apiBase(), researchId, token), RESEARCH_FRAME_NAMES, { frame: () => schedule(), resync: refetchNow });
  }, [researchId, EventSourceCtor, schedule, refetchNow]);

  useEffect(() => {
    if (runId === null) return;
    const found = EventSourceCtor ?? (typeof EventSource === "undefined" ? null : (EventSource as unknown as EventSourceCtor));
    if (found === null) return;
    return openStream(found, (token) => buildStreamUrl({ runId, kind: "logs", token }), RUN_FRAME_NAMES, {
      frame: (name, message) => {
        const trigger = triggerFromFrame(name, parseData(message));
        if (trigger !== null) addTrigger(trigger);
        schedule();
      },
      resync: refetchNow,
    });
  }, [runId, EventSourceCtor, schedule, refetchNow, addTrigger]);

  const columns = useMemo(() => (kanban === undefined ? [] : kanbanColumns(kanban)), [kanban]);

  if (kanban === undefined) {
    return query.isError ? <ErrorState error={query.error} title="無法載入看板" onRetry={() => void query.refetch()} /> : <PageSkeleton />;
  }

  const stale = !kanban.bridgeReachable;
  const bound = kanban.consoleProjectId;
  const links = (): { execute: KanbanLink; monitor: KanbanLink } => {
    if (bound === null) {
      const reason = BUILD_DISABLED_TEXT.needDecomposition;
      return { execute: { href: null, reason }, monitor: { href: null, reason } };
    }
    return {
      execute: kanban.scrOpen ? { href: null, reason: BUILD_DISABLED_TEXT.scrOpen } : { href: consoleCenterHref(bound, "execute", researchId), reason: null },
      monitor: { href: consoleCenterHref(bound, "monitor", researchId), reason: null },
    };
  };
  const doneOf = (key: KanbanColumnKey) => columns.find((c) => c.key === key)!;
  const { decompose, tcs, implement, healing, regression } = kanban.columns;
  const rtm = regression.rtm;
  const facts: Record<KanbanColumnKey, KanbanFact[]> = {
    decompose: [
      { label: "拆解狀態", value: DECOMPOSE_STATUS_LABEL[decompose.status] ?? decompose.status },
      { label: "任務數", value: decompose.tasksCount },
      ...(decompose.stale ? [{ label: "提醒", value: "PRD 已更新，拆解已過期" }] : []),
    ],
    tcs: [
      { label: "階段 2 凍結", value: tcs.stage2Frozen === null ? null : tcs.stage2Frozen ? "已凍結" : "尚未凍結" },
      { label: "狀態機狀態", value: tcs.fsmState },
      { label: "協商", value: tcs.negotiated === null ? null : tcs.negotiated ? "已協商" : "未協商" },
    ],
    implement: [
      { label: "狀態機狀態", value: implement.fsmState },
      { label: "任務總數", value: implement.tasks.total },
      { label: "成功任務", value: implement.tasks.completed },
      { label: "已跳過", value: implement.tasks.skipped },
      { label: "執行中", value: implement.tasks.running },
      { label: "重試中", value: implement.tasks.retrying },
      { label: "失敗", value: implement.tasks.failed },
      { label: "已升級", value: implement.tasks.escalated },
    ],
    healing: [
      { label: "重試中步驟", value: healing.retryingSteps },
      { label: "已升級任務", value: healing.escalatedTasks },
      { label: "重試上限", value: healing.maxRetries },
    ],
    regression: [
      { label: "狀態機狀態", value: regression.fsmState },
      { label: "追溯覆蓋（AC）", value: rtm === null ? "尚無追溯資料" : `${rtm.acCovered}／${rtm.acTotal}（${rtm.acPct}%）` },
      { label: "自動測試（AT）", value: rtm === null ? "尚無追溯資料" : `${rtm.atPassed}／${rtm.atTotal}` },
    ],
  };
  const l = links();

  return (
    <section aria-label="內環看板" data-testid="kanban-board" data-stale={String(stale)} className="flex flex-col gap-4">
      {stale ? (
        <div role="alert" data-testid="kanban-stale-banner" className="rounded-md border border-wg-error bg-wg-draft-bg px-4 py-3 text-sm font-semibold text-wg-error">
          {kanbanStaleBanner(kanban.snapshotAt)}
        </div>
      ) : null}
      <div className="flex flex-wrap items-center gap-3" data-testid="kanban-actions">
        <GateRegisterDialog researchId={researchId} scrOpen={kanban.scrOpen} />
        <ScrLaunchButton researchId={researchId} scrOpen={kanban.scrOpen} />
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5" data-testid="kanban-columns">
        {columns.map((c) => (
          <KanbanColumn key={c.key} columnKey={c.key} label={c.label} done={doneOf(c.key).done} facts={facts[c.key]} advisory={c.key === "regression"} execute={l.execute} monitor={l.monitor} />
        ))}
      </div>
      <KanbanGates kanban={kanban} />
      <DecisionCenter researchId={researchId} pendingReviews={kanban.pendingReviews} triggers={triggers} />
    </section>
  );
}

function KanbanGates({ kanban }: { kanban: ResearchKanban }) {
  if (kanban.gates.length === 0) return null;
  return (
    <section aria-label="SCG 登錄紀錄" data-testid="kanban-gates" className="flex flex-col gap-1 text-sm">
      <h4 className="text-base font-semibold">SCG 登錄紀錄</h4>
      <ul className="flex flex-col gap-1">
        {kanban.gates.map((g) => (
          <li key={`${g.gate}-${g.decidedAt}`} data-testid="kanban-gate" className="break-words">
            {g.gate === "SCG4" ? "SCG-4" : g.gate === "SCG5" ? "SCG-5" : "SCG-6"}：{g.decision === "APPROVED" ? "通過" : "未通過"}（{g.decidedBy}，狀態機：{g.fsmStateAfter}）
            {g.reason !== "" ? `— ${g.reason}` : ""}
          </li>
        ))}
      </ul>
    </section>
  );
}
