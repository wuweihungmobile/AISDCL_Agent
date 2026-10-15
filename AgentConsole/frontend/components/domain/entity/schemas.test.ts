import { describe, expect, it } from "vitest";

import { COMMAND_DENY, goalSchema, projectSchema, taskSchema, toCreateProject, toCreateTask, toUpdateProject, toUpdateTask } from "./schemas";

const project = { name: "P", executionPath: "/home/u/p", description: "", passCriteria: "- ok", autonomyLevel: 3 };
const task = { name: "T", description: "", passCriteria: "- ok", maxRetries: 3, evaluatorCommand: "", expectedOutputRegex: "" };

function firstMessage(result: { success: boolean; error?: { issues: Array<{ message: string }> } }): string | undefined {
  return result.error?.issues[0]?.message;
}

describe("表單驗證（繁中訊息；後端仍是權威）", () => {
  it("名稱不能為空（trim 後）、通過標準不能為空", () => {
    expect(firstMessage(projectSchema.safeParse({ ...project, name: "   " }))).toBe("名稱不能為空");
    expect(firstMessage(goalSchema.safeParse({ name: "G", description: "", passCriteria: " ", dependsOn: [] }))).toBe("通過標準不能為空");
  });

  it.each(["/home/user/p", "C:\\work\\p", "D:/work/p", "\\\\server\\share\\p"])("接受絕對路徑 %s", (p) => {
    expect(projectSchema.safeParse({ ...project, executionPath: p }).success).toBe(true);
  });

  it.each(["relative/path", "./here", "~/home"])("拒絕相對路徑 %s", (p) => {
    const r = projectSchema.safeParse({ ...project, executionPath: p });
    expect(r.success).toBe(false);
    expect(firstMessage(r)).toContain("絕對路徑");
  });

  it("自治等級必須是 1～10 的整數", () => {
    expect(projectSchema.safeParse({ ...project, autonomyLevel: 0 }).success).toBe(false);
    expect(projectSchema.safeParse({ ...project, autonomyLevel: 11 }).success).toBe(false);
    expect(projectSchema.safeParse({ ...project, autonomyLevel: 2.5 }).success).toBe(false);
    expect(projectSchema.safeParse({ ...project, autonomyLevel: Number.NaN }).success).toBe(false);
    expect(projectSchema.safeParse({ ...project, autonomyLevel: 10 }).success).toBe(true);
  });

  it("NFR-SEC-03：驗證命令含禁用字元（! ` > < ~ $ & ; 與控制字元）一律拒絕", () => {
    for (const bad of ["a;b", "a&b", "a>b", "a<b", "a`b`", "a$b", "a~b", "a!b", "a\nb"]) {
      expect(COMMAND_DENY.test(bad), bad).toBe(true);
      expect(taskSchema.safeParse({ ...task, evaluatorCommand: bad }).success, bad).toBe(false);
    }
    expect(taskSchema.safeParse({ ...task, evaluatorCommand: "pytest -q tests/" }).success).toBe(true);
  });

  it("期望輸出 Regex 必須可編譯", () => {
    expect(firstMessage(taskSchema.safeParse({ ...task, expectedOutputRegex: "([a-z" }))).toBe("不是合法的正規表示式");
    expect(taskSchema.safeParse({ ...task, expectedOutputRegex: "^OK$" }).success).toBe(true);
  });

  it("最大重試次數不可為負、必須是整數", () => {
    expect(taskSchema.safeParse({ ...task, maxRetries: -1 }).success).toBe(false);
    expect(taskSchema.safeParse({ ...task, maxRetries: 1.5 }).success).toBe(false);
    expect(taskSchema.safeParse({ ...task, maxRetries: 0 }).success).toBe(true);
  });
});

describe("請求轉換", () => {
  it("建立：空的選填欄位不送出", () => {
    expect(toCreateProject(project)).toEqual({
      name: "P",
      executionPath: "/home/u/p",
      passCriteria: "- ok",
      description: undefined,
      autonomyLevel: 3,
    });
    const t = toCreateTask(task);
    expect(t.evaluatorCommand).toBeUndefined();
    expect(t.expectedOutputRegex).toBeUndefined();
  });

  it("更新：整組送出（空字串＝清除選填欄位）", () => {
    expect(toUpdateTask(task)).toMatchObject({ evaluatorCommand: "", expectedOutputRegex: "", description: "" });
  });

  it("專案 EXECUTING 時只送名稱與說明（其他欄位後端會回 409）", () => {
    expect(toUpdateProject(project, true)).toEqual({ name: "P", description: "" });
    expect(Object.keys(toUpdateProject(project, false)).sort()).toEqual(["autonomyLevel", "description", "executionPath", "name", "passCriteria"].sort());
  });
});
