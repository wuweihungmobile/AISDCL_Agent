/**
 * 內環看板（TCS-ResearchToPRD-P2-20261107 AT-962-11-2～11-8、11-E-1～11-E-3）：五欄順序與計數、SSE 到 DOM ≤500 ms（假計時器＋假 EventSource、不用牆鐘）、
 * 三條串流任一幀觸發去抖重抓（100 ms；99／101 ms 邊界）、斷線回補、深連結、Bridge 不可達、靜態判準、VIEWER、缺值不猜。
 */
import { act, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { KANBAN_DEBOUNCE_MS, KANBAN_SSE_TO_DOM_MAX_MS, READONLY_TITLE, BUILD_DISABLED_TEXT } from "@/lib/domain/research";
import { CONSOLE_PROJECT_ID, R3 } from "@/tests/fixtures/research/ids";
import { KANBAN, RUN_ID, kanbanUnreachable, kanbanWith } from "@/tests/fixtures/research/p2";
import { FakeEventSource } from "@/tests/helpers/fakeEventSource";
import { renderResearch, stubResearchApi } from "@/tests/helpers/research";
import { KanbanBoard } from "./KanbanBoard";

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

const flushMicro = () => act(async () => void (await vi.advanceTimersByTimeAsync(0)));
const advance = (ms: number) => act(async () => void (await vi.advanceTimersByTimeAsync(ms)));
const settle = async () => {
  for (let i = 0; i < 6; i += 1) await flushMicro();
};
const researchStream = () => FakeEventSource.instances.find((es) => es.url.includes("/stream/research/"))!;
const runStream = () => FakeEventSource.lastOf("logs")!;
const kanbanCalls = (calls: Array<{ method: string; path: string }>) => calls.filter((c) => c.method === "GET" && c.path === `/api/v1/research/projects/${R3}/kanban`).length;

async function mount(role: "ADMIN" | "OPERATOR" | "VIEWER" = "OPERATOR", kanban = KANBAN) {
  const stub = stubResearchApi({ kanban });
  const view = renderResearch(<KanbanBoard researchId={R3} />, role);
  await settle();
  return { ...stub, ...view };
}

beforeEach(() => {
  FakeEventSource.reset();
  vi.stubGlobal("EventSource", FakeEventSource);
  vi.useFakeTimers();
  window.sessionStorage.clear();
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("看板渲染", () => {
  it("AT_962_11_2 五欄順序固定、計數與狀態文字等於資料、RTM 欄標諮詢視圖", async () => {
    await mount();
    const cols = [...screen.getByTestId("kanban-columns").querySelectorAll("[data-testid^='kanban-col-']")];
    expect(cols.map((c) => c.getAttribute("data-testid"))).toEqual(["kanban-col-decompose", "kanban-col-tcs", "kanban-col-implement", "kanban-col-healing", "kanban-col-regression"]);
    expect(cols.map((c) => c.querySelector("h4")?.firstChild?.textContent)).toEqual(["Task 拆解", "測試規格產生", "程式碼實作", "自癒修復", "回歸驗收"]);
    expect(screen.getByTestId("kanban-badge-decompose").textContent).toBe("已完成");
    expect(screen.getByTestId("kanban-badge-implement").textContent).toBe("進行中");
    const impl = screen.getByTestId("kanban-col-implement").textContent ?? "";
    expect(impl).toContain("任務總數5");
    expect(impl).toContain("成功任務3");
    expect(impl).toContain("重試中1");
    expect(screen.getByTestId("kanban-col-decompose").textContent).toContain("任務數5");
    expect(screen.getByTestId("kanban-col-healing").textContent).toContain("重試上限3");
    const reg = screen.getByTestId("kanban-col-regression");
    expect(within(reg).getByTestId("kanban-advisory").textContent).toBe("諮詢視圖");
    expect(reg.textContent).toContain("6／10（60%）");
    expect(screen.queryByTestId("kanban-stale-banner")).toBeNull();
  });
});

describe("SSE 與去抖", () => {
  it("AT_962_11_3 幀到 DOM 不超過 500 ms（假計時器、不用牆鐘）；常數取單一出處；負控：人為延後 501 ms 時斷言函式回報違規", async () => {
    const { calls, options } = await mount();
    expect(KANBAN_SSE_TO_DOM_MAX_MS).toBe(500);
    expect(KANBAN_DEBOUNCE_MS).toBe(100);
    act(() => {
      researchStream().open();
      runStream().open();
    });
    const before = kanbanCalls(calls);
    const changed = (total: number): typeof KANBAN => ({ ...KANBAN, columns: { ...KANBAN.columns, implement: { ...KANBAN.columns.implement, tasks: { ...KANBAN.columns.implement.tasks, total } } } });
    /** 自「幀到達（含人為延後）」起逐毫秒推進直到 DOM 反映新值；回量測毫秒數與重抓是否在 100 ms 內發出。 */
    async function measure(total: number, extraDelay: number): Promise<{ ms: number; refetchBy100: boolean }> {
      options.kanban = changed(total);
      const base = kanbanCalls(calls);
      setTimeout(() => act(() => runStream().emit("status-change", { seq: total, ts: "t", runStatus: "RUNNING", bridgeStatus: "RUNNING", reason: "x" }, String(total))), extraDelay);
      let ms = 0;
      let refetchBy100 = false;
      while (!(screen.getByTestId("kanban-col-implement").textContent ?? "").includes(`任務總數${total}`)) {
        await advance(1);
        ms += 1;
        if (ms === extraDelay + KANBAN_DEBOUNCE_MS && kanbanCalls(calls) > base) refetchBy100 = true;
        if (ms > 3000) throw new Error("DOM 沒有更新");
      }
      return { ms, refetchBy100 };
    }
    const within500 = (ms: number): string | null => (ms > KANBAN_SSE_TO_DOM_MAX_MS ? `量測 ${ms} ms 超過 ${KANBAN_SSE_TO_DOM_MAX_MS} ms` : null);
    const normal = await measure(9, 0);
    expect(kanbanCalls(calls)).toBeGreaterThan(before);
    expect(normal.refetchBy100).toBe(true);
    expect(normal.ms).toBeLessThanOrEqual(KANBAN_SSE_TO_DOM_MAX_MS);
    expect(within500(normal.ms)).toBeNull();
    const late = await measure(11, 501);
    expect(late.ms).toBeGreaterThan(KANBAN_SSE_TO_DOM_MAX_MS);
    expect(within500(late.ms)).not.toBeNull();
  });

  it("AT_962_11_4 三條串流任一幀都引發重抓；同一去抖窗內（99 ms）三幀只重抓一次", async () => {
    const { calls } = await mount();
    act(() => {
      researchStream().open();
      runStream().open();
    });
    const frames: Array<[() => FakeEventSource, string]> = [
      [researchStream, "research.step"],
      [researchStream, "research.gate"],
      [researchStream, "research.delivery"],
      [runStream, "status-change"],
      [runStream, "review-request"],
      [runStream, "alert"],
    ];
    for (const [stream, name] of frames) {
      const base = kanbanCalls(calls);
      act(() => stream().emit(name, {}));
      await advance(KANBAN_DEBOUNCE_MS + 5);
      expect(kanbanCalls(calls), name).toBe(base + 1);
    }
    const base = kanbanCalls(calls);
    act(() => researchStream().emit("research.step", {}));
    await advance(40);
    act(() => runStream().emit("status-change", {}));
    await advance(40);
    act(() => researchStream().emit("research.gate", {}));
    await advance(KANBAN_DEBOUNCE_MS + 5);
    expect(kanbanCalls(calls)).toBe(base + 1);
  });

  it("AT_962_11_E_3 去抖邊界：兩幀相隔 99 ms 重抓一次、相隔 101 ms 各自觸發重抓兩次", async () => {
    const { calls } = await mount();
    act(() => researchStream().open());
    let base = kanbanCalls(calls);
    act(() => researchStream().emit("research.step", {}));
    await advance(99);
    act(() => researchStream().emit("research.step", {}));
    await advance(KANBAN_DEBOUNCE_MS + 5);
    expect(kanbanCalls(calls)).toBe(base + 1);
    base = kanbanCalls(calls);
    act(() => researchStream().emit("research.step", {}));
    await advance(101);
    act(() => researchStream().emit("research.step", {}));
    await advance(KANBAN_DEBOUNCE_MS + 5);
    expect(kanbanCalls(calls)).toBe(base + 2);
  });

  it("AT_962_11_5 斷線回補：瀏覽器自己以 Last-Event-ID 重連（同一實例）；重連再開啟與 replay_gap 都以 REST 全量重抓，不顯示過期值", async () => {
    const { calls, options } = await mount();
    const es = researchStream();
    const count = FakeEventSource.instances.length;
    act(() => {
      es.open();
      es.emit("research.step", {}, "7");
    });
    await advance(KANBAN_DEBOUNCE_MS + 5);
    let base = kanbanCalls(calls);
    act(() => es.dropRetrying());
    expect(FakeEventSource.instances).toHaveLength(count); // 沒有另建連線：瀏覽器自己重連
    act(() => es.open());
    await settle();
    expect((es as unknown as { lastId: string }).lastId).toBe("7"); // 重連請求帶的 Last-Event-ID
    expect(kanbanCalls(calls)).toBe(base + 1); // 重連再開啟＝全量重抓（不等去抖）
    base = kanbanCalls(calls);
    options.kanban = kanbanWith({ columns: { ...KANBAN.columns, decompose: { ...KANBAN.columns.decompose, tasksCount: 42 } } });
    act(() => es.emit("research.replay_gap", { toSeq: 99 }));
    await settle();
    expect(kanbanCalls(calls)).toBe(base + 1);
    expect(screen.getByTestId("kanban-col-decompose").textContent).toContain("任務數42");
  });
});

describe("深連結與狀態", () => {
  it("AT_962_11_6 每欄深連結帶 researchId；未綁專案或規格變更中停用並顯示登記文案；用 Link、不呼叫新端點", async () => {
    const bound = await mount();
    for (const col of ["decompose", "tcs", "implement", "healing", "regression"]) {
      expect(screen.getByTestId(`kanban-exec-${col}`).getAttribute("href")).toBe(`/projects/${CONSOLE_PROJECT_ID}/execute?researchId=${R3}`);
      expect(screen.getByTestId(`kanban-monitor-${col}`).getAttribute("href")).toBe(`/projects/${CONSOLE_PROJECT_ID}/monitor?researchId=${R3}`);
    }
    expect(bound.calls.filter((c) => c.method !== "GET")).toHaveLength(0);
    bound.unmount();

    const unbound = await mount("OPERATOR", kanbanWith({ consoleProjectId: null }));
    const exec = screen.getByTestId("kanban-exec-implement");
    expect(exec.getAttribute("href")).toBeNull();
    expect(exec.getAttribute("aria-disabled")).toBe("true");
    expect(exec.getAttribute("title")).toBe(BUILD_DISABLED_TEXT.needDecomposition);
    expect(screen.getByTestId("kanban-monitor-implement").getAttribute("aria-disabled")).toBe("true");
    unbound.unmount();

    await mount("OPERATOR", kanbanWith({ scrOpen: true }));
    const blocked = screen.getByTestId("kanban-exec-implement");
    expect(blocked.getAttribute("href")).toBeNull();
    expect(blocked.getAttribute("title")).toBe(BUILD_DISABLED_TEXT.scrOpen);
    expect(screen.getByTestId("kanban-monitor-implement").getAttribute("href")).toContain("/monitor?researchId=");
  });

  it("AT_962_11_7 Bridge 不可達：橫幅含快照時間、FSM 衍生欄未知徽章、data-stale=true、DB 欄位仍在、未知欄不出現已完成", async () => {
    await mount("OPERATOR", kanbanUnreachable());
    expect(screen.getByTestId("kanban-stale-banner").textContent).toBe("Engine Bridge 無法連線，以下為 2026-11-07T09:00:00+08:00 的 DB 快照");
    expect(screen.getByTestId("kanban-board").getAttribute("data-stale")).toBe("true");
    for (const col of ["tcs", "implement", "regression"]) {
      expect(screen.getByTestId(`kanban-badge-${col}`).textContent).toBe("未知");
      expect(screen.getByTestId(`kanban-col-${col}`).textContent).not.toContain("已完成");
    }
    expect(screen.getByTestId("kanban-col-decompose").textContent).toContain("任務數5"); // DB 欄位仍顯示
    expect(screen.getByTestId("kanban-col-implement").textContent).toContain("任務總數5");
  });

  it("AT_962_11_E_2 缺值不猜：FSM 欄為 null 時對應欄寫未知，沒有 0 與完成字樣", async () => {
    await mount("OPERATOR", kanbanUnreachable());
    for (const col of ["tcs", "regression"]) {
      const text = screen.getByTestId(`kanban-col-${col}`).textContent ?? "";
      expect(text, col).toContain("未知");
      expect(text, col).not.toMatch(/0/);
      expect(text, col).not.toContain("完成");
    }
    expect(within(screen.getByTestId("kanban-col-regression")).getAllByTestId("kanban-fact-regression")[0].textContent).toBe("未知");
  });

  it("AT_962_11_E_1 VIEWER：看板可讀；登錄 SCG 與發起 SCR 停用且 title 為權限不足（唯讀角色）；導覽連結仍可點", async () => {
    await mount("VIEWER");
    const gate = screen.getByTestId("gate-register-trigger") as HTMLButtonElement;
    const scr = screen.getByTestId("scr-launch") as HTMLButtonElement;
    expect(gate.disabled).toBe(true);
    expect(gate.title).toBe(READONLY_TITLE);
    expect(scr.disabled).toBe(true);
    expect(scr.title).toBe("權限不足（唯讀角色）");
    expect(screen.getByTestId("kanban-exec-implement").getAttribute("href")).toContain("/execute?researchId=");
  });
});

describe("靜態判準", () => {
  it("AT_962_11_8 KanbanBoard／KanbanColumn 無直接網路呼叫、不 import 執行控制端點函式；動作只連既有路徑", () => {
    const dir = path.resolve(process.cwd(), "components", "domain", "research");
    const strip = (src: string) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:\\"'`])\/\/.*$/gm, "$1");
    for (const name of ["KanbanBoard.tsx", "KanbanColumn.tsx"]) {
      const src = strip(readFileSync(path.join(dir, name), "utf8"));
      expect(src, name).not.toMatch(new RegExp("\\bfetch" + "\\s*\\("));
      expect(src, name).not.toMatch(/\b(execute|pause|resume|cancel|restore)(Execution|Run)\b/i);
      expect(src, name).not.toMatch(/\bstartExecution|pauseExecution|resumeExecution|cancelExecution|restoreExecution|reviewExecution\b/);
      expect(src, name).not.toContain("axios");
    }
    // 看板的動作鈕只連這幾條既有路徑：執行中心與監控中心（由 consoleCenterHref 組出）
    const col = readFileSync(path.join(dir, "KanbanColumn.tsx"), "utf8");
    expect(col.match(/href=\{[^}]+\}/g)).toEqual(["href={link.href}"]);
    const board = strip(readFileSync(path.join(dir, "KanbanBoard.tsx"), "utf8"));
    expect([...board.matchAll(/consoleCenterHref\(bound, "(\w+)"/g)].map((m) => m[1]).sort()).toEqual(["execute", "monitor"]);
  });
});

describe("看板輔助", () => {
  it("run 串流掛在最新 run 上；沒有 run 時只訂研究串流", async () => {
    await mount("OPERATOR", kanbanWith({ latestRunId: null }));
    expect(FakeEventSource.instances.some((es) => es.url.includes("/stream/research/"))).toBe(true);
    expect(FakeEventSource.lastOf("logs")).toBeUndefined();
    expect(RUN_ID).toBeTruthy();
  });
});
