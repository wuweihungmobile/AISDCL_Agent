"use client";

/**
 * 分流逐步進度（FR-R2P-11-3；TCS-ResearchToPRD-P1-20261107 AT-961-17-7）：以 `GET …/route` 的步驟列初始化，訂研究串流的 `research.route` 事件逐步更新（步驟名、狀態圖示與文字、耗時）；
 * 事件到達同時讓分流查詢重抓——事件只是「通知有變」，畫面的事實以 REST 為準（斷線、缺事件時由 REST 回補，不信任單一事件）。
 * 失敗步驟顯示脫敏後的原因（純文字）；已成功的步驟不顯示重試（重試鈕由 {@link RoutePanel} 持有，只對 ADMIN 開放）。
 * 連線出錯時只以一次延後重連（換新 token）處理，不做無限重試：REST 輪詢（`useResearchRoute` 對 RUNNING 每 5 秒重抓）才是保底。
 */
import { useQueryClient } from "@tanstack/react-query";
import { Check, CircleDot, Loader, MinusCircle, TriangleAlert, type LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { apiBase, getFreshAccessToken } from "@/lib/api/client";
import { qk } from "@/lib/api/queries";
import { READY_CLOSED, type EventSourceCtor, type EventSourceLike } from "@/lib/api/sse";
import type { ResearchRouteDecision, ResearchRouteStep, ResearchRouteStepStatus } from "@/lib/api/types";
import { buildResearchStreamUrl, routeStepLabel, routeStepStatusLabel } from "@/lib/domain/research";
import { cn } from "@/lib/utils";

const ICON: Readonly<Record<string, LucideIcon>> = { RUNNING: Loader, OK: Check, FAILED: TriangleAlert, SKIPPED: MinusCircle, COMPENSATED: CircleDot };
const RETRY_AFTER_MS = 3000;

/** 步驟耗時（秒，一位小數）；沒有結束時間或時間解不出回「—」。 */
export function stepDuration(step: Pick<ResearchRouteStep, "startedAt" | "finishedAt">): string {
  if (step.finishedAt === null) return "—";
  const ms = Date.parse(step.finishedAt) - Date.parse(step.startedAt);
  return Number.isFinite(ms) && ms >= 0 ? `${(ms / 1000).toFixed(1)} 秒` : "—";
}

export function RouteStepsTimeline({
  researchId,
  route,
  streaming = true,
  EventSourceCtor,
}: {
  researchId: string;
  /** 最新分流列（含步驟）；尚無（確認執行剛送出、列還沒寫入）傳 null */
  route: ResearchRouteDecision | null;
  /** 為假時不連串流（唯讀摘要用） */
  streaming?: boolean;
  /** 測試注入；預設瀏覽器的 EventSource */
  EventSourceCtor?: EventSourceCtor;
}) {
  const qc = useQueryClient();
  const [live, setLive] = useState<Record<number, ResearchRouteStepStatus>>({});

  useEffect(() => {
    if (!streaming) return;
    const found = EventSourceCtor ?? (typeof EventSource === "undefined" ? null : (EventSource as unknown as EventSourceCtor));
    if (found === null) return;
    const Source: EventSourceCtor = found;
    let stopped = false;
    let source: EventSourceLike | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const onRoute = (message: MessageEvent) => {
      let data: unknown;
      try {
        data = JSON.parse(String(message.data));
      } catch {
        return;
      }
      const payload = typeof data === "object" && data !== null && "payload" in data ? (data as { payload: unknown }).payload : data;
      if (typeof payload === "object" && payload !== null) {
        const { stepNo, status } = payload as { stepNo?: unknown; status?: unknown };
        if (typeof stepNo === "number" && typeof status === "string") setLive((prev) => ({ ...prev, [stepNo]: status as ResearchRouteStepStatus }));
      }
      void qc.invalidateQueries({ queryKey: qk.researchRoute(researchId) });
    };

    async function connect(force: boolean) {
      if (stopped) return;
      const token = await getFreshAccessToken({ force });
      if (stopped || token === null) return;
      const es = new Source(buildResearchStreamUrl(apiBase(), researchId, token));
      source = es;
      es.addEventListener("research.route", onRoute);
      es.onerror = () => {
        if (stopped || source !== es) return;
        void qc.invalidateQueries({ queryKey: qk.researchRoute(researchId) });
        if (es.readyState === READY_CLOSED && timer === null) {
          source = null;
          timer = setTimeout(() => {
            timer = null;
            void connect(true);
          }, RETRY_AFTER_MS);
        }
      };
    }
    void connect(false);
    return () => {
      stopped = true;
      if (timer !== null) clearTimeout(timer);
      source?.close();
    };
  }, [researchId, streaming, EventSourceCtor, qc]);

  const steps = route?.steps ?? [];
  if (steps.length === 0) {
    return (
      <p data-testid="route-steps-empty" role="status" className="text-sm text-wg-muted">
        分流進行中，等待第一個步驟回報…
      </p>
    );
  }
  return (
    <ol data-testid="route-steps" aria-label="分流步驟進度" className="flex flex-col gap-2">
      {steps.map((step) => {
        const status = live[step.stepNo] ?? step.status;
        const Icon = ICON[status] ?? CircleDot;
        const failed = status === "FAILED";
        return (
          <li
            key={step.stepNo}
            data-testid={`route-step-${step.stepNo}`}
            data-status={status}
            className={cn("flex flex-col gap-1 rounded-md border px-3 py-2 text-sm", failed ? "border-wg-draft-border bg-wg-draft-bg" : "border-wg-line")}
          >
            <span className="flex flex-wrap items-center gap-2">
              <Icon size={16} aria-hidden className={failed ? "text-wg-accent" : undefined} />
              <span className="font-semibold">{routeStepLabel(step.step)}</span>
              <span className="text-xs text-wg-muted">{routeStepStatusLabel(status)}</span>
              <span className="text-xs text-wg-muted">耗時 {stepDuration(step)}</span>
            </span>
            {failed && step.stderrTail !== "" ? (
              <span data-testid="route-step-reason" className="whitespace-pre-wrap break-all font-mono text-[13px]">
                失敗原因：{step.stderrTail}
              </span>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
