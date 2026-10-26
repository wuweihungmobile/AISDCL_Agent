/**
 * SelfImproving 的純函式與常數：唯讀鏡像（P1b；TCS-SelfImprovingMirror-P1b R15、R17、R19）加寫入面（P2b；TCS-SelfImprovingDecide-P2b W17，檔尾）。
 * 鏡像這一半只做「顯示用」的整形：合併分頁、篩選、日期窗、量不到的呈現、錯誤文案；**不重算任何判準**——折疊、digest、NE、歸桶一律是根層
 * `si export` 的事（PRD AC-SI-32-1：頁面＝export 的輸出）。所以模組桶只讀資料自帶的 `buckets`，缺席就停用控制項、不自證據文字推算（R17）。
 * 寫入面同樣不重算判準：不判卡面 digest 新鮮度、不判 PROP 前提的細節（⚖15）——前端只擋「根層入帳時不拒、事後 `check` 才轉紅」的形態錯誤
 * （與 backend 的 SiWriteGates 同一張表，backend 仍為權威），其餘一律交給入帳時的根層 CLI。
 */
import { ApiError, describeError } from "@/lib/api/client";
import type {
  SiCloseRequest,
  SiConsoleWrite,
  SiDecideKind,
  SiDecideRequest,
  SiEvent,
  SiInvalidRow,
  SiNeEntry,
  SiObservationRequest,
  SiObservationRow,
  SiProblem,
  SiProposal,
  SiWriteKind,
} from "@/lib/api/types";

/**
 * 清單查詢的單頁筆數。初值 100（TCS ⚖24：無先例、未校準；`export_limit_max` 為 500，Bridge 不複製上限）；
 * 前端永不送超過上限的值，否則 CLI rc 3 會被標成「SI 不可用」。
 */
export const SI_PAGE_LIMIT = 100;

/**
 * 狀態快篩自動載入的頁數上限（含已載入的頁）：清單是游標分頁、篩選只作用於已載入的頁，所以選了「全部」以外的快篩時面板會把其餘的頁一頁頁載完；
 * 上限擋住「帳本長到數千列」或「游標失控、永遠有下一頁」時的無限請求，超過就停下並說結果不完整（人仍可按「載入更多」繼續）。
 */
export const SI_AUTO_LOAD_MAX_PAGES = 20;

/** 對帳面板一次取回的稽核列筆數（backend 預設 100、上限 500；回應 `truncated` 為真時面板說明尚有更舊的列未載入）。 */
export const SI_CONSOLE_WRITES_LIMIT = 100;

/**
 * SI 的 reason 常數（與凍結的 Architecture §11.1〈SelfImproving 相關的 reason〉表逐字一致，lib/domain/si.test.ts 解析該表比對；P2b 起五個：
 * 表中 `si_` 起頭的全部列）。刻意不放進 lib/api/reasons.ts 的 REASONS：REASONS 與凍結契約附錄 B 雙向鎖，多一個前端常數＝reasons.test.ts 紅（R19、⚖11）。
 * 422 `invalid_request` 是輸入閘與 Bridge 層共用的 reason（backend 的輸入閘直接回它；Bridge 的 422 則以 details.bridgeReason 帶出、頂層 reason 是 BRIDGE_REJECTED），
 * 所以不在這裡。
 */
export const SI_REASONS = {
  UNAVAILABLE: "si_unavailable",
  NOT_FOUND: "si_not_found",
  /** backend 端或 Bridge 端的寫入面停用（金鑰、權杖或稽核目錄未設）：503，`details.cause` 說明缺哪一項。 */
  WRITE_DISABLED: "si_write_disabled",
  /** 帳號不在 backend 的 `console.si.deciders` 名單（或 Bridge 的權杖不符）：403。 */
  WRITE_FORBIDDEN: "si_write_forbidden",
  /** 稽核目錄已有同名 `<audit_ref>.json`（不覆寫）：409。 */
  AUDIT_EXISTS: "si_audit_exists",
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

// ── 狀態快篩（觀察、提案各一組 pill；把處置／狀態的細枚舉折成「未結、延後、已完成」這種一眼看懂的幾類）────────────

/** 觀察的狀態類別：`open`＝未結、`deferred`＝延後、`done`＝已完成（其餘所有終值）。 */
export type ObsStatusClass = "open" | "deferred" | "done";

/**
 * 觀察處置→狀態類別，依 `dispositionKey` 的首詞：`open`→未結、`deferred`→延後，其餘終值（fixed、DEF-*、retired、decided、merged、proposed…）→已完成。
 * 首詞為空字串（處置欄空白）不是終值：歸未結，不得算成已完成——「已完成」只放真的有終值的列，寧可多列一筆在未結，也不宣稱一筆沒處置的列已完成。
 */
export function obsStatusClass(disposition: string): ObsStatusClass {
  const key = dispositionKey(disposition);
  if (key === "" || key === "open") return "open";
  return key === "deferred" ? "deferred" : "done";
}

/** 提案的狀態類別：`pending`＝待決（等人決定）、`active`＝進行中、`done`＝已完成；`unknown`＝不在已登記的狀態字串內。 */
export type PropStatusClass = "pending" | "active" | "done" | "unknown";

/** 待決＝等人看卡面下決定；進行中＝已有決定、流程還在走（退回待改、已核准、沙盒中、已晉升、量測採納中）；已完成＝已有終局。 */
const PROP_STATUS_BY_STATE: Readonly<Record<string, Exclude<PropStatusClass, "unknown">>> = {
  proposed: "pending",
  verified: "pending",
  returned: "active",
  approved: "active",
  sandboxed: "active",
  promoted: "active",
  measuring: "active",
  rejected: "done",
  "handed-off": "done",
  closed: "done",
  retired: "done",
};

/**
 * 提案狀態→類別。表外的字串回 `unknown`，而 `filterProposals` 讓 `unknown` 在任何快篩下都照常顯示：根層日後多一個狀態而這張表還沒跟上時，
 * 那筆提案要看得到（連同它的狀態字串），不能因為沒歸類就被快篩悄悄藏起來。
 */
export function propStatusClass(state: string): PropStatusClass {
  return Object.prototype.hasOwnProperty.call(PROP_STATUS_BY_STATE, state) ? PROP_STATUS_BY_STATE[state] : "unknown";
}

/** 快篩的值：空字串＝全部（不篩）。提案沒有「unknown」這顆 pill——它只作歸類結果，不是可選的篩選條件。 */
export type ObsStatusFilter = "" | ObsStatusClass;
export type PropStatusFilter = "" | Exclude<PropStatusClass, "unknown">;

/** pill 選項（順序＝顯示順序；第一顆「全部」＝不篩）。 */
export const OBS_STATUS_OPTIONS: ReadonlyArray<{ id: ObsStatusFilter; label: string }> = [
  { id: "", label: "全部" },
  { id: "open", label: "未結" },
  { id: "deferred", label: "延後" },
  { id: "done", label: "已完成" },
];
export const PROPOSAL_STATUS_OPTIONS: ReadonlyArray<{ id: PropStatusFilter; label: string }> = [
  { id: "", label: "全部" },
  { id: "pending", label: "待決" },
  { id: "active", label: "進行中" },
  { id: "done", label: "已完成" },
];

// ── 篩選（R17；多個條件為「且」，先分頁後篩選）──────────────────────────────────

/** 空字串＝該條件不篩（控制項的「全部」）。`status` 是狀態快篩（pill），其餘是下拉。 */
export type ObsFilters = { category: string; severity: string; disposition: string; bucket: string; window: DateWindow; status: ObsStatusFilter };
export const EMPTY_OBS_FILTERS: ObsFilters = { category: "", severity: "", disposition: "", bucket: "", window: "all", status: "" };

/**
 * 觀察列篩選：無法解析的壞列（valid 為 false）在任何篩選下都保留；時間無法解析者不被時間窗篩掉；
 * 模組桶只認資料自帶的 `buckets`（含所選值才符合），沒有 `buckets` 欄的列不符合任何選定的桶——前端不自證據座標文字歸桶。
 * 狀態快篩依 `obsStatusClass`，與其他條件取交集。
 */
export function filterObservations(items: ReadonlyArray<SiObservationRow>, filters: Partial<ObsFilters>, anchorIso: string | null | undefined): SiObservationRow[] {
  const f = { ...EMPTY_OBS_FILTERS, ...filters };
  return items.filter((row) => {
    if (isInvalidRow(row)) return true;
    if (f.category && row.category !== f.category) return false;
    if (f.severity && row.severity !== f.severity) return false;
    if (f.disposition && dispositionKey(row.disposition) !== f.disposition) return false;
    if (f.status && obsStatusClass(row.disposition) !== f.status) return false;
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

/** `state` 是依狀態字串精確篩的下拉，`status` 是狀態快篩（pill；依 `propStatusClass` 的類別）。 */
export type ProposalFilters = { state: string; cls: string; status: PropStatusFilter };
export const EMPTY_PROPOSAL_FILTERS: ProposalFilters = { state: "", cls: "", status: "" };

/**
 * 提案篩選：`狀態`（state）、`類別`（cls）與狀態快篩（status），取交集；提案沒有時間窗。
 * 狀態不在 `propStatusClass` 表內（`unknown`）的提案不受狀態快篩影響、照常顯示（見 `propStatusClass` 的說明）；它仍受 `state` 與 `cls` 兩個下拉篩選。
 */
export function filterProposals(items: ReadonlyArray<SiProposal>, filters: Partial<ProposalFilters>): SiProposal[] {
  const f = { ...EMPTY_PROPOSAL_FILTERS, ...filters };
  return items.filter((p) => {
    if (f.state && p.state !== f.state) return false;
    if (f.cls && p.cls !== f.cls) return false;
    if (f.status) {
      const status = propStatusClass(p.state);
      if (status !== "unknown" && status !== f.status) return false;
    }
    return true;
  });
}

// ── 快篩旁的筆數（「符合 N／已載入 M」）──────────────────────────────────────────

/**
 * `loaded`＝已載入的全部列（與分頁標籤的筆數同數）；`pinned`＝目前顯示、但不論篩選都照常顯示而無法歸類的列（壞列、狀態未登記的提案）；
 * `matched`＝顯示的列扣掉 `pinned`，也就是真的符合篩選的列。三者分開算，所以「符合 N」不會把照常顯示的壞列算成符合。
 */
export type FilterCounts = { matched: number; pinned: number; loaded: number };

export function filterCounts<T>(loaded: ReadonlyArray<T>, shown: ReadonlyArray<T>, isPinned: (item: T) => boolean): FilterCounts {
  const pinned = shown.filter(isPinned).length;
  return { matched: shown.length - pinned, pinned, loaded: loaded.length };
}

/** 「符合 N／已載入 M」；有照常顯示的列時加註一句（`pinnedLabel`＝那一類列的說法，例「無法解析的列」）。 */
export function filterCountText(counts: FilterCounts, pinnedLabel: string): string {
  const base = `符合 ${counts.matched}／已載入 ${counts.loaded}`;
  return counts.pinned > 0 ? `${base}（另有 ${counts.pinned} 筆${pinnedLabel}照常顯示）` : base;
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

// ══ 寫入面（P2b；TCS-SelfImprovingDecide-P2b W17；欄位與值域＝§5.2 表 M-V、M-D、M-O、M-C）══════════════════════════════
// 與 backend 的 SiWriteGates 同一張表：前端先擋（不讓使用者送出必被拒的本文）、backend 仍為權威（AT-950-9-2 逐列對拍）。
// 前端**不重算**入帳時才判的東西：卡面 digest 新鮮度、PROP 狀態前提、`retired` 的座標、`corrects` 是否存在（⚖15）。

/** 欄位名→錯誤訊息；空物件＝通過。欄位名同 backend 的 `details.violations[].field`（camelCase）。 */
export type FieldErrors = Record<string, string>;

export const SI_REASON_CLASSES = ["證據不足", "風險過高", "工件類別錯", "已被涵蓋", "範圍外", "卡面不清", "未說明"] as const;
export const SI_CATEGORIES = ["process", "bug", "tooling", "doc", "decision"] as const;
export const SI_SEVERITIES = ["P1", "P2", "P3", "P4"] as const;
export const SI_FACES = ["守衛", "產品", "文件", "流程"] as const;
export const SI_EXPOSURES = ["a", "b", "c", "無"] as const;
/** 關閉觀察的七個終值（沒有 `open`：open 是新增列時的初始處置，不是終值）。 */
export const SI_TERMINALS = ["fixed", "def", "deferred", "retired", "decided", "merged", "proposed"] as const;

export const SI_REASON_MAX = 500;
export const SI_OBS_FIELD_MAX = 300;
/** 三個觀察字串欄的 UTF-8 位元組和上限（必要條件；權威是預檢與根層 CLI 的列位元組上限）。 */
export const SI_OBS_BYTES_MAX = 700;
export const SI_CLOSE_TEXT_MAX = 120;
/** 預檢尚未回來時顯示的列位元組上限（根層協定參數檔的現值，⚖26）；預檢回來後以回應的 `rowMaxBytes` 為準。 */
export const SI_ROW_MAX_DEFAULT = 700;

/** C0 控制字元（U+0000～U+001F）、DEL（U+007F）與孤立的代理字元；`u` 旗標下成對的代理字元是一個合法字元，不會被比對到。 */
const FORBIDDEN_CHARS = /[\u0000-\u001f\u007f\ud800-\udfff]/u;
const DIGEST_PATTERN = /^sha256:[0-9a-f]{64}$/;
const GIT_REF_PATTERN = /^[0-9a-f]{7,40}$/;
const DEF_ID_PATTERN = /^DEF-[0-9]+-[0-9]+$/;
const OBS_ID_PATTERN = /^OBS-SI-[0-9]{3,}$/;
const PROP_ID_PATTERN = /^PROP-SI-[0-9]{3,}$/;
/** 處置文字不得含的空泛說法（根層 `check` 會把含它的列轉紅；PRD AC-SI-35-2）。 */
const VAGUE_DISPOSITION = "之後再看";

export function hasForbiddenChar(text: string): boolean {
  return FORBIDDEN_CHARS.test(text);
}

/** 以 code point 計的長度（與 backend 的 `codePointCount` 同義；CJK 與表情符號各算 1）。 */
export function codePointLength(text: string): number {
  return Array.from(text).length;
}

/** UTF-8 位元組數。 */
export function utf8Bytes(text: string): number {
  return new TextEncoder().encode(text).length;
}

/**
 * 字串欄的通則（與 backend 的 `text()` 同序）：先判原值（所以首尾的換行也拒收，不是靜默剝除）有無控制字元；去前後空白後不可為空；
 * `forbidPipe` 時不可含 `|`（觀察列是 Markdown 九欄表）；長度以 code point 計。回錯誤訊息，通過回 null。
 */
function textProblem(label: string, raw: string, opts: { max: number; forbidPipe?: boolean }): string | null {
  if (hasForbiddenChar(raw)) return `${label} 不可含控制字元（換行、TAB 等）或無效字元`;
  const value = raw.trim();
  if (value === "") return `${label} 為必填（不可全為空白）`;
  if (opts.forbidPipe && value.includes("|")) return `${label} 不可含豎線 |（觀察列是 Markdown 九欄表）`;
  const length = codePointLength(value);
  if (length > opts.max) return `${label} 為 ${length} 個字元，超過上限 ${opts.max}`;
  return null;
}

// ── 決定（表 M-V、M-D）────────────────────────────────────────────────────────────────────

/** 動詞選項：`label` 是給人看的字樣，`dkind` 是送出的值，`needsAck`＝晉升後式（verdict 為 NE 的晉升，須勾選已知悉未驗採納）。 */
export type DecideVerb = { label: string; dkind: SiDecideKind; needsAck: boolean };

/**
 * 決定卡的輸入：提案物件的 `state`、`route`、`verdict`、`cooldown`，或狀態橫幅的 `suspended`（給了 `suspended` 就只看它，不看提案欄位）。
 * 全部是 export 原樣的值：`verdict` 為 `"PASS"`｜`"FAIL"`｜`"NE"`｜null，`cooldown` 在冷卻中為物件、已解除為 null。
 */
export type DecideCard = { state?: string; route?: string; verdict?: unknown; cooldown?: unknown; suspended?: unknown };

const POST_PROMOTE_STATES: ReadonlySet<string> = new Set(["promoted", "measuring", "closed"]);

function verb(label: string, dkind: SiDecideKind, needsAck = false): DecideVerb {
  return { label, dkind, needsAck };
}

/** 橫幅 `suspended`（`null` 或 `{ run }`）的運轉號；不是帶字串 `run` 的物件回 null（量不到或沒有暫停）。 */
export function suspendedRun(suspended: unknown): string | null {
  if (typeof suspended !== "object" || suspended === null || Array.isArray(suspended)) return null;
  const run = (suspended as { run?: unknown }).run;
  return typeof run === "string" && run !== "" ? run : null;
}

/**
 * 某張卡此刻可下的決定（表 M-V；順序＝畫面順序、**預設不選**，沒有批次或全部核准）。表外的組合一律回空（沒有控件）：
 * 前端不替根層猜前提——例如 verdict 為 NE 的卡不提供「退回」（提案資料沒有 NE 的原因碼，⚖12），`rollback` 與 `unblock` 不看 route 與 verdict
 * （根層 `transition_of` 也不看）。晉升的 `needsAck` 只在 verdict 為 NE。
 */
export function decideVerbOptions(card: DecideCard): DecideVerb[] {
  if (card.suspended !== undefined) return suspendedRun(card.suspended) ? [verb("恢復", "resume")] : [];
  const { state, route, verdict, cooldown } = card;
  switch (state) {
    case "proposed":
      if (route === "loop") return [verb("核准", "approve"), verb("否決", "reject"), verb("退回", "return")];
      if (typeof route === "string" && route.startsWith("handoff:")) return [verb("轉交", "ack-handoff"), verb("不轉交", "reject"), verb("退回", "return")];
      return [];
    case "verified":
      if (verdict === "PASS") return [verb("晉升", "promote"), verb("不晉升", "decline-promote")];
      if (verdict === "NE") return [verb("晉升（未驗採納）", "promote", true), verb("不晉升", "decline-promote")];
      if (verdict === "FAIL") return [verb("退回", "return"), verb("不晉升", "decline-promote")];
      return [];
    case "rejected":
      return cooldown !== null && cooldown !== undefined ? [verb("解除", "unblock")] : [];
    default:
      return state !== undefined && POST_PROMOTE_STATES.has(state) ? [verb("回滾", "rollback")] : [];
  }
}

/** 九個動詞各自要的欄位（表 M-D 的「必填欄」；沒列的欄位＝禁止欄，送了 backend 回 422）。 */
export type DecideFields = { digest: boolean; reason: boolean; reasonClass: boolean };
export const DECIDE_FIELDS: Readonly<Record<SiDecideKind, DecideFields>> = {
  approve: { digest: true, reason: false, reasonClass: false },
  reject: { digest: true, reason: true, reasonClass: true },
  return: { digest: true, reason: true, reasonClass: true },
  promote: { digest: true, reason: false, reasonClass: false },
  "decline-promote": { digest: true, reason: true, reasonClass: true },
  rollback: { digest: false, reason: true, reasonClass: false },
  unblock: { digest: false, reason: false, reasonClass: false },
  resume: { digest: false, reason: true, reasonClass: false },
  "ack-handoff": { digest: true, reason: false, reasonClass: false },
};

export function isDecideKind(value: string): value is SiDecideKind {
  return Object.prototype.hasOwnProperty.call(DECIDE_FIELDS, value);
}

/** 決定表單的狀態（全是字串，空字串＝沒填）；`digest` 是開啟當下綁定的卡面值（resume 為空）。 */
export type DecideForm = { dkind: string; digest: string; reason: string; reasonClass: string; unverifiedAck: boolean };

/**
 * 決定表單的驗證（與 backend 同表）：動詞未選＝`dkind` 錯；必填欄缺或格式錯、禁止欄有填、晉升後式未勾選各自回該欄的訊息。
 * `needsAck`＝這個動詞是 verdict 為 NE 的晉升後式（來自 `decideVerbOptions` 的選項）：只有它可（且必須）勾選 `unverifiedAck`。
 */
export function validateDecideForm(form: DecideForm, opts: { needsAck?: boolean } = {}): FieldErrors {
  const errors: FieldErrors = {};
  if (!isDecideKind(form.dkind)) {
    errors.dkind = "請選擇決定動詞";
    return errors;
  }
  const need = DECIDE_FIELDS[form.dkind];
  if (need.digest) {
    if (form.digest === "") errors.digest = "digest 為必填（開啟決定時綁定的卡面 digest）";
    else if (!DIGEST_PATTERN.test(form.digest)) errors.digest = "digest 須為 sha256: 加 64 位小寫十六進位";
  } else if (form.digest !== "") errors.digest = `digest 在 ${form.dkind} 不可填`;
  if (need.reason) {
    const problem = textProblem("理由", form.reason, { max: SI_REASON_MAX });
    if (problem) errors.reason = problem;
  } else if (form.reason.trim() !== "") errors.reason = `理由在 ${form.dkind} 不可填`;
  if (need.reasonClass) {
    if (form.reasonClass === "") errors.reasonClass = "理由類別為必填";
    else if (!(SI_REASON_CLASSES as readonly string[]).includes(form.reasonClass)) errors.reasonClass = `理由類別須為 ${SI_REASON_CLASSES.join("、")} 之一`;
  } else if (form.reasonClass !== "") errors.reasonClass = `理由類別在 ${form.dkind} 不可填`;
  const ackAllowed = form.dkind === "promote" && opts.needsAck === true;
  if (ackAllowed && !form.unverifiedAck) errors.unverifiedAck = "verdict 為 NE 的晉升須勾選「已知悉此提案未經驗證即採納」";
  else if (!ackAllowed && form.unverifiedAck) errors.unverifiedAck = "只有 verdict 為 NE 的晉升可勾選未驗採納";
  return errors;
}

/** 由（已通過驗證的）表單組請求本文：只帶該動詞的欄位（鍵序 dkind、digest、reason、reasonClass、unverifiedAck），字串欄去前後空白。 */
export function buildDecideRequest(form: DecideForm): SiDecideRequest {
  if (!isDecideKind(form.dkind)) throw new Error(`未知的決定動詞：${form.dkind}`);
  const need = DECIDE_FIELDS[form.dkind];
  const body: SiDecideRequest = { dkind: form.dkind };
  if (need.digest) body.digest = form.digest;
  if (need.reason) body.reason = form.reason.trim();
  if (need.reasonClass) body.reasonClass = form.reasonClass as NonNullable<SiDecideRequest["reasonClass"]>;
  if (form.dkind === "promote" && form.unverifiedAck) body.unverifiedAck = true;
  return body;
}

// ── 新增觀察（表 M-O）────────────────────────────────────────────────────────────────────

/** 觀察表單的狀態（字串欄空字串＝沒填；`exposure`、`corrects` 空＝不送）。 */
export type ObservationForm = {
  context: string;
  symptom: string;
  evidence: string;
  category: string;
  severity: string;
  face: string;
  exposure: string;
  externalDerived: boolean;
  corrects: string;
};

export const EMPTY_OBSERVATION_FORM: ObservationForm = { context: "", symptom: "", evidence: "", category: "", severity: "", face: "", exposure: "", externalDerived: false, corrects: "" };

/** 守衛面才有暴露度（根層：`face` 為守衛時 `exposure` 必填，否則禁止）。 */
export const GUARD_FACE = "守衛";

function oneOfProblem(label: string, value: string, allowed: ReadonlyArray<string>): string | null {
  if (value === "") return `${label} 為必填`;
  return allowed.includes(value) ? null : `${label} 須為 ${allowed.join("、")} 之一`;
}

/**
 * 觀察表單的驗證（與 backend 同表；一次回報全部違規）：三個字串欄各 1～300 個 code point、不得含豎線與控制字元、UTF-8 位元組和不得超過 700
 * （必要條件，違反時三欄一併標示）；三個列舉必選；`exposure` 只有 `face` 為守衛時必填、否則禁止；`corrects`（選填）須為 `OBS-SI-` 接三位以上數字。
 */
export function validateObservationForm(form: ObservationForm): FieldErrors {
  const errors: FieldErrors = {};
  const labels = { context: "情境", symptom: "症狀", evidence: "證據座標" } as const;
  for (const key of ["context", "symptom", "evidence"] as const) {
    const problem = textProblem(labels[key], form[key], { max: SI_OBS_FIELD_MAX, forbidPipe: true });
    if (problem) errors[key] = problem;
  }
  if (!errors.context && !errors.symptom && !errors.evidence) {
    const bytes = utf8Bytes(form.context.trim()) + utf8Bytes(form.symptom.trim()) + utf8Bytes(form.evidence.trim());
    if (bytes > SI_OBS_BYTES_MAX) {
      const message = `情境、症狀、證據座標三欄的 UTF-8 位元組和為 ${bytes}，超過 ${SI_OBS_BYTES_MAX}（入帳列還有其他欄位，實際上限更低；以預檢為準）`;
      errors.context = message;
      errors.symptom = message;
      errors.evidence = message;
    }
  }
  const category = oneOfProblem("分類", form.category, SI_CATEGORIES);
  if (category) errors.category = category;
  const severity = oneOfProblem("嚴重度", form.severity, SI_SEVERITIES);
  if (severity) errors.severity = severity;
  const face = oneOfProblem("面", form.face, SI_FACES);
  if (face) errors.face = face;
  if (form.face === GUARD_FACE) {
    if (form.exposure === "") errors.exposure = "面為守衛時暴露度為必填（a、b、c 或 無）";
    else if (!(SI_EXPOSURES as readonly string[]).includes(form.exposure)) errors.exposure = `暴露度須為 ${SI_EXPOSURES.join("、")} 之一`;
  } else if (form.exposure !== "" && !errors.face) {
    errors.exposure = "暴露度只有面為守衛時可填";
  }
  if (form.corrects.trim() !== "") {
    if (hasForbiddenChar(form.corrects)) errors.corrects = "被更正的觀察號不可含控制字元（換行、TAB 等）或無效字元";
    else if (!OBS_ID_PATTERN.test(form.corrects.trim())) errors.corrects = "被更正的觀察號須為 OBS-SI-<三位以上數字>";
  }
  return errors;
}

/** 由（已通過驗證的）表單組請求本文：字串欄去前後空白；`exposure` 只在守衛面帶、`corrects` 只在有填時帶（鍵序同黃金檔）。 */
export function buildObservationRequest(form: ObservationForm): SiObservationRequest {
  const body = {
    context: form.context.trim(),
    symptom: form.symptom.trim(),
    evidence: form.evidence.trim(),
    category: form.category,
    severity: form.severity,
    face: form.face,
    ...(form.face === GUARD_FACE && form.exposure !== "" ? { exposure: form.exposure } : {}),
    externalDerived: form.externalDerived,
    ...(form.corrects.trim() !== "" ? { corrects: form.corrects.trim() } : {}),
  };
  return body as SiObservationRequest;
}

/** 位元組估計的情境：`user` 是登入帳號（寫進標記欄的回報者）；`obsDigits` 是下一個 OBS 號的位數（預設 3，⚖26）。 */
export type RowEstimateContext = { user: string; obsDigits?: number };

/** 估計用的固定寬度佔位：時間格 `YYYY-MM-DD HH:MM ±HH:MM`、`audit_ref` 為 36 字元的 UUID（寬度與真值相同，內容不是）。 */
const ESTIMATE_TIME_CELL = "0000-00-00 00:00 +00:00";
const ESTIMATE_AUDIT_REF = "00000000-0000-4000-8000-000000000000";

/**
 * 入帳列的位元組估計（僅供提示，⚖26；權威是預檢與根層 CLI 的列位元組上限）：與 CLI 同一九欄組列規則——
 * `| OBS-SI-<NNN> | <時間格> | <情境> | <症狀> | <證據> | <分類> | <嚴重度> | open | <標記> |`，標記欄＝`面=<面>`、守衛加 `暴露=<x>`、外部衍生加 `外部衍生=是`、
 * 更正加 `rel=corrects:<ID>`，接 `來源=人;回報者=<帳號>;carrier=console;audit_ref=<UUID>`（以真 CLI 的 dry-run 逐例對過，AT-950-9-3）。
 * 三個字串欄含 `|` 或控制字元＝這份輸入必被拒收，回 null（不給估計值，免得把必敗的輸入估成「還行」）。
 */
export function estimateRowBytes(form: ObservationForm, ctx: RowEstimateContext): number | null {
  const fields = [form.context, form.symptom, form.evidence];
  if (fields.some((value) => hasForbiddenChar(value) || value.includes("|"))) return null;
  const marks = [
    `面=${form.face}`,
    ...(form.face === GUARD_FACE && form.exposure !== "" ? [`暴露=${form.exposure}`] : []),
    ...(form.externalDerived ? ["外部衍生=是"] : []),
    ...(form.corrects.trim() !== "" ? [`rel=corrects:${form.corrects.trim()}`] : []),
    "來源=人",
    `回報者=${ctx.user}`,
    "carrier=console",
    `audit_ref=${ESTIMATE_AUDIT_REF}`,
  ].join(";");
  const cells = [`OBS-SI-${"0".repeat(ctx.obsDigits ?? 3)}`, ESTIMATE_TIME_CELL, ...fields.map((v) => v.trim()), form.category, form.severity, "open", marks];
  return utf8Bytes(`| ${cells.join(" | ")} |`);
}

// ── 關閉觀察（表 M-C）────────────────────────────────────────────────────────────────────

/** 關閉表單的狀態：`ref` 與 `text` 依終值恰擇一（空字串＝沒填）。 */
export type CloseForm = { terminal: string; ref: string; text: string };

/** 帶 `ref` 的終值（格式依終值）與帶 `text` 的終值。 */
const REF_TERMINALS: ReadonlySet<string> = new Set(["fixed", "def", "merged", "proposed"]);

export function terminalTakesRef(terminal: string): boolean {
  return REF_TERMINALS.has(terminal);
}

const REF_RULES: Readonly<Record<string, { pattern: RegExp; hint: string }>> = {
  fixed: { pattern: GIT_REF_PATTERN, hint: "7～40 碼小寫十六進位（提交編號）" },
  def: { pattern: DEF_ID_PATTERN, hint: "DEF-<數字>-<數字>" },
  merged: { pattern: OBS_ID_PATTERN, hint: "OBS-SI-<三位以上數字>" },
  proposed: { pattern: PROP_ID_PATTERN, hint: "PROP-SI-<三位以上數字>" },
};

/** 關閉對話框中某終值的 `ref` 提示字樣（placeholder 與說明用）。 */
export function closeRefHint(terminal: string): string {
  return REF_RULES[terminal]?.hint ?? "";
}

/**
 * 關閉表單的驗證（與 backend 同表）：終值必選且不得為 `open`；fixed、def、merged、proposed 要 `ref`（格式依終值）且不可填 `text`；
 * deferred、retired、decided 要 `text`（1～120 個 code point、不含豎線、控制字元與「之後再看」）且不可填 `ref`。
 */
export function validateCloseForm(form: CloseForm): FieldErrors {
  const errors: FieldErrors = {};
  if (form.terminal.trim() === "open") {
    errors.terminal = "終值不可為 open（open 是新增列時的初始處置，不是終值）";
    return errors;
  }
  if (form.terminal === "") {
    errors.terminal = "請選擇終值";
    return errors;
  }
  if (!(SI_TERMINALS as readonly string[]).includes(form.terminal)) {
    errors.terminal = `終值須為 ${SI_TERMINALS.join("、")} 之一`;
    return errors;
  }
  if (terminalTakesRef(form.terminal)) {
    if (form.text !== "") errors.text = `文字在 ${form.terminal} 不可填`;
    const problem = textProblem("參照", form.ref, { max: 64 });
    if (problem) errors.ref = problem;
    else if (!REF_RULES[form.terminal].pattern.test(form.ref.trim())) errors.ref = `參照須為 ${REF_RULES[form.terminal].hint}`;
  } else {
    if (form.ref !== "") errors.ref = `參照在 ${form.terminal} 不可填`;
    const problem = textProblem("文字", form.text, { max: SI_CLOSE_TEXT_MAX, forbidPipe: true });
    if (problem) errors.text = problem;
    else if (form.text.includes(VAGUE_DISPOSITION)) errors.text = `文字不可含「${VAGUE_DISPOSITION}」（空泛的處置不算處置）`;
  }
  return errors;
}

/** 由（已通過驗證的）表單組請求本文：`{ terminal, ref }` 或 `{ terminal, text }`（去前後空白）。 */
export function buildCloseRequest(form: CloseForm): SiCloseRequest {
  const terminal = form.terminal as SiCloseRequest["terminal"];
  return terminalTakesRef(form.terminal) ? { terminal, ref: form.ref.trim() } : { terminal, text: form.text.trim() };
}

// ── 入帳指令、待入帳與錯誤文案 ───────────────────────────────────────────────────────────

/** 入帳指令：PowerShell 與 POSIX 兩段字串**相同**（`python` 與正斜線路徑在兩個 shell 都成立；於 monorepo 根、已設主機端 `AUTOSDD_SI_AUDIT_KEY` 的 shell 執行，金鑰不出現在指令）。 */
export type IngestCommands = { powershell: string; posix: string };

/**
 * 由稽核檔收據組入帳指令（pull 模式：Console 只把稽核檔落進目錄，由掌舵者在主機端以根層 CLI 入帳）。
 * decide 帶 PROP 號（resume 為 RUN 號）；obs-add 與 obs-close 的對象在稽核檔內，指令不帶。
 */
export function ingestCommands(kind: SiWriteKind, subject: string | null | undefined, auditRef: string): IngestCommands {
  const base = "python tools/selfimproving.py";
  const tail = `--carrier console --audit-ref ${auditRef}`;
  const command = kind === "decide" ? `${base} decide ${subject ?? "<PROP-SI-NNN>"} ${tail}` : `${base} ${kind} ${tail}`;
  return { powershell: command, posix: command };
}

const SI_WRITE_KIND_LABELS: Readonly<Record<SiWriteKind, string>> = { decide: "決定", "obs-add": "新增觀察", "obs-close": "關閉觀察" };

/** 寫入種類的人話（畫面上與原值並列，不取代原值）。 */
export function siWriteKindLabel(kind: SiWriteKind): string {
  return SI_WRITE_KIND_LABELS[kind];
}

/** 對帳面板的「對象」欄：obs-add 在入帳前沒有列號（null），顯示破折號。 */
export function writeSubjectText(subject: string | null | undefined): string {
  return subject === null || subject === undefined || subject === "" ? "—" : subject;
}

/**
 * 待入帳的稽核列：只回 `ingested` 為 false 者（null＝對帳量不到、true＝已入帳都不回），依 `time` 升冪（最久未入帳的在前；同刻依 auditRef）。
 * 量不到時不得當成「沒有待入帳」——呼叫端另以 `reconcile.status` 判斷（NOT-EVALUABLE 時整個清單不可信）。
 */
export function pendingWrites(items: ReadonlyArray<SiConsoleWrite>): SiConsoleWrite[] {
  const stamp = (item: SiConsoleWrite) => {
    const ms = Date.parse(item.time);
    return Number.isNaN(ms) ? 0 : ms;
  };
  return items.filter((item) => item.ingested === false).sort((a, b) => stamp(a) - stamp(b) || (a.auditRef < b.auditRef ? -1 : a.auditRef > b.auditRef ? 1 : 0));
}

/**
 * 寫入失敗的一句話（toast 用；各部分以「；」相接，因為 toast 不保留換行）：`describeError` 的主訊息加 reason 逐字（含 traceId）；
 * 422 另列每筆 violation 的 `欄位：訊息`（取 `details.violations`，沒有時退回頂層 `errors[]`）；503 `si_unavailable` 另列 cause 與 detail 逐字。
 */
export function siWriteErrorText(error: unknown): string {
  const parts = [describeError(error)];
  if (error instanceof ApiError) {
    const violations = error.details?.violations;
    const listed = Array.isArray(violations)
      ? violations.flatMap((v) => (typeof v === "object" && v !== null && typeof (v as { message?: unknown }).message === "string" ? [v as { field?: unknown; message: string }] : []))
      : error.errors;
    if (error.status === 422) for (const v of listed) parts.push(typeof v.field === "string" && v.field !== "" ? `${v.field}：${v.message}` : v.message);
    if (error.status === 503 && error.reason === SI_REASONS.UNAVAILABLE) {
      const { cause, detail } = siErrorParts(error);
      if (cause) parts.push(`cause：${cause}`);
      if (detail) parts.push(`detail：${detail}`);
    }
  }
  return parts.join("；");
}
