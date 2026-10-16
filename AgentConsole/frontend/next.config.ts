import path from "node:path";
import { readFileSync } from "node:fs";
import type { NextConfig } from "next";

// 版本號只讀一次、在建置時內嵌（BottomRegion 顯示 Console v<version>）；建置一律在 frontend/ 目錄執行
const pkg = JSON.parse(readFileSync(path.join(process.cwd(), "package.json"), "utf-8")) as {
  version: string;
};

const nextConfig: NextConfig = {
  // Dockerfile 以 .next/standalone 組最小執行映像（PRD §11.4.1）
  output: "standalone",
  // 明確指定追蹤根目錄：monorepo 內建置時 standalone 輸出仍是 .next/standalone/server.js（不會多一層子目錄）
  outputFileTracingRoot: process.cwd(),
  poweredByHeader: false,
  env: {
    NEXT_PUBLIC_APP_VERSION: pkg.version,
  },
  // 不啟用 cacheComponents／partialPrefetching（create-next-app 16.4 預設為 true）：
  // 本專案資料全部 client-side（TanStack Query），沒有伺服端資料可快取；開了反而要求所有讀 params／searchParams
  // 的路由包 Suspense、並禁用 route segment config。理由與重新評估條件見 docs/02_architecture/ADR-002。
  turbopack: {
    // Markdown 編輯器的左欄原始碼著色與預覽的程式碼區塊都走 rehype-prism-plus（@uiw/react-md-editor、@uiw/react-markdown-preview 都是 `import … from 'rehype-prism-plus'`）。
    // 上游的逐行拆分是 O(行數 × 節點數)，20KB 文件的左欄著色一次就占約 40～50ms（NFR-9.1-05）；換成行為等價、線性時間的版本。
    // 等價性由 components/markdown/rehypePrismLinear.test.ts 對上游逐位比對；那支測試也守這條別名仍然有效（別名只對裸名稱生效，子路徑 /all 等不受影響）。
    resolveAlias: {
      "rehype-prism-plus": "./components/markdown/rehypePrismLinear.ts",
    },
    // Tailwind 4 的 Turbopack 整合（create-next-app 16.4 預設做法）
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
