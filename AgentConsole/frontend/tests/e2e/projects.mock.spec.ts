import { expect, test, type Page } from "@playwright/test";

import { expectNoA11yViolations } from "./a11y";
import { collectConsoleErrors, compose, fail, installApiMock, paged, signInAs, snap, type MockHandler } from "./mockApi";

/**
 * 專案列表的「已刪除」篩選與復原（W5 C-3；契約 §1.6.1～§1.6.2、§4.5 G-09；PRD NFR-9.3-04）——route mock 版：
 *  - OPERATOR 以上才有「已刪除」鈕（VIEWER 沒有：後端對 VIEWER 的 `deleted=true` 回 403）；
 *  - 打開後改打 `GET /projects?deleted=true`，卡片顯示「已刪除」標籤、刪除時間與「復原」鈕；
 *  - 復原成功 toast 並從已刪除清單消失；三種失敗各有白話原因：409 `project_not_deleted`、409 `restore_window_expired`、404（已被清除）。
 * 真後端的語意（連帶軟刪的目標／任務一併回來、保留期判定）由 QA 波的 E2E-13 列 2～3 驗。
 */
const NOW = new Date().toISOString();
const ID = {
  ok: "a0000000-0000-4000-8000-0000000000a1",
  alreadyBack: "a0000000-0000-4000-8000-0000000000a2",
  expired: "a0000000-0000-4000-8000-0000000000a3",
  purged: "a0000000-0000-4000-8000-0000000000a4",
  live: "b0000000-0000-4000-8000-0000000000b1",
};

const summary = (id: string, name: string, patch: Record<string, unknown> = {}) => ({
  id,
  name,
  executionPath: `/work/${name}`,
  status: "READY",
  autonomyLevel: 3,
  signedOff: true,
  goalsCount: 2,
  tasksCount: 5,
  tasksDone: 1,
  updatedAt: NOW,
  ...patch,
});

type Row = ReturnType<typeof summary>;

/** 假後端：已刪除清單與一般清單分開；復原依專案 id 決定結果（成功／已被復原／逾期／已被清除）。 */
function createWorld() {
  const live: Row[] = [summary(ID.live, "仍在使用的專案")];
  const deleted: Row[] = [
    summary(ID.ok, "可復原專案", { status: "ARCHIVED", deletedAt: "2026-10-10T06:00:00Z" }),
    summary(ID.alreadyBack, "已被別人復原的專案", { status: "ARCHIVED", deletedAt: "2026-10-09T06:00:00Z" }),
    summary(ID.expired, "逾期專案", { status: "ARCHIVED", deletedAt: "2026-08-01T06:00:00Z" }),
    summary(ID.purged, "已被清除的專案", { status: "ARCHIVED", deletedAt: "2026-07-01T06:00:00Z" }),
  ];
  const handler: MockHandler = (call) => {
    const { method, path, query } = call;
    if (method === "GET" && path === "/api/v1/notifications/summary") {
      return { data: { pendingSignoffs: 0, pendingReviews: 0, unacknowledgedAlerts: 0, bridgeConnected: null, bridgeCheckedAt: null } };
    }
    if (method === "GET" && path === "/api/v1/projects") {
      return { data: paged(query.get("deleted") === "true" ? deleted : live, Number(query.get("size") ?? 10)) };
    }
    const restore = /^\/api\/v1\/projects\/([\w-]+)\/restore$/.exec(path);
    if (method === "POST" && restore) {
      const id = restore[1];
      if (id === ID.ok) {
        const i = deleted.findIndex((p) => p.id === id);
        const [row] = deleted.splice(i, 1);
        live.push({ ...row, status: "READY", deletedAt: undefined } as Row);
        return { data: { ...row, status: "READY", passCriteria: "- ok", createdAt: NOW, goals: [] } };
      }
      if (id === ID.alreadyBack) {
        const i = deleted.findIndex((p) => p.id === id);
        const [row] = deleted.splice(i, 1); // 其實已被別人復原：之後的重抓清單就沒有它了
        live.push({ ...row, status: "READY", deletedAt: undefined } as Row);
        return fail(409, { message: "專案未被刪除", reason: "project_not_deleted", details: { projectId: id, status: "READY" } });
      }
      if (id === ID.expired) {
        return fail(409, { message: "已逾保留期", reason: "restore_window_expired", details: { projectId: id, deletedAt: "2026-08-01T06:00:00Z", retentionDays: 30 } });
      }
      if (id === ID.purged) {
        const i = deleted.findIndex((p) => p.id === id);
        deleted.splice(i, 1); // 清除排程實體刪除：之後的重抓清單就沒有它了
        return fail(404, { message: `專案不存在或已清除：${id}` });
      }
    }
    return undefined;
  };
  return { handler, live, deleted };
}

async function open(page: Page, role: "OPERATOR" | "VIEWER") {
  const world = createWorld();
  await signInAs(page, role);
  const unhandled: string[] = [];
  const tail: MockHandler = (call) => {
    unhandled.push(`${call.method} ${call.path}`);
    return undefined;
  };
  const { calls } = await installApiMock(page, compose(world.handler, tail));
  const errors = collectConsoleErrors(page);
  await page.goto("/projects");
  await expect(page.getByRole("heading", { name: "專案管理" })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("project-card")).toHaveCount(1);
  return { world, calls, errors, unhandled };
}

const cardOf = (page: Page, name: string) => page.getByTestId("project-card").filter({ hasText: name });

test.describe("專案列表：已刪除篩選與復原（route mock）", () => {
  test.setTimeout(120_000);

  test("OPERATOR：「已刪除」改打 deleted=true、卡片顯示已刪除標籤與刪除時間；復原成功 toast 並從清單消失；再按一次回一般清單", async ({ page }) => {
    const { calls, errors, unhandled } = await open(page, "OPERATOR");
    await expect(page.getByTestId("deleted-filter")).toBeVisible();
    await expect(page.getByTestId("deleted-filter")).toHaveAttribute("aria-pressed", "false");

    await page.getByTestId("deleted-filter").click();
    await expect(page.getByTestId("project-card")).toHaveCount(4);
    await expect(page.getByTestId("deleted-filter")).toHaveAttribute("aria-pressed", "true");
    const deletedReq = calls.filter((c) => c.method === "GET" && c.path === "/api/v1/projects" && c.query.get("deleted") === "true");
    expect(deletedReq.length).toBeGreaterThan(0);
    expect(deletedReq[0].query.has("status")).toBe(false);
    await expect(page.getByTestId("deleted-hint")).toContainText("保留一段時間（預設 30 天）");
    await expect(page.getByRole("group", { name: "狀態篩選" })).toHaveCount(0);

    const ok = cardOf(page, "可復原專案");
    await expect(ok.getByTestId("deleted-tag")).toHaveText("已刪除");
    await expect(ok.getByTestId("deleted-at")).toContainText("刪除於 2026-10-10");
    await expect(ok.getByRole("link")).toHaveCount(0); // 已刪除的專案詳情頁是 404：名稱與按鈕都不是連結
    await expectNoA11yViolations(page, "專案列表（已刪除檢視）");
    await snap(page, "02-projects-deleted.png");

    await ok.getByTestId("project-restore").click();
    await expect(page.getByText("已復原專案「可復原專案」（2 個目標、5 個任務），可在「全部」清單找到它")).toBeVisible();
    await expect(page.getByTestId("project-card")).toHaveCount(3);
    await expect(cardOf(page, "可復原專案")).toHaveCount(0);
    expect(calls.filter((c) => c.method === "POST" && c.path === `/api/v1/projects/${ID.ok}/restore`)).toHaveLength(1);

    // 回一般清單：復原的專案已在其中
    await page.getByTestId("deleted-filter").click();
    await expect(page.getByTestId("deleted-filter")).toHaveAttribute("aria-pressed", "false");
    await expect(cardOf(page, "可復原專案")).toHaveCount(1);
    await expect(page.getByRole("group", { name: "狀態篩選" })).toBeVisible();
    await expectNoA11yViolations(page, "專案列表（一般清單，含草案標籤）");
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
    expect(unhandled, "mock 沒處理的請求").toEqual([]);
  });

  test("復原失敗的三種原因各有白話說明：409 project_not_deleted（並重抓清單）、409 restore_window_expired（帶保留天數）、404（已被清除，並重抓清單）", async ({ page }) => {
    const { errors, unhandled } = await open(page, "OPERATOR");
    await page.getByTestId("deleted-filter").click();
    await expect(page.getByTestId("project-card")).toHaveCount(4);

    // ① 專案其實已被別人復原
    await cardOf(page, "已被別人復原的專案").getByTestId("project-restore").click();
    await expect(page.getByText("復原失敗：這個專案目前沒有被刪除（可能已被其他人復原），不需要復原。")).toBeVisible();
    await expect(page.getByTestId("project-card")).toHaveCount(3); // 重抓後它不在已刪除清單了

    // ② 超過保留期：專案仍在清單上，不重抓
    await cardOf(page, "逾期專案").getByTestId("project-restore").click();
    await expect(page.getByText("復原失敗：這個專案刪除已超過保留期（30 天），無法復原。")).toBeVisible();
    await expect(cardOf(page, "逾期專案")).toHaveCount(1);
    await expect(page.getByTestId("project-card")).toHaveCount(3);

    // ③ 已被清除排程實體刪除（404）
    await cardOf(page, "已被清除的專案").getByTestId("project-restore").click();
    await expect(page.getByText("復原失敗：找不到這個專案：它可能已被永久清除，無法復原。")).toBeVisible();
    await expect(page.getByTestId("project-card")).toHaveCount(2); // 重抓後清單只剩「可復原」與「逾期」
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
    expect(unhandled, "mock 沒處理的請求").toEqual([]);
  });

  test("唯讀角色（VIEWER）：沒有「已刪除」鈕，一般清單照常", async ({ page }) => {
    const { calls, errors, unhandled } = await open(page, "VIEWER");
    await expect(page.getByTestId("deleted-filter")).toHaveCount(0);
    await expect(page.getByRole("group", { name: "狀態篩選" })).toBeVisible();
    expect(calls.some((c) => c.query.get("deleted") === "true")).toBe(false); // 不會對後端送出會被 403 的查詢
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
    expect(unhandled, "mock 沒處理的請求").toEqual([]);
  });
});
