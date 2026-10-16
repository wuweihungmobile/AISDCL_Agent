"use client";

/**
 * Markdown 渲染（PRD §5.1.4：GFM 表格、程式碼區塊語法高亮、checklist）。
 * react-markdown ＋ remark-gfm ＋ rehype-highlight；不渲染原始 HTML（預設安全；原文當成文字顯示，編輯器預覽端比照辦理，見 MarkdownEditorImpl 的 omitRawHtml）。
 * 網址走 safeUrlTransform（與編輯器預覽同一支白名單）：javascript:、data: 等協定的連結拿掉 href，變成沒有行為的文字。
 * variant="prose"＝說明描述（15px／1.7）；variant="criteria"＝通過標準（14px 清單，- [ ] / - [x] 為 18px 核取方塊）。
 */
import { Check } from "lucide-react";
import ReactMarkdown, { type Components } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import "@/styles/markdown.css";
import { cn } from "@/lib/utils";
import { rehypeTaskLabels } from "./rehypeTaskLabels";
import { safeUrlTransform } from "./safeUrl";

const components: Components = {
  // GFM task list：唯讀核取方塊，視覺同設計稿 18px 方塊（勾選＝主色底＋白勾）；名稱＝該項目的文字（rehypeTaskLabels 補上 aria-label）
  input({ type, checked, "aria-label": ariaLabel }) {
    if (type !== "checkbox") return null;
    return (
      <span
        role="checkbox"
        aria-checked={Boolean(checked)}
        aria-readonly="true"
        aria-label={ariaLabel}
        data-checked={Boolean(checked)}
        className="md-checkbox inline-flex size-[18px] shrink-0 items-center justify-center rounded-sm border border-wg-line text-white data-[checked=true]:border-wg-primary data-[checked=true]:bg-wg-primary"
      >
        {checked ? <Check size={13} aria-hidden /> : null}
      </span>
    );
  },
  a({ href, children }) {
    const external = typeof href === "string" && /^https?:\/\//.test(href);
    return (
      <a href={href} {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}>
        {children}
      </a>
    );
  },
  table({ children }) {
    // 寬表格在這個容器內橫向捲動：可捲動區域要能用鍵盤聚焦（axe scrollable-region-focusable），所以容器是 tabIndex=0 的區域
    return (
      <div className="md-table-wrap" tabIndex={0} role="region" aria-label="表格（可橫向捲動）">
        <table>{children}</table>
      </div>
    );
  },
};

export function MarkdownView({
  source,
  variant = "prose",
  empty = "（無內容）",
  className,
}: {
  source: string | null | undefined;
  variant?: "prose" | "criteria";
  /** 沒有內容時顯示的文字 */
  empty?: string;
  className?: string;
}) {
  const text = source?.trim() ?? "";
  if (!text) {
    return <p className={cn("text-sm text-wg-muted", className)}>{empty}</p>;
  }
  return (
    <div data-slot="markdown-view" className={cn("md-view", variant === "criteria" && "md-criteria", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[[rehypeHighlight, { detect: false, ignoreMissing: true }], rehypeTaskLabels]} components={components} urlTransform={safeUrlTransform}>
        {text}
      </ReactMarkdown>
    </div>
  );
}
