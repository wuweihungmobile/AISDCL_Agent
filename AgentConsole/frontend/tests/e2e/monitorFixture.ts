import { TASKS, PROJECT_ID, type Engine } from "./execFixture";
import type { MockHandler, MockReply } from "./mockApi";

/**
 * 監控頁 route mock 用的「假監控後端」（契約 §1.3、§3.7、§3.8）：指標、Token／任務趨勢、告警、日誌查詢、報表匯出、監控系統參數。
 * 批次列表、批次詳情與步驟事件（事件時間軸、Agent 即時狀態、批次比較用）由同一份 execFixture 的 Engine 提供——
 * 這個類別只負責 /api/v1/monitor/** 與 /settings/monitor，並把收到的請求留下來供測試斷言「前端到底送了什麼」。
 */
export type AlertRow = {
  id: string;
  projectId: string;
  runId?: string;
  rule: "TOKEN_BUDGET_WARNING" | "TOKEN_BUDGET_EXCEEDED" | "CONSECUTIVE_FAILURES" | "ENGINE_ESCALATION";
  severity: "WARNING" | "CRITICAL";
  subject?: string;
  message: string;
  createdAt: string;
  acknowledged: boolean;
  acknowledgedBy?: string;
  acknowledgedAt?: string;
};

export type LogRow = { id: string; timestamp: string; level: "INFO" | "WARN" | "ERROR"; source: "STEP" | "RUN" | "ALERT"; message: string; runId?: string; taskId?: string; stepId?: string };

const metric = (value: number | null, previousValue?: number | null) => ({
  value,
  previousValue: previousValue ?? null,
  delta: value !== null && previousValue !== undefined && previousValue !== null ? Math.round((value - previousValue) * 100) / 100 : null,
});

export const CSV_FILENAME = "monitor-report-20261015.csv";
export const CSV_BODY = "runNumber,status,tokens\n1,COMPLETED,3720\n2,FAILED,1240\n3,RUNNING,1240\n";

/** 一批 45 筆日誌（由新到舊：index 0 最新）：每 9 筆有 1 筆 ERROR、每 3 筆有 1 筆 WARN，其餘 INFO；任務交替落在 T1／T2。 */
export function makeLogs(now = Date.now()): LogRow[] {
  return Array.from({ length: 45 }, (_, i) => {
    const level: LogRow["level"] = i % 9 === 0 ? "ERROR" : i % 3 === 0 ? "WARN" : "INFO";
    const task = TASKS[i % 2];
    return {
      id: `step:00000000-0000-4000-8000-${String(i).padStart(12, "0")}`,
      timestamp: new Date(now - i * 60_000).toISOString(),
      level,
      source: "STEP",
      message: level === "ERROR" ? `失敗：${task.name}（${task.stepId}）：測試未通過 #${i}` : level === "WARN" ? `重試：${task.name}（${task.stepId}，第 2 次） #${i}` : `完成：${task.name}（${task.stepId}） #${i}`,
      taskId: task.id,
      stepId: task.stepId,
    };
  });
}

export class MonitorWorld {
  /** 收到的 /monitor/** 與設定請求（依序） */
  readonly seen: Array<{ method: string; path: string; query: URLSearchParams; headers: Record<string, string> }> = [];
  alerts: AlertRow[];
  readonly logs: LogRow[] = makeLogs();
  /** 確認告警：true＝回 500（驗證樂觀更新的還原）；ackDelayMs＝先拖住一會兒（讓測試看得到「樂觀」那一刻） */
  ackFails = false;
  ackDelayMs = 0;
  /** 監控系統參數 monitor.refreshIntervalMs（前端輪詢間隔＝max(此值, 15 秒)） */
  refreshIntervalMs = "15000";

  constructor(private readonly engine: Engine) {
    const run = (n: number) => this.engine.runs.find((r) => r.runNumber === n)?.id;
    const t = (minAgo: number) => new Date(Date.now() - minAgo * 60_000).toISOString();
    this.alerts = [
      { id: "a1000000-0000-4000-8000-000000000001", projectId: PROJECT_ID, runId: run(3), rule: "TOKEN_BUDGET_WARNING", severity: "WARNING", subject: `run:${run(3)}`, message: "Token 使用量已達預算的 80%（1,240 / 1,500）", createdAt: t(2), acknowledged: false },
      { id: "a1000000-0000-4000-8000-000000000002", projectId: PROJECT_ID, runId: run(2), rule: "CONSECUTIVE_FAILURES", severity: "CRITICAL", subject: `task:${TASKS[2].id}`, message: "任務「實作」連續失敗 2 次", createdAt: t(30), acknowledged: false },
      { id: "a1000000-0000-4000-8000-000000000003", projectId: PROJECT_ID, runId: run(2), rule: "ENGINE_ESCALATION", severity: "CRITICAL", subject: "step:G2-T1", message: "引擎升級（ESCALATION）：評估未通過", createdAt: t(31), acknowledged: true, acknowledgedBy: "admin", acknowledgedAt: t(20) },
    ];
  }

  private metrics(runId: string | null, rangeMs: number) {
    const run = runId ? this.engine.runs.find((r) => r.id === runId) : undefined;
    // 數字隨範圍與批次改變，測試才看得出「前端真的帶了範圍／批次去查」
    const tokens = run ? run.tokens : rangeMs <= 3_600_000 ? 1240 : rangeMs <= 86_400_000 ? 8680 : 15000;
    return {
      projectId: PROJECT_ID,
      ...(runId ? { runId } : {}),
      from: new Date(Date.now() - rangeMs).toISOString(),
      to: new Date().toISOString(),
      generatedAt: new Date().toISOString(),
      projectCompletionRate: metric(66.7, 33.3),
      goalAchievementRate: metric(50, 50),
      taskCompletionRate: metric(80, 60),
      taskSuccessRate: metric(85.7, 90),
      averageRetryCount: metric(0.4, 0.2),
      retryRate: metric(14.3, 10),
      totalTokens: metric(tokens, 4960),
      tokenBudgetUsageRate: metric(8.7),
      averageTaskDurationSec: metric(125.5, 90),
      agentAvailability: metric(99.1),
      tokenBudget: 100000,
      taskStatusDistribution: { PENDING: 2, QUEUED: 1, BLOCKED: 0, RUNNING: 1, VALIDATING: 0, COMPLETED: 4, FAILED: 1, ESCALATED: 0, PAUSED: 0, SKIPPED: 0, CANCELLED: 0 },
      taskDurations: [
        { taskId: TASKS[2].id, taskName: "實作", goalName: "核心", durationSec: 210 },
        { taskId: TASKS[1].id, taskName: "設定", goalName: "基礎", durationSec: 95 },
        { taskId: TASKS[0].id, taskName: "初始化", goalName: "基礎", durationSec: 42.3 },
      ],
      retryDistribution: [0, 1, 2, 3, 4, 5].map((retries) => ({ retries, tasks: retries === 0 ? 5 : retries === 1 ? 2 : 0 })),
    };
  }

  private buckets(bucket: string, to: number) {
    const hour = bucket === "HOUR";
    const n = hour ? 6 : 5;
    const step = hour ? 3_600_000 : 86_400_000;
    const floor = Math.floor(to / step) * step;
    return Array.from({ length: n }, (_, i) => new Date(floor - (n - 1 - i) * step).toISOString());
  }

  private logsPage(q: URLSearchParams) {
    const level = q.get("level");
    const keyword = (q.get("q") ?? "").toLowerCase();
    const taskId = q.get("taskId");
    let rows = this.logs.filter((l) => (!level || level === "ALL" || l.level === level) && (!keyword || l.message.toLowerCase().includes(keyword)) && (!taskId || l.taskId === taskId));
    if ((q.get("order") ?? "desc") === "asc") rows = [...rows].reverse();
    const size = Number(q.get("size") ?? 20);
    const page = Number(q.get("page") ?? 0);
    return { content: rows.slice(page * size, page * size + size), page, size, totalElements: rows.length, totalPages: Math.max(1, Math.ceil(rows.length / size)) };
  }

  readonly handler: MockHandler = (call): MockReply => {
    const { method, path, query } = call;
    if (method === "GET" && path === "/api/v1/settings/monitor") {
      const cfg = (key: string, value: string, valueType: string) => ({ id: `c0ffee00-0000-4000-8000-0000000000${key.length}`, category: "monitor", key, value, valueType, defaultValue: value, description: key, isEncrypted: false, hasValue: true, effect: "CONSOLE", updatedAt: new Date().toISOString() });
      return { data: [cfg("refreshIntervalMs", this.refreshIntervalMs, "INT")] };
    }
    const ack = /^\/api\/v1\/monitor\/alerts\/([^/]+)\/acknowledge$/.exec(path);
    if (method === "POST" && ack) {
      this.seen.push({ method, path, query, headers: call.headers });
      if (this.ackFails) return { status: 500, error: { message: "伺服器暫時無法處理確認" }, delayMs: this.ackDelayMs };
      const alert = this.alerts.find((a) => a.id === ack[1]);
      if (!alert) return { status: 404, error: { message: "告警不存在" } };
      if (!alert.acknowledged) Object.assign(alert, { acknowledged: true, acknowledgedBy: "operator", acknowledgedAt: new Date().toISOString() });
      return { status: 204, delayMs: this.ackDelayMs };
    }
    const m = /^\/api\/v1\/monitor\/projects\/([^/]+)\/(metrics|token-trend|task-trend|alerts|logs|report)$/.exec(path);
    if (method !== "GET" || !m || m[1] !== PROJECT_ID) return undefined;
    this.seen.push({ method, path, query, headers: call.headers });
    const from = Date.parse(query.get("from") ?? "") || Date.now() - 86_400_000;
    const to = Date.parse(query.get("to") ?? "") || Date.now();
    switch (m[2]) {
      case "metrics":
        return { data: this.metrics(query.get("runId"), to - from) };
      case "token-trend": {
        let cumulative = 0;
        return {
          data: this.buckets(query.get("bucket") ?? "HOUR", to).map((bucketStart, i) => {
            const tokens = [0, 1240, 0, 2480, 1240, 3720][i % 6];
            cumulative += tokens;
            return { bucketStart, tokens, cumulativeTokens: cumulative, budget: 100000 };
          }),
        };
      }
      case "task-trend":
        return {
          data: this.buckets(query.get("bucket") ?? "HOUR", to).map((bucketStart, i) => ({ bucketStart, started: [1, 2, 0, 3, 1][i % 5], completed: [1, 1, 0, 2, 1][i % 5], failed: [0, 1, 0, 1, 0][i % 5], retried: [0, 1, 0, 0, 1][i % 5] })),
        };
      case "alerts": {
        const runId = query.get("runId");
        const rows = this.alerts.filter((a) => !runId || a.runId === runId).sort((a, b) => b.createdAt.localeCompare(a.createdAt));
        return { data: query.get("acknowledged") === null ? rows : rows.filter((a) => String(a.acknowledged) === query.get("acknowledged")) };
      }
      case "logs":
        return { data: this.logsPage(query) };
      default: {
        // report
        if (query.get("format") === "pdf") return { status: 501, error: { message: "PDF 報表尚未提供（W5）", reason: "PDF 報表尚未提供（W5）" } };
        return { status: 200, raw: CSV_BODY, headers: { "content-type": "text/csv;charset=UTF-8", "content-disposition": `attachment; filename="${CSV_FILENAME}"` } };
      }
    }
  };
}
