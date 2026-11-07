"use client";

/**
 * 「SCR 進行中」文字標籤（FR-R2P-19、AC-R2P-19-4 前端文字半；TCS-ResearchToPRD-P1-20261107 AT-961-18-6）：
 * 只在流程相態為 `SCR_OPEN` 時出現，文字取 `FLOW_PHASE_LABEL`（D-114 定稿）；發起 SCR 的按鈕與橫幅屬 P2，不在這裡。
 */
import { Tag } from "@/components/ui/badge";
import { scrBadge } from "@/lib/domain/research";

export function ScrStateBadge({ phase, className }: { phase: string; className?: string }) {
  const badge = scrBadge(phase);
  if (!badge.visible) return null;
  return (
    <Tag data-testid="scr-badge" className={className}>
      {badge.label}
    </Tag>
  );
}
