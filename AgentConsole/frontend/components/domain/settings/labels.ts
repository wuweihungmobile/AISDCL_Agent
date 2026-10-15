/**
 * 系統參數頁的前端字典（契約 §4.4 S-01／S-02、§4.6 G-S1）：
 *  - 分類 tab 的中文標籤與圖示；
 *  - 50 個參數鍵的中文名稱（契約只給 description，label 由前端字典提供；鍵名即索引，見附錄 C）。
 * 說明文字（description）與影響提示（impactNote）一律用後端回傳的，不在這裡重複。
 */
import { Activity, Bot, ListChecks, Plug, Ruler, Zap, type LucideIcon } from "lucide-react";

import type { ConfigCategory } from "@/lib/api/types";

export const CATEGORY_META: Record<ConfigCategory, { label: string; icon: LucideIcon }> = {
  model: { label: "模型", icon: Bot },
  agent: { label: "Agent", icon: ListChecks },
  execution: { label: "執行", icon: Zap },
  monitor: { label: "監控", icon: Activity },
  autoclaude: { label: "AutoClaude", icon: Plug },
  sdd: { label: "SDD", icon: Ruler },
};

/** `category.key` → 中文名稱 */
export const SETTING_LABELS: Record<string, string> = {
  // model（10）
  "model.provider": "模型提供者",
  "model.apiUrl": "API URL",
  "model.apiKey": "API Key",
  "model.name": "模型名稱",
  "model.maxTokensPerRequest": "最大 Token／請求",
  "model.temperature": "溫度（temperature）",
  "model.topP": "Top-P",
  "model.timeout": "請求逾時（秒）",
  "model.rateLimitPerMinute": "每分鐘請求上限",
  "model.enableKernelBrain": "啟用 Kernel Brain",
  // agent（9）
  "agent.defaultAutonomyLevel": "預設自治等級",
  "agent.maxConcurrentTasks": "最大並行任務數",
  "agent.taskTimeout": "任務逾時（秒）",
  "agent.maxRetries": "預設最大重試次數",
  "agent.retryBackoffMs": "重試退避（毫秒）",
  "agent.retryBackoffMultiplier": "重試退避倍率",
  "agent.checkpointInterval": "斷點間隔（步）",
  "agent.enableAutoMutation": "啟用自動變異",
  "agent.enableSelfEvolution": "啟用自我演化",
  // execution（10）
  "execution.globalTokenBudget": "全域 Token 預算",
  "execution.tokenBudgetWarningThreshold": "Token 預算警示門檻",
  "execution.maxParallelGoals": "最大並行目標數",
  "execution.dagSchedulerStrategy": "DAG 排程策略",
  "execution.enableRollback": "啟用回滾",
  "execution.logRetentionDays": "日誌保留天數",
  "execution.compactThresholdPct": "壓縮門檻（%）",
  "execution.haltThresholdPct": "停機門檻（%）",
  "execution.autoResume": "額度耗盡後自動續跑",
  "execution.maxAutoResumes": "最大自動續跑次數",
  // monitor（6）
  "monitor.refreshIntervalMs": "重新整理間隔（毫秒）",
  "monitor.alertConsecutiveFailures": "連續失敗告警門檻",
  "monitor.alertAgentTimeoutSec": "Agent 無回應告警（秒）",
  "monitor.alertTaskDurationMultiplier": "執行過長告警倍率",
  "monitor.enableEmailNotification": "啟用郵件通知",
  "monitor.notificationEmail": "通知信箱",
  // autoclaude（11）
  "autoclaude.engineUrl": "引擎位址（Engine Bridge）",
  "autoclaude.healthCheckPath": "健康檢查路徑",
  "autoclaude.eventBusType": "事件匯流排類型",
  "autoclaude.dalBackend": "DAL 後端",
  "autoclaude.playbookPath": "Playbook 路徑",
  "autoclaude.claudeCommand": "Claude 命令",
  "autoclaude.claudeExtraArgs": "Claude 額外參數",
  "autoclaude.claudeContinueFlag": "Claude 續跑旗標",
  "autoclaude.claudeEncoding": "Claude 輸出編碼",
  "autoclaude.dbDsn": "資料庫連線字串（DSN）",
  "autoclaude.dualReadResolution": "雙讀衝突策略",
  // sdd（4）
  "sdd.engineUrl": "SDD 引擎位址",
  "sdd.specFormat": "規格格式",
  "sdd.workflowEngine": "工作流引擎",
  "sdd.validationLevel": "驗證等級",
};

/** 字典沒有的鍵（後端日後新增）退回鍵名，不崩潰。 */
export function settingLabel(category: string, key: string): string {
  return SETTING_LABELS[`${category}.${key}`] ?? key;
}

/** 不該顯示成「中文名稱」的等寬值：URL、路徑、命令、DSN、信箱等技術字串用等寬字體。 */
const MONO_KEYS = new Set([
  "model.apiUrl",
  "model.name",
  "autoclaude.engineUrl",
  "autoclaude.healthCheckPath",
  "autoclaude.playbookPath",
  "autoclaude.claudeCommand",
  "autoclaude.claudeExtraArgs",
  "autoclaude.claudeContinueFlag",
  "autoclaude.claudeEncoding",
  "autoclaude.dbDsn",
  "sdd.engineUrl",
]);
export const isMonoSetting = (category: string, key: string): boolean => MONO_KEYS.has(`${category}.${key}`);

/** 表單提示（附錄 C 與契約 §4.4 S-02 指定要在畫面上寫明的限制）。 */
export const SETTING_HINTS: Record<string, string> = {
  "model.apiUrl": "完整的 chat-completions 端點 URL（後端不會替它補路徑）",
  "monitor.refreshIntervalMs": "最小 10000（同一使用者所有頁面共用每分鐘 100 次請求額度，輪詢不得更密）",
};
