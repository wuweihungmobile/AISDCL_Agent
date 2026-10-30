"use client";

/**
 * 「備份清單」分頁（TCS-SysAdminBackup-20261027 FR-BK-02、R-BK-04～09；PRD §5 AC-BK-02-1～02-6）：先是各 repo 的狀態列（儲存位置、pgBackRest 的狀態碼、離站是否與主機同碟），
 * 再是一張十欄表——類型、標籤、儲存位置、開始、結束、耗時、資料庫、備份、基準、結果；列序＝API 回應序（新到舊，前端不另排序）。
 *
 * 設計要點（為什麼這樣做）：
 *  - **repo 異常不當成沒有備份**：某 repo 狀態碼不是 0（例：離站不可達）＝它的狀態列顯示「狀態碼 N」與中文說明，另一個 repo 照常；沒有備份的 repo 不補佔位列。
 *  - **「與主機同碟」要說出來**：離站 repo 的端點是本機 MinIO 時標「本機 MinIO・與主機同碟，主機損毀時一併消失」，任何處都不稱「離站已安全」；外部 S3 才標「外部 S3」。
 *    本機磁碟（repo1，沒有端點主機）固定顯示「本地」、沒有 S3 徽章。
 *  - **量不到絕不顯示成 0**：`backups` 為 null（來源讀不到）顯示原因、不顯示「尚無備份」；完全沒有備份是合法空狀態，寫「尚無備份：首次部署後請立刻做第一份全備」。缺值（邏輯備份沒有開始時間與資料庫大小）一律「—」，
 *    不寫「0 B」「0s」。格式化沿用既有 `formatDateTime`、`formatDuration`、`formatBytes`（本檔不自己定義同名函式）。
 *  - 備份清單只含成功建立的備份；固定一行說明「失敗的工作看狀態卡與工作紀錄」。純文字：標籤與訊息一律是 React 文字節點。
 */
import type { BackupRepo, BackupRow } from "@/lib/api/types";
import { formatDuration } from "@/lib/domain/metrics";
import { backupKindText, backupLocationText, backupResultText, isOffsiteRepo, LIST_EMPTY_TEXT, LIST_NOTE, offsiteBadgeText, repoStatusLine } from "@/lib/domain/sysadminBackup";
import { formatBytes, formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { TONE_TEXT } from "./tone";

const HEADERS = ["類型", "標籤", "儲存位置", "開始", "結束", "耗時", "資料庫", "備份", "基準", "結果"] as const;
const DASH = "—";

const sizeText = (bytes: number | null): string => (typeof bytes === "number" ? formatBytes(bytes) : DASH);

/** 一個 repo 的狀態列：位置名稱（repo1 是本地磁碟、沒有端點主機，不掛 S3 徽章）、離站徽章，與 pgBackRest 的狀態（0＝正常；其餘＝狀態碼加中文說明）。 */
function RepoStatus({ repo }: { repo: BackupRepo }) {
  const normal = repo.statusCode === 0;
  return (
    <li data-testid={`bk-repo-${repo.repo}`} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
      <span className="font-medium">{backupLocationText(`repo${repo.repo}`)}</span>
      {isOffsiteRepo(repo) ? (
        <span
          data-testid={`bk-repo-badge-${repo.repo}`}
          className={cn("rounded-sm border px-2 py-0.5 text-xs", repo.local ? "border-wg-alert-border bg-wg-alert-bg text-wg-warning-text" : "border-wg-line text-wg-muted")}
        >
          {offsiteBadgeText(repo.local)}
        </span>
      ) : null}
      <span data-testid={`bk-repo-status-${repo.repo}`} data-tone={normal ? "ok" : "danger"} className={normal ? TONE_TEXT.ok : cn("font-medium", TONE_TEXT.danger)}>
        {repoStatusLine(repo.statusCode, repo.statusMessage)}
      </span>
    </li>
  );
}

function BackupTable({ backups }: { backups: ReadonlyArray<BackupRow> }) {
  return (
    // 窄螢幕下十欄表橫向溢出：容器要能用鍵盤抵達並捲動（tabIndex 0＋role region＋名稱；焦點環由全域 :focus-visible 提供；axe scrollable-region-focusable，SCG-4 F11）
    <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label="備份清單（可橫向捲動）">
      <table data-testid="bk-table" className="w-full min-w-[56rem] border-collapse text-left text-sm">
        <caption className="sr-only">備份清單</caption>
        <thead>
          <tr className="border-b border-wg-line text-xs text-wg-muted">
            {HEADERS.map((header) => (
              <th key={header} scope="col" className="py-2 pr-3">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {backups.map((row) => {
            const result = backupResultText(row.result);
            return (
              <tr key={`${row.location}:${row.label}`} data-testid={`bk-row-${row.label}`} className="border-b border-wg-line align-top">
                <td className="py-2 pr-3 whitespace-nowrap">{backupKindText(row.kind)}</td>
                <td className="py-2 pr-3 font-mono text-xs break-all">{row.label}</td>
                <td className="py-2 pr-3 whitespace-nowrap">{backupLocationText(row.location)}</td>
                <td className="py-2 pr-3 whitespace-nowrap tabular-nums">{formatDateTime(row.startedAt)}</td>
                <td className="py-2 pr-3 whitespace-nowrap tabular-nums">{formatDateTime(row.finishedAt)}</td>
                <td className="py-2 pr-3 whitespace-nowrap tabular-nums">{formatDuration(row.durationSeconds)}</td>
                <td className="py-2 pr-3 whitespace-nowrap tabular-nums">{sizeText(row.databaseSizeBytes)}</td>
                <td className="py-2 pr-3 whitespace-nowrap tabular-nums">{sizeText(row.repoSizeBytes)}</td>
                <td className="py-2 pr-3 font-mono text-xs break-all">{row.baseLabel ?? DASH}</td>
                <td data-testid={`bk-result-${row.label}`} data-tone={result.tone} className={cn("py-2 whitespace-nowrap", TONE_TEXT[result.tone])}>
                  {result.text}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function BackupList({ backups, repos }: { backups: ReadonlyArray<BackupRow> | null; repos: ReadonlyArray<BackupRepo> | null }) {
  return (
    <div data-testid="bk-list" className="flex flex-col gap-3">
      {repos !== null && repos.length > 0 ? (
        <ul aria-label="各備份庫狀態" className="flex flex-col gap-1.5">
          {repos.map((repo) => (
            <RepoStatus key={repo.repo} repo={repo} />
          ))}
        </ul>
      ) : null}
      <p data-testid="bk-list-note" className="text-xs text-wg-muted">
        {LIST_NOTE}
      </p>
      {backups === null ? (
        <p data-testid="bk-list-unavailable" className="py-3 text-sm text-wg-muted">
          備份清單目前無法取得，原因見上方提示；這不代表沒有備份。
        </p>
      ) : backups.length === 0 ? (
        <p data-testid="bk-list-empty" className="py-3 text-sm text-wg-muted">
          {LIST_EMPTY_TEXT}
        </p>
      ) : (
        <BackupTable backups={backups} />
      )}
    </div>
  );
}
