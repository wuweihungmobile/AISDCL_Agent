"use client";

/**
 * 事件分頁（P1b；TCS-SelfImprovingMirror-P1b R14、R15、R16、⚖10）：上半「運轉」表（`GET /api/v1/si/runs`）、下半「事件帳本」列表
 * （`GET /api/v1/si/events`）——兩個各自獨立的查詢，各有 loading／error／ok 三態，一邊失敗不影響另一邊。
 * 事件詳情顯示收到的物件（camelCase 鍵、值不動）的縮排 JSON 純文字（⚖3）。事件載體不存在時，export 會回空 items 加 carrier-not-established 的 ne 項：
 * 這時顯示「量不到」的說明，不得只顯示沒有事件。
 */
import { Fragment, useState, type ReactNode } from "react";

import { useSiEvents, useSiRuns } from "@/lib/api/queries";
import type { SiEvent, SiRun } from "@/lib/api/types";
import {
  DATE_WINDOW_OPTIONS,
  EMPTY_EVENT_FILTERS,
  distinctValues,
  filterEvents,
  formatNe,
  identityKey,
  mergeNotes,
  mergePages,
  notEvaluableText,
  prettyJson,
  type DateWindow,
  type EventFilters,
} from "@/lib/domain/si";
import { ExpandToggle, FilterSelect, SiError, SiLoadMore, SiLoading, SiNotes, SiScopeNote, countText, useReportTabCount, withAll } from "./siParts";

const EMPTY = "無";

function outcomeText(outcome: Record<string, string> | null | undefined): string {
  const entries = Object.entries(outcome ?? {});
  return entries.length === 0 ? EMPTY : entries.map(([id, state]) => `${id}：${state}`).join("；");
}

/** 運轉表：欄＝id、trigger、openedSeq、closedSeq（null＝未結束）、outcome（提案→結果）、propIds、research。 */
function RunsSection() {
  const q = useSiRuns();
  const pages = q.data?.pages;
  const last = pages?.[pages.length - 1];

  let body: ReactNode;
  if (q.isError) {
    body = <SiError error={q.error} onRetry={() => void q.refetch()} />;
  } else if (!pages || !last) {
    body = <SiLoading what="運轉" />;
  } else {
    const runs: SiRun[] = mergePages(
      pages.map((p) => p.items),
      identityKey,
    );
    body = (
      <div>
        <SiNotes ne={mergeNotes(pages.map((p) => p.ne))} problems={mergeNotes(pages.map((p) => p.problems))} />
        {runs.length === 0 ? (
          <p data-testid="si-runs-empty" className="py-2 text-sm text-wg-muted">
            目前沒有運轉紀錄。
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table data-testid="si-runs-table" className="w-full min-w-[44rem] border-collapse text-left text-sm">
              <caption className="sr-only">運轉</caption>
              <thead>
                <tr className="border-b border-wg-line text-xs text-wg-muted">
                  {["ID", "trigger", "openedSeq", "closedSeq", "outcome", "propIds", "research"].map((h) => (
                    <th key={h} scope="col" className="py-2 pr-3">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={identityKey(r)} data-testid={`si-run-row-${r.id}`} className="border-b border-wg-line align-top">
                    <td data-field="id" className="py-2 pr-3 font-mono text-xs">
                      {r.id}
                    </td>
                    <td data-field="trigger" className="py-2 pr-3">
                      {r.trigger}
                    </td>
                    <td data-field="openedSeq" className="py-2 pr-3">
                      {String(r.openedSeq)}
                    </td>
                    <td data-field="closedSeq" className="py-2 pr-3">
                      {r.closedSeq === null ? "未結束" : String(r.closedSeq)}
                    </td>
                    <td data-field="outcome" className="py-2 pr-3 break-all">
                      {outcomeText(r.outcome)}
                    </td>
                    <td data-field="propIds" className="py-2 pr-3 break-all">
                      {r.propIds.length === 0 ? EMPTY : r.propIds.join("、")}
                    </td>
                    <td data-field="research" className="py-2 break-all">
                      {r.research ? `${r.research.kind} #${r.research.seq}` : EMPTY}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <SiLoadMore hasNext={q.hasNextPage} truncated={last.truncated} fetching={q.isFetchingNextPage} onLoadMore={() => void q.fetchNextPage()} label="載入更多運轉" testId="si-load-more-runs" />
      </div>
    );
  }

  return (
    <section aria-labelledby="si-runs-title" data-testid="si-runs-section" className="mb-6">
      <h2 id="si-runs-title" className="mb-2 text-base font-semibold">
        運轉
      </h2>
      {body}
    </section>
  );
}

function EventsSection({ onCount }: { onCount: (text: string | null) => void }) {
  const q = useSiEvents();
  const [filters, setFilters] = useState<EventFilters>(EMPTY_EVENT_FILTERS);
  const [open, setOpen] = useState<Record<string, boolean>>({});

  const pages = q.data?.pages;
  const last = pages?.[pages.length - 1];
  const items: SiEvent[] = pages
    ? mergePages(
        pages.map((p) => p.items),
        identityKey,
      )
    : [];
  const ready = !q.isError && last !== undefined;
  useReportTabCount(onCount, ready ? countText(items.length, last.truncated) : null);

  let body: ReactNode;
  if (q.isError) {
    body = <SiError error={q.error} onRetry={() => void q.refetch()} />;
  } else if (!pages || !last) {
    body = <SiLoading what="事件" />;
  } else {
    const ne = mergeNotes(pages.map((p) => p.ne));
    const carrier = ne.filter((entry) => entry.field === "events" && entry.reason === "carrier-not-established");
    const shown = filterEvents(items, filters, last.generatedAt);
    body = (
      <div>
        <SiNotes ne={ne} problems={mergeNotes(pages.map((p) => p.problems))} />
        <div className="mb-3 flex flex-wrap items-center gap-x-5 gap-y-2">
          <FilterSelect
            label="種類"
            testId="si-filter-kind"
            value={filters.kind}
            options={withAll(distinctValues(items, (e) => e.kind))}
            onChange={(v) => setFilters((prev) => ({ ...prev, kind: v }))}
          />
          <FilterSelect
            label="時間窗"
            testId="si-filter-events-window"
            value={filters.window}
            options={DATE_WINDOW_OPTIONS.map((o) => ({ value: o.id, label: o.label }))}
            onChange={(v) => setFilters((prev) => ({ ...prev, window: v as DateWindow }))}
          />
        </div>
        {last.truncated ? <SiScopeNote loaded={items.length} /> : null}

        {items.length === 0 ? (
          carrier.length > 0 ? (
            <p data-testid="si-events-ne" className="py-2 text-sm text-wg-warning-text">
              {`事件帳本${notEvaluableText(carrier.map(formatNe).join("；"))}`}
            </p>
          ) : (
            <p data-testid="si-empty" className="py-2 text-sm text-wg-muted">
              事件帳本目前沒有事件。
            </p>
          )
        ) : (
          <div className="overflow-x-auto">
            <table data-testid="si-events-table" className="w-full min-w-[40rem] border-collapse text-left text-sm">
              <caption className="sr-only">事件帳本</caption>
              <thead>
                <tr className="border-b border-wg-line text-xs text-wg-muted">
                  <th scope="col" className="w-10 py-2">
                    <span className="sr-only">操作</span>
                  </th>
                  {["seq", "t", "kind", "by"].map((h) => (
                    <th key={h} scope="col" className="py-2 pr-3">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {shown.map((e) => {
                  const key = String(e.seq);
                  const expanded = open[key] === true;
                  const jsonId = `si-event-json-panel-${key}`;
                  return (
                    <Fragment key={identityKey(e)}>
                      <tr data-testid={`si-event-row-${key}`} className="border-b border-wg-line align-top">
                        <td className="py-1.5">
                          <ExpandToggle name={`事件 ${key}`} expanded={expanded} controls={jsonId} onToggle={() => setOpen((prev) => ({ ...prev, [key]: !expanded }))} />
                        </td>
                        <td data-field="seq" className="py-2 pr-3">
                          {key}
                        </td>
                        <td data-field="t" className="py-2 pr-3">
                          {e.t}
                        </td>
                        <td data-field="kind" className="py-2 pr-3">
                          {e.kind}
                        </td>
                        <td data-field="by" className="py-2">
                          {e.by}
                        </td>
                      </tr>
                      {expanded ? (
                        <tr className="border-b border-wg-line bg-wg-base">
                          <td colSpan={5} className="px-4 py-3">
                            <pre id={jsonId} data-testid={`si-event-json-${key}`} className="overflow-x-auto rounded-md border border-wg-line bg-wg-surface p-3 font-mono text-xs">
                              {prettyJson(e)}
                            </pre>
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
        {shown.length === 0 && items.length > 0 ? <p className="py-3 text-sm text-wg-muted">沒有符合目前篩選的事件。</p> : null}

        <SiLoadMore hasNext={q.hasNextPage} truncated={last.truncated} fetching={q.isFetchingNextPage} onLoadMore={() => void q.fetchNextPage()} />
      </div>
    );
  }

  return (
    <section aria-labelledby="si-events-title" data-testid="si-events-section">
      <h2 id="si-events-title" className="mb-2 text-base font-semibold">
        事件帳本
      </h2>
      {body}
    </section>
  );
}

export function SiEventsPanel({ onCount }: { onCount: (text: string | null) => void }) {
  return (
    <div>
      <RunsSection />
      <EventsSection onCount={onCount} />
    </div>
  );
}
