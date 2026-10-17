import { AlertTriangle, Info } from "lucide-react";
import type { ReactNode } from "react";

import { PARSE_WARNING_CODES } from "@/lib/api/reasons";
import type { ParsedResult, ParseWarning } from "@/lib/api/types";
import { sddText } from "@/lib/domain/sdd";
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

/**
 * 契約 §3.3.6 的 warnings[].code → 給人看的說明（未知 code 退回原字串）。
 * v1.5（整合輪 115；契約 §3.3.2 第 6 點）新增三個路徑 A 的黃色提示（不阻擋，signoff 前由人決定）：
 * at_unmapped 的 detail 列出「規格出現但未編成步驟的 AT」（即編譯回應的 `unmapped_at_ids`）。
 */
export const WARNING_LABEL: Record<string, string> = {
  evaluator_command_dropped: "驗證命令含禁用字元，已被清空",
  regex_dropped: "期望輸出 regex 無法編譯，已被清空",
  passcriteria_placeholder: "通過標準是佔位字串，signoff 前請補齊",
  [PARSE_WARNING_CODES.AT_UNMAPPED]: "規格出現、但未編成步驟的 AT（不會被執行；signoff 前請確認編號是否合文法）",
  [PARSE_WARNING_CODES.FROZEN_DIGEST_ABSENT]: "規格凍結時沒有記錄內容摘要（舊狀態檔），無法偵測凍結後改檔",
  [PARSE_WARNING_CODES.STATE_DIR_NOT_IGNORED]: "專案根的 build/reports/fsm/ 沒有被 git 忽略，請把 build/reports/ 加進該專案的 .gitignore",
};

/**
 * 路徑 A（規格驅動）的解析結果新欄位與併入說明（契約 §3.3.2 第 5 點、§1.10.8；整合輪 115，API-IMP-11／12）：
 * 規格格式版本（只供顯示與稽核，不閘控）、FSM 專案（標準鍵）、規格目錄、規格檔——都是伺服器擁有的欄位，**confirm 才回填**到專案
 * （parse／預覽不回填，放棄的草稿不留綁定）；缺值「—」。帶 `targetProjectId` 時另說明併入規則（新目標接在既有目標之後、專案層簽核不動）。
 * 路徑 B／C 的結果沒有這些欄位、也沒有 targetProjectId 時整塊不顯示。
 */
export function SddSpecInfo({ parsed, targetProjectId, targetName }: { parsed: Partial<ParsedResult>; targetProjectId?: string | null; targetName?: string | null }) {
  const hasSpec = [parsed.specFormatVersion, parsed.sddProject, parsed.sddSpecDir, parsed.sddSpecFile].some((v) => typeof v === "string" && v !== "");
  if (!hasSpec && !targetProjectId) return null;
  const mono = (value: string | undefined) => <span className={value ? "font-mono text-[13px] break-all" : undefined}>{sddText(value)}</span>;
  return (
    <div data-testid="sdd-spec-info" className="mb-4 rounded-md border border-wg-line bg-wg-base px-4 py-3">
      {hasSpec ? (
        <>
          <div className="mb-2 text-sm font-semibold">規格資訊（規格驅動 SDD）</div>
          <dl className="grid grid-cols-[150px_1fr] gap-x-4 gap-y-1.5 text-sm max-md:grid-cols-1 max-md:gap-y-0.5">
            <dt className="text-wg-muted">規格格式版本</dt>
            <dd data-testid="sdd-info-format">{mono(parsed.specFormatVersion)}</dd>
            <dt className="text-wg-muted">FSM 專案（標準鍵）</dt>
            <dd data-testid="sdd-info-project">{mono(parsed.sddProject)}</dd>
            <dt className="text-wg-muted">規格目錄</dt>
            <dd data-testid="sdd-info-dir">{mono(parsed.sddSpecDir)}</dd>
            <dt className="text-wg-muted">規格檔</dt>
            <dd data-testid="sdd-info-file">{mono(parsed.sddSpecFile)}</dd>
          </dl>
          <p className="mt-2 text-xs text-wg-muted">這些欄位要「確認匯入」成功後才會回填到專案；解析與預覽不會回填，放棄的草稿不會留下綁定。</p>
        </>
      ) : null}
      {targetProjectId ? (
        <p data-testid="sdd-merge-note" className={cn("text-sm", hasSpec && "mt-3 border-t border-wg-line pt-3")}>
          <b>併入既有專案</b>：確認匯入後不會建立新專案，而是把這份草稿的目標與任務併入「{targetName || `專案 ${targetProjectId.slice(0, 8)}`}
          」——新目標接在既有目標之後；專案本身的欄位與專案層的簽核都不動， 專案若尚未簽核，執行前仍須另外簽核。
        </p>
      ) : null}
    </div>
  );
}

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
