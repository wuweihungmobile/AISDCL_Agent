/**
 * 備份頁的語意色階 → 設計 token 的 Tailwind 類別（只引用 `wg-*` token，不寫死色碼；全站只有淺色）。
 * 色階本身由 `lib/domain/sysadminBackup.ts` 的純函式決定（`cardStatusTone`、`backupResultText`、`walLine`），這裡只負責「長什麼顏色」。
 * 🔴 顏色從不單獨傳達意思：每個用到它的地方都另有文字（與徽章的 Lucide 圖示）。
 * 🔴 ok 與 info 用 primary-strong（#336A29），不用 success／primary（#498428）：WAL 歸檔單行直接坐在頁面底色（bg-base #F5F7F2）上，
 *    #498428 在那上面只有 4.21:1（真瀏覽器 axe 量到，低於 WCAG AA 的 4.5:1；同 DEF-AC-004 的 hover 底色教訓）；primary-strong 在白卡與頁面底色上都 ≥ 6:1。
 */
import type { BackupTone } from "@/lib/domain/sysadminBackup";

/** 文字色：ok＝成功、warn＝注意、danger＝失敗或警示、info＝進行中、muted＝沒有資料。 */
export const TONE_TEXT: Readonly<Record<BackupTone, string>> = {
  ok: "text-wg-primary-strong",
  warn: "text-wg-warning-text",
  danger: "text-wg-error",
  info: "text-wg-primary-strong",
  muted: "text-wg-muted",
};
