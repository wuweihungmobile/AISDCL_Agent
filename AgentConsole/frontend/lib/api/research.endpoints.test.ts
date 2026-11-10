import { readFileSync } from "node:fs";
import path from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { clearSession, resetSessionCache } from "@/lib/auth/store";
import { ApiError } from "./client";
import * as api from "./endpoints";

/**
 * 研究來源單一化的 API 層（TCS-ResearchRegistry-20261110 AT-965-9-4）：三個追蹤來源端點與兩個同步端點的路徑、方法與本文；
 * 錯誤封包丟帶 `reason` 與 `details` 的 ApiError；已入庫的 schema.d.ts 含三個新 operationId（研究側）。
 * 判定指令：npx vitest run lib/api/si.endpoints.test.ts lib/api/research.endpoints.test.ts -t AT_965_9_4
 */
const ROOT = process.cwd();

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "");
  resetSessionCache();
  clearSession();
});

function okJson(data: unknown = {}, status = 200): Response {
  return new Response(JSON.stringify({ code: status, message: "success", data }), { status, headers: { "content-type": "application/json" } });
}

function stubFetch(responder: () => Response = () => okJson()) {
  const fetchMock = vi.fn(async () => responder());
  vi.stubGlobal("fetch", fetchMock);
  return () => fetchMock.mock.calls.map((c) => c as unknown as [string, RequestInit]);
}

describe("AT_965_9_4 研究來源單一化的端點函式：路徑、方法與 camelCase 本文", () => {
  it("AT_965_9_4 listWatchSources／addWatchSource／patchWatchSource／getRegistrySyncStatus／postRegistrySync 的方法與網址", async () => {
    const calls = stubFetch();
    await api.listWatchSources();
    await api.addWatchSource({ slug: "s1", url: "https://example.org/x", kind: "blog", extract: "全文", layer: "INDUSTRY", expand: { mode: "links", prefix: "/b/", max: 2 } });
    await api.patchWatchSource("a/b", { enabled: false });
    await api.getRegistrySyncStatus();
    await api.postRegistrySync();
    expect(calls().map(([url, init]) => `${init.method ?? "GET"} ${url}`)).toEqual([
      "GET /api/v1/research/watch-sources",
      "POST /api/v1/research/watch-sources",
      "PATCH /api/v1/research/watch-sources/a%2Fb",
      "GET /api/v1/si/research-registry",
      "POST /api/v1/si/research-registry/sync",
    ]);
    const bodies = calls().map(([, init]) => (init.body === undefined ? undefined : JSON.parse(init.body as string)));
    expect(bodies[1]).toEqual({ slug: "s1", url: "https://example.org/x", kind: "blog", extract: "全文", layer: "INDUSTRY", expand: { mode: "links", prefix: "/b/", max: 2 } });
    expect(Object.keys(bodies[1])).not.toContain("addedBy");
    expect(bodies[2]).toEqual({ enabled: false });
    expect(bodies[4]).toEqual({});
  });

  it("AT_965_9_4 回應解開封包：postRegistrySync 回 data（不論有無 data 封包）；清單回陣列", async () => {
    stubFetch(() => okJson({ outcome: "written", state: "pending" }, 201));
    await expect(api.postRegistrySync()).resolves.toEqual({ outcome: "written", state: "pending" });
    stubFetch(() => new Response(JSON.stringify({ outcome: "unchanged", state: "synced" }), { status: 200, headers: { "content-type": "application/json" } }));
    await expect(api.postRegistrySync()).resolves.toEqual({ outcome: "unchanged", state: "synced" });
    stubFetch(() => okJson([]));
    await expect(api.listWatchSources()).resolves.toEqual([]);
  });

  it("AT_965_9_4 錯誤封包丟 ApiError：帶 status、reason 與 details（含 400 的 errors[].rule）", async () => {
    stubFetch(
      () =>
        new Response(JSON.stringify({ code: 422, message: "太大", reason: "registry_too_large", details: { what: "registry_text", limit: 24576, size: 30000 } }), {
          status: 422,
          headers: { "content-type": "application/json" },
        }),
    );
    const error = await api.postRegistrySync().catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 422, reason: "registry_too_large", details: { what: "registry_text", limit: 24576, size: 30000 } });

    stubFetch(
      () =>
        new Response(JSON.stringify({ code: 400, message: "bad", errors: [{ field: "url", rule: "invalid_url", message: "網址不合" }] }), {
          status: 400,
          headers: { "content-type": "application/json" },
        }),
    );
    const bad = (await api.addWatchSource({ slug: "s", url: "http://x", kind: "blog", extract: "e", layer: "OSS", expand: null }).catch((e: unknown) => e)) as ApiError;
    expect(bad.status).toBe(400);
    expect(bad.errors[0]).toMatchObject({ field: "url" });
  });
});

describe("AT_965_9_4 已入庫的 schema.d.ts 含研究側三個新 operationId 與路徑", () => {
  const schema = readFileSync(path.join(ROOT, "lib", "api", "schema.d.ts"), "utf-8");

  it("AT_965_9_4 三個 operationId 與兩個路徑鍵都在；PATCH 區塊只有 patch 一個方法", () => {
    for (const id of ["listResearchWatchSources", "addResearchWatchSource", "updateResearchWatchSource"]) expect(schema, id).toContain(`${id}: {`);
    expect(schema).toContain('"/api/v1/research/watch-sources": {');
    expect(schema).toContain('"/api/v1/research/watch-sources/{slug}": {');
    const start = schema.indexOf('"/api/v1/research/watch-sources/{slug}": {');
    const block = schema.slice(start, schema.indexOf("\n    };", start));
    expect([...block.matchAll(/^ {8}(get|put|post|delete|patch): operations\["([^"]+)"\];$/gm)].map((m) => `${m[1]}:${m[2]}`)).toEqual(["patch:updateResearchWatchSource"]);
  });

  it("AT_965_9_4 schemas 含 WatchSourceDto／ResearchWatchSourceRequest／ResearchRegistrySyncStatus／ResearchRegistrySyncResult；請求本文沒有 addedBy", () => {
    for (const name of ["WatchSourceDto", "ResearchWatchSourceRequest", "ResearchRegistrySyncStatus", "ResearchRegistrySyncResult"]) expect(schema, name).toContain(`${name}: {`);
    const start = schema.indexOf("ResearchWatchSourceRequest: {");
    const block = schema.slice(start, schema.indexOf("\n        };", start));
    expect(block).not.toContain("addedBy");
  });
});
