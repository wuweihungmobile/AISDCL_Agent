"use client";

/**
 * 排序控制列（TCS-ConsoleUxSortHelp W-UX5）：給沒有表頭的列表（專案卡片、研究專案列）。
 * 一個「排序」下拉（選項即欄位）加一顆方向按鈕；`options` 為空陣列時不渲染下拉。
 */
import { ArrowDown, ArrowUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import type { SortState } from "@/lib/domain/sorting";

export type SortBarOption = { key: string; label: string };

export type SortBarProps = {
  options: ReadonlyArray<SortBarOption>;
  /** 目前排序（受控；不可為 null，預設序由呼叫端以 state 初值表達） */
  state: NonNullable<SortState>;
  onChange: (next: NonNullable<SortState>) => void;
  /** group 的 aria-label */
  label: string;
};

export const SORT_DIR_ASC_LABEL = "目前由小到大，按一下改由大到小";
export const SORT_DIR_DESC_LABEL = "目前由大到小，按一下改由小到大";

export function SortBar({ options, state, onChange, label }: SortBarProps) {
  const asc = state.dir === "asc";
  return (
    <div role="group" aria-label={label} className="flex items-center gap-1.5">
      {options.length > 0 ? (
        <Select size="sm" aria-label="排序" value={state.key} onChange={(e) => onChange({ key: e.target.value, dir: state.dir })}>
          {options.map((o) => (
            <option key={o.key} value={o.key}>
              {o.label}
            </option>
          ))}
        </Select>
      ) : null}
      <Button type="button" variant="ghost" size="sm" aria-label={asc ? SORT_DIR_ASC_LABEL : SORT_DIR_DESC_LABEL} onClick={() => onChange({ key: state.key, dir: asc ? "desc" : "asc" })}>
        {asc ? <ArrowUp size={14} aria-hidden="true" /> : <ArrowDown size={14} aria-hidden="true" />}
      </Button>
    </div>
  );
}
