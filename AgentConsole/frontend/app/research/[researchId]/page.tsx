import type { Metadata } from "next";
import { Suspense } from "react";

import { ResearchWorkspaceView } from "@/components/domain/research/ResearchWorkspaceView";

export const metadata: Metadata = { title: "研究工作區" };

export default function ResearchWorkspacePage() {
  // ResearchWorkspaceView 讀 useSearchParams（?step= 切換五個步驟面板），靜態預先渲染時需要 Suspense 邊界
  return (
    <Suspense>
      <ResearchWorkspaceView />
    </Suspense>
  );
}
