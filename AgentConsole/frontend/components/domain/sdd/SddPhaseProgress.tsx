"use client";

/**
 * FSM 階段進度（契約 §4.7.3；UI-SDD-03、M-21）：八個步驟（立案→規格撰寫→人工確認→規格凍結→實作→審查→追溯驗證→發布）依序排列，
 * 「目前」「已過」「未到」各有形狀與文字（不只靠顏色）；觀測態另有「觀測中」標籤與虛線外框，委派中另有「委派 AutoClaude 執行中」；
 * 阻塞態：八個步驟全灰、上方紅色橫幅「阻塞：<currentState>（需人工恢復）」，並說明 Console 不提供恢復動作。
 * `phase` 缺席（W4 之前的 Bridge）或 order 為 0：不畫步驟，只有標籤（缺席「—」）。
 * 測試屬性：進度條 `data-testid="sdd-phase"` 帶 `data-phase`（phase.name）、`data-order`、`data-blocking`、`data-observation`（布林字串）。
 */
import { Check, OctagonAlert } from "lucide-react";

import type { SddFsmState } from "@/lib/api/types";
import { sddPhaseView, sddText, type SddStepState } from "@/lib/domain/sdd";
import { cn } from "@/lib/utils";

const STEP_STATE_TEXT: Record<SddStepState, string> = { done: "已過", current: "目前", upcoming: "未到" };

export function SddPhaseProgress({ fsm }: { fsm: Pick<SddFsmState, "currentState" | "phase"> }) {
  const view = sddPhaseView(fsm);
  return (
    <div data-testid="sdd-phase" data-phase={view.name ?? undefined} data-order={view.order} data-blocking={String(view.blocking)} data-observation={String(view.observation)}>
      {view.blocking ? (
        <div role="alert" data-testid="sdd-blocked-banner" className="mb-2.5 flex items-start gap-2.5 rounded-md border border-wg-draft-border bg-wg-draft-bg px-3.5 py-2.5">
          <OctagonAlert size={20} className="mt-0.5 shrink-0 text-wg-accent" aria-hidden />
          <div className="min-w-0">
            <p className="font-semibold text-wg-accent">阻塞：{sddText(fsm.currentState)}（需人工恢復）</p>
            <p className="mt-0.5 text-[13px] text-wg-text">請在 SDD session 依恢復指令處理，Console 不提供恢復動作。</p>
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <span className="text-xs text-wg-muted">階段</span>
        <span className="text-[15px] font-medium" data-testid="sdd-phase-label">
          {view.label}
        </span>
        {view.observation ? (
          <span data-testid="sdd-phase-observation" className="rounded-sm border border-wg-alert-border bg-wg-alert-bg px-[7px] py-0.5 text-xs font-semibold text-wg-text">
            觀測中
          </span>
        ) : null}
        {view.delegated ? (
          <span data-testid="sdd-phase-delegated" className="rounded-sm border border-wg-primary bg-wg-tertiary px-[7px] py-0.5 text-xs font-semibold text-wg-text">
            委派 AutoClaude 執行中
          </span>
        ) : null}
      </div>

      {view.steps.length > 0 ? (
        <ol aria-label="階段進度" data-testid="sdd-phase-steps" className="mt-2.5 grid grid-cols-8 gap-1.5 max-lg:grid-cols-4 max-sm:grid-cols-2">
          {view.steps.map((step) => (
            <li
              key={step.name}
              data-testid="sdd-phase-step"
              data-step={step.name}
              data-state={step.state}
              aria-current={step.state === "current" ? "step" : undefined}
              className={cn(
                "flex min-w-0 flex-col gap-0.5 rounded-md border px-2 py-1.5 text-xs",
                step.state === "done" && "border-wg-line bg-wg-tertiary text-wg-text",
                step.state === "current" && cn("border-2 bg-wg-surface font-semibold text-wg-text", view.observation ? "border-dashed border-wg-primary" : "border-wg-primary"),
                step.state === "upcoming" && "border-wg-line bg-wg-base text-wg-muted",
              )}
            >
              <span className="flex items-center gap-1">
                {step.state === "done" ? <Check size={12} aria-hidden className="shrink-0 text-wg-primary" /> : <span aria-hidden>{step.order}</span>}
                <span className="min-w-0 break-words">{step.label}</span>
              </span>
              <span className="text-[11px] font-normal">{STEP_STATE_TEXT[step.state]}</span>
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}
