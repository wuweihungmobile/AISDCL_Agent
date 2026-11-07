"use client";

/**
 * 覆蓋矩陣與未覆蓋清單（FR-R2P-14、AC-R2P-14-2；TCS-ResearchToPRD-P1-20261107 AT-961-18-1、18-2、18-E-1）：
 *  - 矩陣：列為 AC、欄為 task，涵蓋處以圖示加可及名稱標示（不只靠顏色）；每列、每欄都有可及名稱；可切換「只看未覆蓋」。
 *    200 個 AC 乘 24 個 task 約五千格，格子只在涵蓋時才畫圖示；矩陣資料由 `coverageMatrix` 一次算好（每個 task 一個 Set）。
 *  - 清單：未覆蓋的 AC 逐條列出，可編輯時每條配一個 {@link WaiverInput}；唯讀（已簽核）時只顯示已存的豁免理由。
 * 純文字渲染：AC 編號、task 名稱一律當文字，不當 HTML。
 */
import { Check } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { coverageMatrix, decompositionTree, type CoverageView } from "@/lib/domain/research";
import type { ResearchDecomposition } from "@/lib/api/types";
import { WaiverInput } from "./WaiverInput";

export function CoverageList({
  decomposition,
  view,
  inputs,
  onInput,
  editable,
  lockTitle,
}: {
  decomposition: Pick<ResearchDecomposition, "goals" | "waivers">;
  view: CoverageView;
  inputs: Readonly<Record<string, string>>;
  onInput: (ac: string, value: string) => void;
  /** 草稿態：顯示豁免輸入欄；否則（已簽核）只顯示已存的豁免理由 */
  editable: boolean;
  /** 草稿態卻不能輸入（唯讀角色、已完成步驟、規格變更中）時的停用說明；有值即停用所有輸入欄 */
  lockTitle?: string;
}) {
  const [onlyUncovered, setOnlyUncovered] = useState(false);
  const tree = useMemo(() => decompositionTree(decomposition.goals), [decomposition.goals]);
  const uncoveredSet = useMemo(() => new Set(view.uncovered), [view.uncovered]);
  const rows = useMemo(() => (onlyUncovered ? view.acs.filter((ac) => uncoveredSet.has(ac)) : view.acs), [onlyUncovered, view.acs, uncoveredSet]);
  const matrix = useMemo(() => coverageMatrix(tree, rows), [tree, rows]);
  const storedWaivers = useMemo(() => new Map(decomposition.waivers.map((w) => [w.ac, w.reason] as const)), [decomposition.waivers]);

  return (
    <div className="flex flex-col gap-4" data-testid="coverage">
      <div className="flex flex-wrap items-center gap-3">
        <h4 className="text-[15px] font-semibold">覆蓋矩陣</h4>
        <span data-testid="coverage-summary" className="text-sm text-wg-muted">
          已覆蓋 {view.covered} ／ 共 {view.total} 個驗收條件
        </span>
        <Button size="sm" variant="ghost" aria-pressed={onlyUncovered} onClick={() => setOnlyUncovered((v) => !v)}>
          {onlyUncovered ? "顯示全部" : "只看未覆蓋"}
        </Button>
      </div>

      {rows.length === 0 || matrix.tasks.length === 0 ? (
        <p data-testid="coverage-matrix-empty" className="text-sm text-wg-muted">
          {matrix.tasks.length === 0 ? "拆解裡還沒有任何任務。" : "沒有符合條件的驗收條件。"}
        </p>
      ) : (
        <div tabIndex={0} role="region" aria-label="覆蓋矩陣（可捲動）" className="max-h-96 overflow-auto rounded-md border border-wg-line">
          <table data-testid="coverage-matrix" className="min-w-full border-collapse text-[13px]">
            <caption className="sr-only">驗收條件與任務的涵蓋關係</caption>
            <thead>
              <tr>
                <th scope="col" className="sticky left-0 top-0 z-10 border-b border-wg-line bg-wg-surface px-3 py-2 text-left font-semibold">
                  驗收條件
                </th>
                {matrix.tasks.map((task) => (
                  <th
                    key={task.id}
                    scope="col"
                    title={task.name}
                    aria-label={`任務 ${task.id}${task.name === "" ? "" : `：${task.name}`}`}
                    className="sticky top-0 border-b border-wg-line bg-wg-surface px-2 py-2 font-mono font-medium"
                  >
                    {task.id}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((ac, i) => (
                <tr key={ac} data-ac={ac} data-uncovered={uncoveredSet.has(ac) || undefined}>
                  <th scope="row" className="sticky left-0 bg-wg-surface px-3 py-1.5 text-left font-mono font-medium">
                    {ac}
                    {uncoveredSet.has(ac) ? <span className="ml-2 font-sans text-wg-accent">未覆蓋</span> : null}
                  </th>
                  {matrix.cells[i].map((hit, j) => (
                    <td key={matrix.tasks[j].id} className="px-2 py-1.5 text-center" aria-label={hit ? `${ac} 由 ${matrix.tasks[j].id} 涵蓋` : undefined}>
                      {hit ? <Check size={14} aria-hidden className="mx-auto text-wg-primary-strong" /> : null}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex flex-col gap-3">
        <h4 className="text-[15px] font-semibold">未覆蓋的驗收條件（{view.uncovered.length}）</h4>
        {view.uncovered.length === 0 ? (
          <p data-testid="uncovered-none" className="text-sm text-wg-muted">
            每個驗收條件都至少被一個任務涵蓋。
          </p>
        ) : (
          <ul data-testid="uncovered-list" className="flex flex-col gap-3">
            {view.uncovered.map((ac) => (
              <li key={ac} data-ac={ac} className="flex flex-col gap-1.5 rounded-md border border-wg-line px-3 py-2">
                <span className="font-mono text-sm font-medium">{ac}</span>
                {editable ? (
                  <WaiverInput
                    ac={ac}
                    value={inputs[ac] ?? storedWaivers.get(ac) ?? ""}
                    onChange={(next) => onInput(ac, next)}
                    disabled={lockTitle !== undefined}
                    title={lockTitle}
                    error={view.errors[ac]}
                  />
                ) : (
                  <span data-testid="waiver-readonly" className="text-sm text-wg-muted" title={lockTitle}>
                    {storedWaivers.has(ac) ? `豁免理由：${storedWaivers.get(ac)}` : "尚無豁免理由"}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
