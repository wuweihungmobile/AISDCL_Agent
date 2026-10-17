import { describe, expect, it } from "vitest";

import type { ExecutionRtm } from "@/lib/api/types";
import { RTM_ADVISORY_NOTE, RTM_DIGEST_SHOWN, RTM_UNMAPPED_NOTE, RTM_WEAK_NOTE, rtmView } from "./rtm";

const DIGEST = "sha256:1f0e2b7a9c4d8e3f6a1b5c7d9e0f2a4b6c8d0e1f3a5b7c9d1e3f5a7b9c0d2e4f";

/** 契約 §1.10.3 的範例：4 個 AT 全過、2 個 AC 全覆蓋、沒有無法歸屬者。 */
const FULL: ExecutionRtm = {
  scenario: "greenfield",
  specDigest: DIGEST,
  at: { passed: 4, total: 4, unmapped: 0, pct: 100 },
  ac: { covered: 2, total: 2, pct: 100 },
  failedAtIds: [],
  weakRegexAtIds: [],
  unmappedAtIds: [],
  fullyCovered: true,
  advisory: true,
};

describe("追溯覆蓋面板的顯示規則（契約 §4.7.2；UI-SDD-02）", () => {
  it("契約範例：「4／4（100.0%）」「2／2（100.0%）」「AC 已達 100% 覆蓋」；清單為空顯示「無」（確定沒有），沒有任何備註", () => {
    expect(rtmView(FULL)).toEqual({
      advisory: true,
      at: "4／4（100.0%）",
      atNote: null,
      ac: "2／2（100.0%）",
      scg5: "AC 已達 100% 覆蓋",
      specDigest: { text: `${DIGEST.slice(0, 19)}…`, full: DIGEST },
      scenario: "greenfield",
      failed: "無",
      weak: "無",
      weakNote: null,
      unmapped: "無",
      unmappedNote: null,
    });
    expect(RTM_DIGEST_SHOWN).toBe("sha256:".length + 12);
    expect(rtmView(FULL).specDigest.text).toBe("sha256:1f0e2b7a9c4d…");
  });

  it("百分比是 Bridge 原值、固定 1 位小數（66.666 → 66.7%）；未過的 AT 以逗號分隔", () => {
    const view = rtmView({ ...FULL, at: { passed: 2, total: 3, unmapped: 0, pct: 66.666 }, ac: { covered: 1, total: 2, pct: 50 }, failedAtIds: ["AT-001-2", "AT-002-1"], fullyCovered: false });
    expect(view.at).toBe("2／3（66.7%）");
    expect(view.ac).toBe("1／2（50.0%）");
    expect(view.failed).toBe("AT-001-2, AT-002-1");
    expect(view.scg5).toBe("AC 未達 100% 覆蓋");
  });

  it("有無法歸屬 AC 的 AT：AT 列加註「其中 n 個無法歸屬到 AC」；AC 已全覆蓋仍「不視為全覆蓋」（fullyCovered=false）；清單列出並附說明", () => {
    const view = rtmView({ ...FULL, at: { passed: 5, total: 5, unmapped: 1, pct: 100 }, unmappedAtIds: ["AT-9-X"], fullyCovered: false });
    expect(view.at).toBe("5／5（100.0%）");
    expect(view.atNote).toBe("其中 1 個無法歸屬到 AC");
    expect(view.scg5).toBe("AC 已達 100%，但有無法歸屬的 AT，不視為全覆蓋");
    expect(view.unmapped).toBe("AT-9-X");
    expect(view.unmappedNote).toBe(RTM_UNMAPPED_NOTE);
    expect(RTM_UNMAPPED_NOTE).toBe("這些 AT 的編號不符 AT-NNN-Y-… 文法或 AC 對不上，已計入 AT 總數但不計入任何 AC");
  });

  it("AC 沒全覆蓋、同時有無法歸屬者：只說「AC 未達 100% 覆蓋」（不誤報成「已達 100%」）", () => {
    const view = rtmView({ ...FULL, ac: { covered: 1, total: 2, pct: 50 }, unmappedAtIds: ["AT-9-X"], fullyCovered: false });
    expect(view.scg5).toBe("AC 未達 100% 覆蓋");
  });

  it("驗收 regex 偏弱的 AT：列出並附「規格的 Then 沒有可推導的引號字面值，驗收可能偏鬆」", () => {
    const view = rtmView({ ...FULL, weakRegexAtIds: ["AT-001-1"] });
    expect(view.weak).toBe("AT-001-1");
    expect(view.weakNote).toBe(RTM_WEAK_NOTE);
    expect(RTM_WEAK_NOTE).toBe("規格的 Then 沒有可推導的引號字面值，驗收可能偏鬆");
  });

  it("固定說明與徽章：AT 通過只代表評估指令與驗收 regex 皆通過，不等於規格被滿足；SCG-4 的人工審查才是真閘", () => {
    expect(RTM_ADVISORY_NOTE).toBe("AT 通過只代表評估指令與驗收 regex 皆通過，不等於規格被滿足；SCG-4 的人工審查才是真閘。");
    expect(rtmView(FULL).advisory).toBe(true);
    expect(rtmView({}).advisory).toBe(true); // 缺席也當諮詢（不讓缺欄位變成「正式報告」）
  });

  it("缺席一律「—」、不顯示 undefined 或 null；摘要與場景空字串「—」；摘要不足 19 碼不加「…」", () => {
    const empty = rtmView({});
    expect(empty).toEqual({
      advisory: true,
      at: "—",
      atNote: null,
      ac: "—",
      scg5: "—",
      specDigest: { text: "—", full: null },
      scenario: "—",
      failed: "—",
      weak: "—",
      weakNote: null,
      unmapped: "—",
      unmappedNote: null,
    });
    expect(rtmView(null).at).toBe("—");
    expect(rtmView(undefined).ac).toBe("—");
    expect(rtmView({ ...FULL, specDigest: "", scenario: "" })).toMatchObject({ specDigest: { text: "—", full: null }, scenario: "—" });
    expect(rtmView({ ...FULL, specDigest: "sha256:abc" }).specDigest).toEqual({ text: "sha256:abc", full: "sha256:abc" });
    // 計數有、百分比缺：只有百分比那一格「—」
    expect(rtmView({ ...FULL, at: { passed: 1, total: 2, unmapped: 0 } as never }).at).toBe("1／2（—）");
    // 計數不是數字：整格「—」
    expect(rtmView({ ...FULL, at: { passed: "x", total: 2, unmapped: 0, pct: 1 } as never }).at).toBe("—");
    expect(rtmView({ ...FULL, failedAtIds: [null, 5] as never }).failed).toBe("—");
    expect(rtmView({ ...FULL, unmappedAtIds: "oops" as never }).unmapped).toBe("—");
  });
});
