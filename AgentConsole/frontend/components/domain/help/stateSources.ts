/**
 * 狀態表的名稱來源（TCS-PageHelp-20261027 C3、R-PH-08、R-PH-10；PRD §8.2）：`STATE_SOURCES[表 id] = { title, keys, labelOf? }`。
 * 說明（lib/help/states.ts）只寫每個狀態的意思與下一步，**不持有狀態名稱**；名稱與鍵集合在載入時**現讀既有常數表**——
 * 畫面改了狀態或標籤，這裡自動跟著改，stateKeys.test.ts 的雙向鎖會在說明沒補時轉紅。
 *  - `keys`：該表的鍵（執行期由既有常數展開）；`sddFsmState` 例外：FSM 原始狀態沒有單一常數，鍵＝兩個升級狀態（取自 `SDD_ESCALATION_STATES`）＋三個程式碼字面值，
 *    鎖只有子字串弱鎖（PRD §8.2 備註 2）；
 *  - `labelOf`：鍵→畫面上的中文標籤；缺＝這張表畫面印原值，只准用 `raw` 名稱模式（`sddFsmState`、`propState`）；
 *  - `title`：這張表在對話框裡的小標題。
 * 本檔只 import 既有常數表，不新增任何名稱字面值，所以依賴方向是 lib/help（純文字）← 本檔 ← PageHelpDialog（輪 1b）。
 */
import { GATE_LABEL } from "@/components/domain/import/gateErrors";
import { SERVICE_LABEL } from "@/hooks/useServiceStatus";
import { SDD_ESCALATION_STATES, SDD_PHASE_LABEL } from "@/lib/domain/sdd";
import { OBS_STATUS_OPTIONS, PROPOSAL_STATUS_OPTIONS, PROP_STATE_KEYS } from "@/lib/domain/si";
import {
  ALERT_RULE_LABEL,
  ALERT_SEVERITY,
  BRIDGE_TRANSITION,
  GOAL_STATUS,
  IMPORT_STATUS,
  PROJECT_STATUS,
  REVIEW_DECISION_LABEL,
  REVIEW_KIND,
  RUN_STATUS,
  STEP_STATUS,
  TASK_STATUS,
} from "@/lib/domain/status";
import type { StateTableId } from "@/lib/help/types";

/** 一張狀態表的名稱來源（也是 PageHelpDialog 的 `content.sources` 值型別，D-PH-3）。 */
export type StateSource = { title: string; keys: readonly string[]; labelOf?: (key: string) => string };

/** 取自「值是 { label }」的常數表（PROJECT_STATUS 等）；有些表是 Partial，所以值可能缺。 */
function fromMeta(title: string, table: Readonly<Record<string, { label: string } | undefined>>): StateSource {
  return { title, keys: Object.keys(table), labelOf: (key) => table[key]?.label ?? key };
}

/** 取自「值就是標籤」的常數表（REVIEW_DECISION_LABEL 等）。 */
function fromLabels(title: string, table: Readonly<Record<string, string | undefined>>): StateSource {
  return { title, keys: Object.keys(table), labelOf: (key) => table[key] ?? key };
}

/** 取自篩選選項（去掉 id 為空字串的「全部」）。 */
function fromOptions(title: string, options: ReadonlyArray<{ id: string; label: string }>): StateSource {
  const real = options.filter((option) => option.id !== "");
  return { title, keys: real.map((option) => option.id), labelOf: (key) => real.find((option) => option.id === key)?.label ?? key };
}

export const STATE_SOURCES: Record<StateTableId, StateSource> = {
  projectStatus: fromMeta("專案狀態", PROJECT_STATUS),
  goalStatus: fromMeta("目標狀態", GOAL_STATUS),
  taskStatus: fromMeta("任務狀態", TASK_STATUS),
  stepStatus: fromMeta("執行步驟事件", STEP_STATUS),
  importStatus: fromMeta("匯入記錄狀態", IMPORT_STATUS),
  runStatus: fromMeta("執行批次狀態", RUN_STATUS),
  runTransition: fromMeta("批次過渡狀態", BRIDGE_TRANSITION),
  reviewKind: fromMeta("審核項種類", REVIEW_KIND),
  reviewDecision: fromLabels("審核決定", REVIEW_DECISION_LABEL),
  alertSeverity: fromMeta("告警嚴重度", ALERT_SEVERITY),
  alertRule: fromLabels("告警規則", ALERT_RULE_LABEL),
  gateName: fromLabels("匯入有界閘", GATE_LABEL),
  sddPhase: fromLabels("SDD 階段", SDD_PHASE_LABEL),
  // 沒有單一常數：兩個升級狀態現讀，其餘三個是程式碼裡的字面值（sdd.ts、SddGovernanceCard、SddFreezeDialog）；只准 raw
  sddFsmState: { title: "SDD 流程原始狀態", keys: ["HUMAN_PENDING", "SPEC_FROZEN", "AUTOCLAUDE_DELEGATED", ...SDD_ESCALATION_STATES] },
  serviceState: fromLabels("連線狀態", SERVICE_LABEL),
  obsClass: fromOptions("觀察分類", OBS_STATUS_OPTIONS),
  propClass: fromOptions("提案分類", PROPOSAL_STATUS_OPTIONS),
  // 畫面印英文原值、沒有中文標籤常數：只准 raw
  propState: { title: "提案狀態", keys: PROP_STATE_KEYS },
};
