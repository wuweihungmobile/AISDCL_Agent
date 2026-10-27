import { SHARED } from "./common";
import type { PageHelp } from "./types";

/**
 * 專案管理頁（`/projects`）的說明（TCS-PageHelp-20261027；PRD §4）。先導三頁之一：用「常數狀態表」（專案狀態）示範。
 * 欄位名是畫面字樣的逐字引用（出處鎖會到 sourceFiles 找它）；兩個字以內的欄位名（排序、自治、目標、任務、更新、路徑）免掃，由 SCG-4 人讀把關。
 * 卡片上的專案名稱旁有狀態點與文字（專案狀態，名稱取自 PROJECT_STATUS），所以狀態段引用 `projectStatus`。
 */
export const projects: PageHelp = {
  id: "projects",
  title: "專案管理",
  purpose: ["這一頁列出您所有的專案，每個專案是一張卡片。", "您可以依狀態篩選、換排序或搜尋，再進入專案查看目標與任務。", "也可以在這裡新建專案，或到匯入頁讓 AI 拆解需求文件。"],
  steps: [
    "先用上方的狀態按鈕篩出您要看的專案，例如只看「執行中」的。",
    "需要的話，用右邊的排序選單改成依名稱或最近建立來排列。",
    "在頁面最上方的搜尋框輸入關鍵字，可以只留下名稱符合的專案。",
    "按專案名稱或「查看」，進入專案看它的目標與任務。",
    "按「編輯」修改專案，按「執行」或「監控」前往該專案的執行頁與監控頁。",
    "按右上的「新建專案」建立新專案，唯讀的角色不能使用。",
    "刪除過的專案要按「已刪除」才找得到，保留期限內可以按「復原」。",
  ],
  fields: [
    { name: "狀態篩選", meaning: "按一下按鈕，只看那個狀態的專案，預設看全部。", source: "您填寫或選擇" },
    { name: "排序", meaning: "決定卡片的排列先後，可選最近更新、名稱或最近建立。", source: "您填寫或選擇" },
    { name: "已刪除", meaning: "只有可以修改的角色才看得到這顆按鈕。按下去只列出被刪除的專案，保留期限內可以復原。", source: "您填寫或選擇" },
    { name: "未審批", meaning: "專案名稱旁的小標，表示草案還沒有人簽核，簽核前不能執行。", source: "系統自動產生" },
    { ...SHARED.autonomy, name: "自治" },
    { name: "目標", meaning: "這個專案底下有幾個目標。", source: "系統自動產生" },
    { name: "任務", meaning: "已完成的任務數與全部任務數，例如 3 / 10。", source: "系統自動產生" },
    { name: "更新", meaning: "專案最後一次被修改的日期。", source: "系統自動產生" },
    { name: "路徑", meaning: "專案資料夾的位置，用等寬字顯示，引擎會在那裡工作。", source: "您填寫或選擇", sourceNote: "建立或編輯專案時設定" },
  ],
  states: [{ table: "projectStatus" }],
  sourceFiles: ["components/domain/views/ProjectsView.tsx", "components/domain/ProjectCard.tsx"],
};
