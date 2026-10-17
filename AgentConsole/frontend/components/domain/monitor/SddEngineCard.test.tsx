import { focusManager } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { SddEngineStatus, SddFsmState, SddProjectEntry } from "@/lib/api/types";
import { SDD_PROJECT_STORAGE_KEY, rememberSddProject, resetSddProjectCache } from "@/lib/nav/sddProject";
import { Providers, failure, makeClient, signIn, stubApi, type ApiCall } from "@/tests/helpers/api";
import { SddEngineCard } from "./SddEngineCard";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/projects/p1/monitor",
  useSearchParams: () => new URLSearchParams(),
}));

/**
 * 「AISDLC_SDD 引擎」卡（契約 §1.7.1、§4.3 M-20；v1.4 D-16，API-ENG-01、NFR-OBS-01）：
 * 假後端依契約映射表回應 GET /engines/sdd（未帶 project → fsm=null；帶 project → 該專案的 FSM；引擎不可用也回 200）。
 */
const PATH = "/api/v1/engines/sdd";
const CHECKED_AT = "2026-10-16T03:21:45Z";
const UPDATED = new Date(2026, 9, 16, 9, 2, 3).toISOString(); // 本機時區建構：顯示成 2026-10-16 09:02:03，不依賴執行機器的時區
const ENTERED = new Date(2026, 9, 15, 16, 0, 0).toISOString();

const entry = (project: string, currentState: string): SddProjectEntry => ({ project, source: `FSM-STATE-${project}.yaml`, currentState, updatedAt: UPDATED });
const ALPHA = entry("e2e-alpha", "IMPLEMENTATION");
const BRAVO = entry("e2e-bravo", "HUMAN_PENDING");

/** decision_trace 的尾 5 筆（舊→新）；巢狀內容原樣＝保留 snake_case 鍵。 */
const TRACE = [1, 2, 3, 4, 5].map((n) => ({
  ts: new Date(2026, 9, 16, 8, n, 0).toISOString(),
  from: `S${n}`,
  to: `S${n + 1}`,
  reason: `r${n}`,
  spec_refs: [`SPEC-${n}`],
  agents_consulted: [],
  trigger: "auto",
}));

const fsmOf = (project: string, patch: Partial<SddFsmState> = {}): SddFsmState => ({
  project,
  currentState: project === "e2e-bravo" ? "HUMAN_PENDING" : "IMPLEMENTATION",
  currentSprint: project === "e2e-bravo" ? 1 : 2,
  sessionId: `sid-${project}`,
  updatedAt: UPDATED,
  frozenStages: [{ stage: "SCG-0" }],
  decisionTrace: project === "e2e-bravo" ? [] : TRACE,
  source: `FSM-STATE-${project}.yaml`,
  humanPending: project === "e2e-bravo" ? { count: 1, items: [{ entered_at: ENTERED, reminder_hours: 72 }] } : { count: 0, items: [] },
  retryHistory: { count: 3, last: { attempt: 1, date: "2026-10-15", failure_reason: "x", scg_gate: "SCG-4", gate: "SCG_VALIDATION" } },
  rtmCoverage: null,
  ...patch,
});

type World = {
  mode: "ok" | "bridge_unreachable" | "sdd_unavailable" | "bridge_error" | "http500";
  projects: SddProjectEntry[];
  /** 專案名 → FSM；"broken" 代表檔案讀不動（422 → fsm_state_unreadable） */
  fsms: Record<string, SddFsmState | "broken">;
};

function sddWorld(patch: Partial<World> = {}) {
  const world: World = { mode: "ok", projects: [ALPHA, BRAVO], fsms: { "e2e-alpha": fsmOf("e2e-alpha"), "e2e-bravo": fsmOf("e2e-bravo") }, ...patch };
  const { calls } = stubApi((c: ApiCall) => {
    if (c.path !== PATH) return undefined;
    if (world.mode === "http500") return failure(500, { message: "伺服器錯誤" });
    const base = { checkedAt: CHECKED_AT };
    if (world.mode !== "ok") {
      const down: SddEngineStatus = { available: false, reason: world.mode, version: null, projects: [], fsm: null, ...base };
      return { data: down };
    }
    const version = { latest: "AISDLC_SDD_v9.99", root: "/sdd/AISDLC_SDD_v9.99" };
    const project = c.query.get("project");
    const ok = (fsm: SddFsmState | null, reason: SddEngineStatus["reason"] = null): { data: SddEngineStatus } => ({
      data: { available: true, reason, version, projects: world.projects, fsm, ...base },
    });
    if (project === null) return ok(null);
    if (!/^[A-Za-z0-9._-]{1,128}$/.test(project)) return failure(400, { message: "請求參數錯誤", errors: [{ field: "project", message: "不合法" }] });
    const found = world.fsms[project];
    if (found === undefined) return ok(null, "fsm_not_found");
    if (found === "broken") return ok(null, "fsm_state_unreadable");
    return ok(found);
  });
  return { world, calls };
}

const sddCalls = (calls: ApiCall[]) => calls.filter((c) => c.path === PATH);
const projectParams = (calls: ApiCall[]) => sddCalls(calls).map((c) => c.query.get("project"));

function view(pollMs?: number) {
  return render(
    <Providers client={makeClient()}>
      <SddEngineCard pollMs={pollMs} />
    </Providers>,
  );
}

beforeEach(() => {
  signIn("OPERATOR", "operator");
  window.localStorage.clear();
  resetSddProjectCache();
});

describe("AISDLC_SDD 引擎卡：可用（契約 §4.3 M-20）", () => {
  it("兩段請求：先不帶 project 取清單，選定第一個專案後帶 project 取它的 FSM；狀態點、版本（只秀 latest）、FSM 專案下拉（依 Bridge 順序）", async () => {
    const { calls } = sddWorld();
    view();
    await screen.findByTestId("sdd-state");
    expect(projectParams(calls)).toEqual([null, "e2e-alpha"]);
    expect(screen.getByTestId("sdd-status")).toHaveAttribute("data-available", "true");
    expect(screen.getByTestId("sdd-status")).toHaveTextContent("可用");
    expect(screen.getByTestId("sdd-version")).toHaveTextContent("AISDLC_SDD_v9.99");
    expect(screen.getByTestId("sdd-card")).not.toHaveTextContent("/sdd/AISDLC_SDD_v9.99"); // version.root 是 Bridge 端路徑，不顯示
    const select = screen.getByTestId("sdd-project-select") as HTMLSelectElement;
    expect([...select.options].map((o) => o.value)).toEqual(["e2e-alpha", "e2e-bravo"]);
    expect(select.value).toBe("e2e-alpha");
    expect(screen.getByRole("combobox", { name: "FSM 專案" })).toBe(select);
  });

  it("選定專案的欄位與 FSM 逐值一致：目前狀態、Sprint N、更新時間（本機時區）、待人工「無」；不顯示 retryHistory、rtmCoverage、frozenStages", async () => {
    sddWorld();
    view();
    expect(await screen.findByTestId("sdd-state")).toHaveTextContent("IMPLEMENTATION");
    expect(screen.getByTestId("sdd-sprint")).toHaveTextContent("Sprint 2");
    expect(screen.getByTestId("sdd-updated")).toHaveTextContent("2026-10-16 09:02:03");
    expect(screen.getByTestId("sdd-updated")).toHaveAttribute("title", UPDATED); // 原值放 tooltip，方便與檔案逐值比對
    expect(screen.getByTestId("sdd-human-pending")).toHaveTextContent(/^無$/);
    expect(screen.queryByTestId("sdd-human-pending-items")).toBeNull();
    const text = screen.getByTestId("sdd-card").textContent ?? "";
    for (const hidden of ["SCG_VALIDATION", "retry", "frozen", "SCG-0", "rtm"]) expect(text.toLowerCase(), hidden).not.toContain(hidden.toLowerCase());
  });

  it("最近決策：API 給的尾 5 筆（舊→新）倒序顯示（新→舊），每筆 `from → to` 與 reason 與檔案原值一致", async () => {
    sddWorld();
    view();
    const items = await screen.findAllByTestId("sdd-decision");
    expect(items).toHaveLength(5);
    expect(items.map((li) => within(li).getByTestId("sdd-decision-transition").textContent)).toEqual(["S5 → S6", "S4 → S5", "S3 → S4", "S2 → S3", "S1 → S2"]);
    expect(items.map((li) => within(li).getByTestId("sdd-decision-reason").textContent)).toEqual(["r5", "r4", "r3", "r2", "r1"]);
    expect(within(items[0]).getByTestId("sdd-decision-ts")).toHaveTextContent("2026-10-16 08:05:00");
    expect(screen.getByRole("list", { name: "最近決策" })).toBeInTheDocument();
  });

  it("沒有決策紀錄：顯示「尚無決策紀錄」，不是空白", async () => {
    const { world } = sddWorld();
    world.fsms["e2e-alpha"] = fsmOf("e2e-alpha", { decisionTrace: [] });
    view();
    expect(await screen.findByTestId("sdd-decisions-empty")).toHaveTextContent("尚無決策紀錄");
    expect(screen.queryByTestId("sdd-decision")).toBeNull();
  });

  it("欄位缺值（currentState、currentSprint、updatedAt 為 null）顯示「—」，不編造", async () => {
    const { world } = sddWorld();
    world.fsms["e2e-alpha"] = fsmOf("e2e-alpha", { currentState: null, currentSprint: null, updatedAt: null });
    view();
    await screen.findByTestId("sdd-state");
    expect(screen.getByTestId("sdd-state")).toHaveTextContent("—");
    expect(screen.getByTestId("sdd-sprint")).toHaveTextContent("—");
    expect(screen.getByTestId("sdd-updated")).toHaveTextContent("—");
    expect(screen.getByTestId("sdd-updated")).not.toHaveAttribute("title");
  });

  it("待人工 1 筆：顯示「等待人工確認」，可展開看 entered_at（本機時區）；0 筆的專案顯示「無」", async () => {
    sddWorld();
    rememberSddProject("e2e-bravo");
    view();
    const summary = await screen.findByTestId("sdd-human-pending");
    expect(summary).toHaveTextContent(/^等待人工確認$/);
    expect(summary.tagName).toBe("SUMMARY"); // <details> 的標題：鍵盤與滑鼠都可展開
    expect(summary.closest("details")).not.toHaveAttribute("open");
    await userEvent.click(summary);
    expect(summary.closest("details")).toHaveAttribute("open");
    expect(screen.getByTestId("sdd-human-pending-items")).toHaveTextContent("進入時間：2026-10-15 16:00:00");
    expect(screen.getByTestId("sdd-state")).toHaveTextContent("HUMAN_PENDING");
    expect(screen.getByTestId("sdd-sprint")).toHaveTextContent("Sprint 1");
  });
});

describe("AISDLC_SDD 引擎卡：選專案（預設、記住、切換）", () => {
  it("預設＝上次選的且仍在清單內者（localStorage 記住）：第二段請求帶的就是它", async () => {
    rememberSddProject("e2e-bravo");
    const { calls } = sddWorld();
    view();
    await screen.findByTestId("sdd-state");
    expect(projectParams(calls)).toEqual([null, "e2e-bravo"]);
    expect((screen.getByTestId("sdd-project-select") as HTMLSelectElement).value).toBe("e2e-bravo");
  });

  it("上次選的專案已不在清單內：退回清單第一個（不拿不存在的專案去查）", async () => {
    window.localStorage.setItem(SDD_PROJECT_STORAGE_KEY, "已被刪掉的專案");
    const { calls } = sddWorld();
    view();
    await screen.findByTestId("sdd-state");
    expect(projectParams(calls)).toEqual([null, "e2e-alpha"]);
  });

  it("沒選過：只是預設第一個，不會自己寫進 localStorage（記住的只有使用者明確的選擇）", async () => {
    sddWorld();
    view();
    await screen.findByTestId("sdd-state");
    expect(window.localStorage.getItem(SDD_PROJECT_STORAGE_KEY)).toBeNull();
  });

  it("在下拉改選另一個專案：改帶新的 project 重取、畫面換成它的內容、選擇存進 localStorage；切回去不必等（快取）", async () => {
    const { calls } = sddWorld();
    view();
    await screen.findByTestId("sdd-state");
    expect(screen.getByTestId("sdd-state")).toHaveTextContent("IMPLEMENTATION");

    await userEvent.selectOptions(screen.getByTestId("sdd-project-select"), "e2e-bravo");
    await waitFor(() => expect(screen.getByTestId("sdd-state")).toHaveTextContent("HUMAN_PENDING"));
    expect(projectParams(calls)).toEqual([null, "e2e-alpha", "e2e-bravo"]);
    expect(window.localStorage.getItem(SDD_PROJECT_STORAGE_KEY)).toBe("e2e-bravo");
    expect(screen.getByTestId("sdd-human-pending")).toHaveTextContent("等待人工確認");
    expect(screen.queryByTestId("sdd-decision")).toBeNull(); // bravo 沒有決策紀錄：不殘留 alpha 的決策

    await userEvent.selectOptions(screen.getByTestId("sdd-project-select"), "e2e-alpha");
    expect(screen.getByTestId("sdd-state")).toHaveTextContent("IMPLEMENTATION"); // 已有快取：立即顯示，背景再重抓
    expect(window.localStorage.getItem(SDD_PROJECT_STORAGE_KEY)).toBe("e2e-alpha");
  });

  it("切換期間（新專案還沒回來）不把上一個專案的內容當成新專案的內容：先顯示載入骨架，下拉與版本仍在", async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => (release = resolve));
    sddWorld();
    const stubbed = globalThis.fetch;
    vi.stubGlobal("fetch", async (input: string, init?: RequestInit) => {
      if (String(input).includes("project=e2e-bravo")) await gate;
      return stubbed(input, init);
    });
    view();
    await screen.findByTestId("sdd-state");
    await userEvent.selectOptions(screen.getByTestId("sdd-project-select"), "e2e-bravo");
    expect(screen.queryByTestId("sdd-state")).toBeNull();
    expect(screen.getByTestId("sdd-version")).toHaveTextContent("AISDLC_SDD_v9.99");
    expect((screen.getByTestId("sdd-project-select") as HTMLSelectElement).value).toBe("e2e-bravo");
    release();
    expect(await screen.findByTestId("sdd-state")).toHaveTextContent("HUMAN_PENDING");
  });
});

describe("AISDLC_SDD 引擎卡：不可用與空清單（契約 M-20 的 reason 字典）", () => {
  it.each([
    ["bridge_unreachable", "Engine Bridge 無法連線"],
    ["sdd_unavailable", "找不到 AISDLC_SDD 目錄（請檢查 Bridge 的 SDD_ROOT）"],
    ["bridge_error", "Engine Bridge 回應異常"],
  ] as const)("available=false、reason=%s：狀態點「不可用」、顯示「%s」；沒有下拉與 FSM 欄位（200 不是錯誤頁）", async (mode, message) => {
    const { calls } = sddWorld({ mode });
    view();
    expect(await screen.findByTestId("sdd-message")).toHaveTextContent(message);
    expect(screen.getByTestId("sdd-message")).toHaveAttribute("data-reason", mode);
    expect(screen.getByTestId("sdd-status")).toHaveAttribute("data-available", "false");
    expect(screen.getByTestId("sdd-status")).toHaveTextContent("不可用");
    expect(screen.queryByTestId("sdd-version")).toBeNull();
    expect(screen.queryByTestId("sdd-project-select")).toBeNull();
    expect(screen.queryByTestId("sdd-state")).toBeNull();
    expect(screen.queryByText("無法取得 AISDLC_SDD 引擎狀態")).toBeNull(); // 這是引擎狀態，不是 console-api 的錯誤
    expect(projectParams(calls)).toEqual([null]); // 沒有專案清單，不會有第二段請求
  });

  it("available=true 但 projects=[]（SDD 目錄在、runtime 還沒跑過）：顯示「尚無 FSM 狀態檔（SDD runtime 執行後才會產生）」，不是錯誤", async () => {
    sddWorld({ projects: [], fsms: {} });
    view();
    expect(await screen.findByTestId("sdd-empty")).toHaveTextContent("尚無 FSM 狀態檔（SDD runtime 執行後才會產生）");
    expect(screen.getByTestId("sdd-status")).toHaveAttribute("data-available", "true");
    expect(screen.getByTestId("sdd-version")).toHaveTextContent("AISDLC_SDD_v9.99");
    expect(screen.queryByTestId("sdd-project-select")).toBeNull();
    expect(screen.queryByTestId("sdd-message")).toBeNull();
  });

  it.each([
    ["fsm_state_unreadable", "broken", "FSM 狀態檔無法讀取"],
    ["fsm_not_found", undefined, "找不到所選專案的 FSM 狀態檔"],
  ] as const)("所選專案取不到 FSM（%s）：引擎仍是「可用」、下拉還在、顯示「%s」；改選別的專案就恢復", async (reason, fsm, message) => {
    const { world } = sddWorld();
    if (fsm === "broken") world.fsms["e2e-alpha"] = "broken";
    else delete world.fsms["e2e-alpha"];
    view();
    const note = await screen.findByTestId("sdd-message");
    expect(note).toHaveTextContent(message);
    expect(note).toHaveAttribute("data-reason", reason);
    expect(screen.getByTestId("sdd-status")).toHaveAttribute("data-available", "true");
    expect(screen.queryByTestId("sdd-state")).toBeNull();
    await userEvent.selectOptions(screen.getByTestId("sdd-project-select"), "e2e-bravo");
    expect(await screen.findByTestId("sdd-state")).toHaveTextContent("HUMAN_PENDING");
    expect(screen.queryByTestId("sdd-message")).toBeNull();
  });

  it("後端日後新增 reason：照樣顯示（附原值），不崩潰也不吞掉", async () => {
    sddWorld({ mode: "bridge_unreachable" });
    const stubbed = globalThis.fetch;
    vi.stubGlobal("fetch", async (input: string, init?: RequestInit) => {
      const res = await stubbed(input, init);
      const body = await res.json();
      return new Response(JSON.stringify({ ...body, data: { ...body.data, reason: "future_reason" } }), { status: 200, headers: { "content-type": "application/json" } });
    });
    view();
    expect(await screen.findByTestId("sdd-message")).toHaveTextContent("引擎回報：future_reason");
  });

  it("console-api 自己回非 2xx（例如 500）：顯示錯誤與重試，不編造狀態；重試成功後恢復", async () => {
    const { world } = sddWorld({ mode: "http500" });
    view();
    expect(await screen.findByText("無法取得 AISDLC_SDD 引擎狀態")).toBeInTheDocument();
    expect(screen.queryByTestId("sdd-status")).toBeNull();
    world.mode = "ok";
    await userEvent.click(screen.getByRole("button", { name: "重試" }));
    expect(await screen.findByTestId("sdd-state")).toHaveTextContent("IMPLEMENTATION");
  });
});

describe("AISDLC_SDD 引擎卡：輪詢（契約 §1.7.1：30 秒一次，分頁不可見時暫停；一張卡約每分鐘 2 次請求）", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });
  afterEach(() => {
    focusManager.setFocused(undefined);
    vi.useRealTimers();
  });

  it("選定專案後只輪詢「選定專案」那一份：29 秒內沒有新請求，過 30 秒恰一個（帶 project），不再重複打不帶 project 的那份", async () => {
    const { calls } = sddWorld();
    view();
    await screen.findByTestId("sdd-state");
    expect(sddCalls(calls)).toHaveLength(2);

    await vi.advanceTimersByTimeAsync(29_000);
    expect(sddCalls(calls)).toHaveLength(2);
    await vi.advanceTimersByTimeAsync(2_000);
    await waitFor(() => expect(sddCalls(calls)).toHaveLength(3));
    await vi.advanceTimersByTimeAsync(30_000);
    await waitFor(() => expect(sddCalls(calls)).toHaveLength(4));
    expect(projectParams(calls)).toEqual([null, "e2e-alpha", "e2e-alpha", "e2e-alpha"]);
  });

  it("監控頁的輪詢設定調得更慢（60 秒）時跟著放慢，不得比設定更密；設定調得更快不會比契約的 30 秒更密", async () => {
    const { calls } = sddWorld();
    view(60_000);
    await screen.findByTestId("sdd-state");
    await vi.advanceTimersByTimeAsync(59_000);
    expect(sddCalls(calls)).toHaveLength(2);
    await vi.advanceTimersByTimeAsync(2_000);
    await waitFor(() => expect(sddCalls(calls)).toHaveLength(3));
  });

  it("下一輪輪詢跟上檔案變動：沒有整頁重載，卡片更新成新狀態與新決策（E2E-15 第 6 列的前端那一半）", async () => {
    const { world } = sddWorld();
    view();
    await screen.findByTestId("sdd-state");
    expect(screen.getByTestId("sdd-state")).toHaveTextContent("IMPLEMENTATION");
    world.fsms["e2e-alpha"] = fsmOf("e2e-alpha", {
      currentState: "REVIEW",
      decisionTrace: [...TRACE.slice(1), { ts: new Date(2026, 9, 16, 8, 6, 0).toISOString(), from: "S6", to: "REVIEW", reason: "新的一筆", spec_refs: [], agents_consulted: [], trigger: "auto" }],
    });
    await vi.advanceTimersByTimeAsync(31_000);
    await waitFor(() => expect(screen.getByTestId("sdd-state")).toHaveTextContent("REVIEW"));
    expect(screen.getAllByTestId("sdd-decision")[0]).toHaveTextContent("S6 → REVIEW");
    expect(screen.getAllByTestId("sdd-decision")[0]).toHaveTextContent("新的一筆");
  });

  it("所選專案的狀態檔之後被刪掉：下拉仍保留它（註明檔案已不存在）、顯示 fsm_not_found 文案，改選別的專案就恢復", async () => {
    const { world } = sddWorld();
    view();
    await screen.findByTestId("sdd-state");
    await userEvent.selectOptions(screen.getByTestId("sdd-project-select"), "e2e-bravo");
    await waitFor(() => expect(screen.getByTestId("sdd-state")).toHaveTextContent("HUMAN_PENDING"));

    world.projects = [ALPHA]; // 檔案被刪：清單少了 bravo，查它回 fsm_not_found
    delete world.fsms["e2e-bravo"];
    await vi.advanceTimersByTimeAsync(31_000);
    expect(await screen.findByTestId("sdd-message")).toHaveTextContent("找不到所選專案的 FSM 狀態檔");
    const select = screen.getByTestId("sdd-project-select") as HTMLSelectElement;
    expect([...select.options].map((o) => o.text)).toEqual(["e2e-alpha", "e2e-bravo（狀態檔已不存在）"]);
    expect(select.value).toBe("e2e-bravo"); // 下拉與畫面內容不脫鉤：仍是使用者選的那個
    expect(screen.queryByTestId("sdd-state")).toBeNull();

    await userEvent.selectOptions(select, "e2e-alpha");
    expect(await screen.findByTestId("sdd-state")).toHaveTextContent("IMPLEMENTATION");
    expect([...(screen.getByTestId("sdd-project-select") as HTMLSelectElement).options].map((o) => o.text)).toEqual(["e2e-alpha"]);
  });
  it("恰好讀到寫一半的檔：顯示「FSM 狀態檔無法讀取」、不崩潰，下一輪輪詢恢復", async () => {
    const { world } = sddWorld();
    view();
    await screen.findByTestId("sdd-state");
    world.fsms["e2e-alpha"] = "broken";
    await vi.advanceTimersByTimeAsync(31_000);
    expect(await screen.findByText("FSM 狀態檔無法讀取")).toBeInTheDocument();
    world.fsms["e2e-alpha"] = fsmOf("e2e-alpha");
    await vi.advanceTimersByTimeAsync(31_000);
    await waitFor(() => expect(screen.getByTestId("sdd-state")).toHaveTextContent("IMPLEMENTATION"));
    expect(screen.queryByTestId("sdd-message")).toBeNull();
  });

  it("引擎不可用時持續輪詢（沒有專案清單可選），Bridge 重啟後下一輪輪詢復原（E2E-15 第 7 列的前端那一半）", async () => {
    const { world, calls } = sddWorld({ mode: "bridge_unreachable" });
    view();
    expect(await screen.findByTestId("sdd-message")).toHaveTextContent("Engine Bridge 無法連線");
    world.mode = "ok";
    await vi.advanceTimersByTimeAsync(31_000);
    expect(await screen.findByTestId("sdd-state")).toHaveTextContent("IMPLEMENTATION");
    expect(screen.getByTestId("sdd-status")).toHaveAttribute("data-available", "true");
    expect(screen.queryByTestId("sdd-message")).toBeNull();
    expect(projectParams(calls)).toEqual([null, null, "e2e-alpha"]); // 復原後才出現第二段
  });

  it("清單是空的（runtime 還沒跑過）時繼續輪詢，檔案出現後自動選定第一個專案", async () => {
    const { world } = sddWorld({ projects: [], fsms: {} });
    view();
    await screen.findByTestId("sdd-empty");
    world.projects = [ALPHA];
    world.fsms["e2e-alpha"] = fsmOf("e2e-alpha");
    await vi.advanceTimersByTimeAsync(31_000);
    expect(await screen.findByTestId("sdd-state")).toHaveTextContent("IMPLEMENTATION");
    expect(screen.queryByTestId("sdd-empty")).toBeNull();
  });

  it("分頁不可見（失焦）時停止輪詢：過了好幾個週期也不再請求", async () => {
    const { calls } = sddWorld();
    view();
    await screen.findByTestId("sdd-state");
    expect(sddCalls(calls)).toHaveLength(2);
    focusManager.setFocused(false);
    await vi.advanceTimersByTimeAsync(30_000 * 3);
    expect(sddCalls(calls)).toHaveLength(2);
  });
});

describe("AISDLC_SDD 引擎卡：唯讀", () => {
  it("沒有任何寫入動作：整張卡除了專案下拉與「等待人工確認」的展開，沒有按鈕；全部請求都是 GET", async () => {
    const { calls } = sddWorld();
    rememberSddProject("e2e-bravo");
    view();
    await screen.findByTestId("sdd-state");
    expect(within(screen.getByTestId("sdd-card")).queryAllByRole("button")).toEqual([]);
    expect(calls.every((c) => c.method === "GET")).toBe(true);
  });

  it("VIEWER 也看得到（VIEWER 以上皆可讀）", async () => {
    signIn("VIEWER", "viewer");
    sddWorld();
    view();
    expect(await screen.findByTestId("sdd-state")).toHaveTextContent("IMPLEMENTATION");
  });
});

// ══ v1.5（整合輪 115；契約 §4.3 M-21、§4.7.3；UI-SDD-03）：階段進度與 ESCALATION、專案模式 ═══════════════════════════════
const P1 = "0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02";
const phaseOf = (name: string, order: number, patch: Partial<NonNullable<SddFsmState["phase"]>> = {}): SddFsmState["phase"] => ({ name, order, blocking: false, observation: false, ...patch });

describe("AISDLC_SDD 引擎卡：階段進度（契約 §4.7.3）", () => {
  it("fsm.phase 為 IMPLEMENTATION／5：進度條標出「目前」；data-phase／data-order／data-blocking／data-observation 供 e2e；沒有阻塞橫幅也沒有 ESCALATION 區塊", async () => {
    const { world } = sddWorld();
    world.fsms["e2e-alpha"] = fsmOf("e2e-alpha", { phase: phaseOf("IMPLEMENTATION", 5) });
    view();
    const bar = await screen.findByTestId("sdd-phase");
    expect(bar).toHaveAttribute("data-phase", "IMPLEMENTATION");
    expect(bar).toHaveAttribute("data-order", "5");
    expect(bar).toHaveAttribute("data-blocking", "false");
    expect(bar).toHaveAttribute("data-observation", "false");
    expect(screen.getByTestId("sdd-phase-label")).toHaveTextContent("實作");
    expect(screen.getAllByTestId("sdd-phase-step").map((li) => li.getAttribute("data-state"))).toEqual(["done", "done", "done", "done", "current", "upcoming", "upcoming", "upcoming"]);
    expect(screen.queryByTestId("sdd-blocked-banner")).toBeNull();
    expect(screen.queryByTestId("sdd-escalation")).toBeNull();
    expect(screen.getByTestId("sdd-state")).toHaveTextContent(/^IMPLEMENTATION$/); // 狀態欄維持原樣（FSM 檔原值），階段標籤另放
  });

  it("觀測態＋AUTOCLAUDE_DELEGATED：「觀測中」與「委派 AutoClaude 執行中」標籤、虛線外框的「目前」步驟", async () => {
    const { world } = sddWorld();
    world.fsms["e2e-alpha"] = fsmOf("e2e-alpha", { currentState: "AUTOCLAUDE_DELEGATED", phase: phaseOf("IMPLEMENTATION", 5, { observation: true }) });
    view();
    await screen.findByTestId("sdd-phase");
    expect(screen.getByTestId("sdd-phase")).toHaveAttribute("data-observation", "true");
    expect(screen.getByTestId("sdd-phase-observation")).toHaveTextContent("觀測中");
    expect(screen.getByTestId("sdd-phase-delegated")).toHaveTextContent("委派 AutoClaude 執行中");
    const current = screen.getAllByTestId("sdd-phase-step").find((li) => li.getAttribute("data-state") === "current");
    expect(current).toHaveAttribute("data-step", "IMPLEMENTATION");
    expect(current?.className).toContain("border-dashed");
  });

  it("phase 缺席（舊 Bridge）：只顯示「階段 —」與 currentState，不畫步驟、不崩潰；order 0 的非主路徑同樣不畫步驟", async () => {
    const { world } = sddWorld();
    view();
    expect(await screen.findByTestId("sdd-phase-label")).toHaveTextContent("—");
    expect(screen.getByTestId("sdd-phase")).toHaveAttribute("data-order", "0");
    expect(screen.queryByTestId("sdd-phase-steps")).toBeNull();
    expect(screen.getByTestId("sdd-state")).toHaveTextContent("IMPLEMENTATION");
    world.fsms["e2e-alpha"] = fsmOf("e2e-alpha", { currentState: "HUB_SYNC", phase: phaseOf("OBSERVATION", 0, { observation: true }) });
    await userEvent.selectOptions(screen.getByTestId("sdd-project-select"), "e2e-bravo");
    await userEvent.selectOptions(screen.getByTestId("sdd-project-select"), "e2e-alpha");
    await waitFor(() => expect(screen.getByTestId("sdd-phase-label")).toHaveTextContent("觀測中"));
    expect(screen.queryByTestId("sdd-phase-steps")).toBeNull();
  });
});

describe("AISDLC_SDD 引擎卡：ESCALATION 標示與恢復指令（契約 §4.7.3；ADR-XPLAT-016 §5.3）", () => {
  const OPEN = { triggered_at: new Date(2026, 9, 17, 9, 0, 0).toISOString(), trigger_reason: "引擎升級：評估未通過", resolved_at: null, resolution: null };
  const blocked = (patch: Partial<SddFsmState> = {}) =>
    fsmOf("e2e-alpha", {
      currentState: "ESCALATION",
      phase: phaseOf("BLOCKED", 0, { blocking: true }),
      escalationHistory: [OPEN],
      escalationProvenance: { source: "autoclaude_delegated_failed", rule_id: "R-9.20.2", reason: "x" },
      recovery: {
        target: "IMPLEMENTATION",
        powershell: 'Push-Location "C:\\sdd"; python -m x resume-from-escalation --reason "<人工原因>"; Pop-Location',
        posix: 'cd "/sdd" && python -m x resume-from-escalation --reason "<人工原因>"',
      },
      ...patch,
    });

  it("阻塞態：紅色橫幅「阻塞：ESCALATION（需人工恢復）」＋Console 不提供恢復動作的說明；八個步驟全灰；ESCALATION 區塊顯示末筆與來源", async () => {
    const { world } = sddWorld();
    world.fsms["e2e-alpha"] = blocked();
    view();
    const banner = await screen.findByTestId("sdd-blocked-banner");
    expect(banner).toHaveTextContent("阻塞：ESCALATION（需人工恢復）");
    expect(banner).toHaveTextContent("請在 SDD session 依恢復指令處理，Console 不提供恢復動作");
    expect(screen.getByTestId("sdd-phase")).toHaveAttribute("data-blocking", "true");
    expect(screen.getAllByTestId("sdd-phase-step").every((li) => li.getAttribute("data-state") === "upcoming")).toBe(true);
    expect(screen.getByTestId("sdd-escalation-summary")).toHaveTextContent("ESCALATION・2026-10-17 09:00:00・引擎升級：評估未通過");
    expect(screen.getByTestId("sdd-escalation-source")).toHaveTextContent("來源：autoclaude_delegated_failed・AutoClaude 委派失敗（引擎升級）");
    expect(screen.getByTestId("sdd-escalation")).toHaveAttribute("data-unresolved", "true");
  });

  it("恢復指令：PowerShell 與 POSIX 兩段原樣顯示（含 <人工原因> 佔位）、各有一個複製鈕；不提供執行鈕", async () => {
    const { world } = sddWorld();
    world.fsms["e2e-alpha"] = blocked();
    view();
    const recovery = await screen.findByTestId("sdd-recovery");
    expect(recovery).toHaveTextContent("恢復（在 SDD session 執行；Console 不提供恢復動作）");
    expect([...recovery.querySelectorAll("[data-shell]")].map((el) => el.getAttribute("data-shell"))).toEqual(["powershell", "posix"]);
    expect(within(recovery).getByTestId("sdd-recovery-command-powershell")).toHaveTextContent('Push-Location "C:\\sdd"; python -m x resume-from-escalation --reason "<人工原因>"; Pop-Location');
    expect(within(recovery).getByTestId("sdd-recovery-command-posix")).toHaveTextContent('cd "/sdd" && python -m x resume-from-escalation --reason "<人工原因>"');
    expect(
      within(recovery)
        .getAllByRole("button")
        .map((b) => b.getAttribute("aria-label")),
    ).toEqual(["複製 PowerShell 指令", "複製 POSIX（bash／zsh） 指令"]);
    expect(within(recovery).queryByRole("button", { name: /執行|恢復/ })).toBeNull();
  });

  it("fsm.recovery 缺席：只有橫幅的文字說明，前端不自己組指令", async () => {
    const { world } = sddWorld();
    world.fsms["e2e-alpha"] = blocked({ recovery: null });
    view();
    await screen.findByTestId("sdd-blocked-banner");
    expect(screen.queryByTestId("sdd-recovery")).toBeNull();
    expect(screen.getByTestId("sdd-card").textContent).not.toContain("resume-from-escalation");
  });

  it("ESCALATION_FINAL 與 phase.blocking（TERMINATED）同樣顯示橫幅與區塊；escalationHistory 為空：區塊寫「（沒有升級紀錄）」、橫幅照顯示", async () => {
    const { world } = sddWorld();
    world.fsms["e2e-alpha"] = blocked({ currentState: "ESCALATION_FINAL", escalationHistory: [], escalationProvenance: null, recovery: null });
    view();
    expect(await screen.findByTestId("sdd-blocked-banner")).toHaveTextContent("阻塞：ESCALATION_FINAL");
    expect(screen.getByTestId("sdd-escalation-summary")).toHaveTextContent("（沒有升級紀錄）");
    expect(screen.queryByTestId("sdd-escalation-source")).toBeNull(); // provenance 缺席：不顯示這一行（不寫「—」）
  });

  it("🔴 人工恢復後（IMPLEMENTATION）即使 escalationProvenance 還在、歷史末筆已有 resolved_at：不顯示橫幅、不顯示 ESCALATION 區塊與恢復指令（不得只看 provenance）", async () => {
    const { world } = sddWorld();
    world.fsms["e2e-alpha"] = fsmOf("e2e-alpha", {
      currentState: "IMPLEMENTATION",
      phase: phaseOf("IMPLEMENTATION", 5),
      escalationHistory: [{ ...OPEN, resolved_at: new Date(2026, 9, 17, 10, 0, 0).toISOString(), resolution: "人工恢復" }],
      escalationProvenance: { source: "autoclaude_delegated_failed" },
      recovery: null,
    });
    view();
    await screen.findByTestId("sdd-phase");
    expect(screen.queryByTestId("sdd-blocked-banner")).toBeNull();
    expect(screen.queryByTestId("sdd-escalation")).toBeNull();
    expect(screen.queryByTestId("sdd-recovery")).toBeNull();
    expect(screen.getByTestId("sdd-card").textContent).not.toContain("autoclaude_delegated_failed");
  });

  it("卡片仍是唯讀：沒有阻塞時沒有任何按鈕；阻塞時按鈕只有兩個「複製」，全部請求都是 GET", async () => {
    const { world, calls } = sddWorld();
    world.fsms["e2e-alpha"] = blocked();
    view();
    await screen.findByTestId("sdd-recovery");
    expect(
      within(screen.getByTestId("sdd-card"))
        .getAllByRole("button")
        .map((b) => b.textContent),
    ).toEqual(["複製", "複製"]);
    expect(calls.every((c) => c.method === "GET")).toBe(true);
  });
});

describe("AISDLC_SDD 引擎卡：專案模式（契約 §4.3 M-21；專案有綁定 FSM 專案）", () => {
  const EXEC_PATH = "/work/core";
  /** 專案模式的假後端：`?projectId=P1`（不帶 project）＝專案根下的有效 FSM 專案；再帶 project＝同一個狀態目錄內改選。 */
  function projectWorld(patch: { reason?: SddEngineStatus["reason"]; available?: boolean; throwNotFound?: boolean } = {}) {
    const files: Record<string, SddFsmState> = {
      "core-fsm": fsmOf("core-fsm", { fsmProject: "core-fsm", phase: phaseOf("IMPLEMENTATION", 5) }),
      "other-fsm": fsmOf("other-fsm", { fsmProject: "other-fsm", currentState: "REVIEW", phase: phaseOf("REVIEW", 6) }),
    };
    const entries = Object.values(files).map((f) => entry(f.fsmProject as string, f.currentState as string));
    const { calls } = stubApi((c: ApiCall) => {
      if (c.path !== PATH) return undefined;
      if (patch.throwNotFound) return failure(404, { message: `專案不存在或已刪除：${P1}` });
      const version = { latest: "AISDLC_SDD_v9.99", root: "/sdd/AISDLC_SDD_v9.99" };
      const base = { checkedAt: CHECKED_AT };
      if (patch.available === false) return { data: { available: false, reason: patch.reason ?? "bridge_unreachable", version: null, projects: [], fsm: null, ...base } satisfies SddEngineStatus };
      if (patch.reason)
        return { data: { available: true, reason: patch.reason, version, projects: patch.reason === "sdd_root_rejected" ? [] : entries, fsm: null, ...base } satisfies SddEngineStatus };
      const project = c.query.get("project") ?? "core-fsm";
      const fsm = files[project] ?? null;
      return { data: { available: true, reason: fsm ? null : "fsm_not_found", version, projects: entries, fsm, ...base } satisfies SddEngineStatus };
    });
    return { calls, files };
  }

  function projectView(binding: { sddProject?: string | null; executionPath?: string } = { sddProject: "core-fsm", executionPath: EXEC_PATH }) {
    return render(
      <Providers client={makeClient()}>
        <SddEngineCard binding={{ projectId: P1, ...binding }} />
      </Providers>,
    );
  }
  const urlsOf = (calls: ApiCall[]) => sddCalls(calls).map((c) => c.url);

  it("專案有 sddProject：只發一個請求 ?projectId=（不帶 project，由後端取有效 FSM 專案）；顯示該 FSM；下拉預選它的標準鍵；不會有全域模式的第一段請求", async () => {
    const { calls } = projectWorld();
    projectView();
    expect(await screen.findByTestId("sdd-state")).toHaveTextContent("IMPLEMENTATION");
    expect(urlsOf(calls)).toEqual([`${PATH}?projectId=${P1}`]);
    expect(screen.getByTestId("sdd-card")).toHaveAttribute("data-mode", "project");
    const select = screen.getByTestId("sdd-project-select") as HTMLSelectElement;
    expect([...select.options].map((o) => o.value)).toEqual(["core-fsm", "other-fsm"]);
    expect(select.value).toBe("core-fsm");
    expect(screen.getByTestId("sdd-phase")).toHaveAttribute("data-phase", "IMPLEMENTATION");
  });

  it("下拉改選同一個狀態目錄內的其他 FSM 專案：改帶 ?projectId=&project=；不寫入 localStorage 的「上次選的專案」（那是全域模式的方便）", async () => {
    const { calls } = projectWorld();
    projectView();
    await screen.findByTestId("sdd-state");
    await userEvent.selectOptions(screen.getByTestId("sdd-project-select"), "other-fsm");
    await waitFor(() => expect(screen.getByTestId("sdd-state")).toHaveTextContent("REVIEW"));
    expect(urlsOf(calls)).toEqual([`${PATH}?projectId=${P1}`, `${PATH}?projectId=${P1}&project=other-fsm`]);
    expect(window.localStorage.getItem(SDD_PROJECT_STORAGE_KEY)).toBeNull();
    expect(screen.getByTestId("sdd-phase")).toHaveAttribute("data-phase", "REVIEW");
  });

  it("沒有綁定（sddProject 為 null 或空白、或沒有 binding）：維持 M-20 的全域模式——兩段請求、不帶 projectId", async () => {
    for (const binding of [{ sddProject: null }, { sddProject: "  " }, {}]) {
      const { calls } = sddWorld();
      const { unmount } = render(
        <Providers client={makeClient()}>
          <SddEngineCard binding={{ projectId: P1, ...binding }} />
        </Providers>,
      );
      await screen.findByTestId("sdd-state");
      expect(projectParams(calls)).toEqual([null, "e2e-alpha"]);
      expect(sddCalls(calls).every((c) => !c.query.has("projectId"))).toBe(true);
      expect(screen.getByTestId("sdd-card")).toHaveAttribute("data-mode", "global");
      unmount();
    }
  });

  it("專案模式每次輪詢仍只有一個請求（30 秒）：輪詢節奏不因多了 projectId 而變密", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const { calls } = projectWorld();
      projectView();
      await screen.findByTestId("sdd-state");
      expect(sddCalls(calls)).toHaveLength(1);
      await vi.advanceTimersByTimeAsync(29_000);
      expect(sddCalls(calls)).toHaveLength(1);
      await vi.advanceTimersByTimeAsync(2_000);
      await waitFor(() => expect(sddCalls(calls)).toHaveLength(2));
    } finally {
      focusManager.setFocused(undefined);
      vi.useRealTimers();
    }
  });

  it("sdd_root_rejected（專案路徑不在 Bridge 允許的根目錄內）：引擎仍是「可用」，顯示專案的文案（不是「尚無 FSM 狀態檔」）", async () => {
    projectWorld({ reason: "sdd_root_rejected" });
    projectView();
    const note = await screen.findByTestId("sdd-message");
    expect(note).toHaveTextContent("專案路徑不在 Bridge 允許的根目錄內（或已不存在）");
    expect(note).toHaveAttribute("data-reason", "sdd_root_rejected");
    expect(screen.getByTestId("sdd-status")).toHaveAttribute("data-available", "true");
    expect(screen.queryByTestId("sdd-empty")).toBeNull();
    expect(screen.queryByTestId("sdd-project-select")).toBeNull();
  });

  it("綁定的 FSM 專案沒有狀態檔（fsm_not_found）：顯示文案並加註建立位置；下拉仍列出綁定的名字（註明狀態檔不存在）與目錄內其他專案，改選就恢復", async () => {
    const world = projectWorld();
    const real = globalThis.fetch;
    vi.stubGlobal("fetch", async (input: string, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("projectId") && !url.includes("project=")) {
        const res = await real(input, init);
        const body = await res.json();
        return new Response(JSON.stringify({ ...body, data: { ...body.data, reason: "fsm_not_found", fsm: null } }), { status: 200, headers: { "content-type": "application/json" } });
      }
      return real(input, init);
    });
    projectView({ sddProject: "missing-fsm", executionPath: EXEC_PATH });
    const note = await screen.findByTestId("sdd-message");
    expect(note).toHaveTextContent("找不到所選專案的 FSM 狀態檔");
    expect(screen.getByTestId("sdd-message-hint")).toHaveTextContent("請在專案根的 SDD session 建立：/work/core/build/reports/fsm");
    const select = screen.getByTestId("sdd-project-select") as HTMLSelectElement;
    expect([...select.options].map((o) => o.text)).toEqual(["core-fsm", "other-fsm", "missing-fsm（狀態檔已不存在）"]);
    expect(select.value).toBe("missing-fsm");
    await userEvent.selectOptions(select, "core-fsm");
    expect(await screen.findByTestId("sdd-state")).toHaveTextContent("IMPLEMENTATION");
    expect(world.calls.length).toBeGreaterThan(1);
  });

  it("引擎不可用（bridge_unreachable）：與全域模式相同的文案；專案已刪除（console-api 404）：顯示錯誤與重試，不編造狀態", async () => {
    projectWorld({ available: false, reason: "bridge_unreachable" });
    const first = projectView();
    expect(await screen.findByTestId("sdd-message")).toHaveTextContent("Engine Bridge 無法連線");
    first.unmount();

    projectWorld({ throwNotFound: true });
    projectView();
    expect(await screen.findByText("無法取得 AISDLC_SDD 引擎狀態")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(`專案不存在或已刪除：${P1}`);
    expect(screen.getByRole("button", { name: "重試" })).toBeInTheDocument();
  });

  it("專案模式的 ESCALATION：階段進度與恢復指令照常顯示（與全域模式同一組元件）", async () => {
    const files = {
      "core-fsm": fsmOf("core-fsm", {
        fsmProject: "core-fsm",
        currentState: "ESCALATION",
        phase: phaseOf("BLOCKED", 0, { blocking: true }),
        escalationHistory: [{ triggered_at: new Date(2026, 9, 17, 9, 0, 0).toISOString(), trigger_reason: "r", resolved_at: null }],
        recovery: { target: "IMPLEMENTATION", powershell: "ps-cmd <人工原因>", posix: "sh-cmd <人工原因>" },
      }),
    };
    stubApi((c) =>
      c.path === PATH
        ? {
            data: {
              available: true,
              reason: null,
              version: { latest: "v", root: "/r" },
              projects: [entry("core-fsm", "ESCALATION")],
              fsm: files["core-fsm"],
              checkedAt: CHECKED_AT,
            } satisfies SddEngineStatus,
          }
        : undefined,
    );
    projectView();
    expect(await screen.findByTestId("sdd-blocked-banner")).toHaveTextContent("阻塞：ESCALATION");
    expect(screen.getByTestId("sdd-recovery-command-posix")).toHaveTextContent("sh-cmd <人工原因>");
  });
});
