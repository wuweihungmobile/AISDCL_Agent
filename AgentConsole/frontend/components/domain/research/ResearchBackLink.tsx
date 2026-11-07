"use client";

/**
 * 回到研發工作流的連結（FR-R2P-15-5、AC-R2P-01-5；TCS-ResearchToPRD-P2-20261107 AT-962-16-*；IFACE-P2 §8；D-138 Q-11）。
 *
 * 設計要點（為什麼這樣做）：
 *  - **零後端、零儲存**：深連結由研究工作區的 `InnerLoopLinks`／看板帶 `?researchId=<uuid>`，執行中心與監控中心讀 query 即知道從哪來；
 *    本檔不呼叫 API、不讀寫 localStorage／sessionStorage／cookie（AT-962-16-E-3 以原始碼靜態掃描加守）。
 *  - **只收標準 UUID**（不分大小寫；`isResearchUuid`）：路徑穿越、腳本、長度不符、非十六進位一律不渲染，DOM 為空（AT-962-16-E-2）；
 *    沒有參數（直接開執行中心）也不渲染、不猜（AT-962-16-E-1）。
 *  - **Suspense 住在這裡**：`useSearchParams` 在靜態預渲染需要 Suspense 邊界；AT-962-16-E-3 規定兩個頁殼 `page.tsx` 零差異，
 *    所以邊界由 `ResearchBackLinkFromQuery` 自帶，兩個 View 只放它（`npm run build` 是這點的唯一驗收）。
 */
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { isResearchUuid } from "@/lib/domain/research";

export function ResearchBackLink({ researchId }: { researchId: string | null }) {
  if (!isResearchUuid(researchId)) return null;
  return (
    <Link
      href={`/research/${researchId}?step=build`}
      data-testid="research-back-link"
      className="mb-3.5 ml-4 inline-flex items-center gap-1.5 text-sm text-wg-muted transition-colors hover:text-wg-primary"
    >
      <ArrowLeft size={16} aria-hidden />
      回到研發工作流
    </Link>
  );
}

function FromQuery() {
  const searchParams = useSearchParams();
  return <ResearchBackLink researchId={searchParams.get("researchId")} />;
}

/** 兩個 View 頁頂用：讀網址的 `?researchId=`，自帶 Suspense（fallback 為空）。 */
export function ResearchBackLinkFromQuery() {
  return (
    <Suspense fallback={null}>
      <FromQuery />
    </Suspense>
  );
}
