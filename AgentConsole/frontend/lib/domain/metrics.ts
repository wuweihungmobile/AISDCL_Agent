/**
 * 監控頁與 Dashboard 的指標邏輯（契約 §1.3、§3.8、§4.3 M-01～M-19、§4.5 G-07／G-08；PRD §5.4.2）。純函式、不依賴 React。
 *  - 時間範圍 select（1h／24h／7d／30d）→ from／to；
 *  - KPI 卡：數值與 delta 的格式化、delta 的好壞色調（完成率↑好、重試率↑壞…）；
 *  - 分佈與趨勢的資料整形（任務狀態分組、執行時間欄、Token／任務趨勢列、事件時間軸）。
 */
import type { ExecutionStep, RetryBucket, TaskDurationItem, TaskTrendPoint, TokenTrendPoint, TrendBucket } from "@/lib/api/types";
import { stepStatus } from "@/lib/domain/status";

const DASH = "—";
const pad = (n: number): string => String(n).padStart(2, "0");

// ── 時間範圍 ──────────────────────────────────────────────────────────────
export type RangeId = "1h" | "24h" | "7d" | "30d";

export const MONITOR_RANGES: ReadonlyArray<{ id: RangeId; label: string; ms: number }> = [
  { id: "1h", label: "最近 1 小時", ms: 3_600_000 },
  { id: "24h", label: "最近 24 小時", ms: 86_400_000 },
  { id: "7d", label: "最近 7 天", ms: 7 * 86_400_000 },
  { id: "30d", label: "最近 30 天", ms: 30 * 86_400_000 },
];

export const DEFAULT_RANGE: RangeId = "24h";

export function isRangeId(value: string): value is RangeId {
  return MONITOR_RANGES.some((r) => r.id === value);
}

/**
 * 範圍 → from／to（ISO-8601，UTC 的 `Z` 寫法，契約接受任何帶 offset 的格式）。
 * from、to 取自同一個時鐘，保證 from 早於 to（用「只給 from、to 讓伺服器填」會在兩邊時鐘不同步時被 400「時間範圍不合法」）。
 * 呼叫時才計算（queryFn 內），所以查詢鍵只放範圍 id，不會因為時間在走而每次都是新查詢。
 */
export function rangeParams(range: RangeId, now: Date = new Date()): { from: string; to: string } {
  const ms = MONITOR_RANGES.find((r) => r.id === range)?.ms ?? 86_400_000;
  return { from: new Date(now.getTime() - ms).toISOString(), to: now.toISOString() };
}

/** 趨勢圖的桶粒度：與契約預設一致（視窗 ≤ 48 小時用 HOUR，否則 DAY）。 */
export function bucketFor(range: RangeId): TrendBucket {
  return range === "1h" || range === "24h" ? "HOUR" : "DAY";
}

/** 本週一 00:00（本機時區）；Dashboard「本週完成任務數」的 from（契約 §4.6 G-G3）。 */
export function weekStart(now: Date = new Date()): Date {
  const sinceMonday = (now.getDay() + 6) % 7;
  return new Date(now.getFullYear(), now.getMonth(), now.getDate() - sinceMonday, 0, 0, 0, 0);
}

// ── KPI 卡 ────────────────────────────────────────────────────────────────
export type MetricKind = "percent" | "tokens" | "decimal" | "seconds";
/** 數值變大是好事（higher）、壞事（lower）；Token 消耗變多不算好事（lower）。 */
export type MetricBetter = "higher" | "lower";

export type KpiKey =
  | "taskCompletionRate"
  | "taskSuccessRate"
  | "retryRate"
  | "totalTokens"
  | "projectCompletionRate"
  | "goalAchievementRate"
  | "averageRetryCount"
  | "tokenBudgetUsageRate"
  | "averageTaskDurationSec"
  | "agentAvailability";

export type KpiDef = { key: KpiKey; label: string; kind: MetricKind; better: MetricBetter };

/** 設計稿的四張卡（畫面 8）：完成率／任務成功率／重試率／Token 消耗。 */
export const PRIMARY_KPIS: readonly KpiDef[] = [
  { key: "taskCompletionRate", label: "完成率", kind: "percent", better: "higher" },
  { key: "taskSuccessRate", label: "任務成功率", kind: "percent", better: "higher" },
  { key: "retryRate", label: "重試率", kind: "percent", better: "lower" },
  { key: "totalTokens", label: "Token 消耗", kind: "tokens", better: "lower" },
];

/** PRD §5.4.2 另外六項（設計稿沒畫；契約 §4.3 M-07 供日後版面，這裡以較小的指標列呈現）。 */
export const SECONDARY_KPIS: readonly KpiDef[] = [
  { key: "projectCompletionRate", label: "專案完成率", kind: "percent", better: "higher" },
  { key: "goalAchievementRate", label: "目標達成率", kind: "percent", better: "higher" },
  { key: "averageRetryCount", label: "平均重試次數", kind: "decimal", better: "lower" },
  { key: "tokenBudgetUsageRate", label: "Token 預算使用率", kind: "percent", better: "lower" },
  { key: "averageTaskDurationSec", label: "平均任務時間", kind: "seconds", better: "lower" },
  { key: "agentAvailability", label: "Agent 可用率", kind: "percent", better: "higher" },
];

export function formatDuration(sec: number | null | undefined): string {
  if (sec === null || sec === undefined || !Number.isFinite(sec)) return DASH;
  if (sec < 10) return `${sec.toFixed(1)}s`;
  if (sec < 60) return `${Math.round(sec)}s`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ${pad(Math.round(sec % 60))}s`;
  return `${Math.floor(sec / 3600)}h ${pad(Math.floor((sec % 3600) / 60))}m`;
}

/** 數值無法計算（分母為 0、沒有探測樣本、無預算）時契約回 null → 顯示「—」。 */
export function formatMetricValue(kind: MetricKind, value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return DASH;
  switch (kind) {
    case "percent":
      return `${value.toFixed(1)}%`;
    case "tokens":
      return Math.round(value).toLocaleString("en-US");
    case "decimal":
      return value.toFixed(2);
    case "seconds":
      return formatDuration(value);
  }
}

/** delta 行（契約：delta＝value−previousValue，百分比為百分點）；沒有 delta 回 null＝不顯示這一行。 */
export function formatDelta(kind: MetricKind, delta: number | null | undefined): string | null {
  if (delta === null || delta === undefined || !Number.isFinite(delta)) return null;
  const arrow = delta > 0 ? "↑" : delta < 0 ? "↓" : "→";
  const magnitude = Math.abs(delta);
  const text =
    kind === "percent" ? `${magnitude.toFixed(1)}%` : kind === "tokens" ? Math.round(magnitude).toLocaleString("en-US") : kind === "decimal" ? magnitude.toFixed(2) : formatDuration(magnitude);
  return `${arrow} ${text}`;
}

/** good＝往好的方向（主色）；bad＝往壞的方向且是「該達成的指標掉了」（error 紅）；warn＝往壞的方向但屬「消耗類」（accent）；flat＝沒變。 */
export type DeltaTone = "good" | "bad" | "warn" | "flat";

export function deltaTone(better: MetricBetter, delta: number | null | undefined): DeltaTone {
  if (delta === null || delta === undefined || delta === 0 || !Number.isFinite(delta)) return "flat";
  if (better === "higher") return delta > 0 ? "good" : "bad";
  return delta > 0 ? "warn" : "good";
}

// ── 分佈 ──────────────────────────────────────────────────────────────────
export type StatusGroupId = "done" | "running" | "failed" | "pending";

const STATUS_GROUPS: ReadonlyArray<{ id: StatusGroupId; label: string; statuses: readonly string[] }> = [
  { id: "done", label: "完成", statuses: ["COMPLETED"] },
  { id: "running", label: "執行中", statuses: ["RUNNING", "VALIDATING", "QUEUED"] },
  { id: "failed", label: "失敗", statuses: ["FAILED", "ESCALATED"] },
];

/**
 * 任務狀態分佈的四條 bar（契約 §4.3 M-09）：完成＝COMPLETED；執行中＝RUNNING＋VALIDATING＋QUEUED；
 * 失敗＝FAILED＋ESCALATED；待處理＝其餘（PENDING／BLOCKED／PAUSED／SKIPPED／CANCELLED 與未知狀態）。
 */
export function groupTaskStatus(distribution: Readonly<Record<string, number>>): Array<{ id: StatusGroupId; label: string; count: number }> {
  const taken = new Set(STATUS_GROUPS.flatMap((g) => g.statuses));
  const count = (statuses: readonly string[]) => statuses.reduce((sum, s) => sum + (distribution[s] ?? 0), 0);
  const rest = Object.entries(distribution)
    .filter(([status]) => !taken.has(status))
    .reduce((sum, [, n]) => sum + n, 0);
  return [...STATUS_GROUPS.map((g) => ({ id: g.id, label: g.label, count: count(g.statuses) })), { id: "pending", label: "待處理", count: rest }];
}

export type Column = { label: string; value: number; heightPct: number; highlight: boolean };

/** 垂直柱：高度以最大值為 100%；最高的標 highlight（設計稿：最高用主色、其餘 secondary）。 */
export function toColumns(items: ReadonlyArray<{ label: string; value: number }>): Column[] {
  const max = Math.max(0, ...items.map((i) => i.value));
  return items.map((i) => ({
    label: i.label,
    value: i.value,
    heightPct: max > 0 ? Math.max(4, Math.round((i.value / max) * 100)) : 0,
    highlight: max > 0 && i.value === max,
  }));
}

/** 執行時間分佈（契約：視窗內完成的任務，耗時由長到短至多 10 筆）→ 前 limit 筆的柱。 */
export function durationColumns(items: readonly TaskDurationItem[], limit = 8): Column[] {
  return toColumns(items.slice(0, limit).map((i) => ({ label: i.taskName, value: i.durationSec })));
}

/** 重試次數分佈（桶 0～5 一律出現；≥5 併入 5）。 */
export function retryColumns(buckets: readonly RetryBucket[]): Column[] {
  return toColumns([...buckets].sort((a, b) => a.retries - b.retries).map((b) => ({ label: b.retries >= 5 ? "≥5 次" : `${b.retries} 次`, value: b.tasks })));
}

// ── 趨勢 ──────────────────────────────────────────────────────────────────
export function formatBucketLabel(iso: string, bucket: TrendBucket): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return DASH;
  const day = `${pad(d.getMonth() + 1)}/${pad(d.getDate())}`;
  return bucket === "HOUR" ? `${day} ${pad(d.getHours())}:00` : day;
}

export type TokenTrendRow = { time: string; used: number; tokens: number; budget: number | null };

/** Token 使用趨勢：折線畫累計（cumulativeTokens），預算線畫 budget（契約 §4.3 M-08）。 */
export function tokenTrendRows(points: readonly TokenTrendPoint[], bucket: TrendBucket): TokenTrendRow[] {
  return points.map((p) => ({
    time: formatBucketLabel(p.bucketStart, bucket),
    used: p.cumulativeTokens,
    tokens: p.tokens,
    budget: p.budget ?? null,
  }));
}

export type TaskTrendRow = { time: string; 完成: number; 失敗: number; 重試: number };

/** 任務執行趨勢（堆疊面積；UI-CHT-01）。 */
export function taskTrendRows(points: readonly TaskTrendPoint[], bucket: TrendBucket): TaskTrendRow[] {
  return points.map((p) => ({ time: formatBucketLabel(p.bucketStart, bucket), 完成: p.completed, 失敗: p.failed, 重試: p.retried }));
}

export type RatioRow = { label: string; success: number; failure: number; total: number };

/** 成功／失敗比率（UI-CHT-03）：成功率與失敗率由 completed、failed 計算（契約 §1.3.3）；兩者皆 0 的桶略過。 */
export function ratioRows(points: readonly TaskTrendPoint[], bucket: TrendBucket): RatioRow[] {
  return points
    .filter((p) => p.completed + p.failed > 0)
    .map((p) => {
      const total = p.completed + p.failed;
      return {
        label: formatBucketLabel(p.bucketStart, bucket),
        success: Math.round((p.completed / total) * 1000) / 10,
        failure: Math.round((p.failed / total) * 1000) / 10,
        total,
      };
    });
}

// ── 事件時間軸（來源＝GET /executions/{runId}/steps；契約 §4.3 M-12）──────────────────
export type TimelineTone = "start" | "done" | "failed" | "retry";

export type TimelineItem = { id: string; time: string; label: string; tone: TimelineTone; title: string };

const TIMELINE_TONE: Record<ExecutionStep["status"], TimelineTone> = {
  STARTED: "start",
  COMPLETED: "done",
  FAILED: "failed",
  RETRYING: "retry",
};

/** 步驟事件 → 時間軸節點（依 stepNumber＝事件 seq 升冪，與時間先後一致）。 */
export function timelineItems(steps: readonly ExecutionStep[]): TimelineItem[] {
  return [...steps]
    .sort((a, b) => a.stepNumber - b.stepNumber)
    .map((s) => {
      const d = new Date(s.timestamp);
      const time = Number.isNaN(d.getTime()) ? DASH : `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
      const code = s.stepId ?? s.taskName ?? "";
      return {
        id: s.id,
        time,
        label: `${code} ${stepStatus(s.status).label}`.trim(),
        tone: TIMELINE_TONE[s.status] ?? "start",
        title: `${time} · ${s.action}（${stepStatus(s.status).label}${s.attempt && s.attempt > 1 ? `，第 ${s.attempt} 次` : ""}）${s.errorMessage ? `：${s.errorMessage}` : ""}`,
      };
    });
}

/** Token 預算使用率（%，小數 1 位）；沒有預算回 null。 */
export function budgetUsagePct(used: number, budget: number | null | undefined): number | null {
  if (!budget || budget <= 0) return null;
  return Math.round((used / budget) * 1000) / 10;
}
