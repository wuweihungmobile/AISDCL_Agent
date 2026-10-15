"use client";

/**
 * 步驟 2 卡「結構預覽與編輯」（設計稿畫面 6；US-I-03／04／09／10）：
 * 三層樹預覽（可展開、可編輯、可拖曳排序）→ 儲存編輯（PUT /import/{id}/result，整樹覆寫）→
 * signoff 警示橫幅與審批（已簽核顯示綠勾）→ 底部「放棄」與「確認匯入」（未 signoff 時禁用）。
 *
 * 要點（為什麼這樣做）：
 *  - 編輯會撤銷既有 signoff（契約 §1.1.4），所以有未儲存編輯時，signoff 與確認匯入一律停用——
 *    否則使用者簽核或確認的是伺服器上的舊版本，而不是畫面上看到的版本。
 *  - 有界閘 422（含 400 欄位錯誤）把 errors[] 完整列出、不截斷，指到的節點標紅，使用者改完可直接重試儲存。
 */
import { Check, CircleCheckBig, RotateCcw, Save, ShieldAlert, TriangleAlert } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useMemo, useReducer, useState } from "react";

import { ConfirmDialog } from "@/components/domain/ConfirmDialog";
import { SignoffDialog, type SignoffTarget } from "@/components/domain/SignoffDialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusLabel } from "@/components/ui/status-dot";
import { useToast } from "@/components/ui/toast";
import { describeError } from "@/lib/api/client";
import { useConfirmImport, useEditImportResult, useRejectImport } from "@/lib/api/queries";
import type { ImportRecordDetail, ParsedResult, ParsePath, ParseWarning } from "@/lib/api/types";
import { importStatus, isLive } from "@/lib/domain/status";
import { formatDateTime, formatNumber } from "@/lib/format";
import { highlightsFromRows, parseFailureFromError, type ParseFailure } from "./gateErrors";
import { NodeEditDialog, type NodeTarget } from "./NodeEditDialog";
import { ParseFailurePanel, ParseWarnings, StepHeader } from "./parts";
import {
  countTasks,
  isTreeDirty,
  randomId,
  toParsedResult,
  toTree,
  treeReducer,
  treeSignature,
  uniqueGoalKey,
  type TreeAction,
} from "./tree";
import { TreeEditor } from "./TreeEditor";

const PATH_LABEL: Record<ParsePath, string> = {
  SDD: "規格驅動（SDD）",
  LLM: "AI 解析（LLM）",
  DECOMPOSE: "高階目標拆解",
};

export function StructureCard({
  record,
  canWrite,
  warnings,
  onWarnings,
  onDiscarded,
}: {
  /** status 為 PARSED／REVIEWING 且 parsedResult 非 null 的匯入記錄 */
  record: ImportRecordDetail;
  canWrite: boolean;
  /** 最近一次 parse／儲存編輯回傳的解析提示 */
  warnings: readonly ParseWarning[];
  onWarnings: (warnings: ParseWarning[]) => void;
  /** 放棄成功後（記錄已轉 REJECTED）：由頁面清掉目前記錄 */
  onDiscarded: () => void;
}) {
  const router = useRouter();
  const toast = useToast();
  const parsed = record.parsedResult as ParsedResult;
  const [tree, dispatch] = useReducer(treeReducer, parsed, toTree);
  /** 樹被改動的次數：用來判斷「錯誤清單指到的節點索引」是否還有效（改過順序之後索引就不準了） */
  const [edits, setEdits] = useState(0);
  const act = useCallback((action: TreeAction) => {
    dispatch(action);
    setEdits((n) => n + 1);
  }, []);
  const baseline = useMemo(() => treeSignature(toTree(parsed)), [parsed]);
  const dirty = isTreeDirty(tree, baseline);

  const [failure, setFailure] = useState<{ value: ParseFailure; atEdit: number } | null>(null);
  const [node, setNode] = useState<NodeTarget | null>(null);
  const [signoff, setSignoff] = useState<SignoffTarget | null>(null);
  const [confirmReject, setConfirmReject] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const edit = useEditImportResult();
  const confirm = useConfirmImport();
  const reject = useRejectImport();

  const writeHint = canWrite ? undefined : "權限不足（唯讀角色）";
  const highlights = failure && failure.atEdit === edits ? highlightsFromRows(failure.value.rows) : null;
  const canConfirm = record.signedOff && !dirty && canWrite;
  const confirmHint = !canWrite
    ? writeHint
    : dirty
      ? "有未儲存的編輯，請先儲存編輯"
      : !record.signedOff
        ? "須先 signoff 才能確認匯入"
        : undefined;

  async function save() {
    setActionError(null);
    const wasSignedOff = record.signedOff;
    try {
      const result = await edit.mutateAsync({ id: record.id, parsedResult: toParsedResult(tree) });
      dispatch({ type: "load", tree: toTree(result.parsedResult) });
      setFailure(null);
      onWarnings(result.warnings ?? []);
      toast.success(wasSignedOff ? "已儲存編輯；先前的 signoff 已撤銷，請重新審批" : "已儲存編輯");
    } catch (e) {
      setFailure({ value: parseFailureFromError(e), atEdit: edits });
    }
  }

  function revert() {
    dispatch({ type: "load", tree: toTree(parsed) });
    setEdits((n) => n + 1);
    setFailure(null);
  }

  async function confirmImport() {
    setActionError(null);
    try {
      const project = await confirm.mutateAsync(record.id);
      toast.success(`已匯入專案：${project.name}`);
      router.push(`/projects/${project.id}`);
    } catch (e) {
      setActionError(describeError(e));
    }
  }

  const goalCount = tree.goals.length;

  return (
    <Card className="mb-6 p-6" data-testid="import-step2">
      <StepHeader
        step={2}
        title="結構預覽與編輯"
        right={
          <>
            {record.parsePath ? (
              <span data-testid="parse-path" className="rounded-sm bg-wg-tertiary px-2 py-0.5 text-xs">
                {PATH_LABEL[record.parsePath]}
              </span>
            ) : null}
            {record.aiModel ? <span className="text-xs text-wg-muted">{record.aiModel}</span> : null}
            {record.tokenUsed != null ? (
              <span className="font-mono text-xs text-wg-muted">{formatNumber(record.tokenUsed)} tokens</span>
            ) : null}
            <span data-testid="import-status">
              <StatusLabel meta={importStatus(record.status)} live={isLive(record.status)} className="text-xs" />
            </span>
          </>
        }
      />
      <p className="mb-3 text-sm text-wg-muted" data-testid="tree-summary">
        {`共 ${goalCount} 個目標 · ${countTasks(tree)} 個任務。展開節點看說明與通過標準；改動只存在畫面上，按「儲存編輯」才會寫回（儲存會撤銷既有 signoff）。`}
      </p>

      <ParseWarnings warnings={warnings} />
      {failure ? <ParseFailurePanel failure={failure.value} className="mb-4" /> : null}

      <TreeEditor
        tree={tree}
        canEdit={canWrite}
        highlights={highlights}
        onEditProject={() => setNode({ kind: "project" })}
        onAddGoal={() => setNode({ kind: "goal", mode: "create", key: uniqueGoalKey(tree.goals.map((g) => g.key), randomId) })}
        onEditGoal={(key) => setNode({ kind: "goal", mode: "edit", key })}
        onDeleteGoal={(key) => act({ type: "deleteGoal", key })}
        onAddTask={(goalKey) => setNode({ kind: "task", mode: "create", goalKey, uid: `t-${randomId()}` })}
        onEditTask={(goalKey, uid) => setNode({ kind: "task", mode: "edit", goalKey, uid })}
        onDeleteTask={(goalKey, uid) => act({ type: "deleteTask", goalKey, uid })}
        onMoveGoal={(activeKey, overKey) => act({ type: "moveGoal", activeKey, overKey })}
        onMoveTask={(goalKey, activeUid, overUid) => act({ type: "moveTask", goalKey, activeUid, overUid })}
      />

      {dirty ? (
        <div
          role="status"
          data-testid="dirty-notice"
          className="mt-3 flex flex-wrap items-center gap-3 rounded-md border border-wg-alert-border bg-wg-alert-bg px-4 py-3"
        >
          <TriangleAlert size={18} className="shrink-0 text-wg-warning" aria-hidden />
          <span className="min-w-0 flex-1 text-sm">
            有未儲存的編輯。儲存後{record.signedOff ? "會撤銷目前的 signoff，需重新審批" : "狀態轉為「審核中」"}；儲存前無法 signoff 或確認匯入。
          </span>
          <Button variant="ghost" size="sm" iconLeft={RotateCcw} onClick={revert} disabled={edit.isPending}>
            還原
          </Button>
          <Button size="sm" iconLeft={Save} loading={edit.isPending} disabled={!canWrite} title={writeHint} onClick={save}>
            儲存編輯
          </Button>
        </div>
      ) : null}

      <div className="mt-5">
        {record.signedOff ? (
          <div
            role="status"
            data-testid="import-signed-off"
            className="flex items-center gap-3 rounded-md border border-wg-line bg-wg-tertiary px-[18px] py-3.5"
          >
            <CircleCheckBig size={22} className="shrink-0 text-wg-primary" aria-hidden />
            <div className="min-w-0 flex-1 text-sm">
              <b className="text-wg-primary">已 signoff</b> — 審批者 {record.signedOffBy ?? "—"}（{formatDateTime(record.signedOffAt)}
              ）；可以確認匯入。
            </div>
          </div>
        ) : (
          <div
            role="status"
            data-testid="import-signoff-banner"
            className="flex items-center gap-3 rounded-md border border-wg-draft-border bg-wg-draft-bg px-[18px] py-3.5 max-md:flex-wrap"
          >
            <ShieldAlert size={22} className="shrink-0 text-wg-accent" aria-hidden />
            <div className="min-w-0 flex-1">
              <div className="font-semibold text-wg-accent">AI 草案 — 待人工 signoff 硬閘</div>
              <div className="text-[13px] text-wg-muted">
                此草案 signed_off=false，未經掌舵者審批前禁止確認匯入與執行（後端二次校驗 409）。
              </div>
            </div>
            <Button
              iconLeft={Check}
              disabled={!canWrite || dirty}
              title={!canWrite ? writeHint : dirty ? "有未儲存的編輯，請先儲存編輯" : undefined}
              onClick={() =>
                setSignoff({ kind: "import", id: record.id, name: record.sourceFileName ?? tree.project.name })
              }
            >
              signoff 審批
            </Button>
          </div>
        )}
      </div>

      {actionError ? (
        <p role="alert" className="mt-4 rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
          {actionError}
        </p>
      ) : null}

      <div className="mt-5 flex justify-end gap-2.5">
        <Button variant="ghost" disabled={!canWrite} title={writeHint} onClick={() => setConfirmReject(true)}>
          放棄
        </Button>
        <Button
          iconLeft={Check}
          loading={confirm.isPending}
          disabled={!canConfirm}
          title={confirmHint}
          onClick={confirmImport}
        >
          確認匯入
        </Button>
      </div>

      <NodeEditDialog target={node} tree={tree} dispatch={act} onClose={() => setNode(null)} />
      <SignoffDialog target={signoff} onClose={() => setSignoff(null)} />
      <ConfirmDialog
        open={confirmReject}
        title="放棄這份匯入草案？"
        confirmLabel="放棄"
        onClose={() => setConfirmReject(false)}
        onConfirm={async () => {
          await reject.mutateAsync(record.id);
          setConfirmReject(false);
          toast.success("已放棄匯入");
          onDiscarded();
        }}
      >
        放棄後記錄狀態轉為「已放棄」，不會建立任何專案；之後仍可在歷史記錄看到它。
      </ConfirmDialog>
    </Card>
  );
}
