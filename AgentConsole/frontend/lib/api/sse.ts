/**
 * SSE 客戶端核心（契約 §2；API-SSE-01～03／US-E-03、07）——純邏輯、不依賴 React，EventSource 與網路都由外部注入，方便測試。
 *
 * 契約重點（這裡的每個行為都對應一條）：
 *  - 用原生 EventSource：不能帶標頭，所以 token 放網址 `?access_token=`（§2.1）；監聽「具名事件」（§2.5、§2.6）。
 *  - id 是 `<seq>` 或 `<seq>.<n>`；依 (seq, n) 字典序比較，客戶端記住「已處理的最大 id」、小於等於者忽略（§2.2、§2.3 第 4 點，at-least-once）。
 *    /logs 與 /metrics 是兩條獨立串流、各自記各自的最大 id（§2.3 第 4 點）。
 *  - 連線層的暫態告警（BRIDGE_UNREACHABLE／BRIDGE_RUN_UNKNOWN）不帶 `id:` 行：EventSource 的 lastEventId 會沿用前一則，
 *    若照 id 去重就會被誤丟，所以這類告警不參與去重（§2.2 第 4 條）。
 *  - 斷線回補順序（主控裁決補充、§2.3 第 6 點、§2.8 第 4 點）：先讓 EventSource 自己以 Last-Event-ID 重連（伺服器端重播），
 *    連續失敗兩次以上才改走 `GET /executions/{runId}/steps?afterSeq=` 回補，再重新連線。
 *  - EventSource 看不到 HTTP 狀態碼：401、404、204 都只是「連線被瀏覽器放棄（readyState=CLOSED）」。
 *    處理法＝先問一次 REST（順便讓 apiRequest 處理 401 換新）：run 已終態就收工，否則強制換新 token 後重建連線（§2.1、§2.4）。
 *  - 後端暫時不可用（v1.2，C-5，QA DEF-AC-007；§2.8 第 7～8 點）：換新失敗分 renewed／invalid／unavailable 三類，只有 invalid 才登出
 *    （client.ts）。getToken 在 unavailable 時沿用尚未過期的現有 token、否則回 null——**null 不是失敗**：不登出、不放棄，
 *    與連線失敗一樣以 1→2→4→…→30 秒退避重建，狀態點維持「重新連線中」（直到連上，或連續失敗超過 DEFAULT_MAX_FAILURES 才 failed）。
 *  - 終態（COMPLETED／FAILED／CANCELLED）：伺服器先送該 status 再送衍生事件（例如 ESCALATED 的審核項）才關連線（§2.4），
 *    所以看到終態不能立刻關，要等伺服器關（或一小段閒置）才收工；收工後不再重連。
 *  - PAUSED／PAUSING／CANCELLING 不結束串流；restore 會讓終態 run 重新變 RUNNING，須由呼叫端 reconnect()（§2.4、§2.8 第 5 點）。
 *  - 離頁 close()：之後不再有任何事件、狀態或重連。
 */
import { apiBase, getFreshAccessToken } from "./client";
import type { AlertEventData, LogEventData, MetricUpdateEventData, ProgressUpdateEventData, ReviewRequestEventData, RunStatus, StatusChangeEventData, TokenUpdateEventData } from "./types";
import { isRunTerminal } from "@/lib/domain/status";

export type StreamKind = "logs" | "metrics";

export const STREAM_EVENT_NAMES: Record<StreamKind, readonly string[]> = {
  logs: ["log", "status-change", "review-request", "alert"],
  metrics: ["progress-update", "token-update", "metric-update"],
};

/** 串流事件（name＝SSE 的 event 欄位；id＝EventSource 的 lastEventId，沒有則 null；data＝解析後的單行 JSON）。 */
export type RunStreamEvent =
  | { name: "log"; id: string | null; data: LogEventData }
  | { name: "status-change"; id: string | null; data: StatusChangeEventData }
  | { name: "review-request"; id: string | null; data: ReviewRequestEventData }
  | { name: "alert"; id: string | null; data: AlertEventData }
  | { name: "progress-update"; id: string | null; data: ProgressUpdateEventData }
  | { name: "token-update"; id: string | null; data: TokenUpdateEventData }
  | { name: "metric-update"; id: string | null; data: MetricUpdateEventData };

/**
 * 連線狀態（「SSE 串流」狀態點，契約 §2.8 第 6 點：客戶端連線狀態，不是伺服器欄位）：
 *  idle＝尚未開始或已離頁關閉；connecting＝第一次連線中；open＝已連上；reconnecting＝斷線重連中；
 *  ended＝正常收工（run 已終態）；failed＝重試用盡（可手動 reconnect）。
 */
export type StreamState = "idle" | "connecting" | "open" | "reconnecting" | "ended" | "failed";

// ── id 工具 ───────────────────────────────────────────────────────────────
export type EventId = readonly [seq: number, sub: number];

const ID_PATTERN = /^(\d+)(?:\.(\d+))?$/;

/** 解析事件 id：`41`→[41,0]、`41.2`→[41,2]；格式不合（契約 §2.3 第 1 點：`^[0-9]+(\.[0-9]+)?$`）回 null。 */
export function parseEventId(id: string | null | undefined): EventId | null {
  if (!id) return null;
  const m = ID_PATTERN.exec(id);
  if (!m) return null;
  return [Number(m[1]), m[2] === undefined ? 0 : Number(m[2])];
}

/** 字典序比較（契約 §2.2：41 < 41.1 < 41.2 < 42）：負＝a 較早、0＝相同、正＝a 較晚。 */
export function compareEventIds(a: EventId, b: EventId): number {
  return a[0] !== b[0] ? a[0] - b[0] : a[1] - b[1];
}

/** 事件是否宣告 run 進入終態：/logs 看 status-change、/metrics 看 progress-update 的 runStatus。 */
export function isTerminalEvent(event: RunStreamEvent): boolean {
  if (event.name === "status-change" || event.name === "progress-update") return isRunTerminal(event.data.runStatus);
  return false;
}

/**
 * 暫態告警（連線層，不持久化、不帶 id 行）：origin=CONSOLE 且沒有子序號。
 * 這類事件不參與去重（見檔頭第三點）；持久化的 Console 規則告警一定有 sub（id＝<seq>.<sub>）。
 */
export function isTransientAlert(event: RunStreamEvent): boolean {
  return event.name === "alert" && event.data.origin === "CONSOLE" && typeof event.data.sub !== "number";
}

export type StreamUrlOptions = {
  base?: string;
  runId: string;
  kind: StreamKind;
  token: string;
  /** 只對 /logs 有意義：沒有 Last-Event-ID 時先重播最後 N 則（預設 200）。重建連線時用較大的值，靠去重補齊。 */
  tail?: number;
};

export function buildStreamUrl({ base = apiBase(), runId, kind, token, tail }: StreamUrlOptions): string {
  const params = new URLSearchParams({ access_token: token });
  if (kind === "logs" && tail !== undefined) params.set("tail", String(tail));
  return `${base}/api/v1/stream/executions/${encodeURIComponent(runId)}/${kind}?${params.toString()}`;
}

// ── EventSource 的最小介面（測試用假物件、正式用瀏覽器原生）─────────────────────
export const READY_CONNECTING = 0;
export const READY_OPEN = 1;
export const READY_CLOSED = 2;

export interface EventSourceLike {
  readonly readyState: number;
  onopen: ((ev: Event) => unknown) | null;
  onerror: ((ev: Event) => unknown) | null;
  addEventListener(type: string, listener: (ev: MessageEvent) => void): void;
  close(): void;
}
export type EventSourceCtor = new (url: string) => EventSourceLike;

export type ChannelDeps = {
  EventSourceCtor: EventSourceCtor;
  /**
   * 取得可放進網址的 access token（快到期或 force 時先換新）。回 null＝眼前拿不到可用的 token：
   * 換新時後端暫時不可用且現有 token 已過期（不登出，稍後重試），或登入已失效（getToken 已負責登出／導向登入，頁面隨即卸載）。
   */
  getToken: (opts?: { force?: boolean }) => Promise<string | null>;
  /** 連線被瀏覽器放棄時問一次 REST（順便讓 apiRequest 處理 401 換新）：run 現在的狀態；問不到回 null。 */
  fetchRunStatus: () => Promise<RunStatus | null>;
  /** 連續失敗兩次以上：以 afterSeq（嚴格大於）取步驟回補（steps 只含步驟事件，契約 §1.2.7）。 */
  backfill: (afterSeq: number) => Promise<void>;
};

export type ChannelHandlers = {
  onEvent: (event: RunStreamEvent) => void;
  onState: (state: StreamState) => void;
};

export type ChannelOptions = {
  runId: string;
  kind: StreamKind;
  base?: string;
  /** 重建連線時的 tail（預設 1000；契約上限 5000）。 */
  rebuildTail?: number;
  /** 連續失敗幾次後放棄（預設 DEFAULT_MAX_FAILURES）。 */
  maxFailures?: number;
  /** 終態後等伺服器關連線的最長閒置（預設 4 秒）；逾時就自己收工。 */
  terminalGraceMs?: number;
  /** 重建前的等待（預設指數退避 1→30 秒，契約 §2.8 第 8 點）；測試可覆寫。 */
  backoffMs?: (failures: number) => number;
};

/** 連續失敗幾次之後，不再等瀏覽器自己重連、改走 REST 回補再重建（契約 §2.8 第 4 點：「兩次以上」）。 */
export const BACKFILL_AFTER_FAILURES = 2;

/** 退避的上限（毫秒）：契約 §2.8 第 8 點「1→2→4→…→30 秒（上限 30 秒）」。 */
export const MAX_BACKOFF_MS = 30_000;

/**
 * 連續失敗幾次後才放棄（進入 failed、由使用者按「重新連線」）。後端重啟經 nginx 約 15～40 秒、較長的維護也只是數分鐘，
 * 這段期間狀態必須維持「重新連線中」而不是「連線失敗」（DEF-AC-007）；30 秒上限的退避下 60 次約 28 分鐘，
 * 之後才停手，避免頁面開著卻對永遠回不來的後端（例如批次已被清除）無止境地重試。
 */
export const DEFAULT_MAX_FAILURES = 60;

export function defaultBackoffMs(failures: number): number {
  return Math.min(1000 * 2 ** Math.max(0, failures - 1), MAX_BACKOFF_MS);
}

/**
 * 單一條串流（/logs 或 /metrics）的連線管理。
 * 一個頁面通常開兩條（各自記自己的最大 id）；useRunStream 把它們接進 React。
 */
export class RunChannel {
  private state: StreamState = "idle";
  private es: EventSourceLike | null = null;
  private maxId: EventId | null = null;
  /** 已處理過的最大 Bridge seq（整數部分）：REST 回補的 afterSeq。 */
  private lastSeq = 0;
  /** 連續失敗次數：連上（open）或收到任何事件即歸零。 */
  private failures = 0;
  private everOpened = false;
  private terminalSeen = false;
  /** 下一次連線是否強制換新 token（連線被瀏覽器放棄時，疑似 401）。 */
  private forceRefresh = false;
  /** 每次 start／reconnect／close 遞增：過期的非同步結果一律丟棄。 */
  private generation = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private terminalTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private readonly options: ChannelOptions,
    private readonly deps: ChannelDeps,
    private readonly handlers: ChannelHandlers,
  ) {}

  get currentState(): StreamState {
    return this.state;
  }

  /** 已處理的最大 id（`41`／`41.2`）；測試與除錯用。 */
  get lastEventId(): string | null {
    if (!this.maxId) return null;
    return this.maxId[1] === 0 ? String(this.maxId[0]) : `${this.maxId[0]}.${this.maxId[1]}`;
  }

  start(): void {
    if (this.state !== "idle") return;
    void this.connect(false);
  }

  /** 離頁：關閉連線，之後不再有事件、狀態變化或重連。 */
  close(): void {
    this.generation += 1;
    this.clearTimers();
    this.es?.close();
    this.es = null;
    this.setState("idle");
  }

  /**
   * 手動重新連線（restore 之後原連線早已因終態關閉；或重試用盡後使用者按「重新連線」）。
   * 連線還活著（connecting／open／reconnecting）時不做事。
   */
  reconnect(): void {
    if (this.state === "connecting" || this.state === "open" || this.state === "reconnecting") return;
    this.generation += 1;
    this.clearTimers();
    this.es?.close();
    this.es = null;
    this.terminalSeen = false;
    this.failures = 0;
    this.forceRefresh = false;
    void this.connect(this.maxId !== null);
  }

  private setState(next: StreamState): void {
    if (this.state === next) return;
    this.state = next;
    this.handlers.onState(next);
  }

  private clearTimers(): void {
    if (this.timer) clearTimeout(this.timer);
    if (this.terminalTimer) clearTimeout(this.terminalTimer);
    this.timer = null;
    this.terminalTimer = null;
  }

  private async connect(rebuilt: boolean): Promise<void> {
    const gen = ++this.generation;
    this.setState(this.everOpened || this.failures > 0 ? "reconnecting" : "connecting");
    const token = await this.deps.getToken({ force: this.forceRefresh });
    if (gen !== this.generation) return;
    if (!token) {
      // 眼前拿不到可用 token（換新時後端暫時不可用且現有 token 已過期；契約 §2.8 第 8 點）：不登出、不放棄——
      // 與連線失敗同一條路：計一次失敗、退避後重試，狀態點維持「重新連線中」（DEF-AC-007）
      this.failures += 1;
      if (this.failures > (this.options.maxFailures ?? DEFAULT_MAX_FAILURES)) {
        this.setState("failed");
        return;
      }
      this.scheduleRebuild(gen, rebuilt);
      return;
    }
    const url = buildStreamUrl({
      base: this.options.base,
      runId: this.options.runId,
      kind: this.options.kind,
      token,
      tail: rebuilt ? (this.options.rebuildTail ?? 1000) : undefined,
    });
    const es = new this.deps.EventSourceCtor(url);
    this.es = es;
    es.onopen = () => {
      if (gen !== this.generation) return;
      this.everOpened = true;
      this.failures = 0;
      this.forceRefresh = false;
      this.setState("open");
    };
    for (const name of STREAM_EVENT_NAMES[this.options.kind]) {
      es.addEventListener(name, (ev) => this.onMessage(gen, name, ev));
    }
    es.onerror = () => this.onError(gen, es);
  }

  private onMessage(gen: number, name: string, ev: MessageEvent): void {
    if (gen !== this.generation) return;
    // 收到事件就代表連線是好的（有些代理不觸發 open，或 open 先於本事件已漏接）
    this.everOpened = true;
    this.failures = 0;
    this.forceRefresh = false;
    this.setState("open");

    let data: unknown;
    try {
      data = JSON.parse(String(ev.data));
    } catch {
      return; // 損毀的資料行：略過，不讓整條串流掛掉
    }
    const id = ev.lastEventId ? ev.lastEventId : null;
    const event = { name, id, data } as RunStreamEvent;

    if (!isTransientAlert(event)) {
      const parsed = parseEventId(id);
      if (parsed) {
        if (this.maxId && compareEventIds(parsed, this.maxId) <= 0) return; // at-least-once：重複的丟掉
        this.maxId = parsed;
        if (parsed[0] > this.lastSeq) this.lastSeq = parsed[0];
      }
    }

    if (isTerminalEvent(event)) this.terminalSeen = true;
    this.handlers.onEvent(event);
    if (this.terminalSeen) this.armTerminalTimer(gen);
  }

  /** 終態後伺服器會先送衍生事件再關連線；每收到一則就重新計時，閒置超過 grace 才自己收工。 */
  private armTerminalTimer(gen: number): void {
    if (this.terminalTimer) clearTimeout(this.terminalTimer);
    this.terminalTimer = setTimeout(() => {
      if (gen === this.generation) this.finish();
    }, this.options.terminalGraceMs ?? 4000);
  }

  private finish(): void {
    this.generation += 1;
    this.clearTimers();
    this.es?.close();
    this.es = null;
    this.setState("ended");
  }

  private onError(gen: number, es: EventSourceLike): void {
    if (gen !== this.generation) return;
    this.failures += 1;

    // 終態已見：這次「錯誤」就是伺服器關連線（收工），不再重連
    if (this.terminalSeen) {
      this.finish();
      return;
    }

    if (es.readyState === READY_CLOSED) {
      // 瀏覽器放棄了（401／404／204…；EventSource 看不到狀態碼）：不會再自己重連
      void this.recover(gen);
      return;
    }

    // readyState=CONNECTING：瀏覽器正在自動重連，並帶 Last-Event-ID（伺服器重播）——先讓它試
    this.setState("reconnecting");
    if (this.failures >= BACKFILL_AFTER_FAILURES) {
      es.close();
      void this.fallback(gen);
    }
  }

  /** 連續失敗兩次以上：REST 回補，再（退避後）重建連線。 */
  private async fallback(gen: number): Promise<void> {
    if (this.failures > (this.options.maxFailures ?? DEFAULT_MAX_FAILURES)) {
      this.setState("failed");
      return;
    }
    try {
      await this.deps.backfill(this.lastSeq);
    } catch {
      // 回補失敗不擋重連：重連後 tail／快照仍會補上大部分內容
    }
    if (gen !== this.generation) return;
    this.scheduleRebuild(gen);
  }

  /** 連線被瀏覽器放棄：先問 REST（終態就收工；順便處理 401 換新），否則強制換新 token 後重建。 */
  private async recover(gen: number): Promise<void> {
    this.es = null;
    let status: RunStatus | null = null;
    try {
      status = await this.deps.fetchRunStatus();
    } catch {
      status = null;
    }
    if (gen !== this.generation) return;
    if (isRunTerminal(status)) {
      this.finish();
      return;
    }
    if (this.failures > (this.options.maxFailures ?? DEFAULT_MAX_FAILURES)) {
      this.setState("failed");
      return;
    }
    this.forceRefresh = true;
    if (this.failures >= BACKFILL_AFTER_FAILURES) {
      try {
        await this.deps.backfill(this.lastSeq);
      } catch {
        // 同上
      }
      if (gen !== this.generation) return;
    }
    this.scheduleRebuild(gen);
  }

  /** 退避後重建連線；rebuilt＝是否沿用「重建」的 tail（第一次連線就拿不到 token 時仍是首次連線，不放大 tail）。 */
  private scheduleRebuild(gen: number, rebuilt = true): void {
    this.setState("reconnecting");
    const wait = (this.options.backoffMs ?? defaultBackoffMs)(this.failures);
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => {
      if (gen !== this.generation) return;
      this.timer = null;
      void this.connect(rebuilt);
    }, wait);
  }
}

/**
 * 兩條串流合成一個「SSE 串流」狀態點：任一失敗＝失敗；兩條都收工＝收工；任一重連／連線中＝重連／連線中；
 * 其餘（含一條已收工、另一條仍開著）＝已連線（還在收事件）。
 */
export function combineStreamStates(a: StreamState, b: StreamState): StreamState {
  const both = [a, b];
  if (both.includes("failed")) return "failed";
  if (both.every((s) => s === "ended")) return "ended";
  if (both.includes("reconnecting")) return "reconnecting";
  if (both.includes("connecting")) return "connecting";
  if (both.every((s) => s === "open" || s === "ended")) return "open";
  return "idle";
}

/**
 * 串流已收工、但 REST 說批次還沒結束（例如 restore 讓終態 run 重新執行，或收工的當下 REST 還是舊的）：該重新連線。
 * REST 狀態未知（undefined／null）不重連；終態不重連。
 */
export function shouldReviveStream(states: readonly StreamState[], runStatus: RunStatus | null | undefined): boolean {
  if (!runStatus || isRunTerminal(runStatus)) return false;
  return states.some((s) => s === "ended");
}

/** 正式用的依賴：瀏覽器的 EventSource 與 client.ts 的 token 換新；fetchRunStatus／backfill 由呼叫端（hook）提供。 */
export function defaultChannelDeps(extra: Pick<ChannelDeps, "fetchRunStatus" | "backfill">, ctor: EventSourceCtor = EventSource as unknown as EventSourceCtor): ChannelDeps {
  return { EventSourceCtor: ctor, getToken: getFreshAccessToken, ...extra };
}
