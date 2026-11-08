/**
 * 終端窗格（TCS-ResearchToPRD-P2-20261107 AT-962-13-*）：與執行中心共用串流客戶端與日誌元件、收合仍訂閱、純文字、終態 REST 回補、
 * 開合只存瀏覽器、≤500 ms（假計時器、不用牆鐘）、靜態判準（先剝註解、正規式以字串拼接組成使本檔不自我命中）。
 */
import { act, fireEvent, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FLUSH_MS } from "@/hooks/useRunStream";
import { KANBAN_SSE_TO_DOM_MAX_MS } from "@/lib/domain/research";
import { RUN_ID } from "@/tests/fixtures/research/p2";
import { FakeEventSource } from "@/tests/helpers/fakeEventSource";
import { renderResearch, stubResearchApi } from "@/tests/helpers/research";
import { TerminalPane } from "./TerminalPane";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  useParams: () => ({}),
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(""),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const T = "2026-11-07T10:00:00+08:00";
const runDetail = (status: string) => ({
  id: RUN_ID,
  projectId: "p1",
  runNumber: 1,
  status,
  bridgeStatus: status,
  autonomyLevel: 4,
  scope: { mode: "ALL", goalIds: [], taskIds: [] },
  totalTokensUsed: 0,
  tokenBudget: 1000,
  startedAt: T,
  completedSteps: 0,
  totalSteps: 0,
  lastEventSeq: 0,
  pendingReviews: [],
  bridge: { connected: true, status, checkedAt: T },
});
const logFrame = (seq: number, message: string) => ({ seq, ts: T, source: "STEP", level: "INFO", message, taskId: "t1", stepStatus: "STARTED" });
const flushMicro = () => act(async () => void (await vi.advanceTimersByTimeAsync(0)));
const advance = (ms: number) => act(async () => void (await vi.advanceTimersByTimeAsync(ms)));

function mount(props: { runId: string | null; defaultOpen?: boolean }, status = "RUNNING", extra?: NonNullable<Parameters<typeof stubResearchApi>[0]>["overrides"]) {
  stubResearchApi({
    overrides: (call) => {
      if (call.method === "GET" && call.path === `/api/v1/executions/${RUN_ID}`) return { data: runDetail(status) };
      return extra?.(call);
    },
  });
  return renderResearch(<TerminalPane {...props} />, "OPERATOR");
}
const logs = () => FakeEventSource.lastOf("logs")!;
const toggle = () => fireEvent.click(screen.getByTestId("terminal-toggle"));

beforeEach(() => {
  FakeEventSource.reset();
  vi.stubGlobal("EventSource", FakeEventSource);
  vi.useFakeTimers();
  window.localStorage.clear();
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

// ── 靜態判準（AT-962-13-2、13-E-1）：掃描函式本身可被餵夾具（負控）──────────────────────────────

/** 先剝註解（行註解不碰 `://`）；本檔的正規式一律以字串拼接組成，避免被自己的掃描命中。 */
const stripComments = (src: string): string => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:\\"'`])\/\/.*$/gm, "$1");
const FORBIDDEN: Array<[string, RegExp]> = [
  ["Web" + "Socket", new RegExp("\\bWeb" + "Socket\\b")],
  ["new Event" + "Source", new RegExp("new\\s+Event" + "Source\\b")],
  ["dangerously" + "SetInnerHTML", new RegExp("dangerously" + "SetInnerHTML")],
  ["lib/" + "sse/", new RegExp("lib\\/" + "sse\\/")],
];
const violationsOf = (src: string): string[] => FORBIDDEN.filter(([, re]) => re.test(stripComments(src))).map(([name]) => name);

function nonTestSources(dir: string, out: Array<{ file: string; src: string }> = []): Array<{ file: string; src: string }> {
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) {
      if (name !== "tests" && name !== "node_modules") nonTestSources(full, out);
    } else if (/\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name)) out.push({ file: full, src: readFileSync(full, "utf8") });
  }
  return out;
}
const RESEARCH_DIR = path.resolve(process.cwd(), "components", "domain", "research");

describe("靜態判準", () => {
  it("AT_962_13_2 TerminalPane 含兩個共用匯入；research 非測試碼（剝註解後）零命中四個禁用形態；兩個匯入只出現在 TerminalPane", () => {
    const sources = nonTestSources(RESEARCH_DIR);
    const pane = sources.find((s) => s.file.endsWith("TerminalPane.tsx"))!;
    expect(pane.src).toContain('from "@/hooks/useRunStream"');
    expect(pane.src).toContain('from "@/components/domain/execute/LiveLogCard"');
    expect(sources.length).toBeGreaterThan(20);
    for (const { file, src } of sources) expect(violationsOf(src), path.basename(file)).toEqual([]);
    const importers = (needle: string) => sources.filter((s) => s.src.includes(needle)).map((s) => path.basename(s.file));
    expect(importers('from "@/hooks/useRunStream"')).toEqual(["TerminalPane.tsx"]);
    expect(importers('from "@/components/domain/execute/LiveLogCard"')).toEqual(["TerminalPane.tsx"]);
  });

  it("AT_962_13_E_3 重用元件原地不分叉：LiveLogCard／useRunStream／LogPanel 三檔在正確路徑存在且不含研究面字樣（真正的零 diff 由 `git diff <基底>..HEAD -- <三檔>` 指令核對；TCS 列的 LogPanel 在 components/domain、不在 execute 目錄）", () => {
    const reused = [
      path.resolve(process.cwd(), "components", "domain", "execute", "LiveLogCard.tsx"),
      path.resolve(process.cwd(), "hooks", "useRunStream.ts"),
      path.resolve(process.cwd(), "components", "domain", "LogPanel.tsx"),
    ];
    for (const file of reused) {
      expect(statSync(file).isFile(), path.basename(file)).toBe(true);
      expect(/research/i.test(readFileSync(file, "utf8")), `${path.basename(file)} 不得被研究面分叉`).toBe(false);
    }
  });

  it("AT_962_13_E_1 負控：夾具含 WebSocket、new EventSource、dangerouslySetInnerHTML 各被判違規；合法夾具與只在註解出現的字樣通過（掃描能咬人）", () => {
    expect(violationsOf("const s = new Web" + "Socket('x');")).toEqual(["Web" + "Socket"]);
    expect(violationsOf("const e = new Event" + "Source('/x');")).toEqual(["new Event" + "Source"]);
    expect(violationsOf("<div dangerously" + "SetInnerHTML={{ __html: x }} />")).toEqual(["dangerously" + "SetInnerHTML"]);
    expect(violationsOf("import x from '@/lib/" + "sse/foo';")).toEqual(["lib/" + "sse/"]);
    expect(violationsOf("const ok = useRunStream(id);\n// 不用 new Event" + "Source，也不用 Web" + "Socket\n/* dangerously" + "SetInnerHTML */")).toEqual([]);
    expect(violationsOf("const url = 'https://a.example/x'; // 行尾註解")).toEqual([]);
  });
});

describe("終端窗格行為", () => {
  it("AT_962_13_E_2 runId 為 null：顯示尚無執行批次，不訂閱（EventSource 實例 0）", async () => {
    mount({ runId: null });
    await flushMicro();
    expect(screen.getByTestId("terminal-empty").textContent).toBe("尚無執行批次");
    expect(FakeEventSource.instances).toHaveLength(0);
  });

  it("AT_962_13_1 展開、收合、再展開：串流實例數不變、未被關閉；收合時不渲染日誌卡、再展開顯示收合期間累積的行", async () => {
    mount({ runId: RUN_ID });
    await flushMicro();
    const count = FakeEventSource.instances.length;
    expect(count).toBeGreaterThan(0);
    expect(screen.queryByTestId("log-card")).toBeNull(); // 預設收合
    toggle();
    expect(screen.getByTestId("log-card")).toBeDefined();
    toggle();
    expect(screen.queryByTestId("log-card")).toBeNull();
    act(() => {
      logs().open();
      logs().emit("log", logFrame(1, "收合期間的一行"), "1");
    });
    await advance(FLUSH_MS + 1);
    toggle();
    expect(FakeEventSource.instances).toHaveLength(count);
    expect(FakeEventSource.instances.every((es) => !es.closed)).toBe(true);
    expect(within(screen.getByTestId("log-box")).getByText("收合期間的一行")).toBeDefined();
  });

  it("AT_962_13_3 純文字哨兵：script、img、on* 屬性與哨兵呼叫皆為 0，可見文字不含 ESC 序列起頭", async () => {
    const sentinel = vi.fn();
    (window as unknown as Record<string, unknown>).__sentinel = sentinel;
    const { container } = mount({ runId: RUN_ID, defaultOpen: true });
    await flushMicro();
    act(() => {
      logs().open();
      logs().emit("log", logFrame(1, "<script>alert(1)</script>"), "1");
      logs().emit("log", logFrame(2, "\u001b[31mRED\u001b[0m"), "2");
      logs().emit("log", logFrame(3, '<img src=x onerror="__sentinel()">'), "3");
    });
    await advance(FLUSH_MS + 1);
    expect(container.querySelectorAll("script, img")).toHaveLength(0);
    const withOn = [...container.querySelectorAll("*")].filter((el) => [...el.attributes].some((a) => a.name.startsWith("on")));
    expect(withOn).toHaveLength(0);
    expect(sentinel).not.toHaveBeenCalled();
    expect(container.textContent ?? "").not.toContain("\u001b[");
    expect(container.textContent ?? "").toContain("RED");
    delete (window as unknown as Record<string, unknown>).__sentinel;
  });

  it("AT_962_13_4 run 終態：開啟窗格後以 afterSeq 分頁取到空頁，顯示的行序列等於各頁步驟逐行", async () => {
    const pages: Record<string, number[]> = { "": [1, 2], "2": [3, 4], "4": [5], "5": [] };
    const asked: string[] = [];
    const step = (n: number) => ({ id: `s${n}`, runId: RUN_ID, taskId: "t1", taskName: "任務", stepNumber: n, stepId: `S${n}`, attempt: 1, action: "a", status: "COMPLETED", timestamp: T });
    mount({ runId: RUN_ID }, "COMPLETED", (call) => {
      if (call.method === "GET" && call.path === `/api/v1/executions/${RUN_ID}/steps`) {
        const after = call.query.get("afterSeq") ?? "";
        asked.push(after);
        const content = (pages[after] ?? []).map(step);
        return { data: { content, page: 0, size: 200, totalElements: content.length, totalPages: 1 } };
      }
      return undefined;
    });
    await flushMicro();
    toggle();
    await advance(FLUSH_MS + 50);
    await advance(50);
    expect(asked).toEqual(["", "2", "4", "5"]);
    const box = screen.getByTestId("log-box");
    const lines = [...box.querySelectorAll("[data-testid='log-line'], div")].map((el) => el.textContent ?? "").filter((t) => /完成：任務（S\d）/.test(t));
    const order = (["S1", "S2", "S3", "S4", "S5"] as const).map((id) => (box.textContent ?? "").indexOf(`（${id}）`));
    expect(order.every((i) => i >= 0)).toBe(true);
    expect([...order].sort((a, b) => a - b)).toEqual(order);
    expect(lines.length).toBeGreaterThanOrEqual(5);
  });

  it("AT_962_13_5 開合狀態：鍵 research.terminal.open，預設收合、重載保留；localStorage 例外時預設收合且不崩潰；不進任何 API 請求", async () => {
    const { calls } = (() => {
      const stub = stubResearchApi({ overrides: (call) => (call.path === `/api/v1/executions/${RUN_ID}` ? { data: runDetail("RUNNING") } : undefined) });
      return stub;
    })();
    const first = renderResearch(<TerminalPane runId={RUN_ID} />, "OPERATOR");
    await flushMicro();
    expect(screen.getByTestId("terminal-pane").getAttribute("data-open")).toBe("false");
    toggle();
    expect(window.localStorage.getItem("research.terminal.open")).toBe("true");
    first.unmount();
    renderResearch(<TerminalPane runId={RUN_ID} />, "OPERATOR");
    await flushMicro();
    expect(screen.getByTestId("terminal-pane").getAttribute("data-open")).toBe("true");
    expect(calls.filter((c) => c.method !== "GET")).toHaveLength(0);
    expect(JSON.stringify(calls)).not.toContain("research.terminal.open");
  });

  it("AT_962_13_5 localStorage 讀寫都拋例外：以預設收合渲染、可開合、不崩潰", async () => {
    // 只對窗格自己的鍵拋例外（session 也住 Storage，不能一起壞）
    const realGet = Storage.prototype.getItem;
    const realSet = Storage.prototype.setItem;
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(function (this: Storage, key: string) {
      if (key === "research.terminal.open") throw new Error("denied");
      return realGet.call(this, key);
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(function (this: Storage, key: string, value: string) {
      if (key === "research.terminal.open") throw new Error("denied");
      realSet.call(this, key, value);
    });
    mount({ runId: RUN_ID });
    await flushMicro();
    expect(screen.getByTestId("terminal-pane").getAttribute("data-open")).toBe("false");
    toggle();
    expect(screen.getByTestId("log-card")).toBeDefined();
  });

  it("AT_962_13_6 log 幀到達至顯示不超過 500 ms（假計時器、不用牆鐘）；負控：人為延後 501 ms 時量測超界、斷言函式回報違規", async () => {
    mount({ runId: RUN_ID, defaultOpen: true });
    await flushMicro();
    act(() => logs().open());
    /** 自「幀到達（含人為延後）」起，逐毫秒推進直到 DOM 出現該行；回量測毫秒數。 */
    async function msUntilVisible(text: string, seq: number, extraDelay: number): Promise<number> {
      setTimeout(() => act(() => logs().emit("log", logFrame(seq, text), String(seq))), extraDelay);
      let ms = 0;
      while (!(screen.queryByTestId("log-box")?.textContent ?? "").includes(text)) {
        await advance(1);
        ms += 1;
        if (ms > 2000) throw new Error("行沒有出現");
      }
      return ms;
    }
    const withinBudget = (ms: number): string | null => (ms > KANBAN_SSE_TO_DOM_MAX_MS ? `量測 ${ms} ms 超過 ${KANBAN_SSE_TO_DOM_MAX_MS} ms` : null);
    const normal = await msUntilVisible("第一行", 1, 0);
    expect(normal).toBeLessThanOrEqual(KANBAN_SSE_TO_DOM_MAX_MS);
    expect(withinBudget(normal)).toBeNull();
    const delayed = await msUntilVisible("第二行", 2, 501);
    expect(delayed).toBeGreaterThan(KANBAN_SSE_TO_DOM_MAX_MS);
    expect(withinBudget(delayed)).not.toBeNull();
  });

  it("AT_962_13_7 斷線重連：同一個連線實例由瀏覽器帶 Last-Event-ID 重連；重播的舊行不重複、缺的行補回", async () => {
    mount({ runId: RUN_ID, defaultOpen: true });
    await flushMicro();
    const es = logs();
    const before = FakeEventSource.instances.length;
    act(() => {
      es.open();
      es.emit("log", logFrame(5, "第五行"), "5");
    });
    await advance(FLUSH_MS + 1);
    act(() => es.dropRetrying());
    act(() => es.open());
    expect(FakeEventSource.instances).toHaveLength(before); // 瀏覽器自己重連：同一實例
    expect((es as unknown as { lastId: string }).lastId).toBe("5"); // 重連請求帶的 Last-Event-ID
    act(() => {
      es.emit("log", logFrame(5, "第五行"), "5"); // 伺服器重播
      es.emit("log", logFrame(6, "第六行（缺的）"), "6");
    });
    await advance(FLUSH_MS + 1);
    const text = screen.getByTestId("log-box").textContent ?? "";
    expect(text.split("第五行").length - 1).toBe(1);
    expect(text).toContain("第六行（缺的）");
  });
});
