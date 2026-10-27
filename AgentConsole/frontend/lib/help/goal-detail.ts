import type { PageHelp } from "./types";

/**
 * 目標詳情（`/projects/[projectId]/goals/[goalId]`）的說明（TCS-PageHelp-20261027；PRD §4）：輪 2 寫實，自 registry.ts 的 PENDING_HELP_PAGES 移進 HELP_PAGES。
 * 固定頁名「目標詳情」：畫面標題是目標名稱（動態），說明標題不帶它（PRD §8.1）。
 * 狀態段兩張表：目標狀態（標題旁的狀態）、任務狀態（任務清單每一列，與任務詳情、任務列表共用同一份釋義）。
 * 欄位名是畫面字樣的逐字引用（出處鎖會到 sourceFiles 找它）；兩個字的欄位名（所屬、進度、審批、重試、詳情）免掃，由 SCG-4 人讀把關。
 */
export const goalDetail: PageHelp = {
  id: "goal-detail",
  title: "目標詳情",
  purpose: ["這一頁是單一目標的詳情，顯示它的狀態、進度、前置依賴、說明與通過標準。", "目標底下的任務也列在這裡，您可以新增任務，也可以編輯或刪除這個目標。"],
  steps: [
    "先看標題旁的狀態，以及下方的進度與前置依賴。",
    "前置依賴是要先完成的其他目標，按名稱可以跳過去看它。",
    "若出現「草案未審批」橫幅，按「審批」，目標審批後才可以執行。",
    "在「目標說明」與「通過標準」確認這個目標要做什麼、怎樣算做完。",
    "在「任務清單」按任務名稱或「詳情」，查看單一任務。",
    "按「新增任務」建立任務，按「編輯目標」修改這個目標。",
    "按「刪除目標」會先跳出確認視窗，含執行中任務時無法刪除。",
  ],
  fields: [
    { name: "所屬", meaning: "這個目標屬於哪個專案，按名稱可以回到該專案。", source: "系統自動產生" },
    { name: "進度", meaning: "已完成的任務數、全部的任務數與完成的百分比。", source: "系統自動產生" },
    { name: "前置依賴", meaning: "要先完成的其他目標，沒有時顯示「無」。已完成的目標名稱旁會有勾號。", source: "您填寫或選擇", sourceNote: "建立或編輯目標時設定" },
    { name: "草案未審批", meaning: "目標還沒有人審批時出現的橫幅。審批前不能執行，後端也會擋下。", source: "系統自動產生" },
    { name: "審批", meaning: "橫幅上的按鈕，確認後會記下審批者與時間。唯讀的角色不能按。", source: "您填寫或選擇" },
    { name: "目標說明", meaning: "目標的背景與概述，用 Markdown 排版顯示。還沒寫時顯示「尚未填寫目標說明」。", source: "您填寫或選擇", sourceNote: "建立或編輯目標時設定" },
    { name: "通過標準", meaning: "說明這個目標怎樣算做完，用 Markdown 排版顯示。", source: "您填寫或選擇", sourceNote: "建立或編輯目標時設定" },
    { name: "任務清單", meaning: "這個目標底下的全部任務，標題旁的數字是任務個數。每一列有狀態、重試次數與「詳情」。", source: "系統自動產生" },
    { name: "新增任務", meaning: "開啟建立任務的視窗，唯讀的角色不能按。", source: "您填寫或選擇" },
    { name: "重試", meaning: "已重試的次數，與引擎最多自動重試的次數，例如 1 / 3。", source: "執行引擎回報" },
    { name: "詳情", meaning: "進入這個任務的詳情頁。", source: "您填寫或選擇" },
    { name: "編輯目標", meaning: "開啟編輯視窗修改這個目標，唯讀的角色不能按。", source: "您填寫或選擇" },
    { name: "刪除目標", meaning: "會先跳出確認視窗，確認後目標底下的任務會一併刪除。含執行中任務，或專案有進行中的批次時無法刪除。", source: "您填寫或選擇" },
  ],
  states: [{ table: "goalStatus" }, { table: "taskStatus" }],
  sourceFiles: ["components/domain/views/GoalDetailView.tsx", "components/domain/TaskListCard.tsx", "components/domain/SignoffBanner.tsx"],
};
