import { Construction } from "lucide-react";
import type { ReactNode } from "react";

import { Card } from "@/components/ui/card";

/** 路由殼的占位卡：本頁功能尚未實作（W4／Phase 3～6），導覽仍可到達。 */
export function PlaceholderCard({
  phase,
  children,
}: {
  /** 例：「Phase 3」 */
  phase: string;
  children?: ReactNode;
}) {
  return (
    <Card data-testid="phase-placeholder" className="flex items-start gap-4 p-[22px]">
      <span className="inline-flex size-12 shrink-0 items-center justify-center rounded-[10px] bg-wg-tertiary">
        <Construction size={24} className="text-wg-primary" aria-hidden />
      </span>
      <div className="min-w-0">
        <h3 className="text-lg font-semibold">本頁於 {phase} 實作</h3>
        <p className="mt-1 text-[15px] leading-[1.7] text-wg-muted">
          {children ?? "路由與導覽已就緒，功能內容待後續階段接線。"}
        </p>
      </div>
    </Card>
  );
}
