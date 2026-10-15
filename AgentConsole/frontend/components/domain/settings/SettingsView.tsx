"use client";

/**
 * 系統參數設定（設計稿畫面 9；PRD §5.5；契約 §1.5、§4.4）：
 * 六個分類 tab → 參數卡（依 valueType 渲染控制項、逐列重置、影響範圍提示、驗證紅字）→ 修改歷史卡 → 儲存變更／全部重置。
 *
 * 設計要點（為什麼這樣做）：
 *  - 草稿只記「使用者改過的鍵」，沒改的鍵一律讀伺服器值：儲存、重置、匯入之後畫面自動跟上，沒有「同步草稿」的 effect。
 *  - 「儲存變更」逐鍵 PUT；全部成功才 toast，任一失敗就停在該鍵、顯示後端原因，其餘草稿保留（不靜默吞掉）。
 *    兩個 token_guard 鍵都改時合成一次原子的 PUT /execution/token-guard（halt 必須大於 compact，前後端各校驗一次）。
 *  - 加密參數（API Key、DB DSN）：儲存與重置都先二次確認並送 confirm=true；「顯示」＝ADMIN 以 reveal=true 取明文，
 *    其他角色按鈕停用。非 ADMIN 整頁唯讀（契約 §4.6 G-S2：後端寫入端點一律 ADMIN，403 只是最後防線）。
 */
import { useQueryClient } from "@tanstack/react-query";
import { Check, Download, RotateCcw, Settings, Upload } from "lucide-react";
import { useMemo, useState } from "react";

import { ConfirmDialog } from "@/components/domain/ConfirmDialog";
import { PageTitle } from "@/components/domain/PageHeader";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { pillPanelId, pillTabId, PillTabs } from "@/components/ui/pill-tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { saveBlob } from "@/lib/api/client";
import { listSettingsByCategory } from "@/lib/api/endpoints";
import {
  invalidateSettings,
  useExportSettings,
  useResetSetting,
  useSettings,
  useUpdateSetting,
  useUpdateTokenGuard,
} from "@/lib/api/queries";
import { CONFIG_CATEGORIES, type Config, type ConfigCategory, type TestConnectionRequest } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ConnectionTest } from "./ConnectionTest";
import { HistoryCard } from "./HistoryCard";
import { ImportSettingsDialog } from "./ImportSettingsDialog";
import { CATEGORY_META, settingLabel } from "./labels";
import { ResetAllDialog } from "./ResetAllDialog";
import { SettingRow } from "./SettingRow";
import { describeSettingsError } from "./settingsErrors";
import {
  MASK,
  TOKEN_GUARD,
  buildSavePlan,
  configId,
  isDirty,
  isTokenGuardKey,
  pendingChanges,
  sensitiveChanges,
  validateTokenGuard,
  validateValue,
  valueOf,
  type Change,
  type DraftMap,
  type RevealedMap,
} from "./settingsModel";
import { TokenGuardCard } from "./TokenGuardCard";

const TABS = CONFIG_CATEGORIES.map((c) => ({ id: c, label: CATEGORY_META[c].label, icon: CATEGORY_META[c].icon }));
const ID_BASE = "settings-category";
const GUARD_ERROR_KEY = "tokenGuard";

function without<T>(record: Record<string, T>, ...keys: string[]): Record<string, T> {
  const next = { ...record };
  for (const k of keys) delete next[k];
  return next;
}

function yyyymmdd(d = new Date()): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}`;
}

export function SettingsView() {
  const qc = useQueryClient();
  const toast = useToast();
  const { role } = useAuth();
  const isAdmin = role === "ADMIN";
  const settings = useSettings();
  const updateSetting = useUpdateSetting();
  const updateGuard = useUpdateTokenGuard();
  const resetOne = useResetSetting();
  const exporter = useExportSettings();

  const [category, setCategory] = useState<ConfigCategory>("model");
  const [drafts, setDrafts] = useState<DraftMap>({});
  const [revealed, setRevealed] = useState<RevealedMap>({});
  const [visible, setVisible] = useState<ReadonlySet<string>>(() => new Set());
  const [revealing, setRevealing] = useState<string | null>(null);
  /** 後端回的錯誤（鍵＝configId 或 tokenGuard）；使用者改那一列就清掉 */
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [confirmSave, setConfirmSave] = useState<Change[] | null>(null);
  const [confirmReset, setConfirmReset] = useState<Config | null>(null);
  const [resetAllOpen, setResetAllOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  const all = useMemo(
    () => (settings.data ? CONFIG_CATEGORIES.flatMap((c) => settings.data[c] ?? []) : []),
    [settings.data],
  );
  const byId = useMemo(() => new Map(all.map((c) => [configId(c), c])), [all]);
  const busy = saving || updateGuard.isPending || resetOne.isPending;

  // ── 驗證（本地）──────────────────────────────────────────────────────
  const changes = pendingChanges(all, drafts, revealed);
  const localErrors: Record<string, string> = {};
  for (const ch of changes) {
    if (ch.config.isEncrypted && ch.value === MASK) continue;
    const message = validateValue(ch.config, ch.value);
    if (message) localErrors[ch.id] = message;
  }
  const compactCfg = byId.get(`${TOKEN_GUARD.category}.${TOKEN_GUARD.compact}`);
  const haltCfg = byId.get(`${TOKEN_GUARD.category}.${TOKEN_GUARD.halt}`);
  const compactId = compactCfg ? configId(compactCfg) : "";
  const haltId = haltCfg ? configId(haltCfg) : "";
  const guardDirty = Boolean(
    (compactCfg && isDirty(compactCfg, drafts, revealed)) || (haltCfg && isDirty(haltCfg, drafts, revealed)),
  );
  const guardValues =
    compactCfg && haltCfg
      ? { compact: valueOf(compactCfg, drafts, revealed), halt: valueOf(haltCfg, drafts, revealed) }
      : null;
  // 每個鍵自己的範圍錯誤優先顯示在該列；兩鍵各自合法才檢查「halt 必須大於 compact」
  const guardOrderError =
    guardDirty && guardValues && !localErrors[compactId] && !localErrors[haltId]
      ? validateTokenGuard(guardValues.compact, guardValues.halt)
      : null;
  const guardBlocked = Boolean(localErrors[compactId] || localErrors[haltId] || guardOrderError);
  const blockingCount = Object.keys(localErrors).length + (guardOrderError ? 1 : 0);

  // ── 編輯 ─────────────────────────────────────────────────────────────
  function setDraft(c: Config, value: string) {
    const id = configId(c);
    setDrafts((d) => ({ ...d, [id]: value }));
    setErrors((e) => without(e, id, ...(isTokenGuardKey(c) ? [GUARD_ERROR_KEY] : [])));
  }

  function clearKeys(ids: string[]) {
    setDrafts((d) => without(d, ...ids));
    setRevealed((r) => without(r, ...ids));
    setVisible((v) => {
      const next = new Set(v);
      ids.forEach((id) => next.delete(id));
      return next;
    });
  }

  /** 顯示／隱藏加密參數：顯示需 ADMIN 以 reveal=true 取明文（每次寫審計，只在使用者按下時才取）。 */
  async function toggleVisible(c: Config) {
    const id = configId(c);
    if (visible.has(id)) {
      setVisible((v) => {
        const next = new Set(v);
        next.delete(id);
        return next;
      });
      return;
    }
    if (!isAdmin) return;
    if (!(id in revealed) && !(id in drafts) && c.hasValue) {
      setRevealing(id);
      try {
        const list = await listSettingsByCategory(c.category, { reveal: true });
        const plain = list.find((x) => configId(x) === id);
        if (plain) setRevealed((r) => ({ ...r, [id]: plain.value }));
      } catch (e) {
        toast.error(`無法顯示：${describeSettingsError(e)}`);
        setRevealing(null);
        return;
      }
      setRevealing(null);
    }
    setVisible((v) => new Set(v).add(id));
  }

  // ── 重置 ─────────────────────────────────────────────────────────────
  async function doReset(c: Config, confirm: boolean) {
    const id = configId(c);
    try {
      await resetOne.mutateAsync({ category: c.category, key: c.key, confirm });
      clearKeys([id]);
      setErrors((e) => without(e, id, ...(isTokenGuardKey(c) ? [GUARD_ERROR_KEY] : [])));
      toast.success(`已重置為預設值：${settingLabel(c.category, c.key)}`);
    } catch (e) {
      const text = describeSettingsError(e);
      setErrors((prev) => ({ ...prev, [isTokenGuardKey(c) ? GUARD_ERROR_KEY : id]: text }));
      toast.error(`重置失敗：${settingLabel(c.category, c.key)}`);
    } finally {
      await invalidateSettings(qc);
    }
  }

  function requestReset(c: Config) {
    if (c.isEncrypted) setConfirmReset(c);
    else void doReset(c, false);
  }

  // ── 儲存 ─────────────────────────────────────────────────────────────
  function startSave() {
    if (changes.length === 0) return;
    if (blockingCount > 0) {
      toast.error(`有 ${blockingCount} 項參數不合法，請先修正紅字欄位`);
      return;
    }
    if (sensitiveChanges(changes).length > 0) setConfirmSave(changes);
    else void runSave(changes);
  }

  /** 逐鍵儲存；全部成功才 toast，任一失敗停在該鍵並顯示原因（其餘草稿保留，使用者修正後可再按儲存）。 */
  async function runSave(toSave: Change[]) {
    setConfirmSave(null);
    setSaving(true);
    setErrors({});
    let saved = 0;
    try {
      for (const op of buildSavePlan(toSave, guardValues)) {
        try {
          if (op.kind === "tokenGuard") {
            await updateGuard.mutateAsync({
              compactThresholdPct: Number(op.compact),
              haltThresholdPct: Number(op.halt),
            });
            clearKeys(op.ids);
            saved += op.ids.length;
          } else {
            const { change } = op;
            await updateSetting.mutateAsync({
              category: change.config.category,
              key: change.config.key,
              // 加密參數走到這裡一定已經過二次確認對話框
              body: { value: change.value, confirm: change.config.isEncrypted ? true : undefined },
            });
            clearKeys([change.id]);
            saved += 1;
          }
        } catch (e) {
          const failedKey = op.kind === "tokenGuard" ? GUARD_ERROR_KEY : op.change.id;
          setErrors({ [failedKey]: describeSettingsError(e) });
          setCategory(op.kind === "tokenGuard" ? TOKEN_GUARD.category : op.change.config.category);
          const failedLabel =
            op.kind === "tokenGuard" ? "Token Guard" : settingLabel(op.change.config.category, op.change.config.key);
          toast.error(`儲存失敗：${failedLabel}（已儲存 ${saved} 項，其餘未送出）`);
          return;
        }
      }
      toast.success(`已儲存 ${saved} 項參數`);
    } finally {
      setSaving(false);
      await invalidateSettings(qc);
    }
  }

  async function applyTokenGuard() {
    if (!guardValues || guardBlocked) return;
    setErrors((e) => without(e, GUARD_ERROR_KEY));
    try {
      await updateGuard.mutateAsync({
        compactThresholdPct: Number(guardValues.compact),
        haltThresholdPct: Number(guardValues.halt),
      });
      clearKeys([compactId, haltId]);
      toast.success("已套用 Token Guard");
    } catch (e) {
      setErrors((prev) => ({ ...prev, [GUARD_ERROR_KEY]: describeSettingsError(e) }));
    } finally {
      await invalidateSettings(qc);
    }
  }

  // ── 匯出 ─────────────────────────────────────────────────────────────
  async function doExport() {
    try {
      const { blob, filename } = await exporter.mutateAsync();
      saveBlob(blob, filename ?? `aisdlc-settings-${yyyymmdd()}.json`);
      toast.success("已匯出設定（加密參數以 <encrypted> 佔位，不含明文）");
    } catch (e) {
      toast.error(`匯出失敗：${describeSettingsError(e)}`);
    }
  }

  /** 測試連線只帶「改過、尚未儲存」的欄位；其餘取後端已儲存值。 */
  function buildTestRequest(): TestConnectionRequest | undefined {
    const req: TestConnectionRequest = {};
    const url = byId.get("model.apiUrl");
    const key = byId.get("model.apiKey");
    const name = byId.get("model.name");
    if (url && isDirty(url, drafts, revealed)) req.apiUrl = drafts[configId(url)];
    if (key && isDirty(key, drafts, revealed)) {
      const typed = drafts[configId(key)];
      if (typed && typed !== MASK) req.apiKey = typed;
    }
    if (name && isDirty(name, drafts, revealed)) req.model = drafts[configId(name)];
    return Object.keys(req).length > 0 ? req : undefined;
  }

  // ── 渲染 ─────────────────────────────────────────────────────────────
  function renderRow(c: Config) {
    const id = configId(c);
    const dirty = isDirty(c, drafts, revealed);
    const atDefault = c.isEncrypted ? !c.hasValue : c.value === (c.defaultValue ?? "");
    return (
      <SettingRow
        key={c.id}
        config={c}
        value={valueOf(c, drafts, revealed)}
        dirty={dirty}
        error={errors[id] ?? localErrors[id] ?? null}
        disabled={!isAdmin || busy}
        onChange={(v) => setDraft(c, v)}
        canReset={isAdmin && !busy && (!atDefault || dirty)}
        resetHint={!isAdmin ? "僅 ADMIN 可重置參數" : "已是預設值"}
        onReset={() => requestReset(c)}
        visible={visible.has(id)}
        onToggleVisible={() => void toggleVisible(c)}
        canReveal={isAdmin}
        revealing={revealing === id}
      />
    );
  }

  const rows = settings.data?.[category] ?? [];
  const guardRows = category === TOKEN_GUARD.category ? rows.filter(isTokenGuardKey) : [];
  const normalRows = rows.filter((c) => !(category === TOKEN_GUARD.category && isTokenGuardKey(c)));
  const CategoryIcon = CATEGORY_META[category].icon;
  const adminHint = isAdmin ? undefined : "權限不足（僅 ADMIN 可修改系統參數）";

  return (
    <div>
      <PageTitle
        title="系統參數設定"
        icon={Settings}
        actions={
          <>
            <Button
              variant="ghost"
              iconLeft={Download}
              loading={exporter.isPending}
              disabled={!isAdmin}
              title={adminHint}
              onClick={() => void doExport()}
            >
              匯出設定
            </Button>
            <Button variant="ghost" iconLeft={Upload} disabled={!isAdmin} title={adminHint} onClick={() => setImportOpen(true)}>
              匯入設定
            </Button>
          </>
        }
      />

      {!isAdmin && role ? (
        <p
          role="status"
          data-testid="readonly-banner"
          className="mb-4 rounded-md border border-wg-line bg-wg-surface px-4 py-3 text-sm text-wg-muted"
        >
          目前角色（{role}）只能檢視系統參數；修改、重置、測試連線、匯出與匯入都需要 ADMIN。
        </p>
      ) : null}

      {settings.isError ? (
        <ErrorState error={settings.error} onRetry={() => settings.refetch()} title="無法載入系統參數" />
      ) : !settings.data ? (
        <div aria-busy="true" aria-label="系統參數載入中" className="flex flex-col gap-4">
          <Skeleton className="h-10 w-3/4" />
          <Skeleton className="h-[420px] rounded-lg" />
        </div>
      ) : (
        <>
          <PillTabs label="參數分類" idBase={ID_BASE} tabs={TABS} value={category} onChange={setCategory} className="mb-4" />

          <Card
            role="tabpanel"
            id={pillPanelId(ID_BASE, category)}
            aria-labelledby={pillTabId(ID_BASE, category)}
            className="px-6 py-5"
            data-testid="settings-panel"
          >
            <h3 className="mb-1 flex items-center gap-2 text-lg font-semibold">
              <CategoryIcon size={20} className="text-wg-primary" aria-hidden />
              {CATEGORY_META[category].label}設定
            </h3>

            {guardRows.length > 0 ? (
              <TokenGuardCard
                error={errors[GUARD_ERROR_KEY] ?? guardOrderError}
                blocked={guardBlocked}
                dirty={guardDirty}
                disabled={!isAdmin || busy}
                applying={updateGuard.isPending}
                onApply={() => void applyTokenGuard()}
              >
                {guardRows.map(renderRow)}
              </TokenGuardCard>
            ) : null}

            {normalRows.map(renderRow)}

            {category === "model" ? <ConnectionTest disabled={!isAdmin} buildRequest={buildTestRequest} /> : null}
          </Card>

          <HistoryCard key={category} category={category} />

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Button
              iconLeft={Check}
              loading={saving}
              disabled={!isAdmin || changes.length === 0 || busy}
              title={adminHint}
              onClick={startSave}
            >
              儲存變更
            </Button>
            <Button
              variant="ghost"
              iconLeft={RotateCcw}
              disabled={!isAdmin || busy}
              title={adminHint}
              onClick={() => setResetAllOpen(true)}
            >
              全部重置為預設值
            </Button>
            {changes.length > 0 ? (
              <span data-testid="unsaved-count" className="text-sm text-wg-muted">
                {changes.length} 項變更尚未儲存
              </span>
            ) : null}
          </div>
        </>
      )}

      <ConfirmDialog
        open={confirmSave !== null}
        title="確認更新敏感參數"
        confirmLabel="確認儲存"
        onClose={() => setConfirmSave(null)}
        onConfirm={async () => {
          if (confirmSave) await runSave(confirmSave);
        }}
      >
        <p>
          即將更新敏感參數：
          <b>{sensitiveChanges(confirmSave ?? []).map((c) => settingLabel(c.config.category, c.config.key)).join("、")}</b>
          。這會留下審計紀錄，儲存時以 confirm=true 送出（修改歷史只記遮罩、不記明文）。
        </p>
        {(confirmSave ?? []).some((c) => c.config.impactNote) ? (
          <ul className="mt-3 flex flex-col gap-1.5 text-sm text-wg-muted" data-testid="confirm-impact-notes">
            {(confirmSave ?? [])
              .filter((c) => c.config.impactNote)
              .map((c) => (
                <li key={c.id}>
                  <b className="text-wg-text">{settingLabel(c.config.category, c.config.key)}</b>：{c.config.impactNote}
                </li>
              ))}
          </ul>
        ) : null}
      </ConfirmDialog>

      <ConfirmDialog
        open={confirmReset !== null}
        title="確認重置敏感參數"
        confirmLabel="確認重置"
        onClose={() => setConfirmReset(null)}
        onConfirm={async () => {
          const target = confirmReset;
          setConfirmReset(null);
          if (target) await doReset(target, true);
        }}
      >
        <p>
          將把敏感參數「<b>{confirmReset ? settingLabel(confirmReset.category, confirmReset.key) : ""}</b>」重置為預設值（清空）。
          這會留下審計紀錄，以 confirm=true 送出。
        </p>
      </ConfirmDialog>

      <ResetAllDialog
        open={resetAllOpen}
        onClose={() => setResetAllOpen(false)}
        onFinished={(completed) => {
          setDrafts({});
          setRevealed({});
          setVisible(new Set());
          setErrors({});
          void invalidateSettings(qc);
          if (completed) {
            setResetAllOpen(false);
            toast.success("已把全部分類重置為預設值");
          }
        }}
      />

      <ImportSettingsDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onApplied={(result) => {
          setDrafts({});
          setRevealed({});
          setVisible(new Set());
          setErrors({});
          toast.success(
            `已匯入設定：套用 ${result.applied} 項、略過 ${result.skipped} 項${result.errors.length > 0 ? `、失敗 ${result.errors.length} 項` : ""}`,
          );
        }}
      />
    </div>
  );
}
