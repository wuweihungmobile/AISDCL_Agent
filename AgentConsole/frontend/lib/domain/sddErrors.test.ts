import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { REASONS } from "@/lib/api/reasons";
import { SDD_BRIDGE_REASON_LABEL, SDD_EXECUTE_REASONS, SDD_VIOLATION_RULE_LABEL, describeSddError, sddBridgeReasonText, shortId } from "./sddErrors";

const api = (status: number, init: { reason?: string; message?: string; details?: Record<string, unknown>; errors?: Array<{ field: string; message: string }> } = {}) =>
  new ApiError({ status, message: init.message ?? "錯誤", reason: init.reason, details: init.details, errors: init.errors, traceId: `tr-${status}` });

describe("describeSddError：核准凍結（契約 §4.7.1 的逐字句子）", () => {
  it("sdd_fsm_state_conflict：「FSM 目前不在 HUMAN_PENDING（目前：<currentState>）」；currentState 缺值「—」", () => {
    const view = describeSddError(api(409, { reason: REASONS.SDD_FSM_STATE_CONFLICT, details: { currentState: "SPEC_FROZEN", expectedState: "HUMAN_PENDING" } }), "freeze");
    expect(view.title).toBe("FSM 目前不在 HUMAN_PENDING（目前：SPEC_FROZEN）");
    expect(view.code).toBe("sdd_fsm_state_conflict");
    expect(view.traceId).toBe("tr-409");
    expect(describeSddError(api(409, { reason: REASONS.SDD_FSM_STATE_CONFLICT }), "freeze").title).toBe("FSM 目前不在 HUMAN_PENDING（目前：—）");
  });

  it("sdd_fsm_not_found：「找不到 FSM 專案狀態檔（<details.sddProject>）；請先在專案根的 SDD session 建立」", () => {
    expect(describeSddError(api(409, { reason: REASONS.SDD_FSM_NOT_FOUND, details: { sddProject: "e2e17-alpha" } }), "freeze").title).toBe(
      "找不到 FSM 專案狀態檔（e2e17-alpha）；請先在專案根的 SDD session 建立",
    );
    expect(describeSddError(api(409, { reason: REASONS.SDD_FSM_NOT_FOUND }), "freeze").title).toContain("（—）");
  });

  it("sdd_binding_conflict（freeze）：逐字句子；衝突專案另列一行；sdd_spec_digest_changed：「規格檔在凍結前已被改動，請重新確認內容」並指出檔案", () => {
    const binding = describeSddError(
      api(409, { reason: REASONS.SDD_BINDING_CONFLICT, details: { cause: "already_bound_elsewhere", sddProject: "a", holderProjectId: "0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02" } }),
      "freeze",
    );
    expect(binding.title).toBe("同一個專案根下已有另一個專案綁定了這個 FSM 專案");
    expect(binding.lines).toEqual(["已綁定的專案：0b8c5d1e"]);
    const digest = describeSddError(api(409, { reason: REASONS.SDD_SPEC_DIGEST_CHANGED, details: { pair: "expected_vs_file", doc: "docs/TCS-A.md" } }), "freeze");
    expect(digest.title).toBe("規格檔在凍結前已被改動，請重新確認內容");
    expect(digest.lines).toEqual(["檔案：docs/TCS-A.md"]);
  });

  it("sdd_write_disabled（503）：「SDD 寫入功能未啟用（需管理員設定寫入權杖）」", () => {
    expect(describeSddError(api(503, { reason: REASONS.SDD_WRITE_DISABLED }), "freeze").title).toBe("SDD 寫入功能未啟用（需管理員設定寫入權杖）");
  });

  it("422 引擎拒絕此請求：列出 violations 的 field 與 rule（missing_tcs 附白話）、引擎回報的 bridgeReason；violations 為空時退回 details.detail", () => {
    const view = describeSddError(
      api(422, {
        reason: REASONS.EXEC_ENGINE_REJECTED,
        details: { bridgeReason: "sdd_invalid_argument", violations: [{ field: "docs", rule: "missing_tcs" }, { field: "reason", rule: "too_long", detail: "超過 500 字元" }, "字串項原樣", 7, null] },
      }),
      "freeze",
    );
    expect(view.title).toBe("引擎拒絕了這次核准凍結");
    expect(view.lines).toEqual(["docs／missing_tcs「規格文件須含至少一份 TCS」", "reason／too_long 超過 500 字元", "字串項原樣", "引擎回報：引數不合規格（核准人、理由或文件路徑）"]);
    const empty = describeSddError(api(422, { reason: REASONS.EXEC_ENGINE_REJECTED, details: { bridgeReason: "fsm_state_unreadable", violations: [], detail: "YAML 壞掉" } }), "freeze");
    expect(empty.lines).toEqual(["引擎回報：FSM 狀態檔無法讀取"]);
    expect(describeSddError(api(422, { reason: REASONS.EXEC_ENGINE_REJECTED, details: { violations: [], detail: "只有 detail" } }), "freeze").lines).toEqual(["只有 detail"]);
    expect(describeSddError(api(422, { reason: REASONS.EXEC_ENGINE_REJECTED }), "freeze").lines).toEqual([]);
  });

  it("502 引擎橋接服務錯誤：把 bridgeReason 白話化（權杖不一致是設定缺陷）並附 bridgeStatus；字典沒有的新值原樣顯示", () => {
    const forbidden = describeSddError(api(502, { reason: REASONS.BRIDGE_ERROR, details: { bridgeStatus: 403, bridgeReason: "sdd_write_forbidden" } }), "freeze");
    expect(forbidden.title).toBe("引擎橋接服務錯誤");
    expect(forbidden.lines[0]).toContain("權杖設定不一致");
    expect(forbidden.lines[1]).toBe("引擎橋接回應狀態：403");
    expect(describeSddError(api(502, { reason: REASONS.BRIDGE_ERROR, details: { bridgeReason: "future_reason" } }), "freeze").lines).toEqual(["引擎回報：future_reason"]);
    expect(describeSddError(api(502, { reason: REASONS.BRIDGE_ERROR }), "freeze").lines).toEqual([]);
  });

  it("引擎橋接無法連線／逾時（502／504）與 403 權限不足：給短句；404 專案不存在沿用後端 message", () => {
    expect(describeSddError(api(502, { reason: REASONS.BRIDGE_UNREACHABLE }), "freeze").title).toBe("引擎橋接服務無法連線");
    expect(describeSddError(api(504, { reason: REASONS.BRIDGE_TIMEOUT }), "freeze").title).toBe("引擎橋接服務逾時");
    expect(describeSddError(api(403, { reason: REASONS.ACCESS_DENIED }), "freeze").title).toContain("OPERATOR 以上");
    expect(describeSddError(api(404, { message: "專案不存在或已刪除：p1" }), "freeze").title).toBe("專案不存在或已刪除：p1");
  });

  it("400 的欄位錯誤分流到 fieldErrors（同欄位只留第一筆）；沒有欄位的項目進 lines；標題改成請修正輸入", () => {
    const view = describeSddError(
      api(400, {
        message: "請求參數錯誤",
        errors: [
          { field: "docs", message: "第 2 項不得含 .." },
          { field: "docs", message: "第二筆不採用" },
          { field: "reason", message: "不可為空" },
        ],
      }),
      "freeze",
    );
    expect(view.fieldErrors).toEqual({ docs: "第 2 項不得含 ..", reason: "不可為空" });
    expect(view.title).toBe("輸入內容有誤，請修正後再送出");
    const fieldless = describeSddError(api(400, { message: "請求格式錯誤", errors: [{ field: "", message: "JSON 解析失敗" }] }), "freeze");
    expect(fieldless.fieldErrors).toEqual({});
    expect(fieldless.lines).toEqual(["JSON 解析失敗"]);
    expect(fieldless.title).toBe("請求格式錯誤");
  });

  it("認不得的 reason：一般顯示（reason 為標題、message 在補充說明），帶 traceId；非 ApiError 退回例外訊息", () => {
    const unknown = describeSddError(api(500, { reason: "future_reason", message: "新的錯誤" }), "freeze");
    expect(unknown).toMatchObject({ title: "future_reason", lines: ["新的錯誤"], traceId: "tr-500" });
    expect(describeSddError(new Error("斷線了"), "freeze")).toEqual({ title: "斷線了", lines: [], fieldErrors: {} });
    expect(describeSddError("oops", "freeze").title).toBe("發生未知錯誤");
  });
});

describe("describeSddError：編輯 FSM 專案、啟動批次、匯入", () => {
  it("編輯綁定：sdd_binding_conflict 帶衝突專案前 8 碼（契約 §4.7.1）；沒有 holder 時用不帶專案的句子", () => {
    const withHolder = describeSddError(
      api(409, { reason: REASONS.SDD_BINDING_CONFLICT, details: { cause: "already_bound_elsewhere", holderProjectId: "0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02" } }),
      "binding",
    );
    expect(withHolder.title).toBe("同一個專案根下已有另一個專案（0b8c5d1e）綁定了這個 FSM 專案");
    expect(describeSddError(api(409, { reason: REASONS.SDD_BINDING_CONFLICT, details: { cause: "already_bound_elsewhere" } }), "binding").title).toBe(
      "同一個專案根下已有另一個專案綁定了這個 FSM 專案",
    );
  });

  it("啟動批次：sdd_fsm_state_conflict 列目前狀態、可啟動的狀態（字串或陣列）、外來委派、佔用批次；升級態指向恢復指令", () => {
    const view = describeSddError(
      api(409, {
        reason: REASONS.SDD_FSM_STATE_CONFLICT,
        details: { currentState: "AUTOCLAUDE_DELEGATED", expectedState: ["IMPLEMENTATION", "SPEC_FROZEN"], runId: "11112222-3333", runStatus: "RUNNING", cause: "foreign_delegation" },
      }),
      "execute",
    );
    expect(view.title).toBe("FSM 狀態不允許啟動 SDD 批次");
    expect(view.lines).toEqual([
      "目前狀態：AUTOCLAUDE_DELEGATED",
      "可啟動批次的狀態：IMPLEMENTATION、SPEC_FROZEN",
      "FSM 正由外來委派佔用（不是 Console 的批次），請在 SDD session 處理後再試。",
      "佔用中的批次：11112222（RUNNING）",
    ]);
    const escalated = describeSddError(api(409, { reason: REASONS.SDD_FSM_STATE_CONFLICT, details: { currentState: "ESCALATION", expectedState: "IMPLEMENTATION" } }), "execute");
    expect(escalated.lines).toContain("可啟動批次的狀態：IMPLEMENTATION");
    expect(escalated.lines.at(-1)).toContain("恢復指令");
    expect(describeSddError(api(409, { reason: REASONS.SDD_FSM_STATE_CONFLICT }), "execute").lines).toEqual(["目前狀態：—"]);
    expect(describeSddError(api(409, { reason: REASONS.SDD_FSM_STATE_CONFLICT, details: { currentState: "X", expectedState: [] } }), "execute").lines).toEqual(["目前狀態：X"]);
  });

  it("啟動批次：摘要不符依 pair 分三種說法（凍結後被改／匯入後被改）；SDD 規格檢查未通過列引擎回報與 detail", () => {
    expect(describeSddError(api(409, { reason: REASONS.SDD_SPEC_DIGEST_CHANGED, details: { pair: "frozen_vs_file", doc: "docs/T.md" } }), "execute").title).toContain("須在 SDD session 重新凍結");
    expect(describeSddError(api(409, { reason: REASONS.SDD_SPEC_DIGEST_CHANGED, details: { pair: "import_vs_file" } }), "execute").title).toContain("請重新匯入規格");
    expect(describeSddError(api(409, { reason: REASONS.SDD_SPEC_DIGEST_CHANGED, details: { pair: "new_pair" } }), "execute").title).toBe("規格檔內容已變更，請重新確認");
    expect(describeSddError(api(409, { reason: REASONS.SDD_SPEC_DIGEST_CHANGED }), "execute").title).toBe("規格檔內容已變更，請重新確認");
    const rejected = describeSddError(api(422, { reason: REASONS.IMPORT_SDD_SPEC_REJECTED, details: { bridgeReason: "spec_not_frozen", detail: "規格檔不在凍結清單" } }), "execute");
    expect(rejected.title).toBe("SDD 規格檢查未通過");
    expect(rejected.lines).toEqual(["引擎回報：規格尚未凍結（或不在凍結清單內）", "規格檔不在凍結清單"]);
    expect([...SDD_EXECUTE_REASONS].sort()).toEqual(["SDD 規格檢查未通過", "sdd_fsm_not_found", "sdd_fsm_state_conflict", "sdd_spec_digest_changed", "sdd_write_disabled"].sort());
  });

  it("匯入：sdd_binding_conflict 的另外兩種 cause——目標專案綁定不同、請求與目標不一致（指出欄位）", () => {
    const differently = describeSddError(api(409, { reason: REASONS.SDD_BINDING_CONFLICT, details: { cause: "target_bound_differently", sddProject: "beta" } }), "import");
    expect(differently.title).toBe("目標專案已綁定了不同的 FSM 專案或規格根，這份規格不能併入它");
    expect(differently.lines).toEqual(["目標專案目前綁定的 FSM 專案：beta"]);
    const request = describeSddError(api(409, { reason: REASONS.SDD_BINDING_CONFLICT, details: { cause: "request_differs_from_target", field: "executionPath" } }), "import");
    expect(request.title).toContain("取自目標專案");
    expect(request.lines).toEqual(["不一致的欄位：executionPath"]);
    expect(describeSddError(api(409, { reason: REASONS.SDD_BINDING_CONFLICT, details: { cause: "request_differs_from_target" } }), "import").lines).toEqual([]);
    expect(describeSddError(api(409, { reason: REASONS.SDD_BINDING_CONFLICT, details: { cause: "target_bound_differently" } }), "import").lines).toEqual([]);
  });
});

describe("輔助與契約對照", () => {
  it("shortId 取前 8 碼；缺值「—」", () => {
    expect(shortId("0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02")).toBe("0b8c5d1e");
    expect(shortId("abc")).toBe("abc");
    for (const empty of [undefined, null, "", 5]) expect(shortId(empty)).toBe("—");
  });

  it("sddBridgeReasonText：字典有的給白話、沒有的原樣、沒值回 null", () => {
    expect(sddBridgeReasonText("sdd_cli_timeout")).toBe("SDD CLI 執行逾時（超過 20 秒）");
    expect(sddBridgeReasonText("brand_new")).toBe("brand_new");
    for (const empty of [undefined, null, "", "  ", 3]) expect(sddBridgeReasonText(empty)).toBeNull();
    expect(SDD_VIOLATION_RULE_LABEL.missing_tcs).toBe("規格文件須含至少一份 TCS");
  });

  it("白話字典的每個 bridgeReason 鍵都出現在契約裡（契約改名就轉紅；前端不自己造 Bridge 的代碼）", () => {
    const md = readFileSync(path.join(process.cwd(), "..", "docs", "02_architecture", "API_Contract_P3-6.md"), "utf-8");
    for (const key of Object.keys(SDD_BRIDGE_REASON_LABEL)) expect(md, `契約找不到 Bridge reason ${key}`).toContain(`\`${key}\``);
    expect(md).toContain("`missing_tcs`");
  });
});
