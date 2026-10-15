/**
 * 建立／編輯表單的驗證與請求轉換（zod，錯誤訊息一律繁中）。
 * 前端驗證只為「更早給回饋」；後端才是權威（Bean Validation＋NFR-SEC-03 消毒），
 * 後端 400 的 errors[] 會由 apiErrors.ts 對應回欄位。
 */
import { z } from "zod";

import type { CreateGoalRequest, CreateProjectRequest, CreateTaskRequest, UpdateGoalRequest, UpdateProjectRequest, UpdateTaskRequest } from "@/lib/api/types";

/** NFR-SEC-03：evaluatorCommand 禁用字元（SSOT 在後端 BASE_DENY_CHARS；這裡只為即時回饋，後端仍會二次校驗） */
export const COMMAND_DENY = /[!`><~$&;\u0000-\u001f\u007f]/;

/** 絕對路徑：POSIX 以 / 開頭，或 Windows 磁碟機代號（C:\ 或 C:/）、UNC（\\server） */
export const ABSOLUTE_PATH = /^(\/|[A-Za-z]:[\\/]|\\\\)/;

const name = z.string().trim().min(1, "名稱不能為空").max(200, "名稱最多 200 個字元");
const description = z.string();
const passCriteria = z.string().trim().min(1, "通過標準不能為空");

export const projectSchema = z.object({
  name,
  executionPath: z.string().trim().min(1, "執行路徑不能為空").max(500, "執行路徑最多 500 個字元").regex(ABSOLUTE_PATH, "執行路徑必須是絕對路徑（POSIX 以 / 開頭，或 Windows 磁碟機代號／UNC 開頭）"),
  description,
  passCriteria,
  autonomyLevel: z.number({ error: "請輸入 1～10 的整數" }).int("自治等級必須是整數").min(1, "自治等級最小為 1").max(10, "自治等級最大為 10"),
});
export type ProjectFormValues = z.infer<typeof projectSchema>;

export const goalSchema = z.object({
  name,
  description,
  passCriteria,
  dependsOn: z.array(z.string()),
});
export type GoalFormValues = z.infer<typeof goalSchema>;

export const taskSchema = z.object({
  name,
  description,
  passCriteria,
  maxRetries: z.number({ error: "請輸入 0 以上的整數" }).int("最大重試次數必須是整數").min(0, "最大重試次數不可為負數"),
  evaluatorCommand: z
    .string()
    .max(1000, "驗證命令最多 1000 個字元")
    .refine((v) => !COMMAND_DENY.test(v), "不可包含 ! ` > < ~ $ & ; 或換行等控制字元（NFR-SEC-03）"),
  expectedOutputRegex: z
    .string()
    .max(1000, "最多 1000 個字元")
    .refine((v) => {
      if (!v) return true;
      try {
        new RegExp(v);
        return true;
      } catch {
        return false;
      }
    }, "不是合法的正規表示式"),
});
export type TaskFormValues = z.infer<typeof taskSchema>;

export const PROJECT_DEFAULTS: ProjectFormValues = {
  name: "",
  executionPath: "",
  description: "",
  passCriteria: "",
  autonomyLevel: 3,
};
export const GOAL_DEFAULTS: GoalFormValues = { name: "", description: "", passCriteria: "", dependsOn: [] };
export const TASK_DEFAULTS: TaskFormValues = {
  name: "",
  description: "",
  passCriteria: "",
  maxRetries: 3,
  evaluatorCommand: "",
  expectedOutputRegex: "",
};

const blankToUndefined = (v: string): string | undefined => (v.trim() === "" ? undefined : v);

// ── 建立：空的選填欄位不送 ──────────────────────────────────────────────
export const toCreateProject = (v: ProjectFormValues): CreateProjectRequest => ({
  name: v.name,
  executionPath: v.executionPath,
  passCriteria: v.passCriteria,
  description: blankToUndefined(v.description),
  autonomyLevel: v.autonomyLevel,
});
export const toCreateGoal = (v: GoalFormValues): CreateGoalRequest => ({
  name: v.name,
  description: blankToUndefined(v.description),
  passCriteria: v.passCriteria,
  dependsOn: v.dependsOn,
});
export const toCreateTask = (v: TaskFormValues): CreateTaskRequest => ({
  name: v.name,
  description: blankToUndefined(v.description),
  passCriteria: v.passCriteria,
  maxRetries: v.maxRetries,
  evaluatorCommand: blankToUndefined(v.evaluatorCommand),
  expectedOutputRegex: blankToUndefined(v.expectedOutputRegex),
});

// ── 更新：後端 PUT 只改有帶的欄位，空字串＝清除選填欄位，所以整組送出 ───────────────
export const toUpdateProject = (v: ProjectFormValues, locked: boolean): UpdateProjectRequest =>
  locked
    ? { name: v.name, description: v.description }
    : {
        name: v.name,
        executionPath: v.executionPath,
        passCriteria: v.passCriteria,
        description: v.description,
        autonomyLevel: v.autonomyLevel,
      };
export const toUpdateGoal = (v: GoalFormValues): UpdateGoalRequest => ({
  name: v.name,
  description: v.description,
  passCriteria: v.passCriteria,
  dependsOn: v.dependsOn,
});
export const toUpdateTask = (v: TaskFormValues): UpdateTaskRequest => ({
  name: v.name,
  description: v.description,
  passCriteria: v.passCriteria,
  maxRetries: v.maxRetries,
  evaluatorCommand: v.evaluatorCommand,
  expectedOutputRegex: v.expectedOutputRegex,
});
