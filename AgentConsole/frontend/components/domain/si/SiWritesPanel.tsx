"use client";

/**
 * Console 寫入對帳面板（P2b；TCS-SelfImprovingDecide-P2b W21；PRD AC-SI-35-5）：**只對 ADMIN 渲染**（非 ADMIN 零控件、零 `console-writes` 請求、無待入帳或警示字樣）。
 * 資料＝`GET /api/v1/si/console-writes`：Console 稽核表的列（只有 kind、對象、time 等，沒有 body 與 mac），與帳本的對帳結果在 backend 一次全量做（前端分頁只載入部分帳本，
 * 逐頁判會誤報待入帳），這裡只顯示：
 *  - 待入帳：稽核檔已落地、帳本還沒有同 `auditRef` 的事件或觀察列標記；每列可展開看入帳指令（PowerShell 與 POSIX，兩段相同）；
 *  - 紅色警示：帳本有 carrier 為 console 的項目、Console 稽核表卻沒有對應列（`role="alert"`，逐項 auditRef、kind、對象）；
 *  - 量不到：對帳回 NOT-EVALUABLE（Bridge 不可用、逾時、頁數超限）時顯示原因逐字，**不得**顯示「無待入帳」——量不到不是沒有；
 *  - 無待入帳：只有對帳成功（ok）且沒有待入帳也沒有 orphans 時才顯示。
 * 沒有任何刪除、移除、清除控件（稽核表列不可改；補償刪除只由 backend 在確定未落檔時做）。帳本字串一律以文字節點渲染。
 */
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useSiConsoleWrites } from "@/lib/api/queries";
import { SI_CONSOLE_WRITES_LIMIT, notEvaluableText, pendingWrites, siWriteKindLabel, writeSubjectText } from "@/lib/domain/si";
import { SiError, SiIngestCommands, SiLoading } from "./siParts";

const SHELL = "mb-5 rounded-lg border border-wg-line bg-wg-surface px-5 py-4";

export function SiWritesPanel() {
  const q = useSiConsoleWrites();
  const [open, setOpen] = useState<Record<string, boolean>>({});

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
  // 量不到時整份清單不可信：待入帳與警示都不列、也不說「無」
  const pending = evaluable ? pendingWrites(items) : [];
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
