"use client";

import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Plus } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { EmptyState } from "@/components/ui/states";
import { StatusDot } from "@/components/ui/status-dot";
import { useToast } from "@/components/ui/toast";
import { describeError } from "@/lib/api/client";
import { useReorderGoals } from "@/lib/api/queries";
import type { GoalBrief } from "@/lib/api/types";
import { goalStatus } from "@/lib/domain/status";
import { percent } from "@/lib/format";
import { cn } from "@/lib/utils";

function GoalRow({
  goal: g,
  projectId,
  sortable,
}: {
  goal: GoalBrief;
  projectId: string;
  sortable: boolean;
}) {
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } =
    useSortable({ id: g.id, disabled: !sortable });
  const meta = goalStatus(g.status);
  const href = `/projects/${projectId}/goals/${g.id}`;
  return (
    <div
      ref={setNodeRef}
      data-testid="goal-row"
      data-goal-id={g.id}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        "flex items-center gap-3.5 border-t border-wg-line bg-wg-surface py-3.5 max-md:flex-wrap",
        isDragging && "relative z-10 bg-wg-tertiary opacity-80",
      )}
    >
      {sortable ? (
        <button
          ref={setActivatorNodeRef}
          type="button"
          aria-label={`拖曳排序：${g.name}`}
          title="拖曳排序（鍵盤：空白鍵拿起、方向鍵移動、空白鍵放下）"
          className="inline-flex size-6 shrink-0 cursor-grab touch-none items-center justify-center rounded-sm text-wg-muted hover:text-wg-primary active:cursor-grabbing"
          {...attributes}
          {...listeners}
        >
          <GripVertical size={16} aria-hidden />
        </button>
      ) : null}
      <StatusDot color={meta.color} size={10} live={g.status === "IN_PROGRESS"} />
      <Link
        href={href}
        className="shrink-0 text-[15px] font-semibold text-wg-text transition-colors hover:text-wg-primary"
      >
        {g.name}
      </Link>
      <span className="text-[13px] text-wg-muted">{meta.label}</span>
      <div className="flex max-w-[320px] flex-1 items-center gap-2.5">
        <Progress
          value={percent(g.completedTaskCount, g.taskCount)}
          label={`${g.name} 任務完成度`}
          className="h-[7px] flex-1"
        />
        <span className="text-[13px] whitespace-nowrap text-wg-muted">
          {g.completedTaskCount} / {g.taskCount}
        </span>
      </div>
      <Button asChild variant="ghost" size="sm" className="ml-auto">
        <Link href={href}>查看</Link>
      </Button>
    </div>
  );
}

/**
 * 目標清單卡（設計稿 3）：狀態點、名稱、狀態、進度條、done/total、查看；標題旁「新增目標」。
 * 拖曳排序（@dnd-kit：指標與鍵盤皆可）→ PUT /goals/reorder；先樂觀換位，失敗還原並 toast。
 */
export function GoalListCard({
  projectId,
  goals,
  canWrite,
  onAdd,
}: {
  projectId: string;
  goals: GoalBrief[];
  canWrite: boolean;
  onAdd: () => void;
}) {
  const toast = useToast();
  const reorder = useReorderGoals(projectId);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const ordered = [...goals].sort((a, b) => a.sortOrder - b.sortOrder);

  function onDragEnd(e: DragEndEvent) {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    const ids = ordered.map((g) => g.id);
    const from = ids.indexOf(String(active.id));
    const to = ids.indexOf(String(over.id));
    if (from < 0 || to < 0) return;
    reorder.mutate(arrayMove(ids, from, to), {
      onSuccess: () => toast.success("已更新目標順序"),
      onError: (err) => toast.error(`調整順序失敗：${describeError(err)}`),
    });
  }

  return (
    <Card className="mb-6 px-[22px] py-5" data-testid="goal-list-card">
      <div className="mb-2 flex items-center justify-between">
        <CardTitle>目標清單 ({ordered.length})</CardTitle>
        <Button
          variant="ghost"
          size="sm"
          iconLeft={Plus}
          onClick={onAdd}
          disabled={!canWrite}
          title={canWrite ? undefined : "權限不足（唯讀角色）"}
        >
          新增目標
        </Button>
      </div>
      {ordered.length === 0 ? (
        <EmptyState title="尚無目標" description="按右上「新增目標」建立第一個目標。" />
      ) : (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
          <SortableContext items={ordered.map((g) => g.id)} strategy={verticalListSortingStrategy}>
            {ordered.map((g) => (
              <GoalRow key={g.id} goal={g} projectId={projectId} sortable={canWrite && ordered.length > 1} />
            ))}
          </SortableContext>
        </DndContext>
      )}
    </Card>
  );
}
