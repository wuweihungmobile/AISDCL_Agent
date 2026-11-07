"use client";

/**
 * 合併請求（PR）區塊與確認框（FR-R2P-20-4；TCS-ResearchToPRD-P2-20261107 AT-962-21-5、21-E-3；IFACE-P2 §6.4；D-138 Q-10；D-142 ⚖P2-13；D-151）。
 *
 * 三種呈現（為什麼這樣做）：
 *  - **已有 PR**（`PULL_REQUEST` 且 CREATED 的交付列）：顯示 PR 編號與連結；外部連結一律經 {@link SafeExternalLink}
 *    （只有 https 才成連結、`target="_blank"`、`rel="noopener noreferrer"`；其餘當純文字，避免 `javascript:`）。
 *  - **無 PR 且為 ADMIN**：「建立 PR」→ 確認框預覽**標題、內文四段與推送目標分支**，須勾「已預覽」才能送（`bodyPreviewAck: true`）。
 *  - **OPERATOR／VIEWER、或前置缺項**（`gh` 不可用、沒有 origin）：顯示「尚未建立」與逐項原因；VIEWER 不渲染任何按鈕（P0 的 VIEWER 全按鈕鎖）。
 *
 *  預覽**不是第二份真相**：標題與內文由 Bridge 確定性產生（`delivery.pr_title`／`pr_body`），前端只依同一份模板字面與追溯表資料（`rpNo`、`title` 截 60 字、`frTotal`、`acTotal`、
 *  已覆蓋、未覆蓋）組出同形預覽；前端拿不到的值（PRD 版本與摘要、凍結 PRD 路徑）顯示「由後端填入」，並明說實際內容以後端產生為準（D-151）。
 *  回應 `created:false`（該分支已有 PR）顯示既有連結而非「已建立」；502 `delivery_step_failed`（`failure_step` 為 push 或 pr_create）顯示失敗步驟，不顯示成功態，不補償。
 */
import { GitPullRequest } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { ApiError } from "@/lib/api/client";
import { useCreateResearchPr, useResearchRoute } from "@/lib/api/queries";
import type { ResearchDelivery, ResearchDeliveryOverview, ResearchPrResult, ResearchTraceability } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { DELIVER_LABEL, PR_ADMIN_ONLY_TEXT, READONLY_TITLE, RESEARCH_REASONS, ROUTE_MISSING_ITEM_LABEL, researchErrorText } from "@/lib/domain/research";

/** 與 Bridge `delivery.PR_TITLE_CHARS`、`PR_TITLE_TEMPLATE` 同一字面（標題截字數與模板）。 */
export const PR_TITLE_CHARS = 60;
const PENDING_FROM_BACKEND = "由後端依凍結 PRD 填入";
/** 缺項（`details.missing[].item`）中文：沿分流登記表，另補 PR 專屬的 origin。 */
const MISSING_LABEL: Readonly<Record<string, string>> = { ...ROUTE_MISSING_ITEM_LABEL, origin: "尚未設定遠端 origin" };

export function prTitlePreview(rpNo: string, title: string, frTotal: number, acTotal: number): string {
  const clipped = Array.from(title).slice(0, PR_TITLE_CHARS).join("");
  return `feat: ${rpNo} ${clipped}（${frTotal} FR／${acTotal} AC）`;
}

export function prBodyPreview(researchId: string, rpNo: string, totals: ResearchTraceability["totals"]): string {
  return [
    `## 摘要\n- 研究專案：${rpNo}（${researchId}）\n- PRD：${PENDING_FROM_BACKEND}\n- 規模：${totals.frTotal} FR／${totals.acTotal} AC`,
    `## 追溯表摘要\n- AC 總數：${totals.acTotal}；已覆蓋：${totals.covered}；未覆蓋：${totals.uncovered}`,
    `## 規格依據\n- 凍結 PRD：${PENDING_FROM_BACKEND}`,
    "## 確認\n合併與雲端 CI 綠由人確認。",
  ].join("\n\n");
}
/** 外部連結：只有 https 才渲染成 `<a>`（新分頁、`rel="noopener noreferrer"`）；否則顯示純文字。 */
export function SafeExternalLink({ href, children }: { href: string | null; children: ReactNode }) {
  if (href === null || !/^https:\/\//i.test(href)) return <span className="break-all">{href ?? children}</span>;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="font-medium break-all text-wg-primary underline">
      {children}
    </a>
  );
}

/** 422 `details.missing[].item`（gh｜gh_auth｜origin｜repo_writable）→ 中文；未登記的原樣顯示。 */
function missingItemLabels(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((entry) => (typeof entry === "string" ? entry : typeof entry === "object" && entry !== null && typeof (entry as { item?: unknown }).item === "string" ? (entry as { item: string }).item : ""))
    .filter((item) => item !== "")
    .map((item) => MISSING_LABEL[item] ?? item);
}

const detailString = (error: unknown, ...keys: string[]): string => {
  if (!(error instanceof ApiError)) return "";
  for (const key of keys) {
    const value = error.details?.[key];
    if (typeof value === "string" && value !== "") return value;
  }
  return "";
};

function PrDialog({
  researchId,
  rpNo,
  title,
  traceability,
  onOpenChange,
}: {
  researchId: string;
  rpNo: string;
  title: string;
  traceability: ResearchTraceability;
  onOpenChange: (open: boolean) => void;
}) {
  const { role } = useAuth();
  const isAdmin = role === "ADMIN";
  const route = useResearchRoute(researchId);
  const create = useCreateResearchPr();
  const [ack, setAck] = useState(false);
  const [result, setResult] = useState<ResearchPrResult | null>(null);
  const [error, setError] = useState<unknown>(null);

  const totals = traceability.totals;
  const branch = route.data?.gitBranch ?? null;
  const canSubmit = isAdmin && ack && !create.isPending && result === null;

  function submit() {
    if (!canSubmit) return;
    setError(null);
    create.mutate({ id: researchId, body: { bodyPreviewAck: true } }, { onSuccess: (data) => setResult(data), onError: (e) => setError(e) });
  }

  const failureStep = error instanceof ApiError && error.reason === RESEARCH_REASONS.DELIVERY_STEP_FAILED ? detailString(error, "failureStep", "failure_step") : "";
  const missing = error instanceof ApiError && error.reason === RESEARCH_REASONS.ROUTE_UNSUPPORTED_IN_DEPLOYMENT ? missingItemLabels(error.details?.missing) : [];
  const forbidden = error instanceof ApiError && error.status === 403;
  const pr = result?.delivery ?? null;

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent title={DELIVER_LABEL.createPr} description="預覽合併請求的標題、內文與推送目標" data-testid="pr-dialog">
        <DialogBody>
          {result !== null && pr !== null ? (
            <div role="status" data-testid="pr-result" data-created={String(result.created)} className="flex flex-col gap-2 text-sm">
              <p className="font-semibold">{result.created ? `已建立 PR #${pr.ref}` : `這個分支已有 PR #${pr.ref}（沒有重複建立）`}</p>
              <SafeExternalLink href={pr.url}>{pr.url ?? `PR #${pr.ref}`}</SafeExternalLink>
            </div>
          ) : (
            <>
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-sm">
                <dt className="text-wg-muted">推送目標分支</dt>
                <dd data-testid="pr-preview-branch" className="font-mono break-all">
                  {branch ?? "由後端依分流決定的分支"}
                </dd>
                <dt className="text-wg-muted">標題</dt>
                <dd data-testid="pr-preview-title" className="break-words">
                  {prTitlePreview(rpNo, title, totals.frTotal, totals.acTotal)}
                </dd>
                <dt className="text-wg-muted">內文</dt>
                <dd>
                  <pre data-testid="pr-preview-body" className="rounded-md border border-wg-line bg-white px-3 py-2 font-sans text-[13px] break-words whitespace-pre-wrap">
                    {prBodyPreview(researchId, rpNo, totals)}
                  </pre>
                </dd>
              </dl>
              <p data-testid="pr-preview-note" className="text-[13px] text-wg-muted">
                實際標題與內文由後端依凍結 PRD 與追溯表確定性產生；此處是同一模板的預覽，帶「{PENDING_FROM_BACKEND}」的欄位以建立結果為準。
              </p>
              <label className="flex items-start gap-2 text-sm">
                <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} className="mt-1" data-testid="pr-ack" />
                <span>我已預覽標題、內文與推送目標，確認建立 PR</span>
              </label>
              {error !== null ? (
                <div role="alert" data-testid="pr-error" className="flex flex-col gap-2 rounded-md border border-wg-error px-3 py-2 text-sm">
                  <p>{forbidden ? PR_ADMIN_ONLY_TEXT : researchErrorText(error)}</p>
                  {failureStep !== "" ? (
                    <p data-testid="pr-failed-step">
                      失敗步驟：{failureStep === "pr_create" ? "建立 PR" : failureStep === "push" ? "推送到遠端" : failureStep}（未建立 PR；已完成的步驟會保留，可重送）
                    </p>
                  ) : null}
                  {missing.length > 0 ? (
                    <ul data-testid="pr-missing" className="list-disc pl-5">
                      {missing.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}
            </>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            {result === null ? "取消" : "關閉"}
          </Button>
          {result === null ? (
            <Button disabled={!canSubmit} loading={create.isPending} title={isAdmin ? (ack ? undefined : "請先勾選已預覽") : PR_ADMIN_ONLY_TEXT} onClick={submit} data-testid="pr-submit">
              建立 PR
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function PrConfirmDialog({
  researchId,
  rpNo,
  title,
  overview,
  traceability,
}: {
  researchId: string;
  rpNo: string;
  title: string;
  overview: ResearchDeliveryOverview;
  traceability: ResearchTraceability;
}) {
  const { role } = useAuth();
  const [open, setOpen] = useState(false);
  const isAdmin = role === "ADMIN";
  const existing: ResearchDelivery | undefined = overview.deliveries.find((d) => d.kind === "PULL_REQUEST" && d.status === "CREATED");

  const missing: string[] = [];
  if (overview.preconditions.ghAvailable === false) missing.push(MISSING_LABEL.gh);
  if (overview.preconditions.hasOrigin === false) missing.push(MISSING_LABEL.origin);
  // 概覽的前置判斷（gh、origin）；Bridge 422 的 details.missing 另在對話框內逐項顯示
  const roleReason = isAdmin ? null : role === "VIEWER" ? READONLY_TITLE : PR_ADMIN_ONLY_TEXT;

  return (
    <section data-testid="pr-block" className="flex flex-col gap-2">
      <h4 className="text-base font-semibold">合併請求（PR）</h4>
      {existing !== undefined ? (
        <p data-testid="pr-existing" className="text-sm">
          PR #{existing.ref}：<SafeExternalLink href={existing.url}>{existing.url ?? `PR #${existing.ref}`}</SafeExternalLink>
        </p>
      ) : (
        <div data-testid="pr-none" className="flex flex-col gap-2 text-sm">
          <p className="font-medium">尚未建立</p>
          {roleReason !== null ? (
            <p data-testid="pr-role-reason" className="text-wg-muted">
              {roleReason}
            </p>
          ) : null}
          {missing.length > 0 ? (
            <div data-testid="pr-missing-block" className="text-wg-muted">
              <p>無法建立 PR：</p>
              <ul className="list-disc pl-5">
                {missing.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {isAdmin ? (
            <div>
              <Button variant="ghost" iconLeft={GitPullRequest} disabled={missing.length > 0} title={missing.length > 0 ? missing[0] : undefined} onClick={() => setOpen(true)} data-testid="pr-create">
                {DELIVER_LABEL.createPr}
              </Button>
            </div>
          ) : null}
        </div>
      )}
      {open ? <PrDialog researchId={researchId} rpNo={rpNo} title={title} traceability={traceability} onOpenChange={setOpen} /> : null}
    </section>
  );
}
