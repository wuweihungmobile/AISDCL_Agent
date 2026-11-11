import { readFileSync } from "node:fs";

import { expect, test, type Page } from "@playwright/test";

import { expectNoA11yViolations, RESEARCH_WIDTHS } from "./a11y";
import { collectConsoleErrors, compose, fail, installApiMock, shellHandler, signInAs, type MockCall, type MockHandler, type MockReply } from "./mockApi";
import { BASE, bigPatch, detailOf, listFixture, OBS, patrolBody, PROP, proposalResponse, REF, whole, type DetailOpts, type Rec } from "./siFlowFixtures";

/**
 * 自我進化核准流程全程可見（TCS-SiFlowVisibility AC-966-16；Console 半第一波）——route mock 版：
 * 後端以 spec 內自帶的 `/api/v1/si/**` 路由替身代替（不打議題端點、不改 mockApi.ts）；唯讀資料取入庫的黃金檔 A.camel.json，
 * 巡邏快照與提案詳情由 siFlowFixtures.ts 產生（前端實際收到的 camelCase；推送狀態與原因白話都放在夾具的 `text` 欄，測試不自建對照表）。
 * 驗真瀏覽器才量得到的事：整條旅程無主控台錯誤、下載檔、三寬度 axe 與橫向溢出、對話框鍵盤與焦點、6000 行 patch 展開不卡死。
 * 一律對 production 建置跑（`E2E_MODE=standalone` 先 `npm run build`）。三寬度取自 a11y.ts 匯出的 RESEARCH_WIDTHS（不另立數字）。
 */
type World = {
  patrol: MockReply;
  detail: Rec;
  /** 待入帳（未入帳）的稽核編號；有值才有對帳列 */
  pending: string[];
  calls: MockCall[];
};

function newWorld(): World {
  return { patrol: { data: patrolBody() }, detail: detailOf(), pending: [], calls: [] };
}

function siBackend(world: World): MockHandler {
  const lists = listFixture();
  return (call) => {
    world.calls.push(call);
    if (call.method !== "GET") return undefined;
    if (call.path === `/api/v1/si/proposals/${PROP}`) return { data: proposalResponse(world.detail) };
    switch (call.path) {
      case "/api/v1/si/status":
        return { data: BASE.status };
      case "/api/v1/si/observations":
        return { data: whole(lists.observations) };
      case "/api/v1/si/proposals":
        return { data: whole(lists.proposals) };
      case "/api/v1/si/events":
        return { data: whole(BASE.events) };
      case "/api/v1/si/runs":
        return { data: whole(BASE.runs) };
      case "/api/v1/si/patrol":
        return world.patrol;
      case "/api/v1/si/console-writes":
        return {
          data: {
            items: world.pending.map((auditRef) => ({
              auditRef,
              kind: "run-request",
              dkind: null,
              user: "admin",
              role: "ADMIN",
              time: "2026-11-11T14:00:00+08:00",
              subjectId: null,
              digest: null,
              keyId: "f076edf0",
              ingested: false,
              supersededBy: null,
            })),
            truncated: false,
            orphans: [],
            reconcile: { status: "ok", reason: null, backfilled: 0 },
          },
        };
      default:
        return undefined;
    }
  };
}

async function open(page: Page, world: World = newWorld(), role: "ADMIN" | "VIEWER" = "ADMIN") {
  const errors = collectConsoleErrors(page);
  await installApiMock(page, compose(siBackend(world), shellHandler()));
  await signInAs(page, role, role.toLowerCase());
  await page.goto("/self-improving");
  await expect(page.getByTestId("si-patrol-card")).toBeVisible();
  return { errors, world };
}

const detailButton = (page: Page) => page.getByTestId(`si-detail-open-${PROP}`);

/** 切到提案分頁、按「詳情」，回傳對話框。 */
async function openDetail(page: Page) {
  await page.getByRole("tab", { name: /^提案/ }).click();
  await detailButton(page).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByTestId("si-next-step")).toBeVisible();
  return dialog;
}

/** 整頁與指定區塊都不得橫向溢出（diff 長行的捲動限於其內部容器）。 */
async function expectNoOverflow(page: Page, label: string, selectors: string[]) {
  const doc = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
  expect(doc.sw, `${label}：整頁橫向溢出（scrollWidth ${doc.sw} > clientWidth ${doc.cw}）`).toBeLessThanOrEqual(doc.cw);
  for (const selector of selectors) {
    const box = await page
      .locator(selector)
      .first()
      .evaluate((el) => ({ sw: el.scrollWidth, cw: el.clientWidth }));
    expect(box.sw, `${label}：${selector} 橫向溢出（scrollWidth ${box.sw} > clientWidth ${box.cw}）`).toBeLessThanOrEqual(box.cw);
  }
}

async function setWidth(page: Page, width: number) {
  await page.setViewportSize({ width, height: 900 });
}

test("AT_966_16_1 旅程：巡邏卡→詳情→五分頁→展開全部→下載 patch→來源觀察跳轉→關閉；無主控台錯誤、零非 GET", async ({ page }) => {
  const world = newWorld();
  const long = bigPatch(450); // 超過 400 行視窗，才有「展開全部」
  world.detail = detailOf({ patch: long });
  const { errors } = await open(page, world);

  // 巡邏卡：新鮮快照，上次心跳 N 分鐘前
  await expect(page.getByTestId("si-patrol-card")).toContainText(/上次心跳：\s*\d+\s*分鐘前/);
  await expect(page.getByTestId("si-patrol-stale")).toHaveCount(0);

  const dialog = await openDetail(page);
  await expect(dialog).toContainText(`提案詳情 ${PROP}`);
  for (const name of ["卡面", "變更內容", "提案本文", "評估集與驗證", "時間線"]) {
    await dialog.getByRole("tab", { name }).click();
    await expect(dialog.getByRole("tab", { name })).toHaveAttribute("aria-selected", "true");
  }

  // 變更內容：展開全部、下載
  await dialog.getByRole("tab", { name: "變更內容" }).click();
  await expect(dialog.getByTestId("si-diff-view")).toBeVisible();
  const before = await dialog.locator("[data-diff-kind]").count();
  await dialog.getByTestId("si-diff-expand").click();
  await expect.poll(() => dialog.locator("[data-diff-kind]").count()).toBeGreaterThan(before);
  const [download] = await Promise.all([page.waitForEvent("download"), dialog.getByTestId("si-diff-download").click()]);
  expect(download.suggestedFilename()).toBe(`${PROP}-r2.patch`);
  const savedPath = await download.path();
  expect(readFileSync(savedPath, "utf-8")).toBe(long);

  // 提案本文：來源觀察跳轉（對話框關閉、切到觀察分頁、目標列高亮並取得焦點）
  await dialog.getByRole("tab", { name: "提案本文" }).click();
  await dialog.getByRole("button", { name: `看觀察 ${OBS}` }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  const row = page.getByTestId(`si-obs-row-${OBS}`);
  await expect(row).toHaveAttribute("data-highlight", "true");
  await expect(row).toBeFocused();

  // 再開再關（Esc）
  await page.getByRole("tab", { name: /^提案/ }).click();
  await detailButton(page).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);

  const writes = world.calls.filter((c) => c.method !== "GET" && c.path.startsWith("/api/v1/si/"));
  expect(writes, "不得有任何非 GET 的 /api/v1/si/ 請求").toEqual([]);
  expect(
    world.calls.filter((c) => c.path.startsWith("/api/v1/issues")),
    "本鍵不打議題端點",
  ).toEqual([]);
  expect(errors, "主控台錯誤").toEqual([]);
});

/** 巡邏卡的四種畫面＋兩種內容：新鮮、含「為什麼沒有啟動運轉」與推送 blocked、過時、缺席、未掛載。 */
const PATROL_SCENARIOS: Array<{ name: string; patrol: () => MockReply; expectTestId: string; expectStale?: boolean }> = [
  { name: "巡邏卡 新鮮", patrol: () => ({ data: patrolBody() }), expectTestId: "si-patrol-header" },
  { name: "巡邏卡 為什麼沒有啟動運轉與推送 blocked", patrol: () => ({ data: patrolBody({ rich: true }) }), expectTestId: "si-patrol-push-text" },
  { name: "巡邏卡 過時警示", patrol: () => ({ data: patrolBody({ minutesAgo: 40 }) }), expectTestId: "si-patrol-stale", expectStale: true },
  {
    name: "巡邏卡 缺席（report_missing）",
    patrol: () => fail(503, { message: "SI 資料面不可用", reason: "si_unavailable", details: { cause: "report_missing", detail: "patrol.json 不存在" } }),
    expectTestId: "si-patrol-missing",
  },
  {
    name: "巡邏卡 未掛載（report_dir_unset）",
    patrol: () => fail(503, { message: "SI 資料面不可用", reason: "si_unavailable", details: { cause: "report_dir_unset", detail: "BRIDGE_SI_REPORT_DIR 未設" } }),
    expectTestId: "si-patrol-unmounted",
  },
];

test("AT_966_16_2 三寬度（RESEARCH_WIDTHS 同源）axe 零違規且無橫向溢出：巡邏卡五情境、詳情三分頁、ADMIN 寫入面板含拒收原因列", async ({ page }) => {
  test.setTimeout(420_000);
  const world = newWorld();
  const { errors } = await open(page, world);
  expect(RESEARCH_WIDTHS).toEqual([1440, 1000, 600]);

  // 一、巡邏卡五情境（改回放內容後重載，等該情境的特徵節點出現才掃）
  for (const scenario of PATROL_SCENARIOS) {
    world.patrol = scenario.patrol();
    await page.reload();
    await expect(page.getByTestId(scenario.expectTestId)).toBeVisible();
    for (const width of RESEARCH_WIDTHS) {
      await setWidth(page, width);
      await expectNoA11yViolations(page, `${scenario.name} ${width}`);
      await expectNoOverflow(page, `${scenario.name} ${width}`, ['[data-testid="si-patrol-card"]']);
    }
    await setWidth(page, RESEARCH_WIDTHS[0]);
  }
  // 過時警示的文字意義確實出現在畫面（對比由 axe 的 color-contrast 負責）
  world.patrol = { data: patrolBody({ minutesAgo: 40 }) };
  await page.reload();
  await expect(page.getByTestId("si-patrol-stale")).toContainText("巡邏可能沒在跑");

  // 二、詳情對話框：變更內容（400 行視窗與展開）、評估集與驗證（低於下限警示）、時間線
  world.patrol = { data: patrolBody() };
  const dialogScenarios: Array<{ name: string; opts: DetailOpts; tab: string; waitTestId: string; expand?: boolean }> = [
    { name: "詳情 變更內容（400 行視窗）", opts: { patch: bigPatch(450, true) }, tab: "變更內容", waitTestId: "si-diff-view" },
    { name: "詳情 變更內容（展開全部）", opts: { patch: bigPatch(450, true) }, tab: "變更內容", waitTestId: "si-diff-view", expand: true },
    { name: "詳情 評估集與驗證（低於下限）", opts: { belowMin: true }, tab: "評估集與驗證", waitTestId: "si-heldout-warning" },
    { name: "詳情 時間線", opts: {}, tab: "時間線", waitTestId: "si-timeline-table" },
  ];
  for (const scenario of dialogScenarios) {
    world.detail = detailOf(scenario.opts);
    for (const width of RESEARCH_WIDTHS) {
      await setWidth(page, width);
      await page.reload();
      const dialog = await openDetail(page);
      await dialog.getByRole("tab", { name: scenario.tab }).click();
      await expect(dialog.getByTestId(scenario.waitTestId)).toBeVisible();
      if (scenario.expand) {
        await dialog.getByTestId("si-diff-expand").click();
        await expect(dialog.getByTestId("si-diff-expand")).toHaveAttribute("aria-expanded", "true");
      }
      await expectNoA11yViolations(page, `${scenario.name} ${width}`);
      await expectNoOverflow(page, `${scenario.name} ${width}`, ['[role="dialog"]']);
      await page.keyboard.press("Escape");
      await expect(page.getByRole("dialog")).toHaveCount(0);
    }
  }

  // 三、ADMIN 寫入面板含拒收原因列（待入帳列對照快照 ingest[]）
  world.detail = detailOf();
  world.pending = [REF(1)];
  world.patrol = { data: patrolBody({ ingestRef: REF(1) }) };
  await setWidth(page, RESEARCH_WIDTHS[0]);
  await page.reload();
  const panel = page.getByTestId("si-writes-panel");
  await expect(panel).toBeVisible();
  await expect(panel.getByTestId("si-ingest-outcome")).toContainText("這個要求的格式不對，主機拒收了");
  for (const width of RESEARCH_WIDTHS) {
    await setWidth(page, width);
    await expectNoA11yViolations(page, `ADMIN 寫入面板（拒收原因列） ${width}`);
    await expectNoOverflow(page, `ADMIN 寫入面板 ${width}`, ['[data-testid="si-writes-panel"]']);
  }
  expect(errors, "主控台錯誤").toEqual([]);
});

test("AT_966_16_3 對話框鍵盤與焦點：Tab／Shift+Tab 循環不逃出、方向鍵切分頁、Esc 關閉且焦點回到「詳情」鈕", async ({ page }) => {
  await open(page);
  const dialog = await openDetail(page);
  const inside = () => dialog.evaluate((el) => el.contains(document.activeElement));
  const activeId = () =>
    page.evaluate(() => `${document.activeElement?.tagName}|${document.activeElement?.getAttribute("data-testid") ?? ""}|${document.activeElement?.textContent?.slice(0, 20) ?? ""}`);

  // Tab 循環：連按 60 次焦點永遠在對話框內，且序列會回到先前出現過的元素（＝繞了一圈）
  for (const key of ["Tab", "Shift+Tab"]) {
    const seen: string[] = [];
    let wrapped = false;
    for (let i = 0; i < 60; i++) {
      await page.keyboard.press(key);
      expect(await inside(), `${key} 第 ${i + 1} 次焦點逃出對話框`).toBe(true);
      const id = await activeId();
      if (seen.includes(id)) wrapped = true;
      seen.push(id);
    }
    expect(wrapped, `${key} 走完一圈沒有回到先前的元素`).toBe(true);
  }
  // 背景不可聚焦：對話框外的巡邏卡按鈕不會取得焦點（上面的 inside 斷言已涵蓋；另確認背景被隱藏於輔助技術）
  const hidden = await page.getByTestId("si-patrol-steps-toggle").evaluate((el) => el.closest('[aria-hidden="true"],[inert]') !== null);
  expect(hidden, "對話框開啟時背景（巡邏卡）須對輔助技術隱藏").toBe(true);

  // 方向鍵切分頁
  const tabs = dialog.getByRole("tablist", { name: "提案詳情分頁" });
  await tabs.getByRole("tab", { name: "卡面" }).click();
  await tabs.getByRole("tab", { name: "卡面" }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(tabs.getByRole("tab", { name: "變更內容" })).toHaveAttribute("aria-selected", "true");
  await page.keyboard.press("ArrowLeft");
  await expect(tabs.getByRole("tab", { name: "卡面" })).toHaveAttribute("aria-selected", "true");

  // Esc 關閉、焦點回到觸發的「詳情」鈕
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(detailButton(page)).toBeFocused();
});

test("AT_966_16_E_1 超大 patch（約 6000 行、256 KiB）：展開全部 5 秒內完成可捲動、axe 零違規、頁面不卡死、Esc 仍可關", async ({ page }) => {
  test.setTimeout(240_000);
  const world = newWorld();
  const huge = bigPatch(6000);
  expect(Buffer.byteLength(huge), "夾具約 256 KiB").toBeGreaterThan(200 * 1024);
  world.detail = detailOf({ patch: huge });
  await open(page, world);
  const dialog = await openDetail(page);
  await dialog.getByRole("tab", { name: "變更內容" }).click();
  await expect(dialog.getByTestId("si-diff-view")).toBeVisible();

  const started = Date.now();
  await dialog.getByTestId("si-diff-expand").click();
  await expect.poll(() => dialog.locator("[data-diff-kind]").count(), { timeout: 5000 }).toBeGreaterThan(5000);
  expect(Date.now() - started, "展開全部須在 5 秒內完成").toBeLessThan(5000);

  // 頁面沒有無回應：展開後立即執行簡單運算須在 1 秒內回傳
  const t0 = Date.now();
  await expect.poll(() => page.evaluate(() => 1 + 1), { timeout: 1000 }).toBe(2);
  expect(Date.now() - t0).toBeLessThan(1000);

  // 可捲動：內部容器的 scrollHeight 或 scrollWidth 大於可視
  const scrollable = await dialog
    .getByTestId("si-diff-lines")
    .evaluate((el) => el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth || (el.closest("[class*='overflow-y']")?.scrollHeight ?? 0) > 0);
  expect(scrollable).toBe(true);

  await expectNoA11yViolations(page, "詳情 變更內容 展開全部（6000 行）");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
