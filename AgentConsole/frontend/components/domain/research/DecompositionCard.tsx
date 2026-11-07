"use client";

/**
 * 拆解卡（FR-R2P-14；TCS-ResearchToPRD-P1-20261107 AT-961-18-1、18-2、18-3、18-E-1）：
 *  - 尚無拆解：說明與「觸發拆解」（OPERATOR 以上；同步請求，進行中顯示忙碌狀態；422 結構化錯誤顯示閘別與說明、不顯示草稿）；
 *  - 草稿（`DRAFTED`、`SCG_PASSED`）：拆解樹、任務數、覆蓋矩陣與未覆蓋清單（{@link CoverageList}）、每個未覆蓋 AC 一句豁免理由（{@link WaiverInput}）、
 *    「簽核」——未覆蓋者清零或各有有效豁免理由前停用並列出原因；簽核者由後端取 JWT subject，前端不送；
 *  - 過期（`stale`）：顯示「PRD 已更新，拆解已過期」與「重新拆解」，不給簽核；已簽核且不過期：唯讀，只顯示簽核者與時間。
 * `lock` 是整張卡的停用說明（唯讀角色、已完成步驟、規格變更中），有值時所有寫入控件停用並以它為 `title`。
 */
import { ListTree, TriangleAlert } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { useSignoffResearchDecomposition, useTriggerResearchDecomposition } from "@/lib/api/queries";
import type { ResearchDecomposition } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { DECOMPOSITION_STATUS_LABEL, coverageView, countTasks, decompositionErrorLines, decompositionTree, formatInstant, type CoverageView, type DecompositionGoalNode } from "@/lib/domain/research";
import { CoverageList } from "./CoverageList";

function TreeView({ tree }: { tree: readonly DecompositionGoalNode[] }) {
  if (tree.length === 0) return <p className="text-sm text-wg-muted">拆解樹是空的。</p>;
  return (
    <ul data-testid="decomposition-tree" className="flex flex-col gap-2 text-sm">
      {tree.map((goal) => (
        <li key={goal.id} data-goal={goal.id}>
          <span className="font-medium">
            <span className="font-mono">{goal.id}</span> {goal.name}
          </span>
          <ul className="ml-5 mt-1 flex list-disc flex-col gap-1">
            {goal.tasks.map((task) => (
              <li key={task.id} data-task={task.id}>
                <span className="font-mono">{task.id}</span> {task.name}
                {task.coversAc.length > 0 ? <span className="text-wg-muted">（涵蓋 {task.coversAc.join("、")}）</span> : null}
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}

/** 草稿與已簽核的內容區（以拆解列 id 當 key：重拆後豁免輸入重新開始，不把舊拆解的輸入帶到新列）。 */
function DecompositionBody({ researchId, decomposition, lock }: { researchId: string; decomposition: ResearchDecomposition; lock: string | null }) {
  const { username } = useAuth();
  const trigger = useTriggerResearchDecomposition();
  const signoff = useSignoffResearchDecomposition();
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [error, setError] = useState<unknown>(null);

  const stale = decomposition.stale || decomposition.status === "STALE";
  const signed = decomposition.status === "SIGNED_OFF" && !stale;
  const view: CoverageView = useMemo(() => coverageView(decomposition, inputs), [decomposition, inputs]);
  const tree = useMemo(() => decompositionTree(decomposition.goals), [decomposition.goals]);
  const treeTasks = countTasks(tree);

  const blockers: string[] = [];
  if (lock !== null) blockers.push(lock);
  if (!view.complete) blockers.push(`仍有 ${view.pending.length} 個未覆蓋的驗收條件沒有有效的豁免理由：${view.pending.join("、")}`);

  async function doSignoff() {
    setError(null);
    try {
      const waivers = view.waived.map((ac) => ({ ac, reason: (inputs[ac] ?? decomposition.waivers.find((w) => w.ac === ac)?.reason ?? "").trim() }));
      await signoff.mutateAsync({ id: researchId, body: { waivers } });
    } catch (e) {
      setError(e);
    }
  }
  async function doRetrigger() {
    setError(null);
    try {
      await trigger.mutateAsync(researchId);
    } catch (e) {
      setError(e);
    }
  }

  return (
    <div data-testid="decomposition-body" data-status={decomposition.status} data-stale={stale || undefined} className="flex flex-col gap-4">
      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-wg-muted">狀態</dt>
        <dd data-testid="decomposition-status">{stale ? "已過期" : (DECOMPOSITION_STATUS_LABEL[decomposition.status] ?? decomposition.status)}</dd>
        <dt className="text-wg-muted">任務數</dt>
        <dd data-testid="decomposition-tasks-count" data-tree-count={treeTasks}>
          {decomposition.tasksCount}
        </dd>
        <dt className="text-wg-muted">PRD 摘要</dt>
        <dd className="font-mono">{decomposition.prdSha256.slice(0, 12)}</dd>
      </dl>

      {stale ? (
        <div role="alert" data-testid="decomposition-stale" className="flex flex-col gap-2 rounded-md border border-wg-draft-border bg-wg-draft-bg px-4 py-3 text-sm">
          <p className="flex items-center gap-2 font-semibold text-wg-accent">
            <TriangleAlert size={16} aria-hidden />
            PRD 已更新，拆解已過期
          </p>
          <p>請重新拆解並再簽核；過期的拆解不能拿去執行。</p>
          <Button className="w-fit" disabled={lock !== null} title={lock ?? undefined} loading={trigger.isPending} onClick={() => void doRetrigger()}>
            重新拆解
          </Button>
        </div>
      ) : null}

      <TreeView tree={tree} />
      <CoverageList
        decomposition={decomposition}
        view={view}
        inputs={inputs}
        onInput={(ac, v) => setInputs((prev) => ({ ...prev, [ac]: v }))}
        editable={!signed && !stale}
        lockTitle={lock ?? undefined}
      />

      {signed ? (
        <p data-testid="decomposition-signed" className="text-sm">
          已簽核（唯讀）：簽核者 {decomposition.signedOffBy ?? "未知"}，時間 {formatInstant(decomposition.signedOffAt)}。
        </p>
      ) : null}

      {!signed && !stale ? (
        <div className="flex flex-col gap-2">
          <p className="text-sm text-wg-muted">簽核者為目前登入的使用者{username === "" ? "" : `（${username}）`}，由後端取登入身分，前端不另送。</p>
          {blockers.length > 0 ? (
            <ul data-testid="signoff-blockers" className="list-disc pl-5 text-sm text-wg-warning-text">
              {blockers.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button disabled={blockers.length > 0} title={blockers.length > 0 ? blockers[0] : undefined} loading={signoff.isPending} onClick={() => void doSignoff()}>
              簽核
            </Button>
            <Button variant="ghost" disabled={lock !== null} title={lock ?? undefined} loading={trigger.isPending} onClick={() => void doRetrigger()}>
              重新拆解
            </Button>
          </div>
        </div>
      ) : null}

      {error !== null ? (
        <div role="alert" data-testid="decomposition-error" className="text-sm text-wg-error">
          {decompositionErrorLines(error).map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function DecompositionCard({ researchId, decomposition, lock }: { researchId: string; decomposition: ResearchDecomposition | null; lock: string | null }) {
  const trigger = useTriggerResearchDecomposition();
  const [error, setError] = useState<unknown>(null);

  async function doTrigger() {
    setError(null);
    try {
      await trigger.mutateAsync(researchId);
    } catch (e) {
      setError(e);
    }
  }

  return (
    <section data-testid="decomposition-card" aria-label="任務拆解" className="flex flex-col gap-3 rounded-md border border-wg-line p-4">
      <h4 className="flex items-center gap-2 text-base font-semibold">
        <ListTree size={18} aria-hidden className="text-wg-muted" />
        任務拆解
      </h4>
      {decomposition === null ? (
        <>
          <p data-testid="decomposition-empty" className="text-sm">
            尚未拆解。規格凍結並分流後，系統會依凍結 PRD 的驗收條件逐項拆成任務，並確認每個條件都有任務涵蓋。
          </p>
          {trigger.isPending ? (
            <p role="status" data-testid="decomposition-busy" className="text-sm text-wg-muted">
              拆解進行中，這是同步請求，大型 PRD 可能需要數分鐘，請不要重複按。
            </p>
          ) : null}
          <Button className="w-fit" disabled={lock !== null} title={lock ?? undefined} loading={trigger.isPending} onClick={() => void doTrigger()}>
            觸發拆解
          </Button>
          {error !== null ? (
            <div role="alert" data-testid="decomposition-error" className="text-sm text-wg-error">
              {decompositionErrorLines(error).map((line) => (
                <p key={line}>{line}</p>
              ))}
            </div>
          ) : null}
        </>
      ) : (
        <DecompositionBody key={decomposition.id} researchId={researchId} decomposition={decomposition} lock={lock} />
      )}
    </section>
  );
}
