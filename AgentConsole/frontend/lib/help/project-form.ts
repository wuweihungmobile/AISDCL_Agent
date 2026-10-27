import { SHARED } from "./common";
import type { PageHelp } from "./types";

/**
 * 專案表單（`/projects/new`、`/projects/[projectId]/edit`）的說明（TCS-PageHelp-20261027；PRD §4、AC-PH-05-7）：輪 2 寫實，自 registry.ts 的 PENDING_HELP_PAGES 移進 HELP_PAGES。
 * 新建與編輯共用 EntityFormPage 與同一張 ProjectForm；沒有會變動的狀態，登記在 NO_STATE_PAGES。
 * 表單欄位清單鎖（AC-PH-05-7，help.static.test.ts）：本頁的欄位名必須涵蓋 EntityForms.tsx 的 ProjectForm 裡每個 Field 與 MarkdownField 的 label——
 * 表單新增欄位而這裡沒補，`npx vitest run` 轉紅。欄位名是畫面字樣的逐字引用（出處鎖會到 sourceFiles 找它）；兩個字的欄位名（建立、取消）免掃。
 * 數字寫成中文（二百、五百）：lint 規則不允許連續三位以上的半形數字（PRD AC-PH-05-3）。
 */
export const projectForm: PageHelp = {
  id: "project-form",
  title: "專案表單",
  purpose: ["這一頁用來新建專案，或修改既有專案的設定。", "新建與編輯共用同一張表單，送出後會前往專案詳情頁。"],
  steps: [
    "填寫「專案名稱」，必填，最多二百個字元。",
    "在「執行路徑」填引擎要工作的資料夾，必須是絕對路徑。",
    "在「說明描述」寫專案的背景，選填，可以用 Markdown 排版。",
    "在「通過標準」寫清楚怎樣算做完，必填。",
    "在「自治等級」填一到十的整數，決定引擎要不要停下來等您確認。",
    "按「建立」或「儲存」送出，欄位有錯會顯示在該欄下方。",
    "專案正在執行時，只能修改名稱與說明，其他欄位會被鎖住。",
    "不想存的話按「取消」，回到上一頁。",
  ],
  fields: [
    { name: "專案名稱", meaning: "專案的名稱，必填，最多二百個字元。", source: "您填寫或選擇" },
    { name: "執行路徑", meaning: "引擎執行這個專案時工作的資料夾，必填，要填絕對路徑。路徑的寫法會隨執行環境不同，欄位下方的提示有範例。", source: "您填寫或選擇" },
    { name: "說明描述", meaning: "專案的背景與概述，選填，可以用 Markdown 排版。編輯器有工具列與預覽，也能匯入或匯出 Markdown 檔。", source: "您填寫或選擇" },
    { name: "通過標準", meaning: "說明這個專案怎樣算做完，必填，可以用 Markdown 寫成條列。專案執行中時這一欄會被鎖住。", source: "您填寫或選擇" },
    { ...SHARED.autonomy, sourceNote: "可填 1 到 10 的整數，預設 3" },
    { name: "建立", meaning: "新建專案時的送出鈕，編輯時改叫「儲存」。成功後會前往專案詳情頁。", source: "您填寫或選擇" },
    { name: "取消", meaning: "放棄這次的填寫，回到上一頁。", source: "您填寫或選擇" },
  ],
  states: [],
  sourceFiles: ["components/domain/entity/EntityForms.tsx", "components/domain/entity/EntityFormPage.tsx", "components/domain/entity/schemas.ts"],
};
