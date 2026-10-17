import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { REASONS } from "@/lib/api/reasons";
import { GATE_LABEL, describeConfirmError, gateLabel, highlightsFromRows, parseFailureFromError, parseFailureFromRecord, rowsFromApiError, rowsFromGateErrors } from "./gateErrors";

/** 422 有界閘回應的 errors 項目帶 gate／detail／location（比 ApiError 的 FieldError 型別多），測試以此函式組出。 */
const apiError = (init: Record<string, unknown>) => new ApiError(init as unknown as ConstructorParameters<typeof ApiError>[0]);

/** 契約 E2E-01 的 GATE_MULTI 變體：25 個任務且其中一個描述為空 → 兩項，順序 empty_prompt、max_steps（再加一個成環示範三項）。 */
const GATE_422 = apiError({
  status: 422,
  message: "解析結果未通過有界閘（2 項）",
  reason: REASONS.IMPORT_GATE_REJECTED,
  errors: [
    { field: "goals[0].tasks[3].description", message: "x", gate: "empty_prompt", detail: "任務「（未命名）」的描述為空（goals[0].tasks[3]）", location: "goals[0].tasks[3].description" },
    { field: "goals[0].tasks", message: "y", gate: "max_steps", detail: "目標「建立基礎架構」的任務數 25 超過上限 24（不截斷、不修剪）", location: "goals[0].tasks" },
    { field: "goals[1].dependsOn", message: "z", gate: "cycle", detail: "目標依賴成環：基礎 -> 核心 -> 基礎", location: "goals[1].dependsOn" },
  ],
  details: { path: "LLM" },
  traceId: "tr-422",
});

describe("匯入的 SDD 錯誤（v1.5，整合輪 115；契約 §3.3.2 第 8、9 點、§1.10.8）", () => {
  it("SDD 規格檢查未通過、bridgeReason=spec_digest_changed（凍結後規格被改，探測模式同樣 fail-closed）：除了引擎回報，另說明怎麼辦、且不會退回 AI 草稿路徑", () => {
    const view = parseFailureFromError(
      apiError({
        status: 422,
        message: "規格已變更",
        reason: REASONS.IMPORT_SDD_SPEC_REJECTED,
        errors: [],
        details: { bridgeReason: "spec_digest_changed", detail: "TCS 內容與凍結時的摘要不同" },
        traceId: "tr-1",
      }),
    );
    expect(view.notes).toEqual(["引擎回報：spec_digest_changed", "TCS 內容與凍結時的摘要不同", "規格在凍結之後又被改動：請在 SDD session 重新凍結（或還原改動）後再解析；不會退回 AI 草稿路徑。"]);
    expect(view.title).toBe("SDD 規格檢查未通過");
  });

  it("其他 bridgeReason（例如 spec_not_frozen）維持原本的兩行（不加 digest 的提示）", () => {
    const view = parseFailureFromError(
      apiError({ status: 422, message: "未凍結", reason: REASONS.IMPORT_SDD_SPEC_REJECTED, errors: [], details: { bridgeReason: "spec_not_frozen", detail: "請先完成凍結" } }),
    );
    expect(view.notes).toEqual(["引擎回報：spec_not_frozen", "請先完成凍結"]);
  });

  it("409 sdd_binding_conflict：標題維持逐字 reason，白話原因（依 cause）放補充說明", () => {
    const request = parseFailureFromError(
      apiError({ status: 409, message: "綁定衝突", reason: REASONS.SDD_BINDING_CONFLICT, errors: [], details: { cause: "request_differs_from_target", field: "specFile" } }),
    );
    expect(request.title).toBe("sdd_binding_conflict");
    expect(request.notes[0]).toContain("取自目標專案");
    expect(request.notes).toContain("不一致的欄位：specFile");
    const elsewhere = parseFailureFromError(
      apiError({
        status: 409,
        message: "綁定衝突",
        reason: REASONS.SDD_BINDING_CONFLICT,
        errors: [],
        details: { cause: "already_bound_elsewhere", sddProject: "a", holderProjectId: "1a2b3c4d-0000" },
      }),
    );
    expect(elsewhere.notes).toEqual(["同一個專案根下已有另一個專案（1a2b3c4d）綁定了這個 FSM 專案"]);
  });

  it("確認匯入失敗的一句話：綁定衝突給白話（不含英文代碼）附 traceId；其餘照一般錯誤；非 ApiError 退回例外訊息", () => {
    const conflict = apiError({
      status: 409,
      message: "綁定衝突",
      reason: REASONS.SDD_BINDING_CONFLICT,
      errors: [],
      details: { cause: "target_bound_differently", sddProject: "beta" },
      traceId: "tr-409",
    });
    expect(describeConfirmError(conflict)).toBe("目標專案已綁定了不同的 FSM 專案或規格根，這份規格不能併入它（目標專案目前綁定的 FSM 專案：beta）（traceId：tr-409）");
    const bare = apiError({ status: 409, message: "綁定衝突", reason: REASONS.SDD_BINDING_CONFLICT, errors: [], details: { cause: "request_differs_from_target" } });
    expect(describeConfirmError(bare)).toBe("使用「匯入到既有專案」時，執行路徑與 SDD 綁定一律取自目標專案，請求帶的值與它不同");
    expect(describeConfirmError(apiError({ status: 409, message: "草案尚未 signoff", reason: REASONS.IMPORT_NOT_SIGNED_OFF, errors: [], traceId: "tr-9" }))).toBe(
      "草案尚未 signoff：草案尚未 signoff，不可確認匯入（traceId：tr-9）",
    );
    expect(describeConfirmError(new Error("斷線"))).toBe("斷線");
    expect(describeConfirmError("oops")).toBe("發生未知錯誤");
  });
});

describe("有界閘錯誤正規化（US-I-10）", () => {
  it("422 的 errors[] 每一項都轉成一列，順序不變、原因全文保留（不截斷）", () => {
    const rows = rowsFromApiError(GATE_422);
    expect(rows.map((r) => r.gate)).toEqual(["empty_prompt", "max_steps", "cycle"]);
    expect(rows.map((r) => r.location)).toEqual(["goals[0].tasks[3].description", "goals[0].tasks", "goals[1].dependsOn"]);
    expect(rows[1].text).toBe("目標「建立基礎架構」的任務數 25 超過上限 24（不截斷、不修剪）");
    expect(rows[2].text).toContain("基礎 -> 核心 -> 基礎");
  });

  it("很長的 detail 也不被截斷", () => {
    const long = `任務「實作」的 prompt 長度 23412 超過上限 20000${"，請縮短".repeat(200)}`;
    const e = apiError({
      status: 422,
      message: "m",
      reason: REASONS.IMPORT_GATE_REJECTED,
      errors: [{ field: "f", message: "m", gate: "prompt_too_long", detail: long }],
    });
    expect(rowsFromApiError(e)[0].text).toBe(long);
  });

  it("parseFailureFromError：標題用 reason（逐字常數），標示為有界閘拒絕，並帶 traceId", () => {
    const f = parseFailureFromError(GATE_422);
    expect(f.title).toBe("解析結果未通過有界閘");
    expect(f.gateRejected).toBe(true);
    expect(f.rows).toHaveLength(3);
    expect(f.traceId).toBe("tr-422");
    expect(f.message).toBe("解析結果未通過有界閘（2 項）");
  });

  it("400 欄位錯誤（沒有 gate）：用 field 當位置、message 當原因", () => {
    const e = new ApiError({
      status: 400,
      message: "驗證失敗",
      errors: [{ field: "parsedResult.goals[0].tasks[1].passCriteria", message: "通過標準不可為空" }],
    });
    const f = parseFailureFromError(e);
    expect(f.gateRejected).toBe(false);
    expect(f.rows).toEqual([{ gate: undefined, location: "parsedResult.goals[0].tasks[1].passCriteria", text: "通過標準不可為空" }]);
  });

  it("422 SDD 規格檢查未通過：把 Bridge 的原因與細節列成說明行", () => {
    const e = new ApiError({
      status: 422,
      message: "SDD 規格未凍結",
      reason: REASONS.IMPORT_SDD_SPEC_REJECTED,
      errors: [{ field: "specDir", message: "規格未凍結" }],
      details: { bridgeReason: "spec_not_frozen", detail: "請先完成 SCG-3 凍結" },
    });
    const f = parseFailureFromError(e);
    expect(f.title).toBe("SDD 規格檢查未通過");
    expect(f.notes).toEqual(["引擎回報：spec_not_frozen", "請先完成 SCG-3 凍結"]);
    expect(f.gateRejected).toBe(false);
  });

  it("非 ApiError（例如執行期例外）也不崩潰", () => {
    expect(parseFailureFromError(new Error("boom"))).toMatchObject({ title: "boom", rows: [], gateRejected: false });
    expect(parseFailureFromError("x").title).toBe("發生未知錯誤");
  });

  it("重新整理或從歷史重開：lastParseErrors 還原成同一份清單；沒有就回 null", () => {
    const f = parseFailureFromRecord([
      { gate: "max_steps", detail: "D1", location: "goals" },
      { gate: "brain_failed", detail: "D2" },
    ]);
    expect(f?.gateRejected).toBe(true);
    expect(f?.rows).toEqual([
      { gate: "max_steps", location: "goals", text: "D1" },
      { gate: "brain_failed", location: undefined, text: "D2" },
    ]);
    expect(parseFailureFromRecord([])).toBeNull();
    expect(parseFailureFromRecord(undefined)).toBeNull();
    expect(rowsFromGateErrors(null)).toEqual([]);
  });

  it("閘別徽章：契約六個閘都有中文說明，未知閘退回原字串", () => {
    expect(Object.keys(GATE_LABEL).sort()).toEqual(["brain_failed", "brain_unsupported", "cycle", "empty_prompt", "max_steps", "prompt_too_long"]);
    expect(gateLabel("max_steps")).toBe("步驟上限（≤ 24）");
    expect(gateLabel("future_gate")).toBe("future_gate");
    expect(gateLabel(undefined)).toBeUndefined();
  });
});

describe("違規位置 → 樹節點", () => {
  it("任務、目標、依賴、400 欄位前綴都能對回節點；沒指到節點的位置（goals、sourceContent）不標紅", () => {
    const h = highlightsFromRows([
      { gate: "empty_prompt", location: "goals[0].tasks[3].description", text: "" },
      { gate: "cycle", location: "goals[1].dependsOn", text: "" },
      { location: "parsedResult.goals[2].tasks[0].passCriteria", text: "" },
      { gate: "max_steps", location: "goals", text: "" },
      { gate: "prompt_too_long", location: "sourceContent", text: "" },
      { location: "project.name", text: "" },
    ]);
    expect([...h.tasks].sort()).toEqual(["0.3", "2.0"]);
    expect([...h.goals]).toEqual([1]);
    expect(h.project).toBe(true);
  });

  it("goals[i].tasks（任務數超限）標在該目標上", () => {
    const h = highlightsFromRows([{ gate: "max_steps", location: "goals[4].tasks", text: "" }]);
    expect([...h.goals]).toEqual([4]);
    expect(h.tasks.size).toBe(0);
  });
});
