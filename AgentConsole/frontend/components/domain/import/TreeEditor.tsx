"use client";

/**
 * 步驟 2 的三層樹（設計稿：#F5F7F2 底框；專案 → 目標 → 任務縮排，folder／target／file-text 圖示）：
 * 可展開看說明與通過標準；每個節點 ✏️ 編輯／🗑️ 刪除（Lucide Pencil／Trash2）；目標與任務可拖曳調整順序
 * （@dnd-kit：指標與鍵盤皆可；任務只能在同一個目標內換位）。
 * 這支元件只負責呈現與回報意圖（callbacks）；樹的狀態與 reducer 在 StructureCard／tree.ts。
 */
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
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ChevronDown, ChevronRight, FileText, Folder, GripVertical, Pencil, Plus, Target, Trash2 } from "lucide-react";
import { useState, type ReactNode } from "react";

import { MarkdownView } from "@/components/markdown/MarkdownView";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { cn } from "@/lib/utils";
import type { Highlights } from "./gateErrors";
import type { GoalNode, TaskNode, Tree } from "./tree";

export type TreeEditorProps = {
  tree: Tree;
  /** 可編輯（OPERATOR 以上）；唯讀角色只看樹 */
  canEdit: boolean;
  /** 有界閘／欄位錯誤指到的節點（標紅）；null＝不標 */
  highlights: Highlights | null;
  onEditProject: () => void;
  onAddGoal: () => void;
  onEditGoal: (key: string) => void;
  onDeleteGoal: (key: string) => void;
  onAddTask: (goalKey: string) => void;
  onEditTask: (goalKey: string, uid: string) => void;
  onDeleteTask: (goalKey: string, uid: string) => void;
  onMoveGoal: (activeKey: string, overKey: string) => void;
  onMoveTask: (goalKey: string, activeUid: string, overUid: string) => void;
};

const UNNAMED = "（未命名）";

function useDragSensors() {
  return useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
}

function DragHandle({
  label,
  setActivatorNodeRef,
  attributes,
  listeners,
}: {
  label: string;
  setActivatorNodeRef: (el: HTMLElement | null) => void;
  attributes: object;
  listeners: object | undefined;
}) {
  return (
    <button
      ref={setActivatorNodeRef}
      type="button"
      aria-label={`拖曳排序：${label}`}
      title="拖曳排序（鍵盤：空白鍵拿起、方向鍵移動、空白鍵放下）"
      className="inline-flex size-6 shrink-0 cursor-grab touch-none items-center justify-center rounded-sm text-wg-muted hover:text-wg-primary active:cursor-grabbing"
      {...attributes}
      {...listeners}
    >
      <GripVertical size={16} aria-hidden />
    </button>
  );
}

function Chevron({ open, onToggle, label }: { open: boolean; onToggle: () => void; label: string }) {
  const Icon = open ? ChevronDown : ChevronRight;
  return (
    <button
      type="button"
      aria-label={`${open ? "收合" : "展開"}詳情：${label}`}
      aria-expanded={open}
      onClick={onToggle}
      className="inline-flex size-6 shrink-0 cursor-pointer items-center justify-center rounded-sm text-wg-muted hover:text-wg-primary"
    >
      <Icon size={16} aria-hidden />
    </button>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <div className="mb-0.5 text-xs font-medium text-wg-muted">{title}</div>
      {children}
    </div>
  );
}

function TaskDetails({ task }: { task: TaskNode }) {
  return (
    <div data-testid="task-details" className="mt-1 mb-2 ml-[58px] flex flex-col gap-2.5 rounded-md bg-wg-surface px-3.5 py-3 text-sm">
      <Section title="說明描述">
        <MarkdownView source={task.description} empty="（尚未填寫）" />
      </Section>
      <Section title="通過標準">
        <MarkdownView source={task.passCriteria} variant="criteria" empty="（尚未填寫）" />
      </Section>
      {task.evaluatorCommand ? (
        <p className="font-mono text-xs break-all">
          <span className="font-sans text-wg-muted">驗證命令　</span>
          {task.evaluatorCommand}
        </p>
      ) : null}
      {task.expectedOutputRegex ? (
        <p className="font-mono text-xs break-all">
          <span className="font-sans text-wg-muted">期望輸出　</span>
          {task.expectedOutputRegex}
        </p>
      ) : null}
      {task.maxRetries !== undefined ? <p className="text-xs text-wg-muted">最大重試次數：{task.maxRetries}</p> : null}
    </div>
  );
}

function TaskRow({
  goal,
  task,
  highlighted,
  canEdit,
  open,
  onToggle,
  onEdit,
  onDelete,
}: {
  goal: GoalNode;
  task: TaskNode;
  highlighted: boolean;
  canEdit: boolean;
  open: boolean;
  onToggle: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } = useSortable({
    id: task.uid,
    disabled: !canEdit || goal.tasks.length < 2,
  });
  const label = task.name || UNNAMED;
  return (
    <div
      ref={setNodeRef}
      data-testid="tree-task"
      data-task-uid={task.uid}
      data-highlighted={highlighted || undefined}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn("rounded-md", isDragging && "relative z-10 bg-wg-tertiary opacity-80")}
    >
      <div
        className={cn(
          "flex items-center gap-1.5 rounded-md py-1 pl-1 pr-1.5",
          highlighted && "border border-wg-error bg-wg-draft-bg",
        )}
      >
        {canEdit && goal.tasks.length > 1 ? (
          <DragHandle label={label} setActivatorNodeRef={setActivatorNodeRef} attributes={attributes} listeners={listeners} />
        ) : (
          <span className="size-6 shrink-0" aria-hidden />
        )}
        <Chevron open={open} onToggle={onToggle} label={label} />
        <FileText size={16} className="shrink-0 text-wg-secondary" aria-hidden />
        <span className={cn("min-w-0 flex-1 truncate text-sm", !task.name && "text-wg-error")} data-testid="task-name">
          {label}
        </span>
        <span className="shrink-0 text-xs text-wg-muted">任務</span>
        {canEdit ? (
          <>
            <IconButton icon={Pencil} label={`編輯任務：${label}`} size={30} onClick={onEdit} />
            <IconButton
              icon={Trash2}
              label={`刪除任務：${label}`}
              size={30}
              disabled={goal.tasks.length <= 1}
              title={goal.tasks.length <= 1 ? "每個目標至少保留一個任務" : `刪除任務：${label}`}
              onClick={onDelete}
            />
          </>
        ) : null}
      </div>
      {open ? <TaskDetails task={task} /> : null}
    </div>
  );
}

function GoalBlock({
  goal,
  index,
  tree,
  props,
  open,
  isOpen,
  toggle,
}: {
  goal: GoalNode;
  index: number;
  tree: Tree;
  props: TreeEditorProps;
  open: boolean;
  isOpen: (id: string) => boolean;
  toggle: (id: string) => void;
}) {
  const { canEdit, highlights } = props;
  const sensors = useDragSensors();
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } = useSortable({
    id: goal.key,
    disabled: !canEdit || tree.goals.length < 2,
  });
  const label = goal.name || UNNAMED;
  const highlighted = Boolean(highlights?.goals.has(index));
  const nameOf = (key: string) => tree.goals.find((g) => g.key === key)?.name || "（未命名目標）";

  function onTaskDragEnd(e: DragEndEvent) {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    props.onMoveTask(goal.key, String(active.id), String(over.id));
  }

  return (
    <div
      ref={setNodeRef}
      data-testid="tree-goal"
      data-goal-key={goal.key}
      data-highlighted={highlighted || undefined}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn("rounded-md", isDragging && "relative z-10 bg-wg-tertiary opacity-80")}
    >
      <div
        className={cn(
          "flex items-center gap-1.5 rounded-md py-1.5 pr-1.5 pl-1",
          highlighted && "border border-wg-error bg-wg-draft-bg",
        )}
      >
        {canEdit && tree.goals.length > 1 ? (
          <DragHandle label={label} setActivatorNodeRef={setActivatorNodeRef} attributes={attributes} listeners={listeners} />
        ) : (
          <span className="size-6 shrink-0" aria-hidden />
        )}
        <Chevron open={open} onToggle={() => toggle(`goal:${goal.key}`)} label={label} />
        <Target size={18} className="shrink-0 text-wg-primary" aria-hidden />
        <span className={cn("min-w-0 flex-1 truncate text-[15px] font-medium", !goal.name && "text-wg-error")} data-testid="goal-name">
          {label}
        </span>
        <span className="shrink-0 text-xs text-wg-muted">目標 · {goal.tasks.length} 任務</span>
        {canEdit ? (
          <>
            <IconButton icon={Pencil} label={`編輯目標：${label}`} size={30} onClick={() => props.onEditGoal(goal.key)} />
            <IconButton
              icon={Trash2}
              label={`刪除目標：${label}`}
              size={30}
              disabled={tree.goals.length <= 1}
              title={tree.goals.length <= 1 ? "至少保留一個目標" : `刪除目標：${label}（含 ${goal.tasks.length} 個任務）`}
              onClick={() => props.onDeleteGoal(goal.key)}
            />
          </>
        ) : null}
      </div>

      {open ? (
        <div data-testid="goal-details" className="mt-1 mb-2 ml-[34px] flex flex-col gap-2.5 rounded-md bg-wg-surface px-3.5 py-3 text-sm">
          <Section title="說明描述">
            <MarkdownView source={goal.description} empty="（無說明）" />
          </Section>
          <Section title="通過標準">
            <MarkdownView source={goal.passCriteria} variant="criteria" empty="（尚未填寫）" />
          </Section>
          <Section title="前置依賴">
            {goal.dependsOn.length === 0 ? (
              <p className="text-sm text-wg-muted">無</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {goal.dependsOn.map((k) => (
                  <span key={k} className="rounded-sm bg-wg-tertiary px-2 py-0.5 text-xs">
                    {nameOf(k)}
                  </span>
                ))}
              </div>
            )}
          </Section>
        </div>
      ) : null}

      <div className="mt-0.5 ml-[18px] border-l border-wg-line pl-3">
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onTaskDragEnd}>
          <SortableContext items={goal.tasks.map((t) => t.uid)} strategy={verticalListSortingStrategy}>
            {goal.tasks.map((t, ti) => (
              <TaskRow
                key={t.uid}
                goal={goal}
                task={t}
                highlighted={Boolean(highlights?.tasks.has(`${index}.${ti}`))}
                canEdit={canEdit}
                open={isOpen(`task:${t.uid}`)}
                onToggle={() => toggle(`task:${t.uid}`)}
                onEdit={() => props.onEditTask(goal.key, t.uid)}
                onDelete={() => props.onDeleteTask(goal.key, t.uid)}
              />
            ))}
          </SortableContext>
        </DndContext>
        {canEdit ? (
          <Button
            variant="ghost"
            size="sm"
            iconLeft={Plus}
            className="my-1 ml-1"
            aria-label={`新增任務到目標：${label}`}
            onClick={() => props.onAddTask(goal.key)}
          >
            新增任務
          </Button>
        ) : null}
      </div>
    </div>
  );
}

export function TreeEditor(props: TreeEditorProps) {
  const { tree, canEdit, highlights } = props;
  const [open, setOpen] = useState<ReadonlySet<string>>(() => new Set());
  const sensors = useDragSensors();
  const isOpen = (id: string) => open.has(id);
  const toggle = (id: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  function onGoalDragEnd(e: DragEndEvent) {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    props.onMoveGoal(String(active.id), String(over.id));
  }

  const projectLabel = tree.project.name || UNNAMED;
  return (
    <div data-testid="import-tree" className="rounded-md bg-wg-base p-4">
      {/* 專案 */}
      <div data-testid="tree-project" data-highlighted={highlights?.project || undefined}>
        <div
          className={cn(
            "flex items-center gap-1.5 rounded-md py-1.5 pr-1.5 pl-1",
            highlights?.project && "border border-wg-error bg-wg-draft-bg",
          )}
        >
          <span className="size-6 shrink-0" aria-hidden />
          <Chevron open={open.has("project")} onToggle={() => toggle("project")} label={projectLabel} />
          <Folder size={18} className="shrink-0 text-wg-primary" aria-hidden />
          <span className={cn("min-w-0 flex-1 truncate text-base font-semibold", !tree.project.name && "text-wg-error")} data-testid="project-name">
            {projectLabel}
          </span>
          <span className="shrink-0 text-xs text-wg-muted">專案 · Lv.{tree.project.autonomyLevel}</span>
          {canEdit ? <IconButton icon={Pencil} label={`編輯專案：${projectLabel}`} size={30} onClick={props.onEditProject} /> : null}
        </div>
        <p className="mb-1 ml-[34px] truncate font-mono text-xs text-wg-muted" title={tree.project.executionPath}>
          {tree.project.executionPath}
        </p>
        {open.has("project") ? (
          <div data-testid="project-details" className="mt-1 mb-2 ml-[34px] flex flex-col gap-2.5 rounded-md bg-wg-surface px-3.5 py-3 text-sm">
            <Section title="說明描述">
              <MarkdownView source={tree.project.description} empty="（無說明）" />
            </Section>
            <Section title="通過標準">
              <MarkdownView source={tree.project.passCriteria} variant="criteria" empty="（尚未填寫）" />
            </Section>
          </div>
        ) : null}
      </div>

      {/* 目標與任務 */}
      <div className="mt-1 ml-3 border-l border-wg-line pl-3">
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onGoalDragEnd}>
          <SortableContext items={tree.goals.map((g) => g.key)} strategy={verticalListSortingStrategy}>
            {tree.goals.map((g, gi) => (
              <GoalBlock
                key={g.key}
                goal={g}
                index={gi}
                tree={tree}
                props={props}
                open={isOpen(`goal:${g.key}`)}
                isOpen={isOpen}
                toggle={toggle}
              />
            ))}
          </SortableContext>
        </DndContext>
        {canEdit ? (
          <Button variant="ghost" size="sm" iconLeft={Plus} className="my-1" onClick={props.onAddGoal}>
            新增目標
          </Button>
        ) : null}
      </div>
    </div>
  );
}
