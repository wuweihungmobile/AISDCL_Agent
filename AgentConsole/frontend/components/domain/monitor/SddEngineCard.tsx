"use client";

import { useState, useSyncExternalStore, type ReactNode } from "react";

import { SddEscalationBlock } from "@/components/domain/sdd/SddEscalationBlock";
import { SddPhaseProgress } from "@/components/domain/sdd/SddPhaseProgress";
import { Card, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusDot } from "@/components/ui/status-dot";
import { ErrorState } from "@/components/ui/states";
import { SDD_POLL_MS, useSddEngine } from "@/lib/api/queries";
import { SDD_EMPTY_MESSAGE, pickSddProject, sddFsmNotFoundHint, sddHumanPending, sddReasonMessage, sddRecentDecisions, sddSprint, sddText, sddTime } from "@/lib/domain/sdd";
import { getRememberedSddProject, getServerRememberedSddProject, rememberSddProject, subscribeSddProject } from "@/lib/nav/sddProject";

const OK = "var(--color-primary)";
const DOWN = "var(--color-error)";

/** 監控頁所屬的 Console 專案的 SDD 綁定（契約 §4.3 M-21）：`sddProject` 非空才進專案模式。 */
export type SddCardBinding = { projectId: string; sddProject?: string | null; executionPath?: string };

/**
 * 「AISDLC_SDD 引擎」卡（PRD §0.2／§0.3 把 FSM-STATE 列為對 SDD 的遙測來源；契約 §1.7.1、§4.3 M-20、M-21；v1.4 D-16，API-ENG-01、NFR-OBS-01；v1.5 整合輪 115，API-ENG-02、UI-SDD-03）：
 * 引擎狀態點與版本、FSM 專案下拉、選定專案的目前狀態／Sprint／更新時間／待人工／**階段進度與 ESCALATION 標示**（v1.5）／最近決策（尾 5 筆、新到舊）。
 * 卡片仍然**唯讀**：沒有任何寫入動作（核准凍結只出現在專案詳情的「SDD 治理」區）；恢復指令的「複製」不是寫入，且 Console 不提供恢復動作。
 *
 * 兩種模式（契約 M-21 ①）：
 *  - 全域模式（M-20，沒有 `binding` 或專案沒有綁定 FSM 專案）：兩段請求——先不帶 `project` 取版本與專案清單（`fsm=null`），再依下面的規則選定專案、帶 `project` 取它的 FSM；
 *    預設專案＝上次選的且仍在清單內者（`localStorage` 記住，只是方便）、否則清單第一個。選定後只輪詢「選定專案」那一份（30 秒；分頁不可見時 TanStack Query 預設暫停），
 *    所以一張開著的卡片約每分鐘 2 次請求；清單是空的（或引擎不可用）時才輪詢不帶 `project` 那份，等它復原。SDD 引擎是全域的，不隨 Console 專案或執行批次的下拉變動。
 *  - 專案模式（M-21，專案有 `sddProject`）：只有一個請求 `GET /engines/sdd?projectId=`——後端取專案根下的有效 FSM 專案（`sddProject`），一個請求就帶回 fsm 與同一個狀態目錄的專案清單；
 *    下拉仍可改選同一個狀態目錄內的其他 FSM 專案（改帶 `project`）。不使用也不寫入 localStorage 的「上次選的專案」（那是全域模式的方便，專案模式的預設就是綁定）。
 * 引擎不可用也回 200（`available=false`＋`reason`）：畫「不可用」與原因，不是錯誤頁；`isError` 只代表 console-api 自己連不上（含專案模式的 404）。
 * `retryHistory`、`rtmCoverage`、`frozenStages` 不顯示（資料留在 API，供 NFR-OBS-01 對照與日後使用）；`version.root` 是 Bridge 端的路徑，只秀 `latest`。
 */
export function SddEngineCard({ pollMs = SDD_POLL_MS, binding }: { pollMs?: number; binding?: SddCardBinding }) {
  // 契約固定 30 秒；監控頁的輪詢設定（monitor.refreshIntervalMs）調得更慢時跟著放慢（不得比設定更密）
  const interval = Math.max(SDD_POLL_MS, pollMs);
  const projectMode = Boolean(binding && typeof binding.sddProject === "string" && binding.sddProject.trim() !== "");
  const remembered = useSyncExternalStore(subscribeSddProject, getRememberedSddProject, getServerRememberedSddProject);
  const [picked, setPicked] = useState<string | null>(null);

  // ── 全域模式（M-20）──
  const listQ = useSddEngine(null, { pollMs: interval, pollWhile: (d) => !d?.projects?.length, enabled: !projectMode });
  // 使用者在下拉明確選的優先（它來自畫面上的清單，不再驗證）；否則是預設規則——只看第一次取到的清單，所以不會與下面那份互相依賴
  const globalSelected = picked ?? pickSddProject(listQ.data?.projects, remembered);
  const fsmQ = useSddEngine(globalSelected, { pollMs: interval, enabled: !projectMode && globalSelected !== null });
  // 沒選定專案時 fsmQ 與 listQ 是同一個查詢鍵（project＝null）：只在選定後才採用 fsmQ 的資料，免得把「清單那份」誤當成專案的 FSM
  const fsmData = !projectMode && globalSelected !== null ? fsmQ.data : undefined;

  // ── 專案模式（M-21）：單一查詢；picked＝null 時由後端取有效 FSM 專案 ──
  const projQ = useSddEngine(projectMode ? picked : null, { pollMs: interval, projectId: projectMode ? binding?.projectId : undefined, enabled: projectMode });

  const firstStage = projectMode ? projQ : listQ; // 第一階段：取得狀態與專案清單
  const status = projectMode ? projQ.data : (fsmData ?? listQ.data); // 全域模式：選定專案那份更新（含最新的專案清單）；還沒回來之前先用第一份的版本與清單
  const fsm = (projectMode ? projQ.data?.fsm : fsmData?.fsm) ?? null;
  const fsmStageError = !projectMode && fsmQ.isError && !fsmData;
  const fsmStageLoading = !projectMode && !fsmData;
  const decisions = sddRecentDecisions(fsm?.decisionTrace);
  const pending = sddHumanPending(fsm?.humanPending);
  const reasonText = sddReasonMessage(status?.reason);
  const engineDown = status ? !status.available : false;

  // 下拉選項＝最新的專案清單；選定的專案若已不在清單內（檔案被刪、或綁定的名字沒有狀態檔），仍列出並註明，不讓下拉與畫面內容脫鉤
  const projects = status?.projects ?? [];
  const names = projects.map((p) => p.project);
  const selected = projectMode ? (picked ?? fsm?.fsmProject ?? binding?.sddProject ?? null) : globalSelected;
  const options = selected !== null && !names.includes(selected) ? [...names, selected] : names;

  function retry() {
    if (projectMode) {
      void projQ.refetch();
      return;
    }
    void listQ.refetch();
    if (globalSelected !== null) void fsmQ.refetch();
  }

  /** 引擎可用、但所選專案取不到 FSM 的說明框；專案模式且知道專案根時，找不到狀態檔另附建立位置（契約 §4.7.1 的同一句處置）。 */
  const message = (fallback: string) => (
    <div role="status" data-testid="sdd-message" data-reason={status?.reason ?? undefined} className="rounded-md border border-wg-alert-border bg-wg-alert-bg px-3 py-2 text-sm">
      {reasonText ?? fallback}
      {projectMode && binding?.executionPath && status?.reason === "fsm_not_found" ? (
        <span className="mt-0.5 block text-wg-muted" data-testid="sdd-message-hint">
          {sddFsmNotFoundHint(binding.executionPath)}
        </span>
      ) : null}
    </div>
  );

  let body: ReactNode;
  if (!status && firstStage.isError) {
    body = <ErrorState error={firstStage.error} onRetry={retry} title="無法取得 AISDLC_SDD 引擎狀態" />;
  } else if (!status) {
    body = <Skeleton className="h-24" />;
  } else if (engineDown) {
    // 用 div 不用 p：設計系統的全域規則把 `p` 的寬度上限設為 800px（可讀行寬），有邊框的訊息框會比卡片窄一截
    body = message("AISDLC_SDD 引擎目前不可用");
  } else if (projects.length === 0 && !fsm) {
    // 專案模式的 sdd_root_rejected 等也是 projects=[]、fsm=null：有 reason 就說原因，沒有 reason 才是「尚無狀態檔」（不是錯誤）
    body = status.reason ? (
      message("取不到所選專案的 FSM 狀態")
    ) : (
      <p data-testid="sdd-empty" className="py-2 text-sm text-wg-muted">
        {SDD_EMPTY_MESSAGE}
        {projectMode && binding?.executionPath ? <span className="mt-0.5 block">{sddFsmNotFoundHint(binding.executionPath)}</span> : null}
      </p>
    );
  } else if (fsmStageError) {
    body = <ErrorState error={fsmQ.error} onRetry={retry} title="無法取得 FSM 狀態" />;
  } else if (fsmStageLoading) {
    body = <Skeleton className="h-24" />;
  } else if (!fsm) {
    // 引擎可用、但所選專案取不到 FSM：fsm_not_found（檔案不存在）或 fsm_state_unreadable（YAML 壞掉或寫到一半；下一輪輪詢會恢復）
    body = message("取不到所選專案的 FSM 狀態");
  } else {
    body = (
      <>
        <div className="grid grid-cols-4 gap-x-6 gap-y-3 max-lg:grid-cols-2" data-testid="sdd-fsm" data-project={fsm.project}>
          <div>
            <div className="text-xs text-wg-muted">目前狀態</div>
            <div className="mt-1 font-mono text-[15px] font-medium break-all" data-testid="sdd-state">
              {sddText(fsm.currentState)}
            </div>
          </div>
          <div>
            <div className="text-xs text-wg-muted">Sprint</div>
            <div className="mt-1 text-[15px]" data-testid="sdd-sprint">
              {sddSprint(fsm.currentSprint)}
            </div>
          </div>
          <div>
            <div className="text-xs text-wg-muted">更新時間</div>
            <div className="mt-1 text-[15px]" data-testid="sdd-updated" title={typeof fsm.updatedAt === "string" ? fsm.updatedAt : undefined}>
              {sddTime(fsm.updatedAt)}
            </div>
          </div>
          <div>
            <div className="text-xs text-wg-muted">待人工</div>
            <div className="mt-1 text-[15px]">
              {pending.count > 0 ? (
                <details>
                  <summary className="cursor-pointer font-medium text-wg-accent" data-testid="sdd-human-pending">
                    {pending.label}
                  </summary>
                  <ul className="mt-1 text-[13px] text-wg-muted" data-testid="sdd-human-pending-items">
                    {pending.enteredAt.map((t, i) => (
                      <li key={i}>進入時間：{t}</li>
                    ))}
                  </ul>
                </details>
              ) : (
                <span data-testid="sdd-human-pending">{pending.label}</span>
              )}
            </div>
          </div>
        </div>

        {/* 階段進度（放在「目前狀態」那一列下方）與 ESCALATION 區塊（契約 §4.7.3、M-21 ②）：phase 缺席時只有「階段 —」，不崩潰 */}
        <div className="mt-4" data-testid="sdd-phase-section">
          <SddPhaseProgress fsm={fsm} />
        </div>
        <div className="mt-3 empty:hidden">
          <SddEscalationBlock fsm={fsm} />
        </div>

        <div className="mt-4">
          <div className="mb-1.5 text-xs text-wg-muted">最近決策（新到舊，最多 5 筆）</div>
          {decisions.length === 0 ? (
            <p className="text-sm text-wg-muted" data-testid="sdd-decisions-empty">
              尚無決策紀錄
            </p>
          ) : (
            <ol className="flex flex-col" data-testid="sdd-decisions" aria-label="最近決策">
              {decisions.map((d, i) => (
                <li key={i} data-testid="sdd-decision" className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 border-t border-wg-line py-1.5 text-[13px] first:border-t-0">
                  <span className="font-mono text-xs text-wg-muted" data-testid="sdd-decision-ts">
                    {d.ts}
                  </span>
                  <span className="font-medium" data-testid="sdd-decision-transition">
                    {d.from} → {d.to}
                  </span>
                  <span className="min-w-0 break-words text-wg-muted" data-testid="sdd-decision-reason">
                    {d.reason}
                  </span>
                </li>
              ))}
            </ol>
          )}
        </div>
      </>
    );
  }

  return (
    <Card className="px-[22px] py-5" data-testid="sdd-card" data-mode={projectMode ? "project" : "global"}>
      <div className="mb-3.5 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <CardTitle>AISDLC_SDD 引擎</CardTitle>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          {status ? (
            <span className="inline-flex items-center gap-2 text-sm" data-testid="sdd-status" data-available={String(status.available)}>
              <StatusDot color={status.available ? OK : DOWN} size={10} />
              {status.available ? "可用" : "不可用"}
              {status.available ? (
                <>
                  <span aria-hidden className="text-wg-muted">
                    ·
                  </span>
                  <span className="font-mono text-[13px]" data-testid="sdd-version">
                    {status.version?.latest ?? "—"}
                  </span>
                </>
              ) : null}
            </span>
          ) : null}
          {/* 專案模式且這個專案根下一個狀態檔都沒有（sdd_root_rejected、尚未建立）：沒有東西可選，也不假裝綁定的名字曾經存在過 */}
          {status?.available && options.length > 0 && !(projectMode && names.length === 0) ? (
            <label className="inline-flex items-center gap-2 text-sm text-wg-muted">
              FSM 專案
              <Select
                size="sm"
                value={selected ?? ""}
                onChange={(e) => {
                  setPicked(e.target.value);
                  // 「上次選的專案」是全域模式的方便；專案模式的預設就是專案的綁定，不去動它
                  if (!projectMode) rememberSddProject(e.target.value);
                }}
                aria-label="FSM 專案"
                data-testid="sdd-project-select"
              >
                {options.map((name) => (
                  <option key={name} value={name}>
                    {names.includes(name) ? name : `${name}（狀態檔已不存在）`}
                  </option>
                ))}
              </Select>
            </label>
          ) : null}
        </div>
      </div>
      {body}
    </Card>
  );
}
