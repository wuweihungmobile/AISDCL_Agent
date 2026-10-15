"use client";

import { History } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";
import { describeError } from "@/lib/api/client";
import type { Checkpoint } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * 「從斷點恢復」的斷點選擇對話框（契約 §4.2 E-08、§4.6 G-E2：設計稿沒有，補上；PRD US-E-11）。
 * 列出 GET checkpoints（舊→新，這裡改成新→舊）：名稱、建立時間、已完成步驟數、還原後從哪一步繼續；選一筆 → POST restore。
 * restore 沿用該批次建立時的 playbook：還原後之前修改的任務內容不會生效（契約 §1.2.10）。
 */
export function CheckpointDialog({
  open,
  onClose,
  checkpoints,
  loading,
  error,
  onRetry,
  onRestore,
}: {
  open: boolean;
  onClose: () => void;
  checkpoints: readonly Checkpoint[] | undefined;
  loading: boolean;
  error: unknown;
  onRetry: () => void;
  onRestore: (checkpoint: Checkpoint) => Promise<void>;
}) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      {open ? (
        <DialogContent title="從斷點恢復" description="選擇一個歷史斷點，批次會從該點之後重新執行">
          <CheckpointBody checkpoints={checkpoints} loading={loading} error={error} onRetry={onRetry} onClose={onClose} onRestore={onRestore} />
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

function CheckpointBody({
  checkpoints,
  loading,
  error,
  onRetry,
  onClose,
  onRestore,
}: {
  checkpoints: readonly Checkpoint[] | undefined;
  loading: boolean;
  error: unknown;
  onRetry: () => void;
  onClose: () => void;
  onRestore: (checkpoint: Checkpoint) => Promise<void>;
}) {
  const [pickedId, setPickedId] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const list = [...(checkpoints ?? [])].reverse(); // 新→舊
  const picked = list.find((c) => c.id === pickedId);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!picked) return;
    setPending(true);
    setFailure(null);
    try {
      await onRestore(picked);
      onClose();
    } catch (err) {
      setFailure(describeError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate data-testid="checkpoint-dialog">
      <DialogBody>
        {error ? (
          <ErrorState error={error} onRetry={onRetry} title="無法載入斷點" />
        ) : loading && !checkpoints ? (
          <Skeleton className="h-24" />
        ) : list.length === 0 ? (
          <p className="text-sm text-wg-muted" data-testid="checkpoint-empty">
            這個批次還沒有可用的斷點（每完成一個步驟，引擎會自動記錄一個）。
          </p>
        ) : (
          <div role="radiogroup" aria-label="斷點列表" className="flex max-h-[320px] flex-col gap-2 overflow-y-auto">
            {list.map((c) => {
              const selected = c.id === pickedId;
              return (
                <label
                  key={c.id}
                  data-testid="checkpoint-option"
                  className={cn(
                    "flex cursor-pointer items-start gap-3 rounded-md border px-3.5 py-3 transition-colors",
                    selected ? "border-wg-primary bg-wg-tertiary" : "border-wg-line hover:border-wg-primary",
                  )}
                >
                  <input
                    type="radio"
                    name="checkpoint"
                    value={c.id}
                    checked={selected}
                    onChange={() => setPickedId(c.id)}
                    className="mt-1 size-4 accent-[var(--color-primary)]"
                    aria-label={`斷點 ${c.name}`}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block font-mono text-sm font-semibold">{c.name}</span>
                    <span className="block text-[13px] text-wg-muted">
                      {formatDateTime(c.createdAt)} · 已完成 {c.completedSteps ?? "?"} 步 · {c.stepId ? `還原後從 ${c.stepId} 繼續` : "已跑完所有步驟，還原後重新確認收尾"}
                      {c.isAutomatic ? " · 自動" : ""}
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        )}
        <p className="text-[13px] text-wg-muted">還原沿用這個批次建立時的 playbook：還原後之前修改的任務內容不會生效；要用新內容請另開批次。</p>
        {failure ? (
          <p role="alert" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
            {failure}
          </p>
        ) : null}
      </DialogBody>
      <DialogFooter>
        <Button variant="ghost" onClick={onClose} disabled={pending}>
          取消
        </Button>
        <Button type="submit" iconLeft={History} disabled={!picked} loading={pending} data-testid="checkpoint-confirm">
          從此斷點恢復
        </Button>
      </DialogFooter>
    </form>
  );
}
