"use client";

/**
 * 狀態橫幅（P1b；TCS-SelfImprovingMirror-P1b R12、R13、R16）：資料＝`GET /api/v1/si/status` 的 `items[0]`（欄名為 camelCase）。
 * 自成一個查詢、一個 loading／error／ok 三態：error 時只顯示錯誤（絕不渲染成「無事件」），ok 時橫幅**每個**頂層鍵都至少有一個可見呈現——
 * 已知九個鍵各有固定位置，其餘鍵（例：日後根層加的 consolePending）以「鍵：緊湊 JSON」純文字列在 si-status-extra，不丟欄位。
 * 量不到（NOT-EVALUABLE）一律以「量不到」加原因呈現，不顯示成 0、無或通過；帳本字串全部以文字節點渲染。
 * P2b：給了 `onResume`（只有 ADMIN）且 `suspended` 帶運轉號時，暫停狀態旁多一個「恢復運轉」鈕（`si-resume-open`），把該運轉號交給呼叫端開啟決定對話框
 * （恢復綁 `suspended.run`）；沒給＝與 P1b 逐位元組相同的唯讀畫面。
 */
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { useSiStatus } from "@/lib/api/queries";
import type { SiStatusItem } from "@/lib/api/types";
import { SI_STATUS_KNOWN_KEYS, compactJson, describeValue, noEventText, notEvaluableText, suspendedRun } from "@/lib/domain/si";
import { SiError, SiLoading, SiNotes } from "./siParts";

const KNOWN: ReadonlySet<string> = new Set(SI_STATUS_KNOWN_KEYS);

/** 一個狀態欄：`data-status-key` 是它對應的 status 鍵（測試與稽核用：每個鍵都有可見呈現）。 */
function Field({ statusKey, title, children }: { statusKey: string; title: string; children: ReactNode }) {
  return (
    <div data-status-key={statusKey} className="min-w-0">
      <dt className="text-xs font-medium text-wg-muted">{title}</dt>
      <dd className="mt-0.5 text-sm break-words">{children}</dd>
    </div>
  );
}

const EMPTY = "無";
/** 已知欄位缺席或型別不符（根層 schema 變動時才會發生）：照量不到呈現，不假裝是「無」或空清單——否則缺了 eventsDetected 會顯示成「無事件」。 */
const MISSING = notEvaluableText("欄位缺席或型別不符");

function listOf<T>(value: unknown): T[] | null {
  return Array.isArray(value) ? (value as T[]) : null;
}

/** 值缺席（undefined）＝量不到；null 是合法的「沒有」（例：suspended），交給 describeValue。 */
function valueText(value: unknown): string {
  return value === undefined ? MISSING : describeValue(value);
}

function BulletList({ testId, lines }: { testId: string; lines: string[] | null }) {
  if (lines === null) return <span data-testid={testId}>{MISSING}</span>;
  if (lines.length === 0) return <span data-testid={testId}>{EMPTY}</span>;
  return (
    <ul data-testid={testId} className="list-disc pl-5">
      {lines.map((line, i) => (
        <li key={`${i}-${line}`}>{line}</li>
      ))}
    </ul>
  );
}

/** `openRuns` 的一項：物件取 `run` 為主、其餘鍵附在括號內（鍵：值）；非物件原樣轉文字。 */
function openRunLine(entry: unknown): string {
  if (typeof entry !== "object" || entry === null || Array.isArray(entry)) return describeValue(entry);
  const { run, ...rest } = entry as Record<string, unknown>;
  const detail = Object.entries(rest)
    .map(([k, v]) => `${k}：${describeValue(v)}`)
    .join("；");
  return `${typeof run === "string" ? run : describeValue(run)}${detail ? `（${detail}）` : ""}`;
}

function StatusItem({ item, onResume }: { item: SiStatusItem; onResume?: (run: string) => void }) {
  const resumable = onResume ? suspendedRun(item.suspended) : null;
  const detected = listOf<SiStatusItem["eventsDetected"][number]>(item.eventsDetected);
  const unavailable = listOf<SiStatusItem["unavailable"][number]>(item.unavailable);
  const openRuns = listOf<unknown>(item.openRuns);
  const pending = listOf<SiStatusItem["pendingProps"][number]>(item.pendingProps);
  const cooldowns = listOf<unknown>(item.cooldowns);
  const skip = typeof item.skipReasons === "object" && item.skipReasons !== null && !Array.isArray(item.skipReasons) ? Object.entries(item.skipReasons) : null;
  const extras = Object.entries(item).filter(([key]) => !KNOWN.has(key));

  return (
    <dl className="mt-3 grid grid-cols-1 gap-x-6 gap-y-3 md:grid-cols-2 xl:grid-cols-3">
      <Field statusKey="eventsDetected" title="事件偵測">
        {detected === null ? (
          <span data-testid="si-events-detected">{MISSING}</span>
        ) : detected.length > 0 ? (
          <ul data-testid="si-events-detected" className="list-disc pl-5">
            {detected.map((e, i) => (
              <li key={`${i}-${e.trigger}`}>{`${e.trigger}｜${e.subject}｜${e.detail}`}</li>
            ))}
          </ul>
        ) : (
          <span data-testid="si-no-event">{unavailable === null ? "無事件（unavailable 欄位缺席或型別不符，量不到的項數不明）" : noEventText(unavailable.length)}</span>
        )}
      </Field>
      <Field statusKey="unavailable" title="量不到的觸發器">
        <BulletList testId="si-unavailable" lines={unavailable && unavailable.map((u) => `觸發 ${u.trigger}：${notEvaluableText(u.reason)}`)} />
      </Field>
      <Field statusKey="openRuns" title="進行中的運轉">
        <BulletList testId="si-open-runs" lines={openRuns && openRuns.map(openRunLine)} />
      </Field>
      <Field statusKey="pendingProps" title="待決提案">
        <BulletList testId="si-pending-props" lines={pending && pending.map((p) => `${p.id}｜rev ${p.rev}｜${p.state}｜${p.route}｜${p.digest8}`)} />
      </Field>
      <Field statusKey="suspended" title="暫停狀態">
        <span data-testid="si-suspended">{valueText(item.suspended)}</span>
        {onResume && resumable ? (
          <Button variant="ghost" size="sm" className="ml-2" aria-label={`恢復運轉 ${resumable}`} data-testid="si-resume-open" onClick={() => onResume(resumable)}>
            恢復運轉
          </Button>
        ) : null}
      </Field>
      <Field statusKey="cooldowns" title="冷卻中">
        <BulletList testId="si-cooldowns" lines={cooldowns && cooldowns.map(describeValue)} />
      </Field>
      <Field statusKey="skipReasons" title="略過原因（次數）">
        <BulletList testId="si-skip-reasons" lines={skip && skip.map(([k, v]) => `${k}：${describeValue(v)}`)} />
      </Field>
      <Field statusKey="capacity" title="容量">
        <span data-testid="si-capacity">{valueText(item.capacity)}</span>
      </Field>
      <Field statusKey="frictionReconcile" title="摩擦對帳">
        <span data-testid="si-friction">{valueText(item.frictionReconcile)}</span>
      </Field>
      {extras.length > 0 ? (
        <div className="min-w-0 md:col-span-2 xl:col-span-3">
          <dt className="text-xs font-medium text-wg-muted">其他欄位（原樣列出，不丟欄位）</dt>
          <dd className="mt-0.5 text-sm break-words">
            <ul data-testid="si-status-extra" className="list-disc pl-5">
              {extras.map(([key, value]) => (
                <li key={key} data-status-key={key}>{`${key}：${compactJson(value)}`}</li>
              ))}
            </ul>
          </dd>
        </div>
      ) : null}
    </dl>
  );
}

export function SiStatusBanner({ onResume }: { onResume?: (run: string) => void } = {}) {
  const q = useSiStatus();
  const shell = "mb-5 rounded-lg border border-wg-line bg-wg-surface px-5 py-4";
  if (q.isError) {
    return (
      <section data-testid="si-status-banner" aria-label="自我進化狀態" className={shell}>
        <SiError error={q.error} onRetry={() => void q.refetch()} />
      </section>
    );
  }
  if (q.isPending) {
    return (
      <section data-testid="si-status-banner" aria-label="自我進化狀態" className={shell}>
        <SiLoading what="狀態" />
      </section>
    );
  }
  const page = q.data;
  const item = page.items[0];
  return (
    <section data-testid="si-status-banner" aria-label="自我進化狀態" className={shell}>
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1 text-sm">
        <span>
          <span className="text-wg-muted">{"head："}</span>
          <code data-testid="si-head-sha" title={page.headSha ?? undefined} className="font-mono">
            {page.headSha ? page.headSha.slice(0, 8) : notEvaluableText()}
          </code>
        </span>
        <span>
          <span className="text-wg-muted">{"產生時間："}</span>
          <time data-testid="si-generated-at">{page.generatedAt}</time>
        </span>
      </div>
      <SiNotes ne={page.ne} problems={page.problems} />
      {item ? <StatusItem item={item} onResume={onResume} /> : <p className="mt-3 text-sm text-wg-accent">{notEvaluableText("status 回應沒有任何項目")}</p>}
    </section>
  );
}
