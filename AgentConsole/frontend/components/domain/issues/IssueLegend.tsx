"use client";

/**
 * 狀態說明對話框（TCS-IssueCenter-20261027 R-IC-63；PRD §5.4、§7）：狀態、結果、來源、嚴重度各一行（名稱＋一句話），說明文字**逐字取自**清單回應的
 * `legend`——前端沒有第二份說明，圖例換字、這裡跟著換。已完成議題的日期是「最後已知動靜」而非結案日，註記同樣取自 `legend.updatedAtNote`，
 * 回應沒帶這個鍵就不顯示（不寫死）。純文字：圖例字串一律以 React 文字節點渲染。
 * 對話框內除了標題與四個分組標題，**沒有任何寫死的說明文字**（連給螢幕閱讀器的 description 也不給：那會是第二份說明），AT-IC-08-2-E-1 以哨兵字串驗證。
 */
import { Dialog, DialogBody, DialogContent } from "@/components/ui/dialog";
import type { IssueLegend as Legend } from "@/lib/api/types";

type Row = { name: string; meaning: string };

function Group({ title, rows, testId }: { title: string; rows: ReadonlyArray<Row>; testId: string }) {
  return (
    <section aria-label={title} data-testid={testId}>
      <h3 className="text-base font-semibold">{title}</h3>
      <dl className="mt-1.5 grid grid-cols-[7rem_1fr] gap-x-4 gap-y-1.5 text-sm">
        {rows.map((row) => (
          <div key={row.name} className="contents">
            <dt className="font-medium">{row.name}</dt>
            <dd className="text-wg-muted">{row.meaning}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export function IssueLegend({ legend, open, onClose }: { legend: Legend | undefined; open: boolean; onClose: () => void }) {
  return (
    <Dialog open={open && legend !== undefined} onOpenChange={(next) => !next && onClose()}>
      {legend ? (
        <DialogContent data-testid="issues-legend-dialog" title="狀態說明">
          <DialogBody>
            <Group title="狀態" rows={legend.statuses} testId="issues-legend-statuses" />
            <Group title="結果" rows={legend.results} testId="issues-legend-results" />
            <Group title="來源" rows={legend.sources} testId="issues-legend-sources" />
            <Group title="嚴重度" rows={legend.severities} testId="issues-legend-severities" />
            {legend.updatedAtNote ? (
              <p data-testid="issues-legend-note" className="rounded-md border border-wg-line bg-wg-base px-3 py-2 text-sm">
                {legend.updatedAtNote}
              </p>
            ) : null}
          </DialogBody>
        </DialogContent>
      ) : null}
    </Dialog>
  );
}
