import { expect, test } from "@playwright/test";

import { eventPage, EVENTS } from "../fixtures/research/events";
import { fsmView } from "../fixtures/research/fsm";
import { R1, R2 } from "../fixtures/research/ids";
import { ALLOWLIST, CAPABILITIES_LOCAL, EVIDENCE, RECORDS_AUDIT, SOURCES } from "../fixtures/research/misc";
import { detailVariant, PROJECT_LIST } from "../fixtures/research/projects";
import { defect, FAIL3_SCORES, makeRound, PRD_CONTENT, PRD_VERSIONS } from "../fixtures/research/reviews";
import { expectNoA11yViolations } from "./a11y";
import { collectConsoleErrors, compose, fail, installApiMock, paged, shellHandler, signInAs, type MockHandler } from "./mockApi";

/**
 * 無障礙掃描（axe-core；WCAG 2.0／2.1 A／AA）——route mock 版，補上其他 mock spec 沒走到的頁面與狀態：
 * 登入頁（含欄位錯誤與登入失敗）、新建專案對話框（Markdown 編輯器工具列）、專案詳情（草案橫幅）、目標詳情、任務詳情（待人工、執行歷史與日誌面板），
 * 以及研發工作流（ResearchToPRD P0）：清單 `/research`、研究工作區 `/research/<id>` 的議題步與 PRD 工作室步，各在 1440／1000／600 三個寬度整頁掃描。
 * 其餘頁面（總覽、監控、執行、匯入、設定、專案列表、通知面板）的掃描放在各自的 mock spec 裡，緊跟在該頁最豐富的狀態之後。
 * 這是 QA 報告 §11 DEF-AC-004／005 的那把尺（axe 掃 11 頁）進 CI：色彩對比、名稱含可見文字、svg 替代文字、list 結構，任何一項改壞這裡就紅。
 */
const NOW = "2026-10-15T08:30:12Z";
const P = "0c1d2e3f-4a5b-4c6d-8e7f-0a1b2c3d4e5f";
const G1 = "a1111111-0000-4000-8000-000000000001";
const G2 = "a1111111-0000-4000-8000-000000000002";
const T1 = "b2222222-0000-4000-8000-000000000001";
const T2 = "b2222222-0000-4000-8000-000000000002";

const GOALS = [
  { id: G1, projectId: P, name: "基礎建設", status: "IN_PROGRESS", sortOrder: 0, signedOff: true, taskCount: 2, completedTaskCount: 1, updatedAt: NOW },
  { id: G2, projectId: P, name: "核心功能", status: "PENDING", sortOrder: 1, signedOff: false, taskCount: 0, completedTaskCount: 0, updatedAt: NOW },
];
/** 草案專案：未 signoff（有橫幅與「未審批」標籤）、說明與通過標準帶 Markdown。 */
const PROJECT = {
  id: P,
  name: "AISDLC Core Platform",
  description: "## 概述\n\n建立 **核心平台**，含 [設計稿](https://example.com)。\n\n- 可重現\n- 可驗證",
  executionPath: "/work/core",
  passCriteria: "- [ ] 所有模組通過單元測試\n- [x] API 契約驗證通過",
  status: "DRAFT",
  autonomyLevel: 4,
  signedOff: false,
  goalsCount: 2,
  tasksCount: 2,
  tasksDone: 1,
  createdAt: NOW,
  updatedAt: NOW,
  goals: GOALS.map(({ id, name, status, sortOrder, signedOff, taskCount, completedTaskCount }) => ({ id, name, status, sortOrder, signedOff, taskCount, completedTaskCount })),
};
const TASKS = [
  { id: T1, goalId: G1, name: "初始化", sortOrder: 0, status: "COMPLETED", retryCount: 0, maxRetries: 1, signedOff: true, updatedAt: NOW },
  { id: T2, goalId: G1, name: "設定", sortOrder: 1, status: "ESCALATED", retryCount: 1, maxRetries: 1, signedOff: false, updatedAt: NOW },
];
const GOAL_DETAIL = {
  ...GOALS[0],
  description: "基礎建設：目錄、設定、CI。",
  passCriteria: "- [x] 目錄結構完成\n- [ ] CI 全綠",
  dependsOn: [],
  completionRatio: 50,
  tasks: TASKS.map(({ id, name, status, sortOrder, retryCount, maxRetries, signedOff }) => ({ id, name, status, sortOrder, retryCount, maxRetries, signedOff })),
  createdAt: NOW,
};
const TASK_DETAIL = {
  ...TASKS[1],
  description: "請輸出 `[T2_DONE]`\n\n```ts\nexport const answer = 42;\n```",
  passCriteria: "- [ ] 設定檔通過驗證",
  evaluatorCommand: "npm test",
  expectedOutputRegex: "T2_DONE",
  assignedAgent: "claude-code",
  actualTokens: 1240,
  startedAt: NOW,
  executionLog: "[08:30:12] 開始設定\n[08:30:20] 驗證失敗：缺少欄位\n[08:30:31] 升級給人工",
  executionHistory: [
    { id: "h1", stepNumber: 1, action: "STEP", status: "STARTED", tokensUsed: 0, timestamp: NOW },
    { id: "h2", stepNumber: 2, action: "STEP", status: "FAILED", tokensUsed: 1240, timestamp: NOW },
  ],
  createdAt: NOW,
};

const backend: MockHandler = (call) => {
  if (call.method !== "GET") return undefined;
  if (call.path === "/api/v1/projects") return { data: paged([PROJECT], 100) };
  if (call.path === "/api/v1/notifications/summary") return { data: { pendingSignoffs: 3, pendingReviews: 0, unacknowledgedAlerts: 0, bridgeConnected: true, bridgeCheckedAt: NOW } };
  if (call.path === `/api/v1/projects/${P}`) return { data: PROJECT };
  if (call.path === `/api/v1/projects/${P}/goals`) return { data: GOALS };
  if (call.path === `/api/v1/goals/${G1}`) return { data: GOAL_DETAIL };
  if (call.path === `/api/v1/goals/${G1}/tasks`) return { data: TASKS };
  if (call.path === `/api/v1/tasks/${T2}`) return { data: TASK_DETAIL };
  return undefined;
};

test.describe("無障礙掃描（route mock＋axe）", () => {
  test.setTimeout(120_000);

  test("登入頁：閒置、欄位驗證錯誤、帳密錯誤（401）三個狀態", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await installApiMock(
      page,
      compose((call) => (call.method === "POST" && call.path === "/api/v1/auth/login" ? fail(401, { message: "帳號或密碼錯誤" }) : undefined)),
    );
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "登入 AISDLC Console" })).toBeVisible({ timeout: 60_000 });
    await expectNoA11yViolations(page, "登入頁（閒置）");

    await page.getByRole("button", { name: "登入", exact: true }).click(); // 兩欄都空：欄位驗證錯誤
    await expect(page.getByText(/請輸入/).first()).toBeVisible();
    await expectNoA11yViolations(page, "登入頁（欄位驗證錯誤）");

    await page.getByLabel("使用者名稱").fill("operator");
    await page.getByLabel("密碼").fill("wrong-password");
    await page.getByRole("button", { name: "登入", exact: true }).click();
    await expect(page.getByRole("alert").filter({ hasText: "帳號或密碼錯誤" })).toBeVisible();
    await expectNoA11yViolations(page, "登入頁（帳密錯誤）");
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("新建專案對話框：Markdown 編輯器（工具列圖示、說明描述與通過標準兩個編輯區）", async ({ page }) => {
    await signInAs(page, "OPERATOR");
    await installApiMock(page, backend);
    await page.goto("/projects");
    await page.getByRole("button", { name: "新建專案" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible({ timeout: 60_000 });
    await expect(dialog.getByRole("textbox", { name: "說明描述", exact: true })).toBeVisible({ timeout: 60_000 });
    await expect(dialog.locator(".w-md-editor-toolbar").first()).toBeVisible();
    await expectNoA11yViolations(page, "新建專案對話框（空編輯器）");

    // 編輯器裡有內容：預覽端的標題、清單、核取清單、表格、程式碼區塊（prism＋highlight 兩套上色）
    const markdown = [
      "## 概述",
      "",
      "- [x] 已完成的項目",
      "- [ ] 待辦的項目",
      "",
      "| 欄位 | 說明 |",
      "| --- | --- |",
      "| id | 唯一識別碼 |",
      "",
      "```ts",
      "const answer: number = 42; // 註解",
      "```",
    ].join("\n");
    await dialog.getByRole("textbox", { name: "說明描述", exact: true }).fill(markdown);
    await expect(dialog.locator(".w-md-editor-preview").first().locator("code.language-ts")).toBeVisible();
    await expectNoA11yViolations(page, "新建專案對話框（編輯器預覽含程式碼區塊與核取清單）");
  });

  test("專案詳情（草案）、目標詳情、任務詳情（待人工）：橫幅、標籤、目標與任務清單、Markdown 渲染、執行日誌與歷史", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await signInAs(page, "OPERATOR");
    await installApiMock(page, backend);

    await page.goto(`/projects/${P}`);
    await expect(page.getByTestId("project-title")).toHaveText("AISDLC Core Platform", { timeout: 60_000 });
    await expect(page.getByTestId("signoff-banner")).toContainText("AI 草案 — 待人工 signoff 硬閘");
    await expect(page.getByText("核心功能")).toBeVisible();
    await expectNoA11yViolations(page, "專案詳情（草案）");

    await page.goto(`/projects/${P}/goals/${G1}`);
    await expect(page.getByRole("heading", { name: /基礎建設/ })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText("設定", { exact: true }).first()).toBeVisible();
    await expectNoA11yViolations(page, "目標詳情");

    await page.goto(`/projects/${P}/goals/${G1}/tasks/${T2}`);
    await expect(page.getByTestId("task-title")).toHaveText("設定", { timeout: 60_000 });
    await expect(page.getByTestId("signoff-banner")).toContainText("草案未審批");
    await expect(page.getByTestId("execution-history")).toBeVisible();
    await expectNoA11yViolations(page, "任務詳情（待人工）");
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });
});

// ── 研發工作流（ResearchToPRD P0；TCS-ResearchToPRD-P0-20261102 AC-R2P-01、09）─────────────────────────────────────────

/** 整頁掃描的三個寬度：與工作室的版面階層同界線（≥1280 三欄、768～1279 目錄收成圖示、<768 改分頁籤），側欄與頁首在三種寬度下的排版也各掃一次。 */
const RESEARCH_WIDTHS = [1440, 1000, 600] as const;

/**
 * 工作室的 PRD 內容：標題、清單、核取清單、GFM 表格、程式碼圍欄（預覽的渲染元素各有一個）；v1 是同一份的稍改版本（Diff 模式有差異可畫）。
 * 程式碼圍欄裡的行內註解是故意留的：編輯器預覽的註解色靠 styles/markdown.css 覆寫成設計 token，覆寫能不能贏過套件自己的 CSS 取決於兩份 CSS 的載入先後——
 * Markdown 渲染管線若又被靜態 import 進首屏（markdown.css 先於編輯器的動態 CSS 載入），這一行會退回套件預設色（#6e7781 在 #f6f8fa 上 4.27:1）而被整頁掃描抓到。
 */
const RESEARCH_PRD_V2 = [
  PRD_CONTENT,
  "## 3 功能需求",
  "",
  "| 項目 | 目標 |",
  "| --- | --- |",
  "| 查詢延遲 | P95 小於 100 毫秒 |",
  "",
  "- [x] 已完成的項目",
  "- [ ] 待辦的項目",
  "",
  "```ts",
  "const answer: number = 42; // 註解",
  "```",
  "",
].join("\n");
const RESEARCH_PRD_V1 = RESEARCH_PRD_V2.replace("P95 小於 100 毫秒", "P95 小於 200 毫秒");
const RESEARCH_PRD_CONTENT: Readonly<Record<number, string>> = { 1: RESEARCH_PRD_V1, 2: RESEARCH_PRD_V2 };

const RESEARCH_BASE = "/api/v1/research/projects";
/**
 * 清單頁另掃「失敗」與「初始化失敗」兩種徽章（INT-14⑥：階段失敗與取消不標「進行中」，徽章字色 accent 坐在 draft-bg 上）：
 * 在三個既有專案之外多兩列，真瀏覽器的 axe 才量得到新徽章的色彩對比（vitest 只能算 token 值）。
 */
const RESEARCH_LIST_WITH_FAILURES = [
  ...PROJECT_LIST,
  {
    ...PROJECT_LIST[0],
    id: "44444444-4444-4444-8444-444444444444",
    rpNo: "RP-0004",
    slug: "failed-one",
    title: "研究失敗的專案",
    flowPhase: "INGESTED",
    flowStatus: "FAILED" as const,
    flowDetail: "no_evidence",
  },
  {
    ...PROJECT_LIST[0],
    id: "55555555-5555-4555-8555-555555555555",
    rpNo: "RP-0005",
    slug: "init-failed",
    title: "初始化失敗的專案",
    flowPhase: "INGESTED",
    flowStatus: "FAILED" as const,
    flowDetail: "init_failed:fsm",
  },
];
const researchConfigRow = (key: string, value: string) => ({ id: `cfg-${key}`, category: "execution", key, value, valueType: "LONG", isEncrypted: false, hasValue: true, effect: "CONSOLE" });
const RESEARCH_ROUND = makeRound(1, FAIL3_SCORES[0], 2, { defects: [defect(1, 1), defect(1, 2, { severity: "P3", dimension: "PRODUCT" })] });

/**
 * 研究端點的假後端（只列清單、議題步、工作室步會打的 GET；寫入端點這支不碰）：R1 在議題步（證據已齊、尚未生成 PRD）、R2 在 PRD 工作室步（兩個 PRD 版本、一輪未通過的審查）。
 * 串流回 204（契約：終態批次）＝瀏覽器放棄連線、動態資料改走 REST；掃描只看靜止畫面，不需要即時事件。
 */
const researchBackend: MockHandler = (call) => {
  if (call.method !== "GET") return undefined;
  const p = call.path;
  if (p === "/api/v1/research/capabilities") return { data: CAPABILITIES_LOCAL };
  if (p === "/api/v1/research/allowlist") return { data: ALLOWLIST };
  if (p === RESEARCH_BASE) return { data: call.query.get("archived") === "true" ? [] : RESEARCH_LIST_WITH_FAILURES };
  if (p === "/api/v1/settings/execution") return { data: [researchConfigRow("globalTokenBudget", "1000000"), researchConfigRow("tokenBudgetWarningThreshold", "0.8")] };
  if (p.startsWith("/api/v1/stream/research/")) return { status: 204 };
  const match = new RegExp(`^${RESEARCH_BASE}/([^/]+)(/.*)?$`).exec(p);
  if (match === null) return undefined;
  const [, id, rest = ""] = match;
  const detail = id === R1 ? detailVariant("topicReady") : id === R2 ? detailVariant("studio") : undefined;
  if (detail === undefined) return undefined;
  if (rest === "") return { data: detail };
  if (rest === "/events") return { data: eventPage(EVENTS, Number(call.query.get("afterSeq") ?? 0), Number(call.query.get("limit") ?? 500)) };
  if (rest === "/sources") return { data: SOURCES };
  if (rest === "/evidence") return { data: EVIDENCE };
  if (rest === "/records/audit") return { data: RECORDS_AUDIT };
  if (rest === "/prd/versions") return { data: PRD_VERSIONS };
  const version = /^\/prd\/versions\/(\d+)$/.exec(rest);
  if (version !== null) {
    const row = PRD_VERSIONS.find((v) => v.versionNo === Number(version[1]));
    return row === undefined ? undefined : { data: { ...row, content: RESEARCH_PRD_CONTENT[row.versionNo] } };
  }
  if (rest === "/review-rounds") return { data: [RESEARCH_ROUND] };
  if (rest === "/fsm") return { data: fsmView("SPEC_DRAFTING", {}, 1) };
  return undefined;
};

test.describe("無障礙掃描：研發工作流（route mock＋axe；整頁；1440／1000／600）", () => {
  test.setTimeout(180_000);

  test("研發工作流清單 /research：三個寬度零違規（ADMIN 登入：含「研究來源設定」入口；五個專案各有迷你步驟列，含「失敗」「初始化失敗」徽章）", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await signInAs(page, "ADMIN");
    await installApiMock(page, compose(shellHandler(), researchBackend));
    await page.setViewportSize({ width: RESEARCH_WIDTHS[0], height: 900 });
    await page.goto("/research");
    await expect(page.getByRole("heading", { name: "研發工作流" })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("research-row")).toHaveCount(RESEARCH_LIST_WITH_FAILURES.length);
    await expect(page.getByTestId("research-badge").filter({ hasText: /^失敗$/ }), "階段失敗的專案標「失敗」、不標進行中").toHaveCount(1);
    await expect(page.getByTestId("research-badge").filter({ hasText: /^初始化失敗$/ })).toHaveCount(1);
    await expect(page.getByTestId("flow-stepper").first()).toBeVisible();
    for (const width of RESEARCH_WIDTHS) {
      await page.setViewportSize({ width, height: 900 });
      await expectNoA11yViolations(page, `研發工作流清單 ${width}`);
    }
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("研究工作區 /research/<id> 議題步（游標在第 1 步；證據與時間軸已有資料）：動態欄三個寬度零違規（含五步列「進行中」「待做」chip），證據矩陣表與技術優缺點矩陣各在 1440 零違規", async ({
    page,
  }) => {
    const errors = collectConsoleErrors(page);
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(shellHandler(), researchBackend));
    await page.setViewportSize({ width: RESEARCH_WIDTHS[0], height: 900 });
    await page.goto(`/research/${R1}`);
    await expect(page.getByTestId("research-workspace")).toHaveAttribute("data-step", "topic", { timeout: 60_000 });
    await expect(page.getByTestId("topic-panel")).toBeVisible();
    await expect(page.getByTestId("flow-stepper")).toBeVisible();
    await expect(page.getByTestId("timeline-event").first()).toBeVisible();
    for (const width of RESEARCH_WIDTHS) {
      await page.setViewportSize({ width, height: 900 });
      await expectNoA11yViolations(page, `研究工作區 議題步 ${width}（動態欄）`);
    }
    // 另兩個分頁（證據矩陣表、技術優缺點矩陣）在 1440 各掃一次
    await page.setViewportSize({ width: RESEARCH_WIDTHS[0], height: 900 });
    await page.getByRole("tab", { name: "證據矩陣表" }).click();
    await expect(page.getByTestId("evidence-table")).toBeVisible();
    await expectNoA11yViolations(page, `研究工作區 議題步 ${RESEARCH_WIDTHS[0]}（證據矩陣表）`);
    await page.getByRole("tab", { name: "技術優缺點矩陣" }).click();
    await expect(page.getByTestId("proscons-matrix")).toBeVisible();
    await expectNoA11yViolations(page, `研究工作區 議題步 ${RESEARCH_WIDTHS[0]}（技術優缺點矩陣）`);
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("研究工作區 /research/<id> PRD 工作室步（游標在第 2 步：議題步「已完成」chip 坐在頁面底色上）：1440 編輯、預覽、Diff 三個模式與 1000、600 各一次零違規", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(shellHandler(), researchBackend));
    await page.setViewportSize({ width: RESEARCH_WIDTHS[0], height: 900 });
    await page.goto(`/research/${R2}`);
    await expect(page.getByTestId("research-workspace")).toHaveAttribute("data-step", "studio", { timeout: 60_000 });
    await expect(page.getByTestId("flow-step-topic")).toHaveAttribute("data-state", "DONE");
    await expect(page.getByTestId("rich-editor-stub").or(page.locator(".w-md-editor-text-input")).first()).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("review-score")).toBeVisible();

    await expectNoA11yViolations(page, `研究工作區 PRD 工作室 ${RESEARCH_WIDTHS[0]} 編輯模式`);
    await page.getByRole("tab", { name: "預覽" }).click();
    await expect(page.getByTestId("prd-preview")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("prd-block").first()).toBeVisible();
    await expectNoA11yViolations(page, `研究工作區 PRD 工作室 ${RESEARCH_WIDTHS[0]} 預覽模式`);
    await page.getByRole("tab", { name: "Diff" }).click();
    await expect(page.getByTestId("diff-summary")).toBeVisible();
    await expectNoA11yViolations(page, `研究工作區 PRD 工作室 ${RESEARCH_WIDTHS[0]} Diff 模式`);
    await page.getByRole("tab", { name: "編輯" }).click();

    await page.setViewportSize({ width: RESEARCH_WIDTHS[1], height: 900 });
    await expect(page.getByTestId("studio-panel")).toHaveAttribute("data-tier", "medium");
    await expectNoA11yViolations(page, `研究工作區 PRD 工作室 ${RESEARCH_WIDTHS[1]}（目錄收合）`);
    await page.setViewportSize({ width: RESEARCH_WIDTHS[2], height: 900 });
    await expect(page.getByTestId("studio-panel")).toHaveAttribute("data-tier", "narrow");
    await expectNoA11yViolations(page, `研究工作區 PRD 工作室 ${RESEARCH_WIDTHS[2]}（分頁籤）`);
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });
});
