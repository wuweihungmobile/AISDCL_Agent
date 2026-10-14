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
import MDEditor from "@uiw/react-md-editor";
import { FileDown, FileUp } from "lucide-react";
import { useId, useRef, useState } from "react";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import "@uiw/react-md-editor/markdown-editor.css";
import "@uiw/react-markdown-preview/markdown.css";
import "@/styles/markdown.css";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** 匯入檔大小上限：1 MB（說明與通過標準是文字，不需要更大） */
export const MAX_IMPORT_BYTES = 1024 * 1024;

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
  const cleaned = name.replace(/[\\/:*?"<>|\u0000-\u001f]/g, "_").trim().replace(/^\.+/, "");
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

export function MarkdownEditorImpl({
  value,
  onChange,
  label,
  placeholder,
  height = 220,
  exportName = "content",
  onNotify,
  className,
}: MarkdownEditorProps) {
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
        visibleDragbar={false}
        textareaProps={{ "aria-label": label, placeholder }}
        previewOptions={{
          remarkPlugins: [remarkGfm],
          rehypePlugins: [[rehypeHighlight, { detect: false, ignoreMissing: true }]],
        }}
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
        <Button
          variant="ghost"
          size="sm"
          iconLeft={FileUp}
          loading={busy}
          onClick={() => fileInput.current?.click()}
        >
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
