"use client";

/**
 * 工作流頁首列（FR-R2P-22；TCS-ResearchToPRD-P0-20261102 AT-960-20-1；ADR-003 D12）：研究工作區內、五步共用的**唯一一份**頁首——
 * ① 研究專案切換下拉（列出可見的研究專案並顯示關聯的 Console 專案名，選擇後導向該專案游標所在步）；
 * ② 狀態燈（Escalated、Healing、Running、Paused、Idle 五態，優先序見 `lampOf`；以文字標籤為準，顏色只作輔助）；
 * ③ Token 速率（近 5 分鐘增量除以 5；無事件顯示「—」）與預算進度（取該研究專案 run 的預算，沒有則取系統參數 `execution.globalTokenBudget`；
 *    用量達 `execution.tokenBudgetWarningThreshold`（初值 0.8）時轉警示）。
 * 全站頂列與底列一概不動：這裡只是工作區版面內的一塊（全站狀態燈列是延後項，D-31）。資料全由既有查詢與純函式取得，不新增遙測來源：
 * Token 取自 `research.run` 事件的累計值（`lib/domain/research.ts` 的 `tokenRate`、`tokensUsedTotal`）。
 */
import { useRouter } from "next/navigation";

import { Progress } from "@/components/ui/progress";
import { Select } from "@/components/ui/select";
import { StatusDot } from "@/components/ui/status-dot";
import { useNow } from "@/hooks/useNow";
import { useAllProjects, useResearchEvents, useResearchProjects, useSettingsCategory } from "@/lib/api/queries";
import type { ResearchProjectDetail } from "@/lib/api/types";
import { LAMP_META, budgetState, executionBudgetSettings, formatTokenRate, lampInputsOf, lampOf, resolveBudget, tokenRate, tokensUsedTotal } from "@/lib/domain/research";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

/** 速率與預算的重算間隔（毫秒）：視窗是滾動的，事件沒到也要定期重算。 */
const REFRESH_MS = 15_000;

export function ResearchFlowHeader({ project }: { project: ResearchProjectDetail }) {
  const router = useRouter();
  const list = useResearchProjects();
  const consoleProjects = useAllProjects();
  const running = project.flow.effective.status === "RUNNING";
  const events = useResearchEvents(project.id, { poll: running });
  const settings = useSettingsCategory("execution");
  const now = useNow(true, REFRESH_MS);

  const consoleName = new Map((consoleProjects.data?.content ?? []).map((p) => [p.id, p.name] as const));
  const optionLabel = (p: { rpNo: string; title: string; consoleProjectId: string | null }) => {
    const name = p.consoleProjectId === null ? undefined : consoleName.get(p.consoleProjectId);
    return `${p.rpNo} · ${p.title}${name === undefined ? "" : `（Console：${name}）`}`;
  };
  const visible = (list.data ?? []).filter((p) => p.archivedAt === null);
  const options = visible.some((p) => p.id === project.id) ? visible : [project, ...visible];

  const inputs = lampInputsOf(project);
  const lampKind = lampOf(inputs.run, inputs.fsm, inputs.tasks);
  const lamp = LAMP_META[lampKind];
  const eventList = events.data;
  const rate = eventList === undefined ? null : tokenRate(eventList, now);
  const used = eventList === undefined ? null : tokensUsedTotal(eventList);
  const budgetSettings = executionBudgetSettings(settings.data ?? []);
  const budget = resolveBudget(null, budgetSettings.globalTokenBudget);
  const state = budgetState(used ?? 0, budget, budgetSettings.warnAt);
  const warn = used !== null && state.level === "warn";

  return (
    <section aria-label="研發工作流頁首" data-testid="research-flow-header" className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-3 rounded-lg border border-wg-line bg-wg-surface px-4 py-3">
      <div className="flex min-w-0 items-center gap-2">
        <span aria-hidden className="text-xs text-wg-muted">
          研究專案
        </span>
        <Select
          size="sm"
          aria-label="切換研究專案"
          data-testid="research-switcher"
          value={project.id}
          onChange={(e) => {
            const target = options.find((p) => p.id === e.target.value);
            if (target !== undefined) router.push(`/research/${target.id}?step=${target.flowStep}`);
          }}
          className="max-w-[320px] min-w-0"
        >
          {options.map((p) => (
            <option key={p.id} value={p.id}>
              {optionLabel(p)}
            </option>
          ))}
        </Select>
      </div>

      <div role="status" data-testid="flow-lamp" data-lamp={lampKind} className="inline-flex items-center gap-1.5 text-sm">
        <StatusDot color={lamp.color} size={10} live={lampKind === "Running" || lampKind === "Healing"} />
        <span className="sr-only">引擎狀態：</span>
        <span className="font-medium">{lamp.label}</span>
      </div>

      <div data-testid="token-rate" className="inline-flex items-center gap-1.5 text-sm">
        <span className="text-xs text-wg-muted">Token 速率</span>
        <span className="font-semibold">{formatTokenRate(rate)}</span>
      </div>

      <div data-testid="token-budget" data-level={used === null ? "unknown" : state.level} className="inline-flex min-w-[220px] flex-1 items-center gap-2 text-sm">
        <span className="text-xs text-wg-muted">預算</span>
        <Progress value={state.percent ?? 0} label="Token 預算進度" className="w-28" barClassName={cn(warn && "bg-wg-warning")} />
        <span>
          已用 {used === null ? "—" : formatNumber(used)} / {budget === null ? "—" : formatNumber(budget)}
          {state.percent !== null && used !== null ? `（${state.percent}%）` : ""}
        </span>
        {warn ? (
          <span role="status" className="text-xs font-medium text-wg-warning-text">
            已達預算警示閾值
          </span>
        ) : null}
      </div>
    </section>
  );
}
