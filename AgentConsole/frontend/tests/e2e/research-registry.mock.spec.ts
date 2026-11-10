import { expect, test } from "@playwright/test";

import { ALLOWLIST, CAPABILITIES_LOCAL } from "../fixtures/research/misc";
import { PROJECT_LIST } from "../fixtures/research/projects";
import { REGISTRY_STATUS, WATCH_SOURCES_17 } from "../fixtures/research/registry";
import { collectConsoleErrors, compose, fail, installApiMock, shellHandler, signInAs, type MockHandler } from "./mockApi";

/**
 * 研究來源單一化：非名單 ADMIN 的同步被拒（route mock；TCS-ResearchRegistry-20261110 AT-965-10-E-1；W-R8；AC-R2P-24-10）。
 *
 * 情境：ADMIN 在研究來源設定新增一筆追蹤來源（POST 201），自動同步回 403 `si_write_forbidden`（此帳號不在自我進化寫入名單）。
 * 預期：顯示「此帳號不在自我進化寫入名單，未同步」且沒有重試鈕；狀態列仍是「有變更尚未同步」；清單含新列；同步請求恰一次（403 後不自動重試）。
 * 判定指令：npx playwright test tests/e2e/research-registry.mock.spec.ts -g AT_965_10_E_1（`E2E_MODE=standalone`；cwd＝AgentConsole/frontend）。
 */
test("AT_965_10_E_1 非名單 ADMIN 新增追蹤來源：同步 403 顯示原因、無重試鈕、狀態仍尚未同步、清單含新列、sync 恰一次", async ({ page }) => {
  const errors = collectConsoleErrors(page);
  const rows = WATCH_SOURCES_17();
  const sync: { count: number; adds: number } = { count: 0, adds: 0 };

  const backend: MockHandler = (call) => {
    if (call.path === "/api/v1/research/capabilities" && call.method === "GET") return { data: CAPABILITIES_LOCAL };
    if (call.path === "/api/v1/research/allowlist" && call.method === "GET") return { data: ALLOWLIST };
    if (call.path === "/api/v1/research/projects" && call.method === "GET") return { data: call.query.get("archived") === "true" ? [] : PROJECT_LIST };
    if (call.path === "/api/v1/settings/execution" && call.method === "GET") return { data: [] };
    if (call.path === "/api/v1/research/watch-sources" && call.method === "GET") return { data: rows };
    if (call.path === "/api/v1/research/watch-sources" && call.method === "POST") {
      const body = call.body as { slug: string; url: string; kind: string; extract: string; layer: string; expand: null };
      sync.adds += 1;
      rows.push({
        ...body,
        host: new URL(body.url).host,
        enabled: true,
        hostAllowed: true,
        addedBy: "admin",
        addedAt: "2026-11-10T08:00:00Z",
        disabledBy: null,
        disabledAt: null,
      } as (typeof rows)[number]);
      return { status: 201, data: rows[rows.length - 1] };
    }
    if (call.path === "/api/v1/si/research-registry" && call.method === "GET") return { data: REGISTRY_STATUS("unsynced") };
    if (call.path === "/api/v1/si/research-registry/sync" && call.method === "POST") {
      sync.count += 1;
      return fail(403, { message: "帳號不在寫入名單", reason: "si_write_forbidden" });
    }
    return undefined;
  };

  await signInAs(page, "ADMIN");
  await installApiMock(page, compose(shellHandler(), backend));
  await page.goto("/research");
  await page.getByRole("button", { name: "研究來源設定" }).click();
  const dialog = page.getByRole("dialog", { name: "研究來源設定" });
  const section = dialog.getByTestId("watch-sources-section");
  await expect(section.getByTestId("watch-row")).toHaveCount(17, { timeout: 60_000 });
  await expect(section.getByTestId("registry-status")).toHaveText("有變更尚未同步");

  await section.getByLabel(/識別碼/).fill("mock-new");
  await section.getByLabel(/^網址/).fill("https://www.anthropic.com/news");
  await section.getByLabel(/抓取說明/).fill("最新消息");
  await section.getByRole("button", { name: "新增追蹤來源" }).click();

  await expect(section.getByTestId("registry-sync-message")).toHaveText("此帳號不在自我進化寫入名單，未同步");
  await expect(section.getByRole("button", { name: "重試同步" }), "403 不顯示重試鈕（重試無用）").toHaveCount(0);
  await expect(section.getByRole("button", { name: "同步到自我進化" }), "手動鈕仍保留").toBeEnabled();
  await expect(section.getByTestId("registry-status"), "狀態仍是有變更尚未同步").toHaveText("有變更尚未同步");
  await expect(section.getByTestId("watch-row")).toHaveCount(18);
  await expect(section.getByTestId("watch-row").filter({ hasText: "mock-new" })).toHaveCount(1);

  // 給一點時間，確認 403 之後沒有任何自動重試
  await page.waitForTimeout(2500);
  expect(sync.adds, "POST 追蹤來源恰一次").toBe(1);
  expect(sync.count, "sync 請求恰一次（403 後不自動重試）").toBe(1);
  expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
});
