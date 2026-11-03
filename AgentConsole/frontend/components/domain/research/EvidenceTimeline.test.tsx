import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";

import { useResearchEvidence, useResearchProject, useResearchSources } from "@/lib/api/queries";
import type { ResearchEvent } from "@/lib/api/types";
import {
  RESEARCH_REPLAY_GAP_EVENT,
  RESEARCH_SSE_EVENT_TYPES,
  contiguousPrefix,
  describeResearchEvent,
  latencySummary,
  mergeEventsBySeq,
  parseTimelineEvent,
  percentile,
  renderLatencyMs,
  timelineView,
  type TimelineEvent,
} from "@/lib/domain/research";
import { R1 } from "@/tests/fixtures/research/ids";
import { FakeEventSource } from "@/tests/helpers/fakeEventSource";
import { callsOf, failure, renderResearch, stubResearchApi, writeCalls } from "@/tests/helpers/research";
import { EvidenceTimeline, type TimelineOptions } from "./EvidenceTimeline";

/**
 * 證據鏈即時動態欄（TCS-ResearchToPRD-P0-20261102 AT-960-10-4、10-5、10-7、10-8；AC-R2P-06-1～06-4）：
 * 外部文字一律純文字（含靜態掃描與負控）、頁面重開由 REST 重建、SSE 重連首筆 id 不連續與 `research.replay_gap` 訊號都全量重抓並去重合併
 * （重抓完成前不渲染缺口之後的事件）、事件到畫面的延遲量測。EventSource 與 fetch 都是替身；等待以 waitFor、重試與退避以注入的短時間（5 毫秒）取代真計時。
 * 判定指令：npx vitest run components/domain/research/EvidenceTimeline.test.tsx -t "<AT 底線形>"
 */
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(),
}));

// ── 夾具 ─────────────────────────────────────────────────────────────────────────────

const at = (n: number): string => `2026-11-02T10:${String(Math.floor(n / 60) % 60).padStart(2, "0")}:${String(n % 60).padStart(2, "0")}+08:00`;

/** 一筆事件（預設是 `research.evidence`，論點為「證據 <seq>」）。 */
function ev(seq: number, eventType = "research.evidence", payload: Record<string, unknown> = {}, extra: Partial<TimelineEvent> = {}): TimelineEvent {
  const base = eventType === "research.evidence" ? { matrixVersion: 1, evidenceNo: `E-${String(seq).padStart(3, "0")}`, sourceNo: "S-001", claim: `證據 ${seq}`, strength: "MEDIUM" } : {};
  return { seq, eventType, step: "topic", actor: "bridge", refKind: null, refId: null, payload: { ...base, ...payload }, occurredAt: at(seq), ...extra };
}
const range = (from: number, to: number): TimelineEvent[] => Array.from({ length: to - from + 1 }, (_, i) => ev(from + i));
const seqList = (from: number, to: number): number[] => range(from, to).map((e) => e.seq);

const rows = (): HTMLElement[] => screen.queryAllByTestId("timeline-event");
const seqs = (): number[] => rows().map((row) => Number(row.getAttribute("data-seq")));
const lastEventIdOf = (es: FakeEventSource): string => (es as unknown as { lastId: string }).lastId;

/**
 * 「任一時刻」不變式：每次 DOM 提交後，畫面上的事件 seq 都必須自 1 起連續、嚴格遞增（無缺漏、無重複）。
 * 以 MutationObserver 在每個提交後檢查，所以測試只在「檢查點」看一眼抓不到的中間狀態也逃不掉；回傳違規說明（空陣列＝全程成立）。
 */
function watchInvariant(): { stop: () => string[] } {
  const violations: string[] = [];
  const check = () => {
    const list = seqs();
    list.forEach((seq, i) => {
      if (seq !== i + 1) violations.push(`第 ${i + 1} 項是 seq ${seq}：${list.join(",")}`);
    });
  };
  const observer = new MutationObserver(check);
  observer.observe(document.body, { childList: true, subtree: true });
  return {
    stop() {
      observer.takeRecords();
      observer.disconnect();
      return violations;
    },
  };
}
const send = (es: FakeEventSource, event: TimelineEvent, id: string | undefined = String(event.seq)) =>
  act(() => {
    es.emit(event.eventType, event, id);
  });

type Stub = Parameters<typeof stubResearchApi>[0];

/** 攔下事件帳的 GET：`hold()` 之後的請求在 `release()` 前不回應（用來觀察「重抓完成前」的畫面）；`issued` 記下被攔下的請求網址。 */
function eventGate() {
  const inner = globalThis.fetch;
  let holding = false;
  let release: () => void = () => {};
  let gate: Promise<void> = Promise.resolve();
  const issued: string[] = [];
  vi.stubGlobal("fetch", (input: Parameters<typeof fetch>[0], init?: Parameters<typeof fetch>[1]) => {
    if (holding && /\/events(\?|$)/.test(String(input)) && (init?.method ?? "GET") === "GET") {
      issued.push(String(input));
      return gate.then(() => inner(input, init));
    }
    return inner(input, init);
  });
  return {
    issued,
    hold() {
      holding = true;
      gate = new Promise<void>((resolve) => {
        release = resolve;
      });
    },
    release() {
      holding = false;
      release();
    },
  };
}

function mount(opts: { events?: ResearchEvent[]; stub?: Stub; props?: Partial<TimelineOptions>; stream?: boolean; hold?: boolean } = {}) {
  FakeEventSource.reset();
  if (opts.stream !== false) vi.stubGlobal("EventSource", FakeEventSource);
  const api = stubResearchApi({ events: opts.events ?? range(1, 3), ...opts.stub });
  const gate = eventGate();
  if (opts.hold === true) gate.hold();
  const ui = renderResearch(<EvidenceTimeline researchId={R1} syncRetryMs={5} backoffMs={() => 5} {...opts.props} />);
  return { ...ui, ...api, gate };
}

/** 等 REST 的事件列出現、EventSource 建好並開啟；回該連線。 */
async function connected(count: number): Promise<FakeEventSource> {
  await waitFor(() => expect(rows()).toHaveLength(count));
  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
  const es = FakeEventSource.last;
  act(() => es.open());
  return es;
}

const detailCalls = (calls: Parameters<typeof callsOf>[0]) => callsOf(calls, "GET", /^\/api\/v1\/research\/projects\/[^/]+$/);
const listCalls = (calls: Parameters<typeof callsOf>[0]) => callsOf(calls, "GET", /^\/api\/v1\/research\/projects$/);
const eventCalls = (calls: Parameters<typeof callsOf>[0]) => callsOf(calls, "GET", /\/events$/);

// ── AT_960_10_4 純文字渲染 ───────────────────────────────────────────────────────────────

const SCRIPT_TITLE = "<script>alert(1)</script>";
const MARKDOWN_CLAIM = "**粗體** 與 <img src=x onerror=alert(1)>";
const ENTITY_SOURCE = "來源名 &lt;b&gt; 結束";
const HOSTILE_ALERT = "<b>警告</b> https://evil.test/?q=<script>";
const HOSTILE_REASON = "<iframe src=javascript:alert(1)></iframe> [連結](javascript:alert(2))";

const HOSTILE_EVENTS: TimelineEvent[] = [
  ev(1, "research.source", { sourceNo: "S-001", layer: "ACADEMIC", tier: "T1", verification: "V2", title: SCRIPT_TITLE, url: "https://example.com/paper", fetchOutcome: "OK" }),
  ev(2, "research.evidence", { claim: MARKDOWN_CLAIM }),
  ev(3, "research.source", { sourceNo: "S-002", layer: "OSS", tier: "T2", verification: "V3", title: ENTITY_SOURCE, url: "javascript:alert(1)", fetchOutcome: "OK" }),
  ev(4, "research.alert", { kind: "DENIED_FETCH", detail: HOSTILE_ALERT }),
  ev(5, "research.review_invalid", { stageRunId: "run-1", roundNo: 2, attempt: 1, reason: HOSTILE_REASON }),
];

const subjectsOf = (): string[] => screen.getAllByTestId("timeline-event").map((row) => row.querySelector('[data-field="subject"]')?.textContent ?? "");

/** 靜態掃描：回違規說明。`dangerouslySetInnerHTML` 任何檔都不准；Markdown／rehype／remark 的 import 只准 StudioPanel.tsx。 */
function renderViolations(file: string, source: string): string[] {
  const code = source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`])\/\/.*$/gm, "$1");
  const found: string[] = [];
  if (/dangerouslySetInnerHTML/.test(code)) found.push(`${file}：dangerouslySetInnerHTML`);
  const markdownImport = /(?:from\s+|import\(\s*|require\(\s*)["'](react-markdown|rehype[\w-]*|remark[\w-]*|@uiw\/[\w-]+|@\/components\/markdown[^"']*|[^"']*\/markdown\/[^"']*)["']/;
  if (path.basename(file) !== "StudioPanel.tsx" && markdownImport.test(code)) found.push(`${file}：Markdown 渲染器 import`);
  return found;
}

function sourcesUnder(dir: string, out: Array<{ file: string; text: string }> = []): Array<{ file: string; text: string }> {
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) sourcesUnder(full, out);
    else if (/\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name)) out.push({ file: path.relative(process.cwd(), full).split(path.sep).join("/"), text: readFileSync(full, "utf-8") });
  }
  return out;
}

describe("AT_960_10_4 動態欄對外部文字原樣純文字顯示", () => {
  it("AT_960_10_4 含 script、Markdown、img 與實體的標題、摘要、來源名、警示與無效原因逐字出現（textContent 相等）；DOM 沒有 script、img、strong、iframe 元素與任何事件屬性", async () => {
    const { container } = mount({ events: HOSTILE_EVENTS });
    await waitFor(() => expect(rows()).toHaveLength(5));
    expect(subjectsOf()).toEqual([SCRIPT_TITLE, MARKDOWN_CLAIM, ENTITY_SOURCE, HOSTILE_ALERT, HOSTILE_REASON]);
    for (const text of [SCRIPT_TITLE, MARKDOWN_CLAIM, ENTITY_SOURCE, HOSTILE_ALERT, HOSTILE_REASON]) expect(screen.getByText(text)).toBeInTheDocument();
    expect(container.querySelector("script, img, strong, iframe, b")).toBeNull();
    expect(container.querySelector("[onerror], [onclick], [onload]")).toBeNull();
    expect(screen.getByText(ENTITY_SOURCE).textContent, "實體不被解碼").toContain("&lt;b&gt;");
    // 來源網址：合法 https 才是連結（rel 含 noopener 與 noreferrer）；javascript: 只顯示文字
    const link = within(rows()[0]).getByRole("link", { name: "https://example.com/paper" });
    expect(link.getAttribute("rel")).toContain("noopener");
    expect(link.getAttribute("rel")).toContain("noreferrer");
    expect(within(rows()[2]).queryByRole("link")).toBeNull();
    expect(within(rows()[2]).getByText("javascript:alert(1)")).toBeInTheDocument();
  });

  it("AT_960_10_4 串流上收到的事件同樣純文字顯示（不執行、不轉格式）", async () => {
    const { container } = mount({ events: range(1, 2) });
    const es = await connected(2);
    send(es, ev(3, "research.source", { sourceNo: "S-009", layer: "COMMUNITY", tier: "T3", verification: "V1", title: SCRIPT_TITLE, fetchOutcome: "OK" }));
    send(es, ev(4, "research.evidence", { claim: MARKDOWN_CLAIM }));
    await waitFor(() => expect(rows()).toHaveLength(4));
    expect(subjectsOf().slice(2)).toEqual([SCRIPT_TITLE, MARKDOWN_CLAIM]);
    expect(container.querySelector("script, img, strong, iframe")).toBeNull();
  });

  it("AT_960_10_4 描述函式不丟例外：缺欄、型別不對、未知事件型別只顯示型別名；所有欄位都是字串", () => {
    const odd = [
      describeResearchEvent({ eventType: "research.source", payload: {} }),
      describeResearchEvent({ eventType: "research.run", payload: { stage: 42, status: { nested: true }, tokensUsed: "NaN" } }),
      describeResearchEvent({ eventType: "research.review", payload: { weightedScore: null } }),
      describeResearchEvent({ eventType: "research.something_new", payload: { x: 1 } }),
    ];
    expect(odd[3]).toMatchObject({ kind: "other", headline: "research.something_new", subject: "" });
    expect(odd[2].meta).toContain("前置檢查未過，未計分");
    for (const line of odd) {
      expect(typeof line.headline).toBe("string");
      expect(typeof line.subject).toBe("string");
      expect(line.meta.every((m) => typeof m === "string")).toBe(true);
    }
  });

  it("AT_960_10_4 靜態掃描：components/domain/research 與 app/research 的非測試原始碼沒有 dangerouslySetInnerHTML，Markdown／rehype／remark 只准出現在 StudioPanel.tsx；掃描範圍非空、掃描器有負控", () => {
    const files = [...sourcesUnder(path.join(process.cwd(), "components", "domain", "research")), ...sourcesUnder(path.join(process.cwd(), "app", "research"))];
    expect(files.length, "掃描範圍非空（四個面板加骨架與頁殼）").toBeGreaterThanOrEqual(8);
    for (const required of ["EvidenceTimeline.tsx", "EvidenceMatrixTable.tsx", "TopicPanel.tsx", "AllowlistDialog.tsx"])
      expect(
        files.map((f) => path.basename(f.file)),
        `掃描範圍含 ${required}`,
      ).toContain(required);
    expect(
      files.some((f) => f.file.startsWith("app/research/")),
      "掃描範圍含 app/research",
    ).toBe(true);
    for (const { file, text } of files) expect(renderViolations(file, text), file).toEqual([]);
    // 負控：違規樣本逐一回非空；StudioPanel.tsx 內的 Markdown import 是唯一例外、其 dangerouslySetInnerHTML 仍不准；良性樣本回空
    const bad: Array<[string, string]> = [
      ["EvidenceTimeline.tsx", "const x = <div dangerouslySetInnerHTML={{ __html: s }} />;"],
      ["EvidenceTimeline.tsx", 'import ReactMarkdown from "react-markdown";'],
      ["EvidenceMatrixTable.tsx", 'import rehypeRaw from "rehype-raw";'],
      ["TopicPanel.tsx", 'import remarkGfm from "remark-gfm";'],
      ["AllowlistDialog.tsx", 'import { MarkdownView } from "@/components/markdown/MarkdownView";'],
      ["GatekeeperPanel.tsx", 'const M = await import("react-markdown");'],
      ["StudioPanel.tsx", "<p dangerouslySetInnerHTML={{ __html: html }} />"],
    ];
    for (const [file, sample] of bad) expect(renderViolations(file, sample), `${file}：${sample}`).not.toEqual([]);
    expect(renderViolations("StudioPanel.tsx", 'import { MarkdownView } from "@/components/markdown/MarkdownView";')).toEqual([]);
    expect(renderViolations("EvidenceTimeline.tsx", '// 註解提到 dangerouslySetInnerHTML 與 "react-markdown" 不算\nconst ok = <p>{text}</p>;')).toEqual([]);
  });
});

// ── AT_960_10_5 頁面重開與 id 不連續 ─────────────────────────────────────────────────────────

describe("AT_960_10_5 頁面重開由 REST 重建；SSE 重連首筆 id 不連續即全量重抓並去重合併", () => {
  it("AT_960_10_5 頁面重開：首屏內容由 REST 事件重建，與結束前畫面逐項相同（不依賴記憶體緩衝）", async () => {
    const first = mount({ events: range(1, 40) });
    const es = await connected(40);
    for (let seq = 41; seq <= 45; seq += 1) send(es, ev(seq));
    await waitFor(() => expect(rows()).toHaveLength(45));
    const before = rows().map((row) => row.textContent);
    first.unmount();

    mount({ events: range(1, 45) });
    await waitFor(() => expect(rows()).toHaveLength(45));
    expect(
      rows().map((row) => row.textContent),
      "重開後與結束前的畫面逐項相同",
    ).toEqual(before);
    expect(seqs()).toEqual(seqList(1, 45));
  });

  it("AT_960_10_5 連線在 REST 載入完成後才建立，網址帶 token；訂閱契約 §3 的全部事件名與 research.replay_gap、heartbeat", async () => {
    const held = mount({ events: range(1, 3), hold: true });
    await act(async () => {
      await Promise.resolve();
    });
    expect(FakeEventSource.instances, "REST 事件帳回來之前不連線").toHaveLength(0);
    held.gate.release();
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
    const es = FakeEventSource.last;
    expect(es.url).toBe(`/api/v1/stream/research/${R1}?access_token=a`);
    expect(es.names).toEqual([...RESEARCH_SSE_EVENT_TYPES, RESEARCH_REPLAY_GAP_EVENT, "heartbeat"].sort());
  });

  it("AT_960_10_5 重連後首筆 id 為 52（不是 46；沒有 research.replay_gap 訊號）：重連帶 Last-Event-ID 45，偵測到不連續即全量重抓並與串流事件去重合併；重抓完成前不渲染缺口之後的事件，任一時刻 seq 嚴格遞增、無缺漏、無重複", async () => {
    const t = mount({ events: range(1, 40) });
    const es = await connected(40);
    const watch = watchInvariant();
    for (let seq = 41; seq <= 45; seq += 1) send(es, ev(seq));
    await waitFor(() => expect(rows()).toHaveLength(45));
    expect(detailCalls(t.calls), "缺口之前沒有任何重抓").toHaveLength(0);
    expect(listCalls(t.calls)).toHaveLength(0);
    const eventRequestsBefore = eventCalls(t.calls).length;

    // 斷線：瀏覽器自己以同一個 EventSource 重連、帶最後處理的 id（45）
    act(() => es.dropRetrying());
    expect(screen.getByTestId("timeline-connection")).toHaveTextContent("重新連線中");
    expect(FakeEventSource.instances, "沿用同一個連線物件（Last-Event-ID 才不會丟）").toHaveLength(1);
    expect(lastEventIdOf(es)).toBe("45");

    // 重連後的首筆事件 id 是 52（不是 46），而且沒有送任何 research.replay_gap
    t.options.events = range(1, 52);
    t.gate.hold();
    send(es, ev(52));
    await waitFor(() => expect(screen.getByTestId("timeline-sync")).toBeInTheDocument());
    await waitFor(() => expect(t.gate.issued.length).toBeGreaterThanOrEqual(1));
    await waitFor(() => expect(detailCalls(t.calls)).toHaveLength(1));
    expect(listCalls(t.calls)).toHaveLength(1);
    expect(seqs(), "重抓完成前不渲染缺口之後的事件：畫面仍是結束前的 1 至 45").toEqual(seqList(1, 45));

    t.gate.release();
    await waitFor(() => expect(seqs()).toEqual(seqList(1, 52)));
    expect(screen.queryByTestId("timeline-sync")).toBeNull();
    expect(screen.getByTestId("timeline-count")).toHaveTextContent("共 52 筆事件");
    expect(eventCalls(t.calls).length - eventRequestsBefore, "事件帳整份重抓一次").toBe(1);
    expect(eventCalls(t.calls).at(-1)?.query.get("afterSeq"), "自 afterSeq=0 起重抓").toBe("0");
    expect(detailCalls(t.calls)).toHaveLength(1);
    expect(listCalls(t.calls)).toHaveLength(1);

    // 之後接續的事件（53、54）直接進來、不再重抓；重複與過舊的事件被忽略
    send(es, ev(53));
    send(es, ev(54));
    send(es, ev(52));
    send(es, ev(40));
    await waitFor(() => expect(seqs()).toEqual(seqList(1, 54)));
    expect(detailCalls(t.calls)).toHaveLength(1);
    expect(watch.stop(), "每個提交後的畫面都是自 1 起連續、嚴格遞增（任一時刻無缺漏、無重複）").toEqual([]);
    expect(writeCalls(t.calls), "全程只有讀取請求").toEqual([]);
  });

  it("INT-12 第一次連線就失敗、期間資料庫多了事件、之後同一個連線物件自己重連成功（沒有 Last-Event-ID 可帶、也沒有後續事件觸發缺口偵測）：重新開啟時以 REST 補抓，動態欄補齊到資料庫、seq 連續", async () => {
    const t = mount({ events: range(1, 17) });
    await waitFor(() => expect(rows()).toHaveLength(17));
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
    const es = FakeEventSource.last;
    const watch = watchInvariant();
    // 載入頁面時串流被擋（網路層錯誤）：瀏覽器自己排程重試（readyState CONNECTING），這個實例從來沒收過事件
    act(() => es.dropRetrying());
    expect(screen.getByTestId("timeline-connection")).toHaveTextContent("重新連線中");
    expect(lastEventIdOf(es), "從沒收過事件＝沒有 Last-Event-ID").toBe("");
    // 被擋期間研究繼續跑：資料庫多了 18 至 24
    t.options.events = range(1, 24);
    const before = eventCalls(t.calls).length;
    act(() => es.open());
    await waitFor(() => expect(seqs()).toEqual(seqList(1, 24)));
    expect(screen.getByTestId("timeline-connection")).toHaveTextContent("即時連線中");
    expect(eventCalls(t.calls).length - before, "重新開啟時事件帳整份補抓一次").toBe(1);
    expect(FakeEventSource.instances, "沿用同一個連線物件").toHaveLength(1);
    // 之後的即時事件直接接續（不再被誤判成缺口）
    send(es, ev(25));
    await waitFor(() => expect(seqs()).toEqual(seqList(1, 25)));
    expect(eventCalls(t.calls).length - before, "接續的事件不再重抓").toBe(1);
    expect(watch.stop(), "每個提交後的畫面都是自 1 起連續、嚴格遞增").toEqual([]);
  });

  it("INT-12 對照：乾淨的第一次開啟（沒出過錯）不多補抓；出過錯後的每次重新開啟各補抓一次", async () => {
    const t = mount({ events: range(1, 3) });
    const es = await connected(3);
    await waitFor(() => expect(screen.getByTestId("timeline-connection")).toHaveTextContent("即時連線中"));
    const afterOpen = eventCalls(t.calls).length;
    act(() => es.open());
    expect(eventCalls(t.calls).length, "沒出過錯的 open 不補抓").toBe(afterOpen);
    for (let round = 1; round <= 2; round += 1) {
      act(() => es.dropRetrying());
      t.options.events = range(1, 3 + round);
      act(() => es.open());
      await waitFor(() => expect(seqs()).toEqual(seqList(1, 3 + round)));
      expect(eventCalls(t.calls).length - afterOpen, `第 ${round} 次斷線重連後累計補抓 ${round} 次`).toBe(round);
    }
  });

  it("AT_960_10_5 缺口補不齊（重抓一直失敗）：有限次重試後顯示警示與「重新同步」，畫面只有缺口之前的連續事件；修好後按「重新同步」補齊", async () => {
    const user = userEvent.setup();
    let broken = false;
    const t = mount({
      events: range(1, 3),
      stub: { overrides: (call) => (broken && call.method === "GET" && call.path.endsWith("/events") ? failure(500, { message: "事件帳暫時讀不到" }) : undefined) },
    });
    const es = await connected(3);
    broken = true;
    send(es, ev(10));
    const alert = await screen.findByTestId("timeline-sync-failed");
    expect(alert).toHaveTextContent("缺少第 4 筆起的事件");
    expect(alert).toHaveTextContent("缺口之後的 1 筆事件先不顯示");
    expect(seqs(), "缺口之後的事件不渲染").toEqual([1, 2, 3]);
    expect(screen.queryByTestId("timeline-sync")).toBeNull();
    expect(eventCalls(t.calls).length, "首次載入一次、同步最多三次").toBeLessThanOrEqual(1 + 3);
    broken = false;
    t.options.events = range(1, 10);
    await user.click(within(alert).getByRole("button", { name: "重新同步" }));
    await waitFor(() => expect(seqs()).toEqual(seqList(1, 10)));
    expect(screen.queryByTestId("timeline-sync-failed")).toBeNull();
  });

  it("AT_960_10_5 連線被瀏覽器放棄（CLOSED）：退避後以新 token 重建連線，重新開啟時以 REST 補抓一次；沒有 EventSource 的環境顯示說明", async () => {
    const renewal: Stub = {
      overrides: (call) => (call.method === "POST" && call.path === "/api/v1/auth/refresh" ? { data: { accessToken: "a2", refreshToken: "r2", expiresIn: 3600, role: "OPERATOR" } } : undefined),
    };
    const t = mount({ events: range(1, 2), stub: renewal });
    const es = await connected(2);
    expect(es.url).toContain("access_token=a");
    const before = eventCalls(t.calls).length;
    act(() => es.dropClosed());
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(2));
    const rebuilt = FakeEventSource.last;
    expect(rebuilt).not.toBe(es);
    expect(rebuilt.url, "重建時先換新 token").toBe(`/api/v1/stream/research/${R1}?access_token=a2`);
    act(() => rebuilt.open());
    await waitFor(() => expect(screen.getByTestId("timeline-connection")).toHaveTextContent("即時連線中"));
    await waitFor(() => expect(eventCalls(t.calls).length).toBe(before + 1));
  });

  it("AT_960_10_5 連續失敗超過上限（61 次）：停手、顯示「即時連線中斷，改以定時重新整理」與「重新連線」，不無止境重試；按「重新連線」重新建立連線", async () => {
    const user = userEvent.setup();
    mount({ events: range(1, 2), props: { backoffMs: () => 1 } });
    await connected(2);
    for (let i = 0; i < 61; i += 1) {
      const before = FakeEventSource.instances.length;
      act(() => FakeEventSource.last.dropClosed());
      if (i < 60) await waitFor(() => expect(FakeEventSource.instances).toHaveLength(before + 1));
    }
    await waitFor(() => expect(screen.getByTestId("timeline-connection")).toHaveTextContent("即時連線中斷，改以定時重新整理"));
    expect(screen.getByTestId("research-timeline")).toHaveAttribute("data-connection", "failed");
    const created = FakeEventSource.instances.length;
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 30));
    });
    expect(FakeEventSource.instances, "停手後不再建立連線").toHaveLength(created);
    await user.click(screen.getByRole("button", { name: "重新連線" }));
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(created + 1));
    act(() => FakeEventSource.last.open());
    await waitFor(() => expect(screen.getByTestId("timeline-connection")).toHaveTextContent("即時連線中"));
    expect(screen.queryByRole("button", { name: "重新連線" })).toBeNull();
  }, 20000);

  it("AT_960_10_5 串流事件讓相關資料保持新鮮：step／run 事件讓專案詳情重抓、source 讓來源重抓、evidence 讓證據矩陣重抓；連續事件去抖成一次；警示等事件不重抓", async () => {
    FakeEventSource.reset();
    vi.stubGlobal("EventSource", FakeEventSource);
    const api = stubResearchApi({ events: range(1, 2) });
    function Probe() {
      useResearchProject(R1);
      useResearchSources(R1);
      useResearchEvidence(R1);
      return <EvidenceTimeline researchId={R1} refreshDebounceMs={10} syncRetryMs={5} backoffMs={() => 5} />;
    }
    renderResearch(<Probe />);
    const es = await connected(2);
    const count = (pattern: RegExp) => callsOf(api.calls, "GET", pattern).length;
    const detailPath = /^\/api\/v1\/research\/projects\/[^/]+$/;
    await waitFor(() => expect([count(detailPath), count(/\/sources$/), count(/\/evidence$/)]).toEqual([1, 1, 1]));

    send(es, ev(3, "research.alert", { kind: "DENIED_FETCH", detail: "x" }));
    await waitFor(() => expect(rows()).toHaveLength(3));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 40));
    });
    expect([count(detailPath), count(/\/sources$/), count(/\/evidence$/)], "警示事件不重抓任何資料").toEqual([1, 1, 1]);

    send(es, ev(4, "research.evidence"));
    send(es, ev(5, "research.evidence"));
    send(es, ev(6, "research.evidence"));
    await waitFor(() => expect(count(/\/evidence$/)).toBe(2));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 40));
    });
    expect(count(/\/evidence$/), "三筆連續的證據事件去抖成一次重抓").toBe(2);
    expect(count(detailPath)).toBe(1);

    send(es, ev(7, "research.source", { sourceNo: "S-009", layer: "OSS", tier: "T2", verification: "V3", title: "新來源", fetchOutcome: "OK" }));
    await waitFor(() => expect(count(/\/sources$/)).toBe(2));
    send(es, ev(8, "research.step", { flowStep: "topic", flowPhase: "EVIDENCE_READY", flowStatus: "IDLE", flowDetail: "" }));
    await waitFor(() => expect(count(detailPath)).toBe(2));
    expect(writeCalls(api.calls)).toEqual([]);
  });

  it("AT_960_10_5 沒有 EventSource 的環境：顯示說明、不建立任何連線（改靠 REST 輪詢），事件照常由 REST 顯示", async () => {
    mount({ events: range(1, 2), stream: false });
    await waitFor(() => expect(rows()).toHaveLength(2));
    expect(screen.getByTestId("timeline-connection")).toHaveTextContent("此瀏覽器不支援即時連線");
    expect(FakeEventSource.instances).toHaveLength(0);
  });

  it("AT_960_10_5 損毀的資料行（不是 JSON、沒有 eventType）被略過，不讓串流掛掉；之後的事件照常顯示", async () => {
    mount({ events: range(1, 2) });
    const es = await connected(2);
    act(() => {
      es.emit("research.run", "{oops", "3");
      es.emit("research.run", { seq: 3, payload: {} }, "3");
    });
    send(es, ev(3));
    await waitFor(() => expect(seqs()).toEqual([1, 2, 3]));
  });

  it("AT_960_10_5 載入失敗顯示原因與「重試」（不當成沒有動態）；REST 回空時顯示「還沒有動態」", async () => {
    const user = userEvent.setup();
    let broken = true;
    mount({ stub: { overrides: (call) => (broken && call.method === "GET" && call.path.endsWith("/events") ? failure(503, { message: "事件帳不可用" }) : undefined) } });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("無法載入研究動態");
    expect(screen.queryByText("還沒有動態")).toBeNull();
    expect(FakeEventSource.instances, "沒有事件帳基線就不連線").toHaveLength(0);
    broken = false;
    await user.click(within(alert).getByRole("button", { name: "重試" }));
    await waitFor(() => expect(rows()).toHaveLength(3));

    FakeEventSource.reset();
    mount({ events: [] });
    expect(await screen.findByText("還沒有動態")).toBeInTheDocument();
  });

  it("AT_960_10_5 超過 500 筆：只渲染最近 500 筆並提示折疊，按「顯示全部」展開；事件數照實計", async () => {
    const user = userEvent.setup();
    mount({ events: range(1, 520) });
    await waitFor(() => expect(rows()).toHaveLength(500));
    expect(seqs()[0]).toBe(21);
    expect(screen.getByText(/較早的 20 筆事件已折疊/)).toBeInTheDocument();
    expect(screen.getByTestId("timeline-count")).toHaveTextContent("共 520 筆事件");
    await user.click(screen.getByRole("button", { name: "顯示全部 520 筆" }));
    expect(rows()).toHaveLength(520);
    expect(seqs()).toEqual(seqList(1, 520));
  });
});

// ── AT_960_10_7 延遲量測 ──────────────────────────────────────────────────────────────

describe("AT_960_10_7 事件自 emitted_at 到 rendered_at 的延遲量測函式", () => {
  const BASE = Date.parse("2026-11-02T10:00:00+08:00");
  /** 同一個瞬間的 +08:00 寫法（毫秒精度）。 */
  const plus8 = (ms: number): string => `${new Date(ms + 8 * 3_600_000).toISOString().slice(0, 23)}+08:00`;
  const latencyOf = (i: number): number => ((i * 53) % 480) + 20;

  it("AT_960_10_7 200 筆合成事件：兩個帶 offset 的時間戳相減（兩邊用不同的時區寫法）；P95 等於參考實作；沒有 emittedAt 的 20 筆計入 unmeasured、不是 0", () => {
    const samples: Array<number | null> = [];
    const known: number[] = [];
    for (let i = 0; i < 200; i += 1) {
      const emittedMs = BASE + i * 10;
      const event: { emittedAt?: string } = i % 10 === 9 ? {} : { emittedAt: plus8(emittedMs) };
      const renderedAt = new Date(emittedMs + latencyOf(i)).toISOString(); // Z 寫法
      const got = renderLatencyMs(event, renderedAt);
      samples.push(got);
      if (event.emittedAt !== undefined) {
        expect(got, `第 ${i} 筆`).toBe(latencyOf(i));
        known.push(latencyOf(i));
      } else expect(got, `第 ${i} 筆沒有 emittedAt`).toBeNull();
    }
    const summary = latencySummary(samples);
    expect(summary.measured).toBe(180);
    expect(summary.unmeasured).toBe(20);
    // 參考實作（以「累計占比」定義，獨立於產品碼的名次公式）：最小的值 v，使得不大於 v 的樣本占比至少 95%
    const sorted = [...known].sort((a, b) => a - b);
    const reference = sorted.find((v) => sorted.filter((x) => x <= v).length / sorted.length >= 0.95);
    expect(summary.p95).toBe(reference);
    expect(summary.p95).toBeLessThan(500);
    expect(percentile(known, 0.95)).toBe(reference);
  });

  it("AT_960_10_7 量不到就是量不到：沒有 emittedAt、為 null、沒有 offset 的 naive 時間戳、解不出的字串都回 null（不是 0）；負值（時鐘偏差）照實回傳；number 與 Date 的 renderedAt 等價", () => {
    const rendered = "2026-11-02T10:00:01+08:00";
    expect(renderLatencyMs({}, rendered)).toBeNull();
    expect(renderLatencyMs({ emittedAt: null }, rendered)).toBeNull();
    expect(renderLatencyMs({ emittedAt: "" }, rendered)).toBeNull();
    expect(renderLatencyMs({ emittedAt: "2026-11-02T10:00:00" }, rendered), "naive 時間戳不可猜時區").toBeNull();
    expect(renderLatencyMs({ emittedAt: "2026-11-02T10:00:00+08:00" }, "2026-11-02T10:00:01")).toBeNull();
    expect(renderLatencyMs({ emittedAt: "not a time+08:00" }, rendered)).toBeNull();
    expect(renderLatencyMs({ emittedAt: "2026-11-02T10:00:00+08:00" }, rendered)).toBe(1000);
    expect(renderLatencyMs({ emittedAt: "2026-11-02T10:00:00+08:00" }, "2026-11-02T10:00:00+08:00"), "相同瞬間是 0，不是 null").toBe(0);
    expect(renderLatencyMs({ emittedAt: "2026-11-02T02:00:00Z" }, "2026-11-02T10:00:01+08:00"), "Z 與 +08:00 是同一個瞬間").toBe(1000);
    expect(renderLatencyMs({ emittedAt: "2026-11-02T10:00:02+08:00" }, rendered)).toBe(-1000);
    const ms = Date.parse(rendered);
    expect(renderLatencyMs({ emittedAt: "2026-11-02T10:00:00+08:00" }, ms)).toBe(1000);
    expect(renderLatencyMs({ emittedAt: "2026-11-02T10:00:00+08:00" }, new Date(ms))).toBe(1000);
    expect(latencySummary([])).toEqual({ measured: 0, unmeasured: 0, p95: null });
    expect(latencySummary([null, null])).toEqual({ measured: 0, unmeasured: 2, p95: null });
    expect(percentile([5], 0.95)).toBe(5);
    expect(percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20], 0.95)).toBe(19);
  });

  it("AT_960_10_7 emittedAt 的三種來源：頂層 emittedAt（帶 offset 的字串）、payload.emitted_at 與 payload.emittedAt（epoch 毫秒或帶 offset 的字串；後端測試替身放 payload.emitted_at 的 epoch 毫秒）；頂層優先；數字是絕對瞬間", () => {
    const base = { seq: 1, eventType: "research.run", payload: {}, occurredAt: at(1) };
    const emitted = Date.parse("2026-11-02T10:00:00+08:00");
    const rendered = "2026-11-02T10:00:00.250+08:00";
    const fromTop = parseTimelineEvent({ ...base, emittedAt: "2026-11-02T10:00:00+08:00" });
    const fromSnake = parseTimelineEvent({ ...base, payload: { emitted_at: emitted } });
    const fromCamel = parseTimelineEvent({ ...base, payload: { emittedAt: "2026-11-02T02:00:00Z" } });
    const both = parseTimelineEvent({ ...base, emittedAt: "2026-11-02T10:00:00+08:00", payload: { emitted_at: emitted + 5000 } });
    for (const [name, event] of [
      ["頂層字串", fromTop],
      ["payload.emitted_at 數字", fromSnake],
      ["payload.emittedAt 字串", fromCamel],
    ] as const)
      expect(renderLatencyMs(event as TimelineEvent, rendered), name).toBe(250);
    expect(renderLatencyMs(both as TimelineEvent, rendered), "頂層優先於 payload").toBe(250);
    for (const bad of [{ emitted_at: "壞的" }, { emitted_at: Number.NaN }, { emitted_at: {} }, { emitted_at: "" }]) {
      const event = parseTimelineEvent({ ...base, payload: bad }) as TimelineEvent;
      expect(event.emittedAt === null || typeof event.emittedAt === "string", JSON.stringify(bad)).toBe(true);
      expect(renderLatencyMs(event, rendered), `${JSON.stringify(bad)} 量不到`).toBeNull();
    }
    expect(parseTimelineEvent({ ...base })?.emittedAt).toBeNull();
    expect(parseTimelineEvent({ ...base, seq: 0 }), "seq 不合法的事件被略過").toBeNull();
    expect(parseTimelineEvent({ ...base, seq: undefined }, "7")?.seq, "data 沒有 seq 才退用 id").toBe(7);
    expect(parseTimelineEvent({ ...base, seq: 3 }, "99")?.seq, "有 data.seq 時以它為準（沿用前一則的 lastEventId 不能當身分）").toBe(3);
  });

  it("AT_960_10_7 動態欄在串流事件變成可見時記 rendered_at：延遲 P95 與量不到的筆數以 data-latency-* 暴露；REST 載入的事件不入樣", async () => {
    mount({ events: range(1, 2) });
    const es = await connected(2);
    const section = screen.getByTestId("research-timeline");
    expect(section).toHaveAttribute("data-latency-measured", "0");
    send(es, ev(3, "research.evidence", {}, { emittedAt: new Date(Date.now() - 250).toISOString() }));
    send(es, ev(4)); // 沒有 emittedAt
    send(es, ev(5, "research.evidence", {}, { emittedAt: new Date(Date.now() - 100).toISOString() }));
    await waitFor(() => expect(rows()).toHaveLength(5));
    await waitFor(() => expect(section).toHaveAttribute("data-latency-measured", "2"));
    expect(section).toHaveAttribute("data-latency-unmeasured", "1");
    const p95 = Number(section.getAttribute("data-latency-p95-ms"));
    expect(p95, "P95 取較大的一筆（約 250 毫秒）").toBeGreaterThanOrEqual(250);
    expect(p95).toBeLessThan(5000);
  });

  it("AT_960_10_7 後端測試替身的事件形狀（payload.emitted_at＝epoch 毫秒）也量得到；REST 重抓回來的同 seq 事件（沒有 emittedAt）不會把已量到的樣本洗掉", async () => {
    const t = mount({ events: range(1, 2) });
    const es = await connected(2);
    const section = screen.getByTestId("research-timeline");
    send(es, ev(3, "research.step", { flowStep: "topic", emitted_at: Date.now() - 300 }));
    await waitFor(() => expect(section).toHaveAttribute("data-latency-measured", "1"));
    expect(Number(section.getAttribute("data-latency-p95-ms"))).toBeGreaterThanOrEqual(300);
    t.options.events = range(1, 3);
    send(es, ev(9)); // 缺口：全量重抓，REST 的第 3 筆沒有 emittedAt
    await waitFor(() => expect(screen.getByTestId("timeline-count")).toHaveTextContent("共 3 筆事件"));
    expect(section).toHaveAttribute("data-latency-measured", "1");
  });
});

// ── AT_960_10_8 research.replay_gap ───────────────────────────────────────────────────────

describe("AT_960_10_8 收到 research.replay_gap 訊號即全量重抓並與後續 SSE 去重合併，訊號本身不顯示為事件", () => {
  it("AT_960_10_8 畫面已有 1 至 5；重連後先送訊號 {fromSeq:6,toSeq:40}（無 id 行）再送 41 至 45：收到訊號即重抓（專案詳情、專案列表、事件自 afterSeq=0），重抓完成前不渲染訊號之後的事件；訊號不顯示、不計入事件數、不改變 Last-Event-ID", async () => {
    const t = mount({ events: range(1, 4) });
    const es = await connected(4);
    send(es, ev(5));
    await waitFor(() => expect(seqs()).toEqual(seqList(1, 5)));
    expect(lastEventIdOf(es), "串流上最後處理的 id 是 5").toBe("5");
    act(() => es.dropRetrying());

    const watch = watchInvariant();
    t.options.events = range(1, 45);
    t.gate.hold();
    act(() => {
      es.emit(RESEARCH_REPLAY_GAP_EVENT, { fromSeq: 6, toSeq: 40 });
    });
    expect(lastEventIdOf(es), "訊號沒有 id 行：最後處理的 id 不變").toBe("5");
    await waitFor(() => expect(detailCalls(t.calls)).toHaveLength(1));
    expect(listCalls(t.calls)).toHaveLength(1);
    await waitFor(() => expect(t.gate.issued).toHaveLength(1));
    expect(t.gate.issued[0]).toMatch(/afterSeq=0/);

    for (let seq = 41; seq <= 45; seq += 1) send(es, ev(seq));
    expect(seqs(), "重抓完成前不渲染訊號之後的事件").toEqual(seqList(1, 5));
    expect(screen.getByTestId("timeline-sync")).toBeInTheDocument();

    t.gate.release();
    await waitFor(() => expect(seqs()).toEqual(seqList(1, 45)));
    expect(screen.queryByTestId("timeline-sync")).toBeNull();
    expect(screen.getByTestId("timeline-count"), "訊號不計入事件數").toHaveTextContent("共 45 筆事件");
    expect(screen.queryByText(RESEARCH_REPLAY_GAP_EVENT)).toBeNull();
    expect(rows().some((row) => row.getAttribute("data-event-type") === RESEARCH_REPLAY_GAP_EVENT)).toBe(false);
    expect(detailCalls(t.calls)).toHaveLength(1);
    expect(writeCalls(t.calls), "全程只有讀取請求").toEqual([]);
    // 最後處理的 seq 仍是實際最大 seq（45）：45 是重複、46 是接續（不再觸發重抓）
    send(es, ev(45));
    send(es, ev(46));
    await waitFor(() => expect(seqs()).toEqual(seqList(1, 46)));
    expect(detailCalls(t.calls)).toHaveLength(1);
    expect(watch.stop(), "每個提交後的畫面都是自 1 起連續、嚴格遞增").toEqual([]);
  });

  it("AT_960_10_8 第二組：訊號之後送的事件 id 為 6 起且連續——訊號本身即觸發重抓（不是靠 id 不連續），連續的事件在重抓完成前同樣不渲染", async () => {
    const t = mount({ events: range(1, 5) });
    const es = await connected(5);
    const watch = watchInvariant();
    t.options.events = range(1, 45);
    t.gate.hold();
    act(() => {
      es.emit(RESEARCH_REPLAY_GAP_EVENT, { fromSeq: 6, toSeq: 40 });
    });
    for (let seq = 6; seq <= 8; seq += 1) send(es, ev(seq));
    await waitFor(() => expect(detailCalls(t.calls)).toHaveLength(1));
    expect(listCalls(t.calls)).toHaveLength(1);
    expect(seqs(), "即使 id 連續（6、7、8），重抓完成前也不渲染").toEqual(seqList(1, 5));
    t.gate.release();
    await waitFor(() => expect(seqs()).toEqual(seqList(1, 45)));
    expect(detailCalls(t.calls), "連續的事件沒有再觸發第二次重抓").toHaveLength(1);
    expect(watch.stop(), "每個提交後的畫面都是自 1 起連續、嚴格遞增").toEqual([]);
  });

  it("AT_960_10_8 事件帳整份重抓：單頁上限 500，truncated 為真時以 nextSeq 續抓（1,100 筆分三頁）；形狀不合的訊號仍觸發重抓", async () => {
    const t = mount({ events: range(1, 5) });
    const es = await connected(5);
    t.options.events = range(1, 1100);
    const before = eventCalls(t.calls).length;
    act(() => {
      es.emit(RESEARCH_REPLAY_GAP_EVENT, "not json");
    });
    await waitFor(() => expect(screen.getByTestId("timeline-count")).toHaveTextContent("共 1100 筆事件"));
    const pages = eventCalls(t.calls).slice(before);
    expect(pages.map((c) => c.query.get("afterSeq"))).toEqual(["0", "500", "1000"]);
    expect(pages.every((c) => c.query.get("limit") === "500")).toBe(true);
    expect(detailCalls(t.calls)).toHaveLength(1);
    expect(listCalls(t.calls)).toHaveLength(1);
  });
});

// ── 純函式（時間軸合併與缺口）────────────────────────────────────────────────────────────

describe("AT_960_10_5 時間軸合併純函式：依 seq 去重、自 1 起連續的前綴、障壁", () => {
  const e = (seq: number) => ({ seq });
  it("AT_960_10_5 mergeEventsBySeq：升冪聯集、同 seq 只留一筆且 REST（base）優先；contiguousPrefix 在第一個缺口截斷", () => {
    const merged = mergeEventsBySeq(
      [
        { seq: 1, from: "rest" },
        { seq: 2, from: "rest" },
      ],
      [
        { seq: 2, from: "live" },
        { seq: 4, from: "live" },
        { seq: 3, from: "live" },
      ],
    );
    expect(merged).toEqual([
      { seq: 1, from: "rest" },
      { seq: 2, from: "rest" },
      { seq: 3, from: "live" },
      { seq: 4, from: "live" },
    ]);
    expect(contiguousPrefix([e(1), e(2), e(4), e(5)])).toEqual([e(1), e(2)]);
    expect(contiguousPrefix([e(2), e(3)]), "不是自 1 起就一個都不渲染").toEqual([]);
    expect(contiguousPrefix([])).toEqual([]);
  });

  it("AT_960_10_5 timelineView：缺口之後扣住（held）並回缺口起點；障壁只放行 seq 不超過它的事件；lastSeq 含被扣住的", () => {
    const rest = [e(1), e(2), e(3)];
    expect(timelineView(rest, [e(5), e(6)])).toMatchObject({ visible: [e(1), e(2), e(3)], held: 2, gapFrom: 4, lastSeq: 6 });
    expect(timelineView(rest, [e(4), e(5)])).toMatchObject({ held: 0, gapFrom: null, lastSeq: 5 });
    expect(timelineView([e(1), e(2), e(3), e(4)], [e(5)], 2)).toMatchObject({ visible: [e(1), e(2)], held: 3, lastSeq: 5 });
    expect(timelineView([], [])).toEqual({ visible: [], held: 0, gapFrom: null, lastSeq: 0 });
  });
});
