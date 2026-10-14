import { beforeEach, describe, expect, it, vi } from "vitest";

import { clearSession, loadSession, resetSessionCache, saveSession, type Session } from "@/lib/auth/store";
import { ApiError, apiRequest, describeError, setUnauthorizedHandler } from "./client";

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
