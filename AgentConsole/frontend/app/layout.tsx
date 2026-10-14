import type { Metadata } from "next";
import type { ReactNode } from "react";

// 字型自託管（styles/fonts.css 說明）：@font-face 隨 npm 套件安裝，由 Next 打包，不依賴外部網路
import "@fontsource-variable/inter/index.css";
import "@fontsource-variable/noto-sans-tc/index.css";
import "@fontsource-variable/jetbrains-mono/index.css";
import "./globals.css";

import { BottomRegion } from "@/components/layout/BottomRegion";
import { ContentRegion } from "@/components/layout/ContentRegion";
import { ToolsRegion } from "@/components/layout/ToolsRegion";
import { TopRegion } from "@/components/layout/TopRegion";
import { Providers } from "@/components/providers/Providers";

export const metadata: Metadata = {
  title: { default: "AISDLC Console", template: "%s · AISDLC Console" },
  description: "AISDLC 自治開發 Agent 控制台：專案／目標／任務管理、人工 signoff 硬閘、執行與監控",
};

/**
 * 全站唯一的版面組裝處（Architecture §5.2）：Top／Tools／Content／Bottom 四區塊。
 * 任何 app/**\/page.tsx 與巢狀 layout 都不得 import 這四個元件、也不得自帶其內容。
 * 固定高度三段式（100vh、不捲動）；本體置中、max-width 1440、左右欄 gap 32px、內距 24px；
 * <768px 以 flex-col-reverse 把 Tools 排到內容下方，成為底部 Tab 導航。
 */
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-Hant-TW" className="h-full">
      <body className="h-full">
        <Providers>
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100] focus:rounded-md focus:bg-wg-surface focus:px-3 focus:py-2"
          >
            跳到主要內容
          </a>
          <div className="flex h-screen flex-col overflow-hidden bg-wg-base font-sans text-wg-text">
            <TopRegion />
            <div className="flex min-h-0 flex-1 justify-center overflow-hidden">
              <div className="flex min-h-0 w-full max-w-[var(--container-max)] gap-8 p-6 max-md:flex-col-reverse max-md:gap-0 max-md:p-4 max-md:pb-0">
                <ToolsRegion />
                <ContentRegion>{children}</ContentRegion>
              </div>
            </div>
            <BottomRegion />
          </div>
        </Providers>
      </body>
    </html>
  );
}
