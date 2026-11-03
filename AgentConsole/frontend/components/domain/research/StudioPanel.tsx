"use client";

/**
 * PRD 工作室（研究工作區步驟 2；PRD 頁面 2；FR-R2P-09、10；TCS-ResearchToPRD-P0-20261102 AT-960-16-1、16-6、16-7、16-E-1、17-1、17-2）：
 * 左欄目錄（`PrdOutline`）、中欄編輯器（編輯／預覽／Diff 三模式）、右欄審批（`GatekeeperPanel`）。面板由頁殼以 `panels={{ studio: StudioPanel }}` 注入工作區（`ResearchPanelProps`）。
 *
 * 設計要點（為什麼這樣做）：
 *  - **內容只信資料庫的版本**：編輯器顯示 head 版本的內文；使用者改過的內容是「本機工作稿」（綁定它是從第幾版開始改的），按「儲存」才送 `PUT …/prd`（帶 `baseVersion`），
 *    成功＝新增一個人工版本、舊的審查結果標「已過期」；別人（或 AI 修訂）先存了新版，後端回 409 `prd_version_conflict`，畫面顯示最新版本並提示重新整理，不覆蓋。
 *    瀏覽器儲存只放「未儲存草稿」的便利層（讀寫都包 try、清掉也不影響頁面正確性）；有未儲存內容時離開會先確認。
 *  - **唯讀不是一種樣式**：VIEWER、已凍結（Gate 0 已核准）與已完成步驟的編輯器是真的唯讀；`MarkdownEditor` 沒有唯讀模式，所以這些情況與超過 `RICH_EDIT_MAX_BYTES` 的大文件改用純文字輸入框
 *    （精簡編輯器：沒有語法高亮與即時預覽，輸入延遲不隨文件大小成長；AC-R2P-09-8 的 200KB 量測見 tests/e2e/research-studio-perf.mock.spec.ts）。
 *  - **預覽分批渲染、超界降級**：預覽把文件切成「一個標題一個區塊」逐批渲染（每批約 `PREVIEW_BATCH_CHARS` 字、排在瀏覽器閒置時），畫面不凍結；Mermaid 圍欄交給延遲載入的 `MermaidBlock`；
 *    超過 `PRD_PREVIEW_MAX_BYTES`（200KB）改顯示純文字並說明原因。預覽不渲染原始 HTML（`MarkdownView` 沒有 rehype-raw）、外部連結一律 `noopener noreferrer`。
 *    Markdown 渲染管線（`MarkdownView`）與 Mermaid 一樣延遲載入，不進 `/research/[researchId]` 的首屏 chunk（見 `BlockPreviewLazy`）。
 *  - **版面三段**：視窗 ≥ 1280 三欄、768～1279 目錄收成圖示鈕、< 768 改分頁籤（目錄、編輯器、審批）；三個區塊永遠都在 DOM 裡（只切顯示），審批欄的串流與狀態不會因切頁籤而中斷。
 *  - 外部衍生文字（PRD 內文由 AI 產生）只經 `MarkdownView`／純文字節點渲染；本檔不用 `dangerouslySetInnerHTML`。
 */
import { useQueryClient } from "@tanstack/react-query";
import { Eye, GitCompareArrows, Lock, Pencil, Save } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { memo, useCallback, useEffect, useId, useMemo, useRef, useState, useSyncExternalStore, type ComponentType } from "react";

import { MarkdownEditor } from "@/components/markdown/MarkdownEditor";
import { Button } from "@/components/ui/button";
import { PillTabs, pillPanelId, pillTabId } from "@/components/ui/pill-tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { invalidateResearch, usePrdVersion, usePrdVersions, useSavePrdVersion } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/AuthProvider";
import { READONLY_TITLE, RESEARCH_REASONS, researchErrorText } from "@/lib/domain/research";
import { cn } from "@/lib/utils";
import { GatekeeperPanel } from "./GatekeeperPanel";
import { PrdDiffView } from "./PrdDiffView";
import { PrdOutline, SECTION_ANCHOR, findOutlineSection, parsePrdOutline, type OutlineItem } from "./PrdOutline";
import type { ResearchPanelProps } from "./ResearchWorkspaceView";

// ── 常數 ─────────────────────────────────────────────────────────────────────────────

/** 預覽的完整渲染上限（位元組，UTF-8）：超過降級為純文字（AC-R2P-09-8；PRD 「≤200KB」）。 */
export const PRD_PREVIEW_MAX_BYTES = 200 * 1024;
/** 儲存的內容上限（契約：PRD 內容 ≤ 1 MiB）。 */
export const PRD_SAVE_MAX_BYTES = 1024 * 1024;
/**
 * 超過這個大小的文件，編輯模式改用純文字輸入框（精簡編輯器）。編輯器套件（`MarkdownEditor`）每個按鍵都重新渲染左右分欄的即時預覽，延遲隨文件大小近似線性成長；
 * 純文字輸入框與大小幾乎無關。實測（tests/e2e/research-studio-perf.mock.spec.ts 的編輯器套件那支與 200KB 那支；Chromium 156、Core i5-14600K、production 建置、
 * 游標在文件中段輸入 50 鍵取 P95，編輯器套件量四次、純文字輸入框量三次三輪）：編輯器套件 10KB 約 26～30ms、20KB 約 36～45ms、30KB 約 57～63ms、40KB 約 72～77ms、
 * 60KB 約 103～120ms（超過 100ms 預算）；200KB 的純文字輸入框每輪約 12～23ms。取 30KB：量測機上約 1.6 倍餘裕（比量測機慢的機器仍在預算內）；40KB 只剩約 1.3 倍，所以不取。
 */
export const RICH_EDIT_MAX_BYTES = 30 * 1024;
/**
 * 預覽每一批渲染的字數預算。每批只渲染新進來的區塊（`PreviewBlock` 是 memo）：200KB 的 PRD 約 4～5 批、全部畫完約 0.5 秒（同一台量測機），
 * 單一工作最長約 120ms；批次再小只會多排幾次閒置排程、不會讓總時間變短。
 */
export const PREVIEW_BATCH_CHARS = 20_000;
/** 未儲存草稿寫進瀏覽器儲存前的去抖（毫秒）。 */
export const DRAFT_DEBOUNCE_MS = 400;
export const DRAFT_KEY_PREFIX = "aisdlc.research.prd-draft.";
export const LEAVE_MESSAGE = "PRD 有尚未儲存的修改，確定要離開嗎？離開後這些修改可能遺失。";
const EDITOR_HEIGHT_PX = 560;

type Mode = "edit" | "preview" | "diff";

/** UTF-8 位元組數。 */
export function utf8Bytes(text: string): number {
  return new TextEncoder().encode(text).length;
}

// ── 預覽的切塊（純函式）──────────────────────────────────────────────────────────────

export type PrdSegment = { kind: "markdown"; text: string } | { kind: "mermaid"; code: string; ordinal: number };
/** 預覽的一個區塊：自一個標題行（或文件開頭）到下一個標題行之前；`line` 是起始行索引（0 起算，與目錄項的 `line` 同一套）。 */
export type PrdBlock = { line: number; chars: number; segments: PrdSegment[] };

const FENCE_OPEN = /^ {0,3}(`{3,}|~{3,})(.*)$/;
const REFERENCE_DEFINITION = /^ {0,3}\[[^\]\n]+\]:[ \t]*\S+/;

/** 圍欄結尾：同種字元、至少一樣長、行內沒有其他文字。 */
const closesFence = (line: string, fence: { char: string; size: number }): boolean => {
  const match = FENCE_OPEN.exec(line);
  return match !== null && match[1][0] === fence.char && match[1].length >= fence.size && match[2].trim() === "";
};

/** 整份文件裡的連結參照定義（`[x]: url`）：區塊各自渲染，參照式連結要能在每個區塊裡解析。 */
function referenceDefinitions(lines: readonly string[]): string[] {
  const defs: string[] = [];
  let fence: { char: string; size: number } | null = null;
  for (const raw of lines) {
    const line = raw.endsWith("\r") ? raw.slice(0, -1) : raw;
    if (fence !== null) {
      if (closesFence(line, fence)) fence = null;
      continue;
    }
    const open = FENCE_OPEN.exec(line);
    if (open !== null) fence = { char: open[1][0], size: open[1].length };
    else if (REFERENCE_DEFINITION.test(line)) defs.push(line);
  }
  return defs;
}

/**
 * 把區塊內的行切成 Markdown 文字段與 Mermaid 圖段（圍欄標記為 mermaid 者）；其他圍欄原樣留在文字段裡
 * （圍欄內出現的「```mermaid」字樣不算）。`ordinal` 是整份文件的圖序號（1 起算）。
 */
function segmentsOf(lines: readonly string[], defs: readonly string[], firstOrdinal: number): { segments: PrdSegment[]; next: number } {
  const segments: PrdSegment[] = [];
  let buffer: string[] = [];
  let ordinal = firstOrdinal;
  let fence: { char: string; size: number; mermaid: boolean } | null = null;
  let code: string[] = [];
  const flush = () => {
    const text = buffer.join("\n");
    buffer = [];
    if (text.trim() !== "") segments.push({ kind: "markdown", text: defs.length === 0 ? text : `${text}\n\n${defs.join("\n")}` });
  };
  for (const raw of lines) {
    const line = raw.endsWith("\r") ? raw.slice(0, -1) : raw;
    if (fence !== null) {
      if (closesFence(line, fence)) {
        if (fence.mermaid) {
          segments.push({ kind: "mermaid", code: code.join("\n"), ordinal });
          ordinal += 1;
          code = [];
        } else buffer.push(raw);
        fence = null;
      } else if (fence.mermaid) code.push(line);
      else buffer.push(raw);
      continue;
    }
    const open = FENCE_OPEN.exec(line);
    if (open !== null) {
      const mermaid = /^\s*mermaid\b/i.test(open[2]);
      fence = { char: open[1][0], size: open[1].length, mermaid };
      if (mermaid) flush();
      else buffer.push(raw);
      continue;
    }
    if (SECTION_ANCHOR.test(line)) continue; // 來源節錨點是給目錄用的記號：預覽不顯示（其他 HTML 與註解仍以字面文字顯示；圍欄內的照原樣）
    buffer.push(raw);
  }
  if (fence?.mermaid) {
    // 沒有結尾的圍欄吃到區塊尾
    segments.push({ kind: "mermaid", code: code.join("\n"), ordinal });
    ordinal += 1;
  } else flush();
  return { segments, next: ordinal };
}

/** PRD 內文切成預覽區塊：每個標題一個區塊（開頭的前言另成一塊），Mermaid 圍欄抽成獨立的圖段。 */
export function splitPrdBlocks(text: string): PrdBlock[] {
  const lines = text.split("\n");
  const defs = referenceDefinitions(lines);
  const boundaries = [...new Set([0, ...parsePrdOutline(text).map((item) => item.line)])].sort((a, b) => a - b);
  const blocks: PrdBlock[] = [];
  let ordinal = 1;
  boundaries.forEach((start, k) => {
    const end = k + 1 < boundaries.length ? boundaries[k + 1] : lines.length;
    const chunk = lines.slice(start, end);
    const { segments, next } = segmentsOf(chunk, defs, ordinal);
    ordinal = next;
    blocks.push({ line: start, chars: chunk.reduce((sum, l) => sum + l.length + 1, 0), segments });
  });
  return blocks;
}

/** 從第 `from` 個區塊起，累計字數達預算為止的區塊總數（至少多一個；到尾端為止）。 */
export function nextBlockCount(blocks: readonly PrdBlock[], from: number, budget: number): number {
  let used = 0;
  let i = from;
  while (i < blocks.length && (i === from || used < budget)) {
    used += blocks[i].chars;
    i += 1;
  }
  return i;
}

/** 排到瀏覽器閒置時執行（沒有 requestIdleCallback 就退回 setTimeout 0）；回傳取消函式。 */
function scheduleIdle(run: () => void): () => void {
  if (typeof window.requestIdleCallback === "function") {
    const id = window.requestIdleCallback(run, { timeout: 120 });
    return () => window.cancelIdleCallback(id);
  }
  const timer = setTimeout(run, 0);
  return () => clearTimeout(timer);
}

// ── 瀏覽器儲存的未儲存草稿（便利層；任何失敗都當沒有）────────────────────────────────────

type Local = { text: string; base: number };

function readDraft(researchId: string): Local | null {
  try {
    const raw = window.localStorage.getItem(`${DRAFT_KEY_PREFIX}${researchId}`);
    if (raw === null) return null;
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed === "object" && parsed !== null && typeof (parsed as Local).text === "string" && Number.isSafeInteger((parsed as Local).base))
      return { text: (parsed as Local).text, base: (parsed as Local).base };
  } catch {
    // 儲存不可用、被清掉或內容壞掉：當作沒有草稿
  }
  return null;
}
function writeDraft(researchId: string, draft: Local): void {
  try {
    window.localStorage.setItem(`${DRAFT_KEY_PREFIX}${researchId}`, JSON.stringify(draft));
  } catch {
    // 配額滿或被停用：草稿只是便利層，不影響編輯與儲存
  }
}
function clearDraft(researchId: string): void {
  try {
    window.localStorage.removeItem(`${DRAFT_KEY_PREFIX}${researchId}`);
  } catch {
    // 同上
  }
}

// ── 版面階層（matchMedia）與離開前確認 ─────────────────────────────────────────────────

type Tier = "wide" | "medium" | "narrow";
const WIDE_QUERY = "(min-width: 1280px)";
const MEDIUM_QUERY = "(min-width: 768px)";

function subscribeTier(onChange: () => void): () => void {
  if (typeof window.matchMedia !== "function") return () => {};
  const lists = [window.matchMedia(WIDE_QUERY), window.matchMedia(MEDIUM_QUERY)];
  for (const list of lists) list.addEventListener("change", onChange);
  return () => {
    for (const list of lists) list.removeEventListener("change", onChange);
  };
}
function tierSnapshot(): Tier {
  if (typeof window.matchMedia !== "function") return "wide";
  return window.matchMedia(WIDE_QUERY).matches ? "wide" : window.matchMedia(MEDIUM_QUERY).matches ? "medium" : "narrow";
}
/** 視窗寬度階層（沿 Console PRD §8.3：≥1280 三欄、768～1279 左欄收合為圖示、<768 分頁籤）。 */
export function useViewportTier(): Tier {
  return useSyncExternalStore(subscribeTier, tierSnapshot, () => "wide");
}

/** 有未儲存內容時：關閉分頁或重新整理（beforeunload）、站內點連結離開（click 捕獲）都先確認。瀏覽器的上一頁不在這裡攔（App Router 沒有對應的鉤子）。 */
function useLeaveGuard(active: boolean): void {
  useEffect(() => {
    if (!active) return;
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    const onClick = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const anchor = event.target instanceof Element ? event.target.closest("a[href]") : null;
      if (!(anchor instanceof HTMLAnchorElement) || anchor.target === "_blank" || anchor.hasAttribute("download")) return;
      const url = new URL(anchor.href, window.location.href);
      if (url.origin === window.location.origin && url.pathname === window.location.pathname && url.search === window.location.search) return; // 同頁的錨點跳轉
      if (!window.confirm(LEAVE_MESSAGE)) {
        event.preventDefault();
        event.stopPropagation();
      }
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    document.addEventListener("click", onClick, true);
    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
      document.removeEventListener("click", onClick, true);
    };
  }, [active]);
}

// ── 編輯器的捲動（目錄與缺陷定位用）──────────────────────────────────────────────────────

const MIRRORED_STYLES = [
  "boxSizing",
  "width",
  "fontFamily",
  "fontSize",
  "fontWeight",
  "lineHeight",
  "letterSpacing",
  "tabSize",
  "paddingTop",
  "paddingRight",
  "paddingBottom",
  "paddingLeft",
  "borderTopWidth",
  "borderRightWidth",
  "borderBottomWidth",
  "borderLeftWidth",
] as const;

/** 把輸入框的游標放到 `offset` 並捲到該處（量一個與輸入框同樣式、同寬的鏡像節點，所以自動換行也量得準）。 */
export function scrollTextareaToOffset(textarea: HTMLTextAreaElement, offset: number): void {
  textarea.focus({ preventScroll: true });
  textarea.setSelectionRange(offset, offset);
  const style = getComputedStyle(textarea);
  const mirror = document.createElement("div");
  for (const name of MIRRORED_STYLES) mirror.style[name] = style[name];
  Object.assign(mirror.style, { position: "absolute", visibility: "hidden", top: "0", left: "-9999px", height: "auto", whiteSpace: "pre-wrap", overflowWrap: "break-word" });
  mirror.textContent = textarea.value.slice(0, offset);
  const marker = document.createElement("span");
  marker.textContent = "​";
  mirror.appendChild(marker);
  document.body.appendChild(mirror);
  const top = marker.offsetTop;
  mirror.remove();
  textarea.scrollTop = Math.max(0, top - 8);
}

// ── 預覽 ─────────────────────────────────────────────────────────────────────────────

const MermaidBlockLazy = dynamic(() => import("./MermaidBlock").then((module) => module.MermaidBlock), { ssr: false, loading: () => <Skeleton className="my-3 h-24 rounded-md" /> });

/** Markdown 渲染元件（`components/markdown/MarkdownView` 的 `MarkdownView`）：本檔不靜態 import 它，預覽延遲載入完成後才以屬性拿到（見 `BlockPreviewLazy`）。 */
type MarkdownRenderer = ComponentType<{ source: string; empty?: string }>;

/**
 * 預覽的一個區塊。`memo`＋穩定的 `block` 物件（`BlockPreview` 以 `useMemo` 切一次）：後面的批次渲染進來時，已經畫好的區塊不重新跑一遍 Markdown 管線——
 * 否則每一批都把前面全部重解析，總成本隨批數平方成長（200KB 的 PRD 約 5 批，實測全部畫完約 1 秒，其中大半是重複工作）。
 */
const PreviewBlock = memo(function PreviewBlock({ block, View }: { block: PrdBlock; View: MarkdownRenderer }) {
  return (
    <section data-testid="prd-block" data-prd-line={block.line}>
      {block.segments.map((segment, i) =>
        segment.kind === "markdown" ? <View key={i} source={segment.text} empty="" /> : <MermaidBlockLazy key={i} code={segment.code} label={`Mermaid 圖表 ${segment.ordinal}`} />,
      )}
    </section>
  );
});

type BlockPreviewProps = {
  text: string;
  focusLine: number | null;
  /** 預覽（含渲染管線）備妥、掛上之後呼叫一次：工作室據此補做「預覽還在載入時收到的捲動請求」。 */
  onReady?: () => void;
};

function BlockPreview({ text, focusLine, onReady, View }: BlockPreviewProps & { View: MarkdownRenderer }) {
  const blocks = useMemo(() => splitPrdBlocks(text), [text]);
  const [shown, setShown] = useState(() => nextBlockCount(blocks, 0, PREVIEW_BATCH_CHARS));
  // 目錄點到還沒渲染的章節時，先把它之前的區塊補齊（在 render 內衍生，不需要 effect 裡設狀態）
  const needed = focusLine === null ? 0 : blocks.findIndex((block) => block.line === focusLine) + 1;
  const count = Math.min(blocks.length, Math.max(shown, needed));
  useEffect(() => {
    if (count >= blocks.length) return;
    return scheduleIdle(() => setShown(nextBlockCount(blocks, count, PREVIEW_BATCH_CHARS)));
  }, [count, blocks]);
  useEffect(() => {
    onReady?.();
  }, [onReady]);
  return (
    <div
      data-testid="prd-preview"
      data-blocks={blocks.length}
      data-rendered={count}
      role="region"
      aria-label="PRD 預覽"
      tabIndex={0}
      className="max-h-[70vh] overflow-auto rounded-md border border-wg-line bg-wg-surface px-5 py-4"
    >
      {blocks.slice(0, count).map((block) => (
        <PreviewBlock key={block.line} block={block} View={View} />
      ))}
      {count < blocks.length ? (
        <p role="status" data-testid="prd-preview-progress" className="py-2 text-sm text-wg-muted">
          正在渲染其餘章節（{count} ／ {blocks.length}）…
        </p>
      ) : null}
    </div>
  );
}

/**
 * 預覽整包延遲載入：Markdown 渲染管線（react-markdown、remark-gfm、rehype-highlight 與語法高亮的語言表，合計約 326KB／gzip 94KB）原本被本檔靜態 import，
 * 因此進了 `/research/[researchId]` 的首屏（量測：首次載入比 FE-C 之前多 54%，其中七成是這一包）；現在它是非同步 chunk，不在首屏路徑上：議題步等其他步驟、
 * 唯讀或超過 200KB 改走純文字的工作室（那條路徑完全不載入管線）都不付這一包。誠實劃界：編輯器套件（`MarkdownEditorImpl`）自己也 import 這幾個套件、與預覽共用同一個 chunk，
 * 所以可寫的小文件進工作室、編輯器掛上時仍會把它抓下來——那是掛上之後的非同步載入，不擋首屏，也讓第一次切預覽不必再等。
 * 載入器回傳的元件把載入好的 `MarkdownView` 以屬性交給 `BlockPreview`：預覽容器（`prd-preview`）在管線備妥之後才出現（載入中只有骨架），
 * 不會有「容器在、內容還沒到」的半成品畫面；區塊的捲動定位與分批渲染都以備妥為前提（載入中收到的捲動請求由 `StudioInner` 保留、`onReady` 之後補做）。
 * 動態 import 的字面仍在本檔：EvidenceTimeline.test.tsx 的掃描規定 Markdown 渲染器只准出現在 StudioPanel.tsx（動態 import 的字面也算 import）。
 */
const BlockPreviewLazy = dynamic<BlockPreviewProps>(
  () =>
    import("@/components/markdown/MarkdownView").then(({ MarkdownView }) => {
      function LoadedBlockPreview(props: BlockPreviewProps) {
        return <BlockPreview {...props} View={MarkdownView} />;
      }
      return LoadedBlockPreview;
    }),
  {
    ssr: false,
    loading: () => (
      <div role="status" aria-busy="true" aria-label="PRD 預覽載入中" data-testid="prd-preview-loading">
        <Skeleton className="h-[320px] rounded-md" />
      </div>
    ),
  },
);

function PrdPreview({ text, bytes, focusLine, onReady }: { text: string; bytes: number; focusLine: number | null; onReady: () => void }) {
  if (bytes <= PRD_PREVIEW_MAX_BYTES) return <BlockPreviewLazy text={text} focusLine={focusLine} onReady={onReady} />;
  return (
    <div data-testid="prd-preview-degraded" className="flex flex-col gap-2">
      <p role="note" className="rounded-md border border-wg-alert-border bg-wg-alert-bg px-3 py-2 text-sm text-wg-warning-text">
        PRD 超過 200KB（目前 {Math.ceil(bytes / 1024)} KB），為保持畫面順暢，預覽改為純文字；編輯與儲存不受影響。
      </p>
      <pre
        role="region"
        aria-label="PRD 純文字預覽"
        tabIndex={0}
        className="max-h-[70vh] overflow-auto rounded-md border border-wg-line bg-wg-surface px-4 py-3 font-mono text-sm break-words whitespace-pre-wrap"
      >
        {text}
      </pre>
    </div>
  );
}

// ── 編輯器 ───────────────────────────────────────────────────────────────────────────

function EditorArea({
  value,
  onChange,
  readOnly,
  bytes,
  onNotify,
}: {
  value: string;
  onChange: (text: string) => void;
  readOnly: boolean;
  bytes: number;
  onNotify: (message: string, tone: "success" | "error") => void;
}) {
  const plain = readOnly || bytes > RICH_EDIT_MAX_BYTES;
  return (
    <div className="flex flex-col gap-2">
      {!readOnly && bytes > RICH_EDIT_MAX_BYTES ? (
        <p role="note" data-testid="editor-large-note" className="rounded-md border border-wg-line bg-wg-base px-3 py-2 text-sm text-wg-muted">
          文件較大（{Math.ceil(bytes / 1024)} KB），為了輸入順暢改用精簡編輯器（沒有語法高亮與即時預覽）；要看渲染結果請切到「預覽」。
        </p>
      ) : null}
      {plain ? (
        <Textarea
          data-testid="prd-textarea"
          aria-label={readOnly ? "PRD 內容（唯讀）" : "PRD 內容（精簡編輯器）"}
          readOnly={readOnly}
          spellCheck={false}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          style={{ height: EDITOR_HEIGHT_PX }}
          className="resize-y font-mono text-sm leading-6"
        />
      ) : (
        // 編輯器套件的即時預覽與「預覽」模式、目錄同一條規則：整行的來源節錨點（`<!-- r2p:section=N -->`）是目錄用的記號，不顯示（INT-14⑤）
        <MarkdownEditor value={value} onChange={onChange} label="PRD 內容" height={EDITOR_HEIGHT_PX} exportName="prd" onNotify={onNotify} previewHiddenLines={SECTION_ANCHOR} />
      )}
    </div>
  );
}

// ── 面板本體 ─────────────────────────────────────────────────────────────────────────

type ScrollRequest = { item: OutlineItem; nonce: number };
type ColumnTab = "outline" | "editor" | "review";

function StudioInner({ researchId, project, completed }: ResearchPanelProps) {
  const toast = useToast();
  const qc = useQueryClient();
  const { canWrite } = useAuth();
  const modeId = useId();
  const columnId = useId();
  const tier = useViewportTier();
  const versionsQuery = usePrdVersions(researchId);
  const save = useSavePrdVersion();

  const versions = versionsQuery.data;
  const head = useMemo(() => (versions === undefined || versions.length === 0 ? undefined : versions.reduce((a, v) => (v.versionNo > a.versionNo ? v : a))), [versions]);
  const headNo = head?.versionNo ?? project.headPrdVersion;
  const headContent = usePrdVersion(researchId, headNo);

  const [mode, setMode] = useState<Mode>("edit");
  const [column, setColumn] = useState<ColumnTab>("editor");
  const [local, setLocal] = useState<Local | null>(() => readDraft(researchId));
  const [justSaved, setJustSaved] = useState<{ no: number; text: string } | null>(null);
  const [conflict, setConflict] = useState<{ headVersion: number | null } | null>(null);
  const [scrollRequest, setScrollRequest] = useState<ScrollRequest | null>(null);
  // 預覽（含延遲載入的 Markdown 管線）每掛上一次加一：預覽還在下載時收到的捲動請求，等它備妥後由下面的 effect 補做
  const [previewEpoch, setPreviewEpoch] = useState(0);
  const onPreviewReady = useCallback(() => setPreviewEpoch((n) => n + 1), []);

  const serverText = headContent.data?.content ?? (justSaved !== null && justSaved.no === headNo ? justSaved.text : undefined);
  const text = local?.text ?? serverText ?? "";
  const bytes = useMemo(() => utf8Bytes(text), [text]);
  const frozen = completed || project.flowPhase === "FROZEN" || head?.kind === "BASELINE";
  const readOnly = !canWrite || frozen;
  const dirty = local !== null && serverText !== undefined && (local.base !== headNo || local.text !== serverText);
  const staleBase = local !== null && headNo !== null && local.base !== headNo;

  // 最新的內文與目錄索引（給定位與目錄捲動在「點下去的當下」才現算，不在每個按鍵上算）
  const textRef = useRef(text);
  const rootRef = useRef<HTMLElement>(null);
  const handledNonce = useRef(0);
  useEffect(() => {
    textRef.current = text;
  }, [text]);

  useLeaveGuard(dirty);

  // 未儲存草稿的便利層：有改動（且與 head 不同）才寫，與 head 相同或已儲存就清
  useEffect(() => {
    if (local === null || !dirty) return;
    const timer = setTimeout(() => writeDraft(researchId, local), DRAFT_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [local, dirty, researchId]);
  const settled = serverText !== undefined;
  useEffect(() => {
    if (settled && !dirty) clearDraft(researchId);
  }, [settled, dirty, researchId]);

  // 目錄與缺陷定位：依目前模式把游標或捲動位置移到該章節（每個 request 只做一次；預覽模式下目標區塊還沒出現＝預覽還在載入，保留到 previewEpoch 變動後再做）
  useEffect(() => {
    if (scrollRequest === null || handledNonce.current === scrollRequest.nonce) return;
    const root = rootRef.current;
    if (root === null) return;
    const { item } = scrollRequest;
    if (mode === "preview") {
      const target = root.querySelector(`[data-prd-line="${item.line}"]`);
      if (target === null) return;
      handledNonce.current = scrollRequest.nonce;
      target.scrollIntoView({ block: "start" });
      return;
    }
    handledNonce.current = scrollRequest.nonce;
    if (mode === "edit") {
      const textarea = root.querySelector("textarea");
      if (textarea instanceof HTMLTextAreaElement) scrollTextareaToOffset(textarea, item.offset);
      // 即時預覽窗（精簡編輯器之外的編輯器）：同序的標題元素一併捲到
      const ordinal = parsePrdOutline(textRef.current).findIndex((entry) => entry.id === item.id);
      root
        .querySelectorAll(".w-md-editor-preview h1, .w-md-editor-preview h2, .w-md-editor-preview h3, .w-md-editor-preview h4, .w-md-editor-preview h5, .w-md-editor-preview h6")
        [ordinal]?.scrollIntoView({ block: "start" });
    }
  }, [scrollRequest, mode, previewEpoch]);

  const selectSection = useCallback((item: OutlineItem) => {
    setMode((current) => (current === "diff" ? "preview" : current)); // Diff 沒有章節可捲：先回到預覽
    setColumn("editor");
    setScrollRequest((prev) => ({ item, nonce: (prev?.nonce ?? 0) + 1 }));
  }, []);

  const locate = useCallback(
    (anchor: string) => {
      const item = findOutlineSection(parsePrdOutline(textRef.current), anchor);
      if (item === null) toast.info(`找不到對應的章節：${anchor}`);
      else selectSection(item);
    },
    [selectSection, toast],
  );

  function edit(next: string) {
    setLocal({ text: next, base: local?.base ?? headNo ?? 0 });
    setConflict(null);
  }

  function discard() {
    setLocal(null);
    setConflict(null);
    clearDraft(researchId);
  }

  const saveBlock = bytes > PRD_SAVE_MAX_BYTES ? "PRD 超過 1 MiB 上限，無法儲存" : text.includes("\u0000") ? "內容含有 NUL 字元，無法儲存" : null;

  async function onSave() {
    if (local === null || !dirty || saveBlock !== null) return;
    setConflict(null);
    try {
      const created = await save.mutateAsync({ id: researchId, body: { baseVersion: local.base, content: local.text } });
      setJustSaved({ no: created.versionNo, text: local.text });
      setLocal(null);
      toast.success(`已儲存為第 ${created.versionNo} 版（人工編輯）；先前的審查結果已過期，請重新審查`);
    } catch (e) {
      if (e instanceof ApiError && e.reason === RESEARCH_REASONS.PRD_VERSION_CONFLICT) {
        const headVersion = e.details?.headVersion;
        setConflict({ headVersion: typeof headVersion === "number" ? headVersion : null });
        void invalidateResearch(qc, researchId);
      } else {
        toast.error(`儲存失敗：${researchErrorText(e)}`);
      }
    }
  }

  const notify = useCallback((message: string, tone: "success" | "error") => (tone === "success" ? toast.success(message) : toast.error(message)), [toast]);
  const latestVersion = versions?.find((v) => v.versionNo === (conflict?.headVersion ?? head?.versionNo));
  const roleTitle = !canWrite ? READONLY_TITLE : frozen ? "規格已凍結，不能再修改" : undefined;

  const center = (() => {
    if (versions === undefined) {
      if (versionsQuery.isError) return <ErrorState error={versionsQuery.error} title="無法載入 PRD 版本" onRetry={() => void versionsQuery.refetch()} />;
      return (
        <div aria-busy="true" aria-label="PRD 載入中" role="status">
          <Skeleton className="h-[560px] rounded-lg" />
        </div>
      );
    }
    if (head === undefined) {
      const drafting = project.flowPhase === "DRAFTING" && project.flowStatus === "RUNNING";
      return <EmptyState title="還沒有 PRD 版本" description={drafting ? "PRD 初稿正在生成，完成後會自動出現在這裡。" : "請回到第一步，研究完成後按「生成 PRD 初稿」。"} />;
    }
    if (serverText === undefined && local === null) {
      if (headContent.isError) return <ErrorState error={headContent.error} title="無法載入 PRD 內容" onRetry={() => void headContent.refetch()} />;
      return (
        <div aria-busy="true" aria-label="PRD 內容載入中" role="status">
          <Skeleton className="h-[560px] rounded-lg" />
        </div>
      );
    }
    return mode === "edit" ? (
      <EditorArea value={text} onChange={edit} readOnly={readOnly} bytes={bytes} onNotify={notify} />
    ) : mode === "preview" ? (
      <PrdPreview text={text} bytes={bytes} focusLine={scrollRequest?.item.line ?? null} onReady={onPreviewReady} />
    ) : (
      <PrdDiffView researchId={researchId} versions={versions} />
    );
  })();

  const columnTabs = [
    { id: "outline", label: "目錄" },
    { id: "editor", label: "編輯器" },
    { id: "review", label: "審批" },
  ] as const;
  const hiddenIf = (id: ColumnTab): boolean => tier === "narrow" && column !== id;

  return (
    <div data-testid="studio-panel" data-tier={tier} className="flex flex-col gap-3">
      {tier === "narrow" ? <PillTabs label="工作室區塊" idBase={columnId} tabs={columnTabs} value={column} onChange={setColumn} /> : null}
      <div
        className={cn(
          "grid items-start gap-4",
          tier === "wide" && "grid-cols-[16rem_minmax(0,1fr)_24rem]",
          tier === "medium" && "grid-cols-[2.5rem_minmax(0,1fr)_22rem]",
          tier === "narrow" && "grid-cols-1",
        )}
      >
        <div
          className="min-w-0"
          hidden={hiddenIf("outline")}
          {...(tier === "narrow" ? { role: "tabpanel", id: pillPanelId(columnId, "outline"), "aria-labelledby": pillTabId(columnId, "outline") } : {})}
        >
          <PrdOutline content={text} collapsed={tier === "medium"} activeId={scrollRequest?.item.id ?? null} onSelect={selectSection} />
        </div>

        <section
          ref={rootRef}
          data-testid="prd-editor"
          aria-label="PRD 編輯器"
          className="flex min-w-0 flex-col gap-3"
          hidden={hiddenIf("editor")}
          {...(tier === "narrow" ? { role: "tabpanel", id: pillPanelId(columnId, "editor"), "aria-labelledby": pillTabId(columnId, "editor") } : {})}
        >
          {frozen ? (
            <div data-testid="studio-frozen" className="flex flex-wrap items-center gap-3 rounded-md border border-wg-line bg-wg-surface px-4 py-2.5 text-sm">
              <Lock size={16} aria-hidden className="shrink-0 text-wg-muted" />
              <span className="min-w-0 flex-1">規格已凍結（Gate 0 已核准）：編輯器唯讀，要修改請走變更請求。</span>
              <Link href={`/research/${encodeURIComponent(researchId)}?step=route`} className="font-medium text-wg-primary hover:underline">
                前往分流
              </Link>
            </div>
          ) : null}
          <div className="flex flex-wrap items-center gap-3">
            <PillTabs
              label="編輯模式"
              idBase={modeId}
              tabs={[
                { id: "edit", label: "編輯", icon: Pencil },
                { id: "preview", label: "預覽", icon: Eye },
                { id: "diff", label: "Diff", icon: GitCompareArrows },
              ]}
              value={mode}
              onChange={(next) => setMode(next)}
            />
            <span data-testid="studio-version" className="text-sm text-wg-muted">
              {head === undefined ? "尚無版本" : `目前版本：${head.semver}（第 ${head.versionNo} 版・${head.authorKind === "HUMAN" ? "人工" : "AI"}）`}
              {head === undefined ? "" : ` · ${Math.ceil(bytes / 1024)} KB`}
            </span>
          </div>

          {conflict !== null || staleBase ? (
            <div role="alert" data-testid="studio-conflict" className="flex flex-wrap items-center gap-3 rounded-md border border-wg-draft-border bg-wg-draft-bg px-4 py-3 text-sm">
              <span className="min-w-0 flex-1">
                <span className="font-semibold text-wg-accent">PRD 已有更新的版本</span>
                {latestVersion === undefined ? "" : `（最新：${latestVersion.semver}，第 ${latestVersion.versionNo} 版）`}：您的修改是從第 {local?.base}{" "}
                版開始改的，不能蓋過新版本。請重新整理取得最新版本；若要保留您的修改，請先複製內容。
              </span>
              <Button size="sm" variant="ghost" onClick={discard}>
                載入最新版本（捨棄我的修改）
              </Button>
            </div>
          ) : null}

          <div role="tabpanel" id={pillPanelId(modeId, mode)} aria-labelledby={pillTabId(modeId, mode)}>
            {center}
          </div>

          {mode === "edit" && head !== undefined ? (
            <div className="flex flex-wrap items-center gap-3 border-t border-wg-line pt-3">
              <Button iconLeft={Save} disabled={readOnly || !dirty || saveBlock !== null} title={roleTitle} loading={save.isPending} onClick={() => void onSave()}>
                儲存
              </Button>
              {dirty ? (
                <Button variant="ghost" disabled={readOnly || save.isPending} title={roleTitle} onClick={discard}>
                  捨棄修改
                </Button>
              ) : null}
              <span role="status" data-testid="studio-dirty" className="text-sm text-wg-muted">
                {saveBlock ?? (dirty ? "有尚未儲存的修改（儲存會產生一個新的人工版本）" : readOnly ? "唯讀" : "沒有未儲存的修改")}
              </span>
            </div>
          ) : null}
        </section>

        <div
          className="min-w-0"
          hidden={hiddenIf("review")}
          {...(tier === "narrow" ? { role: "tabpanel", id: pillPanelId(columnId, "review"), "aria-labelledby": pillTabId(columnId, "review") } : {})}
        >
          <GatekeeperPanel researchId={researchId} project={project} completed={completed} onLocate={locate} />
        </div>
      </div>
    </div>
  );
}

/** 換研究專案時整個重掛（工作稿、模式與捲動請求都不跨專案）。 */
export function StudioPanel(props: ResearchPanelProps) {
  return <StudioInner key={props.researchId} {...props} />;
}
