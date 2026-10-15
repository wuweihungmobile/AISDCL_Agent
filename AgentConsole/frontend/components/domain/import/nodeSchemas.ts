/**
 * 步驟 2 節點編輯對話框的欄位驗證（zod，錯誤訊息繁中）。
 * 規則與 Phase 2 的建立／編輯表單一致（共用 ABSOLUTE_PATH、COMMAND_DENY）；有界閘（步驟數、無環、prompt 長度）
 * 仍由後端在儲存時把關，這裡只擋「欄位本身不合法」的輸入，更早給回饋。
 */
import { z } from "zod";

import { ABSOLUTE_PATH, COMMAND_DENY } from "@/components/domain/entity/schemas";

const required = (label: string) => z.string().trim().min(1, `${label}不能為空`);

export const projectNodeSchema = z.object({
  name: required("專案名稱").max(200, "名稱最多 200 個字元"),
  executionPath: required("執行路徑")
    .max(500, "執行路徑最多 500 個字元")
    .regex(ABSOLUTE_PATH, "執行路徑必須是絕對路徑（POSIX 以 / 開頭，或 Windows 磁碟機代號／UNC 開頭）"),
  description: z.string(),
  passCriteria: required("通過標準"),
  autonomyLevel: z
    .number({ error: "請輸入 1～10 的整數" })
    .int("自治等級必須是整數")
    .min(1, "自治等級最小為 1")
    .max(10, "自治等級最大為 10"),
});
export type ProjectNodeValues = z.infer<typeof projectNodeSchema>;

export const goalNodeSchema = z.object({
  name: required("目標名稱").max(200, "名稱最多 200 個字元"),
  description: z.string(),
  passCriteria: required("通過標準"),
  dependsOn: z.array(z.string()),
});
export type GoalNodeValues = z.infer<typeof goalNodeSchema>;

/** 任務的最大重試次數上限 20（契約 §0.8 第 2 項：Bridge 的 PlaybookIn 上限）；空白＝不指定（用專案預設）。 */
export const MAX_RETRIES_LIMIT = 20;

export const taskNodeSchema = z.object({
  name: required("任務名稱").max(200, "名稱最多 200 個字元"),
  // 描述是送給 Agent 的 prompt：空白會被後端的 empty_prompt 閘擋下，所以這裡也必填
  description: required("任務說明"),
  passCriteria: required("通過標準"),
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
  maxRetries: z
    .string()
    .refine(
      (v) => v.trim() === "" || (/^\d+$/.test(v.trim()) && Number(v.trim()) <= MAX_RETRIES_LIMIT),
      `最大重試次數需為 0～${MAX_RETRIES_LIMIT} 的整數（空白＝沿用預設）`,
    ),
});
export type TaskNodeValues = z.infer<typeof taskNodeSchema>;

/** maxRetries 欄位（字串）→ 契約的數字；空白為 undefined。 */
export function parseMaxRetries(value: string): number | undefined {
  const v = value.trim();
  return v === "" ? undefined : Number(v);
}
