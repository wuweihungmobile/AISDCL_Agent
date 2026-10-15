import { Plus } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import { StatusDot } from "@/components/ui/status-dot";
import type { TaskBrief } from "@/lib/api/types";
import { taskStatus } from "@/lib/domain/status";
import { retryLabel } from "@/lib/format";

/** 任務清單卡（設計稿 4）：狀態點、任務名、狀態、重試 x / y、詳情；標題旁「新增任務」。 */
export function TaskListCard({ projectId, goalId, tasks, canWrite, onAdd }: { projectId: string; goalId: string; tasks: TaskBrief[]; canWrite: boolean; onAdd: () => void }) {
  const ordered = [...tasks].sort((a, b) => a.sortOrder - b.sortOrder);
  return (
    <Card className="mb-6 px-[22px] py-5" data-testid="task-list-card">
      <div className="mb-2 flex items-center justify-between">
        <CardTitle>任務清單 ({ordered.length})</CardTitle>
        <Button variant="ghost" size="sm" iconLeft={Plus} onClick={onAdd} disabled={!canWrite} title={canWrite ? undefined : "權限不足（唯讀角色）"}>
          新增任務
        </Button>
      </div>
      {ordered.length === 0 ? (
        <EmptyState title="尚無任務" description="按右上「新增任務」建立第一個任務。" />
      ) : (
        ordered.map((t) => {
          const meta = taskStatus(t.status);
          const href = `/projects/${projectId}/goals/${goalId}/tasks/${t.id}`;
          return (
            <div key={t.id} data-testid="task-row" data-task-id={t.id} className="flex items-center gap-3.5 border-t border-wg-line py-[13px]">
              <StatusDot color={meta.color} size={10} live={t.status === "RUNNING"} />
              <Link href={href} className="min-w-0 flex-1 truncate text-[15px] text-wg-text transition-colors hover:text-wg-primary">
                {t.name}
              </Link>
              <span className="text-[13px] whitespace-nowrap text-wg-muted">{meta.label}</span>
              <span className="text-xs whitespace-nowrap text-wg-muted">重試 {retryLabel(t.retryCount, t.maxRetries)}</span>
              <Button asChild variant="ghost" size="sm">
                <Link href={href}>詳情</Link>
              </Button>
            </div>
          );
        })
      )}
    </Card>
  );
}
