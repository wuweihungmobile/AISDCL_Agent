/**
 * 假 EventSource（vitest 用；jsdom 沒有 EventSource）：重現瀏覽器的語意——
 *  - lastEventId 是「這條連線最後一次看到的 id」，沒帶 id 的事件沿用前一則的值（所以暫態告警會「看起來」是重複 id）；
 *  - 伺服器正常關閉或網路中斷＝error 事件、readyState=CONNECTING（瀏覽器自己重連）；
 *  - 非 200／204／錯誤的 content-type＝error 事件、readyState=CLOSED（瀏覽器放棄，不再重連）。
 */
import { READY_CLOSED, READY_CONNECTING, READY_OPEN, type EventSourceLike } from "@/lib/api/sse";

export class FakeEventSource implements EventSourceLike {
  static instances: FakeEventSource[] = [];
  static reset(): void {
    FakeEventSource.instances = [];
  }
  static get last(): FakeEventSource {
    return FakeEventSource.instances[FakeEventSource.instances.length - 1];
  }
  /** 依串流種類取最近一個連線（網址含 /logs 或 /metrics） */
  static lastOf(kind: "logs" | "metrics"): FakeEventSource | undefined {
    return [...FakeEventSource.instances].reverse().find((es) => es.url.includes(`/${kind}?`));
  }

  readyState = READY_CONNECTING;
  onopen: ((ev: Event) => unknown) | null = null;
  onerror: ((ev: Event) => unknown) | null = null;
  closed = false;
  private listeners = new Map<string, Array<(ev: MessageEvent) => void>>();
  private lastId = "";

  constructor(public readonly url: string) {
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (ev: MessageEvent) => void): void {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  close(): void {
    this.closed = true;
    this.readyState = READY_CLOSED;
  }

  get names(): string[] {
    return [...this.listeners.keys()].sort();
  }

  // ── 測試驅動 ──
  open(): void {
    this.readyState = READY_OPEN;
    this.onopen?.(new Event("open"));
  }

  emit(name: string, data: unknown, id?: string): void {
    if (id !== undefined) this.lastId = id;
    const ev = new MessageEvent(name, {
      data: typeof data === "string" ? data : JSON.stringify(data),
      lastEventId: this.lastId,
    });
    for (const listener of this.listeners.get(name) ?? []) listener(ev);
  }

  /** 伺服器關連線／網路斷：瀏覽器自己排程重連（CONNECTING） */
  dropRetrying(): void {
    this.readyState = READY_CONNECTING;
    this.onerror?.(new Event("error"));
  }

  /** 瀏覽器放棄（401／404／204） */
  dropClosed(): void {
    this.readyState = READY_CLOSED;
    this.onerror?.(new Event("error"));
  }
}
