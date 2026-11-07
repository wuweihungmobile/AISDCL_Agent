"use client";

/**
 * 規格變更橫幅（FR-R2P-19-4；TCS-ResearchToPRD-P2-20261107 AT-962-15-5）：規格變更進行中（`kanban.scrOpen`）時顯示「規格變更中：SCR-<n>（<kind>）」並連到工作室。
 * 同一個 `scrOpen` 也讓看板、`InnerLoopLinks`、`GateRegisterDialog` 的啟動類動作停用並顯示同一句登記文案（`BUILD_DISABLED_TEXT.scrOpen`；`executionBlock()` 簽名不變）。
 */
import { TriangleAlert } from "lucide-react";
import Link from "next/link";

import { useResearchScr } from "@/lib/api/queries";
import { BUILD_DISABLED_TEXT } from "@/lib/domain/research";

export function ScrBanner({ researchId, scrOpen }: { researchId: string; scrOpen: boolean }) {
  const list = useResearchScr(scrOpen ? researchId : undefined);
  if (!scrOpen) return null;
  const open = list.data?.find((s) => s.status === "OPEN");
  const label = open === undefined ? "規格變更中" : `規格變更中：SCR-${open.scrNo}（${open.kind}）`;
  return (
    <div role="alert" data-testid="scr-banner" className="flex flex-wrap items-center gap-3 rounded-md border border-wg-draft-border bg-wg-draft-bg px-4 py-3 text-sm">
      <TriangleAlert size={18} aria-hidden className="shrink-0 text-wg-accent" />
      <span className="font-semibold text-wg-accent">{label}</span>
      <span className="text-wg-muted">觸發拆解、簽核與草擬測試規格都暫停。{BUILD_DISABLED_TEXT.scrOpen}</span>
      <Link href={`/research/${encodeURIComponent(researchId)}?step=studio`} className="font-medium underline">
        前往規格工作室
      </Link>
    </div>
  );
}
