"use client";

import { Clock, FileText, Flame, Pencil, Repeat, RotateCcw, Trash2 } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";

import { ConfirmDialog } from "@/components/domain/ConfirmDialog";
import { LogPanel } from "@/components/domain/LogPanel";
import { BackLink } from "@/components/domain/PageHeader";
import { SignoffBanner } from "@/components/domain/SignoffBanner";
import { SignoffDialog, type SignoffTarget } from "@/components/domain/SignoffDialog";
import { describeDeleteError } from "@/components/domain/entity/apiErrors";
import { EntityDialog } from "@/components/domain/entity/EntityDialog";
import type { EntityTarget } from "@/components/domain/entity/EntityEditor";
import { MarkdownView } from "@/components/markdown/MarkdownView";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { StatusLabel } from "@/components/ui/status-dot";
import { useToast } from "@/components/ui/toast";
import { describeError } from "@/lib/api/client";
import { useDeleteTask, useGoal, useProject, useRetryTask, useTask } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/AuthProvider";
import { isRetryable, taskStatus } from "@/lib/domain/status";
import { formatClock, formatDateTime, formatNumber, manualRetryLabel, retryLabel } from "@/lib/format";

function Metric({ icon, label, value, testId }: { icon: ReactNode; label: string; value: string; testId: string }) {
  return (
    <Card className="px-[18px] py-4">
      <div className="flex items-center gap-1.5 text-[13px] text-wg-muted">
        {icon}
        {label}
      </div>
      <div data-testid={testId} className="mt-1.5 font-mono text-2xl font-bold">
        {value}
      </div>
    </Card>
  );
}

/** 任務詳情（設計稿 5）：標題列、meta（麵包屑／重試／Agent）、三張指標卡、說明＋通過標準、執行日誌（可搜尋）、底部行動。 */
export function TaskDetailView() {
  const { projectId, goalId, taskId } = useParams<{ projectId: string; goalId: string; taskId: string }>();
  const router = useRouter();
  const toast = useToast();
  const { canWrite } = useAuth();
  const q = useTask(taskId);
  const goal = useGoal(goalId);
  const project = useProject(projectId);
  const retry = useRetryTask();
  const del = useDeleteTask();
  const [entity, setEntity] = useState<EntityTarget | null>(null);
  const [signoff, setSignoff] = useState<SignoffTarget | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const back = `/projects/${projectId}/goals/${goalId}`;

  if (q.isError) {
    return (
      <div>
        <BackLink href={back}>返回目標</BackLink>
        <ErrorState error={q.error} onRetry={() => q.refetch()} title="無法載入任務" />
      </div>
    );
  }
  if (!q.data) {
    return (
      <div>
        <BackLink href={back}>返回目標</BackLink>
        <PageSkeleton />
      </div>
    );
  }

  const t = q.data;
  const meta = taskStatus(t.status);
  const writeHint = canWrite ? undefined : "權限不足（唯讀角色）";
  const canRetry = isRetryable(t.status);

  async function onRetry() {
    try {
      const r = await retry.mutateAsync(t.id);
      toast.success(`已重新排入佇列：${manualRetryLabel(r.retryCount, r.maxRetries)}`);
    } catch (e) {
      toast.error(`重試失敗：${describeError(e)}`);
    }
  }

  return (
    <div>
      <BackLink href={back}>返回目標</BackLink>
      <div className="mb-1.5 flex items-center gap-3.5">
        <span className="inline-flex size-11 shrink-0 items-center justify-center rounded-[10px] bg-wg-tertiary">
          <FileText size={24} className="text-wg-primary" aria-hidden />
        </span>
        <h2 className="text-[26px] font-bold max-md:text-2xl" data-testid="task-title">
          {t.name}
        </h2>
        <StatusLabel meta={meta} dot={9} live={t.status === "RUNNING"} className="text-sm" />
      </div>
      <div className="mb-[18px] pl-[58px] text-sm text-wg-muted max-md:pl-0" data-testid="task-meta">
        {project.data?.name ?? "…"} › {goal.data?.name ?? "…"}　·　重試 {retryLabel(t.retryCount, t.maxRetries)}　·　Agent {t.assignedAgent ?? "—"}
      </div>

      {!t.signedOff ? <SignoffBanner kind="task" canApprove={canWrite} onApprove={() => setSignoff({ kind: "task", id: t.id, name: t.name })} /> : null}

      <div className="mb-6 grid grid-cols-3 gap-4 max-md:grid-cols-1">
        <Metric icon={<Clock size={15} aria-hidden />} label="開始時間" value={formatClock(t.startedAt)} testId="metric-started" />
        <Metric icon={<Flame size={15} aria-hidden />} label="Token 消耗" value={formatNumber(t.actualTokens)} testId="metric-tokens" />
        <Metric icon={<Repeat size={15} aria-hidden />} label="重試次數" value={retryLabel(t.retryCount, t.maxRetries)} testId="metric-retries" />
      </div>

      <div className="mb-6 grid grid-cols-2 gap-6 max-lg:grid-cols-1">
        <Card className="min-w-0 px-[22px] py-5">
          <CardTitle className="mb-3.5">任務說明</CardTitle>
          <MarkdownView source={t.description} empty="尚未填寫任務說明" />
        </Card>
        <Card className="min-w-0 px-[22px] py-5">
          <CardTitle className="mb-3.5">通過標準</CardTitle>
          <MarkdownView source={t.passCriteria} variant="criteria" />
          {t.evaluatorCommand || t.expectedOutputRegex ? (
            <dl className="mt-4 flex flex-col gap-2 border-t border-wg-line pt-3 text-[13px]">
              {t.evaluatorCommand ? (
                <div>
                  <dt className="text-wg-muted">驗證命令</dt>
                  <dd className="mt-0.5 rounded-md border border-wg-line bg-wg-base px-2.5 py-1.5 font-mono break-all">{t.evaluatorCommand}</dd>
                </div>
              ) : null}
              {t.expectedOutputRegex ? (
                <div>
                  <dt className="text-wg-muted">期望輸出 Regex</dt>
                  <dd className="mt-0.5 rounded-md border border-wg-line bg-wg-base px-2.5 py-1.5 font-mono break-all">{t.expectedOutputRegex}</dd>
                </div>
              ) : null}
            </dl>
          ) : null}
        </Card>
      </div>

      <Card className="mb-6 px-[22px] py-5">
        <CardTitle className="mb-3.5">執行日誌</CardTitle>
        <LogPanel log={t.executionLog} />
        {t.executionHistory.length > 0 ? (
          <div className="mt-4 border-t border-wg-line pt-3" data-testid="execution-history">
            <h4 className="mb-2 text-sm font-semibold">執行歷史</h4>
            <ul className="flex flex-col gap-1 text-[13px] text-wg-muted">
              {t.executionHistory.map((s) => (
                <li key={s.id} className="flex flex-wrap gap-x-3">
                  <span className="font-mono">#{s.stepNumber}</span>
                  <span className="text-wg-text">{s.action}</span>
                  <span>{s.status}</span>
                  <span>{formatNumber(s.tokensUsed)} tokens</span>
                  <span>{formatDateTime(s.timestamp)}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </Card>

      <div className="flex flex-wrap gap-2.5">
        <Button
          iconLeft={RotateCcw}
          disabled={!canWrite || !canRetry}
          loading={retry.isPending}
          onClick={onRetry}
          title={!canWrite ? writeHint : canRetry ? undefined : "只有失敗（FAILED）或待人工（ESCALATED）的任務可以重試"}
        >
          重試
        </Button>
        <Button variant="ghost" iconLeft={Pencil} disabled={!canWrite} title={writeHint} onClick={() => setEntity({ kind: "task", mode: "edit", id: t.id, goalId, projectId })}>
          編輯
        </Button>
        <Button variant="ghost" iconLeft={Trash2} disabled={!canWrite} title={writeHint} className="text-wg-accent hover:text-wg-accent-strong" onClick={() => setConfirmDelete(true)}>
          刪除
        </Button>
      </div>

      <EntityDialog target={entity} onClose={() => setEntity(null)} />
      <SignoffDialog target={signoff} onClose={() => setSignoff(null)} />
      <ConfirmDialog
        open={confirmDelete}
        title="刪除任務"
        confirmLabel="確認刪除"
        formatError={describeDeleteError}
        onClose={() => setConfirmDelete(false)}
        onConfirm={async () => {
          await del.mutateAsync(t.id);
          toast.success(`已刪除任務「${t.name}」`);
          router.replace(back);
        }}
      >
        確定刪除任務「<b>{t.name}</b>」？執行中（RUNNING）的任務不可直接刪除；專案有進行中的執行批次時也不能刪除。
      </ConfirmDialog>
    </div>
  );
}
