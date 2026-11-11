import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { expectNoA11yViolations } from "./a11y";
import { collectConsoleErrors, compose, installApiMock, shellHandler, signInAs, type MockCall, type MockHandler } from "./mockApi";

/**
 * 自動演化排程（TCS-SelfImprovingSchedule AT-964-2-4／3-4／4-4；D-CS-9）——route mock 版：ADMIN 在 /self-improving 的排程面板走完三個動作（啟用、改週期、立即啟動），
 * 後端以 spec 內自帶的 `/api/v1/si/**` 路由代替（不改 mockApi.ts）：唯讀資料取自入庫的黃金檔（真 CLI 輸出，與 vitest 共用），`status` 另加 camelCase 的 `schedule`，
 * 兩個 POST 回 201 收據並記下本文；對帳（console-writes）有狀態——送出立即啟動後重取會多一筆 `run-request` 且尚未入帳。
 * 驗真瀏覽器才量得到的事：整條流程無主控台錯誤、週期旁即時換算提示、送出的本文鍵集合（停用不補預設值）、收據文案是「待入帳」而不是已生效、
 * 待入帳後再開立即啟動對話框，主鈕停用並顯示稽核編號。一律對 production 建置跑（`E2E_MODE=standalone` 先 `npm run build`）。
 */
type Fixture = { observations: Page_; events: Page_; proposals: Page_; runs: Page_; status: Page_ & { items: Array<Record<string, unknown>> } };
type Page_ = { items: unknown[]; truncated?: boolean; nextSince?: number | null } & Record<string, unknown>;
const A = JSON.parse(readFileSync(path.join(process.cwd(), "tests", "fixtures", "si", "A.camel.json"), "utf-8")) as Fixture;

const BOUNDS = { periodMin: 60, periodMax: 10080 };
const sched = (over: Record<string, unknown> = {}) => ({
  enabled: false,
  periodMinutes: 1440,
  ...BOUNDS,
  heartbeatMinutes: 15,
  lastSet: { at: "2026-11-09T10:00:00+08:00", by: "admin", carrier: "console" },
  cellStart: "2026-11-09T00:00:00+08:00",
  cellEnd: "2026-11-10T00:00:00+08:00",
  ranThisCell: false,
  lastSkip: null,
  overdue: false,
  armed: "NOT-EVALUABLE：export-reads-no-home",
  ...over,
});

const whole = (page: Page_) => ({ ...page, truncated: false, nextSince: null });
const REF = (n: number) => `a1000000-0000-4000-8000-${String(n).padStart(12, "0")}`;

/** 假後端：唯讀資料取黃金檔；兩個 POST 回 201 並記錄；對帳有狀態（送出立即啟動後多一筆待入帳）。 */
function siBackend(world: { posts: MockCall[]; runRequests: string[] }): MockHandler {
  return (call) => {
    if (call.method === "POST" && (call.path === "/api/v1/si/schedule/set" || call.path === "/api/v1/si/runs/request")) {
      world.posts.push(call);
      const kind = call.path.endsWith("/schedule/set") ? "sched-set" : "run-request";
      const auditRef = REF(world.posts.length);
      if (kind === "run-request") world.runRequests.push(auditRef);
      return { status: 201, data: { auditRef, kind, subject: null, time: "2026-11-09T14:00:00+08:00", keyId: "f076edf0" } };
    }
    if (call.method !== "GET") return undefined;
    switch (call.path) {
      case "/api/v1/si/status":
        return { data: { ...A.status, items: [{ ...A.status.items[0], schedule: sched() }] } };
      case "/api/v1/si/observations":
        return { data: whole(A.observations) };
      case "/api/v1/si/proposals":
        return { data: whole(A.proposals) };
      case "/api/v1/si/events":
        return { data: whole(A.events) };
      case "/api/v1/si/runs":
        return { data: whole(A.runs) };
      case "/api/v1/si/console-writes":
        return {
          data: {
            items: world.runRequests.map((auditRef) => ({
              auditRef,
              kind: "run-request",
              dkind: null,
              user: "admin",
              role: "ADMIN",
              time: "2026-11-09T14:00:00+08:00",
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

async function open(page: Page) {
  const errors = collectConsoleErrors(page);
  const world = { posts: [] as MockCall[], runRequests: [] as string[] };
  await installApiMock(page, compose(siBackend(world), shellHandler()));
  await signInAs(page, "ADMIN", "admin");
  await page.goto("/self-improving");
  await expect(page.getByTestId("si-schedule-panel")).toBeVisible();
  return { errors, world };
}

test("AT_965_10_4 ADMIN 自我進化頁（含「研究來源設定」內文連結）：axe 無 serious／critical 違規（DEF-AC-039：連結小字原用主色、在頁面底色上對比 4.21 低於 4.5）", async ({ page }) => {
  const { errors } = await open(page);
  // 連結只在 ADMIN 渲染；先確認它真的在畫面上，掃描才量得到它（成因：過去沒有任何 mock a11y spec 掃過 /self-improving）
  await expect(page.getByTestId("si-research-sources-note").getByRole("link", { name: "研發工作流 → 研究來源設定" })).toBeVisible();
  await expectNoA11yViolations(page, "自我進化頁（ADMIN、預設分頁）");
  expect(errors, "主控台錯誤").toEqual([]);
});

const closeResult = (page: Page) => page.getByRole("dialog").locator("button", { hasText: /^關閉$/ });

test("AT_964_2_4 ADMIN 啟用開關流程：開對話框、送出、顯示待入帳收據", async ({ page }) => {
  const { errors, world } = await open(page);
  // 現值為停用：啟用或停用鈕寫「啟用排程」，開啟後開關預選為啟用，週期預填現值
  await page.getByTestId("si-schedule-toggle-open").click();
  const dialog = page.getByTestId("si-schedule-dialog");
  await expect(dialog.getByTestId("si-schedule-period")).toHaveValue("1440");
  await expect(dialog.getByTestId("si-schedule-enabled")).toHaveAttribute("aria-checked", "true");
  await expect(dialog.getByTestId("si-schedule-summary")).toContainText("啟用");
  await dialog.getByTestId("si-schedule-submit").click();
  const result = dialog.getByTestId("si-schedule-result");
  await expect(result).toContainText("稽核檔已落地，待入帳");
  await expect(result).not.toContainText(/已生效|已啟用|已啟動/);
  expect(world.posts).toHaveLength(1);
  expect(world.posts[0].body).toEqual({ enabled: true, periodMinutes: 1440 });
  expect(errors, "主控台錯誤").toEqual([]);
});

test("AT_964_3_4 ADMIN 改週期流程：換算提示、送出、收據", async ({ page }) => {
  const { errors, world } = await open(page);
  await page.getByTestId("si-schedule-period-open").click();
  const dialog = page.getByTestId("si-schedule-dialog");
  const period = dialog.getByTestId("si-schedule-period");
  await period.fill("180");
  await expect(dialog.getByTestId("si-schedule-hint")).toHaveText("≈3 小時");
  await dialog.getByTestId("si-schedule-submit").click();
  const result = dialog.getByTestId("si-schedule-result");
  await expect(result).toContainText("稽核檔已落地，待入帳");
  await expect(result.getByTestId("si-ingest-commands")).toContainText("python tools/selfimproving.py sched set --carrier console --audit-ref");
  expect(world.posts).toHaveLength(1);
  expect(world.posts[0].path).toBe("/api/v1/si/schedule/set");
  expect(world.posts[0].body).toEqual({ enabled: false, periodMinutes: 180 });
  expect(errors, "主控台錯誤").toEqual([]);
});

test("AT_964_4_4 ADMIN 立即啟動流程：送出、收據、待入帳後鈕停用", async ({ page }) => {
  const { errors, world } = await open(page);
  await page.getByTestId("si-run-request-open").click();
  const dialog = page.getByTestId("si-run-request-dialog");
  await expect(dialog.getByTestId("si-run-request-submit")).toBeEnabled();
  await dialog.getByTestId("si-run-request-submit").click();
  const result = dialog.getByTestId("si-run-request-result");
  await expect(result).toContainText("稽核檔已落地，待入帳");
  await expect(result).not.toContainText(/已生效|已啟用|已啟動/);
  expect(world.posts).toHaveLength(1);
  expect(world.posts[0].body).toEqual({});
  const sent = world.runRequests[0];
  await closeResult(page).click();
  await expect(page.getByTestId("si-run-request-dialog")).toHaveCount(0);

  // 送出後 console-writes 重取、含一筆未入帳的 run-request：再開對話框，主鈕停用並顯示稽核編號
  await expect(page.getByTestId(`si-pending-${sent}`)).toBeVisible();
  await page.getByTestId("si-run-request-open").click();
  const again = page.getByTestId("si-run-request-dialog");
  await expect(again.getByTestId("si-run-request-submit")).toBeDisabled();
  await expect(again.getByTestId("si-run-request-dup")).toHaveText(`已送出待入帳（稽核編號 ${sent}）`);
  expect(world.posts, "停用後沒有第二次送出").toHaveLength(1);
  expect(errors, "主控台錯誤").toEqual([]);
});
