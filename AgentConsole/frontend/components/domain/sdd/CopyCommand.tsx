"use client";

/**
 * 可複製的指令區塊（契約 §4.7.3「恢復指令」：PowerShell 與 POSIX 各一段等寬字指令與「複製」鈕）。
 * 指令是 Bridge 組好的字串，這裡原樣顯示（React 文字節點，不經 innerHTML）；Console 不替換 `<人工原因>` 佔位、不提供執行鈕。
 * 複製：優先用 Clipboard API（需要安全情境與使用者手勢）；失敗退回選取暫存 textarea＋execCommand（舊瀏覽器、非 https 的內網部署）；
 * 兩條都失敗就老實說「複製失敗，請手動選取」，不假裝成功。複製結果也以隱藏的 role="status" 文字讓螢幕閱讀器知道。
 */
import { Check, Copy } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";

/** 複製到剪貼簿；成功回 true。不丟例外。 */
export async function copyText(text: string): Promise<boolean> {
  try {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // 權限被拒或非安全情境：退回下面的選取複製
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.setAttribute("aria-hidden", "true");
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  try {
    area.select();
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    area.remove(); // 不論成敗都拆掉暫存的 textarea，不留在頁面上
  }
}

type CopyState = "idle" | "copied" | "failed";

/** 「已複製」回復成「複製」的毫秒數。 */
export const COPY_FEEDBACK_MS = 2400;

export function CopyCommand({ shell, label, command }: { shell: string; label: string; command: string }) {
  const [state, setState] = useState<CopyState>("idle");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  async function copy() {
    const ok = await copyText(command);
    setState(ok ? "copied" : "failed");
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setState("idle"), COPY_FEEDBACK_MS);
  }

  const copied = state === "copied";
  return (
    <div data-shell={shell} data-testid={`sdd-recovery-${shell}`} className="min-w-0">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-wg-muted">{label}</span>
        <Button variant="ghost" size="sm" iconLeft={copied ? Check : Copy} aria-label={`${copied ? "已複製" : "複製"} ${label} 指令`} data-testid={`sdd-recovery-copy-${shell}`} onClick={copy}>
          {copied ? "已複製" : "複製"}
        </Button>
      </div>
      {/* 不設捲動容器：長指令以 break-all 換行攤開（捲動區要另外處理鍵盤可及性，攤開最單純） */}
      <pre data-testid={`sdd-recovery-command-${shell}`} className="rounded-md border border-wg-line bg-white px-3 py-2 font-mono text-xs break-all whitespace-pre-wrap text-wg-text">
        {command}
      </pre>
      <span role="status" className="sr-only">
        {copied ? `已複製 ${label} 指令` : state === "failed" ? "複製失敗，請手動選取指令" : ""}
      </span>
      {state === "failed" ? (
        <p role="alert" className="mt-1 text-[13px] text-wg-error">
          複製失敗，請手動選取上面的指令。
        </p>
      ) : null}
    </div>
  );
}
