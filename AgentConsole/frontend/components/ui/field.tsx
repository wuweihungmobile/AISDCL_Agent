import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * 表單欄位外殼（設計稿：label 上、控制項下、gap 6px、label 14px／500）。
 *  - as="label"（預設）：<label> 包住控制項，點標籤即聚焦、getByLabel 可取；
 *  - as="group"：複合控制項（Markdown 編輯器、核取清單）用 role="group"＋aria-labelledby。
 * error 以 role="alert" 顯示在控制項下方（後端 400 的 errors[] 也走這裡）。
 */
export function Field({
  label,
  hint,
  error,
  as = "label",
  className,
  children,
}: {
  label: React.ReactNode;
  hint?: React.ReactNode;
  error?: string;
  as?: "label" | "group";
  className?: string;
  children: React.ReactNode;
}) {
  const labelId = React.useId();
  const body = (
    <>
      <span id={labelId} className="text-sm font-medium">
        {label}
        {hint ? <span className="ml-1 font-normal text-wg-muted">{hint}</span> : null}
      </span>
      {children}
    </>
  );
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      {as === "label" ? (
        <label className="flex flex-col gap-1.5">{body}</label>
      ) : (
        <div role="group" aria-labelledby={labelId} className="flex flex-col gap-1.5">
          {body}
        </div>
      )}
      {error ? (
        <p role="alert" className="text-[13px] text-wg-error">
          {error}
        </p>
      ) : null}
    </div>
  );
}
