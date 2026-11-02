"use client";

/**
 * PRD 目錄樹（中欄編輯器的左欄；FR-R2P-09；TCS-ResearchToPRD-P0-20261102 AT-960-16-1；AC-R2P-09-1）：
 * 由 PRD 的標題與 `<!-- r2p:section=N -->` 錨點導出（痛點、功能需求、Gherkin 驗收、非功能需求、架構都是標題；錨點標出它是來源規格的第幾節），點一項就捲到對應章節。
 *
 * 設計要點（為什麼這樣做）：
 *  - **導出是純函式、逐行掃描**：`parsePrdOutline` 不經 Markdown 渲染器（目錄要在編輯當下就跟著內容變，也要在大文件上便宜）；程式碼圍欄（``` 與 ~~~）內的 `#` 行
 *    （shell 註解、Markdown 範例）不算標題；每個項目帶行索引與字元位移，編輯模式據此把游標與捲動位置移到該章節，預覽模式據此找章節容器。
 *  - **收合不是消失**：視窗 < 1280 時左欄收合為一顆圖示鈕（`collapsed`），按下展開同一份目錄清單（仍可操作、可用鍵盤、Esc 關閉）；選了項目就收回去。
 *  - 本元件只管「顯示目錄與回報選了誰」（`onSelect`），怎麼捲動由工作室依目前模式決定。
 */
import { ListTree } from "lucide-react";
import { useDeferredValue, useId, useMemo, useRef, useState } from "react";

import { Tag } from "@/components/ui/badge";
import { IconButton } from "@/components/ui/icon-button";
import { cn } from "@/lib/utils";

export type OutlineItem = {
  /** 穩定的元素 id：行索引決定（`outline-<行索引>`） */
  id: string;
  /** 標題層級 1～6 */
  level: number;
  /** 標題文字（去掉開頭的 `#` 與結尾的 `#`） */
  text: string;
  /** 標題所在的行（0 起算，以 `\n` 切行） */
  line: number;
  /** 標題行首在全文的字元位移 */
  offset: number;
  /** 標題前一行的 `<!-- r2p:section=N -->` 錨點（來源規格第 N 節）；沒有為 null */
  section: number | null;
};

/** 來源節錨點整行（`<!-- r2p:section=N -->`）：目錄用它標出「來源第 N 節」；預覽不顯示它（工作室的 `splitPrdBlocks`）。 */
export const SECTION_ANCHOR = /^\s*<!--\s*r2p:section=(\d+)\s*-->\s*$/;
/** ATX 標題：開頭至多 3 個空白（4 個以上是縮排程式碼）、1～6 個 `#`、至少一個空白或定位字元、文字、可選的結尾 `#`。 */
const ATX_HEADING = /^ {0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$/;
const FENCE = /^ {0,3}(`{3,}|~{3,})/;

/** 由 PRD 內文導出目錄（依出現順序）。 */
export function parsePrdOutline(markdown: string): OutlineItem[] {
  const items: OutlineItem[] = [];
  const lines = markdown.split("\n");
  let offset = 0;
  let fence: { char: string; size: number } | null = null;
  let pendingSection: number | null = null;
  lines.forEach((raw, line) => {
    const text = raw.endsWith("\r") ? raw.slice(0, -1) : raw;
    const lineOffset = offset;
    offset += raw.length + 1;
    const fenceMatch = FENCE.exec(text);
    if (fence !== null) {
      // 圍欄內：只認同種字元、至少一樣長、且後面沒有其他文字的行當作結尾
      if (fenceMatch !== null && fenceMatch[1][0] === fence.char && fenceMatch[1].length >= fence.size && text.trim() === fenceMatch[1]) fence = null;
      return;
    }
    if (fenceMatch !== null) {
      fence = { char: fenceMatch[1][0], size: fenceMatch[1].length };
      pendingSection = null;
      return;
    }
    const anchor = SECTION_ANCHOR.exec(text);
    if (anchor !== null) {
      pendingSection = Number(anchor[1]);
      return;
    }
    if (text.trim() === "") return; // 空行不打斷「錨點之後的第一個非空行」
    const heading = ATX_HEADING.exec(text);
    if (heading !== null && heading[2] !== "") {
      items.push({ id: `outline-${line}`, level: heading[1].length, text: heading[2].trim(), line, offset: lineOffset, section: pendingSection });
    }
    pendingSection = null;
  });
  return items;
}

/**
 * 缺陷卡的章節定位（`prdAnchor`）對應到目錄項：`r2p:section=N`／`來源第 N 節` 對錨點、`§4.2` 這類章節編號對標題開頭的編號
 * （標題前的符號與空白略過；`4.2` 不會誤中 `4.20`）、其餘文字（例如 `AC-001-1`）對標題內容（不分大小寫）。找不到回 null。
 */
export function findOutlineSection(items: readonly OutlineItem[], anchor: string): OutlineItem | null {
  const token = anchor.replace(/^[§\s]+/, "").trim();
  if (token === "") return null;
  const section = /^(?:r2p:section=|來源第\s*)(\d+)/.exec(token);
  if (section !== null) return items.find((item) => item.section === Number(section[1])) ?? null;
  if (/^\d+(?:\.\d+)*$/.test(token)) {
    return (
      items.find((item) => {
        const lead = /^[^\p{L}\p{N}]*(\d+(?:\.\d+)*)\.?(?=\s|$)/u.exec(item.text);
        return lead !== null && lead[1] === token;
      }) ?? null
    );
  }
  const lower = token.toLowerCase();
  return items.find((item) => item.text.toLowerCase().includes(lower)) ?? null;
}

function OutlineList({ items, activeId, onPick }: { items: readonly OutlineItem[]; activeId: string | null; onPick: (item: OutlineItem) => void }) {
  if (items.length === 0) return <p className="px-2 py-3 text-sm text-wg-muted">PRD 還沒有標題，目錄是空的。</p>;
  const minLevel = Math.min(...items.map((i) => i.level));
  return (
    <ol className="flex flex-col">
      {items.map((item) => (
        <li key={item.id} style={{ paddingLeft: `${(item.level - minLevel) * 0.75}rem` }}>
          <button
            type="button"
            data-testid="outline-item"
            data-line={item.line}
            data-section={item.section ?? undefined}
            aria-current={activeId === item.id ? "location" : undefined}
            onClick={() => onPick(item)}
            className={cn(
              "flex w-full cursor-pointer items-start gap-2 rounded-sm px-2 py-1 text-left text-sm transition-colors hover:bg-wg-base hover:text-wg-primary-strong",
              item.level === minLevel && "font-semibold",
              activeId === item.id && "bg-wg-tertiary",
            )}
          >
            <span className="min-w-0 flex-1 break-words">{item.text}</span>
            {item.section === null ? null : <Tag className="shrink-0">來源第 {item.section} 節</Tag>}
          </button>
        </li>
      ))}
    </ol>
  );
}

export function PrdOutline({ content, collapsed = false, activeId = null, onSelect }: { content: string; collapsed?: boolean; activeId?: string | null; onSelect: (item: OutlineItem) => void }) {
  // 目錄不在輸入的急件路徑上：打字時先更新輸入框，目錄稍後跟上（大文件逐行掃描約數毫秒，也不該拖慢每個按鍵）
  const deferred = useDeferredValue(content);
  const items = useMemo(() => parsePrdOutline(deferred), [deferred]);
  const panelId = useId();
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);

  if (!collapsed) {
    return (
      <nav data-testid="prd-outline" aria-label="PRD 目錄" className="flex flex-col gap-1">
        <h3 className="px-2 text-sm font-semibold text-wg-muted">目錄</h3>
        <OutlineList items={items} activeId={activeId} onPick={onSelect} />
      </nav>
    );
  }
  return (
    <nav
      data-testid="prd-outline"
      data-collapsed
      aria-label="PRD 目錄"
      className="relative"
      onKeyDown={(event) => {
        if (event.key === "Escape" && open) {
          setOpen(false);
          trigger.current?.focus();
        }
      }}
    >
      <IconButton ref={trigger} icon={ListTree} label={open ? "收合 PRD 目錄" : "展開 PRD 目錄"} aria-expanded={open} aria-controls={panelId} onClick={() => setOpen((v) => !v)} />
      {open ? (
        <div id={panelId} data-testid="prd-outline-panel" className="absolute top-full left-0 z-20 mt-1 max-h-[60vh] w-72 overflow-auto rounded-md border border-wg-line bg-wg-surface p-2">
          <OutlineList
            items={items}
            activeId={activeId}
            onPick={(item) => {
              setOpen(false);
              onSelect(item);
            }}
          />
        </div>
      ) : null}
    </nav>
  );
}
