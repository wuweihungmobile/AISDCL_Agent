import { describe, expect, it } from "vitest";

import { EXECUTION_WARNING_CODES, GOVERNANCE_INACTIVE_CAUSES } from "@/lib/api/reasons";
import { GOVERNANCE_INACTIVE_CAUSE_TEXT, executionWarningViews, warningsToastSuffix } from "./executionWarnings";

describe("execute 201 的 warnings[]（契約 §1.10.6、附錄 B.5；API-EXE-15）", () => {
  it("sdd_governance_inactive：白話標題、cause 白話、後端 detail 原樣；五個 cause 都有白話（與契約 §1.10.5 同一組）", () => {
    expect(Object.keys(GOVERNANCE_INACTIVE_CAUSE_TEXT).sort()).toEqual([...GOVERNANCE_INACTIVE_CAUSES].sort());
    const [view] = executionWarningViews([{ code: EXECUTION_WARNING_CODES.SDD_GOVERNANCE_INACTIVE, cause: "mixed_scope", detail: "範圍內有非 SDD 來源的任務，本批次不啟用 SDD 治理" }]);
    expect(view.title).toContain("沒有啟用 SDD 治理");
    expect(view.cause).toBe("範圍內有非 SDD 來源的任務");
    expect(view.detail).toBe("範圍內有非 SDD 來源的任務，本批次不啟用 SDD 治理");
    for (const cause of GOVERNANCE_INACTIVE_CAUSES) {
      expect(executionWarningViews([{ code: "sdd_governance_inactive", cause, detail: "x" }])[0].cause).toBe(GOVERNANCE_INACTIVE_CAUSE_TEXT[cause]);
    }
  });

  it("sdd_frozen_digest_absent：沒有 cause；說明「放行，但無法偵測凍結後改檔」", () => {
    const [view] = executionWarningViews([{ code: EXECUTION_WARNING_CODES.SDD_FROZEN_DIGEST_ABSENT, detail: "舊版狀態檔" }]);
    expect(view.cause).toBeNull();
    expect(view.title).toContain("無法偵測凍結後改檔");
    expect(view.detail).toBe("舊版狀態檔");
  });

  it("日後新增的 code／cause 照樣顯示（原值），不崩潰也不吞掉；同一個 code 多筆各有自己的 key", () => {
    const views = executionWarningViews([
      { code: "future_code", cause: "future_cause", detail: "新的說明" },
      { code: "sdd_governance_inactive", cause: "future_cause", detail: "" },
      { code: "sdd_governance_inactive", cause: "not_bound", detail: "a" },
      { code: "sdd_governance_inactive", cause: "not_bound", detail: "b" },
    ]);
    expect(views[0]).toMatchObject({ title: "future_code", cause: "future_cause", detail: "新的說明" });
    expect(views[1].cause).toBe("future_cause");
    expect(views[1].detail).toBe("");
    expect(new Set(views.map((v) => v.key)).size).toBe(4);
  });

  it("缺席、null、不是陣列、陣列裡有垃圾：沒有警告（空陣列）而不是崩潰；缺 code 顯示「—」", () => {
    expect(executionWarningViews(undefined)).toEqual([]);
    expect(executionWarningViews(null)).toEqual([]);
    expect(executionWarningViews("oops" as never)).toEqual([]);
    expect(executionWarningViews([])).toEqual([]);
    expect(executionWarningViews([null as never, 5 as never])).toEqual([]);
    expect(executionWarningViews([{ detail: "沒有 code" } as never])[0]).toMatchObject({ code: "—", title: "—", cause: null });
  });

  it("toast 後綴：有警告時併進同一句（toast 一次只顯示一則）；沒有警告為空字串", () => {
    expect(warningsToastSuffix(0)).toBe("");
    expect(warningsToastSuffix(2)).toBe("（另有 2 則警告，見執行控制卡）");
  });
});
