import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import { REASONS } from "@/lib/api/reasons";
import { applyServerErrors, describeDeleteError, describeRestoreError } from "./apiErrors";

describe("後端錯誤 → 表單欄位", () => {
  it("errors[].field 對得上的欄位就 setError；全部對上時回 null（不顯示橫幅）", () => {
    const setError = vi.fn();
    const err = new ApiError({
      status: 400,
      message: "Validation failed",
      errors: [
        { field: "name", message: "名稱不能為空" },
        { field: "executionPath", message: "執行路徑必須是絕對路徑" },
      ],
    });
    expect(applyServerErrors(err, setError, ["name", "executionPath"])).toBeNull();
    expect(setError).toHaveBeenCalledWith("name", { type: "server", message: "名稱不能為空" });
    expect(setError).toHaveBeenCalledWith("executionPath", { type: "server", message: "執行路徑必須是絕對路徑" });
  });

  it("對不上欄位的錯誤、409 與網路錯誤以橫幅文字回傳（含 reason 與 traceId）", () => {
    const setError = vi.fn();
    const conflict = new ApiError({
      status: 409,
      message: "專案執行中，不可變更執行路徑",
      reason: "狀態衝突",
      traceId: "tr-1",
    });
    expect(applyServerErrors(conflict, setError, ["name"])).toBe("專案執行中，不可變更執行路徑（狀態衝突）（traceId：tr-1）");
    expect(setError).not.toHaveBeenCalled();
    expect(applyServerErrors(new Error("boom"), setError, [])).toBe("boom");
  });

  it("mapMessage 可改寫欄位訊息（依賴成環：把 UUID 換成名稱）", () => {
    const setError = vi.fn();
    const err = new ApiError({
      status: 400,
      message: "目標依賴成環",
      reason: "依賴成環",
      errors: [{ field: "dependsOn", message: "a -> b -> a" }],
      details: { cycle: ["a", "b", "a"] },
    });
    applyServerErrors(err, setError, ["dependsOn"], (field, _m, e) => (field === "dependsOn" ? `${e.reason}：甲 → 乙 → 甲` : _m));
    expect(setError).toHaveBeenCalledWith("dependsOn", { type: "server", message: "依賴成環：甲 → 乙 → 甲" });
  });
});

describe("復原專案失敗的原因（C-3；契約 §1.6.1）：三種前提不符各有白話說明", () => {
  it("409 project_not_deleted：沒有被刪除", () => {
    const err = new ApiError({ status: 409, message: "專案未被刪除", reason: REASONS.PROJECT_NOT_DELETED, details: { projectId: "p1", status: "READY" }, traceId: "tr-1" });
    expect(describeRestoreError(err)).toBe("這個專案目前沒有被刪除（可能已被其他人復原），不需要復原。（traceId：tr-1）");
  });

  it("409 restore_window_expired：超過保留期，帶出 details.retentionDays；缺 details 時不編造天數", () => {
    const err = new ApiError({
      status: 409,
      message: "已逾保留期",
      reason: REASONS.RESTORE_WINDOW_EXPIRED,
      details: { projectId: "p1", deletedAt: "2026-09-01T00:00:00Z", retentionDays: 30 },
    });
    expect(describeRestoreError(err)).toBe("這個專案刪除已超過保留期（30 天），無法復原。");
    expect(describeRestoreError(new ApiError({ status: 409, message: "x", reason: REASONS.RESTORE_WINDOW_EXPIRED }))).toBe("這個專案刪除已超過保留期，無法復原。");
  });

  it("404：不存在或已被清除；其他錯誤（403、網路）照 describeError", () => {
    expect(describeRestoreError(new ApiError({ status: 404, message: "專案不存在或已清除：x", traceId: "tr-4" }))).toBe("找不到這個專案：它可能已被永久清除，無法復原。（traceId：tr-4）");
    expect(describeRestoreError(new ApiError({ status: 403, message: "權限不足", reason: REASONS.ACCESS_DENIED }))).toBe("權限不足：ACCESS_DENIED");
    expect(describeRestoreError(new Error("boom"))).toBe("boom");
  });
});

describe("刪除目標／任務失敗的原因（C-8；契約 §1.6.3）", () => {
  it("409 project_executing：顯示白話原因與下一步（含 traceId），不是只丟英文識別字", () => {
    const err = new ApiError({
      status: 409,
      message: "專案有進行中批次",
      reason: REASONS.PROJECT_EXECUTING,
      details: { projectId: "p1", runId: "r1" },
      traceId: "tr-9",
    });
    const text = describeDeleteError(err);
    expect(text).toContain("專案目前有進行中的執行批次");
    expect(text).toContain("到執行頁取消批次後再刪除");
    expect(text).toContain("（traceId：tr-9）");
    expect(text).not.toContain("project_executing");
  });

  it("其他錯誤照 describeError：既有的 409「RUNNING 狀態的任務不可刪除」、404、網路錯誤", () => {
    const running = new ApiError({ status: 409, message: "任務執行中", reason: REASONS.TASK_RUNNING_NOT_DELETABLE, traceId: "tr-1" });
    expect(describeDeleteError(running)).toBe("任務執行中：RUNNING 狀態的任務不可刪除（traceId：tr-1）");
    expect(describeDeleteError(new Error("boom"))).toBe("boom");
  });
});
