"use client";

/**
 * 執行詳情「追溯覆蓋（諮詢）」面板（契約 §1.10.3、§4.7.2；UI-SDD-02；G-05）：
 *  - 專案沒有 SDD 規格綁定（`sddSpecDir` 為空）時整個面板不顯示（呼叫端傳 bound=false）；
 *  - 批次非終態只顯示一行「批次結束後才會有追溯覆蓋報告」，不呼叫端點；進入終態（COMPLETED／FAILED／CANCELLED）後取**一次**，不輪詢；
 *  - 🔴 諮詢視圖：標題旁恆有「諮詢視圖」徽章與固定說明（AT 通過只代表評估指令與驗收 regex 皆通過，不等於規格被滿足；SCG-4 的人工審查才是真閘）；
 *  - 404 `rtm_not_found`（批次存在但沒有報告）→ 中性文字「此批次沒有追溯覆蓋報告」（不是錯誤樣式）；422、502、504 與其他錯誤 → 一般錯誤區塊（message 與 traceId）加「重試」。
 * 測試屬性：面板 `data-testid="rtm-panel"`。缺值一律「—」；有無法歸屬 AC 的 AT 時 `at.total` 與 `ac.total` 口徑不同，不互相推算。
 */
import type { ReactNode } from "react";

import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";
import { ApiError } from "@/lib/api/client";
import { useExecutionRtm } from "@/lib/api/queries";
import { REASONS } from "@/lib/api/reasons";
import type { RunStatus } from "@/lib/api/types";
import { RTM_ADVISORY_BADGE, RTM_ADVISORY_NOTE, RTM_NOT_FOUND_HINT, RTM_NOT_FOUND_NOTE, RTM_NOT_TERMINAL_NOTE, RTM_TITLE, rtmView } from "@/lib/domain/rtm";
import { isRunTerminal } from "@/lib/domain/status";

function Row({ label, testid, title, children, note, noteTestid }: { label: string; testid: string; title?: string; children: ReactNode; note?: string | null; noteTestid?: string }) {
  return (
    <div className="contents">
      <dt className="pt-0.5 text-[13px] text-wg-muted">{label}</dt>
      <dd className="min-w-0 text-[15px] break-words">
        <span data-testid={testid} title={title}>
          {children}
        </span>
        {note ? (
          <span data-testid={noteTestid} className="mt-0.5 block text-[13px] text-wg-muted">
            {note}
          </span>
        ) : null}
      </dd>
    </div>
  );
}

export function RtmPanel({ runId, runStatus, bound }: { runId: string | null | undefined; runStatus: RunStatus | undefined; bound: boolean }) {
  const terminal = isRunTerminal(runStatus);
  const q = useExecutionRtm(runId, bound && terminal);
  if (!bound || !runId) return null;

  let body: ReactNode;
  if (runStatus === undefined) {
    body = <Skeleton className="h-24" />;
  } else if (!terminal) {
    body = (
      <p data-testid="rtm-pending" className="text-sm text-wg-muted">
        {RTM_NOT_TERMINAL_NOTE}
      </p>
    );
  } else if (q.isPending) {
    body = <Skeleton className="h-32" />;
  } else if (q.isError) {
    body =
      q.error instanceof ApiError && q.error.reason === REASONS.RTM_NOT_FOUND ? (
        <div role="status" data-testid="rtm-empty" className="text-sm">
          <p className="font-medium">{RTM_NOT_FOUND_NOTE}</p>
          <p className="mt-0.5 text-wg-muted">{RTM_NOT_FOUND_HINT}</p>
        </div>
      ) : (
        <ErrorState error={q.error} onRetry={() => q.refetch()} title="無法載入追溯覆蓋" />
      );
  } else {
    const v = rtmView(q.data);
    body = (
      <>
        <p data-testid="rtm-advisory-note" className="mb-3 text-[13px] text-wg-text">
          {RTM_ADVISORY_NOTE}
        </p>
        <dl className="grid grid-cols-[160px_1fr] gap-x-6 gap-y-2.5 max-md:grid-cols-1 max-md:gap-y-1">
          <Row label="AT 通過" testid="rtm-at" note={v.atNote} noteTestid="rtm-at-note">
            {v.at}
          </Row>
          <Row label="AC 覆蓋" testid="rtm-ac">
            {v.ac}
          </Row>
          <Row label="SCG-5 覆蓋" testid="rtm-scg5">
            {v.scg5}
          </Row>
          <Row label="規格摘要" testid="rtm-digest" title={v.specDigest.full ?? undefined}>
            <span className="font-mono text-sm">{v.specDigest.text}</span>
          </Row>
          <Row label="場景" testid="rtm-scenario">
            {v.scenario}
          </Row>
          <Row label="未通過的 AT" testid="rtm-failed">
            {v.failed}
          </Row>
          <Row label="驗收 regex 偏弱的 AT" testid="rtm-weak" note={v.weakNote} noteTestid="rtm-weak-note">
            {v.weak}
          </Row>
          <Row label="無法歸屬 AC 的 AT" testid="rtm-unmapped" note={v.unmappedNote} noteTestid="rtm-unmapped-note">
            {v.unmapped}
          </Row>
        </dl>
      </>
    );
  }

  const showBadge = terminal && q.isSuccess;
  return (
    <Card className="mb-6 px-[22px] py-5" data-testid="rtm-panel" data-run-id={runId}>
      <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <CardTitle>{RTM_TITLE}</CardTitle>
        {showBadge ? (
          <span data-testid="rtm-advisory-badge" className="rounded-sm border border-wg-alert-border bg-wg-alert-bg px-[7px] py-0.5 text-xs font-semibold text-wg-text">
            {RTM_ADVISORY_BADGE}
          </span>
        ) : null}
      </div>
      {body}
    </Card>
  );
}
