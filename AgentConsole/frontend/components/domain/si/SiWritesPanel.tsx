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
import { SiError, SiIngestCommands, SiLoading } from "./siParts";

const SHELL = "mb-5 rounded-lg border border-wg-line bg-wg-surface px-5 py-4";

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
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [supersededOpen, setSupersededOpen] = useState(false);

  const frame = (children: React.ReactNode) => (
    <section data-testid="si-writes-panel" aria-label="Console 寫入對帳" className={SHELL}>
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
