"use client";

/**
 * 最近狀態卡（TCS-SysAdminBackup-20261027 FR-BK-04、R-BK-15～19、R-BK-09；PRD §7）：全備、增備（差異）、離站 pg_dump、驗證四張，依 API 的順序（前端不重排）。
 * 每張卡：狀態徽章（文字加 Lucide 圖示，不得只有顏色）、最近一次執行（排程或手動、開始時間、耗時）、「最近一次成功」、逾期標記；
 * 全備與增備卡另附「最近一份備份」並標明來源（取自 pgBackRest 清單，所以沒有狀態檔的新環境也看得到）；離站 pg_dump 卡在離站儲存是本機 MinIO 時標「與主機同碟」。
 *
 * 設計要點（為什麼這樣做）：
 *  - **前端不判逾期**：只讀 `card.overdue` 顯示標記；沒有 cron 函式庫、沒有寬限分鐘、不對 `lastDueAt` 做任何運算（靜態鎖 AT_BK_04_3_3）。
 *  - **失敗不覆蓋較早的成功**：失敗卡同時寫「最近一次成功：<時間>」；從未成功寫「從未成功」，不寫「—」也不寫時間。
 *  - **輸出尾段只給 ADMIN**：即使回應裡有 `detailTail`，非 ADMIN 的 DOM 也不渲染（防禦：後端是授權邊界，這裡再擋一次）；尾段是 React 文字節點，不經 HTML 或 Markdown。
 *  - 量不到絕不顯示成 0：缺的時間、耗時一律「—」。
 */
import { CircleAlert, CircleCheck, CircleDashed, CircleX, LoaderCircle, type LucideIcon } from "lucide-react";

import { Card } from "@/components/ui/card";
import type { BackupCard, BackupRepo } from "@/lib/api/types";
import { formatDuration } from "@/lib/domain/metrics";
import { cardStatusText, cardStatusTone, dumpOffsiteNote, isOffsiteRepo, lastSuccessText, scheduleJobLabel, triggerText, type BackupTone } from "@/lib/domain/sysadminBackup";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { TONE_TEXT } from "./tone";

/** 狀態 → Lucide 圖示：成功、失敗、進行中、中斷、從未執行各一個；不認得的狀態用「注意」圖示。 */
const STATUS_ICON: Readonly<Record<string, LucideIcon>> = {
  succeeded: CircleCheck,
  failed: CircleX,
  running: LoaderCircle,
  interrupted: CircleAlert,
  no_run: CircleDashed,
};

/** 卡片底色：失敗或中斷＝警示底；逾期（其餘狀態）＝注意底；其餘白底。 */
function cardSurface(tone: BackupTone, overdue: boolean): string {
  if (tone === "danger") return "border-wg-draft-border bg-wg-draft-bg";
  if (overdue) return "border-wg-alert-border bg-wg-alert-bg";
  return "";
}

/** 離站 pg_dump 的位置說明：與離站 repo 同判；沒有離站 repo 的資訊（`repos` 為 null 或沒有離站項）就不說，不猜。 */
function offsiteNote(repos: ReadonlyArray<BackupRepo> | null): string | null {
  const offsite = repos?.find(isOffsiteRepo);
  return offsite === undefined ? null : dumpOffsiteNote(offsite.local);
}

/** 最近一次執行一行字：觸發（排程或手動）、開始時間、耗時；沒有狀態檔（尚無任何執行記錄）寫「—」。 */
function runText(card: BackupCard): string {
  if (card.trigger === null && card.startedAt === null) return "最近一次執行：—";
  return `最近一次執行：${triggerText(card.trigger)}・${formatDateTime(card.startedAt)}・耗時 ${formatDuration(card.durationSeconds)}`;
}

function StatusCard({ card, repos, isAdmin }: { card: BackupCard; repos: ReadonlyArray<BackupRepo> | null; isAdmin: boolean }) {
  const tone = cardStatusTone(card.status);
  const Icon = STATUS_ICON[card.status] ?? CircleAlert;
  const note = card.job === "dump" ? offsiteNote(repos) : null;
  const tail = isAdmin && typeof card.detailTail === "string" && card.detailTail !== "" ? card.detailTail : null;
  return (
    <Card data-testid={`bk-card-${card.job}`} data-tone={tone} className={cn("flex min-w-0 flex-col gap-2 px-4 py-3", cardSurface(tone, card.overdue))}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-base font-semibold">{scheduleJobLabel(card.job)}</h3>
        {card.overdue ? (
          <span data-testid={`bk-overdue-${card.job}`} className="rounded-sm border border-wg-alert-border bg-wg-alert-bg px-2 py-0.5 text-xs font-semibold text-wg-warning-text">
            逾期
          </span>
        ) : null}
      </div>
      <span data-testid={`bk-badge-${card.job}`} data-status={card.status} data-tone={tone} className={cn("inline-flex items-center gap-1.5 self-start text-sm font-semibold", TONE_TEXT[tone])}>
        <Icon size={16} aria-hidden className="shrink-0" />
        {cardStatusText(card.status)}
      </span>
      <p data-testid={`bk-run-${card.job}`} className="text-sm text-wg-muted">
        {runText(card)}
      </p>
      <p data-testid={`bk-last-success-${card.job}`} className="text-sm">
        {lastSuccessText(card)}
      </p>
      {"latestBackup" in card ? (
        <p data-testid={`bk-latest-${card.job}`} className="text-sm break-words text-wg-muted">
          {card.latestBackup ? `最近一份備份：${card.latestBackup.label}（${formatDateTime(card.latestBackup.finishedAt)}）・來源：pgBackRest 清單` : "最近一份備份：—"}
        </p>
      ) : null}
      {note !== null ? (
        <p data-testid="bk-offsite-dump" className="text-sm break-words text-wg-muted">
          {note}
        </p>
      ) : null}
      {tail !== null ? (
        // 可捲動容器（max-h-48）要能用鍵盤抵達：tabIndex 0＋role region＋名稱（帶工作名，三張卡互不相同）；焦點環由全域 :focus-visible 提供（axe scrollable-region-focusable，SCG-4 F11）
        <pre
          data-testid={`bk-tail-${card.job}`}
          tabIndex={0}
          role="region"
          aria-label={`${scheduleJobLabel(card.job)} 輸出尾段（可捲動）`}
          className="max-h-48 overflow-auto rounded-md border border-wg-line bg-white px-3 py-2 font-mono text-xs break-all whitespace-pre-wrap text-wg-text"
        >
          {tail}
        </pre>
      ) : null}
    </Card>
  );
}

export function BackupStatusCards({ cards, repos, isAdmin }: { cards: ReadonlyArray<BackupCard>; repos: ReadonlyArray<BackupRepo> | null; isAdmin: boolean }) {
  return (
    <div data-testid="bk-cards" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <StatusCard key={card.job} card={card} repos={repos} isAdmin={isAdmin} />
      ))}
    </div>
  );
}
