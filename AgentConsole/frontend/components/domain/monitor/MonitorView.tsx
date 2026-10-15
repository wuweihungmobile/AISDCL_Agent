"use client";

import { closestCenter, DndContext, KeyboardSensor, PointerSensor, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Activity, GripVertical } from "lucide-react";
import { useParams } from "next/navigation";
import { useState, useSyncExternalStore, type ReactNode } from "react";

import { RunSelect } from "@/components/domain/execute/parts";
import { BackLink, PageTitle } from "@/components/domain/PageHeader";
import { Select } from "@/components/ui/select";
import { ErrorState, PageSkeleton } from "@/components/ui/states";
import { useMonitorPollMs, useProject, useProjectExecutions, useProjectMetrics, useTaskTrend, useTokenTrend } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/AuthProvider";
import { DEFAULT_RANGE, MONITOR_RANGES, bucketFor, isRangeId, type RangeId } from "@/lib/domain/metrics";
import { SECTION_TITLE, getLayout, getServerLayout, moveSection, resetLayout, saveLayout, subscribeLayout, type SectionId } from "@/lib/nav/monitorLayout";
import { cn } from "@/lib/utils";
import { AgentCard } from "./AgentCard";
import { AlertsCard } from "./AlertsCard";
import { DistributionCards, TokenTrendCard, TrendCards } from "./ChartCards";
import { CompareCard } from "./CompareCard";
import { ExportBar } from "./ExportBar";
import { KpiCards } from "./KpiCards";
import { LogQueryCard } from "./LogQueryCard";
import { TimelineCard } from "./TimelineCard";

function SortableSection({ id, editing, children }: { id: SectionId; editing: boolean; children: ReactNode }) {
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } = useSortable({ id, disabled: !editing });
  return (
    <section
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      data-testid={`section-${id}`}
      data-section={id}
      aria-label={SECTION_TITLE[id]}
      className={cn("relative", editing && "rounded-lg border border-dashed border-wg-primary p-2", isDragging && "z-10 bg-wg-base opacity-80")}
    >
      {editing ? (
        <div className="mb-2 flex items-center gap-2 text-xs text-wg-muted">
          <button
            ref={setActivatorNodeRef}
            type="button"
            aria-label={`拖曳排序：${SECTION_TITLE[id]}`}
            title="拖曳排序（鍵盤：空白鍵拿起、方向鍵移動、空白鍵放下）"
            data-testid={`drag-${id}`}
            className="inline-flex size-6 shrink-0 cursor-grab touch-none items-center justify-center rounded-sm border-none bg-transparent text-wg-muted hover:text-wg-primary active:cursor-grabbing"
            {...attributes}
            {...listeners}
          >
            <GripVertical size={16} aria-hidden />
          </button>
          {SECTION_TITLE[id]}
        </div>
      ) : null}
      {children}
    </section>
  );
}

/**
 * 專案監控頁（設計稿畫面 8；契約 §1.3、§4.3；PRD §5.4）：
 * 返回連結、標題、右側時間範圍（1h／24h／7d／30d）與執行批次下拉；指標卡、Token 趨勢、狀態與時間分佈、任務趨勢、事件時間軸、
 * 日誌查詢、告警、批次比較、Agent 即時狀態；底部匯出報表／設定告警／自訂儀表板。
 * 各區塊可拖曳重排（自訂儀表板；順序存 localStorage console.monitor.layout）。
 * 輪詢間隔＝max(monitor.refreshIntervalMs，15 秒)，頁面不可見時暫停（契約 §0.4 第 4 點、§1.3）。
 */
export function MonitorView() {
  const { projectId } = useParams<{ projectId: string }>();
  const { canWrite } = useAuth();
  const pollMs = useMonitorPollMs();

  const project = useProject(projectId);
  const runsQ = useProjectExecutions(projectId, { size: 20, sort: "startedAt,desc" }, { pollMs });
  const runs = runsQ.data?.content ?? [];

  const [range, setRange] = useState<RangeId>(DEFAULT_RANGE);
  const [runFilter, setRunFilter] = useState(""); // 空字串＝專案全部批次
  const runId = runFilter || undefined;
  const q = { runId, range };

  const metricsQ = useProjectMetrics(projectId, q, pollMs);
  const tokenQ = useTokenTrend(projectId, q, pollMs);
  const taskQ = useTaskTrend(projectId, q, pollMs);
  const bucket = bucketFor(range);

  // 事件時間軸與 Agent 狀態看單一批次：選了就用它，選「全部批次」取最新一筆（契約 §4.3 M-12）
  const focusRun = runs.find((r) => r.id === runFilter) ?? runs[0];

  const order = useSyncExternalStore(subscribeLayout, getLayout, getServerLayout);
  const [editing, setEditing] = useState(false);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }), useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }));

  function onDragEnd(e: DragEndEvent) {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    const from = order.indexOf(active.id as SectionId);
    const to = order.indexOf(over.id as SectionId);
    if (from < 0 || to < 0) return;
    saveLayout(moveSection(order, from, to));
  }

  if (project.isError) {
    return (
      <div>
        <BackLink href={`/projects/${projectId}`}>返回專案</BackLink>
        <ErrorState error={project.error} onRetry={() => project.refetch()} title="無法載入專案" />
      </div>
    );
  }
  if (!project.data) {
    return (
      <div>
        <BackLink href={`/projects/${projectId}`}>返回專案</BackLink>
        <PageSkeleton />
      </div>
    );
  }

  const sections: Record<SectionId, ReactNode> = {
    kpi: <KpiCards metrics={metricsQ.data} loading={metricsQ.isPending} error={metricsQ.error} onRetry={() => metricsQ.refetch()} />,
    token: <TokenTrendCard points={tokenQ.data} bucket={bucket} loading={tokenQ.isPending} error={tokenQ.error} onRetry={() => tokenQ.refetch()} />,
    distribution: <DistributionCards metrics={metricsQ.data} loading={metricsQ.isPending} error={metricsQ.error} onRetry={() => metricsQ.refetch()} />,
    trends: <TrendCards taskTrend={taskQ.data} metrics={metricsQ.data} bucket={bucket} loading={taskQ.isPending} error={taskQ.error} onRetry={() => taskQ.refetch()} />,
    timeline: <TimelineCard runId={focusRun?.id} pollMs={pollMs} runLabel={focusRun ? `Run #${focusRun.runNumber}` : undefined} />,
    logs: <LogQueryCard projectId={projectId} range={range} runId={runId} pollMs={pollMs} />,
    alerts: <AlertsCard projectId={projectId} runId={runId} pollMs={pollMs} canWrite={canWrite} />,
    compare: <CompareCard runs={runs} />,
    agent: <AgentCard runId={focusRun?.id} availability={metricsQ.data?.agentAvailability} />,
  };

  return (
    <div data-testid="monitor-view">
      <BackLink href={`/projects/${projectId}`}>返回專案</BackLink>
      <PageTitle
        icon={Activity}
        title={`專案監控：${project.data.name}`}
        subtitle="指標 · 趨勢 · 日誌 · 告警"
        className="[&_h2]:text-[28px]"
        actions={
          <>
            <label className="inline-flex items-center gap-2 text-sm text-wg-muted">
              時間範圍
              <Select size="sm" value={range} onChange={(e) => isRangeId(e.target.value) && setRange(e.target.value)} aria-label="時間範圍" data-testid="range-select">
                {MONITOR_RANGES.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.label}
                  </option>
                ))}
              </Select>
            </label>
            <RunSelect runs={runs} value={runFilter} onChange={setRunFilter} allOption="全部批次" />
          </>
        }
      />

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
        <SortableContext items={[...order]} strategy={verticalListSortingStrategy}>
          <div className="flex flex-col gap-6" data-testid="monitor-sections">
            {order.map((id) => (
              <SortableSection key={id} id={id} editing={editing}>
                {sections[id]}
              </SortableSection>
            ))}
          </div>
        </SortableContext>
      </DndContext>

      <ExportBar projectId={projectId} range={range} runId={runId} editing={editing} onToggleEditing={() => setEditing((v) => !v)} onResetLayout={resetLayout} />
    </div>
  );
}
