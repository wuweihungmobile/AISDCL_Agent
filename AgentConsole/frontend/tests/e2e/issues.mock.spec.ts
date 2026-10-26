import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { expectNoA11yViolations } from "./a11y";
import { collectConsoleErrors, compose, installApiMock, shellHandler, signInAs, type MockCall, type MockHandler } from "./mockApi";

/**
 * 議題中心（TCS-IssueCenter-20261027 AT-IC-12-5-2；R-IC-74）——route mock 版：只用鍵盤走完一輪（Tab 到分頁、方向鍵切換、Enter 開詳情、開排序對話框、
 * Esc 關閉、焦點回到觸發鈕），並在三個穩定的畫面（待處理、詳情開啟、排序對話框開啟）與最後各做一次 axe 掃描（沿 a11y.ts；WCAG 2.0／2.1 A／AA）。
 * 後端以 spec 內自帶的 `/api/v1/issues*` 路由代替（不改 mockApi.ts，TCS Q7）：圖例取自入庫的黃金檔（真 CLI 輸出），議題與摘要在這裡組。
 * 分頁、清單、對話框與按鈕的 aria 名稱由元件測試（IssuesView.test.tsx 等）以 getByRole 逐項驗；這裡驗真瀏覽器才量得到的東西——焦點移動、色彩對比、名稱含可見文字。
 */
type Row = Record<string, unknown>;
const LEGEND = (
  JSON.parse(readFileSync(path.join(process.cwd(), "tests", "fixtures", "si", "A.camel.json"), "utf-8")) as { issues: { legend: Row & { statuses: Array<{ name: string; tab: string | null }> } } }
).issues.legend;

function issue(id: string, patch: Row): Row {
  return {
    id,
    source: "系統缺陷",
    title: `${id} 的標題`,
    severity: "中",
    severityRank: 3,
    status: "待解",
    result: null,
    updatedAt: "2026-10-20",
    nextStep: "已成立，尚無人接手",
    origin: { ledger: "缺陷帳本", file: "docs/06_quality/AutoSDD_Defect_Log.md", line: 10 },
    links: [],
    rankable: true,
    action: null,
    priority: null,
    priorityNote: null,
    ...patch,
  };
}

const ITEMS: Row[] = [
  issue("OBS-SI-001", { status: "已完成", result: "已裁決", rankable: false, updatedAt: "2026-10-18", severity: "低", severityRank: 4, source: "系統改善" }),
  issue("OBS-SI-005", { status: "待您決定", action: "close-observation", source: "使用者提案", nextStep: "等掌舵者決定：在此關閉並寫下裁決", updatedAt: "2026-10-21" }),
  issue("OBS-SI-006", { title: "緊急的缺陷", severity: "緊急", severityRank: 1, updatedAt: "2026-10-10", links: ["OBS-SI-001"] }),
  issue("OBS-SI-007", { status: "進行中", severity: "高", severityRank: 2, nextStep: "已分流待修", updatedAt: "2026-10-12", source: "系統改善" }),
  issue("PROP-SI-004", {
    status: "待您決定",
    action: "decide-proposal",
    source: "使用者提案",
    severity: null,
    severityRank: null,
    nextStep: "等掌舵者決定：核准、否決或退回",
    updatedAt: "2026-10-20",
  }),
];

const metaOf = () => ({ schemaRev: 1, kind: "issues", generatedAt: "2026-10-27T10:00:00+08:00", headSha: "0".repeat(40), nextSince: null, truncated: false, ne: [], problems: [] });

/** 假後端：清單（含 legend、summary，依 status 別名篩選）、單筆（含 raw、timeline）、PUT／DELETE 優先順序（有狀態）。 */
function issuesBackend(priorities: Map<string, { rank: number; note: string }>): MockHandler {
  const tabOf = (status: string) => LEGEND.statuses.find((s) => s.name === status)?.tab ?? null;
  const withPriority = (i: Row): Row => {
    const row = priorities.get(String(i.id));
    return i.rankable && row ? { ...i, priority: row.rank, priorityNote: row.note } : i;
  };
  const count = (tab: string) => ITEMS.filter((i) => tabOf(String(i.status)) === tab).length;
  return (call) => {
    if (call.path === "/api/v1/issues" && call.method === "GET") {
      const wanted = call.query.get("status");
      const items = ITEMS.filter((i) => wanted === null || wanted.split(",").some((w) => w === i.status || w === tabOf(String(i.status)))).map(withPriority);
      const byStatus = Object.fromEntries(LEGEND.statuses.map((s) => [s.name, ITEMS.filter((i) => i.status === s.name).length]));
      return {
        data: { ...metaOf(), items, legend: LEGEND, summary: { total: ITEMS.length, byStatus, byTab: { 待處理: count("待處理"), 待您決定: count("待您決定"), 已完成: count("已完成") }, unmapped: 0 } },
      };
    }
    const priority = /^\/api\/v1\/issues\/([^/]+)\/priority$/.exec(call.path);
    if (priority && call.method === "PUT") {
      const body = call.body as { rank: number; note?: string };
      const row = { rank: body.rank, note: body.note ?? "" };
      priorities.set(decodeURIComponent(priority[1]), row);
      return { data: { id: decodeURIComponent(priority[1]), ...row, setBy: "admin", setAt: "2026-10-27T10:00:30+08:00" } };
    }
    if (priority && call.method === "DELETE") {
      priorities.delete(decodeURIComponent(priority[1]));
      return { status: 204 };
    }
    const one = /^\/api\/v1\/issues\/([^/]+)$/.exec(call.path);
    if (one && call.method === "GET") {
      const found = ITEMS.find((i) => i.id === decodeURIComponent(one[1]));
      if (!found) return { status: 404, error: { message: "查無此議題", reason: "si_not_found", details: { id: decodeURIComponent(one[1]) } } };
      return {
        data: {
          ...metaOf(),
          items: [
            {
              ...withPriority(found),
              raw: [
                { label: "處置", value: "open" },
                { label: "症狀", value: "原列的症狀全文" },
              ],
              timeline: [{ seq: 3, t: "2026-10-18T10:00:00+08:00", by: "orchestrator", action: "新增觀察" }],
            },
          ],
        },
      };
    }
    return undefined;
  };
}

/** 一路按 Tab 直到焦點落在符合選擇器的元素上（最多 80 次；找不到就失敗，不空轉）。 */
async function tabUntil(page: Page, selector: string): Promise<void> {
  for (let i = 0; i < 80; i += 1) {
    await page.keyboard.press("Tab");
    if (await page.evaluate((sel) => document.activeElement?.matches(sel) ?? false, selector)) return;
  }
  throw new Error(`按 Tab 80 次仍沒有把焦點帶到 ${selector}`);
}

test.describe("議題中心（route mock）", () => {
  test.setTimeout(180_000);

  test("AT_IC_12_5_2 只用鍵盤走完一輪：Tab 到分頁、方向鍵切換、Enter 開詳情、開排序對話框、Esc 關閉且焦點回到觸發鈕；全程 axe 無違規、無主控台錯誤", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    const priorities = new Map<string, { rank: number; note: string }>();
    await signInAs(page, "ADMIN");
    const { calls } = await installApiMock(page, compose(shellHandler(), issuesBackend(priorities)));
    await page.goto("/issues");
    await expect(page.getByRole("heading", { level: 1, name: "議題中心" })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("issues-table")).toBeVisible();
    await expect(page.getByTestId("issues-summary-pending")).toHaveText("待處理 2");
    await expectNoA11yViolations(page, "議題中心（待處理）");

    // 1. Tab 到分頁（選中的那顆）；方向鍵切換並移動焦點；Home 回第一顆
    await tabUntil(page, '[role="tab"][aria-selected="true"]');
    await expect(page.getByRole("tab", { name: "待處理" })).toBeFocused();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: "待您決定" })).toBeFocused();
    await expect(page.getByRole("tab", { name: "待您決定" })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByTestId("issue-row-PROP-SI-004")).toBeVisible();
    await expect(page.getByTestId("issue-row-OBS-SI-005")).toBeVisible();
    await expect(page.getByTestId("issue-top-pinned")).toHaveCount(2);
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: "已完成" })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByTestId("issue-row-OBS-SI-001")).toBeVisible();
    await page.keyboard.press("Home");
    await expect(page.getByRole("tab", { name: "待處理" })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByTestId("issue-row-OBS-SI-006")).toBeVisible();

    // 2. Tab 到清單第一列的編號鈕，Enter 開詳情（焦點移進面板），Esc 收起且焦點回到編號鈕
    await tabUntil(page, '[data-testid^="issue-open-"]');
    const opener = page.locator('[data-testid^="issue-open-"]:focus');
    await expect(opener).toHaveText("OBS-SI-006");
    await page.keyboard.press("Enter");
    const detail = page.getByTestId("issue-detail");
    await expect(detail).toBeVisible();
    await expect(detail).toBeFocused();
    await expect(page.getByTestId("issue-detail-raw")).toBeVisible();
    await expect(page.getByTestId("issue-detail-links")).toContainText("OBS-SI-001");
    await expectNoA11yViolations(page, "議題中心（詳情開啟）");
    await page.keyboard.press("Escape");
    await expect(detail).toHaveCount(0);
    await expect(page.getByTestId("issue-open-OBS-SI-006")).toBeFocused();

    // 3. Tab 到「排序」鈕，Enter 開對話框（焦點在順位欄），Esc 關閉且焦點回到該鈕
    await tabUntil(page, '[data-testid^="issue-priority-open-"]');
    const rank = page.locator('[data-testid^="issue-priority-open-"]:focus');
    const trigger = (await rank.getAttribute("data-testid")) ?? "";
    await page.keyboard.press("Enter");
    const dialog = page.getByTestId("issue-priority-dialog");
    await expect(dialog).toBeVisible();
    await expect(page.getByTestId("issue-priority-rank")).toBeFocused();
    await page.keyboard.type("3");
    await expect(page.getByTestId("issue-priority-rank")).toHaveValue("3");
    await expectNoA11yViolations(page, "議題中心（排序對話框）");
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(page.getByTestId(trigger)).toBeFocused();
    expect(
      calls.filter((c: MockCall) => c.method !== "GET"),
      "Esc 關閉不送任何寫入請求",
    ).toEqual([]);

    // 4. 再開一次，用鍵盤填順位與備註，Enter 送出：PUT 的本文與回應重排（以回應為準）
    await page.keyboard.press("Enter");
    await expect(dialog).toBeVisible();
    await page.keyboard.type("1");
    await page.keyboard.press("Tab");
    await page.keyboard.type("先做");
    await page.keyboard.press("Enter");
    await expect(dialog).toHaveCount(0);
    const put = calls.find((c) => c.method === "PUT");
    expect(put?.body).toEqual({ rank: 1, note: "先做" });
    await expect(page.getByTestId("issue-priority-OBS-SI-006")).toHaveText("1");
    await expect(page.getByTestId("issue-priority-note-OBS-SI-006")).toHaveText("先做");
    await expectNoA11yViolations(page, "議題中心（儲存順位之後）");
    expect(errors, "瀏覽器主控台沒有 React 警告、被擋的請求或未捕捉例外").toEqual([]);
  });
});
