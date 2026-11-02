"use client";

/**
 * 研究工作區（`/research/<id>?step=…`；FR-R2P-01、21、23；TCS-ResearchToPRD-P0-20261102 AT-960-19-4、19-5、19-6、19-E-2、21-6；ADR-003 D5）：
 * 五個步驟面板同在一條路由內，以 `?step=topic｜studio｜route｜build｜deliver` 切換，共用 `ResearchFlowHeader` 與 `FlowStepper`。
 *
 * 設計要點（為什麼這樣做）：
 *  - **游標取自 API、不取自瀏覽器儲存**：進頁時讀 `GET …/{id}`（流程脊由後端衍生），離開再回來從同一步續做；本檔不讀也不寫 localStorage、sessionStorage。
 *  - **網址只決定「看哪一步」**：`?step=` 超前於 `furthestStep`、缺少或不是五步之一，一律顯示游標所在步並以 `router.replace` 補上／導回網址（不留無效網址在歷史；導回不發任何寫入請求）；
 *    指向已完成步驟＝唯讀檢視（標示「已完成，唯讀」，面板的寫入動作須停用）。沒有「推進游標」的動作——游標只由 Bridge 在引擎動作的同一交易推進（W-R1）。
 *  - **步驟 3～5 在 P0 是占位面板**（PRD §7.3.1）：步驟名、「本步驟於後續階段提供」、目前進度與回到游標所在步的連結；唯讀、沒有任何寫入動作，
 *    也不假裝有執行中心或監控中心的連結（那是 P2 的 ResearchBackLink）。
 *  - **步驟 1、2 的面板由外部接入**（`panels` 屬性）：議題面板與 PRD 工作室是各自獨立的元件，由頁殼（`app/research/[researchId]/page.tsx`）組裝並傳入，本檔不 import 它們——
 *    工作區因此可以單獨測試（面板以替身注入），也不把面板的相依（編輯器、圖表）拖進本檔的 import 圖。沒有注入面板的步驟顯示「面板尚未接入」，不是空白。
 *  - **對帳結果只讀快取**：漂移橫幅（紅色「檔案與資料庫不一致」）讀 `useResearchReconcileCache`，渲染時不發任何請求；「對帳」鈕（POST，OPERATOR 以上；檢視已完成步驟的唯讀檢視時停用）才會替使用者打一次。
 *    橫幅沒有任何「修正」類動作：漂移只顯示與記錄，不自動修正任何一邊（以資料庫為準；AC-R2P-23-2）。
 */
import { Clock, Info, Lock, ScanSearch, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, type ComponentType } from "react";

import { BackLink, PageTitle } from "@/components/domain/PageHeader";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { useReconcileResearch, useReinitResearchProject, useResearchProject, useResearchReconcileCache } from "@/lib/api/queries";
import type { ResearchFlowStepId, ResearchProjectDetail, ResearchReconcileResult } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  DEPTH_OPTIONS,
  FLOW_STEP_LABEL,
  READONLY_TITLE,
  deriveSteps,
  flowPhaseLabel,
  flowStatusLabel,
  isCompletedStep,
  isInitFailed,
  reconcileDriftView,
  researchErrorText,
  resolveViewStep,
  stepNumber,
  stepReachable,
} from "@/lib/domain/research";
import { ResearchFlowHeader } from "./ResearchFlowHeader";
import { FlowStepper } from "./FlowStepper";

/**
 * 步驟面板（步驟 1、2）收到的屬性：`completed`＝這一步已完成（序號小於游標所在步），面板的寫入動作須停用並標示「已完成，唯讀」；
 * VIEWER 的停用（`title` 為「權限不足（唯讀角色）」）由各面板自己依 `useAuth().canWrite` 判，兩種唯讀互不取代。
 */
export type ResearchPanelProps = { researchId: string; project: ResearchProjectDetail; completed: boolean };
/** 外部接入的步驟面板：只有步驟 1（`topic`）與步驟 2（`studio`）；步驟 3～5 在 P0 是占位面板。 */
export type ResearchPanels = Partial<Record<"topic" | "studio", ComponentType<ResearchPanelProps>>>;

const stepHref = (researchId: string, step: ResearchFlowStepId): string => `/research/${encodeURIComponent(researchId)}?step=${step}`;

/** 檢視已完成步驟時的「對帳」說明：對帳是 POST（記事件、寫出狀態投影），已完成步驟的唯讀檢視（AT-960-19-4）不送任何寫入，請回到游標所在步再按。 */
const COMPLETED_RECONCILE_TITLE = "這一步已完成，唯讀；請回到游標所在步再對帳";

/** 占位面板（P0 的步驟 3～5；PRD §7.3.1）：唯讀、無寫入動作；目前進度取自後端衍生的相態。 */
function PlaceholderPanel({ researchId, project, step }: { researchId: string; project: ResearchProjectDetail; step: ResearchFlowStepId }) {
  const { currentStep, effective } = project.flow;
  return (
    <Card data-testid="research-placeholder" data-step={step} className="flex flex-col gap-3 p-6">
      <h3 className="flex items-center gap-2 text-lg font-semibold">
        <Clock size={20} aria-hidden className="text-wg-muted" />第 {stepNumber(step)} 步：{FLOW_STEP_LABEL[step]}
      </h3>
      <p className="text-[15px]">本步驟於後續階段提供</p>
      <p className="text-sm text-wg-muted">
        目前進度：第 {stepNumber(currentStep)} 步「{FLOW_STEP_LABEL[currentStep]}」，{flowPhaseLabel(effective.phase)}（{flowStatusLabel(effective.status)}）。
      </p>
      <Link href={stepHref(researchId, currentStep)} className="w-fit text-sm font-medium text-wg-primary hover:underline">
        回到游標所在步
      </Link>
    </Card>
  );
}

/** 對帳漂移橫幅：以資料庫為準、只顯示差異；沒有任何動作鈕（不自動修正任何一邊）。全部一致時不渲染。 */
function DriftBanner({ result }: { result: ResearchReconcileResult }) {
  const view = reconcileDriftView(result);
  const hasDrift = view.files.length > 0 || view.fsmMapping;
  if (!hasDrift && view.notEvaluable.length === 0) return null;
  return (
    <div
      role="alert"
      data-testid="drift-banner"
      data-drift={hasDrift || undefined}
      className={hasDrift ? "mb-4 rounded-md border border-wg-error bg-wg-draft-bg px-4 py-3 text-sm" : "mb-4 rounded-md border border-wg-alert-border bg-wg-alert-bg px-4 py-3 text-sm"}
    >
      <p className={hasDrift ? "flex items-center gap-2 font-semibold text-wg-error" : "flex items-center gap-2 font-semibold text-wg-warning-text"}>
        <TriangleAlert size={18} aria-hidden />
        {hasDrift ? "檔案與資料庫不一致" : "對帳沒有完成"}
      </p>
      {hasDrift ? <p className="mt-1">畫面上的內容一律取自資料庫版本；這裡只顯示差異，不會自動修正任何一邊。</p> : null}
      {view.files.length > 0 ? (
        <ul data-testid="drift-files" className="mt-2 list-disc space-y-1 pl-5">
          {view.files.map((f) => (
            <li key={`${f.check}:${f.path}`}>
              <span className="font-mono">{f.path}</span>（{f.label}）
              {f.expectedSha256 !== undefined && f.actualSha256 !== undefined ? (
                <span className="text-wg-muted">
                  ：資料庫 {f.expectedSha256.slice(0, 8)}，檔案 {f.actualSha256.slice(0, 8)}
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
      {view.fsmMapping ? (
        <p data-testid="fsm-mapping-warning" className="mt-2">
          狀態機的現態與流程游標的對映不合：請對照狀態機視圖確認目前真正的階段，系統不會替您改任何一邊。
        </p>
      ) : null}
      {view.notEvaluable.length > 0 ? <p className="mt-2 text-wg-muted">無法比對的項目：{view.notEvaluable.join("、")}（不判成一致，也不判成不一致）。</p> : null}
    </div>
  );
}

export function ResearchWorkspaceView({ panels = {} }: { panels?: ResearchPanels }) {
  const params = useParams<{ researchId?: string | string[] }>();
  const researchId = Array.isArray(params.researchId) ? params.researchId[0] : params.researchId;
  const router = useRouter();
  const searchParams = useSearchParams();
  const { canWrite } = useAuth();
  const toast = useToast();
  const query = useResearchProject(researchId);
  const reconcileResult = useResearchReconcileCache(researchId);
  const reconcile = useReconcileResearch();
  const reinit = useReinitResearchProject();
  const project = query.data;

  const resolved = project ? resolveViewStep(searchParams.get("step"), project.flow.currentStep, project.flow.furthestStep) : null;
  const redirectTo = resolved?.redirect ? resolved.step : null;
  useEffect(() => {
    if (researchId && redirectTo !== null) router.replace(stepHref(researchId, redirectTo));
  }, [researchId, redirectTo, router]);

  if (!researchId || (!project && query.isError)) {
    return (
      <div>
        <BackLink href="/research">研發工作流</BackLink>
        <ErrorState error={query.error ?? new Error("缺少研究專案編號")} title="無法載入研究專案" onRetry={researchId ? () => void query.refetch() : undefined} />
      </div>
    );
  }
  if (!project || !resolved) return <PageSkeleton />;

  const { flow } = project;
  const viewed = resolved.step;
  const completed = isCompletedStep(viewed, flow.currentStep);
  const Panel = viewed === "topic" || viewed === "studio" ? panels[viewed] : undefined;
  const depth = DEPTH_OPTIONS.find((d) => d.id === project.depthLevel)?.label ?? project.depthLevel;
  const blocked = (flow.effective.status === "BLOCKED" || flow.effective.status === "FAILED") && !isInitFailed(project);

  async function retryInit(id: string) {
    try {
      await reinit.mutateAsync({ id });
      toast.success("已重試初始化");
    } catch (e) {
      toast.error(`重試初始化失敗：${researchErrorText(e)}`);
    }
  }

  return (
    <div data-testid="research-workspace" data-step={viewed}>
      <BackLink href="/research">研發工作流</BackLink>
      <PageTitle
        className="mb-3"
        title={`${project.rpNo} ${project.title}`}
        subtitle={`代號 ${project.slug} · 檢索深度 ${depth}`}
        actions={
          <Button
            variant="ghost"
            iconLeft={ScanSearch}
            disabled={!canWrite || completed}
            title={!canWrite ? READONLY_TITLE : completed ? COMPLETED_RECONCILE_TITLE : "比對檔案、資料庫與狀態機是否一致（只報告，不修正）"}
            loading={reconcile.isPending}
            onClick={() =>
              reconcile.mutate(project.id, {
                onSuccess: (data) => toast.success(data.result.consistent ? "對帳完成：檔案、資料庫與狀態機一致" : "對帳完成：發現不一致，請看頁面上方的提示"),
                onError: (e) => toast.error(`對帳失敗：${researchErrorText(e)}`),
              })
            }
          >
            對帳
          </Button>
        }
      />
      <ResearchFlowHeader project={project} />
      <FlowStepper
        className="mb-4"
        steps={deriveSteps(flow.effective.step, flow.effective.status)}
        selected={viewed}
        hrefFor={(id) => (stepReachable(id, flow.furthestStep) ? stepHref(researchId, id) : null)}
      />

      {reconcileResult ? <DriftBanner result={reconcileResult} /> : null}

      {isInitFailed(project) ? (
        <div role="alert" data-testid="init-failed-banner" className="mb-4 flex flex-wrap items-center gap-3 rounded-md border border-wg-draft-border bg-wg-draft-bg px-4 py-3 text-sm">
          <TriangleAlert size={18} aria-hidden className="shrink-0 text-wg-accent" />
          <span className="min-w-0 flex-1">
            <span className="font-semibold text-wg-accent">初始化失敗</span>：{project.flowDetail}。工作區或狀態機沒有建好，重試是冪等的（不覆寫已存在的檔案、不重複配號、不重複建鍵）。
          </span>
          <Button size="sm" variant="ghost" disabled={!canWrite} title={canWrite ? undefined : READONLY_TITLE} loading={reinit.isPending} onClick={() => void retryInit(project.id)}>
            重試初始化
          </Button>
        </div>
      ) : null}
      {blocked ? (
        <div role="alert" data-testid="blocked-banner" className="mb-4 flex items-start gap-2 rounded-md border border-wg-draft-border bg-wg-draft-bg px-4 py-3 text-sm">
          <TriangleAlert size={18} aria-hidden className="mt-0.5 shrink-0 text-wg-accent" />
          <span>
            目前{flowStatusLabel(flow.effective.status)}：{flow.effective.detail === "" ? "後端沒有提供原因" : flow.effective.detail}
          </span>
        </div>
      ) : null}
      {completed ? (
        <div role="note" data-testid="completed-readonly-banner" className="mb-4 flex items-center gap-2 rounded-md border border-wg-line bg-wg-surface px-4 py-2.5 text-sm text-wg-muted">
          <Lock size={16} aria-hidden />
          已完成，唯讀
        </div>
      ) : null}

      <div data-testid={`research-panel-${viewed}`}>
        {viewed === "topic" || viewed === "studio" ? (
          Panel ? (
            <Panel researchId={researchId} project={project} completed={completed} />
          ) : (
            <Card data-testid="research-panel-missing" className="flex items-center gap-2 p-6 text-sm text-wg-muted">
              <Info size={18} aria-hidden />
              這一步的操作面板尚未接入。
            </Card>
          )
        ) : (
          <PlaceholderPanel researchId={researchId} project={project} step={viewed} />
        )}
      </div>
    </div>
  );
}
