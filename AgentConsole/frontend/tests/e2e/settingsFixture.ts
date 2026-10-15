/**
 * 系統參數的 route mock 夾具：依契約附錄 C 的 50 個鍵（型別、預設、範圍、選項、effect、影響提示）組出
 * ConfigResponse，並提供一個記憶體內的假後端（寫入、重置、跨鍵校驗、歷史、測試連線、匯出入）。
 * 各鍵的 description 為測試用的中文短句（真值由後端 V5 種子提供）。
 */
import { fail, paged, type MockCall, type MockHandler } from "./mockApi";

type Cat = "model" | "agent" | "execution" | "monitor" | "autoclaude" | "sdd";
export const CATEGORIES: Cat[] = ["model", "agent", "execution", "monitor", "autoclaude", "sdd"];

export type Cfg = {
  id: string;
  category: Cat;
  key: string;
  value: string;
  valueType: string;
  defaultValue: string;
  description: string;
  isEncrypted: boolean;
  hasValue: boolean;
  validationRule?: string;
  options?: string[];
  min?: number;
  max?: number;
  impactNote?: string;
  effect: "ENGINE" | "CONSOLE" | "STORED_ONLY" | "UNVERIFIED";
  updatedAt: string;
  updatedBy: string;
};

export const MASK = "•".repeat(8);
const E = "ENGINE",
  C = "CONSOLE",
  S = "STORED_ONLY",
  U = "UNVERIFIED";

type Row = [key: string, type: string, def: string, effect: Cfg["effect"], extra?: Partial<Pick<Cfg, "options" | "min" | "max" | "impactNote" | "validationRule" | "value">>];

/** 附錄 C 逐鍵（C.1～C.6） */
const CATALOG: Record<Cat, Row[]> = {
  model: [
    ["provider", "ENUM", "ANTHROPIC", S, { options: ["ANTHROPIC", "OPENAI", "LOCAL", "CUSTOM"], impactNote: "僅為 Console 抽象層欄位；引擎是 MiniMax＋Claude CLI 雙腦，不會依此切換" }],
    [
      "apiUrl",
      "STRING",
      "https://api.minimax.io/v1/text/chatcompletion_v2",
      E,
      { validationRule: "^https?://[^\\s/?#][^\\s]*$", impactNote: "須填完整的 chat-completions 端點 URL（後端不補路徑）；原樣當引擎 minimax.base_url，也用於匯入解析與測試連線；新批次起生效" },
    ],
    ["apiKey", "ENCRYPTED", "", E, { impactNote: "加密儲存；新批次起使用新金鑰；留空＝不再帶 MiniMax 設定（引擎不建 Brain，AI 演化提案停用）" }],
    ["name", "STRING", "MiniMax-M2.7", E, { validationRule: "^[A-Za-z0-9._:/\\-]{1,100}$", impactNote: "新批次起生效；也用於匯入解析" }],
    ["maxTokensPerRequest", "INTEGER", "8192", C, { min: 1, max: 200000, impactNote: "只影響匯入解析（路徑 B）的 max_tokens；引擎無對應欄位" }],
    ["temperature", "FLOAT", "0.3", C, { min: 0, max: 2, impactNote: "只影響匯入解析（路徑 B）" }],
    ["topP", "FLOAT", "0.9", C, { min: 0, max: 1, impactNote: "只影響匯入解析（路徑 B）" }],
    ["timeout", "INTEGER", "120", E, { min: 1, max: 600, impactNote: "引擎 minimax.timeout_seconds 與匯入解析逾時；測試連線上限 10 秒；經 nginx 部署時建議 ≤ 150" }],
    ["rateLimitPerMinute", "INTEGER", "60", S, { min: 1, max: 10000, impactNote: "目前不影響任何呼叫" }],
    ["enableKernelBrain", "BOOLEAN", "false", E, { impactNote: "開啟後引擎的 Brain 可改寫失敗步驟並可能觸發升級；新批次起生效" }],
  ],
  agent: [
    ["defaultAutonomyLevel", "INTEGER", "3", C, { min: 1, max: 10, impactNote: "只改之後匯入與執行表單的預設值，不改動既有專案" }],
    ["maxConcurrentTasks", "INTEGER", "3", S, { min: 1, max: 32, impactNote: "引擎序列執行，目前不生效（Architecture L-1）" }],
    ["taskTimeout", "INTEGER", "600", E, { min: 10, max: 86400, impactNote: "新批次的單步逾時（秒）；同時是「任務執行過長」告警門檻的基準" }],
    ["maxRetries", "INTEGER", "3", E, { min: 0, max: 20, impactNote: "新批次的預設最大重試次數（每個任務自己的 maxRetries 優先）" }],
    ["retryBackoffMs", "INTEGER", "5000", S, { min: 0, max: 3600000, impactNote: "引擎無對應欄位" }],
    ["retryBackoffMultiplier", "FLOAT", "2.0", S, { min: 1, max: 10, impactNote: "引擎無對應欄位" }],
    ["checkpointInterval", "INTEGER", "5", S, { min: 1, max: 1000, impactNote: "Bridge 於每個步驟邊界自行記錄歷史快照，此值不生效" }],
    ["enableAutoMutation", "BOOLEAN", "false", U, { impactNote: "引擎沒有對應的設定鍵，Console 不送任何引擎設定" }],
    ["enableSelfEvolution", "BOOLEAN", "false", U, { impactNote: "引擎的 AI 演化提案只由 MINIMAX_API_KEY 的有無決定，與本鍵無關" }],
  ],
  execution: [
    ["globalTokenBudget", "LONG", "1000000", C, { min: 1, max: 1000000000000, impactNote: "新批次的預設 Token 預算；不改動既有批次" }],
    ["tokenBudgetWarningThreshold", "FLOAT", "0.8", C, { min: 0.01, max: 0.99, impactNote: "即時生效於進行中的批次（告警每次評估時讀取）" }],
    ["maxParallelGoals", "INTEGER", "2", S, { min: 1, max: 16, impactNote: "引擎序列執行，目前不生效" }],
    ["dagSchedulerStrategy", "ENUM", "TOPOLOGICAL", C, { options: ["TOPOLOGICAL", "PRIORITY", "SHORTEST_FIRST"], impactNote: "影響新批次同層目標的排序" }],
    ["enableRollback", "BOOLEAN", "true", S, { impactNote: "引擎無對應欄位" }],
    ["logRetentionDays", "INTEGER", "90", C, { min: 1, max: 3650, impactNote: "日誌與 Bridge 工作區的保留天數（清理排程依此）" }],
    ["compactThresholdPct", "INTEGER", "80", E, { min: 1, max: 99, impactNote: "Token Guard：context 達此百分比觸發 /compact；新批次起生效；不得經 Console 提高上限以繞過安全收斂" }],
    ["haltThresholdPct", "INTEGER", "90", E, { min: 2, max: 100, impactNote: "Token Guard：context 達此百分比儲存 checkpoint 並停機；新批次起生效" }],
    ["autoResume", "BOOLEAN", "true", E, { impactNote: "halt 後引擎是否等待並自動續跑（會讓 run 長時間維持 RUNNING）；新批次起生效" }],
    ["maxAutoResumes", "INTEGER", "10", E, { min: 1, max: 100, impactNote: "單次 playbook 最多自動恢復次數；新批次起生效" }],
  ],
  monitor: [
    ["refreshIntervalMs", "INTEGER", "10000", C, { min: 10000, max: 60000, impactNote: "前端輪詢間隔（通知摘要、監控儀表板）；下限 10 秒：同一使用者的所有頁面共用每分鐘 100 次的限流額度" }],
    ["alertConsecutiveFailures", "INTEGER", "3", C, { min: 2, max: 20, impactNote: "「連續任務失敗」告警門檻；即時生效" }],
    ["alertAgentTimeoutSec", "INTEGER", "300", C, { min: 30, max: 86400, impactNote: "「Agent 無回應」告警門檻（秒）；即時生效" }],
    ["alertTaskDurationMultiplier", "FLOAT", "2.0", C, { min: 1, max: 20, impactNote: "「執行時間過長」＝agent.taskTimeout × 此倍數；即時生效" }],
    ["enableEmailNotification", "BOOLEAN", "false", S, { impactNote: "目前沒有郵件發送功能，只儲存" }],
    ["notificationEmail", "STRING", "", S, { validationRule: "^$|^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", impactNote: "同上" }],
  ],
  autoclaude: [
    ["engineUrl", "STRING", "http://engine-bridge:8081", C, { impactNote: "所有 Bridge 呼叫改走新位址；填錯會讓執行與監控失效" }],
    ["healthCheckPath", "STRING", "/health", C, { impactNote: "Bridge 健康探測路徑（Agent 可用率、頂列連線燈）" }],
    ["eventBusType", "ENUM", "INTERNAL", S, { options: ["INTERNAL", "KAFKA", "RABBITMQ"], impactNote: "引擎只有 INTERNAL" }],
    ["dalBackend", "ENUM", "FILE", S, { options: ["FILE", "IN_MEMORY", "POSTGRESQL"], impactNote: "Bridge 固定用檔案型 checkpoint（yaml_only），此值不生效" }],
    ["playbookPath", "STRING", "./playbooks", S, { impactNote: "Bridge 自行管理 playbook 檔，不生效" }],
    ["claudeCommand", "STRING", "claude", E, { validationRule: "^[A-Za-z0-9_.\\-/\\\\:]{1,200}$", impactNote: "新批次起生效；填錯會讓每個步驟在第一秒失敗" }],
    ["claudeExtraArgs", "STRING", "", E, { impactNote: "新批次起生效" }],
    ["claudeContinueFlag", "STRING", "--continue", E, { impactNote: "新批次起生效" }],
    ["claudeEncoding", "STRING", "utf-8", E, { impactNote: "新批次起生效" }],
    ["dbDsn", "ENCRYPTED", "", S, { impactNote: "Bridge 固定 yaml_only，不生效" }],
    ["dualReadResolution", "ENUM", "yaml_wins", S, { options: ["yaml_wins", "db_wins", "fail_loud"], impactNote: "同上" }],
  ],
  sdd: [
    ["engineUrl", "STRING", "http://engine-bridge:8081", C, { impactNote: "匯入路徑 A 的 /sdd/compile 位址" }],
    ["specFormat", "ENUM", "YAML", U, { options: ["YAML", "JSON", "TOML"], impactNote: "與 /sdd/compile 行為的對映尚未驗證" }],
    ["workflowEngine", "ENUM", "DYNAMIC", U, { options: ["STATIC", "DYNAMIC", "ADAPTIVE"], impactNote: "同上" }],
    ["validationLevel", "ENUM", "STRICT", U, { options: ["LAX", "NORMAL", "STRICT"], impactNote: "同上" }],
  ],
};

/** 契約 §1.5：整個分類的 50 個鍵（model.apiKey 預設已設定過一個金鑰；autoclaude.dbDsn 尚未設定；少數鍵改成非預設值方便驗「重置」）。 */
export function buildStore(): Record<Cat, Cfg[]> {
  const out = {} as Record<Cat, Cfg[]>;
  let n = 0;
  for (const cat of CATEGORIES) {
    out[cat] = CATALOG[cat].map(([key, type, def, effect, extra]) => {
      n += 1;
      const encrypted = type === "ENCRYPTED";
      const hasValue = encrypted ? cat === "model" : def !== "";
      return {
        id: `5c2d9f10-7b3a-4e61-8d52-${String(n).padStart(12, "0")}`,
        category: cat,
        key,
        value: encrypted ? MASK : (extra?.value ?? def),
        valueType: type,
        defaultValue: def,
        description: `${cat}.${key} 的參數說明`,
        isEncrypted: encrypted,
        hasValue,
        effect,
        updatedAt: "2026-10-15T08:30:12Z",
        updatedBy: "admin",
        ...(extra ? { options: extra.options, min: extra.min, max: extra.max, impactNote: extra.impactNote, validationRule: extra.validationRule } : {}),
      } satisfies Cfg;
    });
  }
  // 非預設值（讓「重置」按鈕可用、測試重置有意義）
  const set = (cat: Cat, key: string, value: string) => {
    const c = out[cat].find((x) => x.key === key)!;
    c.value = value;
  };
  set("execution", "globalTokenBudget", "2000000");
  set("monitor", "refreshIntervalMs", "15000");
  set("model", "temperature", "0.5");
  return out;
}

export type HistoryRow = { id: string; configId: string; category: string; key: string; oldValue?: string; newValue: string; changedAt: string; changedBy?: string };

/**
 * 假後端：只在 ADMIN 才允許寫入；加密參數須 confirm=true；token_guard 跨鍵校驗；每次寫入追加歷史；
 * 可用 hooks 在單一測試中強制某端點的回應（例如強制 400）。
 */
export function createSettingsServer(role: "ADMIN" | "OPERATOR" | "VIEWER" = "ADMIN") {
  const s = {
    store: buildStore(),
    history: [
      { id: "h1", configId: "c1", category: "model", key: "temperature", oldValue: "0.7", newValue: "0.5", changedAt: "2026-10-14T10:00:00", changedBy: "admin" },
      { id: "h2", configId: "c2", category: "model", key: "apiKey", oldValue: MASK, newValue: MASK, changedAt: "2026-10-13T09:15:00", changedBy: "admin" },
      { id: "h3", configId: "c3", category: "execution", key: "globalTokenBudget", oldValue: "1000000", newValue: "2000000", changedAt: "2026-10-12T18:20:00", changedBy: "admin" },
    ] as HistoryRow[],
    /** 強制回應（優先於預設行為），回 undefined 表示走預設 */
    force: [] as Array<(call: MockCall) => ReturnType<MockHandler>>,
    testConnection: { success: true, latencyMs: 230, message: "連線成功", resolvedHost: "api.minimax.io", httpStatus: 200 } as Record<string, unknown>,
    exportFileName: "aisdlc-settings-20261015.json",
  };
  const find = (cat: string, key: string) => s.store[cat as Cat]?.find((c) => c.key === key);
  const record = (c: Cfg, oldValue: string, newValue: string) =>
    s.history.unshift({ id: `h${s.history.length + 1}`, configId: c.id, category: c.category, key: c.key, oldValue, newValue, changedAt: "2026-10-15T16:00:00", changedBy: role.toLowerCase() });
  const mask = (c: Cfg) => (c.isEncrypted ? MASK : c.value);

  const handler: MockHandler = async (call) => {
    for (const f of s.force) {
      const r = await f(call);
      if (r) return r;
    }
    const { method, path } = call;
    let m: RegExpExecArray | null;

    if (method === "GET" && path === "/api/v1/settings") return { data: s.store };
    if (method === "GET" && path === "/api/v1/settings/history") {
      const cat = call.query.get("category");
      const rows = s.history.filter((h) => !cat || h.category === cat);
      return { data: paged(rows, 20) };
    }
    if (method === "GET" && (m = /^\/api\/v1\/settings\/(\w+)$/.exec(path))) {
      const list = s.store[m[1] as Cat];
      if (!list) return fail(404, { message: `設定分類不存在：${m[1]}` });
      if (call.query.get("reveal") === "true") {
        if (role !== "ADMIN") return fail(403, { message: "僅 ADMIN 可揭露敏感參數", reason: "僅 ADMIN 可揭露敏感參數" });
        return { data: list.map((c) => (c.isEncrypted && c.hasValue ? { ...c, value: "sk-plain-secret-0042" } : c)) };
      }
      return { data: list };
    }

    if (method !== "GET" && role !== "ADMIN") return fail(403, { message: "權限不足", reason: "ACCESS_DENIED" });

    if (method === "PUT" && path === "/api/v1/settings/execution/token-guard") {
      const b = call.body as { compactThresholdPct: number; haltThresholdPct: number };
      if (b.haltThresholdPct <= b.compactThresholdPct) {
        return fail(400, {
          message: "token_guard 跨鍵校驗失敗",
          reason: "halt_threshold_pct 必須大於 compact_threshold_pct",
          errors: [{ field: "haltThresholdPct", message: "必須大於 compactThresholdPct" }],
          details: { compactThresholdPct: b.compactThresholdPct, haltThresholdPct: b.haltThresholdPct },
        });
      }
      const compact = find("execution", "compactThresholdPct")!;
      const halt = find("execution", "haltThresholdPct")!;
      record(compact, compact.value, String(b.compactThresholdPct));
      record(halt, halt.value, String(b.haltThresholdPct));
      compact.value = String(b.compactThresholdPct);
      halt.value = String(b.haltThresholdPct);
      return { data: [compact, halt] };
    }

    if (method === "PUT" && (m = /^\/api\/v1\/settings\/(\w+)\/(\w+)$/.exec(path))) {
      const c = find(m[1], m[2]);
      if (!c) return fail(404, { message: `設定鍵不存在：${m[1]}.${m[2]}` });
      const b = call.body as { value: string; confirm?: boolean };
      if (c.isEncrypted && b.confirm !== true) {
        return fail(409, { message: "敏感參數需二次確認", reason: "敏感參數更新需二次確認（confirm=true）", details: { category: m[1], key: m[2] } });
      }
      record(c, mask(c), c.isEncrypted ? MASK : b.value);
      if (c.isEncrypted) c.hasValue = b.value !== "";
      else c.value = b.value;
      return { data: { ...c, value: mask(c) } };
    }

    if (method === "POST" && path === "/api/v1/settings/test-connection") return { data: s.testConnection };

    if (method === "POST" && path === "/api/v1/settings/export") {
      const configs = CATEGORIES.flatMap((cat) => s.store[cat].map((c) => ({ category: cat, key: c.key, value: c.isEncrypted ? "<encrypted>" : c.value })));
      return {
        raw: JSON.stringify({ version: 1, exportedAt: "2026-10-15T08:45:00Z", configs }),
        headers: { "content-disposition": `attachment; filename="${s.exportFileName}"`, "content-type": "application/json" },
      };
    }

    if (method === "POST" && path === "/api/v1/settings/import") {
      return { data: { applied: 2, skipped: 47, errors: [{ category: "monitor", key: "refreshIntervalMs", reason: "參數值不符合型別或驗證規則" }] } };
    }

    if (method === "POST" && (m = /^\/api\/v1\/settings\/(\w+)\/(\w+)\/reset$/.exec(path))) {
      const c = find(m[1], m[2]);
      if (!c) return fail(404, { message: `設定鍵不存在：${m[1]}.${m[2]}` });
      if (c.isEncrypted && call.query.get("confirm") !== "true") {
        return fail(409, { message: "敏感參數重置需二次確認", reason: "敏感參數重置需二次確認（confirm=true）", details: { category: m[1], key: m[2] } });
      }
      record(c, mask(c), c.isEncrypted ? MASK : c.defaultValue);
      if (c.isEncrypted) c.hasValue = false;
      else c.value = c.defaultValue;
      return { data: { ...c, value: mask(c) } };
    }

    if (method === "POST" && (m = /^\/api\/v1\/settings\/(\w+)\/reset$/.exec(path))) {
      const list = s.store[m[1] as Cat];
      if (!list) return fail(404, { message: `設定分類不存在：${m[1]}` });
      const withSensitive = call.query.get("confirm") === "true";
      for (const c of list) {
        if (c.isEncrypted) {
          if (withSensitive) c.hasValue = false;
        } else if (c.value !== c.defaultValue) {
          record(c, c.value, c.defaultValue);
          c.value = c.defaultValue;
        }
      }
      return { data: list };
    }
    return undefined;
  };
  return { s, handler, find };
}
