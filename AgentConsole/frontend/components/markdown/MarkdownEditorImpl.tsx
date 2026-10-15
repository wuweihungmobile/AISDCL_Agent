"use client";

/**
 * Markdown 編輯器本體（PRD §5.1.4 八項功能，逐項對應見 docs/06_quality/RTM.md 的 UI-MD-01～08）：
 *  1 即時預覽（Split View）＝@uiw/react-md-editor 的 preview="live"（左原始碼、右即時渲染；工具列右側可切換純編輯／純預覽／全螢幕）
 *  2 語法高亮＝編輯器內建的 Markdown 原始碼著色（prism）
 *  3 工具列＝編輯器預設工具列（標題、粗體、斜體、刪除線、引用、連結、行內碼、程式碼區塊、表格、無序／有序／核取清單）
 *  4 GFM 表格、5 程式碼區塊＋語言高亮、6 Checklist＝預覽端 remark-gfm ＋ rehype-highlight
 *  7 匯入 .md＝下方「匯入 .md」（讀入本機檔案、覆蓋欄位內容）　8 匯出 .md＝「匯出 .md」（Blob 下載）
 * 這支檔直接 import 編輯器套件（需要瀏覽器 API），頁面一律經 MarkdownEditor.tsx 以 next/dynamic（ssr:false）載入。
 */
import MDEditor, { getCommands, getExtraCommands, type ICommand } from "@uiw/react-md-editor";
import { FileDown, FileUp } from "lucide-react";
import { cloneElement, isValidElement, useDeferredValue, useId, useMemo, useRef, useState, type ComponentProps } from "react";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import "@uiw/react-md-editor/markdown-editor.css";
import "@uiw/react-markdown-preview/markdown.css";
import "@/styles/markdown.css";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { rehypeTaskLabels } from "./rehypeTaskLabels";

/** 預覽端的 remark／rehype 外掛：模組層級常數（每次 render 重建會讓預覽的記憶化失效）；核取清單的名稱由 rehypeTaskLabels 補上。 */
const PREVIEW_OPTIONS: NonNullable<ComponentProps<typeof MDEditor>["previewOptions"]> = {
  remarkPlugins: [remarkGfm],
  rehypePlugins: [[rehypeHighlight, { detect: false, ignoreMissing: true }], rehypeTaskLabels],
};

/**
 * 超過這個字數才把預覽排到輸入之後。實測（真瀏覽器、production 建置）：渲染時間約與字數成正比，
 * 5,000 字約 30ms、20,000 字約 110ms；文件小的時候分兩段反而慢（1,000 字 13→17ms、5,000 字 30→40ms，多等一個畫面），
 * 大的時候才划算（20,000 字連續打字的輸入延遲 p50 136→80ms）。
 */
export const DEFER_ABOVE_CHARS = 8000;

/**
 * 預覽窗（取代套件預設的預覽；套件把回傳的元素包進 .w-md-editor-preview，並接上捲動同步）。兩件事：
 *  1 大文件時輸入與預覽分開排程（NFR-9.1-05）：預覽拿的是 useDeferredValue(source)。輸入框的更新先提交、先畫出來，
 *    預覽的渲染（remark／rehype／語法高亮）排在後面；連續輸入時中間的值直接被跳過、只渲染最後一個。
 *    小文件不分開：整個渲染一幀內就做完，分兩段只會多等一個畫面（見 DEFER_ABOVE_CHARS）。
 *  2 鍵盤可達（axe scrollable-region-focusable；DEF-AC-005 同類）：.w-md-editor-preview 是可捲動區域，裡面沒有任何可聚焦的東西，
 *    鍵盤使用者就無法捲它。這裡放一個 tabIndex=0 的區域（名稱＝「<欄位名> 預覽」，同一頁有多個編輯器時各自唯一）。
 */
function DeferredPreview({ source, label }: { source: string; label: string }) {
  const deferred = useDeferredValue(source);
  const shown = source.length > DEFER_ABOVE_CHARS ? deferred : source;
  // 渲染結果以 shown 為鍵記憶：輸入當下的「急件」那一輪 deferred 還是舊值，拿到同一個元素、整棵 Markdown 子樹直接跳過；
  // 沒有這一層，急件那輪也會把舊內容整份重新解析一遍（實測 20,000 字反而更慢：預覽出現 129ms→205ms）
  const rendered = useMemo(() => <MDEditor.Markdown {...PREVIEW_OPTIONS} source={shown} />, [shown]);
  return (
    <div tabIndex={0} role="region" aria-label={`${label} 預覽`} data-testid="md-preview-region">
      {rendered}
    </div>
  );
}

/** 匯入檔大小上限：1 MB（說明與通過標準是文字，不需要更大） */
export const MAX_IMPORT_BYTES = 1024 * 1024;

/**
 * 工具列按鈕的圖示 svg 在套件裡帶 role="img" 卻沒有替代文字（axe svg-img-alt；DEF-AC-005）。
 * 每顆按鈕本身已有 aria-label，圖示只是裝飾，所以把 svg 標成 aria-hidden（含群組按鈕底下的子指令）。
 */
export function hideToolbarIcons(command: ICommand): ICommand {
  const icon = isValidElement<Record<string, unknown>>(command.icon) ? cloneElement(command.icon, { "aria-hidden": true }) : command.icon;
  const children = Array.isArray(command.children) ? command.children.map(hideToolbarIcons) : command.children;
  return { ...command, icon, children } as ICommand;
}
const TOOLBAR = getCommands().map(hideToolbarIcons);
const EXTRA_TOOLBAR = getExtraCommands().map(hideToolbarIcons);

export type MarkdownEditorProps = {
  value: string;
  onChange: (value: string) => void;
  /** 無障礙名稱（編輯區 textarea 的 aria-label） */
  label: string;
  placeholder?: string;
  /** 編輯區高度（px）；Dialog 內用小一點，整頁表單用大一點 */
  height?: number;
  /** 匯出檔名（不含副檔名），預設 content */
  exportName?: string;
  /** 匯入／匯出的結果訊息（成功或失敗），由呼叫端決定怎麼呈現（toast） */
  onNotify?: (message: string, tone: "success" | "error") => void;
  className?: string;
};

/** 檔名只留安全字元，避免路徑穿越與跨平台非法字元 */
export function safeFileName(name: string): string {
  const cleaned = name
    .replace(/[\\/:*?"<>|\u0000-\u001f]/g, "_")
    .trim()
    .replace(/^\.+/, "");
  return cleaned || "content";
}

export function downloadMarkdown(text: string, fileBase: string): void {
  const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${safeFileName(fileBase)}.md`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function MarkdownEditorImpl({ value, onChange, label, placeholder, height = 220, exportName = "content", onNotify, className }: MarkdownEditorProps) {
  const fileInput = useRef<HTMLInputElement>(null);
  const inputId = useId();
  const [busy, setBusy] = useState(false);

  async function onPickFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // 允許連續匯入同一個檔案
    if (!file) return;
    if (!/\.(md|markdown|txt)$/i.test(file.name)) {
      onNotify?.("只支援 .md／.markdown／.txt 文字檔", "error");
      return;
    }
    if (file.size > MAX_IMPORT_BYTES) {
      onNotify?.("檔案超過 1 MB 上限", "error");
      return;
    }
    setBusy(true);
    try {
      onChange(await file.text());
      onNotify?.(`已匯入 ${file.name}`, "success");
    } catch {
      onNotify?.("讀取檔案失敗", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div data-slot="markdown-editor" data-color-mode="light" className={cn("md-editor-box", className)}>
      <MDEditor
        value={value}
        onChange={(v) => onChange(v ?? "")}
        preview="live"
        height={height}
        commands={TOOLBAR}
        extraCommands={EXTRA_TOOLBAR}
        visibleDragbar={false}
        textareaProps={{ "aria-label": label, placeholder }}
        previewOptions={PREVIEW_OPTIONS}
        components={{ preview: (source) => <DeferredPreview source={source} label={label} /> }}
      />
      <div className="mt-2 flex items-center justify-end gap-2">
        <input
          ref={fileInput}
          id={inputId}
          type="file"
          accept=".md,.markdown,.txt,text/markdown,text/plain"
          className="sr-only"
          tabIndex={-1}
          aria-label={`${label}：選擇要匯入的 .md 檔案`}
          data-testid="md-import-input"
          onChange={onPickFile}
        />
        <Button variant="ghost" size="sm" iconLeft={FileUp} loading={busy} onClick={() => fileInput.current?.click()}>
          匯入 .md
        </Button>
        <Button
          variant="ghost"
          size="sm"
          iconLeft={FileDown}
          disabled={!value.trim()}
          onClick={() => {
            downloadMarkdown(value, exportName);
            onNotify?.(`已匯出 ${safeFileName(exportName)}.md`, "success");
          }}
        >
          匯出 .md
        </Button>
      </div>
    </div>
  );
}
