/**
 * 研究來源單一化的前端純函式（TCS-ResearchRegistry-20261110 D5；AC-965-8、AC-965-9；FR-R2P-24）。
 * 全是純函式與常數：不讀瀏覽器全域、不發請求；元件（`WatchSourcesSection`）只負責把結果畫出來。
 *
 * 設計要點（為什麼這樣做）：
 *  - **URL 原樣判定、不自動改寫**（D-EQA-1：Console 接受集合 ⊆ 自我進化接受集合）：`checkWatchUrl` 的判準與 Bridge `check_watch_url`
 *    逐條相同（https 起頭、≤500 字元、全 ASCII 無空白與控制字元、無 `#`、host 全小寫且無 userinfo／埠／方括號／尾點、無 `xn--` label、
 *    非 `localhost`、非 IPv4 字面）；大寫 host 與顯式 `:443` 一律拒絕並請使用者自行改寫——自動改寫會讓「使用者看到的」與「送出的」不同。
 *  - **文案單一登記處**：同步狀態與同步結果的白話文案只住 `REGISTRY_SYNC_MESSAGES`／`registrySyncText`，元件不內嵌第二份。
 *  - 同步狀態文案只描述「Console 登記快照 vs 自我進化鏡像」的事實；`pending` 與 `unknown` 時絕不出現「已同步」。
 */
import { ApiError } from "@/lib/api/client";
import type { RegistrySyncStatus, WatchSource, WatchSourceRequest } from "@/lib/api/types";
import { SOURCE_LAYER_LABEL, researchErrorText } from "@/lib/domain/research";

/** 研究登記 reason 的前端常數（三處相等：backend `ErrorReasons.REGISTRY_*`、契約 API_Contract_ResearchToPRD §5A.5、本表；AT-965-9-4 靜態比對）。 */
export const RESEARCH_REGISTRY_REASONS = {
  WATCH_SOURCE_EXISTS: "watch_source_exists",
  HOST_NOT_ALLOWED: "host_not_allowed",
  REGISTRY_TOO_LARGE: "registry_too_large",
} as const;

export const WATCH_KINDS = ["changelog", "docs", "release", "blog", "sitemap", "search"] as const;
export const WATCH_LAYERS = ["ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY"] as const;
export const EXPAND_MODES = ["links", "sitemap"] as const;

export const WATCH_KIND_LABEL: Readonly<Record<(typeof WATCH_KINDS)[number], string>> = {
  changelog: "更新日誌",
  docs: "文件",
  release: "版本發布",
  blog: "部落格",
  sitemap: "網站地圖",
  search: "搜尋查詢",
};

export const WATCH_LAYER_OPTIONS: ReadonlyArray<{ id: (typeof WATCH_LAYERS)[number]; label: string }> = WATCH_LAYERS.map((id) => ({ id, label: SOURCE_LAYER_LABEL[id] }));

export const WATCH_URL_MAX = 500;
export const WATCH_EXTRACT_MAX = 200;
export const WATCH_PREFIX_MAX = 200;
export const WATCH_EXPAND_MAX_RANGE = { min: 1, max: 3 } as const;

const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,31}$/;
const HOST_RE = /^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$/;
const IPV4_LITERAL_RE = /^[0-9.]+$/;
const PREFIX_BAD_RE = /[\s?#\u0000-\u001f\u007f]/;

// ── URL 原樣判定 ─────────────────────────────────────────────────────────────────────────────

/** 取 host（第一個 `/` 或 `?` 之前；`https://` 之後）。 */
function hostOfRaw(rest: string): string {
  const cuts = [rest.indexOf("/"), rest.indexOf("?")].filter((i) => i >= 0);
  return cuts.length === 0 ? rest : rest.slice(0, Math.min(...cuts));
}

/**
 * 原樣判定一個追蹤來源網址：`null`＝接受；否則回**給使用者看的第一則**原因。**不做任何正規化**（不轉小寫、不去 `:443`、不去尾點）。
 * 接受集合與 Bridge `check_watch_url` 逐列相同（根層附錄 D 的 CON 欄；`researchRegistry.test.ts` 逐列對拍）。
 */
export function checkWatchUrl(url: string): string | null {
  if (url.length > WATCH_URL_MAX) return `網址最多 ${WATCH_URL_MAX} 個字元`;
  if (!url.startsWith("https://")) return "網址須以 https:// 開頭";
  // 判準逐字等於 Bridge：ord<=0x20 或 >=0x7F 一律拒（只留可見 ASCII）
  if (/[^!-~]/.test(url)) return "網址只能含半形英數與符號，不可有空白、控制字元或全形、非英文字元";
  if (url.includes("#")) return "網址不可含 # 片段，請自行刪掉 # 之後的部分";
  const host = hostOfRaw(url.slice("https://".length));
  if (!HOST_RE.test(host)) {
    if (/[A-Z]/.test(host)) return "網址的主機名稱須全小寫，請自行改寫成小寫（系統不會自動改）";
    if (host.includes("@")) return "網址不可含帳號密碼（@），請自行刪除";
    if (host.includes("[") || host.includes("]")) return "網址不可使用方括號 IPv6 位址";
    if (host.includes(":")) return "網址不可帶埠號（包含 :443），請自行刪除埠號（系統不會自動改）";
    if (host.endsWith(".")) return "主機名稱結尾不可有句點，請自行刪除";
    return "主機名稱格式不正確（須為小寫英數、句點與連字號）";
  }
  if (host.split(".").some((label) => label.startsWith("xn--"))) return "不接受 xn-- 開頭的國際化網域，請改用一般網域";
  if (host === "localhost" || host.endsWith(".localhost")) return "不接受 localhost 主機";
  if (IPV4_LITERAL_RE.test(host)) return "不接受 IP 位址，請改用網域名稱";
  return null;
}

// ── 表單 ─────────────────────────────────────────────────────────────────────────────────────

export type WatchSourceForm = {
  slug: string;
  url: string;
  kind: string;
  layer: string;
  extract: string;
  /** 展開三欄：全空＝不展開；全填＝展開；其餘＝錯誤 */
  expandMode: string;
  expandPrefix: string;
  expandMax: string;
};
export type WatchSourceFormField = "slug" | "url" | "kind" | "layer" | "extract" | "expand";

export const EMPTY_WATCH_SOURCE_FORM: WatchSourceForm = { slug: "", url: "", kind: "blog", layer: "INDUSTRY", extract: "", expandMode: "", expandPrefix: "", expandMax: "" };

/** slug 若含大寫，回小寫建議（只當提示、絕不改使用者輸入）；沒有建議回 null。 */
export function slugSuggestion(slug: string): string | null {
  const lower = slug.toLowerCase();
  return lower !== slug && SLUG_RE.test(lower) ? lower : null;
}

const hasControl = (text: string): boolean => /[\u0000-\u001f\u007f]/.test(text);

/** 逐欄第一則錯誤（無錯回空物件）。 */
export function watchSourceFormErrors(form: WatchSourceForm): Partial<Record<WatchSourceFormField, string>> {
  const errors: Partial<Record<WatchSourceFormField, string>> = {};
  if (!SLUG_RE.test(form.slug)) errors.slug = "識別碼須為小寫英數與連字號，1～32 字，且以英數開頭";
  const urlError = checkWatchUrl(form.url);
  if (urlError !== null) errors.url = urlError;
  if (!(WATCH_KINDS as readonly string[]).includes(form.kind)) errors.kind = "請選擇種類";
  if (!(WATCH_LAYERS as readonly string[]).includes(form.layer)) errors.layer = "請選擇來源層";
  const extractLength = Array.from(form.extract).length;
  if (extractLength < 1 || extractLength > WATCH_EXTRACT_MAX || hasControl(form.extract)) errors.extract = `抓取說明須為 1～${WATCH_EXTRACT_MAX} 字，不可有控制字元`;
  const filled = [form.expandMode, form.expandPrefix, form.expandMax].filter((v) => v !== "").length;
  if (filled === 1 || filled === 2) {
    errors.expand = "展開設定的三個欄位（方式、路徑前綴、最多幾頁）須全空或全填";
  } else if (filled === 3) {
    if (!(EXPAND_MODES as readonly string[]).includes(form.expandMode)) errors.expand = "展開方式須為 links 或 sitemap";
    else if (!form.expandPrefix.startsWith("/") || form.expandPrefix.length > WATCH_PREFIX_MAX || PREFIX_BAD_RE.test(form.expandPrefix))
      errors.expand = `路徑前綴須以 / 開頭、最多 ${WATCH_PREFIX_MAX} 字，且不可有空白、? 或 #`;
    else if (!/^[0-9]+$/.test(form.expandMax) || Number(form.expandMax) < WATCH_EXPAND_MAX_RANGE.min || Number(form.expandMax) > WATCH_EXPAND_MAX_RANGE.max)
      errors.expand = `最多幾頁須為 ${WATCH_EXPAND_MAX_RANGE.min}～${WATCH_EXPAND_MAX_RANGE.max} 的整數`;
  }
  return errors;
}

/** 請求本文：鍵集合恰 slug、url（原樣）、kind、extract、layer、expand（無 addedBy；操作人由 backend 取 JWT subject）。 */
export function toWatchSourceRequest(form: WatchSourceForm): WatchSourceRequest {
  const expandFilled = form.expandMode !== "" && form.expandPrefix !== "" && form.expandMax !== "";
  return {
    slug: form.slug,
    url: form.url,
    kind: form.kind as WatchSourceRequest["kind"],
    extract: form.extract,
    layer: form.layer as WatchSourceRequest["layer"],
    expand: expandFilled ? { mode: form.expandMode, prefix: form.expandPrefix, max: Number(form.expandMax) } : null,
  };
}

// ── 清單 ─────────────────────────────────────────────────────────────────────────────────────

/** 區頂「啟用 N／共 M」。 */
export function watchSourceCountText(rows: readonly WatchSource[]): string {
  return `啟用 ${rows.filter((r) => r.enabled).length}／共 ${rows.length}`;
}

/** 展開設定的純文字（無展開回 "—"）。 */
export function watchExpandText(expand: WatchSource["expand"]): string {
  return expand === null ? "—" : `${expand.mode}｜${expand.prefix}｜最多 ${expand.max}`;
}

/** 超過自我進化每次抓取上限的純文字警示；上限為 null（量不到）或未超過時回 null——null 時不出現任何數字上限字樣。 */
export function fetchMaxWarning(enabledCount: number, researchFetchMax: number | null | undefined): string | null {
  if (typeof researchFetchMax !== "number" || !Number.isInteger(researchFetchMax) || researchFetchMax <= 0) return null;
  return enabledCount > researchFetchMax ? `已超過自我進化每次抓取上限（${researchFetchMax}）` : null;
}

// ── 同步狀態與結果文案（單一登記處） ───────────────────────────────────────────────────────────

const UNKNOWN_CAUSE_TEXT: Readonly<Record<string, string>> = {
  si_unavailable: "自我進化目前讀不到",
  scan_cap_exceeded: "帳本太大掃不完",
  bridge_unreachable: "引擎橋接服務連不上",
  bridge_timeout: "引擎橋接服務逾時",
};

/** 同步狀態列的純文字（與元件共用）：`pending` 與 `unknown` 時不出現「已同步」。 */
export function registrySyncText(status: Pick<RegistrySyncStatus, "state" | "unknownCause" | "ingestedSha256" | "pendingTime">): string {
  switch (status.state) {
    case "synced":
      return "已同步到自我進化";
    case "unsynced":
      return status.ingestedSha256 === null ? "有變更尚未同步（尚未同步過）" : "有變更尚未同步";
    case "pending":
      return `已送出，待自我進化入帳（主機巡邏會自動處理）${status.pendingTime ? `；送出時間 ${status.pendingTime}` : ""}`;
    case "unknown": {
      const cause = status.unknownCause === null ? undefined : UNKNOWN_CAUSE_TEXT[status.unknownCause];
      return `量不到同步狀態${cause === undefined ? "" : `：${cause}`}`;
    }
    default:
      return "量不到同步狀態";
  }
}

/** 同步結果與錯誤的文案表（單一登記處；`retry`＝是否顯示「重試」鈕）。 */
export const REGISTRY_SYNC_MESSAGES = {
  unchanged: { text: "已是最新，未重送", retry: false },
  written: { text: "已送出，待入帳", retry: false },
  forbidden: { text: "此帳號不在自我進化寫入名單，未同步", retry: false },
  disabled: { text: "自我進化的寫入功能尚未啟用（缺簽章金鑰或寫入權杖），未同步", retry: true },
  unavailable: { text: "自我進化暫時讀不到，稍後再試", retry: true },
  tooLarge: { text: "追蹤來源總量超過可同步上限，請停用部分來源後再同步", retry: false },
  bridge: { text: "連不上引擎橋接服務，未同步", retry: true },
  outcomeUnknown: { text: "送出結果不明，稽核檔可能已落地，請先看狀態再決定是否重試", retry: true },
} as const;

export type RegistrySyncMessage = { text: string; retry: boolean; tone: "ok" | "error" };

/** 同步成功回應（200 `unchanged`／201 `written`）→ 文案。 */
export function registrySyncOutcomeMessage(outcome: string): RegistrySyncMessage {
  const row = outcome === "unchanged" ? REGISTRY_SYNC_MESSAGES.unchanged : REGISTRY_SYNC_MESSAGES.written;
  return { text: row.text, retry: row.retry, tone: "ok" };
}

/** 同步失敗 → 文案與是否可重試（依 HTTP 狀態與 `reason`、`details`；沒有對映時退回通用訊息，可重試）。 */
export function registrySyncErrorMessage(error: unknown): RegistrySyncMessage {
  const pick = (row: { text: string; retry: boolean }): RegistrySyncMessage => ({ text: row.text, retry: row.retry, tone: "error" });
  if (error instanceof ApiError) {
    if (error.status === 403 && error.reason === "si_write_forbidden") return pick(REGISTRY_SYNC_MESSAGES.forbidden);
    if (error.status === 503 && error.reason === "si_write_disabled") return pick(REGISTRY_SYNC_MESSAGES.disabled);
    if (error.status === 503 && error.reason === "si_unavailable") return pick(REGISTRY_SYNC_MESSAGES.unavailable);
    if (error.status === 422 && error.reason === RESEARCH_REGISTRY_REASONS.REGISTRY_TOO_LARGE) return pick(REGISTRY_SYNC_MESSAGES.tooLarge);
    if (error.status === 502 || error.status === 504) {
      return error.details?.outcomeUnknown === true ? pick(REGISTRY_SYNC_MESSAGES.outcomeUnknown) : pick(REGISTRY_SYNC_MESSAGES.bridge);
    }
  }
  return { text: researchErrorText(error), retry: true, tone: "error" };
}

/** 新增、停用追蹤來源（POST／PATCH）失敗的白話原因。 */
export function watchSourceWriteErrorText(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.reason === RESEARCH_REGISTRY_REASONS.HOST_NOT_ALLOWED) return "這個網域還沒開放，請先在上方網域清單新增";
    if (error.reason === RESEARCH_REGISTRY_REASONS.WATCH_SOURCE_EXISTS) return "這個識別碼已經用過（停用的也算，識別碼不會重用），請換一個";
    if (error.status === 404) return "找不到這個追蹤來源，請重新整理後再試";
    if (error.status === 400 && error.errors.length > 0) return `送出的內容沒有通過檢查：${error.errors[0].message}`;
  }
  return researchErrorText(error);
}
