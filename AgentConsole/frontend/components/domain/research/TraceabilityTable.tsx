"use client";

/**
 * 追溯表（FR-R2P-20-1、20-2；TCS-ResearchToPRD-P2-20261107 AT-962-17-8、21-E-2；IFACE-P2 §6.1；D-138 Q-5、D-140 #7）：
 * 一個凍結 PRD 驗收條件（AC）一列，欄位＝AC、使用者故事、Gherkin 摘要、單元狀態、端對端狀態、最近執行時間、來源。
 *
 * 設計要點（為什麼這樣做）：
 *  - **非 `PASS` 的單元狀態列標紅且帶文字標記**（失敗／未執行／無覆蓋任務），不只靠顏色（WCAG 1.4.1）；
 *    `NONE`（沒有覆蓋任務、只靠豁免）同樣標紅——沒有自動測試通過就是沒有。
 *  - **「未覆蓋 n」只算單元欄**＝`totals.uncovered`；端對端欄在 SCG-5 登錄前恆為「未執行」，如實顯示、不計入也不標紅（IFACE §6.1：零測試不是通過，但 E2E 欄不阻擋 Tag）。
 *  - **全部純文字**：`gherkinSummary`、`userStory`、`source` 都是 React 文字節點，沒有 `dangerouslySetInnerHTML`、沒有 `img`、沒有 `on*` 屬性（AT-962-21-E-2）。
 *  - `rtm`（RTM 彙總，諮詢視圖；`advisory` 恆 true）顯示「諮詢」標記：它不是閘門，閘門只看未覆蓋數與狀態機現態。
 */
import { CircleAlert, CircleCheck } from "lucide-react";
import { useState } from "react";

import { SortableHeader } from "@/components/domain/common/SortableHeader";
import type { ResearchTraceRow, ResearchTraceStatus, ResearchTraceability } from "@/lib/api/types";
import { DELIVER_LABEL } from "@/lib/domain/research";
import { nextSort, sortRows, type SortColumn, type SortState } from "@/lib/domain/sorting";

/** 狀態的文字標記（單一登記處；ReleaseActions 的未覆蓋清單也用它）。 */
export const TRACE_STATUS_TEXT: Readonly<Record<ResearchTraceStatus, string>> = {
  PASS: "通過",
  FAIL: "失敗",
  NOT_RUN: "未執行",
  NONE: "無覆蓋任務",
};

/** 單元狀態不是 `PASS` 的列（＝未覆蓋清單）。 */
export const uncoveredRows = (rows: readonly ResearchTraceRow[]): ResearchTraceRow[] => rows.filter((row) => row.unitStatus !== "PASS");

/** Gherkin 三段的標籤（摘要為純文字，標籤固定；缺段顯示空）。 */
const GHERKIN_LABEL = { given: "Given", when: "When", then: "Then" } as const;

const statusText = (status: ResearchTraceStatus): string => TRACE_STATUS_TEXT[status] ?? status;

/** 表頭排序（TCS-ConsoleUxSortHelp §2.1 T9）：預設 AC 自然序升冪（與 Bridge sorted(frozen.acs) 同序）；列首 `<th scope="row">` 維持。 */
const SORT_COLUMNS: ReadonlyArray<SortColumn<ResearchTraceRow> & { label: string }> = [
  { key: "ac", label: "AC", kind: "id", get: (r) => r.ac },
  { key: "userStory", label: "使用者故事", kind: "text", get: (r) => r.userStory },
  { key: "gherkin", label: "Gherkin 摘要", kind: "text", get: (r) => `${r.gherkinSummary.given} ${r.gherkinSummary.when} ${r.gherkinSummary.then}` },
  { key: "unit", label: "單元狀態", kind: "text", get: (r) => statusText(r.unitStatus) },
  { key: "e2e", label: "端對端狀態", kind: "text", get: (r) => statusText(r.e2eStatus) },
  { key: "lastRunAt", label: "最近執行", kind: "iso", get: (r) => r.lastRunAt },
  { key: "source", label: "來源", kind: "text", get: (r) => (r.source.length === 0 ? null : r.source.join(" ")) },
];
const DEFAULT_SORT: NonNullable<SortState> = { key: "ac", dir: "asc" };

export function TraceabilityTable({ data }: { data: ResearchTraceability }) {
  const { totals, rtm } = data;
  const [sort, setSort] = useState<SortState>(null);
  const rows = sortRows(data.rows, SORT_COLUMNS, sort ?? DEFAULT_SORT);
  return (
    <section data-testid="traceability-table" aria-label={DELIVER_LABEL.traceability} className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        <h4 className="text-base font-semibold">{DELIVER_LABEL.traceability}</h4>
        <span data-testid="trace-total">AC 共 {totals.acTotal} 條</span>
        <span data-testid="trace-covered">已覆蓋 {totals.covered}</span>
        <span data-testid="trace-uncovered" data-count={totals.uncovered} className={totals.uncovered > 0 ? "font-semibold text-wg-error" : "text-wg-muted"}>
          {DELIVER_LABEL.uncovered} {totals.uncovered}
        </span>
        {rtm !== null ? (
          <span data-testid="trace-rtm" className="text-wg-muted">
            <span className="mr-1 rounded border border-wg-line px-1.5 py-0.5 text-xs">諮詢</span>
            RTM 覆蓋率 {rtm.acPct}%，{rtm.fullyCovered ? "完全覆蓋" : "尚未完全覆蓋"}
          </span>
        ) : (
          <span data-testid="trace-rtm-none" className="text-wg-muted">
            尚無 RTM 彙總
          </span>
        )}
      </div>
      {/* 窄視窗時表格在這個區域內左右捲動：區域可聚焦並有名稱，鍵盤才捲得動（axe scrollable-region-focusable） */}
      <div role="region" aria-label="追溯表捲動區" tabIndex={0} className="overflow-x-auto">
        <table aria-label={`${DELIVER_LABEL.traceability}：一個驗收條件一列`} className="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-wg-line text-left text-xs text-wg-muted">
              {SORT_COLUMNS.map((c) => (
                <SortableHeader
                  key={c.key}
                  column={c.key}
                  label={c.label}
                  state={sort}
                  defaultSort={DEFAULT_SORT}
                  onSort={(key) => setSort((s) => nextSort(s, key, DEFAULT_SORT))}
                  className="px-2 py-1.5 font-medium"
                />
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const red = row.unitStatus !== "PASS";
              return (
                <tr
                  key={row.ac}
                  data-testid="trace-row"
                  data-ac={row.ac}
                  data-unit={row.unitStatus}
                  data-red={red ? "true" : "false"}
                  className={red ? "border-b border-wg-line bg-wg-draft-bg" : "border-b border-wg-line"}
                >
                  <th scope="row" className="px-2 py-1.5 text-left font-mono font-medium">
                    {row.ac}
                  </th>
                  <td className="px-2 py-1.5">{row.userStory}</td>
                  <td className="max-w-[320px] px-2 py-1.5 break-words" data-testid="trace-gherkin">
                    {(["given", "when", "then"] as const).map((key) => (
                      <p key={key} data-testid={`trace-gherkin-${key}`}>
                        <span className="mr-1 font-semibold text-wg-muted">{GHERKIN_LABEL[key]}</span> {row.gherkinSummary[key]}
                      </p>
                    ))}
                  </td>
                  <td className="px-2 py-1.5">
                    <span data-testid="trace-unit" className={red ? "inline-flex items-center gap-1 font-semibold text-wg-error" : "inline-flex items-center gap-1"}>
                      {red ? <CircleAlert size={14} aria-hidden /> : <CircleCheck size={14} aria-hidden />}
                      {statusText(row.unitStatus)}
                    </span>
                  </td>
                  <td className="px-2 py-1.5 text-wg-muted" data-testid="trace-e2e">
                    {statusText(row.e2eStatus)}
                  </td>
                  <td className="px-2 py-1.5 whitespace-nowrap text-wg-muted">{row.lastRunAt ?? "—"}</td>
                  <td className="px-2 py-1.5 font-mono text-xs break-all" data-testid="trace-source">
                    {row.source.length === 0 ? (
                      <span className="text-wg-muted">無</span>
                    ) : (
                      <ul className="list-none">
                        {row.source.map((s) => (
                          <li key={s}>{s}</li>
                        ))}
                      </ul>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
