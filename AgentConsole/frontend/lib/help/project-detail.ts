import { SHARED } from "./common";
import type { PageHelp } from "./types";

/**
 * 專案詳情（`/projects/[projectId]`）的說明（TCS-PageHelp-20261027；PRD §4）：輪 2 寫實，自 registry.ts 的 PENDING_HELP_PAGES 移進 HELP_PAGES。
 * 固定頁名「專案詳情」：畫面標題是專案名稱（動態），說明標題不帶它（PRD §8.1）。
 * 狀態段四張表：專案狀態（標題旁）、目標狀態（目標清單每一列）、SDD 階段（「階段」列，名稱取自階段字典）、SDD 流程原始狀態（「目前狀態」列印原文，`raw` 模式，只解釋據以決策的五個，PRD Q6）。
 * 畫面私有字樣（無匯出常數、不進狀態表）寫在欄位表：階段進度的「已過」「目前」「未到」與標籤「觀測中」「委派 AutoClaude 執行中」（sdd/SddPhaseProgress.tsx）。
 * 欄位名是畫面字樣的逐字引用（出處鎖會到 sourceFiles 找它）；兩個字的欄位名（目標、任務、更新）免掃，由 SCG-4 人讀把關。
 */
export const projectDetail: PageHelp = {
  id: "project-detail",
  title: "專案詳情",
  purpose: ["這一頁是單一專案的總覽，集中顯示它的狀態、基本資訊、目標清單與規格流程。", "您可以在這裡審批草案、新增或排序目標，並前往執行頁與監控頁。"],
  steps: [
    "先看標題旁的狀態，以及下方小字的自治等級、目標與任務數。",
    "若出現「AI 草案」橫幅，按「審批 signoff」，專案審批後才可以執行。",
    "在「執行路徑」與「通過標準」確認引擎的工作位置與完成條件。",
    "在「目標清單」按目標名稱或「查看」，進入該目標看它的任務。",
    "按「新增目標」建立目標，目標超過一個時可以拖曳調整順序。",
    "展開「SDD 治理」，看規格流程目前停在哪個階段。",
    "流程停在人工確認點時，OPERATOR 以上的角色可以按「核准凍結」。",
    "最下方按「執行專案」「查看監控」前往對應頁面，也可以編輯或刪除專案。",
  ],
  fields: [
    SHARED.autonomy,
    { name: "目標", meaning: "這個專案底下有幾個目標。", source: "系統自動產生" },
    { name: "任務", meaning: "這個專案底下全部任務的數量。", source: "系統自動產生" },
    { name: "更新", meaning: "專案最後一次被修改的日期。", source: "系統自動產生" },
    { name: "建立者", meaning: "建立這個專案的帳號，查不到時顯示「—」。", source: "系統自動產生" },
    { name: "AI 草案 — 待人工 signoff 硬閘", meaning: "專案還沒有人審批時出現的橫幅。審批前不能執行，後端也會擋下。", source: "系統自動產生" },
    { name: "審批 signoff", meaning: "橫幅上的按鈕，確認後會記下審批者與時間。唯讀的角色不能按。", source: "您填寫或選擇" },
    { name: "執行路徑", meaning: "引擎執行這個專案時工作的資料夾位置，用等寬字顯示。", source: "您填寫或選擇", sourceNote: "建立或編輯專案時設定" },
    { name: "通過標準", meaning: "說明這個專案怎樣算做完，用 Markdown 排版顯示。", source: "您填寫或選擇", sourceNote: "建立或編輯專案時設定" },
    { name: "專案說明", meaning: "專案的背景與概述，還沒寫時顯示「尚未填寫專案說明」。", source: "您填寫或選擇", sourceNote: "建立或編輯專案時設定" },
    { name: "目標清單", meaning: "這個專案的全部目標，標題旁的數字是目標個數。每一列有狀態、任務完成度的進度條與已完成的任務數。", source: "系統自動產生" },
    { name: "新增目標", meaning: "開啟建立目標的視窗，唯讀的角色不能按。", source: "您填寫或選擇" },
    { name: "拖曳排序", meaning: "目標超過一個時，拖曳列首的把手調整先後順序，鍵盤也可以操作。只有可以修改的角色能排序。", source: "您填寫或選擇" },
    { name: "SDD 治理", meaning: "展開後顯示這個專案的規格流程（SDD）狀態。從未使用過的專案預設收合，標題會寫「尚未使用」。", source: "系統自動產生" },
    { name: "SDD 專案", meaning: "這個專案在規格流程裡使用的名稱，沒設定時預設用專案名。OPERATOR 以上的角色可以按旁邊的「編輯」修改。", source: "您填寫或選擇" },
    { name: "標準鍵", meaning: "規格流程狀態檔名裡使用的標準名稱。與檔內原名不同時，原名會一併列出。", source: "執行引擎回報" },
    { name: "規格目錄", meaning: "存放規格文件的資料夾，還沒有時顯示「—」。", source: "您填寫或選擇" },
    { name: "規格檔", meaning: "這個專案綁定的規格檔，還沒有時顯示「—」。", source: "您填寫或選擇" },
    {
      name: "目前狀態",
      meaning: "規格流程目前的狀態，直接印出流程狀態檔裡的原文。遇到阻塞或升級時會多出紅色橫幅，需要人工照恢復指令處理。",
      source: "執行引擎回報",
      sourceNote: "原文意思見下方的原值表",
    },
    { name: "階段", meaning: "規格流程走到八個主要階段的哪一步，每一步標示「已過」「目前」或「未到」。階段名稱的意思見下方的表。", source: "執行引擎回報" },
    { name: "觀測中", meaning: "階段旁的小標籤，表示流程處在背景觀測的狀態。這時「目前」的步驟會改用虛線外框。", source: "執行引擎回報" },
    { name: "委派 AutoClaude 執行中", meaning: "階段旁的小標籤，表示實作工作已經交給 AutoClaude 執行。", source: "執行引擎回報" },
    { name: "凍結狀態", meaning: "規格是否已經凍結。已凍結時會寫出最後一次凍結的階段與時間，還沒有時寫「尚未凍結」。", source: "執行引擎回報" },
    { name: "待人工", meaning: "規格流程是不是在等人工確認。沒有時顯示「無」，有時顯示「等待人工確認」。", source: "執行引擎回報" },
    { name: "核准凍結", meaning: "流程停在人工確認點時，OPERATOR 以上的角色可以按它核准規格。核准後規格內容被摘要綁定，無法在 Console 退回。", source: "您填寫或選擇" },
    { name: "執行專案", meaning: "前往這個專案的執行頁，在那裡啟動或查看執行批次。", source: "您填寫或選擇" },
    { name: "查看監控", meaning: "前往這個專案的監控頁，看它的執行狀況。", source: "您填寫或選擇" },
    { name: "編輯專案", meaning: "開啟編輯視窗修改這個專案，唯讀的角色不能按。專案執行中時，只能改名稱與說明。", source: "您填寫或選擇" },
    { name: "刪除專案", meaning: "會先跳出確認視窗，確認後目標與任務會一併刪除。執行中的專案不能刪除。", source: "您填寫或選擇" },
  ],
  states: [{ table: "projectStatus" }, { table: "goalStatus" }, { table: "sddPhase" }, { table: "sddFsmState", name: "raw" }],
  sourceFiles: ["components/domain/views/ProjectDetailView.tsx", "components/domain/GoalListCard.tsx", "components/domain/SignoffBanner.tsx", "components/domain/sdd/**"],
};
