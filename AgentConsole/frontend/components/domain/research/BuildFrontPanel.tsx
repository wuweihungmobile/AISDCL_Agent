"use client";

/**
 * 步驟 4 前半面板（FR-R2P-14、19-4；TCS-ResearchToPRD-P1-20261107 AT-961-18-*、20-E-4、25-4）：拆解與簽核（{@link DecompositionCard}）、測試規格草擬（{@link TcsCard}）、
 * 到既有專案頁／執行中心／監控中心的連結（{@link InnerLoopLinks}）、「重新對帳」、「SCR 進行中」標籤（{@link ScrStateBadge}）。
 * P2 起內環已啟動（內環鍵已採納）時另掛看板（{@link KanbanBoard}）、自癒監視器（{@link HealingMonitor}）、終端窗格（{@link TerminalPane}）與頁頂的「發起規格變更（SCR）」；
 * 對帳漂移橫幅整併到工作區單一 `drift-banner`（本面板只留「待校正」說明）。
 *
 * 設計要點（為什麼這樣做）：
 *  - **資料全取自 API**：拆解（`GET …/decomposition`，無拆解回 `null`）、分流（`GET …/route`）、專案詳情（本面板自己訂一份，父層 props 只作首繪；「重新對帳」成功後重抓它，相態才會從待凍結變成可開始建置）。
 *    尚在載入（`undefined`）與「尚無」（`null`）是兩回事，不混。
 *  - **三道鎖的前端文字半**（後端另有 409）：規格變更中（`SCR_OPEN`）、拆解過期、草稿未簽核、測試規格未凍結；文字住 `BUILD_DISABLED_TEXT`，與後端 `scr_open`、`decomposition_stale`、`fsm_state_conflict` 對應。
 *  - **TCS 凍結後的游標**（D-125）：凍結走既有專案頁的凍結流程，不在研究面；凍結後回到本頁按「重新對帳」（Bridge 校正游標），或等讀端衍生；對帳結果只顯示、不自動修任何一邊——
 *    第三態 `pending_correction` 顯示「待校正」說明而非漂移警示。
 *  - **請求失敗不顯示空白**：沒有資料時顯示錯誤態與重試；曾經載入成功、重抓失敗時保留舊資料並標示「資料可能過期」。
 */
import { Hammer, Info, RefreshCw } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { useReconcileResearch, useResearchDecomposition, useResearchKanban, useResearchProject, useResearchReconcileCache, useResearchRoute } from "@/lib/api/queries";
import type { ResearchProjectDetail, ResearchReconcileResult } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { BUILD_DISABLED_TEXT, executionBlock, flowPhaseLabel, flowStatusLabel, reconcileDriftView, researchErrorText, tcsStage } from "@/lib/domain/research";
import { DecompositionCard } from "./DecompositionCard";
import { HealingMonitor } from "./HealingMonitor";
import { InnerLoopLinks } from "./InnerLoopLinks";
import { KanbanBoard } from "./KanbanBoard";
import { ScrBanner } from "./ScrBanner";
import { ScrLaunchButton } from "./ScrRequestDialog";
import { ScrStateBadge } from "./ScrStateBadge";
import { TcsCard } from "./TcsCard";
import { TerminalPane } from "./TerminalPane";

/**
 * 對帳結果在本面板的呈現：只有「待校正」（pending_correction）的操作說明；**漂移與量不到的橫幅整併到工作區單一 `drift-banner`**（`ResearchWorkspaceView`；D-131(6)、AT-962-25-3），
 * 本面板不再自己渲染第二個漂移橫幅。沒有待校正項目不渲染。
 */
function ReconcileNote({ result }: { result: ResearchReconcileResult }) {
  const view = reconcileDriftView(result);
  if (!view.pendingCorrection) return null;
  return (
    <div data-testid="build-reconcile-note" className="flex flex-col gap-2 text-sm">
      <p data-testid="reconcile-pending" role="note" className="flex items-start gap-2">
        <Info size={16} aria-hidden className="mt-0.5 shrink-0 text-wg-muted" />
        待校正：測試規格已在既有流程凍結，流程游標還停在舊位置；按「重新對帳」即可校正，系統不會自動改任何一邊。
      </p>
    </div>
  );
}
export function BuildFrontPanel({ researchId, project: initialProject, completed }: { researchId: string; project: ResearchProjectDetail; completed: boolean }) {
  const { canWrite } = useAuth();
  const projectQuery = useResearchProject(researchId);
  const decompositionQuery = useResearchDecomposition(researchId);
  const routeQuery = useResearchRoute(researchId);
  const reconcileResult = useResearchReconcileCache(researchId);
  const reconcile = useReconcileResearch();
  const [reconcileError, setReconcileError] = useState<unknown>(null);

  const project = projectQuery.data ?? initialProject;
  const { phase, status, detail } = project.flow.effective;

  const scrOpen = phase === "SCR_OPEN";
  const lockBase = completed ? BUILD_DISABLED_TEXT.completed : !canWrite ? BUILD_DISABLED_TEXT.viewer : null;
  const lock = lockBase ?? (scrOpen ? BUILD_DISABLED_TEXT.scrOpen : null);

  const decomposition = decompositionQuery.data; // undefined＝載入中或失敗；null＝尚無
  const route = routeQuery.data;
  const stage = tcsStage(phase, status);
  const tcsFrozen = stage === "frozen";
  const innerKeyAdopted = route !== undefined && route !== null && route.status === "SUCCEEDED" && route.implFsmProject !== null;
  const prerequisite = route === undefined ? "正在確認分流狀態" : !innerKeyAdopted || decomposition === null || decomposition === undefined ? BUILD_DISABLED_TEXT.needDecomposition : null;
  const block = executionBlock({ scrOpen, decomposition: decomposition ?? null, tcsFrozen });
  const consoleProjectId = route?.consoleProjectId ?? project.consoleProjectId;

  function doReconcile() {
    setReconcileError(null);
    reconcile.mutate(researchId, {
      onSuccess: () => void projectQuery.refetch(),
      onError: (e) => setReconcileError(e),
    });
  }
  const reconcileLock = completed ? BUILD_DISABLED_TEXT.completed : !canWrite ? BUILD_DISABLED_TEXT.viewer : undefined;

  return (
    <Card data-testid="build-front-panel" data-research-id={researchId} data-completed={String(completed)} data-phase={phase} className="flex flex-col gap-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="flex flex-wrap items-center gap-2 text-lg font-semibold">
          <Hammer size={20} aria-hidden className="text-wg-muted" />第 4 步：拆解與執行
          <ScrStateBadge phase={phase} />
        </h3>
        {innerKeyAdopted ? <ScrLaunchButton researchId={researchId} scrOpen={scrOpen} /> : null}
      </div>
      <p data-testid="build-phase" className="text-sm text-wg-muted">
        目前相態：{flowPhaseLabel(phase)}（{flowStatusLabel(status)}）
      </p>

      <ScrBanner researchId={researchId} scrOpen={scrOpen} />

      {projectQuery.isError ? (
        <div role="alert" data-testid="project-error" className="flex flex-wrap items-center gap-3 rounded-md border border-wg-draft-border bg-wg-draft-bg px-4 py-3 text-sm">
          <span>無法更新流程狀態，畫面上的相態可能已過期。</span>
          <Button size="sm" variant="ghost" onClick={() => void projectQuery.refetch()}>
            重試
          </Button>
        </div>
      ) : null}

      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="ghost" iconLeft={RefreshCw} disabled={reconcileLock !== undefined} title={reconcileLock} loading={reconcile.isPending} onClick={doReconcile}>
            重新對帳
          </Button>
          <span className="text-[13px] text-wg-muted">只報告、不修正；凍結後游標沒更新時按它校正。</span>
        </div>
        {reconcileError !== null ? (
          <p role="alert" data-testid="reconcile-error" className="text-sm text-wg-error">
            對帳失敗：{researchErrorText(reconcileError)}（可再按一次重試）
          </p>
        ) : null}
        {reconcileResult ? <ReconcileNote result={reconcileResult} /> : null}
      </div>

      {decomposition === undefined && decompositionQuery.isError ? (
        <ErrorState error={decompositionQuery.error} title="無法載入拆解" onRetry={() => void decompositionQuery.refetch()} />
      ) : decomposition === undefined ? (
        <PageSkeleton />
      ) : (
        <>
          {decompositionQuery.isError ? (
            <div role="alert" data-testid="decomposition-stale-data" className="flex flex-wrap items-center gap-3 rounded-md border border-wg-draft-border bg-wg-draft-bg px-4 py-3 text-sm">
              <span>資料可能過期：最近一次重新載入拆解失敗，以下是先前載入的內容。</span>
              <Button size="sm" variant="ghost" onClick={() => void decompositionQuery.refetch()}>
                重試
              </Button>
            </div>
          ) : null}
          <DecompositionCard researchId={researchId} decomposition={decomposition} lock={lock} />
        </>
      )}

      <TcsCard researchId={researchId} stage={stage} tcs={decomposition?.tcs ?? null} consoleProjectId={consoleProjectId} detail={detail} prerequisiteReason={prerequisite} lock={lock} />
      <InnerLoopLinks consoleProjectId={consoleProjectId} block={block} researchId={researchId} />
      {innerKeyAdopted ? <InnerLoopSection researchId={researchId} /> : null}
    </Card>
  );
}

/** 內環（P2）：看板、自癒監視器、終端窗格。看板與自癒共用同一份看板查詢（TanStack Query 以鍵合併，不重複請求）；終端窗格取看板的最新 run。 */
function InnerLoopSection({ researchId }: { researchId: string }) {
  const kanban = useResearchKanban(researchId);
  return (
    <div data-testid="inner-loop-section" className="flex flex-col gap-4">
      <KanbanBoard researchId={researchId} />
      <HealingMonitor researchId={researchId} />
      <TerminalPane runId={kanban.data?.latestRunId ?? null} />
    </div>
  );
}
