"use client";

import { CircleCheckBig, ClipboardCheck, Flame, ListChecks, Upload, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ProjectStatusChart } from "@/components/charts/ProjectStatusChart";
import { PageTitle } from "@/components/domain/PageHeader";
import { SignoffDialog, type SignoffTarget } from "@/components/domain/SignoffDialog";
import { CountBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { StatusLabel } from "@/components/ui/status-dot";
import { useAllProjects, useLatestRuns, useNotificationSummary, useSignoffQueue, useWeekCompletedTasks } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/AuthProvider";
import { weekStart } from "@/lib/domain/metrics";
import { projectStatus } from "@/lib/domain/status";
import { percent } from "@/lib/format";
import { cn } from "@/lib/utils";

function KpiCard({
  label,
  icon: Icon,
  value,
  delta,
  tone = "muted",
  testId,
}: {
  label: string;
  icon: LucideIcon;
  value: string;
  delta: string;
  tone?: "muted" | "primary" | "accent";
  testId: string;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-wg-muted">{label}</span>
        <span className="inline-flex size-[34px] items-center justify-center rounded-md bg-wg-tertiary">
          <Icon size={18} className="text-wg-primary" aria-hidden />
        </span>
      </div>
      <div data-testid={testId} className="mt-3 text-[32px] leading-none font-bold">
        {value}
      </div>
      <div className={cn("mt-2 text-[13px]", tone === "muted" && "text-wg-muted", tone === "primary" && "text-wg-primary", tone === "accent" && "text-wg-accent")}>{delta}</div>
    </Card>
  );
}

/**
 * 總覽儀表板（設計稿 1）：四張 KPI 卡、進行中的執行、待人工審批。
 * KPI：活躍專案數由專案 API 算；待審批草案數取 GET /notifications/summary 的 pendingSignoffs（跨專案，含目標、任務與匯入草案，
 * 契約 §4.5 G-06，取代 Phase 2 前端只算專案與草案目標的近似值）；
 * 本週完成任務數＝GET /monitor/task-totals 的 completed（v1.2，C-1；契約 §1.3.8、§4.5 G-08：from＝本週一 00:00、to 省略＝現在，
 * 一次請求、每 60 秒輪詢一次；取代 v1.1 對各專案扇出 task-trend 的近似做法，QA DEF-AC-009）；
 * 執行中 run 數＝各 EXECUTING 專案「最新批次」仍在跑的計數（契約 §4.5 G-07）。
 * 「進行中的執行」卡列 EXECUTING 專案與其最新批次的進度（tasksCompleted／tasksTotal）。
 * 「待人工審批」卡的清單仍由專案／目標 API 組（可直接點「審批」的項目）。
 */
export function DashboardView() {
  const { canWrite } = useAuth();
  const all = useAllProjects();
  const queue = useSignoffQueue();
  const summary = useNotificationSummary();
  const pendingSignoffs = summary.data?.pendingSignoffs;
  const [signoff, setSignoff] = useState<SignoffTarget | null>(null);
  // 本週一 00:00：頁面開著期間固定（跨過週一午夜才要重開頁面，與其他輪詢型數字一樣不為此特別處理）
  const [weekStartIso] = useState(() => weekStart().toISOString());

  const projects = all.data?.content ?? [];
  const live = projects.filter((p) => p.status === "EXECUTING");
  const active = projects.filter((p) => !["COMPLETED", "FAILED", "ARCHIVED"].includes(p.status));
  const loading = all.isLoading;

  const weekly = useWeekCompletedTasks(weekStartIso);
  const weeklyDelta = weekly.data ? (weekly.isError ? "更新失敗，顯示的是上一次的數字" : `本週一起 · 跨 ${weekly.data.projectsCounted} 個專案`) : weekly.isError ? "無法載入本週完成任務數" : "統計中…";
  const latest = useLatestRuns(live.map((p) => p.id));
  // 專案 EXECUTING 但最新批次已不在跑（例如剛結束、專案狀態還沒更新）不算；批次資料還沒回來時當作在跑
  const liveRunCount = live.filter((p) => {
    const run = latest.byProject[p.id];
    return !run || run.status === "RUNNING" || run.status === "INITIALIZING";
  }).length;

  return (
    <div>
      <PageTitle
        title="總覽儀表板"
        subtitle="AISDLC 自治開發 Agent · 全局健康度與待辦"
        actions={
          <Button asChild iconLeft={Upload}>
            <Link href="/import">匯入 BRD / PRD</Link>
          </Button>
        }
      />

      {all.isError ? (
        <ErrorState error={all.error} onRetry={() => all.refetch()} title="無法載入儀表板資料" />
      ) : (
        <>
          <div className="mb-6 grid grid-cols-4 gap-6 max-xl:grid-cols-2 max-md:grid-cols-1" data-testid="kpi-grid">
            {loading ? (
              [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[130px] rounded-lg" />)
            ) : (
              <>
                <KpiCard testId="kpi-active" label="活躍專案數" icon={CircleCheckBig} value={String(active.length)} delta={`共 ${all.data?.totalElements ?? 0} 個專案 · 執行中 ${live.length}`} />
                <KpiCard
                  testId="kpi-drafts"
                  label="待審批草案數"
                  icon={ClipboardCheck}
                  value={pendingSignoffs === undefined ? "—" : String(pendingSignoffs)}
                  delta={pendingSignoffs === undefined ? "待通知摘要載入" : pendingSignoffs > 0 ? "需 signoff 才可執行" : "全部已審批"}
                  tone={pendingSignoffs ? "accent" : "muted"}
                />
                <KpiCard
                  testId="kpi-week-done"
                  label="本週完成任務數"
                  icon={ListChecks}
                  value={weekly.data ? String(weekly.data.completed) : "—"}
                  delta={weeklyDelta}
                  tone={weekly.isError ? "accent" : "primary"}
                />
                <KpiCard
                  testId="kpi-runs"
                  label="執行中 run 數"
                  icon={Flame}
                  value={latest.loading ? "—" : String(liveRunCount)}
                  delta={latest.loading ? "查詢中…" : liveRunCount > 0 ? "進行中的執行批次" : "目前沒有執行中的批次"}
                  tone={liveRunCount > 0 ? "primary" : "muted"}
                />
              </>
            )}
          </div>

          <div className="grid grid-cols-[1.6fr_1fr] gap-6 max-lg:grid-cols-1">
            <Card className="px-[22px] py-5">
              <div className="mb-3.5 flex items-center justify-between">
                <CardTitle>進行中的執行</CardTitle>
                <Link href="/projects" className="text-sm text-wg-primary transition-opacity hover:opacity-85">
                  查看全部專案 →
                </Link>
              </div>
              {loading ? (
                <Skeleton className="h-24" />
              ) : live.length === 0 ? (
                <EmptyState title="目前沒有執行中的專案" description="專案進入「執行中」狀態後會顯示在這裡。" />
              ) : (
                live.map((p) => {
                  // 進度取最新批次（契約 §4.5 G-07：tasksCompleted／tasksTotal）；批次資料還沒回來前退回專案本身的計數
                  const run = latest.byProject[p.id];
                  const done = run ? run.tasksCompleted : p.tasksDone;
                  const total = run ? run.tasksTotal : p.tasksCount;
                  return (
                    <div key={p.id} data-testid="active-run" className="border-t border-wg-line py-3.5">
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <Link href={`/projects/${p.id}/execute`} className="truncate text-[15px] font-semibold text-wg-text transition-colors hover:text-wg-primary">
                          {p.name}
                        </Link>
                        <StatusLabel meta={projectStatus(p.status)} live className="shrink-0 text-[13px]" />
                      </div>
                      <Progress value={percent(done, total)} label={`${p.name} 任務完成度`} />
                      <div className="mt-1.5 flex justify-between text-xs text-wg-muted">
                        <span data-testid="active-run-progress">
                          {run ? `Run #${run.runNumber} · ` : ""}
                          {done} / {total} 任務完成
                        </span>
                        <span>{percent(done, total)}%</span>
                      </div>
                    </div>
                  );
                })
              )}
            </Card>

            <Card id="pending-signoff" className="scroll-mt-4 px-[22px] py-5">
              <div className="mb-3.5 flex items-center gap-2">
                <CardTitle>待人工審批</CardTitle>
                <CountBadge count={queue.count} data-testid="pending-count" />
              </div>
              <p className="mb-1.5 text-[13px] text-wg-muted">AI 草案 signoff 硬閘 — 未審批禁止執行</p>
              {queue.isLoading ? (
                <Skeleton className="mt-2 h-16" />
              ) : queue.items.length === 0 ? (
                <EmptyState title="沒有待審批的草案" />
              ) : (
                queue.items.map((d) => (
                  <div key={`${d.kind}:${d.id}`} data-testid="pending-item" className="flex items-center justify-between gap-2 border-t border-wg-line py-3">
                    <div className="min-w-0">
                      <Link
                        href={d.kind === "project" ? `/projects/${d.id}` : `/projects/${d.projectId}/goals/${d.id}`}
                        className="block max-w-[200px] truncate text-sm font-semibold text-wg-text transition-colors hover:text-wg-primary"
                      >
                        {d.name}
                      </Link>
                      <span className="text-xs text-wg-muted">{d.meta}</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={!canWrite}
                      title={canWrite ? undefined : "權限不足（唯讀角色不可審批）"}
                      aria-label={`審批：${d.name}`}
                      onClick={() => setSignoff({ kind: d.kind, id: d.id, name: d.name })}
                    >
                      審批
                    </Button>
                  </div>
                ))
              )}
            </Card>
          </div>

          {!loading ? <ProjectStatusChart projects={projects} /> : null}
        </>
      )}

      <SignoffDialog target={signoff} onClose={() => setSignoff(null)} />
    </div>
  );
}
