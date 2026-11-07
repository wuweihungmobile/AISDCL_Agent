import { expect, test } from "@playwright/test";

import { bigDecomposition, buildProject, DECOMPOSITION_DRAFT, DECOMPOSITION_SIGNED, DECOMPOSITION_WITH_TCS, reconcileWith, ROUTE_ADOPTED } from "../fixtures/research/build";
import { eventPage, EVENTS } from "../fixtures/research/events";
import { CONSOLE_PROJECT_ID, R3 } from "../fixtures/research/ids";
import { ALLOWLIST, CAPABILITIES_LOCAL, EVIDENCE, RECORDS_AUDIT, SOURCES } from "../fixtures/research/misc";
import { PROJECT_LIST } from "../fixtures/research/projects";
import { collectConsoleErrors, compose, fail, installApiMock, shellHandler, signInAs, type MockHandler } from "./mockApi";

/**
 * 研究工作區步驟 4 前半（ResearchToPRD P1；TCS-ResearchToPRD-P1-20261107 AT-961-18-1～18-6、25-4）——build mock 版：
 * 觸發拆解→覆蓋矩陣→豁免理由→簽核（停用／啟用）、TCS 草擬啟動前置 409 的呈現、SCR 進行中標籤與停用、重新對帳後相態校正。
 * 假後端只回放契約形狀的資料；真 Bridge 的拆解與簽核副作用不在這裡驗（整合 P1 在 Docker mock E2E 驗）。
 * 判定指令：npx playwright test tests/e2e/research-build-front.mock.spec.ts --output=<各自目錄>（cwd＝AgentConsole/frontend）
 */
const BASE = `/api/v1/research/projects/${R3}`;

type State = { phase: string; status: "IDLE" | "RUNNING" | "WAITING_HUMAN" | "FAILED"; decomposition: unknown; tcsError: boolean; afterReconcile?: string };

function backend(initial: Partial<State> = {}): { handler: MockHandler; state: State } {
  const state: State = { phase: "ROUTED", status: "IDLE", decomposition: null, tcsError: false, ...initial };
  const handler: MockHandler = (call) => {
    const p = call.path;
    if (p === "/api/v1/research/capabilities") return { data: CAPABILITIES_LOCAL };
    if (p === "/api/v1/research/allowlist") return { data: ALLOWLIST };
    if (p === "/api/v1/research/projects") return { data: PROJECT_LIST };
    if (p.startsWith("/api/v1/stream/research/")) return { status: 204 };
    if (call.method === "GET" && p === "/api/v1/settings/execution") return { data: [] };
    if (p === BASE && call.method === "GET") return { data: buildProject(state.phase, state.status) };
    if (p === `${BASE}/events`) return { data: eventPage(EVENTS, 0, 500) };
    if (p === `${BASE}/sources`) return { data: SOURCES };
    if (p === `${BASE}/evidence`) return { data: EVIDENCE };
    if (p === `${BASE}/records/audit`) return { data: RECORDS_AUDIT };
    if (p === `${BASE}/route` && call.method === "GET") return { data: ROUTE_ADOPTED };
    if (p === `${BASE}/decomposition` && call.method === "GET") return { data: state.decomposition };
    if (p === `${BASE}/decomposition` && call.method === "POST") {
      state.decomposition = DECOMPOSITION_DRAFT;
      return { data: DECOMPOSITION_DRAFT };
    }
    if (p === `${BASE}/decomposition/signoff` && call.method === "POST") {
      state.decomposition = DECOMPOSITION_SIGNED;
      return { data: DECOMPOSITION_SIGNED };
    }
    if (p === `${BASE}/stages/tcs-draft` && call.method === "POST") {
      return state.tcsError
        ? fail(409, { message: "前置未成立", reason: "fsm_state_conflict", details: { unmet: ["route_not_succeeded", "decomposition_missing"] } })
        : { status: 202, data: { stageRunId: "run-1", flowPhase: "TCS_DRAFTING", flowStatus: "RUNNING" } };
    }
    if (p === `${BASE}/reconcile` && call.method === "POST") {
      if (state.afterReconcile !== undefined) state.phase = state.afterReconcile;
      return { data: reconcileWith("ok") };
    }
    return undefined;
  };
  return { handler, state };
}

async function open(page: import("@playwright/test").Page, role: "ADMIN" | "OPERATOR" | "VIEWER", b: ReturnType<typeof backend>) {
  const errors = collectConsoleErrors(page);
  await signInAs(page, role);
  const mock = await installApiMock(page, compose(shellHandler(), b.handler));
  await page.goto(`/research/${R3}?step=build`);
  await expect(page.getByTestId("build-front-panel")).toBeVisible({ timeout: 60_000 });
  return { errors, mock };
}

test.describe("研究工作區步驟 4 前半（mock）", () => {
  test.setTimeout(180_000);

  test("AT_961_18_1／18_2 觸發拆解→覆蓋矩陣與兩個未覆蓋 AC→豁免理由逐條填→簽核由停用變啟用→簽核後唯讀", async ({ page }) => {
    const b = backend({ phase: "ROUTED" });
    const { errors, mock } = await open(page, "OPERATOR", b);
    await expect(page.getByTestId("decomposition-empty")).toBeVisible();
    await page.getByRole("button", { name: "觸發拆解" }).click();
    await expect(page.getByTestId("coverage-matrix")).toBeVisible();
    await expect(page.getByTestId("coverage-summary")).toContainText("已覆蓋 3 ／ 共 5");
    await expect(page.getByTestId("uncovered-list").getByRole("listitem")).toHaveCount(2);
    const sign = page.getByRole("button", { name: "簽核" });
    await expect(sign).toBeDisabled();
    await expect(page.getByTestId("signoff-blockers")).toContainText("AC-003-1");
    await page.getByLabel(/豁免理由：AC-003-1/).fill("由上游服務負責，本專案不實作");
    await expect(sign).toBeDisabled();
    await page.getByLabel(/豁免理由：AC-004-1/).fill("屬後續階段");
    await expect(sign).toBeEnabled();
    await sign.click();
    await expect(page.getByTestId("decomposition-signed")).toContainText("簽核者 operator");
    await expect(page.getByRole("button", { name: "簽核" })).toHaveCount(0);
    const post = mock.calls.find((c) => c.method === "POST" && c.path === `${BASE}/decomposition/signoff`);
    expect(post?.body).toEqual({
      waivers: [
        { ac: "AC-003-1", reason: "由上游服務負責，本專案不實作" },
        { ac: "AC-004-1", reason: "屬後續階段" },
      ],
    });
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("AT_961_18_4 TCS 啟動前置未成立的 409：列出後端 unmet 缺項（中文）", async ({ page }) => {
    const b = backend({ phase: "ROUTED", decomposition: DECOMPOSITION_SIGNED, tcsError: true });
    await open(page, "OPERATOR", b);
    await page.getByRole("button", { name: "草擬測試規格" }).click();
    const error = page.getByTestId("tcs-start-error");
    await expect(error).toContainText("分流尚未完成");
    await expect(error).toContainText("尚未觸發拆解");
  });

  test("AT_961_18_4／18_5／25_4 待凍結：路徑與雜湊、前往凍結連結、執行中心停用並說明；重新對帳後相態校正為可開始建置、執行中心連結啟用", async ({ page }) => {
    const b = backend({ phase: "TCS_PENDING", status: "WAITING_HUMAN", decomposition: DECOMPOSITION_WITH_TCS, afterReconcile: "BUILD_READY" });
    await open(page, "OPERATOR", b);
    await expect(page.getByTestId("tcs-facts")).toContainText("TCS-rag-eval-20261107.md");
    await expect(page.getByRole("link", { name: "前往凍結" })).toHaveAttribute("href", `/projects/${CONSOLE_PROJECT_ID}`);
    await expect(page.getByTestId("execute-disabled")).toHaveAttribute("aria-disabled", "true");
    await expect(page.getByTestId("execute-block-reason")).toContainText("測試規格尚未凍結");
    await page.getByRole("button", { name: "重新對帳" }).click();
    await expect(page.getByTestId("build-phase")).toContainText("可開始建置");
    await expect(page.getByTestId("inner-loop-links").getByRole("link", { name: "執行中心" })).toHaveAttribute("href", `/projects/${CONSOLE_PROJECT_ID}/execute`);
  });

  test("AT_961_18_6 SCR 進行中：橫幅、標籤與操作停用；VIEWER 的寫入鈕 title 為權限不足", async ({ page }) => {
    const b = backend({ phase: "SCR_OPEN", decomposition: DECOMPOSITION_DRAFT });
    await open(page, "OPERATOR", b);
    await expect(page.getByTestId("scr-banner")).toContainText("規格變更中");
    await expect(page.getByTestId("scr-badge")).toContainText("SCR 進行中");
    await expect(page.getByRole("button", { name: "簽核" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "草擬測試規格" })).toBeDisabled();
  });

  test("AT_961_18_6 VIEWER：所有寫入控件停用且 title 為權限不足（唯讀角色）", async ({ page }) => {
    const b = backend({ phase: "ROUTED", decomposition: DECOMPOSITION_DRAFT });
    await open(page, "VIEWER", b);
    for (const name of ["簽核", "重新拆解", "草擬測試規格", "重新對帳"]) {
      const button = page.getByRole("button", { name });
      await expect(button, name).toBeDisabled();
      await expect(button, name).toHaveAttribute("title", /權限不足/);
    }
  });

  test("AT_961_18_E_1 大型 PRD（200 AC × 24 task）：矩陣可渲染並切換篩選", async ({ page }) => {
    const b = backend({ phase: "ROUTED", decomposition: bigDecomposition(200, 24) });
    await open(page, "OPERATOR", b);
    await expect(page.getByTestId("coverage-matrix").getByRole("rowheader")).toHaveCount(200);
    await page.getByRole("button", { name: "只看未覆蓋" }).click();
    await expect(page.getByTestId("coverage-matrix").getByRole("rowheader")).toHaveCount(5);
  });
});
