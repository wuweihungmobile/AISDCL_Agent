"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

import { GoalListCard } from "@/components/domain/GoalListCard";
import { BackLink, PageTitle } from "@/components/domain/PageHeader";
import { TaskListCard } from "@/components/domain/TaskListCard";
import { EntityDialog } from "@/components/domain/entity/EntityDialog";
import type { EntityTarget } from "@/components/domain/entity/EntityEditor";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { useGoal, useProject } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/AuthProvider";

/** /projects/[projectId]/goals：目標列表（含各目標任務數與完成比例；與專案詳情共用 GoalListCard，可拖曳排序）。 */
export function GoalsListPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { canWrite } = useAuth();
  const q = useProject(projectId);
  const [entity, setEntity] = useState<EntityTarget | null>(null);

  return (
    <div>
      <BackLink href={`/projects/${projectId}`}>返回專案</BackLink>
      <PageTitle title="目標列表" subtitle={q.data ? `所屬專案：${q.data.name}` : undefined} />
      {q.isError ? (
        <ErrorState error={q.error} onRetry={() => q.refetch()} title="無法載入目標列表" />
      ) : !q.data ? (
        <PageSkeleton />
      ) : (
        <GoalListCard projectId={projectId} goals={q.data.goals} canWrite={canWrite} onAdd={() => setEntity({ kind: "goal", mode: "create", projectId })} />
      )}
      <EntityDialog target={entity} onClose={() => setEntity(null)} />
    </div>
  );
}

/** /projects/[projectId]/goals/[goalId]/tasks：任務列表（與目標詳情共用 TaskListCard）。 */
export function TasksListPage() {
  const { projectId, goalId } = useParams<{ projectId: string; goalId: string }>();
  const { canWrite } = useAuth();
  const q = useGoal(goalId);
  const [entity, setEntity] = useState<EntityTarget | null>(null);

  return (
    <div>
      <BackLink href={`/projects/${projectId}/goals/${goalId}`}>返回目標</BackLink>
      <PageTitle title="任務列表" subtitle={q.data ? `所屬目標：${q.data.name}` : undefined} />
      {q.isError ? (
        <ErrorState error={q.error} onRetry={() => q.refetch()} title="無法載入任務列表" />
      ) : !q.data ? (
        <PageSkeleton />
      ) : (
        <TaskListCard projectId={projectId} goalId={goalId} tasks={q.data.tasks} canWrite={canWrite} onAdd={() => setEntity({ kind: "task", mode: "create", goalId, projectId })} />
      )}
      <EntityDialog target={entity} onClose={() => setEntity(null)} />
    </div>
  );
}
