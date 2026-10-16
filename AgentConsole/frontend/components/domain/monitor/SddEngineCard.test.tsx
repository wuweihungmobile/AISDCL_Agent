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
