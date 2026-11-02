import type { Metadata } from "next";
import { Suspense } from "react";

import { ResearchWorkspaceView } from "@/components/domain/research/ResearchWorkspaceView";
import { StudioPanel } from "@/components/domain/research/StudioPanel";
import { TopicPanel } from "@/components/domain/research/TopicPanel";

export const metadata: Metadata = { title: "研究工作區" };

export default function ResearchWorkspacePage() {
  // ResearchWorkspaceView 讀 useSearchParams（?step= 切換五個步驟面板），靜態預先渲染時需要 Suspense 邊界。
  // 步驟 1（議題與證據）與步驟 2（PRD 工作室）的面板在這裡接入：兩者都是 "use client" 元件，以元件參照傳給客戶端的工作區
  // （mermaid 與 diff 由工作室內部延遲載入，不進這個頁面的首屏；AT-960-17-3 掃描本檔的靜態 import 圖）。
  return (
    <Suspense>
      <ResearchWorkspaceView panels={{ topic: TopicPanel, studio: StudioPanel }} />
    </Suspense>
  );
}
