import type { PageHelp } from "./types";

/**
 * 任務表單（`/projects/[projectId]/goals/[goalId]/tasks/new`、`…/tasks/[taskId]/edit`）的說明（TCS-PageHelp-20261027；PRD §4、AC-PH-05-7）：輪 2 寫實，自 registry.ts 的 PENDING_HELP_PAGES 移進 HELP_PAGES。
 * 新建與編輯共用 EntityFormPage 與同一張 TaskForm；沒有會變動的狀態，登記在 NO_STATE_PAGES。
 * 表單欄位清單鎖（AC-PH-05-7，help.static.test.ts）：本頁的欄位名必須涵蓋 EntityForms.tsx 的 TaskForm 裡每個 Field 與 MarkdownField 的 label——
 * 表單新增欄位而這裡沒補，`npx vitest run` 轉紅。欄位名是畫面字樣的逐字引用（出處鎖會到 sourceFiles 找它）；兩個字的欄位名（建立、取消）免掃。
 * 驗證命令的禁用字元是安全規則（schemas.ts 的 COMMAND_DENY），說明用白話概括、不逐一列出符號：lint 不允許反引號。數字寫成中文（二百）：lint 不允許連續三位以上的半形數字。
 */
export const taskForm: PageHelp = {
  id: "task-form",
  title: "任務表單",
  purpose: ["這一頁用來新建任務，或修改既有任務的設定。", "任務屬於目標，送出後會前往任務詳情頁。"],
  steps: [
    "填寫「任務名稱」，必填，最多二百個字元。",
    "在「說明描述」寫任務要做什麼，選填，可以用 Markdown 排版。",
    "在「通過標準」寫清楚怎樣算通過，必填。",
    "在「最大重試次數」填失敗後最多自動重試幾次，預設是 3。",
    "需要自動檢查結果時，在「驗證命令」填命令，選填。",
    "需要檢查命令輸出時，在「期望輸出 Regex」填樣式，選填。",
    "按「建立」或「儲存」送出，欄位有錯會顯示在該欄下方。",
    "不想存的話按「取消」，回到上一頁。",
  ],
  fields: [
    { name: "任務名稱", meaning: "任務的名稱，必填，最多二百個字元。", source: "您填寫或選擇" },
    { name: "說明描述", meaning: "任務要做什麼，選填，可以用 Markdown 排版。寫得越清楚，引擎越知道該怎麼做。", source: "您填寫或選擇" },
    { name: "通過標準", meaning: "說明這個任務怎樣算通過，必填，可以用 Markdown 寫成條列。", source: "您填寫或選擇" },
    { name: "最大重試次數", meaning: "任務失敗後，引擎最多自動重試幾次，要填零以上的整數，新建時預設是 3。手動重試不受這個上限限制。", source: "您填寫或選擇" },
    { name: "驗證命令", meaning: "任務做完後，用來檢查結果的命令，選填。為了安全，命令不能含有會串接、轉向或代換的特殊符號，也不能換行。", source: "您填寫或選擇" },
    { name: "期望輸出 Regex", meaning: "驗證命令的輸出要符合的樣式，選填，要寫成合法的正規表示式。寫法不合法時，儲存會被擋下。", source: "您填寫或選擇" },
    { name: "建立", meaning: "新建任務時的送出鈕，編輯時改叫「儲存」。成功後會前往任務詳情頁。", source: "您填寫或選擇" },
    { name: "取消", meaning: "放棄這次的填寫，回到上一頁。", source: "您填寫或選擇" },
  ],
  states: [],
  sourceFiles: ["components/domain/entity/EntityForms.tsx", "components/domain/entity/EntityFormPage.tsx", "components/domain/entity/schemas.ts"],
};
