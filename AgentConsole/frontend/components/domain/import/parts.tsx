import { AlertTriangle, Info } from "lucide-react";
import type { ReactNode } from "react";

import type { ParseWarning } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { gateLabel, type ParseFailure } from "./gateErrors";

/** 步驟標題：綠圓 26px 白字步驟號＋標題（設計稿「步驟 1 卡」「步驟 2 卡」）。 */
export function StepHeader({ step, title, right }: { step: number; title: string; right?: ReactNode }) {
  return (
    <div className="mb-[18px] flex flex-wrap items-center gap-2.5">
      <span aria-hidden className="inline-flex size-[26px] shrink-0 items-center justify-center rounded-full bg-wg-primary text-sm font-semibold text-white">
        {step}
      </span>
      <h3 className="text-lg font-semibold">{title}</h3>
      {right ? <div className="ml-auto flex flex-wrap items-center gap-2">{right}</div> : null}
    </div>
  );
}

/** 契約 §3.3.6 的 warnings[].code → 給人看的說明（未知 code 退回原字串）。 */
export const WARNING_LABEL: Record<string, string> = {
  evaluator_command_dropped: "驗證命令含禁用字元，已被清空",
  regex_dropped: "期望輸出 regex 無法編譯，已被清空",
  passcriteria_placeholder: "通過標準是佔位字串，signoff 前請補齊",
};

/** 解析提示（US-I-08 之外的非阻擋提示；契約 §4.1 I-12）：黃色提示列，逐項列出。 */
export function ParseWarnings({ warnings }: { warnings: readonly ParseWarning[] }) {
  if (warnings.length === 0) return null;
  return (
    <div role="status" data-testid="parse-warnings" className="mb-4 rounded-md border border-wg-alert-border bg-wg-alert-bg px-4 py-3">
      <div className="flex items-center gap-2 text-sm font-semibold">
        <Info size={18} className="shrink-0 text-wg-warning" aria-hidden />
        解析提示（共 {warnings.length} 項，不阻擋儲存）
      </div>
      <ul className="mt-2 flex flex-col gap-1.5">
        {warnings.map((w, i) => (
          <li key={`${i}-${w.code}-${w.location ?? ""}`} data-testid="parse-warning" className="text-sm break-words">
            <span className="font-medium">{WARNING_LABEL[w.code] ?? w.code}</span>
            {w.location ? <code className="ml-2 font-mono text-xs break-all text-wg-muted">{w.location}</code> : null}
            {w.detail ? <span className="ml-2 text-wg-muted">{w.detail}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * 解析失敗面板（US-I-10）：標題＋逐項清單（閘別、位置、完整原因）。
 * 刻意沒有任何截斷：不用 truncate／line-clamp、不限制列數，違規有幾項就列幾項（後端一次回報全部）。
 */
export function ParseFailurePanel({ failure, className }: { failure: ParseFailure; className?: string }) {
  const count = failure.rows.length;
  return (
    <div role="alert" data-testid="parse-failure" className={cn("rounded-md border border-wg-draft-border bg-wg-draft-bg px-4 py-3.5", className)}>
      <div className="flex items-start gap-2.5">
        <AlertTriangle size={20} className="mt-0.5 shrink-0 text-wg-accent" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="font-semibold break-words text-wg-accent" data-testid="parse-failure-title">
            {failure.title}
            {count > 0 ? `（共 ${count} 項）` : ""}
          </p>
          {failure.message ? <p className="mt-0.5 text-sm break-words text-wg-text">{failure.message}</p> : null}
          {failure.notes.map((note) => (
            <p key={note} className="mt-0.5 text-sm break-words text-wg-text">
              {note}
            </p>
          ))}
          {count > 0 ? (
            <ol data-testid="gate-error-list" className="mt-2.5 flex flex-col gap-2">
              {failure.rows.map((row, i) => (
                <li key={`${i}-${row.gate ?? ""}-${row.location ?? ""}`} data-testid="gate-error-row" className="flex flex-col gap-1 rounded-md border border-wg-draft-border bg-white px-3 py-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span data-testid="gate-error-gate" className="rounded-sm bg-wg-draft-bg px-[7px] py-0.5 text-xs font-semibold text-wg-accent">
                      {row.gate ? gateLabel(row.gate) : "欄位"}
                    </span>
                    {row.gate ? <code className="font-mono text-xs text-wg-muted">{row.gate}</code> : null}
                    {row.location ? (
                      <code data-testid="gate-error-location" className="font-mono text-xs break-all text-wg-muted">
                        {row.location}
                      </code>
                    ) : null}
                  </div>
                  <p data-testid="gate-error-detail" className="text-sm break-words text-wg-text">
                    {row.text}
                  </p>
                </li>
              ))}
            </ol>
          ) : null}
          {failure.traceId ? <p className="mt-2 font-mono text-xs text-wg-muted">traceId：{failure.traceId}</p> : null}
        </div>
      </div>
    </div>
  );
}
