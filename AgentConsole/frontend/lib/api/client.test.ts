import { beforeEach, describe, expect, it, vi } from "vitest";

import { clearSession, loadSession, resetSessionCache, saveSession, type Session } from "@/lib/auth/store";
import {
  ApiError,
  apiDownload,
  apiRequest,
  apiRequestWithHeaders,
  describeError,
  filenameFromDisposition,
  getFreshAccessToken,
  renewSession,
  setUnauthorizedHandler,
  TOKEN_RENEW_MARGIN_MS,
} from "./client";

const SESSION: Session = {
  accessToken: "access-old",
  refreshToken: "refresh-old",
  expiresAt: Date.now() + 60_000,
  role: "OPERATOR",
  username: "operator",
};

function json(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...headers },
  });
}
const ok = (data: unknown) => json({ code: 200, message: "success", data, timestamp: "t", traceId: "tr-ok" });

type FetchMock = ReturnType<typeof vi.fn<(input: string, init?: RequestInit) => Promise<Response>>>;
function stubFetch(handler: (url: string, init: RequestInit) => Response | Promise<Response>): FetchMock {
  const mock = vi.fn(async (url: string, init: RequestInit = {}) => handler(url, init));
  vi.stubGlobal("fetch", mock);
  return mock;
}
const authHeader = (init?: RequestInit) => (init?.headers as Record<string, string>)?.Authorization;

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://api.test/");
  resetSessionCache();
  clearSession();
  setUnauthorizedHandler(null);
});

describe("API client：封包解析（PRD §7.2）", () => {
  it("成功封包只回 data；帶上 Bearer、Accept，base URL 去尾斜線", async () => {
    saveSession(SESSION);
    const fetchMock = stubFetch(() => ok({ id: "p1" }));
    await expect(apiRequest<{ id: string }>("/api/v1/projects/p1")).resolves.toEqual({ id: "p1" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://api.test/api/v1/projects/p1");
    expect(authHeader(init)).toBe("Bearer access-old");
    expect((init?.headers as Record<string, string>).Accept).toBe("application/json");
  });

  it("query 參數序列化：略過 undefined／null／空字串", async () => {
    const fetchMock = stubFetch(() => ok({ content: [] }));
    await apiRequest("/api/v1/projects", { query: { page: 0, size: 10, q: "", status: undefined, sort: "name,asc" } });
    expect(fetchMock.mock.calls[0][0]).toBe("http://api.test/api/v1/projects?page=0&size=10&sort=name%2Casc");
  });

  it("POST 送 JSON body 與 Content-Type", async () => {
    const fetchMock = stubFetch(() => ok({ ok: true }));
    await apiRequest("/api/v1/projects", { method: "POST", body: { name: "A" } });
    const init = fetchMock.mock.calls[0][1]!;
    expect(init.method).toBe("POST");
    expect(init.body).toBe('{"name":"A"}');
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("204 無內容回 undefined", async () => {
    stubFetch(() => new Response(null, { status: 204 }));
    await expect(apiRequest("/api/v1/tasks/x", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("FormData body 原樣送出（不 JSON 序列化、不設 Content-Type），Bearer 照帶", async () => {
    saveSession(SESSION);
    const fetchMock = stubFetch(() => ok({ id: "i1" }));
    const form = new FormData();
    form.append("file", new File(["x"], "a.md"));
    await apiRequest("/api/v1/import/upload", { method: "POST", body: form });
    const init = fetchMock.mock.calls[0][1]!;
    expect(init.body).toBe(form);
    expect((init.headers as Record<string, string>)["Content-Type"]).toBeUndefined();
    expect(authHeader(init)).toBe("Bearer access-old");
  });

  it("FormData 上傳遇到 401：換新 token 後以同一份 FormData 重送一次", async () => {
    saveSession(SESSION);
    const bodies: unknown[] = [];
    stubFetch((url, init) => {
      if (url.endsWith("/api/v1/auth/refresh")) {
        return ok({ accessToken: "access-new", refreshToken: "refresh-new", expiresIn: 1800, role: "OPERATOR" });
      }
      bodies.push(init.body);
      return authHeader(init) === "Bearer access-new" ? ok({ id: "i1" }) : json({ code: 401, message: "x", errors: [] }, 401);
    });
    const form = new FormData();
    form.append("file", new File(["x"], "a.md"));
    await expect(apiRequest("/api/v1/import/upload", { method: "POST", body: form })).resolves.toEqual({ id: "i1" });
    expect(bodies).toEqual([form, form]);
  });

  it("錯誤封包 → ApiError（欄位錯誤、reason、details、traceId 都保留）", async () => {
    stubFetch(() =>
      json(
        {
          code: 400,
          message: "目標依賴成環",
          reason: "依賴成環",
          errors: [{ field: "dependsOn", message: "成環" }],
          details: { cycle: ["a", "b", "a"] },
          timestamp: "t",
          traceId: "tr-body",
        },
        400,
        { "X-Trace-Id": "tr-header" },
      ),
    );
    const err = await apiRequest("/api/v1/goals/g").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    const e = err as ApiError;
    expect(e.status).toBe(400);
    expect(e.reason).toBe("依賴成環");
    expect(e.errors).toEqual([{ field: "dependsOn", message: "成環" }]);
    expect(e.details).toEqual({ cycle: ["a", "b", "a"] });
    expect(e.traceId).toBe("tr-body"); // 封包欄位優先於標頭
    expect(describeError(e)).toBe("目標依賴成環：依賴成環（traceId：tr-body）");
  });

  it("封包沒有 traceId 時退回回應標頭 X-Trace-Id；非 JSON 錯誤（例如 nginx 502）也不崩潰", async () => {
    stubFetch(() => new Response("<html>Bad Gateway</html>", { status: 502, headers: { "X-Trace-Id": "tr-h" } }));
    const e = (await apiRequest("/api/v1/projects").catch((x: unknown) => x)) as ApiError;
    expect(e).toBeInstanceOf(ApiError);
    expect(e.status).toBe(502);
    expect(e.traceId).toBe("tr-h");
    expect(e.isNetworkError).toBe(false);
  });

  it("網路層失敗 → status 0 的 ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const e = (await apiRequest("/api/v1/projects").catch((x: unknown) => x)) as ApiError;
    expect(e).toBeInstanceOf(ApiError);
    expect(e.isNetworkError).toBe(true);
    expect(e.message).toContain("無法連線");
  });
});

describe("API client：檔案下載（apiDownload）", () => {
  it("成功：回 Blob 與 Content-Disposition 的檔名，帶 Bearer，不解封包", async () => {
    saveSession(SESSION);
    const fetchMock = stubFetch(
      () =>
        new Response("{\"version\":1}", {
          status: 200,
          headers: { "content-type": "application/json", "content-disposition": "attachment; filename=\"a.json\"" },
        }),
    );
    const out = await apiDownload("/api/v1/settings/export", { method: "POST" });
    expect(out.filename).toBe("a.json");
    expect(await out.blob.text()).toBe("{\"version\":1}");
    expect(authHeader(fetchMock.mock.calls[0][1])).toBe("Bearer access-old");
  });

  it("失敗（403）：照常解成 ApiError（reason 與 traceId 保留），不回 Blob", async () => {
    saveSession(SESSION);
    stubFetch(() => json({ code: 403, message: "權限不足", reason: "ACCESS_DENIED", errors: [], traceId: "tr-403" }, 403));
    const e = (await apiDownload("/api/v1/settings/export", { method: "POST" }).catch((x: unknown) => x)) as ApiError;
    expect(e).toBeInstanceOf(ApiError);
    expect(e.status).toBe(403);
    expect(e.reason).toBe("ACCESS_DENIED");
    expect(e.traceId).toBe("tr-403");
  });

  it.each([
    ["attachment; filename=\"aisdlc-settings-20261015.json\"", "aisdlc-settings-20261015.json"],
    ["attachment; filename=plain.json", "plain.json"],
    ["attachment; filename*=UTF-8''%E8%A8%AD%E5%AE%9A.json", "設定.json"],
    ["attachment", null],
    [null, null],
  ])("filenameFromDisposition(%s) → %s", (header, expected) => {
    expect(filenameFromDisposition(header)).toBe(expected);
  });
});

describe("API client：回應標頭（apiRequestWithHeaders）與自訂 Accept", () => {
  it("連同回應標頭一併回傳（審核的 X-Follow-Up-Run-Id）；204 的 data 為 undefined", async () => {
    saveSession(SESSION);
    stubFetch(() => new Response(null, { status: 204, headers: { "X-Follow-Up-Run-Id": "run-2" } }));
    const out = await apiRequestWithHeaders<void>("/api/v1/executions/r/review/v", { method: "POST", body: { decision: "SKIP" } });
    expect(out.data).toBeUndefined();
    expect(out.headers.get("X-Follow-Up-Run-Id")).toBe("run-2");
  });

  it("失敗照常丟 ApiError；accept 選項改寫 Accept 標頭", async () => {
    const fetchMock = stubFetch(() => json({ code: 409, message: "審核項已處理", reason: "審核項已處理", errors: [] }, 409));
    const e = (await apiRequestWithHeaders("/x", { accept: "text/csv" }).catch((x: unknown) => x)) as ApiError;
    expect(e).toBeInstanceOf(ApiError);
    expect(e.reason).toBe("審核項已處理");
    expect((fetchMock.mock.calls[0][1]?.headers as Record<string, string>).Accept).toBe("text/csv");
  });
});

describe("API client：給 SSE 用的 token 換新（EventSource 不能帶標頭、看不到 401）", () => {
  const refreshReply = () => ok({ accessToken: "access-new", refreshToken: "refresh-new", expiresIn: 1800, role: "OPERATOR" });

  it("token 還有效：getFreshAccessToken 直接回現值，不打換新端點", async () => {
    saveSession({ ...SESSION, expiresAt: Date.now() + TOKEN_RENEW_MARGIN_MS * 10 });
    const fetchMock = stubFetch(refreshReply);
    await expect(getFreshAccessToken()).resolves.toBe("access-old");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("快到期（在換新餘裕內）：先換新再回新 token（網址上的 token 不能是快過期的）", async () => {
    saveSession({ ...SESSION, expiresAt: Date.now() + TOKEN_RENEW_MARGIN_MS - 1_000 });
    const fetchMock = stubFetch(refreshReply);
    await expect(getFreshAccessToken()).resolves.toBe("access-new");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(loadSession()?.refreshToken).toBe("refresh-new");
  });

  it("force（連線被關、疑似 401）：不管到期時間一律換新", async () => {
    saveSession({ ...SESSION, expiresAt: Date.now() + 3_600_000 });
    stubFetch(refreshReply);
    await expect(getFreshAccessToken({ force: true })).resolves.toBe("access-new");
  });

  it("沒有登入狀態回 null；換新失敗＝登入失效（清 session、呼叫處理器）並回 null", async () => {
    stubFetch(refreshReply);
    await expect(getFreshAccessToken()).resolves.toBeNull();

    saveSession(SESSION);
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    stubFetch(() => json({ code: 401, message: "x", errors: [] }, 401));
    await expect(getFreshAccessToken({ force: true })).resolves.toBeNull();
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
    expect(loadSession()).toBeNull();
  });

  it("renewSession：成功回 true 並寫回新 token；沒有 session 回 false 且觸發登入失效", async () => {
    saveSession(SESSION);
    stubFetch(refreshReply);
    await expect(renewSession()).resolves.toBe(true);
    expect(loadSession()?.accessToken).toBe("access-new");

    clearSession();
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    await expect(renewSession()).resolves.toBe(false);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });
});

describe("API client：401 → refresh token 換新 → 重送一次", () => {
  it("換新成功：新 token 寫回 session，原請求以新 token 重送並成功", async () => {
    saveSession(SESSION);
    const fetchMock = stubFetch((url, init) => {
      if (url.endsWith("/api/v1/auth/refresh")) {
        expect(JSON.parse(String(init.body))).toEqual({ refreshToken: "refresh-old" });
        expect(authHeader(init)).toBeUndefined(); // 換新請求不帶舊的 Bearer
        return ok({ accessToken: "access-new", refreshToken: "refresh-new", expiresIn: 1800, role: "OPERATOR" });
      }
      return authHeader(init) === "Bearer access-new"
        ? ok({ id: "p1" })
        : json({ code: 401, message: "未認證", errors: [], timestamp: "t", traceId: "x" }, 401);
    });

    await expect(apiRequest("/api/v1/projects/p1")).resolves.toEqual({ id: "p1" });
    expect(fetchMock).toHaveBeenCalledTimes(3); // 401、refresh、重送
    expect(loadSession()).toMatchObject({ accessToken: "access-new", refreshToken: "refresh-new", username: "operator" });
  });

  it("換新失敗：清掉 session、呼叫登入失效處理器、丟 401 ApiError", async () => {
    saveSession(SESSION);
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    stubFetch(() => json({ code: 401, message: "未認證", errors: [], timestamp: "t", traceId: "x" }, 401));

    const e = (await apiRequest("/api/v1/projects").catch((x: unknown) => x)) as ApiError;
    expect(e.status).toBe(401);
    expect(e.message).toContain("登入已逾期");
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
    expect(loadSession()).toBeNull();
  });

  it("同時多個 401 只會換新一次", async () => {
    saveSession(SESSION);
    let refreshes = 0;
    stubFetch((url, init) => {
      if (url.endsWith("/api/v1/auth/refresh")) {
        refreshes += 1;
        return ok({ accessToken: "access-new", refreshToken: "refresh-new", expiresIn: 1800, role: "OPERATOR" });
      }
      return authHeader(init) === "Bearer access-new" ? ok("fine") : json({ code: 401, message: "x", errors: [] }, 401);
    });
    const results = await Promise.all([apiRequest("/a"), apiRequest("/b"), apiRequest("/c")]);
    expect(results).toEqual(["fine", "fine", "fine"]);
    expect(refreshes).toBe(1);
  });

  it("auth:false（登入）收到 401 不換新、不導向，直接丟錯給表單顯示", async () => {
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    const fetchMock = stubFetch(() => json({ code: 401, message: "帳號或密碼錯誤", errors: [] }, 401));
    const e = (await apiRequest("/api/v1/auth/login", { method: "POST", body: {}, auth: false }).catch(
      (x: unknown) => x,
    )) as ApiError;
    expect(e.status).toBe(401);
    expect(e.message).toBe("帳號或密碼錯誤");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });
});
