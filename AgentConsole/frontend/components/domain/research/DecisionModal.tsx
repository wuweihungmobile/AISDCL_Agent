"use client";

/**
 * 決策彈窗（FR-R2P-18-2、18-3；TCS-ResearchToPRD-P2-20261107 AT-962-14-*；IFACE-P2 §5）：研究面**唯一**的決策彈窗殼（{@link DecisionModal}），
 * 類型 (b) 自癒耗盡（待審 kind=ESCALATED）、(c) Agent 請求審核（其他待審與 `review-request` 幀）、(d) 引擎升級事件（`alert` 幀）三種都走它；
 * P0 的類型 (a)（Gate 0 審查升級）仍在 `GatekeeperPanel` 重用 `SddEscalationBlock`，兩者不重疊（AT-962-14-7 靜態掃描）。
 *
 * 設計要點（為什麼這樣做）：
 *  - **決定走既有端點**：`useReviewExecution`（`POST /executions/{runId}/review/{reviewId}`，body `{decision, comment}`）；不寫 research gates、不新增端點。
 *    按鈕集合由 `allowedDecisions` 驅動，之外的按鈕不渲染；**Console 不替人判斷事情大不大，也不自動處理**——沒有任何逾時計時器。
 *  - **去重與重建**：去重鍵＝`decisionKey`（`reviewId`，無則 alert 幀 `seq`）；同鍵的 SSE 重播只合成一個項目、同一時間只開一窗；重新整理後以 `kanban.pendingReviews` 重建。
 *  - **「稍後處理」只關窗**：把鍵記進 `sessionStorage`（`research.decision.snoozed`，本分頁不再自動彈出），待辦仍在列表（{@link PendingReviewList}）與頂列徽章；不呼叫決定端點、不呼叫 `GET /signoffs/pending`。
 *  - **他人已決定**（409／404）：顯示錯誤、重抓待審清單、確認鈕停用（不重複送出）。VIEWER 可讀、決定鈕全停用且 `title="權限不足"`。純文字渲染。
 */
import { useQueryClient } from "@tanstack/react-query";
import { BellRing } from "lucide-react";
import { useMemo, useState } from "react";

import { PendingReviewList } from "@/components/domain/research/PendingReviewList";
import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Textarea } from "@/components/ui/textarea";
import { qk, useReviewExecution } from "@/lib/api/queries";
import { ApiError } from "@/lib/api/client";
import type { ResearchPendingReview, ReviewDecision } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { DECISION_LABEL, DECISION_SNOOZE_STORAGE_KEY, decisionButtons, decisionKey, decisionKindLabel, type DecisionItem } from "@/lib/domain/research";

export type { DecisionItem };
/** 串流幀轉成的觸發（與 {@link DecisionItem} 同形）。 */
export type DecisionTrigger = DecisionItem;

export function itemFromPending(p: ResearchPendingReview): DecisionItem {
  return { key: decisionKey({ reviewId: p.reviewId }) as string, reviewId: p.reviewId, runId: p.runId, kind: p.kind, taskId: p.taskId, reason: p.reason ?? "", allowedDecisions: p.allowedDecisions };
}

/** 待審與觸發合併：同鍵只留一個（待審優先，因為它是伺服器事實）。 */
export function mergeDecisionItems(pending: readonly ResearchPendingReview[], triggers: readonly DecisionTrigger[]): DecisionItem[] {
  const byKey = new Map<string, DecisionItem>();
  for (const p of pending) byKey.set(itemFromPending(p).key, itemFromPending(p));
  for (const t of triggers) if (!byKey.has(t.key)) byKey.set(t.key, t);
  return [...byKey.values()];
}

export function readSnoozed(): Set<string> {
  try {
    const raw = window.sessionStorage.getItem(DECISION_SNOOZE_STORAGE_KEY);
    const parsed: unknown = raw === null ? [] : JSON.parse(raw);
    return new Set(Array.isArray(parsed) ? parsed.filter((k): k is string => typeof k === "string") : []);
  } catch {
    return new Set();
  }
}

function writeSnoozed(keys: Set<string>): void {
  try {
    window.sessionStorage.setItem(DECISION_SNOOZE_STORAGE_KEY, JSON.stringify([...keys]));
  } catch {
    // 儲存被禁用：只是不記得「稍後」，待辦仍在列表
  }
}

/** 決策彈窗殼（受控）：`item` 為 null＝關閉。 */
export function DecisionModal({
  researchId,
  item,
  onClose,
  onSnooze,
  onDecided,
}: {
  researchId: string;
  item: DecisionItem | null;
  onClose: (key: string) => void;
  onSnooze: (key: string) => void;
  onDecided: (key: string) => void;
}) {
  const { canWrite } = useAuth();
  const qc = useQueryClient();
  const review = useReviewExecution();
  const [picked, setPicked] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [settled, setSettled] = useState(false);

  // 換一個項目＝重置表單（以 key 當 React key 的等價做法：render 期間比對）
  const [shownKey, setShownKey] = useState<string | null>(null);
  if ((item?.key ?? null) !== shownKey) {
    setShownKey(item?.key ?? null);
    setPicked(null);
    setComment("");
    setError(null);
    setSettled(false);
  }

  const buttons = item === null ? [] : decisionButtons(item.allowedDecisions);
  const canDecide = item !== null && item.reviewId !== null && item.runId !== null;
  const lockTitle = canWrite ? undefined : "權限不足";

  function confirm() {
    if (!canWrite || item === null || item.reviewId === null || item.runId === null || picked === null || settled) return;
    setError(null);
    setSettled(true); // 只送一次：失敗（含他人已決定）也不重複送出，要重來先關窗讓待審清單重抓
    review.mutate(
      { runId: item.runId, reviewId: item.reviewId, decision: picked as ReviewDecision, ...(comment.trim() === "" ? {} : { comment: comment.trim() }) },
      {
        onSuccess: () => {
          void qc.invalidateQueries({ queryKey: qk.researchKanban(researchId) });
          onDecided(item.key);
        },
        onError: (e) => {
          void qc.invalidateQueries({ queryKey: qk.researchKanban(researchId) });
          const gone = e instanceof ApiError && (e.status === 409 || e.status === 404);
          setError(gone ? "這個決定已經有人處理過（或已不存在），已重新載入待審清單。" : `送出決定失敗：${e instanceof Error ? e.message : "未知錯誤"}`);
          if (!gone) setSettled(false);
        },
      },
    );
  }

  return (
    <Dialog open={item !== null} onOpenChange={(next) => (!next && item !== null ? onClose(item.key) : undefined)}>
      <DialogContent title="需要人工決定" description="請處理待審項目" data-testid="decision-modal">
        {item !== null ? (
          <>
            <DialogBody>
              <p className="flex items-center gap-2 text-sm font-semibold" data-testid="decision-kind" data-kind={item.kind}>
                <BellRing size={16} aria-hidden className="text-wg-accent" />
                {decisionKindLabel(item.kind)}
              </p>
              <p data-testid="decision-reason" className="whitespace-pre-wrap break-words text-sm">
                {item.reason}
              </p>
              {item.taskId !== null ? (
                <p className="text-xs text-wg-muted">
                  任務：<span className="font-mono">{item.taskId}</span>
                </p>
              ) : null}
              {canDecide ? (
                <>
                  <div role="group" aria-label="決定" className="flex flex-wrap gap-2" data-testid="decision-buttons">
                    {buttons.map((d) => (
                      <Button
                        key={d}
                        variant={picked === d ? "solid" : "ghost"}
                        aria-pressed={picked === d}
                        disabled={!canWrite || settled}
                        title={lockTitle}
                        onClick={() => setPicked(d)}
                        data-testid={`decision-${d}`}
                      >
                        {DECISION_LABEL[d]}
                      </Button>
                    ))}
                  </div>
                  <Field label="理由" hint="（選填）">
                    <Textarea value={comment} onChange={(e) => setComment(e.target.value)} disabled={!canWrite} />
                  </Field>
                </>
              ) : (
                <p data-testid="decision-info-only" className="text-sm text-wg-muted">
                  這是引擎回報的事件，沒有可在這裡送出的決定；請到監控中心查看。
                </p>
              )}
              {error !== null ? (
                <p role="alert" data-testid="decision-error" className="text-sm text-wg-error">
                  {error}
                </p>
              ) : null}
            </DialogBody>
            <DialogFooter>
              <Button variant="ghost" onClick={() => onSnooze(item.key)} data-testid="decision-snooze">
                稍後處理
              </Button>
              {canDecide ? (
                <Button disabled={!canWrite || picked === null || settled} title={lockTitle} loading={review.isPending} onClick={confirm} data-testid="decision-confirm">
                  確認
                </Button>
              ) : null}
            </DialogFooter>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

/**
 * 決策中心：合併待審與串流觸發、一次只開一窗、記住「稍後」。`kanban.pendingReviews` 是事實來源（重新整理後據此重建）。
 * 同時渲染待辦列表（{@link PendingReviewList}）：列表永遠列出全部待審（含稍後處理者），按「處理」才強制開窗。
 */
export function DecisionCenter({ researchId, pendingReviews, triggers = [] }: { researchId: string; pendingReviews: readonly ResearchPendingReview[]; triggers?: readonly DecisionTrigger[] }) {
  const items = useMemo(() => mergeDecisionItems(pendingReviews, triggers), [pendingReviews, triggers]);
  const [snoozed, setSnoozed] = useState<Set<string>>(readSnoozed);
  const [dismissed, setDismissed] = useState<Set<string>>(() => new Set());
  const [forced, setForced] = useState<string | null>(null);

  const forcedItem = forced === null ? null : (items.find((i) => i.key === forced) ?? null);
  const auto = items.find((i) => !snoozed.has(i.key) && !dismissed.has(i.key)) ?? null;
  const active = forcedItem ?? auto;

  const close = (key: string) => {
    setDismissed((cur) => new Set(cur).add(key));
    setForced(null);
  };
  const snooze = (key: string) => {
    const next = new Set(snoozed).add(key);
    writeSnoozed(next);
    setSnoozed(next);
    close(key);
  };

  return (
    <>
      <PendingReviewList items={items} onOpen={(key) => setForced(key)} />
      <DecisionModal researchId={researchId} item={active} onClose={close} onSnooze={snooze} onDecided={close} />
    </>
  );
}
