/**
 * 匯入來源的前端預檢（契約 §1.1.1、§1.1.2）。只為「更早給回饋」：後端才是權威（副檔名、魔術位元組、大小、
 * 文字擷取都會再驗一次），這裡的訊息一律取自契約附錄 B 的逐字 reason，伺服器回應的 reason 與它同字。
 */
import { REASONS } from "@/lib/api/reasons";

/** 檔案上限：10MB＝10,485,760 bytes（契約 §1.1.1） */
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
export const ALLOWED_EXTENSIONS = [".md", ".pdf", ".docx"] as const;
/** 貼上文字上限：2,000,000 字元（契約 §1.1.2） */
export const MAX_TEXT_CHARS = 2_000_000;
/** 補充說明上限：4,000 字元（契約 §1.1.3 ParseOptions.additionalPrompt） */
export const MAX_ADDITIONAL_PROMPT_CHARS = 4_000;

/** 檔案預檢：通過回 null，否則回契約的 reason 字串（副檔名不分大小寫）。 */
export function validateSourceFile(file: { name: string; size: number }): string | null {
  const lower = file.name.toLowerCase();
  if (!ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext))) return REASONS.IMPORT_UNSUPPORTED_EXTENSION;
  if (file.size === 0) return REASONS.IMPORT_EMPTY_FILE;
  if (file.size > MAX_UPLOAD_BYTES) return REASONS.IMPORT_FILE_TOO_LARGE;
  return null;
}

/** 執行路徑欄位的提示（Architecture §12.1 L-8：本機與 Docker 全棧的寫法不同）。 */
export const EXECUTION_PATH_HINT =
  "本機開發填主機路徑（Windows 例：C:\\Projects\\my-service；macOS／Linux 例：/home/user/projects/my-service）；" +
  "Docker 全棧填 Bridge 容器內的路徑（預設在 /workspace/ 之下，例：/workspace/my-service），" +
  "要改主機目錄須另行 bind mount，並加入 BRIDGE_ALLOWED_PATH_ROOTS。";
