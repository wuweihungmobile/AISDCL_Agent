/**
 * SelfImproving 唯讀鏡像（P1b）的純函式與常數（TCS-SelfImprovingMirror-P1b R15、R17、R19）。
 * 這裡只做「顯示用」的整形：合併分頁、篩選、日期窗、量不到的呈現、錯誤文案；**不重算任何判準**——折疊、digest、NE、歸桶一律是根層
 * `si export` 的事（PRD AC-SI-32-1：頁面＝export 的輸出）。所以模組桶只讀資料自帶的 `buckets`，缺席就停用控制項、不自證據文字推算（R17）。
 */
import { ApiError, describeError } from "@/lib/api/client";
import type { SiEvent, SiInvalidRow, SiNeEntry, SiObservationRow, SiProblem, SiProposal } from "@/lib/api/types";

/**
 * 清單查詢的單頁筆數。初值 100（TCS ⚖24：無先例、未校準；`export_limit_max` 為 500，Bridge 不複製上限）；
 * 前端永不送超過上限的值，否則 CLI rc 3 會被標成「SI 不可用」。
 */
export const SI_PAGE_LIMIT = 100;

/**
 * SI 的 reason 常數（與凍結的 Architecture §11.1〈SelfImproving 相關的 reason〉表逐字一致，lib/domain/si.test.ts 解析該表比對）。
 * 刻意不放進 lib/api/reasons.ts 的 REASONS：REASONS 與凍結契約附錄 B 雙向鎖，多一個前端常數＝reasons.test.ts 紅（R19、⚖11）。
 * 422 `invalid_request` 是 Bridge 層的 reason（backend 以 details.bridgeReason 帶出、頂層 reason 是 BRIDGE_REJECTED），所以不在這裡。
 */
export const SI_REASONS = {
  UNAVAILABLE: "si_unavailable",
  NOT_FOUND: "si_not_found",
} as const;

/** 模組桶選項的顯示次序（只管排序，不管歸屬：比對恆用資料自帶的 `buckets` 成員關係）；表外的值依出現序附在後面。 */
export const BUCKET_DISPLAY_ORDER = ["SelfImproving", "AutoClaude", "AISDLC_SDD", "AgentConsole", "根層", "未分類"] as const;

/** `status` 單項的已知鍵（R13）；表外的鍵一律原樣列在 `si-status-extra`，不丟欄位。 */
export const SI_STATUS_KNOWN_KEYS = ["eventsDetected", "unavailable", "openRuns", "pendingProps", "suspended", "cooldowns", "skipReasons", "capacity", "frictionReconcile"] as const;

/** `status` 內「量不到」物件的標記值：`{ status: "NOT-EVALUABLE", reason }`。 */
export const NOT_EVALUABLE = "NOT-EVALUABLE";

// ── 分頁合併（R15）────────────────────────────────────────────────────────

/**
 * 清單項的身分鍵：有 seq（事件帳本的每一筆）用 seq，否則有 id（觀察列、提案、運轉）用 id，否則 line（壞列）；以型別前綴避免不同欄位互撞。
 * seq 必須排在 id 前面：事件物件本身可能帶 id（attr、prop 事件的 ATT-SI-…／PROP-SI-…），同一個提案的後續事件共用 id，但 seq 唯一。
 */
export function identityKey(item: { id?: unknown; seq?: unknown; line?: unknown }): string {
  if (typeof item.seq === "number") return `seq:${item.seq}`;
  if (typeof item.id === "string") return `id:${item.id}`;
  if (typeof item.line === "number") return `line:${item.line}`;
  // 沒有任何身分欄（不該發生）：以整個物件當鍵，不把兩個不同的項誤併成一個
  return `json:${JSON.stringify(item)}`;
}

/**
 * 依序串接各頁、依身分鍵去重（保留先到者）、不丟任何一筆。空頁與單頁不出錯。
 * 去重是為了「載入更多」的游標若重送一筆已出現的項（伺服器重疊或重試），畫面不會顯示兩次；先到者的內容不被覆寫。
 */
export function mergePages<T>(pages: ReadonlyArray<ReadonlyArray<T>>, keyOf: (item: T) => string | number): T[] {
  const seen = new Set<string | number>();
  const out: T[] = [];
  for (const page of pages) {
    for (const item of page) {
      const key = keyOf(item);
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(item);
    }
  }
  return out;
}

/** 多頁的 `ne[]`／`problems[]` 合併：依內容去重（每頁都可能重複列出全帳本層級的同一項）。 */
export function mergeNotes<T>(pages: ReadonlyArray<ReadonlyArray<T>>): T[] {
  return mergePages(pages, (item) => JSON.stringify(item));
}

// ── 觀察列 ─────────────────────────────────────────────────────────────────

export function isInvalidRow(row: SiObservationRow): row is SiInvalidRow {
  return row.valid === false;
}

/**
 * 處置的篩選鍵（R17、⚖20）：處置字串自頭起、到第一個 `：`、`；`、`;`、`:`、`@` 或空白為止的首詞；首詞以 `DEF-` 起頭者併為 `DEF-*`。
 * 例：`decided：寫成某檔`→`decided`、`fixed@abc1234`→`fixed`、`DEF-AC-003`→`DEF-*`、空字串→空字串。
 */
export function dispositionKey(text: string): string {
  const head = /^[^：；;:@\s]*/.exec(text.trimStart())?.[0] ?? "";
  return head.startsWith("DEF-") ? "DEF-*" : head;
}

// ── 時間窗（R17、⚖9）────────────────────────────────────────────────────────

export type DateWindow = "all" | "today" | "7d" | "30d";
/** 時間窗控制項的選項（順序＝顯示順序）。 */
export const DATE_WINDOW_OPTIONS: ReadonlyArray<{ id: DateWindow; label: string }> = [
  { id: "all", label: "全部" },
  { id: "today", label: "今天" },
  { id: "7d", label: "近 7 天" },
  { id: "30d", label: "近 30 天" },
];
export type WindowVerdict = "in" | "out" | "unparsable";

const WINDOW_DAYS: Record<Exclude<DateWindow, "all">, number> = { today: 1, "7d": 7, "30d": 30 };
const DAY_MS = 86_400_000;

/** 文字前 10 字元的日曆日（YYYY-MM-DD）→ 自 1970-01-01 起的整數日序；格式不符或不是真實存在的日期回 null。純日曆算術，不經時區。 */
function dayNumber(text: string | null | undefined): number | null {
  if (typeof text !== "string") return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(text.trim());
  if (!m) return null;
  const [year, month, day] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const ms = Date.UTC(year, month - 1, day);
  const back = new Date(ms);
  // 往返一次：2026-02-30 這類不存在的日期會被 Date.UTC 滾到隔月，往返不相等就是無法解析
  if (back.getUTCFullYear() !== year || back.getUTCMonth() !== month - 1 || back.getUTCDate() !== day) return null;
  return ms / DAY_MS;
}

/**
 * 日期是否落在時間窗內。錨點是該回應 `generatedAt` 的日期部分（依其自帶 offset 取字面日期，不用瀏覽器時鐘）；
 * `today`＝日期等於錨點日；`7d`／`30d`＝日期介於錨點日往前 N−1 日與錨點日之間，含兩端。
 * 觀察以 `time`、事件以 `t` 的前 10 字元為日期（區間寫法 `2026-10-18 21:20～22:05` 取前 10 字元）。
 * 日期或錨點無法解析 → `unparsable`（呼叫端不得把它篩掉，並標「時間無法解析」）；`all` 恆為 `in`。
 * 不做時區換算：觀察時間欄無 offset、檔頭 tz 不在 export 內；±1 日邊界是已知邊界（TCS §4 已知邊界 9）。
 */
export function inDateWindow(dateText: string | null | undefined, anchorIso: string | null | undefined, win: DateWindow): WindowVerdict {
  if (win === "all") return "in";
  const day = dayNumber(dateText);
  const anchor = dayNumber(anchorIso);
  if (day === null || anchor === null) return "unparsable";
  return day <= anchor && day >= anchor - (WINDOW_DAYS[win] - 1) ? "in" : "out";
}

// ── 篩選（R17；多個條件為「且」，先分頁後篩選）──────────────────────────────────

/** 空字串＝該條件不篩（控制項的「全部」）。 */
export type ObsFilters = { category: string; severity: string; disposition: string; bucket: string; window: DateWindow };
export const EMPTY_OBS_FILTERS: ObsFilters = { category: "", severity: "", disposition: "", bucket: "", window: "all" };

/**
 * 觀察列篩選：無法解析的壞列（valid 為 false）在任何篩選下都保留；時間無法解析者不被時間窗篩掉；
 * 模組桶只認資料自帶的 `buckets`（含所選值才符合），沒有 `buckets` 欄的列不符合任何選定的桶——前端不自證據座標文字歸桶。
 */
export function filterObservations(items: ReadonlyArray<SiObservationRow>, filters: Partial<ObsFilters>, anchorIso: string | null | undefined): SiObservationRow[] {
  const f = { ...EMPTY_OBS_FILTERS, ...filters };
  return items.filter((row) => {
    if (isInvalidRow(row)) return true;
    if (f.category && row.category !== f.category) return false;
    if (f.severity && row.severity !== f.severity) return false;
    if (f.disposition && dispositionKey(row.disposition) !== f.disposition) return false;
    if (f.bucket && !(Array.isArray(row.buckets) && row.buckets.includes(f.bucket))) return false;
    return inDateWindow(row.time, anchorIso, f.window) !== "out";
  });
}

/** 任何一筆有效觀察帶 `buckets` 欄＝根層已交付模組桶；全部都沒有＝控制項停用並說明（R17）。 */
export function hasBucketData(items: ReadonlyArray<SiObservationRow>): boolean {
  return items.some((row) => !isInvalidRow(row) && Array.isArray(row.buckets));
}

/** 模組桶的選項：取自已載入資料的相異值，已知桶依 BUCKET_DISPLAY_ORDER、未知桶依出現序附後。 */
export function bucketOptions(items: ReadonlyArray<SiObservationRow>): string[] {
  const seen: string[] = [];
  for (const row of items) {
    if (isInvalidRow(row) || !Array.isArray(row.buckets)) continue;
    for (const bucket of row.buckets) if (typeof bucket === "string" && !seen.includes(bucket)) seen.push(bucket);
  }
  const order: readonly string[] = BUCKET_DISPLAY_ORDER;
  return [...order.filter((b) => seen.includes(b)), ...seen.filter((b) => !order.includes(b))];
}

/** 控制項選項：取自已載入資料的相異非空值，依字碼排序（與環境語系無關，輸出穩定）。 */
export function distinctValues<T>(items: ReadonlyArray<T>, pick: (item: T) => string | null | undefined): string[] {
  const set = new Set<string>();
  for (const item of items) {
    const value = pick(item);
    if (typeof value === "string" && value !== "") set.add(value);
  }
  return [...set].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

export type ProposalFilters = { state: string; cls: string };
export const EMPTY_PROPOSAL_FILTERS: ProposalFilters = { state: "", cls: "" };

/** 提案篩選：`狀態`（state）與 `類別`（cls）；提案沒有時間窗。 */
export function filterProposals(items: ReadonlyArray<SiProposal>, filters: Partial<ProposalFilters>): SiProposal[] {
  const f = { ...EMPTY_PROPOSAL_FILTERS, ...filters };
  return items.filter((p) => (!f.state || p.state === f.state) && (!f.cls || p.cls === f.cls));
}

export type EventFilters = { kind: string; window: DateWindow };
export const EMPTY_EVENT_FILTERS: EventFilters = { kind: "", window: "all" };

/** 事件篩選：`種類`（kind）與時間窗（以 `t` 的前 10 字元為日期）；時間無法解析者不被篩掉。 */
export function filterEvents(items: ReadonlyArray<SiEvent>, filters: Partial<EventFilters>, anchorIso: string | null | undefined): SiEvent[] {
  const f = { ...EMPTY_EVENT_FILTERS, ...filters };
  return items.filter((e) => (!f.kind || e.kind === f.kind) && inDateWindow(e.t, anchorIso, f.window) !== "out");
}

// ── 量不到與狀態橫幅的呈現（R13、R16）─────────────────────────────────────────

/** `{ status: "NOT-EVALUABLE", reason }` 形態：欄位量不到，不得顯示成 0、空字串、無、通過或正常。 */
export function isNotEvaluable(value: unknown): value is { status: typeof NOT_EVALUABLE; reason?: unknown } {
  return typeof value === "object" && value !== null && !Array.isArray(value) && (value as { status?: unknown }).status === NOT_EVALUABLE;
}

export function compactJson(value: unknown): string {
  return JSON.stringify(value) ?? "";
}

export function prettyJson(value: unknown): string {
  return JSON.stringify(value, null, 2) ?? "";
}

/** 量不到的固定句型：`量不到（NOT-EVALUABLE）`，有原因時接 `：<原因>`。 */
export function notEvaluableText(reason?: unknown): string {
  const base = "量不到（NOT-EVALUABLE）";
  return reason === undefined || reason === null || reason === "" ? base : `${base}：${typeof reason === "string" ? reason : compactJson(reason)}`;
}

/**
 * 狀態橫幅單一值的純文字：量不到物件 → `量不到（NOT-EVALUABLE）：<reason>`；null → `無`（`suspended` 的「沒有暫停」）；
 * 字串、數字、布林原樣；陣列與物件為緊湊 JSON。一律回字串，由呼叫端放進 React 文字節點（不渲染成 HTML）。
 */
export function describeValue(value: unknown): string {
  if (isNotEvaluable(value)) return notEvaluableText(value.reason);
  if (value === null || value === undefined) return "無";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return compactJson(value);
}

/** 提案 `touched`／`touchedCount` 量不到的原因：根層 export 在對應的 rN.patch 讀不到或無法解析時給 null，且不附 ne 項。 */
export const TOUCHED_NE_REASON = "patch 讀不到或無法解析";

/**
 * 提案 `touched`／`touchedCount` 的純文字（R16）：null（或缺席）是量不到，不是「沒有觸及檔案」——後者是 `[]` 與 `0`，照 describeValue 顯示；
 * 所以 null 不得顯示成「無」，改顯示 `量不到（NOT-EVALUABLE）：patch 讀不到或無法解析`。
 */
export function describeTouched(value: unknown): string {
  return value === null || value === undefined ? notEvaluableText(TOUCHED_NE_REASON) : describeValue(value);
}

/** `eventsDetected` 為空時的說明：`unavailable` 長度 k>0 時要帶「尚有 k 項量不到」，不得只說無事件（R13、R16）。 */
export function noEventText(unavailableCount: number): string {
  return unavailableCount > 0 ? `無事件（尚有 ${unavailableCount} 項量不到）` : "無事件";
}

export function formatNe(entry: SiNeEntry): string {
  return `${entry.field}：${entry.reason}`;
}

export function formatProblem(problem: SiProblem): string {
  return `${problem.subject} ${problem.code} ${problem.detail}`;
}

/** 提案 digest 的前 8 碼（去掉 `sha256:` 前綴；與狀態橫幅的 digest8、卡面的 digest 同形）。 */
export function digest8(digest: string): string {
  return digest.replace(/^sha256:/, "").slice(0, 8);
}

/** 某提案卡面量不到時，`ne[]` 中對應的項（欄位名含該提案 id 且以 card 結尾，例 `proposals.PROP-SI-004.card`）。 */
export function cardNeEntries(ne: ReadonlyArray<SiNeEntry>, proposalId: string): SiNeEntry[] {
  return ne.filter((entry) => entry.field.includes(proposalId) && entry.field.endsWith("card"));
}

// ── 錯誤文案（R19）────────────────────────────────────────────────────────────

/**
 * 錯誤態的一句摘要：503 加 `si_unavailable`＝`SI 資料面不可用`；404 加 `si_not_found`＝`查無此筆`；其餘沿 describeError。
 * 摘要只是一句人話，不取代 reason／detail／cause 的逐字顯示。
 */
export function siErrorSummary(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 503 && error.reason === SI_REASONS.UNAVAILABLE) return "SI 資料面不可用";
    if (error.status === 404 && error.reason === SI_REASONS.NOT_FOUND) return "查無此筆";
  }
  return describeError(error);
}

/** 錯誤態要逐字顯示的三項：`ApiError.reason`、`details.detail`（`rc=<n>; stderr=…`）、`details.cause`（Bridge 的失敗碼）；缺者不顯示。 */
export function siErrorParts(error: unknown): { reason?: string; detail?: string; cause?: string } {
  if (!(error instanceof ApiError)) return {};
  const pick = (value: unknown): string | undefined => (typeof value === "string" ? value : undefined);
  return { reason: error.reason, detail: pick(error.details?.detail), cause: pick(error.details?.cause) };
}
