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
    const v = describeStartError(
      err(409, REASONS.EXEC_UNSIGNED_DRAFT, { unsignedProjectId: "p1", unsignedGoalIds: ["g1", "g2"], unsignedTaskIds: ["t1", "abcdef0123456789"] }),
      nameOf,
    );
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
    const fields = describeStartError(
      new ApiError({ status: 400, message: "驗證失敗", errors: [{ field: "autonomyLevel", message: "必須介於 1～10" }] }),
      nameOf,
    );
    expect(fields.lines).toEqual(["autonomyLevel：必須介於 1～10"]);
    const gw = describeStartError(new ApiError({ status: 502, message: "引擎橋接服務無法連線", reason: REASONS.BRIDGE_UNREACHABLE }), nameOf);
    expect(gw.title).toBe("引擎橋接服務無法連線");
    expect(describeStartError(new Error("boom"), nameOf)).toEqual({ title: "boom", lines: [], unsigned: false });
    expect(describeStartError("weird", nameOf).title).toBe("啟動失敗");
  });
});
