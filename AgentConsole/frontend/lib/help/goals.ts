import type { PageHelp } from "./types";

/**
 * 目標列表（`/projects/[projectId]/goals`）的說明（TCS-PageHelp-20261027；PRD §4）：輪 2 寫實，自 registry.ts 的 PENDING_HELP_PAGES 移進 HELP_PAGES。
 * 這一頁與專案詳情共用 GoalListCard（目標清單卡），欄位與狀態取自它：每一列的狀態點與文字是目標狀態（名稱取自 GOAL_STATUS）。
 * 欄位名是畫面字樣的逐字引用（出處鎖會到 sourceFiles 找它）：頁首的「所屬專案」「返回專案」來自 ListPages.tsx，其餘來自 GoalListCard.tsx；兩個字的欄位名（查看）免掃。
 */
export const goals: PageHelp = {
  id: "goals",
  title: "目標列表",
  purpose: ["這一頁列出某個專案的全部目標，並顯示各目標的狀態與任務完成度。", "您可以在這裡新增目標，也可以拖曳調整目標的先後順序。"],
  steps: [
    "先看頁首的「所屬專案」，確認您看的是哪個專案的目標。",
    "每一列的圓點與文字是目標的狀態，中間的進度條是任務完成度。",
    "按目標名稱或「查看」，進入該目標看它的任務。",
    "按右上的「新增目標」，建立新的目標。",
    "目標超過一個時，拖曳左邊的把手就能調整順序，鍵盤也可以操作。",
    "按「返回專案」，回到這個專案的詳情頁。",
  ],
  fields: [
    { name: "所屬專案", meaning: "頁首小字，寫明這些目標屬於哪個專案。", source: "系統自動產生" },
    { name: "目標清單", meaning: "這個專案的全部目標，標題旁的數字是目標個數。", source: "系統自動產生" },
    { name: "任務完成度", meaning: "每一列的進度條與右邊的數字，是這個目標已完成與全部的任務數。", source: "系統自動產生" },
    { name: "查看", meaning: "進入這個目標的詳情頁。", source: "您填寫或選擇" },
    { name: "新增目標", meaning: "開啟建立目標的視窗，唯讀的角色不能按。", source: "您填寫或選擇" },
    { name: "拖曳排序", meaning: "目標超過一個時，拖曳列首的把手調整先後順序。只有可以修改的角色能排序，失敗時順序會還原。", source: "您填寫或選擇" },
    { name: "返回專案", meaning: "回到這個專案的詳情頁。", source: "您填寫或選擇" },
  ],
  states: [{ table: "goalStatus" }],
  sourceFiles: ["components/domain/views/ListPages.tsx", "components/domain/GoalListCard.tsx"],
};
