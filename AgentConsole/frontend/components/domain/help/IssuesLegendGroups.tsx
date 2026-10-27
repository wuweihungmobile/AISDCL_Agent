"use client";

/**
 * 議題中心說明的「狀態說明」段（TCS-PageHelp-20261027 C4、C6、D-PH-7、D-PH-8；PRD AC-PH-04-4、04-5）：狀態、結果、來源、嚴重度四群詞表與日期註記，
 * 逐字取自 `GET /api/v1/issues?limit=1` 回應的 `legend`——前端沒有第二份說明，帳本改了詞，這裡自動跟著換（與議題中心既有的「狀態說明」鈕共用同一份 API 圖例）。
 *  - 取數：`useQuery`，query key `["help","issuesLegend"]`（不掛議題清單的 `["issues"]` 家族、也不用 `useIssues`），沿 `SI_QUERY_OPTIONS`：
 *    失敗不重試、不留快取、每次開啟都重取。只在說明對話框開啟時才掛載，所以其他路由、以及議題中心對話框關閉時，都沒有這個請求；
 *  - 載入中、失敗各一句固定文字（`page-help-legend-loading`、`page-help-legend-error`）；回應沒有詞表（200 但沒有 `legend`，或四群缺一）也走失敗句，不顯示空表；
 *  - 純文字：詞表字串一律以 React 文字節點渲染；本檔不寫死任何狀態詞（靜態鎖 help.static.test.ts 掃本檔）。
 * 刻意不帶 `signal`：請求一旦送出就讓它走完（開關對話框的瞬間不取消、不重送），重取由「每次開啟都重新掛載」保證。
 */
import { useQuery } from "@tanstack/react-query";

import { describeError } from "@/lib/api/client";
import { getIssues } from "@/lib/api/endpoints";
import { SI_QUERY_OPTIONS } from "@/lib/api/queries";
import type { IssueLegend } from "@/lib/api/types";
import { siErrorParts } from "@/lib/domain/si";

type Term = { name: string; meaning: string };

/** 一群詞表：群標題（h4）加定義清單；名稱與說明逐字取自 API。 */
function Group({ title, rows, testId }: { title: string; rows: ReadonlyArray<Term>; testId: string }) {
  return (
    <section aria-label={title} data-testid={testId}>
      <h4 className="text-sm font-semibold">{title}</h4>
      <dl className="mt-1.5 grid grid-cols-[7rem_1fr] gap-x-4 gap-y-1.5 text-sm max-md:grid-cols-1 max-md:gap-y-0.5">
        {rows.map((row, i) => (
          <div key={`${i}-${row.name}`} className="contents">
            <dt className="font-medium">{row.name}</dt>
            <dd className="text-wg-muted max-md:mb-1.5">{row.meaning}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

/** 回應裡可用的圖例：四群都是陣列才算；缺了就回 null（走失敗句，不顯示空表）。 */
function usableLegend(legend: Partial<IssueLegend> | undefined): IssueLegend | null {
  if (typeof legend !== "object" || legend === null) return null;
  return Array.isArray(legend.statuses) && Array.isArray(legend.results) && Array.isArray(legend.sources) && Array.isArray(legend.severities) ? (legend as IssueLegend) : null;
}

/** 失敗的原因：reason、cause、detail 存在者逐字（方便對照 Bridge 日誌）；三者皆空（網路失敗、無詳情）時改接 describeError。 */
function failureReason(error: unknown): string {
  const { reason, cause, detail } = siErrorParts(error);
  const parts = [reason, cause, detail].filter((part): part is string => part !== undefined && part !== "");
  return parts.length > 0 ? parts.join("；") : describeError(error);
}

function Failure({ reason }: { reason: string }) {
  return (
    <p role="alert" data-testid="page-help-legend-error" className="rounded-md border border-wg-line bg-wg-base px-3 py-2 text-sm">
      狀態詞表暫時取不到：{reason}
    </p>
  );
}

export function IssuesLegendGroups() {
  const query = useQuery({ queryKey: ["help", "issuesLegend"], queryFn: () => getIssues({ limit: 1 }), ...SI_QUERY_OPTIONS });

  if (query.isPending) {
    return (
      <p role="status" data-testid="page-help-legend-loading" className="text-sm text-wg-muted">
        狀態詞表載入中…
      </p>
    );
  }
  if (query.isError) return <Failure reason={failureReason(query.error)} />;

  const legend = usableLegend(query.data?.legend);
  if (legend === null) return <Failure reason="回應沒有詞表" />;
  const note = typeof legend.updatedAtNote === "string" ? legend.updatedAtNote : "";
  return (
    <div className="flex flex-col gap-3">
      <Group title="狀態" rows={legend.statuses} testId="page-help-legend-statuses" />
      <Group title="結果" rows={legend.results} testId="page-help-legend-results" />
      <Group title="來源" rows={legend.sources} testId="page-help-legend-sources" />
      <Group title="嚴重度" rows={legend.severities} testId="page-help-legend-severities" />
      {note !== "" ? (
        <p data-testid="page-help-legend-note" className="rounded-md border border-wg-line bg-wg-base px-3 py-2 text-sm">
          {note}
        </p>
      ) : null}
    </div>
  );
}
