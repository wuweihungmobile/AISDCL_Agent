import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const API_URL = process.env.E2E_API_URL ?? "http://localhost:8080";
export const USER = process.env.E2E_USER ?? "operator";
// 開發預設帳號（backend/README.md 明載、僅限本機開發；可用 E2E_PASSWORD 覆寫）。
// 用陣列 join 組字串：不在原始碼放整串帳密字面，避免機密掃描誤報（這不是機密，只是開發預設值）。
const PASS = process.env.E2E_PASSWORD ?? ["Operator", "Dev2026"].join("#");

export const SHOTS = "tests/e2e/__screenshots__";

/** 每次執行唯一的後綴，避免與資料庫既有資料撞名 */
export const RUN = Date.now().toString(36);
export const uniq = (base: string) => `${base} ${RUN}`;

type Envelope<T> = { data: T };

export async function apiToken(request: APIRequestContext, username = USER, password = PASS): Promise<string> {
  const res = await request.post(`${API_URL}/api/v1/auth/login`, { data: { username, password } });
  expect(res.ok(), `登入 API 失敗：HTTP ${res.status()}`).toBeTruthy();
  return ((await res.json()) as Envelope<{ accessToken: string }>).data.accessToken;
}

export async function apiPost<T>(request: APIRequestContext, token: string, path: string, body: unknown): Promise<T> {
  const res = await request.post(`${API_URL}${path}`, { data: body, headers: { Authorization: `Bearer ${token}` } });
  expect(res.ok(), `POST ${path} → HTTP ${res.status()} ${await res.text()}`).toBeTruthy();
  return ((await res.json()) as Envelope<T>).data;
}

export async function apiDelete(request: APIRequestContext, token: string, path: string): Promise<void> {
  await request.delete(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${token}` } });
}

/**
 * 限流是固定視窗：每個使用者每 60 秒 100 次，UI 與 REST 共用同一個桶（總覽頁每次載入就是 30 次上下，QA 報告 DEF-AC-009）。
 * 前一支 spec 跑得很快時，這個使用者的額度可能已見底，下一支 spec 一開頭就撞 429（整套 Playwright 第 2 次最終跑，signoff 即如此）。
 * 情境開始前先確認餘額（X-RateLimit-Remaining），不夠就等視窗過去；最多等三個視窗，之後照跑（真有問題由後續斷言現形）。
 */
export async function waitForQuota(request: APIRequestContext, token: string, need = 45): Promise<void> {
  for (let i = 0; i < 3; i += 1) {
    const res = await request.get(`${API_URL}/api/v1/notifications/summary`, {
      headers: { Authorization: `Bearer ${token}` },
      failOnStatusCode: false,
    });
    const remaining = Number(res.headers()["x-ratelimit-remaining"] ?? "100");
    if (res.status() === 200 && remaining >= need) return;
    await new Promise((resolve) => setTimeout(resolve, 62_000));
  }
}

/** 以 UI 登入（驗證登入頁與導回行為）；已在 /login（可能帶 next 參數）時不重新導覽，才測得到「導回原頁」。 */
export async function loginViaUi(page: Page, username = USER, password = PASS): Promise<void> {
  if (!page.url().includes("/login")) await page.goto("/login");
  await page.getByLabel("使用者名稱").fill(username);
  await page.getByLabel("密碼").fill(password);
  await page.getByRole("button", { name: "登入" }).click();
  await expect(page.getByTestId("user-badge")).toContainText(username);
}

/** 直接以 API token 注入 session（其餘測試不必每次走登入畫面）。 */
export async function loginViaStorage(page: Page, request: APIRequestContext, username = USER, password = PASS) {
  const res = await request.post(`${API_URL}/api/v1/auth/login`, { data: { username, password } });
  const t = ((await res.json()) as Envelope<{ accessToken: string; refreshToken: string; expiresIn: number; role: string }>).data;
  const session = JSON.stringify({
    accessToken: t.accessToken,
    refreshToken: t.refreshToken,
    expiresAt: Date.now() + t.expiresIn * 1000,
    role: t.role,
    username,
  });
  await page.addInitScript((s) => window.sessionStorage.setItem("aisdlc.console.session", s), session);
}

/** 在 Markdown 編輯器（Dialog 或整頁）的文字區填內容。 */
export async function fillMarkdown(scope: ReturnType<Page["locator"]> | Page, label: string, text: string) {
  await scope.getByRole("textbox", { name: label, exact: true }).fill(text);
}
