import { expect, test, type Locator } from "@playwright/test";

import { axeViolations, expectNoA11yViolations, formatViolations } from "./a11y";
import { collectConsoleErrors, compose, installApiMock, shellHandler, signInAs, type MockHandler } from "./mockApi";

/**
 * 系統管理／資料庫備份（TCS-SysAdminBackup-20261027 AT-BK-01-2-E-2；R-BK-02、R-BK-03）——route mock 版：以 VIEWER 登入，左列有「系統管理」且點擊後網址為 /sysadmin；
 * 再點入口卡進 /sysadmin/backup；兩個畫面左列 active 都是「系統管理」（aria-current）；頁面沒有任何寫入請求（沒有 POST、PUT、DELETE）。
 * 後端以 spec 內自帶的 `/api/v1/sysadmin/backups` 路由代替（不改 mockApi.ts，TCS §5.2）。
 * 版面細節（卡片、清單、排程、說明區的文字）由元件測試（BackupView.test.tsx 等）以 getByRole／testid 逐項驗；這裡驗真瀏覽器才量得到的東西——
 * 導覽 active、路由換頁、色彩對比（axe 掃描，沿 a11y.ts；WCAG 2.0／2.1 A／AA）與瀏覽器主控台沒有 React 警告。
 */
const card = (job: string, patch: Record<string, unknown> = {}) => ({
  job,
  status: "succeeded",
  trigger: "scheduled",
  startedAt: "2026-10-26T18:00:00Z",
  finishedAt: "2026-10-26T18:10:00Z",
  durationSeconds: 600,
  lastSuccessAt: "2026-10-26T18:10:00Z",
  lastDueAt: "2026-10-26T18:00:00Z",
  overdue: false,
  never: false,
  reason: null,
  ...(job === "full" || job === "diff" ? { latestBackup: { label: "20261026-020002F", finishedAt: "2026-10-25T18:12:00Z", source: "pgbackrest" } } : {}),
  ...patch,
});

/** 一份完整、健康的總覽（API 形；VIEWER 沒有 detailTail、requestedBy 兩個鍵）。 */
const OVERVIEW = {
  control: { available: true, canTrigger: false, reason: null, heartbeatAgeSeconds: 5, exportAgeSeconds: 12, exportGeneratedAt: "2026-10-27T06:39:08Z", warnings: [] },
  timezone: "Asia/Taipei",
  activeJob: null,
  cards: [
    card("full"),
    card("diff", { status: "failed", trigger: "scheduled", reason: "script_failed" }),
    card("dump"),
    card("verify", { status: "no_run", trigger: null, startedAt: null, finishedAt: null, durationSeconds: null, lastSuccessAt: null, never: true }),
  ],
  backups: [
    {
      kind: "diff",
      label: "20261026-020000F_20261027-020000D",
      location: "repo1",
      startedAt: "2026-10-26T18:00:00Z",
      finishedAt: "2026-10-26T18:02:00Z",
      durationSeconds: 120,
      databaseSizeBytes: 33619968,
      repoSizeBytes: 524288,
      baseLabel: "20261026-020000F",
      result: "ok_with_errors",
    },
    {
      kind: "full",
      label: "20261026-020000F",
      location: "repo1",
      startedAt: "2026-10-25T18:00:00Z",
      finishedAt: "2026-10-25T18:10:00Z",
      durationSeconds: 600,
      databaseSizeBytes: 33554432,
      repoSizeBytes: 4194304,
      baseLabel: null,
      result: "ok",
    },
    {
      kind: "logical",
      label: "aisdlc-20261025-183000.dump",
      location: "logical",
      startedAt: null,
      finishedAt: "2026-10-25T18:30:05Z",
      durationSeconds: null,
      databaseSizeBytes: null,
      repoSizeBytes: 1048576,
      baseLabel: null,
      result: "ok",
    },
  ],
  schedule: {
    entries: [
      { job: "full", cron: "0 2 * * 0", nextRunAt: "2026-10-31T18:00:00Z" },
      { job: "diff", cron: "0 2 * * 1-6", nextRunAt: "2026-10-27T18:00:00Z" },
      { job: "dump", cron: "30 2 * * *", nextRunAt: "2026-10-27T18:30:00Z" },
      { job: "verify", cron: "0 4 * * 3", nextRunAt: "2026-10-27T20:00:00Z" },
      { job: "expire", cron: "0 3 * * *", nextRunAt: "2026-10-27T19:00:00Z" },
      { job: "wal_clean", cron: "30 3 * * *", nextRunAt: "2026-10-27T19:30:00Z" },
    ],
    retention: { repo1: { full: 4, diff: 7 }, repo2: { full: 4, diff: null }, logicalDays: 28 },
  },
  repos: [
    { repo: 1, endpointHost: null, local: true, statusCode: 0, statusMessage: "ok" },
    { repo: 2, endpointHost: "minio", local: true, statusCode: 0, statusMessage: "ok" },
  ],
  walArchive: { lastArchivedAt: "2026-10-27T02:15:00Z", failedCount: 0, lastFailedAt: null },
};

/**
 * 48 行的輸出尾段：遠超過 `max-h-48`（12rem＝192px）的可見高度，輸出尾段的 pre 才真的「可捲」。
 * 為什麼要長資料：axe 的 scrollable-region-focusable 只檢查真的可捲的容器；短資料（VIEWER 沒有尾段、清單在 1440 寬放得下）掃不到它們，
 * SCG-4 一審後的真機掃描才發現（F11）。
 */
const LONG_TAIL = Array.from({ length: 48 }, (_, i) => `第 ${String(i + 1).padStart(2, "0")} 行：pgbackrest 備份輸出（假資料，用來撐出可捲動的輸出尾段）`).join("\n");

/** ADMIN 看到的總覽：full、diff、dump 三張卡帶長輸出尾段（verify 從未執行，沒有尾段）；其餘同 VIEWER 的 OVERVIEW。 */
const ADMIN_OVERVIEW = {
  ...OVERVIEW,
  cards: OVERVIEW.cards.map((c) => ({ ...c, detailTail: c.job === "verify" ? "" : LONG_TAIL, requestedBy: null })),
};

const backupBackend =
  (overview: unknown = OVERVIEW): MockHandler =>
  (call) =>
    call.method === "GET" && call.path === "/api/v1/sysadmin/backups" ? { data: overview } : undefined;

/** 可捲動區域必須能用鍵盤抵達：tabindex=0（axe 的 scrollable-region-focusable），聚焦後確實成為 activeElement。 */
async function expectKeyboardRegion(region: Locator, label: string): Promise<void> {
  await expect(region, `${label}：有 tabindex=0`).toHaveAttribute("tabindex", "0");
  await region.focus();
  await expect(region, `${label}：聚焦後為 activeElement`).toBeFocused();
}

test.describe("系統管理／資料庫備份（route mock）", () => {
  test.setTimeout(180_000);

  test("AT_BK_01_2_E_2 VIEWER 從左列進「系統管理」再進備份頁：網址換頁、左列 active 為系統管理（aria-current）、頁面沒有任何寫入請求；兩個畫面 axe 無違規、無主控台錯誤", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await signInAs(page, "VIEWER");
    const { calls } = await installApiMock(page, compose(shellHandler(), backupBackend()));
    await page.goto("/projects");
    const nav = page.getByRole("navigation", { name: "主導覽" });
    const entry = nav.getByRole("link", { name: "系統管理" });
    await expect(entry).toBeVisible({ timeout: 60_000 });
    await expect(entry).not.toHaveAttribute("aria-current", "page");

    // 左列「系統管理」→ /sysadmin：入口卡、左列 active
    await entry.click();
    await expect(page).toHaveURL(/\/sysadmin$/);
    await expect(page.getByTestId("sysadmin-home")).toBeVisible();
    const homeCard = page.getByTestId("sysadmin-card-backup");
    await expect(homeCard).toBeVisible();
    await expect(homeCard).toHaveAttribute("href", "/sysadmin/backup");
    await expect(page.getByTestId("sysadmin-backup-summary")).toHaveText("成功");
    await expect(entry).toHaveAttribute("aria-current", "page");
    await expectNoA11yViolations(page, "系統管理入口頁");

    // 入口卡 → /sysadmin/backup：最近狀態、備份清單；左列 active 仍為系統管理
    await homeCard.click();
    await expect(page).toHaveURL(/\/sysadmin\/backup$/);
    await expect(page.getByRole("heading", { level: 1, name: "資料庫備份" })).toBeVisible();
    await expect(page.getByTestId("bk-cards")).toBeVisible();
    await expect(page.getByTestId("bk-badge-diff")).toHaveText("失敗");
    await expect(page.getByTestId("bk-badge-verify")).toHaveText("從未執行");
    await expect(page.getByTestId("bk-wal-line")).toContainText("WAL 歸檔：最近");
    await expect(page.getByTestId("bk-table")).toBeVisible();
    await expect(page.getByTestId("bk-result-20261026-020000F_20261027-020000D")).toHaveText("成功，但有校驗錯誤");
    await expect(page.getByTestId("bk-repo-badge-2")).toContainText("與主機同碟");
    await expect(entry).toHaveAttribute("aria-current", "page");
    await expectNoA11yViolations(page, "資料庫備份（備份清單）");

    // 切到另外兩個分頁看一眼（都是唯讀說明與排程）
    await page.getByRole("tab", { name: "排程與保留" }).click();
    await expect(page.getByTestId("bk-sched-full")).toContainText("每週日 02:00・全備");
    await expect(page.getByTestId("bk-retention")).toHaveText("本地：全備 4、差異 7；離站：全備 4、差異隨全備到期；邏輯備份 28 天");
    await expectNoA11yViolations(page, "資料庫備份（排程與保留）");
    await page.getByRole("tab", { name: "還原與說明" }).click();
    await expect(page.getByTestId("bk-no-restore-note")).toContainText("本頁不提供還原按鈕");
    await expect(page.getByTestId("bk-coverage-row-engine_workspace")).toContainText("未涵蓋");
    await expectNoA11yViolations(page, "資料庫備份（還原與說明）");

    // 全程沒有任何寫入請求；只打過總覽端點
    expect(
      calls.filter((c) => c.method !== "GET"),
      "頁面沒有任何 POST、PUT、DELETE",
    ).toEqual([]);
    expect(calls.some((c) => c.path === "/api/v1/sysadmin/backups")).toBe(true);
    expect(errors, "瀏覽器主控台沒有 React 警告、被擋的請求或未捕捉例外").toEqual([]);
  });

  test("AT_BK_01_2_E_3 ADMIN 長資料（三張卡的輸出尾段超過 12rem、390 寬時清單與涵蓋表橫向溢出）：1440 與 390 寬、三個分頁 axe 皆無違規；三個可捲動區域都能用鍵盤聚焦（tabindex=0、role=region、有名稱）", async ({
    page,
  }) => {
    const errors = collectConsoleErrors(page);
    await signInAs(page, "ADMIN");
    await installApiMock(page, compose(shellHandler(), backupBackend(ADMIN_OVERVIEW)));
    const tabs = ["備份清單", "排程與保留", "還原與說明"] as const;
    const summary: string[] = [];

    for (const viewport of [
      { width: 1440, height: 900 },
      { width: 390, height: 844 },
    ]) {
      await page.setViewportSize(viewport);
      await page.goto("/sysadmin/backup");
      await expect(page.getByTestId("bk-cards")).toBeVisible({ timeout: 60_000 });

      // 前置（防反空轉）：資料真的讓可捲動區域「可捲」；否則 axe 根本不檢查它們，綠燈就什麼也沒證明
      const tails = page.locator('[data-testid^="bk-tail-"]');
      await expect(tails, "ADMIN 的 full、diff、dump 三張卡各有輸出尾段").toHaveCount(3);
      for (const [i, tail] of (await tails.all()).entries()) {
        expect(await tail.evaluate((el) => el.scrollHeight > el.clientHeight), `${viewport.width} 寬：第 ${i + 1} 個輸出尾段超出可見高度（可捲）`).toBe(true);
      }

      for (const name of tabs) {
        await page.getByRole("tab", { name }).click();
        const label = `ADMIN ${viewport.width} 寬「${name}」`;
        const wide = name === "備份清單" ? page.getByTestId("bk-table") : name === "還原與說明" ? page.getByTestId("bk-coverage") : null;
        if (wide !== null) {
          await expect(wide).toBeVisible();
          // 390 寬：十欄表（min 56rem）與涵蓋表（min 40rem）必橫向溢出，外層容器才是可捲動區域
          if (viewport.width === 390) {
            expect(await wide.locator("xpath=..").evaluate((el) => el.scrollWidth > el.clientWidth), `${label}：外層容器橫向溢出（可捲）`).toBe(true);
          }
        }
        // soft：六次掃描都跑完、各自列出規則與節點，失敗訊息不會只停在第一個
        const findings = await axeViolations(page);
        summary.push(`${label}：${findings.length === 0 ? "0 違規" : findings.map((f) => `${f.id}×${f.nodes.length}`).join("、")}`);
        expect.soft(findings, `${label}：無障礙違規\n${formatViolations(findings)}`).toEqual([]);
      }
    }
    console.log(`axe 掃描結果（規則×節點數）：\n  ${summary.join("\n  ")}`);

    // 三個可捲動區域（此時為 390 寬、停在「還原與說明」）：有名稱的 region，tabindex=0、聚焦後是 activeElement；三個輸出尾段的名稱互不相同（各帶工作名）
    const tailRegions = page.getByRole("region", { name: /輸出尾段（可捲動）$/ });
    await expect(tailRegions, "三個輸出尾段各是一個有名稱的 region").toHaveCount(3);
    const tailNames = await tailRegions.evaluateAll((els) => els.map((el) => el.getAttribute("aria-label")));
    expect(new Set(tailNames).size, `三個輸出尾段的名稱互不相同：${tailNames.join("｜")}`).toBe(3);
    for (const [i, region] of (await tailRegions.all()).entries()) await expectKeyboardRegion(region, `輸出尾段 ${i + 1}`);
    await expectKeyboardRegion(page.getByRole("region", { name: "涵蓋範圍表（可橫向捲動）" }), "涵蓋範圍表");
    await page.getByRole("tab", { name: "備份清單" }).click();
    await expectKeyboardRegion(page.getByRole("region", { name: "備份清單（可橫向捲動）" }), "備份清單");

    expect(errors, "瀏覽器主控台沒有 React 警告、被擋的請求或未捕捉例外").toEqual([]);
  });
});
