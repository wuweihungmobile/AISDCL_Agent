import { describe, expect, it } from "vitest";

import {
  SDD_EMPTY_MESSAGE,
  SDD_PHASE_LABEL,
  SDD_PHASE_STEPS,
  SDD_REASON_MESSAGE,
  isSddEscalationState,
  pickSddProject,
  sddEscalationView,
  sddFrozenSummary,
  sddFsmNotFoundHint,
  sddHasUnresolvedEscalation,
  sddHumanPending,
  sddKeyDisplay,
  sddPhaseLabel,
  sddPhaseView,
  sddProjectDisplay,
  sddReasonMessage,
  sddRecentDecisions,
  sddRecoveryView,
  sddShowsEscalation,
  sddSprint,
  sddStateDir,
  sddText,
  sddTime,
  sddUsed,
} from "./sdd";

describe("AISDLC_SDD 引擎卡的顯示規則（契約 §1.7.1、§4.3 M-20；v1.4 D-16）", () => {
  it("reason 的中文文案逐字取自契約 M-20／M-21；六個值各一句，互不重複（v1.5 加 sdd_root_rejected）", () => {
    expect(SDD_REASON_MESSAGE).toEqual({
      bridge_unreachable: "Engine Bridge 無法連線",
      sdd_unavailable: "找不到 AISDLC_SDD 目錄（請檢查 Bridge 的 SDD_ROOT）",
      bridge_error: "Engine Bridge 回應異常",
      fsm_not_found: "找不到所選專案的 FSM 狀態檔",
      fsm_state_unreadable: "FSM 狀態檔無法讀取",
      sdd_root_rejected: "專案路徑不在 Bridge 允許的根目錄內（或已不存在）",
    });
    expect(new Set(Object.values(SDD_REASON_MESSAGE)).size).toBe(6);
    expect(SDD_EMPTY_MESSAGE).toBe("尚無 FSM 狀態檔（SDD runtime 執行後才會產生）");
  });

  it("沒有 reason（null、undefined、空字串）＝沒有訊息；後端日後新增的 reason 照樣顯示並附原值", () => {
    expect(sddReasonMessage(null)).toBeNull();
    expect(sddReasonMessage(undefined)).toBeNull();
    expect(sddReasonMessage("")).toBeNull();
    expect(sddReasonMessage("bridge_unreachable")).toBe("Engine Bridge 無法連線");
    expect(sddReasonMessage("future_reason")).toBe("引擎回報：future_reason");
  });

  it("預設專案：上次選的且仍在清單內者，否則清單第一個（不重排），沒有專案回 null", () => {
    const list = [{ project: "e2e-alpha" }, { project: "e2e-bravo" }, { project: "Zed" }];
    expect(pickSddProject(list, "e2e-bravo")).toBe("e2e-bravo");
    expect(pickSddProject(list, "已被刪掉的專案")).toBe("e2e-alpha");
    expect(pickSddProject(list, null)).toBe("e2e-alpha");
    expect(pickSddProject([], "e2e-bravo")).toBeNull();
    expect(pickSddProject(undefined, "e2e-bravo")).toBeNull();
  });

  it("欄位值轉顯示字串：字串與數字照原值、缺值與物件顯示「—」（不編造、不轉譯）", () => {
    expect(sddText("INIT")).toBe("INIT");
    expect(sddText("")).toBe("—");
    expect(sddText(7)).toBe("7");
    expect(sddText(true)).toBe("true");
    expect(sddText(null)).toBe("—");
    expect(sddText(undefined)).toBe("—");
    expect(sddText({ a: 1 })).toBe("—");
  });

  it("時間（ISO-8601 原樣字串）轉本機時區的「日期 時:分:秒」；解析不了就顯示原字串、缺值「—」", () => {
    const iso = new Date(2026, 9, 16, 9, 2, 3).toISOString(); // 用本機時區建構，避免依賴執行機器的時區
    expect(sddTime(iso)).toBe("2026-10-16 09:02:03");
    expect(sddTime("2026-10-16T01:02:03+00:00")).toMatch(/^2026-10-1[56] \d{2}:\d{2}:\d{2}$/);
    expect(sddTime("昨天下午")).toBe("昨天下午");
    expect(sddTime(null)).toBe("—");
    expect(sddTime("")).toBe("—");
    expect(sddTime(1234)).toBe("—");
  });

  it("Sprint：寫成「Sprint N」，缺值「—」", () => {
    expect(sddSprint(2)).toBe("Sprint 2");
    expect(sddSprint(0)).toBe("Sprint 0");
    expect(sddSprint(null)).toBe("—");
    expect(sddSprint(undefined)).toBe("—");
  });

  it("待人工：0＝「無」、1＝「等待人工確認」並列出 entered_at（本機時區）；多筆註明件數、最多列 5 個；缺 items 不崩潰", () => {
    expect(sddHumanPending({ count: 0, items: [] })).toEqual({ count: 0, label: "無", enteredAt: [] });
    expect(sddHumanPending(undefined)).toEqual({ count: 0, label: "無", enteredAt: [] });
    const one = sddHumanPending({ count: 1, items: [{ entered_at: new Date(2026, 9, 15, 16, 0, 0).toISOString(), reminder_hours: 72 }] });
    expect(one.label).toBe("等待人工確認");
    expect(one.enteredAt).toEqual(["2026-10-15 16:00:00"]);
    const many = sddHumanPending({ count: 7, items: Array.from({ length: 7 }, (_, i) => ({ entered_at: `2026-10-0${(i % 9) + 1}T00:00:00Z` })) });
    expect(many.label).toBe("等待人工確認（7 項）");
    expect(many.enteredAt).toHaveLength(5);
    expect(sddHumanPending({ count: 1, items: [] })).toEqual({ count: 1, label: "等待人工確認", enteredAt: [] }); // 計數有、項目沒給：不編造時間
    expect(sddHumanPending({ count: 1, items: [{}] }).enteredAt).toEqual(["—"]);
  });

  it("最近決策：取尾 5 筆、倒序（新→舊），每筆 from／to／reason 與原值逐值相等；缺值「—」", () => {
    const trace = Array.from({ length: 7 }, (_, i) => ({ ts: `2026-10-16T0${i}:00:00+00:00`, from: `S${i}`, to: `S${i + 1}`, reason: `r${i + 1}`, spec_refs: [], agents_consulted: [], trigger: "x" }));
    const rows = sddRecentDecisions(trace.slice(-5)); // API 給的是尾 5 筆（舊→新）
    expect(rows.map((r) => [r.from, r.to, r.reason])).toEqual([
      ["S6", "S7", "r7"],
      ["S5", "S6", "r6"],
      ["S4", "S5", "r5"],
      ["S3", "S4", "r4"],
      ["S2", "S3", "r3"],
    ]);
    expect(sddRecentDecisions(trace).map((r) => r.reason)).toEqual(["r7", "r6", "r5", "r4", "r3"]); // 就算拿到更長的陣列，也只取最後 5 筆
    expect(sddRecentDecisions([{ to: "INIT" }])).toEqual([{ ts: "—", from: "—", to: "INIT", reason: "—" }]);
    expect(sddRecentDecisions([])).toEqual([]);
    expect(sddRecentDecisions(undefined)).toEqual([]);
  });
});

describe("專案詳情「SDD 治理」區的綁定與狀態顯示（契約 §4.7.1；v1.5 整合輪 115，UI-SDD-01）", () => {
  it("狀態目錄＝<executionPath>/build/reports/fsm（結尾分隔符先去掉）；fsm_not_found 的處置說明帶它", () => {
    expect(sddStateDir("/work/core")).toBe("/work/core/build/reports/fsm");
    expect(sddStateDir("/work/core/")).toBe("/work/core/build/reports/fsm");
    expect(sddStateDir("D:\\work\\core\\")).toBe("D:\\work\\core/build/reports/fsm");
    expect(sddFsmNotFoundHint("/work/core")).toBe("請在專案根的 SDD session 建立：/work/core/build/reports/fsm");
  });

  it("「已使用 SDD」＝三欄（sddProject／sddSpecDir／sddSpecFile）任一有值；全空、null、空白字串都算沒用過（沒有「未綁定」狀態）", () => {
    expect(sddUsed({})).toBe(false);
    expect(sddUsed(null)).toBe(false);
    expect(sddUsed(undefined)).toBe(false);
    expect(sddUsed({ sddProject: null, sddSpecDir: null, sddSpecFile: null })).toBe(false);
    expect(sddUsed({ sddProject: "  ", sddSpecDir: "" })).toBe(false);
    expect(sddUsed({ sddProject: "alpha" })).toBe(true);
    expect(sddUsed({ sddSpecDir: "/work/core/docs" })).toBe(true);
    expect(sddUsed({ sddSpecFile: "/work/core/docs/TCS-A.md" })).toBe(true);
  });

  it("「SDD 專案」列：有值顯示值；缺值（NULL＝用預設）顯示「（預設：<專案名>）」而不是「—」", () => {
    expect(sddProjectDisplay("e2e17-alpha", "AISDLC Core")).toEqual({ text: "e2e17-alpha", isDefault: false });
    expect(sddProjectDisplay(null, "AISDLC Core")).toEqual({ text: "（預設：AISDLC Core）", isDefault: true });
    expect(sddProjectDisplay(undefined, "AISDLC Core")).toEqual({ text: "（預設：AISDLC Core）", isDefault: true });
    expect(sddProjectDisplay("   ", "AISDLC Core").isDefault).toBe(true);
  });

  it("「標準鍵」列：顯示 fsmProject；與檔內原名 project 不同時並列並標出原名；缺值「—」且不退回 project（🔴 不能拿 project 當鍵）", () => {
    expect(sddKeyDisplay({ project: "alpha", fsmProject: "alpha" })).toEqual({ key: "alpha", originalName: null });
    expect(sddKeyDisplay({ project: "我的/專案", fsmProject: "我的_專案" })).toEqual({ key: "我的_專案", originalName: "我的/專案" });
    expect(sddKeyDisplay({ project: "alpha", fsmProject: null })).toEqual({ key: "—", originalName: null });
    expect(sddKeyDisplay({ project: "alpha" })).toEqual({ key: "—", originalName: null });
    expect(sddKeyDisplay(null)).toEqual({ key: "—", originalName: null });
  });

  it("「凍結狀態」列：空陣列＝尚未凍結；≥1 筆＝已凍結：<最後一筆 stage>（<frozen_at 本機時區>）；單筆缺值各自「—」；缺席＝「—」", () => {
    expect(sddFrozenSummary([])).toBe("尚未凍結");
    const iso = new Date(2026, 9, 17, 8, 30, 12).toISOString();
    expect(
      sddFrozenSummary([
        { stage: "Stage-1", frozen_at: "2026-01-01T00:00:00Z" },
        { stage: "Stage-2", frozen_at: iso, approved_by: "operator", spec_doc_digests: { "a.md": "sha256:ab" } },
      ]),
    ).toBe("已凍結：Stage-2（2026-10-17 08:30:12）");
    expect(sddFrozenSummary([{ frozen_at: iso }])).toBe("已凍結：—（2026-10-17 08:30:12）");
    expect(sddFrozenSummary([{ stage: "S" }])).toBe("已凍結：S（—）");
    expect(sddFrozenSummary([{}])).toBe("已凍結：—（—）");
    expect(sddFrozenSummary([null as never])).toBe("已凍結：—（—）");
    expect(sddFrozenSummary(undefined)).toBe("—");
    expect(sddFrozenSummary(null)).toBe("—");
    expect(sddFrozenSummary("x" as never)).toBe("—");
  });
});

describe("階段進度（契約 §3.1.5、§4.7.3；UI-SDD-03）", () => {
  it("階段字典逐字取自契約：主路徑八個（order 1～8）加非主路徑四個；字典沒有的新值原樣顯示，缺值「—」", () => {
    expect(SDD_PHASE_STEPS.map((s) => [s.order, s.name, s.label])).toEqual([
      [1, "INTAKE", "立案"],
      [2, "SPECIFICATION", "規格撰寫"],
      [3, "HUMAN_GATE", "人工確認"],
      [4, "FROZEN", "規格凍結"],
      [5, "IMPLEMENTATION", "實作"],
      [6, "REVIEW", "審查"],
      [7, "VERIFICATION", "追溯驗證"],
      [8, "RELEASE", "發布"],
    ]);
    expect(SDD_PHASE_LABEL).toMatchObject({ BLOCKED: "阻塞（需人工）", TRANSIENT: "過渡中", OBSERVATION: "觀測中", UNKNOWN: "未知" });
    expect(Object.keys(SDD_PHASE_LABEL)).toHaveLength(12);
    expect(sddPhaseLabel("REVIEW")).toBe("審查");
    expect(sddPhaseLabel("FUTURE_PHASE")).toBe("FUTURE_PHASE");
    for (const empty of [null, undefined, "", "  "]) expect(sddPhaseLabel(empty)).toBe("—");
  });

  it("主路徑 order 1～8：該步驟「目前」、之前「已過」、之後「未到」", () => {
    const view = sddPhaseView({ currentState: "IMPLEMENTATION", phase: { name: "IMPLEMENTATION", order: 5, blocking: false, observation: false } });
    expect(view).toMatchObject({ present: true, name: "IMPLEMENTATION", label: "實作", order: 5, blocking: false, observation: false, delegated: false });
    expect(view.steps.map((s) => s.state)).toEqual(["done", "done", "done", "done", "current", "upcoming", "upcoming", "upcoming"]);
    expect(view.steps.map((s) => s.label)).toEqual(["立案", "規格撰寫", "人工確認", "規格凍結", "實作", "審查", "追溯驗證", "發布"]);
    const first = sddPhaseView({ currentState: "INIT", phase: { name: "INTAKE", order: 1, blocking: false, observation: false } });
    expect(first.steps.map((s) => s.state)).toEqual(["current", "upcoming", "upcoming", "upcoming", "upcoming", "upcoming", "upcoming", "upcoming"]);
    const last = sddPhaseView({ currentState: "RELEASE", phase: { name: "RELEASE", order: 8, blocking: false, observation: false } });
    expect(last.steps.map((s) => s.state)).toEqual(["done", "done", "done", "done", "done", "done", "done", "current"]);
  });

  it("觀測態：observation=true、「目前」是回歸階段；AUTOCLAUDE_DELEGATED 另有「委派」旗標（只看 currentState）", () => {
    const delegated = sddPhaseView({ currentState: "AUTOCLAUDE_DELEGATED", phase: { name: "IMPLEMENTATION", order: 5, blocking: false, observation: true } });
    expect(delegated).toMatchObject({ observation: true, delegated: true, order: 5, blocking: false });
    expect(delegated.steps.find((s) => s.state === "current")?.name).toBe("IMPLEMENTATION");
    const hub = sddPhaseView({ currentState: "HUB_SYNC", phase: { name: "OBSERVATION", order: 0, blocking: false, observation: true } });
    expect(hub).toMatchObject({ observation: true, delegated: false, order: 0, label: "觀測中" });
    expect(hub.steps).toEqual([]); // order 0：不標任何步驟
  });

  it("阻塞態：八個步驟全是「未到」（灰階）、blocking=true、標籤「阻塞（需人工）」", () => {
    const view = sddPhaseView({ currentState: "ESCALATION", phase: { name: "BLOCKED", order: 0, blocking: true, observation: false } });
    expect(view).toMatchObject({ blocking: true, label: "阻塞（需人工）", order: 0 });
    expect(view.steps).toHaveLength(8);
    expect(view.steps.every((s) => s.state === "upcoming")).toBe(true);
  });

  it("order 為 0 的非主路徑（TRANSIENT、UNKNOWN）：不畫步驟，只有標籤；未知的新階段名原樣顯示", () => {
    expect(sddPhaseView({ currentState: "AUTO_COMPACT_PENDING", phase: { name: "TRANSIENT", order: 0, blocking: false, observation: false } })).toMatchObject({ label: "過渡中", steps: [] });
    expect(sddPhaseView({ currentState: "???", phase: { name: "UNKNOWN", order: 0, blocking: false, observation: false } })).toMatchObject({ label: "未知", steps: [] });
    expect(sddPhaseView({ currentState: "NEW", phase: { name: "FUTURE_PHASE", order: 9, blocking: false, observation: false } })).toMatchObject({ label: "FUTURE_PHASE", steps: [] }); // order 超出 1～8：不畫
  });

  it("phase 缺席（null、undefined、整個 fsm 缺）或欄位格式不對：標籤「—」、不畫步驟、不崩潰", () => {
    for (const fsm of [{ currentState: "INIT" }, { currentState: "INIT", phase: null }, null, undefined]) {
      const view = sddPhaseView(fsm);
      expect(view).toMatchObject({ present: false, name: null, label: "—", order: 0, blocking: false, observation: false, steps: [] });
    }
    const garbage = sddPhaseView({ currentState: "INIT", phase: { name: 5, order: "x", blocking: "yes", observation: 1 } as never });
    expect(garbage).toMatchObject({ present: true, name: null, label: "—", order: 0, blocking: false, observation: false, steps: [] });
    expect(sddPhaseView({ currentState: "INIT", phase: { name: "REVIEW", order: 6.9, blocking: false, observation: false } }).order).toBe(6);
  });
});

describe("ESCALATION 區塊、未解升級的判斷式與恢復指令（契約 §4.7.3；ADR-XPLAT-016 §5.3）", () => {
  const OPEN = { triggered_at: new Date(2026, 9, 17, 9, 0, 0).toISOString(), trigger_reason: "引擎升級：評估未通過", resolved_at: null, resolution: null, source: "autoclaude_delegated" };
  const DONE = { ...OPEN, resolved_at: new Date(2026, 9, 17, 10, 30, 0).toISOString(), resolution: "人工恢復到 IMPLEMENTATION" };

  it("阻塞態判定：ESCALATION、ESCALATION_FINAL 兩個狀態（逐字，不看前後空白）；顯示區塊的條件還含 phase.blocking=true", () => {
    expect(isSddEscalationState("ESCALATION")).toBe(true);
    expect(isSddEscalationState("ESCALATION_FINAL")).toBe(true);
    for (const other of ["IMPLEMENTATION", "TERMINATED", " ESCALATION", "escalation", "", null, undefined, 7]) expect(isSddEscalationState(other)).toBe(false);
    expect(sddShowsEscalation({ currentState: "ESCALATION" })).toBe(true);
    expect(sddShowsEscalation({ currentState: "TERMINATED", phase: { name: "BLOCKED", order: 0, blocking: true, observation: false } })).toBe(true);
    expect(sddShowsEscalation({ currentState: "IMPLEMENTATION", phase: { name: "IMPLEMENTATION", order: 5, blocking: false, observation: false } })).toBe(false);
    expect(sddShowsEscalation(null)).toBe(false);
  });

  it("🔴 未解升級的判斷式＝「狀態屬 ESCALATION／ESCALATION_FINAL」且「末筆 resolved_at 為空」；人工恢復後（IMPLEMENTATION）即使 escalationProvenance 還在也不算", () => {
    expect(sddHasUnresolvedEscalation({ currentState: "ESCALATION", escalationHistory: [OPEN] })).toBe(true);
    expect(sddHasUnresolvedEscalation({ currentState: "ESCALATION_FINAL", escalationHistory: [DONE, OPEN] })).toBe(true); // 看末筆，不看前面的舊紀錄
    expect(sddHasUnresolvedEscalation({ currentState: "ESCALATION", escalationHistory: [OPEN, DONE] })).toBe(false); // 末筆已解
    expect(sddHasUnresolvedEscalation({ currentState: "ESCALATION", escalationHistory: [{ ...OPEN, resolved_at: "" }] })).toBe(true); // 空字串也是空
    expect(sddHasUnresolvedEscalation({ currentState: "ESCALATION", escalationHistory: [] })).toBe(true); // 狀態已是升級態、沒有任何歷史：仍是未解
    expect(sddHasUnresolvedEscalation({ currentState: "ESCALATION" })).toBe(true);
    expect(sddHasUnresolvedEscalation({ currentState: "IMPLEMENTATION", escalationHistory: [OPEN] })).toBe(false); // 恢復後的 IMPLEMENTATION：歷史殘留不算
    expect(sddHasUnresolvedEscalation({ currentState: null, escalationHistory: [OPEN] })).toBe(false);
    expect(sddHasUnresolvedEscalation(null)).toBe(false);
  });

  it("末筆摘要：「ESCALATION・<triggered_at 本機時區>・<trigger_reason>」；有 resolved_at 時加「已解決：<resolved_at>／<resolution>」；來源行只在 provenance 有值時出現", () => {
    const open = sddEscalationView({ currentState: "ESCALATION", escalationHistory: [DONE, OPEN], escalationProvenance: { source: "autoclaude_delegated_failed", rule_id: "R-9.20", reason: "x" } });
    expect(open).toMatchObject({ noRecord: false, unresolved: true, triggeredAt: "2026-10-17 09:00:00", reason: "引擎升級：評估未通過", resolved: null });
    expect(open.summary).toBe("ESCALATION・2026-10-17 09:00:00・引擎升級：評估未通過");
    expect(open.source).toBe("來源：autoclaude_delegated_failed・AutoClaude 委派失敗（引擎升級）");

    const done = sddEscalationView({ currentState: "ESCALATION", escalationHistory: [DONE] });
    expect(done.resolved).toBe("已解決：2026-10-17 10:30:00／人工恢復到 IMPLEMENTATION");
    expect(done.unresolved).toBe(false);
    expect(done.source).toBeNull(); // provenance 缺席：不顯示這一行（不寫「—」）
    expect(sddEscalationView({ currentState: "ESCALATION", escalationHistory: [OPEN], escalationProvenance: null }).source).toBeNull();
    expect(sddEscalationView({ currentState: "ESCALATION", escalationHistory: [OPEN], escalationProvenance: { source: "other_source" } }).source).toBe("來源：other_source");
    expect(sddEscalationView({ currentState: "ESCALATION", escalationHistory: [OPEN], escalationProvenance: {} }).source).toBe("來源：—"); // 有 provenance 而沒有 source：各欄缺值「—」
  });

  it("歷史為空而狀態是阻塞態：區塊寫「（沒有升級紀錄）」；末筆缺欄位各自「—」", () => {
    expect(sddEscalationView({ currentState: "ESCALATION", escalationHistory: [] })).toMatchObject({ noRecord: true, summary: "（沒有升級紀錄）", resolved: null });
    expect(sddEscalationView({ currentState: "ESCALATION" }).noRecord).toBe(true);
    const sparse = sddEscalationView({ currentState: "ESCALATION", escalationHistory: [{}] });
    expect(sparse).toMatchObject({ noRecord: false, triggeredAt: "—", reason: "—", summary: "ESCALATION・—・—" });
    expect(sddEscalationView(null).noRecord).toBe(true);
  });

  it("恢復指令：fsm.recovery 的 target／powershell／posix 原樣（含 <人工原因> 佔位）；缺席、null、兩段都沒字串＝null（前端絕不自己組指令）", () => {
    const recovery = {
      target: "IMPLEMENTATION",
      powershell: 'Push-Location "C:\\sdd"; & python -m x resume-from-escalation --reason "<人工原因>"; Pop-Location',
      posix: 'cd "/sdd" && python -m x resume-from-escalation --reason "<人工原因>"',
    };
    const view = sddRecoveryView(recovery);
    expect(view?.target).toBe("IMPLEMENTATION");
    expect(view?.commands).toEqual([
      { shell: "powershell", label: "PowerShell", command: recovery.powershell },
      { shell: "posix", label: "POSIX（bash／zsh）", command: recovery.posix },
    ]);
    expect(sddRecoveryView({ target: "IMPLEMENTATION", powershell: "只有 PowerShell", posix: "" })?.commands.map((c) => c.shell)).toEqual(["powershell"]);
    expect(sddRecoveryView({ target: "", powershell: "", posix: "" })).toBeNull();
    expect(sddRecoveryView(null)).toBeNull();
    expect(sddRecoveryView(undefined)).toBeNull();
    expect(sddRecoveryView("oops" as never)).toBeNull();
    expect(sddRecoveryView({ powershell: "a" } as never)?.target).toBe("—");
  });
});
