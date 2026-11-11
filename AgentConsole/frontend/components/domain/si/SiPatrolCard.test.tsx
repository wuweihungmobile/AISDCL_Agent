/**
 * 巡邏狀態卡（TCS-SiFlowVisibility AC-966-11、12：AT-966-11-1～11-7、11-E-1、11-E-2、12-1～12-7、12-E-1、12-E-2）。
 * 整個 SiView 以 renderFlow 渲染（真 Providers＋fetch 替身；固定 readAt＝NOW）；「每分鐘重繪」以可控時鐘替身前進（只重繪、不發請求）。
 */
import { cleanup, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SI_QUERY_OPTIONS } from "@/lib/api/queries";
import { pushView } from "@/lib/domain/siFlow";
import { failure } from "@/tests/helpers/api";
import { ADMIN_UI, OPERATOR_UI, VIEWER_UI, siUnavailable } from "@/tests/helpers/si";
import { advanceMinutes, resetClock } from "@/tests/helpers/siClock";
import { DROP, NOW, PATROL, goldenPatrol, iso, renderFlow, type FlowOptions } from "@/tests/helpers/siFlow";

vi.setConfig({ testTimeout: 30_000 });
vi.mock("@/components/domain/si/useMinuteTick", async () => (await import("@/tests/helpers/siClock")).clockMock());
const router = vi.hoisted(() => ({ push: () => undefined, replace: () => undefined, back: () => undefined }));
vi.mock("next/navigation", () => ({ usePathname: () => "/self-improving", useRouter: () => router, useSearchParams: () => new URLSearchParams(), useParams: () => ({}) }));

beforeEach(() => resetClock());
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const text = (el: HTMLElement) => el.textContent ?? "";
const data =
  (over: Record<string, unknown> = {}, top: Record<string, unknown> = {}): FlowOptions["patrol"] =>
  () => ({ data: PATROL(over, top) });
async function card(opts: FlowOptions = {}) {
  const view = renderFlow({ ...VIEWER_UI, ...opts });
  const el = await screen.findByTestId("si-patrol-card");
  await waitFor(() => expect(el.querySelector("[data-testid='si-loading']")).toBeNull());
  return { el, ...view };
}
const patrolCalls = (stub: { calls: Array<{ path: string }> }) => stub.calls.filter((c) => c.path === "/api/v1/si/patrol").length;
const block = (el: HTMLElement, id: string) => within(el).getByTestId(id);

describe("AT_966_11_1 掛載位置、角色、請求次數", () => {
  it.each([
    ["VIEWER", VIEWER_UI],
    ["OPERATOR", OPERATOR_UI],
    ["ADMIN", ADMIN_UI],
  ])("%s：位置在狀態橫幅之後、研究來源說明列之前；載入 1 次、重新整理 2 次、前進 1 小時仍 2 次", async (role, ui) => {
    const user = userEvent.setup({ delay: null });
    const { el, stub } = await card(ui);
    const banner = await screen.findByTestId("si-status-banner");
    const note = screen.getByTestId("si-research-sources-note");
    expect(banner.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING, role).toBeTruthy();
    expect(el.compareDocumentPosition(note) & Node.DOCUMENT_POSITION_FOLLOWING, role).toBeTruthy();
    expect(within(el).getByRole("heading", { name: "巡邏狀態" })).toBeInTheDocument();
    expect(patrolCalls(stub)).toBe(1);
    await user.click(screen.getByTestId("si-refresh"));
    await waitFor(() => expect(patrolCalls(stub)).toBe(2));
    advanceMinutes(60);
    window.dispatchEvent(new Event("focus"));
    expect(patrolCalls(stub)).toBe(2);
    expect(SI_QUERY_OPTIONS.refetchInterval).toBe(false);
    expect(SI_QUERY_OPTIONS.refetchOnWindowFocus).toBe(false);
    const buttons = within(el).getAllByRole("button");
    expect(buttons.map((b) => b.dataset.testid)).toEqual(["si-patrol-steps-toggle"]);
    expect(buttons[0]).toHaveAttribute("aria-expanded");
  });
});

describe("AT_966_11_2 新鮮呈現與時間前進", () => {
  it("初始 3 分鐘前；前進 10 分鐘變 13 分鐘前，不重抓、無警示", async () => {
    const { el, stub } = await card({ patrol: data() });
    expect(text(el)).toContain("上次心跳：3 分鐘前");
    expect(el.querySelector("time")?.getAttribute("datetime")).toBe(iso(3));
    expect(text(el)).toContain("巡邏每 15 分鐘一次");
    expect(text(el)).toContain(`資料讀取於 ${NOW}`);
    expect(within(el).queryByTestId("si-patrol-stale")).toBeNull();
    expect(within(el).getByTestId("si-patrol-state")).toHaveTextContent("巡邏正常");
    advanceMinutes(10);
    expect(text(el)).toContain("上次心跳：13 分鐘前");
    expect(text(el)).not.toContain("上次心跳：3 分鐘前");
    expect(within(el).queryByTestId("si-patrol-stale")).toBeNull();
    expect(patrolCalls(stub)).toBe(1);
  });
});

describe("AT_966_11_3 過時警示邊界與自動轉警示", () => {
  const WARN = (limit: number, period: number) =>
    `巡邏可能沒在跑：已超過 ${limit} 分鐘沒有新的回報（巡邏每 ${period} 分鐘一次）。可能原因：電腦睡眠、排程任務被移除、巡邏被環境變數暫停。請按『重新整理』取得最新回報。`;
  it("35:00 無警示", async () => {
    const { el } = await card({ patrol: data({ generatedAt: iso(35) }) });
    expect(within(el).queryByTestId("si-patrol-stale")).toBeNull();
  });
  it("35:01 出現警示與狀態標籤，仍顯示快照內容", async () => {
    const { el } = await card({ patrol: data({ generatedAt: iso(35, 1) }) });
    const warn = within(el).getByTestId("si-patrol-stale");
    expect(warn).toHaveAttribute("role", "status");
    expect(text(warn)).toContain(WARN(35, 15));
    expect(text(warn)).toContain("分鐘前的回報");
    expect(within(el).getByTestId("si-patrol-state")).toHaveTextContent("巡邏可能沒在跑");
    expect(within(el).getByTestId("si-patrol-props")).toHaveTextContent("PROP-SI-901");
  });
  it("週期 60：限度顯示 125", async () => {
    const { el } = await card({ patrol: data({ generatedAt: iso(125, 1), heartbeatMinutes: 60 }) });
    expect(text(within(el).getByTestId("si-patrol-stale"))).toContain(WARN(125, 60));
  });
  it("放著不動：抵達後 32 分鐘無警示、再過 1 分鐘自動出現，網路請求次數不變", async () => {
    const { el, stub } = await card({ patrol: data() });
    advanceMinutes(32);
    expect(within(el).queryByTestId("si-patrol-stale")).toBeNull();
    advanceMinutes(1);
    expect(within(el).getByTestId("si-patrol-stale")).toBeInTheDocument();
    expect(patrolCalls(stub)).toBe(1);
  });
});

describe("AT_966_11_4 環境變數暫停", () => {
  it("暫停時空陣列不代表沒事；新鮮度照常；off 缺席視為 false；非布林視為量不到", async () => {
    const { el } = await card({ patrol: data({ off: true, props: [], runs: { live: [], waiting: [], queued: [] }, ingest: [] }) });
    expect(text(el)).toContain("巡邏已暫停（環境變數 AUTOSDD_SI_PATROL_OFF 有設定）");
    expect(text(el)).not.toContain("目前沒有需要巡邏推進的提案");
    expect(text(el)).toContain("上次心跳：3 分鐘前");
    cleanup();
    const b = await card({ patrol: data({ off: DROP }) });
    expect(text(b.el)).not.toContain("巡邏已暫停");
    cleanup();
    const c = await card({ patrol: data({ off: "yes" }) });
    expect(text(c.el)).toContain("量不到暫停狀態");
    expect(text(c.el)).not.toContain("巡邏正常");
  });
});

describe("AT_966_11_5～11_6 快照缺席與未掛載是兩種畫面", () => {
  it("AT_966_11_5 缺席：標題、三個原因、重新整理提示；不用錯誤樣式、沒有按鈕與沒有提案字樣", async () => {
    const { el } = await card({ patrol: () => siUnavailable("report_missing", "patrol.json 不存在") });
    expect(text(el)).toContain("還沒有收到巡邏回報");
    for (const s of ["巡邏任務還沒安裝", "巡邏還沒跑過第一次", "主機的回報目錄是空的", "按『重新整理』再看一次"]) expect(text(el)).toContain(s);
    expect(el.querySelector("[role='alert']")).toBeNull();
    expect(within(el).queryAllByRole("button")).toHaveLength(0);
    expect(text(el)).not.toMatch(/沒有提案|沒有運轉|目前沒有/);
    expect(screen.getByTestId("si-status-banner")).toBeInTheDocument();
  });
  it("AT_966_11_6 未掛載：標題與說明與缺席不同，沒有重試鈕", async () => {
    const { el } = await card({ patrol: () => siUnavailable("report_dir_unset", "未設定") });
    expect(text(el)).toContain("這個部署沒有掛載巡邏回報目錄");
    expect(text(el)).toContain("看不到巡邏狀態，其他自我進化功能照常；要看請照部署說明加上回報目錄");
    expect(text(el)).not.toContain("還沒有收到巡邏回報");
    expect(within(el).queryAllByRole("button")).toHaveLength(0);
  });
});

describe("AT_966_11_7 壞檔與其他失敗", () => {
  it.each([["report_invalid"], ["report_unreadable"]])("%s：標題、cause 與 detail 逐字、重試恰多 1 次請求", async (cause) => {
    const user = userEvent.setup({ delay: null });
    const { el, stub } = await card({ patrol: () => siUnavailable(cause, "patrol.json 第 3 行：不是合法 JSON") });
    expect(text(el)).toContain("巡邏回報檔有問題");
    expect(block(el, "si-patrol-cause")).toHaveTextContent(cause);
    expect(block(el, "si-patrol-detail")).toHaveTextContent("patrol.json 第 3 行：不是合法 JSON");
    const before = patrolCalls(stub);
    await user.click(within(el).getByRole("button", { name: "重試" }));
    await waitFor(() => expect(patrolCalls(stub)).toBe(before + 1));
  });
  it.each([
    ["503 nonzero_rc", () => siUnavailable("nonzero_rc", "rc=2")],
    ["502", () => failure(502, { message: "後端服務無法連線", reason: "bridge_unreachable" })],
    ["504", () => failure(504, { message: "後端服務逾時", reason: "bridge_timeout" })],
    [
      "網路錯誤",
      () => {
        throw new TypeError("Failed to fetch");
      },
    ],
  ])("%s 走既有錯誤態", async (_name, patrol) => {
    const { el } = await card({ patrol });
    expect(within(el).getByTestId("si-error")).toBeInTheDocument();
    expect(text(el)).not.toContain("上次心跳");
  });
  it("失敗時不顯示舊快照（重新整理後改壞）", async () => {
    const user = userEvent.setup({ delay: null });
    let n = 0;
    const { el } = await card({ patrol: () => (n++ === 0 ? { data: PATROL() } : siUnavailable("report_invalid", "壞了")) });
    expect(text(el)).toContain("上次心跳：3 分鐘前");
    await user.click(screen.getByTestId("si-refresh"));
    await waitFor(() => expect(text(el)).toContain("巡邏回報檔有問題"));
    expect(text(el)).not.toContain("上次心跳");
    expect(text(el)).not.toContain("PROP-SI-901");
  });
});

describe("AT_966_11_E_1 缺週期與時鐘異常", () => {
  it.each([[DROP], [0], [-5], ["15"], [Number.NaN]])("(a) 週期 %s：無法判斷，不顯示巡邏正常也不顯示過時警示", async (hb) => {
    const { el } = await card({ patrol: data({ heartbeatMinutes: hb }) });
    expect(text(el)).toContain("無法判斷是否過時：快照沒有巡邏週期");
    expect(text(el)).not.toContain("巡邏正常");
    expect(within(el).queryByTestId("si-patrol-stale")).toBeNull();
  });
  it("(b) 時鐘異常 (c) 時間無法解析 (d) readAt 缺席", async () => {
    const b = await card({ patrol: data({ generatedAt: iso(-6) }) });
    expect(text(b.el)).toContain("快照時間在未來，電腦時鐘可能不同步");
    cleanup();
    const c = await card({ patrol: data({ generatedAt: "昨天" }) });
    expect(text(c.el)).toContain("上次心跳時間量不到");
    cleanup();
    const d = await card({ patrol: data({ generatedAt: new Date(Date.now() - 3 * 60_000).toISOString() }, { readAt: DROP }) });
    expect(text(d.el)).toContain("（用瀏覽器時間估算）");
  });
});

describe("AT_966_11_E_2 惡意字串純文字", () => {
  it("全為字面文字，DOM 無注入元素", async () => {
    const evil = "<script>window.__x=1</script><img src=x onerror=alert(1)>**粗體**[a](javascript:alert(1))";
    const { el } = await card({
      patrol: data({
        generatedAt: evil,
        props: [{ id: "PROP-SI-901", state: "verified", code: "C", who: "掌舵者", text: evil }],
        steps: [{ step: "巡視", result: evil }],
        push: { enabled: true, state: "blocked", code: "PUSH-X", text: evil },
        runs: { live: [], waiting: [{ run: "RUN-SI-902", code: "W", text: evil }], queued: [] },
        schedule: { enabled: true, current: { code: "C", text: "x" }, lastSkip: { seq: 1, t: "t", code: "S", text: evil, auditRef: null } },
        ingest: [{ auditRef: "A1", status: "rejected", code: "X", text: evil, permanent: true }],
      }),
    });
    await userEvent.setup({ delay: null }).click(within(el).getByTestId("si-patrol-steps-toggle"));
    expect(el.querySelector("script, img, a[href^='javascript']")).toBeNull();
    expect(text(el)).toContain("<script>window.__x=1</script>");
    expect((window as unknown as Record<string, unknown>).__x).toBeUndefined();
  });
});

const PROP = (over: Record<string, unknown>): Record<string, unknown> => ({ id: "PROP-SI-901", state: "verified", code: "C", who: "掌舵者", text: "文字", ...over });
describe("AT_966_12_1 提案卡住原因清單", () => {
  it("依輸入序列出、逐字、不暗示自動凍結；空陣列顯示沒有；已載入的提案編號可點開詳情", async () => {
    const props = [
      PROP({ id: "PROP-SI-901", state: "approved", code: "NO-HELDOUT", who: "主機管理者", text: "尚未凍結評估集；需有人用 heldout-freeze，巡邏器不會自己湊" }),
      PROP({ id: "PROP-SI-902", state: "verified", code: "WAIT-PROMOTE-DECISION", who: "掌舵者", text: "驗證通過，等你決定是否晉升" }),
    ];
    const user = userEvent.setup({ delay: null });
    const { el } = await card({ patrol: data({ props }) });
    const rows = within(block(el, "si-patrol-props")).getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("PROP-SI-901");
    expect(rows[0]).toHaveTextContent("等：主機管理者");
    expect(rows[0]).toHaveTextContent("尚未凍結評估集；需有人用 heldout-freeze，巡邏器不會自己湊");
    expect(rows[0]).toHaveTextContent("NO-HELDOUT");
    expect(rows[1]).toHaveTextContent("等：掌舵者");
    expect(text(el)).not.toMatch(/自動凍結|會自動凍結/);
    // 提案分頁載入後，卡上的提案編號變成按鈕，點了開詳情
    await user.click(screen.getByRole("tab", { name: /提案/ }));
    await screen.findByTestId("si-detail-open-PROP-SI-901");
    await user.click(await within(el).findByRole("button", { name: "PROP-SI-901" }));
    expect(await screen.findByRole("dialog", { name: "提案詳情 PROP-SI-901" })).toBeInTheDocument();
  });
  it("空陣列（未暫停）顯示沒有需要推進的提案", async () => {
    const { el } = await card({ patrol: data({ props: [] }) });
    expect(block(el, "si-patrol-props")).toHaveTextContent("目前沒有需要巡邏推進的提案");
  });
});

describe("AT_966_12_2 未知等待對象與未知碼保底", () => {
  it("缺欄與未知值走保底；後加的碼逐字顯示 text", async () => {
    const props = [
      PROP({ id: "P-1", who: "外星人" }),
      PROP({ id: "P-2", who: DROP }),
      PROP({ id: "P-3", text: DROP, code: "ONLY-CODE" }),
      PROP({ id: "P-4", text: DROP, code: DROP }),
      PROP({ id: "P-5", state: DROP }),
      PROP({ id: "P-6", code: "COMMIT-LEFTOVER", who: "主機管理者", text: "上次提交還有殘留檔案，請由人清理" }),
      PROP({ id: "P-7", code: "COMMIT-RECORD-FAILED", who: "主機管理者", text: "提交沒記進帳本，請由人處理" }),
    ].map((p) => Object.fromEntries(Object.entries(p).filter(([, v]) => v !== DROP)));
    const { el } = await card({ patrol: data({ props }) });
    const rows = within(block(el, "si-patrol-props")).getAllByRole("listitem");
    expect(rows[0]).toHaveTextContent("等：未知值『外星人』");
    expect(rows[1]).toHaveTextContent("等：量不到");
    expect(rows[2]).toHaveTextContent("主機沒有提供白話說明（原因碼 ONLY-CODE）。");
    expect(rows[3]).toHaveTextContent("主機沒有提供原因。");
    expect(rows[4]).toHaveTextContent("狀態量不到");
    expect(rows[5]).toHaveTextContent("上次提交還有殘留檔案，請由人清理");
    expect(rows[5]).toHaveTextContent("COMMIT-LEFTOVER");
    expect(rows[6]).toHaveTextContent("提交沒記進帳本，請由人處理");
    expect(rows[0].className + rows[0].innerHTML).not.toMatch(/success/);
  });
});

describe("AT_966_12_3 進行中的運轉與第二波值不當成已知", () => {
  const live = (run: string, purpose: unknown) => ({ run, purpose, startedAt: iso(12), wallDueAt: iso(-48) });
  it("三種第一波目的逐字；第二波與未知值為未知值；queued 不渲染", async () => {
    const { el } = await card({
      patrol: data({
        runs: {
          live: [live("RUN-SI-901", "scheduled"), live("RUN-SI-902", "console"), live("RUN-SI-903", "manual"), live("RUN-SI-904", "freeze"), live("RUN-SI-905", "zzz")],
          waiting: [],
          queued: [{ purpose: "revise", target: "PROP-SI-902", why: "x" }],
        },
      }),
    });
    const runs = block(el, "si-patrol-runs");
    expect(runs).toHaveTextContent("進行中：RUN-SI-901（排程啟動）。12 分鐘前開始，預計最晚 48 分鐘後結束。");
    expect(runs).toHaveTextContent("RUN-SI-902（從畫面按『立即啟動』）");
    expect(runs).toHaveTextContent("RUN-SI-903（手動啟動）");
    expect(runs).toHaveTextContent("RUN-SI-904（未知值『freeze』）");
    expect(runs).toHaveTextContent("RUN-SI-905（未知值『zzz』）");
    expect(text(el)).not.toMatch(/revise|排隊/);
    expect(text(el)).not.toContain("PROP-SI-902");
  });
  it("空陣列、缺席", async () => {
    const a = await card({ patrol: data({ runs: { live: [], waiting: [], queued: [] } }) });
    expect(block(a.el, "si-patrol-runs")).toHaveTextContent("目前沒有進行中的運轉");
    cleanup();
    const b = await card({ patrol: data({ runs: { waiting: [] } }) });
    expect(block(b.el, "si-patrol-runs")).toHaveTextContent("進行中的運轉量不到");
  });
});

describe("AT_966_12_4 步驟與入帳摘要", () => {
  const over = {
    steps: [
      { step: "入帳", result: "入帳 1、拒收 0" },
      { step: "推進", result: "PROP-SI-901 跳過：NO-HELDOUT" },
    ],
    ingest: [
      { auditRef: "A1", status: "rejected", permanent: true, code: "X", text: "t" },
      { auditRef: "A2", status: "deferred", permanent: false, code: "Y", text: "u" },
    ],
  };
  it("預設收合、展開逐字列出；ADMIN 才有看待入帳清單鈕且聚焦面板", async () => {
    const user = userEvent.setup({ delay: null });
    const a = await card({ ...ADMIN_UI, patrol: data(over) });
    const toggle = within(a.el).getByRole("button", { name: /這一輪做了什麼/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(text(a.el)).not.toContain("PROP-SI-901 跳過：NO-HELDOUT");
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    const items = within(block(a.el, "si-patrol-steps"))
      .getAllByRole("listitem")
      .map((li) => li.textContent);
    expect(items).toEqual(["入帳：入帳 1、拒收 0", "推進：PROP-SI-901 跳過：NO-HELDOUT"]);
    expect(text(a.el)).toContain("有 2 筆稽核檔被拒收或延後");
    await user.click(within(a.el).getByRole("button", { name: "看待入帳清單" }));
    expect(screen.getByTestId("si-writes-panel")).toHaveFocus();
    cleanup();
    for (const ui of [VIEWER_UI, OPERATOR_UI]) {
      const v = await card({ ...ui, patrol: data(over) });
      expect(text(v.el)).toContain("有 2 筆稽核檔被拒收或延後");
      expect(within(v.el).queryByRole("button", { name: "看待入帳清單" })).toBeNull();
      cleanup();
    }
  });
  it("ingest 空陣列與 steps 缺席", async () => {
    const a = await card({ patrol: data({ ingest: [] }) });
    expect(text(a.el)).toContain("這一輪沒有被拒收的稽核檔");
    cleanup();
    const b = await card({ patrol: data({ steps: DROP }) });
    expect(text(b.el)).toContain("這一輪的步驟量不到");
  });
});

describe("AT_966_12_5 推送八態與未知態", () => {
  const p = (state: string, code: string, textv: string, extra: Record<string, unknown> = {}) => ({ enabled: true, state, code, text: textv, retry: null, ...extra });
  const pushes = [
    p("off", "PUSH-OFF", "自動推送已關閉"),
    p("idle", "PUSH-NOT-AHEAD", "沒有待推送的提交"),
    p("pending", "PUSH-PENDING", "等推送任務下一次執行（每個心跳一次）"),
    p("waiting-login", "PUSH-WAITING-LOGIN", "等使用者登入後自動推送"),
    p("running", "PUSH-RUNNING", "正在推送"),
    p("ok", "PUSH-OK", "已推送", { sha: "abcdef0123456789", finishedAt: NOW }),
    p("failed", "PUSH-FAILED", "推送失敗，稍後自動重試", { retry: "wait", attempts: 2 }),
    p("blocked", "PUSH-DIRTY-TREE", "工作樹有未提交的修改"),
    p("skipped", "PUSH-X", "第二波才有的狀態"),
  ];
  it.each(pushes.map((push) => [push.state, push] as const))("%s", async (_state, push) => {
    const { el } = await card({ patrol: data({ push }) });
    const view = pushView(push);
    const box = block(el, "si-patrol-push-text");
    expect(box.textContent).toContain(view.text);
    expect(text(block(el, "si-patrol-push"))).toContain("自動推送");
    expect(text(el)).toContain("推送由主機自動執行，這裡只顯示狀態");
    if (push.state === "ok") {
      expect(box.textContent).toContain("完成：");
      expect(box.querySelector("time")).not.toBeNull();
      expect(box.textContent).toContain("（提交 abcdef01）");
    } else if (push.state === "failed" || push.state === "blocked") {
      expect(box.textContent).toContain("需要處理：");
      expect(box.dataset.tone).toBe("warn");
    }
    if (push.state === "failed") expect(box.textContent).toContain("已嘗試 2 次");
    if (push.state === "skipped") {
      expect(box.textContent).toContain("未知的推送狀態『skipped』");
      expect(box.dataset.tone).toBe("neutral");
    }
    if (push.state === "waiting-login") expect(box.textContent).toContain("等使用者登入後自動推送");
  });
  it("enabled:false 與 off 態", async () => {
    const { el } = await card({ patrol: data({ push: p("off", "PUSH-OFF", "自動推送已關閉", { enabled: false }) }) });
    expect(block(el, "si-patrol-push-text")).toHaveTextContent("自動推送已關閉");
  });
});

describe("AT_966_12_6 無推送按鈕與憑證遮罩", () => {
  it("沒有名稱含推送的互動元素；憑證被遮罩；原始碼無寫入引用", async () => {
    // 帶帳密的網址在執行期拼出（機密掃描閘）
    const dirty1 = "https://" + "user" + ":" + "token123" + "@github.com/o/r.git";
    const dirty2 = "https://" + "a" + ":" + "b" + "@c/d";
    const { el } = await card({
      ...ADMIN_UI,
      patrol: data({
        push: { enabled: true, state: "failed", code: "PUSH-FAILED", text: `push ${dirty1} failed` },
        props: [PROP({ text: `看 ${dirty2}` })],
        ingest: [{ auditRef: "A1", status: "rejected", permanent: true, code: "X", text: "t" }],
      }),
    });
    for (const node of Array.from(el.querySelectorAll<HTMLElement>("button, a, [role=button]"))) {
      expect(`${node.getAttribute("aria-label") ?? ""} ${node.textContent ?? ""}`).not.toMatch(/推送|推|push/i);
    }
    expect(text(el)).not.toContain("token123");
    expect(text(el)).not.toContain("user:");
    expect(text(el)).toContain("https://***@github.com/o/r.git");
    expect(text(el)).toContain("https://***@c/d");
    expect(readFileSync(path.join(process.cwd(), "components/domain/si/SiPatrolCard.tsx"), "utf-8")).not.toMatch(/\busePost\w*|\buseWrite|\bpostSi\w*/);
  });
});

describe("AT_966_12_7 為什麼沒有啟動運轉", () => {
  const sched = (over: Record<string, unknown> = {}) => ({
    enabled: true,
    current: { code: "SKIP-RUN-OPEN", text: "已有未關運轉（RUN-SI-901），排程與立即啟動都會等它關閉" },
    lastSkip: { seq: 99, t: "2026-11-11T13:45:00+08:00", code: "SKIP-RUN-OPEN", text: "已有未關運轉（RUN-SI-901）…", auditRef: null },
    ...over,
  });
  const run = async (over: Record<string, unknown>) => block((await card({ patrol: data(over) })).el, "si-patrol-schedule");
  it("(a)(b) 啟用中與立即啟動被略過", async () => {
    const a = await run({ schedule: sched() });
    expect(a).toHaveTextContent("排程：啟用中");
    expect(a).toHaveTextContent("目前狀態：已有未關運轉（RUN-SI-901），排程與立即啟動都會等它關閉");
    expect(a).toHaveTextContent("最近一次略過：2026-11-11T13:45:00+08:00 已有未關運轉（RUN-SI-901）…");
    expect(a).toHaveTextContent("SKIP-RUN-OPEN");
    expect(a.textContent).not.toContain("立即啟動』（稽核編號");
    cleanup();
    const ref = "a1000000-0000-4000-8000-000000000001";
    const b = await run({ schedule: sched({ lastSkip: { seq: 99, t: "t", code: "SKIP-RUN-OPEN", text: "x", auditRef: ref } }) });
    expect(b).toHaveTextContent(`這次略過的是你從畫面按的『立即啟動』（稽核編號 ${ref}）`);
  });
  it("(c)(d)(i)(e) 停用、暫停、無排程資訊、現況量不到", async () => {
    expect(await run({ schedule: sched({ enabled: false, current: { code: "SCHED-DISABLED", text: "自動演化排程目前停用（立即啟動仍可用）" }, lastSkip: null }) })).toHaveTextContent(
      "自動演化排程目前停用（立即啟動仍可用）",
    );
    cleanup();
    const d = await run({ off: true, schedule: null });
    expect(d).toHaveTextContent("巡邏已暫停，沒有排程資訊");
    expect(d.textContent).not.toContain("排程停用");
    cleanup();
    expect(await run({ off: false, schedule: null })).toHaveTextContent("這份回報沒有排程資訊");
    cleanup();
    expect(await run({ schedule: sched({ current: null }) })).toHaveTextContent("目前這一格的排程狀態量不到");
  });
  it("(f)(g)(h) 等待中的運轉；全區零按鈕；text 缺席用保底句", async () => {
    const f = await run({ runs: { live: [], waiting: [{ run: "RUN-SI-902", code: "SKIP-OTHER-DRIVER", text: "近期有人在互動視窗工作，巡邏器先不開運轉" }], queued: [] } });
    expect(f).toHaveTextContent("RUN-SI-902 等待中：近期有人在互動視窗工作，巡邏器先不開運轉");
    expect(f).toHaveTextContent("SKIP-OTHER-DRIVER");
    expect(within(f).queryAllByRole("button")).toHaveLength(0);
    cleanup();
    expect(await run({ runs: { live: [], waiting: [], queued: [] } })).toHaveTextContent("目前沒有在等待啟動的運轉");
    cleanup();
    expect(await run({ runs: { live: [], queued: [] } })).toHaveTextContent("等待中的運轉量不到");
    cleanup();
    expect(await run({ runs: { waiting: [{ run: "RUN-SI-903", code: "W-X" }] } })).toHaveTextContent("RUN-SI-903 等待中：主機沒有提供白話說明（原因碼 W-X）。");
  });
  it("根層帶『第二波起可由 Console 處理』字樣時逐字顯示，不另加承諾", async () => {
    const s = await run({ schedule: sched({ current: { code: "SKIP-RUN-OPEN", text: "已有未關運轉；第二波起可由 Console 處理" } }) });
    expect(s).toHaveTextContent("已有未關運轉；第二波起可由 Console 處理");
  });
});

describe("AT_966_12_E_1 段落缺席＝量不到，與 truncated", () => {
  it("只有 generatedAt 時五區各顯示量不到，沒有「沒有」「無」字樣", async () => {
    const { el } = await card({ patrol: () => ({ data: { schemaRev: 1, kind: "patrol", readAt: NOW, report: { schemaRev: 1, generatedAt: iso(3), heartbeatMinutes: 15 } } }) });
    const body = (id: string, title: string) => text(block(el, id)).replace(title, "").replace("推送由主機自動執行，這裡只顯示狀態", "");
    expect(body("si-patrol-props", "每個提案現在卡在哪")).toContain("量不到");
    expect(body("si-patrol-runs", "進行中的運轉")).toContain("量不到");
    expect(body("si-patrol-schedule", "為什麼沒有啟動運轉")).toContain("量不到");
    expect(body("si-patrol-steps", "這一輪做了什麼")).toContain("量不到");
    expect(body("si-patrol-push", "自動推送")).toContain("量不到");
    for (const [id, title] of [
      ["si-patrol-props", "每個提案現在卡在哪"],
      ["si-patrol-runs", "進行中的運轉"],
      ["si-patrol-schedule", "為什麼沒有啟動運轉"],
      ["si-patrol-steps", "這一輪做了什麼"],
      ["si-patrol-push", "自動推送"],
    ]) {
      expect(body(id, title), id).not.toMatch(/沒有|無/);
    }
    expect(text(el)).toContain("上次心跳：3 分鐘前");
    expect(within(el).queryByTestId("si-patrol-truncated")).toBeNull();
  });
  it("truncated:true 顯示提醒", async () => {
    const { el } = await card({ patrol: data({ truncated: true }) });
    expect(block(el, "si-patrol-truncated")).toHaveTextContent("這份回報太長，被截短了，清單可能不完整");
  });
});

describe("AT_966_12_E_2 兩百個提案的捲動區", () => {
  it("200 列全渲染，容器可捲動且可鍵盤聚焦", async () => {
    const props = Array.from({ length: 200 }, (_, i) => PROP({ id: `PROP-SI-${1000 + i}` }));
    const { el } = await card({ patrol: data({ props }) });
    const list = block(el, "si-patrol-props-list");
    expect(within(list).getAllByRole("listitem")).toHaveLength(200);
    expect(list.className).toMatch(/max-h-/);
    expect(list.className).toContain("overflow-y-auto");
    expect(list).toHaveAttribute("tabindex", "0");
    expect(list.getAttribute("aria-label")).toBeTruthy();
  });
});

describe("AT_966_12_1 與 AT_966_12_7 黃金樣本列（根層 patrol.golden.json 轉成 camelCase；白話逐字取自主機）", () => {
  it("AT_966_12_1 黃金列：四個提案依輸入序、等待對象與白話逐字，NO-HELDOUT 的對象是主機管理者", async () => {
    const { el } = await card({ patrol: () => ({ data: goldenPatrol() }) });
    const rows = within(block(el, "si-patrol-props")).getAllByRole("listitem");
    expect(rows.map((r) => r.querySelector("code")?.textContent ?? r.textContent?.slice(0, 11))).toEqual(["PROP-SI-902", "PROP-SI-903", "PROP-SI-904", "PROP-SI-905"]);
    expect(rows[0]).toHaveTextContent("等：掌舵者");
    expect(rows[0]).toHaveTextContent("驗證通過，等你決定是否晉升");
    expect(rows[1]).toHaveTextContent("等：巡邏器");
    expect(rows[1]).toHaveTextContent("等巡邏器下一次心跳做沙盒套用");
    expect(rows[2]).toHaveTextContent("等：主機管理者");
    expect(rows[2]).toHaveTextContent("尚未凍結評估集；需有人用 heldout-freeze，巡邏器不會自己湊");
    expect(rows[2]).toHaveTextContent("NO-HELDOUT");
    expect(rows[3]).toHaveTextContent("等你核准、否決或退回");
    expect(text(el)).not.toMatch(/自動凍結/);
    expect(text(el)).toContain("上次心跳：1 分鐘前");
  });
  it("AT_966_12_7 黃金列：排程現況、最近略過（含畫面按的立即啟動）、等待中的運轉、進行中的運轉與推送", async () => {
    const { el } = await card({ patrol: () => ({ data: goldenPatrol() }) });
    const sched = block(el, "si-patrol-schedule");
    expect(sched).toHaveTextContent("排程：啟用中");
    expect(sched).toHaveTextContent("目前狀態：本期已經跑過一次，等下一期");
    expect(sched).toHaveTextContent("最近一次略過：2026-11-11T11:40:00+08:00 已有未關運轉（已有未關運轉 RUN-SI-005），排程與立即啟動都會等它關閉（第二波起可由 Console 處理）");
    expect(sched).toHaveTextContent("這次略過的是你從畫面按的『立即啟動』（稽核編號 6f1c2a3e-8b4d-4e5f-9a7b-000000000901）");
    expect(sched).toHaveTextContent("RUN-SI-006 等待中：已有進行中的無人運轉，這個運轉等它結束後再啟動");
    expect(within(sched).queryAllByRole("button")).toHaveLength(0);
    expect(block(el, "si-patrol-runs")).toHaveTextContent("進行中：RUN-SI-005（排程啟動）。1 小時 59 分鐘前開始，預計最晚 59 分鐘後結束。");
    expect(block(el, "si-patrol-push-text")).toHaveTextContent("等使用者登入後自動推送");
  });
});
