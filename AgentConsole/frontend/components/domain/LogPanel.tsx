"use client";

import { Search } from "lucide-react";
import { useId, useMemo, useState } from "react";

import { Input } from "@/components/ui/input";

/**
 * 執行日誌面板（設計稿 5）：深色終端機面板 #1c241a、8px 圓角、等寬 13px、文字 #d7e4cd、最高 260px 可捲動。
 * 上方搜尋框即時過濾（不分大小寫、逐行比對；PRD US-T-05「支援搜尋與篩選」）。
 */
export function LogPanel({ log }: { log: string | null | undefined }) {
  const [query, setQuery] = useState("");
  const searchId = useId();
  const lines = useMemo(() => (log ? log.split(/\r?\n/).filter((l) => l.length > 0) : []), [log]);
  const q = query.trim().toLowerCase();
  const shown = q ? lines.filter((l) => l.toLowerCase().includes(q)) : lines;

  return (
    <div data-testid="log-panel">
      <div className="mb-3 flex items-center gap-2.5">
        <label htmlFor={searchId} className="sr-only">
          搜尋執行日誌
        </label>
        <div className="relative max-w-[320px] flex-1">
          <Search size={16} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-wg-muted" aria-hidden />
          <Input
            id={searchId}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜尋日誌…"
            className="min-h-9 py-1.5 pl-9 text-sm"
          />
        </div>
        <span className="text-xs text-wg-muted" aria-live="polite">
          {q ? `${shown.length} / ${lines.length} 行` : `${lines.length} 行`}
        </span>
      </div>
      <div
        role="log"
        aria-label="執行日誌"
        tabIndex={0}
        className="max-h-[260px] overflow-y-auto rounded-md bg-wg-terminal px-4 py-3.5 font-mono text-[13px] leading-[1.8] text-wg-terminal-text"
      >
        {lines.length === 0 ? (
          <div className="opacity-60">（尚無執行日誌；任務由執行引擎跑過之後，這裡會顯示最近一次的日誌）</div>
        ) : shown.length === 0 ? (
          <div className="opacity-60">（沒有符合「{query.trim()}」的日誌行）</div>
        ) : (
          shown.map((line, i) => <div key={`${i}-${line}`}>{line}</div>)
        )}
      </div>
    </div>
  );
}
