import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import { applyServerErrors } from "./apiErrors";

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
    expect(applyServerErrors(conflict, setError, ["name"])).toBe(
      "專案執行中，不可變更執行路徑（狀態衝突）（traceId：tr-1）",
    );
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
    applyServerErrors(err, setError, ["dependsOn"], (field, _m, e) =>
      field === "dependsOn" ? `${e.reason}：甲 → 乙 → 甲` : _m,
    );
    expect(setError).toHaveBeenCalledWith("dependsOn", { type: "server", message: "依賴成環：甲 → 乙 → 甲" });
  });
});
