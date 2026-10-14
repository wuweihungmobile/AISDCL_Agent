"use client";

import { CircleCheck, Pencil, Target, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { ConfirmDialog } from "@/components/domain/ConfirmDialog";
import { BackLink } from "@/components/domain/PageHeader";
import { SignoffBanner } from "@/components/domain/SignoffBanner";
import { SignoffDialog, type SignoffTarget } from "@/components/domain/SignoffDialog";
import { TaskListCard } from "@/components/domain/TaskListCard";
import { EntityDialog } from "@/components/domain/entity/EntityDialog";
import type { EntityTarget } from "@/components/domain/entity/EntityEditor";
import { MarkdownView } from "@/components/markdown/MarkdownView";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { StatusLabel } from "@/components/ui/status-dot";
import { useToast } from "@/components/ui/toast";
import { useDeleteGoal, useGoal, useProject } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/AuthProvider";
import { goalStatus } from "@/lib/domain/status";
import { percent } from "@/lib/format";

/** 目標詳情（設計稿 4）：標題列、meta（所屬專案／進度／前置依賴 chips）、草案橫幅、說明＋通過標準 checklist、任務清單。 */
export function GoalDetailView() {
  const { projectId, goalId } = useParams<{ projectId: string; goalId: string }>();
  const router = useRouter();
  const toast = useToast();
  const { canWrite } = useAuth();
  const q = useGoal(goalId);
  const project = useProject(projectId);
  const del = useDeleteGoal();
  const [entity, setEntity] = useState<EntityTarget | null>(null);
  const [signoff, setSignoff] = useState<SignoffTarget | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const back = `/projects/${projectId}`;

  if (q.isError) {
    return (
      <div>
        <BackLink href={back}>返回專案</BackLink>
        <ErrorState error={q.error} onRetry={() => q.refetch()} title="無法載入目標" />
      </div>
    );
  }
  if (!q.data) {
    return (
      <div>
        <BackLink href={back}>返回專案</BackLink>
        <PageSkeleton />
      </div>
    );
  }

  const g = q.data;
  const meta = goalStatus(g.status);
  const goalsById = new Map((project.data?.goals ?? []).map((x) => [x.id, x]));
  const writeHint = canWrite ? undefined : "權限不足（唯讀角色）";

  return (
    <div>
      <BackLink href={back}>返回專案</BackLink>
      <div className="mb-1.5 flex items-center gap-3.5">
        <span className="inline-flex size-11 shrink-0 items-center justify-center rounded-[10px] bg-wg-tertiary">
          <Target size={24} className="text-wg-primary" aria-hidden />
        </span>
        <h2 className="text-[26px] font-bold max-md:text-2xl" data-testid="goal-title">
          {g.name}
        </h2>
        <StatusLabel meta={meta} dot={9} live={g.status === "IN_PROGRESS"} className="text-sm" />
      </div>
      <div className="mb-[18px] flex flex-wrap items-center gap-x-5 gap-y-1.5 pl-[58px] text-sm text-wg-muted max-md:pl-0">
        <span>
          所屬：
          <Link href={back} className="transition-colors hover:text-wg-primary">
            {project.data?.name ?? "…"}
          </Link>
        </span>
        <span>
          進度 {g.completedTaskCount} / {g.taskCount} ({percent(g.completedTaskCount, g.taskCount)}%)
        </span>
        <span className="inline-flex flex-wrap items-center gap-1.5" data-testid="goal-deps">
          前置依賴：
          {g.dependsOn.length === 0 ? (
            "無"
          ) : (
            g.dependsOn.map((id) => {
              const dep = goalsById.get(id);
              return (
                <Link
                  key={id}
                  href={`/projects/${projectId}/goals/${id}`}
                  className="inline-flex items-center gap-1 rounded-sm border border-wg-line bg-wg-surface px-2 py-0.5 text-[13px] text-wg-text transition-colors hover:border-wg-primary hover:text-wg-primary"
                >
                  {dep?.name ?? id.slice(0, 8)}
                  {dep?.status === "COMPLETED" ? (
                    <CircleCheck size={13} className="text-wg-primary" aria-label="已完成" />
                  ) : null}
                </Link>
              );
            })
          )}
        </span>
      </div>

      {!g.signedOff ? (
        <SignoffBanner
          kind="goal"
          canApprove={canWrite}
          onApprove={() => setSignoff({ kind: "goal", id: g.id, name: g.name })}
        />
      ) : null}

      <div className="mb-6 grid grid-cols-2 gap-6 max-lg:grid-cols-1">
        <Card className="min-w-0 px-[22px] py-5">
          <CardTitle className="mb-3.5">目標說明</CardTitle>
          <MarkdownView source={g.description} empty="尚未填寫目標說明" />
        </Card>
        <Card className="min-w-0 px-[22px] py-5">
          <CardTitle className="mb-3.5">通過標準</CardTitle>
          <MarkdownView source={g.passCriteria} variant="criteria" />
        </Card>
      </div>

      <TaskListCard
        projectId={projectId}
        goalId={g.id}
        tasks={g.tasks}
        canWrite={canWrite}
        onAdd={() => setEntity({ kind: "task", mode: "create", goalId: g.id, projectId })}
      />

      <div className="flex flex-wrap gap-2.5">
        <Button
          variant="ghost"
          iconLeft={Pencil}
          disabled={!canWrite}
          title={writeHint}
          onClick={() => setEntity({ kind: "goal", mode: "edit", id: g.id, projectId })}
        >
          編輯目標
        </Button>
        <Button
          variant="ghost"
          iconLeft={Trash2}
          disabled={!canWrite}
          title={writeHint}
          className="text-wg-accent hover:text-wg-accent-strong"
          onClick={() => setConfirmDelete(true)}
        >
          刪除目標
        </Button>
      </div>

      <EntityDialog target={entity} onClose={() => setEntity(null)} />
      <SignoffDialog target={signoff} onClose={() => setSignoff(null)} />
      <ConfirmDialog
        open={confirmDelete}
        title="刪除目標"
        confirmLabel="確認刪除"
        onClose={() => setConfirmDelete(false)}
        onConfirm={async () => {
          await del.mutateAsync(g.id);
          toast.success(`已刪除目標「${g.name}」`);
          router.replace(back);
        }}
      >
        確定刪除目標「<b>{g.name}</b>」？其下任務會一併軟刪除；含執行中任務時無法刪除。
      </ConfirmDialog>
    </div>
  );
}
