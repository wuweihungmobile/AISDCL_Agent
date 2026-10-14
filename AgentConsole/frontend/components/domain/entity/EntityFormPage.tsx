"use client";

/**
 * 整頁版的建立／編輯表單（PRD §4.2 的 new／edit 路由，可深連結）：與 Dialog 共用同一個 EntityEditor。
 * 成功後導向該實體的詳情頁；取消回上一頁。
 */
import { useParams, useRouter } from "next/navigation";

import { BackLink, PageTitle } from "@/components/domain/PageHeader";
import { Card } from "@/components/ui/card";
import { EntityEditor, entityTitle, type EntityKind, type EntityTarget } from "./EntityEditor";

function buildTarget(
  kind: EntityKind,
  mode: "create" | "edit",
  p: { projectId?: string; goalId?: string; taskId?: string },
): EntityTarget | null {
  if (kind === "project") {
    if (mode === "create") return { kind, mode };
    return p.projectId ? { kind, mode, id: p.projectId } : null;
  }
  if (kind === "goal") {
    if (!p.projectId) return null;
    if (mode === "create") return { kind, mode, projectId: p.projectId };
    return p.goalId ? { kind, mode, id: p.goalId, projectId: p.projectId } : null;
  }
  if (!p.projectId || !p.goalId) return null;
  if (mode === "create") return { kind, mode, goalId: p.goalId, projectId: p.projectId };
  return p.taskId ? { kind, mode, id: p.taskId, goalId: p.goalId, projectId: p.projectId } : null;
}

export function EntityFormPage({ kind, mode }: { kind: EntityKind; mode: "create" | "edit" }) {
  const params = useParams<{ projectId?: string; goalId?: string; taskId?: string }>();
  const router = useRouter();
  const target = buildTarget(kind, mode, params);
  if (!target) return null;

  const backHref =
    kind === "project"
      ? mode === "edit"
        ? `/projects/${params.projectId}`
        : "/projects"
      : kind === "goal"
        ? mode === "edit"
          ? `/projects/${params.projectId}/goals/${params.goalId}`
          : `/projects/${params.projectId}`
        : mode === "edit"
          ? `/projects/${params.projectId}/goals/${params.goalId}/tasks/${params.taskId}`
          : `/projects/${params.projectId}/goals/${params.goalId}`;

  function detailHref(id: string): string {
    if (kind === "project") return `/projects/${id}`;
    if (kind === "goal") return `/projects/${params.projectId}/goals/${id}`;
    return `/projects/${params.projectId}/goals/${params.goalId}/tasks/${id}`;
  }

  return (
    <div className="max-w-[960px]">
      <BackLink href={backHref}>返回</BackLink>
      <PageTitle title={entityTitle(target)} />
      <Card className="p-[22px]">
        <EntityEditor
          key={JSON.stringify(target)}
          target={target}
          variant="page"
          onCancel={() => router.push(backHref)}
          onDone={(done) => router.push(detailHref(done.id))}
        />
      </Card>
    </div>
  );
}
