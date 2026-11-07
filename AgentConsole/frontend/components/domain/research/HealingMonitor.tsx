"use client";

/**
 * 自癒監視器（FR-R2P-16；TCS-ResearchToPRD-P2-20261107 AT-962-12-*；IFACE-P2 §3）：每個任務一列——嘗試次數對上限（`maxRetries`）、最近失敗摘錄、歸因與補丁結果、升級與規格漂移提示。
 *
 * 設計要點（為什麼這樣做）：
 *  - **不假造**：歸因與補丁結果引擎沒有獨立資料來源，後端恆回 `null`，這裡寫「引擎未提供」（D-140 #5）；空資料顯示「目前沒有自癒嘗試」，不顯示「0／上限」的假進度。
 *  - **純文字**：失敗摘錄（已在後端遮蔽、尾 300 字元）一律當文字渲染，長字串以 `break-all` 與 `overflow-x-auto` 不撐破容器，不截斷。
 *  - **升級＝交給人**：任務已升級（`escalated`）時只顯示「已升級，等待人工決定」徽章，點它開決策彈窗（{@link DecisionModal}，研究面唯一的決策殼）；**沒有自動重試鈕**，重試走彈窗的既有審核動作。
 *  - **規格漂移**：`specChangeForbidden` 的列顯示「補丁觸及凍結規格，請發起 SCR」並開 {@link ScrRequestDialog}（`sourceKind` 預填 `HEALING_FAILED`）；VIEWER 的發起鈕停用。
 *  - 日誌落後（`logBehind`）大於 0 時顯示「日誌落後 N 筆」；0 筆不顯示。
 */
import { useQueryClient } from "@tanstack/react-query";
import { HeartPulse } from "lucide-react";
import { useMemo, useState } from "react";

import { DecisionModal, itemFromPending } from "@/components/domain/research/DecisionModal";
import { ScrRequestDialog } from "@/components/domain/research/ScrRequestDialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { qk, useResearchHealing, useResearchKanban } from "@/lib/api/queries";
import type { ResearchHealingRow, ResearchPendingReview } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { READONLY_TITLE } from "@/lib/domain/research";

type TaskGroup = { taskId: string; last: ResearchHealingRow; escalated: boolean; specChangeForbidden: boolean; resolved: boolean };

/** 依任務分組（保留第一次出現的順序）；每組取最後一列為「最近」。 */
function groupByTask(rows: readonly ResearchHealingRow[]): TaskGroup[] {
  const groups = new Map<string, ResearchHealingRow[]>();
  for (const row of rows) groups.set(row.taskId, [...(groups.get(row.taskId) ?? []), row]);
  return [...groups.entries()].map(([taskId, list]) => ({
    taskId,
    last: list[list.length - 1],
    escalated: list.some((r) => r.escalated === true),
    specChangeForbidden: list.some((r) => r.specChangeForbidden === true),
    resolved: list[list.length - 1].resolved === true,
  }));
}

const STATUS_TEXT: Readonly<Record<string, string>> = { RETRYING: "重試中", FAILED: "失敗" };

export function HealingMonitor({ researchId }: { researchId: string }) {
  const { canWrite } = useAuth();
  const qc = useQueryClient();
  const healing = useResearchHealing(researchId);
  const kanban = useResearchKanban(researchId);
  const [scrFor, setScrFor] = useState<string | null>(null);
  const [reviewFor, setReviewFor] = useState<ResearchPendingReview | null>(null);

  const groups = useMemo(() => groupByTask(healing.data?.rows ?? []), [healing.data]);
  const pending = kanban.data?.pendingReviews ?? [];
  const escalatedReview = (taskId: string): ResearchPendingReview | undefined => pending.find((p) => p.kind === "ESCALATED" && p.taskId === taskId);

  if (healing.data === undefined) {
    return healing.isError ? <ErrorState error={healing.error} title="無法載入自癒監視器" onRetry={() => void healing.refetch()} /> : <PageSkeleton />;
  }
  const { maxRetries, logBehind } = healing.data;

  return (
    <Card data-testid="healing-monitor" className="flex flex-col gap-3 p-4">
      <h4 className="flex flex-wrap items-center gap-2 text-base font-semibold">
        <HeartPulse size={18} aria-hidden className="text-wg-muted" />
        自癒監視器
        {logBehind > 0 ? (
          <span data-testid="healing-log-behind" className="rounded border border-wg-draft-border bg-wg-draft-bg px-2 py-0.5 text-xs font-medium text-wg-accent">
            日誌落後 {logBehind} 筆
          </span>
        ) : null}
      </h4>
      {groups.length === 0 ? (
        <p data-testid="healing-empty" className="text-sm text-wg-muted">
          目前沒有自癒嘗試
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {groups.map((g) => {
            const review = escalatedReview(g.taskId);
            return (
              <li key={g.taskId} data-testid="healing-row" data-task={g.taskId} className="flex min-w-0 flex-col gap-1 rounded-md border border-wg-line p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold">任務 {g.taskId}</span>
                  <span data-testid="healing-attempt">
                    嘗試 {g.last.attempt}／{maxRetries}
                  </span>
                  <span className="text-wg-muted">{g.resolved ? "已修復" : (STATUS_TEXT[g.last.status] ?? g.last.status)}</span>
                  {g.escalated ? (
                    review !== undefined ? (
                      <Button size="sm" variant="ghost" onClick={() => setReviewFor(review)} data-testid="healing-escalated">
                        已升級，等待人工決定
                      </Button>
                    ) : (
                      <span data-testid="healing-escalated" className="rounded border border-wg-draft-border bg-wg-draft-bg px-2 py-0.5 text-xs font-medium text-wg-accent">
                        已升級，等待人工決定
                      </span>
                    )
                  ) : null}
                </div>
                <pre data-testid="healing-excerpt" className="max-w-full overflow-x-auto whitespace-pre-wrap break-all font-mono text-[13px]">
                  {g.last.excerpt}
                </pre>
                <p className="text-wg-muted" data-testid="healing-attribution">
                  歸因：{g.last.attribution ?? "引擎未提供"}
                </p>
                <p className="text-wg-muted" data-testid="healing-patch">
                  補丁結果：{g.last.patchResult ?? "引擎未提供"}
                </p>
                {g.specChangeForbidden ? (
                  <div data-testid="healing-spec-change" role="alert" className="flex flex-wrap items-center gap-3 rounded-md border border-wg-error px-3 py-2">
                    <span className="font-semibold text-wg-error">補丁觸及凍結規格，請發起 SCR</span>
                    <Button size="sm" variant="ghost" disabled={!canWrite} title={canWrite ? undefined : READONLY_TITLE} onClick={() => setScrFor(g.taskId)} data-testid="healing-scr">
                      發起 SCR
                    </Button>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
      {scrFor !== null ? <ScrRequestDialog researchId={researchId} open onOpenChange={(open) => !open && setScrFor(null)} sourceKind="HEALING_FAILED" /> : null}
      <DecisionModal
        researchId={researchId}
        item={reviewFor === null ? null : itemFromPending(reviewFor)}
        onClose={() => setReviewFor(null)}
        onSnooze={() => setReviewFor(null)}
        onDecided={() => {
          setReviewFor(null);
          void qc.invalidateQueries({ queryKey: qk.researchKanban(researchId) });
        }}
      />
    </Card>
  );
}
