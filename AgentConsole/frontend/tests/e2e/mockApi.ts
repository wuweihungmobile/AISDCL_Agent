import type { Locator, Page } from "@playwright/test";

import { SHOTS } from "./helpers";

/**
 * route mock 共用工具（*.mock.spec.ts）：以 page.route 攔 **／api/v1/**，回契約形狀的假資料，不需要後端。
 * 與真後端 specs 的分工：這裡驗「前端對契約形狀的行為」，真後端對接與契約漂移由 QA 波與 specs 另驗。
 *
 *  - 跨來源（前端 3000 → 後端 8080）時瀏覽器要求 CORS：每個回應都帶放行標頭，OPTIONS 預檢直接回 204。
 *  - 登入：直接把 session 寫進 sessionStorage（login 端點不需要存在）。
 *  - calls 依序記下每次請求（方法、路徑、query、解析後的 body），供斷言「前端到底送了什麼」。
 */
export type MockCall = {
  method: string;
  path: string;
  query: URLSearchParams;
  /** JSON body 已解析；multipart 為 { multipart: true, raw }（raw 是原始本文，檔案內容可在其中比對） */
  body: unknown;
  contentType: string;
};

export type MockReply =
  | { status?: number; data?: unknown; delayMs?: number }
  | { status: number; error: { message?: string; reason?: string; errors?: unknown[]; details?: Record<string, unknown> }; delayMs?: number }
  | { status?: number; raw: string; headers?: Record<string, string>; delayMs?: number }
  | undefined;

export type MockHandler = (call: MockCall) => MockReply | Promise<MockReply>;

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "*",
  "access-control-allow-methods": "GET,POST,PUT,DELETE,OPTIONS",
  "access-control-expose-headers": "X-Trace-Id,Content-Disposition",
};

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** 錯誤回覆的簡寫（契約 §0.3 的 ApiError 形狀）。 */
export function fail(
  status: number,
  error: { message?: string; reason?: string; errors?: unknown[]; details?: Record<string, unknown> } = {},
): MockReply {
  return { status, error };
}

/** 分頁封包（契約 §0.2） */
export function paged<T>(content: T[], size = 10, pageNo = 0) {
  return { content, page: pageNo, size, totalElements: content.length, totalPages: Math.max(1, Math.ceil(content.length / size)) };
}

/** 依序試每個 handler，第一個有回覆的勝出。 */
export function compose(...handlers: MockHandler[]): MockHandler {
  return async (call) => {
    for (const handler of handlers) {
      const reply = await handler(call);
      if (reply) return reply;
    }
    return undefined;
  };
}

export async function installApiMock(pw: Page, handler: MockHandler): Promise<{ calls: MockCall[] }> {
  const calls: MockCall[] = [];
  await pw.route("**/api/v1/**", async (route) => {
    const req = route.request();
    if (req.method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: CORS });
      return;
    }
    const url = new URL(req.url());
    const contentType = req.headers()["content-type"] ?? "";
    let body: unknown;
    if (contentType.includes("application/json")) {
      try {
        body = req.postDataJSON();
      } catch {
        body = undefined;
      }
    } else if (contentType.includes("multipart/form-data")) {
      body = { multipart: true, raw: req.postData() ?? "" };
    }
    const call: MockCall = { method: req.method(), path: url.pathname, query: url.searchParams, body, contentType };
    calls.push(call);

    const reply = await handler(call);
    if (!reply) {
      await route.fulfill({
        status: 404,
        headers: { ...CORS, "content-type": "application/json" },
        body: JSON.stringify({ code: 404, message: `mock 沒有處理 ${call.method} ${call.path}`, errors: [], timestamp: "t", traceId: "tr-mock-404" }),
      });
      return;
    }
    if (reply.delayMs) await sleep(reply.delayMs);
    const status = reply.status ?? 200;
    if ("raw" in reply) {
      await route.fulfill({ status, headers: { ...CORS, "content-type": "application/json", ...reply.headers }, body: reply.raw });
    } else if ("error" in reply) {
      await route.fulfill({
        status,
        headers: { ...CORS, "content-type": "application/json", "X-Trace-Id": `tr-mock-${status}` },
        body: JSON.stringify({
          code: status,
          message: reply.error.message ?? "錯誤",
          reason: reply.error.reason,
          errors: reply.error.errors ?? [],
          details: reply.error.details,
          timestamp: "2026-10-15T16:30:12+08:00",
          traceId: `tr-mock-${status}`,
        }),
      });
    } else if (status === 204) {
      await route.fulfill({ status, headers: CORS });
    } else {
      await route.fulfill({
        status,
        headers: { ...CORS, "content-type": "application/json", "X-Trace-Id": "tr-mock-ok" },
        body: JSON.stringify({ code: status, message: "success", data: reply.data, timestamp: "2026-10-15T16:30:12+08:00", traceId: "tr-mock-ok" }),
      });
    }
  });
  return { calls };
}

/** 把已登入狀態寫進 sessionStorage（login 端點不需要存在）；須在 page.goto 之前呼叫。 */
export async function signInAs(
  pw: Page,
  role: "ADMIN" | "OPERATOR" | "VIEWER" = "OPERATOR",
  username = role.toLowerCase(),
): Promise<void> {
  const session = JSON.stringify({
    accessToken: "mock-access-token",
    refreshToken: "mock-refresh-token",
    expiresAt: Date.now() + 3_600_000,
    role,
    username,
  });
  await pw.addInitScript((s) => window.sessionStorage.setItem("aisdlc.console.session", s), session);
}

/**
 * 收集瀏覽器主控台的 error（React 警告、被擋的請求、未捕捉例外）：整段流程結束時應為空。
 * 這是 route mock 版特別需要的守衛——假資料形狀若與前端不合，常以 console error 而非斷言失敗的樣子出現。
 */
export function collectConsoleErrors(pw: Page): string[] {
  const errors: string[] = [];
  pw.on("console", (msg) => {
    if (msg.type() !== "error") return;
    // 情境本來就會回 4xx／5xx（422 有界閘、400 驗證…）：Chrome 會為每個非 2xx 回應印一行「Failed to load resource」，
    // 那是預期內的雜訊；CORS 被擋、React 警告、其他錯誤仍然收進來
    if (/Failed to load resource: the server responded with a status of [45]\d\d/.test(msg.text())) return;
    errors.push(msg.text());
  });
  pw.on("pageerror", (err) => errors.push(`pageerror: ${err.message}`));
  return errors;
}

/**
 * 截圖存到 tests/e2e/__screenshots__/：內容區是固定高度內捲動，長頁面用較高的視窗（tall）才拍得到全貌；
 * 拍完還原視窗，並先捲回頂端（或捲到指定區塊 focus，例如有界閘清單）。
 */
export async function snap(pw: Page, file: string, opts: { tall?: boolean; focus?: Locator } = {}): Promise<void> {
  if (opts.tall) await pw.setViewportSize({ width: 1440, height: 1700 });
  if (opts.focus) await opts.focus.scrollIntoViewIfNeeded();
  else await pw.locator('[data-region="content"]').evaluate((el) => el.scrollTo(0, 0));
  await pw.screenshot({ path: `${SHOTS}/${file}` });
  if (opts.tall) await pw.setViewportSize({ width: 1440, height: 900 });
}

/** 每頁都會打的共用端點（頂列的專案 chips 與通知摘要）。summary 由各 spec 提供，預設全 0。 */
export function shellHandler(summary: () => Record<string, unknown> = () => ({})): MockHandler {
  return (call) => {
    if (call.method !== "GET") return undefined;
    if (call.path === "/api/v1/projects") return { data: paged([], 100) };
    if (call.path === "/api/v1/notifications/summary") {
      return { data: { pendingSignoffs: 0, pendingReviews: 0, unacknowledgedAlerts: 0, bridgeConnected: null, bridgeCheckedAt: null, ...summary() } };
    }
    return undefined;
  };
}
