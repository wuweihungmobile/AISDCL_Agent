import type { PageHelp } from "./types";

/**
 * 研究專案清單頁（`/research`）的說明（TCS-ResearchToPRD-P0-20261102 FR-R2P-21、AC-R2P-21-2；體例沿 TCS-PageHelp-20261027）：
 * 這一頁只有清單、篩選與新建對話框，狀態徽章（進行中、Gate 0 已核准、已交付、規格變更進行中、初始化失敗、已封存）是畫面私有字樣，沒有可對應狀態說明表的常數表，
 * 所以 `states` 留空並登記 NO_STATE_PAGES（雙向相等鎖）；工作流的狀態與階段詞彙寫在工作區頁（`research-workspace`）引用的 `researchFlow` 表。
 * 欄位名是畫面字樣的逐字引用（出處鎖會到 sourceFiles 找它）：欄位名住 ResearchListView.tsx（對話框標籤、按鈕與 aria-label）與 lib/domain/research.ts（徽章標籤）。
 * 英文只用白名單詞；數字不超過兩位。
 */
export const research: PageHelp = {
  id: "research",
  title: "研發工作流",
  purpose: [
    "這一頁列出所有研究專案，每個研究專案都走同一條工作流：研究、規格工作室、分流、拆解與執行、交付。",
    "您可以在這裡新建研究專案，也能回到上次做到的那一步繼續。",
    "目前開放前兩步，後三步只會看到說明面板。",
  ],
  steps: [
    "按右上的「新建研究專案」，輸入研究命題、檢索深度，並勾選要用的來源層。",
    "按每一列的「繼續」連結，回到這個研究專案上次做到的那一步。",
    "用上方的搜尋與篩選，依編號、名稱、狀態或步驟找研究專案。",
    "不再需要的研究專案可以封存，30 天內能在狀態篩選選「已封存」後復原。",
    "初始化失敗的研究專案請先打開它，再按「重試初始化」。",
  ],
  fields: [
    {
      name: "新建研究專案",
      meaning: "打開新建對話框，輸入命題後建立。唯讀的角色按鈕是灰的，不能按。",
      source: "您填寫或選擇",
    },
    { name: "研究命題", meaning: "您要研究的問題，必填，最多五百字。", source: "您填寫或選擇" },
    {
      name: "網址代號",
      meaning: "研究專案的短代號，只能用小寫英數與連字號。建立後就不能再改。",
      source: "您填寫或選擇",
      sourceNote: "由命題自動產生，建立前可改",
    },
    { name: "檢索深度", meaning: "快速、標準、深入三選一。越深入，每一層取的來源越多，也越花時間。", source: "您填寫或選擇" },
    {
      name: "來源層",
      meaning: "論文、官方文獻與業界、開源專案、社群四種來源，至少勾選一個。官方文獻與業界要先啟用網頁層才能選。",
      source: "您填寫或選擇",
    },
    { name: "搜尋研究專案", meaning: "輸入編號、名稱或代號的一部分，清單會即時縮小。", source: "您填寫或選擇" },
    { name: "狀態篩選", meaning: "只看某一種狀態的研究專案。預設的「全部」不含已封存的。", source: "您填寫或選擇" },
    { name: "步驟篩選", meaning: "只看目前停在某一步的研究專案。", source: "您填寫或選擇" },
    {
      name: "Gate 0 已核准",
      meaning: "規格已經由 ADMIN 核准並凍結，之後要改只能走規格變更。",
      source: "系統自動產生",
      sourceNote: "取決於研究專案做到哪一步",
    },
    { name: "初始化失敗", meaning: "工作區或狀態機沒有建好。打開它再按「重試初始化」，重試不會重複建立。", source: "系統自動產生" },
    { name: "封存研究專案", meaning: "把研究專案移出清單，30 天內可以復原。唯讀的角色不能封存。", source: "您填寫或選擇" },
  ],
  states: [],
  sourceFiles: ["components/domain/research/ResearchListView.tsx", "lib/domain/research.ts"],
};
