import { describe, expect, it } from "vitest";

import {
  allCheckState,
  buildScope,
  goalCheckState,
  initialSelection,
  isTaskChecked,
  lockReport,
  toggleAll,
  toggleGoal,
  toggleTask,
  type ScopeGoal,
  type ScopeTask,
  type Selection,
} from "./scope";

const goal = (id: string, patch: Partial<ScopeGoal> = {}): ScopeGoal => ({ id, name: `目標 ${id}`, status: "PENDING", signedOff: true, taskCount: 2, ...patch });
const task = (id: string, patch: Partial<ScopeTask> = {}): ScopeTask => ({ id, name: `任務 ${id}`, status: "PENDING", signedOff: true, ...patch });

const G1 = goal("g1");
const G2 = goal("g2");
const G3 = goal("g3", { status: "COMPLETED" });
const GOALS = [G1, G2, G3];
const T1 = [task("t1"), task("t2"), task("t3", { status: "COMPLETED" })];

describe("執行範圍選取（US-E-02；契約 §1.2.1 範圍解析）", () => {
  it("預設：全部「可執行」的目標整個選中（已完成的目標不選、不可勾）→ mode ALL", () => {
    const sel = initialSelection(GOALS);
    expect(sel).toEqual({ g1: true, g2: true });
    expect(allCheckState(sel, GOALS)).toBe("all");
    expect(buildScope(sel, GOALS).scope).toEqual({ mode: "ALL" });
    expect(toggleGoal(sel, G3)).toBe(sel); // 已完成：不可勾
  });

  it("取消一個目標：改成 SELECTED，goalIds 只列還選著的（ALL 時不帶 id，SELECTED 才帶）", () => {
    const sel = toggleGoal(initialSelection(GOALS), G2);
    expect(allCheckState(sel, GOALS)).toBe("some");
    expect(buildScope(sel, GOALS)).toEqual({ scope: { mode: "SELECTED", goalIds: ["g1"], taskIds: [] }, goalIds: ["g1"], taskIds: [] });
  });

  it("「全部目標」勾選：已全選 → 全取消（不可啟動：scope 為 null）；否則全選", () => {
    const none = toggleAll(initialSelection(GOALS), GOALS);
    expect(none).toEqual({});
    expect(buildScope(none, GOALS).scope).toBeNull();
    expect(allCheckState(none, GOALS)).toBe("none");
    expect(toggleAll(none, GOALS)).toEqual({ g1: true, g2: true });
    const some = toggleGoal(initialSelection(GOALS), G1);
    expect(toggleAll(some, GOALS)).toEqual({ g1: true, g2: true }); // 部分 → 補滿
  });

  it("展開任務：取消整個目標裡的一個任務 → 改成「其餘可執行任務」陣列；再勾回來就收斂回整個目標；已完成的任務不可勾", () => {
    let sel: Selection = initialSelection(GOALS);
    sel = toggleTask(sel, G1, T1[0], T1);
    expect(sel.g1).toEqual(["t2"]);
    expect(goalCheckState(sel, G1)).toBe("some");
    expect(isTaskChecked(sel, "g1", "t1")).toBe(false);
    expect(isTaskChecked(sel, "g1", "t2")).toBe(true);
    expect(allCheckState(sel, GOALS)).toBe("some");
    sel = toggleTask(sel, G1, T1[0], T1);
    expect(sel.g1).toBe(true);
    expect(toggleTask(sel, G1, T1[2], T1)).toBe(sel); // COMPLETED 的任務
  });

  it("部分任務 → mode SELECTED，goalIds 與 taskIds 分開列；全部取消則該目標從選取中移除", () => {
    let sel: Selection = {};
    sel = toggleTask(sel, G1, T1[0], T1);
    expect(sel).toEqual({ g1: ["t1"] });
    expect(buildScope(sel, GOALS)).toEqual({ scope: { mode: "SELECTED", goalIds: [], taskIds: ["t1"] }, goalIds: [], taskIds: ["t1"] });
    sel = { ...sel, g2: true };
    expect(buildScope(sel, GOALS).scope).toEqual({ mode: "SELECTED", goalIds: ["g2"], taskIds: ["t1"] });
    sel = toggleTask(sel, G1, T1[0], T1);
    expect(sel).toEqual({ g2: true });
  });

  it("全部可執行目標都整個選了，才是 ALL；只要有一個只選部分任務就不是", () => {
    const sel: Selection = { g1: ["t1"], g2: true };
    expect(buildScope(sel, GOALS).scope?.mode).toBe("SELECTED");
    expect(buildScope({ g1: true, g2: true }, GOALS).scope?.mode).toBe("ALL");
    expect(buildScope({ g1: true, g2: true }, [G1, G2]).scope?.mode).toBe("ALL");
    expect(buildScope({ g1: true }, [G1]).scope?.mode).toBe("ALL");
  });

  it("沒有任何可執行的目標（全完成）：不可啟動", () => {
    expect(initialSelection([G3])).toEqual({});
    expect(buildScope({}, [G3]).scope).toBeNull();
    expect(allCheckState({}, [G3])).toBe("none");
  });
});

describe("簽核鎖定（契約 §4.2 E-02：專案、所選目標、所選任務皆 signoff 才可啟動）", () => {
  const unsignedG2 = goal("g2", { signedOff: false });

  it("專案未簽：鎖定；全部簽了：不鎖", () => {
    expect(lockReport(false, [G1], { g1: true }, {})).toMatchObject({ projectUnsigned: true, locked: true });
    expect(lockReport(true, [G1, G2], { g1: true, g2: true }, {})).toMatchObject({ locked: false, unsignedGoals: [], unsignedTasks: [] });
  });

  it("只看「有選」的目標：未簽的目標沒被選就不鎖；選了就列出名稱並鎖定", () => {
    expect(lockReport(true, [G1, unsignedG2], { g1: true }, {}).locked).toBe(false);
    const r = lockReport(true, [G1, unsignedG2], { g1: true, g2: true }, {});
    expect(r).toMatchObject({ locked: true, unsignedGoals: ["目標 g2"] });
  });

  it("只選部分任務時不替後端多設一道（目標本身未簽但只選其中任務：不鎖，後端 409 會說明）", () => {
    expect(lockReport(true, [unsignedG2], { g2: ["t1"] }, { g2: [task("t1")] }).locked).toBe(false);
  });

  it("已載入的任務：被選中（整個目標或個別）且未簽就鎖定；沒被選、已完成的不算", () => {
    const tasks = { g1: [task("t1", { signedOff: false }), task("t2", { signedOff: false, status: "COMPLETED" }), task("t3")] };
    expect(lockReport(true, [G1], { g1: true }, tasks)).toMatchObject({ locked: true, unsignedTasks: ["任務 t1"] });
    expect(lockReport(true, [G1], { g1: ["t3"] }, tasks).locked).toBe(false);
    expect(lockReport(true, [G1], { g1: ["t1"] }, tasks).locked).toBe(true);
  });

  it("已完成的目標即使未簽也不算（不會被執行）", () => {
    expect(lockReport(true, [goal("gx", { status: "COMPLETED", signedOff: false })], { gx: true }, {}).locked).toBe(false);
  });
});
