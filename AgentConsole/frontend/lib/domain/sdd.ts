/**
 * 「AISDLC_SDD 引擎」卡與專案詳情「SDD 治理」區的顯示規則（契約 §1.7.1、§4.3 M-20、M-21、§4.7；v1.4 D-16 API-ENG-01；v1.5 整合輪 115
 * API-ENG-02、UI-SDD-01／03）。純函式、不依賴 React。
 * 唯讀：Console 不寫 SDD 目錄與 FSM 狀態檔（唯一的 FSM 寫入動詞是 Bridge 的 `:freeze`，由 SddFreezeDialog 經 console-api 呼叫）；
 * FSM 的巢狀內容（decisionTrace、humanPending.items、escalationHistory…）是「檔案寫什麼就是什麼」，保留 snake_case 鍵與原值，
 * 畫面顯示不轉譯、不重排欄位，使「FSM 檔 ↔ API ↔ 畫面」可逐值比對（NFR-OBS-01、E2E-15 第 5 列）。
 * 缺值（null、缺席、空字串、無法解析）一律顯示單一的「—」；空陣列（確定沒有）與缺席（不知道）要分開（§4.7）。
 */
import type { SddEngineReason, SddFsmPhase, SddFsmState, SddHumanPending, SddProjectEntry, SddRecovery } from "@/lib/api/types";
import { formatClock, formatDate } from "@/lib/format";

/**
 * `reason` 的中文文案（契約 M-20；回應欄位的值，不是 ApiError.reason）：
 * 前三個是引擎不可用（available=false）；其餘是「引擎可用、但所選專案取不到 FSM」（available=true、fsm=null）；
 * v1.5 新增 `sdd_root_rejected`（M-21 ④）：帶了 projectId，而專案根不在 Bridge 允許的根目錄內（或已不存在）。
 */
export const SDD_REASON_MESSAGE: Record<SddEngineReason, string> = {
  bridge_unreachable: "Engine Bridge 無法連線",
  sdd_unavailable: "找不到 AISDLC_SDD 目錄（請檢查 Bridge 的 SDD_ROOT）",
  bridge_error: "Engine Bridge 回應異常",
  fsm_not_found: "找不到所選專案的 FSM 狀態檔",
  fsm_state_unreadable: "FSM 狀態檔無法讀取",
  sdd_root_rejected: "專案路徑不在 Bridge 允許的根目錄內（或已不存在）",
};

/** 缺值的單一顯示（契約 §4.7：不顯示 undefined、null 或「目前沒有提供這項資料」之類字樣）。 */
export const SDD_DASH = "—";

/**
 * 專案的 FSM 狀態目錄（契約 §4.7.1 的提示文字「請在專案根的 SDD session 建立：<executionPath>/build/reports/fsm」；ADR-XPLAT-016 §7.2）：
 * 專案根＝專案的 executionPath，狀態目錄固定是其下的 build/reports/fsm。結尾的分隔符先去掉，免得出現 `//`。
 */
export function sddStateDir(executionPath: string): string {
  return `${executionPath.replace(/[\\/]+$/, "")}/build/reports/fsm`;
}

/** `fsm_not_found` 時 FSM 找不到的處置說明（契約 §4.7.1「目前狀態」列）：狀態檔要先在專案根的 SDD session 建立。 */
export function sddFsmNotFoundHint(executionPath: string): string {
  return `請在專案根的 SDD session 建立：${sddStateDir(executionPath)}`;
}

/** `available=true` 且 `projects=[]`：SDD 目錄存在、但 SDD runtime 還沒跑過（正常狀態，不是錯誤）。 */
export const SDD_EMPTY_MESSAGE = "尚無 FSM 狀態檔（SDD runtime 執行後才會產生）";

/** 後端日後新增 reason 值：照樣顯示（附原值），不崩潰也不吞掉。 */
export function sddReasonMessage(reason: string | null | undefined): string | null {
  if (!reason) return null;
  return (SDD_REASON_MESSAGE as Record<string, string>)[reason] ?? `引擎回報：${reason}`;
}

/**
 * 預設選哪個 FSM 專案（契約 M-20）：上次選的且仍在清單內者（localStorage 記住，只是方便），否則清單第一個；沒有專案回 null。
 * 清單順序＝Bridge 順序（專案名不分大小寫升冪），不重排。
 */
export function pickSddProject(projects: readonly Pick<SddProjectEntry, "project">[] | undefined, preferred: string | null): string | null {
  if (!projects || projects.length === 0) return null;
  if (preferred && projects.some((p) => p.project === preferred)) return preferred;
  return projects[0].project;
}

/** 巢狀內容的欄位值轉成可顯示的字串：字串與數字照原值、布林轉字、其餘（缺值、null、物件）顯示「—」。 */
export function sddText(value: unknown): string {
  if (typeof value === "string") return value === "" ? "—" : value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "—";
}

/** FSM 檔裡的時間（ISO-8601 字串，原樣）轉本機時區的「2026-10-16 09:02:03」；解析不了就顯示原字串、缺值顯示「—」。 */
export function sddTime(value: unknown): string {
  if (typeof value !== "string" || value === "") return "—";
  const date = formatDate(value);
  return date === "—" ? value : `${date} ${formatClock(value)}`;
}

/** 「Sprint N」；缺值（null）顯示「—」。 */
export function sddSprint(sprint: number | null | undefined): string {
  return typeof sprint === "number" ? `Sprint ${sprint}` : "—";
}

/**
 * 待人工（契約 M-20）：count＝0 顯示「無」、1 顯示「等待人工確認」（並可展開看 items[0].entered_at）。
 * 現行 FSM 的 human_pending_tracking 是單一映射，count 實務上只會是 0 或 1；若日後 schema 改成多筆，count 大於 1 時註明件數。
 * enteredAt＝每個項目的 entered_at（轉本機時區；缺值「—」），最多列 5 個（API 的 items 本來就只回尾 5 筆）。
 */
export function sddHumanPending(hp: SddHumanPending | undefined): { count: number; label: string; enteredAt: string[] } {
  const count = hp?.count ?? 0;
  const label = count <= 0 ? "無" : count === 1 ? "等待人工確認" : `等待人工確認（${count} 項）`;
  return { count, label, enteredAt: count > 0 ? (hp?.items ?? []).slice(0, 5).map((item) => sddTime(item?.entered_at)) : [] };
}

export type SddDecisionRow = { ts: string; from: string; to: string; reason: string };

/**
 * 最近決策（契約 M-20）：`decisionTrace` 是 API 給的尾 5 筆（舊→新），卡片倒序顯示（新→舊），每筆 `from → to` 與 `reason`；
 * 這裡再保險取最後 `limit` 筆（API 已截，缺席或不是陣列時當作空）。
 */
export function sddRecentDecisions(trace: SddFsmState["decisionTrace"] | undefined, limit = 5): SddDecisionRow[] {
  if (!Array.isArray(trace)) return [];
  return trace
    .slice(-limit)
    .reverse()
    .map((d) => ({ ts: sddTime(d?.ts), from: sddText(d?.from), to: sddText(d?.to), reason: sddText(d?.reason) }));
}

// ══ v1.5（整合輪 115）：專案綁定顯示、階段進度、ESCALATION 與恢復指令、凍結摘要 ═══════════════════════════════

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
/** null、缺席、空白字串＝「沒有值」（FSM 檔的 `resolved_at` 清成 null 或空字串都算空）。 */
const isBlank = (v: unknown): boolean => v === null || v === undefined || (typeof v === "string" && v.trim() === "");

/** 專案的 SDD 綁定三欄（`GET /projects/{id}` 的 sddProject／sddSpecDir／sddSpecFile；null 與缺席等價，契約 §1.10.5）。 */
export type SddBinding = { sddProject?: string | null; sddSpecDir?: string | null; sddSpecFile?: string | null };

/** 專案是否「已使用 SDD」：三欄任一有值（§4.7.1：從未使用的專案區塊預設收合、標題帶「（尚未使用）」；沒有「未綁定」狀態）。 */
export function sddUsed(binding: SddBinding | null | undefined): boolean {
  return !isBlank(binding?.sddProject) || !isBlank(binding?.sddSpecDir) || !isBlank(binding?.sddSpecFile);
}

/** 「SDD 專案」列（§4.7.1）：有值顯示值本身；缺值（NULL＝用預設）顯示「（預設：<專案名>）」而不是「—」。 */
export function sddProjectDisplay(sddProject: string | null | undefined, projectName: string): { text: string; isDefault: boolean } {
  return isBlank(sddProject) ? { text: `（預設：${projectName}）`, isDefault: true } : { text: String(sddProject), isDefault: false };
}

/**
 * 「標準鍵」列（§4.7.1）：`fsm.fsmProject`（狀態檔名裡淨化後的鍵）；與 `fsm.project`（檔內原名）不同時兩者並列、原名加註「檔內原名」。
 * 🔴 不能拿 `project` 當鍵（ADR-XPLAT-016 §7.2）：fsmProject 缺值就顯示「—」，不退回 project。
 */
export function sddKeyDisplay(fsm: Pick<SddFsmState, "project" | "fsmProject"> | null | undefined): { key: string; originalName: string | null } {
  const key = sddText(fsm?.fsmProject);
  const original = fsm?.project;
  const differs = key !== SDD_DASH && typeof original === "string" && original.trim() !== "" && original !== fsm?.fsmProject;
  return { key, originalName: differs ? original : null };
}

/**
 * 「凍結狀態」列（§4.7.1）：空陣列＝「尚未凍結」；≥ 1 筆＝「已凍結：<最後一筆的 stage>（<frozen_at 轉本機時區>）」，單筆內缺值各自「—」；
 * 缺席（不是陣列）＝「—」。不解讀 `spec_doc_digests`、`approved_by`（原樣留在 API）。
 */
export function sddFrozenSummary(stages: SddFsmState["frozenStages"] | null | undefined): string {
  if (!Array.isArray(stages)) return SDD_DASH;
  if (stages.length === 0) return "尚未凍結";
  const last: unknown = stages[stages.length - 1];
  const entry = isRecord(last) ? last : {};
  return `已凍結：${sddText(entry.stage)}（${sddTime(entry.frozen_at)}）`;
}

// ── 階段進度（§3.1.5、§4.7.3）────────────────────────────────────────────

/** 進度條的八個主路徑步驟（`phase.order` 1～8；標籤＝§4.7.3 的階段字典）。 */
export const SDD_PHASE_STEPS = [
  { order: 1, name: "INTAKE", label: "立案" },
  { order: 2, name: "SPECIFICATION", label: "規格撰寫" },
  { order: 3, name: "HUMAN_GATE", label: "人工確認" },
  { order: 4, name: "FROZEN", label: "規格凍結" },
  { order: 5, name: "IMPLEMENTATION", label: "實作" },
  { order: 6, name: "REVIEW", label: "審查" },
  { order: 7, name: "VERIFICATION", label: "追溯驗證" },
  { order: 8, name: "RELEASE", label: "發布" },
] as const;

/** 階段字典（§4.7.3）：主路徑八個加非主路徑四個（order 一律 0）；字典沒有的新值原樣顯示（見 sddPhaseLabel）。 */
export const SDD_PHASE_LABEL: Readonly<Record<string, string>> = {
  ...Object.fromEntries(SDD_PHASE_STEPS.map((s) => [s.name, s.label])),
  BLOCKED: "阻塞（需人工）",
  TRANSIENT: "過渡中",
  OBSERVATION: "觀測中",
  UNKNOWN: "未知",
};

/** `phase.name` → 中文標籤：字典沒有的新值（日後 Bridge 加階段）顯示原字串、不崩潰；缺值「—」。 */
export function sddPhaseLabel(name: string | null | undefined): string {
  if (typeof name !== "string" || name.trim() === "") return SDD_DASH;
  return SDD_PHASE_LABEL[name] ?? name;
}

export type SddStepState = "done" | "current" | "upcoming";
export type SddPhaseStep = { order: number; name: string; label: string; state: SddStepState };

/**
 * 階段進度的顯示模型（§4.7.3）：
 *  - `phase.order` 為 1～8：該步驟「目前」、之前「已過」、之後「未到」；
 *  - `observation=true`：另有「觀測中」標籤（「目前」步驟改虛線外框＝回歸階段）；`currentState` 為 AUTOCLAUDE_DELEGATED 時另有「委派 AutoClaude 執行中」；
 *  - `blocking=true`：八個步驟全部「未到」（灰階），畫面另有紅色橫幅與 ESCALATION 區塊；
 *  - `order` 為 0（OBSERVATION／TRANSIENT／UNKNOWN）或 `phase` 缺席：不畫步驟（steps 為空），只有 currentState 與標籤（缺席標籤「—」）。
 * `present`＝phase 物件存在；欄位格式不對（order 不是有限數字等）一律退成 0／false，不崩潰。
 */
export type SddPhaseView = {
  present: boolean;
  name: string | null;
  label: string;
  order: number;
  blocking: boolean;
  observation: boolean;
  delegated: boolean;
  steps: SddPhaseStep[];
};

export function sddPhaseView(fsm: Pick<SddFsmState, "currentState" | "phase"> | null | undefined): SddPhaseView {
  const phase: Partial<SddFsmPhase> | null = isRecord(fsm?.phase) ? (fsm?.phase as Partial<SddFsmPhase>) : null;
  const name = typeof phase?.name === "string" && phase.name.trim() !== "" ? phase.name : null;
  const order = typeof phase?.order === "number" && Number.isFinite(phase.order) ? Math.trunc(phase.order) : 0;
  const blocking = phase?.blocking === true;
  const observation = phase?.observation === true;
  const delegated = fsm?.currentState === "AUTOCLAUDE_DELEGATED";
  const onMainPath = order >= 1 && order <= SDD_PHASE_STEPS.length;
  const steps: SddPhaseStep[] =
    blocking || onMainPath
      ? SDD_PHASE_STEPS.map((s) => ({
          ...s,
          state: blocking ? "upcoming" : s.order < order ? "done" : s.order === order ? "current" : "upcoming",
        }))
      : [];
  return { present: phase !== null, name, label: sddPhaseLabel(name), order, blocking, observation, delegated, steps };
}

// ── ESCALATION（§4.7.3；ADR-XPLAT-016 §5.3）────────────────────────────────

/** 阻塞態裡「要人工恢復」的兩個 FSM 狀態：ESCALATION 與 ESCALATION_FINAL（結構性或自動恢復失敗）。 */
export const SDD_ESCALATION_STATES: readonly string[] = ["ESCALATION", "ESCALATION_FINAL"];

export function isSddEscalationState(state: unknown): boolean {
  return typeof state === "string" && SDD_ESCALATION_STATES.includes(state);
}

/** 顯示 ESCALATION 區塊與紅色橫幅的條件：`phase.blocking=true`，或 `currentState` 為 ESCALATION／ESCALATION_FINAL（§4.7.3）。 */
export function sddShowsEscalation(fsm: Pick<SddFsmState, "currentState" | "phase"> | null | undefined): boolean {
  return isSddEscalationState(fsm?.currentState) || sddPhaseView(fsm).blocking;
}

function lastEscalationEntry(history: SddFsmState["escalationHistory"] | null | undefined): Record<string, unknown> | null {
  if (!Array.isArray(history) || history.length === 0) return null;
  const last: unknown = history[history.length - 1];
  return isRecord(last) ? last : {};
}

/**
 * 「有沒有未解的升級」（§4.7.3、ADR-XPLAT-016 §5.3）：🔴 判斷式只能是「`currentState` 屬 ESCALATION／ESCALATION_FINAL，
 * 且 `escalationHistory` 末筆的 `resolved_at` 為空」（沒有任何歷史而狀態已是升級態，也算未解）。
 * 絕不能只看 `escalationProvenance` 在不在——人工恢復後它**不會被清除**，在 IMPLEMENTATION 上會顯示過期的失敗。
 */
export function sddHasUnresolvedEscalation(fsm: Pick<SddFsmState, "currentState" | "escalationHistory"> | null | undefined): boolean {
  if (!isSddEscalationState(fsm?.currentState)) return false;
  const last = lastEscalationEntry(fsm?.escalationHistory);
  return last === null || isBlank(last.resolved_at);
}

export type SddEscalationView = {
  /** `escalationHistory` 沒有任何項目（阻塞態卻沒有升級紀錄：區塊內寫「（沒有升級紀錄）」，橫幅照顯示） */
  noRecord: boolean;
  unresolved: boolean;
  triggeredAt: string;
  reason: string;
  /** 「ESCALATION・<triggered_at 本機時區>・<trigger_reason>」；沒有紀錄時為「（沒有升級紀錄）」 */
  summary: string;
  /** 「已解決：<resolved_at>／<resolution>」；末筆沒有 resolved_at 為 null */
  resolved: string | null;
  /** 「來源：<source>」（`source=autoclaude_delegated_failed` 另註明「AutoClaude 委派失敗（引擎升級）」）；`escalationProvenance` 缺席為 null（不寫「—」） */
  source: string | null;
};

const PROVENANCE_NOTE: Readonly<Record<string, string>> = { autoclaude_delegated_failed: "AutoClaude 委派失敗（引擎升級）" };

export function sddEscalationView(fsm: Pick<SddFsmState, "currentState" | "escalationHistory" | "escalationProvenance"> | null | undefined): SddEscalationView {
  const last = lastEscalationEntry(fsm?.escalationHistory);
  const noRecord = last === null;
  const triggeredAt = sddTime(last?.triggered_at);
  const reason = sddText(last?.trigger_reason);
  const resolved = last !== null && !isBlank(last.resolved_at) ? `已解決：${sddTime(last.resolved_at)}／${sddText(last.resolution)}` : null;
  const provenance = isRecord(fsm?.escalationProvenance) ? fsm.escalationProvenance : null;
  const sourceRaw = provenance ? provenance.source : undefined;
  const note = typeof sourceRaw === "string" ? PROVENANCE_NOTE[sourceRaw] : undefined;
  return {
    noRecord,
    unresolved: sddHasUnresolvedEscalation(fsm),
    triggeredAt,
    reason,
    summary: noRecord ? "（沒有升級紀錄）" : `ESCALATION・${triggeredAt}・${reason}`,
    resolved,
    source: provenance ? `來源：${sddText(sourceRaw)}${note ? `・${note}` : ""}` : null,
  };
}

/**
 * ESCALATION 的恢復指令（§4.7.3）：`fsm.recovery` 有值（只在 ESCALATION／ESCALATION_FINAL 時由 Bridge 回）才顯示；
 * 🔴 缺席時只顯示橫幅的文字說明，**不得由前端自行組指令**（目標與路徑由 Bridge 決定；`<SDD 版本目錄>` 與 `<python>` 只有 Bridge 知道）。
 * 指令原樣顯示（含 `<人工原因>` 佔位，由使用者自行替換；Console 不替換、不提供執行鈕）。兩段都沒有字串視同沒有。
 */
export type SddRecoveryCommand = { shell: "powershell" | "posix"; label: string; command: string };
export type SddRecoveryView = { target: string; commands: SddRecoveryCommand[] };

export function sddRecoveryView(recovery: SddRecovery | null | undefined): SddRecoveryView | null {
  if (!isRecord(recovery)) return null;
  const commands: SddRecoveryCommand[] = [];
  if (typeof recovery.powershell === "string" && recovery.powershell !== "") commands.push({ shell: "powershell", label: "PowerShell", command: recovery.powershell });
  if (typeof recovery.posix === "string" && recovery.posix !== "") commands.push({ shell: "posix", label: "POSIX（bash／zsh）", command: recovery.posix });
  if (commands.length === 0) return null;
  return { target: sddText(recovery.target), commands };
}
