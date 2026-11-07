"use client";

/**
 * 分流精靈抽屜（FR-R2P-11；TCS-ResearchToPRD-P1-20261107 AT-961-16-5、16-E-2、17-1、17-3～17-6、17-8、17-E-1）：三段固定——
 * 一、選卡填參數（卡 A 併入 AISDLC、卡 B 獨立專案、評估維度表）→ 二、預演（`POST …/route/preview`，零副作用，顯示動作清單、警示、預期入版控檔案）→ 三、確認執行（`POST …/route`，僅 ADMIN）。
 *
 * 設計要點（為什麼這樣做）：
 *  - **預演與確認的對應**：確認鈕只在「預演通過、且之後沒有改過任何參數」時啟用（以請求本文的序列化當鑰匙；改一個字就失效，必須重新預演）。
 *  - **角色與缺項的停用都在這裡判、文案取單一登記處**（`lib/domain/research.ts` 的 `ROUTE_DISABLED_TEXT`，IFACE §8.3）：VIEWER 全面停用（`title` 為「權限不足（唯讀角色）」）、OPERATOR 可預演不可確認、
 *    git 缺或容器模式兩軌皆停、repoWritable 假停卡 A、scaffold 缺停卡 B、gh 缺只停「建立 GitHub 遠端」勾選。停用的控件 `disabled` 且不送任何請求。
 *  - **差異警示**：所選軌道與 PRD 目標範圍不同時並列兩者、必填一句理由（1～200 字）；`approver` 與 `targetPath` 不由前端送（後端取 JWT subject、路徑由 Bridge 導出）。
 *  - **capabilities 載入失敗不假裝可用**：顯示錯誤與重試，兩卡與預演、確認皆停用，不渲染任何預設為可用的欄位。
 *  - **還原**：重新載入後的初始表單取自 API 的分流列與 PRD 預設（不取瀏覽器儲存；W-R1）。
 */
import { ClipboardCheck, TriangleAlert } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ErrorState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { usePreviewResearchRoute, useResearchRoute, useRouteResearchProject } from "@/lib/api/queries";
import type { ResearchCapabilities, ResearchProjectDetail, ResearchRouteConfirmRequest, ResearchRoutePreview, ResearchRouteTrack } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  READONLY_TITLE,
  RESEARCH_REASONS,
  ROUTE_DISABLED_TEXT,
  ROUTE_EVAL_TABLE,
  ROUTE_TRACK_LABEL,
  initialRouteForm,
  resolveDefaultModule,
  researchErrorText,
  routeCapabilityBlocks,
  routeFormErrors,
  routeMissingLabels,
  routeScopeDiffers,
  toRouteRequest,
  type RouteBlockCode,
  type RouteForm,
} from "@/lib/domain/research";
import type { EventSourceCtor } from "@/lib/api/sse";
import { RouteActionList } from "./RouteActionList";
import { RouteCardA } from "./RouteCardA";
import { RouteCardB } from "./RouteCardB";
import { RouteStepsTimeline } from "./RouteStepsTimeline";

/** 預演與確認失敗的呈現：白話原因加（`route_unsupported_in_deployment`）缺項中文、（欄位違規）逐項列出。 */
function RouteErrorBox({ error }: { error: unknown }) {
  const reason = error instanceof ApiError ? error.reason : undefined;
  const missing = error instanceof ApiError && reason === RESEARCH_REASONS.ROUTE_UNSUPPORTED_IN_DEPLOYMENT ? routeMissingLabels(error.details?.missing) : [];
  const violations =
    error instanceof ApiError && Array.isArray(error.details?.violations)
      ? (error.details.violations as unknown[]).map((v) =>
          typeof v === "object" && v !== null
            ? `${String((v as { field?: unknown }).field ?? "")}：${String((v as { message?: unknown }).message ?? (v as { rule?: unknown }).rule ?? "")}`
            : String(v),
        )
      : [];
  const fieldErrors = error instanceof ApiError ? error.errors.map((e) => `${e.field}：${e.message}`) : [];
  return (
    <div role="alert" data-testid="route-error" className="flex flex-col gap-1 rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm">
      <p className="flex items-center gap-2 font-semibold text-wg-accent">
        <TriangleAlert size={16} aria-hidden />
        {researchErrorText(error)}
      </p>
      {missing.length > 0 ? (
        <ul data-testid="route-missing" className="list-disc pl-5">
          {missing.map((label) => (
            <li key={label}>{label}</li>
          ))}
        </ul>
      ) : null}
      {[...violations, ...fieldErrors].length > 0 ? (
        <ul data-testid="route-violations" className="list-disc pl-5">
          {[...violations, ...fieldErrors].map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export type RouteDrawerProject = Pick<ResearchProjectDetail, "rpNo" | "targetScope" | "topic" | "slug">;

export function RouteDrawer({
  open,
  onOpenChange,
  researchId,
  project,
  defaultTrack,
  capabilities,
  capabilitiesError,
  onRetryCapabilities,
  readOnly = false,
  onConfirmed,
  EventSourceCtor,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  researchId: string;
  project: RouteDrawerProject;
  /** 依 PRD `targetScope` 預選的軌道；`null`＝兩卡皆不預選 */
  defaultTrack: ResearchRouteTrack | null;
  capabilities: ResearchCapabilities | undefined;
  capabilitiesError?: unknown;
  onRetryCapabilities?: () => void;
  /** 已完成步驟的唯讀檢視：整個精靈停用 */
  readOnly?: boolean;
  /** 確認執行成功後回呼（帶送出的請求本文，供「重試失敗步驟」沿用同一份輸入） */
  onConfirmed?: (request: ResearchRouteConfirmRequest) => void;
  EventSourceCtor?: EventSourceCtor;
}) {
  const { role, canWrite } = useAuth();
  const isAdmin = role === "ADMIN";
  const toast = useToast();
  const routeQuery = useResearchRoute(researchId);
  const previewMut = usePreviewResearchRoute();
  const routeMut = useRouteResearchProject();
  const [form, setForm] = useState<RouteForm>(() => initialRouteForm(project, defaultTrack, capabilities, routeQuery.data ?? null));
  const [preview, setPreview] = useState<{ key: string; data: ResearchRoutePreview } | null>(null);
  const [confirmError, setConfirmError] = useState<unknown>(null);

  const change = (patch: Partial<RouteForm>) => setForm((prev) => ({ ...prev, ...patch }));
  // 能力探針比抽屜晚載入時，範本欄還沒有值：以探針的第一個範本補上（只補顯示與請求，不覆寫使用者已選的值）
  const firstTemplate = capabilities?.scaffoldTemplates[0] ?? "";
  const shown: RouteForm = form.stackTemplate === "" && firstTemplate !== "" ? { ...form, stackTemplate: firstTemplate } : form;
  const differs = shown.track !== null && routeScopeDiffers(project.targetScope, shown.track);
  const errors = routeFormErrors(shown, differs);
  const formValid = Object.keys(errors).length === 0;
  const request = shown.track === null || !formValid ? null : toRouteRequest(shown, differs);
  const requestKey = request === null ? "" : JSON.stringify(request);
  const previewCurrent = preview !== null && preview.key === requestKey;

  const blocks = capabilities === undefined ? null : routeCapabilityBlocks(capabilities);
  const loadFailed = capabilitiesError !== undefined && capabilitiesError !== null;
  const text = (code: RouteBlockCode | null): string | null => (code === null ? null : ROUTE_DISABLED_TEXT[code]);
  const base = readOnly ? "這一步已完成，唯讀" : !canWrite ? READONLY_TITLE : loadFailed ? "無法確認部署能力，暫時不能分流" : blocks === null ? "正在檢查部署能力…" : text(blocks.all);
  const cardA = base ?? text(blocks?.trackA ?? null);
  const cardB = base ?? text(blocks?.trackB ?? null);
  const github = !canWrite ? READONLY_TITLE : text(blocks?.github ?? null);
  const previewBlock = base ?? (shown.track === null ? "請先選擇分流軌道" : !formValid ? "請先修正欄位錯誤" : shown.track === "A" ? cardA : cardB);
  const confirmBlock = base ?? (!isAdmin ? ROUTE_DISABLED_TEXT.adminOnly : (previewBlock ?? (!previewCurrent ? "請先預演；預演通過且參數沒有再改動，才能確認執行" : null)));

  async function runPreview() {
    if (request === null) return;
    setConfirmError(null);
    try {
      const data = await previewMut.mutateAsync({ id: researchId, body: request });
      setPreview({ key: requestKey, data });
    } catch {
      setPreview(null);
    }
  }

  async function runConfirm() {
    if (request === null) return;
    setConfirmError(null);
    try {
      await routeMut.mutateAsync({ id: researchId, body: request });
      toast.success("分流已完成");
      onConfirmed?.(request);
      onOpenChange(false);
    } catch (e) {
      setConfirmError(e);
      onConfirmed?.(request);
    }
  }

  const defaultModule = resolveDefaultModule(project);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        title="分流精靈"
        description="選擇併入既有模組或另開新專案，先預演再由 ADMIN 確認執行"
        data-testid="route-drawer"
        className="top-0 right-0 left-auto h-screen max-h-screen w-[680px] max-w-full translate-x-0 translate-y-0 rounded-none border-y-0 border-r-0"
      >
        <DialogBody>
          <ol aria-label="分流三段" className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-wg-muted">
            <li>第一段：選卡與參數</li>
            <li>第二段：預演</li>
            <li>第三段：確認</li>
          </ol>

          {loadFailed ? <ErrorState error={capabilitiesError} title="無法載入部署能力" onRetry={onRetryCapabilities} /> : null}

          <div role="radiogroup" aria-label="分流軌道" className="flex flex-col gap-3">
            <RouteCardA
              selected={shown.track === "A"}
              onSelect={() => change({ track: "A" })}
              form={shown}
              onChange={change}
              errors={errors}
              defaultModule={defaultModule}
              disabled={cardA !== null}
              disabledReason={cardA}
            />
            <RouteCardB
              selected={shown.track === "B"}
              onSelect={() => change({ track: "B" })}
              form={shown}
              onChange={change}
              errors={errors}
              templates={capabilities?.scaffoldTemplates ?? []}
              disabled={cardB !== null}
              disabledReason={cardB}
              githubDisabledReason={github}
            />
          </div>

          <table data-testid="route-eval-table" className="w-full border-collapse text-left text-[13px]">
            <caption className="mb-1 text-left text-sm font-medium">評估維度表</caption>
            <thead>
              <tr className="border-b border-wg-line">
                <th scope="col" className="py-1 pr-2 font-semibold">
                  維度
                </th>
                <th scope="col" className="py-1 pr-2 font-semibold">
                  軌道 A
                </th>
                <th scope="col" className="py-1 font-semibold">
                  軌道 B
                </th>
              </tr>
            </thead>
            <tbody>
              {ROUTE_EVAL_TABLE.map((row) => (
                <tr key={row.dimension} className="border-b border-wg-line align-top">
                  <th scope="row" className="py-1 pr-2 font-medium">
                    {row.dimension}
                  </th>
                  <td className="py-1 pr-2">{row.trackA}</td>
                  <td className="py-1">{row.trackB}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {differs && shown.track !== null ? (
            <div role="alert" data-testid="scope-differs" className="flex flex-col gap-2 rounded-md border border-wg-alert-border bg-wg-alert-bg px-3 py-3 text-sm">
              <p className="flex items-center gap-2 font-semibold text-wg-warning-text">
                <TriangleAlert size={16} aria-hidden />
                所選軌道與 PRD 的目標範圍不同
              </p>
              <p>
                PRD 的目標範圍：{project.targetScope}；所選：{ROUTE_TRACK_LABEL[shown.track]}
              </p>
              <Field label="差異理由" hint="必填，1 至 200 字" error={errors.scopeDiffersReason}>
                <Input
                  value={shown.scopeDiffersReason}
                  aria-invalid={errors.scopeDiffersReason ? true : undefined}
                  disabled={base !== null}
                  title={base ?? undefined}
                  onChange={(event) => change({ scopeDiffersReason: event.target.value })}
                />
              </Field>
            </div>
          ) : null}

          <section aria-label="預演" className="flex flex-col gap-2">
            <Button variant="ghost" iconLeft={ClipboardCheck} disabled={previewBlock !== null} title={previewBlock ?? undefined} loading={previewMut.isPending} onClick={() => void runPreview()}>
              預演
            </Button>
            {previewMut.isError && !previewCurrent ? <RouteErrorBox error={previewMut.error} /> : null}
            {previewCurrent && preview !== null ? <RouteActionList preview={preview.data} /> : null}
          </section>

          <section aria-label="確認" className="flex flex-col gap-2">
            {routeMut.isPending ? (
              <div data-testid="route-running" role="status" className="flex flex-col gap-2">
                <p className="text-sm font-medium">分流進行中，請勿關閉頁面…</p>
                <RouteStepsTimeline researchId={researchId} route={routeQuery.data ?? null} EventSourceCtor={EventSourceCtor} />
              </div>
            ) : null}
            {confirmError !== null ? <RouteErrorBox error={confirmError} /> : null}
          </section>
        </DialogBody>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            關閉
          </Button>
          <Button disabled={confirmBlock !== null} title={confirmBlock ?? undefined} loading={routeMut.isPending} onClick={() => void runConfirm()}>
            確認執行
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
