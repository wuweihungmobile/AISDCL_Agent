/**
 * 自我進化「核准流程全程可見」的純函式庫（TCS-SiFlowVisibility-20261111 AC-966-5、W-F5～W-F14、C-5）。
 *
 * 設計要點（為什麼這樣做）：
 *  - 純函式：不讀時鐘、不讀 DOM、不 import React 與任何 `lib/api/*`（AT-966-14-3 靜態鎖）；時間一律由呼叫端傳入。
 *  - Console 不持有任何「原因碼→白話」對照表：白話字一律逐字取自主機給的 `text` 欄（W-F7），缺席時才用保底句（含原因碼原文）。
 *    Console 只持有少數固定列舉的標籤（運轉目的第一波三值、驗證結果三值、入帳狀態兩值）與等待對象五值的「是否屬於」判定。
 *  - 量不到（缺席、null、錯型別）與「無」（空陣列、空字串）一律分開（NFR-FV-3）；任何輸入都不得漏出 null、undefined、NaN、[object Object]。
 *  - 所有固定句、標籤、保底句模板住 `SI_FLOW_TEXTS`（元件只取用，不自寫句子；AT-966-15-2）。
 */

/** 新鮮度：過時門檻＝2×心跳分鐘＋5（嚴格大於才過時）。 */
export const STALE_FACTOR = 2;
export const STALE_GRACE_MINUTES = 5;
/** diff 預設視窗行數。 */
export const DIFF_WINDOW_LINES = 400;
/** 待入帳面板「最近已入帳」最多列幾筆。 */
export const RECENT_INGESTED_SHOWN = 5;
/** 快照時間比讀取時間晚超過這麼多分鐘＝時鐘異常。 */
export const CLOCK_SKEW_MINUTES = 5;

/**
 * 版面分支鍵（TCS 勘誤 E-20；W-F7 的唯一例外）：Console 不列舉原因碼，唯有這兩個 `ne` 碼決定「是否顯示提示區塊」
 * （來源觀察帳本讀不到、時間線被截短——根層 §2.1 沒有可取代的結構欄位）。封閉、只減不增；白話仍逐字取主機的 `text`；
 * 與 Bridge 的 `filter_detail` 同步修訂。前端原始碼的其餘原因碼字面由 AT-966-14-3 的靜態掃描擋下。
 */
export const LAYOUT_BRANCH_CODES = ["OBS-LEDGER-UNREADABLE", "TIMELINE-TRUNCATED"] as const;
export const [CODE_SOURCE_LEDGER_UNREADABLE, CODE_TIMELINE_TRUNCATED] = LAYOUT_BRANCH_CODES;

type Rec = Record<string, unknown>;
const isRec = (v: unknown): v is Rec => typeof v === "object" && v !== null && !Array.isArray(v);
/** 非空字串才回字串，其餘 null。 */
const str = (v: unknown): string | null => (typeof v === "string" && v !== "" ? v : null);
const MS_MIN = 60_000;

// ── 固定文字（單一出處；含 {名稱} 的是模板，用 `fillText` 代入）────────────────────────────────
export const SI_FLOW_TEXTS = {
  unmeasurable: "量不到",
  noReason: "主機沒有提供原因。",
  noPlainText: "主機沒有提供白話說明（原因碼 {code}）。",
  unknownValue: "未知值『{value}』",
  unknownResult: "未知結果『{value}』",
  objectPlaceholder: "[物件]",
  // 詳情對話框
  detailButton: "詳情",
  detailButtonLabelFmt: "詳情 {id}",
  detailTabsLabel: "提案詳情分頁",
  tabCard: "卡面",
  tabDiff: "變更內容",
  tabBody: "提案本文",
  tabVerify: "評估集與驗證",
  tabTimeline: "時間線",
  detailLoading: "提案詳情載入中…",
  detailNotFound: "查無這個提案",
  detailRetry: "重試",
  detailNotProvided: "這個根層版本還沒提供詳情（量不到）",
  detailTitleFmt: "提案詳情 {id}",
  detailLoadingWhat: "提案詳情",
  detailDescription: "提案的完整內容：變更內容、本文、評估集、驗證結果與時間線",
  srcSeverity: "嚴重度：",
  srcDisposition: "處置：",
  srcContext: "情境：",
  srcSymptom: "症狀：",
  cardMissing: "卡面量不到",
  cardNeNote: "對應的原因：",
  nextStepPrefix: "下一步：",
  nextStepNobody: "目前不需要任何人動作：",
  nextStepWaitFmt: "下一步：等{who}｜{text}",
  nextStepUnknown: "下一步：量不到",
  nextSourceSnapshot: "依巡邏回報",
  nextSourceLedger: "依帳本判斷",
  patrolMayBeDown: "巡邏可能沒在跑，這一步可能不會自動進行",
  // diff
  diffSummary: "新增 {add} 行、刪除 {del} 行",
  diffDownload: "下載 patch 檔",
  diffScroll: "變更內容的每一行（可捲動）",
  diffDownloadTruncatedNote: "這是截斷後的內容",
  diffTruncated: "內容過長已截斷，完整檔在 {rel}",
  diffExpand: "展開全部（{count} 行）",
  diffCollapse: "只看前 400 行",
  diffMissing: "變更內容量不到",
  diffEmpty: "這個提案沒有變更內容",
  diffPrefixAdd: "新增：",
  diffPrefixDel: "刪除：",
  diffPrefixHunk: "區段：",
  diffBytes: "{bytes} 位元組",
  // 提案本文與來源
  bodyMissing: "提案本文量不到",
  bodyEmpty: "這個提案沒有本文",
  sourcesTitle: "來源觀察",
  sourcesNone: "這個提案沒有登記來源觀察",
  sourcesUnknown: "來源量不到",
  sourceJump: "看觀察 {id}",
  sourceMissingRow: "找不到這筆觀察 {id}（觀察帳本裡沒有）",
  sourceNotLoaded: "找不到 {id}（可能在更舊的頁，請按『載入更多』）",
  // 評估集與驗證
  heldoutTitle: "評估集（用來驗證的考題）",
  heldoutUnfrozen: "還沒有凍結評估集",
  heldoutUnfrozenNote: "評估集要由人在主機上凍結，巡邏器不會自己建立；凍結前這個提案不會進行驗證",
  heldoutFrozenFmt: "已凍結：{n} 筆案例（下限 {min}），凍結者：{by}",
  heldoutFrozenNoMin: "已凍結：{n} 筆案例，凍結者：{by}",
  heldoutFrozenNoBy: "已凍結：{n} 筆案例",
  heldoutFrozenNoN: "已凍結，案例數量不明",
  heldoutUnknown: "評估集狀態量不到",
  heldoutBelowMinFallback: "案例數低於下限，驗證結果只能是『無法評估』",
  heldoutBelowMinNote: "這不會擋住凍結，只表示驗證結果不能當成通過",
  sandboxTitle: "隔離試跑（沙盒）",
  sandboxNone: "還沒有做隔離試跑",
  sandboxOk: "已套用修補、只動到允許的檔案、回滾正常",
  sandboxFailHeadline: "沒有通過：{code}",
  sandboxNoPlain: "（主機沒有提供白話說明）",
  sandboxFailNoCode: "沒有通過",
  sandboxFailFallback: "隔離試跑沒有通過：{code}（主機沒有提供白話說明）",
  sandboxApplied: "已套用修補",
  sandboxTouched: "只動到允許的檔案",
  sandboxRollback: "回滾正常",
  verifyTitle: "驗證結果",
  verifyNone: "還沒有驗證結果",
  verifyResultFmt: "結果：{label}",
  verifyStepBaseline: "修補前確實重現症狀",
  verifyStepPatched: "修補後症狀消失",
  verifyStepMutated: "故意弄壞修補後症狀又出現",
  verifyStepFailed: "這一步沒過",
  verifyProbes: "檢查項目（探針）：{n}",
  verifyCarrier: "驗證用的測量工具自我檢查",
  verifyReasonsTitle: "保留原因",
  verifyReasonsNoneKept: "沒有任何保留原因",
  verifyReasonsNoReport: "主機沒有回報原因",
  verifyReasonsMissing: "原因量不到",
  yes: "是",
  no: "否",
  pass: "通過",
  fail: "沒通過",
  // 時間線
  timelineCaption: "提案事件時間線",
  timelineEmpty: "這個提案還沒有事件",
  timelineMissing: "時間線量不到",
  timeMissing: "時間量不到",
  colSeq: "序號",
  colTime: "時間",
  colWho: "誰",
  colAction: "做了什麼",
  // 巡邏狀態卡
  patrolTitle: "巡邏狀態",
  patrolOk: "巡邏正常",
  patrolStaleLabel: "巡邏可能沒在跑",
  patrolPaused: "巡邏已暫停（環境變數 AUTOSDD_SI_PATROL_OFF 有設定）",
  patrolPauseUnknown: "量不到暫停狀態",
  patrolHeartbeat: "上次心跳：{ago}",
  patrolHeartbeatUnknown: "上次心跳時間量不到",
  patrolPeriod: "巡邏每 {n} 分鐘一次",
  patrolReadAt: "資料讀取於 {time}",
  patrolEstimated: "（用瀏覽器時間估算）",
  patrolNoPeriod: "無法判斷是否過時：快照沒有巡邏週期",
  patrolClockSkew: "快照時間在未來，電腦時鐘可能不同步",
  patrolStaleWarn: "巡邏可能沒在跑：已超過 {limit} 分鐘沒有新的回報（巡邏每 {period} 分鐘一次）。可能原因：電腦睡眠、排程任務被移除、巡邏被環境變數暫停。請按『重新整理』取得最新回報。",
  patrolStaleAgo: "以下是 {ago}的回報",
  patrolTruncated: "這份回報太長，被截短了，清單可能不完整",
  patrolMissingTitle: "還沒有收到巡邏回報",
  patrolMissingReasons: ["巡邏任務還沒安裝", "巡邏還沒跑過第一次", "主機的回報目錄是空的"],
  patrolMissingHint: "按『重新整理』再看一次",
  patrolUnmountedTitle: "這個部署沒有掛載巡邏回報目錄",
  patrolUnmountedNote: "看不到巡邏狀態，其他自我進化功能照常；要看請照部署說明加上回報目錄",
  patrolBadFileTitle: "巡邏回報檔有問題",
  patrolPropsTitle: "每個提案現在卡在哪",
  patrolPropsNone: "目前沒有需要巡邏推進的提案",
  patrolPropsMissing: "每個提案現在卡在哪量不到",
  propWaitFmt: "等：{who}",
  propWaitUnknownFmt: "等：{value}",
  propStateMissing: "狀態量不到",
  propsScroll: "提案卡住原因清單",
  runsTitle: "進行中的運轉",
  runsNone: "目前沒有進行中的運轉",
  runsMissing: "進行中的運轉量不到",
  runLiveHead: "進行中：{run}（{purpose}）。",
  runLiveTail: "{started}開始，預計最晚 {due}後結束。",
  runLiveTailDue: "{started}開始，已到預計結束時間。",
  scheduleTitle: "為什麼沒有啟動運轉",
  scheduleEnabled: "排程：啟用中",
  scheduleDisabled: "排程：已停用",
  scheduleEnabledUnknown: "排程：狀態量不到",
  scheduleCurrentFmt: "目前狀態：{text}",
  scheduleMissing: "排程狀態量不到",
  scheduleCurrentMissing: "目前這一格的排程狀態量不到",
  schedulePaused: "巡邏已暫停，沒有排程資訊",
  scheduleAbsent: "這份回報沒有排程資訊",
  lastSkipFmt: "最近一次略過：{time} {text}",
  lastSkipConsoleFmt: "這次略過的是你從畫面按的『立即啟動』（稽核編號 {ref}）",
  waitingFmt: "{run} 等待中：{text}",
  waitingNone: "目前沒有在等待啟動的運轉",
  waitingMissing: "等待中的運轉量不到",
  stepsTitle: "這一輪做了什麼",
  stepsMissing: "這一輪的步驟量不到",
  ingestSummaryFmt: "有 {n} 筆稽核檔被拒收或延後",
  ingestNone: "這一輪沒有被拒收的稽核檔",
  ingestMissing: "入帳摘要量不到",
  openWrites: "看待入帳清單",
  pushTitle: "自動推送",
  pushNote: "推送由主機自動執行，這裡只顯示狀態",
  pushMissing: "自動推送狀態量不到",
  pushUnknownFmt: "未知的推送狀態『{value}』",
  pushCommitFmt: "（提交 {sha}）",
  pushAttemptsFmt: "已嘗試 {n} 次",
  pushPrefixOk: "完成：",
  pushPrefixWarn: "需要處理：",
  // 待入帳面板
  ingestRejected: "被拒收",
  ingestDeferred: "延後",
  ingestUnknownStatusFmt: "未知狀態『{value}』",
  ingestHuman: "需要人處理：這筆不會自動入帳。請看最新卡面後重新送出決定；目前畫面沒有取消功能，這筆會留在清單。",
  ingestAuto: "條件解除後下一次心跳會自動入帳",
  ingestUnsure: "是否會自動入帳不明",
  ingestNotYet: "主機還沒處理這筆",
  ingestStaleFmt: "巡邏回報已過時（{ago}）：下面的原因可能已經改變",
  ingestUnavailableFmt: "拒收原因量不到：{why}",
  ingestWhyUnset: "這個部署沒有掛載巡邏回報目錄",
  ingestWhyMissing: "還沒有收到巡邏回報",
  ingestWhyBad: "巡邏回報檔有問題",
  ingestWhyOther: "連不上後端服務",
  recentIngestedFmt: "最近已入帳（{n}）",
  recentIngestedNote: "只列最近 {shown} 筆",
  ingestedBadge: "已入帳",
  // 通用
  retry: "重試",
  loading: "載入中",
  loadError: "自我進化資料無法取得",
  lockedByPatrol: "這個畫面沒有任何推送或寫入功能",
} as const;

/** 代入 `{名稱}`；缺的名稱保留原樣不丟例外。 */
export function fillText(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (whole, name: string) => (name in vars ? String(vars[name]) : whole));
}
const T = SI_FLOW_TEXTS;

// ── 未知值與標籤 ────────────────────────────────────────────────────────────────────────────────
/** 缺席、null、空字串＝量不到；數字與布林用 String；物件與陣列用「[物件]」（不得漏出 [object Object]）。 */
export function unknownValueText(value: unknown): string {
  if (value === null || value === undefined || value === "") return T.unmeasurable;
  const shown = typeof value === "string" ? value : typeof value === "number" || typeof value === "boolean" ? String(value) : T.objectPlaceholder;
  return fillText(T.unknownValue, { value: shown });
}

export type Labeled = { known: boolean; text: string };
const pick = (table: Readonly<Record<string, string>>, value: unknown): Labeled => {
  if (typeof value === "string" && Object.prototype.hasOwnProperty.call(table, value)) return { known: true, text: table[value] };
  return { known: false, text: unknownValueText(value) };
};

const PURPOSE_LABELS = { scheduled: "排程啟動", console: "從畫面按『立即啟動』", manual: "手動啟動" } as const;
const VERDICT_LABELS = { PASS: "通過", FAIL: "未通過", NE: "無法評估" } as const;
const INGEST_STATUS_LABELS = { rejected: T.ingestRejected, deferred: T.ingestDeferred } as const;
/** 等待對象五值（本身就是中文，原樣顯示）。 */
export const WHO_VALUES = ["掌舵者", "巡邏器", "無人運轉", "主機管理者", "無"] as const;
/** 推送狀態八值（只決定樣式與是否為已知值；顯示的句子是主機給的 `text`）。 */
export const PUSH_STATES = ["off", "idle", "pending", "waiting-login", "running", "ok", "failed", "blocked"] as const;

/** 運轉目的：第一波只有三值；`freeze`／`revise`／`propose` 等第二波值一律是未知值。 */
export const labelOfPurpose = (v: unknown): Labeled => pick(PURPOSE_LABELS, v);
export const labelOfVerdict = (v: unknown): Labeled => pick(VERDICT_LABELS, v);
export const labelOfIngestStatus = (v: unknown): Labeled => pick(INGEST_STATUS_LABELS, v);
export function labelOfWho(v: unknown): Labeled {
  if (typeof v === "string" && (WHO_VALUES as readonly string[]).includes(v)) return { known: true, text: v };
  return { known: false, text: unknownValueText(v) };
}

export type Tone = "ok" | "warn" | "neutral";
/** 推送狀態：只回是否已知與樣式類別，**不回任何標籤句**。 */
export function pushStateInfo(v: unknown): { known: boolean; tone: Tone } {
  if (typeof v !== "string" || !(PUSH_STATES as readonly string[]).includes(v)) return { known: false, tone: "neutral" };
  return { known: true, tone: v === "ok" ? "ok" : v === "failed" || v === "blocked" ? "warn" : "neutral" };
}

/** 原因句：有合法白話字逐字回；否則含原因碼的保底句；碼也沒有＝「主機沒有提供原因。」。 */
export function reasonText(code: unknown, text: unknown): string {
  const t = str(text);
  if (t !== null) return t;
  const c = str(code);
  return c !== null ? fillText(T.noPlainText, { code: c }) : T.noReason;
}

/** 把 `scheme://userinfo@` 換成 `scheme://***@`（憑證不得上畫面）。 */
export function maskCredentials(text: string): string {
  return text.replace(/\b([A-Za-z][A-Za-z0-9+.-]*):\/\/[^\s/@]+@/g, "$1://***@");
}

// ── 新鮮度 ──────────────────────────────────────────────────────────────────────────────────────
export type FreshnessState = "fresh" | "stale" | "clock-skew" | "unknown-period" | "unknown-time";
export type Freshness = { state: FreshnessState; ageMinutes: number | null; limitMinutes: number | null; usedClientClock: boolean };

const parseMs = (v: unknown): number => (typeof v === "string" ? Date.parse(v) : Number.NaN);

/**
 * 快照新鮮度（W-F5）：`ageMinutes＝(readAt−generatedAt)＋(現在−資料抵達瀏覽器的時刻)`；`stale ⇔ age > 2×heartbeat＋5`（嚴格大於）。
 * 前一項以 Bridge 的讀取時間為準（不受瀏覽器與主機時鐘偏移影響），後一項只用瀏覽器自己的兩個時刻相減；
 * `readAt` 缺席或無法解析時退用「現在−generatedAt」並回 `usedClientClock: true`。
 */
export function patrolFreshness(report: unknown, readAt: unknown, receivedAtMs: number, nowMs: number): Freshness {
  const r: Rec = isRec(report) ? report : {};
  const genMs = parseMs(r.generatedAt);
  const hb = r.heartbeatMinutes;
  const limit = typeof hb === "number" && Number.isInteger(hb) && hb > 0 ? STALE_FACTOR * hb + STALE_GRACE_MINUTES : null;
  const readMs = parseMs(readAt);
  const usedClientClock = Number.isNaN(readMs);
  if (Number.isNaN(genMs)) return { state: "unknown-time", ageMinutes: null, limitMinutes: limit, usedClientClock };
  const ageMs = usedClientClock ? nowMs - genMs : readMs - genMs + Math.max(0, nowMs - receivedAtMs);
  const ageMinutes = Math.max(0, ageMs / MS_MIN);
  if (limit === null) return { state: "unknown-period", ageMinutes, limitMinutes: null, usedClientClock };
  const skewed = !usedClientClock && genMs - readMs > CLOCK_SKEW_MINUTES * MS_MIN;
  if (skewed) return { state: "clock-skew", ageMinutes, limitMinutes: limit, usedClientClock };
  return { state: ageMs > limit * MS_MIN ? "stale" : "fresh", ageMinutes, limitMinutes: limit, usedClientClock };
}

/** 讓畫面時間隨時間前進的「有效現在」（以 Bridge 讀取時間為錨）；readAt 無法解析時回瀏覽器現在。 */
export function effectiveNowMs(readAt: unknown, receivedAtMs: number, nowMs: number): number {
  const readMs = parseMs(readAt);
  return Number.isNaN(readMs) ? nowMs : readMs + Math.max(0, nowMs - receivedAtMs);
}

/** 分鐘數轉相對時間句（0 與不足 1 分＝剛剛；負數與 NaN＝時間量不到）。 */
export function relativeMinutesText(minutes: unknown): string {
  if (typeof minutes !== "number" || !Number.isFinite(minutes) || minutes < 0) return T.timeMissing;
  const m = Math.floor(minutes);
  if (m < 1) return "剛剛";
  if (m < 60) return `${m} 分鐘前`;
  if (m < 1440) {
    const h = Math.floor(m / 60);
    const rest = m % 60;
    return rest > 0 ? `${h} 小時 ${rest} 分鐘前` : `${h} 小時前`;
  }
  const d = Math.floor(m / 1440);
  const h = Math.floor((m % 1440) / 60);
  return h > 0 ? `${d} 天 ${h} 小時前` : `${d} 天前`;
}

/** 不帶「前」字的長度（供「預計最晚 N 分鐘後」用）。 */
function spanText(minutes: number): string {
  return relativeMinutesText(minutes).replace(/前$/, "");
}

/** 缺席、null、錯型別＝unknown；空陣列＝empty；非空陣列＝items（任何輸入除了真的空陣列都不得得到 empty）。 */
export function sectionState(value: unknown): "unknown" | "empty" | "items" {
  if (!Array.isArray(value)) return "unknown";
  return value.length === 0 ? "empty" : "items";
}

// ── 下一步 ──────────────────────────────────────────────────────────────────────────────────────
export type NextStep = { source: "snapshot" | "detail" | "none"; code?: string; who?: unknown; text: string; warnPatrolMayBeDown: boolean };

/**
 * 下一步來源序（W-F6）：快照可用（新鮮且 `ledgerSeq ≥ 提案 lastSeq` 且 props 有該提案）→ 快照；否則單筆詳情的 `next`；否則「量不到」。
 */
export function resolveNextStep(input: { proposalId: string; lastSeq: number; report: unknown; freshness: Freshness | null; detailNext: unknown }): NextStep {
  const { proposalId, lastSeq, report, freshness, detailNext } = input;
  const r = isRec(report) ? report : null;
  const usable = r !== null && freshness?.state === "fresh" && typeof r.ledgerSeq === "number" && r.ledgerSeq >= lastSeq;
  if (usable && Array.isArray(r.props)) {
    const hit = r.props.find((p): p is Rec => isRec(p) && p.id === proposalId);
    if (hit) return { source: "snapshot", code: str(hit.code) ?? undefined, who: hit.who, text: reasonText(hit.code, hit.text), warnPatrolMayBeDown: false };
  }
  if (isRec(detailNext)) {
    const warn = detailNext.who === "巡邏器" && freshness?.state === "stale";
    return { source: "detail", code: str(detailNext.code) ?? undefined, who: detailNext.who, text: reasonText(detailNext.code, detailNext.text), warnPatrolMayBeDown: warn };
  }
  return { source: "none", text: T.unmeasurable, warnPatrolMayBeDown: false };
}

/** 頂端「下一步」那一行的文字。 */
export function nextStepLine(step: NextStep): string {
  if (step.source === "none") return T.nextStepUnknown;
  if (step.who === "無") return `${T.nextStepNobody}${step.text}`;
  const who = labelOfWho(step.who);
  return fillText(T.nextStepWaitFmt, { who: who.text, text: step.text });
}

// ── diff ────────────────────────────────────────────────────────────────────────────────────────
export type DiffKind = "add" | "del" | "hunk" | "file" | "meta" | "ctx";
export type DiffLine = { kind: DiffKind; text: string };

function kindOf(line: string): DiffKind {
  if (line.startsWith("+++ ") || line.startsWith("--- ") || line.startsWith("diff ") || line.startsWith("index ")) return "file";
  if (line.startsWith("@@")) return "hunk";
  if (line.startsWith("+")) return "add";
  if (line.startsWith("-")) return "del";
  if (line.startsWith("\\")) return "meta";
  return "ctx";
}

/** patch 文字逐行解析：每行保留原文（含行首符號與行尾 `\r`）；輸入以換行結尾時最後的空元素不算一行；`file` 行不計入新增與刪除。 */
export function parseDiff(text: string): { lines: DiffLine[]; addCount: number; delCount: number } {
  if (text === "" || text === "\n") return { lines: [], addCount: 0, delCount: 0 };
  const parts = text.split("\n");
  if (parts[parts.length - 1] === "") parts.pop();
  const lines = parts.map((t) => ({ kind: kindOf(t), text: t }));
  return { lines, addCount: lines.filter((l) => l.kind === "add").length, delCount: lines.filter((l) => l.kind === "del").length };
}

/** 視窗化：未展開且超過 400 行只顯示前 400 行。 */
export function diffWindow<L>(lines: readonly L[], expanded: boolean): { shown: readonly L[]; hiddenCount: number; canExpand: boolean } {
  if (lines.length <= DIFF_WINDOW_LINES) return { shown: lines, hiddenCount: 0, canExpand: false };
  if (expanded) return { shown: lines, hiddenCount: 0, canExpand: true };
  return { shown: lines.slice(0, DIFF_WINDOW_LINES), hiddenCount: lines.length - DIFF_WINDOW_LINES, canExpand: true };
}

/** 下載描述：檔名只取安全字元，內容＝畫面已取得的全文。 */
export function downloadSpec(propId: string, rev: number | null | undefined, patch: { rel?: unknown; text?: unknown; truncated?: unknown }): { filename: string; content: string; mime: string } {
  const safeId = propId.replace(/[^A-Za-z0-9_-]/g, "_");
  const rel = typeof patch.rel === "string" ? patch.rel : "";
  const fromRel = /r(\d+)\.patch$/.exec(rel);
  const revText = fromRel ? fromRel[1] : typeof rev === "number" && Number.isFinite(rev) ? String(Math.trunc(rev)) : "0";
  const mark = patch.truncated === true ? ".truncated" : "";
  return { filename: `${safeId}-r${revText}${mark}.patch`, content: typeof patch.text === "string" ? patch.text : "", mime: "text/plain;charset=utf-8" };
}

// ── 入帳結果結合 ────────────────────────────────────────────────────────────────────────────────
export type Join = { status: unknown; code: unknown; text: unknown; permanent: unknown; mode: "human" | "auto" | "unknown" };

/**
 * 以 `auditRef` 對照快照 `ingest[]`（前端只認 camelCase 鍵）：只對 `ingested===false` 的列結合；重複取第一筆；找不到或快照缺席回 null。
 * `ingested` 為 true 或 null 的列不出現在結果中。
 */
export function joinHostRejections(items: ReadonlyArray<{ auditRef: string; ingested?: boolean | null }>, report: unknown): Array<{ auditRef: string; join: Join | null }> {
  const ingest = isRec(report) && Array.isArray(report.ingest) ? report.ingest : null;
  return items
    .filter((row) => row.ingested === false)
    .map((row) => {
      const hit = ingest?.find((e): e is Rec => isRec(e) && e.auditRef === row.auditRef);
      if (!hit) return { auditRef: row.auditRef, join: null };
      const mode = hit.permanent === true ? "human" : hit.permanent === false ? "auto" : "unknown";
      return { auditRef: row.auditRef, join: { status: hit.status, code: hit.code, text: hit.text, permanent: hit.permanent, mode } };
    });
}

// ── 評估集、驗證、隔離試跑 ──────────────────────────────────────────────────────────────────────
const triText = (v: unknown): string => (v === true ? T.yes : v === false ? T.no : T.unmeasurable);

export type HeldoutView = { state: "unknown"; text: string } | { state: "unfrozen"; text: string; note: string } | { state: "frozen"; text: string; warning: string | null; seq: number | null };

/** 評估集只取七個欄位（不含 `digest8`、也不含任何未知鍵）；低於下限的警示逐字用主機給的 `neNote`。 */
export function heldoutView(h: unknown): HeldoutView {
  if (!isRec(h)) return { state: "unknown", text: T.heldoutUnknown };
  if (h.frozen === false) return { state: "unfrozen", text: T.heldoutUnfrozen, note: T.heldoutUnfrozenNote };
  if (h.frozen !== true) return { state: "unknown", text: T.heldoutUnknown };
  const n = typeof h.n === "number" && Number.isFinite(h.n) ? h.n : null;
  const min = typeof h.min === "number" && Number.isFinite(h.min) ? h.min : null;
  const by = str(h.frozenBy);
  let text: string = T.heldoutFrozenNoN;
  if (n !== null) {
    text = by === null ? fillText(T.heldoutFrozenNoBy, { n }) : min === null ? fillText(T.heldoutFrozenNoMin, { n, by }) : fillText(T.heldoutFrozenFmt, { n, min, by });
  }
  const warning = h.belowMin === true ? (str(h.neNote) ?? T.heldoutBelowMinFallback) : null;
  return { state: "frozen", text, warning, seq: typeof h.seq === "number" ? h.seq : null };
}

export type VerifyView =
  | { state: "none"; text: string }
  | {
      state: "present";
      verdict: { known: boolean; text: string };
      steps: Array<{ key: string; label: string; value: string; failed: boolean }>;
      probes: string;
      carrier: string;
      reasons: { state: "list" | "none-kept" | "no-report" | "missing"; items: Array<{ code: string | null; text: string }> };
    };

/** 驗證檢視模型：三步證據（是／否／量不到）、測量工具自我檢查（通過／沒通過／量不到）與原因清單。 */
export function verifyView(v: unknown): VerifyView {
  if (!isRec(v)) return { state: "none", text: T.verifyNone };
  const verdictLabel = labelOfVerdict(v.verdict);
  const verdict = verdictLabel.known
    ? verdictLabel
    : {
        known: false,
        text:
          v.verdict === null || v.verdict === undefined || v.verdict === ""
            ? T.unmeasurable
            : fillText(T.unknownResult, {
                value: typeof v.verdict === "string" ? v.verdict : typeof v.verdict === "number" || typeof v.verdict === "boolean" ? String(v.verdict) : T.objectPlaceholder,
              }),
      };
  const step = (key: string, label: string): { key: string; label: string; value: string; failed: boolean } => ({ key, label, value: triText(v[key]), failed: v[key] === false });
  const steps = [step("baselineRed", T.verifyStepBaseline), step("patchedGreen", T.verifyStepPatched), step("mutatedRed", T.verifyStepMutated)];
  const probes = typeof v.probesN === "number" && Number.isFinite(v.probesN) ? String(v.probesN) : T.unmeasurable;
  const carrier = v.carrierProof === true ? T.pass : v.carrierProof === false ? T.fail : T.unmeasurable;
  let reasons: { state: "list" | "none-kept" | "no-report" | "missing"; items: Array<{ code: string | null; text: string }> };
  if (!Array.isArray(v.reasons)) reasons = { state: "missing", items: [] };
  else if (v.reasons.length === 0) reasons = { state: v.verdict === "PASS" ? "none-kept" : "no-report", items: [] };
  else reasons = { state: "list", items: v.reasons.map((r) => (isRec(r) ? { code: str(r.code), text: reasonText(r.code, r.text) } : { code: null, text: T.noReason })) };
  return { state: "present", verdict, steps, probes, carrier, reasons };
}

export type SandboxView =
  | { state: "none"; text: string }
  | { state: "ok"; text: string; flags: Array<{ label: string; value: string }> }
  | { state: "fail"; code: string | null; headline: string; detail: string | null; text: string; flags: Array<{ label: string; value: string }> };

/** 隔離試跑（沙盒）：`failText` 非空時逐字使用，缺席或空字串才用保底句。 */
export function sandboxView(s: unknown): SandboxView {
  if (!isRec(s)) return { state: "none", text: T.sandboxNone };
  const flags = [
    { label: T.sandboxApplied, value: triText(s.applied) },
    { label: T.sandboxTouched, value: triText(s.touchedOk) },
    { label: T.sandboxRollback, value: triText(s.rollbackOk) },
  ];
  if (s.applied === true && s.touchedOk === true && s.rollbackOk === true) return { state: "ok", text: T.sandboxOk, flags };
  const code = str(s.failCode);
  const failText = str(s.failText);
  const base = code === null ? T.sandboxFailNoCode : fillText(T.sandboxFailHeadline, { code });
  return {
    state: "fail",
    code,
    headline: failText === null ? `${base}${T.sandboxNoPlain}` : base,
    detail: failText,
    text: failText ?? fillText(T.sandboxFailFallback, { code: code ?? T.unmeasurable }),
    flags,
  };
}

// ── 推送、排程、等待 ────────────────────────────────────────────────────────────────────────────
export type PushView = { known: boolean; state: string | null; tone: Tone; text: string; extras: string[]; time: string | null };

/** 推送狀態：顯示句逐字等於主機給的 `text`（缺席才用保底句）；Console 不自建狀態對照、不對任何碼寫特例；所有輸出經憑證遮罩。 */
export function pushView(push: unknown): PushView {
  if (!isRec(push)) return { known: false, state: null, tone: "neutral", text: T.pushMissing, extras: [], time: null };
  const info = pushStateInfo(push.state);
  const text = maskCredentials(reasonText(push.code, push.text));
  if (!info.known) {
    const head = fillText(T.pushUnknownFmt, { value: typeof push.state === "string" && push.state !== "" ? push.state : T.unmeasurable });
    return { known: false, state: null, tone: "neutral", text: str(push.text) === null ? head : `${head} ${text}`, extras: [], time: null };
  }
  const extras: string[] = [];
  let time: string | null = null;
  if (push.state === "ok") {
    const sha = str(push.sha);
    if (sha !== null) extras.push(fillText(T.pushCommitFmt, { sha: sha.slice(0, 8) }));
    time = str(push.finishedAt);
  }
  if (push.state === "failed" && typeof push.attempts === "number" && Number.isFinite(push.attempts)) extras.push(fillText(T.pushAttemptsFmt, { n: push.attempts }));
  return { known: true, state: push.state as string, tone: info.tone, text, extras, time };
}

export type ScheduleView =
  | { state: "paused" | "absent"; message: string }
  | { state: "present"; enabledText: string; current: { text: string; code: string | null }; lastSkip: { line: string; code: string | null; note: string | null } | null };

/** 排程狀態：`schedule` 為 null 時區分「巡邏暫停」與「回報沒有排程資訊」，不互相冒充。 */
export function scheduleView(schedule: unknown, off: unknown): ScheduleView {
  if (!isRec(schedule))
    return schedule === null || schedule === undefined
      ? off === true
        ? { state: "paused", message: T.schedulePaused }
        : { state: "absent", message: T.scheduleAbsent }
      : { state: "absent", message: T.scheduleAbsent };
  const enabledText = schedule.enabled === true ? T.scheduleEnabled : schedule.enabled === false ? T.scheduleDisabled : T.scheduleEnabledUnknown;
  const cur = isRec(schedule.current) ? schedule.current : null;
  const current = cur ? { text: reasonText(cur.code, cur.text), code: str(cur.code) } : { text: T.scheduleCurrentMissing, code: null };
  const skip = isRec(schedule.lastSkip) ? schedule.lastSkip : null;
  const lastSkip = skip
    ? {
        line: fillText(T.lastSkipFmt, { time: str(skip.t) ?? T.timeMissing, text: reasonText(skip.code, skip.text) }),
        code: str(skip.code),
        note: str(skip.auditRef) === null ? null : fillText(T.lastSkipConsoleFmt, { ref: str(skip.auditRef) as string }),
      }
    : null;
  return { state: "present", enabledText, current, lastSkip };
}

export type WaitingView = { state: "unknown" | "empty"; text: string } | { state: "items"; items: Array<{ key: string; text: string; code: string | null }> };

/** 等待啟動的運轉：每筆「<run> 等待中：<白話>」。 */
export function waitingView(waiting: unknown): WaitingView {
  const s = sectionState(waiting);
  if (s === "unknown") return { state: "unknown", text: T.waitingMissing };
  if (s === "empty") return { state: "empty", text: T.waitingNone };
  const items = (waiting as unknown[]).map((w, i) => {
    const r = isRec(w) ? w : {};
    return { key: `${str(r.run) ?? "run"}-${i}`, text: fillText(T.waitingFmt, { run: str(r.run) ?? T.unmeasurable, text: maskCredentials(reasonText(r.code, r.text)) }), code: str(r.code) };
  });
  return { state: "items", items };
}

/** 進行中運轉那一行：時間以「有效現在」（毫秒）換算；時間無法解析時省略時間。 */
export function liveRunLine(run: unknown, effectiveNow: number): { text: string; known: boolean } {
  const r = isRec(run) ? run : {};
  const purpose = labelOfPurpose(r.purpose);
  const id = str(r.run) ?? T.unmeasurable;
  const startedMs = parseMs(r.startedAt);
  const dueMs = parseMs(r.wallDueAt);
  const head = fillText(T.runLiveHead, { run: id, purpose: purpose.text });
  if (Number.isNaN(startedMs) || Number.isNaN(dueMs)) return { text: head, known: purpose.known };
  const started = relativeMinutesText(Math.round((effectiveNow - startedMs) / MS_MIN));
  const dueMin = Math.round((dueMs - effectiveNow) / MS_MIN);
  // 拆成兩個短句（每句不超過可讀性鎖的 40 字）
  const tail = dueMin < 1 ? fillText(T.runLiveTailDue, { started }) : fillText(T.runLiveTail, { started, due: spanText(dueMin) });
  return { text: `${head}${tail}`, known: purpose.known };
}

/** 來源觀察編號：只有符合 `OBS-SI-\d{3,}` 者可跳轉；依首次出現序去重。 */
export function obsSourceIds(sources: unknown): string[] {
  if (!Array.isArray(sources)) return [];
  const seen = new Set<string>();
  for (const s of sources) if (typeof s === "string" && /^OBS-SI-\d{3,}$/.test(s)) seen.add(s);
  return [...seen];
}
