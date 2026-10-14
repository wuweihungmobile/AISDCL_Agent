"use client";

import { Activity, Folder, Pencil, Play, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { ConfirmDialog } from "@/components/domain/ConfirmDialog";
import { GoalListCard } from "@/components/domain/GoalListCard";
import { BackLink } from "@/components/domain/PageHeader";
import { SignoffBanner } from "@/components/domain/SignoffBanner";
import { SignoffDialog, type SignoffTarget } from "@/components/domain/SignoffDialog";
import { EntityDialog } from "@/components/domain/entity/EntityDialog";
import type { EntityTarget } from "@/components/domain/entity/EntityEditor";
import { MarkdownView } from "@/components/markdown/MarkdownView";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { StatusLabel } from "@/components/ui/status-dot";
import { useToast } from "@/components/ui/toast";
import { useDeleteProject, useProject } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/AuthProvider";
import { projectStatus } from "@/lib/domain/status";
import { formatDate } from "@/lib/format";

/** 專案詳情（設計稿 3）：標題列、meta、signoff 警示橫幅、基本資訊／專案說明兩欄卡、目標清單（可拖曳排序）、底部行動。 */
export function ProjectDetailView() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const toast = useToast();
  const { canWrite } = useAuth();
  const q = useProject(projectId);
  const del = useDeleteProject();
  const [entity, setEntity] = useState<EntityTarget | null>(null);
  const [signoff, setSignoff] = useState<SignoffTarget | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  if (q.isError) {
    return (
      <div>
        <BackLink href="/projects">返回專案列表</BackLink>
        <ErrorState error={q.error} onRetry={() => q.refetch()} title="無法載入專案" />
      </div>
    );
  }
  if (!q.data) {
    return (
      <div>
        <BackLink href="/projects">返回專案列表</BackLink>
        <PageSkeleton />
      </div>
    );
  }

  const p = q.data;
  const meta = projectStatus(p.status);
  const writeHint = canWrite ? undefined : "權限不足（唯讀角色）";

  return (
    <div>
      <BackLink href="/projects">返回專案列表</BackLink>
      <div className="mb-1.5 flex items-center gap-3.5">
        <span className="inline-flex size-12 shrink-0 items-center justify-center rounded-[10px] bg-wg-tertiary">
          <Folder size={26} className="text-wg-primary" aria-hidden />
        </span>
        <h2 className="text-[28px] font-bold max-md:text-2xl" data-testid="project-title">
          {p.name}
        </h2>
        <StatusLabel meta={meta} dot={9} live={p.status === "EXECUTING"} className="text-sm" />
      </div>
      <div className="mb-[18px] flex flex-wrap gap-x-5 gap-y-1 pl-[62px] text-sm text-wg-muted max-md:pl-0">
        <span>自治等級 Lv.{p.autonomyLevel}</span>
        <span>
          目標 {p.goalsCount} · 任務 {p.tasksCount}
        </span>
        <span>更新 {formatDate(p.updatedAt)}</span>
        <span>建立者 {p.createdBy ?? "—"}</span>
      </div>

      {!p.signedOff ? (
        <SignoffBanner
          kind="project"
          canApprove={canWrite}
          onApprove={() => setSignoff({ kind: "project", id: p.id, name: p.name })}
        />
      ) : null}

      <div className="mb-6 grid grid-cols-2 gap-6 max-lg:grid-cols-1">
        <Card className="min-w-0 px-[22px] py-5">
          <CardTitle className="mb-3.5">基本資訊</CardTitle>
          <div className="mb-1 text-[13px] text-wg-muted">執行路徑</div>
          <div
            data-testid="project-path"
            className="mb-4 rounded-md border border-wg-line bg-wg-base px-3 py-2 font-mono text-sm break-all"
          >
            {p.executionPath}
          </div>
          <div className="mb-2 text-[13px] text-wg-muted">通過標準</div>
          <MarkdownView source={p.passCriteria} variant="criteria" />
        </Card>
        <Card className="min-w-0 px-[22px] py-5">
          <CardTitle className="mb-3.5">專案說明</CardTitle>
          <MarkdownView source={p.description} empty="尚未填寫專案說明" />
        </Card>
      </div>

      <GoalListCard
        projectId={p.id}
        goals={p.goals}
        canWrite={canWrite}
        onAdd={() => setEntity({ kind: "goal", mode: "create", projectId: p.id })}
      />

      <div className="flex flex-wrap gap-2.5">
        <Button asChild iconLeft={Play}>
          <Link href={`/projects/${p.id}/execute`}>執行專案</Link>
        </Button>
        <Button asChild variant="ghost" iconLeft={Activity}>
          <Link href={`/projects/${p.id}/monitor`}>查看監控</Link>
        </Button>
        <Button
          variant="ghost"
          iconLeft={Pencil}
          disabled={!canWrite}
          title={writeHint}
          onClick={() => setEntity({ kind: "project", mode: "edit", id: p.id })}
        >
          編輯專案
        </Button>
        <Button
          variant="ghost"
          iconLeft={Trash2}
          disabled={!canWrite}
          title={writeHint}
          className="text-wg-accent hover:text-wg-accent-strong"
          onClick={() => setConfirmDelete(true)}
        >
          刪除專案
        </Button>
      </div>

      <EntityDialog target={entity} onClose={() => setEntity(null)} />
      <SignoffDialog target={signoff} onClose={() => setSignoff(null)} />
      <ConfirmDialog
        open={confirmDelete}
        title="刪除專案"
        confirmLabel="確認刪除"
        onClose={() => setConfirmDelete(false)}
        onConfirm={async () => {
          await del.mutateAsync(p.id);
          toast.success(`已刪除專案「${p.name}」`);
          router.replace("/projects");
        }}
      >
        確定刪除專案「<b>{p.name}</b>」？其下所有目標與任務會一併軟刪除。執行中的專案不可刪除。
      </ConfirmDialog>
    </div>
  );
}
