"use client";

/**
 * 系統管理／資料庫備份頁（TCS-SysAdminBackup-20261027 FR-BK-02～05、08、R-BK-04～28、R-BK-43～45；PRD §7）：一眼看出「昨晚備份成功了嗎、最近一份全備是何時、離站有沒有備到、備份真的還原得起來嗎」。
 * 頁面資料＝console-api 的 `GET /api/v1/sysadmin/backups`（讀 sidecar 匯出的檔案；每 30 秒重抓，分頁不可見時停止）；Console 在這一頁是**顯示面**——不寫備份、不改排程與保留。
 *
 * 版面（上到下）：標題與麵包屑 → 紅色離線橫幅（控制面無回應時）→ 提示條（來源讀不到時）→ 最近狀態（四張卡）→ WAL 歸檔單行 → 資料更新時間 →
 * 三個分頁（備份清單、排程與保留、還原與說明；沿用 `PillTabs`）。階段二才有「手動操作」區與「工作紀錄」分頁。
 *
 * 設計要點（為什麼這樣做）：
 *  - **fail-loud，量不到絕不顯示成 0**：整頁讀取失敗＝整片顯示原因與「重試」（不拿舊資料頂替）；控制面未設定、匯出檔格式不符或無法讀取（`control.reason`）＝**整頁只顯示原因面板**
 *    （資料區塊全是 null，不渲染卡片、表格、任何數字）；個別來源讀不到（`warnings`）＝提示條明說缺哪一塊、其餘照常。
 *  - **控制面離線不是「沒有資料」**：心跳逾 30 秒（`runner_offline`）資料照回，所以只加紅橫幅（`role="alert"`）與「可能已過期」標記；匯出資料超過 180 秒另加「已過期」。
 *  - 角色只決定「看不看得到輸出尾段」（僅 ADMIN）；沒有任何寫入入口。未登入時查詢不啟用（零請求），登入閘的導向由 `ContentRegion` 負責。
 *  - 純文字：所有字串（標籤、訊息、輸出尾段）一律以 React 文字節點渲染，不經 HTML 或 Markdown。
 */
import { DatabaseBackup, ServerOff } from "lucide-react";
import Link from "next/link";
import { useState, type ReactNode } from "react";

import { Card } from "@/components/ui/card";
import { pillPanelId, pillTabId, PillTabs } from "@/components/ui/pill-tabs";
import { ErrorState } from "@/components/ui/states";
import { useBackupOverview } from "@/lib/api/queries";
import type { BackupOverview } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { controlReasonText, offlineBannerText, reasonBlocksData, RUNNER_OFFLINE, staleMarkText, warningText } from "@/lib/domain/sysadminBackup";
import { formatClock } from "@/lib/format";
import { BackupHelp } from "./BackupHelp";
import { BackupList } from "./BackupList";
import { BackupSchedule } from "./BackupSchedule";
import { BackupStatusCards } from "./BackupStatusCards";
import { WalArchiveLine } from "./WalArchiveLine";

type TabId = "list" | "schedule" | "help";
const TABS: ReadonlyArray<{ id: TabId; label: string }> = [
  { id: "list", label: "備份清單" },
  { id: "schedule", label: "排程與保留" },
  { id: "help", label: "還原與說明" },
];
const ID_BASE = "bk-tab";

/** 紅色離線橫幅：控制面無回應（心跳逾 30 秒或缺席）；進行中的工作不是豁免。 */
function OfflineBanner({ heartbeatAgeSeconds }: { heartbeatAgeSeconds: number | null }) {
  return (
    <div role="alert" data-testid="bk-banner-offline" className="mb-4 flex items-start gap-2 rounded-md border border-wg-draft-border bg-wg-draft-bg px-4 py-3 text-sm font-medium text-wg-error">
      <ServerOff size={18} aria-hidden className="mt-0.5 shrink-0" />
      {offlineBannerText(heartbeatAgeSeconds)}
    </div>
  );
}

/** 提示條：`control.warnings` 非空才出現（來源讀不到、cron 解析不了等）；說明缺的是哪一塊，不阻擋其餘畫面。 */
function HintBar({ warnings }: { warnings: ReadonlyArray<string> }) {
  if (warnings.length === 0) return null;
  return (
    <div role="note" data-testid="bk-hint-bar" className="mb-4 rounded-md border border-wg-alert-border bg-wg-alert-bg px-4 py-3 text-sm">
      <p className="font-medium text-wg-warning-text">有部分資料讀不到，畫面只顯示讀得到的部分</p>
      <ul className="mt-1 list-disc pl-5">
        {warnings.map((code) => (
          <li key={code} className="break-words">
            {warningText(code)}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** 資料區：最近狀態、WAL 歸檔、資料更新時間與三個分頁。`data.control.reason` 不阻擋資料（已由呼叫端判斷）。 */
function DataArea({ data, isAdmin }: { data: BackupOverview; isAdmin: boolean }) {
  const [tab, setTab] = useState<TabId>("list");
  const { control } = data;
  const mark = staleMarkText(control.reason, control.exportAgeSeconds);
  return (
    <>
      <HintBar warnings={control.warnings} />

      <section aria-labelledby="bk-status-heading" className="mb-3">
        <h2 id="bk-status-heading" className="mb-2 text-lg font-semibold">
          最近狀態
        </h2>
        {data.cards === null ? (
          <p data-testid="bk-cards-unavailable" className="text-sm text-wg-muted">
            最近狀態目前無法取得，原因見上方提示。
          </p>
        ) : (
          <BackupStatusCards cards={data.cards} repos={data.repos} isAdmin={isAdmin} />
        )}
      </section>
      <div className="mb-4">
        <WalArchiveLine walArchive={data.walArchive} />
      </div>

      <div className="mb-2 flex flex-wrap items-center justify-between gap-x-6 gap-y-1">
        <PillTabs label="備份分頁" idBase={ID_BASE} tabs={TABS} value={tab} onChange={setTab} />
        <div className="flex flex-col items-end gap-0.5 text-xs text-wg-muted max-md:items-start">
          <span data-testid="bk-timezone-note">{`時間顯示為瀏覽器本機時區；排程時區：${data.timezone ?? "—"}`}</span>
          <span data-testid="bk-updated">
            {`資料更新於 ${formatClock(control.exportGeneratedAt)}`}
            {mark !== null ? (
              <span data-testid="bk-stale-mark" className="ml-2 rounded-sm border border-wg-alert-border bg-wg-alert-bg px-1.5 py-0.5 font-medium text-wg-warning-text">
                {mark}
              </span>
            ) : null}
          </span>
        </div>
      </div>

      <Card role="tabpanel" id={pillPanelId(ID_BASE, tab)} aria-labelledby={pillTabId(ID_BASE, tab)} data-testid={`bk-panel-${tab}`} className="min-w-0 px-5 py-4">
        {tab === "list" ? <BackupList backups={data.backups} repos={data.repos} /> : null}
        {tab === "schedule" ? <BackupSchedule schedule={data.schedule} timezone={data.timezone} reason={control.reason} /> : null}
        {tab === "help" ? <BackupHelp /> : null}
      </Card>
    </>
  );
}

export function BackupView() {
  const { role } = useAuth();
  const q = useBackupOverview();
  /** 輸出尾段只對 ADMIN 渲染；沒有任何寫入入口。 */
  const isAdmin = role === "ADMIN";

  let body: ReactNode;
  if (q.isError) {
    // 整頁讀取失敗：只顯示原因與重試（不拿快取或上一次的資料頂替）
    body = (
      <div data-testid="bk-error-panel">
        <ErrorState error={q.error} title="備份資料無法取得" onRetry={() => void q.refetch()} />
      </div>
    );
  } else if (!q.data) {
    body = (
      <div role="status" data-testid="bk-loading" className="px-1 py-6 text-sm text-wg-muted">
        備份資料載入中…
      </div>
    );
  } else {
    const { control } = q.data;
    body = (
      <>
        {control.reason === RUNNER_OFFLINE ? <OfflineBanner heartbeatAgeSeconds={control.heartbeatAgeSeconds} /> : null}
        {reasonBlocksData(control.reason) ? (
          <div data-testid="bk-reason-panel" data-reason={control.reason} className="rounded-md border border-wg-alert-border bg-wg-alert-bg px-5 py-4 text-[15px] text-wg-warning-text">
            {controlReasonText(control.reason as string)}
          </div>
        ) : (
          <DataArea data={q.data} isAdmin={isAdmin} />
        )}
      </>
    );
  }

  return (
    <div data-testid="bk-page">
      <div className="mb-5">
        <p className="text-sm text-wg-muted">
          <Link href="/sysadmin" className="underline underline-offset-2 hover:text-wg-primary">
            系統管理
          </Link>
          {" › 資料庫備份"}
        </p>
        <h1 className="mt-1 flex items-center gap-2.5 text-[30px] font-bold max-md:text-2xl">
          <DatabaseBackup size={26} className="shrink-0 text-wg-primary" aria-hidden />
          資料庫備份
        </h1>
        <p className="mt-1 text-[15px] text-wg-muted">備份清單、排程、最近四種工作的結果與還原說明；這一頁只讀取備份控制面匯出的資料，不會改動任何備份。</p>
      </div>
      {body}
    </div>
  );
}
