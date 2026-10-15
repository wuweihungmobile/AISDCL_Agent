"use client";

import { AlertTriangle, Check } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { CountBadge } from "@/components/ui/badge";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { describeError } from "@/lib/api/client";
import type { ReviewDecision, ReviewItem } from "@/lib/api/types";
import { REVIEW_DECISION_LABEL, REVIEW_DECISION_ORDER, reviewKind } from "@/lib/domain/status";
import { formatClock } from "@/lib/format";
import { isDestructiveDecision, reviewConsequence } from "./reviewHelp";

export type DecideHandler = (review: ReviewItem, decision: ReviewDecision, comment: string) => Promise<void>;

/**
 * 「待審核項目」卡（設計稿畫面 7；契約 §4.2 E-16～E-19；PRD US-E-07、E-08）：
 * 標題＋accent 計數 badge；每列＝alert-triangle＋種類＋原因＋四按鈕 通過(solid)／重試／跳過／拒絕。
 * 按鈕是否可按＝後端給的 review.allowedDecisions（ESCALATED 沒有「通過」、gate 類沒有「跳過」）；
 * 按下去先開確認對話框（顯示原因與後果、可填意見），確認後才送出 POST review。
 */
export function ReviewCard({
  projectId,
  reviews,
  canWrite,
  onDecide,
}: {
  projectId: string;
  reviews: readonly ReviewItem[];
  canWrite: boolean;
  onDecide: DecideHandler;
}) {
  const [picked, setPicked] = useState<{ review: ReviewItem; decision: ReviewDecision } | null>(null);

  return (
    <Card className="mt-6 px-[22px] py-5" data-testid="review-card">
      <div className="mb-3.5 flex items-center gap-2.5">
        <CardTitle>待審核項目</CardTitle>
        <CountBadge count={reviews.length} data-testid="review-count" />
      </div>
      {reviews.length === 0 ? (
        <p className="py-4 text-center text-sm text-wg-muted" data-testid="review-empty">
          目前沒有待審核的項目。
        </p>
      ) : (
        reviews.map((r) => {
          const kind = reviewKind(r.kind);
          const where = [r.goalName, r.taskName].filter(Boolean).join(" / ");
          return (
            <div key={r.id} data-testid="review-row" data-kind={r.kind} className="flex items-start gap-3 border-t border-wg-line py-3.5 first:border-t-0 max-md:flex-wrap">
              <AlertTriangle size={20} className="mt-0.5 shrink-0 text-wg-warning" aria-hidden />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-sm bg-wg-alert-bg px-1.5 py-0.5 text-xs font-semibold" data-testid="review-kind">
                    {kind.label}
                  </span>
                  <span className="text-[15px] font-medium" data-testid="review-reason">
                    {r.reason}
                  </span>
                </div>
                <div className="mt-0.5 flex flex-wrap items-center gap-x-3 text-[13px] text-wg-muted">
                  {where ? <span>{where}</span> : null}
                  <span>{formatClock(r.requestedAt)} 提出</span>
                  {r.taskId && r.goalId ? (
                    <Link href={`/projects/${projectId}/goals/${r.goalId}/tasks/${r.taskId}`} className="text-wg-primary transition-opacity hover:opacity-85" data-testid="review-task-link">
                      查看任務
                    </Link>
                  ) : null}
                </div>
              </div>
              <div className="flex flex-wrap gap-2" role="group" aria-label={`審核：${r.reason}`}>
                {REVIEW_DECISION_ORDER.map((d) => {
                  const allowed = r.allowedDecisions.includes(d);
                  return (
                    <Button
                      key={d}
                      size="sm"
                      variant={d === "APPROVE" ? "solid" : "ghost"}
                      disabled={!canWrite || !allowed}
                      title={!canWrite ? "權限不足（唯讀角色）" : allowed ? undefined : "這個審核項不允許此決定"}
                      data-testid={`review-${d.toLowerCase()}`}
                      onClick={() => setPicked({ review: r, decision: d })}
                    >
                      {REVIEW_DECISION_LABEL[d]}
                    </Button>
                  );
                })}
              </div>
            </div>
          );
        })
      )}

      <Dialog open={picked !== null} onOpenChange={(open) => !open && setPicked(null)}>
        {picked ? (
          <DialogContent title={`${REVIEW_DECISION_LABEL[picked.decision]}：${reviewKind(picked.review.kind).label}`} description="審核決定會寫入審核人與時間">
            <ReviewBody
              key={picked.review.id}
              review={picked.review}
              decision={picked.decision}
              onClose={() => setPicked(null)}
              onDecide={onDecide}
            />
          </DialogContent>
        ) : null}
      </Dialog>
    </Card>
  );
}

function ReviewBody({
  review,
  decision,
  onClose,
  onDecide,
}: {
  review: ReviewItem;
  decision: ReviewDecision;
  onClose: () => void;
  onDecide: DecideHandler;
}) {
  const [comment, setComment] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const destructive = isDestructiveDecision(review.kind, decision);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      await onDecide(review, decision, comment.trim());
      onClose();
    } catch (err) {
      setError(describeError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate data-testid="review-dialog">
      <DialogBody>
        <p className="text-[15px] leading-[1.7]">{review.reason}</p>
        <p className="rounded-md bg-wg-base px-3 py-2 text-sm text-wg-muted" data-testid="review-consequence">
          {REVIEW_DECISION_LABEL[decision]}：{reviewConsequence(review.kind, decision)}
        </p>
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">意見（選填）</span>
          <Textarea value={comment} onChange={(e) => setComment(e.target.value)} maxLength={2000} placeholder="寫給審計紀錄的備註，最多 2,000 字" data-testid="review-comment" />
        </label>
        {error ? (
          <p role="alert" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
            {error}
          </p>
        ) : null}
      </DialogBody>
      <DialogFooter>
        <Button variant="ghost" onClick={onClose} disabled={pending}>
          取消
        </Button>
        <Button type="submit" variant={destructive ? "accent" : "solid"} iconLeft={Check} loading={pending} data-testid="review-confirm">
          確認{REVIEW_DECISION_LABEL[decision]}
        </Button>
      </DialogFooter>
    </form>
  );
}
