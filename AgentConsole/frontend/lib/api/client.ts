/**
 * 唯一的 fetch 包裝（Architecture §5.3）：
 *  - 自動帶 Bearer token；
 *  - 401 → 以 refresh token 換新（同時多個 401 只換一次）後重送一次；refresh token 無效 → 清登入狀態並導向 /login；
 *    後端暫時不可用（網路錯誤、5xx、429）→ 不登出，丟 ApiError 503 `upstream_unavailable`；
 *  - 解 PRD §7.2 封包：成功 {code,message,data,timestamp,traceId} 回 data；
 *    錯誤 {code,message,errors[],reason?,details?,traceId} 一律丟 ApiError；
 *  - traceId 取封包欄位，缺席時退回回應標頭 X-Trace-Id，帶進錯誤訊息方便對照後端日誌；
 *  - FormData（檔案上傳）原樣送出、不設 Content-Type；apiDownload 回 Blob（設定匯出、監控報表，不包封包）。
 * 換新（POST /auth/refresh）的失敗分三類（契約 §2.8 第 7～9 點；v1.2，C-5，QA DEF-AC-007）：
 *   renewed（2xx）／invalid（400、401、403＝refresh token 無效，唯一會登出的情形）／
 *   unavailable（網路錯誤、5xx、429 與其他未列狀態碼＝後端暫時不可用，保留 session，寧可不登出也不誤登出）。
 * 這支檔不依賴 React；頁面一律經 lib/api/endpoints.ts／queries.ts 使用，不直接呼叫 fetch。
 */
import { clearSession, loadSession, saveSession } from "@/lib/auth/store";
import { REASONS } from "./reasons";
import type { FieldError, Role, TokenResponse } from "./types";

/** 後端 origin（不含 /api/v1）。全棧經 nginx 同源時為空字串；每次呼叫時讀取，方便測試改值。 */
export function apiBase(): string {
  return (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/+$/, "");
}

export class ApiError extends Error {
  /** HTTP 狀態碼；0＝網路層失敗（連不上、被中止以外的 fetch 例外） */
  readonly status: number;
  /** 封包 code（通常等於 HTTP 狀態碼） */
  readonly code: number;
  readonly reason?: string;
  readonly errors: FieldError[];
  readonly details?: Record<string, unknown>;
  readonly traceId?: string;

  constructor(init: { status: number; message: string; code?: number; reason?: string; errors?: FieldError[]; details?: Record<string, unknown>; traceId?: string }) {
    super(init.message);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code ?? init.status;
    this.reason = init.reason;
    this.errors = init.errors ?? [];
    this.details = init.details;
    this.traceId = init.traceId;
  }

  get isNetworkError(): boolean {
    return this.status === 0;
  }
}

/** 給人看的訊息：主訊息＋原因＋traceId（若有）。 */
export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    const base = error.reason ? `${error.message}：${error.reason}` : error.message;
    return error.traceId ? `${base}（traceId：${error.traceId}）` : base;
  }
  if (error instanceof Error) return error.message;
  return "發生未知錯誤";
}

export type QueryValue = string | number | boolean | null | undefined;

export type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  query?: Record<string, QueryValue>;
  /** 一般物件以 JSON 送出；FormData（檔案上傳）原樣送出，由瀏覽器自己帶 multipart boundary（絕不手設 Content-Type） */
  body?: unknown;
  signal?: AbortSignal;
  /** false＝不帶 token、也不做 401 換新（登入／換新端點自己用） */
  auth?: boolean;
  /** Accept 標頭；預設 application/json。報表下載要 text/csv（契約 §1.3.7）。 */
  accept?: string;
};

type Unauthorized = () => void;
let unauthorizedHandler: Unauthorized | null = null;

/** AuthProvider 註冊：登入失效時用 Next router 導向，而不是整頁重載。 */
export function setUnauthorizedHandler(handler: Unauthorized | null): void {
  unauthorizedHandler = handler;
}

function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  if (window.location.pathname === "/login") return;
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  // 沒有 Next router 可用時的後備路徑（AuthProvider 未掛載）：整頁導向，順便清掉記憶體內的狀態
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.assign(`/login?next=${next}`);
}

function handleUnauthorized(): void {
  clearSession();
  (unauthorizedHandler ?? redirectToLogin)();
}

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const url = `${apiBase()}${path}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

function isFormData(value: unknown): value is FormData {
  return typeof FormData !== "undefined" && value instanceof FormData;
}

async function send(path: string, opts: RequestOptions): Promise<Response> {
  const { method = "GET", query, body, signal, auth = true, accept = "application/json" } = opts;
  const headers: Record<string, string> = { Accept: accept };
  const multipart = isFormData(body);
  // multipart 的 Content-Type 必須含瀏覽器產生的 boundary，手設就會讓後端解析不到檔案部件
  if (body !== undefined && !multipart) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = loadSession()?.accessToken;
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  try {
    return await fetch(buildUrl(path, query), {
      method,
      headers,
      body: body === undefined ? undefined : multipart ? body : JSON.stringify(body),
      signal,
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiError({
      status: 0,
      message: "無法連線到伺服器，請確認 console-api 是否在線",
    });
  }
}

type Envelope = {
  code?: number;
  message?: string;
  data?: unknown;
  errors?: FieldError[];
  reason?: string;
  details?: Record<string, unknown>;
  traceId?: string;
};

async function parse<T>(res: Response): Promise<T> {
  const headerTrace = res.headers.get("X-Trace-Id") ?? undefined;
  const isJson = (res.headers.get("content-type") ?? "").includes("json");
  let body: Envelope | undefined;
  if (res.status !== 204 && isJson) {
    try {
      body = (await res.json()) as Envelope;
    } catch {
      body = undefined;
    }
  }

  if (!res.ok) {
    throw new ApiError({
      status: res.status,
      code: body?.code,
      message: body?.message ?? (res.statusText || `HTTP ${res.status}`),
      reason: body?.reason,
      errors: body?.errors ?? [],
      details: body?.details,
      traceId: body?.traceId ?? headerTrace,
    });
  }

  if (res.status === 204 || body === undefined) return undefined as T;
  return ("data" in body ? body.data : body) as T;
}

/** 換新結果三態（契約 §2.8 第 7 點）。 */
export type RefreshOutcome = "renewed" | "invalid" | "unavailable";

/** 這三個狀態碼＝refresh token 無效、過期或被撤銷：唯一會登出的情形；其餘一律視為 unavailable。 */
const REFRESH_INVALID_STATUS: ReadonlySet<number> = new Set([400, 401, 403]);

let refreshing: Promise<RefreshOutcome> | null = null;

/** 同時間只有一個換新請求在飛；其餘 401 等同一個結果。 */
function refreshTokens(): Promise<RefreshOutcome> {
  if (!refreshing) {
    refreshing = doRefresh().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

/**
 * 換新：成功寫回新 token。沒有登入狀態＝invalid（沒有可換的 refresh token）。
 * 網路錯誤（fetch 丟例外）、5xx（含 nginx 在 backend 重啟時立即回的 502／503／504）、429、其餘未列狀態碼，
 * 以及 2xx 卻不是 token 封包（例如代理回的 HTML 頁）都是 unavailable：保留 session，由呼叫端退避重試。
 */
async function doRefresh(): Promise<RefreshOutcome> {
  const current = loadSession();
  if (!current) return "invalid";
  let res: Response;
  try {
    res = await send("/api/v1/auth/refresh", {
      method: "POST",
      body: { refreshToken: current.refreshToken },
      auth: false,
    });
  } catch {
    return "unavailable";
  }
  if (!res.ok) return REFRESH_INVALID_STATUS.has(res.status) ? "invalid" : "unavailable";
  let tokens: TokenResponse | undefined;
  try {
    tokens = await parse<TokenResponse>(res);
  } catch {
    return "unavailable";
  }
  if (typeof tokens?.accessToken !== "string" || typeof tokens.refreshToken !== "string") return "unavailable";
  saveSession({
    ...current,
    accessToken: tokens.accessToken,
    refreshToken: tokens.refreshToken,
    expiresAt: Date.now() + tokens.expiresIn * 1000,
    role: (tokens.role as Role) ?? current.role,
  });
  return "renewed";
}

/** REST 路徑的「暫時無法連線」：不登出；呼叫端顯示 message、保留畫面狀態（契約 §2.8 第 9 點）。 */
function upstreamUnavailable(traceId?: string | null): ApiError {
  return new ApiError({
    status: 503,
    message: "伺服器暫時無法連線，請稍後再試",
    reason: REASONS.UPSTREAM_UNAVAILABLE,
    traceId: traceId ?? undefined,
  });
}

/** 送出請求並處理 401 換新（apiRequest 與 apiDownload 共用）。 */
async function sendWithRenewal(path: string, opts: RequestOptions): Promise<Response> {
  const auth = opts.auth ?? true;
  let res = await send(path, opts);
  if (res.status === 401 && auth) {
    const outcome = await refreshTokens();
    // 後端暫時不可用：換新失敗不等於登入失效——保留 session、不導向登入，丟 503 upstream_unavailable 讓畫面保留現況
    if (outcome === "unavailable") throw upstreamUnavailable(res.headers.get("X-Trace-Id"));
    if (outcome === "renewed") res = await send(path, opts);
    if (outcome === "invalid" || res.status === 401) {
      handleUnauthorized();
      throw new ApiError({
        status: 401,
        message: "登入已逾期，請重新登入",
        traceId: res.headers.get("X-Trace-Id") ?? undefined,
      });
    }
  }
  return res;
}

export async function apiRequest<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  return parse<T>(await sendWithRenewal(path, opts));
}

export type ApiResponse<T> = {
  data: T;
  /** 回應標頭（跨來源時瀏覽器只給「已暴露」的標頭；契約 §0.4 第 3 點：X-Follow-Up-Run-Id、Retry-After、Content-Disposition） */
  headers: Headers;
};

/** 與 apiRequest 相同，但連同回應標頭一併回傳：審核（204）要讀 X-Follow-Up-Run-Id（契約 §1.2.11）。 */
export async function apiRequestWithHeaders<T = unknown>(path: string, opts: RequestOptions = {}): Promise<ApiResponse<T>> {
  const res = await sendWithRenewal(path, opts);
  const data = await parse<T>(res);
  return { data, headers: res.headers };
}

/**
 * 換新 token，回三態。只有 invalid（refresh token 無效＝登入已失效）才清 session、導向登入（與 401 重送失敗同一條路）；
 * unavailable（後端暫時不可用）保留 session，由呼叫端決定怎麼退避。
 * SSE 用得到：EventSource 不能帶標頭、也看不到 HTTP 狀態碼，token 要放進網址，過期時只看得到「連線被關」。
 */
export async function renewSession(): Promise<RefreshOutcome> {
  const outcome = await refreshTokens();
  if (outcome === "invalid") handleUnauthorized();
  return outcome;
}

/** access token 到期前多久就先換新（SSE 連線建立後不會再驗 token，但重連會；別拿快到期的 token 去連）。 */
export const TOKEN_RENEW_MARGIN_MS = 30_000;

/**
 * 取得可用於網址的 access token：快到期或 force 時先換新。
 *  - renewed：回新 token；
 *  - invalid：已登出（renewSession 清了 session），回 null；
 *  - unavailable（後端暫時不可用，契約 §2.8 第 8 點）：現有 token 尚未過期就沿用（SSE 連線建立後不再驗 token）；
 *    已過期回 null——但**不登出**，串流層以退避重試、狀態維持「重新連線中」。
 * 沒有登入狀態回 null。
 */
export async function getFreshAccessToken(opts: { force?: boolean } = {}): Promise<string | null> {
  const session = loadSession();
  if (!session) return null;
  const expiring = session.expiresAt > 0 && session.expiresAt - Date.now() < TOKEN_RENEW_MARGIN_MS;
  if (opts.force || expiring) {
    const outcome = await renewSession();
    if (outcome === "invalid") return null;
    if (outcome === "unavailable") {
      const current = loadSession();
      // expiresAt 為 0＝到期時間未知（舊版 session），視為未過期；已知且已到期才放棄
      return current && !(current.expiresAt > 0 && current.expiresAt <= Date.now()) ? current.accessToken : null;
    }
  }
  return loadSession()?.accessToken ?? null;
}

export type DownloadResult = {
  blob: Blob;
  /** 取自 Content-Disposition；跨來源時瀏覽器要求後端 CORS 暴露該標頭，缺席為 null，由呼叫端給預設檔名 */
  filename: string | null;
};

/** 從 Content-Disposition 取檔名（支援 filename*=UTF-8''… 與 filename="…"）；取不到回 null。 */
export function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null;
  const star = /filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)/.exec(header);
  if (star) {
    try {
      return decodeURIComponent(star[1].trim());
    } catch {
      // 編碼損毀：退回一般 filename
    }
  }
  const plain = /filename\s*=\s*"?([^";]+)"?/.exec(header);
  return plain ? plain[1].trim() : null;
}

/**
 * 檔案下載（設定匯出、監控報表）：同樣帶 Bearer、同樣處理 401 換新；
 * 成功回 Blob＋檔名；失敗（401／403／429…）照常解 ApiError 封包丟出。
 */
export async function apiDownload(path: string, opts: RequestOptions = {}): Promise<DownloadResult> {
  const res = await sendWithRenewal(path, opts);
  if (!res.ok) await parse<never>(res); // 非 2xx：parse 會丟 ApiError
  return { blob: await res.blob(), filename: filenameFromDisposition(res.headers.get("Content-Disposition")) };
}

/** 觸發瀏覽器下載（錨點 download）；檔名只留安全字元。 */
export function saveBlob(blob: Blob, filename: string): void {
  const safe = filename.replace(/[\\/:*?"<>|\u0000-\u001f]/g, "_").trim() || "download";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = safe;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
