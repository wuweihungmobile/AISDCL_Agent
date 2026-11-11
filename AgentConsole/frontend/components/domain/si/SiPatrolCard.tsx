"use client";

/**
 * 巡邏狀態卡（TCS-SiFlowVisibility AC-966-11、12；W-F5、W-F7、W-F13）：掛在自我進化頁（所有角色），回答「巡邏器有沒有在跑、每個提案卡在哪、
 * 為什麼沒有啟動運轉、推送到哪了」。資料＝`GET /api/v1/si/patrol`（主機每個心跳寫的快照；Console 只讀）。
 *  - **畫面不能說謊**：快照過時（`usePatrolView` 含每分鐘本地重算）就明說，不顯示成正常；快照缺席、未掛載、壞檔各有各的畫面，不混為一談。
 *  - **量不到不是沒有**：段落缺席／null／錯型別一律「…量不到」，只有真的空陣列才說「沒有」；暫停時空陣列不代表沒事。
 *  - 白話字一律逐字取自主機的 `text` 欄（缺席才用保底句）；Console 不持有任何原因碼對照表，也不認得根層之後新增的碼。
 *  - 第二波才有的值（`freeze` 等運轉目的、`runs.queued`）不當成已知：目的顯示未知值、`queued` 完全不渲染。
 *  - 只讀：沒有推送按鈕、沒有任何寫入或 mutation；全部純文字節點。
 */
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { useSiProposalsCache } from "@/lib/api/queries";
import type { SiProposal } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { siErrorParts } from "@/lib/domain/si";
import {
  SI_FLOW_TEXTS as T,
  effectiveNowMs,
  fillText,
  labelOfWho,
  liveRunLine,
  maskCredentials,
  pushView,
  reasonText,
  relativeMinutesText,
  scheduleView,
  sectionState,
  waitingView,
} from "@/lib/domain/siFlow";
import { cn } from "@/lib/utils";
import { SiError, SiLoading } from "./siParts";
import { usePatrolView, type PatrolView } from "./usePatrolView";

type Rec = Record<string, unknown>;
const isRec = (v: unknown): v is Rec => typeof v === "object" && v !== null && !Array.isArray(v);
const str = (v: unknown): string | null => (typeof v === "string" && v !== "" ? v : null);

const SHELL = "mb-5 rounded-lg border border-wg-line bg-wg-surface px-5 py-4";

function Block({ title, testId, children }: { title: string; testId: string; children: React.ReactNode }) {
  return (
    <section data-testid={testId} className="mt-4">
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="mt-1 text-sm">{children}</div>
    </section>
  );
}

const Muted = ({ children, testId }: { children: React.ReactNode; testId?: string }) => (
  <p data-testid={testId} className="text-wg-muted">
    {children}
  </p>
);

function Code({ children }: { children: React.ReactNode }) {
  return <code className="font-mono text-xs break-all text-wg-muted">{children}</code>;
}

/** 失敗畫面：缺席、未掛載、壞檔各一種；其餘（502、504、nonzero_rc…）走既有的 SiError。 */
function PatrolFailure({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const { cause, detail } = siErrorParts(error);
  const unavailable = error instanceof ApiError && error.status === 503;
  if (unavailable && cause === "report_missing") {
    return (
      <div data-testid="si-patrol-missing" className="mt-2 text-sm">
        <p className="font-semibold">{T.patrolMissingTitle}</p>
        <ul className="mt-1 list-disc pl-5">
          {T.patrolMissingReasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
        <p className="mt-1 text-wg-muted">{T.patrolMissingHint}</p>
      </div>
    );
  }
  if (unavailable && cause === "report_dir_unset") {
    return (
      <div data-testid="si-patrol-unmounted" className="mt-2 text-sm">
        <p className="font-semibold">{T.patrolUnmountedTitle}</p>
        <p className="mt-1 text-wg-muted">{T.patrolUnmountedNote}</p>
      </div>
    );
  }
  if (unavailable && (cause === "report_invalid" || cause === "report_unreadable")) {
    return (
      <div data-testid="si-patrol-bad-file" className="mt-2 flex flex-col gap-1.5 text-sm">
        <p className="font-semibold">{T.patrolBadFileTitle}</p>
        <code data-testid="si-patrol-cause" className="font-mono text-xs">
          {cause}
        </code>
        {detail ? (
          <code data-testid="si-patrol-detail" className="font-mono text-xs break-all whitespace-pre-wrap">
            {detail}
          </code>
        ) : null}
        <div>
          <Button variant="ghost" size="sm" data-testid="si-retry" onClick={onRetry}>
            {T.retry}
          </Button>
        </div>
      </div>
    );
  }
  return <SiError error={error} onRetry={onRetry} />;
}

function HeaderBlock({ view, paused, pauseUnknown }: { view: PatrolView; paused: boolean; pauseUnknown: boolean }) {
  const { report, freshness, readAt } = view;
  const r = report as Rec;
  const f = freshness!;
  const generatedAt = str(r.generatedAt);
  let label: string | null = null;
  if (paused) label = T.patrolPaused;
  else if (pauseUnknown) label = T.patrolPauseUnknown;
  else if (f.state === "fresh") label = T.patrolOk;
  else if (f.state === "stale") label = T.patrolStaleLabel;
  const age = f.ageMinutes;
  const readAtText = str(readAt);
  return (
    <div data-testid="si-patrol-header" className="mt-2 flex flex-col gap-1 text-sm">
      {label ? (
        <p
          data-testid="si-patrol-state"
          className={cn("w-fit rounded-md border px-2 py-0.5 font-semibold", f.state === "stale" ? "border-wg-alert-border bg-wg-alert-bg text-wg-warning-text" : "border-wg-line")}
        >
          {label}
        </p>
      ) : null}
      {f.state === "unknown-time" || generatedAt === null ? (
        <p>{T.patrolHeartbeatUnknown}</p>
      ) : (
        <p>
          {fillText(T.patrolHeartbeat, { ago: "" })}
          <time dateTime={generatedAt}>{relativeMinutesText(age === null ? null : Math.round(age))}</time>
        </p>
      )}
      {typeof r.heartbeatMinutes === "number" && Number.isInteger(r.heartbeatMinutes) && r.heartbeatMinutes > 0 ? (
        <p className="text-wg-muted">{fillText(T.patrolPeriod, { n: r.heartbeatMinutes })}</p>
      ) : null}
      {f.state === "unknown-period" ? <p data-testid="si-patrol-no-period">{T.patrolNoPeriod}</p> : null}
      {f.state === "clock-skew" ? <p data-testid="si-patrol-skew">{T.patrolClockSkew}</p> : null}
      <p className="text-xs text-wg-muted">
        {fillText(T.patrolReadAt, { time: readAtText ?? T.unmeasurable })}
        {f.usedClientClock ? T.patrolEstimated : ""}
      </p>
      {f.state === "stale" ? (
        <div role="status" data-testid="si-patrol-stale" className="rounded-md border border-wg-alert-border bg-wg-alert-bg px-3 py-2 text-wg-warning-text">
          <p>{fillText(T.patrolStaleWarn, { limit: f.limitMinutes ?? "", period: typeof r.heartbeatMinutes === "number" ? r.heartbeatMinutes : "" })}</p>
          <p className="mt-0.5">{fillText(T.patrolStaleAgo, { ago: relativeMinutesText(age === null ? null : Math.round(age)) })}</p>
        </div>
      ) : null}
    </div>
  );
}

function PropsBlock({ report, paused, onOpen, loaded }: { report: Rec; paused: boolean; onOpen?: (p: SiProposal) => void; loaded: ReadonlyMap<string, SiProposal> }) {
  const props = report.props;
  const s = sectionState(props);
  return (
    <Block title={T.patrolPropsTitle} testId="si-patrol-props">
      {s === "unknown" ? <Muted>{T.patrolPropsMissing}</Muted> : null}
      {s === "empty" && !paused ? <Muted>{T.patrolPropsNone}</Muted> : null}
      {s === "items" ? (
        <ul data-testid="si-patrol-props-list" tabIndex={0} aria-label={T.propsScroll} className="flex max-h-72 flex-col gap-2 overflow-y-auto">
          {(props as unknown[]).map((p, i) => {
            const r = isRec(p) ? p : {};
            const id = str(r.id);
            const who = labelOfWho(r.who);
            const row = id === null ? undefined : loaded.get(id);
            return (
              <li key={`${id ?? "x"}-${i}`} data-testid={id ? `si-patrol-prop-${id}` : undefined} className="rounded-md border border-wg-line bg-wg-base px-3 py-2">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  {id === null ? (
                    <span>{T.unmeasurable}</span>
                  ) : onOpen && row ? (
                    <button type="button" className="cursor-pointer font-mono text-xs text-wg-primary-strong underline underline-offset-2" onClick={() => onOpen(row)}>
                      {id}
                    </button>
                  ) : (
                    <code className="font-mono text-xs">{id}</code>
                  )}
                  <span>{str(r.state) ?? T.propStateMissing}</span>
                  <span className="rounded-md border border-wg-line px-2 py-0.5 text-xs">{fillText(T.propWaitFmt, { who: who.text })}</span>
                </div>
                <p className="mt-1 break-words whitespace-pre-wrap">{maskCredentials(reasonText(r.code, r.text))}</p>
                {str(r.code) ? <Code>{str(r.code)}</Code> : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </Block>
  );
}

function RunsBlock({ report, effNow }: { report: Rec; effNow: number }) {
  const runs = isRec(report.runs) ? report.runs : null;
  const s = sectionState(runs?.live);
  return (
    <Block title={T.runsTitle} testId="si-patrol-runs">
      {s === "unknown" ? <Muted>{T.runsMissing}</Muted> : null}
      {s === "empty" ? <Muted>{T.runsNone}</Muted> : null}
      {s === "items" ? (
        <ul>
          {(runs?.live as unknown[]).map((run, i) => (
            <li key={i} className={cn("break-words", liveRunLine(run, effNow).known ? "" : "text-wg-warning-text")}>
              {liveRunLine(run, effNow).text}
            </li>
          ))}
        </ul>
      ) : null}
    </Block>
  );
}

function ScheduleBlock({ report }: { report: Rec }) {
  const runs = isRec(report.runs) ? report.runs : null;
  const waiting = waitingView(runs?.waiting);
  const hasSchedule = "schedule" in report;
  const sched = scheduleView(report.schedule, report.off);
  return (
    <Block title={T.scheduleTitle} testId="si-patrol-schedule">
      {!hasSchedule ? (
        <Muted>{T.scheduleMissing}</Muted>
      ) : sched.state !== "present" ? (
        <p>{sched.message}</p>
      ) : (
        <div className="flex flex-col gap-0.5">
          <p>{sched.enabledText}</p>
          <p className="break-words">
            {fillText(T.scheduleCurrentFmt, { text: sched.current.text })} {sched.current.code ? <Code>{sched.current.code}</Code> : null}
          </p>
          {sched.lastSkip ? (
            <>
              <p className="break-words">
                {sched.lastSkip.line} {sched.lastSkip.code ? <Code>{sched.lastSkip.code}</Code> : null}
              </p>
              {sched.lastSkip.note ? <p data-testid="si-patrol-skip-console">{sched.lastSkip.note}</p> : null}
            </>
          ) : null}
        </div>
      )}
      <div className="mt-2">
        {waiting.state === "items" ? (
          <ul>
            {waiting.items.map((w) => (
              <li key={w.key} className="break-words">
                {w.text} {w.code ? <Code>{w.code}</Code> : null}
              </li>
            ))}
          </ul>
        ) : (
          <Muted>{waiting.text}</Muted>
        )}
      </div>
    </Block>
  );
}

function StepsBlock({ report, isAdmin }: { report: Rec; isAdmin: boolean }) {
  const [open, setOpen] = useState(false);
  const steps = report.steps;
  const stepsState = sectionState(steps);
  const ingest = report.ingest;
  const ingestState = sectionState(ingest);
  const openWrites = () => {
    const el = document.getElementById("si-writes-panel");
    el?.scrollIntoView?.({ block: "start" });
    el?.focus();
  };
  return (
    <Block title={T.stepsTitle} testId="si-patrol-steps">
      {stepsState === "unknown" ? (
        <Muted>{T.stepsMissing}</Muted>
      ) : (
        <>
          <Button variant="ghost" size="sm" aria-expanded={open} aria-controls="si-patrol-steps-list" data-testid="si-patrol-steps-toggle" onClick={() => setOpen((v) => !v)}>
            {T.stepsTitle}
          </Button>
          {open ? (
            <ol id="si-patrol-steps-list" className="mt-1 list-decimal pl-5">
              {(steps as unknown[]).map((s, i) => {
                const r = isRec(s) ? s : {};
                return (
                  <li key={i} className="break-words">
                    {`${str(r.step) ?? T.unmeasurable}：${maskCredentials(str(r.result) ?? T.unmeasurable)}`}
                  </li>
                );
              })}
            </ol>
          ) : null}
        </>
      )}
      <div className="mt-1" data-testid="si-patrol-ingest">
        {ingestState === "unknown" ? <Muted>{T.ingestMissing}</Muted> : null}
        {ingestState === "empty" ? <Muted>{T.ingestNone}</Muted> : null}
        {ingestState === "items" ? (
          <div className="flex flex-wrap items-center gap-2">
            <p>{fillText(T.ingestSummaryFmt, { n: (ingest as unknown[]).length })}</p>
            {isAdmin ? (
              <Button variant="ghost" size="sm" data-testid="si-patrol-open-writes" onClick={openWrites}>
                {T.openWrites}
              </Button>
            ) : null}
          </div>
        ) : null}
      </div>
    </Block>
  );
}

function PushBlock({ report }: { report: Rec }) {
  const v = pushView(report.push);
  const prefix = v.known ? (v.tone === "ok" ? T.pushPrefixOk : v.tone === "warn" ? T.pushPrefixWarn : "") : "";
  return (
    <Block title={T.pushTitle} testId="si-patrol-push">
      <p className="text-xs text-wg-muted">{T.pushNote}</p>
      <p
        data-testid="si-patrol-push-text"
        data-tone={v.tone}
        className={cn("mt-1 break-words whitespace-pre-wrap", v.tone === "warn" ? "rounded-md border border-wg-alert-border bg-wg-alert-bg px-3 py-1.5 text-wg-warning-text" : "")}
      >
        {`${prefix}${v.text}`}
        {v.extras.length > 0 ? ` ${v.extras.join(" ")}` : ""}
        {v.time ? (
          <>
            {" "}
            <time dateTime={v.time}>{v.time}</time>
          </>
        ) : null}
      </p>
    </Block>
  );
}

export function SiPatrolCard({ onOpenProposal }: { onOpenProposal?: (proposal: SiProposal) => void }) {
  const { role } = useAuth();
  const view = usePatrolView();
  const cache = useSiProposalsCache();
  const { q, report, freshness } = view;

  const frame = (children: React.ReactNode) => (
    <section data-testid="si-patrol-card" aria-label={T.patrolTitle} className={SHELL}>
      <h2 className="text-base font-semibold">{T.patrolTitle}</h2>
      {children}
    </section>
  );

  if (q.isError) return frame(<PatrolFailure error={q.error} onRetry={() => void q.refetch()} />);
  if (q.isPending) return frame(<SiLoading what={T.patrolTitle} />);
  if (report === null || freshness === null) return frame(<p className="mt-2 text-sm text-wg-warning-text">{T.unmeasurable}</p>);

  const loaded = new Map<string, SiProposal>();
  for (const page of cache?.pages ?? []) for (const p of page.items) loaded.set(p.id, p);
  const off = report.off;
  const paused = off === true;
  const pauseUnknown = off !== undefined && off !== null && typeof off !== "boolean";
  const effNow = effectiveNowMs(view.readAt, view.receivedAtMs, view.nowMs);

  return frame(
    <>
      {report.truncated === true ? (
        <p data-testid="si-patrol-truncated" className="mt-2 text-sm text-wg-warning-text">
          {T.patrolTruncated}
        </p>
      ) : null}
      <HeaderBlock view={view} paused={paused} pauseUnknown={pauseUnknown} />
      <PropsBlock report={report} paused={paused} onOpen={onOpenProposal} loaded={loaded} />
      <RunsBlock report={report} effNow={effNow} />
      <ScheduleBlock report={report} />
      <StepsBlock report={report} isAdmin={role === "ADMIN"} />
      <PushBlock report={report} />
    </>,
  );
}
