"use client";

import { AlertTriangle, Check, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { CountBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";
import { useToast } from "@/components/ui/toast";
import { describeError } from "@/lib/api/client";
import { useAcknowledgeAlert, useProjectAlerts } from "@/lib/api/queries";
import type { Alert } from "@/lib/api/types";
import { ALERT_RULE_LABEL, alertSeverity } from "@/lib/domain/status";
import { formatClock, formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

function AlertRow({ alert, canWrite, onAck, pending }: { alert: Alert; canWrite: boolean; onAck: (a: Alert) => void; pending: boolean }) {
  const [open, setOpen] = useState(false);
  const sev = alertSeverity(alert.severity);
  return (
    <div className="rounded-md border border-wg-alert-border bg-wg-alert-bg px-3.5 py-2.5" data-testid="alert-row" data-ack={alert.acknowledged} data-severity={alert.severity}>
      <div className="flex items-center gap-3 max-md:flex-wrap">
        <AlertTriangle size={18} className={cn("shrink-0", alert.severity === "CRITICAL" ? "text-wg-error" : "text-wg-warning")} aria-hidden />
        <span className="shrink-0 font-mono text-xs text-wg-muted">{formatClock(alert.createdAt)}</span>
        <span className="min-w-0 flex-1 text-sm">
          <span className="font-semibold" style={{ color: sev.color }}>
            [{ALERT_RULE_LABEL[alert.rule] ?? alert.rule}]
          </span>{" "}
          {alert.message}
        </span>
        <Button variant="ghost" size="sm" iconLeft={open ? ChevronUp : ChevronDown} onClick={() => setOpen((v) => !v)} aria-expanded={open} data-testid="alert-detail-toggle">
          詳情
        </Button>
        {alert.acknowledged ? (
          <span className="inline-flex shrink-0 items-center gap-1 text-sm text-wg-muted" data-testid="alert-acked">
            <Check size={14} aria-hidden />
            已確認
          </span>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            disabled={!canWrite || pending}
            title={canWrite ? undefined : "權限不足（唯讀角色不可確認）"}
            onClick={() => onAck(alert)}
            data-testid="alert-ack"
          >
            確認
          </Button>
        )}
      </div>
      {open ? (
        <dl className="mt-2 grid grid-cols-[88px_1fr] gap-x-3 gap-y-1 border-t border-wg-alert-border pt-2 text-[13px]" data-testid="alert-detail">
          <dt className="text-wg-muted">規則</dt>
          <dd>{ALERT_RULE_LABEL[alert.rule] ?? alert.rule}（{sev.label}）</dd>
          <dt className="text-wg-muted">對象</dt>
          <dd className="font-mono break-all">{alert.subject ?? "—"}</dd>
          <dt className="text-wg-muted">批次</dt>
          <dd className="font-mono break-all">{alert.runId ?? "—"}</dd>
          <dt className="text-wg-muted">發生時間</dt>
          <dd>{formatDateTime(alert.createdAt)}</dd>
          {alert.acknowledged ? (
            <>
              <dt className="text-wg-muted">確認</dt>
              <dd>
                {alert.acknowledgedBy ?? "—"}（{formatDateTime(alert.acknowledgedAt)}）
              </dd>
            </>
          ) : null}
        </dl>
      ) : null}
    </div>
  );
}

/**
 * 「告警」卡（設計稿畫面 8；契約 §1.3.4、§1.3.5、§4.3 M-14、M-15；PRD US-M-05）：
 * 每列＝alert-triangle＋時間＋規則與訊息＋「確認」ghost 或「已確認」（#fef7ea 底、#f5e2bd 邊，用 token）；「詳情」展開規則／對象／批次。
 * 確認走樂觀更新（畫面立刻變「已確認」，失敗還原並 toast）；契約冪等，已確認者再確認仍 204。
 */
export function AlertsCard({
  projectId,
  runId,
  pollMs,
  canWrite,
}: {
  projectId: string;
  runId: string | undefined;
  pollMs: number | false;
  canWrite: boolean;
}) {
  const toast = useToast();
  const q = useProjectAlerts(projectId, { runId, limit: 50 }, pollMs);
  const ack = useAcknowledgeAlert();
  const alerts = q.data ?? [];
  const open = alerts.filter((a) => !a.acknowledged).length;

  function onAck(a: Alert) {
    ack.mutate(a.id, {
      onSuccess: () => toast.success("已確認告警"),
      onError: (err) => toast.error(`確認告警失敗：${describeError(err)}`),
    });
  }

  return (
    <Card className="px-[22px] py-5" data-testid="alerts-card">
      <div className="mb-3.5 flex items-center gap-2.5">
        <CardTitle>告警</CardTitle>
        {open > 0 ? <CountBadge count={open} data-testid="alerts-open-count" /> : null}
      </div>
      {q.isError && !q.data ? (
        <ErrorState error={q.error} onRetry={() => q.refetch()} title="無法載入告警" />
      ) : q.isPending ? (
        <Skeleton className="h-16" />
      ) : alerts.length === 0 ? (
        <p className="py-4 text-center text-sm text-wg-muted" data-testid="alerts-empty">
          目前沒有告警
        </p>
      ) : (
        <div className="flex flex-col gap-2.5">
          {alerts.map((a) => (
            <AlertRow key={a.id} alert={a} canWrite={canWrite} onAck={onAck} pending={ack.isPending && ack.variables === a.id} />
          ))}
        </div>
      )}
    </Card>
  );
}
