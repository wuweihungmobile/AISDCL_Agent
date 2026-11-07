"use client";

/**
 * 建立 Tag 確認框（FR-R2P-20-3；TCS-ResearchToPRD-P2-20261107 AT-962-21-4；IFACE-P2 §6.2；D-138 Q-4、Q-8；D-142 ⚖P2-9）。
 *
 * 設計要點（為什麼這樣做）：
 *  - **semver 即時驗證**：不合就停用送出並顯示規則；規則字面與 Bridge、console-api 的 `tagName` 正規式逐字相同（TCS §5.1「`tagName` 正規式」，長度至多 64），
 *    不在輸入框設 `maxLength`——超長要看得到錯誤，而不是被默默截掉。`message` 選填、至多 200 字（計數器；同樣不截斷）。
 *  - **`push` 預設未勾**並附說明：勾選且遠端 origin 存在才推送，絕不 force。`createGithubRelease` **不顯示、不送**（P2 不實作；D-138 Q-8）。
 *  - **不補償、不回滾**：Tag 與推送是外部副作用，失敗只留可重送的冪等路徑；`delivery_step_failed` 的 `failure_step=push` 明說「本地 Tag 已建」，不提供回滾。
 *  - **錯誤取登記表**：文案走 `researchErrorText`（`RESEARCH_REASON_TEXT`＋`DELIVERY_STEP_LABEL`）；409 `details.unmet[]` 逐項中文；
 *    422 `digest_mismatch` 逐一列出漂移路徑並給「發起 SCR」入口（`sourceKind` 預填 `SCG4`；重用 `ScrLaunchButton`）；422 `route_unsupported_in_deployment` 如實顯示缺項。全部純文字。
 *  - 權限：僅 ADMIN 能開啟（入口在 `ReleaseActions`）；本框內送出再判一次，非 ADMIN 送出請求數為 0。
 */
import { useState } from "react";

import { ScrLaunchButton } from "@/components/domain/research/ScrRequestDialog";
import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/client";
import { useCreateResearchTag } from "@/lib/api/queries";
import type { ResearchTagResult } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  DELIVER_LABEL,
  READONLY_TITLE,
  RESEARCH_REASONS,
  TAG_ADMIN_ONLY_TEXT,
  TAG_MESSAGE_MAX,
  TAG_NAME_MAX,
  TAG_NAME_PATTERN,
  TAG_RULE_TEXT,
  gateErrorView,
  routeMissingLabels,
} from "@/lib/domain/research";

/** 回 null＝合法；空字串另由送出鈕停用處理（不顯示錯誤，避免一開框就紅）。 */
export function tagNameError(value: string): string | null {
  if (value === "") return null;
  if ([...value].length > TAG_NAME_MAX) return `版本號最多 ${TAG_NAME_MAX} 字`;
  return TAG_NAME_PATTERN.test(value) ? null : TAG_RULE_TEXT;
}

const detailString = (error: unknown, ...keys: string[]): string => {
  if (!(error instanceof ApiError)) return "";
  for (const key of keys) {
    const value = error.details?.[key];
    if (typeof value === "string" && value !== "") return value;
  }
  return "";
};

export function TagConfirmDialog({ researchId, open, onOpenChange }: { researchId: string; open: boolean; onOpenChange: (open: boolean) => void }) {
  const { role } = useAuth();
  const isAdmin = role === "ADMIN";
  const create = useCreateResearchTag();
  const [tagName, setTagName] = useState("");
  const [message, setMessage] = useState("");
  const [push, setPush] = useState(false);
  const [result, setResult] = useState<ResearchTagResult | null>(null);
  const [error, setError] = useState<unknown>(null);

  const nameError = tagNameError(tagName);
  const messageLen = [...message].length;
  const messageError = messageLen > TAG_MESSAGE_MAX ? `備註最多 ${TAG_MESSAGE_MAX} 字` : null;
  const canSubmit = isAdmin && tagName !== "" && nameError === null && messageError === null && !create.isPending;

  function submit() {
    if (!canSubmit) return;
    setError(null);
    create.mutate({ id: researchId, body: { tagName, push, ...(message.trim() === "" ? {} : { message: message.trim() }) } }, { onSuccess: (data) => setResult(data), onError: (e) => setError(e) });
  }

  const view = error === null ? null : gateErrorView(error);
  const forbidden = error instanceof ApiError && error.status === 403;
  // `gateErrorView` 的 digest_mismatch 文案（凍結檔與摘要不一致、要改規格請發起 SCR）對 Tag 前置的同一漂移同樣適用；其餘 reason 它退回 `researchErrorText`。
  const errorText = forbidden ? TAG_ADMIN_ONLY_TEXT : (view?.text ?? "");
  const failureStep = error instanceof ApiError && error.reason === RESEARCH_REASONS.DELIVERY_STEP_FAILED ? detailString(error, "failureStep", "failure_step") : "";
  const missing = error instanceof ApiError && error.reason === RESEARCH_REASONS.ROUTE_UNSUPPORTED_IN_DEPLOYMENT ? routeMissingLabels(error.details?.missing) : [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title={DELIVER_LABEL.createTag} description="建立版本標籤並寫入追溯快照" data-testid="tag-dialog">
        <DialogBody>
          {result !== null ? (
            <div role="status" data-testid="tag-result" className="flex flex-col gap-2 text-sm">
              <p className="font-semibold">已建立 Tag {result.delivery.ref}</p>
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
                <dt className="text-wg-muted">Tag</dt>
                <dd data-testid="tag-result-ref" className="font-mono break-all">
                  {result.delivery.ref}
                </dd>
                <dt className="text-wg-muted">提交編號</dt>
                <dd data-testid="tag-result-commit" className="font-mono">
                  {(result.delivery.commitSha ?? "").slice(0, 12)}
                </dd>
                <dt className="text-wg-muted">追溯快照 sha256</dt>
                <dd data-testid="tag-result-sha" className="font-mono break-all">
                  {result.snapshot.sha256}
                </dd>
                <dt className="text-wg-muted">快照路徑</dt>
                <dd data-testid="tag-result-path" className="font-mono break-all">
                  {result.snapshot.relPath}
                </dd>
              </dl>
            </div>
          ) : (
            <>
              <Field label="版本號（Tag 名稱）" error={nameError ?? undefined}>
                <Input
                  value={tagName}
                  onChange={(e) => setTagName(e.target.value)}
                  placeholder="v1.0.0"
                  autoComplete="off"
                  spellCheck={false}
                  aria-invalid={nameError !== null}
                  data-testid="tag-name"
                />
              </Field>
              <p data-testid="tag-rule" className="-mt-2 text-xs text-wg-muted">
                {TAG_RULE_TEXT}
              </p>
              <Field label="備註" hint="（選填）" error={messageError ?? undefined}>
                <Textarea value={message} onChange={(e) => setMessage(e.target.value)} aria-invalid={messageError !== null} data-testid="tag-message" />
              </Field>
              <p data-testid="tag-message-counter" className="-mt-2 text-xs text-wg-muted">
                剩餘 {TAG_MESSAGE_MAX - messageLen} 字（上限 {TAG_MESSAGE_MAX} 字）；備註只存紀錄，不會寫進 Tag 訊息
              </p>
              <label className="flex items-start gap-2 text-sm">
                <input type="checkbox" checked={push} onChange={(e) => setPush(e.target.checked)} className="mt-1" data-testid="tag-push" />
                <span>
                  <span className="font-medium">{DELIVER_LABEL.pushRemote}</span>
                  <span data-testid="tag-push-note" className="block text-wg-muted">
                    勾選且遠端 origin 存在才推送；不會 force。
                  </span>
                </span>
              </label>
              {error !== null && view !== null ? (
                <div role="alert" data-testid="tag-error" className="flex flex-col gap-2 rounded-md border border-wg-error px-3 py-2 text-sm">
                  <p>{errorText}</p>
                  {failureStep === "push" ? <p data-testid="tag-push-failed-note">本地 Tag 已建立；可直接重送同一個動作續跑（系統不提供回滾）。</p> : null}
                  {view.unmet.length > 0 ? (
                    <ul data-testid="tag-unmet" className="list-disc pl-5">
                      {view.unmet.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  ) : null}
                  {view.drift.length > 0 ? (
                    <ul data-testid="tag-drift" className="list-disc pl-5">
                      {view.drift.map((path) => (
                        <li key={path} className="font-mono break-all">
                          {path}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  {missing.length > 0 ? (
                    <ul data-testid="tag-missing" className="list-disc pl-5">
                      {missing.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  ) : null}
                  {view.offerScr ? <ScrLaunchButton researchId={researchId} sourceKind="SCG4" label="發起 SCR" /> : null}
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
            <Button disabled={!canSubmit} loading={create.isPending} title={isAdmin ? undefined : role === "VIEWER" ? READONLY_TITLE : TAG_ADMIN_ONLY_TEXT} onClick={submit} data-testid="tag-submit">
              建立
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
