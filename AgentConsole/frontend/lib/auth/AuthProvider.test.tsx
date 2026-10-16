import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Providers, failure, signIn, stubApi } from "@/tests/helpers/api";
import { useAuth } from "./AuthProvider";
import { clearSession, loadSession } from "./store";

const router = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn(), back: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/",
}));

const LOGOUT_PATH = "/api/v1/auth/logout";

function LogoutButton() {
  const { logout, status } = useAuth();
  return (
    <button type="button" onClick={logout} data-status={status}>
      登出
    </button>
  );
}

function view(client = new QueryClient()) {
  render(
    <Providers client={client}>
      <LogoutButton />
    </Providers>,
  );
  return client;
}

beforeEach(() => {
  router.replace.mockClear();
  signIn("OPERATOR", "operator"); // refreshToken＝"r"
});

describe("登出（契約 §1.9.1、§2.8 第 10 點；v1.4 D-19，API-AUTH-03）", () => {
  it("先 POST /auth/logout 撤銷 refresh token（body 帶目前 session 的 refreshToken、不帶 Authorization），再清 session 與快取、導向 /login", async () => {
    const { calls } = stubApi((c) => (c.path === LOGOUT_PATH ? { status: 204 } : undefined));
    const headers: Array<Record<string, string>> = [];
    const realFetch = globalThis.fetch;
    vi.stubGlobal("fetch", (input: string, init: RequestInit = {}) => {
      headers.push((init.headers ?? {}) as Record<string, string>);
      return realFetch(input, init);
    });
    const client = view();
    client.setQueryData(["x"], "cached");
    await userEvent.click(screen.getByRole("button", { name: "登出" }));

    await waitFor(() => expect(calls.filter((c) => c.path === LOGOUT_PATH)).toHaveLength(1));
    const call = calls.find((c) => c.path === LOGOUT_PATH)!;
    expect(call.method).toBe("POST");
    expect(call.body).toEqual({ refreshToken: "r" });
    expect(headers.at(-1)?.Authorization).toBeUndefined(); // 免認證：登出時 access token 可能已過期

    expect(loadSession()).toBeNull();
    expect(client.getQueryData(["x"])).toBeUndefined();
    expect(router.replace).toHaveBeenCalledWith("/login");
  });

  it.each([
    ["伺服器 500", () => failure(500, { message: "伺服器錯誤" })],
    ["400（格式不合）", () => failure(400, { message: "請求格式錯誤", errors: [{ field: "refreshToken", message: "不可為空" }] })],
  ])("logout 請求失敗（%s）也照常登出：清 session、導向 /login；失敗被吞掉（vitest 會把未處理的拒絕判為整支失敗）", async (_name, reply) => {
    const { calls } = stubApi((c) => (c.path === LOGOUT_PATH ? reply() : undefined));
    view();
    await userEvent.click(screen.getByRole("button", { name: "登出" }));
    await waitFor(() => expect(calls.some((c) => c.path === LOGOUT_PATH)).toBe(true));
    expect(loadSession()).toBeNull();
    expect(router.replace).toHaveBeenCalledWith("/login");
    await new Promise((resolve) => setTimeout(resolve, 20)); // 讓被吞掉的拒絕有機會冒出來
  });

  it("網路失敗（fetch 丟例外）也照常登出", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    view();
    await userEvent.click(screen.getByRole("button", { name: "登出" }));
    expect(loadSession()).toBeNull();
    expect(router.replace).toHaveBeenCalledWith("/login");
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(1));
  });

  it("不等結果：logout 請求永遠沒回應，本機登出仍同步完成（不阻擋導向登入頁）", async () => {
    const fetchMock = vi.fn(() => new Promise<Response>(() => undefined));
    vi.stubGlobal("fetch", fetchMock);
    view();
    await userEvent.click(screen.getByRole("button", { name: "登出" }));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(loadSession()).toBeNull();
    expect(router.replace).toHaveBeenCalledWith("/login");
  });

  it("沒有 session（已被清掉）就不呼叫端點，只做本機登出", async () => {
    const { calls } = stubApi(() => ({ status: 204 }));
    view();
    clearSession();
    await userEvent.click(screen.getByRole("button", { name: "登出" }));
    expect(calls).toEqual([]);
    expect(router.replace).toHaveBeenCalledWith("/login");
  });
});
