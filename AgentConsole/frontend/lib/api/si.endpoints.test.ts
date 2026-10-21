import { readFileSync } from "node:fs";
import path from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { clearSession, resetSessionCache } from "@/lib/auth/store";
import * as api from "./endpoints";

/**
 * SelfImproving 唯讀鏡像的 API 層（TCS-SelfImprovingMirror-P1b R11）：端點函式恰六個、全是 GET；網址、查詢與 id 編碼；
 * 已入庫的 schema.d.ts 含六個路徑且各只有 get。
 */
const ROOT = process.cwd();

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "");
  resetSessionCache();
  clearSession();
});

function okJson(data: unknown = {}): Response {
  return new Response(JSON.stringify({ code: 200, message: "success", data }), { status: 200, headers: { "content-type": "application/json" } });
}

/** 取代全域 fetch：回傳每次呼叫的 [網址, init]。 */
function stubFetch() {
  const fetchMock = vi.fn(async () => okJson());
  vi.stubGlobal("fetch", fetchMock);
  return () => fetchMock.mock.calls.map((c) => c as unknown as [string, RequestInit]);
}

const SI_FUNCTIONS = ["getSiEvents", "getSiObservations", "getSiProposal", "getSiProposals", "getSiRuns", "getSiStatus"];

describe("AT_932_2_7 endpoints.ts 的 SI 匯出恰為六個 GET 函式", () => {
  it("AT_932_2_7 名稱符合 ^(get|post|put|patch|delete)Si 的匯出恰為六個 getSi*，沒有任何 postSi、putSi、patchSi、deleteSi", () => {
    const names = Object.keys(api).filter((n) => /^(get|post|put|patch|delete)Si/.test(n));
    expect(names.sort()).toEqual(SI_FUNCTIONS);
    expect(names.filter((n) => /^(post|put|patch|delete)Si/.test(n))).toEqual([]);
  });

  it("AT_932_2_7 六個函式皆為 GET、無本文，網址依序為 status、observations?since&limit、events?limit、proposals、proposals/{id}、runs?since；undefined 的選項不進網址", async () => {
    const calls = stubFetch();
    await api.getSiStatus();
    await api.getSiObservations({ since: 7, limit: 100 });
    await api.getSiEvents({ limit: 100 });
    await api.getSiProposals();
    await api.getSiProposal("PROP-SI-004");
    await api.getSiRuns({ since: 3 });
    // undefined 的選項不進網址（含空物件與明示 undefined）
    await api.getSiObservations({});
    await api.getSiObservations({ since: undefined, limit: undefined });
    // since 為 0 是合法游標（不是缺值），必須原樣送出
    await api.getSiEvents({ since: 0, limit: 5 });

    expect(calls().map(([url]) => url)).toEqual([
      "/api/v1/si/status",
      "/api/v1/si/observations?since=7&limit=100",
      "/api/v1/si/events?limit=100",
      "/api/v1/si/proposals",
      "/api/v1/si/proposals/PROP-SI-004",
      "/api/v1/si/runs?since=3",
      "/api/v1/si/observations",
      "/api/v1/si/observations",
      "/api/v1/si/events?since=0&limit=5",
    ]);
    for (const [, init] of calls()) {
      expect(init.method ?? "GET", "SI 端點不得有 GET 以外的方法").toBe("GET");
      expect(init.body, "SI 請求不得帶本文").toBeUndefined();
    }
  });

  it("AT_932_2_7 getSiProposal 對含 /、空白、中文的 id 以 encodeURIComponent 編碼，結果仍是單一路徑段", async () => {
    const calls = stubFetch();
    const ids = ["a/b", "PROP SI 004", "提案", "PROP-SI-004?x=1", "PROP#1", "50%"];
    for (const id of ids) await api.getSiProposal(id);
    const urls = calls().map(([url]) => url);
    expect(urls).toEqual(ids.map((id) => `/api/v1/si/proposals/${encodeURIComponent(id)}`));
    const base = "/api/v1/si/proposals/".split("/").length;
    for (const url of urls) {
      // 查詢字元與斜線都被編碼：不多出路徑段、不多出查詢字串或片段
      expect(url.split("/").length, url).toBe(base);
      expect(url.includes("?") || url.includes("#"), url).toBe(false);
    }
    expect(urls[0]).toBe("/api/v1/si/proposals/a%2Fb");
    expect(urls[1]).toBe("/api/v1/si/proposals/PROP%20SI%20004");
    expect(urls[2]).toBe("/api/v1/si/proposals/%E6%8F%90%E6%A1%88");
  });

  it("AT_932_2_7 signal 原樣傳給 fetch（查詢被取消時請求一併中止）", async () => {
    const calls = stubFetch();
    const controller = new AbortController();
    await api.getSiStatus({ signal: controller.signal });
    await api.getSiObservations({ limit: 5, signal: controller.signal });
    for (const [, init] of calls()) expect(init.signal).toBe(controller.signal);
  });

  it("AT_932_2_7 回傳解開封包後的 data（apiRequest 的行為）；後端的 503 si_unavailable 丟出帶 reason 與 details 的 ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => okJson({ schemaRev: 1, kind: "status", items: [] })),
    );
    await expect(api.getSiStatus()).resolves.toEqual({ schemaRev: 1, kind: "status", items: [] });
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ code: 503, message: "SI 不可用", reason: "si_unavailable", details: { cause: "timeout", detail: "rc=none; stderr=x" } }), {
            status: 503,
            headers: { "content-type": "application/json" },
          }),
      ),
    );
    await expect(api.getSiStatus()).rejects.toMatchObject({ status: 503, reason: "si_unavailable", details: { cause: "timeout", detail: "rc=none; stderr=x" } });
  });
});

describe("AT_940_8_2 已入庫的 schema.d.ts 含六個 SI 路徑且各只有 get", () => {
  const schema = readFileSync(path.join(ROOT, "lib", "api", "schema.d.ts"), "utf-8");
  const PATHS: Array<[path: string, operationId: string]> = [
    ["/api/v1/si/status", "getSiStatus"],
    ["/api/v1/si/observations", "getSiObservations"],
    ["/api/v1/si/events", "getSiEvents"],
    ["/api/v1/si/proposals", "getSiProposals"],
    ["/api/v1/si/proposals/{id}", "getSiProposal"],
    ["/api/v1/si/runs", "getSiRuns"],
  ];

  /** openapi-typescript 的 paths 區塊：`"<路徑>": {` 起、下一個縮排四格的 `};` 止。 */
  function pathBlock(key: string): string {
    const start = schema.indexOf(`"${key}": {`);
    expect(start, `schema.d.ts 找不到路徑 ${key}`).toBeGreaterThan(-1);
    const end = schema.indexOf("\n    };", start);
    expect(end, `schema.d.ts 的路徑 ${key} 區塊沒有結尾`).toBeGreaterThan(start);
    return schema.slice(start, end);
  }

  it.each(PATHS)("AT_940_8_2 %s：區塊內只有 get（operationId %s），沒有 post、put、patch、delete 的操作", (key, operationId) => {
    const block = pathBlock(key);
    expect(block).toContain(`get: operations["${operationId}"]`);
    expect(block.match(/\b(post|put|patch|delete): operations\[/g) ?? []).toEqual([]);
    expect(schema).toContain(`${operationId}: {`);
  });

  it("AT_940_8_2 schema.d.ts 中以 /api/v1/si/ 起頭的路徑鍵恰為這六個（不多不少）", () => {
    const keys = [...schema.matchAll(/^ {4}"(\/api\/v1\/si\/[^"]*)": \{/gm)].map((m) => m[1]);
    expect(keys.sort()).toEqual(PATHS.map(([key]) => key).sort());
  });

  it("AT_940_8_2 package.json 的 scripts 有 gen:api（重產指令；重產後無差異由 V7 現查）", () => {
    const pkg = JSON.parse(readFileSync(path.join(ROOT, "package.json"), "utf-8")) as { scripts: Record<string, string> };
    expect(pkg.scripts["gen:api"]).toBe("node scripts/gen-api.mjs");
  });
});
