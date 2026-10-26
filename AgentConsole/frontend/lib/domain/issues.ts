/**
 * 議題中心的純函式與常數（TCS-IssueCenter-20261027 R-IC-63～71、R-IC-73；PRD §5.3、§7）：分頁與 `status` 傳值、顯示序（含優先順序）、嚴重度計件、篩選、
 * 提示條文字、優先順序表單驗證、英文詞偵測、reason 常數與錯誤文案。
 *
 * 只做「顯示用」的整形，**不重算任何判準**：歸類、中文對照、下一步、可排與否一律是根層 `issues` 的事（頁面＝export 的輸出）。
 * 所以本檔**不持有狀態詞清單**：分頁只認三個分頁名（它們就是傳給 API 的 `status` 別名，由根層展開成員）；其餘狀態、結果、來源、嚴重度的文字
 * 一律取自回應的 `legend`。靜態鎖（components/domain/issues/issues.static.test.ts）掃本檔，含 4 個以上不同的狀態詞即紅——包括註解，所以這裡不列舉它們。
 */
import { ApiError, describeError } from "@/lib/api/client";
import type { Issue, IssueLegend, IssuePriorityRequest, IssueSummary, SiNeEntry, SiProblem } from "@/lib/api/types";
import { SI_REASONS, codePointLength, hasForbiddenChar } from "@/lib/domain/si";

// ── 分頁與 status 傳值（R-IC-64）─────────────────────────────────────────────────────

export type IssueTabId = "pending" | "decide" | "done" | "all";

/** 摘要列與分頁的三個分頁名；同時也是向 API 傳的 `status` 值（全部分頁不帶）。 */
export const TAB_PENDING = "待處理";
export const TAB_DECIDE = "待您決定";
export const TAB_DONE = "已完成";

/** 四個分頁（顯示序，預設第一個）與各自向 API 傳的 `status`：全部＝null（不帶）。前端不展開成員清單。 */
export const ISSUE_TABS: ReadonlyArray<{ id: IssueTabId; label: string; status: string | null }> = [
  { id: "pending", label: TAB_PENDING, status: TAB_PENDING },
  { id: "decide", label: TAB_DECIDE, status: TAB_DECIDE },
  { id: "done", label: TAB_DONE, status: TAB_DONE },
  { id: "all", label: "全部", status: null },
];

export function tabStatus(tab: IssueTabId): string | null {
  return ISSUE_TABS.find((t) => t.id === tab)?.status ?? null;
}

/** 量不到（含載入中）一律顯示這個字，絕不顯示成 0。 */
export const EMPTY_VALUE = "—";

/** 摘要列某分頁的件數：`summary.byTab` 對應格為 null、缺席或根本沒有 summary（載入中、失敗）＝null（畫面顯示「—」）。 */
export function summaryCount(summary: IssueSummary | undefined, tab: Exclude<IssueTabId, "all">): number | null {
  const value = summary?.byTab[tabStatus(tab) as string];
  return typeof value === "number" ? value : null;
}

export function countText(count: number | null): string {
  return count === null ? EMPTY_VALUE : String(count);
}

// ── 顯示序（PRD §5.3；R-IC-66）──────────────────────────────────────────────────────

export type SortableIssue = Pick<Issue, "id" | "severityRank" | "updatedAt" | "rankable" | "priority">;

/** 有效順位：只對可排的列存在；不可排的列即使帶著遺留順位也視為無順位（不顯示、不參與排序）。 */
export function effectivePriority(issue: Pick<Issue, "rankable" | "priority">): number | null {
  return issue.rankable && typeof issue.priority === "number" ? issue.priority : null;
}

const ascending = <T extends number | string>(a: T, b: T): number => (a < b ? -1 : a > b ? 1 : 0);

/** 兩值比較，null 一律排最後（不論升降冪）。 */
function nullsLast<T extends number | string>(a: T | null, b: T | null, compare: (x: T, y: T) => number): number {
  if (a === null || b === null) return a === b ? 0 : a === null ? 1 : -1;
  return compare(a, b);
}

/** 第一條（待處理、待您決定）：優先順序升冪（無順位最後）→ severityRank 升冪（null 最後）→ updatedAt 升冪（最久沒動的在前，null 最後）→ id 字串升冪。 */
function compareQueue(a: SortableIssue, b: SortableIssue): number {
  return (
    nullsLast(effectivePriority(a), effectivePriority(b), ascending) || nullsLast(a.severityRank, b.severityRank, ascending) || nullsLast(a.updatedAt, b.updatedAt, ascending) || ascending(a.id, b.id)
  );
}

/** 第二條（已完成、全部）：updatedAt 降冪（null 最後）→ id 升冪。 */
function compareHistory(a: SortableIssue, b: SortableIssue): number {
  return nullsLast(a.updatedAt, b.updatedAt, (x, y) => ascending(y, x)) || ascending(a.id, b.id);
}

/** 依分頁套用兩條規則之一（待處理與待您決定用第一條，已完成與全部用第二條）；回傳新陣列，不改動輸入。 */
export function sortIssues<T extends SortableIssue>(items: ReadonlyArray<T>, tab: IssueTabId): T[] {
  return [...items].sort(tab === "pending" || tab === "decide" ? compareQueue : compareHistory);
}

/** 全部分頁置頂的狀態名：圖例中專屬分頁為「待您決定」的狀態（取自回應，不寫死狀態詞）。 */
export function pinnedStatuses(legend: IssueLegend | undefined): ReadonlySet<string> {
  return new Set((legend?.statuses ?? []).filter((s) => s.tab === TAB_DECIDE).map((s) => s.name));
}

/** 這一列要不要帶「置頂」標記：待您決定分頁每列都帶；全部分頁只有置頂狀態的列帶；其餘分頁沒有。 */
export function isPinned(issue: Pick<Issue, "status">, tab: IssueTabId, pinned: ReadonlySet<string>): boolean {
  return tab === "decide" || (tab === "all" && pinned.has(issue.status));
}

/** 畫面的列序：依分頁排序；全部分頁另把置頂狀態的列移到最前（其內依第一條），其餘依第二條。置頂只改顯示序，不改任何件數。 */
export function displayOrder<T extends SortableIssue & Pick<Issue, "status">>(items: ReadonlyArray<T>, tab: IssueTabId, pinned: ReadonlySet<string>): T[] {
  const sorted = sortIssues(items, tab);
  if (tab !== "all") return sorted;
  const top = sortIssues(
    sorted.filter((i) => pinned.has(i.status)),
    "decide",
  );
  return [...top, ...sorted.filter((i) => !pinned.has(i.status))];
}

// ── 嚴重度計件條（R-IC-64）──────────────────────────────────────────────────────────

export const SEVERITY_KEYS = ["urgent", "high", "mid", "low", "none", "unmapped"] as const;
export type SeverityKey = (typeof SEVERITY_KEYS)[number];
const RANK_KEYS: ReadonlyArray<SeverityKey> = ["urgent", "high", "mid", "low"];

/**
 * 六格計件：severity 為 null＝「—」；severityRank 為 1～4＝依序緊急、高、中、低；其餘（含「未歸類：P5」類與未知的 rank）＝未歸類。
 * 每個議題恰落入一格，所以六格加總恆等於輸入件數。
 */
export function severityCounts(items: ReadonlyArray<Pick<Issue, "severity" | "severityRank">>): Record<SeverityKey, number> {
  const counts: Record<SeverityKey, number> = { urgent: 0, high: 0, mid: 0, low: 0, none: 0, unmapped: 0 };
  for (const item of items) {
    const rank = item.severityRank;
    if (item.severity === null) counts.none += 1;
    else if (rank !== null && Number.isInteger(rank) && rank >= 1 && rank <= RANK_KEYS.length) counts[RANK_KEYS[rank - 1]] += 1;
    else counts.unmapped += 1;
  }
  return counts;
}

/** 計件條六格的文字：前四格取自圖例（依 rank），「—」固定，未歸類取圖例的前綴字串。 */
export function severityLabels(legend: IssueLegend): Record<SeverityKey, string> {
  const nameOf = (rank: number) => legend.severities.find((s) => s.rank === rank)?.name ?? EMPTY_VALUE;
  return { urgent: nameOf(1), high: nameOf(2), mid: nameOf(3), low: nameOf(4), none: EMPTY_VALUE, unmapped: legend.unmappedLabel };
}

// ── 篩選（R-IC-63、R-IC-66；B-21）───────────────────────────────────────────────────

export type IssueFilters = { source: string; keyword: string; status: string; result: string };
export const EMPTY_ISSUE_FILTERS: IssueFilters = { source: "", keyword: "", status: "", result: "" };

/** ASCII 不分大小寫：只折 A～Z，不碰其他字元（不依語系）。 */
export function foldAscii(text: string): string {
  return text.replace(/[A-Z]/g, (c) => String.fromCharCode(c.charCodeAt(0) + 32));
}

/** 關鍵字＝編號與標題的不分大小寫（ASCII）子字串；前後空白去掉，空白關鍵字＝不篩。 */
export function matchesKeyword(issue: Pick<Issue, "id" | "title">, keyword: string): boolean {
  const needle = foldAscii(keyword.trim());
  return needle === "" || foldAscii(issue.id).includes(needle) || foldAscii(issue.title).includes(needle);
}

/** 以圖例的前綴字串（「未歸類」）認「表外值」：值形如「<前綴>：<原值>」。 */
function isUnmapped(value: string | null, legend: IssueLegend | undefined): boolean {
  return value !== null && legend !== undefined && legend.unmappedLabel !== "" && value.startsWith(legend.unmappedLabel);
}

/** 下拉與 pill 的選值：空字串＝不篩；等於圖例前綴字串＝篩表外值；其餘為全等比對。 */
function matchesValue(actual: string | null, wanted: string, legend: IssueLegend | undefined): boolean {
  if (wanted === "") return true;
  if (legend !== undefined && wanted === legend.unmappedLabel) return isUnmapped(actual, legend);
  return actual === wanted;
}

/** 四種篩選（來源、狀態 pill、結果、關鍵字）取交集；只作用於已載入的項目。 */
export function filterIssues<T extends Pick<Issue, "id" | "title" | "source" | "status" | "result">>(items: ReadonlyArray<T>, filters: IssueFilters, legend: IssueLegend | undefined): T[] {
  return items.filter(
    (i) => matchesValue(i.source, filters.source, legend) && matchesValue(i.status, filters.status, legend) && matchesValue(i.result, filters.result, legend) && matchesKeyword(i, filters.keyword),
  );
}

export type IssueOption = { value: string; label: string };

/** 來源下拉：「全部」＋圖例四來源＋表外值（前綴字串）；文字都取自圖例。 */
export function sourceOptions(legend: IssueLegend): IssueOption[] {
  return [{ value: "", label: "全部" }, ...legend.sources.map((s) => ({ value: s.name, label: s.name })), { value: legend.unmappedLabel, label: legend.unmappedLabel }];
}

/** 結果快篩：「全部」＋圖例的結果（隨圖例改變，不寫死）。 */
export function resultOptions(legend: IssueLegend): IssueOption[] {
  return [{ value: "", label: "全部" }, ...legend.results.map((r) => ({ value: r.name, label: r.name }))];
}

/** 全部分頁的狀態 pill：圖例的每個狀態加表外值（前綴字串）。 */
export function statusPillNames(legend: IssueLegend): string[] {
  return [...legend.statuses.map((s) => s.name), legend.unmappedLabel];
}

// ── 列內文字 ─────────────────────────────────────────────────────────────────────────

/** 「<狀態>」；有結果時併列「<狀態>・<結果>」。 */
export function statusText(issue: Pick<Issue, "status" | "result">): string {
  return issue.result ? `${issue.status}・${issue.result}` : issue.status;
}

export function orDash(value: string | null | undefined): string {
  return value === null || value === undefined || value === "" ? EMPTY_VALUE : value;
}

// ── 提示條（R-IC-63）：說明文字取自圖例 ─────────────────────────────────────────────────

/** 每組最多列幾個對象，其餘以「等共 N 項」收尾（帳本問題可能上百筆，提示條不能撐爆版面）。 */
const HINT_MAX_TARGETS = 5;

export type HintLine = { key: string; text: string };

/** `ne` 條目的對象：項目級 `issues.<編號>.<欄>` 取編號，姊妹軌與歸檔檔取檔名；整本帳層級（例：缺陷帳本）的說明已寫在圖例釋義裡，不另列。 */
function neTarget(field: string): string | null {
  const item = /^issues\.([^.]+)\.[a-z_]+$/.exec(field);
  if (item) return item[1];
  const file = /^ledger\.(?:sibling|observation)\.(.+)$/.exec(field);
  return file ? file[1] : null;
}

function targetsText(targets: string[]): string {
  const shown = targets.slice(0, HINT_MAX_TARGETS).join("、");
  return targets.length > HINT_MAX_TARGETS ? `${shown} 等共 ${targets.length} 項` : shown;
}

/** 依 key 分組、保留首見次序。 */
function groupBy<T>(items: ReadonlyArray<T>, keyOf: (item: T) => string): Map<string, T[]> {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const key = keyOf(item);
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  return groups;
}

/** 提示條標題：`ne`、`problems` 各自非空才帶；兩者皆空回 null（沒有提示條）。 */
export function hintTitle(ne: ReadonlyArray<SiNeEntry>, problems: ReadonlyArray<SiProblem>): string | null {
  if (ne.length === 0 && problems.length === 0) return null;
  const parts = [ne.length > 0 ? `${ne.length} 項資料量不到` : null, problems.length > 0 ? `${problems.length} 筆帳本問題` : null];
  return `提示：${parts.filter((p) => p !== null).join("、")}`;
}

/**
 * 提示條的逐行說明：`ne` 依理由分組、`problems` 依問題碼分組，說明取自圖例（`neReasons`、`problemCodes` 的 meaning；圖例沒有該碼時退回原碼）。
 * 帳本讀不到時由圖例的釋義明說是哪一本（例：缺陷帳本讀不到）。
 */
export function hintLines(ne: ReadonlyArray<SiNeEntry>, problems: ReadonlyArray<SiProblem>, legend: IssueLegend | undefined): HintLine[] {
  const lines: HintLine[] = [];
  for (const [reason, entries] of groupBy(ne, (e) => e.reason)) {
    const meaning = legend?.neReasons.find((r) => r.reason === reason)?.meaning ?? reason;
    const targets = entries.map((e) => neTarget(e.field)).filter((t): t is string => t !== null);
    lines.push({ key: `ne:${reason}`, text: targets.length > 0 ? `${meaning}：${targetsText(targets)}` : meaning });
  }
  for (const [code, entries] of groupBy(problems, (p) => p.code)) {
    const meaning = legend?.problemCodes.find((c) => c.code === code)?.meaning ?? code;
    const targets = entries.map((p) => (p.detail ? `${p.subject}（${p.detail}）` : p.subject));
    lines.push({ key: `problem:${code}`, text: `${meaning}：${targetsText(targets)}` });
  }
  return lines;
}

// ── 優先順序表單（R-IC-70；B-22）─────────────────────────────────────────────────────

export const ISSUE_RANK_MIN = 1;
export const ISSUE_RANK_MAX = 9999;
export const ISSUE_NOTE_MAX = 200;

export type PriorityForm = { rank: string; note: string };
export type PriorityErrors = { rank?: string; note?: string };

/** 去前後空白後須全為半形數字（至多 4 位）且 1～9999；「1.5」「１２」「1e3」「0」「10000」一律不合。 */
const RANK_PATTERN = /^[0-9]{1,4}$/;

/**
 * 與 backend 輸入閘同一張表（backend 仍為權威）：順位必填、整數 1～9999；備註選填、至多 200 個 code point（全形與表情符號各算 1），不含控制字元
 * （含換行；backend 以 422 擋下）。前端先擋，不送出必被拒的本文。回傳欄位名→說明；空物件＝通過。
 */
export function validatePriorityForm(form: PriorityForm): PriorityErrors {
  const errors: PriorityErrors = {};
  const rank = form.rank.trim();
  if (rank === "") errors.rank = `順位為必填（${ISSUE_RANK_MIN}～${ISSUE_RANK_MAX} 的整數）`;
  else if (!RANK_PATTERN.test(rank) || Number(rank) < ISSUE_RANK_MIN) errors.rank = `順位須為 ${ISSUE_RANK_MIN}～${ISSUE_RANK_MAX} 的整數（半形數字）`;
  if (hasForbiddenChar(form.note)) errors.note = "備註不可含換行或控制字元";
  else {
    const length = codePointLength(form.note);
    if (length > ISSUE_NOTE_MAX) errors.note = `備註為 ${length} 個字元，超過上限 ${ISSUE_NOTE_MAX}`;
  }
  return errors;
}

/** 送給 PUT 的本文：順位去前後空白後轉數字，備註原樣（缺省以空字串送出）。呼叫前須先通過 validatePriorityForm。 */
export function buildPriorityRequest(form: PriorityForm): IssuePriorityRequest {
  return { rank: Number(form.rank.trim()), note: form.note };
}

// ── reason 與錯誤文案（R-IC-61）──────────────────────────────────────────────────────

/**
 * 議題中心自己的 reason（reason → 中文訊息）。刻意不放進 lib/api/reasons.ts：那個檔與凍結契約附錄 B 雙向鎖，多一個前端常數＝reasons.test.ts 紅。
 * 訊息與新契約檔 API_Contract_IssueCenter.md 的 issue 類 reason 表、backend 409 的 message 逐字相同（issues.test.ts 解析契約表雙向比對）。
 */
export const ISSUE_REASONS = {
  issue_not_rankable: "此議題目前的狀態不能設定優先順序",
} as const;

/** 422 的 `details.violations[{field,message}]` 逐項訊息（缺者回空陣列）。 */
function violationMessages(error: ApiError): string[] {
  const raw = error.details?.violations;
  if (!Array.isArray(raw)) return [];
  return raw.flatMap((v) => (typeof v === "object" && v !== null && typeof (v as { message?: unknown }).message === "string" ? [(v as { message: string }).message] : []));
}

/** 寫入（設定、清除順位）失敗的文案：409 的 `issue_not_rankable` 用逐字訊息；422 列出輸入閘的逐項說明；其餘沿 describeError。 */
export function issueWriteErrorText(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409 && error.reason === "issue_not_rankable") return ISSUE_REASONS.issue_not_rankable;
    if (error.status === 422) {
      const messages = violationMessages(error);
      if (messages.length > 0) return `輸入不合：${messages.join("；")}`;
    }
  }
  return describeError(error);
}

/** 讀取失敗的一句摘要：503 加 `si_unavailable`＝資料面不可用；404 加 `si_not_found`＝查無此議題；其餘沿 describeError。reason、detail、cause 另逐字顯示。 */
export function issuesErrorSummary(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 503 && error.reason === SI_REASONS.UNAVAILABLE) return "議題資料暫時無法取得";
    if (error.status === 404 && error.reason === SI_REASONS.NOT_FOUND) return "查無此議題";
  }
  return describeError(error);
}

// ── 中文判準（R-IC-69；§5.4）──────────────────────────────────────────────────────────

/**
 * 英文狀態詞表（22 詞；整詞比對、前後字元不屬英數與 `-`；議題 ID 形態先剔除）。根層 `issues.py` 的下一步與前端的可見文字檢查都引用這 22 詞，
 * 前端的單一份住這裡（D-C8）。畫面可見文字（排除標題、編號、原列展開區、優先順序備註、下一步欄的帳本原文節錄）不得含其中任何一個。
 */
export const ENGLISH_STATE_WORDS = [
  "open",
  "deferred",
  "fixed",
  "decided",
  "retired",
  "merged",
  "proposed",
  "routed",
  "wontfix",
  "closed-by-decision",
  "no_action_needed",
  "partial",
  "workaround",
  "verified",
  "approved",
  "returned",
  "sandboxed",
  "promoted",
  "measuring",
  "closed",
  "rejected",
  "handed-off",
] as const;

const ISSUE_ID_SHAPE = /OBS-SI-\d+|PROP-SI-\d+|DEF-\d+-\d+/g;
const escapeRegExp = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** 文字中出現的英文狀態詞（依詞表序、不重複）；空陣列＝通過。 */
export function englishStateWords(text: string): string[] {
  const stripped = text.replace(ISSUE_ID_SHAPE, " ");
  return ENGLISH_STATE_WORDS.filter((word) => new RegExp(`(?<![A-Za-z0-9-])${escapeRegExp(word)}(?![A-Za-z0-9-])`, "i").test(stripped));
}
