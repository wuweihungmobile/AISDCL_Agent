import { readFileSync } from "node:fs";
import path from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { clearSession, resetSessionCache } from "@/lib/auth/store";
import * as api from "./endpoints";

/**
 * SelfImproving 的 API 層：P1b 的六個唯讀函式（TCS-SelfImprovingMirror-P1b R11：網址、查詢與 id 編碼）加 P2b 的寫入載體
 * （TCS-SelfImprovingDecide-P2b W16、W23：四個 POST 加一個對帳 GET）；已入庫的 schema.d.ts 含十個 SI 路徑、各自只有規劃過的方法。
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

const SI_READ_FUNCTIONS = ["getSiConsoleWrites", "getSiEvents", "getSiObservations", "getSiProposal", "getSiProposals", "getSiRuns", "getSiStatus"];
const SI_WRITE_FUNCTIONS = ["postSiDecide", "postSiObservation", "postSiObservationClose", "postSiObservationValidate"];

describe("AT_950_9_E_1 endpoints.ts 的 SI 匯出受限：get 加 Si 恰七個、post 加 Si 恰四個，沒有 put、patch、delete，總數受同步", () => {
  it("AT_950_9_E_1 名稱符合 ^(get|post|put|patch|delete)Si 的匯出恰為七個 getSi*（P1b 的六個加 getSiConsoleWrites）與四個 postSi*，沒有任何 putSi、patchSi、deleteSi", () => {
    const names = Object.keys(api).filter((n) => /^(get|post|put|patch|delete)Si/.test(n));
    expect(names.filter((n) => n.startsWith("get")).sort()).toEqual(SI_READ_FUNCTIONS);
    expect(names.filter((n) => n.startsWith("post")).sort()).toEqual(SI_WRITE_FUNCTIONS);
    expect(names.filter((n) => /^(put|patch|delete)Si/.test(n))).toEqual([]);
    expect(names).toHaveLength(SI_READ_FUNCTIONS.length + SI_WRITE_FUNCTIONS.length);
  });

  it("AT_950_9_E_1 endpoints.test.ts 的總數釘選為 84（P2b 由 74 加五個 SI 函式成 79，議題中心再加四個，備份總覽再加一個）、EXPECTED 的 SI 十一列只增不減：讀原始碼逐項核對，不靠記憶", () => {
    const source = readFileSync(path.join(ROOT, "lib", "api", "endpoints.test.ts"), "utf-8");
    expect(source, "總數釘選必須是 84").toContain("expect(names).toHaveLength(84);");
    expect(source, "總數釘選不得還留著 79").not.toContain("toHaveLength(79)");
    for (const fn of [...SI_READ_FUNCTIONS.filter((n) => n !== "getSiConsoleWrites"), "getSiConsoleWrites", ...SI_WRITE_FUNCTIONS]) {
      expect(source, `EXPECTED 缺 ${fn}`).toContain(`"${fn}"`);
    }
    // 五個 P2b 新列的方法與網址：POST 四列、GET 一列（含 limit 的網址）
    expect(source).toMatch(/"POST",\s*"\/api\/v1\/si\/proposals\/PROP-SI-004\/decide"/);
    expect(source).toContain('"/api/v1/si/console-writes?limit=100"');
  });
});

describe("AT_932_2_7 P1b 的六個唯讀函式：網址、查詢、id 編碼、signal 與錯誤封包", () => {
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
      expect(init.method ?? "GET", "唯讀端點不得有 GET 以外的方法").toBe("GET");
      expect(init.body, "唯讀請求不得帶本文").toBeUndefined();
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
    await api.getSiConsoleWrites({ limit: 5, signal: controller.signal });
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

describe("AT_950_9_1 五個新端點函式：方法、網址、本文與 id 編碼（P2b W16）", () => {
  const DIGEST = `sha256:${"b".repeat(64)}`;
  const OBS_BODY = { context: "情境", symptom: "症狀", evidence: "docs/x.md:1", category: "bug", severity: "P3", face: "產品", externalDerived: false } as const;

  it("AT_950_9_1 四個 POST 與一個 GET 的方法與網址依序如 W16；POST 本文逐位元組等於輸入的 JSON.stringify，GET 不帶本文", async () => {
    const calls = stubFetch();
    const decide = { dkind: "reject", digest: DIGEST, reason: "證據座標不足，無法判定", reasonClass: "證據不足" } as const;
    const close = { terminal: "fixed", ref: "2b2b0b3d" } as const;
    await api.postSiDecide("PROP-SI-004", decide);
    await api.postSiObservation(OBS_BODY);
    await api.postSiObservationClose("OBS-SI-005", close);
    await api.postSiObservationValidate(OBS_BODY);
    await api.getSiConsoleWrites({ limit: 50 });
    await api.getSiConsoleWrites();

    const seen = calls();
    expect(seen.map(([url, init]) => `${init.method ?? "GET"} ${url}`)).toEqual([
      "POST /api/v1/si/proposals/PROP-SI-004/decide",
      "POST /api/v1/si/observations",
      "POST /api/v1/si/observations/OBS-SI-005/close",
      "POST /api/v1/si/observations/validate",
      "GET /api/v1/si/console-writes?limit=50",
      "GET /api/v1/si/console-writes",
    ]);
    expect(seen[0][1].body).toBe(JSON.stringify(decide));
    expect(seen[1][1].body).toBe(JSON.stringify(OBS_BODY));
    expect(seen[2][1].body).toBe(JSON.stringify(close));
    expect(seen[3][1].body).toBe(JSON.stringify(OBS_BODY));
    expect(seen[4][1].body, "GET 不帶本文").toBeUndefined();
    expect(seen[5][1].body, "GET 不帶本文").toBeUndefined();
    for (const [, init] of seen.slice(0, 4)) {
      expect((init.headers as Record<string, string>)["Content-Type"], "POST 帶 JSON 標頭").toBe("application/json");
    }
  });

  it("AT_950_9_1 postSiDecide 與 postSiObservationClose 的 id 以 encodeURIComponent 編成單一路徑段（含 /、空白、中文、? 與 #）", async () => {
    const calls = stubFetch();
    const ids = ["a/b", "RUN SI 001", "提案", "PROP-SI-004?x=1", "PROP#1", "50%"];
    for (const id of ids) {
      await api.postSiDecide(id, { dkind: "unblock" });
      await api.postSiObservationClose(id, { terminal: "decided", text: "x" });
    }
    const urls = calls().map(([url]) => url);
    const decideBase = "/api/v1/si/proposals//decide".split("/").length;
    const closeBase = "/api/v1/si/observations//close".split("/").length;
    ids.forEach((id, i) => {
      expect(urls[2 * i]).toBe(`/api/v1/si/proposals/${encodeURIComponent(id)}/decide`);
      expect(urls[2 * i + 1]).toBe(`/api/v1/si/observations/${encodeURIComponent(id)}/close`);
      expect(urls[2 * i].split("/").length, urls[2 * i]).toBe(decideBase);
      expect(urls[2 * i + 1].split("/").length, urls[2 * i + 1]).toBe(closeBase);
      expect(urls[2 * i].includes("?") || urls[2 * i].includes("#"), urls[2 * i]).toBe(false);
    });
    expect(urls[0]).toBe("/api/v1/si/proposals/a%2Fb/decide");
    expect(urls[2]).toBe("/api/v1/si/proposals/RUN%20SI%20001/decide");
  });

  it("AT_950_9_1 寫入失敗丟帶 reason 與 details 的 ApiError（403 si_write_forbidden、422 帶 errors）；成功回解開封包後的 data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => okJson({ auditRef: "b2000000-0000-4000-8000-000000000001", kind: "decide", subject: "PROP-SI-004", time: "2026-10-24T22:30:15+08:00", keyId: "f076edf0" })),
    );
    await expect(api.postSiDecide("PROP-SI-004", { dkind: "unblock" })).resolves.toMatchObject({ auditRef: "b2000000-0000-4000-8000-000000000001", kind: "decide" });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ code: 403, message: "帳號不在決定者名單內", reason: "si_write_forbidden" }), { status: 403, headers: { "content-type": "application/json" } })),
    );
    await expect(api.postSiDecide("PROP-SI-004", { dkind: "unblock" })).rejects.toMatchObject({ status: 403, reason: "si_write_forbidden" });
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              code: 422,
              message: "請求欄位未通過檢查（1 項）",
              reason: "invalid_request",
              errors: [{ field: "reason", message: "reason 為必填" }],
              details: { violations: [{ field: "reason", message: "reason 為必填" }] },
            }),
            { status: 422, headers: { "content-type": "application/json" } },
          ),
      ),
    );
    await expect(api.postSiObservationClose("OBS-SI-005", { terminal: "decided" })).rejects.toMatchObject({ status: 422, reason: "invalid_request", errors: [{ field: "reason" }] });
  });
});

/** 一個 SI 路徑期望的方法與 operationId（其餘方法一律不得出現）。 */
type PathSpec = Partial<Record<"get" | "post", string>>;

describe("AT_950_10_2 已入庫的 schema.d.ts 含十個 SI 路徑，各自只有規劃過的方法（含五個新 operationId）", () => {
  const schema = readFileSync(path.join(ROOT, "lib", "api", "schema.d.ts"), "utf-8");
  const PATHS: Array<[path: string, spec: PathSpec]> = [
    ["/api/v1/si/status", { get: "getSiStatus" }],
    ["/api/v1/si/observations", { get: "getSiObservations", post: "postSiObservation" }],
    ["/api/v1/si/events", { get: "getSiEvents" }],
    ["/api/v1/si/proposals", { get: "getSiProposals" }],
    ["/api/v1/si/proposals/{id}", { get: "getSiProposal" }],
    ["/api/v1/si/runs", { get: "getSiRuns" }],
    ["/api/v1/si/proposals/{id}/decide", { post: "postSiDecide" }],
    ["/api/v1/si/observations/{id}/close", { post: "postSiObservationClose" }],
    ["/api/v1/si/observations/validate", { post: "postSiObservationValidate" }],
    ["/api/v1/si/console-writes", { get: "getSiConsoleWrites" }],
  ];

  /** openapi-typescript 的 paths 區塊：`"<路徑>": {` 起、下一個縮排四格的 `};` 止。 */
  function pathBlock(key: string): string {
    const start = schema.indexOf(`"${key}": {`);
    expect(start, `schema.d.ts 找不到路徑 ${key}`).toBeGreaterThan(-1);
    const end = schema.indexOf("\n    };", start);
    expect(end, `schema.d.ts 的路徑 ${key} 區塊沒有結尾`).toBeGreaterThan(start);
    return schema.slice(start, end);
  }

  it.each(PATHS)("AT_950_10_2 %s：區塊內的操作恰為規劃的方法與 operationId，其餘方法一律不出現（沒有 put、patch、delete）", (key, spec) => {
    const block = pathBlock(key);
    const present = [...block.matchAll(/^ {8}(get|put|post|delete|patch): operations\["([^"]+)"\];$/gm)].map((m) => `${m[1]}:${m[2]}`);
    const expected = Object.entries(spec).map(([method, operationId]) => `${method}:${operationId}`);
    expect(present.sort()).toEqual(expected.sort());
    for (const operationId of Object.values(spec)) expect(schema).toContain(`${operationId}: {`);
  });

  it("AT_950_10_2 schema.d.ts 中以 /api/v1/si/ 起頭的路徑鍵恰為這十個（不多不少）；四個新路徑與五個新 operationId 都在", () => {
    const keys = [...schema.matchAll(/^ {4}"(\/api\/v1\/si\/[^"]*)": \{/gm)].map((m) => m[1]);
    expect(keys.sort()).toEqual(PATHS.map(([key]) => key).sort());
    for (const key of ["/api/v1/si/proposals/{id}/decide", "/api/v1/si/observations/{id}/close", "/api/v1/si/observations/validate", "/api/v1/si/console-writes"]) {
      expect(schema, `新路徑 ${key}`).toContain(`"${key}": {`);
    }
    for (const operationId of ["postSiDecide", "postSiObservation", "postSiObservationClose", "postSiObservationValidate", "getSiConsoleWrites"]) {
      expect(schema, `新 operationId ${operationId}`).toContain(`${operationId}: {`);
    }
  });

  it("AT_950_10_2 package.json 的 scripts 有 gen:api（重產指令；重產後無差異由 V7 現查）", () => {
    const pkg = JSON.parse(readFileSync(path.join(ROOT, "package.json"), "utf-8")) as { scripts: Record<string, string> };
    expect(pkg.scripts["gen:api"]).toBe("node scripts/gen-api.mjs");
  });
});
