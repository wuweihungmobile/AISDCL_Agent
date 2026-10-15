/**
 * 元件測試共用：假後端（fetch 替身）與 Provider 外殼。
 * 契約形狀（封包、錯誤）一律在這裡組，各測試只描述「哪個端點回什麼」。
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { vi } from "vitest";

import { ToastHost, ToastProvider } from "@/components/ui/toast";
import { AuthProvider } from "@/lib/auth/AuthProvider";
import { clearSession, resetSessionCache, saveSession } from "@/lib/auth/store";
import type { Role } from "@/lib/api/types";

export type ApiCall = {
  method: string;
  /** 含 query string 的路徑（不含 origin） */
  url: string;
  path: string;
  query: URLSearchParams;
  /** JSON body 已解析；FormData 為 FormData；沒有 body 為 undefined */
  body: unknown;
};

/** Response＝原樣回（要自訂標頭或非封包內容時用）；物件＝成功封包；undefined＝沒人處理（404） */
export type Reply = Response | { status?: number; data?: unknown } | undefined;

/** 成功封包（契約 §0.2） */
export function envelope(data: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify({ code: status, message: "success", data, timestamp: "t", traceId: "tr-ok" }), {
    status,
    headers: { "content-type": "application/json" },
  });
}

/** 錯誤封包（契約 §0.3；errors 項目可帶 gate／detail／location） */
export function failure(
  status: number,
  body: { message?: string; reason?: string; errors?: unknown[]; details?: Record<string, unknown> } = {},
): Response {
  return new Response(
    JSON.stringify({
      code: status,
      message: body.message ?? "錯誤",
      reason: body.reason,
      errors: body.errors ?? [],
      details: body.details,
      timestamp: "t",
      traceId: `tr-${status}`,
    }),
    { status, headers: { "content-type": "application/json" } },
  );
}

/**
 * 以 handler 取代全域 fetch。handler 回 undefined＝這個端點沒人處理（回 404，測試會看到清楚的訊息）。
 * 回傳的 calls 依序記下每次請求，供斷言「送了什麼」。
 */
export function stubApi(handler: (call: ApiCall) => Reply): { calls: ApiCall[] } {
  const calls: ApiCall[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init: RequestInit = {}) => {
      const url = new URL(input, "http://api.test");
      const raw = init.body;
      const body = raw === undefined || raw === null ? undefined : typeof raw === "string" ? JSON.parse(raw) : raw;
      const call: ApiCall = {
        method: init.method ?? "GET",
        url: url.pathname + url.search,
        path: url.pathname,
        query: url.searchParams,
        body,
      };
      calls.push(call);
      const reply = handler(call);
      if (reply instanceof Response) return reply;
      if (reply === undefined) return failure(404, { message: `測試沒有處理 ${call.method} ${call.url}` });
      return envelope(reply.data, reply.status ?? 200);
    }),
  );
  return { calls };
}

/** 寫入已登入狀態（sessionStorage）。 */
export function signIn(role: Role = "ADMIN", username = "admin"): void {
  resetSessionCache();
  clearSession();
  saveSession({ accessToken: "a", refreshToken: "r", expiresAt: Date.now() + 1e6, role, username });
}

export function makeClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 }, mutations: { retry: false } } });
}

/** TanStack Query ＋ 登入狀態 ＋ Toast（含宿主，toast 訊息可用 getByText 斷言）。 */
export function Providers({ children, client }: { children: ReactNode; client: QueryClient }) {
  return (
    <QueryClientProvider client={client}>
      <AuthProvider>
        <ToastProvider>
          {children}
          <ToastHost />
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
