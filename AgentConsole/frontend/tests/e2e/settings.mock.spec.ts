import { readFileSync } from "node:fs";

import { expect, test, type Page } from "@playwright/test";

import { expectNoA11yViolations } from "./a11y";
import { collectConsoleErrors, compose, fail, installApiMock, shellHandler, signInAs, snap, type MockHandler } from "./mockApi";
import { CATEGORIES, MASK, createSettingsServer } from "./settingsFixture";

/**
 * 系統參數設定頁（畫面 9）——route mock 版，不需要後端：50 個鍵依契約附錄 C，寫入端點行為依契約 §1.5
 * （ADMIN 專屬、加密參數須 confirm、token_guard 跨鍵校驗、逐筆歷史）。
 * 驗：六個分類 tab、改一個數值儲存、敏感鍵二次確認、Token Guard 的 400、測試連線、匯出下載、匯入、重置、揭露、唯讀角色。
 */
const FIRST_LOAD = { timeout: 60_000 };
const KEY_COUNTS = [10, 9, 10, 6, 11, 4];
const TAB_LABELS = ["模型", "Agent", "執行", "監控", "AutoClaude", "SDD"];

async function open(page: Page, role: "ADMIN" | "OPERATOR" | "VIEWER" = "ADMIN") {
  const consoleErrors = collectConsoleErrors(page);
  const server = createSettingsServer(role);
  await signInAs(page, role);
  const { calls } = await installApiMock(page, compose(shellHandler(), server.handler as MockHandler));
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "系統參數設定" })).toBeVisible(FIRST_LOAD);
  await expect(page.getByTestId("settings-panel")).toBeVisible();
  return { server, calls, consoleErrors };
}

const row = (page: Page, id: string) => page.locator(`[data-setting="${id}"]`);
const toast = (page: Page, text: string) => page.getByRole("status").filter({ hasText: text });

test.describe("系統參數設定（route mock）", () => {
  test.setTimeout(120_000);

  test("六個分類 tab 都能切換：標題、參數列數與契約附錄 C 一致；執行 tab 的 Token Guard 成對編輯", async ({ page }) => {
    const { consoleErrors } = await open(page);
    await expect(page.getByRole("tab")).toHaveText(TAB_LABELS);
    await expect(page.getByRole("tab", { name: "模型" })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByRole("button", { name: "匯出設定" })).toBeEnabled();
    await expect(page.getByRole("button", { name: "匯入設定" })).toBeEnabled();
    await expectNoA11yViolations(page, "系統設定（模型 tab）");
    await snap(page, "09-settings-model.png", { tall: true });

    for (const [i, label] of TAB_LABELS.entries()) {
      await page.getByRole("tab", { name: label, exact: true }).click();
      await expect(page.getByRole("heading", { name: `${label}設定` })).toBeVisible();
      await expect(page.getByTestId("setting-row")).toHaveCount(KEY_COUNTS[i]);
      await expect(page.getByRole("tabpanel")).toBeVisible();
    }

    // 控制項依 valueType：模型 tab 的 ENUM／ENCRYPTED／INTEGER／FLOAT／BOOLEAN
    await page.getByRole("tab", { name: "模型" }).click();
    await expect(row(page, "model.provider").getByRole("combobox")).toHaveValue("ANTHROPIC");
    await expect(row(page, "model.apiKey").getByLabel("API Key", { exact: true })).toHaveAttribute("type", "password");
    await expect(row(page, "model.apiKey").getByLabel("API Key", { exact: true })).toHaveValue(MASK);
    await expect(row(page, "model.maxTokensPerRequest").getByRole("textbox")).toHaveAttribute("inputmode", "numeric");
    await expect(row(page, "model.temperature").getByRole("textbox")).toHaveAttribute("inputmode", "decimal");
    await expect(row(page, "model.enableKernelBrain").getByRole("switch")).toHaveAttribute("aria-checked", "false");
    // 影響提示與誠實標示（US-S-08）
    await expect(row(page, "model.apiUrl").getByTestId("impact-note")).toContainText("完整的 chat-completions 端點 URL");
    await expect(row(page, "model.apiUrl").getByTestId("setting-hint")).toContainText("完整的 chat-completions 端點 URL");
    await expect(row(page, "model.provider").getByTestId("effect-tag")).toHaveText("僅儲存、不影響引擎");

    // 執行 tab：Token Guard 小卡
    await page.getByRole("tab", { name: "執行" }).click();
    const guard = page.getByTestId("token-guard-card");
    await expect(guard.getByLabel("壓縮門檻（%）", { exact: true })).toHaveValue("80");
    await expect(guard.getByLabel("停機門檻（%）", { exact: true })).toHaveValue("90");
    await expect(guard.getByRole("button", { name: "套用 Token Guard" })).toBeDisabled();
    await expectNoA11yViolations(page, "系統設定（執行 tab，含 Token Guard 小卡與修改歷史）");
    await snap(page, "09-settings-execution.png", { tall: true });

    // 監控 tab：refreshIntervalMs 最小 10000
    await page.getByRole("tab", { name: "監控" }).click();
    await expect(row(page, "monitor.refreshIntervalMs").getByTestId("setting-hint")).toContainText("最小 10000");
    await snap(page, "09-settings-monitor.png");

    // 鍵盤：方向鍵在 tab 間移動並切換
    await page.getByRole("tab", { name: "監控" }).focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: "AutoClaude" })).toHaveAttribute("aria-selected", "true");
    expect(CATEGORIES).toHaveLength(6);
    expect(consoleErrors, "整段流程不應有主控台錯誤").toEqual([]);
  });

  test("Agent tab 的兩個引擎旗標（契約 v1.3，D-11；S-13）：enableAutoMutation 為 ENGINE＝沒有小標籤、影響說明寫 Brain 逐步校正；enableSelfEvolution 為 STORED_ONLY＝加「僅儲存、不影響引擎」", async ({
    page,
  }) => {
    const { consoleErrors } = await open(page);
    await page.getByRole("tab", { name: "Agent", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Agent設定" })).toBeVisible();

    const mutation = row(page, "agent.enableAutoMutation");
    await expect(mutation.getByTestId("effect-tag")).toHaveCount(0); // ENGINE 與 CONSOLE 的鍵不加小標籤
    await expect(mutation.getByTestId("impact-note")).toContainText("Brain 逐步校正：失敗步驟先改寫 prompt 再重試");
    await expect(mutation.getByTestId("impact-note")).toContainText("沒有金鑰時不送，批次回報 UNAVAILABLE_NO_API_KEY");
    await expect(mutation).not.toContainText("尚未驗證對映");

    const evolution = row(page, "agent.enableSelfEvolution");
    await expect(evolution.getByTestId("effect-tag")).toHaveText("僅儲存、不影響引擎");
    await expect(evolution.getByTestId("impact-note")).toContainText("引擎沒有演化開關");
    await expect(evolution.getByTestId("impact-note")).toContainText("只寫引擎日誌、不套用也不重載");

    await expectNoA11yViolations(page, "系統設定（Agent tab：引擎旗標的標籤與影響說明）");
    expect(consoleErrors, "整段流程不應有主控台錯誤").toEqual([]);
  });

  test("改一個數值並儲存：只送有變動的鍵；成功 toast；修改歷史多一列", async ({ page }) => {
    const { calls, consoleErrors } = await open(page);
    const input = row(page, "model.maxTokensPerRequest").getByRole("textbox");
    await input.fill("4096");
    await expect(page.getByTestId("unsaved-count")).toHaveText("1 項變更尚未儲存");
    await expect(row(page, "model.maxTokensPerRequest")).toHaveAttribute("data-dirty", "true");
    await page.getByRole("button", { name: "儲存變更" }).click();

    await expect(toast(page, "已儲存 1 項參數")).toBeVisible();
    const puts = calls.filter((c) => c.method === "PUT");
    expect(puts).toHaveLength(1);
    expect(puts[0].path).toBe("/api/v1/settings/model/maxTokensPerRequest");
    expect(puts[0].body).toEqual({ value: "4096" });
    await expect(page.getByTestId("unsaved-count")).toHaveCount(0);
    await expect(input).toHaveValue("4096");
    // 修改歷史（等寬字體）：最新一列在最上面
    const first = page.getByTestId("history-line").first();
    await expect(first).toContainText("model.maxTokensPerRequest");
    await expect(first).toContainText("8192 → 4096");
    await expect(first).toContainText("@admin");
    await expect(page.getByTestId("history-line").first()).toHaveCSS("font-family", /JetBrains Mono|monospace/);
    await snap(page, "09-settings-saved.png", { tall: true });

    // 本地驗證紅字：超出範圍就地提示、儲存被擋（不送請求）
    const before = calls.length;
    await row(page, "model.temperature").getByRole("textbox").fill("3");
    await expect(row(page, "model.temperature").getByTestId("setting-error")).toHaveText("需為數字（0～2）");
    await page.getByRole("button", { name: "儲存變更" }).click();
    await expect(toast(page, "有 1 項參數不合法，請先修正紅字欄位")).toBeVisible();
    expect(calls.slice(before).filter((c) => c.method === "PUT")).toHaveLength(0);
    expect(consoleErrors, "整段流程不應有主控台錯誤").toEqual([]);
  });

  test("敏感鍵（API Key）：儲存前二次確認，確認後以 confirm=true 送出；歷史只記遮罩", async ({ page }) => {
    const { calls } = await open(page);
    const key = row(page, "model.apiKey").getByLabel("API Key", { exact: true });
    await key.click(); // 聚焦遮罩欄位會全選，輸入直接取代
    await page.keyboard.type("sk-new-secret-7788");
    await page.getByRole("button", { name: "儲存變更" }).click();

    const dialog = page.getByRole("dialog", { name: "確認更新敏感參數" });
    await expect(dialog).toContainText("API Key");
    await expect(dialog.getByTestId("confirm-impact-notes")).toContainText("加密儲存；新批次起使用新金鑰");
    await snap(page, "09-settings-sensitive-confirm.png");
    // 先取消：不送、草稿保留
    await dialog.getByRole("button", { name: "取消" }).click();
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(0);
    await expect(page.getByTestId("unsaved-count")).toBeVisible();

    await page.getByRole("button", { name: "儲存變更" }).click();
    await page.getByRole("dialog", { name: "確認更新敏感參數" }).getByRole("button", { name: "確認儲存" }).click();
    await expect(toast(page, "已儲存 1 項參數")).toBeVisible();
    const put = calls.find((c) => c.method === "PUT");
    expect(put?.path).toBe("/api/v1/settings/model/apiKey");
    expect(put?.body).toEqual({ value: "sk-new-secret-7788", confirm: true });
    await expect(page.getByTestId("history-line").first()).toContainText(`${MASK} → ${MASK}`);
    await expect(page.getByTestId("history-line").first()).not.toContainText("sk-new-secret");
    // 儲存後欄位回到遮罩，不殘留明文
    await expect(row(page, "model.apiKey").getByLabel("API Key", { exact: true })).toHaveValue(MASK);
  });

  test("API Key「顯示」：ADMIN 以 reveal=true 取明文，隱藏後回遮罩", async ({ page }) => {
    const { calls } = await open(page);
    await row(page, "model.apiKey").getByRole("button", { name: "顯示：API Key" }).click();
    await expect(row(page, "model.apiKey").getByLabel("API Key", { exact: true })).toHaveValue("sk-plain-secret-0042");
    await expect(row(page, "model.apiKey").getByLabel("API Key", { exact: true })).toHaveAttribute("type", "text");
    expect(calls.filter((c) => c.query.get("reveal") === "true").map((c) => c.path)).toEqual(["/api/v1/settings/model"]);
    await expect(page.getByTestId("unsaved-count")).toHaveCount(0); // 揭露不算變更
    await row(page, "model.apiKey").getByRole("button", { name: "隱藏：API Key" }).click();
    await expect(row(page, "model.apiKey").getByLabel("API Key", { exact: true })).toHaveAttribute("type", "password");
    // 尚未設定的加密鍵：顯示鈕停用
    await page.getByRole("tab", { name: "AutoClaude" }).click();
    await expect(row(page, "autoclaude.dbDsn").getByRole("button", { name: "顯示：資料庫連線字串（DSN）" })).toBeDisabled();
  });

  test("Token Guard：前端鏡射跨鍵規則（不送請求）；後端 400 顯示 reason；成對套用一次 PUT", async ({ page }) => {
    const { server, calls, consoleErrors } = await open(page);
    await page.getByRole("tab", { name: "執行" }).click();
    const guard = page.getByTestId("token-guard-card");

    // ① halt 不大於 compact：就地顯示逐字 reason，套用停用，不送請求
    await guard.getByLabel("停機門檻（%）", { exact: true }).fill("60");
    await expect(guard.getByTestId("token-guard-error")).toHaveText("halt_threshold_pct 必須大於 compact_threshold_pct");
    await expect(guard.getByRole("button", { name: "套用 Token Guard" })).toBeDisabled();
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(0);

    // ② 前端放行但後端 400（伺服器上的值剛被別人改過）：顯示 reason、欄位訊息與 traceId，草稿保留
    server.s.force.push((c) =>
      c.method === "PUT" && c.path.endsWith("/token-guard")
        ? fail(400, {
            message: "token_guard 跨鍵校驗失敗",
            reason: "halt_threshold_pct 必須大於 compact_threshold_pct",
            errors: [{ field: "haltThresholdPct", message: "必須大於 compactThresholdPct" }],
            details: { compactThresholdPct: 70, haltThresholdPct: 95 },
          })
        : undefined,
    );
    await guard.getByLabel("壓縮門檻（%）", { exact: true }).fill("70");
    await guard.getByLabel("停機門檻（%）", { exact: true }).fill("95");
    await expect(guard.getByTestId("token-guard-error")).toHaveCount(0);
    await guard.getByRole("button", { name: "套用 Token Guard" }).click();
    await expect(guard.getByTestId("token-guard-error")).toContainText("halt_threshold_pct 必須大於 compact_threshold_pct");
    await expect(guard.getByTestId("token-guard-error")).toContainText("必須大於 compactThresholdPct");
    await expect(guard.getByTestId("token-guard-error")).toContainText("traceId：tr-mock-400");
    await expect(guard.getByLabel("停機門檻（%）", { exact: true })).toHaveValue("95");
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(1);
    await snap(page, "09-settings-token-guard-400.png", { tall: true });

    // ③ 後端恢復：同一組值成功套用，原子 PUT 帶兩個整數
    server.s.force.length = 0;
    await guard.getByRole("button", { name: "套用 Token Guard" }).click();
    await expect(toast(page, "已套用 Token Guard")).toBeVisible();
    const last = calls.filter((c) => c.method === "PUT").at(-1);
    expect(last?.path).toBe("/api/v1/settings/execution/token-guard");
    expect(last?.body).toEqual({ compactThresholdPct: 70, haltThresholdPct: 95 });
    await expect(guard.getByTestId("token-guard-error")).toHaveCount(0);
    await expect(page.getByTestId("unsaved-count")).toHaveCount(0);
    expect(consoleErrors, "整段流程不應有主控台錯誤").toEqual([]);
  });

  test("測試連線：測試中 spinner → 綠勾「連線成功（延遲 230ms）」；失敗與 SSRF 拒絕顯示紅字原因；可帶尚未儲存的值", async ({ page }) => {
    const { server, calls } = await open(page);
    server.s.force.push(async (c) => {
      if (c.path !== "/api/v1/settings/test-connection") return undefined;
      return { data: server.s.testConnection, delayMs: 800 };
    });
    await page.getByRole("button", { name: "測試連線" }).click();
    await expect(page.getByTestId("test-connection-result")).toContainText("測試中…");
    await expect(page.getByTestId("test-connection-result")).toContainText("連線成功（延遲 230ms）");
    await snap(page, "09-settings-test-connection.png", { tall: true });
    expect(calls.find((c) => c.path.endsWith("/test-connection"))?.body).toBeUndefined(); // 沒改過 → 取已儲存值

    // 帶表單內尚未儲存的 apiUrl／apiKey；後端回 success=false（認證失敗）
    server.s.force.length = 0;
    server.s.testConnection = { success: false, latencyMs: null, message: "認證失敗（HTTP 401）", resolvedHost: "api.minimax.io", httpStatus: 401 };
    await row(page, "model.apiUrl").getByRole("textbox").fill("https://api.minimax.io/v1/chat");
    await row(page, "model.apiKey").getByLabel("API Key", { exact: true }).click();
    await page.keyboard.type("sk-typed-key");
    await page.getByRole("button", { name: "測試連線" }).click();
    await expect(page.getByTestId("test-connection-result")).toContainText("連線失敗：認證失敗（HTTP 401）");
    expect(calls.filter((c) => c.path.endsWith("/test-connection")).at(-1)?.body).toEqual({
      apiUrl: "https://api.minimax.io/v1/chat",
      apiKey: "sk-typed-key",
    });

    // 422：私網位址被 SSRF 規則拒絕（沒有任何連線）
    server.s.force.push((c) =>
      c.path === "/api/v1/settings/test-connection"
        ? fail(422, { message: "位址被拒", reason: "目標位址未通過 SSRF／allowlist 檢查", details: { host: "10.0.0.5", violation: "private_ip" } })
        : undefined,
    );
    await page.getByRole("button", { name: "測試連線" }).click();
    await expect(page.getByTestId("test-connection-result")).toContainText("目標位址未通過 SSRF／allowlist 檢查（不可連到私有網段位址；host：10.0.0.5）");
  });

  test("匯出設定：POST export 下載 JSON（50 個鍵、加密參數為 <encrypted>）；匯入設定：上傳 JSON 顯示 applied／skipped／errors", async ({ page }) => {
    const { calls } = await open(page);
    const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "匯出設定" }).click()]);
    expect(download.suggestedFilename()).toBe("aisdlc-settings-20261015.json");
    const doc = JSON.parse(readFileSync((await download.path()) as string, "utf-8")) as { version: number; configs: Array<{ category: string; key: string; value: string }> };
    expect(doc.version).toBe(1);
    expect(doc.configs).toHaveLength(50);
    expect(doc.configs.find((c) => c.key === "apiKey")?.value).toBe("<encrypted>");
    expect(doc.configs.find((c) => c.key === "temperature")?.value).toBe("0.5");
    await expect(toast(page, "已匯出設定")).toBeVisible();
    expect(calls.find((c) => c.path === "/api/v1/settings/export")?.method).toBe("POST");

    await page.getByRole("button", { name: "匯入設定" }).click();
    const dialog = page.getByRole("dialog", { name: "匯入設定" });
    // 非 .json 當場擋下
    await dialog.getByTestId("settings-file-input").setInputFiles({ name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("x") });
    await expect(dialog.getByRole("alert")).toHaveText("只接受 JSON 設定檔");
    await expect(dialog.getByRole("button", { name: "匯入", exact: true })).toBeDisabled();
    await dialog.getByTestId("settings-file-input").setInputFiles({ name: "aisdlc-settings.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify({ version: 1, configs: [] })) });
    await expect(dialog.getByTestId("settings-selected-file")).toContainText("aisdlc-settings.json");
    await dialog.getByRole("button", { name: "匯入", exact: true }).click();
    const result = dialog.getByTestId("settings-import-result");
    await expect(result.getByTestId("import-applied")).toHaveText("2");
    await expect(result.getByTestId("import-skipped")).toHaveText("47");
    await expect(result.getByTestId("import-failed")).toHaveText("1");
    await expect(result.getByTestId("settings-import-error")).toContainText("monitor.refreshIntervalMs — 參數值不符合型別或驗證規則");
    const upload = calls.find((c) => c.path === "/api/v1/settings/import");
    expect(upload?.contentType).toMatch(/^multipart\/form-data; boundary=/);
    expect((upload?.body as { raw: string }).raw).toContain('filename="aisdlc-settings.json"');
    await snap(page, "09-settings-import.png");
  });

  test("重置：單鍵（一般參數直接、敏感參數先確認並帶 confirm=true）；全部重置對六個分類各呼叫一次", async ({ page }) => {
    const { calls } = await open(page);
    // 一般參數
    await page.getByRole("tab", { name: "執行" }).click();
    await expect(row(page, "execution.dagSchedulerStrategy").getByRole("button", { name: "重置：DAG 排程策略" })).toBeDisabled(); // 已是預設值
    await row(page, "execution.globalTokenBudget").getByRole("button", { name: "重置：全域 Token 預算" }).click();
    await expect(toast(page, "已重置為預設值：全域 Token 預算")).toBeVisible();
    expect(calls.find((c) => c.method === "POST")?.path).toBe("/api/v1/settings/execution/globalTokenBudget/reset");
    await expect(row(page, "execution.globalTokenBudget").getByRole("textbox")).toHaveValue("1000000");

    // 敏感參數：先確認
    await page.getByRole("tab", { name: "模型" }).click();
    await row(page, "model.apiKey").getByRole("button", { name: "重置：API Key" }).click();
    const confirm = page.getByRole("dialog", { name: "確認重置敏感參數" });
    await expect(confirm).toContainText("API Key");
    await confirm.getByRole("button", { name: "確認重置" }).click();
    await expect(toast(page, "已重置為預設值：API Key")).toBeVisible();
    expect(
      calls
        .filter((c) => c.method === "POST")
        .at(-1)
        ?.query.get("confirm"),
    ).toBe("true");
    await expect(row(page, "model.apiKey").getByLabel("API Key", { exact: true })).toHaveValue("");

    // 全部重置：六個分類各呼叫一次分類級 reset
    calls.length = 0;
    await page.getByRole("button", { name: "全部重置為預設值" }).click();
    const all = page.getByRole("dialog", { name: "全部重置為預設值" });
    await snap(page, "09-settings-reset-all.png");
    await all.getByRole("button", { name: "全部重置" }).click();
    await expect(toast(page, "已把全部分類重置為預設值")).toBeVisible();
    expect(calls.filter((c) => c.method === "POST").map((c) => c.path)).toEqual(CATEGORIES.map((c) => `/api/v1/settings/${c}/reset`));
    await page.getByRole("tab", { name: "監控" }).click();
    await expect(row(page, "monitor.refreshIntervalMs").getByRole("textbox")).toHaveValue("10000");
  });

  test("唯讀角色（OPERATOR／VIEWER）：看得到參數與歷史，但輸入、重置、儲存、匯出入、測試連線全部停用", async ({ page }) => {
    await open(page, "VIEWER");
    await expect(page.getByTestId("readonly-banner")).toContainText("目前角色（VIEWER）只能檢視系統參數");
    await expect(row(page, "model.maxTokensPerRequest").getByRole("textbox")).toBeDisabled();
    await expect(row(page, "model.enableKernelBrain").getByRole("switch")).toBeDisabled();
    await expect(row(page, "model.apiKey").getByRole("button", { name: "顯示：API Key" })).toBeDisabled();
    await expect(row(page, "model.apiKey").getByRole("button", { name: "顯示：API Key" })).toHaveAttribute("title", "僅 ADMIN 可揭露敏感參數");
    for (const name of ["儲存變更", "全部重置為預設值", "匯出設定", "匯入設定", "測試連線"]) {
      await expect(page.getByRole("button", { name })).toBeDisabled();
    }
    await expect(page.getByTestId("history-line").first()).toBeVisible();
    await snap(page, "09-settings-readonly.png", { tall: true });
  });
});
