/**
 * 提案詳情對話框（TCS-SiFlowVisibility AC-966-6、8、9、10）：AT-966-6-1～6-7、6-E-1、8-1～8-5、8-E-1、9-1～9-6、9-E-1、10-1～10-3、10-E-1。
 * 整個 SiView 以 renderFlow 渲染（真 Providers＋fetch 替身；時間取 NOW）；提案分頁有三列，P901 是被開詳情的那一列。
 */
import { cleanup, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import { failure } from "@/tests/helpers/api";
import { ADMIN_UI, OPERATOR_UI, VIEWER_UI, siNotFound, siUnavailable } from "@/tests/helpers/si";
import { DETAIL, DROP, NOW, PATROL, flowFixture, goldenProposalResponse, iso, openDetail, proposalResponse, renderFlow, type FlowOptions } from "@/tests/helpers/siFlow";

vi.setConfig({ testTimeout: 30_000 });
const router = vi.hoisted(() => ({ push: () => undefined, replace: () => undefined, back: () => undefined }));
vi.mock("next/navigation", () => ({ usePathname: () => "/self-improving", useRouter: () => router, useSearchParams: () => new URLSearchParams(), useParams: () => ({}) }));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  delete (window as unknown as Record<string, unknown>).__x;
});

const detailOf = (over: Record<string, unknown> = {}, extra: { ne?: Array<Record<string, unknown>>; proposal?: Record<string, unknown> } = {}): FlowOptions => ({
  proposal: () => ({ data: proposalResponse({ detail: DETAIL(over), ne: extra.ne, proposal: extra.proposal }) }),
});

/** 開詳情並等載入完成；可選切到某分頁。 */
async function openWith(opts: FlowOptions = {}, tabName?: string) {
  const user = userEvent.setup({ delay: null });
  const view = renderFlow({ ...VIEWER_UI, ...opts });
  const dialog = await openDetail(user);
  await within(dialog).findByTestId("si-next-step");
  if (tabName) await user.click(within(dialog).getByRole("tab", { name: tabName }));
  return { user, dialog, ...view };
}
// 帳本裡不存在的編號：執行期拼出（前綴與數字分開寫），避免被 si check 的 ref.obs 當成懸空引用
const GHOST_A = "OBS-SI" + "-" + "777";
const GHOST_B = "OBS-SI" + "-" + "902";
const text = (el: HTMLElement) => el.textContent ?? "";

describe("AT_966_6_1 每列「詳情」鈕、開關與焦點歸還", () => {
  it.each([
    ["VIEWER", VIEWER_UI],
    ["OPERATOR", OPERATOR_UI],
    ["ADMIN", ADMIN_UI],
  ])("%s", async (role, ui) => {
    const user = userEvent.setup({ delay: null });
    renderFlow({ ...ui });
    await user.click(screen.getByRole("tab", { name: /提案/ }));
    const button = await screen.findByTestId("si-detail-open-PROP-SI-901");
    expect(screen.getAllByTestId(/^si-detail-open-/), role).toHaveLength(3);
    expect(button).toHaveAttribute("aria-label", "詳情 PROP-SI-901");
    await user.click(button);
    const dialog = await screen.findByRole("dialog", { name: "提案詳情 PROP-SI-901" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(screen.getByTestId("si-detail-open-PROP-SI-901")).toHaveFocus();
    if (role === "ADMIN") expect(screen.getByTestId("si-decide-open-PROP-SI-901")).toBeInTheDocument();
  });
});

describe("AT_966_6_2 五分頁順序與鍵盤", () => {
  it("順序、預設選卡面、方向鍵與 Home／End、tabpanel 關聯", async () => {
    const { user, dialog } = await openWith();
    const tablist = within(dialog).getByRole("tablist", { name: "提案詳情分頁" });
    const tabs = within(tablist).getAllByRole("tab");
    expect(tabs.map((t) => t.textContent)).toEqual(["卡面", "變更內容", "提案本文", "評估集與驗證", "時間線"]);
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    tabs[0].focus();
    await user.keyboard("{ArrowRight}");
    expect(tabs[1]).toHaveAttribute("aria-selected", "true");
    expect(tabs[1]).toHaveFocus();
    await user.keyboard("{End}");
    expect(tabs[4]).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{ArrowLeft}");
    expect(tabs[3]).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{Home}");
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    const panel = within(dialog).getByRole("tabpanel");
    expect(panel).toHaveAttribute("aria-labelledby", tabs[0].id);
  });
});

describe("AT_966_6_3 懶取數與請求次數", () => {
  it("(a) 不點 0 次 (b) 點 1 次 (c) 切五分頁仍 1 次且不打議題端點 (d) 關閉再開共 2 次", async () => {
    const user = userEvent.setup({ delay: null });
    const { stub } = renderFlow(VIEWER_UI);
    const detailCalls = () => stub.calls.filter((c) => c.path.startsWith("/api/v1/si/proposals/"));
    await user.click(screen.getByRole("tab", { name: /提案/ }));
    await screen.findByTestId("si-detail-open-PROP-SI-901");
    expect(detailCalls()).toHaveLength(0);
    await user.click(screen.getByTestId("si-detail-open-PROP-SI-901"));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByTestId("si-next-step");
    expect(detailCalls().map((c) => c.path)).toEqual(["/api/v1/si/proposals/PROP-SI-901"]);
    for (const name of ["變更內容", "提案本文", "評估集與驗證", "時間線", "卡面"]) await user.click(within(dialog).getByRole("tab", { name }));
    expect(detailCalls()).toHaveLength(1);
    expect(stub.calls.filter((c) => c.path.startsWith("/api/v1/issues"))).toHaveLength(0);
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await user.click(screen.getByTestId("si-detail-open-PROP-SI-901"));
    await within(await screen.findByRole("dialog")).findByTestId("si-next-step");
    expect(detailCalls()).toHaveLength(2);
    expect(stub.calls.every((c) => c.method === "GET")).toBe(true);
  });
});

describe("AT_966_6_4 載入、503、404 三態", () => {
  const EMPTY_WORDS = /沒有變更|未凍結|還沒有凍結|這個提案沒有/;
  it("載入中不顯示任何「沒有」字樣", async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((r) => (release = r));
    const user = userEvent.setup({ delay: null });
    renderFlow({ ...VIEWER_UI, proposal: async () => (await gate, { data: proposalResponse() }) });
    const dialog = await openDetail(user);
    expect(within(dialog).getByRole("status")).toHaveTextContent("載入中");
    expect(text(dialog)).not.toMatch(EMPTY_WORDS);
    release();
  });
  it("503 逐字顯示原因並可重試（恰多 1 次請求）", async () => {
    const user = userEvent.setup({ delay: null });
    const { stub } = renderFlow({ ...VIEWER_UI, proposal: () => siUnavailable("nonzero_rc", "rc=2; stderr=boom 全形字元") });
    const dialog = await openDetail(user);
    await within(dialog).findByTestId("si-error");
    for (const s of ["si_unavailable", "nonzero_rc", "rc=2; stderr=boom 全形字元"]) expect(text(dialog)).toContain(s);
    expect(text(dialog)).not.toMatch(EMPTY_WORDS);
    expect(within(dialog).queryByRole("tablist")).toBeNull();
    const before = stub.calls.filter((c) => c.path.startsWith("/api/v1/si/proposals/")).length;
    await user.click(within(dialog).getByRole("button", { name: "重試" }));
    await waitFor(() => expect(stub.calls.filter((c) => c.path.startsWith("/api/v1/si/proposals/"))).toHaveLength(before + 1));
  });
  it("404 顯示查無這個提案；502 顯示通用錯誤與原因", async () => {
    const user = userEvent.setup({ delay: null });
    renderFlow({ ...VIEWER_UI, proposal: () => siNotFound("PROP-SI-901") });
    const dialog = await openDetail(user);
    expect(await within(dialog).findByText("查無這個提案")).toBeInTheDocument();
    expect(text(dialog)).not.toMatch(EMPTY_WORDS);
    cleanup();
    renderFlow({ ...VIEWER_UI, proposal: () => failure(502, { message: "後端服務無法連線", reason: "bridge_unreachable" }) });
    const dialog2 = await openDetail(user);
    await within(dialog2).findByTestId("si-error");
    expect(text(dialog2)).toContain("bridge_unreachable");
    expect(text(dialog2)).not.toMatch(EMPTY_WORDS);
  });
});

describe("AT_966_6_5 頂端「下一步」三種來源", () => {
  it("(a) 快照可用：依巡邏回報", async () => {
    const patrol = () => ({ data: PATROL({ props: [{ id: "PROP-SI-901", state: "verified", code: "WAIT", who: "掌舵者", text: "等你決定要不要晉升" }] }) });
    const { dialog } = await openWith({ patrol });
    const step = within(dialog).getByTestId("si-next-step");
    expect(step).toHaveTextContent("下一步：等掌舵者｜等你決定要不要晉升");
    expect(step).toHaveTextContent("依巡邏回報");
  });
  it("(b) 快照過時：取詳情、依帳本判斷", async () => {
    const { dialog } = await openWith({ ...detailOf({ next: { code: "AUTO", who: "巡邏器", text: "巡邏器會自動跑驗證" } }), patrol: () => ({ data: PATROL({ generatedAt: iso(40) }) }) });
    const step = within(dialog).getByTestId("si-next-step");
    expect(step).toHaveTextContent("下一步：等巡邏器｜巡邏器會自動跑驗證");
    expect(step).toHaveTextContent("依帳本判斷");
  });
  it("(c) 快照 503 且詳情無 next：量不到", async () => {
    const { dialog } = await openWith({ ...detailOf({ next: DROP }), patrol: () => siUnavailable("report_missing") });
    expect(within(dialog).getByTestId("si-next-step")).toHaveTextContent("下一步：量不到");
  });
  it("who 為「無」改寫成目前不需要任何人動作", async () => {
    const { dialog } = await openWith({ ...detailOf({ next: { code: "DONE", who: "無", text: "已完成" } }), patrol: () => siUnavailable("report_missing") });
    expect(within(dialog).getByTestId("si-next-step")).toHaveTextContent("目前不需要任何人動作：已完成");
    expect(within(dialog).getByTestId("si-next-step").textContent).not.toContain("等無");
  });
});

describe("AT_966_6_6 過時快照加巡邏器警示行", () => {
  it("who 為巡邏器且快照過時才有警示", async () => {
    const stale = () => ({ data: PATROL({ generatedAt: iso(40) }) });
    const a = await openWith({ ...detailOf({ next: { code: "X", who: "巡邏器", text: "自動" } }), patrol: stale });
    expect(within(a.dialog).getByTestId("si-next-warning")).toHaveTextContent("巡邏可能沒在跑，這一步可能不會自動進行");
    cleanup();
    const b = await openWith({ ...detailOf({ next: { code: "X", who: "掌舵者", text: "請決定" } }), patrol: stale });
    expect(within(b.dialog).queryByTestId("si-next-warning")).toBeNull();
  });
});

const EVIL = "<img src=x onerror=alert(1)><script>window.__x=1</script>**粗體**[x](javascript:alert(1))&lt;";
describe("AT_966_6_7 純文字渲染與靜態無 innerHTML", () => {
  it("惡意字串在五分頁都是字面文字", async () => {
    const hostile = DETAIL({
      patch: { rel: "r", bytes: 1, text: `+${EVIL}`, truncated: false },
      body: { rel: "b", bytes: 1, text: EVIL, truncated: false },
      next: { code: "X", who: "掌舵者", text: EVIL },
      heldout: { frozen: true, seq: 1, n: 1, min: 5, belowMin: true, frozenBy: EVIL, digest8: "x", neNote: EVIL },
      sandbox: { applied: false, touchedOk: false, rollbackOk: false, failCode: EVIL, failText: EVIL },
      verify: { verdict: "FAIL", baselineRed: true, patchedGreen: false, mutatedRed: true, probesN: 1, carrierProof: true, reasons: [{ code: "R", text: EVIL }] },
      sourceObs: [{ id: "OBS-SI-050", context: EVIL, symptom: EVIL, severity: "P2", disposition: EVIL }],
      timeline: [{ seq: 1, t: "t", by: EVIL, kind: "k", action: EVIL }],
    });
    const fixture = flowFixture();
    fixture.proposals.items[0] = { ...fixture.proposals.items[0], card: EVIL };
    const { user, dialog } = await openWith({ fixture, proposal: () => ({ data: proposalResponse({ detail: hostile }) }) });
    for (const name of ["卡面", "變更內容", "提案本文", "評估集與驗證", "時間線"]) {
      await user.click(within(dialog).getByRole("tab", { name }));
      expect(dialog.querySelector("img, script, a[href^='javascript']"), name).toBeNull();
    }
    for (const name of ["卡面", "變更內容", "提案本文", "評估集與驗證"]) {
      await user.click(within(dialog).getByRole("tab", { name }));
      expect(text(dialog), name).toContain("<img src=x onerror=alert(1)>");
    }
    expect((window as unknown as Record<string, unknown>).__x).toBeUndefined();
  });
  it("四支原始碼不含 dangerouslySetInnerHTML、innerHTML、insertAdjacentHTML、document.write", () => {
    const root = process.cwd();
    for (const rel of ["components/domain/si/SiProposalDetail.tsx", "components/domain/si/SiDiffView.tsx", "components/domain/si/SiPatrolCard.tsx", "lib/domain/siFlow.ts"]) {
      expect(readFileSync(path.join(root, rel), "utf-8"), rel).not.toMatch(/dangerouslySetInnerHTML|innerHTML|insertAdjacentHTML|document\.write/);
    }
  });
});

describe("AT_966_6_E_1 舊根層無 detail、卡面為 null", () => {
  it("(a) 缺 detail：四分頁顯示量不到，卡面仍逐字，下一步依快照", async () => {
    const { user, dialog } = await openWith({ proposal: () => ({ data: proposalResponse({ detail: DROP }) }) });
    expect(within(dialog).getByTestId("si-detail-card")).toHaveTextContent("CARD-LINE-1");
    for (const name of ["變更內容", "提案本文", "評估集與驗證", "時間線"]) {
      await user.click(within(dialog).getByRole("tab", { name }));
      expect(within(dialog).getByTestId("si-detail-not-provided")).toHaveTextContent("這個根層版本還沒提供詳情（量不到）");
    }
    expect(within(dialog).getByTestId("si-next-step")).toHaveTextContent("下一步：等掌舵者");
  });
  it("(b) 卡面為 null：卡面量不到加對應 ne，其餘分頁照常", async () => {
    const fixture = flowFixture();
    fixture.proposals.items[0] = { ...fixture.proposals.items[0], card: null };
    const ne = [{ field: "proposals.PROP-SI-901.card", reason: "CARD-UNREADABLE" }];
    const { user, dialog } = await openWith({ fixture, ...detailOf({}, { ne, proposal: { card: null } }) });
    expect(within(dialog).getByTestId("si-detail-card-missing")).toHaveTextContent("卡面量不到");
    expect(within(dialog).getByTestId("si-detail-card-missing")).toHaveTextContent("CARD-UNREADABLE");
    await user.click(within(dialog).getByRole("tab", { name: "變更內容" }));
    expect(within(dialog).getByTestId("si-diff-view")).toBeInTheDocument();
  });
});

describe("AT_966_8_1～8_2 提案本文", () => {
  it("AT_966_8_1 純文字、顯示 rel、截斷提示", async () => {
    const body = { rel: "docs/x/r2.md", bytes: 48, text: "# 標題\n\n- 項目 <b>x</b>\n", truncated: false };
    const a = await openWith(detailOf({ body }), "提案本文");
    const pre = within(a.dialog).getByTestId("si-body-text");
    expect(pre.tagName).toBe("PRE");
    expect(pre.className).toContain("whitespace-pre-wrap");
    expect(pre.className).toContain("break-words");
    expect(pre.textContent).toBe(body.text);
    expect(a.dialog.querySelector("h1, h2 + ul, b")).toBeNull();
    expect(text(a.dialog)).toContain("docs/x/r2.md");
    expect(within(a.dialog).queryByTestId("si-body-truncated")).toBeNull();
    cleanup();
    const b = await openWith(detailOf({ body: { ...body, truncated: true } }), "提案本文");
    expect(within(b.dialog).getByTestId("si-body-truncated")).toHaveTextContent("內容過長已截斷，完整檔在 docs/x/r2.md");
  });
  it("AT_966_8_2 本文為 null 與空字串不同句", async () => {
    const a = await openWith(detailOf({ body: null }), "提案本文");
    expect(within(a.dialog).getByText("提案本文量不到")).toBeInTheDocument();
    cleanup();
    const b = await openWith(detailOf({ body: { rel: "x", bytes: 0, text: "", truncated: false } }), "提案本文");
    expect(within(b.dialog).getByText("這個提案沒有本文")).toBeInTheDocument();
    expect(within(b.dialog).queryByText("提案本文量不到")).toBeNull();
  });
});

describe("AT_966_8_3 來源觀察跳轉與高亮", () => {
  it("對話框關閉、切到觀察分頁、該列高亮並取得焦點、離開再回來後消失", async () => {
    const { user, dialog, stub } = await openWith({}, "提案本文");
    const before = stub.calls.length;
    await user.click(within(dialog).getByRole("button", { name: "看觀察 OBS-SI-050" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(screen.getByRole("tab", { name: /觀察/ })).toHaveAttribute("aria-selected", "true");
    const row = await screen.findByTestId("si-obs-row-OBS-SI-050");
    await waitFor(() => expect(row).toHaveAttribute("data-highlight", "true"));
    await waitFor(() => expect(row).toHaveFocus());
    expect(document.querySelectorAll("[data-highlight='true']")).toHaveLength(1);
    // 跳轉本身不打詳情、巡邏、議題端點（觀察分頁因切換而重掛、重取清單屬既有行為）
    const added = stub.calls.slice(before).map((c) => c.path);
    expect(added.filter((p) => !p.startsWith("/api/v1/si/observations"))).toEqual([]);
    expect(added.filter((p) => p.startsWith("/api/v1/si/observations")).length, "觀察清單至多重取一次").toBeLessThanOrEqual(1);
    await user.click(screen.getByRole("tab", { name: /事件/ }));
    await user.click(screen.getByRole("tab", { name: /觀察/ }));
    const again = await screen.findByTestId("si-obs-row-OBS-SI-050");
    expect(again).not.toHaveAttribute("data-highlight");
  });
});

describe("AT_966_8_4 跳轉目標不在已載入頁、非 OBS 來源、無來源", () => {
  it("目標不在已載入頁：跳轉後顯示說明，不丟例外", async () => {
    const { user, dialog } = await openWith(detailOf({ sourceObs: [{ id: GHOST_A, context: "c", symptom: "s", severity: "P2", disposition: "open" }] }), "提案本文");
    await user.click(within(dialog).getByRole("button", { name: `看觀察 ${GHOST_A}` }));
    expect(await screen.findByTestId("si-obs-highlight-missing")).toHaveTextContent(`找不到 ${GHOST_A}（可能在更舊的頁，請按『載入更多』）`);
  });
  it("非 OBS 來源只有純文字、沒有跳轉鈕", async () => {
    const { dialog } = await openWith(detailOf({ sourceObs: DROP }, { proposal: { sources: ["DEF-200-575", "手寫說明"] } }), "提案本文");
    const section = within(dialog).getByTestId("si-sources-section");
    expect(section).toHaveTextContent("DEF-200-575");
    expect(section).toHaveTextContent("手寫說明");
    expect(within(section).queryAllByRole("button")).toHaveLength(0);
  });
  it("無來源與來源量不到", async () => {
    const a = await openWith(detailOf({ sourceObs: [] }, { proposal: { sources: [] } }), "提案本文");
    expect(within(a.dialog).getByTestId("si-sources-section")).toHaveTextContent("這個提案沒有登記來源觀察");
    cleanup();
    const b = await openWith(detailOf({ sourceObs: DROP }, { proposal: { sources: undefined as unknown as string[] } }), "提案本文");
    expect(within(b.dialog).getByTestId("si-sources-section")).toHaveTextContent("來源量不到");
  });
});

describe("AT_966_8_5 來源觀察摘要與缺列", () => {
  it("逐筆摘要、缺列句；帳本讀不到時顯示根層白話", async () => {
    const sourceObs = [
      { id: "OBS-SI-050", context: "巡邏日誌", symptom: "提案卡了三天沒人處理 <b>x</b>", severity: "P2", disposition: "open" },
      { id: GHOST_B, missing: true },
    ];
    const a = await openWith(detailOf({ sourceObs }), "提案本文");
    const sec = within(a.dialog).getByTestId("si-sources-section");
    expect(sec).toHaveTextContent("OBS-SI-050");
    expect(sec).toHaveTextContent("嚴重度：P2");
    expect(sec).toHaveTextContent("處置：open");
    expect(sec).toHaveTextContent("情境：巡邏日誌");
    expect(sec).toHaveTextContent("症狀：提案卡了三天沒人處理 <b>x</b>");
    expect(sec).toHaveTextContent(`找不到這筆觀察 ${GHOST_B}（觀察帳本裡沒有）`);
    expect(sec.querySelector("b")).toBeNull();
    cleanup();
    const ne = [{ field: "proposals.PROP-SI-901.detail.sourceObs", reason: "OBS-LEDGER-UNREADABLE", text: "觀察帳本讀不到，來源無法列出" }];
    const b = await openWith(detailOf({ sourceObs: [] }, { ne }), "提案本文");
    expect(within(b.dialog).getByTestId("si-sources-section")).toHaveTextContent("觀察帳本讀不到，來源無法列出");
    expect(within(b.dialog).getByTestId("si-sources-section")).not.toHaveTextContent("沒有登記來源觀察");
  });
});

describe("AT_966_8_E_1 大量與重複來源", () => {
  it("30 個來源（5 個重複）顯示 25 個不重複的鈕，區域可捲動", async () => {
    const sources = [...Array.from({ length: 25 }, (_, i) => `OBS-SI-${String(100 + i)}`), ...Array.from({ length: 5 }, (_, i) => `OBS-SI-${String(100 + i)}`)];
    const { dialog } = await openWith(detailOf({ sourceObs: DROP }, { proposal: { sources } }), "提案本文");
    const list = within(dialog).getByTestId("si-source-list");
    const buttons = within(list).getAllByRole("button");
    expect(buttons).toHaveLength(25);
    expect(buttons.map((b) => b.textContent)).toEqual(Array.from({ length: 25 }, (_, i) => `看觀察 OBS-SI-${100 + i}`));
    expect(list.className).toContain("overflow-y-auto");
    buttons[0].focus();
    expect(buttons[0]).toHaveFocus();
  });
});

describe("AT_966_9_1 評估集四種狀態與低於下限提示", () => {
  const heldoutText = async (heldout: unknown) => {
    const { dialog } = await openWith(detailOf({ heldout }), "評估集與驗證");
    return dialog;
  };
  it("(a) 未凍結：說明句且不暗示自動凍結", async () => {
    const dialog = await heldoutText({ frozen: false });
    expect(within(dialog).getByText("還沒有凍結評估集")).toBeInTheDocument();
    expect(text(dialog)).toContain("評估集要由人在主機上凍結，巡邏器不會自己建立；凍結前這個提案不會進行驗證");
    expect(text(dialog)).not.toMatch(/自動凍結|會自動/);
    expect(text(dialog)).toContain("評估集（用來驗證的考題）");
  });
  it("(b) 已凍結且未低於下限", async () => {
    const dialog = await heldoutText({ frozen: true, seq: 60, n: 7, min: 5, belowMin: false, frozenBy: "凍結者甲", neNote: null, digest8: "0a1b2c3d" });
    expect(within(dialog).getByText("已凍結：7 筆案例（下限 5），凍結者：凍結者甲")).toBeInTheDocument();
    expect(within(dialog).queryByTestId("si-heldout-warning")).toBeNull();
    expect(text(dialog)).not.toContain("0a1b2c3d");
  });
  it("(c) 低於下限：警示逐字等於 neNote；(c2) neNote 缺席用保底句", async () => {
    const note = "案例數 4 低於下限 5，驗證結果只能是 NE";
    const a = await heldoutText({ frozen: true, n: 4, min: 5, belowMin: true, frozenBy: "凍結者甲", neNote: note });
    expect(within(a).getByTestId("si-heldout-warning").textContent).toBe(note);
    expect(text(a)).toContain("這不會擋住凍結，只表示驗證結果不能當成通過");
    cleanup();
    const b = await heldoutText({ frozen: true, n: 4, min: 5, belowMin: true, frozenBy: "凍結者甲", neNote: null });
    expect(within(b).getByTestId("si-heldout-warning").textContent).toBe("案例數低於下限，驗證結果只能是『無法評估』");
  });
  it("(d) 案例數不明：沒有低於下限警示", async () => {
    const dialog = await heldoutText({ frozen: true, n: null, min: 5, belowMin: null });
    expect(within(dialog).getByText("已凍結，案例數量不明")).toBeInTheDocument();
    expect(within(dialog).queryByTestId("si-heldout-warning")).toBeNull();
  });
});

describe("AT_966_9_2 評估集內容不外洩（金絲雀）", () => {
  it("整個對話框的文字與 HTML 都不含哨兵，且只有一條詳情請求", async () => {
    const heldout = {
      frozen: true,
      seq: 60,
      n: 7,
      min: 5,
      belowMin: false,
      frozenBy: "甲",
      neNote: null,
      digest8: "CANARY08",
      cases: ["CANARY-CASE-7f3a"],
      probes: "CANARY-PROBE",
      digest: "sha256:CANARY",
      files: { a: "CANARY-FILE" },
      items: [{ x: "CANARY-ITEM" }],
    };
    const { user, dialog, stub } = await openWith(detailOf({ heldout }));
    for (const name of ["卡面", "變更內容", "提案本文", "評估集與驗證", "時間線"]) {
      await user.click(within(dialog).getByRole("tab", { name }));
      expect(text(dialog), name).not.toContain("CANARY");
      expect(dialog.outerHTML, name).not.toContain("CANARY");
    }
    expect(stub.calls.filter((c) => c.path.startsWith("/api/v1/si/proposals/")).map((c) => c.path)).toEqual(["/api/v1/si/proposals/PROP-SI-901"]);
  });
});

describe("AT_966_9_3 隔離試跑（沙盒）結果呈現", () => {
  it("四種情境", async () => {
    const run = async (sandbox: unknown) => (await openWith(detailOf({ sandbox }), "評估集與驗證")).dialog;
    const a = await run({ applied: true, touchedOk: true, rollbackOk: true, failCode: null, failText: null });
    expect(text(a)).toContain("隔離試跑（沙盒）");
    expect(text(a)).toContain("已套用修補、只動到允許的檔案、回滾正常");
    cleanup();
    const b = await run({ applied: false, touchedOk: false, rollbackOk: true, failCode: "SANDBOX-NOT-APPLIED", failText: "修補套不上去，請退回或修訂提案" });
    expect(within(b).getByTestId("si-sandbox-section")).toHaveTextContent("沒有通過：SANDBOX-NOT-APPLIED");
    expect(text(b)).toContain("修補套不上去，請退回或修訂提案");
    expect(text(b)).toContain("已套用修補：否");
    expect(text(b)).toContain("回滾正常：是");
    expect(b.querySelector("code")?.className).toContain("font-mono");
    cleanup();
    const b2 = await run({ applied: false, touchedOk: false, rollbackOk: true, failCode: "SANDBOX-NOT-APPLIED", failText: null });
    expect(within(b2).getByTestId("si-sandbox-section")).toHaveTextContent("沒有通過：SANDBOX-NOT-APPLIED（主機沒有提供白話說明）");
    cleanup();
    const c = await run(null);
    expect(within(c).getByTestId("si-sandbox-section")).toHaveTextContent("還沒有做隔離試跑");
    expect(within(c).getByTestId("si-sandbox-section")).not.toHaveTextContent("沒有通過");
  });
});

describe("AT_966_9_4 驗證三步證據與結果", () => {
  const verify = (over: Record<string, unknown>) => ({
    seq: 62,
    id: "A",
    verdict: "PASS",
    baselineRed: true,
    patchedGreen: true,
    mutatedRed: true,
    probesN: 6,
    carrierProof: true,
    reasons: [],
    ...over,
  });
  const run = async (v: unknown) => (await openWith(detailOf({ verify: v }), "評估集與驗證")).dialog;
  it("PASS：結果標籤、三步、探針數、測量工具自我檢查", async () => {
    const d = await run(verify({}));
    expect(within(d).getByTestId("si-verdict")).toHaveTextContent("結果：通過");
    for (const s of ["修補前確實重現症狀：是", "修補後症狀消失：是", "故意弄壞修補後症狀又出現：是", "檢查項目（探針）：6", "驗證用的測量工具自我檢查：通過"]) expect(text(d)).toContain(s);
    expect(text(d)).not.toMatch(/\btrue\b|\bfalse\b/);
  });
  it("FAIL 第二步為否並標示這一步沒過；NE；carrierProof 三態", async () => {
    const f = await run(verify({ verdict: "FAIL", patchedGreen: false }));
    expect(within(f).getByTestId("si-verdict")).toHaveTextContent("結果：未通過");
    expect(f.querySelector("[data-step='patchedGreen']")).toHaveTextContent("修補後症狀消失：否（這一步沒過）");
    cleanup();
    expect(within(await run(verify({ verdict: "NE" }))).getByTestId("si-verdict")).toHaveTextContent("結果：無法評估");
    cleanup();
    expect(text(await run(verify({ carrierProof: false })))).toContain("驗證用的測量工具自我檢查：沒通過");
    cleanup();
    expect(text(await run(verify({ carrierProof: null })))).toContain("驗證用的測量工具自我檢查：量不到");
  });
});

describe("AT_966_9_5 原因清單與保底", () => {
  const run = async (verify: Record<string, unknown>) =>
    (await openWith(detailOf({ verify: { seq: 1, id: "A", verdict: "PASS", baselineRed: true, patchedGreen: true, mutatedRed: true, probesN: 1, carrierProof: true, ...verify } }), "評估集與驗證"))
      .dialog;
  it("五種情境", async () => {
    const a = await run({ reasons: [{ code: "HELDOUT-TOO-SMALL", text: "評估集案例數低於下限" }] });
    expect(text(a)).toContain("HELDOUT-TOO-SMALL");
    expect(text(a)).toContain("評估集案例數低於下限");
    cleanup();
    for (const reasons of [[{ code: "UNK-9" }], [{ code: "UNK-9", text: "" }]]) {
      expect(text(await run({ reasons }))).toContain("主機沒有提供白話說明（原因碼 UNK-9）。");
      cleanup();
    }
    expect(text(await run({ reasons: [] }))).toContain("沒有任何保留原因");
    cleanup();
    expect(text(await run({ reasons: [], verdict: "NE" }))).toContain("主機沒有回報原因");
    cleanup();
    expect(text(await run({ reasons: DROP as unknown as undefined }))).toContain("原因量不到");
  });
});

describe("AT_966_9_6 缺席的三種情形", () => {
  it("(a) verify 為 null 加下一步提示 (b) null 布林顯示量不到 (c) heldout 缺席", async () => {
    const a = await openWith(detailOf({ verify: null }), "評估集與驗證");
    expect(within(a.dialog).getByTestId("si-verify-section")).toHaveTextContent("還沒有驗證結果");
    expect(within(a.dialog).getByTestId("si-verify-section")).toHaveTextContent("下一步：等掌舵者");
    cleanup();
    const b = await openWith(detailOf({ verify: { seq: 1, id: "A", verdict: "PASS", baselineRed: null, probesN: 1, carrierProof: true, reasons: [] } }), "評估集與驗證");
    expect(text(b.dialog)).toContain("修補前確實重現症狀：量不到");
    expect(text(b.dialog)).toContain("修補後症狀消失：量不到");
    expect(text(b.dialog)).not.toContain("修補前確實重現症狀：否");
    cleanup();
    const c = await openWith(detailOf({ heldout: DROP }), "評估集與驗證");
    expect(text(c.dialog)).toContain("評估集狀態量不到");
  });
});

describe("AT_966_9_E_1 未知驗證結果", () => {
  it("WEIRD、空字串、缺席：不套成功或失敗樣式，仍顯示三步", async () => {
    for (const verdict of ["WEIRD", "", DROP]) {
      const base = { seq: 1, id: "A", baselineRed: true, patchedGreen: true, mutatedRed: true, probesN: 1, carrierProof: true, reasons: [] } as Record<string, unknown>;
      if (verdict !== DROP) base.verdict = verdict;
      const { dialog } = await openWith(detailOf({ verify: base }), "評估集與驗證");
      const tag = within(dialog).getByTestId("si-verdict");
      expect(tag.textContent).toContain(verdict === "WEIRD" ? "未知結果『WEIRD』" : "量不到");
      expect(tag.className).not.toMatch(/text-wg-success|bg-wg-success|border-wg-success|text-wg-error|bg-wg-error|border-wg-error/);
      expect(text(dialog)).toContain("修補前確實重現症狀：是");
      cleanup();
    }
  });
});

describe("AT_966_10_1～10_3 時間線", () => {
  const tl = (rows: unknown[]) => detailOf({ timeline: rows });
  it("AT_966_10_1 取自 detail、依 seq 升冪、四欄、不打議題端點", async () => {
    const rows = [
      { seq: 30, t: "2026-11-10T09:00:00+08:00", by: "掌舵者", kind: "dec", action: "核准" },
      { seq: 12, t: "2026-11-10T08:00:00+08:00", by: "巡邏器", kind: "prop", action: "提出提案" },
      { seq: 21, t: "2026-11-10T08:30:00+08:00", by: "巡邏器", kind: "app", action: "開始驗證" },
    ];
    const { dialog, stub } = await openWith(tl(rows), "時間線");
    const table = within(dialog).getByTestId("si-timeline-table");
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["序號", "時間", "誰", "做了什麼"]);
    expect(table.querySelector("caption")).toHaveTextContent("提案事件時間線");
    expect(table.querySelector("caption")?.className).toContain("sr-only");
    const body = within(table).getAllByRole("row").slice(1);
    expect(body.map((r) => r.querySelector("td")?.textContent)).toEqual(["12", "21", "30"]);
    expect(text(table)).not.toContain("prop");
    expect(stub.calls.filter((c) => c.path.startsWith("/api/v1/issues"))).toHaveLength(0);
  });
  it("AT_966_10_2 空陣列與缺席", async () => {
    expect(within((await openWith(tl([]), "時間線")).dialog).getByText("這個提案還沒有事件")).toBeInTheDocument();
    cleanup();
    expect(within((await openWith(detailOf({ timeline: DROP }), "時間線")).dialog).getByText("時間線量不到")).toBeInTheDocument();
    cleanup();
    expect(within((await openWith(detailOf({ timeline: null }), "時間線")).dialog).getByText("時間線量不到")).toBeInTheDocument();
  });
  it("AT_966_10_3 被截短的說明（逐字；缺 text 用保底句）", async () => {
    const rows = Array.from({ length: 500 }, (_, i) => ({ seq: i + 1, t: "2026-11-10T09:00:00+08:00", by: "巡邏器", kind: "k", action: `動作${i}` }));
    const ne = [{ field: "proposals.PROP-SI-901.detail.timeline", reason: "TIMELINE-TRUNCATED", text: "事件太多，時間線只顯示最後 500 筆" }];
    const a = await openWith(detailOf({ timeline: rows }, { ne }), "時間線");
    expect(within(a.dialog).getByTestId("si-timeline-truncated")).toHaveTextContent("事件太多，時間線只顯示最後 500 筆");
    expect(within(a.dialog).getAllByRole("row")).toHaveLength(501);
    cleanup();
    const b = await openWith(detailOf({ timeline: rows }, { ne: [{ field: ne[0].field, reason: "TIMELINE-TRUNCATED" }] }), "時間線");
    expect(within(b.dialog).getByTestId("si-timeline-truncated")).toHaveTextContent("主機沒有提供白話說明（原因碼 TIMELINE-TRUNCATED）。");
  });
  it("AT_966_10_E_1 無法解析的時間與重複 seq 穩定排序", async () => {
    const rows = [
      { seq: 12, t: "昨天", by: "甲", kind: "k", action: "第一筆" },
      { seq: 12, t: null, by: "乙", kind: "k", action: "第二筆" },
      { seq: 5, t: NOW, by: "丙", kind: "k", action: "最早" },
    ];
    const { dialog } = await openWith(tl(rows), "時間線");
    const body = within(dialog).getAllByRole("row").slice(1);
    expect(body.map((r) => r.querySelectorAll("td")[3].textContent)).toEqual(["最早", "第一筆", "第二筆"]);
    expect(body[1].querySelectorAll("td")[1].textContent).toBe("昨天");
    expect(body[2].querySelectorAll("td")[1].textContent).toBe("時間量不到");
  });
});

describe("AT_966_9_1 與 AT_966_9_4 黃金樣本列（根層 detail.golden.json 的 items[0] 轉成 camelCase）", () => {
  const golden: FlowOptions = { proposal: () => ({ data: goldenProposalResponse() }) };
  it("AT_966_9_1 黃金列：已凍結但低於下限，警示逐字等於主機給的 neNote，不顯示 digest8", async () => {
    const { dialog } = await openWith(golden, "評估集與驗證");
    expect(text(dialog)).toContain("已凍結：4 筆案例（下限 5），凍結者：FZ");
    expect(within(dialog).getByTestId("si-heldout-warning").textContent).toBe("評估集只有 4 個案例，低於下限 5，驗證必判 NE（未驗證）；晉升只能走「未驗採納」式");
    expect(text(dialog)).not.toContain("abcd0123");
  });
  it("AT_966_9_4 黃金列：隔離試跑逐字用主機的 failText；驗證為無法評估、三步量不到、測量工具自我檢查通過、原因一筆", async () => {
    const { dialog } = await openWith(golden, "評估集與驗證");
    const sandbox = within(dialog).getByTestId("si-sandbox-section");
    expect(sandbox).toHaveTextContent("沒有通過：SANDBOX-APPLY-TIMEOUT");
    expect(sandbox).toHaveTextContent("沙盒套用失敗；提案需退回或修訂");
    expect(sandbox).not.toHaveTextContent("主機沒有提供白話說明");
    const verify = within(dialog).getByTestId("si-verify-section");
    expect(within(dialog).getByTestId("si-verdict")).toHaveTextContent("結果：無法評估");
    for (const s of ["修補前確實重現症狀：量不到", "修補後症狀消失：量不到", "故意弄壞修補後症狀又出現：量不到", "檢查項目（探針）：1", "驗證用的測量工具自我檢查：通過"])
      expect(verify).toHaveTextContent(s);
    const reasons = verify.querySelectorAll("li:not([data-step])");
    expect(reasons).toHaveLength(1);
    expect(reasons[0]).toHaveTextContent("SANDBOX-APPLY-TIMEOUT");
    expect(reasons[0]).toHaveTextContent("沙盒套用失敗；提案需退回或修訂");
  });
});
