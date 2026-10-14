"use client";

/**
 * Markdown 渲染（PRD §5.1.4：GFM 表格、程式碼區塊語法高亮、checklist）。
 * react-markdown ＋ remark-gfm ＋ rehype-highlight；不渲染原始 HTML（預設安全）。
 * variant="prose"＝說明描述（15px／1.7）；variant="criteria"＝通過標準（14px 清單，- [ ] / - [x] 為 18px 核取方塊）。
 */
import { Check } from "lucide-react";
import ReactMarkdown, { type Components } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import "@/styles/markdown.css";
import { cn } from "@/lib/utils";

const components: Components = {
  // GFM task list：唯讀核取方塊，視覺同設計稿 18px 方塊（勾選＝主色底＋白勾）
  input({ type, checked }) {
    if (type !== "checkbox") return null;
    return (
      <span
        role="checkbox"
        aria-checked={Boolean(checked)}
        aria-readonly="true"
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
    return (
      <div className="md-table-wrap">
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
    <div
      data-slot="markdown-view"
      className={cn("md-view", variant === "criteria" && "md-criteria", className)}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: false, ignoreMissing: true }]]}
        components={components}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
