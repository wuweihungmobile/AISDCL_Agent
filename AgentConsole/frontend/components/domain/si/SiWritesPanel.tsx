"use client";

/**
 * Console 寫入對帳面板（P2b；TCS-SelfImprovingDecide-P2b W21；PRD AC-SI-35-5；決定重送去重 TCS-SelfImprovingDecideDedupe W-D4）：**只對 ADMIN 渲染**
 * （非 ADMIN 零控件、零 `console-writes` 請求、無待入帳或警示字樣）。
 * 資料＝`GET /api/v1/si/console-writes`：Console 稽核表的列（只有 kind、決定動詞、對象、time 等，沒有 body 與 mac），與帳本的對帳結果在 backend 一次全量做
 * （前端分頁只載入部分帳本，逐頁判會誤報待入帳），這裡只顯示：
 *  - 待入帳：稽核檔已落地、帳本還沒有同 `auditRef` 的事件或觀察列標記，且沒有被取代；每列可展開看入帳指令（PowerShell 與 POSIX，兩段相同）；
 *  - 已被取代（預設收合的群組，待入帳清單之後）：同一張卡的同一決定（同對象、同 digest、同動詞）已由另一份稽核檔入帳——主機端只能入帳其中一份，其餘的列在帳本
 *    永遠沒有對應項；它們仍是 `ingested=false`（不冒充已入帳），但不再當成待入帳、也沒有入帳指令，只列出動詞、對象、時間、編號與取代者的編號；
 *  - 紅色警示：帳本有 carrier 為 console 的項目、Console 稽核表卻沒有對應列（`role="alert"`，逐項 auditRef、kind、對象）；
 *  - 量不到：對帳回 NOT-EVALUABLE（Bridge 不可用、逾時、頁數超限）時顯示原因逐字，**不得**顯示「無待入帳」，也不渲染被取代群組——量不到不是沒有；
 *  - 無待入帳：只有對帳成功（ok）且沒有待入帳也沒有 orphans 時才顯示（被取代的列不算待入帳，也不影響這個判定）。
 * 沒有任何刪除、移除、清除控件（稽核表列不可改；補償刪除只由 backend 在確定未落檔時做；被取代的稽核檔仍在稽核目錄，這裡只標示、不處置）。
 * 帳本字串一律以文字節點渲染。
 */
import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useSiConsoleWrites } from "@/lib/api/queries";
import { SI_CONSOLE_WRITES_LIMIT, decideKindLabel, notEvaluableText, pendingWrites, siWriteKindLabel, supersededWrites, writeSubjectText } from "@/lib/domain/si";
import type { SiConsoleWrite } from "@/lib/api/types";
import { ApiError } from "@/lib/api/client";
import { RECENT_INGESTED_SHOWN, SI_FLOW_TEXTS as T, fillText, joinHostRejections, labelOfIngestStatus, maskCredentials, reasonText, relativeMinutesText, type Join } from "@/lib/domain/siFlow";
import { SiError, SiIngestCommands, SiLoading } from "./siParts";
import { usePatrolView, type PatrolView } from "./usePatrolView";

const SHELL = "mb-5 rounded-lg border border-wg-line bg-wg-surface px-5 py-4";

/** 巡邏回報量不到的原因（面板層級說一次）：四種各自一句，不把「量不到」畫成「主機還沒處理」。 */
function unavailableWhy(error: unknown): string {
  const cause = error instanceof ApiError && error.status === 503 && typeof error.details?.cause === "string" ? error.details.cause : null;
  if (cause === "report_dir_unset") return T.ingestWhyUnset;
  if (cause === "report_missing") return T.ingestWhyMissing;
  if (cause === "report_invalid" || cause === "report_unreadable") return T.ingestWhyBad;
  return T.ingestWhyOther;
}

/** 單一待入帳列的入帳結果（只對未入帳列、以稽核編號結合快照 `ingest[]`；主機回報的原因逐字顯示）。 */
function IngestOutcome({ join }: { join: Join | null }) {
  if (join === null)
    return (
      <p data-testid="si-ingest-not-yet" className="mt-1 text-sm text-wg-muted">
        {T.ingestNotYet}
      </p>
    );
  const status = labelOfIngestStatus(join.status);
  const statusText = status.known ? status.text : fillText(T.ingestUnknownStatusFmt, { value: typeof join.status === "string" && join.status !== "" ? join.status : T.unmeasurable });
  const code = typeof join.code === "string" && join.code !== "" ? join.code : null;
  return (
    <div data-testid="si-ingest-outcome" className="mt-1 text-sm">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="rounded-md border border-wg-alert-border bg-wg-alert-bg px-2 py-0.5 text-xs text-wg-warning-text">{statusText}</span>
        {code ? <code className="font-mono text-xs">{code}</code> : null}
      </div>
      <p className="mt-0.5 break-words whitespace-pre-wrap">{maskCredentials(reasonText(join.code, join.text))}</p>
      <p className="mt-0.5 text-wg-muted">{join.mode === "human" ? T.ingestHuman : join.mode === "auto" ? T.ingestAuto : T.ingestUnsure}</p>
    </div>
  );
}

/** 最近已入帳（常駐顯示、不加展開鈕；待入帳清單之下直接列時間最新的 `RECENT_INGESTED_SHOWN` 筆；段內沒有按鈕，TCS 勘誤 E-3）。 */
function RecentIngested({ items }: { items: ReadonlyArray<SiConsoleWrite> }) {
  const done = items.filter((w) => w.ingested === true);
  if (done.length === 0) return null;
  const ms = (t: string) => {
    const v = Date.parse(t);
    return Number.isNaN(v) ? 0 : v;
  };
  const shown = [...done].sort((a, b) => ms(b.time) - ms(a.time)).slice(0, RECENT_INGESTED_SHOWN);
  return (
    <section data-testid="si-recent-ingested" aria-label={fillText(T.recentIngestedFmt, { n: done.length })} className="mt-3">
      <h3 className="text-sm font-semibold">{fillText(T.recentIngestedFmt, { n: done.length })}</h3>
      <p className="text-xs text-wg-muted">{fillText(T.recentIngestedNote, { shown: RECENT_INGESTED_SHOWN })}</p>
      <ul>
        {shown.map((w) => (
          <li key={w.auditRef} data-testid={`si-ingested-${w.auditRef}`} className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-wg-line py-2 text-sm last:border-b-0">
            <span className="rounded-md border border-wg-line px-2 py-0.5 text-xs">{T.ingestedBadge}</span>
            <span>
              {`${siWriteKindLabel(w.kind)} `}
              <code className="font-mono text-xs">{w.kind}</code>
            </span>
            <span className="font-mono">{writeSubjectText(w.subjectId)}</span>
            <time dateTime={w.time} className="text-wg-muted">
              {w.time}
            </time>
            <code className="font-mono text-xs break-all text-wg-muted">{w.auditRef}</code>
          </li>
        ))}
      </ul>
    </section>
  );
}
/** 面板層級的回報說明：量不到（四種原因各一句）或已過時（原因可能已改變）。 */
function PatrolNote({ patrol }: { patrol: PatrolView }) {
  const { q, freshness } = patrol;
  if (q.isError)
    return (
      <p data-testid="si-ingest-unavailable" className="mt-3 text-sm text-wg-warning-text">
        {fillText(T.ingestUnavailableFmt, { why: unavailableWhy(q.error) })}
      </p>
    );
  if (freshness?.state === "stale") {
    const age = freshness.ageMinutes === null ? null : Math.round(freshness.ageMinutes);
    return (
      <p data-testid="si-ingest-stale" className="mt-3 text-sm text-wg-warning-text">
        {fillText(T.ingestStaleFmt, { ago: relativeMinutesText(age) })}
      </p>
    );
  }
  return null;
}

/** 決定動詞（中文標籤加原文，例 `核准 approve`）；`dkind` 為 null（非 decide 列或看不出動詞）時不渲染。 */
function Dkind({ auditRef, dkind }: { auditRef: string; dkind: string | null | undefined }) {
  if (dkind === null || dkind === undefined || dkind === "") return null;
  const label = decideKindLabel(dkind);
  return (
    <span data-testid={`si-dkind-${auditRef}`}>
      {label === dkind ? null : `${label} `}
      <code className="font-mono text-xs">{dkind}</code>
    </span>
  );
}

export function SiWritesPanel() {
  const q = useSiConsoleWrites();
  const patrol = usePatrolView();
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [supersededOpen, setSupersededOpen] = useState(false);

  const frame = (children: React.ReactNode) => (
    <section id="si-writes-panel" tabIndex={-1} data-testid="si-writes-panel" aria-label="Console 寫入對帳" className={SHELL}>
      <h2 className="text-base font-semibold">Console 寫入（待入帳與對帳）</h2>
      <p className="mt-0.5 text-[13px] text-wg-muted">決定與新增觀察只落稽核檔，由主機端 CLI 驗簽入帳；入帳前它們尚未寫進帳本。</p>
      {children}
    </section>
  );

  if (q.isError) return frame(<SiError error={q.error} onRetry={() => void q.refetch()} />);
  if (q.isPending) return frame(<SiLoading what="對帳" />);

  const { items, truncated, orphans, reconcile } = q.data;
  const evaluable = reconcile.status === "ok";
  // 量不到時整份清單不可信：待入帳、被取代與警示都不列、也不說「無」
  const pending = evaluable ? pendingWrites(items) : [];
  const superseded = evaluable ? supersededWrites(items) : [];
  const orphanList = evaluable ? (orphans ?? []) : [];
  // 入帳結果：只對未入帳的待入帳列、以稽核編號結合巡邏快照（W-F10）；快照量不到時各列維持「待入帳」、面板層級說一次原因
  const joins = new Map(joinHostRejections(pending, patrol.report).map((j) => [j.auditRef, j.join] as const));
  const reportUsable = patrol.report !== null && !patrol.q.isError;

  return frame(
    <>
      {evaluable ? null : (
        <p data-testid="si-reconcile-ne" className="mt-3 rounded-md border border-wg-alert-border bg-wg-alert-bg px-3 py-2 text-sm text-wg-warning-text">
          {`對帳${notEvaluableText(reconcile.reason)}。待入帳與警示無法判定，這不代表沒有。`}
        </p>
      )}

      {orphanList.length > 0 ? (
        <div data-testid="si-write-alerts" role="alert" className="mt-3 rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm">
          <p className="font-semibold text-wg-accent">對帳警示：帳本有 Console 載體的項目，Console 的稽核表卻沒有對應的列</p>
          <ul className="mt-1 list-disc pl-5">
            {orphanList.map((o) => (
              <li key={o.auditRef} data-testid={`si-orphan-${o.auditRef}`} className="break-all">
                <code className="font-mono">{o.auditRef}</code>
                {`｜${o.kind}｜${writeSubjectText(o.subject)}`}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {evaluable && pending.length > 0 ? <PatrolNote patrol={patrol} /> : null}

      {pending.length > 0 ? (
        <ul data-testid="si-pending-list" className="mt-3">
          {pending.map((w) => {
            const expanded = open[w.auditRef] === true;
            const panelId = `si-pending-commands-${w.auditRef}`;
            return (
              <li key={w.auditRef} data-testid={`si-pending-${w.auditRef}`} className="border-b border-wg-line py-2 last:border-b-0">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                  <span className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-2 py-0.5 text-xs text-wg-accent">待入帳</span>
                  <span>
                    {`${siWriteKindLabel(w.kind)} `}
                    <code className="font-mono text-xs">{w.kind}</code>
                  </span>
                  <Dkind auditRef={w.auditRef} dkind={w.dkind} />
                  <span>
                    <span className="text-wg-muted">{"對象："}</span>
                    <span className="font-mono">{writeSubjectText(w.subjectId)}</span>
                  </span>
                  <time dateTime={w.time} className="text-wg-muted">
                    {w.time}
                  </time>
                  <code className="font-mono text-xs break-all text-wg-muted">{w.auditRef}</code>
                  <Button variant="ghost" size="sm" aria-expanded={expanded} aria-controls={panelId} onClick={() => setOpen((prev) => ({ ...prev, [w.auditRef]: !expanded }))}>
                    入帳指令
                  </Button>
                </div>
                {reportUsable ? <IngestOutcome join={joins.get(w.auditRef) ?? null} /> : null}
                {expanded ? (
                  <div id={panelId} className="mt-2">
                    <SiIngestCommands kind={w.kind} subject={w.subjectId} auditRef={w.auditRef} />
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}

      {superseded.length > 0 ? (
        <div data-testid="si-superseded-list" className="mt-3">
          <Button
            variant="ghost"
            size="sm"
            iconLeft={supersededOpen ? ChevronDown : ChevronRight}
            aria-expanded={supersededOpen}
            aria-controls="si-superseded-items"
            data-testid="si-superseded-toggle"
            onClick={() => setSupersededOpen((prev) => !prev)}
          >
            {`另有 ${superseded.length} 筆已被取代（同一張卡的同一決定已由其他稽核檔入帳）`}
          </Button>
          {supersededOpen ? (
            <ul id="si-superseded-items" className="mt-1">
              {superseded.map((w) => (
                <li key={w.auditRef} data-testid={`si-superseded-${w.auditRef}`} className="border-b border-wg-line py-2 last:border-b-0">
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                    <Dkind auditRef={w.auditRef} dkind={w.dkind} />
                    <span>
                      <span className="text-wg-muted">{"對象："}</span>
                      <span className="font-mono">{writeSubjectText(w.subjectId)}</span>
                    </span>
                    <time dateTime={w.time} className="text-wg-muted">
                      {w.time}
                    </time>
                    <code className="font-mono text-xs break-all text-wg-muted">{w.auditRef}</code>
                    <span data-testid={`si-superseded-by-${w.auditRef}`} className="font-mono text-xs break-all text-wg-muted">
                      {`取代者：${w.supersededBy}`}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {evaluable ? <RecentIngested items={items} /> : null}

      {evaluable && pending.length === 0 && orphanList.length === 0 ? (
        <p data-testid="si-writes-empty" className="mt-3 text-sm text-wg-muted">
          {`無待入帳${truncated ? `（僅涵蓋最新 ${SI_CONSOLE_WRITES_LIMIT} 筆稽核列）` : ""}`}
        </p>
      ) : null}

      {truncated ? (
        <p data-testid="si-writes-truncated" className="mt-2 text-xs text-wg-muted">
          {`僅顯示最新 ${SI_CONSOLE_WRITES_LIMIT} 筆稽核列；更舊的列未載入，不在上面的待入帳與警示判斷內。`}
        </p>
      ) : null}
    </>,
  );
}
