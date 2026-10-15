import { Check, ShieldAlert } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

/**
 * Signoff 警示橫幅（設計稿：#fdeee9 底、#f3c7bb 邊、shield-alert 圖示）。
 * signedOff=false 的專案／目標／任務是「AI 草案」，人工審批前禁止執行（後端另有 409 二次校驗）。
 * 專案版有標題＋說明；目標／任務版是一行精簡訊息。
 */
export function SignoffBanner({ kind, onApprove, canApprove = true }: { kind: "project" | "goal" | "task"; onApprove: () => void; canApprove?: boolean }) {
  const label = kind === "project" ? "專案" : kind === "goal" ? "目標" : "任務";
  let body: ReactNode;
  if (kind === "project") {
    body = (
      <div className="min-w-0 flex-1">
        <div className="font-semibold text-wg-accent">AI 草案 — 待人工 signoff 硬閘</div>
        <div className="text-[13px] text-wg-muted">此專案 signed_off=false，未經掌舵者審批前禁止執行（後端二次校驗 409）。</div>
      </div>
    );
  } else {
    body = (
      <div className="min-w-0 flex-1 text-sm">
        <b className="text-wg-accent">草案未審批</b> — 此{label}需 signoff 後方可執行。
      </div>
    );
  }
  return (
    <div role="status" data-testid="signoff-banner" className="mb-5 flex items-center gap-3 rounded-md border border-wg-draft-border bg-wg-draft-bg px-[18px] py-3.5 max-md:flex-wrap">
      <ShieldAlert size={22} className="shrink-0 text-wg-accent" aria-hidden />
      {body}
      <Button iconLeft={Check} onClick={onApprove} disabled={!canApprove} title={canApprove ? undefined : "權限不足（唯讀角色不可審批）"}>
        {kind === "project" ? "審批 signoff" : "審批"}
      </Button>
    </div>
  );
}
