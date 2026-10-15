"use client";

/**
 * 模型 tab 的「測試連線」（設計稿；US-S-05；契約 §1.5.7）：
 * 測試中 spinner → 成功綠勾「連線成功（延遲 NNNms）」／失敗紅字原因。
 * 可帶表單內「尚未儲存」的 apiUrl／apiKey／model 做測試（金鑰僅寫入、不回顯）；沒改的欄位不送，後端取已儲存值。
 * 注意：測試會對 apiUrl 送一則 1-token 的 ping（供應商端約消耗一個 token）；不是 GET /v1/models。
 */
import { CircleCheckBig, CircleX, Plug } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useTestConnection } from "@/lib/api/queries";
import type { TestConnectionRequest } from "@/lib/api/types";
import { describeSettingsError } from "./settingsErrors";

export function ConnectionTest({
  disabled,
  buildRequest,
}: {
  disabled: boolean;
  /** 組出本次測試要帶的欄位（只含使用者改過、尚未儲存的值）；沒有就回 undefined */
  buildRequest: () => TestConnectionRequest | undefined;
}) {
  const test = useTestConnection();
  const result = test.data;
  return (
    <div className="mt-2 flex flex-wrap items-center gap-3 border-t border-wg-line pt-4" data-testid="connection-test">
      <Button
        variant="ghost"
        iconLeft={Plug}
        loading={test.isPending}
        disabled={disabled}
        title={disabled ? "權限不足（僅 ADMIN 可測試連線）" : undefined}
        onClick={() => test.mutate(buildRequest())}
      >
        測試連線
      </Button>
      <div role="status" aria-live="polite" data-testid="test-connection-result" className="min-w-0 flex-1 text-sm">
        {test.isPending ? (
          <span className="inline-flex items-center gap-2 text-wg-muted">
            <Spinner size={16} label="測試連線中" />
            測試中…
          </span>
        ) : result?.success ? (
          <span className="inline-flex items-center gap-1.5 text-wg-primary">
            <CircleCheckBig size={18} aria-hidden />
            {result.latencyMs != null ? `連線成功（延遲 ${result.latencyMs}ms）` : "連線成功"}
          </span>
        ) : result ? (
          <span className="inline-flex items-start gap-1.5 break-words text-wg-error">
            <CircleX size={18} className="mt-px shrink-0" aria-hidden />
            連線失敗：{result.message}
          </span>
        ) : test.isError ? (
          <span className="inline-flex items-start gap-1.5 break-words text-wg-error">
            <CircleX size={18} className="mt-px shrink-0" aria-hidden />
            {describeSettingsError(test.error)}
          </span>
        ) : null}
      </div>
    </div>
  );
}
