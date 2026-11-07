"use client";

/**
 * 步驟 5「交付」面板（FR-R2P-20、21；TCS-ResearchToPRD-P2-20261107 AT-962-21-1、21-2、25-2；IFACE-P2 §6；D-148 FE-1）：
 * 追溯表（{@link TraceabilityTable}）＋發布動作（{@link ReleaseActions}、{@link PrConfirmDialog}；Tag 與 PR 的確認框在其內）＋已建立的交付紀錄＋最近一次對帳的「交付」項。
 *
 * 設計要點（為什麼這樣做）：
 *  - **資料全取自 API**：`useResearchDelivery`（概覽與前置條件）、`useResearchTraceability`（追溯表；Bridge 零副作用預覽）、專案詳情（相態：已交付與否取自流程相態，不自己衍生）。
 *    載入中與失敗是兩回事：失敗顯示錯誤態與重試（不顯示空白）。
 *  - **對帳只顯示、不另造橫幅**：「交付」漂移的橫幅仍只有工作區那一個（D-131(6)、AT-962-25-3）；這裡只用一行文字顯示該項最近的結果，沒有修正鈕。
 *  - **寫入控件只給有權限者**：Tag 鈕（僅 ADMIN）與 PR 建立鈕（僅 ADMIN）由各元件判角色；VIEWER 沒有任何可按的寫入控件。
 *  - 字樣取 `DELIVER_LABEL`（`lib/domain/research.ts`；D-156）。本檔沒有任何通往執行中心或監控中心的字樣或連結（P0 的反向釘：步驟 5 不得出現）。
 */
import { PackageCheck } from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { useResearchDelivery, useResearchProject, useResearchReconcileCache, useResearchTraceability } from "@/lib/api/queries";
import type { ResearchDelivery, ResearchProjectDetail } from "@/lib/api/types";
import { DELIVER_LABEL, FLOW_STEP_LABEL, RECONCILE_CHECK_LABEL } from "@/lib/domain/research";
import { PrConfirmDialog, SafeExternalLink } from "./PrConfirmDialog";
import { ReleaseActions } from "./ReleaseActions";
import { TraceabilityTable } from "./TraceabilityTable";

const KIND_LABEL: Readonly<Record<string, string>> = { RELEASE_TAG: "Tag", PULL_REQUEST: "PR", RELEASE_NOTE: "發布說明" };
const RECONCILE_STATUS_TEXT: Readonly<Record<string, string>> = {
  ok: "一致",
  drift: "不一致（請看頁面上方的提示；以資料庫為準，不會自動修正）",
  NOT_EVALUABLE: "量不到（不判成一致也不判成不一致）",
  pending_correction: "待校正",
};

function RecordsList({ deliveries }: { deliveries: ResearchDelivery[] }) {
  return (
    <section data-testid="delivery-records" className="flex flex-col gap-2">
      <h4 className="text-base font-semibold">{DELIVER_LABEL.records}</h4>
      {deliveries.length === 0 ? (
        <p data-testid="delivery-records-empty" className="text-sm text-wg-muted">
          還沒有交付紀錄。
        </p>
      ) : (
        <ul className="flex flex-col gap-2 text-sm">
          {deliveries.map((d) => (
            <li key={`${d.kind}:${d.ref}`} data-testid="delivery-record" data-kind={d.kind} className="flex flex-wrap items-baseline gap-x-4 gap-y-1 rounded-md border border-wg-line px-3 py-2">
              <span className="font-semibold">{KIND_LABEL[d.kind] ?? d.kind}</span>
              <span className="font-mono break-all">{d.ref}</span>
              {d.status === "FAILED" ? <span className="text-wg-error">失敗</span> : null}
              {d.commitSha !== null ? <span className="font-mono text-wg-muted">提交 {d.commitSha.slice(0, 12)}</span> : null}
              <span className="text-wg-muted">{d.createdAt}</span>
              {d.url !== null ? <SafeExternalLink href={d.url}>{d.url}</SafeExternalLink> : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function DeliverPanel({ researchId, project: initialProject, completed }: { researchId: string; project: ResearchProjectDetail; completed: boolean }) {
  const projectQuery = useResearchProject(researchId);
  const delivery = useResearchDelivery(researchId);
  const traceability = useResearchTraceability(researchId);
  const reconcile = useResearchReconcileCache(researchId);

  const project = projectQuery.data ?? initialProject;
  const overview = delivery.data;
  const trace = traceability.data;
  const phase = project.flow.effective.phase;
  const fsmRelease = phase === "DELIVERED" || (project.flowStep === "deliver" && project.flowStatus === "COMPLETED");
  const scrOpen = phase === "SCR_OPEN" || overview?.preconditions.scrOpen === true;
  const reconcileDelivery = reconcile?.checks.find((c) => c.name === "delivery");

  const error = delivery.isError && overview === undefined ? delivery.error : traceability.isError && trace === undefined ? traceability.error : null;
  function retry() {
    void delivery.refetch();
    void traceability.refetch();
  }

  return (
    <Card data-testid="deliver-panel" data-research-id={researchId} data-completed={String(completed)} className="flex flex-col gap-5 p-6">
      <h3 className="flex items-center gap-2 text-lg font-semibold">
        <PackageCheck size={20} aria-hidden className="text-wg-muted" />第 5 步：{FLOW_STEP_LABEL.deliver}
      </h3>
      {error !== null ? (
        <ErrorState error={error} title="無法載入交付資料" onRetry={retry} />
      ) : overview === undefined || trace === undefined ? (
        <PageSkeleton />
      ) : (
        <>
          {delivery.isError || traceability.isError ? (
            <div role="alert" data-testid="deliver-stale-data" className="flex flex-wrap items-center gap-3 rounded-md border border-wg-draft-border bg-wg-draft-bg px-4 py-3 text-sm">
              <span>資料可能過期：最近一次重新載入交付資料失敗，以下是先前載入的內容。</span>
              <Button size="sm" variant="ghost" onClick={retry}>
                重試
              </Button>
            </div>
          ) : null}
          <TraceabilityTable data={trace} />
          <div className="flex flex-col gap-5 lg:flex-row lg:flex-wrap lg:gap-x-10">
            <div className="min-w-0 flex-1 basis-[320px]">
              <ReleaseActions researchId={researchId} overview={overview} traceability={trace} fsmRelease={fsmRelease} scrOpen={scrOpen} completed={completed} />
            </div>
            <div className="min-w-0 flex-1 basis-[320px]">
              <PrConfirmDialog researchId={researchId} rpNo={project.rpNo} title={project.title} overview={overview} traceability={trace} />
            </div>
          </div>
          <RecordsList deliveries={overview.deliveries} />
          <p data-testid="deliver-reconcile" data-status={reconcileDelivery?.status ?? "none"} className="text-sm text-wg-muted">
            最近對帳「{RECONCILE_CHECK_LABEL.delivery}」：
            {reconcileDelivery === undefined ? "尚無對帳結果" : (RECONCILE_STATUS_TEXT[reconcileDelivery.status] ?? reconcileDelivery.status)}
          </p>
        </>
      )}
    </Card>
  );
}
