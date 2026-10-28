"use client";

/**
 * WAL 歸檔單行（TCS-SysAdminBackup-20261027 AC-BK-04-6、R-BK-22、D-BK-T20；PRD 掌舵者裁決 Q7）：「WAL 歸檔：最近 <時間>・失敗 N 次」。
 * 唯讀單行（沒有按鈕、沒有輸入）；失敗次數大於零且最近失敗晚於最近歸檔＝警示色；讀不到（`walArchive` 為 null）寫「WAL 歸檔：—」，
 * 絕不寫成「失敗 0 次」——那會把「量不到」讀成「沒有失敗」。文字與色階都由 `walLine`（`lib/domain/sysadminBackup.ts`）決定，這裡只排版。
 */
import { CircleAlert, CircleCheck, CircleDashed } from "lucide-react";

import type { BackupWalArchive } from "@/lib/api/types";
import { walLine, type BackupTone } from "@/lib/domain/sysadminBackup";
import { cn } from "@/lib/utils";
import { TONE_TEXT } from "./tone";

const TONE_ICON = { ok: CircleCheck, danger: CircleAlert, warn: CircleAlert, info: CircleCheck, muted: CircleDashed } as const satisfies Record<BackupTone, unknown>;

export function WalArchiveLine({ walArchive }: { walArchive: BackupWalArchive | null }) {
  const { text, tone } = walLine(walArchive);
  const Icon = TONE_ICON[tone];
  return (
    <p data-testid="bk-wal-line" data-tone={tone} className={cn("flex items-center gap-2 text-sm", TONE_TEXT[tone])}>
      <Icon size={16} aria-hidden className="shrink-0" />
      {text}
    </p>
  );
}
