import { beforeEach, describe, expect, it, vi } from "vitest";

import { clearSession, resetSessionCache } from "@/lib/auth/store";
import * as api from "./endpoints";

/** 函式名與 PRD §7.1 的端點一一對應（RTM：API-PRJ／GOL／TSK／SGN／AUTH）。 */
const EXPECTED: Array<[fn: keyof typeof api, call: () => Promise<unknown>, method: string, path: string, body?: unknown]> = [
  ["login", () => api.login("u", "p"), "POST", "/api/v1/auth/login", { username: "u", password: "p" }],
  ["refreshToken", () => api.refreshToken("r"), "POST", "/api/v1/auth/refresh", { refreshToken: "r" }],
  ["createProject", () => api.createProject({ name: "n", executionPath: "/x", passCriteria: "c" }), "POST", "/api/v1/projects", { name: "n", executionPath: "/x", passCriteria: "c" }],
  ["listProjects", () => api.listProjects({ page: 1, size: 5 }), "GET", "/api/v1/projects?page=1&size=5"],
  ["getProject", () => api.getProject("P"), "GET", "/api/v1/projects/P"],
  ["updateProject", () => api.updateProject("P", { name: "n2" }), "PUT", "/api/v1/projects/P", { name: "n2" }],
  ["deleteProject", () => api.deleteProject("P"), "DELETE", "/api/v1/projects/P"],
  ["signoffProject", () => api.signoffProject("P", "me"), "POST", "/api/v1/projects/P/signoff", { approver: "me" }],
  ["createGoal", () => api.createGoal("P", { name: "g", passCriteria: "c" }), "POST", "/api/v1/projects/P/goals", { name: "g", passCriteria: "c" }],
  ["listGoals", () => api.listGoals("P"), "GET", "/api/v1/projects/P/goals"],
  ["getGoal", () => api.getGoal("G"), "GET", "/api/v1/goals/G"],
  ["updateGoal", () => api.updateGoal("G", { dependsOn: ["X"] }), "PUT", "/api/v1/goals/G", { dependsOn: ["X"] }],
  ["deleteGoal", () => api.deleteGoal("G"), "DELETE", "/api/v1/goals/G"],
  ["reorderGoals", () => api.reorderGoals("P", ["B", "A"]), "PUT", "/api/v1/goals/reorder", { projectId: "P", orderedGoalIds: ["B", "A"] }],
  ["signoffGoal", () => api.signoffGoal("G", "me"), "POST", "/api/v1/goals/G/signoff", { approver: "me" }],
  ["createTask", () => api.createTask("G", { name: "t", passCriteria: "c" }), "POST", "/api/v1/goals/G/tasks", { name: "t", passCriteria: "c" }],
  ["listTasks", () => api.listTasks("G"), "GET", "/api/v1/goals/G/tasks"],
  ["getTask", () => api.getTask("T"), "GET", "/api/v1/tasks/T"],
  ["updateTask", () => api.updateTask("T", { maxRetries: 5 }), "PUT", "/api/v1/tasks/T", { maxRetries: 5 }],
  ["deleteTask", () => api.deleteTask("T"), "DELETE", "/api/v1/tasks/T"],
  ["retryTask", () => api.retryTask("T"), "POST", "/api/v1/tasks/T/retry"],
  ["signoffTask", () => api.signoffTask("T", "me"), "POST", "/api/v1/tasks/T/signoff", { approver: "me" }],

  // ── Phase 3：BRD/PRD 匯入（契約 §1.1）：上傳是 multipart，另見下方專屬測試 ──
  ["listImports", () => api.listImports({ page: 0, size: 10, status: "PARSED", sort: "createdAt,desc" }), "GET", "/api/v1/import?page=0&size=10&status=PARSED&sort=createdAt%2Cdesc"],
  ["importText", () => api.importText({ content: "# BRD", sourceFileName: "e2e-brd.md", sourceType: "MARKDOWN" }), "POST", "/api/v1/import/text", { content: "# BRD", sourceFileName: "e2e-brd.md", sourceType: "MARKDOWN" }],
  ["getImport", () => api.getImport("I"), "GET", "/api/v1/import/I"],
  ["parseImport", () => api.parseImport("I", { autonomyLevel: 3, executionPath: "/x" }), "POST", "/api/v1/import/I/parse", { autonomyLevel: 3, executionPath: "/x" }],
  [
    "editImportResult",
    () => api.editImportResult("I", { project: { name: "n", executionPath: "/x", passCriteria: "c" }, goals: [] }),
    "PUT",
    "/api/v1/import/I/result",
    { parsedResult: { project: { name: "n", executionPath: "/x", passCriteria: "c" }, goals: [] } },
  ],
  ["signoffImport", () => api.signoffImport("I", "me"), "POST", "/api/v1/import/I/signoff", { approver: "me" }],
  ["confirmImport", () => api.confirmImport("I"), "POST", "/api/v1/import/I/confirm"],
  ["rejectImport", () => api.rejectImport("I"), "POST", "/api/v1/import/I/reject"],

  // ── 通知摘要（契約 §1.4）──
  ["getNotificationSummary", () => api.getNotificationSummary(), "GET", "/api/v1/notifications/summary"],

  // ── Phase 6：系統參數（契約 §1.5）：匯入是 multipart、匯出是下載，另見下方專屬測試 ──
  ["listSettings", () => api.listSettings(), "GET", "/api/v1/settings"],
  ["listSettingsByCategory", () => api.listSettingsByCategory("model", { reveal: true }), "GET", "/api/v1/settings/model?reveal=true"],
  ["updateSetting", () => api.updateSetting("model", "apiKey", { value: "k", confirm: true }), "PUT", "/api/v1/settings/model/apiKey", { value: "k", confirm: true }],
  ["updateTokenGuard", () => api.updateTokenGuard({ compactThresholdPct: 70, haltThresholdPct: 95 }), "PUT", "/api/v1/settings/execution/token-guard", { compactThresholdPct: 70, haltThresholdPct: 95 }],
  ["resetSetting", () => api.resetSetting("model", "apiKey", true), "POST", "/api/v1/settings/model/apiKey/reset?confirm=true"],
  ["resetCategory", () => api.resetCategory("execution"), "POST", "/api/v1/settings/execution/reset"],
  ["testConnection", () => api.testConnection({ apiUrl: "https://api.minimax.io/v1/text/chatcompletion_v2" }), "POST", "/api/v1/settings/test-connection", { apiUrl: "https://api.minimax.io/v1/text/chatcompletion_v2" }],
  ["listSettingsHistory", () => api.listSettingsHistory({ category: "execution", page: 1, size: 20 }), "GET", "/api/v1/settings/history?category=execution&page=1&size=20"],

  // ── Phase 4：專案執行（契約 §1.2）──
  ["executeProject", () => api.executeProject("P", { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } }), "POST", "/api/v1/projects/P/execute", { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } }],
  ["listProjectExecutions", () => api.listProjectExecutions("P", { page: 0, size: 1, sort: "startedAt,desc" }), "GET", "/api/v1/projects/P/executions?page=0&size=1&sort=startedAt%2Cdesc"],
  ["getExecution", () => api.getExecution("R"), "GET", "/api/v1/executions/R"],
  ["pauseExecution", () => api.pauseExecution("R"), "POST", "/api/v1/executions/R/pause"],
  ["resumeExecution", () => api.resumeExecution("R"), "POST", "/api/v1/executions/R/resume"],
  ["cancelExecution", () => api.cancelExecution("R"), "POST", "/api/v1/executions/R/cancel"],
  ["listExecutionSteps", () => api.listExecutionSteps("R", { size: 200, afterSeq: 41 }), "GET", "/api/v1/executions/R/steps?size=200&afterSeq=41"],
  ["getExecutionDag", () => api.getExecutionDag("R"), "GET", "/api/v1/executions/R/dag"],
  ["listExecutionCheckpoints", () => api.listExecutionCheckpoints("R"), "GET", "/api/v1/executions/R/checkpoints"],
  ["restoreExecution", () => api.restoreExecution("R", "C"), "POST", "/api/v1/executions/R/restore/C"],
  ["reviewExecution", () => api.reviewExecution("R", "V", { decision: "RETRY", comment: "再試一次" }), "POST", "/api/v1/executions/R/review/V", { decision: "RETRY", comment: "再試一次" }],

  // ── Phase 5：專案監控（契約 §1.3）──
  ["getProjectMetrics", () => api.getProjectMetrics("P", { runId: "R", from: "2026-10-14T00:00:00Z" }), "GET", "/api/v1/monitor/projects/P/metrics?runId=R&from=2026-10-14T00%3A00%3A00Z"],
  ["getTokenTrend", () => api.getTokenTrend("P", { bucket: "HOUR" }), "GET", "/api/v1/monitor/projects/P/token-trend?bucket=HOUR"],
  ["getTaskTrend", () => api.getTaskTrend("P", { bucket: "DAY", runId: "R" }), "GET", "/api/v1/monitor/projects/P/task-trend?bucket=DAY&runId=R"],
  ["listProjectAlerts", () => api.listProjectAlerts("P", { acknowledged: false, limit: 50 }), "GET", "/api/v1/monitor/projects/P/alerts?acknowledged=false&limit=50"],
  ["acknowledgeAlert", () => api.acknowledgeAlert("A"), "POST", "/api/v1/monitor/alerts/A/acknowledge"],
  ["listProjectLogs", () => api.listProjectLogs("P", { level: "ERROR", q: "失敗", order: "desc", page: 0, size: 50 }), "GET", "/api/v1/monitor/projects/P/logs?level=ERROR&q=%E5%A4%B1%E6%95%97&order=desc&page=0&size=50"],
];

/** 不走 JSON 的端點：上傳（multipart）與下載（Blob）。 */
const MULTIPART = ["uploadImport", "importSettings"];
const DOWNLOAD = ["exportSettings", "downloadProjectReport"];

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "");
  resetSessionCache();
  clearSession();
});

function okJson(data: unknown = {}): Response {
  return new Response(JSON.stringify({ code: 200, message: "success", data }), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

describe("endpoints：每個後端端點一個函式", () => {
  it("匯出的函式恰好是 Phase 1～6 對應的 60 個（Phase 1+2 共 22、匯入 9、通知 1、設定 10、執行 11、監控 7；不多不少）", () => {
    const names = [...EXPECTED.map(([name]) => name), ...MULTIPART, ...DOWNLOAD];
    expect(Object.keys(api).sort()).toEqual(names.sort());
    expect(names).toHaveLength(60);
  });

  it.each(EXPECTED)("%s → %s %s", async (_name, call, method, path, body) => {
    const fetchMock = vi.fn(async () => okJson());
    vi.stubGlobal("fetch", fetchMock);
    await call();
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(path);
    expect(init.method).toBe(method);
    if (body === undefined) expect(init.body).toBeUndefined();
    else expect(JSON.parse(String(init.body))).toEqual(body);
  });
});

describe("endpoints：檔案上傳（multipart）與下載（Blob）", () => {
  it.each([
    ["uploadImport", "/api/v1/import/upload", (f: File) => api.uploadImport(f)],
    ["importSettings", "/api/v1/settings/import", (f: File) => api.importSettings(f)],
  ] as const)("%s：以 FormData 欄位 file 送出，且不手設 Content-Type（boundary 由瀏覽器帶）", async (_name, path, call) => {
    const fetchMock = vi.fn(async () => okJson({ id: "I" }));
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["# BRD"], "brd.md", { type: "text/markdown" });
    await call(file);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(path);
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("file")).toBe(file);
    expect((init.headers as Record<string, string>)["Content-Type"]).toBeUndefined();
  });

  it("exportSettings：POST 取回 Blob，檔名取自 Content-Disposition；不解封包", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response('{"version":1,"configs":[]}', {
          status: 200,
          headers: {
            "content-type": "application/json",
            "content-disposition": 'attachment; filename="aisdlc-settings-20261015.json"',
          },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const result = await api.exportSettings();
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/settings/export");
    expect(init.method).toBe("POST");
    expect(result.filename).toBe("aisdlc-settings-20261015.json");
    expect(JSON.parse(await result.blob.text())).toEqual({ version: 1, configs: [] });
  });

  it("downloadProjectReport：GET 取回 CSV Blob，檔名取自 Content-Disposition；Accept 帶 text/csv（契約 §1.3.7），錯誤封包仍可協商", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response("#report,AISDLC", {
          status: 200,
          headers: {
            "content-type": "text/csv; charset=UTF-8",
            "content-disposition": 'attachment; filename="monitor-report-0b8c5d1e-20261015-0840.csv"',
          },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const result = await api.downloadProjectReport("P", { format: "csv", runId: "R", from: "2026-10-14T00:00:00Z" });
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/monitor/projects/P/report?format=csv&runId=R&from=2026-10-14T00%3A00%3A00Z");
    expect(init.method ?? "GET").toBe("GET");
    const accept = (init.headers as Record<string, string>).Accept;
    expect(accept.startsWith("text/csv")).toBe(true);
    expect(accept).toContain("application/json");
    expect(result.filename).toBe("monitor-report-0b8c5d1e-20261015-0840.csv");
    expect(await result.blob.text()).toBe("#report,AISDLC");
  });

  it("downloadProjectReport：PDF 回 501 時照常解成 ApiError（reason 保留，前端據此顯示「尚未提供」）", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ code: 501, message: "尚未提供", reason: "PDF 報表尚未提供（W5）", errors: [], traceId: "tr-501" }), {
            status: 501,
            headers: { "content-type": "application/json" },
          }),
      ),
    );
    const e = (await api.downloadProjectReport("P", { format: "pdf" }).catch((x: unknown) => x)) as { status: number; reason: string };
    expect(e.status).toBe(501);
    expect(e.reason).toBe("PDF 報表尚未提供（W5）");
  });

  it("reviewExecution：204 無本文；SKIP／無還原點的 RETRY 以回應標頭 X-Follow-Up-Run-Id 回傳後續批次 id，其餘回 null", async () => {
    const replies = [
      new Response(null, { status: 204, headers: { "X-Follow-Up-Run-Id": "11111111-2222-4333-8444-555555555555" } }),
      new Response(null, { status: 204 }),
    ];
    vi.stubGlobal("fetch", vi.fn(async () => replies.shift() as Response));
    await expect(api.reviewExecution("R", "V", { decision: "SKIP" })).resolves.toEqual({
      followUpRunId: "11111111-2222-4333-8444-555555555555",
    });
    await expect(api.reviewExecution("R", "V", { decision: "APPROVE", comment: "ok" })).resolves.toEqual({ followUpRunId: null });
  });

  it("加密鍵重置的 confirm 只在需要時才帶（沒帶＝不出現在網址）", async () => {
    const fetchMock = vi.fn(async () => okJson());
    vi.stubGlobal("fetch", fetchMock);
    await api.resetSetting("model", "apiKey");
    await api.resetSetting("model", "apiKey", true);
    const urls = fetchMock.mock.calls.map((c) => (c as unknown as [string])[0]);
    expect(urls).toEqual(["/api/v1/settings/model/apiKey/reset", "/api/v1/settings/model/apiKey/reset?confirm=true"]);
  });
});
