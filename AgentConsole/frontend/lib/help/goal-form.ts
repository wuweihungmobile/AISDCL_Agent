import type { PageHelp } from "./types";

/**
 * 目標表單（`/projects/[projectId]/goals/new`、`…/goals/[goalId]/edit`）的說明（TCS-PageHelp-20261027；PRD §4、AC-PH-05-7）：輪 2 寫實，自 registry.ts 的 PENDING_HELP_PAGES 移進 HELP_PAGES。
 * 新建與編輯共用 EntityFormPage 與同一張 GoalForm；「前置依賴」挑選器每一列帶著那個目標的狀態，所以狀態段引用目標狀態表（不在 NO_STATE_PAGES，PRD §4 發現 6）。
 * 表單欄位清單鎖（AC-PH-05-7，help.static.test.ts）：本頁的欄位名必須涵蓋 EntityForms.tsx 的 GoalForm 與 DependsOnField 裡每個 Field 與 MarkdownField 的 label——
 * 表單新增欄位而這裡沒補，`npx vitest run` 轉紅。欄位名是畫面字樣的逐字引用（出處鎖會到 sourceFiles 找它）；兩個字的欄位名（建立、取消）免掃。
 * 數字寫成中文（二百）：lint 規則不允許連續三位以上的半形數字（PRD AC-PH-05-3）。
 */
export const goalForm: PageHelp = {
  id: "goal-form",
  title: "目標表單",
  purpose: ["這一頁用來新建目標，或修改既有目標的設定。", "目標屬於專案，送出後會前往目標詳情頁。"],
  steps: [
    "填寫「目標名稱」，必填，最多二百個字元。",
    "在「說明描述」寫目標的背景，選填，可以用 Markdown 排版。",
    "在「通過標準」寫清楚怎樣算做完，必填。",
    "需要時，在「前置依賴」勾選要先完成的其他目標。",
    "勾選清單每一列旁邊的狀態，是那個目標目前的狀態。",
    "按「建立」或「儲存」送出，欄位有錯會顯示在該欄下方。",
    "依賴關係繞成一圈時，儲存會被擋下，請取消其中一個勾選。",
    "不想存的話按「取消」，回到上一頁。",
  ],
  fields: [
    { name: "目標名稱", meaning: "目標的名稱，必填，最多二百個字元。", source: "您填寫或選擇" },
    { name: "說明描述", meaning: "目標的背景與概述，選填，可以用 Markdown 排版。編輯器有工具列與預覽，也能匯入或匯出 Markdown 檔。", source: "您填寫或選擇" },
    { name: "通過標準", meaning: "說明這個目標怎樣算做完，必填，可以用 Markdown 寫成條列。", source: "您填寫或選擇" },
    {
      name: "前置依賴",
      meaning: "選填，勾選要先完成的其他目標，它們完成後才會輪到這個目標。依賴關係繞成一圈時，儲存會被擋下並顯示原因。",
      source: "您填寫或選擇",
      sourceNote: "清單列出同專案的其他目標",
    },
    { name: "建立", meaning: "新建目標時的送出鈕，編輯時改叫「儲存」。成功後會前往目標詳情頁。", source: "您填寫或選擇" },
    { name: "取消", meaning: "放棄這次的填寫，回到上一頁。", source: "您填寫或選擇" },
  ],
  states: [{ table: "goalStatus" }],
  sourceFiles: ["components/domain/entity/EntityForms.tsx", "components/domain/entity/EntityFormPage.tsx", "components/domain/entity/schemas.ts"],
};
