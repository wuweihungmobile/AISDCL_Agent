"use client";

/**
 * 提案詳情對話框（TCS-SiFlowVisibility AC-966-6、8、9、10；W-F4、W-F6、W-F9、W-F14）：
 *  - 只有按下列上的「詳情」鈕才取數，恰一個請求 `GET /api/v1/si/proposals/{id}`；時間線與來源觀察皆取自回應的 `detail`（不打議題端點）；
 *    對話框關閉即丟棄（gcTime 0），重開重取。
 *  - 頂端「下一步」一句話：快照可用就用快照、否則用詳情的 `next`、都沒有就「量不到」（來源序在 `resolveNextStep`）。
 *  - 五分頁：卡面／變更內容／提案本文／評估集與驗證／時間線。載入中、404、其他失敗各一態，**錯誤態不渲染任何空的分頁內容**。
 *  - 全部純文字節點；評估集只顯示七個欄位（`heldoutView` 不輸出 `digest8` 與未知鍵），不洩漏評估集內容。
 *  - 只讀：沒有任何寫入、表單或 mutation（AT-966-14-3 靜態鎖）；所有角色看到的內容一視同仁。
 */
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent } from "@/components/ui/dialog";
import { pillPanelId, pillTabId, PillTabs } from "@/components/ui/pill-tabs";
import { ApiError } from "@/lib/api/client";
import { useSiProposalDetail } from "@/lib/api/queries";
import type { SiNeEntry, SiProposal } from "@/lib/api/types";
import { cardNeEntries, formatNe } from "@/lib/domain/si";
import { SI_FLOW_TEXTS as T, fillText, heldoutView, nextStepLine, obsSourceIds, reasonText, resolveNextStep, sandboxView, verifyView } from "@/lib/domain/siFlow";
import { cn } from "@/lib/utils";
import { SiDiffView, type NeWithText } from "./SiDiffView";
import { SiError, SiLoading } from "./siParts";
import { usePatrolView } from "./usePatrolView";

type DetailTab = "card" | "diff" | "body" | "verify" | "timeline";
const TABS: ReadonlyArray<{ id: DetailTab; label: string }> = [
  { id: "card", label: T.tabCard },
  { id: "diff", label: T.tabDiff },
  { id: "body", label: T.tabBody },
  { id: "verify", label: T.tabVerify },
  { id: "timeline", label: T.tabTimeline },
];
const ID_BASE = "si-detail";

type Rec = Record<string, unknown>;
const isRec = (v: unknown): v is Rec => typeof v === "object" && v !== null && !Array.isArray(v);
const asText = (v: unknown): string => (typeof v === "string" && v !== "" ? v : T.unmeasurable);

function Section({ title, children, testId }: { title: string; children: React.ReactNode; testId?: string }) {
  return (
    <section data-testid={testId} className="rounded-md border border-wg-line bg-wg-base px-4 py-3">
      <h3 className="mb-1.5 text-sm font-semibold">{title}</h3>
      {children}
    </section>
  );
}

function NotProvided() {
  return (
    <p data-testid="si-detail-not-provided" className="text-sm text-wg-muted">
      {T.detailNotProvided}
    </p>
  );
}

function BodyTab({ item, detail, ne, onJump }: { item: Rec; detail: Rec; ne: ReadonlyArray<NeWithText>; onJump: (id: string) => void }) {
  const body = detail.body;
  const text = isRec(body) && typeof body.text === "string" ? body.text : null;
  const sourceObs = detail.sourceObs;
  // 只看單筆回應自己帶的 `sources`（不退用清單列的值：兩者皆缺席才是「來源量不到」）
  const sources = item.sources;
  const ledgerNe = ne.find((e) => e.reason === "OBS-LEDGER-UNREADABLE");

  let sourcesNode: React.ReactNode;
  if (Array.isArray(sourceObs) && sourceObs.length > 0) {
    sourcesNode = (
      <ul data-testid="si-source-list" className="flex max-h-64 flex-col gap-2 overflow-y-auto">
        {sourceObs.map((o, i) => {
          const r = isRec(o) ? o : {};
          const id = typeof r.id === "string" ? r.id : "";
          if (r.missing === true) {
            return (
              <li key={`${id}-${i}`} className="text-sm text-wg-warning-text">
                {fillText(T.sourceMissingRow, { id })}
              </li>
            );
          }
          return (
            <li key={`${id}-${i}`} className="rounded-md border border-wg-line bg-wg-surface px-3 py-2 text-sm">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <code className="font-mono text-xs">{id}</code>
                <span>{`${T.srcSeverity}${asText(r.severity)}`}</span>
                <span>{`${T.srcDisposition}${asText(r.disposition)}`}</span>
                {/^OBS-SI-\d{3,}$/.test(id) ? (
                  <Button variant="ghost" size="sm" onClick={() => onJump(id)}>
                    {fillText(T.sourceJump, { id })}
                  </Button>
                ) : null}
              </div>
              <p className="mt-1 break-words whitespace-pre-wrap">{`${T.srcContext}${asText(r.context)}`}</p>
              <p className="break-words whitespace-pre-wrap">{`${T.srcSymptom}${asText(r.symptom)}`}</p>
            </li>
          );
        })}
      </ul>
    );
  } else if (ledgerNe) {
    sourcesNode = <p className="text-sm text-wg-warning-text">{reasonText(ledgerNe.reason, ledgerNe.text)}</p>;
  } else if (Array.isArray(sources) && sources.length > 0) {
    const unique = [...new Set(sources.filter((s): s is string => typeof s === "string"))];
    const jumpable = new Set(obsSourceIds(unique));
    sourcesNode = (
      <ul data-testid="si-source-list" className="flex max-h-48 flex-wrap gap-2 overflow-y-auto">
        {unique.map((s) => (
          <li key={s} className="text-sm">
            {jumpable.has(s) ? (
              <Button variant="ghost" size="sm" onClick={() => onJump(s)}>
                {fillText(T.sourceJump, { id: s })}
              </Button>
            ) : (
              <span className="break-all">{s}</span>
            )}
          </li>
        ))}
      </ul>
    );
  } else if (Array.isArray(sources) || Array.isArray(sourceObs)) {
    sourcesNode = <p className="text-sm text-wg-muted">{T.sourcesNone}</p>;
  } else {
    sourcesNode = <p className="text-sm text-wg-muted">{T.sourcesUnknown}</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      <Section title={T.tabBody} testId="si-body-section">
        {text === null ? (
          <p className="text-sm text-wg-warning-text">{T.bodyMissing}</p>
        ) : text === "" ? (
          <p className="text-sm text-wg-muted">{T.bodyEmpty}</p>
        ) : (
          <>
            {isRec(body) && typeof body.rel === "string" ? <p className="mb-1 font-mono text-xs break-all text-wg-muted">{body.rel}</p> : null}
            <pre data-testid="si-body-text" className="rounded-md border border-wg-line bg-wg-surface p-3 text-sm break-words whitespace-pre-wrap">
              {text}
            </pre>
            {isRec(body) && body.truncated === true ? (
              <p data-testid="si-body-truncated" className="mt-1 text-sm text-wg-warning-text">
                {fillText(T.diffTruncated, { rel: typeof body.rel === "string" ? body.rel : "" })}
              </p>
            ) : null}
          </>
        )}
      </Section>
      <Section title={T.sourcesTitle} testId="si-sources-section">
        {sourcesNode}
      </Section>
    </div>
  );
}

function VerifyTab({ detail, nextHint }: { detail: Rec; nextHint: string | null }) {
  const held = heldoutView(detail.heldout);
  const sandbox = sandboxView(detail.sandbox);
  const verify = verifyView(detail.verify);
  return (
    <div className="flex flex-col gap-3">
      <Section title={T.heldoutTitle} testId="si-heldout-section">
        <p className="text-sm">{held.text}</p>
        {held.state === "unfrozen" ? <p className="mt-1 text-sm text-wg-muted">{held.note}</p> : null}
        {held.state === "frozen" && held.warning !== null ? (
          <div className="mt-1.5 rounded-md border border-wg-alert-border bg-wg-alert-bg px-3 py-2 text-sm text-wg-warning-text">
            <p data-testid="si-heldout-warning">{held.warning}</p>
            <p className="mt-0.5">{T.heldoutBelowMinNote}</p>
          </div>
        ) : null}
      </Section>
      <Section title={T.sandboxTitle} testId="si-sandbox-section">
        {sandbox.state === "none" ? (
          <p className="text-sm text-wg-muted">{sandbox.text}</p>
        ) : (
          <>
            {sandbox.state === "ok" ? <p className="text-sm">{sandbox.text}</p> : null}
            {sandbox.state === "fail" ? (
              <div className="text-sm">
                <p className="text-wg-warning-text">{sandbox.headline}</p>
                {sandbox.detail !== null ? <p className="mt-0.5 break-words whitespace-pre-wrap">{sandbox.detail}</p> : null}
                {sandbox.code !== null ? <code className="font-mono text-xs">{sandbox.code}</code> : null}
              </div>
            ) : null}
            <ul className="mt-1.5 text-sm text-wg-muted">
              {sandbox.flags.map((f) => (
                <li key={f.label}>{`${f.label}：${f.value}`}</li>
              ))}
            </ul>
          </>
        )}
      </Section>
      <Section title={T.verifyTitle} testId="si-verify-section">
        {verify.state === "none" ? (
          <p className="text-sm">
            {verify.text}
            {nextHint === null ? null : `。${nextHint}`}
          </p>
        ) : (
          <div className="flex flex-col gap-1.5 text-sm">
            <p
              data-testid="si-verdict"
              className={cn(
                "w-fit rounded-md border px-2 py-0.5 font-semibold",
                verify.verdict.known ? "border-wg-line" : "border-wg-line italic",
                verify.verdict.text === "通過" ? "border-wg-success" : verify.verdict.text === "未通過" ? "border-wg-error" : "",
              )}
            >
              {fillText(T.verifyResultFmt, { label: verify.verdict.text })}
            </p>
            <ul>
              {verify.steps.map((s) => (
                <li key={s.key} data-step={s.key} className={s.failed ? "text-wg-warning-text" : undefined}>
                  {`${s.label}：${s.value}`}
                  {s.failed ? `（${T.verifyStepFailed}）` : ""}
                </li>
              ))}
            </ul>
            <p>{fillText(T.verifyProbes, { n: verify.probes })}</p>
            <p>{`${T.verifyCarrier}：${verify.carrier}`}</p>
            <div>
              <p className="font-medium">{T.verifyReasonsTitle}</p>
              {verify.reasons.state === "list" ? (
                <ul className="list-disc pl-5">
                  {verify.reasons.items.map((r, i) => (
                    <li key={`${r.code ?? "x"}-${i}`} className="break-words">
                      {r.code === null ? null : <code className="mr-1 font-mono text-xs">{r.code}</code>}
                      {r.text}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-wg-muted">
                  {verify.reasons.state === "none-kept" ? T.verifyReasonsNoneKept : verify.reasons.state === "no-report" ? T.verifyReasonsNoReport : T.verifyReasonsMissing}
                </p>
              )}
            </div>
          </div>
        )}
      </Section>
    </div>
  );
}

function TimelineTab({ detail, ne, propId }: { detail: Rec; ne: ReadonlyArray<NeWithText>; propId: string }) {
  const timeline = detail.timeline;
  if (!Array.isArray(timeline)) return <p className="text-sm text-wg-warning-text">{T.timelineMissing}</p>;
  if (timeline.length === 0) return <p className="text-sm text-wg-muted">{T.timelineEmpty}</p>;
  const rows = timeline.map((e) => (isRec(e) ? e : {}));
  const seqKey = (r: Rec) => (typeof r.seq === "number" && Number.isFinite(r.seq) ? r.seq : Number.POSITIVE_INFINITY);
  // 穩定排序（Array.prototype.sort 自 ES2019 起穩定）：依 seq 升冪，重複 seq 保持輸入相對序
  const sorted = [...rows].sort((a, b) => seqKey(a) - seqKey(b));
  const cut = ne.filter((e) => e.reason === "TIMELINE-TRUNCATED" && (e.field === "" || e.field.includes(propId)));
  return (
    <div className="flex flex-col gap-2">
      {cut.map((e, i) => (
        <p key={i} data-testid="si-timeline-truncated" className="text-sm text-wg-warning-text">
          {reasonText(e.reason, e.text)}
        </p>
      ))}
      <div className="overflow-x-auto">
        <table data-testid="si-timeline-table" className="w-full min-w-[28rem] border-collapse text-left text-sm">
          <caption className="sr-only">{T.timelineCaption}</caption>
          <thead>
            <tr className="border-b border-wg-line text-xs text-wg-muted">
              <th scope="col" className="py-1.5 pr-3">
                {T.colSeq}
              </th>
              <th scope="col" className="py-1.5 pr-3">
                {T.colTime}
              </th>
              <th scope="col" className="py-1.5 pr-3">
                {T.colWho}
              </th>
              <th scope="col" className="py-1.5">
                {T.colAction}
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => (
              <tr key={i} className="border-b border-wg-line align-top">
                <td className="py-1.5 pr-3 font-mono text-xs">{typeof r.seq === "number" ? r.seq : T.unmeasurable}</td>
                <td className="py-1.5 pr-3 break-all">{typeof r.t === "string" && r.t !== "" ? r.t : T.timeMissing}</td>
                <td className="py-1.5 pr-3 break-words">{asText(r.by)}</td>
                <td className="py-1.5 break-words whitespace-pre-wrap">{asText(r.action)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DetailBody({ proposal, onJump }: { proposal: SiProposal; onJump: (id: string) => void }) {
  const [tab, setTab] = useState<DetailTab>("card");
  const q = useSiProposalDetail(proposal.id);
  const patrol = usePatrolView();

  if (q.isError) {
    if (q.error instanceof ApiError && q.error.status === 404) {
      return (
        <p data-testid="si-detail-not-found" className="text-sm">
          {T.detailNotFound}
        </p>
      );
    }
    return <SiError error={q.error} onRetry={() => void q.refetch()} />;
  }
  if (q.isPending) return <SiLoading what={T.detailLoadingWhat} />;

  const page = q.data;
  const item: Rec = isRec(page.items[0]) ? (page.items[0] as unknown as Rec) : {};
  const detail = isRec(item.detail) ? item.detail : null;
  const ne: NeWithText[] = Array.isArray(page.ne) ? (page.ne as Array<SiNeEntry & { text?: unknown }>) : [];
  const step = resolveNextStep({ proposalId: proposal.id, lastSeq: proposal.lastSeq, report: patrol.report, freshness: patrol.freshness, detailNext: detail?.next });
  const cardNe = proposal.card === null ? cardNeEntries(ne, proposal.id) : [];

  return (
    <div className="flex flex-col gap-3">
      <div data-testid="si-next-step" className="rounded-md border border-wg-line bg-wg-base px-4 py-2.5 text-sm">
        <p className="font-semibold break-words">{nextStepLine(step)}</p>
        {step.source === "none" ? null : <p className="text-xs text-wg-muted">{step.source === "snapshot" ? T.nextSourceSnapshot : T.nextSourceLedger}</p>}
        {step.warnPatrolMayBeDown ? (
          <p data-testid="si-next-warning" className="mt-1 text-wg-warning-text">
            {T.patrolMayBeDown}
          </p>
        ) : null}
      </div>

      <PillTabs label={T.detailTabsLabel} idBase={ID_BASE} tabs={TABS} value={tab} onChange={setTab} />

      <div role="tabpanel" id={pillPanelId(ID_BASE, tab)} aria-labelledby={pillTabId(ID_BASE, tab)} data-testid={`si-detail-panel-${tab}`}>
        {tab === "card" ? (
          proposal.card === null ? (
            <div data-testid="si-detail-card-missing" className="text-sm text-wg-warning-text">
              <p>{T.cardMissing}</p>
              {cardNe.length > 0 ? <p className="break-all">{`${T.cardNeNote}${cardNe.map(formatNe).join("；")}`}</p> : null}
            </div>
          ) : (
            <pre data-testid="si-detail-card" className="overflow-x-auto rounded-md border border-wg-line bg-wg-surface p-3 font-mono text-xs leading-relaxed">
              {proposal.card}
            </pre>
          )
        ) : detail === null ? (
          <NotProvided />
        ) : tab === "diff" ? (
          <SiDiffView propId={proposal.id} rev={proposal.rev} patch={detail.patch} ne={ne} />
        ) : tab === "body" ? (
          <BodyTab item={item} detail={detail} ne={ne} onJump={onJump} />
        ) : tab === "verify" ? (
          <VerifyTab detail={detail} nextHint={step.source === "none" ? null : nextStepLine(step)} />
        ) : (
          <TimelineTab detail={detail} ne={ne} propId={proposal.id} />
        )}
      </div>
    </div>
  );
}

/**
 * 提案詳情對話框：`proposal` 為 null＝關閉；開啟時才掛載內容（因此才取數），關閉即卸載（資料隨之丟棄）。
 * `onJumpToObservation`：來源觀察的跳轉（呼叫端關閉對話框、切到觀察分頁並高亮）。
 */
export function SiProposalDetail({ proposal, onClose, onJumpToObservation }: { proposal: SiProposal | null; onClose: () => void; onJumpToObservation: (obsId: string) => void }) {
  return (
    <Dialog open={proposal !== null} onOpenChange={(open) => (open ? undefined : onClose())}>
      {proposal ? (
        <DialogContent title={fillText(T.detailTitleFmt, { id: proposal.id })} description={T.detailDescription} aria-modal="true" className="w-[920px]">
          <DialogBody>
            <DetailBody
              proposal={proposal}
              onJump={(id) => {
                onClose();
                onJumpToObservation(id);
              }}
            />
          </DialogBody>
        </DialogContent>
      ) : null}
    </Dialog>
  );
}
