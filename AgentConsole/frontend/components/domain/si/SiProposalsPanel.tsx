"use client";

/**
 * 提案分頁（P1b；TCS-SelfImprovingMirror-P1b R14、R16、R18）：`GET /api/v1/si/proposals` 的游標分頁清單。
 * 每筆一列（ID／狀態／類別／route／rev／digest 前 8 碼／verdict／cooldown）；待決（proposed、verified）預設展開、其餘可展開。
 * 展開區的卡面 `<pre data-testid="si-card-<ID>">` 的 textContent 逐位元組等於 export 的 `card`（`si card` 的 stdout）：
 * 前端不渲染、不重排行、不裁切、不加前後綴，單一文字節點；card 為 null 時顯示「卡面量不到」並指向對應的 ne 項，不渲染空的卡面區。
 */
import { Fragment, useState } from "react";

import { useSiProposals } from "@/lib/api/queries";
import type { SiProposal } from "@/lib/api/types";
import {
  EMPTY_PROPOSAL_FILTERS,
  cardNeEntries,
  describeTouched,
  describeValue,
  digest8,
  distinctValues,
  filterProposals,
  formatNe,
  identityKey,
  mergeNotes,
  mergePages,
  notEvaluableText,
  type ProposalFilters,
} from "@/lib/domain/si";
import { ExpandToggle, FilterSelect, SiError, SiLoadMore, SiLoading, SiNotes, SiScopeNote, countText, useReportTabCount, withAll } from "./siParts";

const COLUMNS = 9;
/** 待決提案：等人看卡面的狀態，預設展開。 */
const PENDING_STATES: ReadonlySet<string> = new Set(["proposed", "verified"]);

/** `nullIsNe`：該欄的 null 是「量不到」而不是「無」（R16）——touched／touchedCount 在 rN.patch 讀不到時為 null，空集合是 `[]` 與 `0`。 */
const OTHER_FIELDS: ReadonlyArray<{ key: keyof SiProposal & string; label: string; nullIsNe?: boolean }> = [
  { key: "action", label: "action" },
  { key: "run", label: "run" },
  { key: "target", label: "target" },
  { key: "touched", label: "touched", nullIsNe: true },
  { key: "touchedCount", label: "touchedCount", nullIsNe: true },
  { key: "sources", label: "sources" },
  { key: "createdSeq", label: "createdSeq" },
  { key: "lastSeq", label: "lastSeq" },
  { key: "flags", label: "flags" },
];

/** 卡面為 null 時這裡不渲染卡面區（「卡面量不到」與對應 ne 項由提案列顯示）；其餘欄位照列。 */
function ProposalDetail({ p, id }: { p: SiProposal; id: string }) {
  return (
    <div id={id} data-testid={`si-prop-detail-${p.id}`} className="flex flex-col gap-3">
      {p.card === null ? null : (
        <pre data-testid={`si-card-${p.id}`} className="overflow-x-auto rounded-md border border-wg-line bg-wg-surface p-3 font-mono text-xs leading-relaxed">
          {p.card}
        </pre>
      )}
      <dl className="grid grid-cols-1 gap-x-6 gap-y-1 text-sm md:grid-cols-[8rem_1fr]">
        {OTHER_FIELDS.map(({ key, label, nullIsNe }) => (
          <div key={key} className="contents">
            <dt className="text-wg-muted">{label}</dt>
            <dd data-testid={`si-prop-field-${p.id}-${key}`} className="break-all">
              {nullIsNe ? describeTouched(p[key]) : describeValue(p[key])}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function SiProposalsPanel({ onCount }: { onCount: (text: string | null) => void }) {
  const q = useSiProposals();
  const [filters, setFilters] = useState<ProposalFilters>(EMPTY_PROPOSAL_FILTERS);
  const [open, setOpen] = useState<Record<string, boolean>>({});

  const pages = q.data?.pages;
  const last = pages?.[pages.length - 1];
  const items: SiProposal[] = pages
    ? mergePages(
        pages.map((p) => p.items),
        identityKey,
      )
    : [];
  const ready = !q.isError && last !== undefined;
  useReportTabCount(onCount, ready ? countText(items.length, last.truncated) : null);

  if (q.isError) return <SiError error={q.error} onRetry={() => void q.refetch()} />;
  if (!pages || !last) return <SiLoading what="提案" />;

  const ne = mergeNotes(pages.map((p) => p.ne));
  const shown = filterProposals(items, filters);
  const set = <K extends keyof ProposalFilters>(key: K, value: string) => setFilters((prev) => ({ ...prev, [key]: value }));

  return (
    <div>
      <SiNotes ne={ne} problems={mergeNotes(pages.map((p) => p.problems))} />

      <div className="mb-3 flex flex-wrap items-center gap-x-5 gap-y-2">
        <FilterSelect label="狀態" testId="si-filter-state" value={filters.state} options={withAll(distinctValues(items, (p) => p.state))} onChange={(v) => set("state", v)} />
        <FilterSelect label="類別" testId="si-filter-cls" value={filters.cls} options={withAll(distinctValues(items, (p) => p.cls))} onChange={(v) => set("cls", v)} />
      </div>
      {last.truncated ? <SiScopeNote loaded={items.length} /> : null}

      {items.length === 0 ? (
        <p data-testid="si-empty" className="py-4 text-sm text-wg-muted">
          目前沒有任何提案。
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table data-testid="si-prop-table" className="w-full min-w-[52rem] border-collapse text-left text-sm">
            <caption className="sr-only">提案</caption>
            <thead>
              <tr className="border-b border-wg-line text-xs text-wg-muted">
                <th scope="col" className="w-10 py-2">
                  <span className="sr-only">操作</span>
                </th>
                {["ID", "狀態", "類別", "route", "rev", "digest", "verdict", "cooldown"].map((h) => (
                  <th key={h} scope="col" className="py-2 pr-3">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {shown.map((p) => {
                const expanded = open[p.id] ?? PENDING_STATES.has(p.state);
                const detailId = `si-prop-detail-panel-${p.id}`;
                const cardNe = p.card === null ? cardNeEntries(ne, p.id) : [];
                return (
                  <Fragment key={identityKey(p)}>
                    <tr data-testid={`si-prop-row-${p.id}`} className="border-b border-wg-line align-top">
                      <td className="py-1.5">
                        <ExpandToggle name={p.id} expanded={expanded} controls={detailId} onToggle={() => setOpen((prev) => ({ ...prev, [p.id]: !expanded }))} />
                      </td>
                      <td className="py-2 pr-3 font-mono text-xs">
                        {p.id}
                        {p.card === null ? (
                          <span data-testid={`si-card-ne-${p.id}`} className="mt-1 block font-sans text-xs text-wg-warning-text">
                            {`卡面${notEvaluableText()}${cardNe.length > 0 ? `；對應 ne 項：${cardNe.map(formatNe).join("；")}` : ""}`}
                          </span>
                        ) : null}
                      </td>
                      <td className="py-2 pr-3">{p.state}</td>
                      <td className="py-2 pr-3">{p.cls}</td>
                      <td className="py-2 pr-3">{p.route}</td>
                      <td className="py-2 pr-3">{p.rev}</td>
                      <td className="py-2 pr-3 font-mono text-xs" title={p.digest}>
                        {digest8(p.digest)}
                      </td>
                      <td className="py-2 pr-3 break-all">{describeValue(p.verdict)}</td>
                      <td className="py-2 break-all">{describeValue(p.cooldown)}</td>
                    </tr>
                    {expanded ? (
                      <tr className="border-b border-wg-line bg-wg-base">
                        <td colSpan={COLUMNS} className="px-4 py-3">
                          <ProposalDetail p={p} id={detailId} />
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

      {shown.length === 0 && items.length > 0 ? <p className="py-3 text-sm text-wg-muted">沒有符合目前篩選的提案。</p> : null}

      <SiLoadMore hasNext={q.hasNextPage} truncated={last.truncated} fetching={q.isFetchingNextPage} onLoadMore={() => void q.fetchNextPage()} />
    </div>
  );
}
