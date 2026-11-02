"use client";

/**
 * 證據矩陣表與技術優缺點矩陣（研究工作區步驟 1；FR-R2P-05、06；TCS-ResearchToPRD-P0-20261102 AT-960-10-6；PRD 頁面 1 的兩個分頁）：
 *  - **證據矩陣表**：每列一個證據（`E-NNN`、候選技術、論點、來源、查證層級、強度、標記），可展開看 F1～F7 七欄與該來源的抓取紀錄；頁頂計 UNANCHORED 與授權待查；
 *    最新版以外的版本唯讀（矩陣本來就沒有任何編輯動作，舊版另加說明）。
 *  - **技術優缺點矩陣**：依候選技術分組、**只列有證據列的候選**（沒有候選名的列不歸任何組、只存在於範圍的候選不憑空出現）；每格帶 `[E-NNN]` 連結，點了切到矩陣表並展開該列。
 *
 * 設計要點（為什麼這樣做）：
 *  - **兩種視圖同在一份 DOM**（`view` 決定哪一個可見，另一個 `hidden`）：優缺點格的連結目標（矩陣表的列）恆存在，不必等切換分頁；切換分頁由呼叫端（議題面板）持有。
 *  - **外部來源是資料不是指令**：標題、論點、批評、限制等一律以文字節點渲染（沒有 Markdown、沒有原始 HTML）；來源網址只有合法 https 才成為連結（`rel="noopener noreferrer"`），
 *    其餘（`javascript:`、`data:`、沒有網址）只顯示文字。解析不出 host 的被拒外呼其 host 是保留字 `(unparsed)`，原樣顯示、不轉空白、不加連結（D-66）。
 *  - 資料全由既有查詢取得（`useResearchEvidence`、`useResearchSources`；尚無矩陣時後端回 `matrixVersion=0` 的空矩陣，顯示空狀態而不是錯誤）。
 */
import { ChevronDown, ChevronRight, TriangleAlert } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { useResearchEvidence, useResearchSources } from "@/lib/api/queries";
import type { ResearchCounterEvidence, ResearchEvidenceItem, ResearchSource } from "@/lib/api/types";
import {
  EVIDENCE_STRENGTH_LABEL,
  RESEARCH_UNPARSED_HOST,
  SOURCE_LAYER_LABEL,
  formatInstant,
  isLicensePending,
  licensePendingCount,
  prosConsMatrix,
  qualifiedEvidenceRows,
  safeExternalHref,
  unanchoredCount,
  type ProsConsEntry,
} from "@/lib/domain/research";
import { cn } from "@/lib/utils";

export type EvidenceMatrixView = "table" | "proscons";
/** 呼叫端的分頁籤要接的面板屬性（`PillTabs` 的 `aria-controls` 指向這些 id）；沒給就只是兩個普通區塊。 */
export type MatrixTabPanels = Partial<Record<EvidenceMatrixView, { id: string; labelledBy: string }>>;
const panelProps = (panel: { id: string; labelledBy: string } | undefined) => (panel === undefined ? {} : { role: "tabpanel" as const, id: panel.id, "aria-labelledby": panel.labelledBy });

const COUNTER_LABEL: Readonly<Record<ResearchCounterEvidence["conclusion"], string>> = { WEAKEN: "削弱", LIMIT: "限縮", IRRELEVANT: "無關", NOT_FOUND: "查無", NOT_SEARCHED: "未搜尋" };
const OBSERVED_LABEL = { BRIDGE: "Bridge 觀測", AGENT_DECLARED: "agent 宣告" } as const;

const rowId = (evidenceNo: string): string => `evidence-row-${evidenceNo}`;
/** 空白欄位一律顯示「未見」（框架模板：缺欄寫「未見」、不留白）。 */
const orUnseen = (text: string | null | undefined): string => (typeof text === "string" && text.trim() !== "" ? text : "未見");

/** 合法 https 才成連結；其餘只顯示文字。 */
function MaybeLink({ url, children }: { url: string | null; children: ReactNode }) {
  const href = safeExternalHref(url);
  if (href === null) return <>{children}</>;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-wg-primary hover:underline">
      {children}
    </a>
  );
}

function Flag({ tone, children }: { tone: "alert" | "muted"; children: ReactNode }) {
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-xs font-medium", tone === "alert" ? "bg-wg-alert-bg text-wg-warning-text" : "bg-wg-base text-wg-muted")}>
      {tone === "alert" ? <TriangleAlert size={12} aria-hidden /> : null}
      {children}
    </span>
  );
}

function FetchRecords({ source }: { source: ResearchSource | undefined }) {
  if (source === undefined || source.fetches.length === 0) return <p className="text-sm text-wg-muted">無（宣告型）：這個來源沒有 Bridge 的抓取紀錄，查證層級以 agent 宣告為準。</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-xs" data-testid="fetch-records">
        <caption className="sr-only">抓取紀錄</caption>
        <thead>
          <tr className="text-left text-wg-muted">
            {["編號", "方法", "觀測者", "主機", "狀態碼", "結果", "原文 sha256", "位元組", "時間"].map((head) => (
              <th key={head} scope="col" className="px-2 py-1 font-medium">
                {head}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {source.fetches.map((fetch) => (
            <tr key={fetch.fetchNo} data-testid="fetch-record" className="border-t border-wg-line">
              <td className="px-2 py-1 font-mono">{fetch.fetchNo}</td>
              <td className="px-2 py-1">{fetch.method}</td>
              <td className="px-2 py-1">{OBSERVED_LABEL[fetch.observedBy] ?? fetch.observedBy}</td>
              <td className="px-2 py-1 font-mono" title={fetch.host === RESEARCH_UNPARSED_HOST ? "網址解析不出主機名稱（被拒的外呼）" : undefined}>
                {fetch.host}
              </td>
              <td className="px-2 py-1">{fetch.httpStatus ?? "—"}</td>
              <td className={cn("px-2 py-1", fetch.outcome !== "OK" && "font-medium text-wg-warning-text")}>{fetch.outcome}</td>
              <td className="px-2 py-1 font-mono">{fetch.rawSha256 === null ? "—" : fetch.rawSha256.slice(0, 8)}</td>
              <td className="px-2 py-1">{fetch.rawBytes === null ? "—" : fetch.rawBytes.toLocaleString("en-US")}</td>
              <td className="px-2 py-1">{formatInstant(fetch.fetchedAt)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EvidenceDetail({ item, source, counters }: { item: ResearchEvidenceItem; source: ResearchSource | undefined; counters: ResearchCounterEvidence[] }) {
  const applicability = Object.entries(item.f5Applicability);
  const fields: Array<[string, ReactNode]> = [
    ["F1 機制", orUnseen(item.f1Mechanism)],
    ["F2 證據", orUnseen(item.f2Evidence)],
    ["F3 失敗與批評", orUnseen(item.f3Critique)],
    ["F4 風險標籤", item.f4RiskTags.length === 0 ? "無" : item.f4RiskTags.join("、")],
    [
      "F5 適用性",
      applicability.length === 0 ? (
        "未見"
      ) : (
        <ul className="list-disc pl-4">
          {applicability.map(([axis, cell]) => (
            <li key={axis}>
              {axis}：{cell.grade}（{cell.reason}）
            </li>
          ))}
        </ul>
      ),
    ],
    ["F6 限制", orUnseen(item.f6Limits)],
    ["F7 查證層級", item.f7Verification],
  ];
  return (
    <div className="flex flex-col gap-3 px-4 py-3" data-testid="evidence-detail">
      <dl className="grid gap-x-4 gap-y-2 text-sm md:grid-cols-[9rem_1fr]">
        {fields.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="font-medium text-wg-muted">{label}</dt>
            <dd className="min-w-0 break-words">{value}</dd>
          </div>
        ))}
      </dl>
      {counters.length > 0 ? (
        <div className="text-sm">
          <p className="font-medium text-wg-muted">反證</p>
          <ul className="list-disc pl-4">
            {counters.map((counter, i) => (
              <li key={`${counter.searchId ?? "none"}-${i}`}>
                {COUNTER_LABEL[counter.conclusion] ?? counter.conclusion}：{orUnseen(counter.note)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <div>
        <p className="mb-1 text-sm font-medium text-wg-muted">抓取紀錄</p>
        <FetchRecords source={source} />
      </div>
    </div>
  );
}

function SourceCell({ source, sourceNo }: { source: ResearchSource | undefined; sourceNo: string }) {
  if (source === undefined) return <span className="font-mono text-xs">{sourceNo}</span>;
  const locator = source.doi !== null ? `DOI ${source.doi}` : source.gitCommit !== null ? `commit ${source.gitCommit.slice(0, 7)}` : null;
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <span className="font-mono text-xs text-wg-muted">
        {source.sourceNo} · {SOURCE_LAYER_LABEL[source.layer] ?? source.layer}
      </span>
      <MaybeLink url={source.url}>
        <span className="break-words">{source.title}</span>
      </MaybeLink>
      {locator === null ? null : <span className="font-mono text-xs text-wg-muted">{locator}</span>}
    </div>
  );
}

function ProsConsList({ entries, kind, onGo }: { entries: ProsConsEntry[]; kind: "pro" | "con"; onGo: (evidenceNo: string) => void }) {
  if (entries.length === 0) return <span className="text-wg-muted">—</span>;
  return (
    <ul className="flex flex-col gap-1.5">
      {entries.map((entry, i) => (
        <li key={`${entry.evidenceNo}-${i}`} data-testid="proscons-cell" data-kind={kind} data-evidence-no={entry.evidenceNo} className="break-words">
          <span>{entry.text}</span>{" "}
          <a
            href={`#${rowId(entry.evidenceNo)}`}
            title={`跳到證據矩陣表的 ${entry.evidenceNo} 列`}
            onClick={(event) => {
              event.preventDefault();
              onGo(entry.evidenceNo);
            }}
            className="font-mono text-xs text-wg-primary hover:underline"
          >
            [{entry.evidenceNo}]
          </a>
        </li>
      ))}
    </ul>
  );
}

export function EvidenceMatrixTable({
  researchId,
  view,
  onViewChange,
  tabPanels,
}: {
  researchId: string;
  view: EvidenceMatrixView;
  onViewChange?: (view: EvidenceMatrixView) => void;
  tabPanels?: MatrixTabPanels;
}) {
  const [picked, setPicked] = useState<number | null>(null);
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(new Set());
  const [focus, setFocus] = useState<{ evidenceNo: string; n: number } | null>(null);
  const rows = useRef(new Map<string, HTMLTableRowElement>());
  const latestQuery = useResearchEvidence(researchId);
  const pickedQuery = useResearchEvidence(researchId, picked ?? undefined);
  const sourcesQuery = useResearchSources(researchId);
  const sources = sourcesQuery.data;

  // 從優缺點格的 [E-NNN] 連結跳來：矩陣表可見之後再捲到並聚焦該列（尚未切過來時列是 hidden，不能先聚焦）
  useEffect(() => {
    if (focus === null || view !== "table") return;
    const row = rows.current.get(focus.evidenceNo);
    if (row === undefined) return;
    if (typeof row.scrollIntoView === "function") row.scrollIntoView({ block: "center" });
    row.focus();
  }, [focus, view]);

  // 最新版第一次載入（或失敗）才整個換成骨架／錯誤；切到舊版時標頭與版本下拉常駐，只有內文換成載入中，使用者才切得回去
  const latest = latestQuery.data;
  if (latest === undefined) {
    if (latestQuery.isError) return <ErrorState error={latestQuery.error} title="無法載入證據矩陣" onRetry={() => void latestQuery.refetch()} />;
    return (
      <div aria-busy="true" aria-label="證據矩陣載入中" role="status">
        <Skeleton className="h-40 rounded-lg" />
      </div>
    );
  }

  const latestVersion = latest.matrixVersion;
  const matrix = picked === null ? latest : pickedQuery.data;
  const isOld = matrix !== undefined && matrix.matrixVersion < latestVersion;
  const items = matrix?.items ?? [];
  const sourceOf = new Map((sources ?? []).map((s) => [s.sourceNo, s] as const));
  const countersOf = (evidenceNo: string) => (matrix?.counterEvidence ?? []).filter((c) => c.evidenceNo === evidenceNo);
  const candidates = matrix === undefined ? [] : prosConsMatrix(matrix);

  function toggle(evidenceNo: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(evidenceNo)) next.delete(evidenceNo);
      else next.add(evidenceNo);
      return next;
    });
  }
  function goTo(evidenceNo: string) {
    setExpanded((current) => new Set(current).add(evidenceNo));
    setFocus((current) => ({ evidenceNo, n: (current?.n ?? 0) + 1 }));
    onViewChange?.("table");
  }

  return (
    <section data-testid="evidence-matrix" aria-label="證據矩陣" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-wg-muted" data-testid="evidence-summary">
        {matrix === undefined ? (
          <span>載入矩陣 v{picked}…</span>
        ) : (
          <>
            <span>
              {matrix.matrixVersion === 0 ? "尚無矩陣版本" : `矩陣 v${matrix.matrixVersion}`}
              {isOld ? "（舊版，唯讀）" : ""} · 共 {items.length} 列
            </span>
            {sources === undefined ? null : <span>合格 {qualifiedEvidenceRows(items, sources).length} 列</span>}
            <span data-testid="unanchored-count">UNANCHORED：{unanchoredCount(items)} 筆</span>
            {sources === undefined ? null : <span data-testid="license-pending-count">授權待查：{licensePendingCount(items, sources)} 列</span>}
          </>
        )}
        {latestVersion > 1 ? (
          <Select
            size="sm"
            aria-label="矩陣版本"
            value={picked === null ? latestVersion : picked}
            onChange={(event) => {
              const version = Number(event.target.value);
              setPicked(version === latestVersion ? null : version);
            }}
            className="w-auto"
          >
            {Array.from({ length: latestVersion }, (_, i) => latestVersion - i).map((version) => (
              <option key={version} value={version}>
                v{version}
                {version === latestVersion ? "（最新）" : ""}
              </option>
            ))}
          </Select>
        ) : null}
      </div>
      {isOld ? (
        <p role="note" className="rounded-md border border-wg-line bg-wg-surface px-3 py-2 text-sm text-wg-muted">
          這是舊版矩陣（v{matrix.matrixVersion}），只供對照；最新版是 v{latestVersion}。
        </p>
      ) : null}

      {matrix === undefined ? (
        pickedQuery.isError ? (
          <ErrorState error={pickedQuery.error} title={`無法載入矩陣 v${picked}`} onRetry={() => void pickedQuery.refetch()} />
        ) : (
          <div aria-busy="true" aria-label="證據矩陣載入中" role="status">
            <Skeleton className="h-40 rounded-lg" />
          </div>
        )
      ) : null}
      <div hidden={view !== "table" || matrix === undefined} data-testid="evidence-table-view" {...panelProps(tabPanels?.table)}>
        {items.length === 0 ? (
          <EmptyState title="還沒有證據列" description="啟動深研後，取得的來源與抽取出的證據列會出現在這裡。" />
        ) : (
          <div className="overflow-x-auto rounded-md border border-wg-line">
            <table className="w-full min-w-[760px] border-collapse text-sm" data-testid="evidence-table">
              <caption className="sr-only">證據矩陣表</caption>
              <thead>
                <tr className="bg-wg-base text-left text-xs text-wg-muted">
                  {["編號", "候選技術", "論點", "來源", "層級", "強度", "標記"].map((head) => (
                    <th key={head} scope="col" className="px-3 py-2 font-medium">
                      {head}
                    </th>
                  ))}
                </tr>
              </thead>
              {items.map((item) => {
                const source = sourceOf.get(item.sourceNo);
                const open = expanded.has(item.evidenceNo);
                const detailId = `evidence-detail-${item.evidenceNo}`;
                return (
                  <tbody key={item.evidenceNo} className="border-t border-wg-line">
                    <tr
                      id={rowId(item.evidenceNo)}
                      ref={(node) => {
                        if (node === null) rows.current.delete(item.evidenceNo);
                        else rows.current.set(item.evidenceNo, node);
                      }}
                      tabIndex={-1}
                      data-testid="evidence-row"
                      data-evidence-no={item.evidenceNo}
                      data-expanded={open || undefined}
                      className="align-top"
                    >
                      <td className="px-3 py-2">
                        <button
                          type="button"
                          aria-expanded={open}
                          aria-controls={detailId}
                          aria-label={`${open ? "收合" : "展開"} ${item.evidenceNo} 的七欄與抓取紀錄`}
                          onClick={() => toggle(item.evidenceNo)}
                          className="inline-flex cursor-pointer items-center gap-1 font-mono text-xs hover:text-wg-primary"
                        >
                          {open ? <ChevronDown size={14} aria-hidden /> : <ChevronRight size={14} aria-hidden />}
                          {item.evidenceNo}
                        </button>
                      </td>
                      <td className="px-3 py-2">{item.candidate ?? "—"}</td>
                      <td className="min-w-0 px-3 py-2 break-words">{item.claim}</td>
                      <td className="px-3 py-2">
                        <SourceCell source={source} sourceNo={item.sourceNo} />
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        {source === undefined ? "" : `${source.tier} · `}
                        {item.f7Verification}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">{EVIDENCE_STRENGTH_LABEL[item.strength] ?? item.strength}</td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          {item.unanchored ? <Flag tone="alert">UNANCHORED</Flag> : null}
                          {source !== undefined && isLicensePending(source.licenseSpdx) ? <Flag tone="muted">授權待查</Flag> : null}
                          {source?.clueOnly === true ? <Flag tone="muted">線索</Flag> : null}
                        </div>
                      </td>
                    </tr>
                    {open ? (
                      <tr id={detailId} className="bg-wg-surface">
                        <td colSpan={7}>
                          <EvidenceDetail item={item} source={source} counters={countersOf(item.evidenceNo)} />
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                );
              })}
            </table>
          </div>
        )}
      </div>

      <div hidden={view !== "proscons" || matrix === undefined} data-testid="proscons-view" {...panelProps(tabPanels?.proscons)}>
        {candidates.length === 0 ? (
          <EmptyState
            title={items.length === 0 ? "還沒有證據列" : "沒有可分組的候選技術"}
            description={items.length === 0 ? "有證據列的候選技術才會列在這裡，不會憑空列出。" : "證據列沒有填候選技術名稱，所以沒有優缺點可列。"}
          />
        ) : (
          <div className="flex flex-col gap-2">
            <p className="text-xs text-wg-muted">只列有證據列的候選技術。優點取自證據列的論點；缺點取自失敗與批評（F3）、限制（F6）與判為削弱或限縮的反證；每格的 [E-NNN] 可跳到矩陣表的對應列。</p>
            <div className="overflow-x-auto rounded-md border border-wg-line">
              <table className="w-full min-w-[640px] border-collapse text-sm" data-testid="proscons-matrix">
                <caption className="sr-only">技術優缺點矩陣</caption>
                <thead>
                  <tr className="bg-wg-base text-left text-xs text-wg-muted">
                    <th scope="col" className="px-3 py-2 font-medium">
                      候選技術
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      優點
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      缺點
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {candidates.map((candidate) => (
                    <tr key={candidate.candidate} data-testid="proscons-candidate" data-candidate={candidate.candidate} className="border-t border-wg-line align-top">
                      <th scope="row" className="px-3 py-2 text-left font-medium">
                        {candidate.candidate}
                        <span className="block text-xs font-normal text-wg-muted">{candidate.evidenceNos.length} 列證據</span>
                      </th>
                      <td className="px-3 py-2">
                        <ProsConsList entries={candidate.pros} kind="pro" onGo={goTo} />
                      </td>
                      <td className="px-3 py-2">
                        <ProsConsList entries={candidate.cons} kind="con" onGo={goTo} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
