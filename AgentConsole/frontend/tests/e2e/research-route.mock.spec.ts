import { expect, test } from "@playwright/test";

import { eventPage, EVENTS } from "../fixtures/research/events";
import { R3 } from "../fixtures/research/ids";
import { ALLOWLIST, EVIDENCE, RECORDS_AUDIT, SOURCES } from "../fixtures/research/misc";
import { detailVariant, PROJECT_LIST } from "../fixtures/research/projects";
import { CAPABILITIES_ROUTE_READY, CAPABILITIES_ROUTE_VARIANTS, PREVIEW_A, PREVIEW_B, ROUTE_SUCCEEDED } from "../fixtures/research/route";
import { expectNoA11yViolations } from "./a11y";
import { collectConsoleErrors, compose, fail, installApiMock, shellHandler, signInAs, type MockHandler } from "./mockApi";

/**
 * 研究工作區步驟 3「分流」（ResearchToPRD P1；TCS-ResearchToPRD-P1-20261107 AT-961-17-1、17-4～17-6、16-5、22-7）——route mock 版：
 * 三段流程（選卡填參數→預演→確認）、capabilities 停用規則、Public 確認、差異警示與理由、確認後的完成摘要。
 * 假後端只回放契約形狀的資料；真 git 與真 gh 的副作用不在這裡驗（整合 P1 在拋棄式 clone 與假 gh 上驗）。
 * 判定指令：npx playwright test tests/e2e/research-route.mock.spec.ts --output=<各自目錄>（cwd＝AgentConsole/frontend）
 */
const BASE = `/api/v1/research/projects/${R3}`;

function backend(opts: { caps?: object; targetScope?: string; onRoute?: () => void } = {}): { handler: MockHandler; state: { route: unknown } } {
  const state: { route: unknown } = { route: null };
  const detail = detailVariant("frozen", { targetScope: opts.targetScope ?? "AISDLC_MODULE" });
  const handler: MockHandler = (call) => {
    const p = call.path;
    if (p === "/api/v1/research/capabilities") return { data: opts.caps ?? CAPABILITIES_ROUTE_READY };
    if (p === "/api/v1/research/allowlist") return { data: ALLOWLIST };
    if (p === "/api/v1/research/projects") return { data: PROJECT_LIST };
    if (p.startsWith("/api/v1/stream/research/")) return { status: 204 };
    if (call.method === "GET" && p === "/api/v1/settings/execution") return { data: [] };
    if (p === BASE && call.method === "GET") return { data: detail };
    if (p === `${BASE}/events`) return { data: eventPage(EVENTS, 0, 500) };
    if (p === `${BASE}/sources`) return { data: SOURCES };
    if (p === `${BASE}/evidence`) return { data: EVIDENCE };
    if (p === `${BASE}/records/audit`) return { data: RECORDS_AUDIT };
    if (p === `${BASE}/route` && call.method === "GET") return { data: state.route };
    if (p === `${BASE}/route/preview` && call.method === "POST") {
      const body = call.body as { track?: string };
      return { data: body.track === "B" ? PREVIEW_B : PREVIEW_A };
    }
    if (p === `${BASE}/route` && call.method === "POST") {
      opts.onRoute?.();
      state.route = ROUTE_SUCCEEDED;
      return { data: ROUTE_SUCCEEDED };
    }
    return undefined;
  };
  return { handler, state };
}

async function open(page: import("@playwright/test").Page, role: "ADMIN" | "OPERATOR" | "VIEWER", b: ReturnType<typeof backend>) {
  const errors = collectConsoleErrors(page);
  await signInAs(page, role);
  const mock = await installApiMock(page, compose(shellHandler(), b.handler));
  await page.goto(`/research/${R3}?step=route`);
  await expect(page.getByTestId("route-panel")).toBeVisible({ timeout: 60_000 });
  return { errors, mock };
}

test.describe("研究工作區步驟 3 分流（mock）", () => {
  test.setTimeout(180_000);

  test("AT_961_17_5 三段流程：抽屜自動開啟→選卡 A→預演（零副作用）→ADMIN 確認→完成摘要與前往下一步；預演前確認停用", async ({ page }) => {
    let routePosts = 0;
    const b = backend({ targetScope: "AISDLC_MODULE", onRoute: () => (routePosts += 1) });
    const { errors, mock } = await open(page, "ADMIN", b);
    const dialog = page.getByRole("dialog", { name: "分流精靈" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("radio", { name: /軌道 A/ })).toHaveAttribute("aria-checked", "true");
    await expect(dialog.getByRole("button", { name: "確認執行" })).toBeDisabled();
    await dialog.getByRole("button", { name: "預演" }).click();
    await expect(dialog.getByTestId("route-actions")).toBeVisible();
    expect(routePosts, "預演沒有觸發確認").toBe(0);
    expect(mock.calls.filter((c) => c.method === "POST" && c.path.endsWith("/route/preview"))).toHaveLength(1);
    await expect(dialog.getByRole("button", { name: "確認執行" })).toBeEnabled();
    await dialog.getByRole("button", { name: "確認執行" }).click();
    await expect(page.getByTestId("route-summary")).toBeVisible();
    await expect(page.getByRole("link", { name: "前往拆解與執行" })).toHaveAttribute("href", `/research/${R3}?step=build`);
    expect(routePosts).toBe(1);
    const post = mock.calls.find((c) => c.method === "POST" && c.path === `${BASE}/route`);
    expect(post?.body).toMatchObject({ track: "A", targetModule: expect.any(String), baseRef: "main" });
    expect(post?.body as Record<string, unknown>).not.toHaveProperty("approver");
    expect(post?.body as Record<string, unknown>).not.toHaveProperty("targetPath");
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("AT_961_17_6 差異警示與理由必填、Public 需輸入庫名確認（AT_961_17_4）：軌道 B 與 PRD 不同時理由 0 字停用、1 字啟用；Public 確認名差一字元停用", async ({ page }) => {
    const b = backend({ targetScope: "AISDLC_MODULE" });
    await open(page, "ADMIN", b);
    const dialog = page.getByRole("dialog", { name: "分流精靈" });
    await dialog.getByRole("radio", { name: /軌道 B/ }).click();
    await dialog.getByLabel(/^專案名稱/).fill("demo-app");
    await expect(dialog.getByTestId("scope-differs")).toContainText("軌道 B：獨立專案");
    await expect(dialog.getByRole("button", { name: "預演" })).toBeDisabled();
    await dialog.getByLabel(/差異理由/).fill("本需求是獨立產品");
    await expect(dialog.getByRole("button", { name: "預演" })).toBeEnabled();
    await dialog.getByRole("combobox", { name: /可見度/ }).selectOption("PUBLIC");
    await expect(dialog.getByTestId("public-repo-confirm")).toContainText("PRD 與證據矩陣將公開");
    await expect(dialog.getByRole("button", { name: "預演" })).toBeDisabled();
    await dialog.getByLabel(/重新輸入庫名/).fill("demo-ap");
    await expect(dialog.getByRole("button", { name: "預演" })).toBeDisabled();
    await dialog.getByLabel(/重新輸入庫名/).fill("demo-app");
    await expect(dialog.getByRole("button", { name: "預演" })).toBeEnabled();
    await dialog.getByRole("button", { name: "預演" }).click();
    await expect(dialog.getByTestId("route-actions").getByText("外部系統")).toBeVisible();
  });

  test("AT_961_16_5 capabilities 缺項停用：容器模式兩卡皆停用並說明；缺 gh 只停 GitHub 勾選", async ({ page }) => {
    const mockOnly = backend({ caps: CAPABILITIES_ROUTE_VARIANTS.mockOnly });
    await open(page, "ADMIN", mockOnly);
    const dialog = page.getByRole("dialog", { name: "分流精靈" });
    await expect(dialog.getByRole("radio", { name: /軌道 A/ })).toBeDisabled();
    await expect(dialog.getByRole("radio", { name: /軌道 B/ })).toBeDisabled();
    await expect(dialog.getByTestId("route-card-a-disabled")).toContainText("容器模式只跑 mock claude 的驗收；真分流限本機模式");
    await expect(dialog.getByRole("button", { name: "確認執行" })).toBeDisabled();
  });

  test("AT_961_16_5 缺 gh：本地骨架仍可選，「建立 GitHub 遠端」勾選停用並說明", async ({ page }) => {
    const noGh = backend({ caps: CAPABILITIES_ROUTE_VARIANTS.noGh, targetScope: "STANDALONE_PROJECT" });
    await open(page, "OPERATOR", noGh);
    const dialog = page.getByRole("dialog", { name: "分流精靈" });
    await expect(dialog.getByRole("radio", { name: /軌道 B/ })).toHaveAttribute("aria-checked", "true");
    await expect(dialog.getByRole("checkbox", { name: "建立 GitHub 遠端" })).toBeDisabled();
    await expect(dialog.getByTestId("github-disabled")).toContainText("找不到 gh");
    // OPERATOR：確認停用且說明僅 ADMIN
    await expect(dialog.getByRole("button", { name: "確認執行" })).toBeDisabled();
    await expect(dialog.getByRole("button", { name: "確認執行" })).toHaveAttribute("title", /權限不足/);
  });

  test("AT_961_17_6 VIEWER：不自動彈出抽屜、所有寫入控件停用且 title 為權限不足（唯讀角色）", async ({ page }) => {
    const b = backend();
    await open(page, "VIEWER", b);
    await expect(page.getByRole("dialog")).toHaveCount(0);
    const reopen = page.getByRole("button", { name: "重新開啟分流精靈" });
    await expect(reopen).toBeDisabled();
    await expect(reopen).toHaveAttribute("title", "權限不足（唯讀角色）");
  });

  test("AT_961_17_8 預演 422 route_unsupported_in_deployment：缺項以中文顯示，不顯示動作清單", async ({ page }) => {
    const b = backend();
    const base = b.handler;
    const handler: MockHandler = (call) =>
      call.method === "POST" && call.path === `${BASE}/route/preview`
        ? fail(422, { message: "不支援", reason: "route_unsupported_in_deployment", details: { missing: [{ item: "gh" }, { item: "repo_writable" }] } })
        : base(call);
    const errors = collectConsoleErrors(page);
    await signInAs(page, "ADMIN");
    await installApiMock(page, compose(shellHandler(), handler));
    await page.goto(`/research/${R3}?step=route`);
    const dialog = page.getByRole("dialog", { name: "分流精靈" });
    await dialog.getByRole("button", { name: "預演" }).click();
    await expect(dialog.getByTestId("route-missing")).toContainText("gh 命令不可用");
    await expect(dialog.getByTestId("route-missing")).toContainText("無法寫入程式庫");
    await expect(dialog.getByTestId("route-actions")).toHaveCount(0);
    void errors;
  });

  test("AT_961_22_7 抽屜焦點與無障礙：Esc 關閉後焦點回到「重新開啟分流精靈」；三個寬度零違規、無水平溢出", async ({ page }) => {
    const b = backend({ targetScope: "AISDLC_MODULE" });
    const { errors } = await open(page, "ADMIN", b);
    const dialog = page.getByRole("dialog", { name: "分流精靈" });
    await expect(dialog).toBeVisible();
    for (const width of [1440, 1000, 600]) {
      await page.setViewportSize({ width, height: 900 });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, `寬度 ${width} 無水平溢出`).toBeLessThanOrEqual(0);
      await expectNoA11yViolations(page, `分流精靈抽屜 ${width}`);
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    const reopen = page.getByRole("button", { name: "重新開啟分流精靈" });
    await reopen.focus();
    await page.keyboard.press("Enter");
    await expect(dialog).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(reopen).toBeFocused();
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });
});
