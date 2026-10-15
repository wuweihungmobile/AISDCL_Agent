/**
 * 系統參數頁的純邏輯（契約 §1.5、附錄 C）：草稿與基準值、前端驗證、儲存計畫、修改歷史格式。
 * 不碰 React、不碰網路。前端驗證只為「更早給回饋」（契約 §4.4 S-06：前端以 zod 鏡射同規則）；後端才是權威，
 * 它的 400 reason 與 errors[] 另由頁面對應回該列。
 */
import { REASONS } from "@/lib/api/reasons";
import type { Config, ConfigCategory, ConfigHistory } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

/** 加密參數的遮罩字串：U+2022 共八個（契約 §1.5 通則）。 */
export const MASK = "•".repeat(8);

export const TOKEN_GUARD = {
  category: "execution" as ConfigCategory,
  compact: "compactThresholdPct",
  halt: "haltThresholdPct",
} as const;

/** `category.key` */
export const configId = (c: { category: string; key: string }): string => `${c.category}.${c.key}`;

export const isTokenGuardKey = (c: { category: string; key: string }): boolean =>
  c.category === TOKEN_GUARD.category && (c.key === TOKEN_GUARD.compact || c.key === TOKEN_GUARD.halt);

/** 使用者編輯中的值（只存「改過的鍵」；沒改的鍵一律讀伺服器值，所以伺服器資料更新時畫面自動跟上）。 */
export type DraftMap = Record<string, string>;
/** ADMIN 以 reveal=true 取得的加密參數明文（頁面內暫存，不進查詢快取）。 */
export type RevealedMap = Record<string, string>;

/**
 * 伺服器端的基準值（畫面上「沒改過」的值）：
 * 加密參數有值時是遮罩字串（揭露後是明文），沒值時是空字串；其餘參數就是 value。
 */
export function baselineOf(c: Config, revealed?: string): string {
  if (c.isEncrypted) return revealed ?? (c.hasValue ? MASK : "");
  return c.value;
}

export function valueOf(c: Config, drafts: DraftMap, revealed: RevealedMap): string {
  const id = configId(c);
  return id in drafts ? drafts[id] : baselineOf(c, revealed[id]);
}

export function isDirty(c: Config, drafts: DraftMap, revealed: RevealedMap): boolean {
  const id = configId(c);
  return id in drafts && drafts[id] !== baselineOf(c, revealed[id]);
}

// ── 驗證（鏡射契約 §1.5 通則與附錄 C）──────────────────────────────────────

const INT_RE = /^(0|-?[1-9][0-9]*)$/;
const FLOAT_RE = /^-?[0-9]+(\.[0-9]+)?$/;

function rangeText(c: Config, unit: "整數" | "數字"): string {
  const { min, max } = c;
  if (min != null && max != null) return `需為${unit}（${min}～${max}）`;
  if (min != null) return `需為${unit}（最小 ${min}）`;
  if (max != null) return `需為${unit}（最大 ${max}）`;
  return `需為${unit}`;
}

/** 通過回 null，否則回給人看的原因（與後端 400 的 errors[0].message 同風格）。 */
export function validateValue(c: Config, value: string): string | null {
  switch (c.valueType) {
    case "BOOLEAN":
      return value === "true" || value === "false" ? null : "需為 true 或 false";
    case "ENUM":
      return c.options && c.options.length > 0 && !c.options.includes(value)
        ? `需為下列之一：${c.options.join("、")}`
        : null;
    case "INTEGER":
    case "LONG": {
      if (!INT_RE.test(value)) return rangeText(c, "整數");
      const n = Number(value);
      if ((c.min != null && n < c.min) || (c.max != null && n > c.max)) return rangeText(c, "整數");
      return null;
    }
    case "FLOAT": {
      if (!FLOAT_RE.test(value)) return rangeText(c, "數字");
      const n = Number(value);
      if ((c.min != null && n < c.min) || (c.max != null && n > c.max)) return rangeText(c, "數字");
      return null;
    }
    case "ENCRYPTED":
      // 遮罩字串代表「沒改」，不該被當成新值驗證；空字串＝清除
      return value.length > 512 ? "最多 512 個字元" : null;
    case "STRING":
    default: {
      if (value.includes("\u0000")) return "不可含 NUL 字元";
      if (value.length > 4000) return "最多 4,000 個字元";
      if (c.validationRule) {
        try {
          // 契約的 validationRule 是 Java 正規表示式，對「完整字串」比對；現行 50 鍵的規則與 JS 語法相容，
          // 萬一日後出現不相容語法就放行（交給後端判定），不讓前端誤擋
          if (!new RegExp(c.validationRule).test(value)) return "格式不符合規則";
        } catch {
          return null;
        }
      }
      return null;
    }
  }
}

/**
 * Token Guard 跨鍵規則（NFR-SEC-05 第 ③ 道）：halt 必須大於 compact；compact 1～99、halt 2～100、皆整數。
 * 通過回 null；順序違規回契約逐字 reason。
 */
export function validateTokenGuard(compact: string, halt: string): string | null {
  const c = compact.trim();
  const h = halt.trim();
  if (!INT_RE.test(c) || Number(c) < 1 || Number(c) > 99) return "壓縮門檻需為 1～99 的整數";
  if (!INT_RE.test(h) || Number(h) < 2 || Number(h) > 100) return "停機門檻需為 2～100 的整數";
  return Number(h) > Number(c) ? null : REASONS.SETTINGS_TOKEN_GUARD_ORDER;
}

// ── 儲存計畫 ───────────────────────────────────────────────────────────

export type Change = { config: Config; id: string; value: string };

/** 所有「改過且與基準不同」的參數，依傳入順序（分類順序＋附錄 C 順序）。 */
export function pendingChanges(configs: readonly Config[], drafts: DraftMap, revealed: RevealedMap): Change[] {
  return configs
    .filter((c) => isDirty(c, drafts, revealed))
    .map((c) => ({ config: c, id: configId(c), value: drafts[configId(c)] }));
}

export type SaveOp =
  | { kind: "single"; change: Change }
  /** 原子更新 Token Guard：帶畫面上兩個門檻的目前值（改了哪一個都一樣）；ids＝這次真的有改的鍵 */
  | { kind: "tokenGuard"; compact: string; halt: string; ids: string[] };

export type GuardValues = { compact: string; halt: string };

/**
 * 儲存計畫：只要 token_guard 的任一鍵有改，就合成**一次**原子的 PUT /settings/execution/token-guard，
 * 帶兩個門檻的目前值（PRD §7.1.8：token_guard 群組鍵改走群組端點；對端沒改就帶它畫面上的值，
 * 跨鍵校驗因此永遠看得到完整的一對）。其餘參數逐鍵 PUT，順序不變。
 * guardValues 缺席（參數尚未載入）時退回單鍵 PUT，由後端讀對端現值校驗。
 */
export function buildSavePlan(changes: readonly Change[], guardValues?: GuardValues | null): SaveOp[] {
  const isGuard = (c: Change) => isTokenGuardKey(c.config);
  const guardIds = changes.filter(isGuard).map((c) => c.id);
  const ops: SaveOp[] = [];
  let pairEmitted = false;
  for (const change of changes) {
    if (guardValues && isGuard(change)) {
      if (!pairEmitted) ops.push({ kind: "tokenGuard", compact: guardValues.compact, halt: guardValues.halt, ids: guardIds });
      pairEmitted = true;
      continue;
    }
    ops.push({ kind: "single", change });
  }
  return ops;
}

/** 儲存前需要二次確認的敏感參數（加密儲存者；契約 §1.5.3 第 5 項）。 */
export const sensitiveChanges = (changes: readonly Change[]): Change[] => changes.filter((c) => c.config.isEncrypted);

// ── 修改歷史 ───────────────────────────────────────────────────────────

/** `2026-10-15 15:30 │ model.temperature │ 0.5 → 0.3 │ @admin`（加密參數兩個值後端已是遮罩）。 */
export function formatHistoryLine(h: ConfigHistory): { time: string; param: string; change: string; by: string } {
  return {
    time: formatDateTime(h.changedAt),
    param: `${h.category}.${h.key}`,
    change: `${h.oldValue ?? "（無）"} → ${h.newValue}`,
    by: h.changedBy ? `@${h.changedBy}` : "@系統",
  };
}
