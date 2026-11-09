import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { forgetProjectId, getLastProjectId, rememberProjectId, resolveCurrentProjectId } from "@/lib/nav/lastProject";
import { Providers, makeClient, signIn, stubApi } from "@/tests/helpers/api";
import { useCurrentProjectId } from "./useCurrentProjectId";

vi.mock("next/navigation", () => ({
  usePathname: () => "/execute",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

/**
 * 側欄「目前專案」的存在性判斷（DEF-AC-035；TCS-ExecMonitorEntry 勘誤 11 W-E6）：
 * AT_953_6_1（最近造訪不在已載入且完整的列表 → 遺忘並退第一筆）、AT_953_6_2（在列表內 → 沿用）、
 * AT_953_6_3（列表不完整 → 不判定）、AT_953_6_4（列表未載入 → 不判定）。
 * 判定指令：npx vitest run hooks/useCurrentProjectId.test.tsx -t "<AT 底線形>"
 */
const row = (id: string) => ({
  id,
  name: id,
  executionPath: `/work/${id}`,
  status: "ACTIVE",
  autonomyLevel: 3,
  signedOff: true,
  goalsCount: 0,
  tasksCount: 0,
  tasksDone: 0,
  updatedAt: "2026-11-09T00:00:00Z",
});
const page = (ids: string[], totalElements = ids.length) => ({ content: ids.map(row), page: 0, size: 100, totalElements, totalPages: 1 });

function backend(ids: string[], totalElements?: number) {
  stubApi((c) => (c.method === "GET" && c.path === "/api/v1/projects" ? { data: page(ids, totalElements) } : undefined));
}

function mount() {
  const wrapper = ({ children }: { children: ReactNode }) => <Providers client={makeClient()}>{children}</Providers>;
  return renderHook(() => useCurrentProjectId(), { wrapper });
}

beforeEach(() => signIn("OPERATOR", "operator"));
afterEach(() => {
  for (const id of ["p9", "p2"]) forgetProjectId(id);
});

describe("resolveCurrentProjectId 純函式", () => {
  it("網址優先；沒有最近造訪時取列表第一筆；都沒有＝null", () => {
    expect(resolveCurrentProjectId({ fromPath: "a", last: "b", page: page(["c"]) })).toEqual({ id: "a", stale: false });
    expect(resolveCurrentProjectId({ fromPath: null, last: null, page: page(["c", "d"]) })).toEqual({ id: "c", stale: false });
    expect(resolveCurrentProjectId({ fromPath: null, last: null, page: undefined })).toEqual({ id: null, stale: false });
    expect(resolveCurrentProjectId({ fromPath: null, last: "b", page: page([]) })).toEqual({ id: null, stale: true });
  });

  it("AT_953_6_1 純函式：最近造訪不在已載入且完整的列表內時，退到列表第一筆並標 stale（SCG-4 一審 F-01：殺「stale 時不退第一筆」突變）", () => {
    expect(resolveCurrentProjectId({ fromPath: null, last: "b", page: page(["c", "d"]) })).toEqual({ id: "c", stale: true });
    // 列表不完整（總數大於已載入筆數）時不判定：沿用最近造訪、不標 stale
    expect(resolveCurrentProjectId({ fromPath: null, last: "b", page: page(["c", "d"], 150) })).toEqual({ id: "b", stale: false });
  });
});

describe("useCurrentProjectId 最近造訪的存在性判斷", () => {
  it("AT_953_6_1 最近造訪＝p9、列表已載入且完整 [p1,p2]：回 p1，鍵被移除", async () => {
    rememberProjectId("p9");
    backend(["p1", "p2"]);
    const { result } = mount();
    await waitFor(() => expect(result.current).toBe("p1"));
    await waitFor(() => expect(getLastProjectId()).toBeNull());
    expect(window.sessionStorage.getItem("aisdlc.console.lastProject")).toBeNull();
  });

  it("AT_953_6_2 最近造訪＝p2、列表 [p1,p2]：回 p2，鍵仍在", async () => {
    rememberProjectId("p2");
    backend(["p1", "p2"]);
    const { result } = mount();
    await waitFor(() => expect(result.current).toBe("p2"));
    await new Promise((r) => setTimeout(r, 30)); // 給（不該發生的）遺忘一個落地的機會
    expect(getLastProjectId()).toBe("p2");
  });

  it("AT_953_6_3 最近造訪＝p9、列表已載入但不完整（2 筆、totalElements 150）：回 p9，鍵仍在", async () => {
    rememberProjectId("p9");
    backend(["p1", "p2"], 150);
    const { result } = mount();
    await new Promise((r) => setTimeout(r, 60));
    expect(result.current).toBe("p9");
    expect(getLastProjectId()).toBe("p9");
  });

  it("AT_953_6_4 最近造訪＝p9、列表尚未載入：回 p9，鍵仍在", async () => {
    rememberProjectId("p9");
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>(() => {})),
    ); // 請求永不回應 ⇒ data 恆為 undefined
    const { result } = mount();
    await new Promise((r) => setTimeout(r, 30));
    expect(result.current).toBe("p9");
    expect(getLastProjectId()).toBe("p9");
  });
});
