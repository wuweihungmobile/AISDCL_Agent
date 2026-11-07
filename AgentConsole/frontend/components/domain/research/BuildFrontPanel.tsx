"use client";

/**
 * 步驟 4 前半面板（拆解、覆蓋與簽核、測試規格草擬、到既有凍結與執行的連結）——**占位 stub**：
 * PKG-FE-D1 只建殼並由 `ResearchWorkspaceView` 一次接好（TCS-ResearchToPRD-P1-20261107 §5.7）；PKG-FE-D2 填實本檔（拆解樹、覆蓋矩陣、簽核、TCS 草擬、重新對帳），
 * 屆時不得再動 `ResearchWorkspaceView.tsx`。屬性形狀（`researchId`、`project`、`completed`）定稿於此：面板自己用 `useResearchDecomposition`、`useResearchScr` 等查詢 hook 取資料。
 */
import { Hammer } from "lucide-react";

import { Card } from "@/components/ui/card";
import type { ResearchProjectDetail } from "@/lib/api/types";

export function BuildFrontPanel({ researchId, project, completed }: { researchId: string; project: ResearchProjectDetail; completed: boolean }) {
  return (
    <Card data-testid="build-front-panel" data-research-id={researchId} data-completed={String(completed)} data-phase={project.flow.effective.phase} className="flex flex-col gap-3 p-6">
      <h3 className="flex items-center gap-2 text-lg font-semibold">
        <Hammer size={20} aria-hidden className="text-wg-muted" />第 4 步：拆解與執行
      </h3>
      <p className="text-sm text-wg-muted">拆解、簽核與測試規格草擬面板由後續階段接入。</p>
    </Card>
  );
}
