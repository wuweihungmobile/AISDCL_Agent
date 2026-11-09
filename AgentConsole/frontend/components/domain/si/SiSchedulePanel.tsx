"use client";

/**
 * 自動演化排程面板（P4；TCS-SelfImprovingSchedule W-S1～W-S6；PRD §0.11）：**只對 ADMIN 渲染**（非 ADMIN 沒有任何控件，唯讀欄位組在狀態橫幅）。
 * 欄位組與橫幅共用 `ScheduleFieldList`（同一個 `scheduleFields`）；三個控件鈕只是開對話框——啟用或停用、修改週期、立即啟動一次演化——
 * 對話框掛在頁層（SiView），面板本身沒有表單、沒有 mutation、不發任何 POST。資料取自狀態橫幅同一個查詢（同查詢鍵，不多打請求）。
 * 面板不替 Console 宣稱任何主機端狀態：`armed` 恆量不到（L-SI-1），寫入送出後只是「稽核檔已落地，待入帳」。
 */
import { Play, Settings2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useSiStatus } from "@/lib/api/queries";
import { scheduleFields } from "@/lib/domain/si";
import { ScheduleFieldList } from "./siParts";

const SHELL = "mb-5 rounded-lg border border-wg-line bg-wg-surface px-5 py-4";

export function SiSchedulePanel({ onSetSchedule, onRequestRun }: { onSetSchedule: (initialEnabled: boolean) => void; onRequestRun: () => void }) {
  const q = useSiStatus();
  // 載入中與失敗由狀態橫幅呈現（同一個查詢）；面板沒有資料就不渲染控件——不拿量不到的現值去預填
  if (q.isError || q.isPending) return null;
  const schedule = q.data.items[0]?.schedule;
  const view = scheduleFields(schedule);
  const enabled = view.enabled;

  return (
    <section data-testid="si-schedule-panel" aria-label="自動演化排程" className={SHELL}>
      <h2 className="text-base font-semibold">自動演化排程</h2>
      <p className="mt-0.5 mb-3 text-[13px] text-wg-muted">啟用、改週期與立即啟動只落稽核檔，由主機端 CLI 入帳後才生效；Console 看不到主機上的排程任務。</p>
      <ScheduleFieldList schedule={schedule} scope="panel" />
      <div className="mt-4 flex flex-wrap gap-2">
        <Button variant="ghost" iconLeft={Settings2} data-testid="si-schedule-toggle-open" onClick={() => onSetSchedule(enabled === null ? true : !enabled)}>
          {enabled === true ? "停用排程" : "啟用排程"}
        </Button>
        <Button variant="ghost" iconLeft={Settings2} data-testid="si-schedule-period-open" onClick={() => onSetSchedule(enabled ?? true)}>
          修改週期
        </Button>
        <Button iconLeft={Play} data-testid="si-run-request-open" onClick={onRequestRun}>
          立即啟動一次演化
        </Button>
      </div>
    </section>
  );
}
