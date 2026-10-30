import type { PageHelp } from "./types";

/**
 * 系統管理入口頁（`/sysadmin`）的說明（TCS-PageHelp-20261027；姊妹案 TCS-SysAdminBackup-20261027 AT-BK-01-2-4、PRD D-12）：2026-10-31 補頁寫實，自 registry.ts 的 PENDING_HELP_PAGES 移進 HELP_PAGES。
 * 這一頁只有一張「資料庫備份」入口卡與「最近全備」摘要；摘要只讀 API 的全備卡，前端不算時間也不判逾期（SysAdminHome.tsx）。
 * 狀態詞（成功、失敗、進行中、中斷、從未執行）是畫面私有字樣，沒有匯出的常數表可以對應 StateTableId；新增 StateTableId 與改 states.ts 都是每頁說明案的凍結面，補頁不碰，
 * 所以狀態詞寫在「最近全備」的釋義裡、`states` 留空並登記 NO_STATE_PAGES（雙向相等鎖）。
 * 欄位名是畫面字樣的逐字引用（出處鎖會到 sourceFiles 找它）：標題與入口卡文字住 SysAdminHome.tsx，「—」旁的原因文字有兩處來源——
 * 請求失敗與讀不到全備住 SysAdminHome.tsx，控制面未設定、匯出檔格式版本不符與無法讀取住 lib/domain/sysadminBackup.ts 的 CONTROL_REASON_TEXT，所以兩個檔都列入。
 * sourceFiles 只列入口頁自己的元件檔，不用整個 components/domain/sysadmin/**：「系統管理」「資料庫備份」兩個名稱也出現在備份頁，
 * 整個目錄會讓入口頁原始碼被改掉卻仍被備份頁的字面值滿足，鎖就失去鑑別力。
 * 釋義一律用中文：英文字樣（Docker、pg_dump、WAL、MinIO 等）只放欄位名欄，釋義裡不引用（英文詞白名單不含它們，PRD §8.3）。
 */
export const sysadmin: PageHelp = {
  id: "sysadmin",
  title: "系統管理",
  purpose: [
    "這一頁是系統管理的入口，把 Console 背後的系統設施集中在一起。",
    "目前只有「資料庫備份」一張卡，整張卡都可以點，會前往備份頁。",
    "卡上先顯示最近一次全備（完整備份整個資料庫）的結果，讓您不必點進去，就能知道備份有沒有出問題。",
  ],
  steps: [
    "先看「資料庫備份」卡上的「最近全備」，了解最近一次全備是成功還是失敗。",
    "「最近全備」顯示「—」時，看它下面的小字，那裡寫明讀不到的原因。",
    "按卡片上的任何位置，就會前往資料庫備份頁，看完整的備份狀態。",
  ],
  fields: [
    { name: "系統管理", meaning: "頁面標題，也是左側導覽的項目名稱。這一頁沒有任何會改動系統的按鈕，不論哪種角色都看得到。", source: "系統自動產生" },
    {
      name: "資料庫備份",
      meaning: "目前唯一的入口卡，整張卡都是連結，按下去會前往資料庫備份頁。卡上的說明寫明備份頁可以看備份清單、排程與保留策略、最近的備份狀態和還原說明。",
      source: "您填寫或選擇",
    },
    {
      name: "最近全備",
      meaning: "顯示最近一次全備的結果：成功是順利完成，失敗是出錯，進行中是正在做，中斷是沒做完就停了，從未執行是還沒跑過。後面接那次的時間，讀不到時顯示「—」，這不代表成功，也不代表沒有備份。",
      source: "系統自動產生",
      sourceNote: "取自備份控制面匯出的檔案",
    },
    { name: "載入中…", meaning: "還在向後端讀取資料時顯示，讀完就會換成實際的結果。", source: "系統自動產生" },
    {
      name: "備份狀態暫時無法取得",
      meaning: "向後端讀取失敗時，「最近全備」會顯示「—」，並在下面寫出這一行小字。請稍後重新整理頁面再試。",
      source: "系統自動產生",
    },
    {
      name: "備份控制面未設定（不在 Docker 全棧）",
      meaning: "備份控制面是負責執行備份的獨立服務，這個環境沒有設定它，所以讀不到任何備份資料。常見於沒有用完整容器組合啟動的開發環境。",
      source: "系統自動產生",
    },
    {
      name: "匯出檔格式版本不符",
      meaning: "備份控制面匯出的檔案版本和 Console 不一致，所以不顯示任何備份資料。請把兩邊更新到同一版本。",
      source: "系統自動產生",
    },
    {
      name: "匯出檔無法讀取",
      meaning: "備份控制面匯出的檔案不存在、損毀或是空的，所以不顯示任何備份資料。請確認備份控制面是否正常運作。",
      source: "系統自動產生",
    },
    { name: "目前讀不到全備的狀態", meaning: "資料讀取成功，但裡面沒有全備的狀態，所以「最近全備」只能顯示「—」。", source: "系統自動產生" },
  ],
  states: [],
  sourceFiles: ["components/domain/sysadmin/SysAdminHome.tsx", "lib/domain/sysadminBackup.ts"],
};
