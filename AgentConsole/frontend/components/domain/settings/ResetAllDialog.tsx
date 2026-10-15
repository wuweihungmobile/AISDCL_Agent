"use client";

/**
 * 「全部重置為預設值」確認對話框（US-S-03；契約 §1.5.6 的分類級 reset）。
 * 對六個分類各呼叫一次 POST /settings/{category}/reset（同分類同交易、token_guard 以重置後最終值校驗）。
 * 加密參數（API Key、DB DSN）預設略過；要連同重置須明確勾選（送 confirm=true）——重置會清空金鑰，不能被「全部」順手帶走。
 * 任一分類失敗就停下並顯示原因（前面已完成的分類不回復，畫面會重抓顯示實際狀態）。
 */
import { RotateCcw } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogBody, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { useResetCategory } from "@/lib/api/queries";
import { CONFIG_CATEGORIES } from "@/lib/api/types";
import { CATEGORY_META } from "./labels";
import { describeSettingsError } from "./settingsErrors";

export function ResetAllDialog({
  open,
  onClose,
  onFinished,
}: {
  open: boolean;
  onClose: () => void;
  /** 結束時呼叫（全部成功 completed＝true；中途失敗 completed＝false）：頁面清草稿並重抓 */
  onFinished: (completed: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      {open ? (
        <DialogContent title="全部重置為預設值" description="把六個分類的全部參數重置為預設值">
          <Body onClose={onClose} onFinished={onFinished} />
        </DialogContent>
      ) : null}
    </Dialog>
  );
}

function Body({ onClose, onFinished }: { onClose: () => void; onFinished: (completed: boolean) => void }) {
  const reset = useResetCategory();
  const [includeSensitive, setIncludeSensitive] = useState(false);
  const [pending, setPending] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setPending(true);
    setError(null);
    for (const [i, category] of CONFIG_CATEGORIES.entries()) {
      const name = CATEGORY_META[category].label;
      setProgress(`${name}（${i + 1}／${CONFIG_CATEGORIES.length}）`);
      try {
        await reset.mutateAsync({ category, confirm: includeSensitive });
      } catch (e) {
        setPending(false);
        setProgress(null);
        setError(`重置「${name}」失敗：${describeSettingsError(e)}。前面的分類已重置。`);
        onFinished(false);
        return;
      }
    }
    setPending(false);
    setProgress(null);
    onFinished(true);
  }

  return (
    <>
      <DialogBody>
        <p className="text-[15px] leading-[1.7]">
          這會把<b>模型、Agent、執行、監控、AutoClaude、SDD</b>六個分類的全部參數重置為預設值，並各寫一筆修改歷史。
        </p>
        <label className="flex cursor-pointer items-start gap-2.5 text-sm">
          <Checkbox checked={includeSensitive} onCheckedChange={(v) => setIncludeSensitive(v === true)} disabled={pending} className="mt-0.5" />
          <span>
            同時重置加密參數（API Key、資料庫連線字串）
            <span className="mt-0.5 block text-xs text-wg-muted">未勾選時加密參數維持原值（後端預設略過）；勾選會清空它們。</span>
          </span>
        </label>
        {progress ? (
          <p role="status" className="text-sm text-wg-muted">
            重置中：{progress}
          </p>
        ) : null}
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
        <Button variant="accent" iconLeft={RotateCcw} loading={pending} onClick={run}>
          全部重置
        </Button>
      </DialogFooter>
    </>
  );
}
