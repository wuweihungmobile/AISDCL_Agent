"use client";

/**
 * 證據鏈即時動態欄（研究工作區步驟 1 的時間軸；FR-R2P-06；TCS-ResearchToPRD-P0-20261102 AT-960-10-4、10-5、10-7、10-8；ADR-001 D4 唯一串流）：
 * 研究 run 期間依 `seq` 即時顯示來源、證據列、run 狀態與警示；**動態欄不是真相**——頁面重開時整份由資料庫的事件帳（REST `…/events`）重建，串流只負責「更新鮮」。
 *
 * 設計要點（為什麼這樣做）：
 *  - **顯示＝REST 事件與串流事件依 seq 去重合併後「自 1 起連續」的前綴**：缺口之後的事件一律扣住不渲染，所以任一時刻畫面上的 seq 嚴格遞增、無缺漏、無重複。
 *  - **兩種缺口偵測，都走同一條全量重抓**：(1) 伺服器重播不完整時先送的傳輸層訊號 `research.replay_gap`（不是事件、不佔 seq、不顯示、不影響「最後處理的 seq」）；
 *    (2) 訊號遺失時，事件 `id` 不是「已處理的最大 seq 加一」。全量重抓＝專案詳情、專案列表與事件帳自 `afterSeq=0` 整份重抓（`truncated` 時以 `nextSeq` 續抓，由 `useResearchEvents` 負責）。
 *    重抓期間設「障壁」：只渲染障壁（缺口或訊號當下的最後處理 seq）以內的事件，重抓完成才放掉障壁、與串流事件依 seq 去重合併；補不齊就有限次重試，仍補不齊顯示警示與「重新同步」。
 *  - **重連靠同一個 EventSource**：瀏覽器自動重連時帶 `Last-Event-ID`（最後處理的 id）；連線被瀏覽器放棄（401／404 等，`readyState` 為 CLOSED）才退避重建（換新 token），並以 REST 補抓一次。
 *    連續失敗過多就停手、改以 REST 輪詢，並提供「重新連線」。
 *  - **訂閱契約 §3 的全部事件名**（含 P1／P2 才出現的、畫面不顯示的）：沒訂閱的事件仍佔用 seq，會讓下一則事件被誤判成缺口。
 *  - **外部衍生的文字一律純文字**：標題、摘要、來源名、無效原因、警示說明都以文字節點渲染（沒有 Markdown、沒有原始 HTML）；來源網址只有合法 https 才成連結。
 *  - 量測 AC-R2P-06-1：串流事件若帶 `emittedAt`，在事件變成可見的當下記 `rendered_at`，延遲 P95 與量不到的筆數以 `data-latency-*` 暴露給 E2E／效能探針。
 */
import { useQueryClient } from "@tanstack/react-query";
import { Activity, ArrowRight, Bug, CircleDot, ClipboardCheck, FileSearch, FileText, ListChecks, RefreshCw, ShieldCheck, TriangleAlert, type LucideIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { StatusDot } from "@/components/ui/status-dot";
import { apiBase, getFreshAccessToken } from "@/lib/api/client";
import { getResearchProject, listResearchProjects } from "@/lib/api/endpoints";
import { qk, useResearchEvents } from "@/lib/api/queries";
import { DEFAULT_MAX_FAILURES, READY_CLOSED, defaultBackoffMs, type EventSourceCtor, type EventSourceLike } from "@/lib/api/sse";
import type { ResearchEvent } from "@/lib/api/types";
import {
  FLOW_STEP_LABEL,
  RESEARCH_HEARTBEAT_EVENT,
  RESEARCH_REPLAY_GAP_EVENT,
  RESEARCH_SSE_EVENT_TYPES,
  TIMELINE_RENDER_LIMIT,
  buildResearchStreamUrl,
  classifyIncomingSeq,
  describeResearchEvent,
  formatInstant,
  isFlowStepId,
  latencySummary,
  mergeEventsBySeq,
  parseReplayGap,
  parseTimelineEvent,
  renderLatencyMs,
  safeExternalHref,
  stepNumber,
  timelineView,
  type EventKind,
  type EventTone,
  type LatencySummary,
  type TimelineEvent,
} from "@/lib/domain/research";
import { cn } from "@/lib/utils";

/** 缺口補不齊時，再重抓前的等待（毫秒）與最多再重抓幾次。 */
export const SYNC_RETRY_MS = 1500;
export const SYNC_RETRY_MAX = 2;
/** 串流事件之後讓相關查詢（專案詳情、來源、證據矩陣）重抓前的去抖（毫秒）：連續事件只重抓一次。 */
export const REFRESH_DEBOUNCE_MS = 400;

/** 哪些串流事件代表哪一份資料變了：專案詳情（游標與計數）、來源、證據矩陣；其餘事件（警示等）不需要重抓。 */
const REFRESH_KIND: Readonly<Record<string, "project" | "sources" | "evidence">> = {
  "research.step": "project",
  "research.run": "project",
  "research.prd": "project",
  "research.review": "project",
  "research.review_invalid": "project",
  "research.defect": "project",
  "research.gate": "project",
  "research.reconcile": "project",
  "research.source": "sources",
  "research.evidence": "evidence",
};

export type TimelineConnection = "connecting" | "open" | "reconnecting" | "failed" | "unsupported";

export type TimelineOptions = {
  /** 測試注入；預設瀏覽器的 EventSource */
  EventSourceCtor?: EventSourceCtor;
  /** 缺口補不齊時，再重抓前的等待（毫秒） */
  syncRetryMs?: number;
  /** 串流事件之後相關查詢重抓前的去抖（毫秒） */
  refreshDebounceMs?: number;
  /** 連線被瀏覽器放棄後，重建前的等待（毫秒）；預設指數退避 1→30 秒 */
  backoffMs?: (failures: number) => number;
};

/**
 * 研究專案的事件時間軸（REST 事件帳＋SSE 串流＋缺口同步）。換研究專案時呼叫端應以 `key={researchId}` 重掛。
 * 回傳的 `view.visible` 是要渲染的事件（嚴格遞增、自 1 起連續、無重複）。
 */
export function useResearchTimeline(researchId: string, options: TimelineOptions = {}) {
  const { EventSourceCtor, syncRetryMs = SYNC_RETRY_MS, refreshDebounceMs = REFRESH_DEBOUNCE_MS, backoffMs = defaultBackoffMs } = options;
  const qc = useQueryClient();
  const supported = EventSourceCtor !== undefined || typeof EventSource !== "undefined";
  const [connection, setConnection] = useState<TimelineConnection>(supported ? "connecting" : "unsupported");
  // 串流不可用（不支援或連線放棄後停手）時，退回 REST 輪詢
  const eventsQuery = useResearchEvents(researchId, { poll: connection === "failed" || connection === "unsupported" });
  const rest = eventsQuery.data;

  const [live, setLive] = useState<TimelineEvent[]>([]);
  const [barrier, setBarrier] = useState<number | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncFailed, setSyncFailed] = useState(false);
  const [nonce, setNonce] = useState(0);
  const [latency, setLatency] = useState<LatencySummary>({ measured: 0, unmeasured: 0, p95: null });

  const liveRef = useRef<TimelineEvent[]>([]);
  const lastSeqRef = useRef(0);
  const syncingRef = useRef(false);
  const targetRef = useRef(0);
  const refetchRef = useRef(eventsQuery.refetch);
  const aliveRef = useRef(true);
  const timersRef = useRef(new Set<ReturnType<typeof setTimeout>>());
  const measuredRef = useRef<{ upTo: number; samples: Array<number | null> }>({ upTo: 0, samples: [] });

  useEffect(() => {
    refetchRef.current = eventsQuery.refetch;
  }, [eventsQuery.refetch]);

  useEffect(() => {
    aliveRef.current = true;
    const timers = timersRef.current;
    return () => {
      aliveRef.current = false;
      for (const timer of timers) clearTimeout(timer);
      timers.clear();
    };
  }, []);

  // 資料庫的事件帳是「已處理」的一部分：串流事件相對「REST 與串流合起來的最大 seq」判重複、接續或缺口
  useEffect(() => {
    if (rest !== undefined && rest.length > 0) lastSeqRef.current = Math.max(lastSeqRef.current, rest[rest.length - 1].seq);
  }, [rest]);

  const view = useMemo(() => timelineView<ResearchEvent>(rest ?? [], live, barrier), [rest, live, barrier]);

  // 串流事件讓相關資料保持新鮮（研究一完成，游標、證據矩陣與「生成 PRD 初稿」的證據閘就跟著更新，不必等輪詢）；連續事件去抖成一次重抓
  const pendingRefresh = useRef<{ kinds: Set<string>; timer: ReturnType<typeof setTimeout> | null }>({ kinds: new Set(), timer: null });
  const scheduleRefresh = useCallback(
    (eventType: string) => {
      const kind = REFRESH_KIND[eventType];
      if (kind === undefined) return;
      const pending = pendingRefresh.current;
      pending.kinds.add(kind);
      if (pending.timer !== null) return;
      const timer = setTimeout(() => {
        pending.timer = null;
        timersRef.current.delete(timer);
        const kinds = new Set(pending.kinds);
        pending.kinds.clear();
        if (!aliveRef.current) return;
        if (kinds.has("project")) {
          void qc.invalidateQueries({ queryKey: qk.researchProject(researchId) });
          void qc.invalidateQueries({ queryKey: qk.researchProjects });
        }
        if (kinds.has("sources")) void qc.invalidateQueries({ queryKey: qk.researchSources(researchId) });
        if (kinds.has("evidence")) void qc.invalidateQueries({ queryKey: [...qk.researchProjectAll(researchId), "evidence"] });
      }, refreshDebounceMs);
      pending.timer = timer;
      timersRef.current.add(timer);
    },
    [qc, researchId, refreshDebounceMs],
  );

  // 全量重抓：專案詳情、專案列表、事件帳自 afterSeq=0 整份；完成前障壁擋住缺口或訊號之後的事件
  const startSync = useCallback(
    (barrierSeq: number, target: number) => {
      if (syncingRef.current) {
        targetRef.current = Math.max(targetRef.current, target);
        return;
      }
      syncingRef.current = true;
      targetRef.current = target;
      setSyncing(true);
      setSyncFailed(false);
      setBarrier(barrierSeq);
      const finish = (ok: boolean) => {
        syncingRef.current = false;
        setSyncing(false);
        setBarrier(null);
        setSyncFailed(!ok);
      };
      void (async () => {
        for (let attempt = 0; ; attempt += 1) {
          const [, , refreshed] = await Promise.all([
            qc.fetchQuery({ queryKey: qk.researchProject(researchId), queryFn: ({ signal }) => getResearchProject(researchId, { signal }), staleTime: 0 }).catch(() => null),
            qc.fetchQuery({ queryKey: qk.researchProjects, queryFn: ({ signal }) => listResearchProjects({ signal }), staleTime: 0 }).catch(() => null),
            refetchRef.current(),
          ]);
          if (!aliveRef.current) return;
          if (!refreshed.isError && refreshed.data !== undefined) {
            const merged = timelineView(refreshed.data, liveRef.current);
            lastSeqRef.current = Math.max(lastSeqRef.current, merged.lastSeq);
            if (merged.held === 0 && merged.visible.length >= targetRef.current) {
              // 缺漏的事件裡可能有來源與證據列：矩陣也一併更新
              scheduleRefresh("research.source");
              scheduleRefresh("research.evidence");
              return finish(true);
            }
          }
          if (attempt >= SYNC_RETRY_MAX) return finish(false);
          await new Promise<void>((resolve) => {
            const timer = setTimeout(() => {
              timersRef.current.delete(timer);
              resolve();
            }, syncRetryMs);
            timersRef.current.add(timer);
          });
          if (!aliveRef.current) return;
        }
      })();
    },
    [qc, researchId, syncRetryMs, scheduleRefresh],
  );

  // SSE：REST 事件帳載入完成才連線（先有「已處理的最大 seq」，第一則串流事件才不會被誤判成缺口）
  const streamEnabled = rest !== undefined;
  useEffect(() => {
    if (!streamEnabled) return;
    const found = EventSourceCtor ?? (typeof EventSource === "undefined" ? null : (EventSource as unknown as EventSourceCtor));
    if (found === null) return; // 沒有 EventSource：初始狀態已是 unsupported，改靠 REST 輪詢
    const Source: EventSourceCtor = found;
    let stopped = false;
    let source: EventSourceLike | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let failures = 0;
    let everOpened = false;

    const onEvent = (message: MessageEvent) => {
      let data: unknown;
      try {
        data = JSON.parse(String(message.data));
      } catch {
        return; // 損毀的資料行：略過，不讓整條串流掛掉
      }
      const event = parseTimelineEvent(data, message.lastEventId ? message.lastEventId : null);
      if (event === null) return;
      const kind = classifyIncomingSeq(lastSeqRef.current, event.seq);
      if (kind === "duplicate") return; // 至少一次送達：重播的事件只算一次
      const previous = lastSeqRef.current;
      lastSeqRef.current = event.seq;
      liveRef.current = mergeEventsBySeq(liveRef.current, [event]);
      setLive(liveRef.current);
      scheduleRefresh(event.eventType);
      if (kind === "gap") startSync(previous, event.seq);
      else if (syncingRef.current) targetRef.current = Math.max(targetRef.current, event.seq);
    };

    // 傳輸層訊號：不是事件、不改「最後處理的 seq」；一律全量重抓（訊號之後的事件在重抓完成前不渲染）
    const onGapSignal = (message: MessageEvent) => {
      let data: unknown = null;
      try {
        data = JSON.parse(String(message.data));
      } catch {
        data = null;
      }
      startSync(lastSeqRef.current, parseReplayGap(data)?.toSeq ?? lastSeqRef.current);
    };

    const retryLater = () => {
      if (failures > DEFAULT_MAX_FAILURES) {
        setConnection("failed");
        return;
      }
      setConnection("reconnecting");
      timer = setTimeout(() => {
        timer = null;
        void connect(true);
      }, backoffMs(failures));
    };

    async function connect(rebuilt: boolean) {
      if (stopped) return;
      setConnection(everOpened || failures > 0 ? "reconnecting" : "connecting");
      const token = await getFreshAccessToken({ force: rebuilt });
      if (stopped) return;
      if (token === null) {
        // 眼前拿不到可用 token（後端暫時不可用且現有 token 已過期）：不放棄，與連線失敗同一條路退避重試
        failures += 1;
        retryLater();
        return;
      }
      const es = new Source(buildResearchStreamUrl(apiBase(), researchId, token));
      source = es;
      es.onopen = () => {
        if (stopped || source !== es) return;
        everOpened = true;
        failures = 0;
        setConnection("open");
        if (rebuilt) void refetchRef.current(); // 新連線沒有 Last-Event-ID：以 REST 補抓斷線期間的事件
      };
      for (const name of RESEARCH_SSE_EVENT_TYPES) es.addEventListener(name, onEvent);
      es.addEventListener(RESEARCH_REPLAY_GAP_EVENT, onGapSignal);
      es.addEventListener(RESEARCH_HEARTBEAT_EVENT, () => {
        if (!stopped && source === es) setConnection("open");
      });
      es.onerror = () => {
        if (stopped || source !== es) return;
        if (es.readyState === READY_CLOSED) {
          // 瀏覽器放棄了（401／404／204…；EventSource 看不到狀態碼）：不會再自己重連，退避後換新 token 重建
          source = null;
          failures += 1;
          retryLater();
        } else {
          setConnection("reconnecting"); // 瀏覽器自己帶 Last-Event-ID 重連：同一個實例
        }
      };
    }

    void connect(false);
    return () => {
      stopped = true;
      if (timer !== null) clearTimeout(timer);
      source?.close();
      source = null;
    };
  }, [researchId, streamEnabled, EventSourceCtor, backoffMs, startSync, scheduleRefresh, nonce]);

  // 量測延遲：串流事件在「變成可見」的當下記 rendered_at；REST 載入的事件沒有 emittedAt，不入樣
  useEffect(() => {
    const measured = measuredRef.current;
    const fromStream = new Map(live.map((event) => [event.seq, event] as const));
    let changed = false;
    for (const event of view.visible) {
      if (event.seq <= measured.upTo) continue;
      const streamed = fromStream.get(event.seq);
      if (streamed !== undefined) {
        measured.samples.push(renderLatencyMs(streamed, Date.now()));
        changed = true;
      }
    }
    if (view.visible.length > 0) measured.upTo = Math.max(measured.upTo, view.visible[view.visible.length - 1].seq);
    if (changed) setLatency(latencySummary(measured.samples));
  }, [view.visible, live]);

  return {
    ready: rest !== undefined,
    loadError: rest === undefined && eventsQuery.isError ? eventsQuery.error : null,
    reload: () => void eventsQuery.refetch(),
    view,
    connection,
    syncing,
    syncFailed,
    /** 手動重新同步（補不齊時）：以目前畫面為障壁，補到目前已知的最大 seq */
    resync: () => startSync(view.visible.length, view.lastSeq),
    /** 手動重新連線（連續失敗後停手時） */
    reconnect: () => setNonce((n) => n + 1),
    latency,
  };
}

const KIND_ICON: Readonly<Record<EventKind, LucideIcon>> = {
  step: ArrowRight,
  run: Activity,
  source: FileSearch,
  evidence: ListChecks,
  prd: FileText,
  review: ClipboardCheck,
  defect: Bug,
  gate: ShieldCheck,
  reconcile: RefreshCw,
  alert: TriangleAlert,
  other: CircleDot,
};

const TONE_CLASS: Readonly<Record<EventTone, string>> = {
  normal: "text-wg-muted",
  good: "text-wg-primary",
  warn: "text-wg-warning-text",
  error: "text-wg-error",
};

const CONNECTION_META: Readonly<Record<TimelineConnection, { label: string; color: string; live: boolean }>> = {
  connecting: { label: "連線中…", color: "var(--color-text-muted)", live: true },
  open: { label: "即時連線中", color: "var(--color-primary)", live: false },
  reconnecting: { label: "重新連線中…", color: "var(--color-warning)", live: true },
  failed: { label: "即時連線中斷，改以定時重新整理", color: "var(--color-accent)", live: false },
  unsupported: { label: "此瀏覽器不支援即時連線，改以定時重新整理", color: "var(--color-text-muted)", live: false },
};

function EventRow({ event }: { event: ResearchEvent }) {
  const line = describeResearchEvent(event);
  const Icon = KIND_ICON[line.kind];
  const href = safeExternalHref(line.url);
  return (
    <li data-testid="timeline-event" data-seq={event.seq} data-event-type={event.eventType} data-tone={line.tone} className="flex gap-3 border-b border-wg-line py-2.5 text-sm last:border-b-0">
      <Icon size={16} aria-hidden className={cn("mt-0.5 shrink-0", TONE_CLASS[line.tone])} />
      <div className="min-w-0 flex-1">
        <p className="break-words">
          <span className="font-medium">{line.headline}</span>
          {line.subject === "" ? null : (
            <>
              {" "}
              <span data-field="subject">{line.subject}</span>
            </>
          )}
        </p>
        {line.url === undefined ? null : (
          <p className="text-xs break-all text-wg-muted" data-field="url">
            {href === null ? (
              line.url
            ) : (
              <a href={href} target="_blank" rel="noopener noreferrer" className="text-wg-primary hover:underline">
                {line.url}
              </a>
            )}
          </p>
        )}
        <p className="mt-0.5 text-xs text-wg-muted">
          {[...line.meta, isFlowStepId(event.step) ? `第 ${stepNumber(event.step)} 步「${FLOW_STEP_LABEL[event.step]}」` : ""].filter((part) => part !== "").join(" · ")}
        </p>
      </div>
      <time {...(event.occurredAt === "" ? {} : { dateTime: event.occurredAt })} className="shrink-0 text-xs text-wg-muted">
        {formatInstant(event.occurredAt)}
      </time>
    </li>
  );
}

export function EvidenceTimeline({ researchId, EventSourceCtor, syncRetryMs, refreshDebounceMs, backoffMs }: { researchId: string } & TimelineOptions) {
  const timeline = useResearchTimeline(researchId, { EventSourceCtor, syncRetryMs, refreshDebounceMs, backoffMs });
  const [showAll, setShowAll] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);
  const stick = useRef(true);
  const { view, connection } = timeline;
  const shown = showAll ? view.visible : view.visible.slice(-TIMELINE_RENDER_LIMIT);
  const folded = view.visible.length - shown.length;

  // 使用者停在最底時，新事件到了就跟著捲；往上翻看舊事件時不搶捲動
  useEffect(() => {
    const el = scroller.current;
    if (el !== null && stick.current) el.scrollTop = el.scrollHeight;
  }, [shown.length]);

  if (!timeline.ready) {
    if (timeline.loadError !== null) return <ErrorState error={timeline.loadError} title="無法載入研究動態" onRetry={timeline.reload} />;
    return (
      <div aria-busy="true" aria-label="研究動態載入中" role="status">
        <Skeleton className="h-40 rounded-lg" />
      </div>
    );
  }

  const meta = CONNECTION_META[connection];
  return (
    <section
      data-testid="research-timeline"
      aria-label="研究動態"
      data-connection={connection}
      data-latency-p95-ms={timeline.latency.p95 ?? undefined}
      data-latency-measured={timeline.latency.measured}
      data-latency-unmeasured={timeline.latency.unmeasured}
      className="flex flex-col gap-2"
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-wg-muted">
        <span role="status" data-testid="timeline-connection" className="inline-flex items-center gap-1.5">
          <StatusDot color={meta.color} size={8} live={meta.live} />
          {meta.label}
        </span>
        <span data-testid="timeline-count">共 {view.visible.length} 筆事件</span>
        {connection === "failed" ? (
          <Button size="sm" variant="ghost" onClick={timeline.reconnect}>
            重新連線
          </Button>
        ) : null}
      </div>
      {timeline.syncing ? (
        <p role="status" data-testid="timeline-sync" className="rounded-md border border-wg-line bg-wg-surface px-3 py-2 text-sm text-wg-muted">
          正在與資料庫同步動態（補齊缺漏的事件），完成前不顯示缺口之後的事件…
        </p>
      ) : null}
      {timeline.syncFailed ? (
        <div role="alert" data-testid="timeline-sync-failed" className="flex flex-wrap items-center gap-3 rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm">
          <span className="min-w-0 flex-1 text-wg-accent">
            動態與資料庫尚未同步：缺少第 {view.gapFrom ?? view.visible.length + 1} 筆起的事件，缺口之後的 {view.held} 筆事件先不顯示。
          </span>
          <Button size="sm" variant="ghost" onClick={timeline.resync}>
            重新同步
          </Button>
        </div>
      ) : null}
      {view.visible.length === 0 ? (
        <EmptyState title="還沒有動態" description="啟動深研後，取得的來源、抽取的證據列與 run 狀態會即時出現在這裡。" />
      ) : (
        <div
          ref={scroller}
          role="log"
          aria-label="研究動態清單"
          tabIndex={0}
          onScroll={(event) => {
            const el = event.currentTarget;
            stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 48;
          }}
          className="max-h-[420px] overflow-y-auto rounded-md border border-wg-line bg-wg-surface px-4"
        >
          {folded > 0 ? (
            <div className="border-b border-wg-line py-2 text-xs text-wg-muted">
              較早的 {folded} 筆事件已折疊{" "}
              <button type="button" onClick={() => setShowAll(true)} className="cursor-pointer text-wg-primary hover:underline">
                顯示全部 {view.visible.length} 筆
              </button>
            </div>
          ) : null}
          <ol data-testid="timeline-list">
            {shown.map((event) => (
              <EventRow key={event.seq} event={event} />
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
