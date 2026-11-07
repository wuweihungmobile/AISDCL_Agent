"use client";

/**
 * 預演結果（FR-R2P-11-2；TCS-ResearchToPRD-P1-20261107 AT-961-17-5）：動作清單（動作、目標、是否觸及外部系統）、警示、（軌道 B）初始 commit 預期入版控的檔案。
 * 所有文字（含 target、detail、warnings）一律以純文字渲染——它們可能含 `<script>`，沒有任何 `dangerouslySetInnerHTML`；外部系統標示用徽章文字加 Lucide 圖示，不只靠顏色。
 */
import { Globe, TriangleAlert } from "lucide-react";

import type { ResearchRoutePreview } from "@/lib/api/types";
import { isExternalRouteAction, routeStepLabel } from "@/lib/domain/research";

export function RouteActionList({ preview }: { preview: ResearchRoutePreview }) {
  return (
    <div data-testid="route-preview" className="flex flex-col gap-3">
      <p className="text-sm text-wg-muted">
        預演結果：共 {preview.actions.length} 個動作，內環鍵 <span className="font-mono">{preview.implFsmProject}</span>；預演沒有改動任何東西。
      </p>
      {preview.warnings.length > 0 ? (
        <ul data-testid="route-warnings" className="flex flex-col gap-1">
          {preview.warnings.map((warning) => (
            <li key={`${warning.code}:${warning.message}`} className="flex items-center gap-2 text-sm font-medium text-wg-warning-text">
              <TriangleAlert size={16} aria-hidden />
              {warning.message}
            </li>
          ))}
        </ul>
      ) : null}
      <ol data-testid="route-actions" aria-label="預演的動作清單" className="flex flex-col gap-2">
        {preview.actions.map((action) => {
          const external = isExternalRouteAction(action);
          return (
            <li key={action.seq} data-external={external || undefined} className="flex flex-col gap-0.5 rounded-md border border-wg-line px-3 py-2 text-sm">
              <span className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">
                  {action.seq}. {routeStepLabel(action.step)}
                </span>
                <span className="font-mono text-xs text-wg-muted">{action.action}</span>
                {external ? (
                  <span className="inline-flex items-center gap-1 rounded-sm bg-wg-draft-bg px-1.5 py-0.5 text-xs font-semibold text-wg-accent">
                    <Globe size={12} aria-hidden />
                    外部系統
                  </span>
                ) : null}
              </span>
              <span className="break-all font-mono text-[13px]">{action.target}</span>
              {action.detail !== "" ? <span className="text-[13px] text-wg-muted">{action.detail}</span> : null}
            </li>
          );
        })}
      </ol>
      {preview.expectedTrackedFiles.length > 0 ? (
        <details data-testid="route-tracked-files" className="text-sm">
          <summary className="cursor-pointer font-medium">初始提交預期入版控的檔案（{preview.expectedTrackedFiles.length}）</summary>
          <ul className="mt-1 flex flex-col gap-0.5 font-mono text-[13px]">
            {preview.expectedTrackedFiles.map((file) => (
              <li key={file} className="break-all">
                {file}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
