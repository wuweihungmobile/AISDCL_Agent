"use client";

import { Search } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";

import { Card, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import type { StreamState } from "@/lib/api/sse";
import { visibleLines, type LiveState, type LogLine } from "@/lib/domain/runLive";
import { formatClock } from "@/lib/format";
import { cn } from "@/lib/utils";
import { SseDot } from "./parts";

/** 終端機配色（設計稿：深色面板 #1c241a、文字 #d7e4cd）；狀態變化用強調色插一行，告警與錯誤各用警示色。 */
function lineClass(line: LogLine): string {
  if (line.kind === "status") return "font-semibold text-wg-accent";
  if (line.level === "ERROR" || line.level === "CRITICAL") return "text-wg-error";
  if (line.level === "WARN") return "text-wg-warning";
  if (line.kind === "engine") return "opacity-60";
  return "";
}

/**
 * 「即時日誌」卡（設計稿畫面 7；契約 §4.2 E-14、E-15；PRD US-E-03）：
 * 深色終端、高 240px、自動捲動開關、搜尋過濾、「SSE 串流」狀態點。
 * 預設只看步驟摘要、狀態變化、告警與審核（STEP／狀態／告警）；引擎原始 stdout 量大，另設「顯示引擎原始輸出」開關。
 */
export function LiveLogCard({
  live,
  connection,
  onReconnect,
}: {
  live: LiveState;
  connection: StreamState;
  onReconnect: () => void;
}) {
  const [query, setQuery] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const [showEngine, setShowEngine] = useState(false);
  const searchId = useId();
  const box = useRef<HTMLDivElement>(null);

  const all = useMemo(() => visibleLines(live, showEngine), [live, showEngine]);
  const q = query.trim().toLowerCase();
  const shown = useMemo(() => (q ? all.filter((l) => l.message.toLowerCase().includes(q)) : all), [all, q]);

  // 自動捲到底：新行進來、或切換顯示內容時
  useEffect(() => {
    if (autoScroll && box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [autoScroll, shown.length]);

  return (
    <Card className="mt-6 px-[22px] py-5" data-testid="log-card">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div className="flex items-center gap-3">
          <CardTitle>即時日誌</CardTitle>
          <SseDot state={connection} onReconnect={onReconnect} />
        </div>
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <label className="flex cursor-pointer items-center gap-2">
            <Checkbox checked={autoScroll} onCheckedChange={(v) => setAutoScroll(v === true)} data-testid="log-autoscroll" aria-label="自動捲動" />
            自動捲動
          </label>
          <label className="flex cursor-pointer items-center gap-2">
            <Checkbox checked={showEngine} onCheckedChange={(v) => setShowEngine(v === true)} data-testid="log-engine-toggle" aria-label="顯示引擎原始輸出" />
            顯示引擎原始輸出
          </label>
          <div className="relative w-[220px] max-sm:w-full">
            <label htmlFor={searchId} className="sr-only">
              搜尋日誌
            </label>
            <Search size={16} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-wg-muted" aria-hidden />
            <Input
              id={searchId}
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜尋日誌…"
              className="min-h-9 py-1.5 pl-9 text-sm"
              data-testid="log-search"
            />
          </div>
          <span className="text-xs text-wg-muted" aria-live="polite" data-testid="log-count">
            {q ? `${shown.length} / ${all.length} 行` : `${all.length} 行`}
          </span>
        </div>
      </div>
      <div
        ref={box}
        id="exec-log"
        role="log"
        aria-label="即時執行日誌"
        tabIndex={0}
        data-testid="log-box"
        className="h-[240px] overflow-y-auto rounded-md bg-wg-terminal px-4 py-3.5 font-mono text-[13px] leading-[1.8] text-wg-terminal-text"
      >
        {all.length === 0 ? (
          <div className="opacity-60">（尚無日誌；批次啟動後，步驟、狀態變化與告警會即時出現在這裡）</div>
        ) : shown.length === 0 ? (
          <div className="opacity-60">（沒有符合「{query.trim()}」的日誌行）</div>
        ) : (
          shown.map((l) => (
            <div key={l.key} data-testid="log-line" data-kind={l.kind} className={cn("break-words whitespace-pre-wrap", lineClass(l))}>
              <span className="opacity-60">[{formatClock(l.ts)}]</span> {l.message}
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
