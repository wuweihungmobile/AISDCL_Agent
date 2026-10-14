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
