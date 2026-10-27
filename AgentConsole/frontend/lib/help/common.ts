/**
 * 全站共通的說明（TCS-PageHelp-20261027 C2、D-PH-11、R-PH-34；PRD §4 末列、§8.1、Q7）：
 *  - `HELP_COMMON`：每個對話框底部、預設收合的「全站共通」段——頂列公告列與搜尋、通知、待審批、連線點、左側導覽與「我的專案」。這些每頁都看得到，卻不屬於任何一頁；
 *    **只寫這一份**，任兩頁展開後文字相同，頁檔不得複製（content.test.ts 與 PageHelpDialog.test.tsx 鎖）；連線狀態詞用 `serviceState`，名稱取自 SERVICE_LABEL，不在這裡另抄。
 *    公告列的「說明文件」「下載 CLI」「GitHub」「通知總覽」「幫助中心」「繁體中文」目前都只是靜態字樣、不能點（契約 G-G5），「幫助中心」特別寫明，免得與頂列的「本頁說明」鈕混淆（PRD R-5）。
 *  - `SHARED`：跨頁共用的欄位釋義，頁檔放進自己的 `fields`（畫面上的字樣不同時，頁檔以 `{ ...SHARED.xxx, name: "畫面字樣" }` 換掉名稱，釋義仍共用一份）。
 * 欄位名是畫面字樣的逐字引用，出處鎖（AC-PH-05-5）會到 `sourceFiles` 的原始碼裡找它；釋義文字受 lint.ts 白話規則約束。
 */
import type { CommonHelp, HelpField } from "./types";

export const SHARED: Record<string, HelpField> = {
  autonomy: {
    name: "自治等級",
    meaning: "決定引擎執行時，要不要停下來等您確認，數字越大越自動。例如 Level 1 每個任務開始前都要您確認，Level 5 則全自動、只有失敗才找您。",
    source: "您填寫或選擇",
    sourceNote: "建立或編輯專案時設定",
  },
};

export const HELP_COMMON: CommonHelp = {
  fields: [
    { name: "說明文件", meaning: "公告列上的靜態字樣，目前不能點，也不會開啟任何文件。", source: "系統自動產生" },
    { name: "下載 CLI", meaning: "公告列上的靜態字樣，目前不能點，也不會下載任何東西。", source: "系統自動產生" },
    { name: "GitHub", meaning: "公告列上的靜態字樣，目前不能點，也不會前往任何網站。", source: "系統自動產生" },
    {
      name: "Engine Bridge",
      meaning: "公告列與底部都有的連線點，顯示 Console 連不連得上 Engine Bridge。圓點與文字是同一個意思，狀態詞見下方的表。",
      source: "系統自動產生",
      sourceNote: "每 30 秒檢查一次",
    },
    { name: "console-api", meaning: "底部的連線點，顯示 Console 連不連得上後端服務。狀態詞見下方的表。", source: "系統自動產生", sourceNote: "每 30 秒檢查一次" },
    { name: "通知總覽", meaning: "公告列上的靜態字樣，目前不能點。要看通知，請按頂列的鈴。", source: "系統自動產生" },
    { name: "幫助中心", meaning: "公告列上的靜態字樣，目前不能點。要看這一頁的說明，請按頂列的「本頁說明」。", source: "系統自動產生" },
    { name: "繁體中文", meaning: "公告列上的靜態字樣，只表示介面使用繁體中文，目前不能切換語言。", source: "系統自動產生" },
    { name: "搜尋專案、目標、任務", meaning: "頂列的搜尋框，輸入關鍵字後按搜尋鈕，會前往專案管理並套用這個關鍵字。", source: "您填寫或選擇" },
    { name: "最近專案", meaning: "搜尋框下方列出最近的幾個專案，點一下就前往該專案。", source: "系統自動產生" },
    { name: "通知", meaning: "頂列的鈴，紅色數字是待審核項目與未確認告警的合計。點開會看到三個數字與前往的連結。", source: "系統自動產生", sourceNote: "每 30 秒更新一次" },
    { name: "待審批佇列", meaning: "頂列的圖示鈕，數字是等著您簽核的草案數。點下去會前往儀表板的「待人工審批」卡。", source: "系統自動產生", sourceNote: "每 30 秒更新一次" },
    { name: "主導覽", meaning: "左側（手機在底部）的功能入口，亮起來的是您現在所在的功能。", source: "系統自動產生" },
    { name: "我的專案", meaning: "左側導覽下方的專案清單，圓點的顏色代表專案的狀態，沒有文字。螢幕不夠寬時，這個清單會被收起來。", source: "系統自動產生" },
    { name: "登出", meaning: "頂列右上角顯示您的帳號，按「登出」就會結束這次登入。", source: "系統自動產生" },
  ],
  states: [{ table: "serviceState" }],
  sourceFiles: ["components/layout/**", "hooks/useServiceStatus.ts"],
};
