/**
 * 系統參數測試夾具：依契約附錄 C 的鍵與預設值組出 ConfigResponse（只取測試用得到的代表鍵）。
 * 欄位形狀取自契約 §1.5.1 的 ConfigResponse。
 */
import type { Config, ConfigCategory } from "@/lib/api/types";

let seq = 0;

export function cfg(category: ConfigCategory, key: string, over: Partial<Config> = {}): Config {
  seq += 1;
  const base: Config = {
    id: `00000000-0000-4000-8000-${String(seq).padStart(12, "0")}`,
    category,
    key,
    value: "",
    valueType: "STRING",
    defaultValue: "",
    description: `${category}.${key} 的說明`,
    isEncrypted: false,
    hasValue: true,
    effect: "ENGINE",
    updatedAt: "2026-10-15T08:30:12Z",
    updatedBy: "admin",
  };
  const merged = { ...base, ...over };
  return merged.isEncrypted ? { ...merged, hasValue: over.hasValue ?? merged.value !== "" } : { ...merged, hasValue: merged.value !== "" };
}

export const MASKED = "•".repeat(8);

/** 附錄 C 的代表鍵（型別、預設、範圍、選項與契約一致） */
export const FIXTURE = {
  provider: () =>
    cfg("model", "provider", { value: "ANTHROPIC", defaultValue: "ANTHROPIC", valueType: "ENUM", options: ["ANTHROPIC", "OPENAI", "LOCAL", "CUSTOM"], effect: "STORED_ONLY", impactNote: "僅為 Console 抽象層欄位；引擎是 MiniMax＋Claude CLI 雙腦，不會依此切換" }),
  apiUrl: () =>
    cfg("model", "apiUrl", { value: "https://api.minimax.io/v1/text/chatcompletion_v2", defaultValue: "https://api.minimax.io/v1/text/chatcompletion_v2", validationRule: "^https?://[^\\s/?#][^\\s]*$", impactNote: "須填完整的 chat-completions 端點 URL（後端不補路徑）" }),
  apiKey: (hasValue = true) =>
    cfg("model", "apiKey", { value: MASKED, defaultValue: "", valueType: "ENCRYPTED", isEncrypted: true, hasValue, impactNote: "加密儲存；新批次起使用新金鑰" }),
  name: () => cfg("model", "name", { value: "MiniMax-M2.7", defaultValue: "MiniMax-M2.7", validationRule: "^[A-Za-z0-9._:/\\-]{1,100}$" }),
  maxTokensPerRequest: () => cfg("model", "maxTokensPerRequest", { value: "8192", defaultValue: "8192", valueType: "INTEGER", min: 1, max: 200000, effect: "CONSOLE" }),
  temperature: () => cfg("model", "temperature", { value: "0.3", defaultValue: "0.3", valueType: "FLOAT", min: 0, max: 2, effect: "CONSOLE" }),
  enableKernelBrain: () => cfg("model", "enableKernelBrain", { value: "false", defaultValue: "false", valueType: "BOOLEAN" }),
  defaultAutonomyLevel: (value = "3") => cfg("agent", "defaultAutonomyLevel", { value, defaultValue: "3", valueType: "INTEGER", min: 1, max: 10, effect: "CONSOLE" }),
  maxConcurrentTasks: () => cfg("agent", "maxConcurrentTasks", { value: "3", defaultValue: "3", valueType: "INTEGER", min: 1, max: 32, effect: "STORED_ONLY" }),
  enableAutoMutation: () => cfg("agent", "enableAutoMutation", { value: "false", defaultValue: "false", valueType: "BOOLEAN", effect: "UNVERIFIED" }),
  globalTokenBudget: (value = "1000000") => cfg("execution", "globalTokenBudget", { value, defaultValue: "1000000", valueType: "LONG", min: 1, max: 1000000000000, effect: "CONSOLE", impactNote: "新批次的預設 Token 預算；不改動既有批次" }),
  tokenBudgetWarningThreshold: (value = "0.8") => cfg("execution", "tokenBudgetWarningThreshold", { value, defaultValue: "0.8", valueType: "FLOAT", min: 0.01, max: 0.99, effect: "CONSOLE", impactNote: "即時生效於進行中的批次（告警每次評估時讀取）" }),
  compactThresholdPct: (value = "80") => cfg("execution", "compactThresholdPct", { value, defaultValue: "80", valueType: "INTEGER", min: 1, max: 99, impactNote: "Token Guard：context 達此百分比觸發 /compact" }),
  haltThresholdPct: (value = "90") => cfg("execution", "haltThresholdPct", { value, defaultValue: "90", valueType: "INTEGER", min: 2, max: 100, impactNote: "Token Guard：context 達此百分比儲存 checkpoint 並停機" }),
  dagSchedulerStrategy: () => cfg("execution", "dagSchedulerStrategy", { value: "TOPOLOGICAL", defaultValue: "TOPOLOGICAL", valueType: "ENUM", options: ["TOPOLOGICAL", "PRIORITY", "SHORTEST_FIRST"], effect: "CONSOLE" }),
  refreshIntervalMs: (value = "10000") => cfg("monitor", "refreshIntervalMs", { value, defaultValue: "10000", valueType: "INTEGER", min: 10000, max: 60000, effect: "CONSOLE" }),
  notificationEmail: () => cfg("monitor", "notificationEmail", { value: "", defaultValue: "", validationRule: "^$|^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", effect: "STORED_ONLY" }),
  dbDsn: () => cfg("autoclaude", "dbDsn", { value: MASKED, defaultValue: "", valueType: "ENCRYPTED", isEncrypted: true, hasValue: false, effect: "STORED_ONLY" }),
  specFormat: () => cfg("sdd", "specFormat", { value: "YAML", defaultValue: "YAML", valueType: "ENUM", options: ["YAML", "JSON", "TOML"], effect: "UNVERIFIED" }),
};
