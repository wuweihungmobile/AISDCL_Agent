import { defineConfig, devices } from "@playwright/test";

/**
 * E2E（對真後端 console-api）。環境變數（皆有預設，Windows／macOS 通用）：
 *   E2E_API_URL   後端 origin，預設 http://localhost:8080
 *   E2E_WEB_PORT  前端埠，預設 3000
 *   E2E_MODE      dev（預設，next dev，NEXT_PUBLIC_API_URL 於啟動時決定）｜standalone（用已建置的產物；
 *                 NEXT_PUBLIC_API_URL 已在 build 時內嵌，需先以同一個 API 位址 npm run build）
 *   E2E_USER／E2E_PASSWORD  登入帳密，預設 operator（開發預設帳號，見 backend/README.md）
 * 後端必須設 CONSOLE_CORS_ALLOWED_ORIGINS 包含 http://localhost:<E2E_WEB_PORT>。
 * 詳見 tests/e2e/README.md。
 */
const apiUrl = process.env.E2E_API_URL ?? "http://localhost:8080";
const port = Number(process.env.E2E_WEB_PORT ?? "3000");
const mode = process.env.E2E_MODE ?? "dev";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "**/*.spec.ts",
  // 共用同一個資料庫、列表計數會互相影響：一律序列執行
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  outputDir: "test-results",
  use: {
    baseURL: `http://localhost:${port}`,
    viewport: { width: 1440, height: 900 },
    locale: "zh-TW",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
  webServer: {
    command: mode === "standalone" ? "node scripts/start-standalone.mjs" : `npx next dev -p ${port}`,
    url: `http://localhost:${port}/api/health`,
    reuseExistingServer: true,
    timeout: 180_000,
    env: {
      PORT: String(port),
      HOSTNAME: "0.0.0.0",
      NEXT_PUBLIC_API_URL: apiUrl,
    },
  },
});
