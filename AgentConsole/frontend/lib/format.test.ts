import { describe, expect, it } from "vitest";

import type { ResourceUsage } from "@/lib/api/types";

import { formatBytes, formatClock, formatDate, formatDateTime, formatElapsed, formatNumber, formatResourceUsage, manualRetryLabel, percent, retryLabel } from "./format";

describe("format", () => {
  // 用本機時區建構時間，避免測試依賴執行機器的時區
  const iso = new Date(2026, 5, 17, 14, 32, 5).toISOString();

  it("把 ISO 時間格式化成本機的日期／時間", () => {
    expect(formatDate(iso)).toBe("2026-06-17");
    expect(formatClock(iso)).toBe("14:32:05");
    expect(formatDateTime(iso)).toBe("2026-06-17 14:32");
  });

  it("缺值或壞值一律顯示「—」，不丟例外", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatClock(undefined)).toBe("—");
    expect(formatDateTime("not-a-date")).toBe("—");
    expect(formatNumber(undefined)).toBe("—");
  });

  it("執行耗時 HH:MM:SS（執行頁）；缺值、負值、NaN 顯示「—」", () => {
    expect(formatElapsed(0)).toBe("00:00:00");
    expect(formatElapsed(83)).toBe("00:01:23");
    expect(formatElapsed(5025)).toBe("01:23:45");
    expect(formatElapsed(360_000)).toBe("100:00:00");
    expect(formatElapsed(7.9)).toBe("00:00:07");
    expect(formatElapsed(null)).toBe("—");
    expect(formatElapsed(-1)).toBe("—");
    expect(formatElapsed(Number.NaN)).toBe("—");
  });

  it("檔案大小：B／KB／MB 三段，一位小數", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });

  it("數字加千分位、百分比取整且分母為 0 時回 0", () => {
    expect(formatNumber(12450)).toBe("12,450");
    expect(percent(3, 8)).toBe(38);
    expect(percent(0, 0)).toBe(0);
    expect(retryLabel(1, 3)).toBe("1 / 3");
  });

  it("手動重試文案（C-9）：第 N 次、明說不計入自動重試上限 M——手動重試可超過上限，不寫成「3 / 1」", () => {
    expect(manualRetryLabel(1, 3)).toBe("手動重試第 1 次（不計入自動重試上限 3）");
    expect(manualRetryLabel(3, 1)).toBe("手動重試第 3 次（不計入自動重試上限 1）");
  });

  describe("資源使用（契約 §4.3 M-19；US-M-10）", () => {
    const MB = 1024 * 1024;
    const GB = 1024 * MB;
    const usage = (memoryBytes: number, cpuPercent = 12.3, processCount = 3): ResourceUsage => ({ cpuPercent, memoryBytes, processCount, sampledAt: "2026-10-16T03:21:45.123456+00:00" });

    it("契約範例：CPU 小數 1 位加 %、記憶體 MB 取整數、行程數，三段以全形中點「・」相連", () => {
      expect(formatResourceUsage(usage(361_758_720))).toBe("CPU 12.3%・記憶體 345 MB・3 行程");
      expect(formatResourceUsage(usage(361_758_720))).toContain("%・記憶體 "); // 分隔字元是全形中點 U+30FB，不是半形的 · 或 •
    });

    it("CPU 一律一位小數（0 也寫 0.0、100 也寫 100.0）", () => {
      expect(formatResourceUsage(usage(10 * MB, 0, 1))).toBe("CPU 0.0%・記憶體 10 MB・1 行程");
      expect(formatResourceUsage(usage(10 * MB, 12.34))).toContain("CPU 12.3%");
      expect(formatResourceUsage(usage(10 * MB, 100))).toContain("CPU 100.0%");
    });

    it("記憶體 ÷ 1,048,576 四捨五入到整數 MB", () => {
      expect(formatResourceUsage(usage(344 * MB + 400_000))).toContain("記憶體 344 MB");
      expect(formatResourceUsage(usage(345 * MB + 600_000))).toContain("記憶體 346 MB");
      expect(formatResourceUsage(usage(1 * MB))).toContain("記憶體 1 MB");
    });

    it("不足 1 MB 寫「<1 MB」（含 0），不寫成「0 MB」或進位成「1 MB」", () => {
      expect(formatResourceUsage(usage(512 * 1024))).toContain("記憶體 <1 MB・");
      expect(formatResourceUsage(usage(MB - 1))).toContain("記憶體 <1 MB・");
      expect(formatResourceUsage(usage(0))).toContain("記憶體 <1 MB・");
    });

    it("達 1,024 MB 改以 GB（小數 1 位）；門檻比未四捨五入的位元組數，與「<1 MB」同一把尺", () => {
      expect(formatResourceUsage(usage(GB))).toContain("記憶體 1.0 GB・");
      expect(formatResourceUsage(usage(2.5 * GB))).toContain("記憶體 2.5 GB・");
      expect(formatResourceUsage(usage(GB - 1))).toContain("記憶體 1024 MB・"); // 差 1 byte 還是 MB 區間，不因四捨五入提前跳 GB
    });

    it("沒有資料（null／缺席）顯示單一「—」，不是半截的字串", () => {
      expect(formatResourceUsage(null)).toBe("—");
      expect(formatResourceUsage(undefined)).toBe("—");
    });

    it("任一欄位不是非負有限數字一律「—」（寧可不顯示，也不顯示 NaN 或負數）", () => {
      expect(formatResourceUsage(usage(MB, Number.NaN))).toBe("—");
      expect(formatResourceUsage(usage(-1))).toBe("—");
      expect(formatResourceUsage(usage(Number.POSITIVE_INFINITY))).toBe("—");
      expect(formatResourceUsage({ cpuPercent: 1, memoryBytes: MB } as unknown as ResourceUsage)).toBe("—"); // 缺 processCount
    });
  });
});
