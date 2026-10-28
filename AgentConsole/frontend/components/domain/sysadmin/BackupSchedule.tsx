"use client";

/**
 * 「排程與保留」分頁（TCS-SysAdminBackup-20261027 FR-BK-03、R-BK-10～14；PRD §5 AC-BK-03-1～03-4）：**完全唯讀**——沒有輸入元件、沒有編輯類按鈕、不發任何寫入請求
 * （排程住 sidecar 的 crontab、保留住 pgBackRest 設定，Console 只讀、只顯示；即使 ADMIN 亦然）。
 *
 * 設計要點（為什麼這樣做）：
 *  - 排程列來自匯出的 `schedule.entries`，有幾條就列幾條（缺的不補佔位列），再加一條固定列「WAL 持續歸檔」；每列「<白話>・<工作名>」並附原 cron 與排程時區、下次執行時間
 *    （`nextRunAt` 由 console-api 以排程時區算好，前端只用本機時區顯示）。cron 認不得就原表達式退回（`humanizeCron`），不猜、不丟例外、不 `console.error`。
 *  - 保留策略一行字：量不到（`retention` 為 null）顯示「—」，不填預設值；工作名與保留文字都由 `lib/domain/sysadminBackup.ts` 決定。
 *  - `schedule` 為 null（匯出缺）＝顯示原因文字，不顯示空表——「量不到」不能被讀成「沒有排程」。
 */
import type { BackupSchedule as BackupScheduleData } from "@/lib/api/types";
import { controlReasonText, retentionText, scheduleRowText, WAL_FIXED_ROW_TEXT } from "@/lib/domain/sysadminBackup";
import { formatDateTime } from "@/lib/format";

export function BackupSchedule({ schedule, timezone, reason }: { schedule: BackupScheduleData | null; timezone: string | null; reason: string | null }) {
  if (schedule === null) {
    return (
      <p data-testid="bk-sched-unavailable" className="py-3 text-sm text-wg-muted">
        {`排程資料目前無法取得${reason ? `：${controlReasonText(reason)}` : ""}`}
      </p>
    );
  }
  return (
    <div data-testid="bk-schedule" className="flex flex-col gap-4">
      <ul aria-label="排程" className="flex flex-col divide-y divide-wg-line">
        {schedule.entries.map((entry) => (
          <li key={entry.job} data-testid={`bk-sched-${entry.job}`} className="flex flex-wrap items-baseline gap-x-4 gap-y-1 py-2 text-sm">
            <span className="font-medium">{scheduleRowText(entry)}</span>
            <span className="text-xs text-wg-muted">
              原 cron：<code className="font-mono">{entry.cron}</code>
            </span>
            <span className="text-xs text-wg-muted">{`時區：${timezone ?? "—"}`}</span>
            <span className="text-xs text-wg-muted">{`下次：${formatDateTime(entry.nextRunAt)}`}</span>
          </li>
        ))}
        <li data-testid="bk-sched-fixed-wal" className="py-2 text-sm">
          {WAL_FIXED_ROW_TEXT}
        </li>
      </ul>
      <div>
        <h3 className="mb-1 text-sm font-semibold">保留策略</h3>
        <p data-testid="bk-retention" className="text-sm">
          {retentionText(schedule.retention)}
        </p>
      </div>
    </div>
  );
}
