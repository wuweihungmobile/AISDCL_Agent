"use client";

/**
 * 測試規格（TCS）草擬卡（FR-R2P-14-7；TCS-ResearchToPRD-P1-20261107 AT-961-18-4）：
 *  - 「草擬測試規格」：前置＝分流已完成、內環鍵已採納基線、已有拆解列（D-110）；前置未成立時停用並說明，409 時列出後端 `details.unmet[]` 的缺項；
 *  - 四態（取自 `flow.effective` 的相態）：草擬中、待凍結（顯示路徑與雜湊前 12 碼與「前往凍結」連到既有專案頁的凍結流程，不重做凍結介面）、已凍結、失敗；
 *    `tcs_invalid` 失敗顯示缺項說明（純文字）並可重試；
 *  - 凍結走既有 `:freeze`，凍結後游標由讀端衍生或「重新對帳」校正（D-125），所以待凍結態的導引文字寫明這件事。
 */
import { FileCheck2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useStartResearchStage } from "@/lib/api/queries";
import { researchErrorText, tcsInvalidText, unmetLabels, type TcsStage } from "@/lib/domain/research";

const STAGE_TEXT: Readonly<Record<TcsStage, string>> = {
  none: "尚未草擬",
  drafting: "測試規格草擬中",
  pending: "測試規格已草擬，待人工凍結",
  frozen: "測試規格已凍結",
  failed: "測試規格草擬失敗",
};

export function TcsCard({
  researchId,
  stage,
  tcs,
  consoleProjectId,
  detail,
  prerequisiteReason,
  lock,
}: {
  researchId: string;
  stage: TcsStage;
  /** 拆解列帶的 TCS 路徑與雜湊（尚未草擬為 null） */
  tcs: { relPath: string | null; sha256: string | null } | null;
  consoleProjectId: string | null;
  /** 游標 `flow_detail`（失敗時含 `tcs_invalid` 缺項） */
  detail: string;
  /** 前置未成立的說明（null＝前置齊備）：停用「草擬測試規格」並顯示 */
  prerequisiteReason: string | null;
  /** 整張卡的停用說明（唯讀角色、已完成步驟、規格變更中） */
  lock: string | null;
}) {
  const start = useStartResearchStage();
  const [error, setError] = useState<unknown>(null);
  const disabledReason = lock ?? prerequisiteReason;
  const canStart = stage === "none" || stage === "failed";
  const invalid = stage === "failed" ? tcsInvalidText(detail) : null;
  const unmet = unmetLabels(error);

  async function doStart() {
    setError(null);
    try {
      await start.mutateAsync({ id: researchId, stage: "tcs-draft" });
    } catch (e) {
      setError(e);
    }
  }

  return (
    <section data-testid="tcs-card" data-stage={stage} aria-label="測試規格草擬" className="flex flex-col gap-3 rounded-md border border-wg-line p-4">
      <h4 className="flex items-center gap-2 text-base font-semibold">
        <FileCheck2 size={18} aria-hidden className="text-wg-muted" />
        測試規格草擬
      </h4>
      <p data-testid="tcs-stage-text" className="text-sm">
        {STAGE_TEXT[stage]}
      </p>

      {stage === "drafting" ? (
        <p role="status" className="text-sm text-wg-muted">
          系統正在依拆解與驗收條件草擬測試規格，完成後會進入待凍結。
        </p>
      ) : null}

      {stage === "failed" ? (
        <div role="alert" data-testid="tcs-failed" className="text-sm text-wg-error">
          {invalid !== null ? <p>測試規格沒有通過預檢，缺項：{invalid === "" ? "後端沒有提供缺項明細" : invalid}</p> : <p>草擬沒有完成：{detail === "" ? "後端沒有提供原因" : detail}</p>}
        </div>
      ) : null}

      {stage === "pending" || stage === "frozen" ? (
        <dl data-testid="tcs-facts" className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-wg-muted">路徑</dt>
          <dd className="break-all font-mono">{tcs?.relPath ?? "後端尚未回報"}</dd>
          <dt className="text-wg-muted">雜湊</dt>
          <dd className="font-mono">{tcs?.sha256 ? tcs.sha256.slice(0, 12) : "後端尚未回報"}</dd>
        </dl>
      ) : null}

      {stage === "pending" ? (
        <div className="flex flex-col gap-2 text-sm">
          <p data-testid="tcs-freeze-guide">請到既有的專案頁走凍結流程；凍結後回到此頁按「重新對帳」，或等待系統自動校正。</p>
          {consoleProjectId !== null ? (
            <Link href={`/projects/${encodeURIComponent(consoleProjectId)}`} className="w-fit font-medium text-wg-primary hover:underline">
              前往凍結
            </Link>
          ) : (
            <p className="text-wg-muted">尚無 Console 專案，無法前往凍結。</p>
          )}
        </div>
      ) : null}

      {canStart ? (
        <>
          <Button className="w-fit" disabled={disabledReason !== null} title={disabledReason ?? undefined} loading={start.isPending} onClick={() => void doStart()}>
            草擬測試規格
          </Button>
          {disabledReason !== null ? (
            <p role="note" data-testid="tcs-disabled-reason" className="text-[13px] text-wg-warning-text">
              {disabledReason}
            </p>
          ) : null}
        </>
      ) : null}

      {error !== null ? (
        <div role="alert" data-testid="tcs-start-error" className="text-sm text-wg-error">
          <p>{researchErrorText(error)}</p>
          {unmet.length > 0 ? (
            <ul className="list-disc pl-5">
              {unmet.map((u) => (
                <li key={u}>{u}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
