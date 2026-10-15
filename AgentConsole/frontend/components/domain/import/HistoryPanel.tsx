"use client";

import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { StatusLabel } from "@/components/ui/status-dot";
import { useImports } from "@/lib/api/queries";
import type { ImportStatus } from "@/lib/api/types";
import { IMPORT_STATUS, importStatus, isImportReopenable, isLive } from "@/lib/domain/status";
import { formatDateTime, formatNumber } from "@/lib/format";

const PAGE_SIZE = 10;

/**
 * 歷史記錄 tab（US-I-06；契約 §4.1 I-17）：匯入時間、來源檔名、狀態、產生的專案連結、aiModel／tokenUsed，分頁。
 * 仍有下一步的記錄（已上傳、已解析、審核中）可「開啟」回到步驟流程（唯讀角色也能開啟檢視，寫入動作由步驟卡自己停用）；
 * 終態（已匯入、已放棄）與解析中不開。
 */
export function HistoryPanel({ onOpen }: { onOpen: (id: string) => void }) {
  const [status, setStatus] = useState<"" | ImportStatus>("");
  // 換篩選就回第 1 頁：頁碼連同條件鍵一起存，鍵不符即視為第 1 頁
  const [paging, setPaging] = useState({ key: "", page: 1 });
  const page = paging.key === status ? paging.page : 1;
  const query = useImports({ page: page - 1, size: PAGE_SIZE, status: status || undefined, sort: "createdAt,desc" });
  const data = query.data;
  const totalPages = Math.max(1, data?.totalPages ?? 1);

  return (
    <div data-testid="import-history-panel">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <span className="text-sm text-wg-muted">共 {data?.totalElements ?? 0} 筆匯入記錄</span>
        <Select size="sm" aria-label="依狀態篩選" value={status} onChange={(e) => setStatus(e.target.value as "" | ImportStatus)}>
          <option value="">全部狀態</option>
          {(Object.keys(IMPORT_STATUS) as ImportStatus[]).map((s) => (
            <option key={s} value={s}>
              {IMPORT_STATUS[s].label}
            </option>
          ))}
        </Select>
      </div>

      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} title="無法載入匯入歷史" />
      ) : !data ? (
        <div aria-busy="true" aria-label="匯入歷史載入中" className="flex flex-col gap-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-11" />
          ))}
        </div>
      ) : data.content.length === 0 ? (
        <EmptyState title="還沒有匯入記錄" description="上傳檔案或貼上文字並解析後，記錄會出現在這裡。" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] border-collapse text-sm" data-testid="import-history">
            <thead>
              <tr className="text-left text-xs text-wg-muted">
                <th className="pr-3 pb-2 font-medium">匯入時間</th>
                <th className="pr-3 pb-2 font-medium">來源</th>
                <th className="pr-3 pb-2 font-medium">狀態</th>
                <th className="pr-3 pb-2 font-medium">專案</th>
                <th className="pr-3 pb-2 font-medium">AI 模型 · Token</th>
                <th className="pb-2" />
              </tr>
            </thead>
            <tbody>
              {data.content.map((r) => (
                <tr key={r.id} data-testid="import-history-row" data-status={r.status} className="border-t border-wg-line">
                  <td className="py-2.5 pr-3 font-mono text-xs whitespace-nowrap">{formatDateTime(r.createdAt)}</td>
                  <td className="py-2.5 pr-3 break-all">{r.sourceFileName ?? "（貼上文字）"}</td>
                  <td className="py-2.5 pr-3 whitespace-nowrap">
                    <StatusLabel meta={importStatus(r.status)} live={isLive(r.status)} className="text-[13px]" />
                  </td>
                  <td className="py-2.5 pr-3 whitespace-nowrap">
                    {r.projectId ? (
                      <Link href={`/projects/${r.projectId}`} className="text-wg-primary transition-opacity hover:opacity-85">
                        查看專案
                      </Link>
                    ) : (
                      <span className="text-wg-muted">—</span>
                    )}
                  </td>
                  <td className="py-2.5 pr-3 text-xs whitespace-nowrap text-wg-muted">
                    {r.aiModel ?? "—"} · {formatNumber(r.tokenUsed)}
                  </td>
                  <td className="py-1.5 text-right">
                    {isImportReopenable(r.status) ? (
                      <Button variant="ghost" size="sm" aria-label={`開啟匯入記錄：${r.sourceFileName ?? "貼上文字"}`} onClick={() => onOpen(r.id)}>
                        開啟
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 ? <Pagination className="mt-5" page={page} totalPages={totalPages} onPageChange={(p) => setPaging({ key: status, page: p })} /> : null}
    </div>
  );
}
