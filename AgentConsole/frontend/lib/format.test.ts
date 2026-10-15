import { describe, expect, it } from "vitest";

import { formatBytes, formatClock, formatDate, formatDateTime, formatElapsed, formatNumber, manualRetryLabel, percent, retryLabel } from "./format";

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
});
