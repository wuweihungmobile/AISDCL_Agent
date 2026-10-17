"use client";

/**
 * 專案詳情「SDD 治理」區（契約 §4.7.1；UI-SDD-01；G-07、D-115-03、D-115-14）：位置在目標清單之下、「執行專案」等行動列之上。
 * 🔴 沒有「未綁定」狀態（Console 專案是錨，FSM 專案預設＝專案名）：專案從未使用 SDD（sddProject／sddSpecDir／sddSpecFile 皆空）時預設收合、
 * 標題「SDD 治理（尚未使用）」，展開後內容與已使用者相同（只是 fsm 通常為 null）；已使用時預設展開。收合時不輪詢（不發任何請求）。
 * 資料：專案詳情的綁定三欄（呼叫端傳入）＋ `GET /engines/sdd?projectId=`（FSM 狀態；30 秒輪詢、分頁不可見時暫停，與監控頁 SDD 卡同節奏）。
 * 缺值（null、缺席、空字串、無法解析）一律單一的「—」；「SDD 專案」缺值顯示「（預設：<專案名>）」。
 * OPERATOR 以上才看得到「編輯」與「核准凍結」（VIEWER 不顯示）；核准凍結只在 FSM 為 HUMAN_PENDING 時可按（其他狀態停用並說明）。
 */
import { ChevronDown, ChevronRight, Pencil, ShieldCheck } from "lucide-react";
import { useId, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";
import { useSddEngine } from "@/lib/api/queries";
import type { ProjectDetail } from "@/lib/api/types";
import { SDD_DASH, SDD_EMPTY_MESSAGE, sddFrozenSummary, sddFsmNotFoundHint, sddHumanPending, sddKeyDisplay, sddProjectDisplay, sddReasonMessage, sddText, sddUsed } from "@/lib/domain/sdd";
import { SddBindingDialog } from "./SddBindingDialog";
import { SddEscalationBlock } from "./SddEscalationBlock";
import { SddFreezeDialog } from "./SddFreezeDialog";
import { SddPhaseProgress } from "./SddPhaseProgress";

/** 靜態提示（契約 §4.7.1 區塊底部）。 */
export const SDD_STATE_DIR_NOTE = "FSM 狀態檔位於專案根的 build/reports/fsm，請把 build/reports/ 加入該專案的 .gitignore。";

function Row({ label, testid, children }: { label: string; testid: string; children: ReactNode }) {
  return (
    <div className="contents">
      <dt className="pt-0.5 text-[13px] text-wg-muted">{label}</dt>
      <dd data-testid={testid} className="min-w-0 text-[15px]">
        {children}
      </dd>
    </div>
  );
}

const MONO = "font-mono text-sm break-all";

export function SddGovernanceCard({ project, canWrite }: { project: ProjectDetail; canWrite: boolean }) {
  const used = sddUsed(project);
  const [userExpanded, setUserExpanded] = useState<boolean | null>(null);
  const expanded = userExpanded ?? used;
  const panelId = useId();
  const hintId = useId();
  const [editing, setEditing] = useState(false);
  const [freezing, setFreezing] = useState(false);

  // 收合時不發請求、不輪詢（enabled=false）；展開後 30 秒輪詢，分頁不可見時 TanStack Query 預設暫停
  const engine = useSddEngine(null, { projectId: project.id, enabled: expanded });
  const status = engine.data;
  const fsm = status?.fsm ?? null;
  const loading = !status && !engine.isError;
  const failed = engine.isError && !status;

  const binding = sddProjectDisplay(project.sddProject, project.name);
  const key = sddKeyDisplay(fsm);
  const pending = sddHumanPending(fsm?.humanPending);
  const canFreeze = fsm?.currentState === "HUMAN_PENDING";
  const freezeHint = `FSM 目前不在 HUMAN_PENDING（目前：${sddText(fsm?.currentState)}）`;

  /** FSM 欄位的共同呈現：載入中骨架、取得時顯示值、取不到一律「—」。 */
  const fsmCell = (render: () => ReactNode): ReactNode => (loading ? <Skeleton className="h-5 w-40" /> : fsm ? render() : SDD_DASH);

  let stateCell: ReactNode;
  if (loading) stateCell = <Skeleton className="h-5 w-40" />;
  else if (fsm) stateCell = <span className="font-mono text-[15px] break-all">{sddText(fsm.currentState)}</span>;
  else if (failed) stateCell = SDD_DASH;
  else {
    // 引擎不可用，或所選專案取不到 FSM：依 reason 顯示 M-20 的文案；找不到狀態檔時加註怎麼建立（契約 §4.7.1「目前狀態」列）
    const reason = status?.reason ?? null;
    const message = reason ? (sddReasonMessage(reason) ?? SDD_EMPTY_MESSAGE) : SDD_EMPTY_MESSAGE;
    const needsHint = reason === null || reason === "fsm_not_found";
    stateCell = (
      <div role="status" data-testid="sdd-gov-message" data-reason={reason ?? undefined} className="rounded-md border border-wg-alert-border bg-wg-alert-bg px-3 py-2 text-sm">
        <p>{message}</p>
        {needsHint ? (
          <p className="mt-0.5 text-wg-muted" data-testid="sdd-gov-hint">
            {sddFsmNotFoundHint(project.executionPath)}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <Card className="mb-6 px-[22px] py-5" data-testid="sdd-governance" data-used={String(used)} data-expanded={String(expanded)}>
      <CardTitle>
        <button
          type="button"
          aria-expanded={expanded}
          aria-controls={panelId}
          data-testid="sdd-governance-toggle"
          onClick={() => setUserExpanded(!expanded)}
          className="inline-flex cursor-pointer items-center gap-1.5 rounded-sm border-none bg-transparent p-0 text-left text-lg font-semibold transition-colors hover:text-wg-primary"
        >
          {expanded ? <ChevronDown size={18} aria-hidden /> : <ChevronRight size={18} aria-hidden />}
          {used ? "SDD 治理" : "SDD 治理（尚未使用）"}
        </button>
      </CardTitle>

      {expanded ? (
        <div id={panelId} data-testid="sdd-governance-body" className="mt-4">
          <dl className="grid grid-cols-[160px_1fr] gap-x-6 gap-y-3.5 max-md:grid-cols-1 max-md:gap-y-1">
            <Row label="SDD 專案" testid="sdd-gov-project">
              <span className="flex flex-wrap items-center gap-2">
                <span className={binding.isDefault ? "text-wg-muted" : MONO} data-default={String(binding.isDefault)}>
                  {binding.text}
                </span>
                {canWrite ? (
                  <Button variant="ghost" size="sm" iconLeft={Pencil} aria-label="編輯 SDD 專案" data-testid="sdd-binding-edit" onClick={() => setEditing(true)}>
                    編輯
                  </Button>
                ) : null}
              </span>
            </Row>
            <Row label="標準鍵" testid="sdd-gov-key">
              {fsmCell(() => (
                <span className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                  <span className={MONO}>{key.key}</span>
                  {key.originalName ? (
                    <span className="text-[13px] text-wg-muted" data-testid="sdd-gov-original-name">
                      <span className={MONO}>{key.originalName}</span>（檔內原名）
                    </span>
                  ) : null}
                </span>
              ))}
            </Row>
            <Row label="規格目錄" testid="sdd-gov-dir">
              <span className={project.sddSpecDir ? MONO : undefined}>{sddText(project.sddSpecDir)}</span>
            </Row>
            <Row label="規格檔" testid="sdd-gov-file">
              <span className={project.sddSpecFile ? MONO : undefined}>{sddText(project.sddSpecFile)}</span>
            </Row>
            <Row label="目前狀態" testid="sdd-gov-state">
              {stateCell}
            </Row>
            <Row label="階段" testid="sdd-gov-phase">
              {fsmCell(() => (fsm ? <SddPhaseProgress fsm={fsm} /> : SDD_DASH))}
            </Row>
            <Row label="凍結狀態" testid="sdd-gov-frozen">
              {fsmCell(() => sddFrozenSummary(fsm?.frozenStages))}
            </Row>
            <Row label="待人工" testid="sdd-gov-pending">
              {fsmCell(() => pending.label)}
            </Row>
          </dl>

          {failed ? (
            <div className="mt-4">
              <ErrorState error={engine.error} onRetry={() => engine.refetch()} title="無法取得 SDD 治理狀態" />
            </div>
          ) : null}

          {fsm ? (
            <div className="mt-4 empty:hidden">
              <SddEscalationBlock fsm={fsm} />
            </div>
          ) : null}

          {canWrite ? (
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Button
                iconLeft={ShieldCheck}
                disabled={!canFreeze}
                title={canFreeze ? undefined : freezeHint}
                aria-describedby={canFreeze ? undefined : hintId}
                data-testid="sdd-freeze-button"
                onClick={() => setFreezing(true)}
              >
                核准凍結
              </Button>
              {canFreeze ? null : (
                <span id={hintId} data-testid="sdd-freeze-hint" className="text-[13px] text-wg-muted">
                  {freezeHint}
                </span>
              )}
            </div>
          ) : null}

          <p data-testid="sdd-gov-note" className="mt-4 text-xs leading-relaxed text-wg-muted">
            {SDD_STATE_DIR_NOTE}
          </p>

          <SddBindingDialog project={project} open={editing} onClose={() => setEditing(false)} />
          <SddFreezeDialog project={project} open={freezing} onClose={() => setFreezing(false)} />
        </div>
      ) : null}
    </Card>
  );
}
