"use client";

/**
 * Token Guard 小卡（執行 tab；契約 §1.5.4、NFR-SEC-05）：壓縮門檻與停機門檻成對編輯，
 * 「套用」送 PUT /settings/execution/token-guard（同一交易校驗並寫兩個鍵）。
 * 為什麼獨立成卡：halt 必須大於 compact 是跨鍵約束，兩個輸入框分開存會讓中間狀態違規
 * （後端對單鍵也會讀對端現值校驗，但成對提交才是原子的）。
 */
import { Check, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

export function TokenGuardCard({
  children,
  error,
  blocked,
  dirty,
  disabled,
  applying,
  onApply,
}: {
  /** 兩列 SettingRow（compactThresholdPct、haltThresholdPct） */
  children: ReactNode;
  /** 前端跨鍵驗證或後端 400 的 reason（逐字常數） */
  error?: string | null;
  /** 前端驗證不過：不送出（紅字已在 error 裡） */
  blocked: boolean;
  dirty: boolean;
  /** 不可套用（非 ADMIN、儲存中） */
  disabled: boolean;
  applying: boolean;
  onApply: () => void;
}) {
  return (
    <section aria-labelledby="token-guard-title" data-testid="token-guard-card" className="mb-2 rounded-lg border border-wg-line bg-wg-base px-5 pt-4 pb-3">
      <div className="flex items-center gap-2">
        <ShieldCheck size={18} className="text-wg-primary" aria-hidden />
        <h4 id="token-guard-title" className="text-base font-semibold">
          Token Guard
        </h4>
      </div>
      <p className="mt-0.5 text-xs text-wg-muted">壓縮門檻與停機門檻成對編輯：停機門檻必須大於壓縮門檻，後端以原子交易一併校驗，不得經 Console 提高上限繞過安全收斂。</p>
      <div className="mt-1">{children}</div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-wg-line pt-3">
        {error ? (
          <p role="alert" data-testid="token-guard-error" className="min-w-0 flex-1 text-[13px] break-words text-wg-error">
            {error}
          </p>
        ) : (
          <span className="flex-1" />
        )}
        <Button size="sm" iconLeft={Check} loading={applying} disabled={disabled || !dirty || blocked} onClick={onApply}>
          套用 Token Guard
        </Button>
      </div>
    </section>
  );
}
