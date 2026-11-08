"use client";

/**
 * 可排序表頭（TCS-ConsoleUxSortHelp W-UX2）：`<th scope="col" aria-sort>` 內含 `<button type="button">`。
 *  - `<th>` 的 textContent 必須嚴格等於欄名：圖示 aria-hidden、不加 sr-only 補字、不加 aria-label（凍結的表頭字樣鎖；排序狀態只靠 aria-sort 表達）。
 *  - `state` 為 null 時以 `defaultSort` 顯示預設序對應的欄（起始 aria-sort 即為該方向）。
 *  - 兩鍵欄（匯入歷史「AI 模型 · Token」）以 `second` 傳第二個鍵，渲染兩顆按鈕、中間文字節點「 · 」。
 */
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";

import type { SortState } from "@/lib/domain/sorting";

export type SortableHeaderProps = {
  /** 欄鍵（對應 `SortColumn.key`） */
  column: string;
  label: string;
  state: SortState;
  onSort: (key: string) => void;
  /** 預設序對應某欄時的顯示（不影響 state）。 */
  defaultSort?: SortState;
  /** 兩鍵欄的第二個鍵 */
  second?: { column: string; label: string };
  className?: string;
};

function SortButton({ column, label, eff, onSort }: { column: string; label: string; eff: SortState; onSort: (key: string) => void }) {
  const active = eff?.key === column;
  const Icon = !active ? ArrowUpDown : eff.dir === "asc" ? ArrowUp : ArrowDown;
  return (
    <button type="button" data-sort-key={column} onClick={() => onSort(column)} className="inline-flex cursor-pointer items-center gap-1 font-[inherit] text-[inherit] hover:text-wg-text">
      {label}
      <Icon size={12} aria-hidden="true" className="shrink-0" />
    </button>
  );
}

export function SortableHeader({ column, label, state, onSort, defaultSort, second, className }: SortableHeaderProps) {
  const eff = state ?? defaultSort ?? null;
  const hit = eff && (eff.key === column || (second && eff.key === second.column)) ? eff : null;
  const ariaSort = hit ? (hit.dir === "asc" ? "ascending" : "descending") : "none";
  return (
    <th scope="col" aria-sort={ariaSort} className={className ?? "py-2 pr-3"}>
      <SortButton column={column} label={label} eff={eff} onSort={onSort} />
      {second ? (
        <>
          {" · "}
          <SortButton column={second.column} label={second.label} eff={eff} onSort={onSort} />
        </>
      ) : null}
    </th>
  );
}
