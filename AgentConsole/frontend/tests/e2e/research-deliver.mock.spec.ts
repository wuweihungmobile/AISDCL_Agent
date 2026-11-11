import { expect, test, type Locator, type Page } from "@playwright/test";

import { ROUTE_ADOPTED } from "../fixtures/research/build";
import { eventPage, EVENTS } from "../fixtures/research/events";
import { R3 } from "../fixtures/research/ids";
import { ALLOWLIST, CAPABILITIES_LOCAL, EVIDENCE, RECORDS_AUDIT, SOURCES } from "../fixtures/research/misc";
import { DELIVERY_OVERVIEW, TRACEABILITY } from "../fixtures/research/p2";
import { detailVariant, flowOf, PROJECT_LIST } from "../fixtures/research/projects";
import { expectNoA11yViolations, RESEARCH_WIDTHS } from "./a11y";
import { collectConsoleErrors, compose, installApiMock, shellHandler, signInAs, type MockHandler } from "./mockApi";

/**
 * 研究工作區步驟 5「交付」（ResearchToPRD P2；TCS-ResearchToPRD-P2-20261107 AT-962-21-8）——deliver mock 版：
 * 1440／1000／600 三個寬度的版面無水平溢出、axe 無 serious／critical 違規、兩個確認框（建立 Tag、建立 PR）的焦點陷阱與歸還。
 * 假後端只回放契約形狀的資料（夾具取自 tests/fixtures/research/p2.ts）；真 Bridge 的 Tag／PR 副作用不在這裡驗（整合 P2 在 Docker 全棧驗）。
 * 判定指令：npx playwright test tests/e2e/research-deliver.mock.spec.ts --output=<各自目錄>（cwd＝AgentConsole/frontend；production 建置形態用 E2E_MODE=standalone）
 */
const BASE = `/api/v1/research/projects/${R3}`;

const LONG_TEXT = "Given 一個很長很長的情境描述 When 使用者在狹窄的視窗開啟追溯表 Then 版面必須自己換行而不是把頁面撐出水平捲軸，".repeat(3);
const LONG_SOURCE = `task:${"t".repeat(80)}／RTM-COVERAGE-${"x".repeat(60)}.yaml`;

/** 全 PASS 的追溯表（含超長摘要與來源）：Tag 鈕可啟用。 */
const TRACE_PASS = {
  ...TRACEABILITY,
  rows: [
    ...TRACEABILITY.rows.map((r) => ({ ...r, unitStatus: "PASS" as const })),
    {
      ac: "AC-R2P-99-1",
      userStory: "US-99",
      gherkinSummary: { given: LONG_TEXT, when: LONG_TEXT, then: LONG_TEXT },
      unitStatus: "PASS" as const,
      e2eStatus: "NOT_RUN" as const,
      lastRunAt: TRACEABILITY.generatedAt,
      source: [LONG_SOURCE, LONG_SOURCE + "-2"],
    },
  ],
  totals: { acTotal: 4, covered: 4, uncovered: 0, frTotal: 2 },
  rtm: { runId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", fullyCovered: true, acPct: 100, advisory: true as const },
};
const READY_OVERVIEW = { ...DELIVERY_OVERVIEW, preconditions: { ...DELIVERY_OVERVIEW.preconditions, releaseReady: true, rtmFull: true } };

/** R3 在步驟 5（流程游標在 deliver、發布待處理）。 */
const deliverProject = () => ({
  ...detailVariant("frozen"),
  flowStep: "deliver" as const,
  flowPhase: "RELEASE_PENDING",
  flowStatus: "IDLE" as const,
  flow: flowOf(R3, "deliver", "RELEASE_PENDING", "IDLE"),
});

function backend(opts: { traceability: unknown; overview: unknown }): MockHandler {
  return (call) => {
    const p = call.path;
    if (call.method !== "GET") return undefined;
    if (p.startsWith("/api/v1/stream/")) return { status: 204 };
    if (p === "/api/v1/research/capabilities") return { data: CAPABILITIES_LOCAL };
    if (p === "/api/v1/research/allowlist") return { data: ALLOWLIST };
    if (p === "/api/v1/research/projects") return { data: PROJECT_LIST };
    if (p === "/api/v1/settings/execution") return { data: [] };
    if (!p.startsWith(`${BASE}`)) return undefined;
    const rest = p.slice(BASE.length);
    if (rest === "") return { data: deliverProject() };
    if (rest === "/events") return { data: eventPage(EVENTS, Number(call.query.get("afterSeq") ?? 0), Number(call.query.get("limit") ?? 500)) };
    if (rest === "/sources") return { data: SOURCES };
    if (rest === "/evidence") return { data: EVIDENCE };
    if (rest === "/records/audit") return { data: RECORDS_AUDIT };
    if (rest === "/route") return { data: ROUTE_ADOPTED };
    if (rest === "/delivery") return { data: opts.overview };
    if (rest === "/delivery/traceability") return { data: opts.traceability };
    return undefined;
  };
}

const overflowOf = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

/** 開框後連按 Tab 都留在框內（焦點陷阱）；Esc 關閉後焦點回到觸發鈕（歸還）。 */
async function expectFocusTrapAndReturn(page: Page, trigger: Locator, dialogId: string) {
  await trigger.focus();
  await trigger.click();
  const dialog = page.getByTestId(dialogId);
  await expect(dialog).toBeVisible();
  for (let i = 0; i < 14; i += 1) {
    await page.keyboard.press("Tab");
    const inside = await page.evaluate((id) => document.activeElement?.closest(`[data-testid="${id}"]`) !== null && document.activeElement?.closest(`[data-testid="${id}"]`) !== undefined, dialogId);
    expect(inside, `${dialogId}：第 ${i + 1} 次 Tab 後焦點仍在對話框內`).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(trigger, `${dialogId}：關閉後焦點回到觸發鈕`).toBeFocused();
}

test.describe("研究工作區步驟 5 交付（mock）", () => {
  test.setTimeout(180_000);

  test("AT_962_21_8 /research/<id>?step=deliver：三個寬度無水平溢出、axe 零 serious／critical；Tag 與 PR 兩個確認框焦點陷阱與歸還", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await signInAs(page, "ADMIN");
    await installApiMock(page, compose(shellHandler(), backend({ traceability: TRACE_PASS, overview: READY_OVERVIEW })));
    await page.setViewportSize({ width: RESEARCH_WIDTHS[0], height: 900 });
    await page.goto(`/research/${R3}?step=deliver`);
    await expect(page.getByTestId("deliver-panel")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("traceability-table")).toBeVisible();
    await expect(page.getByTestId("tag-create")).toBeEnabled();
    await expect(page.getByTestId("pr-create")).toBeEnabled();
    for (const width of RESEARCH_WIDTHS) {
      await page.setViewportSize({ width, height: 900 });
      expect(await overflowOf(page), `步驟 5 ${width} 無水平溢出`).toBeLessThanOrEqual(0);
      await expectNoA11yViolations(page, `研究工作區 步驟 5 ${width}`);
      await expectFocusTrapAndReturn(page, page.getByTestId("tag-create"), "tag-dialog");
      await expectFocusTrapAndReturn(page, page.getByTestId("pr-create"), "pr-dialog");
    }
    // 對話框開著的畫面也零違規（1440）
    await page.setViewportSize({ width: RESEARCH_WIDTHS[0], height: 900 });
    await page.getByTestId("tag-create").click();
    await expect(page.getByTestId("tag-dialog")).toBeVisible();
    await page.getByTestId("tag-name").fill("v1.2");
    await expect(page.getByTestId("tag-submit")).toBeDisabled();
    await expectNoA11yViolations(page, "建立 Tag 對話框（版本號不合）1440");
    await page.keyboard.press("Escape");
    await page.getByTestId("pr-create").click();
    await expect(page.getByTestId("pr-dialog")).toBeVisible();
    await expectNoA11yViolations(page, "建立 PR 對話框 1440");
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("AT_962_21_8 追溯表有紅列（失敗、無覆蓋任務）時：三個寬度無水平溢出、axe 零違規；Tag 鈕停用並列出未覆蓋 AC", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(shellHandler(), backend({ traceability: TRACEABILITY, overview: DELIVERY_OVERVIEW })));
    await page.setViewportSize({ width: RESEARCH_WIDTHS[0], height: 900 });
    await page.goto(`/research/${R3}?step=deliver`);
    await expect(page.getByTestId("deliver-panel")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("tag-create")).toBeDisabled();
    await expect(page.getByTestId("tag-uncovered-list").getByRole("listitem")).toHaveCount(2);
    await expect(page.getByTestId("trace-uncovered")).toContainText("未覆蓋 2");
    for (const width of RESEARCH_WIDTHS) {
      await page.setViewportSize({ width, height: 900 });
      expect(await overflowOf(page), `步驟 5（有紅列）${width} 無水平溢出`).toBeLessThanOrEqual(0);
      await expectNoA11yViolations(page, `研究工作區 步驟 5（有紅列）${width}`);
    }
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });
});
