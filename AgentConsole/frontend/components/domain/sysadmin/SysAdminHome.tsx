"use client";

/**
 * 「系統管理」入口頁（TCS-SysAdminBackup-20261027 FR-BK-01、R-BK-02；PRD §5 AC-BK-01-2、§7）：子頁入口卡，目前只有一張「資料庫備份」——一句說明加「最近全備」狀態摘要，整張卡是連到
 * `/sysadmin/backup` 的連結；任一角色可見。
 *
 * 設計要點（為什麼這樣做）：
 *  - **摘要量不到就寫「—」並帶原因，絕不顯示成成功或 0**：請求失敗、控制面未設定、匯出檔壞掉（資料區塊為 null）都是「—」；全備從未執行寫「從未執行」；失敗寫「失敗」（警示色）。
 *    摘要只讀 API 的 `cards[full]`，前端不算任何時間或逾期。
 *  - 未登入（或登入狀態水合中）不渲染入口卡、不發任何備份請求（查詢以登入狀態啟用）；登入閘的導向由 `ContentRegion` 負責，這裡不新增第二套。
 */
import { DatabaseBackup } from "lucide-react";
import Link from "next/link";

import { Card } from "@/components/ui/card";
import { useBackupOverview } from "@/lib/api/queries";
import type { BackupOverview } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { cardStatusText, cardStatusTone, controlReasonText, reasonBlocksData, type BackupTone } from "@/lib/domain/sysadminBackup";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { TONE_TEXT } from "./tone";

/** `text`＝狀態文字（成功、失敗、從未執行…）或「—」；`time`＝全備最近一次的時間（沒有就 null）；`note`＝量不到的原因。 */
type Summary = { text: string; time: string | null; tone: BackupTone; note: string | null };

/** 「最近全備」摘要：載入中、取不到（請求失敗或資料區塊為 null）、全備卡的狀態與時間。 */
function summarize(data: BackupOverview | undefined, failed: boolean): Summary {
  if (failed) return { text: "—", time: null, tone: "muted", note: "備份狀態暫時無法取得" };
  if (!data) return { text: "載入中…", time: null, tone: "muted", note: null };
  const { control, cards } = data;
  if (reasonBlocksData(control.reason)) return { text: "—", time: null, tone: "muted", note: controlReasonText(control.reason as string) };
  const full = cards?.find((card) => card.job === "full");
  if (full === undefined) return { text: "—", time: null, tone: "muted", note: "目前讀不到全備的狀態" };
  const at = full.finishedAt ?? full.startedAt;
  return { text: cardStatusText(full.status), time: full.status === "no_run" || !at ? null : formatDateTime(at), tone: cardStatusTone(full.status), note: null };
}

export function SysAdminHome() {
  const { status } = useAuth();
  const q = useBackupOverview();
  const summary = summarize(q.data, q.isError);
  return (
    <div data-testid="sysadmin-home">
      <div className="mb-5">
        <h1 className="text-[30px] font-bold max-md:text-2xl">系統管理</h1>
        <p className="mt-1 text-[15px] text-wg-muted">管理 Console 背後的系統設施；目前提供資料庫備份。</p>
      </div>
      {status === "authed" ? (
        <Link href="/sysadmin/backup" data-testid="sysadmin-card-backup" className="block max-w-xl rounded-lg">
          <Card className="px-5 py-4 transition-colors hover:border-wg-primary">
            <div className="flex items-center gap-2.5">
              <DatabaseBackup size={22} className="shrink-0 text-wg-primary" aria-hidden />
              <h2 className="text-lg font-semibold">資料庫備份</h2>
            </div>
            <p className="mt-2 text-sm text-wg-muted">查看備份清單、排程與保留策略、最近的備份狀態，以及還原說明。</p>
            <p className="mt-3 text-sm">
              {"最近全備："}
              <strong data-testid="sysadmin-backup-summary" data-tone={summary.tone} className={cn("font-semibold", TONE_TEXT[summary.tone])}>
                {summary.text}
              </strong>
              {summary.time !== null ? (
                <span data-testid="sysadmin-backup-summary-time" className="ml-2 text-wg-muted">
                  {summary.time}
                </span>
              ) : null}
            </p>
            {summary.note !== null ? (
              <p data-testid="sysadmin-backup-summary-note" className="mt-1 text-xs text-wg-muted">
                {summary.note}
              </p>
            ) : null}
          </Card>
        </Link>
      ) : null}
    </div>
  );
}
