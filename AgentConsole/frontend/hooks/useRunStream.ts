"use client";

/**
 * useRunStream(runId)：把一個執行批次的兩條 SSE（/logs、/metrics）接進 React（契約 §2、§2.8）。
 *  - 連線、去重、斷線回補、401 換 token、終態收工都在 lib/api/sse.ts 的 RunChannel；這裡只做 React 接線。
 *  - 事件先進佇列、每 FLUSH_MS 一批：重播（tail 200）一次湧入幾百則時，只重繪一次。
 *  - 批次本身的進度／狀態／Token／待審核項：直接修補 TanStack Query 快取裡的 ExecutionRunDetail（patchRunDetail），
 *    畫面只讀快取一份資料；需要以伺服器為準的（終態、審核項、告警）合併成一次重抓（refreshPlan）。
 *  - 日誌行與任務即時狀態只存在串流：放在 hook 內的 reducer（LiveState）。
 *  - 離頁（unmount）或換批次：兩條連線都關閉、計時器清掉；之後不再有任何事件。
 *  - 串流已收工但 REST 說批次還沒結束（restore 讓終態 run 重新執行）：自動重新連線（最多 MAX_REVIVES 次）。
 */
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";

import { getExecution, listExecutionSteps } from "@/lib/api/endpoints";
import { STEPS_MAX_PAGES, STEPS_PAGE_SIZE, invalidateRuns, qk } from "@/lib/api/queries";
import { RunChannel, combineStreamStates, defaultChannelDeps, shouldReviveStream, type EventSourceCtor, type RunStreamEvent, type StreamKind, type StreamState } from "@/lib/api/sse";
import type { ExecutionRunDetail, RunStatus } from "@/lib/api/types";
import { initialLive, liveReducer, patchRunDetail, refreshPlan, stepToLogData, type LiveState } from "@/lib/domain/runLive";

/** 事件佇列的批次間隔（毫秒）。 */
export const FLUSH_MS = 80;
/** 事件之後向伺服器重抓的去抖（毫秒）：連續事件只重抓一次。 */
export const REFRESH_DEBOUNCE_MS = 400;
/** 串流收工但 REST 說還沒結束時，等多久再重連（毫秒），以及最多重連幾次。 */
export const REVIVE_DELAY_MS = 1500;
export const MAX_REVIVES = 5;

export type UseRunStreamOptions = {
  /** false＝不連線（未登入、沒選批次） */
  enabled?: boolean;
  /** REST 目前知道的批次狀態：串流收工但這裡說「還沒結束」就自動重連 */
  runStatus?: RunStatus | null;
  /** 測試注入；預設瀏覽器的 EventSource */
  EventSourceCtor?: EventSourceCtor;
};

export type RunStreamResult = {
  live: LiveState;
  /** 兩條串流合成的連線狀態（「SSE 串流」狀態點） */
  connection: StreamState;
  logsState: StreamState;
  metricsState: StreamState;
  /** 手動重新連線（restore 之後、或重試用盡後使用者按「重新連線」） */
  reconnect: () => void;
};

type States = { runId: string | null; logs: StreamState; metrics: StreamState };

export function useRunStream(runId: string | null | undefined, options: UseRunStreamOptions = {}): RunStreamResult {
  const { enabled = true, runStatus, EventSourceCtor } = options;
  const qc = useQueryClient();
  const id = runId ?? null;
  const active = enabled && id !== null;

  const [raw, dispatch] = useReducer(liveReducer, id, initialLive);
  const [states, setStates] = useState<States>({ runId: null, logs: "idle", metrics: "idle" });
  const channels = useRef<{ logs: RunChannel; metrics: RunChannel } | null>(null);
  const revives = useRef(0);

  useEffect(() => {
    if (!enabled || id === null) return;
    const ctor = EventSourceCtor ?? (typeof EventSource === "undefined" ? null : (EventSource as unknown as EventSourceCtor));
    if (!ctor) return; // 沒有 EventSource（SSR 或極舊瀏覽器）：只靠 REST 輪詢

    let alive = true;
    const queue: RunStreamEvent[] = [];
    let flushTimer: ReturnType<typeof setTimeout> | null = null;
    let refreshTimer: ReturnType<typeof setTimeout> | null = null;
    let pendingPlan = { detail: false, dag: false, notifications: false, runs: false };

    const refresh = () => {
      refreshTimer = null;
      if (!alive) return;
      const plan = pendingPlan;
      pendingPlan = { detail: false, dag: false, notifications: false, runs: false };
      if (plan.runs) void invalidateRuns(qc);
      else {
        if (plan.detail) void qc.invalidateQueries({ queryKey: qk.execution(id) });
        if (plan.notifications) void qc.invalidateQueries({ queryKey: ["notifications"] });
      }
      if (plan.dag) void qc.invalidateQueries({ queryKey: qk.dag(id) });
    };

    const flush = () => {
      flushTimer = null;
      if (!alive || queue.length === 0) return;
      const batch = queue.splice(0, queue.length);
      dispatch({ type: "events", runId: id, events: batch });
      qc.setQueryData<ExecutionRunDetail>(qk.execution(id), (old) => (old ? batch.reduce<ExecutionRunDetail>(patchRunDetail, old) : old));
      const plan = refreshPlan(batch);
      if (plan.detail || plan.dag || plan.notifications || plan.runs) {
        pendingPlan = {
          detail: pendingPlan.detail || plan.detail,
          dag: pendingPlan.dag || plan.dag,
          notifications: pendingPlan.notifications || plan.notifications,
          runs: pendingPlan.runs || plan.runs,
        };
        if (!refreshTimer) refreshTimer = setTimeout(refresh, REFRESH_DEBOUNCE_MS);
      }
    };

    const push = (event: RunStreamEvent) => {
      queue.push(event);
      if (!flushTimer) flushTimer = setTimeout(flush, FLUSH_MS);
    };

    const deps = defaultChannelDeps(
      {
        // 連線被瀏覽器放棄時問一次 REST：順便讓 apiRequest 處理 401 換新，且把最新批次詳情寫回快取
        fetchRunStatus: async () => {
          const detail = await qc.fetchQuery({
            queryKey: qk.execution(id),
            queryFn: ({ signal }) => getExecution(id, { signal }),
            staleTime: 0,
          });
          return detail.status;
        },
        // 連續失敗兩次以上：以 afterSeq（嚴格大於）取步驟回補，轉成與 SSE log 同形的事件，走同一條去重路徑
        backfill: async (afterSeq) => {
          let after = afterSeq;
          for (let page = 0; page < STEPS_MAX_PAGES; page++) {
            const res = await listExecutionSteps(id, { size: STEPS_PAGE_SIZE, afterSeq: after > 0 ? after : undefined });
            for (const step of res.content) push({ name: "log", id: null, data: stepToLogData(step) });
            if (res.content.length < STEPS_PAGE_SIZE) break;
            after = res.content[res.content.length - 1].stepNumber;
          }
        },
      },
      ctor,
    );

    const make = (kind: StreamKind) =>
      new RunChannel({ runId: id, kind }, deps, {
        onEvent: push,
        onState: (state) => {
          if (!alive) return;
          setStates((cur) => {
            const base: States = cur.runId === id ? cur : { runId: id, logs: "idle", metrics: "idle" };
            return kind === "logs" ? { ...base, logs: state } : { ...base, metrics: state };
          });
        },
      });

    const pair = { logs: make("logs"), metrics: make("metrics") };
    channels.current = pair;
    pair.logs.start();
    pair.metrics.start();

    return () => {
      alive = false;
      if (flushTimer) clearTimeout(flushTimer);
      if (refreshTimer) clearTimeout(refreshTimer);
      pair.logs.close();
      pair.metrics.close();
      channels.current = null;
    };
  }, [enabled, id, qc, EventSourceCtor]);

  const mine = states.runId === id;
  const logsState: StreamState = active && mine ? states.logs : "idle";
  const metricsState: StreamState = active && mine ? states.metrics : "idle";

  // 串流收工但 REST 說批次還沒結束：稍後自動重連（restore 之後最常見）；兩條都連上就把嘗試次數歸零
  useEffect(() => {
    if (!active) return;
    if (logsState === "open" && metricsState === "open") {
      revives.current = 0;
      return;
    }
    if (!shouldReviveStream([logsState, metricsState], runStatus)) return;
    if (revives.current >= MAX_REVIVES) return;
    const timer = setTimeout(() => {
      revives.current += 1;
      channels.current?.logs.reconnect();
      channels.current?.metrics.reconnect();
    }, REVIVE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [active, logsState, metricsState, runStatus]);

  // 換批次：嘗試次數重新計
  useEffect(() => {
    revives.current = 0;
  }, [id]);

  const reconnect = useCallback(() => {
    revives.current = 0;
    channels.current?.logs.reconnect();
    channels.current?.metrics.reconnect();
  }, []);

  const live = useMemo(() => (raw.runId === id ? raw : initialLive(id)), [raw, id]);

  return {
    live,
    connection: combineStreamStates(logsState, metricsState),
    logsState,
    metricsState,
    reconnect,
  };
}
