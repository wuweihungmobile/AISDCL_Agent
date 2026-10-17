/**
 * 核准凍結與編輯 FSM 專案的表單模型（契約 §1.10.2、§1.10.7、§4.7.1；整合輪 115，UI-SDD-01）。純函式、不依賴 React。
 * 前端只做「格式檢查」（早一步給回饋、不得送出）：是否含 TCS、檔案是否存在、摘要是否相符一律由 Bridge 判定，錯誤原樣顯示（sddErrors.ts）。
 * approver 不由畫面指定（一律取 JWT subject，請求內沒有這欄）；請求沒有 `binding` 欄；v1.5 的畫面不送 `expectedDigests`。
 */
import type { SddFreezeRequest } from "@/lib/api/types";

/** 理由：去前後空白後 1～500 字元，不含控制字元（含換行）；不靜默截斷、不替換（契約 §1.10.2）。長度以 UTF-16 單位計（與後端 Bean Validation 同口徑）。 */
export const FREEZE_REASON_MAX = 500;
/** 要凍結的規格文件：1～20 項（契約 §1.10.2）。 */
export const FREEZE_DOCS_MAX = 20;
/** 階段名（選填）：`^[A-Za-z0-9._-]{1,64}$`；省略時 Bridge 用 `Stage-<n>`（階段名不要求唯一）。 */
export const FREEZE_STAGE_PATTERN = /^[A-Za-z0-9._-]{1,64}$/;
/** 編輯 FSM 專案：非空時去前後空白後 1～100 字元、不含控制字元（契約 §1.10.7）。 */
export const SDD_PROJECT_MAX = 100;

const CONTROL_CHARS = /[\u0000-\u001f\u007f]/;

/** 多行輸入切成清單：一行一個路徑、去前後空白、忽略空行。 */
export function parseDocsInput(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line !== "");
}

/**
 * 單一路徑的格式檢查：必須是相對專案根的 POSIX 路徑——不得為絕對路徑（`/`、`\`、磁碟機代號開頭）、不得含 `..` 段、不得用反斜線分隔、不含控制字元。
 * 通過回 null；否則回說明（含該路徑）。是否含 TCS、檔案是否存在由 Bridge 判定。
 */
export function docPathProblem(docPath: string): string | null {
  if (docPath.startsWith("/") || docPath.startsWith("\\") || /^[A-Za-z]:/.test(docPath)) return `「${docPath}」必須是相對專案根的路徑（不得以 / 或磁碟機代號開頭）`;
  if (docPath.split(/[\\/]/).some((segment) => segment === "..")) return `「${docPath}」不得含 ..`;
  if (docPath.includes("\\")) return `「${docPath}」請用 / 分隔（POSIX 路徑）`;
  if (CONTROL_CHARS.test(docPath)) return `「${docPath}」含控制字元`;
  return null;
}

const toSlashes = (p: string): string => p.replace(/\\/g, "/").replace(/\/+$/, "");
/** Windows 路徑（磁碟機代號或 UNC）不分大小寫；POSIX 路徑分大小寫。 */
const isWindowsPath = (p: string): boolean => /^[A-Za-z]:/.test(p) || p.startsWith("\\\\") || p.startsWith("//");

/**
 * 專案已有規格檔（`sddSpecFile`，絕對路徑）時，預填「要凍結的規格文件」＝它換算成相對 executionPath 的 POSIX 路徑（契約 §4.7.1）。
 * 規格檔不在專案根之下（或缺值）回 null——預填留空，使用者自己填；後端對「docs 不含已綁定規格檔」回 400（欄位 docs）。
 */
export function relativeSpecDoc(sddSpecFile: string | null | undefined, executionPath: string): string | null {
  if (!sddSpecFile || sddSpecFile.trim() === "") return null;
  const base = toSlashes(executionPath);
  const file = toSlashes(sddSpecFile);
  if (base === "" || file.length <= base.length + 1) return null;
  const fold = isWindowsPath(executionPath) || isWindowsPath(sddSpecFile);
  const prefix = file.slice(0, base.length + 1);
  const wanted = `${base}/`;
  if (fold ? prefix.toLowerCase() !== wanted.toLowerCase() : prefix !== wanted) return null;
  const rest = file.slice(base.length + 1);
  return docPathProblem(rest) === null ? rest : null;
}

export type FreezeFormErrors = { reason?: string; docs?: string; stage?: string };

export type FreezeFormInput = { reason: string; docsText: string; stage?: string };

export type FreezeFormResult = { ok: true; request: SddFreezeRequest } | { ok: false; errors: FreezeFormErrors };

/**
 * 核准凍結表單檢查（契約 §4.7.1）：理由必填、docs 1～20 行且各行格式合格、不重複、階段名（有填時）符合格式。
 * 合格回請求本文（`reason` 去前後空白、`docs` 去重前已確認無重複、`stage` 空白不送）；不合格回逐欄錯誤，一律不得送出。
 */
export function validateFreezeForm(input: FreezeFormInput): FreezeFormResult {
  const errors: FreezeFormErrors = {};

  const reason = input.reason.trim();
  if (reason === "") errors.reason = "請填寫核准理由";
  else if (reason.length > FREEZE_REASON_MAX) errors.reason = `理由最多 ${FREEZE_REASON_MAX} 字元（目前 ${reason.length}）`;
  else if (CONTROL_CHARS.test(reason)) errors.reason = "理由不得含換行或控制字元";

  const docs = parseDocsInput(input.docsText);
  if (docs.length === 0) errors.docs = "請至少填寫一份規格文件（每行一個相對專案根的路徑）";
  else if (docs.length > FREEZE_DOCS_MAX) errors.docs = `最多 ${FREEZE_DOCS_MAX} 份規格文件（目前 ${docs.length} 份）`;
  else {
    const problems = docs.map(docPathProblem).filter((p): p is string => p !== null);
    const duplicates = docs.filter((d, i) => docs.indexOf(d) !== i);
    if (duplicates.length > 0) problems.push(`有重複的路徑：${[...new Set(duplicates)].join("、")}`);
    if (problems.length > 0) errors.docs = problems.join("；");
  }

  const stage = (input.stage ?? "").trim();
  if (stage !== "" && !FREEZE_STAGE_PATTERN.test(stage)) errors.stage = "階段名稱只能含英數字與 . _ -（1～64 字元）";

  if (Object.keys(errors).length > 0) return { ok: false, errors };
  return { ok: true, request: { reason, docs, ...(stage !== "" ? { stage } : {}) } };
}

export type SddProjectInputResult = { ok: true; value: string | null } | { ok: false; error: string };

/**
 * 「編輯 SDD 專案」輸入檢查（契約 §1.10.7）：留白＝清除（`null`，回到「用預設」＝專案名）；有值則去前後空白後 1～100 字元、不含控制字元。
 * 值交給 Bridge 淨化後生效（自由輸入、Console 不淨化，也不檢查 Windows 禁用字元）。
 */
export function validateSddProjectInput(text: string): SddProjectInputResult {
  const value = text.trim();
  if (value === "") return { ok: true, value: null };
  if (value.length > SDD_PROJECT_MAX) return { ok: false, error: `最多 ${SDD_PROJECT_MAX} 字元（目前 ${value.length}）` };
  if (CONTROL_CHARS.test(value)) return { ok: false, error: "不得含換行或控制字元" };
  return { ok: true, value };
}
