import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { API_URL, RUN } from "./helpers";
import { collectConsoleErrors, snap } from "./mockApi";
import { E2E_ROOT, FakeLlm, NEEDS_BRIDGE, bootstrapSettings, call, dataOf, ensureQuota, signIn, tokenOf, type Json } from "./realBackend";

/**
 * Phase 6 系統設定（畫面 9）——對真後端（console-api＋PG）：50 鍵、Token Guard 跨鍵校驗、敏感值二次確認與 reveal、
 * 測試連線（假 OpenAI 相容伺服器；私網位址被 SSRF 規則拒絕）、匯出入、重置、修改歷史、角色（契約 §5 E2E-09、E2E-10）。
 * 每個情境結束都把動過的鍵還原；全檔結束再把執行類情境需要的前置（替身引擎等）補回（契約 §5.0.2）。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const FIRST_LOAD = { timeout: 60_000 };
const MOCK_CLAUDE = path.resolve(process.cwd(), "..", "..", ".venv", process.platform === "win32" ? "Scripts/aisdlc-mock-claude.exe" : "bin/aisdlc-mock-claude");
const KEY_COUNTS = [10, 9, 10, 6, 11, 4];
const TAB_LABELS = ["模型", "Agent", "執行", "監控", "AutoClaude", "SDD"];
const MASK = "••••••••";

const row = (page: Page, id: string) => page.locator(`[data-setting="${id}"]`);
const toast = (page: Page, text: string) => page.getByRole("status").filter({ hasText: text });

async function openSettings(page: Page, request: APIRequestContext, role: "admin" | "operator" | "viewer" = "admin") {
  await signIn(page, request, role);
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "系統參數設定" })).toBeVisible(FIRST_LOAD);
  await expect(page.getByTestId("settings-panel")).toBeVisible();
}

type Cfg = { category: string; key: string; value: string; defaultValue: string; hasValue: boolean; isEncrypted: boolean; effect: string; min?: number | null; max?: number | null };
const settingsOf = async (request: APIRequestContext, role: "admin" | "operator" | "viewer", category: string, reveal = false): Promise<Cfg[]> =>
  dataOf<Cfg[]>(await call(request, role, "GET", `/api/v1/settings/${category}${reveal ? "?reveal=true" : ""}`));

let llm: FakeLlm;

test.describe.configure({ mode: "serial" });

test.beforeAll(async () => {
  llm = new FakeLlm(`QA 設定 ${RUN}`);
  await llm.listen();
});

test.afterAll(async ({ request }) => {
  await llm.close();
  // 還原：模型端點／金鑰、token_guard 兩鍵、執行類情境的前置（契約 §5.0.2）
  await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true");
  await call(request, "admin", "POST", "/api/v1/settings/model/apiUrl/reset");
  await call(request, "admin", "POST", "/api/v1/settings/monitor/refreshIntervalMs/reset");
  await call(request, "admin", "PUT", "/api/v1/settings/execution/token-guard", { compactThresholdPct: 80, haltThresholdPct: 90 });
  await bootstrapSettings(request, MOCK_CLAUDE);
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "admin", 40);
});

test.describe("系統參數設定（真後端）", () => {
  test.setTimeout(240_000);

  test("六個分類 tab：參數列數、標題、控制項型別、影響提示與誠實標示；加密鍵一律遮罩（US-S-01／04／08）", async ({ page, request }) => {
    const errors = collectConsoleErrors(page);
    await openSettings(page, request);
    await expect(page.getByRole("tab")).toHaveText(TAB_LABELS);
    for (const [i, label] of TAB_LABELS.entries()) {
      await page.getByRole("tab", { name: label, exact: true }).click();
      await expect(page.getByRole("heading", { name: `${label}設定` })).toBeVisible();
      await expect(page.getByTestId("setting-row")).toHaveCount(KEY_COUNTS[i]);
    }
    await page.getByRole("tab", { name: "模型", exact: true }).click();
    await expect(row(page, "model.apiKey").getByLabel("API Key", { exact: true })).toHaveAttribute("type", "password");
    // 尚未設定的加密鍵（hasValue=false）畫面顯示空白（F1-6：以 hasValue 判斷「尚未設定」）；設了值之後才是遮罩（見敏感鍵情境）
    await expect(row(page, "model.apiKey").getByLabel("API Key", { exact: true })).toHaveValue("");
    await expect(row(page, "model.apiUrl").getByTestId("impact-note")).toContainText("完整的 chat-completions 端點 URL");
    await expect(row(page, "model.maxTokensPerRequest").getByRole("textbox")).toHaveAttribute("inputmode", "numeric");
    await expect(row(page, "model.enableKernelBrain").getByRole("switch")).toHaveAttribute("aria-checked", "false");
    await snap(page, "p6-settings-model.png", { tall: true });
    await page.getByRole("tab", { name: "執行", exact: true }).click();
    const guard = page.getByTestId("token-guard-card");
    await expect(guard.getByLabel("壓縮門檻（%）", { exact: true })).toHaveValue("80");
    await expect(guard.getByLabel("停機門檻（%）", { exact: true })).toHaveValue("90");
    await snap(page, "p6-settings-execution.png", { tall: true });
    await page.getByRole("tab", { name: "監控", exact: true }).click();
    await expect(row(page, "monitor.refreshIntervalMs").getByTestId("setting-hint")).toContainText("最小 10000");
    await page.getByRole("tab", { name: "AutoClaude", exact: true }).click();
    await expect(row(page, "autoclaude.claudeCommand").getByRole("textbox")).toHaveValue(MOCK_CLAUDE);
    // API 對照（契約 E2E-09 步驟 1）：五十鍵、六分類計數、每筆都有 effect；加密鍵遮罩且 hasValue
    const all = dataOf<Record<string, Cfg[]>>(await call(request, "viewer", "GET", "/api/v1/settings"));
    expect(Object.keys(all)).toEqual(["model", "agent", "execution", "monitor", "autoclaude", "sdd"]);
    expect(Object.values(all).map((v) => v.length)).toEqual(KEY_COUNTS);
    expect(
      Object.values(all)
        .flat()
        .every((c) => !!c.effect),
    ).toBe(true);
    const apiKey = all.model.find((c) => c.key === "apiKey")!;
    expect(apiKey).toMatchObject({ value: MASK, isEncrypted: true, hasValue: false });
    expect(all.monitor.find((c) => c.key === "refreshIntervalMs")).toMatchObject({ value: "10000", defaultValue: "10000", min: 10000 });
    expect(all.model.find((c) => c.key === "apiUrl")!.defaultValue).toBe("https://api.minimax.io/v1/text/chatcompletion_v2");
    expect(errors, "整段流程不應有主控台錯誤").toEqual([]);
  });

  test("改一個數值並儲存（只送有變動的鍵）→ 歷史多一列 → 重置；本地驗證紅字不送請求（US-S-02／03／07）", async ({ page, request }) => {
    await openSettings(page, request);
    const key = row(page, "model.maxTokensPerRequest").getByRole("textbox");
    const before = (await settingsOf(request, "admin", "model")).find((c) => c.key === "maxTokensPerRequest")!;
    await key.fill("4096");
    await expect(page.getByTestId("unsaved-count")).toHaveText("1 項變更尚未儲存");
    const putPromise = page.waitForRequest((r) => r.method() === "PUT" && r.url().endsWith("/api/v1/settings/model/maxTokensPerRequest"));
    await page.getByRole("button", { name: "儲存變更" }).click();
    const put = await putPromise;
    expect(put.postDataJSON()).toEqual({ value: "4096" });
    await expect(toast(page, "已儲存 1 項參數")).toBeVisible();
    const first = page.getByTestId("history-line").first();
    await expect(first).toContainText("model.maxTokensPerRequest");
    await expect(first).toContainText(`${before.value} → 4096`);
    await expect(first).toContainText("@admin");
    await snap(page, "p6-settings-saved.png", { tall: true });
    // 後端歷史（新→舊）
    const history = dataOf<{ content: Array<{ category: string; key: string; oldValue: string; newValue: string; changedBy: string }> }>(
      await call(request, "viewer", "GET", "/api/v1/settings/history?category=model&key=maxTokensPerRequest&size=2"),
    );
    expect(history.content[0]).toMatchObject({ category: "model", key: "maxTokensPerRequest", oldValue: before.value, newValue: "4096", changedBy: "admin" });
    // 本地驗證紅字（溫度 0～2）：不送請求
    const puts: string[] = [];
    page.on("request", (r) => {
      if (r.method() === "PUT") puts.push(r.url());
    });
    await row(page, "model.temperature").getByRole("textbox").fill("3");
    await expect(row(page, "model.temperature").getByTestId("setting-error")).toHaveText("需為數字（0～2）");
    await page.getByRole("button", { name: "儲存變更" }).click();
    await expect(toast(page, "有 1 項參數不合法，請先修正紅字欄位")).toBeVisible();
    expect(puts).toEqual([]);
    // 重置：單鍵
    await row(page, "model.temperature").getByRole("textbox").fill("0.5");
    await row(page, "model.maxTokensPerRequest").getByRole("button", { name: "重置：最大 Token／請求" }).click();
    await expect(toast(page, "已重置為預設值")).toBeVisible();
    await expect.poll(async () => (await settingsOf(request, "admin", "model")).find((c) => c.key === "maxTokensPerRequest")!.value).toBe(before.defaultValue);
  });

  test("Token Guard：前端鏡射 halt>compact（不送請求）；成對套用一次 PUT；後端跨鍵 400 的原因逐字（US-S-02、NFR-SEC-05；契約 E2E-09 步驟 2～6、10）", async ({ page, request }) => {
    await openSettings(page, request);
    await page.getByRole("tab", { name: "執行", exact: true }).click();
    const guard = page.getByTestId("token-guard-card");
    const puts: string[] = [];
    page.on("request", (r) => {
      if (r.method() === "PUT") puts.push(r.url());
    });
    await guard.getByLabel("停機門檻（%）", { exact: true }).fill("60");
    await expect(guard.getByTestId("token-guard-error")).toHaveText("halt_threshold_pct 必須大於 compact_threshold_pct");
    await expect(guard.getByRole("button", { name: "套用 Token Guard" })).toBeDisabled();
    expect(puts).toEqual([]);
    await snap(page, "p6-settings-token-guard-error.png", { tall: true });
    await guard.getByLabel("壓縮門檻（%）", { exact: true }).fill("70");
    await guard.getByLabel("停機門檻（%）", { exact: true }).fill("95");
    await guard.getByRole("button", { name: "套用 Token Guard" }).click();
    await expect(toast(page, "已套用 Token Guard")).toBeVisible();
    expect(puts).toEqual([expect.stringMatching(/\/api\/v1\/settings\/execution\/token-guard$/)]);
    const now = await settingsOf(request, "admin", "execution");
    expect([now.find((c) => c.key === "compactThresholdPct")!.value, now.find((c) => c.key === "haltThresholdPct")!.value]).toEqual(["70", "95"]);

    // 後端校驗（API 直打）：reason 為 PRD 逐字常數；失敗不改任何一個鍵
    const REASON = "halt_threshold_pct 必須大於 compact_threshold_pct";
    const bad = await call(request, "admin", "PUT", "/api/v1/settings/execution/token-guard", { compactThresholdPct: 90, haltThresholdPct: 80 });
    expect(bad.status).toBe(400);
    expect(bad.json.reason).toBe(REASON);
    for (const body of [{ compactThresholdPct: 80, haltThresholdPct: 80 }]) {
      const r = await call(request, "admin", "PUT", "/api/v1/settings/execution/token-guard", body);
      expect(r.status).toBe(400);
      expect(r.json.reason).toBe(REASON);
    }
    for (const body of [
      { compactThresholdPct: 100, haltThresholdPct: 100 },
      { compactThresholdPct: 0, haltThresholdPct: 50 },
    ]) {
      const r = await call(request, "admin", "PUT", "/api/v1/settings/execution/token-guard", body);
      expect(r.status).toBe(400);
      expect(r.json.reason, JSON.stringify(r.json)).not.toBe(REASON); // Bean Validation：欄位錯誤，不是跨鍵 reason
      expect((r.json.errors as Array<{ field: string }>)[0].field).toMatch(/ThresholdPct$/);
    }
    // 單鍵跨鍵校驗（對端現值 70／95）
    for (const [key, value] of [
      ["haltThresholdPct", "60"],
      ["compactThresholdPct", "96"],
    ] as const) {
      const r = await call(request, "admin", "PUT", `/api/v1/settings/execution/${key}`, { value });
      expect(r.status, key).toBe(400);
      expect(r.json.reason).toBe(REASON);
    }
    const typeBad = await call(request, "admin", "PUT", "/api/v1/settings/execution/compactThresholdPct", { value: "abc" });
    expect(typeBad.status).toBe(400);
    expect(typeBad.json.reason).toBe("參數值不符合型別或驗證規則");
    const still = await settingsOf(request, "admin", "execution");
    expect([still.find((c) => c.key === "compactThresholdPct")!.value, still.find((c) => c.key === "haltThresholdPct")!.value]).toEqual(["70", "95"]);
    // 重置的跨鍵（compact=70、halt=95）：① {70,75} ② compact 重置→400（預設 80 ≥ 75）③ halt 重置→200（90）④ compact 重置→200（80）
    expect((await call(request, "admin", "PUT", "/api/v1/settings/execution/token-guard", { compactThresholdPct: 70, haltThresholdPct: 75 })).status).toBe(200);
    const r2 = await call(request, "admin", "POST", "/api/v1/settings/execution/compactThresholdPct/reset");
    expect(r2.status).toBe(400);
    expect(r2.json.reason).toBe(REASON);
    expect((await call(request, "admin", "POST", "/api/v1/settings/execution/haltThresholdPct/reset")).status).toBe(200);
    expect((await call(request, "admin", "POST", "/api/v1/settings/execution/compactThresholdPct/reset")).status).toBe(200);
    const end = await settingsOf(request, "admin", "execution");
    expect([end.find((c) => c.key === "compactThresholdPct")!.value, end.find((c) => c.key === "haltThresholdPct")!.value]).toEqual(["80", "90"]);
  });

  test("敏感鍵（API Key）：二次確認才送 confirm=true、歷史只記遮罩、ADMIN 才能顯示明文（US-S-02／04；契約 E2E-09 步驟 7～9、11）", async ({ page, request }) => {
    await openSettings(page, request);
    const input = row(page, "model.apiKey").getByLabel("API Key", { exact: true });
    await input.click();
    await page.keyboard.type("sk-new-secret-7788");
    await page.getByRole("button", { name: "儲存變更" }).click();
    const dialog = page.getByRole("dialog", { name: "確認更新敏感參數" });
    await expect(dialog).toContainText("API Key");
    await snap(page, "p6-settings-sensitive-confirm.png");
    await dialog.getByRole("button", { name: "取消" }).click();
    expect((await settingsOf(request, "admin", "model")).find((c) => c.key === "apiKey")!.hasValue).toBe(false); // 取消＝不送
    await page.getByRole("button", { name: "儲存變更" }).click();
    const putPromise = page.waitForRequest((r) => r.method() === "PUT" && r.url().endsWith("/api/v1/settings/model/apiKey"));
    await page.getByRole("dialog", { name: "確認更新敏感參數" }).getByRole("button", { name: "確認儲存" }).click();
    expect((await putPromise).postDataJSON()).toEqual({ value: "sk-new-secret-7788", confirm: true });
    await expect(toast(page, "已儲存 1 項參數")).toBeVisible();
    await expect(input).toHaveValue(MASK);
    await expect(page.getByTestId("history-line").first()).toContainText(`${MASK} → ${MASK}`);
    await expect(page.getByTestId("history-line").first()).not.toContainText("sk-new-secret");

    // ADMIN 顯示明文（reveal=true）；operator／viewer 403
    await row(page, "model.apiKey").getByRole("button", { name: "顯示：API Key" }).click();
    await expect(input).toHaveValue("sk-new-secret-7788");
    await row(page, "model.apiKey").getByRole("button", { name: "隱藏：API Key" }).click();
    await expect(input).toHaveAttribute("type", "password");
    for (const role of ["operator", "viewer"] as const) {
      const r = await call(request, role, "GET", "/api/v1/settings/model?reveal=true");
      expect(r.status, role).toBe(403);
      expect(r.json.reason).toBe("僅 ADMIN 可揭露敏感參數");
    }
    // 未帶 reveal 的 operator 仍是遮罩；API 層：無 confirm → 409、重置需 confirm
    expect((await settingsOf(request, "operator", "model")).find((c) => c.key === "apiKey")!.value).toBe(MASK);
    const noConfirm = await call(request, "admin", "PUT", "/api/v1/settings/model/apiKey", { value: "sk-other" });
    expect(noConfirm.status).toBe(409);
    expect(noConfirm.json.reason).toBe("敏感參數更新需二次確認（confirm=true）");
    const noReset = await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset");
    expect(noReset.status).toBe(409);
    expect(noReset.json.reason).toBe("敏感參數重置需二次確認（confirm=true）");
    // 清掉（UI 重置鈕：先確認並帶 confirm=true）
    await row(page, "model.apiKey").getByRole("button", { name: "重置：API Key" }).click();
    await page.getByRole("dialog", { name: "確認重置敏感參數" }).getByRole("button", { name: "確認重置" }).click();
    await expect(toast(page, "已重置為預設值：API Key")).toBeVisible();
    expect((await settingsOf(request, "admin", "model")).find((c) => c.key === "apiKey")!.hasValue).toBe(false);
  });

  test("測試連線：對假 server 成功（金鑰只走 Authorization、不回顯）；對 http://10.0.0.1 被 SSRF 規則拒絕且沒有任何連線（US-S-05、NFR-SEC-04；契約 E2E-10）", async ({ page, request }) => {
    expect((await call(request, "admin", "PUT", "/api/v1/settings/model/timeout", { value: "3" })).status).toBe(200);
    try {
      await openSettings(page, request);
      // UI：帶表單內尚未儲存的 apiUrl／apiKey
      await row(page, "model.apiUrl").getByRole("textbox").fill(llm.endpoint);
      await row(page, "model.apiKey").getByLabel("API Key", { exact: true }).click();
      await page.keyboard.type("sk-secret-xyz");
      const before = llm.count();
      await page.getByRole("button", { name: "測試連線" }).click();
      await expect(page.getByTestId("test-connection-result")).toContainText(/連線成功（延遲 \d+ms）/);
      await snap(page, "p6-settings-test-connection.png", { tall: true });
      expect(llm.count()).toBe(before + 1);
      const probe = llm.requests.filter((r) => r.url === "/v1/chat/completions").at(-1)!;
      expect(probe.headers.authorization).toBe("Bearer sk-secret-xyz");
      expect(probe.body).toMatchObject({ max_tokens: 1, stream: false });
      expect((probe.body.messages as Array<{ content: string }>)[0].content).toBe("ping");
      // UI：私網位址被拒（沒有任何連線）
      await row(page, "model.apiUrl").getByRole("textbox").fill("http://10.0.0.1");
      await page.getByRole("button", { name: "測試連線" }).click();
      await expect(page.getByTestId("test-connection-result")).toContainText("目標位址未通過 SSRF／allowlist 檢查");
      await expect(page.getByTestId("test-connection-result")).toContainText("10.0.0.1");
      await snap(page, "p6-settings-test-connection-ssrf.png", { tall: true });
      expect(llm.count()).toBe(before + 1); // 被拒的請求沒有發出任何連線

      // API 矩陣（契約 E2E-10）：違規類別逐字、422、沒有連線
      const urlCases: Array<[string, string]> = [
        ["http://10.0.0.5:8080", "private_ip"],
        ["http://192.168.1.1", "private_ip"],
        ["http://172.16.0.9", "private_ip"],
        ["http://100.64.0.1", "private_ip"],
        ["http://169.254.169.254/latest/meta-data", "link_local"],
        ["http://[::1]:8080", "loopback"],
        ["http://0x7f.0.0.1", "malformed_url"],
        ["http://2130706433", "malformed_url"],
        ["ftp://api.minimax.io/v1/text/chatcompletion_v2", "scheme"],
        ["http://exämple.com/v1", "malformed_url"],
        ["http://user:your_password_here@api.minimax.io/v1/text/chatcompletion_v2", "userinfo"],
        ["https://example.com", "not_in_allowlist"],
        ["http://localhost.evil.example", "not_in_allowlist"],
        ["http://rebind.e2e.test/v1/chat/completions", "dns_rebinding"],
      ];
      for (const [apiUrl, violation] of urlCases) {
        const r = await call(request, "admin", "POST", "/api/v1/settings/test-connection", { apiUrl });
        expect(r.status, apiUrl).toBe(422);
        expect(r.json.reason, apiUrl).toBe("目標位址未通過 SSRF／allowlist 檢查");
        expect((r.json.details as Json).violation, apiUrl).toBe(violation);
      }
      expect(llm.count()).toBe(before + 1);
      // 成功：金鑰不回顯、HTTP 狀態與解析 host
      const ok = await call(request, "admin", "POST", "/api/v1/settings/test-connection", { apiUrl: llm.endpoint, apiKey: "sk-secret-xyz" });
      expect(ok.status).toBe(200);
      expect(dataOf(ok)).toMatchObject({ success: true, message: "連線成功", httpStatus: 200, resolvedHost: "127.0.0.1" });
      expect(JSON.stringify(ok.json)).not.toContain("sk-secret-xyz");
      // 沒有路徑的 URL：後端不補路徑（假 server 對 POST / 回 404）
      const noPath = await call(request, "admin", "POST", "/api/v1/settings/test-connection", { apiUrl: `http://127.0.0.1:${llm.port}` });
      expect(dataOf(noPath)).toMatchObject({ success: false, message: "端點路徑不存在或不接受 POST（HTTP 404）" });
      // 401／503／302（不跟隨）
      llm.probeStatus = 401;
      expect(dataOf(await call(request, "admin", "POST", "/api/v1/settings/test-connection", { apiUrl: llm.endpoint }))).toMatchObject({ success: false, message: "認證失敗（HTTP 401）" });
      llm.probeStatus = 503;
      expect(dataOf(await call(request, "admin", "POST", "/api/v1/settings/test-connection", { apiUrl: llm.endpoint }))).toMatchObject({ success: false, message: "服務回應錯誤（HTTP 503）" });
      llm.probeStatus = 200;
      // 角色：operator／viewer 一律 403
      for (const role of ["operator", "viewer"] as const) {
        expect((await call(request, role, "POST", "/api/v1/settings/test-connection", { apiUrl: llm.endpoint })).status, role).toBe(403);
      }
    } finally {
      llm.probeStatus = 200;
      await call(request, "admin", "PUT", "/api/v1/settings/model/timeout", { value: "30" });
    }
  });

  test("匯出（50 鍵、加密鍵為 <encrypted>）→ 改一個值匯入（applied=1）→ 異常檔 400／413／415；全部重置（US-S-03／06；契約 E2E-09 步驟 12～15）", async ({ page, request }) => {
    // 讓已儲存的 model.apiUrl 落在 e2e 的 allowlist 內（預設值 api.minimax.io 不在 e2e allowlist；那個情形由下一支 DEF-AC-002 另測）
    expect((await call(request, "admin", "PUT", "/api/v1/settings/model/apiUrl", { value: llm.endpoint })).status).toBe(200);
    await openSettings(page, request);
    const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "匯出設定" }).click()]);
    expect(download.suggestedFilename()).toMatch(/^aisdlc-settings-\d{8}\.json$/);
    const raw = readFileSync((await download.path()) as string, "utf-8");
    const doc = JSON.parse(raw) as { version: number; configs: Array<{ category: string; key: string; value: string }> };
    expect(doc.version).toBe(1);
    expect(doc.configs).toHaveLength(50);
    expect(doc.configs.find((c) => c.key === "apiKey")!.value).toBe("<encrypted>");
    expect(doc.configs.find((c) => c.key === "dbDsn")!.value).toBe("<encrypted>");
    expect(raw).not.toContain("sk-");
    await expect(toast(page, "已匯出設定")).toBeVisible();

    // 匯入：改 monitor.refreshIntervalMs 為 15000 → applied=1、skipped=49（兩筆 <encrypted> 佔位＋47 筆值未變）
    const changed = { ...doc, configs: doc.configs.map((c) => (c.key === "refreshIntervalMs" ? { ...c, value: "15000" } : c)) };
    await page.getByRole("button", { name: "匯入設定" }).click();
    const dialog = page.getByRole("dialog", { name: "匯入設定" });
    await dialog.getByTestId("settings-file-input").setInputFiles({ name: "aisdlc-settings.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(changed)) });
    await dialog.getByRole("button", { name: "匯入", exact: true }).click();
    const result = dialog.getByTestId("settings-import-result");
    await expect(result.getByTestId("import-applied")).toHaveText("1");
    await expect(result.getByTestId("import-skipped")).toHaveText("49");
    await expect(result.getByTestId("import-failed")).toHaveCount(0); // 沒有失敗項時不顯示「失敗 N 項」
    await snap(page, "p6-settings-import.png");
    expect((await settingsOf(request, "admin", "monitor")).find((c) => c.key === "refreshIntervalMs")!.value).toBe("15000");
    // API：低於最小值 → errors（applied=0）；token_guard 跨鍵 → 兩鍵皆列入且不套用
    const adminToken = await tokenOf(request, "admin");
    const upload = async (payload: unknown, name = "s.json", mimeType = "application/json") =>
      request.fetch(`${API_URL}/api/v1/settings/import`, {
        method: "POST",
        headers: { Authorization: `Bearer ${adminToken}` },
        multipart: { file: { name, mimeType, buffer: Buffer.from(typeof payload === "string" ? payload : JSON.stringify(payload)) } },
        failOnStatusCode: false,
      });
    const low = await upload({ ...doc, configs: doc.configs.map((c) => (c.key === "refreshIntervalMs" ? { ...c, value: "900" } : c)) });
    const lowJson = (await low.json()) as { data: { applied: number; errors: Array<{ key: string; reason: string }> } };
    expect(low.status()).toBe(200);
    expect(lowJson.data.applied).toBe(0);
    expect(lowJson.data.errors.map((e) => e.key)).toContain("refreshIntervalMs");
    const guardBad = await upload({ ...doc, configs: doc.configs.map((c) => (c.key === "compactThresholdPct" ? { ...c, value: "90" } : c.key === "haltThresholdPct" ? { ...c, value: "80" } : c)) });
    const guardJson = (await guardBad.json()) as { data: { applied: number; errors: Array<{ key: string; reason: string }> } };
    expect(guardJson.data.errors.map((e) => e.key).sort()).toEqual(["compactThresholdPct", "haltThresholdPct"]);
    expect(guardJson.data.errors.every((e) => e.reason === "halt_threshold_pct 必須大於 compact_threshold_pct")).toBe(true);
    // 異常檔
    const v2 = await upload({ version: 2, configs: [] });
    expect(v2.status()).toBe(400);
    expect(((await v2.json()) as { reason: string; details: { problem: string } }).details.problem).toBe("unsupported_version");
    const notJson = await upload("這不是 JSON");
    expect(notJson.status()).toBe(400);
    expect(((await notJson.json()) as { details: { problem: string } }).details.problem).toBe("invalid_json");
    const big = await upload("x".repeat(2 * 1024 * 1024));
    expect(big.status()).toBe(413);
    const txt = await upload("hello", "s.txt", "text/plain");
    expect(txt.status()).toBe(415);
    // 還原監控刷新間隔
    expect((await call(request, "admin", "POST", "/api/v1/settings/monitor/refreshIntervalMs/reset")).status).toBe(200);
  });

  test("DEF-AC-002（W5 已修）：匯出後原樣匯入（一個值都沒改）errors=[]、applied=0、skipped=50（2 筆 <encrypted>＋48 筆值未變）；把 model.apiUrl 改成不在 allowlist 的主機才進 errors，其餘 skipped（契約 §1.5.10；E2E-13 列 6）", async ({
    request,
  }) => {
    // W4 的缺陷：匯入對「值未變」的項目仍先跑 SSRF／allowlist 驗證。e2e profile 的 allowlist 是 127.0.0.1,localhost,rebind.e2e.test，
    // 種子預設的 model.apiUrl（api.minimax.io）不在其中 ⇒ 原樣匯入得到 errors=[model.apiUrl 目標位址未通過 SSRF／allowlist 檢查]、skipped=49。
    // W5-BE：值未變一律先計 skipped（順序：<encrypted> 佔位 → 加密鍵給明文 errors → 值未變 skipped → 驗證 → 候選）。本情境在 W5-QA 移除了 test.fail。
    expect((await call(request, "admin", "POST", "/api/v1/settings/model/apiUrl/reset")).status).toBe(200);
    const token = await tokenOf(request, "admin");
    const exported = await request.fetch(`${API_URL}/api/v1/settings/export`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, failOnStatusCode: false });
    expect(exported.status()).toBe(200);
    const exportedBody = await exported.body();
    type ImportData = { applied: number; skipped: number; errors: Array<{ category: string; key: string; reason: string }> };
    const upload = async (buffer: Buffer): Promise<{ status: number; data: ImportData }> => {
      const res = await request.fetch(`${API_URL}/api/v1/settings/import`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        multipart: { file: { name: "aisdlc-settings.json", mimeType: "application/json", buffer } },
        failOnStatusCode: false,
      });
      return { status: res.status(), data: ((await res.json()) as { data: ImportData }).data };
    };
    // ① 原樣匯入
    const same = await upload(exportedBody);
    expect(same.status).toBe(200);
    expect(same.data.errors, `原樣匯入的結果：${JSON.stringify(same.data)}`).toEqual([]);
    expect(same.data.applied).toBe(0);
    expect(same.data.skipped, "2 筆 <encrypted> 佔位＋48 筆值未變").toBe(50);
    // ② 只把 model.apiUrl 改成不在 allowlist 的主機：該鍵進 errors，其餘 skipped，且沒有任何值被套用
    const doc = JSON.parse(exportedBody.toString("utf-8")) as { configs: Array<{ category: string; key: string; value: string }> };
    const before = (await settingsOf(request, "admin", "model")).find((c) => c.key === "apiUrl")!.value;
    const forbidden = "https://not-on-the-allowlist.example/v1/chat/completions";
    const changed = await upload(Buffer.from(JSON.stringify({ ...doc, configs: doc.configs.map((c) => (c.key === "apiUrl" ? { ...c, value: forbidden } : c)) })));
    expect(changed.status).toBe(200);
    expect(changed.data.errors.map((e) => `${e.category}.${e.key}`)).toEqual(["model.apiUrl"]);
    expect(changed.data.errors[0].reason).toContain("allowlist");
    expect(changed.data.applied).toBe(0);
    expect(changed.data.skipped, "其餘 49 筆（2 佔位＋47 值未變）").toBe(49);
    expect((await settingsOf(request, "admin", "model")).find((c) => c.key === "apiUrl")!.value, "被拒的值沒有寫進去").toBe(before);
  });
  test("角色：operator／viewer 看得到參數與歷史，但輸入、重置、儲存、匯出入、測試連線全部停用；後端對寫入 403（契約 E2E-09 步驟 9）", async ({ page, request }) => {
    await openSettings(page, request, "viewer");
    await expect(page.getByTestId("readonly-banner")).toContainText("目前角色（VIEWER）只能檢視系統參數");
    await expect(row(page, "model.maxTokensPerRequest").getByRole("textbox")).toBeDisabled();
    for (const name of ["儲存變更", "全部重置為預設值", "匯出設定", "匯入設定", "測試連線"]) {
      await expect(page.getByRole("button", { name })).toBeDisabled();
    }
    await expect(page.getByTestId("history-line").first()).toBeVisible();
    await snap(page, "p6-settings-readonly.png", { tall: true });
    for (const role of ["operator", "viewer"] as const) {
      expect((await call(request, role, "PUT", "/api/v1/settings/model/maxTokensPerRequest", { value: "1000" })).status, role).toBe(403);
      expect((await call(request, role, "POST", "/api/v1/settings/execution/reset")).status, role).toBe(403);
      expect((await call(request, role, "POST", "/api/v1/settings/export")).status, role).toBe(403);
      expect((await call(request, role, "GET", "/api/v1/settings")).status, role).toBe(200);
      expect((await call(request, role, "GET", "/api/v1/settings/history")).status, role).toBe(200);
    }
    const noToken = await request.fetch(`${API_URL}/api/v1/settings`, { failOnStatusCode: false });
    expect(noToken.status()).toBe(401);
  });
});
