"use client";

/**
 * PRD 版本差異（中欄的 Diff 模式；FR-R2P-09；TCS-ResearchToPRD-P0-20261102 AT-960-16-2、17-1、17-3；AC-R2P-09-2、09-8、09-9；ADR-003 D9）：
 * 選兩個版本（A 舊、B 新）逐行比對，`+ 新增`、`- 刪除` 以前綴符號加文字標籤呈現（不只靠顏色），可一鍵對調 A／B。
 *
 * 設計要點（為什麼這樣做）：
 *  - **行級、無 DOM 的比對函式庫，只在 Diff 模式才下載**：`diff` 以 `import("diff")` 動態載入（AC-R2P-09-9；AST 掃描釘住只有本檔這樣載入）。
 *    進函式庫前先用 `lib/domain/research.ts` 的 `splitLines` 把換行正規化（CRLF 與 LF 等價、結尾換行不多算一行），所以與確定性比對 `diffLines` 對同一輸入逐行相同。
 *  - **最壞情況有界**：兩版幾乎整份重寫時，Myers 演算法的成本隨編輯數增長（200KB 實測改動 90% 的行約 1.3 秒），所以帶 `maxEditLength`（取 `DIFF_MAX_EDITS`）；
 *    超過就退回 `lib/domain/research.ts` 的 `diffLines`（同一個上限，超界改成「整段刪除加整段新增」——合法但不最小）。計算耗時以 `data-diff-ms` 暴露給效能探針。
 *  - **畫面行數也要有界**：逐行結果超過 `DIFF_FOLD_MIN_ROWS` 列時，只展開變更行與其前後 `DIFF_CONTEXT_LINES` 行，其餘相同的行收成一列「顯示其餘 N 行相同的內容」（可展開）；\n *    200KB 的 PRD 只改幾處時，DOM 只有幾十列，不是五千列；不長的文件全部展開，與確定性比對逐行相同。
 *  - **凍結版可比對、不可編輯**：選到 BASELINE 時標示唯讀（`data-readonly`）；比對本身永遠唯讀，編輯器的唯讀由 StudioPanel 依專案狀態決定。
 *  - 版本內文取自 `GET …/prd/versions/{n}`（資料庫版本，不是瀏覽器暫存）；文字一律當純文字渲染。
 */
import { ArrowLeftRight, Lock } from "lucide-react";
import { useEffect, useId, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { usePrdVersion } from "@/lib/api/queries";
import type { ResearchPrdVersion } from "@/lib/api/types";
import { DIFF_MAX_EDITS, diffLines as referenceDiffLines, splitLines, type DiffLine } from "@/lib/domain/research";
import { cn } from "@/lib/utils";

/** 變更行前後各保留幾行上下文；更遠的相同行收合。 */
export const DIFF_CONTEXT_LINES = 3;
/** 逐行結果不超過這個列數就全部展開（一般的 PRD 改動直接看得完，也與確定性比對逐行相同）；更長的才收合遠離變更的相同行。 */
export const DIFF_FOLD_MIN_ROWS = 200;

/** 進比對函式庫前的正規化：與 `diffLines`（lib/domain）同一套切行規則，每行以換行結尾，空文件為空字串。 */
export function normalizeForDiff(text: string): string {
  const lines = splitLines(text);
  return lines.length === 0 ? "" : `${lines.join("\n")}\n`;
}

/** 函式庫回傳的區塊（`added`／`removed`／相同）展開成逐行結果，行號自 1 起算；刪除行只有 A 行號、新增行只有 B 行號。 */
export function diffRowsFromParts(parts: ReadonlyArray<{ value: string; added?: boolean; removed?: boolean }>): DiffLine[] {
  const rows: DiffLine[] = [];
  let aLine = 0;
  let bLine = 0;
  for (const part of parts) {
    const lines = part.value.split("\n");
    if (lines[lines.length - 1] === "") lines.pop();
    for (const text of lines) {
      if (part.added === true) {
        bLine += 1;
        rows.push({ kind: "add", text, aLine: null, bLine });
      } else if (part.removed === true) {
        aLine += 1;
        rows.push({ kind: "remove", text, aLine, bLine: null });
      } else {
        aLine += 1;
        bLine += 1;
        rows.push({ kind: "same", text, aLine, bLine });
      }
    }
  }
  return rows;
}

export type DiffComputation = { rows: DiffLine[]; engine: "library" | "fallback"; ms: number };

/** 兩份文字的逐行比對：函式庫優先、超過編輯上限退回確定性比對。第一次呼叫才下載 `diff`。 */
export async function computeDiffRows(a: string, b: string): Promise<DiffComputation> {
  const { diffLines } = await import("diff");
  const start = performance.now();
  const parts = diffLines(normalizeForDiff(a), normalizeForDiff(b), { maxEditLength: DIFF_MAX_EDITS });
  const result: Omit<DiffComputation, "ms"> = parts === undefined ? { rows: referenceDiffLines(a, b), engine: "fallback" } : { rows: diffRowsFromParts(parts), engine: "library" };
  return { ...result, ms: Math.round(performance.now() - start) };
}

export type FoldedRow = { type: "row"; row: DiffLine } | { type: "fold"; from: number; rows: DiffLine[] };

/**
 * 收合遠離變更的相同行：每個變更行前後各 `context` 行照常顯示，其餘連續的相同行收成一列（不足兩行不值得收，照常顯示）。
 * 逐行結果不超過 `minRows` 列時不收合。`from` 是這一段在逐行結果裡的起始索引（展開狀態的鍵）。
 */
export function foldRows(rows: readonly DiffLine[], { context = DIFF_CONTEXT_LINES, minRows = DIFF_FOLD_MIN_ROWS }: { context?: number; minRows?: number } = {}): FoldedRow[] {
  if (rows.length <= minRows) return rows.map((row) => ({ type: "row", row }));
  const keep = new Array<boolean>(rows.length).fill(false);
  rows.forEach((row, i) => {
    if (row.kind === "same") return;
    for (let k = Math.max(0, i - context); k <= Math.min(rows.length - 1, i + context); k += 1) keep[k] = true;
  });
  const out: FoldedRow[] = [];
  let i = 0;
  while (i < rows.length) {
    if (keep[i]) {
      out.push({ type: "row", row: rows[i] });
      i += 1;
      continue;
    }
    let j = i;
    while (j < rows.length && !keep[j]) j += 1;
    if (j - i >= 2) out.push({ type: "fold", from: i, rows: rows.slice(i, j) });
    else for (let k = i; k < j; k += 1) out.push({ type: "row", row: rows[k] });
    i = j;
  }
  return out;
}

const ROW_LABEL: Readonly<Record<DiffLine["kind"], { sign: string; text: string }>> = {
  add: { sign: "+", text: "新增" },
  remove: { sign: "-", text: "刪除" },
  same: { sign: "", text: "" },
};

function DiffRow({ row }: { row: DiffLine }) {
  const label = ROW_LABEL[row.kind];
  return (
    <li
      data-testid="diff-row"
      data-kind={row.kind}
      data-a-line={row.aLine ?? undefined}
      data-b-line={row.bLine ?? undefined}
      className={cn("grid grid-cols-[3rem_3rem_4.5rem_minmax(0,1fr)] gap-x-2 px-2 py-0.5 text-sm", row.kind === "add" && "bg-wg-tertiary", row.kind === "remove" && "bg-wg-draft-bg")}
    >
      <span aria-hidden className="text-right text-xs text-wg-muted">
        {row.aLine ?? ""}
      </span>
      <span aria-hidden className="text-right text-xs text-wg-muted">
        {row.bLine ?? ""}
      </span>
      <span data-testid="diff-label" className="font-mono text-xs font-semibold whitespace-nowrap">
        {label.sign === "" ? "" : `${label.sign} ${label.text}`}
      </span>
      <code className="min-h-[1.5em] font-mono break-words whitespace-pre-wrap">{row.text}</code>
    </li>
  );
}

function DiffRows({ rows }: { rows: readonly DiffLine[] }) {
  const folded = useMemo(() => foldRows(rows), [rows]);
  const [expanded, setExpanded] = useState<ReadonlySet<number>>(new Set());
  return (
    <ol data-testid="diff-rows" className="font-mono">
      {folded.map((item) =>
        item.type === "row" ? (
          <DiffRow key={`r${item.row.aLine ?? "-"}:${item.row.bLine ?? "-"}:${item.row.kind}`} row={item.row} />
        ) : expanded.has(item.from) ? (
          item.rows.map((row) => <DiffRow key={`r${row.aLine}:${row.bLine}:same`} row={row} />)
        ) : (
          <li key={`f${item.from}`} data-testid="diff-fold" className="px-2 py-1 text-center">
            <Button variant="ghost" size="sm" onClick={() => setExpanded((prev) => new Set(prev).add(item.from))}>
              顯示其餘 {item.rows.length} 行相同的內容
            </Button>
          </li>
        ),
      )}
    </ol>
  );
}

const versionLabel = (v: ResearchPrdVersion): string => `${v.semver}（第 ${v.versionNo} 版・${v.authorKind === "HUMAN" ? "人工" : "AI"}${v.kind === "BASELINE" ? "・凍結基線" : ""}）`;

type Settled = ({ a: string; b: string } & ({ done: DiffComputation } | { error: string })) | null;

export function PrdDiffView({ researchId, versions }: { researchId: string; versions: readonly ResearchPrdVersion[] }) {
  const idBase = useId();
  const sorted = useMemo(() => [...versions].sort((x, y) => x.versionNo - y.versionNo), [versions]);
  const latest = sorted[sorted.length - 1];
  const previous = sorted.length >= 2 ? sorted[sorted.length - 2] : latest;
  const [pickA, setPickA] = useState<number | null>(null);
  const [pickB, setPickB] = useState<number | null>(null);
  const aNo = pickA ?? previous?.versionNo ?? null;
  const bNo = pickB ?? latest?.versionNo ?? null;
  const aQuery = usePrdVersion(researchId, aNo);
  const bQuery = usePrdVersion(researchId, bNo);
  const aText = aQuery.data?.content;
  const bText = bQuery.data?.content;
  const [settled, setSettled] = useState<Settled>(null);

  useEffect(() => {
    if (aText === undefined || bText === undefined) return;
    let alive = true;
    computeDiffRows(aText, bText).then(
      (done) => {
        if (alive) setSettled({ a: aText, b: bText, done });
      },
      (error: unknown) => {
        if (alive) setSettled({ a: aText, b: bText, error: error instanceof Error ? error.message : "比對失敗" });
      },
    );
    return () => {
      alive = false;
    };
  }, [aText, bText]);

  if (sorted.length < 2) return <EmptyState title="還沒有可以比對的版本" description="PRD 至少要有兩個版本才能比對；草擬或儲存新版本後這裡就會出現差異。" />;

  const current = settled !== null && settled.a === aText && settled.b === bText ? settled : null;
  const versionA = sorted.find((v) => v.versionNo === aNo);
  const versionB = sorted.find((v) => v.versionNo === bNo);
  const frozen = versionA?.kind === "BASELINE" || versionB?.kind === "BASELINE";
  const loadError = aQuery.error ?? bQuery.error;
  const rows = current !== null && "done" in current ? current.done.rows : null;
  const added = rows?.filter((r) => r.kind === "add").length ?? 0;
  const removed = rows?.filter((r) => r.kind === "remove").length ?? 0;

  return (
    <section
      data-testid="prd-diff"
      aria-label="PRD 版本差異"
      data-readonly={frozen || undefined}
      data-diff-ms={current !== null && "done" in current ? current.done.ms : undefined}
      data-diff-engine={current !== null && "done" in current ? current.done.engine : undefined}
      className="flex flex-col gap-3"
    >
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex min-w-0 flex-col gap-1 text-sm font-medium" htmlFor={`${idBase}-a`}>
          版本 A（舊）
          <Select id={`${idBase}-a`} size="sm" value={aNo ?? ""} onChange={(e) => setPickA(Number(e.target.value))}>
            {sorted.map((v) => (
              <option key={v.versionNo} value={v.versionNo}>
                {versionLabel(v)}
              </option>
            ))}
          </Select>
        </label>
        <Button
          variant="ghost"
          size="sm"
          iconLeft={ArrowLeftRight}
          onClick={() => {
            setPickA(bNo);
            setPickB(aNo);
          }}
        >
          對調 A／B
        </Button>
        <label className="flex min-w-0 flex-col gap-1 text-sm font-medium" htmlFor={`${idBase}-b`}>
          版本 B（新）
          <Select id={`${idBase}-b`} size="sm" value={bNo ?? ""} onChange={(e) => setPickB(Number(e.target.value))}>
            {sorted.map((v) => (
              <option key={v.versionNo} value={v.versionNo}>
                {versionLabel(v)}
              </option>
            ))}
          </Select>
        </label>
      </div>
      {frozen ? (
        <p role="note" data-testid="diff-frozen-note" className="flex items-center gap-2 text-sm text-wg-muted">
          <Lock size={16} aria-hidden />
          比對含凍結版本（BASELINE）：凍結版只能比對、不能編輯。
        </p>
      ) : null}
      {loadError ? <ErrorState error={loadError} title="無法載入版本內容" onRetry={() => void Promise.all([aQuery.refetch(), bQuery.refetch()])} /> : null}
      {current !== null && "error" in current ? <ErrorState error={new Error(current.error)} title="比對失敗" /> : null}
      {rows === null && !loadError && current === null ? (
        <div aria-busy="true" aria-label="正在比對">
          <Skeleton className="h-32 rounded-md" />
        </div>
      ) : null}
      {rows !== null ? (
        <>
          <p role="status" data-testid="diff-summary" className="text-sm text-wg-muted">
            {added + removed === 0 ? "兩個版本的內容相同，沒有差異。" : `新增 ${added} 行、刪除 ${removed} 行（相同的行共 ${rows.length - added - removed} 行）`}
          </p>
          {added + removed === 0 ? null : (
            <div role="region" aria-label="差異內容" tabIndex={0} className="max-h-[70vh] overflow-auto rounded-md border border-wg-line bg-wg-surface">
              <DiffRows key={`${aNo}:${bNo}`} rows={rows} />
            </div>
          )}
        </>
      ) : null}
    </section>
  );
}
