import { describe, expect, it } from "vitest";

import { MAX_RETRIES_LIMIT, goalNodeSchema, parseMaxRetries, projectNodeSchema, taskNodeSchema } from "./nodeSchemas";

const okTask = { name: "實作", description: "請輸出 [T3_DONE]", passCriteria: "輸出含 [T3_DONE]", evaluatorCommand: "", expectedOutputRegex: "", maxRetries: "" };

const firstMessage = (result: { success: boolean; error?: { issues: Array<{ message: string }> } }) => (result.success ? null : result.error?.issues[0].message);

describe("節點編輯表單驗證", () => {
  it("任務：名稱、說明、通過標準都必填（說明是 prompt，空白會被 empty_prompt 閘擋下）", () => {
    expect(taskNodeSchema.safeParse(okTask).success).toBe(true);
    expect(firstMessage(taskNodeSchema.safeParse({ ...okTask, name: "  " }))).toBe("任務名稱不能為空");
    expect(firstMessage(taskNodeSchema.safeParse({ ...okTask, description: "" }))).toBe("任務說明不能為空");
    expect(firstMessage(taskNodeSchema.safeParse({ ...okTask, passCriteria: " " }))).toBe("通過標準不能為空");
  });

  it("驗證命令：含禁用字元（; ` $ & > < ~ ! 或控制字元）擋下，與 Phase 2 同規則（NFR-SEC-03）", () => {
    for (const bad of ["pytest -q; echo done", "echo `id`", "a && b", "cat < x", "echo $HOME", "ls ~", "wow!", "line1\nline2"]) {
      expect(taskNodeSchema.safeParse({ ...okTask, evaluatorCommand: bad }).success, bad).toBe(false);
    }
    expect(taskNodeSchema.safeParse({ ...okTask, evaluatorCommand: "pytest -q tests/unit" }).success).toBe(true);
  });

  it("期望輸出 regex：無法編譯擋下，空白與合法值通過", () => {
    expect(firstMessage(taskNodeSchema.safeParse({ ...okTask, expectedOutputRegex: "([" }))).toBe("不是合法的正規表示式");
    expect(taskNodeSchema.safeParse({ ...okTask, expectedOutputRegex: "\\[T1_DONE\\]" }).success).toBe(true);
  });

  it(`最大重試次數：空白＝沿用預設；0～${MAX_RETRIES_LIMIT} 整數通過；負數、小數、超過上限擋下`, () => {
    for (const ok of ["", "0", "3", String(MAX_RETRIES_LIMIT)]) {
      expect(taskNodeSchema.safeParse({ ...okTask, maxRetries: ok }).success, ok).toBe(true);
    }
    for (const bad of ["-1", "1.5", String(MAX_RETRIES_LIMIT + 1), "abc"]) {
      expect(taskNodeSchema.safeParse({ ...okTask, maxRetries: bad }).success, bad).toBe(false);
    }
    expect(parseMaxRetries("")).toBeUndefined();
    expect(parseMaxRetries(" 5 ")).toBe(5);
  });

  it("目標：名稱與通過標準必填、說明可空；專案：路徑須為絕對路徑、自治等級 1～10", () => {
    expect(goalNodeSchema.safeParse({ name: "核心", description: "", passCriteria: "c", dependsOn: [] }).success).toBe(true);
    expect(firstMessage(goalNodeSchema.safeParse({ name: "", description: "", passCriteria: "c", dependsOn: [] }))).toBe("目標名稱不能為空");
    const project = { name: "p", executionPath: "/home/u/p", description: "", passCriteria: "c", autonomyLevel: 3 };
    expect(projectNodeSchema.safeParse(project).success).toBe(true);
    expect(projectNodeSchema.safeParse({ ...project, executionPath: "C:\\Projects\\p" }).success).toBe(true);
    expect(projectNodeSchema.safeParse({ ...project, executionPath: "relative/path" }).success).toBe(false);
    expect(projectNodeSchema.safeParse({ ...project, autonomyLevel: 11 }).success).toBe(false);
    expect(projectNodeSchema.safeParse({ ...project, autonomyLevel: 0 }).success).toBe(false);
  });
});
