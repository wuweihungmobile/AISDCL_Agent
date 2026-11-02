"use client";

/**
 * 議題面板（研究工作區步驟 1；PRD 頁面 1；FR-R2P-04、06；TCS-ResearchToPRD-P0-20261102 AT-960-19-7）：
 * ① 議題（命題、檢索範圍、目標技術棧、檢索深度、來源層）與主動作「啟動深研」；② 三個分頁——動態欄（`EvidenceTimeline`）、證據矩陣表、技術優缺點矩陣
 * （`EvidenceMatrixTable`）；③ 研究完成後的主動作「生成 PRD 初稿」。面板由頁殼以 `panels={{ topic: TopicPanel }}` 注入工作區（`ResearchPanelProps`）。
 *
 * 設計要點（為什麼這樣做）：
 *  - **議題內容唯讀呈現資料庫版本**：命題、範圍、深度與來源層在建立研究專案時定案；P0 的 API 契約沒有範圍修訂端點（`POST …/stages/research` 的本文也沒有範圍欄位），
 *    所以這裡不放會「看似可改、實際不生效」的輸入框。
 *  - **啟動閘分兩層，原因都寫在畫面上**：環境（探針失敗、Bridge 沒連資料庫、容器模式只跑 mock claude、找不到 claude）與角色／步驟（VIEWER、已完成步驟的唯讀檢視）。
 *    停用的按鈕一律說明為什麼——環境類寫在按鈕旁、角色類寫在 `title`（VIEWER 為「權限不足（唯讀角色）」）。伺服器端不因 mock-only 拒絕（供 API 直呼驗證），這只是 UI 的停用。
 *  - **研究失敗不得顯示為完成**：游標 `flow_status=FAILED`（初始化失敗不算）時顯示橫幅「研究未完成：原因」加「續跑」（`no_evidence` 是「研究失敗」加「重試」，沒有 checkpoint 可續）；
 *    續跑與重試都是再 POST 一次 `stages/research`（`attempt` 加一由伺服端決定）。
 *  - **「生成 PRD 初稿」由證據閘把關**：游標在 `EVIDENCE_READY` 且最新矩陣至少 `MIN_EVIDENCE_ROWS` 列「層級 V2 以上、非 UNANCHORED、非線索」才啟用；不過時停用並說明缺什麼。
 *    成功後導向步驟 2（`?step=studio`）；游標由 Bridge 推進，前端沒有「推進步驟」的動作（W-R1）。
 *  - 寫入失敗（含 Bridge 尚未實作的 502）一律以白話原因顯示在 toast，不假裝成功；寫入成功後查詢由 `invalidateResearch` 重抓。
 */
import { FileText, Play, RotateCcw, Square } from "lucide-react";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { PillTabs, pillPanelId, pillTabId } from "@/components/ui/pill-tabs";
import { useToast } from "@/components/ui/toast";
import { useCancelResearchStage, useResearchCapabilities, useResearchEvidence, useResearchSources, useStartResearchStage } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  DEPTH_OPTIONS,
  LAYER_OPTIONS,
  READONLY_TITLE,
  evidenceGate,
  flowPhaseLabel,
  flowStatusLabel,
  isInitFailed,
  readResearchScope,
  researchEnvironmentBlock,
  researchErrorText,
  researchFailureOf,
} from "@/lib/domain/research";
import { cn } from "@/lib/utils";
import { EvidenceMatrixTable, type EvidenceMatrixView } from "./EvidenceMatrixTable";
import { EvidenceTimeline } from "./EvidenceTimeline";
import type { ResearchPanelProps } from "./ResearchWorkspaceView";

type TopicTab = "feed" | EvidenceMatrixView;

const TABS = [
  { id: "feed", label: "動態欄" },
  { id: "table", label: "證據矩陣表" },
  { id: "proscons", label: "技術優缺點矩陣" },
] as const;

/** 已完成步驟的唯讀檢視（工作區頂端另有「已完成，唯讀」橫幅）。 */
const COMPLETED_TITLE = "這一步已完成，唯讀";

function Bullets({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-medium text-wg-muted">{label}</dt>
      <dd className="text-sm">
        {items.length === 0 ? (
          "—"
        ) : (
          <ul className="list-disc pl-4">
            {items.map((item, i) => (
              <li key={`${i}-${item}`} className="break-words">
                {item}
              </li>
            ))}
          </ul>
        )}
      </dd>
    </div>
  );
}

export function TopicPanel({ researchId, project, completed }: ResearchPanelProps) {
  const router = useRouter();
  const toast = useToast();
  const { canWrite } = useAuth();
  const idBase = useId();
  const capabilities = useResearchCapabilities();
  const evidence = useResearchEvidence(researchId);
  const sources = useResearchSources(researchId);
  const start = useStartResearchStage();
  const cancel = useCancelResearchStage();
  const [tab, setTab] = useState<TopicTab>("feed");

  const scope = readResearchScope(project.scope);
  const webLayerEnabled = capabilities.data?.webLayerEnabled === true;
  const running = project.flowStatus === "RUNNING";
  const blocked = project.flowStatus === "BLOCKED";
  const initFailed = isInitFailed(project);
  const failure = researchFailureOf(project);
  const researched = project.flowPhase === "EVIDENCE_READY" && project.flowStatus === "IDLE";
  const busy = start.isPending || cancel.isPending;
  // 轉圈只出現在被按的那一顆（啟動與草擬共用同一個寫入 hook）
  const starting = start.isPending ? start.variables?.stage : undefined;

  // 角色與步驟的停用說明（title）：VIEWER 優先，其次已完成步驟的唯讀檢視
  const roleTitle = !canWrite ? READONLY_TITLE : completed ? COMPLETED_TITLE : undefined;
  // 環境與狀態的停用說明（寫在按鈕旁）：探針、容器模式、初始化失敗、資料庫阻塞
  const environment = researchEnvironmentBlock(capabilities.data, capabilities.isError);
  const stateBlock = initFailed ? "工作區尚未初始化完成，請先在上方重試初始化" : blocked ? "資料庫暫時阻塞，恢復後會自動繼續，暫時不能啟動研究" : null;
  // 專案自己的狀態（初始化失敗、資料庫阻塞）比全域環境更具體，先說
  const launchBlock = stateBlock ?? environment;
  const launchDisabled = roleTitle !== undefined || launchBlock !== null || busy;

  const gate = evidence.data !== undefined && sources.data !== undefined ? evidenceGate(evidence.data.items, sources.data) : null;
  const draftBlock = researched ? (gate === null ? "正在載入證據矩陣…" : gate.ok ? null : gate.text) : failure !== null ? "研究尚未完成：請先續跑或重試" : "研究尚未完成：請先啟動深研並等它完成";
  const draftDisabled = roleTitle !== undefined || draftBlock !== null || busy;

  async function launch(label: string) {
    try {
      await start.mutateAsync({ id: researchId, stage: "research" });
      toast.success(`${label}：已送出，動態欄會即時更新`);
    } catch (e) {
      toast.error(`${label}失敗：${researchErrorText(e)}`);
    }
  }

  async function stop() {
    try {
      await cancel.mutateAsync(researchId);
      toast.success("已要求停止研究，已入庫的證據會保留");
    } catch (e) {
      toast.error(`停止失敗：${researchErrorText(e)}`);
    }
  }

  async function generateDraft() {
    try {
      await start.mutateAsync({ id: researchId, stage: "draft" });
      toast.success("已開始生成 PRD 初稿");
      router.push(`/research/${encodeURIComponent(researchId)}?step=studio`);
    } catch (e) {
      toast.error(`生成 PRD 初稿失敗：${researchErrorText(e)}`);
    }
  }

  return (
    <div data-testid="topic-panel" className="flex flex-col gap-4">
      {capabilities.isError ? (
        <div role="alert" data-testid="capabilities-error" className="flex flex-wrap items-center gap-3 rounded-md border border-wg-draft-border bg-wg-draft-bg px-4 py-3 text-sm">
          <span className="min-w-0 flex-1 text-wg-accent">無法取得研究環境狀態：{researchErrorText(capabilities.error)}。證據與動態仍取自資料庫，但暫時不能啟動研究。</span>
          <Button size="sm" variant="ghost" onClick={() => void capabilities.refetch()}>
            重新檢查
          </Button>
        </div>
      ) : null}

      {failure !== null ? (
        <div role="alert" data-testid="research-failure" className="flex flex-wrap items-center gap-3 rounded-md border border-wg-draft-border bg-wg-draft-bg px-4 py-3 text-sm">
          <span className="min-w-0 flex-1 font-semibold text-wg-accent">{failure.text}</span>
          <Button
            size="sm"
            iconLeft={RotateCcw}
            disabled={launchDisabled}
            title={roleTitle}
            loading={starting === "research"}
            onClick={() => void launch(failure.action === "resume" ? "續跑" : "重試")}
          >
            {failure.action === "resume" ? "續跑" : "重試"}
          </Button>
        </div>
      ) : null}

      <Card className="flex flex-col gap-4 p-5" data-testid="topic-scope">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h3 className="text-lg font-semibold">研究議題</h3>
          <span data-testid="topic-status" className="text-sm text-wg-muted">
            目前：{flowPhaseLabel(project.flowPhase)}（{flowStatusLabel(project.flowStatus)}）
          </span>
        </div>
        <p data-testid="topic-text" className="text-[15px] leading-[1.7] break-words whitespace-pre-wrap">
          {project.topic}
        </p>
        <dl className="grid gap-4 md:grid-cols-2">
          <Bullets label="納入範圍" items={scope.inScope} />
          <Bullets label="排除範圍" items={scope.outOfScope} />
          <div className="min-w-0">
            <dt className="text-xs font-medium text-wg-muted">目標技術棧</dt>
            <dd className="text-sm break-words">{scope.techStack === "" ? "—" : scope.techStack}</dd>
          </div>
          <div className="min-w-0">
            <dt className="text-xs font-medium text-wg-muted">文獻年限與適用性軸</dt>
            <dd className="text-sm break-words">
              {scope.recencyYears === null ? "—" : `近 ${scope.recencyYears} 年`}
              {scope.applicabilityAxes.length === 0 ? "" : ` · ${scope.applicabilityAxes.join("、")}`}
            </dd>
          </div>
        </dl>
        <div className="grid gap-4 md:grid-cols-2">
          <div role="radiogroup" aria-label="檢索深度" className="flex flex-wrap gap-2">
            {DEPTH_OPTIONS.map((option) => (
              <label
                key={option.id}
                className={cn("flex flex-col rounded-md border px-3 py-2 text-sm", project.depthLevel === option.id ? "border-wg-primary bg-wg-base" : "border-wg-line text-wg-muted")}
              >
                <span className="flex items-center gap-2 font-medium">
                  <input type="radio" name={`depth-${idBase}`} value={option.id} checked={project.depthLevel === option.id} disabled readOnly />
                  {option.label}
                </span>
                <span className="text-xs text-wg-muted">{option.hint}</span>
              </label>
            ))}
          </div>
          <div role="group" aria-label="來源層" className="flex flex-col gap-2">
            {LAYER_OPTIONS.map((layer) => {
              const noteId = `${idBase}-${layer.id}-note`;
              const industryOff = layer.id === "industry" && !webLayerEnabled;
              return (
                <label key={layer.id} className={cn("flex items-center gap-2 text-sm", industryOff && "text-wg-muted")}>
                  <Checkbox checked={scope.layers[layer.id]} disabled aria-describedby={industryOff ? noteId : undefined} />
                  {layer.label}
                  {industryOff ? (
                    <span id={noteId} data-testid="web-layer-note" className="text-xs text-wg-warning-text">
                      Web 層未啟用（目前沒有任何網域在允許清單內），這一層暫時不會被研究；ADMIN 可在研發工作流清單頁的「研究來源設定」加入網域。
                    </span>
                  ) : null}
                </label>
              );
            })}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t border-wg-line pt-4">
          {running ? (
            <Button variant="accent" iconLeft={Square} disabled={roleTitle !== undefined || busy} title={roleTitle} loading={cancel.isPending} onClick={() => void stop()}>
              停止研究
            </Button>
          ) : failure !== null ? null : (
            <Button
              variant={researched ? "ghost" : "solid"}
              iconLeft={researched ? RotateCcw : Play}
              disabled={launchDisabled}
              title={roleTitle}
              loading={starting === "research"}
              onClick={() => void launch(researched ? "再次深研" : "啟動深研")}
            >
              {researched ? "再次深研" : "啟動深研"}
            </Button>
          )}
          {running ? <span className="text-sm text-wg-muted">研究進行中，動態欄會即時更新。</span> : null}
          {!running && launchBlock !== null && roleTitle === undefined ? (
            <span role="note" data-testid="launch-hint" className="text-sm text-wg-muted">
              {launchBlock}
            </span>
          ) : null}
        </div>
      </Card>

      <Card className="flex flex-col gap-3 p-5">
        <PillTabs label="研究證據視圖" idBase={idBase} tabs={TABS} value={tab} onChange={(next) => setTab(next)} />
        <div role="tabpanel" id={pillPanelId(idBase, "feed")} aria-labelledby={pillTabId(idBase, "feed")} hidden={tab !== "feed"}>
          <EvidenceTimeline key={researchId} researchId={researchId} />
        </div>
        <div hidden={tab === "feed"}>
          <EvidenceMatrixTable
            researchId={researchId}
            view={tab === "proscons" ? "proscons" : "table"}
            onViewChange={(next) => setTab(next)}
            tabPanels={{
              table: { id: pillPanelId(idBase, "table"), labelledBy: pillTabId(idBase, "table") },
              proscons: { id: pillPanelId(idBase, "proscons"), labelledBy: pillTabId(idBase, "proscons") },
            }}
          />
        </div>
      </Card>

      <Card className="flex flex-wrap items-center gap-3 p-5" data-testid="topic-draft">
        <Button iconLeft={FileText} disabled={draftDisabled} title={roleTitle} loading={starting === "draft"} onClick={() => void generateDraft()}>
          生成 PRD 初稿
        </Button>
        <span role="note" data-testid="draft-hint" className="min-w-0 flex-1 text-sm text-wg-muted">
          {roleTitle !== undefined ? "" : (draftBlock ?? (gate === null ? "" : gate.text))}
        </span>
      </Card>
    </div>
  );
}
