"use client";

import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { describeError } from "@/lib/api/client";

/**
 * 確認對話框（刪除等破壞性動作）。onConfirm 丟錯時把訊息（含 traceId）顯示在對話框內、不關閉，
 * 例如後端 409「EXECUTING 專案不可刪除」。
 */
export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel = "確認",
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  confirmLabel?: string;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      {open ? (
        <DialogContent title={title} description={title}>
          <ConfirmBody confirmLabel={confirmLabel} onConfirm={onConfirm} onClose={onClose}>
            {children}
          </ConfirmBody>
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

function ConfirmBody({
  children,
  confirmLabel,
  onConfirm,
  onClose,
}: {
  children: ReactNode;
  confirmLabel: string;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setPending(true);
    setError(null);
    try {
      await onConfirm();
    } catch (e) {
      setError(describeError(e));
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <DialogBody>
        <div className="text-[15px] leading-[1.7]">{children}</div>
        {error ? (
          <p role="alert" className="rounded-md border border-wg-draft-border bg-wg-draft-bg px-3 py-2 text-sm text-wg-accent">
            {error}
          </p>
        ) : null}
      </DialogBody>
      <DialogFooter>
        <Button variant="ghost" onClick={onClose} disabled={pending}>
          取消
        </Button>
        <Button variant="accent" onClick={run} loading={pending}>
          {confirmLabel}
        </Button>
      </DialogFooter>
    </>
  );
}
