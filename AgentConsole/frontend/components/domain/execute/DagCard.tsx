"use client";

import { ChevronsDownUp, ChevronsUpDown, Maximize2, Minimize2 } from "lucide-react";
import { useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";
import type { Dag } from "@/lib/api/types";
import { TONE_LABEL, layoutDag, nodeTone, overlayDag, type DagColumn, type DagTone } from "@/lib/domain/dag";
import type { TaskLive } from "@/lib/domain/runLive";
import { cn } from "@/lib/utils";

/**
 * 設計稿：完成＝主色實底；進行中＝tertiary 底＋主色邊；待處理＝灰底（失敗、略過另有色調）。
 * 待處理的字用次要文字色（設計稿用 disabled 文字色 #A6B0A1，在灰底只有 1.86:1，節點上的目標名與步驟代碼讀不出來；DEF-AC-004）：
 * 底色仍是灰，所以「還沒輪到」的辨識度不變。
 */
const NODE_CLASS: Record<DagTone, string> = {
  done: "border-wg-primary bg-wg-primary text-white",
  active: "border-wg-primary bg-wg-tertiary text-wg-text",
  pending: "border-transparent bg-wg-disabled-bg text-wg-muted",
  failed: "border-wg-error bg-wg-draft-bg text-wg-error",
  skipped: "border-wg-line bg-wg-base text-wg-muted",
};

/** 任務節點只顯示 step_id 的最後一段（G1-T2 → T2）；其餘資訊放 title 與螢幕閱讀器清單。 */
const shortCode = (stepId: string | undefined, fallback: string): string => {
  if (!stepId) return fallback;
  const tail = stepId.split("-").pop();
  return tail && tail.length > 0 ? tail : stepId;
};

function Connector({ kind }: { kind: "dependency" | "sequence" }) {
  return kind === "dependency" ? (
    <span aria-hidden data-testid="dag-connector" data-kind="dependency" className="mx-1 h-0.5 w-9 shrink-0 bg-wg-line" />
  ) : (
    <span aria-hidden data-testid="dag-connector" data-kind="sequence" className="mx-1 h-0 w-9 shrink-0 border-t-2 border-dashed border-wg-line" />
  );
}

/**
 * 全螢幕覆蓋層的外框（契約 §4.2 E-22，v1.4 D-20）：把共用層 Dialog 的白卡鋪滿視窗——頁面內覆蓋層，不用瀏覽器 Fullscreen API（需要使用者手勢、無頭測試不可用）。
 * Dialog 帶來焦點鎖、Esc、背景 aria-hidden 與「關閉後焦點歸還開啟它的按鈕」（DEF-AC-011 的共用層機制）。
 * inset-0＋寬高 auto：尺寸＝視窗（不用 100vw，那會把捲軸寬度算進去）；其餘覆寫掉白卡的置中、560px 寬、88vh 高上限、圓角與邊框。
 */
const FULLSCREEN_CLASS = "inset-0 h-auto w-auto max-h-none max-w-none translate-x-0 translate-y-0 rounded-none border-0";

/** 圖形主體：載入／錯誤／空狀態與目標＋任務節點。同一時間只掛一份（卡內或全螢幕內），測試用的 data-testid 因此始終唯一。 */
function DagBody({
  dag,
  columns,
  open,
  loading,
  error,
  onRetry,
  fullscreen,
}: {
  dag: Dag | undefined;
  columns: DagColumn[];
  /** 展開任務節點（false＝只畫目標） */
  open: boolean;
  loading: boolean;
  error: unknown;
  onRetry: () => void;
  fullscreen: boolean;
}) {
  if (error) return <ErrorState error={error} onRetry={onRetry} title="無法載入 DAG" />;
  if (loading && !dag) return <Skeleton className="h-24" />;
  if (columns.length === 0) return <p className="text-sm text-wg-muted">啟動執行後，這裡會顯示目標與任務的依賴關係與即時進度。</p>;
  return (
    <>
      {/* 全螢幕裡的圖形會被視窗大小限制而可捲動：給它鍵盤焦點與名稱，才過 axe 的 scrollable-region-focusable，鍵盤使用者也捲得動 */}
      <div
        className={cn("pb-2", fullscreen ? "min-h-0 flex-1 overflow-auto" : "overflow-x-auto")}
        data-testid="dag-scroll"
        {...(fullscreen ? { tabIndex: 0, role: "region", "aria-label": "DAG 圖形（可用方向鍵捲動）" } : {})}
      >
        <div className="flex w-max items-start" role="img" aria-label={`DAG：${columns.map((c, i) => `G${i + 1} ${TONE_LABEL[nodeTone(c.goal.status)]}`).join("、")}`}>
          {columns.map((c, i) => {
            const goalTone = nodeTone(c.goal.status);
            return (
              <div key={c.goal.id} className="flex items-start">
                {c.connector !== "none" ? (
                  <div className="flex h-9 items-center">
                    <Connector kind={c.connector} />
                  </div>
                ) : null}
                <div className="flex min-w-[88px] flex-col items-center gap-1.5" data-testid={`dag-col-${c.goal.id}`}>
                  <span
                    data-testid={`dag-goal-${c.goal.id}`}
                    data-tone={goalTone}
                    title={`${c.goal.label}（${TONE_LABEL[goalTone]}）`}
                    className={cn(
                      "inline-flex h-9 min-w-[64px] max-w-[140px] items-center justify-center gap-1.5 rounded-md border px-3 text-sm font-semibold transition-colors",
                      NODE_CLASS[goalTone],
                      goalTone === "active" && "animate-wg-blink",
                    )}
                  >
                    G{c.goal.sequence ?? i + 1}
                    {/* 不加 opacity：主色底上的小字淡化後只剩 4.03:1（純白 4.55:1） */}
                    <span className="truncate text-xs font-normal">{c.goal.label}</span>
                  </span>
                  {c.dependsOn.length > 0 && c.connector !== "dependency" ? (
                    <span className="text-[11px] text-wg-muted" data-testid={`dag-deps-${c.goal.id}`}>
                      依賴 {c.dependsOn.map((id) => `G${columns.find((x) => x.goal.id === id)?.goal.sequence ?? "?"}`).join("、")}
                    </span>
                  ) : null}
                  {open
                    ? c.tasks.map((t, ti) => {
                        const tone = nodeTone(t.status);
                        return (
                          <span
                            key={t.id}
                            data-testid={`dag-task-${t.id}`}
                            data-tone={tone}
                            title={`${t.stepId ?? ""} ${t.label}（${TONE_LABEL[tone]}）`.trim()}
                            className={cn(
                              "inline-flex h-6 min-w-[44px] items-center justify-center rounded-sm border px-1.5 font-mono text-[11px] transition-colors",
                              NODE_CLASS[tone],
                              tone === "active" && "animate-wg-blink",
                            )}
                          >
                            {shortCode(t.stepId, `T${ti + 1}`)}
                          </span>
                        );
                      })
                    : null}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <ul className="sr-only" data-testid="dag-summary">
        {columns.map((c) => (
          <li key={c.goal.id}>
            {c.goal.label}：{TONE_LABEL[nodeTone(c.goal.status)]}（{c.tasks.length} 個任務，完成 {c.tasks.filter((t) => nodeTone(t.status) === "done").length}）
          </li>
        ))}
      </ul>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-wg-muted" aria-hidden>
        {(["done", "active", "pending", "failed"] as const).map((t) => (
          <span key={t} className="inline-flex items-center gap-1.5">
            <span className={cn("inline-block size-3 rounded-sm border", NODE_CLASS[t])} />
            {TONE_LABEL[t]}
          </span>
        ))}
      </div>
    </>
  );
}

/**
 * 「DAG 依賴視覺化」卡（設計稿畫面 7 右下；契約 §1.2.8、§4.2 E-13／E-22；PRD US-E-09）：
 * 目標節點橫向排列 G1 ─── G2 ─── G3（可橫向捲動），各目標下方列任務節點；顏色依狀態。
 * REST 的節點狀態是讀取當下的現況，串流看到的任務狀態（live）即時疊上去（lib/domain/dag.ts 的 overlayDag）。
 *
 * 全螢幕（E-22，v1.4，D-20；PRD §5.3.6 wireframe 的 `[展開/收合] [全螢幕]`）：標題列的「全螢幕」鈕把圖形搬進鋪滿視窗的覆蓋層，
 * 覆蓋層內的鈕變「結束全螢幕」（aria-pressed 同步），Esc 同樣結束，結束後焦點回到「全螢幕」鈕。
 * 圖形只掛一份（全螢幕時卡內換成等高的空位，結束時版面不跳），所以 SSE 驅動的節點狀態照常更新、展開／收合狀態進出全螢幕都保留。
 */
export function DagCard({ dag, live, loading, error, onRetry }: { dag: Dag | undefined; live: Readonly<Record<string, TaskLive>>; loading: boolean; error: unknown; onRetry: () => void }) {
  const [open, setOpen] = useState(true);
  const [fullscreen, setFullscreen] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);
  const [reservedHeight, setReservedHeight] = useState(0);
  const columns = useMemo(() => (dag ? layoutDag(overlayDag(dag, live)) : []), [dag, live]);

  const enterFullscreen = () => {
    setReservedHeight(bodyRef.current?.offsetHeight ?? 0); // 圖形搬走後卡內留同高的空位：結束全螢幕時頁面不會因為卡片忽高忽低而跳動
    setFullscreen(true);
  };
  const expandToggle = (testId: string) => (
    <Button variant="ghost" size="sm" iconLeft={open ? ChevronsDownUp : ChevronsUpDown} onClick={() => setOpen((v) => !v)} aria-expanded={open} data-testid={testId}>
      {open ? "收合任務" : "展開任務"}
    </Button>
  );
  const body = { dag, columns, open, loading, error, onRetry };

  return (
    <Card className="px-[22px] py-5" data-testid="dag-card">
      <div className="mb-3 flex items-center justify-between gap-2">
        <CardTitle>DAG 依賴視覺化</CardTitle>
        {columns.length > 0 ? (
          <div className="flex items-center gap-1">
            {expandToggle("dag-toggle")}
            <Button variant="ghost" size="sm" iconLeft={Maximize2} onClick={enterFullscreen} aria-pressed={fullscreen} data-testid="dag-fullscreen-open">
              全螢幕
            </Button>
          </div>
        ) : null}
      </div>

      {fullscreen ? (
        <div aria-hidden data-testid="dag-placeholder" style={{ height: reservedHeight }} />
      ) : (
        <div ref={bodyRef}>
          <DagBody {...body} fullscreen={false} />
        </div>
      )}

      <Dialog open={fullscreen} onOpenChange={setFullscreen}>
        <DialogContent title="DAG 依賴視覺化" description="目標與任務的依賴關係與即時進度。按 Esc 或「結束全螢幕」回到執行頁。" className={FULLSCREEN_CLASS} data-testid="dag-fullscreen">
          <div className="flex min-h-0 flex-1 flex-col gap-3 px-6 py-4">
            <div className="flex items-center justify-end gap-1">
              {columns.length > 0 ? expandToggle("dag-fs-toggle") : null}
              <Button variant="ghost" size="sm" iconLeft={Minimize2} onClick={() => setFullscreen(false)} aria-pressed={fullscreen} data-testid="dag-fullscreen-exit">
                結束全螢幕
              </Button>
            </div>
            <DagBody {...body} fullscreen />
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
