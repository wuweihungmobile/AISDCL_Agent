import type { PageHelp } from "./types";

/**
 * 監控中心入口頁（`/monitor`）的說明（TCS-ExecMonitorEntry-20261101 W-E3；Console PRD §0.8；體例沿 TCS-PageHelp-20261027）：
 * 與 `execute-entry` 是同一個元件（CenterEntryView）的另一個變體，只差標題、目的頁與一句說明；理由、`states` 留空與數字寫法都同 `execute-entry.ts` 檔頭，不在這裡重抄。
 * 與 `monitor`（專案監控頁）刻意分成兩條說明（⚖4）：專案監控頁的欄位與狀態入口頁都沒有。
 * 欄位名是畫面字樣的逐字引用，三個名稱都住 CenterEntryView.tsx。
 */
export const monitorEntry: PageHelp = {
  id: "monitor-entry",
  title: "監控中心",
  purpose: [
    "這一頁是監控中心的入口，用來選擇要進入哪一個專案的監控頁。",
    "每個專案有自己的監控頁，可以看指標、趨勢、日誌與告警。",
    "平常左側導覽會直接帶您進入專案，只有沒有專案或直接開啟這個網址時，才會停在這一頁。",
  ],
  steps: [
    "先看清單上方的說明，確認這裡是監控中心的入口。",
    "在「選擇專案」清單點一個專案，就會前往它的監控頁。",
    "進入監控頁後，查看指標、趨勢、日誌與告警。",
    "還沒有專案時，按「新建專案」建立第一個專案。",
    "也可以按旁邊的匯入按鈕，讓 AI 把需求文件拆成專案。",
    "專案超過一百個時，先到專案管理頁搜尋，再進入專案。",
  ],
  fields: [
    { name: "新建專案", meaning: "前往新建專案的表單，建立好之後就可以回到這裡選它。唯讀的角色按鈕是灰的，不能按。", source: "您填寫或選擇" },
    { name: "BRD/PRD 匯入", meaning: "前往匯入頁，把 BRD（商業需求文件）或 PRD（產品需求文件）交給 AI。AI 會拆成專案、目標與任務，三種角色都看得到這個連結。", source: "您填寫或選擇" },
    {
      name: "選擇專案",
      meaning: "列出可以進入的專案，點一個就前往它的監控頁。每一列有狀態圓點與狀態文字，依最近更新排序。",
      source: "系統自動產生",
      sourceNote: "取自專案管理，最多列出一百個",
    },
  ],
  states: [],
  sourceFiles: ["components/domain/entry/CenterEntryView.tsx"],
};
