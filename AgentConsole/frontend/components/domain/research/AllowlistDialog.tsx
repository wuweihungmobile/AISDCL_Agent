"use client";

/**
 * 研究來源設定（ADMIN 專屬的 allowlist 對話框；FR-R2P-04；TCS-ResearchToPRD-P0-20261102 AT-960-19-8；PRD 頁面 0「研究來源設定」）：
 * 清單（區分部署環境變數基底 `ENV` 與管理員新增的 `ADMIN`）、新增網域、停用條目；Reddit 網域須先勾選「已自建 Reddit 應用並接受其條款」。
 *
 * 設計要點（為什麼這樣做）：
 *  - **只有 ADMIN 看得到入口**：其他角色整個元件不渲染（不是停用）——這是管理面，不是「能看但不能按」的資料面（後端另有 403 把關：OPERATOR、VIEWER 送出一律被擋）。
 *  - **ENV 基底條目不可動**：它們沒有資料列（`id` 為 null），沒有停用鈕；ADMIN 條目才可停用（`PATCH …/allowlist/<id>` 本文只有 `enabled`），也可再啟用。
 *    `minIntervalSeconds` 建立後不可改（受控更新守衛只放行 `enabled` 與停用欄），要調整間隔＝停用後重建；實際間隔取 Bridge 內建下限與條目值的較大者，這裡只能把間隔拉長。
 *  - **稽核由後端做**（D-62(1)：寫入成功後 console-api 以 `AuditTrail.note` 標註）；前端只顯示結果，不另記任何稽核。
 *  - 新增成功後清單與能力探針一併重抓（`webLayerEnabled` 會跟著變：Web 層清單有條目才算啟用）；失敗原因（含 Bridge 尚未實作的 502）以白話顯示在對話框內，不關閉、不假裝成功。
 *  - **有效主機另列**（INT-08 前端側）：清單含已停用的條目，研究階段實際會連的主機是能力探針的 `fetchHosts`（基底加啟用中的 ADMIN 條目），所以清單下方另有一區只讀的
 *    「目前有效的抓取主機」，並帶出框架樹、分流腳手架根與 repo 可寫（能力探針的其餘新鍵）；探針失敗只影響這一區（說明原因），清單與新增表單照常。
 */
import { Globe } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { useAddResearchAllowlistEntry, useResearchAllowlist, useResearchCapabilities, useUpdateResearchAllowlistEntry } from "@/lib/api/queries";
import type { ResearchAllowlistEntry } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  ALLOWLIST_DEFAULT_INTERVAL,
  ALLOWLIST_LAYER_OPTIONS,
  ALLOWLIST_LIST_KIND_LABEL,
  SOURCE_LAYER_LABEL,
  allowlistFormErrors,
  isRedditHost,
  researchErrorText,
  toAllowlistRequest,
  type AllowlistForm,
  type AllowlistFormField,
} from "@/lib/domain/research";
import { cn } from "@/lib/utils";

const EMPTY_FORM: AllowlistForm = { listKind: "WEB", host: "", layer: "INDUSTRY", purpose: "", tosNote: "", minIntervalSeconds: String(ALLOWLIST_DEFAULT_INTERVAL), tosAcknowledged: false };

const entryKey = (entry: ResearchAllowlistEntry): string => `${entry.listKind}:${entry.host}`;

function EntryRow({ entry, busy, onToggle }: { entry: ResearchAllowlistEntry; busy: boolean; onToggle: (entry: ResearchAllowlistEntry, enabled: boolean) => void }) {
  // ENV 基底沒有資料列（id 為 null）：沒有任何動作
  const actionable = entry.source === "ADMIN" && entry.id !== null;
  const layerLabel = entry.layer === null ? "—" : ((SOURCE_LAYER_LABEL as Readonly<Record<string, string | undefined>>)[entry.layer] ?? entry.layer);
  return (
    <tr
      data-testid="allowlist-row"
      data-host={entry.host}
      data-source={entry.source}
      data-enabled={entry.enabled}
      className={cn("border-t border-wg-line align-top", !entry.enabled && "text-wg-muted")}
    >
      <td className="px-3 py-2 font-mono text-xs break-all">{entry.host}</td>
      <td className="px-3 py-2">{ALLOWLIST_LIST_KIND_LABEL[entry.listKind]}</td>
      <td className="px-3 py-2">{layerLabel}</td>
      <td className="px-3 py-2 break-words">{entry.purpose === "" ? "—" : entry.purpose}</td>
      <td className="px-3 py-2 whitespace-nowrap">
        {entry.source === "ENV" ? "ENV 部署設定" : "ADMIN 管理員新增"}
        {entry.tosAcknowledged ? <span className="block text-xs text-wg-muted">已確認條款</span> : null}
      </td>
      <td className="px-3 py-2 whitespace-nowrap">{entry.minIntervalSeconds} 秒</td>
      <td className="px-3 py-2 whitespace-nowrap">{entry.enabled ? "啟用中" : "已停用"}</td>
      <td className="px-3 py-2">
        {actionable ? (
          <Button
            size="sm"
            variant="ghost"
            loading={busy}
            aria-label={`${entry.enabled ? "停用" : "啟用"} ${entry.host}`}
            title={entry.enabled ? "停用後下一個階段的有效清單就不含它" : "重新啟用這個條目"}
            onClick={() => onToggle(entry, !entry.enabled)}
          >
            {entry.enabled ? "停用" : "啟用"}
          </Button>
        ) : (
          <span className="text-xs text-wg-muted" title="部署環境變數設定的基底條目，不能在這裡停用">
            不可變更
          </span>
        )}
      </td>
    </tr>
  );
}

/**
 * 能力探針的研究環境事實（INT-08 前端側；只讀、不改任何流程）：有效的抓取主機（`fetchHosts`＝部署基底加啟用中的 ADMIN 條目，停用即消失——
 * 上面的清單含已停用的條目，這裡才是研究階段實際會連的主機）、框架樹、分流腳手架根、目標 repo 可寫與否。新增與停用成功後能力探針會一併重抓（`useAllowlistWrite`），所以這一區跟著變。
 */
function EffectiveEnvironment() {
  const capabilities = useResearchCapabilities();
  const data = capabilities.data;
  return (
    <section aria-labelledby="effective-hosts-title" data-testid="effective-environment" className="flex flex-col gap-3 rounded-md border border-wg-line bg-wg-surface px-3 py-3">
      <h3 id="effective-hosts-title" className="text-base font-semibold">
        目前有效的抓取主機
      </h3>
      {data === undefined ? (
        capabilities.isError ? (
          <p role="note" data-testid="effective-environment-error" className="text-sm text-wg-muted">
            無法取得研究環境狀態：{researchErrorText(capabilities.error)}。上面的清單仍是資料庫的內容。
          </p>
        ) : (
          <div aria-busy="true" aria-label="研究環境載入中" role="status">
            <Skeleton className="h-10 rounded-md" />
          </div>
        )
      ) : (
        <>
          <p className="text-xs text-wg-muted">研究階段實際會連線的主機：部署環境變數的基底加上啟用中的管理員條目；停用的條目不在其中。</p>
          {data.fetchHosts.length === 0 ? (
            <p data-testid="effective-hosts-empty" className="text-sm text-wg-muted">
              目前沒有任何有效的抓取主機。
            </p>
          ) : (
            <ul aria-label="有效的抓取主機" data-testid="effective-hosts" className="flex flex-wrap gap-2">
              {data.fetchHosts.map((host) => (
                <li key={host} className="rounded-sm bg-wg-base px-2 py-0.5 font-mono text-xs break-all">
                  {host}
                </li>
              ))}
            </ul>
          )}
          <dl data-testid="effective-facts" className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-wg-muted">AISDLC_SDD 框架樹</dt>
            <dd data-testid="fact-sdd-root" className="font-mono text-xs break-all">
              {data.sddRoot ?? "未解析到"}
            </dd>
            <dt className="text-wg-muted">分流腳手架根</dt>
            <dd data-testid="fact-scaffold-root" className="font-mono text-xs break-all">
              {data.scaffoldRoot ?? "未設定"}
            </dd>
            <dt className="text-wg-muted">目標 repo 可寫</dt>
            <dd data-testid="fact-repo-writable">{data.repoWritable ? "是" : "否"}</dd>
          </dl>
        </>
      )}
    </section>
  );
}

function AddForm() {
  const toast = useToast();
  const add = useAddResearchAllowlistEntry();
  const [form, setForm] = useState<AllowlistForm>(EMPTY_FORM);
  const [errors, setErrors] = useState<Partial<Record<AllowlistFormField, string>>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const reddit = isRedditHost(form.host);
  const change = (patch: Partial<AllowlistForm>) => setForm((current) => ({ ...current, ...patch }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    const found = allowlistFormErrors(form);
    setSubmitError(null);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    try {
      const created = await add.mutateAsync(toAllowlistRequest(form));
      toast.success(`已新增 ${created.host}`);
      setForm(EMPTY_FORM);
    } catch (e) {
      setSubmitError(researchErrorText(e));
    }
  }

  return (
    <form onSubmit={submit} noValidate aria-label="新增研究來源" className="flex flex-col gap-3">
      <h3 className="text-base font-semibold">新增來源網域</h3>
      {submitError ? (
        <p role="alert" data-testid="allowlist-error" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
          {submitError}
        </p>
      ) : null}
      <div className="grid gap-3 md:grid-cols-2">
        <Field label="清單類別">
          <Select value={form.listKind} onChange={(e) => change({ listKind: e.target.value as AllowlistForm["listKind"] })}>
            {(Object.keys(ALLOWLIST_LIST_KIND_LABEL) as AllowlistForm["listKind"][]).map((kind) => (
              <option key={kind} value={kind}>
                {ALLOWLIST_LIST_KIND_LABEL[kind]}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="來源層" error={errors.layer}>
          <Select value={form.layer} onChange={(e) => change({ layer: e.target.value })}>
            {ALLOWLIST_LAYER_OPTIONS.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="主機名稱" hint="（例 blog.example.com）" error={errors.host}>
          <Input value={form.host} onChange={(e) => change({ host: e.target.value })} aria-invalid={errors.host ? true : undefined} autoComplete="off" />
        </Field>
        <Field label="最小間隔（秒）" error={errors.minIntervalSeconds}>
          <Input
            type="number"
            min={1}
            max={3600}
            value={form.minIntervalSeconds}
            onChange={(e) => change({ minIntervalSeconds: e.target.value })}
            aria-invalid={errors.minIntervalSeconds ? true : undefined}
          />
        </Field>
        <Field label="用途" hint="（選填）" error={errors.purpose}>
          <Input value={form.purpose} onChange={(e) => change({ purpose: e.target.value })} aria-invalid={errors.purpose ? true : undefined} />
        </Field>
        <Field label="條款或授權備註" hint="（選填）">
          <Input value={form.tosNote} onChange={(e) => change({ tosNote: e.target.value })} />
        </Field>
      </div>
      <p className="text-xs text-wg-muted">實際抓取間隔取 Bridge 內建下限與這裡填的值中較大者；間隔建立後不能改，要調整請停用後重建。</p>
      {reddit ? (
        <div className="flex flex-col gap-1.5 rounded-md border border-wg-line bg-wg-surface px-3 py-2.5">
          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={form.tosAcknowledged} onCheckedChange={(v) => change({ tosAcknowledged: v === true })} />
            已自建 Reddit 應用並接受其條款
          </label>
          {form.tosAcknowledged ? null : (
            <p role="note" data-testid="reddit-hint" className="text-xs text-wg-warning-text">
              Reddit 預設不在任何清單：須先勾選「已自建 Reddit 應用並接受其條款」才能新增。
            </p>
          )}
        </div>
      ) : null}
      <div className="flex justify-end">
        <Button type="submit" loading={add.isPending} disabled={reddit && !form.tosAcknowledged}>
          新增
        </Button>
      </div>
    </form>
  );
}

function AllowlistBody({ onClose }: { onClose: () => void }) {
  const toast = useToast();
  const list = useResearchAllowlist(true);
  const update = useUpdateResearchAllowlistEntry();
  const [busyId, setBusyId] = useState<string | null>(null);
  const entries = list.data;

  async function toggle(entry: ResearchAllowlistEntry, enabled: boolean) {
    if (entry.id === null) return;
    setBusyId(entry.id);
    try {
      await update.mutateAsync({ id: entry.id, body: { enabled } });
      toast.success(`${enabled ? "已啟用" : "已停用"} ${entry.host}`);
    } catch (e) {
      toast.error(`${enabled ? "啟用" : "停用"}失敗：${researchErrorText(e)}`);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <DialogBody>
        <p className="text-sm text-wg-muted">
          有效清單＝部署環境變數設定的基底加上這裡啟用中的條目；每個階段開始執行時會記下當時的快照。產業網域（Web 層）要先加進來，研究才能勾選「官方文獻與業界」。
        </p>
        {entries === undefined ? (
          list.isError ? (
            <ErrorState error={list.error} title="無法載入研究來源清單" onRetry={() => void list.refetch()} />
          ) : (
            <div aria-busy="true" aria-label="研究來源清單載入中" role="status">
              <Skeleton className="h-32 rounded-lg" />
            </div>
          )
        ) : entries.length === 0 ? (
          <EmptyState title="還沒有任何來源條目" description="部署沒有設定基底清單，請在下方新增。" />
        ) : (
          <div className="overflow-x-auto rounded-md border border-wg-line">
            <table className="w-full min-w-[720px] border-collapse text-sm" data-testid="allowlist-table">
              <caption className="sr-only">研究來源清單</caption>
              <thead>
                <tr className="bg-wg-base text-left text-xs text-wg-muted">
                  {["主機", "清單", "層", "用途", "來源", "最小間隔", "狀態", "動作"].map((head) => (
                    <th key={head} scope="col" className="px-3 py-2 font-medium">
                      {head}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <EntryRow key={entryKey(entry)} entry={entry} busy={entry.id !== null && busyId === entry.id} onToggle={(e, enabled) => void toggle(e, enabled)} />
                ))}
              </tbody>
            </table>
          </div>
        )}
        <EffectiveEnvironment />
        <AddForm />
      </DialogBody>
      <DialogFooter>
        <Button variant="ghost" onClick={onClose}>
          完成
        </Button>
      </DialogFooter>
    </>
  );
}

/** 「研究來源設定」入口與對話框：只有 ADMIN 渲染（頁殼把它放進清單頁的標題列動作）。 */
export function AllowlistDialog() {
  const { role } = useAuth();
  const [open, setOpen] = useState(false);
  if (role !== "ADMIN") return null;
  return (
    <>
      <Button variant="ghost" iconLeft={Globe} onClick={() => setOpen(true)}>
        研究來源設定
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        {open ? (
          <DialogContent title="研究來源設定" description="管理研究可以抓取的來源網域：清單、新增與停用" className="w-[860px]" data-testid="allowlist-dialog">
            <AllowlistBody onClose={() => setOpen(false)} />
          </DialogContent>
        ) : null}
      </Dialog>
    </>
  );
}
