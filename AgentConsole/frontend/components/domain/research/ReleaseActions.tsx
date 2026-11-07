"use client";

/**
 * 發布動作（FR-R2P-20-2、20-3、20-5；TCS-ResearchToPRD-P2-20261107 AT-962-21-3、21-6、21-E-1、21-E-4；IFACE-P2 §6.2、§6.5；D-148 FE-3、D-150 #1）：
 * 「建立 Tag」鈕（開 {@link TagConfirmDialog}）與「開啟本地專案」。
 *
 * 設計要點（為什麼這樣做）：
 *  - **建立 Tag 的停用規則**（任一成立即停用並顯示原因；全部成立才啟用，後端另有 409 再擋一次）：
 *    角色不是 ADMIN、這一步已完成（唯讀檢視）、狀態機現態不是 RELEASE_READY（**即使 RTM 100% 也停用**；AT-962-21-E-1）、未覆蓋大於 0（原因逐 AC 列出）、規格變更進行中
 *    （文案取 `BUILD_DISABLED_TEXT.scrOpen`，不內嵌第二份）。VIEWER 的 `title` 一律是 `READONLY_TITLE`（P0 的 VIEWER 全按鈕鎖逐字比對它）。
 *  - **已交付**（狀態機為 RELEASE 且已有 CREATED 的 RELEASE_TAG 列）：顯示「已建立 <tag>」、鈕停用、不再能送出（AT-962-21-E-4）。
 *  - **開啟本地專案不假裝能開**：瀏覽器沒有開本機資料夾的能力，所以只顯示專案根路徑；OPERATOR 以上另有複製鈕（重用 `CopyCommand`）。
 *    VIEWER 不渲染複製鈕、只顯示可選取的路徑文字（D-150 #1：P0 的 VIEWER 全按鈕鎖是凍結契約，複製是便利不是權利）。容器模式加註「此為容器內路徑」。
 *    沒有 `file://` 連結、不呼叫 `window.open`。
 *  - 本檔不放任何通往執行中心或監控中心的字樣或連結（P0 的反向釘：步驟 5 不得出現）。
 */
import { Tag } from "lucide-react";
import { useState } from "react";

import { CopyCommand } from "@/components/domain/sdd/CopyCommand";
import { Button } from "@/components/ui/button";
import type { ResearchDeliveryOverview, ResearchTraceability } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { BUILD_DISABLED_TEXT, DELIVER_LABEL, READONLY_TITLE, TAG_ADMIN_ONLY_TEXT } from "@/lib/domain/research";
import { TagConfirmDialog } from "./TagConfirmDialog";
import { TRACE_STATUS_TEXT, uncoveredRows } from "./TraceabilityTable";

export const RELEASE_READY_REQUIRED_TEXT = "尚未達 RELEASE_READY：狀態機要先到發布就緒（SCG-4、SCG-5 都登錄通過）才能建立 Tag";

export function ReleaseActions({
  researchId,
  overview,
  traceability,
  fsmRelease,
  scrOpen,
  completed = false,
}: {
  researchId: string;
  overview: ResearchDeliveryOverview;
  traceability: ResearchTraceability;
  /** 狀態機現態是否已是 `RELEASE`（已交付） */
  fsmRelease: boolean;
  scrOpen: boolean;
  completed?: boolean;
}) {
  const { role } = useAuth();
  const [open, setOpen] = useState(false);
  const isAdmin = role === "ADMIN";

  const tagRow = overview.deliveries.find((d) => d.kind === "RELEASE_TAG" && d.status === "CREATED");
  const delivered = fsmRelease && tagRow !== undefined;
  const uncovered = uncoveredRows(traceability.rows);
  const uncoveredCount = Math.max(traceability.totals.uncovered, uncovered.length);

  const roleReason = isAdmin ? null : role === "VIEWER" ? READONLY_TITLE : TAG_ADMIN_ONLY_TEXT;
  const reasons: string[] = [];
  if (roleReason !== null) reasons.push(roleReason);
  if (completed) reasons.push(BUILD_DISABLED_TEXT.completed);
  if (!overview.preconditions.releaseReady) reasons.push(RELEASE_READY_REQUIRED_TEXT);
  if (uncoveredCount > 0) reasons.push(`仍有 ${uncoveredCount} 個${DELIVER_LABEL.uncovered}的驗收條件，補齊測試後才能建立 Tag`);
  if (scrOpen) reasons.push(BUILD_DISABLED_TEXT.scrOpen);
  const enabled = !delivered && reasons.length === 0;
  const title = delivered ? `已建立 ${tagRow.ref}` : (reasons[0] ?? undefined);

  const root = overview.projectRoot;
  const canCopy = role !== undefined && role !== "VIEWER"; // D-150 #1：VIEWER 不渲染複製鈕

  return (
    <section data-testid="release-actions" className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="ghost" iconLeft={Tag} disabled={!enabled} title={title} onClick={() => setOpen(true)} data-testid="tag-create">
            {delivered ? `已建立 ${tagRow.ref}` : DELIVER_LABEL.createTag}
          </Button>
          {delivered ? (
            <span data-testid="tag-delivered" className="text-sm text-wg-muted">
              這個研究專案已交付，不能重複建立 Tag。
            </span>
          ) : null}
        </div>
        {!delivered && reasons.length > 0 ? (
          <div data-testid="tag-block" className="text-sm text-wg-muted">
            <p>無法建立 Tag：</p>
            <ul className="list-disc pl-5">
              {reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
            {uncoveredCount > 0 ? (
              <ul data-testid="tag-uncovered-list" aria-label={`${DELIVER_LABEL.uncovered}的驗收條件`} className="mt-1 list-disc pl-5">
                {uncovered.map((row) => (
                  <li key={row.ac} data-ac={row.ac}>
                    <span className="font-mono">{row.ac}</span>（{TRACE_STATUS_TEXT[row.unitStatus] ?? row.unitStatus}）
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
        {open ? <TagConfirmDialog researchId={researchId} open={open} onOpenChange={setOpen} /> : null}
      </div>

      <div data-testid="open-local" className="flex flex-col gap-2">
        <h4 className="text-base font-semibold">{DELIVER_LABEL.openLocal}</h4>
        {root === null || root === "" ? (
          <p data-testid="project-root-none" className="text-sm text-wg-muted">
            尚無專案根路徑（尚未完成分流）。
          </p>
        ) : canCopy ? (
          <div data-testid="project-root-copy">
            <CopyCommand shell="project-root" label="專案根路徑" command={root} />
          </div>
        ) : (
          <div>
            <span className="mb-1 block text-xs font-medium text-wg-muted">專案根路徑</span>
            <pre data-testid="project-root" className="rounded-md border border-wg-line bg-white px-3 py-2 font-mono text-xs break-all whitespace-pre-wrap select-text">
              {root}
            </pre>
          </div>
        )}
        {overview.containerMode ? (
          <p data-testid="project-root-container" className="text-sm font-medium">
            此為容器內路徑
          </p>
        ) : null}
        <p data-testid="open-local-note" className="text-[13px] text-wg-muted">
          系統不會直接開啟資料夾；請{canCopy ? "複製" : "選取"}路徑後自行在本機開啟。
        </p>
      </div>
    </section>
  );
}
