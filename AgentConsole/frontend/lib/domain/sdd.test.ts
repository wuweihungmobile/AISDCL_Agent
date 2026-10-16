import { describe, expect, it } from "vitest";

import { SDD_EMPTY_MESSAGE, SDD_REASON_MESSAGE, pickSddProject, sddHumanPending, sddReasonMessage, sddRecentDecisions, sddSprint, sddText, sddTime } from "./sdd";

describe("AISDLC_SDD 引擎卡的顯示規則（契約 §1.7.1、§4.3 M-20；v1.4 D-16）", () => {
  it("reason 的中文文案逐字取自契約 M-20；五個值各一句，互不重複", () => {
    expect(SDD_REASON_MESSAGE).toEqual({
      bridge_unreachable: "Engine Bridge 無法連線",
      sdd_unavailable: "找不到 AISDLC_SDD 目錄（請檢查 Bridge 的 SDD_ROOT）",
      bridge_error: "Engine Bridge 回應異常",
      fsm_not_found: "找不到所選專案的 FSM 狀態檔",
      fsm_state_unreadable: "FSM 狀態檔無法讀取",
    });
    expect(new Set(Object.values(SDD_REASON_MESSAGE)).size).toBe(5);
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
