"use client";

import { ArchiveRestore, ChevronLeft, ChevronRight, Plus, SlidersHorizontal, Upload, X } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { PageTitle } from "@/components/domain/PageHeader";
import { ProjectCard } from "@/components/domain/ProjectCard";
import { describeRestoreError } from "@/components/domain/entity/apiErrors";
import { EntityDialog } from "@/components/domain/entity/EntityDialog";
import type { EntityTarget } from "@/components/domain/entity/EntityEditor";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { IconButton } from "@/components/ui/icon-button";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { REASONS } from "@/lib/api/reasons";
import { useProjects, useRestoreProject } from "@/lib/api/queries";
import type { ProjectStatus, ProjectSummary } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { PROJECT_STATUS_TABS } from "@/lib/domain/status";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 10;

/** 排序選項：設計稿第三項「任務數」後端不支援（sort 欄位白名單只有 name／status／createdAt／updatedAt），以「最近建立」取代。 */
const SORTS = {
  updated: { label: "最近更新", param: "updatedAt,desc" },
  name: { label: "名稱", param: "name,asc" },
  created: { label: "最近建立", param: "createdAt,desc" },
} as const;
type SortId = keyof typeof SORTS;

/**
 * 專案列表（設計稿 2）：標題列、Toolbar（狀態 tab／排序／mini 分頁器）、專案卡清單、底部分頁器。
 * v1.2（C-3；契約 §1.6.1～§1.6.2、§4.5 G-09）：OPERATOR 以上多一個「已刪除」篩選——`GET /projects?deleted=true` 只列軟刪除的專案，
 * 每張卡有「復原」鈕（`POST /projects/{id}/restore`）；VIEWER 不顯示（後端對 VIEWER 回 403）。
 */
export function ProjectsView() {
  const q = (useSearchParams().get("q") ?? "").trim();
  const router = useRouter();
  const toast = useToast();
  const { canWrite } = useAuth();
  const restore = useRestoreProject();
  const [tab, setTab] = useState<"ALL" | ProjectStatus>("ALL");
  const [showDeleted, setShowDeleted] = useState(false);
  const [restoringId, setRestoringId] = useState<string | null>(null);
  const [sortId, setSortId] = useState<SortId>("updated");
  const [entity, setEntity] = useState<EntityTarget | null>(null);
  // 已刪除清單只給 OPERATOR 以上（角色降級時自動回到一般清單，不留下會 403 的查詢）
  const deletedMode = showDeleted && canWrite;

  // 換條件就回第 1 頁：頁碼連同「條件鍵」一起存，鍵不符即視為第 1 頁（不需要 effect 重設）
  const filterKey = `${q}|${tab}|${sortId}|${deletedMode}`;
  const [paging, setPaging] = useState({ key: filterKey, page: 1 });
  const page = paging.key === filterKey ? paging.page : 1;
  const setPage = (p: number) => setPaging({ key: filterKey, page: p });

  const query = useProjects({
    page: page - 1,
    size: PAGE_SIZE,
    q: q || undefined,
    status: deletedMode || tab === "ALL" ? undefined : tab,
    sort: SORTS[sortId].param,
    deleted: deletedMode ? true : undefined,
  });
  const data = query.data;
  const total = data?.totalElements ?? 0;
  const totalPages = Math.max(1, data?.totalPages ?? 1);
  const filtering = (!deletedMode && tab !== "ALL") || q !== "";

  async function onRestore(project: ProjectSummary) {
    setRestoringId(project.id);
    try {
      const restored = await restore.mutateAsync(project.id);
      toast.success(`已復原專案「${restored.name}」（${restored.goalsCount} 個目標、${restored.tasksCount} 個任務），可在「全部」清單找到它`);
    } catch (e) {
      toast.error(`復原失敗：${describeRestoreError(e)}`);
      // 專案其實沒被刪除、或已被清除：清單已過期，重抓才會反映現況
      if (e instanceof ApiError && (e.reason === REASONS.PROJECT_NOT_DELETED || e.status === 404)) void query.refetch();
    } finally {
      setRestoringId(null);
    }
  }

  return (
    <div>
      <PageTitle
        className="mb-[18px]"
        title="專案管理"
        subtitle={`Project → Goal → Task 三層管理 · 共 ${total} 筆`}
        actions={
          <>
            <Button asChild variant="ghost" iconLeft={Upload}>
              <Link href="/import">匯入</Link>
            </Button>
            <Button iconLeft={Plus} disabled={!canWrite} title={canWrite ? undefined : "權限不足（唯讀角色）"} onClick={() => setEntity({ kind: "project", mode: "create" })}>
              新建專案
            </Button>
          </>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-3.5 rounded-md border border-wg-line bg-wg-surface px-3.5 py-2.5">
        <span className="inline-flex items-center gap-1.5 pr-1.5 text-sm text-wg-muted">
          <SlidersHorizontal size={18} aria-hidden />
          篩選
        </span>
        <span aria-hidden className="h-[18px] w-px bg-wg-line" />
        {deletedMode ? (
          // 已刪除的專案狀態被改成封存，依狀態篩選沒有意義：換成一句說明
          <span className="text-sm text-wg-muted" data-testid="deleted-hint">
            已刪除的專案保留一段時間（預設 30 天），期間可復原；逾期無法復原。
          </span>
        ) : (
          <div role="group" aria-label="狀態篩選" className="flex flex-wrap gap-1.5">
            {PROJECT_STATUS_TABS.map((t) => {
              const active = tab === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setTab(t.id)}
                  className={cn(
                    "cursor-pointer rounded-md border-none px-4 py-[7px] text-sm font-medium transition-colors",
                    active ? "bg-wg-primary text-white" : "bg-transparent text-wg-text hover:bg-wg-base",
                  )}
                >
                  {t.label}
                </button>
              );
            })}
          </div>
        )}
        {canWrite ? (
          <button
            type="button"
            aria-pressed={deletedMode}
            data-testid="deleted-filter"
            onClick={() => setShowDeleted((v) => !v)}
            className={cn(
              "inline-flex cursor-pointer items-center gap-1.5 rounded-md border-none px-4 py-[7px] text-sm font-medium transition-colors",
              deletedMode ? "bg-wg-primary text-white" : "bg-transparent text-wg-text hover:bg-wg-base",
            )}
          >
            <ArchiveRestore size={16} aria-hidden />
            已刪除
          </button>
        ) : null}
        {q ? (
          <span data-testid="search-chip" className="inline-flex items-center gap-1 rounded-sm bg-wg-tertiary py-1 pr-1 pl-2.5 text-[13px] text-wg-text">
            搜尋：{q}
            <button
              type="button"
              aria-label="清除搜尋"
              onClick={() => router.push("/projects")}
              className="inline-flex size-5 cursor-pointer items-center justify-center rounded-sm border-none bg-transparent text-wg-muted hover:text-wg-primary"
            >
              <X size={14} aria-hidden />
            </button>
          </span>
        ) : null}
        <div className="flex-1" />
        <Select size="sm" aria-label="排序" value={sortId} onChange={(e) => setSortId(e.target.value as SortId)}>
          {(Object.keys(SORTS) as SortId[]).map((id) => (
            <option key={id} value={id}>
              {SORTS[id].label}
            </option>
          ))}
        </Select>
        <span aria-hidden className="h-[18px] w-px bg-wg-line" />
        <div className="flex items-center gap-1 text-sm text-wg-muted" data-testid="mini-pager">
          <span className="font-semibold text-wg-primary">{page}</span>/{totalPages}
          <IconButton icon={ChevronLeft} label="上一頁" size={32} disabled={page <= 1} onClick={() => setPage(page - 1)} />
          <IconButton icon={ChevronRight} label="下一頁" size={32} disabled={page >= totalPages} onClick={() => setPage(page + 1)} />
        </div>
      </div>

      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} title="無法載入專案列表" />
      ) : !data ? (
        <div className="flex flex-col gap-4" aria-busy="true" aria-label="專案列表載入中">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-[92px] rounded-lg" />
          ))}
        </div>
      ) : data.content.length === 0 ? (
        <Card>
          {deletedMode ? (
            <EmptyState title={q ? "沒有符合條件的已刪除專案" : "沒有已刪除的專案"} description="刪除的專案會出現在這裡，保留期內可以復原。" />
          ) : (
            <EmptyState
              title={filtering ? "沒有符合條件的專案" : "還沒有任何專案"}
              description={filtering ? "調整篩選條件或清除搜尋看看。" : "按右上「新建專案」開始，或從「BRD/PRD 匯入」讓 AI 拆解。"}
            />
          )}
        </Card>
      ) : (
        <div className="flex flex-col gap-4" data-testid="project-list">
          {data.content.map((p) => (
            <ProjectCard
              key={p.id}
              project={p}
              canWrite={canWrite}
              deleted={deletedMode}
              restoring={restoringId === p.id}
              onRestore={onRestore}
              onEdit={(id) => setEntity({ kind: "project", mode: "edit", id })}
            />
          ))}
        </div>
      )}

      {totalPages > 1 ? <Pagination className="mt-7" page={page} totalPages={totalPages} onPageChange={setPage} /> : null}

      <EntityDialog target={entity} onClose={() => setEntity(null)} />
    </div>
  );
}
