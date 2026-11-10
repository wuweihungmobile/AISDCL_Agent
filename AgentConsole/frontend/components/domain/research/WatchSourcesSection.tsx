"use client";

/**
 * 研究來源設定的「自我進化追蹤來源」區（TCS-ResearchRegistry-20261110 AC-965-8；FR-R2P-24；PRD 頁面 0「研究來源設定」）：
 * 清單（slug、網址、種類、層、展開設定、啟用狀態）、新增表單（前端即時驗證）、停用／重新啟用、同步狀態列與「同步到自我進化」鈕。
 *
 * 設計要點（為什麼這樣做）：
 *  - **只掛在 ADMIN 的對話框裡**（`AllowlistDialog` 對非 ADMIN 整個不渲染）；本元件自己也再擋一次：非 ADMIN 不渲染、不發任何請求（防被別處單獨引用時漏風）。
 *  - **新增或停用成功後自動同步**：帳號有沒有自我進化寫入權由 backend 判（403 `si_write_forbidden`），前端不維護名單——被拒就照實顯示原因、不重試（重試無用）。
 *    POST／PATCH 失敗不送 sync（沒有東西要同步）。
 *  - **同步單線＋尾隨去重**：同時只有一個 sync 在飛；飛行中的自動同步請求（再新增一筆）只「恰再排一次」，不平行送兩個；手動連點在飛行中一律忽略。
 *  - **URL 原樣判定**：前端驗證只擋、不改寫（大寫 host、顯式 :443 由使用者自行改）；slug 的小寫建議只當提示。
 *  - 全部文案取自 `lib/domain/researchRegistry.ts`（單一登記處）；API 回傳的字串（slug、網址、extract、錯誤訊息）一律只以文字節點渲染。
 */
import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { useAddWatchSource, usePatchWatchSource, useRegistrySync, useRegistrySyncStatus, useWatchSources } from "@/lib/api/queries";
import type { WatchSource } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { SOURCE_LAYER_LABEL } from "@/lib/domain/research";
import {
  EMPTY_WATCH_SOURCE_FORM,
  EXPAND_MODES,
  WATCH_KINDS,
  WATCH_KIND_LABEL,
  WATCH_LAYER_OPTIONS,
  fetchMaxWarning,
  registrySyncErrorMessage,
  registrySyncOutcomeMessage,
  registrySyncText,
  slugSuggestion,
  toWatchSourceRequest,
  watchExpandText,
  watchSourceCountText,
  watchSourceFormErrors,
  watchSourceWriteErrorText,
  type RegistrySyncMessage,
  type WatchSourceForm,
  type WatchSourceFormField,
} from "@/lib/domain/researchRegistry";
import { cn } from "@/lib/utils";

const layerText = (layer: string): string => (SOURCE_LAYER_LABEL as Readonly<Record<string, string | undefined>>)[layer] ?? layer;
const kindText = (kind: string): string => (WATCH_KIND_LABEL as Readonly<Record<string, string | undefined>>)[kind] ?? kind;

/** 同步到自我進化的協調器：單線＋尾隨去重（見檔頭）；回傳目前訊息、進行中旗標與兩個入口（自動排程、手動）。 */
function useRegistrySyncRunner() {
  const sync = useRegistrySync();
  const mutateRef = useRef(sync.mutateAsync);
  useEffect(() => {
    mutateRef.current = sync.mutateAsync;
  }, [sync.mutateAsync]);
  const inFlight = useRef(false);
  const trailing = useRef(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<RegistrySyncMessage | null>(null);

  const run = useCallback(async (mode: "auto" | "manual") => {
    if (inFlight.current) {
      // 飛行中：自動請求排成「恰再一次」；手動連點直接忽略
      if (mode === "auto") trailing.current = true;
      return;
    }
    inFlight.current = true;
    setBusy(true);
    try {
      do {
        trailing.current = false;
        try {
          const result = await mutateRef.current();
          setMessage(registrySyncOutcomeMessage(result.outcome));
        } catch (error) {
          setMessage(registrySyncErrorMessage(error));
        }
      } while (trailing.current);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }, []);
  return { busy, message, runAuto: () => void run("auto"), runManual: () => void run("manual") };
}

function SyncPanel({ runner, enabledCount }: { runner: ReturnType<typeof useRegistrySyncRunner>; enabledCount: number }) {
  const status = useRegistrySyncStatus(true);
  const data = status.data;
  const warning = fetchMaxWarning(enabledCount, data?.researchFetchMax);
  return (
    <div className="flex flex-col gap-2 rounded-md border border-wg-line bg-wg-base px-3 py-2.5" data-testid="registry-sync-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {data === undefined ? (
          status.isError ? (
            <p role="status" data-testid="registry-status" className="text-sm">
              量不到同步狀態
            </p>
          ) : (
            <div aria-busy="true" aria-label="同步狀態載入中" role="status" className="w-48">
              <Skeleton className="h-5 rounded-md" />
            </div>
          )
        ) : (
          <p role="status" data-testid="registry-status" data-state={data.state} className="text-sm font-medium">
            {registrySyncText(data)}
          </p>
        )}
        <Button size="sm" variant="ghost" iconLeft={RefreshCw} loading={runner.busy} onClick={runner.runManual}>
          同步到自我進化
        </Button>
      </div>
      {warning === null ? null : (
        <p role="note" data-testid="watch-fetch-warning" className="text-sm text-wg-warning-text">
          {warning}
        </p>
      )}
      {runner.message === null ? null : (
        <div className="flex flex-wrap items-center gap-2">
          <p role={runner.message.tone === "error" ? "alert" : "status"} data-testid="registry-sync-message" className={cn("text-sm", runner.message.tone === "error" && "text-wg-error")}>
            {runner.message.text}
          </p>
          {runner.message.retry ? (
            <Button size="sm" variant="ghost" disabled={runner.busy} onClick={runner.runManual}>
              重試同步
            </Button>
          ) : null}
        </div>
      )}
    </div>
  );
}

function WatchRow({ row, busy, onToggle }: { row: WatchSource; busy: boolean; onToggle: (row: WatchSource, enabled: boolean) => void }) {
  const reenableBlocked = !row.enabled && !row.hostAllowed;
  return (
    <tr data-testid="watch-row" data-slug={row.slug} data-enabled={row.enabled} className={cn("border-t border-wg-line align-top", !row.enabled && "text-wg-muted")}>
      <td className="px-3 py-2 font-mono text-xs break-all">{row.slug}</td>
      <td className="px-3 py-2 font-mono text-xs break-all select-all">{row.url}</td>
      <td className="px-3 py-2 whitespace-nowrap">{kindText(row.kind)}</td>
      <td className="px-3 py-2 whitespace-nowrap">{layerText(row.layer)}</td>
      <td className="px-3 py-2 text-xs break-all">{watchExpandText(row.expand)}</td>
      <td className="px-3 py-2">
        <span className="whitespace-nowrap">{row.enabled ? "啟用中" : "已停用"}</span>
        {row.hostAllowed ? null : (
          <span className="block text-xs text-wg-warning-text" data-testid="watch-host-closed">
            網域未開放：請到上方網域清單開放 {row.host}
          </span>
        )}
      </td>
      <td className="px-3 py-2">
        {row.enabled ? (
          <Button size="sm" variant="ghost" loading={busy} aria-label={`停用 ${row.slug}`} onClick={() => onToggle(row, false)}>
            停用
          </Button>
        ) : (
          <Button
            size="sm"
            variant="ghost"
            loading={busy}
            disabled={reenableBlocked}
            aria-label={`重新啟用 ${row.slug}`}
            title={reenableBlocked ? "這個來源的網域還沒開放，請先在上方網域清單開放後再重新啟用" : "重新啟用這個追蹤來源"}
            onClick={() => onToggle(row, true)}
          >
            重新啟用
          </Button>
        )}
      </td>
    </tr>
  );
}

function AddWatchForm({ onAdded }: { onAdded: () => void }) {
  const toast = useToast();
  const add = useAddWatchSource();
  const uid = useId();
  const [form, setForm] = useState<WatchSourceForm>(EMPTY_WATCH_SOURCE_FORM);
  const [errors, setErrors] = useState<Partial<Record<WatchSourceFormField, string>>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const change = (patch: Partial<WatchSourceForm>) => setForm((current) => ({ ...current, ...patch }));
  const errId = (field: WatchSourceFormField) => `${uid}-${field}-error`;
  const invalid = (field: WatchSourceFormField) => (errors[field] ? { "aria-invalid": true as const, "aria-describedby": errId(field) } : {});
  const errorText = (field: WatchSourceFormField) =>
    errors[field] ? (
      <p id={errId(field)} role="alert" className="text-[13px] text-wg-error">
        {errors[field]}
      </p>
    ) : null;
  const suggestion = slugSuggestion(form.slug);
  const errorCount = Object.keys(errors).length;

  async function submit(event: FormEvent) {
    event.preventDefault();
    const found = watchSourceFormErrors(form);
    setSubmitError(null);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    try {
      const created = await add.mutateAsync(toWatchSourceRequest(form));
      toast.success(`已新增追蹤來源 ${created.slug}`);
      setForm(EMPTY_WATCH_SOURCE_FORM);
      onAdded();
    } catch (e) {
      setSubmitError(watchSourceWriteErrorText(e));
    }
  }

  return (
    <form onSubmit={submit} noValidate aria-label="新增追蹤來源" className="flex flex-col gap-3">
      <h4 className="text-sm font-semibold">新增追蹤來源</h4>
      {errorCount > 0 ? (
        <p role="alert" data-testid="watch-form-summary" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
          有 {errorCount} 個欄位需要修正，請看欄位下方的說明。
        </p>
      ) : null}
      {submitError ? (
        <p role="alert" data-testid="watch-submit-error" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
          {submitError}
        </p>
      ) : null}
      <div className="grid gap-3 md:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Field label="識別碼" hint="（小寫英數與連字號）">
            <Input value={form.slug} onChange={(e) => change({ slug: e.target.value })} autoComplete="off" {...invalid("slug")} />
          </Field>
          {suggestion === null ? null : (
            <p role="note" data-testid="watch-slug-suggestion" className="text-xs text-wg-muted">
              識別碼須為小寫，建議改成 {suggestion}（系統不會自動改）
            </p>
          )}
          {errorText("slug")}
        </div>
        <div className="flex flex-col gap-1.5">
          <Field label="種類">
            <Select value={form.kind} onChange={(e) => change({ kind: e.target.value })} {...invalid("kind")}>
              {WATCH_KINDS.map((kind) => (
                <option key={kind} value={kind}>
                  {WATCH_KIND_LABEL[kind]}
                </option>
              ))}
            </Select>
          </Field>
          {errorText("kind")}
        </div>
        <div className="flex flex-col gap-1.5 md:col-span-2">
          <Field label="網址" hint="（https 開頭、主機名稱全小寫、不帶埠號）">
            <Input value={form.url} onChange={(e) => change({ url: e.target.value })} autoComplete="off" spellCheck={false} {...invalid("url")} />
          </Field>
          {errorText("url")}
        </div>
        <div className="flex flex-col gap-1.5">
          <Field label="來源層">
            <Select value={form.layer} onChange={(e) => change({ layer: e.target.value })} {...invalid("layer")}>
              {WATCH_LAYER_OPTIONS.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
          {errorText("layer")}
        </div>
        <div className="flex flex-col gap-1.5">
          <Field label="抓取說明" hint="（要逐字保留什麼，1～200 字）">
            <Input value={form.extract} onChange={(e) => change({ extract: e.target.value })} autoComplete="off" {...invalid("extract")} />
          </Field>
          {errorText("extract")}
        </div>
      </div>
      <fieldset className="flex flex-col gap-2 rounded-md border border-wg-line px-3 py-2.5">
        <legend className="px-1 text-sm font-medium">展開設定（選填；三欄全空或全填）</legend>
        <div className="grid gap-3 md:grid-cols-3">
          <Field label="展開方式">
            <Select value={form.expandMode} onChange={(e) => change({ expandMode: e.target.value })} {...invalid("expand")}>
              <option value="">不展開</option>
              {EXPAND_MODES.map((mode) => (
                <option key={mode} value={mode}>
                  {mode}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="路徑前綴" hint="（例 /blog/）">
            <Input value={form.expandPrefix} onChange={(e) => change({ expandPrefix: e.target.value })} autoComplete="off" {...invalid("expand")} />
          </Field>
          <Field label="最多幾頁" hint="（1～3）">
            <Input inputMode="numeric" value={form.expandMax} onChange={(e) => change({ expandMax: e.target.value })} autoComplete="off" {...invalid("expand")} />
          </Field>
        </div>
        {errorText("expand")}
      </fieldset>
      <p className="text-xs text-wg-muted">網址會原樣送出、不自動修正；新增成功後會自動同步到自我進化。識別碼用過就不會再重用（含已停用的）。</p>
      <div className="flex justify-end">
        <Button type="submit" loading={add.isPending}>
          新增追蹤來源
        </Button>
      </div>
    </form>
  );
}

function WatchSourcesBody() {
  const toast = useToast();
  const list = useWatchSources(true);
  const patch = usePatchWatchSource();
  const runner = useRegistrySyncRunner();
  const [busySlug, setBusySlug] = useState<string | null>(null);
  const [toggleError, setToggleError] = useState<string | null>(null);
  const rows = list.data;

  async function toggle(row: WatchSource, enabled: boolean) {
    setBusySlug(row.slug);
    setToggleError(null);
    try {
      await patch.mutateAsync({ slug: row.slug, body: { enabled } });
      toast.success(`${enabled ? "已重新啟用" : "已停用"} ${row.slug}`);
      runner.runAuto();
    } catch (e) {
      setToggleError(`${enabled ? "重新啟用" : "停用"} ${row.slug} 失敗：${watchSourceWriteErrorText(e)}`);
    } finally {
      setBusySlug(null);
    }
  }

  const enabledCount = rows === undefined ? 0 : rows.filter((r) => r.enabled).length;
  return (
    <>
      <p className="text-sm text-wg-muted">自我進化會依這份清單去抓取資料（網域須先在上方網域清單開放）。停用的來源不會被抓，但識別碼仍保留。</p>
      <SyncPanel runner={runner} enabledCount={enabledCount} />
      {toggleError === null ? null : (
        <p role="alert" data-testid="watch-toggle-error" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
          {toggleError}
        </p>
      )}
      {rows === undefined ? (
        list.isError ? (
          <div role="alert" className="flex items-center gap-2 text-sm">
            <span>無法載入追蹤來源清單</span>
            <Button size="sm" variant="ghost" onClick={() => void list.refetch()}>
              重試
            </Button>
          </div>
        ) : (
          <div aria-busy="true" aria-label="追蹤來源清單載入中" role="status">
            <Skeleton className="h-24 rounded-lg" />
          </div>
        )
      ) : (
        <>
          <p data-testid="watch-count" className="text-sm font-medium">
            {watchSourceCountText(rows)}
          </p>
          <div className="overflow-x-auto rounded-md border border-wg-line">
            <table className="w-full min-w-[760px] border-collapse text-sm" data-testid="watch-table">
              <caption className="sr-only">自我進化追蹤來源清單</caption>
              <thead>
                <tr className="bg-wg-base text-left text-xs text-wg-muted">
                  {["識別碼", "網址", "種類", "層", "展開設定", "狀態", "動作"].map((label) => (
                    <th key={label} scope="col" className="px-3 py-2 font-medium">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <WatchRow key={row.slug} row={row} busy={busySlug === row.slug} onToggle={(r, enabled) => void toggle(r, enabled)} />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <AddWatchForm onAdded={runner.runAuto} />
    </>
  );
}

/** 「自我進化追蹤來源」區：僅 ADMIN（非 ADMIN 不渲染、不發任何 `watch-sources` 或 `research-registry` 請求）。 */
export function WatchSourcesSection() {
  const { role } = useAuth();
  if (role !== "ADMIN") return null;
  return (
    <section aria-labelledby="watch-sources-title" data-testid="watch-sources-section" className="flex flex-col gap-3 rounded-md border border-wg-line bg-wg-surface px-3 py-3">
      <h3 id="watch-sources-title" className="text-base font-semibold">
        自我進化追蹤來源
      </h3>
      <WatchSourcesBody />
    </section>
  );
}
