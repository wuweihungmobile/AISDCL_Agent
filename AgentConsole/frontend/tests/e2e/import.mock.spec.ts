import { expect, test, type Page } from "@playwright/test";

import { collectConsoleErrors, compose, fail, installApiMock, paged, shellHandler, signInAs, snap, type MockHandler } from "./mockApi";

/**
 * BRD/PRD 匯入頁（畫面 6）——route mock 版，不需要後端：以 page.route 攔 **／api/v1/**，回契約 §1.1 形狀的假資料。
 * 驗的是前端行為：貼文字 → 解析 → 三層樹 → 編輯 → 有界閘 422（三條全列）→ 修正儲存 → signoff → 確認匯入 → 專案頁；
 * 另含歷史記錄重開（重新整理後還原）、上傳檔案與錯誤、唯讀角色。真後端對接由 QA 波另驗。
 */
const IMPORT_ID = "7d9f3b52-1c0a-4e8e-9a43-5f6b2c1d8e01";
const PROJECT_ID = "0c1d2e3f-4a5b-4c6d-8e7f-0a1b2c3d4e5f";
const NOW = "2026-10-15T08:30:12Z";

/** 契約 E2E-01 的 S-OK 解析結果：g1 兩個任務、g2 一個任務且依賴 g1（路徑 LLM）。 */
const TREE = {
  project: { name: "E2E 匯入專案", executionPath: "/e2e/proj-import", passCriteria: "三個目標全部完成", description: "由 BRD 匯入", autonomyLevel: 4 },
  goals: [
    {
      key: "g1",
      name: "基礎",
      description: "",
      passCriteria: "基礎任務完成",
      sortOrder: 0,
      dependsOn: [],
      tasks: [
        { name: "初始化", description: "請輸出 [T1_DONE]", passCriteria: "輸出含 [T1_DONE]", sortOrder: 0 },
        { name: "設定", description: "請輸出 [T2_DONE]", passCriteria: "輸出含 [T2_DONE]", sortOrder: 1 },
      ],
    },
    {
      key: "g2",
      name: "核心",
      description: "",
      passCriteria: "核心任務完成",
      sortOrder: 1,
      dependsOn: ["g1"],
      tasks: [{ name: "實作", description: "請輸出 [T3_DONE]", passCriteria: "輸出含 [T3_DONE]", sortOrder: 0 }],
    },
  ],
  path: "LLM",
  aiModel: "e2e-model",
  tokenUsed: 1152,
};

/** 契約 §5 E2E-01 有界閘變體：三條違規（空 prompt、步驟超限、成環）；位置對得到上面那棵樹的節點。 */
const GATE_ERRORS = [
  { field: "goals[0].tasks[1].description", message: "任務描述不可為空", gate: "empty_prompt", detail: "任務「設定環境」的描述為空（goals[0].tasks[1]）", location: "goals[0].tasks[1].description" },
  { field: "goals[0].tasks", message: "任務數超過上限", gate: "max_steps", detail: "目標「基礎」的任務數 25 超過上限 24（不截斷、不修剪）", location: "goals[0].tasks" },
  { field: "goals[1].dependsOn", message: "依賴成環", gate: "cycle", detail: "目標依賴成環：基礎 -> 核心 -> 基礎", location: "goals[1].dependsOn" },
];

const BRD = `# BRD：E2E 匯入專案\n\n## 基礎\n建立專案骨架與設定環境，確保任何人 clone 之後都能一鍵啟動。\n\n## 核心\n實作核心模組並補上單元測試，覆蓋率達標才算完成。\n\n（以上為測試用需求文件，長度刻意超過 200 字元以走路徑 B）${"細節描述。".repeat(20)}`;

type Rec = {
  id: string;
  sourceType: string;
  sourceFileName?: string;
  status: string;
  signedOff: boolean;
  signedOffBy?: string;
  signedOffAt?: string;
  projectId?: string;
  createdAt: string;
  aiModel?: string;
  tokenUsed?: number;
  parsePath?: string;
  lastParseErrors?: unknown[];
  sourceContent: string;
  parsedResult: typeof TREE | null;
};

/** 列表與寫入端點回的 ImportRecordResponse：不含原文與解析結果（那兩欄只在 GET /import/{id}） */
const summary = (r: Rec) =>
  Object.fromEntries(Object.entries(r).filter(([key]) => key !== "sourceContent" && key !== "parsedResult"));

/** 一份「假後端」：狀態轉移照契約 §1.1（UPLOADED→PARSED→REVIEWING→IMPORTED），可切換 parse／PUT 的 422 模式。 */
function createServer(initial: Rec[] = []) {
  const s = {
    records: new Map<string, Rec>(initial.map((r) => [r.id, r])),
    parseMode: "ok" as "ok" | "gate",
    putMode: "ok" as "ok" | "gate",
    parseDelayMs: 0,
    uploadStatus: 201 as 201 | 413,
    tree: structuredClone(TREE),
  };
  const pending = () => [...s.records.values()].filter((r) => ["PARSED", "REVIEWING"].includes(r.status) && !r.signedOff).length;

  const handler: MockHandler = (call) => {
    const { method, path } = call;
    if (method === "GET" && path === "/api/v1/settings/agent") {
      return { data: [{ id: "c1", category: "agent", key: "defaultAutonomyLevel", value: "4", valueType: "INTEGER", defaultValue: "3", isEncrypted: false, hasValue: true, effect: "CONSOLE" }] };
    }
    if (method === "GET" && path === "/api/v1/import") {
      const all = [...s.records.values()].sort((a, b) => b.createdAt.localeCompare(a.createdAt)).map(summary);
      return { data: paged(all, 10) };
    }
    if (method === "POST" && (path === "/api/v1/import/text" || path === "/api/v1/import/upload")) {
      if (path.endsWith("/upload") && s.uploadStatus === 413) {
        return fail(413, { message: "上傳失敗", reason: "檔案超過 10MB 上限", details: { limitBytes: 10485760 } });
      }
      const isText = path.endsWith("/text");
      const body = call.body as { content?: string; sourceFileName?: string; sourceType?: string; multipart?: boolean; raw?: string };
      const rec: Rec = {
        id: IMPORT_ID,
        sourceType: isText ? (body.sourceType ?? "PLAIN_TEXT") : "MARKDOWN",
        sourceFileName: isText ? body.sourceFileName : "brd.md",
        status: "UPLOADED",
        signedOff: false,
        createdAt: NOW,
        sourceContent: isText ? (body.content ?? "") : "# 上傳的 BRD",
        parsedResult: null,
      };
      s.records.set(rec.id, rec);
      return { status: 201, data: summary(rec) };
    }
    const m = /^\/api\/v1\/import\/([\w-]+)(?:\/(parse|result|signoff|confirm|reject))?$/.exec(path);
    if (!m) {
      const p = /^\/api\/v1\/projects\/([\w-]+)$/.exec(path);
      if (method === "GET" && p && p[1] === PROJECT_ID) {
        return {
          data: {
            id: PROJECT_ID, name: "E2E 匯入專案", executionPath: "/e2e/proj-import", passCriteria: "三個目標全部完成", description: "由 BRD 匯入",
            status: "DRAFT", autonomyLevel: 4, signedOff: true, signedOffBy: "operator", signedOffAt: NOW, goalsCount: 2, tasksCount: 3, tasksDone: 0,
            createdAt: NOW, updatedAt: NOW, createdBy: "operator",
            goals: [
              { id: "g-1", name: "基礎", status: "PENDING", sortOrder: 0, signedOff: true, taskCount: 2, completedTaskCount: 0 },
              { id: "g-2", name: "核心", status: "PENDING", sortOrder: 1, signedOff: true, taskCount: 1, completedTaskCount: 0 },
            ],
          },
        };
      }
      return undefined;
    }
    const rec = s.records.get(m[1]);
    if (!rec) return fail(404, { message: `匯入記錄不存在或已刪除：${m[1]}` });
    const action = m[2];

    if (method === "GET" && !action) return { data: rec };

    if (method === "POST" && action === "parse") {
      const opts = call.body as { executionPath?: string };
      if (!opts.executionPath) return fail(400, { message: "驗證失敗", errors: [{ field: "executionPath", message: "必須是絕對路徑" }] });
      if (s.parseMode === "gate") {
        rec.lastParseErrors = GATE_ERRORS.map(({ gate, detail, location }) => ({ gate, detail, location }));
        return { status: 422, error: { message: "解析結果未通過有界閘（3 項）", reason: "解析結果未通過有界閘", errors: GATE_ERRORS, details: { path: "LLM" } }, delayMs: s.parseDelayMs };
      }
      rec.status = "PARSED";
      rec.parsedResult = structuredClone(s.tree);
      rec.parsePath = "LLM";
      rec.aiModel = "e2e-model";
      rec.tokenUsed = 1152;
      rec.lastParseErrors = undefined;
      return {
        data: { importId: rec.id, status: "PARSED", path: "LLM", parsedResult: rec.parsedResult, signedOff: false, aiModel: "e2e-model", tokenUsed: 1152, errors: [], warnings: [] },
        delayMs: s.parseDelayMs,
      };
    }

    if (method === "PUT" && action === "result") {
      if (s.putMode === "gate") {
        return { status: 422, error: { message: "解析結果未通過有界閘（3 項）", reason: "解析結果未通過有界閘", errors: GATE_ERRORS, details: { path: "LLM" } } };
      }
      const parsed = (call.body as { parsedResult: typeof TREE }).parsedResult;
      rec.parsedResult = { ...parsed, path: "LLM", aiModel: "e2e-model", tokenUsed: 1152 };
      rec.status = "REVIEWING";
      rec.signedOff = false;
      rec.signedOffBy = undefined;
      rec.signedOffAt = undefined;
      return {
        data: {
          importId: rec.id, status: "REVIEWING", path: "LLM", parsedResult: rec.parsedResult, signedOff: false, aiModel: "e2e-model", tokenUsed: 1152, errors: [],
          warnings: [{ code: "passcriteria_placeholder", detail: "通過標準為佔位字串，請於 signoff 前補齊", location: "goals[1].tasks[0]" }],
        },
      };
    }

    if (method === "POST" && action === "signoff") {
      const approver = ((call.body as { approver?: string }).approver ?? "").trim();
      if (!approver) return fail(400, { message: "驗證失敗", errors: [{ field: "approver", message: "approver 不可為空（人工 signoff 不可匿名）" }] });
      if (rec.signedOff) return fail(409, { message: "已簽核", reason: "已 signoff", details: { signedOffBy: rec.signedOffBy, signedOffAt: rec.signedOffAt } });
      rec.signedOff = true;
      rec.signedOffBy = approver;
      rec.signedOffAt = "2026-10-15T09:00:00Z";
      return { data: summary(rec) };
    }

    if (method === "POST" && action === "confirm") {
      if (!rec.signedOff) return fail(409, { message: "草案尚未 signoff", reason: "草案尚未 signoff，不可確認匯入", details: { status: rec.status, signedOff: false } });
      rec.status = "IMPORTED";
      rec.projectId = PROJECT_ID;
      return { status: 201, data: { id: PROJECT_ID, name: "E2E 匯入專案", executionPath: "/e2e/proj-import", passCriteria: "三個目標全部完成", status: "DRAFT", autonomyLevel: 4, signedOff: true, goalsCount: 2, tasksCount: 3 } };
    }

    if (method === "POST" && action === "reject") {
      rec.status = "REJECTED";
      return { data: summary(rec) };
    }
    return undefined;
  };
  return { s, handler, pending };
}

async function setup(page: Page, server: ReturnType<typeof createServer>, role: "ADMIN" | "OPERATOR" | "VIEWER" = "OPERATOR") {
  await signInAs(page, role);
  return installApiMock(page, compose(shellHandler(() => ({ pendingSignoffs: server.pending() })), server.handler));
}

/** 首次造訪頁面時 next dev 要編譯，給寬鬆的等待時間（之後的操作用預設 15 秒）。 */
const FIRST_LOAD = { timeout: 60_000 };


test.describe("BRD/PRD 匯入（route mock）", () => {
  test.setTimeout(150_000);

  test("貼上文字 → 解析 → 三層樹 → 編輯任務名 → 422 三條 gate → 修正儲存 → signoff → 確認匯入 → 專案頁", async ({ page }) => {
    const consoleErrors = collectConsoleErrors(page);
    const server = createServer();
    server.s.parseDelayMs = 1200;
    const { calls } = await setup(page, server);

    await page.goto("/import");
    await expect(page.getByRole("heading", { name: "BRD / PRD 智能匯入" })).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("import-step1")).toBeVisible();
    // 預設自治等級取自設定 agent.defaultAutonomyLevel（契約 §4.1 I-04）
    await expect(page.getByLabel("自治等級")).toHaveValue("4");

    // ── 步驟 1：貼上文字 ──
    await page.getByRole("tab", { name: "貼上文字" }).click();
    await page.getByLabel("需求文字").fill(BRD);
    await page.getByLabel("來源名稱").fill("e2e-brd.md");
    await page.getByLabel("格式").selectOption("MARKDOWN");
    await page.getByLabel("執行路徑").fill("/e2e/proj-import");
    await page.getByLabel("補充說明").fill("盡量少於 5 個任務");
    await snap(page, "06-import-step1.png");

    await page.getByRole("button", { name: "開始解析" }).click();
    // 解析中：spinner＋說明（設計稿 importParsing）
    await expect(page.getByTestId("import-parsing")).toBeVisible();
    await expect(page.getByTestId("import-parsing")).toContainText("AI 解析中…（套用有界閘：步驟 ≤24 / Kahn 無環 / prompt 非空）");
    await snap(page, "06-import-parsing.png");

    // ── 步驟 2：三層樹 ──
    await expect(page.getByTestId("import-step2")).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`/import\\?id=${IMPORT_ID}$`));
    await expect(page.getByTestId("project-name")).toHaveText("E2E 匯入專案");
    await expect(page.getByTestId("tree-goal")).toHaveCount(2);
    await expect(page.getByTestId("tree-task")).toHaveCount(3);
    await expect(page.getByTestId("task-name")).toHaveText(["初始化", "設定", "實作"]);
    await expect(page.getByTestId("parse-path")).toHaveText("AI 解析（LLM）");
    await expect(page.getByTestId("import-signoff-banner")).toContainText("signed_off=false");
    await expect(page.getByRole("button", { name: "確認匯入" })).toBeDisabled();
    // 匯入草案計入頂列 signoff 佇列徽章（pendingSignoffs 含 PARSED／REVIEWING 的匯入記錄）
    await expect(page.getByTestId("signoff-badge")).toHaveText("1");
    await page.getByRole("button", { name: "展開詳情：初始化" }).click();
    await expect(page.getByTestId("task-details")).toContainText("請輸出 [T1_DONE]");
    await snap(page, "06-import-step2.png", { tall: true });

    // 送出內容檢查：文字來源與解析選項（US-I-02／05／07／08）
    expect(calls.find((c) => c.path === "/api/v1/import/text")?.body).toEqual({ content: BRD, sourceFileName: "e2e-brd.md", sourceType: "MARKDOWN" });
    expect(calls.find((c) => c.path.endsWith("/parse"))?.body).toEqual({ autonomyLevel: 4, executionPath: "/e2e/proj-import", additionalPrompt: "盡量少於 5 個任務" });

    // ── 編輯一個任務名 → 出現未儲存提示，signoff／確認匯入都停用 ──
    await page.getByRole("button", { name: "編輯任務：設定" }).click();
    const dialog = page.getByRole("dialog", { name: "編輯任務" });
    await dialog.getByLabel("任務名稱").fill("設定環境");
    await dialog.getByRole("button", { name: "確定" }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByTestId("task-name")).toHaveText(["初始化", "設定環境", "實作"]);
    await expect(page.getByTestId("dirty-notice")).toBeVisible();
    await expect(page.getByRole("button", { name: "signoff 審批" })).toBeDisabled();
    await snap(page, "06-import-step2-edited.png", { tall: true });

    // ── 儲存遇到 422：三條 gate 全列、不截斷；指到的節點標紅 ──
    server.s.putMode = "gate";
    await page.getByRole("button", { name: "儲存編輯" }).click();
    const rows = page.getByTestId("gate-error-row");
    await expect(rows).toHaveCount(3);
    await expect(page.getByTestId("parse-failure-title")).toHaveText("解析結果未通過有界閘（共 3 項）");
    await expect(page.getByTestId("gate-error-detail")).toHaveText(GATE_ERRORS.map((e) => e.detail));
    await expect(page.getByTestId("gate-error-location")).toHaveText(GATE_ERRORS.map((e) => e.location));
    await expect(rows.nth(0)).toContainText("empty_prompt");
    await expect(rows.nth(1)).toContainText("max_steps");
    await expect(rows.nth(2)).toContainText("cycle");
    await expect(page.getByTestId("tree-goal").nth(0)).toHaveAttribute("data-highlighted", "true");
    await expect(page.getByTestId("tree-goal").nth(1)).toHaveAttribute("data-highlighted", "true");
    await expect(page.getByTestId("tree-task").nth(1)).toHaveAttribute("data-highlighted", "true");
    await expect(page.getByTestId("dirty-notice")).toBeVisible(); // 編輯還在，可修改後重試
    await snap(page, "06-import-gate-errors.png", { tall: true });

    // ── 修正後重試 → 儲存成功（狀態轉審核中、顯示解析提示）──
    server.s.putMode = "ok";
    await page.getByRole("button", { name: "儲存編輯" }).click();
    await expect(page.getByRole("status").filter({ hasText: "已儲存編輯" })).toBeVisible();
    await expect(page.getByTestId("dirty-notice")).toHaveCount(0);
    await expect(page.getByTestId("parse-failure")).toHaveCount(0);
    await expect(page.getByTestId("parse-warning")).toContainText("通過標準是佔位字串，signoff 前請補齊");
    await expect(page.getByTestId("import-status")).toHaveText("審核中");
    const put = calls.filter((c) => c.method === "PUT").at(-1)?.body as { parsedResult: typeof TREE };
    expect(put.parsedResult.goals[0].tasks.map((t) => t.name)).toEqual(["初始化", "設定環境"]);
    expect(put.parsedResult.goals[1].dependsOn).toEqual(["g1"]);

    // ── signoff：approver 預設帶目前使用者，成功後綠勾 ──
    await page.getByRole("button", { name: "signoff 審批" }).click();
    const signoff = page.getByRole("dialog", { name: "審批 signoff：匯入草案" });
    await expect(signoff.getByLabel("審批者")).toHaveValue("operator");
    await snap(page, "06-import-signoff-dialog.png");
    await signoff.getByRole("button", { name: "確認 signoff" }).click();
    await expect(page.getByTestId("import-signed-off")).toContainText("已 signoff");
    await expect(page.getByTestId("import-signed-off")).toContainText("審批者 operator");
    await expect(page.getByTestId("import-signoff-banner")).toHaveCount(0);
    await expect(page.getByTestId("signoff-badge")).toHaveCount(0); // 佇列清空
    await expect(page.getByRole("button", { name: "確認匯入" })).toBeEnabled();
    await snap(page, "06-import-signed-off.png", { tall: true });

    // ── 確認匯入 → 導向專案頁 ──
    await page.getByRole("button", { name: "確認匯入" }).click();
    await expect(page).toHaveURL(new RegExp(`/projects/${PROJECT_ID}$`));
    await expect(page.getByRole("heading", { name: /E2E 匯入專案/ })).toBeVisible();
    expect(calls.some((c) => c.method === "POST" && c.path === `/api/v1/import/${IMPORT_ID}/confirm`)).toBe(true);
    expect(consoleErrors, "整段流程不應有主控台錯誤（React 警告、被擋的請求、例外）").toEqual([]);
  });

  test("解析被有界閘擋下（422）：清單完整列出、保留已填的選項；改選項後直接重試（不重複建立記錄）", async ({ page }) => {
    const server = createServer();
    server.s.parseMode = "gate";
    const { calls } = await setup(page, server);
    await page.goto("/import");
    await expect(page.getByTestId("import-step1")).toBeVisible(FIRST_LOAD);

    await page.getByRole("tab", { name: "貼上文字" }).click();
    await page.getByLabel("需求文字").fill(BRD);
    await page.getByLabel("執行路徑").fill("/e2e/proj-import");
    await page.getByLabel("補充說明").fill("請拆細一點");
    await page.getByRole("button", { name: "開始解析" }).click();

    await expect(page.getByTestId("gate-error-row")).toHaveCount(3);
    await expect(page.getByTestId("parse-failure-title")).toHaveText("解析結果未通過有界閘（共 3 項）");
    await expect(page.getByTestId("gate-error-gate")).toHaveText(["prompt 不可為空", "步驟上限（≤ 24）", "依賴成環（Kahn 無環）"]);
    // 記錄已建立（UPLOADED），畫面改為沿用既有記錄；先前輸入的選項都還在
    await expect(page.getByTestId("existing-source")).toContainText("（貼上文字）");
    await expect(page.getByLabel("執行路徑")).toHaveValue("/e2e/proj-import");
    await expect(page.getByLabel("補充說明")).toHaveValue("請拆細一點");
    await snap(page, "06-import-parse-gate-failure.png", { tall: true });

    // 重試（這次通過）：只呼叫 parse，不會再建立第二筆記錄
    server.s.parseMode = "ok";
    await page.getByLabel("補充說明").fill("少於 5 個任務");
    await page.getByRole("button", { name: "開始解析" }).click();
    await expect(page.getByTestId("import-step2")).toBeVisible();
    expect(calls.filter((c) => c.method === "POST" && c.path === "/api/v1/import/text")).toHaveLength(1);
    expect(calls.filter((c) => c.path.endsWith("/parse"))).toHaveLength(2);
    await expect(page.getByTestId("parse-failure")).toHaveCount(0);
  });

  test("歷史記錄：列出時間／來源／狀態／專案連結／模型 Token；重開已解析的記錄，重新整理後仍還原；重開被擋下的記錄還原閘清單", async ({ page }) => {
    const parsed: Rec = { id: "aaaaaaaa-0000-4000-8000-000000000001", sourceType: "MARKDOWN", sourceFileName: "parsed.md", status: "PARSED", signedOff: false, createdAt: "2026-10-15T08:00:00Z", aiModel: "e2e-model", tokenUsed: 1152, parsePath: "LLM", sourceContent: "# parsed", parsedResult: structuredClone(TREE) };
    const stuck: Rec = {
      id: "aaaaaaaa-0000-4000-8000-000000000002", sourceType: "PLAIN_TEXT", status: "UPLOADED", signedOff: false, createdAt: "2026-10-15T07:00:00Z", sourceContent: "太長的需求文字", parsedResult: null,
      lastParseErrors: GATE_ERRORS.map(({ gate, detail, location }) => ({ gate, detail, location })),
    };
    const done: Rec = { id: "aaaaaaaa-0000-4000-8000-000000000003", sourceType: "PDF", sourceFileName: "done.pdf", status: "IMPORTED", signedOff: true, signedOffBy: "operator", projectId: PROJECT_ID, createdAt: "2026-10-14T09:00:00Z", aiModel: "e2e-model", tokenUsed: 2048, sourceContent: "x", parsedResult: structuredClone(TREE) };
    const dropped: Rec = { id: "aaaaaaaa-0000-4000-8000-000000000004", sourceType: "DOCX", sourceFileName: "dropped.docx", status: "REJECTED", signedOff: false, createdAt: "2026-10-13T09:00:00Z", sourceContent: "x", parsedResult: null };
    const server = createServer([parsed, stuck, done, dropped]);
    await setup(page, server);

    await page.goto("/import");
    await expect(page.getByTestId("import-step1")).toBeVisible(FIRST_LOAD);
    await page.getByRole("tab", { name: "歷史記錄" }).click();
    const rows = page.getByTestId("import-history-row");
    await expect(rows).toHaveCount(4);
    await expect(rows.nth(0)).toContainText("parsed.md");
    await expect(rows.nth(0)).toContainText("已解析");
    await expect(rows.nth(0)).toContainText("e2e-model · 1,152");
    await expect(rows.nth(1)).toContainText("（貼上文字）");
    await expect(rows.nth(1)).toContainText("已上傳");
    await expect(rows.nth(2)).toContainText("已匯入");
    await expect(rows.nth(2).getByRole("link", { name: "查看專案" })).toHaveAttribute("href", `/projects/${PROJECT_ID}`);
    await expect(rows.nth(3)).toContainText("已放棄");
    // 只有仍有下一步的記錄能開啟
    await expect(rows.nth(0).getByRole("button", { name: /^開啟匯入記錄/ })).toBeVisible();
    await expect(rows.nth(1).getByRole("button", { name: /^開啟匯入記錄/ })).toBeVisible();
    await expect(rows.nth(2).getByRole("button", { name: /^開啟匯入記錄/ })).toHaveCount(0);
    await expect(rows.nth(3).getByRole("button", { name: /^開啟匯入記錄/ })).toHaveCount(0);
    await snap(page, "06-import-history.png");

    // 開啟已解析的記錄 → 步驟 2；重新整理後仍還原（?id= ＋ GET /import/{id}）
    await rows.nth(0).getByRole("button", { name: /^開啟匯入記錄/ }).click();
    await expect(page.getByTestId("import-step2")).toBeVisible();
    await expect(page.getByTestId("tree-task")).toHaveCount(3);
    await page.reload();
    await expect(page.getByTestId("import-step2")).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("task-name")).toHaveText(["初始化", "設定", "實作"]);

    // 開啟被有界閘擋下的記錄 → 步驟 1（沿用既有記錄）＋還原 lastParseErrors 清單
    await page.goto("/import");
    await page.getByRole("tab", { name: "歷史記錄" }).click();
    await page.getByTestId("import-history-row").nth(1).getByRole("button", { name: /^開啟匯入記錄/ }).click();
    await expect(page.getByTestId("existing-source")).toBeVisible();
    await expect(page.getByTestId("gate-error-row")).toHaveCount(3);
    await expect(page.getByTestId("gate-error-detail").nth(2)).toHaveText("目標依賴成環：基礎 -> 核心 -> 基礎");
    await snap(page, "06-import-restored-gates.png", { tall: true });
  });

  test("上傳檔案：選檔（含拖放區說明）→ multipart 上傳 → 解析；副檔名不符當場擋下；後端 413 顯示 reason", async ({ page }) => {
    const server = createServer();
    const { calls } = await setup(page, server);
    await page.goto("/import");
    await expect(page.getByTestId("import-dropzone")).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("import-dropzone")).toContainText("拖曳檔案至此，或點擊選擇");
    await expect(page.getByTestId("import-dropzone")).toContainText("支援格式：.md · .pdf · .docx　|　檔案大小限制 10MB");
    await snap(page, "06-import-dropzone.png");

    const input = page.getByTestId("import-file-input");
    await input.setInputFiles({ name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("x") });
    await expect(page.getByTestId("source-error")).toHaveText("只支援 .md／.pdf／.docx 檔案");

    await input.setInputFiles({ name: "brd.md", mimeType: "text/markdown", buffer: Buffer.from("# 上傳的 BRD\n需求內容") });
    await expect(page.getByTestId("selected-file")).toContainText("brd.md");
    await expect(page.getByTestId("source-error")).toHaveCount(0);

    // 沒填執行路徑：行內錯誤，不呼叫後端
    await page.getByRole("button", { name: "開始解析" }).click();
    await expect(page.getByText("執行路徑不能為空")).toBeVisible();
    expect(calls.some((c) => c.path === "/api/v1/import/upload")).toBe(false);

    // 後端 413：reason 顯示在拖放區下方
    server.s.uploadStatus = 413;
    await page.getByLabel("執行路徑").fill("/e2e/proj-import");
    await page.getByRole("button", { name: "開始解析" }).click();
    await expect(page.getByTestId("source-error")).toContainText("檔案超過 10MB 上限");
    await expect(page.getByTestId("source-error")).toContainText("traceId：tr-mock-413");
    await snap(page, "06-import-upload-error.png");

    // 改回成功：multipart 欄位 file，Content-Type 帶 boundary（由瀏覽器產生）
    server.s.uploadStatus = 201;
    await page.getByRole("button", { name: "開始解析" }).click();
    await expect(page.getByTestId("import-step2")).toBeVisible();
    const upload = calls.filter((c) => c.path === "/api/v1/import/upload").at(-1);
    expect(upload?.contentType).toMatch(/^multipart\/form-data; boundary=/);
    expect((upload?.body as { raw: string }).raw).toContain('filename="brd.md"');
    expect((upload?.body as { raw: string }).raw).toContain("上傳的 BRD");
  });

  test("放棄：確認對話框 → REJECTED → 回到新的匯入", async ({ page }) => {
    const server = createServer();
    const { calls } = await setup(page, server);
    await page.goto("/import");
    await expect(page.getByTestId("import-step1")).toBeVisible(FIRST_LOAD);
    await page.getByRole("tab", { name: "貼上文字" }).click();
    await page.getByLabel("需求文字").fill(BRD);
    await page.getByLabel("執行路徑").fill("/e2e/proj-import");
    await page.getByRole("button", { name: "開始解析" }).click();
    await expect(page.getByTestId("import-step2")).toBeVisible();

    await page.getByRole("button", { name: "放棄" }).click();
    const dialog = page.getByRole("dialog", { name: "放棄這份匯入草案？" });
    await dialog.getByRole("button", { name: "放棄" }).click();
    await expect(page.getByRole("status").filter({ hasText: "已放棄匯入" })).toBeVisible();
    await expect(page).toHaveURL(/\/import$/);
    await expect(page.getByTestId("import-step1")).toBeVisible();
    await expect(page.getByTestId("import-step2")).toHaveCount(0);
    expect(calls.some((c) => c.method === "POST" && c.path.endsWith("/reject"))).toBe(true);
  });

  test("唯讀角色（VIEWER）：看得到頁面與歷史，但拖放區、欄位與開始解析全部停用", async ({ page }) => {
    const server = createServer();
    await setup(page, server, "VIEWER");
    await page.goto("/import");
    await expect(page.getByTestId("import-dropzone")).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("import-dropzone")).toBeDisabled();
    await expect(page.getByRole("button", { name: "開始解析" })).toBeDisabled();
    await expect(page.getByLabel("執行路徑")).toBeDisabled();
    await page.getByRole("tab", { name: "歷史記錄" }).click();
    await expect(page.getByTestId("import-history-panel")).toBeVisible();
  });
});
