import { defineConfig, devices } from "@playwright/test";

/**
 * Docker 全棧 E2E 設定（經 nginx、同源）：`docker compose --profile db --profile app --profile full up -d` 之後執行。
 *
 *   $env:E2E_API_URL = "http://localhost"; npx playwright test -c tests/e2e/docker.config.ts
 *
 * 與預設的 playwright.config.ts 分開，因為：
 *   · 沒有 webServer：前端是 compose 裡的容器；預設設定的就緒探測打 /api/health，經 nginx 會被導到後端而 404。
 *   · 跑 *.stack.ts（需要 docker CLI 與全棧容器），另加不依賴 e2e profile 的既有真後端 specs（登入～CRUD、signoff、設計系統、圖表、版面）：
 *     全棧是乾淨的資料庫、經 nginx 同源，正好驗證那批情境在正式入口下照常運作。
 * 環境變數：E2E_API_URL＝nginx 入口（預設 http://localhost，必須與瀏覽器 baseURL 同源）、
 *   E2E_BRIDGE_CONTAINER／E2E_BACKEND_CONTAINER／E2E_NGINX_CONTAINER＝容器名稱（預設 compose 的 container_name）。
 */
const baseURL = process.env.E2E_API_URL ?? "http://localhost";

export default defineConfig({
  testDir: ".",
  testMatch: ["**/*.stack.ts", "**/crud-flow.spec.ts", "**/signoff.spec.ts", "**/design-system.spec.ts", "**/chart.spec.ts", "**/shells-and-layout.spec.ts"],
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 300_000,
  expect: { timeout: 20_000 },
  reporter: [["list"]],
  outputDir: "../../test-results/docker",
  use: {
    baseURL,
    viewport: { width: 1440, height: 900 },
    locale: "zh-TW",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
});
