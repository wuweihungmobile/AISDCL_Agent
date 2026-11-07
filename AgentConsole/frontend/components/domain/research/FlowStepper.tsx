"use client";

/**
 * 工作流五步列（FR-R2P-01；TCS-ResearchToPRD-P0-20261102 AT-960-19-3）：**整個工作區唯一一份五步列實作**——工作區的五個面板與清單頁的迷你步驟列都用它，
 * 不得每個面板各寫一份（`components/domain/research/**` 內的掃描）。步驟與狀態由 `lib/domain/research.ts` 的 `deriveSteps` 算出（已完成／進行中／受阻／待做），
 * 本元件只負責畫：
 *  - 每項的可及名稱含狀態文字（`aria-label`＝「序號 名稱，狀態」，畫面上也印出狀態文字），不只靠顏色與圖示；
 *  - 有連結的項（`hrefFor` 回網址）是 `<a>`，回 null 的項（超前、不可達）只顯示文字，不是連結；
 *  - `compact`：清單列的迷你版——只印序號圓點，名稱與狀態改為只給螢幕閱讀器。
 */
import { Check, ChevronRight, Circle, CircleDot, FileDiff, TriangleAlert, type LucideIcon } from "lucide-react";
import Link from "next/link";

import type { ResearchFlowStepId, ResearchFlowStepState } from "@/lib/api/types";
import { STEP_STATE_LABEL, type ResearchStepView } from "@/lib/domain/research";
import { cn } from "@/lib/utils";

const STATE_ICON: Readonly<Record<ResearchFlowStepState, LucideIcon>> = { DONE: Check, CURRENT: CircleDot, BLOCKED: TriangleAlert, TODO: Circle };

/**
 * 狀態的底色與字色（只取設計 token；顏色只作輔助，意思由文字與圖示表達）。
 * 「已完成」的字用 primary-strong、框線維持主色：步驟 chip 沒有自己的底，字直接坐在頁面底色（bg-base）上，主色字在那上面只有 4.22:1（真瀏覽器 axe 回報 4.21，
 * 低於 WCAG AA 一般文字的 4.5:1）；primary-strong 是同一個綠加深（6.02:1），先例＝styles/tokens.console.css〈無障礙覆寫〉與 components/domain/sysadmin/tone.ts。
 */
const STATE_CLASS: Readonly<Record<ResearchFlowStepState, string>> = {
  DONE: "border-wg-primary text-wg-primary-strong",
  CURRENT: "border-wg-primary bg-wg-primary text-white",
  BLOCKED: "border-wg-draft-border bg-wg-draft-bg text-wg-accent",
  TODO: "border-wg-line text-wg-muted",
};

export function FlowStepper({
  steps,
  selected,
  hrefFor,
  compact = false,
  label = "研發工作流步驟",
  className,
  blockedReason,
  scrOpen = false,
}: {
  steps: readonly ResearchStepView[];
  /** 目前顯示的步驟（標 `aria-current="step"`） */
  selected?: ResearchFlowStepId;
  /** 步驟的連結；回 null＝不可達，只顯示文字 */
  hrefFor?: (step: ResearchFlowStepId) => string | null;
  compact?: boolean;
  label?: string;
  className?: string;
  /** 受阻步驟旁顯示的原因（取游標 `flow_detail` 的純文字；P1：分流失敗時為失敗步驟名）。只在非精簡版、狀態為受阻的那一項顯示。 */
  blockedReason?: string;
  /** 規格變更請求進行中（`flowPhase` 為 `SCR_OPEN`）：在步驟列尾端標示「SCR 進行中」（P1；AT-961-19-4） */
  scrOpen?: boolean;
}) {
  return (
    <ol aria-label={label} data-testid="flow-stepper" data-compact={compact || undefined} className={cn("flex flex-wrap items-center", compact ? "gap-1" : "gap-x-1 gap-y-2", className)}>
      {steps.map((step, index) => {
        const Icon = STATE_ICON[step.state];
        const stateText = STEP_STATE_LABEL[step.state];
        const href = hrefFor?.(step.id) ?? null;
        const selectedHere = selected === step.id;
        const chip = (
          <span className={cn("inline-flex items-center gap-1.5 rounded-md border", compact ? "px-1.5 py-0.5 text-xs" : "px-3 py-1.5 text-sm", STATE_CLASS[step.state])}>
            <Icon size={compact ? 12 : 16} aria-hidden />
            <span className="font-semibold">{step.number}</span>
            {compact ? (
              <span className="sr-only">
                {step.label}，{stateText}
              </span>
            ) : (
              <>
                <span className="font-medium">{step.label}</span>
                <span className="text-xs">{stateText}</span>
                {step.state === "BLOCKED" && blockedReason ? (
                  <span data-testid="flow-step-blocked-reason" title={blockedReason} className="max-w-[16rem] truncate text-xs">
                    原因：{blockedReason}
                  </span>
                ) : null}
              </>
            )}
          </span>
        );
        return (
          <li key={step.id} data-testid={`flow-step-${step.id}`} data-state={step.state} aria-label={`${step.number} ${step.label}，${stateText}`} className="flex items-center gap-1">
            {href ? (
              <Link
                href={href}
                aria-current={selectedHere ? "step" : undefined}
                className={cn("rounded-md transition-colors hover:opacity-80", selectedHere && "outline outline-2 outline-offset-2 outline-wg-primary")}
              >
                {chip}
              </Link>
            ) : (
              <span aria-current={selectedHere ? "step" : undefined} className={cn("rounded-md", selectedHere && "outline outline-2 outline-offset-2 outline-wg-primary")}>
                {chip}
              </span>
            )}
            {index < steps.length - 1 ? <ChevronRight size={compact ? 12 : 16} aria-hidden className="text-wg-muted" /> : null}
          </li>
        );
      })}
      {scrOpen ? (
        <li data-testid="flow-scr-open" aria-label="SCR 進行中" className="flex items-center gap-1">
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md border border-wg-alert-border bg-wg-alert-bg font-medium text-wg-warning-text",
              compact ? "px-1.5 py-0.5 text-xs" : "px-3 py-1.5 text-sm",
            )}
          >
            <FileDiff size={compact ? 12 : 16} aria-hidden />
            SCR 進行中
          </span>
        </li>
      ) : null}
    </ol>
  );
}
