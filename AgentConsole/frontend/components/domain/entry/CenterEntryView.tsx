"use client";

/**
 * 執行中心／監控中心的無專案入口頁（TCS-ExecMonitorEntry-20261101 F-905、W-E1；Console PRD §0.8，掌舵者 2026-11-01 真機回報「監控中心與執行中心UI無法執行」）：
 * 路由 `/execute`、`/monitor`，由 `app/execute/page.tsx`、`app/monitor/page.tsx` 只殼組本元件（`kind` 決定標題、圖示、目的路徑與說明）。
 *
 * 為什麼有這一頁：執行與監控都以專案為單位，側欄入口靠 `useCurrentProjectId`（網址 → 最近造訪 → 列表第一筆）找目的專案；三層都落空（資料庫沒有未封存的專案）時，
 * 舊行為是退回 `/projects`，使用者點了「執行中心」卻只看到專案管理的空狀態，網址、標題與 active 項都對不上，以為功能壞了。現在改退回本頁：
 * 說明為什麼要先有專案、列出可進入的專案、並給出「新建專案」「BRD/PRD 匯入」兩個去處。
 *
 * 設計要點（為什麼這樣做）：
 *  - **不自動跳轉**（⚖2）：有專案時側欄已直達該專案頁，本頁只在「深連結或零專案」時出現；自動跳轉會讓「選擇」消失，也不好測試與解釋。入口頁不呼叫任何 mutation、不 `router.push`、不記住專案（記住由專案頁的 `useCurrentProjectId` 負責）。
 *  - **清單沿用 `useAllProjects`**（⚖7）：與側欄 rail、儀表板同一份快取，最多 100 筆、更新時間新到舊，不另加端點、不分頁、不搜尋；超過 100 個專案時從專案管理頁搜尋後由專案頁進入（每頁說明寫明）。
 *  - **只有「根本沒有資料」才換成錯誤或骨架**：背景重抓失敗時 `data` 仍是上一份，清單照常顯示（同執行頁 DEF-AC-007 的取捨）。
 *  - **VIEWER 的「新建專案」停用而不隱藏**（⚖5）：與專案管理頁同體例；「BRD/PRD 匯入」三種角色皆顯示（匯入頁自管權限）。
 *  - 每筆專案連結的可及名稱恰為專案名（`aria-label`），狀態標籤放 `aria-hidden` 容器：視覺上有狀態、讀屏不重複念。
 */
import { Activity, Play, Plus, Upload, type LucideIcon } from "lucide-react";
import Link from "next/link";

import { PageTitle } from "@/components/domain/PageHeader";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusDot } from "@/components/ui/status-dot";
import { EmptyState, ErrorState, PageSkeleton } from "@/components/ui/states";
import { useAllProjects } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/AuthProvider";
import { projectStatus } from "@/lib/domain/status";

type Kind = "execute" | "monitor";

type Copy = { icon: LucideIcon; title: string; subtitle: string; intro: string; emptyDescription: string };

/** 兩頁只差標題、圖示、說明（目的路徑由 `kind` 直接組進連結）；文字逐字取自 TCS-ExecMonitorEntry-20261101 W-E1 (a)～(c)。 */
const COPY: Record<Kind, Copy> = {
  execute: {
    icon: Play,
    title: "執行中心",
    subtitle: "以專案為單位 · 選擇專案進入它的執行頁",
    intro: "執行中心以專案為單位：每個專案有自己的執行頁（啟動、暫停、恢復、取消批次與審核）。請從下面選擇一個專案進入；還沒有專案時，先新建專案或從 BRD/PRD 匯入。",
    emptyDescription: "執行中心需要一個專案。先按「新建專案」，或從「BRD/PRD 匯入」讓 AI 拆解，建立後再回到這裡選擇它進入。",
  },
  monitor: {
    icon: Activity,
    title: "監控中心",
    subtitle: "以專案為單位 · 選擇專案進入它的監控頁",
    intro: "監控中心以專案為單位：每個專案有自己的監控頁（指標、趨勢、日誌、告警）。請從下面選擇一個專案進入；還沒有專案時，先新建專案或從 BRD/PRD 匯入。",
    emptyDescription: "監控中心需要一個專案。先按「新建專案」，或從「BRD/PRD 匯入」讓 AI 拆解，建立後再回到這裡選擇它進入。",
  },
};

export function CenterEntryView({ kind }: { kind: Kind }) {
  const copy = COPY[kind];
  const { canWrite } = useAuth();
  const all = useAllProjects();
  const projects = all.data?.content;

  return (
    <div data-testid="center-entry-view" data-kind={kind}>
      <PageTitle
        className="mb-3"
        icon={copy.icon}
        title={copy.title}
        subtitle={copy.subtitle}
        actions={
          <>
            <Button asChild variant="ghost" iconLeft={Upload}>
              <Link href="/import">BRD/PRD 匯入</Link>
            </Button>
            {canWrite ? (
              <Button asChild iconLeft={Plus}>
                <Link href="/projects/new">新建專案</Link>
              </Button>
            ) : (
              <Button iconLeft={Plus} disabled title="權限不足（唯讀角色）">
                新建專案
              </Button>
            )}
          </>
        }
      />
      <p data-testid="entry-intro" className="mb-5 text-sm text-wg-muted">
        {copy.intro}
      </p>

      {projects === undefined ? (
        all.isError ? (
          <ErrorState error={all.error} onRetry={() => all.refetch()} title="無法載入專案列表" />
        ) : (
          <PageSkeleton />
        )
      ) : projects.length === 0 ? (
        <Card>
          <EmptyState title="還沒有任何專案" description={copy.emptyDescription} />
        </Card>
      ) : (
        <ul role="list" aria-label="選擇專案" data-testid="entry-project-list" className="flex flex-col gap-3">
          {projects.map((p) => {
            const status = projectStatus(p.status);
            return (
              <li key={p.id}>
                <Link href={`/projects/${p.id}/${kind}`} aria-label={p.name} className="block rounded-lg">
                  <Card className="flex items-center gap-3 px-5 py-3.5 transition-colors hover:border-wg-primary">
                    <StatusDot color={status.color} />
                    <span className="min-w-0 flex-1 truncate text-[17px] font-semibold text-wg-text">{p.name}</span>
                    <span aria-hidden className="shrink-0 text-[13px] text-wg-muted">
                      {status.label}
                    </span>
                  </Card>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
