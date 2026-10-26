/**
 * 自我進化頁「狀態快篩」的元件測試（觀察分頁：全部／未結／延後／已完成；提案分頁：全部／待決／進行中／已完成）。
 * 為什麼重要：掌舵者要一鍵看「已完成」與「未結」，不必懂處置與提案狀態的細枚舉；但清單是游標分頁、篩選只作用於已載入的頁——
 * 若快篩只篩第一頁，「已完成」會被讀成「帳本裡就只有這些」。所以這裡釘四件事：歸類與篩選結果對（含壞列與未登記狀態永遠顯示的反例）、
 * 快篩開著時其餘頁自動載完（一次一頁、關掉就停、失敗就停、有頁數上限）、載不完時老實說「結果不完整」、旁邊的「符合 N／已載入 M」不把照常顯示的列算成符合。
 * 資料來自 tests/helpers/si.tsx 的 fetch 替身（狀態 A 的黃金檔，since／limit 語意同 CLI）；SI_PAGE_LIMIT 以 5 或 1 切頁，同 SiView.test.tsx 的作法。
 */
import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SiObservation, SiObservationRow, SiProposal } from "@/lib/api/types";
import { SI_AUTO_LOAD_MAX_PAGES } from "@/lib/domain/si";
import { GA, clone, renderSi, siUnavailable, type SiCall, type SiFixture } from "@/tests/helpers/si";

// SI_PAGE_LIMIT 可由測試局部覆寫（以 5 或 1 切頁）；其餘測試維持正式值，以 getter 在每次讀取時回傳
const limits = vi.hoisted(() => ({ value: 100 }));
vi.mock("@/lib/domain/si", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/domain/si")>();
  return {
    ...mod,
    get SI_PAGE_LIMIT() {
      return limits.value;
    },
  };
});
// 測試環境沒有 App Router：AuthProvider 要的 useRouter 換成穩定的替身（SiView 本身不導覽）
const router = vi.hoisted(() => ({ push: () => undefined, replace: () => undefined, back: () => undefined }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/self-improving",
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));
// 「載到頁數上限」的案例要循序打 20 個請求，整套平行跑時比單檔慢：給寬一點的逾時，不靠重試掩蓋真的卡住
vi.setConfig({ testTimeout: 30_000 });
afterEach(() => {
  limits.value = 100;
});

// ── 小工具 ────────────────────────────────────────────────────────────────

const isValid = (r: SiObservationRow): r is SiObservation => r.valid !== false;
const GOLDEN_OBS = GA.observations.items.filter(isValid);
const BAD = GA.observations.items.find((r) => !isValid(r)) as { line: number; raw: string; valid: false };

const panel = (tab: "observations" | "proposals") => screen.getByTestId(`si-panel-${tab}`);
const pill = (tab: "observations" | "proposals", value: string) => screen.getByTestId(`si-status-${tab}-${value}`);
const count = (tab: "observations" | "proposals") => screen.getByTestId(`si-status-count-${tab}`).textContent;
const pressedPills = (tab: "observations" | "proposals") =>
  Array.from(within(screen.getByTestId(`si-status-filter-${tab}`)).getAllByRole("button"))
    .filter((b) => b.getAttribute("aria-pressed") === "true")
    .map((b) => b.textContent);

/** 面板內依文件順序列出的觀察有效列 ID（壞列另算）。 */
const obsRowIds = (root: HTMLElement) => Array.from(root.querySelectorAll<HTMLElement>('[data-testid^="si-obs-row-"]')).map((el) => (el.dataset.testid as string).replace("si-obs-row-", ""));
const badRows = (root: HTMLElement) => root.querySelectorAll('[data-testid^="si-obs-invalid-"]');
const propRowIds = (root: HTMLElement) => Array.from(root.querySelectorAll<HTMLElement>('[data-testid^="si-prop-row-"]')).map((el) => (el.dataset.testid as string).replace("si-prop-row-", ""));
const obsRequests = (urls: string[]) => urls.filter((u) => u.includes("/api/v1/si/observations"));
const propRequests = (urls: string[]) => urls.filter((u) => u.includes("/api/v1/si/proposals"));

/** 讓出事件迴圈一小段時間：否定式斷言（「之後沒有再發請求」）要給可能的多餘請求一個發生的機會。 */
const settle = () =>
  act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 100));
  });

/** 黃金檔 A 的有效觀察列依處置分三類（獨立於被測函式，直接看處置文字）；各類筆數是防反空轉。 */
const OPEN_IDS = GOLDEN_OBS.filter((o) => o.disposition === "open").map((o) => o.id);
const DEFERRED_IDS = GOLDEN_OBS.filter((o) => o.disposition.startsWith("deferred")).map((o) => o.id);
const DONE_IDS = GOLDEN_OBS.filter((o) => o.disposition !== "open" && !o.disposition.startsWith("deferred")).map((o) => o.id);

/** 提案夾具：七筆各一個狀態（最後一筆的狀態不在已登記的表內）；id 的數字尾即游標。 */
const PROPOSAL_STATES: ReadonlyArray<readonly [number, string, string]> = [
  [101, "proposed", "M"],
  [102, "verified", "C"],
  [103, "approved", "M"],
  [104, "measuring", "C"],
  [105, "rejected", "M"],
  [106, "closed", "C"],
  [107, "archived-x", "C"],
];
function proposalsFixture(rows: ReadonlyArray<readonly [number, string, string]> = PROPOSAL_STATES): SiFixture {
  const fixture = clone(GA);
  const base = GA.proposals.items[0];
  fixture.proposals.items = rows.map(([n, state, cls]): SiProposal => ({ ...clone(base), id: `PROP-SI-${n}`, state, cls }));
  return fixture;
}

describe("觀察分頁的狀態快篩：未結、延後、已完成", () => {
  it("四顆 pill（全部、未結、延後、已完成）：預設只有「全部」被按下；整組的名稱是「狀態快篩」，pill 是 type=button 的按鈕，旁邊顯示符合與已載入筆數，壞列另註", async () => {
    renderSi();
    await screen.findByTestId("si-obs-table");
    const bar = screen.getByTestId("si-status-filter-observations");
    const group = within(bar).getByRole("group", { name: "狀態快篩" });
    const buttons = within(group).getAllByRole("button");
    expect(buttons.map((b) => b.textContent)).toEqual(["全部", "未結", "延後", "已完成"]);
    expect(buttons.map((b) => b.dataset.testid)).toEqual(["si-status-observations-all", "si-status-observations-open", "si-status-observations-deferred", "si-status-observations-done"]);
    for (const b of buttons) expect(b).toHaveAttribute("type", "button");
    expect(pressedPills("observations")).toEqual(["全部"]);
    // 三類加起來是全部有效列（防反空轉：每一類都真的有列）
    expect(OPEN_IDS.length).toBeGreaterThan(0);
    expect(DEFERRED_IDS.length).toBeGreaterThan(0);
    expect(DONE_IDS.length).toBeGreaterThan(0);
    expect(OPEN_IDS.length + DEFERRED_IDS.length + DONE_IDS.length).toBe(GOLDEN_OBS.length);
    // 預設不篩：有效列全在；壞列不算符合、另註（11 筆有效列加 1 筆壞列，共 12 筆已載入）
    expect(obsRowIds(panel("observations"))).toEqual(GOLDEN_OBS.map((o) => o.id));
    expect(count("observations")).toBe(`符合 ${GOLDEN_OBS.length}／已載入 ${GA.observations.items.length}（另有 1 筆無法解析的列照常顯示）`);
  });

  it("按「已完成」只剩有終值的列（decided、merged…）；按「未結」只剩 open；按「延後」只剩 deferred；壞列每次都在；再按「全部」12 項全回來；不多打任何請求", async () => {
    const user = userEvent.setup();
    const { urls } = renderSi();
    await screen.findByTestId("si-obs-table");
    const obs = panel("observations");

    await user.click(pill("observations", "done"));
    expect(obsRowIds(obs)).toEqual(DONE_IDS);
    expect(badRows(obs)).toHaveLength(1);
    expect(pressedPills("observations")).toEqual(["已完成"]);
    expect(count("observations")).toBe(`符合 ${DONE_IDS.length}／已載入 ${GA.observations.items.length}（另有 1 筆無法解析的列照常顯示）`);

    await user.click(pill("observations", "open"));
    expect(obsRowIds(obs)).toEqual(OPEN_IDS);
    expect(badRows(obs)).toHaveLength(1);
    expect(pressedPills("observations")).toEqual(["未結"]);

    await user.click(pill("observations", "deferred"));
    expect(obsRowIds(obs)).toEqual(DEFERRED_IDS);
    expect(badRows(obs)).toHaveLength(1);
    expect(pressedPills("observations")).toEqual(["延後"]);

    // 單選：再按一次已按下的 pill 維持原選擇（要取消靠「全部」）
    await user.click(pill("observations", "deferred"));
    expect(pressedPills("observations")).toEqual(["延後"]);
    expect(obsRowIds(obs)).toEqual(DEFERRED_IDS);

    await user.click(pill("observations", "all"));
    expect(pressedPills("observations")).toEqual(["全部"]);
    expect(obsRowIds(obs)).toEqual(GOLDEN_OBS.map((o) => o.id));
    expect(badRows(obs)).toHaveLength(1);

    // 這份黃金檔一頁就載完（沒有下一頁）：快篩不需要、也不該多打請求
    expect(obsRequests(urls())).toHaveLength(1);
  });

  it("與其他篩選取交集：已完成加嚴重度 P3，只剩兩個條件同時成立的列", async () => {
    const user = userEvent.setup();
    renderSi();
    await screen.findByTestId("si-obs-table");
    const obs = panel("observations");
    await user.click(pill("observations", "done"));
    await user.selectOptions(within(obs).getByLabelText("嚴重度"), "P3");
    const expected = GOLDEN_OBS.filter((o) => DONE_IDS.includes(o.id) && o.severity === "P3").map((o) => o.id);
    expect(expected.length).toBeGreaterThan(0);
    expect(expected.length).toBeLessThan(DONE_IDS.length);
    expect(obsRowIds(obs)).toEqual(expected);
    expect(badRows(obs)).toHaveLength(1);
  });

  it("壞列永遠顯示：快篩下沒有任何有效列符合時只剩壞列，並說「沒有符合目前篩選的觀察列」；符合數是 0、壞列另註", async () => {
    const user = userEvent.setup();
    const fixture = clone(GA);
    for (const o of fixture.observations.items.filter(isValid)) o.disposition = "open";
    renderSi({ fixture });
    await screen.findByTestId("si-obs-table");
    const obs = panel("observations");
    await user.click(pill("observations", "done"));
    expect(obsRowIds(obs)).toEqual([]);
    expect(within(obs).getByTestId(`si-obs-invalid-${BAD.line}`)).toHaveTextContent(BAD.raw);
    expect(obs).toHaveTextContent("沒有符合目前篩選的觀察列");
    expect(count("observations")).toBe(`符合 0／已載入 ${fixture.observations.items.length}（另有 1 筆無法解析的列照常顯示）`);
  });

  it("空處置的有效列歸「未結」，不出現在「已完成」（不宣稱一筆沒處置的列已完成）", async () => {
    const user = userEvent.setup();
    const fixture = clone(GA);
    const blank = fixture.observations.items.filter(isValid)[0];
    blank.disposition = "";
    renderSi({ fixture });
    await screen.findByTestId("si-obs-table");
    const obs = panel("observations");
    await user.click(pill("observations", "open"));
    expect(obsRowIds(obs)).toContain(blank.id);
    await user.click(pill("observations", "done"));
    expect(obsRowIds(obs)).not.toContain(blank.id);
  });
});

describe("提案分頁的狀態快篩：待決、進行中、已完成", () => {
  it("四顆 pill（全部、待決、進行中、已完成）：預設只有「全部」被按下；「狀態快篩」與既有的「狀態」下拉是兩個不同名稱的控制項（getByLabelText 仍取得唯一的下拉）", async () => {
    const user = userEvent.setup();
    renderSi({ fixture: proposalsFixture() });
    await user.click(await screen.findByRole("tab", { name: /^提案/ }));
    await screen.findByTestId("si-prop-table");
    const props = panel("proposals");
    const group = within(screen.getByTestId("si-status-filter-proposals")).getByRole("group", { name: "狀態快篩" });
    const buttons = within(group).getAllByRole("button");
    expect(buttons.map((b) => b.textContent)).toEqual(["全部", "待決", "進行中", "已完成"]);
    expect(buttons.map((b) => b.dataset.testid)).toEqual(["si-status-proposals-all", "si-status-proposals-pending", "si-status-proposals-active", "si-status-proposals-done"]);
    for (const b of buttons) expect(b).toHaveAttribute("type", "button");
    expect(pressedPills("proposals")).toEqual(["全部"]);
    expect(within(props).getByLabelText("狀態").tagName).toBe("SELECT");
    expect(propRowIds(props)).toEqual(PROPOSAL_STATES.map(([n]) => `PROP-SI-${n}`));
    expect(count("proposals")).toBe("符合 7／已載入 7");
  });

  it("按「待決」只剩 proposed、verified；「進行中」只剩 approved、measuring；「已完成」只剩 rejected、closed；狀態未登記的提案在每一顆下都照常顯示並另註", async () => {
    const user = userEvent.setup();
    renderSi({ fixture: proposalsFixture() });
    await user.click(await screen.findByRole("tab", { name: /^提案/ }));
    await screen.findByTestId("si-prop-table");
    const props = panel("proposals");
    const UNKNOWN = "PROP-SI-107";

    await user.click(pill("proposals", "pending"));
    expect(propRowIds(props)).toEqual(["PROP-SI-101", "PROP-SI-102", UNKNOWN]);
    expect(count("proposals")).toBe("符合 2／已載入 7（另有 1 筆狀態未登記的提案照常顯示）");
    expect(pressedPills("proposals")).toEqual(["待決"]);

    await user.click(pill("proposals", "active"));
    expect(propRowIds(props)).toEqual(["PROP-SI-103", "PROP-SI-104", UNKNOWN]);
    expect(count("proposals")).toBe("符合 2／已載入 7（另有 1 筆狀態未登記的提案照常顯示）");

    await user.click(pill("proposals", "done"));
    expect(propRowIds(props)).toEqual(["PROP-SI-105", "PROP-SI-106", UNKNOWN]);
    // 未登記的狀態字串原樣顯示在那一列（不改寫成別的類別）
    expect(within(props).getByTestId(`si-prop-row-${UNKNOWN}`)).toHaveTextContent("archived-x");

    await user.click(pill("proposals", "all"));
    expect(propRowIds(props)).toHaveLength(7);
    expect(count("proposals")).toBe("符合 7／已載入 7");
  });

  it("與「狀態」下拉、「類別」下拉取交集：快篩不凌駕下拉；未登記的狀態只躲過快篩，躲不過另兩個條件", async () => {
    const user = userEvent.setup();
    renderSi({ fixture: proposalsFixture() });
    await user.click(await screen.findByRole("tab", { name: /^提案/ }));
    await screen.findByTestId("si-prop-table");
    const props = panel("proposals");

    await user.click(pill("proposals", "done"));
    await user.selectOptions(within(props).getByLabelText("類別"), "C");
    expect(propRowIds(props)).toEqual(["PROP-SI-106", "PROP-SI-107"]);
    await user.selectOptions(within(props).getByLabelText("類別"), "M");
    expect(propRowIds(props)).toEqual(["PROP-SI-105"]);
    await user.selectOptions(within(props).getByLabelText("類別"), "");
    await user.selectOptions(within(props).getByLabelText("狀態"), "rejected");
    expect(propRowIds(props)).toEqual(["PROP-SI-105"]);
    // 快篩選「待決」而下拉選「rejected」：兩者交集為空（快篩不會把下拉蓋掉），沒有未登記的狀態是 rejected，所以整列清單為空並說明
    await user.click(pill("proposals", "pending"));
    expect(propRowIds(props)).toEqual([]);
    expect(props).toHaveTextContent("沒有符合目前篩選的提案");
  });
});

describe("快篩開著時自動載完其餘頁", () => {
  it("觀察：選「已完成」不必按「載入更多」就把三頁載完（一次一頁）；載入期間顯示載入中、不宣稱「沒有符合」；載完後說明都消失；快篩沒開時不自動載", async () => {
    limits.value = 5;
    const user = userEvent.setup();
    // 前五個有效列全改成 open：第一頁沒有任何「已完成」，才看得出載入期間不會說「沒有符合」
    const fixture = clone(GA);
    for (const o of fixture.observations.items.filter(isValid).slice(0, 5)) o.disposition = "open";
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const { urls } = renderSi({
      fixture,
      overrides: {
        observations: async (call) => {
          if (call.query.get("since") === "5") await gate; // 第二頁卡住，觀察載入中的畫面
          return undefined;
        },
      },
    });
    await screen.findByRole("tab", { name: "觀察 (5+)" });
    await settle();
    expect(obsRequests(urls())).toEqual(["/api/v1/si/observations?limit=5"]); // 快篩沒開：只有第一頁，不自動載

    await user.click(pill("observations", "done"));
    const obs = panel("observations");
    expect(await within(obs).findByTestId("si-loading")).toHaveTextContent("其餘觀察列載入中…");
    expect(obs).not.toHaveTextContent("沒有符合目前篩選的觀察列");
    expect(within(obs).queryByTestId("si-status-incomplete-observations")).toBeNull();
    expect(within(obs).queryByRole("button", { name: "載入更多" }), "自動載入期間不放手動的載入更多").toBeNull();

    release();
    await screen.findByRole("tab", { name: "觀察 (12)" });
    expect(obsRequests(urls())).toEqual(["/api/v1/si/observations?limit=5", "/api/v1/si/observations?since=5&limit=5", "/api/v1/si/observations?since=10&limit=5"]);
    expect(within(obs).queryByTestId("si-loading")).toBeNull();
    expect(within(obs).queryByTestId("si-status-incomplete-observations")).toBeNull();
    expect(within(obs).queryByTestId("si-filter-scope-note")).toBeNull();
    expect(within(obs).queryByRole("button", { name: "載入更多" })).toBeNull();
    // 篩選結果涵蓋全部三頁：第六列起的終值列都在
    const expected = fixture.observations.items
      .filter(isValid)
      .filter((o) => o.disposition !== "open" && !o.disposition.startsWith("deferred"))
      .map((o) => o.id);
    expect(expected.length).toBeGreaterThan(0);
    expect(obsRowIds(obs)).toEqual(expected);
    expect(count("observations")).toBe(`符合 ${expected.length}／已載入 12（另有 1 筆無法解析的列照常顯示）`);
  });

  it("快篩關掉（回到「全部」）立刻停止自動載入：在飛的那一頁照收，之後不再要下一頁", async () => {
    limits.value = 5;
    const user = userEvent.setup();
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const { urls } = renderSi({
      overrides: {
        observations: async (call) => {
          if (call.query.get("since") === "5") await gate;
          return undefined;
        },
      },
    });
    await screen.findByRole("tab", { name: "觀察 (5+)" });
    await user.click(pill("observations", "done"));
    await within(panel("observations")).findByTestId("si-loading");
    await user.click(pill("observations", "all"));
    expect(within(panel("observations")).queryByTestId("si-loading")).toBeNull();
    release();
    await screen.findByRole("tab", { name: "觀察 (10+)" });
    await settle();
    expect(obsRequests(urls())).toEqual(["/api/v1/si/observations?limit=5", "/api/v1/si/observations?since=5&limit=5"]);
    expect(screen.getByRole("button", { name: "載入更多" })).toBeEnabled(); // 還有第三頁，留給人按
  });

  it(`載到頁數上限（${SI_AUTO_LOAD_MAX_PAGES} 頁）仍有下一頁：停止自動載入並說「尚有未載入的列，結果不完整」；人仍可按「載入更多」繼續，但自動載入不因此恢復`, async () => {
    const user = userEvent.setup();
    // 永遠有下一頁的替身（游標失控的情境）：每頁一個「已完成」的有效列
    const endless = (call: SiCall) => {
      const n = Number(call.query.get("since") ?? 0) + 1;
      const row: SiObservation = { ...clone(GOLDEN_OBS[0]), id: `OBS-SI-${1000 + n}`, disposition: "decided：x", line: n };
      return { data: { ...clone(GA.observations), items: [row], truncated: true, nextSince: n, ne: [], problems: [] } };
    };
    const { urls } = renderSi({ overrides: { observations: endless } });
    await screen.findByRole("tab", { name: "觀察 (1+)" });
    await user.click(pill("observations", "done"));
    const obs = panel("observations");
    const note = await within(obs).findByTestId("si-status-incomplete-observations", {}, { timeout: 20_000 });
    expect(note).toHaveTextContent("尚有未載入的列，結果不完整");
    expect(obsRequests(urls())).toHaveLength(SI_AUTO_LOAD_MAX_PAGES);
    expect(within(obs).queryByTestId("si-loading")).toBeNull();
    expect(count("observations")).toBe(`符合 ${SI_AUTO_LOAD_MAX_PAGES}／已載入 ${SI_AUTO_LOAD_MAX_PAGES}`);
    expect(within(obs).getByTestId("si-filter-scope-note")).toBeInTheDocument();
    await settle();
    expect(obsRequests(urls())).toHaveLength(SI_AUTO_LOAD_MAX_PAGES); // 到上限就停，沒有後續請求

    await user.click(within(obs).getByTestId("si-load-more"));
    await screen.findByRole("tab", { name: `觀察 (${SI_AUTO_LOAD_MAX_PAGES + 1}+)` });
    await settle();
    expect(obsRequests(urls())).toHaveLength(SI_AUTO_LOAD_MAX_PAGES + 1); // 手動多載一頁；自動載入沒有因此恢復
    expect(within(obs).getByTestId("si-status-incomplete-observations")).toBeInTheDocument();
  });

  it("回應標示 truncated 卻沒有游標（契約被違反）：快篩下不空等載入、也不再打請求，直接說結果不完整（既有的缺游標警示照舊）", async () => {
    limits.value = 5;
    const user = userEvent.setup();
    const page1 = clone(GA.observations);
    page1.items = page1.items.slice(0, 5);
    page1.truncated = true;
    page1.nextSince = null;
    const { urls } = renderSi({ overrides: { observations: () => ({ data: page1 }) } });
    await screen.findByRole("tab", { name: "觀察 (5+)" });
    await user.click(pill("observations", "done"));
    const obs = panel("observations");
    expect(await within(obs).findByTestId("si-status-incomplete-observations")).toHaveTextContent("尚有未載入的列，結果不完整");
    expect(within(obs).queryByTestId("si-loading")).toBeNull();
    expect(within(obs).getByTestId("si-cursor-missing")).toBeInTheDocument();
    await settle();
    expect(obsRequests(urls())).toHaveLength(1);
  });

  it("取頁失敗就停：顯示錯誤態與原因、不自動重打；重試成功後接著把其餘頁載完，快篩的選擇仍在", async () => {
    limits.value = 5;
    const user = userEvent.setup();
    let failSecondPage = true;
    const { urls } = renderSi({ overrides: { observations: (call) => (failSecondPage && call.query.get("since") === "5" ? siUnavailable() : undefined) } });
    await screen.findByRole("tab", { name: "觀察 (5+)" });
    await user.click(pill("observations", "done"));
    const obs = panel("observations");
    await within(obs).findByTestId("si-error");
    await settle();
    expect(obsRequests(urls())).toEqual(["/api/v1/si/observations?limit=5", "/api/v1/si/observations?since=5&limit=5"]); // 失敗後沒有自動重打

    failSecondPage = false;
    await user.click(within(obs).getByTestId("si-retry"));
    await screen.findByRole("tab", { name: "觀察 (12)" });
    expect(pressedPills("observations")).toEqual(["已完成"]);
    expect(obsRowIds(obs)).toEqual(DONE_IDS);
    expect(obsRequests(urls())).toEqual([
      "/api/v1/si/observations?limit=5",
      "/api/v1/si/observations?since=5&limit=5", // 失敗的那一次
      "/api/v1/si/observations?limit=5", // 重試：重抓已載入的頁
      "/api/v1/si/observations?since=5&limit=5",
      "/api/v1/si/observations?since=10&limit=5",
    ]);
  });

  it("提案分頁同樣自動載完其餘頁（一頁一筆、三頁）；未登記狀態的提案照常顯示並另註", async () => {
    limits.value = 1;
    const user = userEvent.setup();
    const { urls } = renderSi({
      fixture: proposalsFixture([
        [101, "closed", "M"],
        [102, "proposed", "M"],
        [103, "archived-x", "M"],
      ]),
    });
    await user.click(await screen.findByRole("tab", { name: /^提案/ }));
    await screen.findByRole("tab", { name: "提案 (1+)" });
    await settle();
    expect(propRequests(urls())).toEqual(["/api/v1/si/proposals?limit=1"]); // 快篩沒開：不自動載

    await user.click(pill("proposals", "pending"));
    await screen.findByRole("tab", { name: "提案 (3)" });
    expect(propRequests(urls())).toEqual(["/api/v1/si/proposals?limit=1", "/api/v1/si/proposals?since=101&limit=1", "/api/v1/si/proposals?since=102&limit=1"]);
    const props = panel("proposals");
    expect(propRowIds(props)).toEqual(["PROP-SI-102", "PROP-SI-103"]);
    expect(count("proposals")).toBe("符合 1／已載入 3（另有 1 筆狀態未登記的提案照常顯示）");
    expect(within(props).queryByTestId("si-loading")).toBeNull();
    expect(within(props).queryByTestId("si-status-incomplete-proposals")).toBeNull();
  });
});
