"use client";

/**
 * 終端窗格（FR-R2P-17；TCS-ResearchToPRD-P2-20261107 AT-962-13-*；IFACE-P2 §4）：折疊殼，內部以 `useRunStream` 餵既有 `LiveLogCard`——與執行中心共用同一個串流客戶端與日誌元件，
 * **不自己建第二份串流、不自己渲染 HTML**（純文字由 LiveLogCard 負責；本包不改它）。
 *
 * 設計要點（為什麼這樣做）：
 *  - **收合時仍訂閱**：串流 hook 住在殼層，開合只切顯示；再展開時看到收合期間累積的行，開合不重連。
 *  - **開合狀態只存瀏覽器**：`localStorage` 鍵 `research.terminal.open`；讀寫都包 try/catch，缺值或例外＝預設收合且不崩潰；狀態不進任何 API 請求。
 *  - **run 終態後以 REST 補齊**：串流伺服器在終態後會關線；窗格開啟且 run 已終態時，以既有 `listExecutionSteps(runId,{afterSeq})` 分頁取到空頁，轉成與 SSE 同形的行事件併進顯示（去重鍵相同，不重複顯示）。
 *  - **ANSI 剝除**：`LiveLogCard` 不處理 ANSI 序列（本包不改它，以勘誤回報）；窗格在餵入前剝掉，滿足純文字判準。
 *  - **`runId=null` 不訂閱**：顯示「尚無執行批次」。
 */
import { ChevronDown, ChevronRight, Terminal } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { LiveLogCard } from "@/components/domain/execute/LiveLogCard";
import { Card } from "@/components/ui/card";
import { useRunStream } from "@/hooks/useRunStream";
import { listExecutionSteps } from "@/lib/api/endpoints";
import { STEPS_MAX_PAGES, STEPS_PAGE_SIZE, useExecution } from "@/lib/api/queries";
import type { RunStreamEvent } from "@/lib/api/sse";
import { TERMINAL_OPEN_STORAGE_KEY, stripAnsi } from "@/lib/domain/research";
import { applyStreamEvents, stepToLogData } from "@/lib/domain/runLive";
import { isRunTerminal } from "@/lib/domain/status";

function readOpen(fallback: boolean): boolean {
  try {
    const raw = window.localStorage.getItem(TERMINAL_OPEN_STORAGE_KEY);
    return raw === "true" ? true : raw === "false" ? false : fallback;
  } catch {
    return fallback;
  }
}

function writeOpen(open: boolean): void {
  try {
    window.localStorage.setItem(TERMINAL_OPEN_STORAGE_KEY, String(open));
  } catch {
    // 儲存被禁用或已滿：只是不記得開合，窗格照常可用
  }
}

export function TerminalPane({ runId, defaultOpen = false }: { runId: string | null; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(() => readOpen(defaultOpen));
  const stream = useRunStream(runId);
  const run = useExecution(runId);
  const terminal = isRunTerminal(run.data?.status);
  const [backfill, setBackfill] = useState<{ runId: string; events: RunStreamEvent[] } | null>(null);

  // run 終態且窗格開著：以 afterSeq 分頁取步驟直到空頁（或頁數上限），補齊串流關線後才需要的歷史
  useEffect(() => {
    if (runId === null || !open || !terminal) return;
    let alive = true;
    void (async () => {
      const events: RunStreamEvent[] = [];
      let after = 0;
      for (let page = 0; page < STEPS_MAX_PAGES; page += 1) {
        const res = await listExecutionSteps(runId, { size: STEPS_PAGE_SIZE, afterSeq: after > 0 ? after : undefined });
        if (res.content.length === 0) break;
        for (const step of res.content) events.push({ name: "log", id: null, data: stepToLogData(step) });
        after = res.content[res.content.length - 1].stepNumber;
      }
      if (alive) setBackfill({ runId, events });
    })().catch(() => {
      // 補齊失敗：保留串流已收到的行，不顯示空白錯誤（下次開合會再試）
    });
    return () => {
      alive = false;
    };
  }, [runId, open, terminal]);

  const live = useMemo(() => {
    const merged = backfill !== null && backfill.runId === runId ? applyStreamEvents(stream.live, backfill.events) : stream.live;
    // 純文字（AC-17-3）：共用日誌元件已當文字渲染（無 HTML 注入），這裡再剝 ANSI 序列，可見文字不殘留 ESC 起頭
    const clean = (lines: typeof merged.lines) => lines.map((l) => (l.message.includes("\u001b") ? { ...l, message: stripAnsi(l.message) } : l));
    return { ...merged, lines: clean(merged.lines), engine: clean(merged.engine) };
  }, [backfill, runId, stream.live]);

  function toggle() {
    const next = !open;
    setOpen(next);
    writeOpen(next);
  }

  if (runId === null) {
    return (
      <Card data-testid="terminal-pane" data-open="false" className="flex items-center gap-2 p-4 text-sm text-wg-muted">
        <Terminal size={18} aria-hidden />
        <span className="font-semibold text-wg-text">終端窗格</span>
        <span data-testid="terminal-empty">尚無執行批次</span>
      </Card>
    );
  }
  const Chevron = open ? ChevronDown : ChevronRight;
  return (
    <section data-testid="terminal-pane" data-open={String(open)} aria-label="終端窗格" className="flex flex-col">
      <button
        type="button"
        data-testid="terminal-toggle"
        aria-expanded={open}
        onClick={toggle}
        className="flex items-center gap-2 self-start rounded-md border border-wg-line px-4 py-2 text-sm font-semibold hover:bg-wg-surface-alt"
      >
        <Chevron size={16} aria-hidden />
        <Terminal size={18} aria-hidden />
        終端窗格
      </button>
      {open ? <LiveLogCard live={live} connection={stream.connection} onReconnect={stream.reconnect} /> : null}
    </section>
  );
}
