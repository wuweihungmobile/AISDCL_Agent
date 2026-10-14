"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/skeleton";
import type { MarkdownEditorProps } from "./MarkdownEditorImpl";

export type { MarkdownEditorProps } from "./MarkdownEditorImpl";

/**
 * 頁面使用的 Markdown 編輯器入口：以 next/dynamic（ssr:false）載入編輯器本體——
 * 編輯器套件需要瀏覽器 API，且體積大，只在真的開表單時才下載。
 */
export const MarkdownEditor = dynamic<MarkdownEditorProps>(
  () => import("./MarkdownEditorImpl").then((m) => m.MarkdownEditorImpl),
  {
    ssr: false,
    loading: () => <Skeleton className="h-[220px] w-full rounded-md" />,
  },
);
