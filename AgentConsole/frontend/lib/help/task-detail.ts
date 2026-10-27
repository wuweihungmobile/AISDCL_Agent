import type { PageHelp } from "./types";

/**
 * 任務詳情（`/projects/[projectId]/goals/[goalId]/tasks/[taskId]`）的說明（TCS-PageHelp-20261027；PRD §4）：輪 2 寫實，自 registry.ts 的 PENDING_HELP_PAGES 移進 HELP_PAGES。
 * 固定頁名「任務詳情」：畫面標題是任務名稱（動態），說明標題不帶它（PRD §8.1）。
 * 狀態段兩張表：任務狀態（標題旁，名稱取自 TASK_STATUS）、執行步驟事件（「執行歷史」直接印原值 STARTED、COMPLETED、FAILED、RETRYING，不經 STEP_STATUS，
 * 所以登記為 `raw` 模式，欄標題會寫「畫面上的原值」，PRD §4 發現 6）。
 * 欄位名是畫面字樣的逐字引用（出處鎖會到 sourceFiles 找它）：頁面本體在 TaskDetailView.tsx，日誌面板在 LogPanel.tsx，草案橫幅在 SignoffBanner.tsx；
 * 兩個字的欄位名（審批、重試、編輯、刪除）免掃，由 SCG-4 人讀把關。
 */
export const taskDetail: PageHelp = {
  id: "task-detail",
  title: "任務詳情",
  purpose: ["這一頁是單一任務的詳情，顯示它的狀態、重試次數、說明、通過標準與執行日誌。", "您可以在這裡重試失敗的任務，也可以編輯或刪除它。"],
  steps: [
    "先看標題旁的任務狀態，以及下方小字的重試次數與負責的 Agent。",
    "若出現「草案未審批」橫幅，按「審批」，任務審批後才可以執行。",
    "看三張指標卡，了解開始時間、Token 消耗與重試次數。",
    "在「任務說明」與「通過標準」確認這個任務要做什麼、怎樣算通過。",
    "在「執行日誌」讀引擎留下的紀錄，可以用搜尋框篩出關鍵字。",
    "在「執行歷史」看引擎每個步驟的結果，狀態詞是原文。",
    "任務失敗或待人工時，按「重試」重新排入佇列。",
    "按「編輯」修改任務，按「刪除」移除任務。",
  ],
  fields: [
    { name: "Agent", meaning: "負責這個任務的 Agent 名稱，還沒有指派時顯示「—」。", source: "執行引擎回報" },
    { name: "草案未審批", meaning: "任務還沒有人審批時出現的橫幅。審批前不能執行，後端也會擋下。", source: "系統自動產生" },
    { name: "審批", meaning: "橫幅上的按鈕，確認後會記下審批者與時間。唯讀的角色不能按。", source: "您填寫或選擇" },
    { name: "開始時間", meaning: "任務開始執行的時間點，只顯示時分秒。還沒開始時顯示「—」。", source: "執行引擎回報" },
    { name: "Token 消耗", meaning: "這個任務實際用掉的 Token 數量。還沒有紀錄時顯示「—」。", source: "執行引擎回報" },
    { name: "重試次數", meaning: "左邊是已重試的次數，右邊是引擎最多自動重試的次數。手動重試不受右邊上限限制，所以左邊可能比右邊大。", source: "執行引擎回報" },
    { name: "任務說明", meaning: "任務要做什麼，用 Markdown 排版顯示。還沒寫時顯示「尚未填寫任務說明」。", source: "您填寫或選擇", sourceNote: "建立或編輯任務時設定" },
    { name: "通過標準", meaning: "說明這個任務怎樣算通過，用 Markdown 排版顯示。", source: "您填寫或選擇", sourceNote: "建立或編輯任務時設定" },
    { name: "驗證命令", meaning: "任務做完後，用來檢查結果的命令。只有設定過才會顯示。", source: "您填寫或選擇", sourceNote: "建立或編輯任務時設定" },
    { name: "期望輸出 Regex", meaning: "驗證命令的輸出必須符合的樣式。只有設定過才會顯示。", source: "您填寫或選擇", sourceNote: "建立或編輯任務時設定" },
    { name: "執行日誌", meaning: "引擎最近一次執行這個任務留下的日誌，內容多時可以捲動。還沒執行過時會寫明尚無日誌。", source: "執行引擎回報" },
    { name: "搜尋日誌", meaning: "輸入關鍵字，只留下含有它的日誌行，不分大小寫。旁邊會顯示符合的行數與全部的行數。", source: "您填寫或選擇" },
    {
      name: "執行歷史",
      meaning: "引擎每做一個步驟就記一筆，每筆有步驟編號、動作、步驟狀態、Token 數與時間。步驟狀態直接印原文，意思見下方的原值表。",
      source: "執行引擎回報",
      sourceNote: "跨批次，最多列最近二百筆",
    },
    { name: "重試", meaning: "把失敗或待人工的任務重新排入佇列，其他狀態的任務按不了。唯讀的角色也不能按。", source: "您填寫或選擇" },
    { name: "編輯", meaning: "開啟編輯視窗修改這個任務，唯讀的角色不能按。", source: "您填寫或選擇" },
    { name: "刪除", meaning: "會先跳出確認視窗。執行中的任務不能直接刪除，專案有進行中的批次時也不行。", source: "您填寫或選擇" },
  ],
  states: [{ table: "taskStatus" }, { table: "stepStatus", name: "raw" }],
  sourceFiles: ["components/domain/views/TaskDetailView.tsx", "components/domain/LogPanel.tsx", "components/domain/SignoffBanner.tsx"],
};
