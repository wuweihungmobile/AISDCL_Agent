import type { PageHelp } from "./types";

/**
 * 任務列表（`/projects/[projectId]/goals/[goalId]/tasks`）的說明（TCS-PageHelp-20261027；PRD §4）：輪 2 寫實，自 registry.ts 的 PENDING_HELP_PAGES 移進 HELP_PAGES。
 * 這一頁與目標詳情共用 TaskListCard（任務清單卡），每一列的狀態點與文字是任務狀態（名稱取自 TASK_STATUS）。
 * 欄位名是畫面字樣的逐字引用（出處鎖會到 sourceFiles 找它）：頁首的「所屬目標」「返回目標」來自 ListPages.tsx，其餘來自 TaskListCard.tsx；兩個字的欄位名（重試、詳情）免掃。
 */
export const tasks: PageHelp = {
  id: "tasks",
  title: "任務列表",
  purpose: ["這一頁列出某個目標底下的全部任務，並顯示各任務的狀態與重試次數。", "您可以在這裡新增任務，再進入任務看詳情。"],
  steps: [
    "先看頁首的「所屬目標」，確認您看的是哪個目標的任務。",
    "每一列的圓點與文字是任務的狀態，後面的「重試」是已重試次數與上限。",
    "按任務名稱或「詳情」，進入該任務看說明、日誌與執行歷史。",
    "按右上的「新增任務」，建立新的任務，唯讀的角色不能使用。",
    "按「返回目標」，回到這個目標的詳情頁。",
  ],
  fields: [
    { name: "所屬目標", meaning: "頁首小字，寫明這些任務屬於哪個目標。", source: "系統自動產生" },
    { name: "任務清單", meaning: "這個目標底下的全部任務，標題旁的數字是任務個數。", source: "系統自動產生" },
    { name: "重試", meaning: "已重試的次數，與引擎最多自動重試的次數，例如 1 / 3。", source: "執行引擎回報" },
    { name: "詳情", meaning: "進入這個任務的詳情頁。", source: "您填寫或選擇" },
    { name: "新增任務", meaning: "開啟建立任務的視窗，唯讀的角色不能按。", source: "您填寫或選擇" },
    { name: "返回目標", meaning: "回到這個目標的詳情頁。", source: "您填寫或選擇" },
  ],
  states: [{ table: "taskStatus" }],
  sourceFiles: ["components/domain/views/ListPages.tsx", "components/domain/TaskListCard.tsx"],
};
