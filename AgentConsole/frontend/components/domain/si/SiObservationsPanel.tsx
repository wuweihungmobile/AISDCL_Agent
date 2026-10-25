"use client";

/**
 * 觀察分頁（P1b；TCS-SelfImprovingMirror-P1b R14、R15、R17、R18）：`GET /api/v1/si/observations` 的游標分頁清單。
 * 每筆一列（ID／時間／分類／嚴重度／處置／症狀；DOM 文字是完整字串，截斷只靠 CSS），可展開看九欄原文與 marksKv、行號、模組桶；
 * 無法解析的壞列永遠顯示（原文逐字）、不受任何篩選影響。篩選只作用於已載入的頁；模組桶只讀資料自帶的 `buckets`，缺席時停用並說明。
 * P2b：給了寫入回呼（只有 ADMIN）時多出三個入口——工具列的「新增觀察」（`si-obs-new`）、每個**有效列**的「更正」（`si-obs-correct-<ID>`；壞列沒有 id、不提供）、
 * 以及處置**恰為 open** 的有效列的「關閉」（`si-close-open-<ID>`）。沒給＝與 P1b 逐位元組相同的唯讀畫面。
 */
import { Fragment, useState } from "react";

import { Button } from "@/components/ui/button";
import { useSiObservations } from "@/lib/api/queries";
import type { SiObservation, SiObservationRow } from "@/lib/api/types";
import {
  EMPTY_OBS_FILTERS,
  DATE_WINDOW_OPTIONS,
  bucketOptions,
  dispositionKey,
  distinctValues,
  filterObservations,
  hasBucketData,
  identityKey,
  inDateWindow,
  isInvalidRow,
  mergeNotes,
  mergePages,
  type DateWindow,
  type ObsFilters,
} from "@/lib/domain/si";
import { ExpandToggle, FilterSelect, SiError, SiLoadMore, SiLoading, SiNotes, SiScopeNote, countText, useReportTabCount, withAll } from "./siParts";

const BASE_COLUMNS = 7;

/** P2b 的寫入入口回呼（只有 ADMIN 才會傳）：新增一列、更正某列、關閉某列（只對處置恰為 open 的有效列）。 */
export type ObservationWriteActions = { onNew: () => void; onCorrect: (id: string) => void; onCloseObservation: (id: string) => void };

/** 展開後的九欄：標籤逐字取自帳本表頭（ID、時間、情境、症狀、證據座標、分類、嚴重度、處置、標記）。 */
const NINE_FIELDS: ReadonlyArray<{ key: keyof SiObservation & string; label: string }> = [
  { key: "id", label: "ID" },
  { key: "time", label: "時間" },
  { key: "context", label: "情境" },
  { key: "symptom", label: "症狀" },
  { key: "evidence", label: "證據座標" },
  { key: "category", label: "分類" },
  { key: "severity", label: "嚴重度" },
  { key: "disposition", label: "處置" },
  { key: "marks", label: "標記" },
];

function ObservationFields({ row, id }: { row: SiObservation; id: string }) {
  const marks = Object.entries(row.marksKv ?? {});
  return (
    <dl id={id} data-testid={`si-obs-fields-${row.id}`} className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm md:grid-cols-[8rem_1fr]">
      {NINE_FIELDS.map(({ key, label }) => (
        <div key={key} className="contents">
          <dt className="text-wg-muted">{label}</dt>
          <dd data-testid={`si-obs-field-${row.id}-${key}`} className="break-words whitespace-pre-wrap">
            {String(row[key] ?? "")}
          </dd>
        </div>
      ))}
      <div className="contents">
        <dt className="text-wg-muted">標記（解析後）</dt>
        <dd data-testid={`si-obs-field-${row.id}-marksKv`}>
          {marks.length === 0 ? (
            "無"
          ) : (
            <ul className="list-disc pl-5">
              {marks.map(([k, v]) => (
                <li key={k} className="break-words">{`${k}：${v}`}</li>
              ))}
            </ul>
          )}
        </dd>
      </div>
      <div className="contents">
        <dt className="text-wg-muted">帳本行號</dt>
        <dd data-testid={`si-obs-field-${row.id}-line`}>{String(row.line)}</dd>
      </div>
      {Array.isArray(row.buckets) ? (
        <div className="contents">
          <dt className="text-wg-muted">模組桶</dt>
          <dd data-testid={`si-obs-field-${row.id}-buckets`}>{row.buckets.length === 0 ? "無" : row.buckets.join("、")}</dd>
        </div>
      ) : null}
    </dl>
  );
}

export function SiObservationsPanel({ onCount, actions }: { onCount: (text: string | null) => void; actions?: ObservationWriteActions }) {
  const columns = actions ? BASE_COLUMNS + 1 : BASE_COLUMNS;
  const q = useSiObservations();
  const [filters, setFilters] = useState<ObsFilters>(EMPTY_OBS_FILTERS);
  const [open, setOpen] = useState<Record<string, boolean>>({});

  const pages = q.data?.pages;
  const last = pages?.[pages.length - 1];
  const items: SiObservationRow[] = pages
    ? mergePages(
        pages.map((p) => p.items),
        identityKey,
      )
    : [];
  const ready = !q.isError && last !== undefined;
  useReportTabCount(onCount, ready ? countText(items.length, last.truncated) : null);

  if (q.isError) return <SiError error={q.error} onRetry={() => void q.refetch()} />;
  if (!pages || !last) return <SiLoading what="觀察" />;

  const anchor = last.generatedAt;
  const valid = items.filter((r): r is SiObservation => !isInvalidRow(r));
  const shown = filterObservations(items, filters, anchor);
  const bucketsPresent = hasBucketData(items);
  const set = <K extends keyof ObsFilters>(key: K, value: ObsFilters[K]) => setFilters((prev) => ({ ...prev, [key]: value }));

  return (
    <div>
      <SiNotes ne={mergeNotes(pages.map((p) => p.ne))} problems={mergeNotes(pages.map((p) => p.problems))} />

      <div className="mb-3 flex flex-wrap items-center gap-x-5 gap-y-2">
        <FilterSelect label="分類" testId="si-filter-category" value={filters.category} options={withAll(distinctValues(valid, (r) => r.category))} onChange={(v) => set("category", v)} />
        <FilterSelect label="嚴重度" testId="si-filter-severity" value={filters.severity} options={withAll(distinctValues(valid, (r) => r.severity))} onChange={(v) => set("severity", v)} />
        <FilterSelect
          label="處置"
          testId="si-filter-disposition"
          value={filters.disposition}
          options={withAll(distinctValues(valid, (r) => dispositionKey(r.disposition)))}
          onChange={(v) => set("disposition", v)}
        />
        <FilterSelect label="模組桶" testId="si-filter-bucket" value={filters.bucket} disabled={!bucketsPresent} options={withAll(bucketOptions(items))} onChange={(v) => set("bucket", v)} />
        <FilterSelect
          label="時間窗"
          testId="si-filter-window"
          value={filters.window}
          options={DATE_WINDOW_OPTIONS.map((o) => ({ value: o.id, label: o.label }))}
          onChange={(v) => set("window", v as DateWindow)}
        />
        {bucketsPresent ? null : (
          <span data-testid="si-bucket-note" className="text-xs text-wg-muted">
            此版本的 export 尚無模組桶欄（待根層 P2 交付）
          </span>
        )}
        {actions ? (
          <Button size="sm" className="ml-auto" data-testid="si-obs-new" onClick={actions.onNew}>
            新增觀察
          </Button>
        ) : null}
      </div>
      {last.truncated ? <SiScopeNote loaded={items.length} /> : null}

      {items.length === 0 ? (
        <p data-testid="si-empty" className="py-4 text-sm text-wg-muted">
          帳本目前沒有觀察列。
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table data-testid="si-obs-table" className="w-full min-w-[56rem] table-fixed border-collapse text-left text-sm">
            <caption className="sr-only">觀察帳本</caption>
            <thead>
              <tr className="border-b border-wg-line text-xs text-wg-muted">
                <th scope="col" className="w-10 py-2">
                  <span className="sr-only">操作</span>
                </th>
                <th scope="col" className="w-28 py-2 pr-3">
                  ID
                </th>
                <th scope="col" className="w-40 py-2 pr-3">
                  時間
                </th>
                <th scope="col" className="w-24 py-2 pr-3">
                  分類
                </th>
                <th scope="col" className="w-20 py-2 pr-3">
                  嚴重度
                </th>
                <th scope="col" className="w-48 py-2 pr-3">
                  處置
                </th>
                <th scope="col" className="py-2">
                  症狀
                </th>
                {actions ? (
                  <th scope="col" className="w-36 py-2 pl-3">
                    <span className="sr-only">寫入操作</span>
                  </th>
                ) : null}
              </tr>
            </thead>
            <tbody>
              {shown.map((row) => {
                if (isInvalidRow(row)) {
                  return (
                    <tr key={identityKey(row)} data-testid={`si-obs-invalid-${row.line}`} className="border-b border-wg-line align-top">
                      <td colSpan={columns} className="py-2">
                        <p className="font-medium text-wg-accent">{`無法解析的列（第 ${row.line} 行）`}</p>
                        <pre className="mt-1 overflow-x-auto font-mono text-xs break-all whitespace-pre-wrap">{row.raw}</pre>
                      </td>
                    </tr>
                  );
                }
                const expanded = open[row.id] === true;
                const fieldsId = `si-obs-fields-panel-${row.id}`;
                const unparsable = filters.window !== "all" && inDateWindow(row.time, anchor, filters.window) === "unparsable";
                return (
                  <Fragment key={identityKey(row)}>
                    <tr data-testid={`si-obs-row-${row.id}`} className="border-b border-wg-line align-top">
                      <td className="py-1.5">
                        <ExpandToggle name={row.id} expanded={expanded} controls={fieldsId} onToggle={() => setOpen((prev) => ({ ...prev, [row.id]: !expanded }))} />
                      </td>
                      <td className="py-2 pr-3 font-mono text-xs">{row.id}</td>
                      <td className="py-2 pr-3">
                        {row.time}
                        {unparsable ? (
                          <span data-testid={`si-time-unparsable-${row.id}`} className="ml-1 text-xs text-wg-warning-text">
                            時間無法解析
                          </span>
                        ) : null}
                      </td>
                      <td className="py-2 pr-3">{row.category}</td>
                      <td className="py-2 pr-3">{row.severity}</td>
                      <td className="truncate py-2 pr-3" title={row.disposition}>
                        {row.disposition}
                      </td>
                      <td className="truncate py-2" title={row.symptom}>
                        {row.symptom}
                      </td>
                      {actions ? (
                        <td className="py-1.5 pl-3">
                          <div className="flex gap-1">
                            <Button variant="ghost" size="sm" aria-label={`更正 ${row.id}`} data-testid={`si-obs-correct-${row.id}`} onClick={() => actions.onCorrect(row.id)}>
                              更正
                            </Button>
                            {row.disposition === "open" ? (
                              <Button variant="ghost" size="sm" aria-label={`關閉 ${row.id}`} data-testid={`si-close-open-${row.id}`} onClick={() => actions.onCloseObservation(row.id)}>
                                關閉
                              </Button>
                            ) : null}
                          </div>
                        </td>
                      ) : null}
                    </tr>
                    {expanded ? (
                      <tr className="border-b border-wg-line bg-wg-base">
                        <td colSpan={columns} className="px-4 py-3">
                          <ObservationFields row={row} id={fieldsId} />
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* 壞列永遠顯示、不算「符合」：有效列一筆都不符合時要說，否則只剩壞列的畫面看不出有效列為什麼不見了 */}
      {valid.length > 0 && !shown.some((row) => !isInvalidRow(row)) ? <p className="py-3 text-sm text-wg-muted">沒有符合目前篩選的觀察列。</p> : null}

      <SiLoadMore hasNext={q.hasNextPage} truncated={last.truncated} fetching={q.isFetchingNextPage} onLoadMore={() => void q.fetchNextPage()} />
    </div>
  );
}
