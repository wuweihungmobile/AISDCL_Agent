import { beforeEach, describe, expect, it, vi } from "vitest";

import { clearSession, resetSessionCache, saveSession } from "@/lib/auth/store";
import * as api from "./endpoints";

/** 函式名與 PRD §7.1 的端點一一對應（RTM：API-PRJ／GOL／TSK／SGN／AUTH）。 */
const EXPECTED: Array<[fn: keyof typeof api, call: () => Promise<unknown>, method: string, path: string, body?: unknown]> = [
  ["login", () => api.login("u", "p"), "POST", "/api/v1/auth/login", { username: "u", password: "p" }],
  ["refreshToken", () => api.refreshToken("r"), "POST", "/api/v1/auth/refresh", { refreshToken: "r" }],
  // v1.4（D-19，API-AUTH-03）：登出並撤銷 refresh token（免認證，204）
  ["logout", () => api.logout("RT"), "POST", "/api/v1/auth/logout", { refreshToken: "RT" }],
  ["createProject", () => api.createProject({ name: "n", executionPath: "/x", passCriteria: "c" }), "POST", "/api/v1/projects", { name: "n", executionPath: "/x", passCriteria: "c" }],
  ["listProjects", () => api.listProjects({ page: 1, size: 5 }), "GET", "/api/v1/projects?page=1&size=5"],
  ["getProject", () => api.getProject("P"), "GET", "/api/v1/projects/P"],
  ["updateProject", () => api.updateProject("P", { name: "n2" }), "PUT", "/api/v1/projects/P", { name: "n2" }],
  ["deleteProject", () => api.deleteProject("P"), "DELETE", "/api/v1/projects/P"],
  ["signoffProject", () => api.signoffProject("P", "me"), "POST", "/api/v1/projects/P/signoff", { approver: "me" }],
  // v1.2（C-3，API-PRJ-06）：復原軟刪除的專案（POST，無 body）
  ["restoreProject", () => api.restoreProject("P"), "POST", "/api/v1/projects/P/restore"],
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
  [
    "importText",
    () => api.importText({ content: "# BRD", sourceFileName: "e2e-brd.md", sourceType: "MARKDOWN" }),
    "POST",
    "/api/v1/import/text",
    { content: "# BRD", sourceFileName: "e2e-brd.md", sourceType: "MARKDOWN" },
  ],
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
  // ── v1.4（W7 第二批）：待審批清單（契約 §1.8.1，API-SGN-05）與 AISDLC_SDD 引擎狀態（§1.7.1，API-ENG-01）──
  ["getPendingSignoffs", () => api.getPendingSignoffs({ limit: 50 }), "GET", "/api/v1/signoffs/pending?limit=50"],
  ["getSddEngineStatus", () => api.getSddEngineStatus({ project: "e2e-alpha" }), "GET", "/api/v1/engines/sdd?project=e2e-alpha"],
  // ── v1.5（整合輪 115；契約 §1.10）：核准凍結（API-SGN-06）、編輯 FSM 專案（API-PRJ-08）、執行追溯覆蓋（API-EXE-16）──
  [
    "freezeProjectSddSpec",
    () => api.freezeProjectSddSpec("P", { reason: "規格已走完 SCG-0～3", docs: ["docs/03_testing/contracts/TCS-Alpha.md"] }),
    "POST",
    "/api/v1/projects/P/sdd/freeze",
    { reason: "規格已走完 SCG-0～3", docs: ["docs/03_testing/contracts/TCS-Alpha.md"] },
  ],
  ["updateProjectSddBinding", () => api.updateProjectSddBinding("P", "e2e17-alpha"), "PUT", "/api/v1/projects/P/sdd-binding", { sddProject: "e2e17-alpha" }],
  ["getExecutionRtm", () => api.getExecutionRtm("R"), "GET", "/api/v1/executions/R/rtm"],

  // ── Phase 6：系統參數（契約 §1.5）：匯入是 multipart、匯出是下載，另見下方專屬測試 ──
  ["listSettings", () => api.listSettings(), "GET", "/api/v1/settings"],
  ["listSettingsByCategory", () => api.listSettingsByCategory("model", { reveal: true }), "GET", "/api/v1/settings/model?reveal=true"],
  ["updateSetting", () => api.updateSetting("model", "apiKey", { value: "k", confirm: true }), "PUT", "/api/v1/settings/model/apiKey", { value: "k", confirm: true }],
  [
    "updateTokenGuard",
    () => api.updateTokenGuard({ compactThresholdPct: 70, haltThresholdPct: 95 }),
    "PUT",
    "/api/v1/settings/execution/token-guard",
    { compactThresholdPct: 70, haltThresholdPct: 95 },
  ],
  ["resetSetting", () => api.resetSetting("model", "apiKey", true), "POST", "/api/v1/settings/model/apiKey/reset?confirm=true"],
  ["resetCategory", () => api.resetCategory("execution"), "POST", "/api/v1/settings/execution/reset"],
  [
    "testConnection",
    () => api.testConnection({ apiUrl: "https://api.minimax.io/v1/text/chatcompletion_v2" }),
    "POST",
    "/api/v1/settings/test-connection",
    { apiUrl: "https://api.minimax.io/v1/text/chatcompletion_v2" },
  ],
  ["listSettingsHistory", () => api.listSettingsHistory({ category: "execution", page: 1, size: 20 }), "GET", "/api/v1/settings/history?category=execution&page=1&size=20"],

  // ── Phase 4：專案執行（契約 §1.2）──
  [
    "executeProject",
    () => api.executeProject("P", { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } }),
    "POST",
    "/api/v1/projects/P/execute",
    { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } },
  ],
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
  // v1.2（C-1，API-MON-08）：全域任務總計——from 必填、to 省略＝現在
  ["getTaskTotals", () => api.getTaskTotals({ from: "2026-10-12T00:00:00.000Z" }), "GET", "/api/v1/monitor/task-totals?from=2026-10-12T00%3A00%3A00.000Z"],
  ["listProjectAlerts", () => api.listProjectAlerts("P", { acknowledged: false, limit: 50 }), "GET", "/api/v1/monitor/projects/P/alerts?acknowledged=false&limit=50"],
  ["acknowledgeAlert", () => api.acknowledgeAlert("A"), "POST", "/api/v1/monitor/alerts/A/acknowledge"],
  [
    "listProjectLogs",
    () => api.listProjectLogs("P", { level: "ERROR", q: "失敗", order: "desc", page: 0, size: 50 }),
    "GET",
    "/api/v1/monitor/projects/P/logs?level=ERROR&q=%E5%A4%B1%E6%95%97&order=desc&page=0&size=50",
  ],

  // ── SelfImproving 唯讀鏡像（P1b；TCS-SelfImprovingMirror-P1b R11）：六個 GET，沒有任何寫入函式；`since`、`limit` 為 undefined 時不進網址 ──
  ["getSiStatus", () => api.getSiStatus(), "GET", "/api/v1/si/status"],
  ["getSiObservations", () => api.getSiObservations({ since: 7, limit: 100 }), "GET", "/api/v1/si/observations?since=7&limit=100"],
  ["getSiEvents", () => api.getSiEvents({ limit: 100 }), "GET", "/api/v1/si/events?limit=100"],
  ["getSiProposals", () => api.getSiProposals(), "GET", "/api/v1/si/proposals"],
  ["getSiProposal", () => api.getSiProposal("PROP-SI-004"), "GET", "/api/v1/si/proposals/PROP-SI-004"],
  ["getSiRuns", () => api.getSiRuns({ since: 3 }), "GET", "/api/v1/si/runs?since=3"],

  // ── SelfImproving 寫入載體（P2b；TCS-SelfImprovingDecide-P2b W16）：四個 POST（僅 ADMIN）加一個對帳讀面；本文逐位元組等於呼叫端給的 JSON ──
  [
    "postSiDecide",
    () => api.postSiDecide("PROP-SI-004", { dkind: "reject", digest: `sha256:${"a".repeat(64)}`, reason: "證據不足以判定", reasonClass: "證據不足" }),
    "POST",
    "/api/v1/si/proposals/PROP-SI-004/decide",
    { dkind: "reject", digest: `sha256:${"a".repeat(64)}`, reason: "證據不足以判定", reasonClass: "證據不足" },
  ],
  [
    "postSiObservation",
    () => api.postSiObservation({ context: "情境", symptom: "症狀", evidence: "docs/x.md:1", category: "bug", severity: "P3", face: "產品", externalDerived: false }),
    "POST",
    "/api/v1/si/observations",
    { context: "情境", symptom: "症狀", evidence: "docs/x.md:1", category: "bug", severity: "P3", face: "產品", externalDerived: false },
  ],
  [
    "postSiObservationClose",
    () => api.postSiObservationClose("OBS-SI-005", { terminal: "decided", text: "夾具關閉" }),
    "POST",
    "/api/v1/si/observations/OBS-SI-005/close",
    { terminal: "decided", text: "夾具關閉" },
  ],
  [
    "postSiObservationValidate",
    () => api.postSiObservationValidate({ context: "情境", symptom: "症狀", evidence: "docs/x.md:1", category: "bug", severity: "P3", face: "產品", externalDerived: false }),
    "POST",
    "/api/v1/si/observations/validate",
    { context: "情境", symptom: "症狀", evidence: "docs/x.md:1", category: "bug", severity: "P3", face: "產品", externalDerived: false },
  ],
  ["getSiConsoleWrites", () => api.getSiConsoleWrites({ limit: 100 }), "GET", "/api/v1/si/console-writes?limit=100"],

  // ── 議題中心（TCS-IssueCenter-20261027 §C4）：兩個唯讀 GET 與僅 ADMIN 的優先順序寫入（PUT 設定、DELETE 清除）；中文篩選別名逐字編碼 ──
  [
    "getIssues",
    () => api.getIssues({ status: "待處理", source: "系統缺陷,研究提案", since: 7, limit: 100 }),
    "GET",
    `/api/v1/issues?status=${encodeURIComponent("待處理")}&source=${encodeURIComponent("系統缺陷,研究提案")}&since=7&limit=100`,
  ],
  ["getIssue", () => api.getIssue("PROP-SI-004"), "GET", "/api/v1/issues/PROP-SI-004"],
  ["putIssuePriority", () => api.putIssuePriority("PROP-SI-004", { rank: 3, note: "先做" }), "PUT", "/api/v1/issues/PROP-SI-004/priority", { rank: 3, note: "先做" }],
  ["deleteIssuePriority", () => api.deleteIssuePriority("PROP-SI-004"), "DELETE", "/api/v1/issues/PROP-SI-004/priority"],
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
  it("匯出的函式恰好是 Phase 1～6 對應的 83 個（Phase 1+2 共 23、匯入 9、通知 1、設定 10、執行 11、監控 8，加 v1.4 的登出、待審批清單、SDD 引擎各 1，再加 v1.5 的核准凍結、編輯 FSM 專案、追溯覆蓋各 1，再加 P1b 的六個 getSi*，再加 P2b 的四個 postSi* 與 getSiConsoleWrites，再加議題中心的 getIssues、getIssue、putIssuePriority、deleteIssuePriority；不多不少）", () => {
    const names = [...EXPECTED.map(([name]) => name), ...MULTIPART, ...DOWNLOAD];
    expect(Object.keys(api).sort()).toEqual(names.sort());
    expect(names).toHaveLength(83);
  });

  it("v1.4 的三個端點省略可選參數時，網址上不帶它們（getPendingSignoffs 不帶 limit、getSddEngineStatus 不帶 project 也不帶 projectId）", async () => {
    const fetchMock = vi.fn(async () => okJson());
    vi.stubGlobal("fetch", fetchMock);
    await api.getPendingSignoffs();
    await api.getSddEngineStatus();
    await api.getSddEngineStatus({ project: undefined });
    await api.getSddEngineStatus({ project: undefined, projectId: undefined });
    const urls = fetchMock.mock.calls.map((c) => (c as unknown as [string])[0]);
    expect(urls).toEqual(["/api/v1/signoffs/pending", "/api/v1/engines/sdd", "/api/v1/engines/sdd", "/api/v1/engines/sdd"]);
  });

  it("getSddEngineStatus 的 v1.5 專案模式（契約 §1.10.4）：projectId 單獨＝讀專案根下的有效 FSM 專案；再帶 project＝同一個狀態目錄內改選別的 FSM 專案（原樣編碼，含空白與中文）", async () => {
    const fetchMock = vi.fn(async () => okJson());
    vi.stubGlobal("fetch", fetchMock);
    await api.getSddEngineStatus({ projectId: "0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02" });
    await api.getSddEngineStatus({ projectId: "0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02", project: "我的 專案" });
    const urls = fetchMock.mock.calls.map((c) => (c as unknown as [string])[0]);
    expect(urls).toEqual([
      "/api/v1/engines/sdd?projectId=0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02",
      "/api/v1/engines/sdd?projectId=0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02&project=%E6%88%91%E7%9A%84+%E5%B0%88%E6%A1%88",
    ]);
  });

  it("updateProjectSddBinding：null 原樣送出（清除＝回到「用預設」），不被當成缺值丟掉", async () => {
    const fetchMock = vi.fn(async () => okJson());
    vi.stubGlobal("fetch", fetchMock);
    await api.updateProjectSddBinding("P", null);
    const init = (fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1];
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body as string)).toEqual({ sddProject: null });
  });

  it("logout（契約 §1.9.1）：免認證——即使本機有 session 也不帶 Authorization；204 回 undefined；失敗丟 ApiError（由呼叫端吞掉，不阻擋本機登出）", async () => {
    saveSession({ accessToken: "stale-access", refreshToken: "RT", expiresAt: Date.now() - 1000, role: "OPERATOR", username: "operator" });
    const replies = [
      new Response(null, { status: 204 }),
      new Response(JSON.stringify({ code: 400, message: "請求格式錯誤", errors: [{ field: "refreshToken", message: "不可為空" }] }), { status: 400, headers: { "content-type": "application/json" } }),
    ];
    const fetchMock = vi.fn(async () => replies.shift() as Response);
    vi.stubGlobal("fetch", fetchMock);
    await expect(api.logout("RT")).resolves.toBeUndefined();
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined();
    await expect(api.logout("")).rejects.toMatchObject({ status: 400, errors: [{ field: "refreshToken" }] });
    expect(fetchMock).toHaveBeenCalledTimes(2); // 400 不會觸發換新或重送
  });

  it("listProjects：deleted=true 只列軟刪除的專案（C-3）；省略時網址上沒有 deleted", async () => {
    const fetchMock = vi.fn(async () => okJson());
    vi.stubGlobal("fetch", fetchMock);
    await api.listProjects({ page: 0, size: 10, deleted: true, sort: "updatedAt,desc" });
    await api.listProjects({ page: 0, size: 10 });
    const urls = fetchMock.mock.calls.map((c) => (c as unknown as [string])[0]);
    expect(urls[0]).toBe("/api/v1/projects?page=0&size=10&deleted=true&sort=updatedAt%2Cdesc");
    expect(urls[1]).toBe("/api/v1/projects?page=0&size=10");
  });

  it("getTaskTotals：帶 to 時兩個參數都在網址上（契約 §1.3.8）", async () => {
    const fetchMock = vi.fn(async () => okJson());
    vi.stubGlobal("fetch", fetchMock);
    await api.getTaskTotals({ from: "2026-10-12T00:00:00.000Z", to: "2026-10-15T08:40:00.000Z" });
    const [url] = fetchMock.mock.calls[0] as unknown as [string];
    expect(url).toBe("/api/v1/monitor/task-totals?from=2026-10-12T00%3A00%3A00.000Z&to=2026-10-15T08%3A40%3A00.000Z");
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

  it("downloadProjectReport：PDF 回 200（v1.2，C-4）——Accept 帶 application/pdf（契約 §1.3.7），取回 PDF Blob，檔名取自 Content-Disposition（.pdf）", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response("%PDF-1.7 mock", {
          status: 200,
          headers: {
            "content-type": "application/pdf",
            "content-disposition": 'attachment; filename="monitor-report-0b8c5d1e-20261015-0840.pdf"',
          },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const result = await api.downloadProjectReport("P", { format: "pdf", runId: "R" });
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/monitor/projects/P/report?format=pdf&runId=R");
    const accept = (init.headers as Record<string, string>).Accept;
    expect(accept.startsWith("application/pdf")).toBe(true);
    expect(accept).toContain("application/json"); // 錯誤封包（400／404）仍可協商
    expect(result.filename).toBe("monitor-report-0b8c5d1e-20261015-0840.pdf");
    expect(await result.blob.text()).toBe("%PDF-1.7 mock");
  });

  it("reviewExecution：204 無本文；SKIP／無還原點的 RETRY 以回應標頭 X-Follow-Up-Run-Id 回傳後續批次 id，其餘回 null", async () => {
    const replies = [new Response(null, { status: 204, headers: { "X-Follow-Up-Run-Id": "11111111-2222-4333-8444-555555555555" } }), new Response(null, { status: 204 })];
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => replies.shift() as Response),
    );
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
