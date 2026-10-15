import { describe, expect, it } from "vitest";

import type { BridgeRunStatus, RunStatus } from "@/lib/api/types";
import { buttonFor, controlButtons, type ControlInput } from "./runControl";

const run = (status: RunStatus, bridgeStatus?: BridgeRunStatus) => ({ status, bridgeStatus });
const base = { canWrite: true, locked: false } as const;

/** 以「動作:啟用」的簡寫看按鈕列（保留順序）。 */
const row = (input: ControlInput) => controlButtons(input).map((b) => `${b.action}:${b.enabled ? "on" : "off"}`);

describe("執行控制按鈕狀態機（每個 run 狀態顯示哪些按鈕；契約 §4.2 E-07／E-08）", () => {
  it("沒有批次：只有「啟動執行」", () => {
    expect(row({ ...base, run: null })).toEqual(["start:on"]);
    expect(row({ ...base, run: undefined })).toEqual(["start:on"]);
  });

  it.each(["COMPLETED", "FAILED", "CANCELLED"] as const)("終態 %s：「啟動執行」（開新批次）與「從斷點恢復」（終態可還原）", (status) => {
    expect(row({ ...base, run: run(status) })).toEqual(["start:on", "restore:on"]);
  });

  it("RUNNING：「暫停」「取消」；不出現啟動、恢復、還原", () => {
    expect(row({ ...base, run: run("RUNNING", "RUNNING") })).toEqual(["pause:on", "cancel:on"]);
  });

  it("PAUSED：「恢復」「取消」「從斷點恢復」", () => {
    expect(row({ ...base, run: run("PAUSED", "PAUSED") })).toEqual(["resume:on", "cancel:on", "restore:on"]);
  });

  it("INITIALIZING（引擎啟動中）：暫停與取消都顯示但停用（後端會 409）", () => {
    const buttons = controlButtons({ ...base, run: run("INITIALIZING") });
    expect(buttons.map((b) => [b.action, b.enabled])).toEqual([
      ["pause", false],
      ["cancel", false],
    ]);
    expect(buttons.every((b) => b.hint)).toBe(true);
  });

  it("Bridge 過渡態：PAUSING 時暫停鈕停用並顯示「暫停中…」、取消仍可；CANCELLING 時兩顆都停用、取消顯示「取消中…」", () => {
    const pausing = controlButtons({ ...base, run: run("RUNNING", "PAUSING") });
    expect(buttonFor(pausing, "pause")).toMatchObject({ enabled: false, label: "暫停中…" });
    expect(buttonFor(pausing, "cancel")).toMatchObject({ enabled: true, label: "取消" });
    const cancelling = controlButtons({ ...base, run: run("RUNNING", "CANCELLING") });
    expect(buttonFor(cancelling, "pause")?.enabled).toBe(false);
    expect(buttonFor(cancelling, "cancel")).toMatchObject({ enabled: false, label: "取消中…" });
  });

  it("簽核鎖定：只停用「啟動執行」，並說明原因；暫停／恢復／取消不受影響", () => {
    const locked = controlButtons({ ...base, locked: true, run: null });
    expect(buttonFor(locked, "start")).toMatchObject({ enabled: false });
    expect(buttonFor(locked, "start")?.hint).toContain("signoff");
    expect(row({ ...base, locked: true, run: run("PAUSED", "PAUSED") })).toEqual(["resume:on", "cancel:on", "restore:on"]);
    expect(row({ ...base, locked: true, run: run("COMPLETED") })).toEqual(["start:off", "restore:on"]);
  });

  it("唯讀角色（VIEWER）：每個按鈕都停用並標示權限不足；有請求在途時也全部停用", () => {
    for (const r of [null, run("RUNNING", "RUNNING"), run("PAUSED"), run("FAILED")]) {
      const buttons = controlButtons({ canWrite: false, locked: false, run: r });
      expect(buttons.every((b) => !b.enabled && b.hint?.includes("唯讀"))).toBe(true);
    }
    const busy = controlButtons({ ...base, busy: true, run: run("RUNNING", "RUNNING") });
    expect(busy.every((b) => !b.enabled)).toBe(true);
  });

  it("還原鈕：不是專案最新批次、或已知沒有斷點時停用並說明；未知視為可用", () => {
    expect(buttonFor(controlButtons({ ...base, run: run("PAUSED"), isLatest: false }), "restore")).toMatchObject({ enabled: false, hint: "只能還原專案最新的執行批次" });
    expect(buttonFor(controlButtons({ ...base, run: run("FAILED"), hasCheckpoints: false }), "restore")?.enabled).toBe(false);
    expect(buttonFor(controlButtons({ ...base, run: run("FAILED") }), "restore")?.enabled).toBe(true);
  });

  it("按鈕文字＝設計稿（啟動執行／暫停／恢復／取消／從斷點恢復）", () => {
    const labels = (r: ControlInput["run"]) => controlButtons({ ...base, run: r }).map((b) => b.label);
    expect(labels(null)).toEqual(["啟動執行"]);
    expect(labels(run("RUNNING", "RUNNING"))).toEqual(["暫停", "取消"]);
    expect(labels(run("PAUSED"))).toEqual(["恢復", "取消", "從斷點恢復"]);
  });
});
