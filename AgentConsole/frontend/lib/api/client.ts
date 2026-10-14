/**
 * 唯一的 fetch 包裝（Architecture §5.3）：
 *  - 自動帶 Bearer token；
 *  - 401 → 以 refresh token 換新（同時多個 401 只換一次）後重送一次；換不到 → 清登入狀態並導向 /login；
 *  - 解 PRD §7.2 封包：成功 {code,message,data,timestamp,traceId} 回 data；
 *    錯誤 {code,message,errors[],reason?,details?,traceId} 一律丟 ApiError；
 *  - traceId 取封包欄位，缺席時退回回應標頭 X-Trace-Id，帶進錯誤訊息方便對照後端日誌。
 * 這支檔不依賴 React；頁面一律經 lib/api/endpoints.ts／queries.ts 使用，不直接呼叫 fetch。
 */
import { clearSession, loadSession, saveSession } from "@/lib/auth/store";
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

  constructor(init: {
    status: number;
    message: string;
    code?: number;
    reason?: string;
    errors?: FieldError[];
    details?: Record<string, unknown>;
    traceId?: string;
  }) {
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
  body?: unknown;
  signal?: AbortSignal;
  /** false＝不帶 token、也不做 401 換新（登入／換新端點自己用） */
  auth?: boolean;
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

async function send(path: string, opts: RequestOptions): Promise<Response> {
  const { method = "GET", query, body, signal, auth = true } = opts;
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = loadSession()?.accessToken;
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  try {
    return await fetch(buildUrl(path, query), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
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

let refreshing: Promise<boolean> | null = null;

/** 同時間只有一個換新請求在飛；其餘 401 等同一個結果。 */
function refreshTokens(): Promise<boolean> {
  if (!refreshing) {
    refreshing = doRefresh().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

async function doRefresh(): Promise<boolean> {
  const current = loadSession();
  if (!current) return false;
  try {
    const res = await send("/api/v1/auth/refresh", {
      method: "POST",
      body: { refreshToken: current.refreshToken },
      auth: false,
    });
    const tokens = await parse<TokenResponse>(res);
    saveSession({
      ...current,
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
      expiresAt: Date.now() + tokens.expiresIn * 1000,
      role: (tokens.role as Role) ?? current.role,
    });
    return true;
  } catch {
    return false;
  }
}

export async function apiRequest<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  const auth = opts.auth ?? true;
  let res = await send(path, opts);
  if (res.status === 401 && auth) {
    const renewed = await refreshTokens();
    if (renewed) res = await send(path, opts);
    if (!renewed || res.status === 401) {
      handleUnauthorized();
      throw new ApiError({
        status: 401,
        message: "登入已逾期，請重新登入",
        traceId: res.headers.get("X-Trace-Id") ?? undefined,
      });
    }
  }
  return parse<T>(res);
}
