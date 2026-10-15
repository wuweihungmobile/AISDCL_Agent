"use client";

import { Download, FileText, LayoutGrid, RotateCcw, Settings } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { describeError, saveBlob } from "@/lib/api/client";
import { useDownloadReport } from "@/lib/api/queries";
import { rangeParams, type RangeId } from "@/lib/domain/metrics";

/**
 * 底部行動列（設計稿畫面 8 與 PRD §5.4.5）：「匯出報表」「匯出 PDF」「設定告警」「自訂儀表板」。
 *  - 匯出報表／匯出 PDF：GET report?format=csv｜pdf（不包封包的檔案下載，檔名取自 Content-Disposition；v1.2 起 PDF 與 CSV 同樣回 200，
 *    內容是同一份四個區段，C-4）。匯出範圍＝目前的時間範圍與批次選擇。
 *  - 設定告警：導向 /settings（契約 §4.3 M-17：監控分頁 monitor.*，沒有專用端點）。
 *  - 自訂儀表板：切換編輯模式，各區塊出現拖曳把手（US-M-08；版面存 localStorage）。
 */
export function ExportBar({
  projectId,
  range,
  runId,
  editing,
  onToggleEditing,
  onResetLayout,
}: {
  projectId: string;
  range: RangeId;
  runId: string | undefined;
  editing: boolean;
  onToggleEditing: () => void;
  onResetLayout: () => void;
}) {
  const toast = useToast();
  const download = useDownloadReport();

  async function exportReport(format: "csv" | "pdf") {
    try {
      const { blob, filename } = await download.mutateAsync({ projectId, params: { format, runId, ...rangeParams(range) } });
      const name = filename ?? `monitor-report.${format}`;
      saveBlob(blob, name);
      toast.success(`已匯出報表：${name}`);
    } catch (err) {
      toast.error(`匯出失敗：${describeError(err)}`);
    }
  }

  return (
    <div className="mt-6 flex flex-wrap items-center gap-2.5" data-testid="monitor-actions">
      <Button iconLeft={Download} onClick={() => void exportReport("csv")} loading={download.isPending && download.variables?.params.format === "csv"} data-testid="export-csv">
        匯出報表
      </Button>
      <Button variant="ghost" iconLeft={FileText} onClick={() => void exportReport("pdf")} loading={download.isPending && download.variables?.params.format === "pdf"} data-testid="export-pdf">
        匯出 PDF
      </Button>
      <Button asChild variant="ghost" iconLeft={Settings}>
        <Link href="/settings" data-testid="alert-settings-link">
          設定告警
        </Link>
      </Button>
      <Button variant={editing ? "solid" : "ghost"} iconLeft={LayoutGrid} onClick={onToggleEditing} aria-pressed={editing} data-testid="layout-toggle">
        {editing ? "完成自訂" : "自訂儀表板"}
      </Button>
      {editing ? (
        <Button variant="ghost" iconLeft={RotateCcw} onClick={onResetLayout} data-testid="layout-reset">
          重設版面
        </Button>
      ) : null}
    </div>
  );
}
