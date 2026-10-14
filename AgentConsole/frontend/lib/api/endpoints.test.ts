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
];

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "");
  resetSessionCache();
  clearSession();
});

describe("endpoints：每個後端端點一個函式", () => {
  it("匯出的函式恰好是 PRD §7.1 對應的 22 個（不多不少）", () => {
    expect(Object.keys(api).sort()).toEqual(EXPECTED.map(([name]) => name).sort());
    expect(EXPECTED).toHaveLength(22);
  });

  it.each(EXPECTED)("%s → %s %s", async (_name, call, method, path, body) => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ code: 200, message: "success", data: {} }), { status: 200, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    await call();
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(path);
    expect(init.method).toBe(method);
    if (body === undefined) expect(init.body).toBeUndefined();
    else expect(JSON.parse(String(init.body))).toEqual(body);
  });
});
