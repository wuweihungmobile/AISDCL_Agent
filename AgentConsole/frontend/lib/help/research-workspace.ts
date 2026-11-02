import type { PageHelp } from "./types";

/**
 * 研究工作區（`/research/[researchId]`，單一路由以 `?step=` 切換五步）的說明（TCS-ResearchToPRD-P0-20261102 FR-R2P-21、AC-R2P-21-2；體例沿 TCS-PageHelp-20261027）：
 * 五步各做什麼寫在 `steps` 欄（AT-960-18-2：五步差異）；狀態與階段詞彙引用 `researchFlow` 表（名稱取自 lib/domain/research.ts，說明不自持名稱）。
 * 欄位名是畫面字樣的逐字引用（出處鎖會到 sourceFiles 找它）：頁首與步驟列的字樣住 ResearchFlowHeader.tsx、FlowStepper.tsx，占位面板與橫幅的字樣住 ResearchWorkspaceView.tsx。
 * 各步驟面板（議題面板、PRD 工作室）自己的欄位字樣尚未在這頁登記：它們是獨立元件，上線後依出處鎖的規則補進這頁的 fields 與 sourceFiles。
 * 英文只用白名單詞；數字不超過兩位。
 */
export const researchWorkspace: PageHelp = {
  id: "research-workspace",
  title: "研究工作區",
  purpose: ["這一頁是單一研究專案的工作區，五個步驟都在這裡，用上方的步驟列切換。", "離開再回來，會自動回到上次做到的那一步。", "前面的步驟完成後只能唯讀檢視，後面的步驟要等前面做完才會開放。"],
  steps: [
    "第一步「研究」：寫下研究命題並啟動深研，系統會蒐集來源並整理成證據矩陣。",
    "第二步「規格工作室」：用證據草擬 PRD，經四方審查通過後，由 ADMIN 核准並凍結。",
    "第三步「分流」：決定規格要併入既有模組或另開新專案，目前尚未開放。",
    "第四步「拆解與執行」：把規格拆成任務並交給執行引擎，目前尚未開放。",
    "第五步「交付」：驗收追溯結果並發布，目前尚未開放。",
    "步驟列亮起的是目前做到的那一步，已完成的步驟可以點開唯讀檢視。",
    "頁首可以切換研究專案，並看到引擎狀態燈、Token 速率與預算。",
    "按「對帳」可以檢查檔案、資料庫與狀態機是否一致，只報告、不修正。",
  ],
  fields: [
    { name: "研發工作流步驟", meaning: "步驟列。每一步都標出已完成、進行中、受阻或待做，不只靠顏色。", source: "系統自動產生" },
    { name: "切換研究專案", meaning: "下拉選單，列出所有研究專案。選一個會前往它做到的那一步。", source: "您填寫或選擇" },
    {
      name: "Token 速率",
      meaning: "最近五分鐘新增的 token 數除以五，單位是每分鐘。沒有事件時顯示破折號。",
      source: "執行引擎回報",
      sourceNote: "取自研究階段的 token 累計",
    },
    {
      name: "Token 預算進度",
      meaning: "已用的 token 佔預算的比例。達到警示閾值時會改用警示色。",
      source: "系統參數",
      sourceNote: "預算與閾值取自執行分類的參數",
    },
    { name: "已完成，唯讀", meaning: "您打開的是已經完成的步驟，只能看，所有會寫入的動作都停用。", source: "系統自動產生" },
    { name: "本步驟於後續階段提供", meaning: "分流、拆解與執行、交付三步目前只顯示說明，還沒有可以操作的內容。", source: "系統自動產生" },
    { name: "回到游標所在步", meaning: "從說明面板回到目前真正做到的那一步。", source: "其他頁面帶入" },
    {
      name: "檔案與資料庫不一致",
      meaning: "對帳發現檔案與資料庫內容不同時，顯示的紅色提示。畫面內容以資料庫為準，系統不會自動修正。",
      source: "系統自動產生",
    },
    { name: "重試初始化", meaning: "只有初始化失敗時才能按。重試不會覆寫已有的檔案，也不會重複建立狀態機。", source: "您填寫或選擇" },
  ],
  states: [{ table: "researchFlow" }],
  sourceFiles: ["components/domain/research/ResearchWorkspaceView.tsx", "components/domain/research/ResearchFlowHeader.tsx", "components/domain/research/FlowStepper.tsx"],
};
