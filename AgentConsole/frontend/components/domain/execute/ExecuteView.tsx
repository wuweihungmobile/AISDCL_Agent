"use client";

import { useQueries } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";

import { ConfirmDialog } from "@/components/domain/ConfirmDialog";
import { BackLink, PageTitle } from "@/components/domain/PageHeader";
import { SignoffDialog } from "@/components/domain/SignoffDialog";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { useNow } from "@/hooks/useNow";
import { useRunStream } from "@/hooks/useRunStream";
import { describeError } from "@/lib/api/client";
import { listTasks } from "@/lib/api/endpoints";
import {
  qk,
  useCancelExecution,
  useCheckpoints,
  useExecution,
  useExecutionDag,
  usePauseExecution,
  useProject,
  useProjectExecutions,
  useRestoreExecution,
  useResumeExecution,
  useReviewExecution,
  useSettingsCategory,
  useStartExecution,
} from "@/lib/api/queries";
import type { Checkpoint, ReviewDecision, ReviewItem, StartExecutionRequest } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { controlButtons, type ControlAction } from "@/lib/domain/runControl";
import {
  buildScope,
  initialSelection,
  lockReport,
  type ScopeGoal,
  type ScopeTask,
  type Selection,
} from "@/lib/domain/scope";
import { isRunTerminal } from "@/lib/domain/status";
import { CheckpointDialog } from "./CheckpointDialog";
import { ControlCard } from "./ControlCard";
import { DagCard } from "./DagCard";
import { LiveLogCard } from "./LiveLogCard";
import { LockBanner, RunSelect } from "./parts";
import { ProgressCard } from "./ProgressCard";
import { ReviewCard } from "./ReviewCard";
import { reviewDoneMessage } from "./reviewHelp";
import { describeStartError, type StartErrorView } from "./startErrors";

/** 批次下拉的列表輪詢：批次進行中時 run 的新增（例如後續批次）要看得到；遠高於契約的 10 秒地板。 */
const RUN_LIST_POLL_MS = 30_000;
const DEFAULT_WARN_THRESHOLD = 0.8;

/** 解析 Token 數輸入（允許千分位逗號）：空字串＝未填（undefined）；其餘須為正整數，否則 NaN。 */
export function parseTokenInput(raw: string): number | undefined {
  const text = raw.replace(/[,\s]/g, "");
  if (text === "") return undefined;
  return /^[1-9]\d{0,14}$/.test(text) ? Number(text) : Number.NaN;
}

/**
 * 專案執行頁（設計稿畫面 7；契約 §1.2、§2、§4.2；PRD §5.3）：
 * 返回連結、標題、鎖定橫幅、執行控制卡（等級／預算／範圍樹／按鈕）、執行進度卡、DAG 卡、即時日誌卡、待審核項目卡；
 * 頁首的批次下拉可切換目前看的批次（預設最新）。批次進度與狀態＝REST 當底＋SSE 即時修補（hooks/useRunStream）。
 */
export function ExecuteView() {
  const { projectId } = useParams<{ projectId: string }>();
  const { canWrite, status: authStatus } = useAuth();
  const toast = useToast();

  const project = useProject(projectId);
  const runsQ = useProjectExecutions(projectId, { size: 20, sort: "startedAt,desc" }, { pollMs: RUN_LIST_POLL_MS });
  const runs = useMemo(() => runsQ.data?.content ?? [], [runsQ.data]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const activeRunId = selectedRunId ?? runs[0]?.id ?? null;
  const isLatest = !activeRunId || runs.length === 0 || activeRunId === runs[0]?.id;

  const detailQ = useExecution(activeRunId);
  const detail = detailQ.data;
  const summary = runs.find((r) => r.id === activeRunId);
  const runStatus = detail?.status ?? summary?.status;
  const terminal = isRunTerminal(runStatus);

  const stream = useRunStream(activeRunId, { enabled: authStatus === "authed", runStatus });
  const dagQ = useExecutionDag(activeRunId, Boolean(detail) && !terminal);
  const now = useNow(Boolean(detail) && !terminal);

  // ── 系統參數：預設預算與 Token 警告閾值（契約 §4.2 E-04、E-11）──
  const execSettings = useSettingsCategory("execution");
  const settingValue = (key: string) => execSettings.data?.find((c) => c.key === key)?.value;
  const warnRaw = Number(settingValue("tokenBudgetWarningThreshold"));
  const warnThreshold = Number.isFinite(warnRaw) && warnRaw > 0 && warnRaw < 1 ? warnRaw : DEFAULT_WARN_THRESHOLD;
  const defaultBudget = (() => {
    const n = Number(settingValue("globalTokenBudget"));
    return Number.isFinite(n) && n > 0 ? Math.round(n).toLocaleString("en-US") : ""; // 設計稿：100,000（千分位；輸入時逗號可有可無，parseTokenInput 會去掉）
  })();

  // ── 控制表單（草稿 null＝沿用預設，避免用 effect 把預設值灌進 state）──
  const goals: ScopeGoal[] = useMemo(
    () => [...(project.data?.goals ?? [])].sort((a, b) => a.sortOrder - b.sortOrder),
    [project.data],
  );
  const [levelDraft, setLevelDraft] = useState<number | null>(null);
  const [budgetDraft, setBudgetDraft] = useState<string | null>(null);
  const [selectionDraft, setSelectionDraft] = useState<Selection | null>(null);
  const [taskLimit, setTaskLimit] = useState("");
  const [goalLimit, setGoalLimit] = useState("");
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(new Set());
  const level = levelDraft ?? project.data?.autonomyLevel ?? 3;
  const budget = budgetDraft ?? defaultBudget;
  const selection = selectionDraft ?? initialSelection(goals);

  // 展開的目標才載入任務（執行範圍樹的任務層級；契約 §4.6 G-E1）
  const expandedIds = [...expanded];
  const taskQueries = useQueries({
    queries: expandedIds.map((id) => ({
      queryKey: qk.tasks(id),
      queryFn: ({ signal }: { signal: AbortSignal }) => listTasks(id, { signal }),
      enabled: authStatus === "authed",
      staleTime: 15_000,
    })),
  });
  const tasksByGoal: Record<string, ScopeTask[] | undefined> = {};
  const tasksLoading: Record<string, boolean> = {};
  expandedIds.forEach((id, i) => {
    tasksByGoal[id] = taskQueries[i]?.data;
    tasksLoading[id] = Boolean(taskQueries[i]?.isPending);
  });

  const lock = lockReport(project.data?.signedOff ?? true, goals, selection, tasksByGoal);
  const nameOf = (id: string): string | undefined =>
    goals.find((g) => g.id === id)?.name ?? Object.values(tasksByGoal).flatMap((t) => t ?? []).find((t) => t.id === id)?.name;

  // ── 動作 ──
  const startM = useStartExecution();
  const pauseM = usePauseExecution();
  const resumeM = useResumeExecution();
  const cancelM = useCancelExecution();
  const restoreM = useRestoreExecution();
  const reviewM = useReviewExecution();
  const [budgetError, setBudgetError] = useState<string | undefined>();
  const [startError, setStartError] = useState<StartErrorView | null>(null);
  const [signoffOpen, setSignoffOpen] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [checkpointOpen, setCheckpointOpen] = useState(false);
  const cpQ = useCheckpoints(activeRunId, checkpointOpen);

  const pendingAction: ControlAction | null = startM.isPending
    ? "start"
    : pauseM.isPending
      ? "pause"
      : resumeM.isPending
        ? "resume"
        : cancelM.isPending
          ? "cancel"
          : restoreM.isPending
            ? "restore"
            : null;
  const busy = pendingAction !== null || reviewM.isPending;

  const runForButtons = detail ?? summary;
  const buttons = controlButtons({
    run: runForButtons ? { status: runForButtons.status, bridgeStatus: detail?.bridgeStatus } : null,
    canWrite,
    locked: lock.locked,
    busy,
    isLatest,
    hasCheckpoints: cpQ.data ? cpQ.data.length > 0 : undefined,
  });
  const frozen = Boolean(runForButtons) && !isRunTerminal(runForButtons?.status);

  async function doStart() {
    const built = buildScope(selection, goals);
    if (!built.scope) {
      toast.error("請至少選擇一個目標或任務");
      return;
    }
    const budgetNum = parseTokenInput(budget);
    const taskTokens = parseTokenInput(taskLimit);
    const goalTokens = parseTokenInput(goalLimit);
    if (Number.isNaN(budgetNum) || Number.isNaN(taskTokens) || Number.isNaN(goalTokens)) {
      setBudgetError("Token 數須為大於 0 的整數（預算與上限皆同）");
      return;
    }
    setBudgetError(undefined);
    setStartError(null);
    const limits = taskTokens || goalTokens ? { ...(taskTokens ? { taskTokens } : {}), ...(goalTokens ? { goalTokens } : {}) } : undefined;
    const body: StartExecutionRequest = {
      autonomyLevel: level,
      ...(budgetNum ? { tokenBudget: budgetNum } : {}),
      scope: { ...built.scope, ...(limits ? { limits } : {}) },
    };
    try {
      const run = await startM.mutateAsync({ projectId, body });
      setSelectedRunId(run.id);
      toast.success(`已啟動 Run #${run.runNumber}`);
    } catch (err) {
      setStartError(describeStartError(err, nameOf));
    }
  }

  async function control(fn: () => Promise<unknown>, done: string) {
    try {
      await fn();
      toast.success(done);
    } catch (err) {
      toast.error(describeError(err));
    }
  }

  function onAction(action: ControlAction) {
    if (action === "start") void doStart();
    else if (action === "restore") setCheckpointOpen(true);
    else if (action === "cancel") setConfirmCancel(true);
    else if (!activeRunId) return;
    else if (action === "pause") void control(() => pauseM.mutateAsync(activeRunId), "已要求暫停，會在下一個步驟邊界生效");
    else if (action === "resume") void control(() => resumeM.mutateAsync(activeRunId), "已恢復執行");
  }

  async function onRestore(cp: Checkpoint) {
    if (!activeRunId) return;
    await restoreM.mutateAsync({ runId: activeRunId, checkpointId: cp.id });
    toast.success(`已從斷點「${cp.name}」恢復`);
    stream.reconnect();
  }

  async function onDecide(review: ReviewItem, decision: ReviewDecision, comment: string) {
    if (!activeRunId) return;
    const res = await reviewM.mutateAsync({ runId: activeRunId, reviewId: review.id, decision, comment: comment || undefined });
    toast.success(reviewDoneMessage(decision, res.followUpRunId !== null));
    if (res.followUpRunId) setSelectedRunId(res.followUpRunId);
    else stream.reconnect(); // RETRY 走 restore：終態 run 重新執行，原連線早已關閉
  }

  const toggleExpand = (goalId: string) =>
    setExpanded((cur) => {
      const next = new Set(cur);
      if (next.has(goalId)) next.delete(goalId);
      else next.add(goalId);
      return next;
    });

  if (project.isError) {
    return (
      <div>
        <BackLink href={`/projects/${projectId}`}>返回專案</BackLink>
        <ErrorState error={project.error} onRetry={() => project.refetch()} title="無法載入專案" />
      </div>
    );
  }
  if (!project.data) {
    return (
      <div>
        <BackLink href={`/projects/${projectId}`}>返回專案</BackLink>
        <PageSkeleton />
      </div>
    );
  }
  const p = project.data;

  return (
    <div data-testid="execute-view">
      <BackLink href={`/projects/${projectId}`}>返回專案</BackLink>
      <PageTitle
        icon={Play}
        title={`專案執行：${p.name}`}
        subtitle="漸進式自治 · DAG 排程 · 斷點續行"
        className="[&_h2]:text-[28px]"
        actions={
          runs.length > 0 ? (
            <RunSelect
              runs={runs}
              value={activeRunId ?? ""}
              onChange={(id) => {
                setSelectedRunId(id);
                setStartError(null);
              }}
            />
          ) : null
        }
      />

      {!p.signedOff ? <LockBanner canApprove={canWrite} onApprove={() => setSignoffOpen(true)} /> : null}

      <div className="mb-0 grid grid-cols-[1fr_1.2fr] gap-6 max-lg:grid-cols-1">
        <ControlCard
          goals={goals}
          tasksByGoal={tasksByGoal}
          tasksLoading={tasksLoading}
          expanded={expanded}
          onToggleExpand={toggleExpand}
          selection={selection}
          onSelection={setSelectionDraft}
          level={level}
          onLevel={setLevelDraft}
          budget={budget}
          onBudget={(v) => {
            setBudgetDraft(v);
            setBudgetError(undefined);
          }}
          budgetError={budgetError}
          taskLimit={taskLimit}
          onTaskLimit={setTaskLimit}
          goalLimit={goalLimit}
          onGoalLimit={setGoalLimit}
          frozen={frozen}
          buttons={buttons}
          pendingAction={pendingAction}
          onAction={onAction}
          lock={lock}
          startError={startError}
          onApprove={() => setSignoffOpen(true)}
        />
        <div className="flex min-w-0 flex-col gap-6">
          {detailQ.isError && !detail ? (
            <ErrorState error={detailQ.error} onRetry={() => detailQ.refetch()} title="無法載入執行狀態" />
          ) : (
            <ProgressCard run={detail} now={now} warnThreshold={warnThreshold} />
          )}
          <DagCard dag={dagQ.data} live={stream.live.taskStatus} loading={dagQ.isPending && Boolean(activeRunId)} error={dagQ.isError ? dagQ.error : null} onRetry={() => dagQ.refetch()} />
        </div>
      </div>

      <LiveLogCard live={stream.live} connection={stream.connection} onReconnect={stream.reconnect} />
      <ReviewCard projectId={projectId} reviews={detail?.pendingReviews ?? []} canWrite={canWrite} onDecide={onDecide} />

      <SignoffDialog target={signoffOpen ? { kind: "project", id: p.id, name: p.name } : null} onClose={() => setSignoffOpen(false)} />
      <ConfirmDialog
        open={confirmCancel}
        title="取消執行"
        confirmLabel="確認取消"
        onClose={() => setConfirmCancel(false)}
        onConfirm={async () => {
          if (!activeRunId) return;
          await cancelM.mutateAsync(activeRunId);
          toast.success("已要求取消，引擎收尾後狀態會變為已取消");
          setConfirmCancel(false);
        }}
      >
        確定取消這個執行批次？進行中的任務會被終止，尚未開始的任務一併取消；取消後可重新啟動或從斷點恢復。
      </ConfirmDialog>
      <CheckpointDialog
        open={checkpointOpen}
        onClose={() => setCheckpointOpen(false)}
        checkpoints={cpQ.data}
        loading={cpQ.isPending}
        error={cpQ.isError ? cpQ.error : null}
        onRetry={() => cpQ.refetch()}
        onRestore={onRestore}
      />
    </div>
  );
}
