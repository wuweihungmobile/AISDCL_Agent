"use client";

/**
 * 內環連結（FR-R2P-14-3、14-5；TCS-ResearchToPRD-P1-20261107 AT-961-18-5）：連到既有的專案頁（凍結與匯入）、執行中心、監控中心，**不重做任何執行控制**（FR-15-2）。
 * 執行中心連結只有在 `block` 為 null（已簽核、拆解未過期、測試規格已凍結、無 SCR 進行中）時才是連結；其餘一律停用並顯示原因（與後端 409 一致）。
 * 看板、自癒與終端屬 P2，這裡不渲染；`ResearchBackLink` 同屬 P2。
 */
import { Activity, FolderOpen, Play } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { BUILD_DISABLED_TEXT } from "@/lib/domain/research";

type Block = keyof typeof BUILD_DISABLED_TEXT;

export function InnerLoopLinks({ consoleProjectId, block }: { consoleProjectId: string | null; block: Block | null }) {
  if (consoleProjectId === null) {
    return (
      <section data-testid="inner-loop-links" aria-label="既有流程連結" className="flex flex-col gap-2 rounded-md border border-wg-line p-4">
        <h4 className="text-base font-semibold">既有流程</h4>
        <p className="text-sm text-wg-muted">尚無 Console 專案：分流完成後才會建立，到時這裡會出現專案頁、執行中心與監控中心的連結。</p>
      </section>
    );
  }
  const base = `/projects/${encodeURIComponent(consoleProjectId)}`;
  const reason = block === null ? null : BUILD_DISABLED_TEXT[block];
  return (
    <section data-testid="inner-loop-links" aria-label="既有流程連結" className="flex flex-col gap-3 rounded-md border border-wg-line p-4">
      <h4 className="text-base font-semibold">既有流程</h4>
      <div className="flex flex-wrap gap-2">
        <Button asChild variant="ghost" iconLeft={FolderOpen}>
          <Link href={base}>專案頁（凍結與匯入）</Link>
        </Button>
        {block === null ? (
          <Button asChild variant="ghost" iconLeft={Play}>
            <Link href={`${base}/execute`}>執行中心</Link>
          </Button>
        ) : (
          // 停用的「連結」不是按鈕：它本來就不是寫入控件，不該被當成「按了會送請求但被擋」的按鈕；原因在 title 與下方說明
          <span
            data-testid="execute-disabled"
            aria-disabled="true"
            title={reason ?? undefined}
            className="inline-flex cursor-not-allowed items-center gap-2 rounded-md border border-wg-line px-5 py-2 text-sm font-medium text-wg-muted"
          >
            <Play size={18} aria-hidden />
            執行中心
          </span>
        )}
        <Button asChild variant="ghost" iconLeft={Activity}>
          <Link href={`${base}/monitor`}>監控中心</Link>
        </Button>
      </div>
      {reason !== null ? (
        <p role="note" data-testid="execute-block-reason" data-block={block ?? undefined} className="text-[13px] text-wg-warning-text">
          執行中心暫不能用：{reason}
        </p>
      ) : null}
    </section>
  );
}
