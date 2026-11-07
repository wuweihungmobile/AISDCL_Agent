"use client";

/**
 * 步驟 3「分流」面板（FR-R2P-11；TCS-ResearchToPRD-P1-20261107 AT-961-17-1、17-2、17-7、17-8、16-E-2）：
 *  - Gate 0 未完成（游標還沒越過規格工作室）：只顯示阻擋說明與連回步驟 2 的連結，沒有任何寫入控件；
 *  - 尚未分流：抽屜自動開啟（{@link RouteDrawer}），關掉後提供「重新開啟分流精靈」；
 *  - 分流中／失敗／完成：逐步進度（{@link RouteStepsTimeline}）；失敗顯示失敗步驟與原因並提供「重試失敗步驟」（僅 ADMIN；送出 `retry: true`，已成功的步驟不重做）；
 *    完成顯示唯讀摘要（分支、遠端 URL、Console 專案）與「前往拆解與執行」。
 * 游標與分流列都取自 API（`GET …/route`），不取瀏覽器儲存：重新載入後從失敗步驟續（W-R1）。
 */
import { Lock, Route as RouteIcon, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { useResearchCapabilities, useResearchRoute, useRouteResearchProject } from "@/lib/api/queries";
import type { EventSourceCtor } from "@/lib/api/sse";
import type { ResearchProjectDetail, ResearchRouteConfirmRequest, ResearchRouteDecision } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { READONLY_TITLE, ROUTE_DISABLED_TEXT, researchErrorText, routeIsActive, routeRowToRequest, routeStatusLabel, routeTrackForScope, safeRepoHref, stepIndex } from "@/lib/domain/research";
import { RouteDrawer } from "./RouteDrawer";
import { RouteStepsTimeline } from "./RouteStepsTimeline";

const stepHref = (researchId: string, step: string): string => `/research/${encodeURIComponent(researchId)}?step=${step}`;

function RouteSummary({ route }: { route: ResearchRouteDecision }) {
  const repoHref = safeRepoHref(route.repoUrl);
  return (
    <dl data-testid="route-summary" className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
      <dt className="text-wg-muted">軌道</dt>
      <dd>{route.track === "A" ? "軌道 A：併入 AISDLC" : "軌道 B：獨立專案"}</dd>
      {route.gitBranch !== null ? (
        <>
          <dt className="text-wg-muted">分支</dt>
          <dd className="font-mono">{route.gitBranch}</dd>
        </>
      ) : null}
      {route.repoUrl !== null ? (
        <>
          <dt className="text-wg-muted">遠端庫</dt>
          <dd className="break-all font-mono">
            {repoHref !== null ? (
              <a href={repoHref} target="_blank" rel="noopener noreferrer" className="text-wg-primary hover:underline">
                {route.repoUrl}
              </a>
            ) : (
              route.repoUrl
            )}
          </dd>
        </>
      ) : null}
      {route.consoleProjectId !== null ? (
        <>
          <dt className="text-wg-muted">Console 專案</dt>
          <dd>
            <Link href={`/projects/${encodeURIComponent(route.consoleProjectId)}`} className="text-wg-primary hover:underline">
              開啟專案
            </Link>
          </dd>
        </>
      ) : null}
    </dl>
  );
}

export function RoutePanel({
  researchId,
  project,
  completed,
  EventSourceCtor,
}: {
  researchId: string;
  project: ResearchProjectDetail;
  /** 這一步已完成的唯讀檢視（序號小於游標所在步） */
  completed: boolean;
  EventSourceCtor?: EventSourceCtor;
}) {
  const { role, canWrite } = useAuth();
  const isAdmin = role === "ADMIN";
  const toast = useToast();
  const capabilities = useResearchCapabilities();
  const routeQuery = useResearchRoute(researchId);
  const retryMut = useRouteResearchProject();
  const [forceOpen, setForceOpen] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [lastRequest, setLastRequest] = useState<ResearchRouteConfirmRequest | null>(null);
  const [retryError, setRetryError] = useState<unknown>(null);

  if (stepIndex(project.flow.currentStep) < stepIndex("route")) {
    return (
      <Card data-testid="route-blocked" className="flex flex-col gap-3 p-6">
        <h3 className="flex items-center gap-2 text-lg font-semibold">
          <Lock size={20} aria-hidden className="text-wg-muted" />第 3 步：分流
        </h3>
        <p className="text-[15px]">Gate 0 還沒有核准，規格尚未凍結，不能分流。</p>
        <Link href={stepHref(researchId, "studio")} className="w-fit text-sm font-medium text-wg-primary hover:underline">
          回到規格工作室
        </Link>
      </Card>
    );
  }
  if (routeQuery.isLoading) return <PageSkeleton />;
  if (routeQuery.isError) return <ErrorState error={routeQuery.error} title="無法載入分流狀態" onRetry={() => void routeQuery.refetch()} />;

  const route = routeQuery.data ?? null;
  // 唯讀角色不自動彈出抽屜（沒有可做的事）；已完成步驟的唯讀檢視同樣不彈
  const drawerOpen = forceOpen || (!dismissed && route === null && !completed && canWrite);
  const readOnly = completed || !canWrite;

  async function retry(current: ResearchRouteDecision) {
    setRetryError(null);
    try {
      await retryMut.mutateAsync({ id: researchId, body: { ...(lastRequest ?? routeRowToRequest(current, project)), retry: true } });
      toast.success("已重試失敗的步驟");
    } catch (e) {
      setRetryError(e);
    }
  }

  const retryTitle = completed ? "這一步已完成，唯讀" : !canWrite ? READONLY_TITLE : !isAdmin ? ROUTE_DISABLED_TEXT.adminOnly : undefined;
  return (
    <Card data-testid="route-panel" data-route-status={route?.status ?? "NONE"} className="flex flex-col gap-4 p-6">
      <h3 className="flex items-center gap-2 text-lg font-semibold">
        <RouteIcon size={20} aria-hidden className="text-wg-muted" />第 3 步：分流
        {route !== null ? <span className="text-sm font-normal text-wg-muted">（{routeStatusLabel(route.status)}）</span> : null}
      </h3>

      {capabilities.isError && !drawerOpen ? <ErrorState error={capabilities.error} title="無法載入部署能力" onRetry={() => void capabilities.refetch()} /> : null}

      {route === null ? (
        <>
          <p className="text-[15px]">規格已凍結。請選擇併入既有 AISDLC 模組（軌道 A）或另開獨立專案（軌道 B），先預演，再由 ADMIN 確認執行。</p>
          <Button className="w-fit" variant="ghost" disabled={readOnly} title={readOnly ? (completed ? "這一步已完成，唯讀" : READONLY_TITLE) : undefined} onClick={() => setForceOpen(true)}>
            重新開啟分流精靈
          </Button>
        </>
      ) : (
        <>
          <RouteSummary route={route} />
          <RouteStepsTimeline researchId={researchId} route={route} streaming={routeIsActive(route.status)} EventSourceCtor={EventSourceCtor} />
          {route.status === "FAILED" ? (
            <div role="alert" data-testid="route-failed" className="flex flex-col gap-2 rounded-md border border-wg-draft-border bg-wg-draft-bg px-4 py-3 text-sm">
              <p className="flex items-center gap-2 font-semibold text-wg-accent">
                <TriangleAlert size={16} aria-hidden />
                分流在「{route.failureStep ?? "未知步驟"}」失敗了，已完成的步驟會保留。
              </p>
              {retryError !== null ? <p data-testid="route-retry-error">{researchErrorText(retryError)}</p> : null}
              <Button className="w-fit" disabled={readOnly || !isAdmin} title={retryTitle} loading={retryMut.isPending} onClick={() => void retry(route)}>
                重試失敗步驟
              </Button>
            </div>
          ) : null}
          {route.status === "SUCCEEDED" ? (
            <Link href={stepHref(researchId, "build")} className="w-fit text-sm font-medium text-wg-primary hover:underline">
              前往拆解與執行
            </Link>
          ) : null}
          {route.status === "FAILED" || route.status === "COMPENSATED" ? (
            <Button className="w-fit" variant="ghost" disabled={readOnly} title={readOnly ? (completed ? "這一步已完成，唯讀" : READONLY_TITLE) : undefined} onClick={() => setForceOpen(true)}>
              重新開啟分流精靈
            </Button>
          ) : null}
        </>
      )}

      <RouteDrawer
        open={drawerOpen}
        onOpenChange={(next) => {
          setForceOpen(next);
          if (!next) setDismissed(true);
        }}
        researchId={researchId}
        project={project}
        defaultTrack={routeTrackForScope(project.targetScope)}
        capabilities={capabilities.data}
        capabilitiesError={capabilities.isError ? capabilities.error : undefined}
        onRetryCapabilities={() => void capabilities.refetch()}
        readOnly={completed}
        onConfirmed={(request) => setLastRequest(request)}
        EventSourceCtor={EventSourceCtor}
      />
    </Card>
  );
}
