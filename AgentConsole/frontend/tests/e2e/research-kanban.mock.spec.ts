import { expect, test, type Page } from "@playwright/test";

import { buildProject, DECOMPOSITION_SIGNED, ROUTE_ADOPTED } from "../fixtures/research/build";
import { eventPage, EVENTS } from "../fixtures/research/events";
import { R3 } from "../fixtures/research/ids";
import { ALLOWLIST, CAPABILITIES_LOCAL, EVIDENCE, RECORDS_AUDIT, SOURCES } from "../fixtures/research/misc";
import { PROJECT_LIST } from "../fixtures/research/projects";
import { HEALING, KANBAN, kanbanUnreachable } from "../fixtures/research/p2";
import { collectConsoleErrors, compose, installApiMock, shellHandler, signInAs, type MockHandler } from "./mockApi";

/**
 * 研究工作區步驟 4 內環看板（ResearchToPRD P2；TCS-ResearchToPRD-P2-20261107 AT-962-11-9）——真瀏覽器、route mock 版：
 * ① SSE 幀到瀏覽器至看板 DOM commit ≤500 ms（頁內 `performance.mark` 量測，不用牆鐘估計）；
 * ② 斷線回補：瀏覽器自己重連（同一個連線實例）再開啟後與 `replay_gap` 都以 REST 全量重抓，畫面不顯示過期值；
 * ③ Bridge 不可達態：橫幅加快照時間、FSM 衍生欄「未知」徽章、不渲染空看板。
 * EventSource 以頁內的可控替身取代（`page.route` 的 fulfill 做不到「連線一直開著、事件陸續送達」；這裡只需要「由測試決定何時送哪一幀」）。
 * 判定指令：npx playwright test tests/e2e/research-kanban.mock.spec.ts --output=<各自目錄>（cwd＝AgentConsole/frontend；E2E_WEB_PORT 避開他人）
 */
const BASE = `/api/v1/research/projects/${R3}`;

type World = { kanban: typeof KANBAN };

function backend(world: World): MockHandler {
  return (call) => {
    const p = call.path;
    if (p === "/api/v1/research/capabilities") return { data: CAPABILITIES_LOCAL };
    if (p === "/api/v1/research/allowlist") return { data: ALLOWLIST };
    if (p === "/api/v1/research/projects") return { data: PROJECT_LIST };
    if (call.method === "GET" && p === "/api/v1/settings/execution") return { data: [] };
    if (call.method !== "GET") return undefined;
    if (p === BASE) return { data: buildProject("BUILD_READY") };
    if (p === `${BASE}/events`) return { data: eventPage(EVENTS, 0, 500) };
    if (p === `${BASE}/sources`) return { data: SOURCES };
    if (p === `${BASE}/evidence`) return { data: EVIDENCE };
    if (p === `${BASE}/records/audit`) return { data: RECORDS_AUDIT };
    if (p === `${BASE}/route`) return { data: ROUTE_ADOPTED };
    if (p === `${BASE}/decomposition`) return { data: DECOMPOSITION_SIGNED };
    if (p === `${BASE}/kanban`) return { data: world.kanban };
    if (p === `${BASE}/healing`) return { data: HEALING };
    return undefined;
  };
}

/** 頁內可控的 EventSource 替身：記下每個連線，`__emit` 對指定種類（research／logs）最後一個連線送一幀。 */
async function installFakeEventSource(page: Page) {
  await page.addInitScript(() => {
    type Listener = (e: MessageEvent) => void;
    class FakeES {
      static all: FakeES[] = [];
      readyState = 0;
      onopen: ((e: Event) => void) | null = null;
      onerror: ((e: Event) => void) | null = null;
      lastId = "";
      closed = false;
      listeners: Record<string, Listener[]> = {};
      constructor(public url: string) {
        FakeES.all.push(this);
        setTimeout(() => this.open(), 0);
      }
      addEventListener(type: string, l: Listener) {
        (this.listeners[type] ??= []).push(l);
      }
      close() {
        this.closed = true;
        this.readyState = 2;
      }
      open() {
        this.readyState = 1;
        this.onopen?.(new Event("open"));
      }
    }
    // 同一種串流可能有多個連線（例如終端窗格自己的 run 日誌串流）：一律對所有未關閉的同類連線操作，與真伺服器「廣播給所有訂閱者」一致
    const all = (kind: string) => FakeES.all.filter((s) => !s.closed && (kind === "research" ? s.url.includes("/stream/research/") : s.url.includes("/logs?")));
    const w = window as unknown as Record<string, unknown>;
    w.EventSource = FakeES;
    w.__sseCount = () => FakeES.all.length;
    w.__emit = (kind: string, name: string, data: unknown, id?: string) => {
      const targets = all(kind);
      if (targets.length === 0) throw new Error(`沒有 ${kind} 串流`);
      for (const s of targets) {
        if (id !== undefined) s.lastId = id;
        const ev = new MessageEvent(name, { data: JSON.stringify(data), lastEventId: s.lastId });
        for (const l of s.listeners[name] ?? []) l(ev);
      }
    };
    w.__dropRetrying = (kind: string) => {
      for (const s of all(kind)) {
        s.readyState = 0;
        s.onerror?.(new Event("error"));
      }
    };
    w.__reopen = (kind: string) => all(kind).forEach((s) => s.open());
    w.__lastId = (kind: string) => all(kind)[0]?.lastId;
  });
}

async function open(page: Page, world: World, role: "ADMIN" | "OPERATOR" | "VIEWER" = "OPERATOR") {
  const errors = collectConsoleErrors(page);
  await signInAs(page, role);
  await installFakeEventSource(page);
  const mock = await installApiMock(page, compose(shellHandler(), backend(world)));
  await page.goto(`/research/${R3}?step=build`);
  await expect(page.getByTestId("kanban-board")).toBeVisible({ timeout: 60_000 });
  // 兩條串流都連上（研究專案串流＋最新 run 的日誌串流）
  await expect.poll(() => page.evaluate(() => (window as unknown as { __sseCount: () => number }).__sseCount())).toBeGreaterThanOrEqual(2);
  return { errors, mock };
}

const kanbanGets = (calls: Array<{ method: string; path: string }>) => calls.filter((c) => c.method === "GET" && c.path === `${BASE}/kanban`).length;

test.describe("研究工作區步驟 4 內環看板（mock）", () => {
  test.setTimeout(180_000);

  test("AT_962_11_9 SSE 幀到看板 DOM commit 不超過 500 ms（頁內 performance.mark 量測）", async ({ page }) => {
    const world: World = { kanban: KANBAN };
    const { errors } = await open(page, world);
    await expect(page.getByTestId("kanban-col-implement")).toContainText("任務總數5");
    // 伺服器端狀態先變，再送 status-change 幀；從「幀到達」量到看板欄位出現新值
    world.kanban = { ...KANBAN, columns: { ...KANBAN.columns, implement: { ...KANBAN.columns.implement, tasks: { ...KANBAN.columns.implement.tasks, total: 9 } } } };
    const ms = await page.evaluate(async () => {
      const board = document.querySelector('[data-testid="kanban-board"]')!;
      return await new Promise<number>((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error("看板沒有更新")), 5000);
        const observer = new MutationObserver(() => {
          if (!(board.textContent ?? "").includes("任務總數9")) return;
          observer.disconnect();
          clearTimeout(timer);
          performance.mark("dom-committed");
          resolve(performance.measure("sse-to-dom", "frame-arrived", "dom-committed").duration);
        });
        observer.observe(board, { subtree: true, childList: true, characterData: true });
        performance.mark("frame-arrived");
        (window as unknown as { __emit: (k: string, n: string, d: unknown, i?: string) => void }).__emit(
          "logs",
          "status-change",
          { seq: 7, ts: new Date().toISOString(), runStatus: "RUNNING", bridgeStatus: "RUNNING", reason: "x" },
          "7",
        );
      });
    });
    console.info(`[AT_962_11_9] 幀到 DOM ${ms.toFixed(1)} ms（上限 500；含 100 ms 去抖與 mock REST）`);
    expect(ms).toBeLessThanOrEqual(500);
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("AT_962_11_9 斷線回補：瀏覽器自己重連（同一實例、帶 Last-Event-ID）再開啟就全量重抓；replay_gap 也重抓，畫面不顯示過期值", async ({ page }) => {
    const world: World = { kanban: KANBAN };
    const { mock } = await open(page, world);
    const sseCount = () => page.evaluate(() => (window as unknown as { __sseCount: () => number }).__sseCount());
    const count = await sseCount();
    await page.evaluate(() => (window as unknown as { __emit: (k: string, n: string, d: unknown, i?: string) => void }).__emit("research", "research.step", {}, "7"));
    await expect.poll(() => kanbanGets(mock.calls)).toBeGreaterThanOrEqual(2); // 去抖後的一次重抓
    const before = kanbanGets(mock.calls);
    world.kanban = { ...KANBAN, columns: { ...KANBAN.columns, decompose: { ...KANBAN.columns.decompose, tasksCount: 42 } } };
    await page.evaluate(() => {
      const w = window as unknown as Record<string, (k: string) => void>;
      w.__dropRetrying("research");
      w.__reopen("research");
    });
    await expect(page.getByTestId("kanban-col-decompose")).toContainText("任務數42");
    expect(kanbanGets(mock.calls)).toBeGreaterThan(before);
    expect(await sseCount()).toBe(count); // 沒有另建連線：瀏覽器自己重連
    expect(await page.evaluate(() => (window as unknown as { __lastId: (k: string) => string }).__lastId("research"))).toBe("7"); // 重連請求帶的 Last-Event-ID

    const afterReopen = kanbanGets(mock.calls);
    world.kanban = { ...KANBAN, columns: { ...KANBAN.columns, decompose: { ...KANBAN.columns.decompose, tasksCount: 77 } } };
    await page.evaluate(() => (window as unknown as { __emit: (k: string, n: string, d: unknown) => void }).__emit("research", "research.replay_gap", { toSeq: 99 }));
    await expect(page.getByTestId("kanban-col-decompose")).toContainText("任務數77");
    expect(kanbanGets(mock.calls)).toBeGreaterThan(afterReopen);
  });

  test("AT_962_11_9 Bridge 不可達：橫幅含快照時間、FSM 衍生欄未知徽章、不渲染空看板；VIEWER 的寫入鈕停用", async ({ page }) => {
    const world: World = { kanban: kanbanUnreachable() };
    const { errors } = await open(page, world, "VIEWER");
    await expect(page.getByTestId("kanban-stale-banner")).toHaveText("Engine Bridge 無法連線，以下為 2026-11-07T09:00:00+08:00 的 DB 快照");
    await expect(page.getByTestId("kanban-board")).toHaveAttribute("data-stale", "true");
    for (const col of ["tcs", "implement", "regression"]) await expect(page.getByTestId(`kanban-badge-${col}`)).toHaveText("未知");
    await expect(page.getByTestId("kanban-col-decompose")).toContainText("任務數5");
    await expect(page.getByTestId("gate-register-trigger")).toBeDisabled();
    await expect(page.getByTestId("gate-register-trigger")).toHaveAttribute("title", "權限不足（唯讀角色）");
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });
});
