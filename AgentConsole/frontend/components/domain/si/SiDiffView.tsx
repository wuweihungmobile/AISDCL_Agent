"use client";

/**
 * 提案「變更內容」分頁（TCS-SiFlowVisibility AC-966-7、W-F8）：patch 文字逐行原樣顯示（純文字節點，不經 HTML 或 Markdown）。
 *  - 每行一個 `data-diff-kind` 元素，行首符號保留在文字裡；意義不只靠顏色：新增＝實線左邊框＋讀屏前綴「新增：」、刪除＝虛線左邊框＋「刪除：」、
 *    區段標頭＝粗體＋「區段：」（讀屏前綴在 `.diff-text` 之外，不污染原文）。
 *  - 預設只畫前 400 行（視窗化，防止 256 KiB 全量渲染拖垮頁面），按「展開全部」才畫完；單行超長由容器橫向捲動，元件層不截斷。
 *  - 下載＝畫面已取得的全文（零網路請求）；內容被主機截斷時檔名與旁註都明說。
 *  - patch 為 null＝量不到（沿 `ne` 的原因），空字串＝「沒有變更內容」，兩者不同句。
 */
import { Download } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { SI_FLOW_TEXTS as T, diffWindow, downloadSpec, fillText, parseDiff, reasonText, type DiffKind } from "@/lib/domain/siFlow";
import { cn } from "@/lib/utils";

export type NeWithText = { field: string; reason: string; text?: unknown };

const LINE_CLASS: Record<DiffKind, string> = {
  add: "border-l-2 border-solid border-wg-primary bg-wg-base",
  del: "border-l-2 border-dashed border-wg-alert-border bg-wg-alert-bg",
  hunk: "border-l-2 border-transparent font-bold",
  file: "border-l-2 border-transparent font-semibold",
  meta: "border-l-2 border-transparent italic",
  ctx: "border-l-2 border-transparent",
};
const PREFIX: Partial<Record<DiffKind, string>> = { add: T.diffPrefixAdd, del: T.diffPrefixDel, hunk: T.diffPrefixHunk };

/** 觸發瀏覽器下載（Blob → 暫時網址 → 點擊 → 立刻釋放）；不發任何網路請求。 */
function triggerDownload(spec: { filename: string; content: string; mime: string }): void {
  const url = URL.createObjectURL(new Blob([spec.content], { type: spec.mime }));
  const a = document.createElement("a");
  a.href = url;
  a.download = spec.filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function SiDiffView({ propId, rev, patch, ne }: { propId: string; rev: number; patch: unknown; ne: ReadonlyArray<NeWithText> }) {
  const [expanded, setExpanded] = useState(false);
  const rec = typeof patch === "object" && patch !== null && !Array.isArray(patch) ? (patch as Record<string, unknown>) : null;
  const text = rec !== null && typeof rec.text === "string" ? rec.text : null;

  if (rec === null || text === null) {
    const related = ne.filter((e) => e.field === `proposals.${propId}.detail.patch`);
    return (
      <div data-testid="si-diff-missing" className="text-sm">
        <p className="text-wg-warning-text">{T.diffMissing}</p>
        {related.length > 0 ? (
          <ul className="mt-1 list-disc pl-5">
            {related.map((e, i) => (
              <li key={`${e.reason}-${i}`} className="break-all">
                {reasonText(e.reason, e.text)}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    );
  }
  if (text === "") {
    return (
      <p data-testid="si-diff-empty" className="text-sm text-wg-muted">
        {T.diffEmpty}
      </p>
    );
  }

  const parsed = parseDiff(text);
  const win = diffWindow(parsed.lines, expanded);
  const rel = typeof rec.rel === "string" ? rec.rel : "";
  const bytes = typeof rec.bytes === "number" ? rec.bytes : null;
  const truncated = rec.truncated === true;
  const spec = downloadSpec(propId, rev, rec);

  return (
    <div data-testid="si-diff-view" className="flex flex-col gap-2 text-sm">
      <p data-testid="si-diff-summary" className="font-medium">
        {fillText(T.diffSummary, { add: parsed.addCount, del: parsed.delCount })}
      </p>
      <p className="text-xs text-wg-muted">
        <span className="font-mono break-all">{rel}</span>
        {bytes === null ? null : ` ${fillText(T.diffBytes, { bytes })}`}
      </p>
      {truncated ? (
        <p data-testid="si-diff-truncated" className="text-wg-warning-text">
          {fillText(T.diffTruncated, { rel })}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="ghost" size="sm" iconLeft={Download} data-testid="si-diff-download" onClick={() => triggerDownload(spec)}>
          {T.diffDownload}
        </Button>
        {truncated ? <span className="text-xs text-wg-muted">{T.diffDownloadTruncatedNote}</span> : null}
      </div>
      {/* 長行會讓這個容器出現捲軸：須能用鍵盤聚焦才算可用（axe scrollable-region-focusable） */}
      <div
        role="region"
        tabIndex={0}
        aria-label={T.diffScroll}
        className="overflow-x-auto rounded-md border border-wg-line bg-wg-surface font-mono text-xs leading-relaxed whitespace-pre"
        data-testid="si-diff-lines"
      >
        {win.shown.map((line, i) => (
          <div key={i} data-diff-kind={line.kind} className={cn("px-2", LINE_CLASS[line.kind])}>
            {PREFIX[line.kind] ? <span className="sr-only">{PREFIX[line.kind]}</span> : null}
            <span className="diff-text">{line.text}</span>
          </div>
        ))}
      </div>
      {win.canExpand ? (
        <div>
          <Button variant="ghost" size="sm" data-testid="si-diff-expand" aria-expanded={expanded} onClick={() => setExpanded((v) => !v)}>
            {expanded ? T.diffCollapse : fillText(T.diffExpand, { count: parsed.lines.length })}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
