"use client";

import * as React from "react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export type PillTab<T extends string> = { id: T; label: string; icon?: LucideIcon };

/** 分頁籤的 DOM id 規則：呼叫端的面板用同一組 id，才接得上 aria-controls／aria-labelledby。 */
export const pillTabId = (idBase: string, tab: string) => `${idBase}-tab-${tab}`;
export const pillPanelId = (idBase: string, tab: string) => `${idBase}-panel-${tab}`;

/**
 * 膠囊分頁籤（設計稿：匯入頁的來源 tab、設定頁的分類 tab）：
 * active＝主色實底白字（含圖示）；其餘白底細邊框。role="tablist"／"tab"，方向鍵、Home／End 切換並移動焦點。
 * hover 只改顏色（設計系統規範）。
 */
export function PillTabs<T extends string>({
  label,
  idBase,
  tabs,
  value,
  onChange,
  className,
}: {
  /** tablist 的無障礙名稱 */
  label: string;
  /** 面板 id 規則的前綴（見 pillTabId／pillPanelId） */
  idBase: string;
  tabs: ReadonlyArray<PillTab<T>>;
  value: T;
  onChange: (id: T) => void;
  className?: string;
}) {
  function onKeyDown(e: React.KeyboardEvent<HTMLButtonElement>, index: number) {
    let next: number;
    if (e.key === "ArrowRight") next = (index + 1) % tabs.length;
    else if (e.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabs.length - 1;
    else return;
    e.preventDefault();
    const target = tabs[next];
    onChange(target.id);
    document.getElementById(pillTabId(idBase, target.id))?.focus();
  }

  return (
    <div role="tablist" aria-label={label} className={cn("flex flex-wrap gap-2", className)}>
      {tabs.map(({ id, label: text, icon: Icon }, index) => {
        const active = id === value;
        return (
          <button
            key={id}
            id={pillTabId(idBase, id)}
            type="button"
            role="tab"
            aria-selected={active}
            aria-controls={pillPanelId(idBase, id)}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(id)}
            onKeyDown={(e) => onKeyDown(e, index)}
            className={cn(
              "inline-flex cursor-pointer items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors",
              active
                ? "border-wg-primary bg-wg-primary text-white"
                : "border-wg-line bg-wg-surface text-wg-text hover:text-wg-primary",
            )}
          >
            {Icon ? <Icon size={16} aria-hidden /> : null}
            {text}
          </button>
        );
      })}
    </div>
  );
}
