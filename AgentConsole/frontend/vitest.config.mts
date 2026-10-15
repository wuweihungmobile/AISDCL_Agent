import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

/**
 * 單元／元件測試（jsdom）。E2E（Playwright）在 tests/e2e，由 playwright.config.ts 管，不進 vitest。
 * 覆蓋率範圍（coverage.include）只列「單元測試真正負責的邏輯層」：API client／auth store／狀態表／格式化／
 * 表單驗證與錯誤對應／Markdown 元件／四區塊版面／Toast 等 UI 原子；
 * 整頁視圖（views／頁面）的行為由 Playwright E2E 對真後端驗證，不計入這個門檻。
 */
export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL("./", import.meta.url)) },
  },
  // 與 tsconfig 的 jsx: "react-jsx" 一致（Vite 8 以 Oxc 轉譯 TSX）
  oxc: { jsx: { runtime: "automatic" } },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["**/*.test.{ts,tsx}"],
    exclude: ["node_modules/**", ".next/**", "tests/e2e/**"],
    css: false,
    restoreMocks: true,
    coverage: {
      provider: "v8",
      reporter: ["text-summary", "text"],
      include: [
        "lib/api/client.ts",
        "lib/api/endpoints.ts",
        "lib/auth/store.ts",
        "lib/domain/status.ts",
        "lib/format.ts",
        "lib/nav/lastProject.ts",
        "components/domain/entity/schemas.ts",
        "components/domain/entity/apiErrors.ts",
        // W4-F1：匯入與設定頁的純邏輯層（樹編輯模型、有界閘錯誤、來源預檢、節點驗證、設定草稿與驗證、reason 常數）
        "components/domain/import/tree.ts",
        "components/domain/import/gateErrors.ts",
        "components/domain/import/sourceRules.ts",
        "components/domain/import/nodeSchemas.ts",
        "components/domain/settings/settingsModel.ts",
        "components/domain/settings/settingsErrors.ts",
        "lib/api/reasons.ts",
        // W4-F2：執行頁與監控頁的邏輯層（SSE 連線管理、即時狀態與批次快取修補、按鈕狀態機、範圍模型、DAG、指標整形、版面存取）、
        // 把串流接進 React 的 hook、不依賴圖表庫的簡易圖表
        "lib/api/sse.ts",
        "lib/domain/runLive.ts",
        "lib/domain/runControl.ts",
        "lib/domain/scope.ts",
        "lib/domain/dag.ts",
        "lib/domain/metrics.ts",
        "lib/nav/monitorLayout.ts",
        "components/domain/execute/reviewHelp.ts",
        "components/domain/execute/startErrors.ts",
        "hooks/useRunStream.ts",
        "components/charts/SimpleCharts.tsx",
        "components/markdown/**/*.tsx",
        "components/layout/*.tsx",
        "components/ui/toast.tsx",
        "components/ui/pagination.tsx",
        "components/ui/button.tsx",
      ],
      thresholds: { lines: 70, statements: 70, functions: 70, branches: 60 },
    },
  },
});
