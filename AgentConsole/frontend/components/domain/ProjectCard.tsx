import { Folder } from "lucide-react";
import Link from "next/link";

import { Tag } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusLabel } from "@/components/ui/status-dot";
import type { ProjectSummary } from "@/lib/api/types";
import { projectStatus } from "@/lib/domain/status";
import { formatDate, formatDateTime } from "@/lib/format";

/**
 * 專案列表卡（設計稿 2）：48px 圖示方塊、專案名、狀態點與文字、「未審批」紅標、meta 行
 * （Lv.N 自治／目標 N／任務 done / total／更新日期／等寬路徑）、右側四個 ghost 按鈕：查看／編輯／執行／監控。
 * 「已刪除」模式（v1.2，C-3；契約 §1.6.2）：專案名不可連（詳情頁已 404）、狀態點換成「已刪除」標籤、meta 顯示刪除時間，
 * 右側只有一顆「復原」（OPERATOR 以上才可按；POST /projects/{id}/restore）。
 */
export function ProjectCard({
  project: p,
  onEdit,
  canWrite,
  deleted = false,
  onRestore,
  restoring = false,
}: {
  project: ProjectSummary;
  onEdit: (id: string) => void;
  canWrite: boolean;
  /** 已刪除清單的卡片（GET /projects?deleted=true） */
  deleted?: boolean;
  onRestore?: (project: ProjectSummary) => void;
  /** 這個專案的復原請求進行中 */
  restoring?: boolean;
}) {
  const meta = projectStatus(p.status);
  return (
    <Card data-testid="project-card" data-project-id={p.id} data-deleted={deleted || undefined} className="flex items-center gap-5 px-5 py-[18px] max-lg:flex-wrap">
      <span className="inline-flex size-12 shrink-0 items-center justify-center rounded-[10px] bg-wg-tertiary">
        <Folder size={24} className="text-wg-primary" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <div className="mb-1.5 flex items-center gap-2.5">
          {deleted ? (
            <span className="truncate text-[17px] font-semibold text-wg-text" data-testid="project-name">
              {p.name}
            </span>
          ) : (
            <Link href={`/projects/${p.id}`} className="truncate text-[17px] font-semibold text-wg-text transition-colors hover:text-wg-primary">
              {p.name}
            </Link>
          )}
          {deleted ? <Tag data-testid="deleted-tag">已刪除</Tag> : <StatusLabel meta={meta} live={p.status === "EXECUTING"} className="shrink-0 text-[13px]" />}
          {!p.signedOff ? <Tag>未審批</Tag> : null}
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-wg-muted">
          <span>Lv.{p.autonomyLevel} 自治</span>
          <span>目標 {p.goalsCount}</span>
          <span>
            任務 {p.tasksDone} / {p.tasksCount}
          </span>
          {deleted ? <span data-testid="deleted-at">刪除於 {formatDateTime(p.deletedAt)}</span> : <span>更新 {formatDate(p.updatedAt)}</span>}
          <span className="font-mono break-all">{p.executionPath}</span>
        </div>
      </div>
      <div className="flex shrink-0 gap-1.5">
        {deleted ? (
          <Button
            size="sm"
            data-testid="project-restore"
            aria-label={`復原專案：${p.name}`}
            loading={restoring}
            disabled={!canWrite || !onRestore}
            title={canWrite ? undefined : "權限不足（唯讀角色）"}
            onClick={() => onRestore?.(p)}
          >
            復原
          </Button>
        ) : (
          <>
            <Button asChild variant="ghost" size="sm">
              <Link href={`/projects/${p.id}`}>查看</Link>
            </Button>
            <Button variant="ghost" size="sm" onClick={() => onEdit(p.id)} disabled={!canWrite} title={canWrite ? undefined : "權限不足（唯讀角色）"}>
              編輯
            </Button>
            <Button asChild variant="ghost" size="sm">
              <Link href={`/projects/${p.id}/execute`}>執行</Link>
            </Button>
            <Button asChild variant="ghost" size="sm">
              <Link href={`/projects/${p.id}/monitor`}>監控</Link>
            </Button>
          </>
        )}
      </div>
    </Card>
  );
}
