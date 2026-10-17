import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { REASONS } from "@/lib/api/reasons";
import { describeStartError } from "./startErrors";

const names: Record<string, string> = { g1: "基礎", g2: "核心", t1: "初始化" };
const nameOf = (id: string) => names[id];

const err = (status: number, reason: string, details: Record<string, unknown> = {}, extra: Partial<ConstructorParameters<typeof ApiError>[0]> = {}) =>
  new ApiError({ status, message: `訊息：${reason}`, reason, details, traceId: "tr-1", ...extra });

describe("啟動失敗的說明（契約 §1.2.1 驗證順序表）", () => {
  it("未 signoff（409）：標記 unsigned；專案本身、未審批的目標與任務分層列出（id 轉名稱，查不到退成前 8 碼）", () => {
    const v = describeStartError(err(409, REASONS.EXEC_UNSIGNED_DRAFT, { unsignedProjectId: "p1", unsignedGoalIds: ["g1", "g2"], unsignedTaskIds: ["t1", "abcdef0123456789"] }), nameOf);
    expect(v.unsigned).toBe(true);
    expect(v.title).toBe("未經人工審批的草案不可執行");
    expect(v.lines).toEqual(["專案本身尚未 signoff", "未審批的目標：基礎、核心", "未審批的任務：初始化、abcdef01"]);
    expect(v.traceId).toBe("tr-1");
  });

  it("專案本身已簽時 unsignedProjectId 缺席（details 不輸出 null）：不列「專案本身」", () => {
    const v = describeStartError(err(409, REASONS.EXEC_UNSIGNED_DRAFT, { unsignedGoalIds: ["g2"], unsignedTaskIds: [] }), nameOf);
    expect(v.lines).toEqual(["未審批的目標：核心"]);
  });

  it.each([
    [REASONS.EXEC_PROJECT_RUNNING, { projectId: "p1", runId: "r1" }, "已有進行中的批次"],
    [REASONS.EXEC_PROJECT_STATE_NOT_ALLOWED, { status: "ARCHIVED" }, "專案目前狀態：ARCHIVED"],
    [REASONS.EXEC_SCOPE_INVALID, { invalidGoalIds: ["g1"], invalidTaskIds: ["t1"] }, "不屬於此專案的目標：基礎"],
    [REASONS.EXEC_SCOPE_ALREADY_COMPLETED, { goalIds: ["g1"], taskIds: [] }, "已完成的目標：基礎"],
    [REASONS.EXEC_SCOPE_MISSING_DEPENDENCIES, { missingGoalIds: ["g2"] }, "需要一併選取的前置目標：核心"],
    [REASONS.EXEC_NO_RUNNABLE_TASKS, {}, "沒有可執行的任務"],
    [REASONS.EXEC_PATH_LOCKED, { holderRunId: "r0" }, "同一個專案路徑已有執行中的批次"],
    [REASONS.EXEC_PROMPT_TOO_LONG, { taskId: "t1", stepId: "G1-T1", length: 25000, limit: 20000 }, "G1-T1 的 prompt 長度 25000 超過上限 20000"],
    [REASONS.EXEC_EVALUATOR_FORBIDDEN_CHARS, { taskId: "t1", chars: ["|", ";"] }, "任務「初始化」的評估指令含禁用字元：| ;"],
    [REASONS.EXEC_EVALUATOR_NOT_WHITELISTED, { taskId: "t1", executable: "rm" }, "rm 不在可執行檔白名單"],
    [REASONS.EXEC_REGEX_INVALID, { taskId: "t1" }, "expectedOutputRegex 無法編譯"],
    [REASONS.EXEC_TOO_MANY_TASKS, { count: 600, limit: 500 }, "範圍內有 600 個任務，超過單一批次上限 500"],
    [REASONS.EXEC_MAX_RETRIES_EXCEEDED, { taskId: "t1", maxRetries: 25, limit: 20 }, "最大重試次數 25 超過上限 20"],
    [REASONS.EXEC_ENGINE_REJECTED, { bridgeReason: "path_not_allowed", violations: [] }, "引擎回報：path_not_allowed"],
  ])("%s：details 轉成人話（不拿 message 判斷、只認 reason 常數）", (reason, details, expected) => {
    const v = describeStartError(err(409, reason, details), nameOf);
    expect(v.title).toBe(reason);
    expect(v.lines.join("\n")).toContain(expected);
    expect(v.unsigned).toBe(false);
  });

  it("400 的欄位錯誤（Bean Validation）逐欄列出；未知 reason 與 502 退回後端訊息；非 ApiError 退回例外訊息", () => {
    const fields = describeStartError(new ApiError({ status: 400, message: "驗證失敗", errors: [{ field: "autonomyLevel", message: "必須介於 1～10" }] }), nameOf);
    expect(fields.lines).toEqual(["autonomyLevel：必須介於 1～10"]);
    const gw = describeStartError(new ApiError({ status: 502, message: "引擎橋接服務無法連線", reason: REASONS.BRIDGE_UNREACHABLE }), nameOf);
    expect(gw.title).toBe("引擎橋接服務無法連線");
    expect(describeStartError(new Error("boom"), nameOf)).toEqual({ title: "boom", lines: [], unsigned: false });
    expect(describeStartError("weird", nameOf).title).toBe("啟動失敗");
  });
});

describe("SDD 批次的預檢失敗（契約 §1.2.1 的 v1.5 加註、§1.10.6、附錄 B.5；整合輪 115）", () => {
  it("409 sdd_fsm_state_conflict：白話標題、目前狀態、可啟動的狀態、外來委派與佔用批次；附「代碼」行；不標 unsigned", () => {
    const v = describeStartError(
      err(409, REASONS.SDD_FSM_STATE_CONFLICT, { currentState: "AUTOCLAUDE_DELEGATED", expectedState: "IMPLEMENTATION", cause: "foreign_delegation", runId: "11112222-3333", runStatus: "RUNNING" }),
      nameOf,
    );
    expect(v.title).toBe("FSM 狀態不允許啟動 SDD 批次");
    expect(v.lines).toEqual([
      "目前狀態：AUTOCLAUDE_DELEGATED",
      "可啟動批次的狀態：IMPLEMENTATION",
      "FSM 正由外來委派佔用（不是 Console 的批次），請在 SDD session 處理後再試。",
      "佔用中的批次：11112222（RUNNING）",
      "代碼：sdd_fsm_state_conflict",
    ]);
    expect(v.unsigned).toBe(false);
    expect(v.traceId).toBe("tr-1");
  });

  it("ESCALATION 後的常態：指向恢復指令（Console 不提供恢復動作）", () => {
    const v = describeStartError(err(409, REASONS.SDD_FSM_STATE_CONFLICT, { currentState: "ESCALATION", expectedState: "IMPLEMENTATION" }), nameOf);
    expect(v.lines.some((l) => l.includes("SDD session 依恢復指令處理"))).toBe(true);
  });

  it.each([
    [REASONS.SDD_FSM_NOT_FOUND, { sddProject: "core-fsm" }, "找不到 FSM 專案狀態檔（core-fsm）；請先在專案根的 SDD session 建立"],
    [REASONS.SDD_SPEC_DIGEST_CHANGED, { pair: "frozen_vs_file", doc: "docs/T.md", frozenDigest: "sha256:a", currentDigest: "sha256:b" }, "凍結後規格檔內容已變更"],
    [REASONS.SDD_SPEC_DIGEST_CHANGED, { pair: "import_vs_file", doc: "docs/T.md" }, "規格檔內容與匯入時不同，請重新匯入規格"],
    [REASONS.SDD_WRITE_DISABLED, {}, "SDD 寫入功能未啟用（需管理員設定寫入權杖）"],
  ])("%s：標題是白話句子（原 reason 退到「代碼」行）", (reason, details, title) => {
    const v = describeStartError(err(409, reason, details), nameOf);
    expect(v.title).toContain(title);
    expect(v.lines).toContain(`代碼：${reason}`);
  });

  it("422 SDD 規格檢查未通過（預檢第 3 項）：引擎回報的原因白話化、附 Bridge 的 detail；reason 是中文，不另附代碼行", () => {
    const v = describeStartError(err(422, REASONS.IMPORT_SDD_SPEC_REJECTED, { bridgeReason: "spec_not_frozen", detail: "規格檔不在凍結清單" }), nameOf);
    expect(v.title).toBe("SDD 規格檢查未通過");
    expect(v.lines).toEqual(["引擎回報：規格尚未凍結（或不在凍結清單內）", "規格檔不在凍結清單"]);
  });

  it("422 引擎拒絕此請求維持原有的說明（bridgeReason 一行）；sdd_block_invalid 這類 Bridge 代碼原樣顯示", () => {
    const v = describeStartError(err(422, REASONS.EXEC_ENGINE_REJECTED, { bridgeReason: "sdd_block_invalid", violations: [] }), nameOf);
    expect(v.title).toBe("引擎拒絕此請求");
    expect(v.lines).toEqual(["引擎回報：sdd_block_invalid"]);
  });
});
