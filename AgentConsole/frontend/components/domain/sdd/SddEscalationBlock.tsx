"use client";

/**
 * ESCALATION 區塊（契約 §4.7.3；UI-SDD-03；ADR-XPLAT-016 §5.3）：`phase.blocking=true`，或 `currentState` 為 ESCALATION／ESCALATION_FINAL 時顯示——
 * `escalationHistory` 末筆「ESCALATION・<triggered_at 本機時區>・<trigger_reason>」（有 resolved_at 時加「已解決：…」）、
 * `escalationProvenance` 有值時的「來源」行、`fsm.recovery` 有值時的恢復指令（PowerShell 與 POSIX 各一段，各有複製鈕）。
 * 🔴 Console 不提供恢復動作：恢復只有人、留在 SDD session；指令內的 `<人工原因>` 由使用者自行替換；`fsm.recovery` 缺席時不顯示指令，
 * 也不得由前端自行組（目標與路徑由 Bridge 決定）。「有沒有未解的升級」的判斷式見 lib/domain/sdd.ts 的 sddHasUnresolvedEscalation（不得只看 provenance）。
 * 測試屬性：區塊 `data-testid="sdd-escalation"`；恢復指令 `data-testid="sdd-recovery"`（內含 `data-shell="powershell"｜"posix"` 的兩段）。
 */
import { TriangleAlert } from "lucide-react";

import type { SddFsmState } from "@/lib/api/types";
import { sddEscalationView, sddRecoveryView, sddShowsEscalation } from "@/lib/domain/sdd";
import { CopyCommand } from "./CopyCommand";

export function SddEscalationBlock({ fsm }: { fsm: Pick<SddFsmState, "currentState" | "phase" | "escalationHistory" | "escalationProvenance" | "recovery"> }) {
  if (!sddShowsEscalation(fsm)) return null;
  const view = sddEscalationView(fsm);
  const recovery = sddRecoveryView(fsm.recovery);
  return (
    <div data-testid="sdd-escalation" data-unresolved={String(view.unresolved)} className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-4 py-3">
      <div className="flex items-start gap-2.5">
        <TriangleAlert size={20} className="mt-0.5 shrink-0 text-wg-accent" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="font-semibold break-words text-wg-accent" data-testid="sdd-escalation-summary">
            {view.summary}
          </p>
          {view.resolved ? (
            <p className="mt-0.5 text-sm break-words text-wg-text" data-testid="sdd-escalation-resolved">
              {view.resolved}
            </p>
          ) : null}
          {view.source ? (
            <p className="mt-0.5 text-sm break-words text-wg-text" data-testid="sdd-escalation-source">
              {view.source}
            </p>
          ) : null}

          {recovery ? (
            <div data-testid="sdd-recovery" className="mt-3 border-t border-wg-draft-border pt-3">
              <h4 className="text-sm font-semibold">恢復（在 SDD session 執行；Console 不提供恢復動作）</h4>
              <p className="mt-0.5 text-[13px] text-wg-text">
                建議恢復到 <span className="font-mono">{recovery.target}</span>。指令內的 <span className="font-mono">&lt;人工原因&gt;</span> 請自行替換為實際原因；Console 不替換、也不執行它。
              </p>
              <div className="mt-2 flex flex-col gap-3">
                {recovery.commands.map((c) => (
                  <CopyCommand key={c.shell} shell={c.shell} label={c.label} command={c.command} />
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
