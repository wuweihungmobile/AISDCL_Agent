import { describe, expect, it } from "vitest";

import type { ExecutionStep, TaskTrendPoint, TokenTrendPoint } from "@/lib/api/types";
import {
  DEFAULT_RANGE,
  MONITOR_RANGES,
  PRIMARY_KPIS,
  SECONDARY_KPIS,
  bucketFor,
  budgetUsagePct,
  deltaTone,
  durationColumns,
  formatBucketLabel,
  formatDelta,
  formatDuration,
  formatMetricValue,
  groupTaskStatus,
  isRangeId,
  rangeParams,
  ratioRows,
  retryColumns,
  taskTrendRows,
  timelineItems,
  toColumns,
  tokenTrendRows,
  weekStart,
} from "./metrics";

describe("時間範圍（1h／24h／7d／30d → from／to）", () => {
  it("四個選項、預設 24 小時；範圍 id 判斷", () => {
    expect(MONITOR_RANGES.map((r) => r.id)).toEqual(["1h", "24h", "7d", "30d"]);
    expect(DEFAULT_RANGE).toBe("24h");
    expect(isRangeId("7d")).toBe(true);
    expect(isRangeId("2d")).toBe(false);
  });

  it("from／to 取自同一個時鐘：to＝現在、from＝現在減範圍；from 一定早於 to（不會被後端 400「時間範圍不合法」）", () => {
    const now = new Date("2026-10-15T08:30:00.000Z");
    expect(rangeParams("1h", now)).toEqual({ from: "2026-10-15T07:30:00.000Z", to: "2026-10-15T08:30:00.000Z" });
    expect(rangeParams("24h", now).from).toBe("2026-10-14T08:30:00.000Z");
    expect(rangeParams("7d", now).from).toBe("2026-10-08T08:30:00.000Z");
    expect(rangeParams("30d", now).from).toBe("2026-09-15T08:30:00.000Z");
    for (const r of MONITOR_RANGES) {
      const p = rangeParams(r.id, now);
      expect(Date.parse(p.from)).toBeLessThan(Date.parse(p.to));
      // 契約：視窗上限 366 天
      expect(Date.parse(p.to) - Date.parse(p.from)).toBeLessThanOrEqual(366 * 86_400_000);
    }
  });

  it("桶粒度與契約預設一致：視窗 ≤ 48 小時用 HOUR，否則 DAY", () => {
    expect(bucketFor("1h")).toBe("HOUR");
    expect(bucketFor("24h")).toBe("HOUR");
    expect(bucketFor("7d")).toBe("DAY");
    expect(bucketFor("30d")).toBe("DAY");
  });

  it("本週一 00:00（本機時區）：週三、週日、週一當天都對", () => {
    const wed = weekStart(new Date(2026, 9, 14, 15, 30)); // 2026-10-14 是週三
    expect([wed.getFullYear(), wed.getMonth(), wed.getDate(), wed.getHours(), wed.getMinutes()]).toEqual([2026, 9, 12, 0, 0]);
    const sun = weekStart(new Date(2026, 9, 18, 23, 59)); // 週日屬於前一個週一開始的那週
    expect(sun.getDate()).toBe(12);
    const mon = weekStart(new Date(2026, 9, 12, 0, 0));
    expect(mon.getDate()).toBe(12);
    const crossMonth = weekStart(new Date(2026, 10, 3, 10, 0)); // 2026-11-03 週二 → 11-02 週一
    expect([crossMonth.getMonth(), crossMonth.getDate()]).toEqual([10, 2]);
    const prevMonth = weekStart(new Date(2026, 10, 1, 10, 0)); // 2026-11-01 週日 → 10-26 週一
    expect([prevMonth.getMonth(), prevMonth.getDate()]).toEqual([9, 26]);
  });
});

describe("KPI 卡格式化（契約：百分比 0～100 小數 1 位；null＝無法計算顯示「—」）", () => {
  it("設計稿四張卡與 PRD 另外六項：鍵、標籤、種類齊全", () => {
    expect(PRIMARY_KPIS.map((k) => k.label)).toEqual(["完成率", "任務成功率", "重試率", "Token 消耗"]);
    expect(SECONDARY_KPIS.map((k) => k.key)).toEqual([
      "projectCompletionRate",
      "goalAchievementRate",
      "averageRetryCount",
      "tokenBudgetUsageRate",
      "averageTaskDurationSec",
      "agentAvailability",
    ]);
    // 十個 KPI 一個不漏（契約 §1.3.1：十個 MetricValue）
    expect(new Set([...PRIMARY_KPIS, ...SECONDARY_KPIS].map((k) => k.key)).size).toBe(10);
  });

  it("數值：百分比一位小數、Token 千分位整數、平均兩位小數、秒數人話；null／NaN 顯示「—」", () => {
    expect(formatMetricValue("percent", 34.8)).toBe("34.8%");
    expect(formatMetricValue("percent", 100)).toBe("100.0%");
    expect(formatMetricValue("percent", 0)).toBe("0.0%");
    expect(formatMetricValue("tokens", 45230)).toBe("45,230");
    expect(formatMetricValue("decimal", 0.5)).toBe("0.50");
    expect(formatMetricValue("seconds", 1.8)).toBe("1.8s");
    for (const kind of ["percent", "tokens", "decimal", "seconds"] as const) {
      expect(formatMetricValue(kind, null)).toBe("—");
      expect(formatMetricValue(kind, undefined)).toBe("—");
      expect(formatMetricValue(kind, Number.NaN)).toBe("—");
    }
  });

  it("秒數格式：<10 秒一位小數、<60 秒整數、分鐘、小時", () => {
    expect(formatDuration(1.84)).toBe("1.8s");
    expect(formatDuration(45)).toBe("45s");
    expect(formatDuration(65)).toBe("1m 05s");
    expect(formatDuration(3725)).toBe("1h 02m");
    expect(formatDuration(null)).toBe("—");
  });

  it("delta 行：↑／↓／→ 加數值；沒有 delta（null／undefined）回 null＝整行不顯示", () => {
    expect(formatDelta("percent", 12.3)).toBe("↑ 12.3%");
    expect(formatDelta("percent", -2.1)).toBe("↓ 2.1%");
    expect(formatDelta("percent", 0)).toBe("→ 0.0%");
    expect(formatDelta("tokens", 8430)).toBe("↑ 8,430");
    expect(formatDelta("decimal", -0.25)).toBe("↓ 0.25");
    expect(formatDelta("seconds", 12)).toBe("↑ 12s");
    expect(formatDelta("percent", null)).toBeNull();
    expect(formatDelta("percent", undefined)).toBeNull();
  });

  it("delta 色調（設計稿：完成率↑綠、成功率↓紅、重試率↑ accent、Token↑ accent）", () => {
    expect(deltaTone("higher", 12.3)).toBe("good");
    expect(deltaTone("higher", -2.1)).toBe("bad");
    expect(deltaTone("lower", 1.5)).toBe("warn");
    expect(deltaTone("lower", -1.5)).toBe("good");
    expect(deltaTone("higher", 0)).toBe("flat");
    expect(deltaTone("higher", null)).toBe("flat");
  });

  it("預算使用率：已用／預算，一位小數；沒有預算回 null", () => {
    expect(budgetUsagePct(45230, 100000)).toBe(45.2);
    expect(budgetUsagePct(2480, 1500)).toBe(165.3);
    expect(budgetUsagePct(10, null)).toBeNull();
    expect(budgetUsagePct(10, 0)).toBeNull();
  });
});

describe("分佈整形", () => {
  it("任務狀態分四條（契約 §4.3 M-09）：完成＝COMPLETED；執行中＝RUNNING＋VALIDATING＋QUEUED；失敗＝FAILED＋ESCALATED；待處理＝其餘", () => {
    const dist = { PENDING: 1, QUEUED: 2, BLOCKED: 3, RUNNING: 4, VALIDATING: 5, COMPLETED: 6, FAILED: 7, ESCALATED: 8, PAUSED: 9, SKIPPED: 10, CANCELLED: 11 };
    expect(groupTaskStatus(dist)).toEqual([
      { id: "done", label: "完成", count: 6 },
      { id: "running", label: "執行中", count: 2 + 4 + 5 },
      { id: "failed", label: "失敗", count: 7 + 8 },
      { id: "pending", label: "待處理", count: 1 + 3 + 9 + 10 + 11 },
    ]);
    // 缺的狀態當 0；後端新增未知狀態算進「待處理」，總數守恆
    const partial = groupTaskStatus({ COMPLETED: 3, FUTURE: 2 });
    expect(partial.map((g) => g.count)).toEqual([3, 0, 0, 2]);
    expect(groupTaskStatus({}).every((g) => g.count === 0)).toBe(true);
  });

  it("垂直柱：高度以最大值為 100%，最高的標 highlight；全 0 時高度 0、沒有 highlight；非零的柱至少 4% 高才看得見", () => {
    const cols = toColumns([
      { label: "T1", value: 45 },
      { label: "T2", value: 32 },
      { label: "T3", value: 68 },
      { label: "T4", value: 1 },
    ]);
    expect(cols.map((c) => c.heightPct)).toEqual([66, 47, 100, 4]);
    expect(cols.map((c) => c.highlight)).toEqual([false, false, true, false]);
    const zeros = toColumns([{ label: "a", value: 0 }]);
    expect(zeros[0]).toMatchObject({ heightPct: 0, highlight: false });
    expect(toColumns([])).toEqual([]);
  });

  it("執行時間分佈：取前 8 筆（契約最多 10 筆、由長到短）；標籤是任務名", () => {
    const items = Array.from({ length: 10 }, (_, i) => ({ taskId: `t${i}`, taskName: `任務${i}`, durationSec: 100 - i }));
    const cols = durationColumns(items);
    expect(cols).toHaveLength(8);
    expect(cols[0]).toMatchObject({ label: "任務0", value: 100, highlight: true });
  });

  it("重試次數分佈：桶 0～5 依序，≥5 標「≥5 次」", () => {
    const cols = retryColumns([
      { retries: 5, tasks: 1 },
      { retries: 0, tasks: 8 },
      { retries: 2, tasks: 2 },
    ]);
    expect(cols.map((c) => c.label)).toEqual(["0 次", "2 次", "≥5 次"]);
    expect(cols.map((c) => c.value)).toEqual([8, 2, 1]);
  });
});

describe("趨勢整形", () => {
  const iso = (h: number) => new Date(2026, 9, 15, h, 0, 0).toISOString();

  it("桶標籤：HOUR＝「月/日 時:00」、DAY＝「月/日」（本機時區）；壞日期回「—」", () => {
    expect(formatBucketLabel(iso(14), "HOUR")).toBe("10/15 14:00");
    expect(formatBucketLabel(iso(14), "DAY")).toBe("10/15");
    expect(formatBucketLabel("not-a-date", "HOUR")).toBe("—");
  });

  it("Token 趨勢：折線取累計、預算線取 budget（沒有預算為 null）", () => {
    const points: TokenTrendPoint[] = [
      { bucketStart: iso(10), tokens: 1240, cumulativeTokens: 1240, budget: 100000 },
      { bucketStart: iso(11), tokens: 2480, cumulativeTokens: 3720, budget: null },
    ];
    expect(tokenTrendRows(points, "HOUR")).toEqual([
      { time: "10/15 10:00", used: 1240, tokens: 1240, budget: 100000 },
      { time: "10/15 11:00", used: 3720, tokens: 2480, budget: null },
    ]);
  });

  it("任務趨勢：完成／失敗／重試三條（堆疊面積）", () => {
    const points: TaskTrendPoint[] = [{ bucketStart: iso(10), started: 3, completed: 2, failed: 1, retried: 1 }];
    expect(taskTrendRows(points, "HOUR")).toEqual([{ time: "10/15 10:00", 完成: 2, 失敗: 1, 重試: 1 }]);
  });

  it("成功／失敗比率：由 completed、failed 計算（一位小數）；兩者皆 0 的桶略過", () => {
    const points: TaskTrendPoint[] = [
      { bucketStart: iso(10), started: 3, completed: 2, failed: 1, retried: 0 },
      { bucketStart: iso(11), started: 1, completed: 0, failed: 0, retried: 0 },
      { bucketStart: iso(12), started: 4, completed: 4, failed: 0, retried: 0 },
    ];
    expect(ratioRows(points, "HOUR")).toEqual([
      { label: "10/15 10:00", success: 66.7, failure: 33.3, total: 3 },
      { label: "10/15 12:00", success: 100, failure: 0, total: 4 },
    ]);
  });
});

describe("事件時間軸（來源＝步驟事件；啟動／完成／失敗／重試）", () => {
  const step = (n: number, status: ExecutionStep["status"], extra: Partial<ExecutionStep> = {}): ExecutionStep => ({
    id: `s${n}`,
    runId: "r",
    taskId: "t",
    taskName: "初始化",
    stepNumber: n,
    stepId: "G1-T1",
    attempt: 1,
    action: "G1-T1: 初始化",
    status,
    timestamp: new Date(2026, 9, 15, 10, 0, n).toISOString(),
    ...extra,
  });

  it("依事件 seq 升冪排列；色調對映：開始／完成／失敗／重試", () => {
    const items = timelineItems([step(3, "COMPLETED"), step(1, "STARTED"), step(2, "RETRYING", { attempt: 2 }), step(4, "FAILED", { errorMessage: "評估未通過" })]);
    expect(items.map((i) => i.tone)).toEqual(["start", "retry", "done", "failed"]);
    expect(items.map((i) => i.label)).toEqual(["G1-T1 開始", "G1-T1 重試", "G1-T1 完成", "G1-T1 失敗"]);
    expect(items[0].time).toBe("10:00:01");
    expect(items[1].title).toContain("第 2 次");
    expect(items[3].title).toContain("評估未通過");
  });

  it("沒有 stepId 時用任務名；沒有步驟：空陣列", () => {
    expect(timelineItems([step(1, "STARTED", { stepId: undefined })])[0].label).toBe("初始化 開始");
    expect(timelineItems([])).toEqual([]);
  });
});
