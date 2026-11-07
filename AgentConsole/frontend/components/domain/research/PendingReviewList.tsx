"use client";

/**
 * 待辦列表（FR-R2P-18-3；步驟 4 頁面上的待審清單）：永遠列出 `kanban.pendingReviews` 與串流觸發合併後的全部項目——「稍後處理」只關窗，不會讓項目從這裡消失。
 * 每列的「處理」鈕交給 {@link DecisionCenter}（唯一彈窗殼）強制開窗；本元件自己不送任何請求。
 */
import { ListChecks } from "lucide-react";

import { Button } from "@/components/ui/button";
import { decisionKindLabel, type DecisionItem } from "@/lib/domain/research";

export function PendingReviewList({ items, onOpen }: { items: readonly DecisionItem[]; onOpen: (key: string) => void }) {
  return (
    <section aria-label="待辦決定" data-testid="pending-reviews" data-count={items.length} className="flex flex-col gap-2 rounded-md border border-wg-line p-4">
      <h4 className="flex items-center gap-2 text-base font-semibold">
        <ListChecks size={18} aria-hidden className="text-wg-muted" />
        待辦決定（{items.length}）
      </h4>
      {items.length === 0 ? (
        <p data-testid="pending-reviews-empty" className="text-sm text-wg-muted">
          目前沒有待人工決定的項目。
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((item) => (
            <li key={item.key} data-testid="pending-review" data-key={item.key} className="flex flex-wrap items-center gap-3 text-sm">
              <span className="font-semibold">{decisionKindLabel(item.kind)}</span>
              <span className="min-w-0 flex-1 break-words text-wg-muted">{item.reason}</span>
              <Button size="sm" variant="ghost" onClick={() => onOpen(item.key)}>
                處理
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
