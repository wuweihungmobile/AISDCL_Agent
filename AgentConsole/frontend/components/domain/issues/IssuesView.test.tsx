/**
 * IssuesView 的元件測試（TCS-IssueCenter-20261027 FR-IC-05、08、09、10、12 的前端畫面 AT；R-IC-63～71、R-IC-74）：
 * 整頁（摘要列、四分頁、篩選、提示條、清單、詳情、狀態說明、優先順序、決定與關閉按鈕）對 issues.fixtures.ts 的假後端（回放黃金檔的圖例）渲染。
 * 畫面的 DOM 契約（data-testid）見 TCS §5.4：issues-page／issues-error-panel／issues-empty／issues-incomplete／issues-hint-bar、issues-summary-*、issues-sev-*、
 * issues-filter-*、issues-status-pill-*、issue-row-<ID>／issue-top-pinned、issue-detail*、issue-priority-*、issue-decide-／issue-close-／issue-admin-only-<ID>。
 * 頁大小與自動載入頁數上限由 vi.mock 的 getter 局部覆寫（其餘測試維持正式值）。
 */
import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Issue, Role } from "@/lib/api/types";
import { englishStateWords } from "@/lib/domain/issues";
import { failure } from "@/tests/helpers/api";
import { IssuesView } from "./IssuesView";
import { LEGEND, PROPOSAL, clone, makeIssue, newStub, renderIssues, unavailable, type IssuesStub } from "./tests/issues.fixtures";

const limits = vi.hoisted(() => ({ pageSize: 100, maxPages: 20 }));
vi.mock("@/lib/domain/si", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/domain/si")>();
  return {
    ...mod,
    get SI_PAGE_LIMIT() {
      return limits.pageSize;
    },
    get SI_AUTO_LOAD_MAX_PAGES() {
      return limits.maxPages;
    },
  };
});
// 測試環境沒有 App Router：AuthProvider 要的 useRouter 換成可斷言的替身（詳情不換路由＝這些都不該被呼叫）
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/issues",
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));
afterEach(() => {
  limits.pageSize = 100;
  limits.maxPages = 20;
  delete (window as unknown as Record<string, unknown>).__xss;
});

// ── 小工具 ────────────────────────────────────────────────────────────────────

/** 十八個夾具議題在各分頁的列序（第一條：待處理、待您決定；第二條：已完成、全部＋待您決定置頂）。 */
const PENDING = ["OBS-SI-006", "DEF-999-005", "OBS-SI-007", "OBS-SI-008", "OBS-SI-009"];
const DECIDE = ["OBS-SI-005", "PROP-SI-004"];
const DONE = ["OBS-SI-011", "PROP-SI-005", "OBS-SI-001", "OBS-SI-002", "OBS-SI-010", "DEF-999-003", "DEF-999-002", "DEF-999-001"];
const ALL = [
  ...DECIDE,
  "OBS-SI-011",
  "PROP-SI-005",
  "OBS-SI-004",
  "OBS-SI-001",
  "OBS-SI-002",
  "OBS-SI-003",
  "OBS-SI-008",
  "OBS-SI-007",
  "OBS-SI-006",
  "DEF-999-005",
  "OBS-SI-010",
  "DEF-999-004",
  "DEF-999-003",
  "DEF-999-002",
  "DEF-999-001",
  "OBS-SI-009",
];

const rowIds = () => Array.from(document.querySelectorAll<HTMLElement>('[data-testid^="issue-row-"]')).map((el) => (el.dataset.testid as string).replace("issue-row-", ""));
const row = (id: string) => screen.getByTestId(`issue-row-${id}`);
/** 某列第 index 格（不經可及性樹：Radix 對話框開著時其餘畫面是 aria-hidden，role 查詢會看不到它）。 */
const cell = (id: string, index: number) => row(id).querySelectorAll("td")[index];
const tabButton = (name: string) => screen.getByRole("tab", { name });
const listCalls = (stub: IssuesStub) => stub.calls.filter((c) => c.method === "GET" && c.path === "/api/v1/issues");
const summaryText = (name: "pending" | "decide" | "done") => (screen.getByTestId(`issues-summary-${name}`).textContent ?? "").trim();

async function open(options: { role?: Role; stub?: IssuesStub; username?: string } = {}) {
  const user = userEvent.setup();
  const view = renderIssues(<IssuesView />, options);
  return { user, ...view };
}
/** 切到某分頁並等它的資料載入完（載入中時表格會先卸載）。 */
async function goTo(user: ReturnType<typeof userEvent.setup>, name: string) {
  await user.click(tabButton(name));
  await waitFor(() => expect(screen.getByRole("tab", { name })).toHaveAttribute("aria-selected", "true"));
  await screen.findByTestId("issues-table");
}
const stubOf = (items: Issue[] = []): IssuesStub => newStub({ items });

// ── 摘要列、分頁與 status 傳值 ─────────────────────────────────────────────────────

describe("AT_IC_08_3 開頁、分頁與 status 傳值", () => {
  it("AT_IC_08_3_1 預設分頁＝待處理；四分頁各以規定的 status 向 API 取資料；摘要列三數字＝summary.byTab；待處理上方有計件條；沒有「本週完成」", async () => {
    const { user, stub } = await open();
    await screen.findByTestId("issues-table");
    expect(tabButton("待處理")).toHaveAttribute("aria-selected", "true");
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["待處理", "待您決定", "已完成", "全部"]);
    expect(rowIds()).toEqual(PENDING);
    expect([summaryText("pending"), summaryText("decide"), summaryText("done")]).toEqual(["待處理 5", "待您決定 2", "已完成 8"]);
    expect(screen.getByTestId("issues-severity-bar")).toBeInTheDocument();
    expect(screen.queryByText(/本週完成/)).toBeNull();

    // 逐一切分頁：待您決定→「待您決定」、已完成→「已完成」、全部→不帶 status；第一個請求是待處理→「待處理」
    await goTo(user, "待您決定");
    await goTo(user, "已完成");
    await goTo(user, "全部");
    expect(listCalls(stub).map((c) => c.query.get("status"))).toEqual(["待處理", "待您決定", "已完成", null]);
    expect(listCalls(stub).map((c) => c.query.has("status"))).toEqual([true, true, true, false]);
    // 摘要列不隨分頁改變（整本帳的計數）
    expect([summaryText("pending"), summaryText("decide"), summaryText("done")]).toEqual(["待處理 5", "待您決定 2", "已完成 8"]);
    expect(rowIds()).toHaveLength(18);
  });

  it("AT_IC_08_3_E_1 切到待處理恰一個請求且 status＝「待處理」（不是三個成員的列舉）；前端不持有成員清單", async () => {
    const { user, stub } = await open();
    await goTo(user, "已完成");
    stub.calls.length = 0;
    await goTo(user, "待處理");
    const calls = listCalls(stub);
    expect(calls).toHaveLength(1);
    expect(calls[0].query.get("status")).toBe("待處理");
    expect(calls[0].query.get("status")).not.toContain(",");
    expect(calls[0].url).toBe(`/api/v1/issues?status=${encodeURIComponent("待處理")}&limit=100`);
    expect(rowIds()).toEqual(PENDING);
  });
});

describe("AT_IC_08_4 清單與詳情", () => {
  it("AT_IC_08_4_1 固定八欄依序為編號、來源、標題、嚴重度、狀態、優先順序、最後更新、下一步；點編號開側面板詳情（同頁、不換路由）", async () => {
    const { user } = await open();
    const table = await screen.findByTestId("issues-table");
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["編號", "來源", "標題", "嚴重度", "狀態", "優先順序", "最後更新", "下一步"]);
    // 列內容逐欄對得上（以待處理第一列 OBS-SI-006 為例）
    expect(
      within(row("OBS-SI-006"))
        .getAllByRole("cell")
        .map((c) => c.textContent),
    ).toEqual(["OBS-SI-006", "系統缺陷", "緊急的缺陷", "緊急", "待解", "—", "2026-10-10", "已成立，尚無人接手"]);
    // 表外值與 null 以「—」顯示
    expect(cell("OBS-SI-009", 3).textContent).toBe("未歸類：P5");
    expect(cell("OBS-SI-009", 6).textContent).toBe("—");
    expect(cell("DEF-999-005", 1).textContent).toBe("—");
    expect(cell("OBS-SI-008", 3).textContent).toBe("—");

    const before = window.location.href;
    expect(screen.queryByTestId("issue-detail")).toBeNull();
    await user.click(screen.getByRole("button", { name: "OBS-SI-006" }));
    const detail = await screen.findByTestId("issue-detail");
    // 同頁的側面板：原列、時間線、關聯都在，沒有導覽
    for (const testId of ["issue-detail-raw", "issue-detail-timeline", "issue-detail-links"]) expect(await within(detail).findByTestId(testId)).toBeInTheDocument();
    expect(window.location.href).toBe(before);
    expect(router.push).not.toHaveBeenCalled();
    expect(router.replace).not.toHaveBeenCalled();
    expect(row("OBS-SI-006")).toHaveAttribute("aria-current", "true");
    // 關閉鈕收起面板
    await user.click(within(detail).getByRole("button", { name: "關閉詳情" }));
    expect(screen.queryByTestId("issue-detail")).toBeNull();
  });
});

// ── 置頂 ─────────────────────────────────────────────────────────────────────────

describe("AT_IC_05_7 全部分頁待您決定的列置頂", () => {
  it("AT_IC_05_7_1 全部分頁：待您決定的列全部置頂（帶 issue-top-pinned 與 aria-label=置頂，其內依第一條），其餘依第二條且無該元素；待您決定分頁每列同樣帶該元素", async () => {
    const { user } = await open();
    await goTo(user, "全部");
    await waitFor(() => expect(rowIds()).toHaveLength(18));
    expect(rowIds()).toEqual(ALL);
    const pinned = screen.getAllByTestId("issue-top-pinned");
    expect(pinned).toHaveLength(2);
    for (const el of pinned) expect(el).toHaveAttribute("aria-label", "置頂");
    for (const id of DECIDE) expect(within(row(id)).getByTestId("issue-top-pinned")).toBeInTheDocument();
    for (const id of ALL.slice(2)) expect(within(row(id)).queryByTestId("issue-top-pinned"), id).toBeNull();

    await goTo(user, "待您決定");
    expect(rowIds()).toEqual(DECIDE);
    expect(screen.getAllByTestId("issue-top-pinned")).toHaveLength(2);
    for (const id of DECIDE) expect(within(row(id)).getByRole("img", { name: "置頂" })).toBeInTheDocument();
  });

  it("AT_IC_05_7_E_1 置頂只改顯示序：summary 數字與各分頁件數不變；待處理與已完成分頁沒有該元素", async () => {
    const { user } = await open();
    const counts: Record<string, number> = {};
    for (const [name, expected] of [
      ["待處理", PENDING],
      ["待您決定", DECIDE],
      ["已完成", DONE],
      ["全部", ALL],
    ] as const) {
      await goTo(user, name);
      await waitFor(() => expect(rowIds()).toHaveLength(expected.length));
      counts[name] = rowIds().length;
      expect(rowIds().slice().sort()).toEqual([...expected].sort());
      expect([summaryText("pending"), summaryText("decide"), summaryText("done")]).toEqual(["待處理 5", "待您決定 2", "已完成 8"]);
      if (name === "待處理" || name === "已完成") expect(screen.queryByTestId("issue-top-pinned"), name).toBeNull();
    }
    expect(counts).toEqual({ 待處理: 5, 待您決定: 2, 已完成: 8, 全部: 18 });
    // 件數＝摘要列的數字（全部＝七狀態件數和加表外值）
    expect(counts["全部"]).toBe(5 + 2 + 8 + 1 + 1 + 1);
  });
});

// ── 中文判準 ──────────────────────────────────────────────────────────────────────

describe("AT_IC_08_1 畫面可見文字不含英文狀態詞", () => {
  it("AT_IC_08_1_1 渲染清單、詳情與狀態說明：可見文字（排除標題、編號、原列展開區、優先順序備註、延後列的下一步原文節錄）不含 §5.4 的英文詞；原列展開區顯示原值且標籤為中文", async () => {
    const stub = newStub();
    stub.ne = [{ field: "ledger.sibling.AutoSDD_External_Blocked_Log.md", reason: "SIBLING-LEDGER-UNAVAILABLE" }];
    stub.problems = [{ subject: "OBS-SI-012", code: "ROW-ARITY", detail: "欄數與表頭不符" }];
    stub.priorities.set("OBS-SI-006", { rank: 1, note: "備註含 fixed 與 open 等英文" });
    const { user } = await open({ role: "ADMIN", stub });
    await goTo(user, "全部");
    await waitFor(() => expect(rowIds()).toHaveLength(18));
    await user.click(screen.getByRole("button", { name: "OBS-SI-003" }));
    const raw = await screen.findByTestId("issue-detail-raw");
    await user.click(screen.getByTestId("issues-legend-open"));
    await screen.findByTestId("issues-legend-dialog");

    // 原列展開區：標籤是中文、值逐字（含英文原值）
    expect(Array.from(raw.querySelectorAll("dt")).every((el) => !/[A-Za-z]/.test(el.textContent ?? ""))).toBe(true);
    expect(raw.textContent).toContain("open");
    expect(englishStateWords(raw.textContent ?? "").length).toBeGreaterThan(0);
    // 下一步欄的原文節錄與備註含英文（它們是被排除的區域）
    expect(englishStateWords(screen.getByTestId("issue-next-OBS-SI-003").textContent ?? "").length).toBeGreaterThan(0);
    expect(englishStateWords(screen.getByTestId("issue-priority-note-OBS-SI-006").textContent ?? "").length).toBeGreaterThan(0);

    // 其餘可見文字：清掉被排除的區域後，整個文件（含對話框的 portal）不含任何英文狀態詞
    const copy = document.body.cloneNode(true) as HTMLElement;
    // （延後列的下一步原文節錄在清單的下一步欄與詳情的「下一步」區各出現一次）
    copy
      .querySelectorAll(
        [
          '[data-testid^="issue-title-"]',
          '[data-testid^="issue-open-"]',
          '[data-testid="issue-detail-raw"]',
          '[data-testid="issue-detail-title"]',
          '[data-testid^="issue-priority-note-"]',
          '[data-testid="issue-next-OBS-SI-003"]',
          'section[aria-label="下一步"]',
          "h2",
        ].join(","),
      )
      .forEach((el) => el.remove());
    const visible = copy.textContent ?? "";
    expect(visible).toContain("狀態說明");
    expect(visible).toContain("提示：");
    expect(englishStateWords(visible)).toEqual([]);
  });
});

// ── 錯誤、不完整與提示條 ───────────────────────────────────────────────────────────

describe("AT_IC_08_5 量不到與提示條", () => {
  it("AT_IC_08_5_1 Bridge 503 或 504：整片顯示原因（cause、detail 逐字），摘要列三數字顯示「—」，不顯示「0 件」或空表", async () => {
    // 503（CLI 失敗）：reason、cause、detail 逐字
    const down = await open({ stub: newStub({ overrides: { list: () => unavailable("nonzero_rc", "rc=2; stderr=boom 全形字元") } }) });
    const panel = await screen.findByTestId("issues-error-panel");
    expect(within(panel).getByTestId("issues-error-summary")).toHaveTextContent("議題資料暫時無法取得");
    expect(within(panel).getByTestId("issues-error-reason").textContent).toBe("si_unavailable");
    expect(within(panel).getByTestId("issues-error-cause").textContent).toBe("nonzero_rc");
    expect(within(panel).getByTestId("issues-error-detail").textContent).toBe("rc=2; stderr=boom 全形字元");
    expect([summaryText("pending"), summaryText("decide"), summaryText("done")]).toEqual(["待處理 —", "待您決定 —", "已完成 —"]);
    for (const testId of ["issues-table", "issues-empty", "issues-no-match", "issues-severity-bar", "issues-filter-source"]) expect(screen.queryByTestId(testId), testId).toBeNull();
    expect(screen.queryByText(/0 件/)).toBeNull();
    expect(screen.getByTestId("issues-legend-open")).toBeDisabled(); // 沒有圖例可看
    // 重試：下一次成功就回到清單
    down.stub.overrides.list = undefined;
    await down.user.click(screen.getByTestId("issues-retry"));
    await screen.findByTestId("issues-table");
    expect(screen.queryByTestId("issues-error-panel")).toBeNull();
    expect(summaryText("pending")).toBe("待處理 5");
    down.unmount();

    // 504（逾時）：同樣整片錯誤、摘要「—」
    await open({ stub: newStub({ overrides: { list: () => failure(504, { message: "引擎橋接服務逾時", reason: "引擎橋接服務逾時" }) } }) });
    const timeout = await screen.findByTestId("issues-error-panel");
    expect(within(timeout).getByTestId("issues-error-reason").textContent).toBe("引擎橋接服務逾時");
    expect(summaryText("pending")).toBe("待處理 —");
    expect(screen.queryByTestId("issues-table")).toBeNull();
  });

  it("AT_IC_08_5_2 某帳本讀不到（ne 含 *-LEDGER-UNAVAILABLE、summary.byTab 對應格 null）：該格顯示「—」、其餘格與清單照常；提示條明說哪一本讀不到（說明取自 legend）", async () => {
    const stub = newStub();
    stub.ne = [{ field: "ledger.defect", reason: "DEFECT-LEDGER-UNAVAILABLE" }];
    stub.summary = (s) => ({ ...s, byTab: { ...s.byTab, 待處理: null, 已完成: null } });
    await open({ stub });
    await screen.findByTestId("issues-table");
    expect([summaryText("pending"), summaryText("decide"), summaryText("done")]).toEqual(["待處理 —", "待您決定 2", "已完成 —"]);
    expect(rowIds()).toEqual(PENDING); // 清單照常
    const hint = screen.getByTestId("issues-hint-bar");
    const meaning = LEGEND.neReasons.find((r) => r.reason === "DEFECT-LEDGER-UNAVAILABLE")?.meaning ?? "";
    expect(meaning).toContain("缺陷帳本");
    expect(hint).toHaveTextContent(meaning);
    expect(hint).toHaveTextContent("提示：1 項資料量不到");
  });

  it("AT_IC_08_5_E_1 ne 或 problems 非空：一律顯示提示條但清單照常；兩者皆空：沒有提示條", async () => {
    const cases: Array<[string, Partial<Pick<IssuesStub, "ne" | "problems">>, boolean]> = [
      ["只有 ne", { ne: [{ field: "head_sha", reason: "git-unavailable" }] }, true],
      ["只有 problems", { problems: [{ subject: "OBS-SI-012", code: "ROW-ARITY", detail: "欄數與表頭不符" }] }, true],
      ["兩者皆有", { ne: [{ field: "head_sha", reason: "git-unavailable" }], problems: [{ subject: "PROP-SI-004", code: "UNMAPPED", detail: "來源：x" }] }, true],
      ["兩者皆空", {}, false],
    ];
    for (const [label, notes, shown] of cases) {
      const stub = newStub();
      Object.assign(stub, notes);
      const view = await open({ stub });
      await screen.findByTestId("issues-table");
      expect(screen.queryByTestId("issues-hint-bar") !== null, label).toBe(shown);
      expect(rowIds(), label).toEqual(PENDING);
      if (label === "只有 problems") {
        expect(screen.getByTestId("issues-hint-bar")).toHaveTextContent("提示：1 筆帳本問題");
        expect(screen.getByTestId("issues-hint-bar")).toHaveTextContent("OBS-SI-012（欄數與表頭不符）");
      }
      view.unmount();
    }
  });
});

describe("AT_IC_08_6 自動載完與結果不完整", () => {
  it("AT_IC_08_6_1 回應 truncated 為 true：自動逐頁載完（since 取自上一頁的 nextSince），全部取回後沒有「結果不完整」", async () => {
    limits.pageSize = 5;
    const { user, stub } = await open();
    await goTo(user, "全部");
    await waitFor(() => expect(rowIds()).toHaveLength(18), { timeout: 4000 });
    expect(screen.queryByTestId("issues-incomplete")).toBeNull();
    expect(screen.queryByTestId("issues-loading-more")).toBeNull();
    const all = listCalls(stub).filter((c) => !c.query.has("status"));
    expect(all.map((c) => c.query.get("since"))).toEqual([null, "5", "10", "15"]);
    expect(all.every((c) => c.query.get("limit") === "5")).toBe(true);
    expect(rowIds()).toEqual(ALL); // 併頁後仍依規則排序、不漏不重
  });

  it("AT_IC_08_6_E_1 取完第 20 頁後仍有下一頁：明說「結果不完整」並顯示已載入件數（人仍可按「載入更多」）；恰 20 頁取完且已無下一頁：不顯示", async () => {
    limits.pageSize = 1;
    const make = (n: number) => Array.from({ length: n }, (_, i) => makeIssue(`DEF-999-${String(100 + i)}`, { severityRank: 3, updatedAt: "2026-10-01" }));

    // 21 件：頁大小 1，載到第 20 頁停下
    const more = await open({ stub: stubOf(make(21)) });
    const note = await screen.findByTestId("issues-incomplete", undefined, { timeout: 5000 });
    expect(note).toHaveTextContent("結果不完整");
    expect(note).toHaveTextContent("已載入 20 件");
    expect(rowIds()).toHaveLength(20);
    expect(listCalls(more.stub)).toHaveLength(20);
    // 人仍可手動繼續：載入第 21 頁後件數變 21、不完整的說明消失
    await more.user.click(within(note).getByRole("button", { name: "載入更多" }));
    await waitFor(() => expect(rowIds()).toHaveLength(21));
    expect(screen.queryByTestId("issues-incomplete")).toBeNull();
    more.unmount();

    // 恰 20 件：取完第 20 頁就沒有下一頁，不顯示
    const exact = await open({ stub: stubOf(make(20)) });
    await waitFor(() => expect(rowIds()).toHaveLength(20), { timeout: 5000 });
    await waitFor(() => expect(listCalls(exact.stub)).toHaveLength(20));
    expect(screen.queryByTestId("issues-incomplete")).toBeNull();
    expect(screen.queryByTestId("issues-load-more")).toBeNull();
  }, 30_000);
});

// ── 純文字 ────────────────────────────────────────────────────────────────────────

describe("AT_IC_08_7 帳本與備註文字一律純文字", () => {
  it("AT_IC_08_7_1 標題與優先順序備註含 <script>、**、反引號：一律純文字顯示（不執行、不成元素、不渲染 markdown）", async () => {
    const hostile = "<img src=x onerror=alert(1)> <script>window.__xss=1</script> **粗** `碼` [連結](https://example.invalid/x)";
    const stub = newStub();
    stub.priorities.set("OBS-SI-006", { rank: 1, note: hostile });
    const { user } = await open({ stub });
    await goTo(user, "全部");
    await waitFor(() => expect(rowIds()).toHaveLength(18));
    const title = screen.getByTestId("issue-title-OBS-SI-005");
    expect(title.textContent).toBe(stub.items.find((i) => i.id === "OBS-SI-005")?.title);
    expect(title.textContent).toContain("<script>window.__xss=1</script>");
    const note = screen.getByTestId("issue-priority-note-OBS-SI-006");
    expect(note.textContent).toBe(hostile);
    for (const el of [title, note]) {
      expect(el.children).toHaveLength(0);
      expect(el.querySelector("script, img, strong, b, code, a")).toBeNull();
    }
    expect((window as unknown as Record<string, unknown>).__xss).toBeUndefined();
  });
});

// ── 全部分頁的快篩與關鍵字 ──────────────────────────────────────────────────────────

describe("AT_IC_08_8 全部分頁的快篩、來源下拉與關鍵字", () => {
  it("AT_IC_08_8_1 七顆狀態 pill（文字取自 legend）加「未歸類」、來源下拉、關鍵字；待您決定的列置頂", async () => {
    const { user } = await open();
    await goTo(user, "全部");
    await waitFor(() => expect(rowIds()).toHaveLength(18));
    const names = [...LEGEND.statuses.map((s) => s.name), LEGEND.unmappedLabel];
    expect(names).toHaveLength(8);
    for (const name of names) expect(screen.getByTestId(`issues-status-pill-${name}`).textContent).toBe(name);
    expect(within(screen.getByRole("group", { name: "狀態快篩" })).getAllByRole("button")).toHaveLength(8);
    expect(Array.from(screen.getByTestId("issues-filter-source").querySelectorAll("option")).map((o) => o.textContent)).toEqual(["全部", "使用者提案", "系統缺陷", "研究提案", "系統改善", "未歸類"]);
    expect(screen.getByTestId("issues-filter-keyword")).toBeInTheDocument();
    expect(rowIds().slice(0, 2)).toEqual(DECIDE);

    // 狀態 pill：選一顆只留該狀態、再按一次取消；表外值用「未歸類」
    await user.click(screen.getByTestId("issues-status-pill-延後"));
    expect(rowIds()).toEqual(["OBS-SI-003"]);
    expect(screen.getByTestId("issues-status-pill-延後")).toHaveAttribute("aria-pressed", "true");
    await user.click(screen.getByTestId("issues-status-pill-延後"));
    expect(rowIds()).toHaveLength(18);
    await user.click(screen.getByTestId("issues-status-pill-未歸類"));
    expect(rowIds()).toEqual(["DEF-999-004"]);
    await user.click(screen.getByTestId("issues-status-pill-未歸類"));

    // 來源下拉與關鍵字
    await user.selectOptions(screen.getByTestId("issues-filter-source"), "研究提案");
    expect(rowIds()).toEqual(["OBS-SI-011", "OBS-SI-004"]);
    await user.selectOptions(screen.getByTestId("issues-filter-source"), "未歸類");
    expect(rowIds()).toEqual(["DEF-999-004"]);
    await user.selectOptions(screen.getByTestId("issues-filter-source"), "全部");
    await user.type(screen.getByTestId("issues-filter-keyword"), "prop-si");
    expect(rowIds()).toEqual(["PROP-SI-004", "PROP-SI-005"]);
    // 狀態 pill 只屬於全部分頁：換分頁再換回來，選值被清掉（關鍵字是全域的，先清掉免得待處理分頁沒有符合的列）
    await user.click(screen.getByTestId("issues-status-pill-待您決定"));
    expect(rowIds()).toEqual(["PROP-SI-004"]);
    await user.clear(screen.getByTestId("issues-filter-keyword"));
    await goTo(user, "待處理");
    await goTo(user, "全部");
    await waitFor(() => expect(rowIds()).toHaveLength(18));
    expect(screen.getByTestId("issues-status-pill-待您決定")).toHaveAttribute("aria-pressed", "false");
  });

  it("AT_IC_08_8_E_1 分頁真的沒有議題＝「這個分頁目前沒有議題」（與錯誤整片顯示不同）；關鍵字為不分大小寫（ASCII）子字串、比對編號與標題、只篩已載入的頁；空白關鍵字＝不篩", async () => {
    // 分頁真的沒有議題：只有已結案的議題，待處理分頁是空的
    const empty = await open({ stub: stubOf([makeIssue("DEF-999-201", { status: "已完成", result: "已修復", rankable: false })]) });
    expect(await screen.findByTestId("issues-empty")).toHaveTextContent("這個分頁目前沒有議題");
    expect(screen.queryByTestId("issues-error-panel")).toBeNull();
    expect(screen.queryByTestId("issues-table")).toBeNull();
    expect(summaryText("pending")).toBe("待處理 0"); // 量得到的 0，不是「—」
    empty.unmount();

    // 關鍵字語意
    const { user } = await open();
    await goTo(user, "全部");
    await waitFor(() => expect(rowIds()).toHaveLength(18));
    const input = screen.getByTestId("issues-filter-keyword");
    await user.type(input, "PrOp-Si-004");
    expect(rowIds()).toEqual(["PROP-SI-004"]);
    await user.clear(input);
    await user.type(input, "緊急的缺陷"); // 只出現在標題
    expect(rowIds()).toEqual(["OBS-SI-006"]);
    await user.clear(input);
    await user.type(input, "   "); // 空白關鍵字＝不篩
    expect(rowIds()).toHaveLength(18);
    await user.clear(input);
    await user.type(input, "不存在的字串");
    expect(await screen.findByTestId("issues-no-match")).toHaveTextContent("沒有符合目前篩選的議題");
    expect(screen.queryByTestId("issues-empty")).toBeNull();
  });

  it("AT_IC_08_8_E_1 列表只載入部分頁時輸入關鍵字：只篩已載入的頁並明說不完整；載入更多之後才會出現後面的項目", async () => {
    limits.pageSize = 5;
    limits.maxPages = 1; // 不自動續載：停在第一頁
    const { user } = await open();
    await goTo(user, "全部");
    await waitFor(() => expect(rowIds()).toHaveLength(5));
    expect(screen.getByTestId("issues-incomplete")).toHaveTextContent("已載入 5 件");
    await user.type(screen.getByTestId("issues-filter-keyword"), "DEF-999-005"); // 位置 18：在第四頁
    expect(await screen.findByTestId("issues-no-match")).toBeInTheDocument();
    expect(rowIds()).toEqual([]);
    // 一次載一頁（5、5、3 件）：每按一次，已載入件數隨之增加，說明仍在；最後一頁載入後說明消失、第 18 件出現
    for (const loaded of [10, 15]) {
      await user.click(screen.getByTestId("issues-load-more"));
      await waitFor(() => expect(screen.getByTestId("issues-incomplete")).toHaveTextContent(`已載入 ${loaded} 件`));
      expect(rowIds()).toEqual([]);
    }
    await user.click(screen.getByTestId("issues-load-more"));
    await waitFor(() => expect(rowIds()).toEqual(["DEF-999-005"]));
    expect(screen.queryByTestId("issues-incomplete")).toBeNull();
  });
});

// ── 嚴重度計件條與摘要列切換 ────────────────────────────────────────────────────────

describe("AT_IC_08_9 待處理的計件條與摘要列切換", () => {
  it("AT_IC_08_9_1 計件條六格（緊急、高、中、低、—、未歸類）加總＝待處理件數；點摘要列三數字之一切到對應分頁", async () => {
    const { user } = await open();
    await screen.findByTestId("issues-table");
    const cells = Object.fromEntries(["urgent", "high", "mid", "low", "none", "unmapped"].map((k) => [k, (screen.getByTestId(`issues-sev-${k}`).textContent ?? "").trim()]));
    expect(cells).toEqual({ urgent: "緊急 1", high: "高 2", mid: "中 0", low: "低 0", none: "— 1", unmapped: "未歸類 1" });
    const sum = Object.values(cells).reduce((n, text) => n + Number(text.replace(/\D+/g, "")), 0);
    expect(sum).toBe(rowIds().length);
    expect(sum).toBe(5);
    expect(summaryText("pending")).toBe("待處理 5");

    await user.click(screen.getByTestId("issues-summary-done"));
    await waitFor(() => expect(tabButton("已完成")).toHaveAttribute("aria-selected", "true"));
    await waitFor(() => expect(rowIds()).toEqual(DONE));
    expect(screen.queryByTestId("issues-severity-bar")).toBeNull(); // 計件條只在待處理
    await user.click(screen.getByTestId("issues-summary-decide"));
    await waitFor(() => expect(tabButton("待您決定")).toHaveAttribute("aria-selected", "true"));
    await waitFor(() => expect(rowIds()).toEqual(DECIDE));
    await user.click(screen.getByTestId("issues-summary-pending"));
    await waitFor(() => expect(tabButton("待處理")).toHaveAttribute("aria-selected", "true"));
    await waitFor(() => expect(rowIds()).toEqual(PENDING));
  });
});

// ── 已完成分頁的篩選 ────────────────────────────────────────────────────────────────

describe("AT_IC_08_10 已完成分頁：來源、結果與關鍵字取交集", () => {
  it("AT_IC_08_10_1 依來源下拉、結果快篩（選項＝legend.results）、關鍵字篩：三者取交集", async () => {
    const { user } = await open();
    await goTo(user, "已完成");
    expect(rowIds()).toEqual(DONE);
    const results = screen.getByTestId("issues-filter-result");
    expect(Array.from(results.querySelectorAll("option")).map((o) => o.textContent)).toEqual(["全部", ...LEGEND.results.map((r) => r.name)]);
    expect(LEGEND.results).toHaveLength(8);

    await user.selectOptions(screen.getByTestId("issues-filter-source"), "系統缺陷");
    expect(rowIds()).toEqual(["DEF-999-003", "DEF-999-002", "DEF-999-001"]);
    await user.selectOptions(results, "已退役");
    expect(rowIds()).toEqual(["DEF-999-001"]);
    await user.type(screen.getByTestId("issues-filter-keyword"), "退役");
    expect(rowIds()).toEqual(["DEF-999-001"]);
    await user.clear(screen.getByTestId("issues-filter-keyword"));
    await user.type(screen.getByTestId("issues-filter-keyword"), "xyz");
    expect(await screen.findByTestId("issues-no-match")).toBeInTheDocument();
    // 結果單獨篩（跨來源）：已採納只有一件
    await user.clear(screen.getByTestId("issues-filter-keyword"));
    await user.selectOptions(screen.getByTestId("issues-filter-source"), "全部");
    await user.selectOptions(results, "已採納");
    expect(rowIds()).toEqual(["OBS-SI-011"]);
    // 來源與結果都選但交集為空
    await user.selectOptions(screen.getByTestId("issues-filter-source"), "系統缺陷");
    expect(screen.queryByTestId("issues-table")).toBeNull();
    expect(screen.getByTestId("issues-no-match")).toBeInTheDocument();
  });

  it("AT_IC_08_10_E_1 清掉篩選回到全部已完成議題；結果快篩的選項隨 legend.results 改變（不寫死）", async () => {
    const first = await open();
    const { user } = first;
    await goTo(user, "已完成");
    await user.selectOptions(screen.getByTestId("issues-filter-result"), "已合併");
    expect(rowIds()).toEqual(["OBS-SI-002"]);
    await user.selectOptions(screen.getByTestId("issues-filter-result"), "全部");
    expect(rowIds()).toEqual(DONE);
    first.unmount();

    // legend 的一個結果改名：選項跟著變（新名在、舊名不在）
    const legend = clone(LEGEND);
    legend.results = legend.results.map((r) => (r.name === "已修復" ? { ...r, name: "已修好了" } : r));
    const renamed = await open({ stub: newStub({ legend }) });
    await goTo(renamed.user, "已完成");
    const options = Array.from(screen.getByTestId("issues-filter-result").querySelectorAll("option")).map((o) => o.textContent);
    expect(options).toContain("已修好了");
    expect(options).not.toContain("已修復");
    expect(options).toHaveLength(9);
  });
});

// ── 非 ADMIN 與優先順序顯示 ─────────────────────────────────────────────────────────

describe("AT_IC_09_9_1 非 ADMIN：看得到順位與備註、沒有編輯控制項、網路層無 PUT 與 DELETE", () => {
  it.each(["VIEWER", "OPERATOR"] as const)("AT_IC_09_9_1 %s 開頁：順位與備註照常顯示並影響列序；沒有排序鈕、沒有寫入請求", async (role) => {
    const stub = newStub();
    stub.priorities.set("OBS-SI-006", { rank: 2, note: "備註一" });
    stub.priorities.set("OBS-SI-007", { rank: 1, note: "備註二" });
    const { user } = await open({ role, stub });
    await screen.findByTestId("issues-table");
    expect(rowIds()).toEqual(["OBS-SI-007", "OBS-SI-006", "DEF-999-005", "OBS-SI-008", "OBS-SI-009"]);
    expect(screen.getByTestId("issue-priority-OBS-SI-007").textContent).toBe("1");
    expect(screen.getByTestId("issue-priority-note-OBS-SI-007").textContent).toBe("備註二");
    expect(screen.getByTestId("issue-priority-OBS-SI-006").textContent).toBe("2");
    expect(screen.queryByRole("button", { name: /^排序/ })).toBeNull();
    expect(screen.queryByTestId("issue-priority-dialog")).toBeNull();
    // 開詳情也不產生寫入
    await user.click(screen.getByRole("button", { name: "OBS-SI-006" }));
    await screen.findByTestId("issue-detail-raw");
    expect(stub.calls.filter((c) => c.method !== "GET")).toEqual([]);
  });
});

// ── 決定與關閉按鈕 ─────────────────────────────────────────────────────────────────

describe("AT_IC_10 待您決定的按鈕（僅 ADMIN）", () => {
  it("AT_IC_10_1_1 提案列「決定」：先 getSiProposal 取快照，再開 SiDecideDialog（綁快照的 digest）；送出走 POST /api/v1/si/proposals/{id}/decide", async () => {
    const { user, stub } = await open({ role: "ADMIN" });
    await goTo(user, "待您決定");
    stub.calls.length = 0;
    await user.click(screen.getByTestId("issue-decide-PROP-SI-004"));
    const dialog = await screen.findByTestId("si-decide-dialog");
    // 先取快照（GET 提案單筆），後開對話框
    expect(stub.calls.map((c) => `${c.method} ${c.path}`)).toEqual(["GET /api/v1/si/proposals/PROP-SI-004"]);
    expect(within(dialog).getByTestId("si-decide-digest")).toHaveAttribute("title", PROPOSAL.digest);
    await user.selectOptions(within(dialog).getByTestId("si-decide-verb"), "approve");
    await user.click(within(dialog).getByTestId("si-decide-submit"));
    await within(dialog).findByTestId("si-decide-result");
    const decide = stub.calls.find((c) => c.method === "POST");
    expect(decide?.path).toBe("/api/v1/si/proposals/PROP-SI-004/decide");
    expect(JSON.parse(decide?.body ?? "{}")).toEqual({ dkind: "approve", digest: PROPOSAL.digest });
  });

  it("AT_IC_10_1_1 closed 的提案：對話框的動詞只有「回滾」", async () => {
    const stub = newStub({
      overrides: {
        proposal: () => ({
          data: { schemaRev: 1, kind: "proposals", generatedAt: "t", headSha: null, items: [{ ...PROPOSAL, state: "closed" }], nextSince: null, truncated: false, ne: [], problems: [] },
        }),
      },
    });
    const { user } = await open({ role: "ADMIN", stub });
    await goTo(user, "待您決定");
    await user.click(screen.getByTestId("issue-decide-PROP-SI-004"));
    const select = within(await screen.findByTestId("si-decide-dialog")).getByTestId("si-decide-verb");
    expect(Array.from(select.querySelectorAll("option")).map((o) => o.textContent)).toEqual(["請選擇動詞", "回滾"]);
  });

  it("AT_IC_10_1_E_1 getSiProposal 失敗：不開對話框、顯示錯誤；對話框的 digest 取自點擊當下的快照（不是清單項、也不是上一次的快照）", async () => {
    const other = `sha256:${"b".repeat(64)}`;
    let mode: "fail" | "other" | "default" = "fail";
    const stub = newStub({
      overrides: {
        proposal: () => {
          if (mode === "fail") return unavailable("nonzero_rc", "rc=2; stderr=boom");
          if (mode === "other")
            return { data: { schemaRev: 1, kind: "proposals", generatedAt: "t", headSha: null, items: [{ ...PROPOSAL, digest: other }], nextSince: null, truncated: false, ne: [], problems: [] } };
          return undefined;
        },
      },
    });
    const { user } = await open({ role: "ADMIN", stub });
    await goTo(user, "待您決定");
    await user.click(screen.getByTestId("issue-decide-PROP-SI-004"));
    expect(await screen.findByText(/無法取得提案快照/)).toBeInTheDocument();
    expect(screen.queryByTestId("si-decide-dialog")).toBeNull();
    expect(stub.calls.filter((c) => c.method === "POST")).toEqual([]);
    await waitFor(() => expect(screen.getByTestId("issue-decide-PROP-SI-004")).toHaveTextContent("決定"));

    // 快照換了一份（卡面 digest 變了）：對話框綁的是這一次取到的
    mode = "other";
    await user.click(screen.getByTestId("issue-decide-PROP-SI-004"));
    const first = await screen.findByTestId("si-decide-dialog");
    expect(within(first).getByTestId("si-decide-digest")).toHaveAttribute("title", other);
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("si-decide-dialog")).toBeNull());
    mode = "default";
    await user.click(screen.getByTestId("issue-decide-PROP-SI-004"));
    expect(within(await screen.findByTestId("si-decide-dialog")).getByTestId("si-decide-digest")).toHaveAttribute("title", PROPOSAL.digest);
  });

  it("AT_IC_10_2_1 觀察列「關閉並裁決」：開 SiObsCloseDialog（target＝該觀察號），送出走 POST /api/v1/si/observations/{id}/close", async () => {
    const { user, stub } = await open({ role: "ADMIN" });
    await goTo(user, "待您決定");
    await user.click(screen.getByTestId("issue-close-OBS-SI-005"));
    const dialog = await screen.findByTestId("si-obs-close-dialog");
    expect(dialog).toHaveAccessibleName("關閉觀察：OBS-SI-005");
    await user.selectOptions(within(dialog).getByTestId("si-close-terminal"), "decided");
    await user.type(within(dialog).getByTestId("si-close-text"), "夾具關閉");
    await user.click(within(dialog).getByTestId("si-close-submit"));
    await within(dialog).findByTestId("si-close-result");
    const close = stub.calls.find((c) => c.method === "POST");
    expect(close?.path).toBe("/api/v1/si/observations/OBS-SI-005/close");
    expect(JSON.parse(close?.body ?? "{}")).toEqual({ terminal: "decided", text: "夾具關閉" });
  });

  it("AT_IC_10_2_E_1 觀察列沒有「決定」鈕、提案列沒有「關閉並裁決」鈕；action 為 null 的列沒有任何按鈕", async () => {
    const { user } = await open({ role: "ADMIN" });
    await goTo(user, "全部");
    await waitFor(() => expect(rowIds()).toHaveLength(18));
    expect(within(row("OBS-SI-005")).queryByTestId("issue-decide-OBS-SI-005")).toBeNull();
    expect(within(row("OBS-SI-005")).getByTestId("issue-close-OBS-SI-005")).toBeInTheDocument();
    expect(within(row("PROP-SI-004")).queryByTestId("issue-close-PROP-SI-004")).toBeNull();
    expect(within(row("PROP-SI-004")).getByTestId("issue-decide-PROP-SI-004")).toBeInTheDocument();
    for (const id of ALL.filter((i) => !DECIDE.includes(i))) {
      expect(within(row(id)).queryByTestId(`issue-decide-${id}`), id).toBeNull();
      expect(within(row(id)).queryByTestId(`issue-close-${id}`), id).toBeNull();
      expect(within(row(id)).queryByTestId(`issue-admin-only-${id}`), id).toBeNull();
    }
    expect(screen.getAllByRole("button", { name: /^決定 / })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: /^關閉並裁決 / })).toHaveLength(1);
  });

  it("AT_IC_10_4_1 簽章成功（201 receipt）但帳本尚未入帳：重新整理後該列仍在待您決定（狀態只跟帳本走）", async () => {
    const { user, stub } = await open({ role: "ADMIN" });
    await goTo(user, "待您決定");
    await user.click(screen.getByTestId("issue-decide-PROP-SI-004"));
    const dialog = await screen.findByTestId("si-decide-dialog");
    await user.selectOptions(within(dialog).getByTestId("si-decide-verb"), "approve");
    await user.click(within(dialog).getByTestId("si-decide-submit"));
    await within(dialog).findByTestId("si-decide-result");
    // 簽章成功的當下：列不動、狀態文字不變、沒有為此多打議題清單請求
    const listsBefore = listCalls(stub).length;
    expect(rowIds()).toEqual(DECIDE);
    expect(cell("PROP-SI-004", 4).textContent).toBe("待您決定");
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("si-decide-dialog")).toBeNull());
    expect(listCalls(stub)).toHaveLength(listsBefore);
    // 重新整理：帳本沒變（尚未入帳）→ 仍在待您決定
    await user.click(screen.getByTestId("issues-refresh"));
    await waitFor(() => expect(listCalls(stub)).toHaveLength(listsBefore + 1));
    await waitFor(() => expect(rowIds()).toEqual(DECIDE));
    expect(cell("PROP-SI-004", 4).textContent).toBe("待您決定");
    expect(within(row("PROP-SI-004")).getByTestId("issue-decide-PROP-SI-004")).toBeInTheDocument();
  });

  it("AT_IC_10_4_E_1 入帳後（第二次載入回新狀態）列移到新狀態；簽章成功當下列不樂觀移動（狀態文字不變）", async () => {
    const { user, stub } = await open({ role: "ADMIN" });
    await goTo(user, "全部");
    await waitFor(() => expect(rowIds()).toHaveLength(18));
    expect(rowIds().slice(0, 2)).toEqual(DECIDE);
    await user.click(screen.getByTestId("issue-decide-PROP-SI-004"));
    const dialog = await screen.findByTestId("si-decide-dialog");
    await user.selectOptions(within(dialog).getByTestId("si-decide-verb"), "approve");
    await user.click(within(dialog).getByTestId("si-decide-submit"));
    await within(dialog).findByTestId("si-decide-result");
    // 簽章成功的當下：狀態文字不變、仍置頂
    expect(cell("PROP-SI-004", 4).textContent).toBe("待您決定");
    expect(within(row("PROP-SI-004")).getByTestId("issue-top-pinned")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("si-decide-dialog")).toBeNull());
    // 入帳（假後端的帳本換了新狀態）後重新整理：列換成新狀態、不再置頂、不再有決定鈕
    const item = stub.items.find((i) => i.id === "PROP-SI-004");
    if (!item) throw new Error("夾具缺 PROP-SI-004");
    item.status = "進行中";
    item.action = null;
    item.nextStep = "已核准，等沙盒套用";
    await user.click(screen.getByTestId("issues-refresh"));
    await waitFor(() => expect(cell("PROP-SI-004", 4).textContent).toBe("進行中"));
    expect(within(row("PROP-SI-004")).queryByTestId("issue-top-pinned")).toBeNull();
    expect(within(row("PROP-SI-004")).queryByTestId("issue-decide-PROP-SI-004")).toBeNull();
    expect(rowIds().slice(0, 1)).toEqual(["OBS-SI-005"]);
  });

  it("AT_IC_10_5_1 非 ADMIN 開待您決定分頁：待您決定的列顯示「需要 ADMIN 角色才能操作」且沒有按鈕；網路層零寫入請求、也不取提案快照", async () => {
    const { user, stub } = await open({ role: "VIEWER" });
    await goTo(user, "待您決定");
    for (const id of DECIDE) expect(within(row(id)).getByTestId(`issue-admin-only-${id}`).textContent).toBe("需要 ADMIN 角色才能操作");
    expect(screen.queryByRole("button", { name: /^決定 / })).toBeNull();
    expect(screen.queryByRole("button", { name: /^關閉並裁決 / })).toBeNull();
    expect(screen.queryByTestId("si-decide-dialog")).toBeNull();
    expect(stub.calls.filter((c) => c.method !== "GET")).toEqual([]);
    expect(stub.calls.filter((c) => c.path.startsWith("/api/v1/si/"))).toEqual([]);
  });

  it.each([
    ["ADMIN", true],
    ["VIEWER", false],
    ["OPERATOR", false],
  ] as const)("AT_IC_10_5_E_1 %s：按鈕與「需要 ADMIN 角色」提示的有無（ADMIN 顯示按鈕且不顯示該提示；VIEWER、OPERATOR 皆視為非 ADMIN）", async (role, admin) => {
    const { user } = await open({ role });
    await goTo(user, "待您決定");
    expect(screen.queryByTestId("issue-decide-PROP-SI-004") !== null).toBe(admin);
    expect(screen.queryByTestId("issue-close-OBS-SI-005") !== null).toBe(admin);
    expect(screen.queryByTestId("issue-admin-only-PROP-SI-004") !== null).toBe(!admin);
    expect(screen.queryByTestId("issue-admin-only-OBS-SI-005") !== null).toBe(!admin);
    expect(screen.queryAllByText("需要 ADMIN 角色才能操作").length > 0).toBe(!admin);
  });
});

// ── 不快取與鍵盤 ────────────────────────────────────────────────────────────────────

describe("AT_IC_12 非功能", () => {
  it("AT_IC_12_3_E_1 進頁與按「重新整理」各重取一次（沒有快取命中）；整頁失敗後重新整理能復原", async () => {
    const { user, stub } = await open();
    await screen.findByTestId("issues-table");
    expect(listCalls(stub)).toHaveLength(1);
    await user.click(screen.getByTestId("issues-refresh"));
    await waitFor(() => expect(listCalls(stub)).toHaveLength(2));
    await user.click(screen.getByTestId("issues-refresh"));
    await waitFor(() => expect(listCalls(stub)).toHaveLength(3));
    expect(listCalls(stub).map((c) => c.query.get("status"))).toEqual(["待處理", "待處理", "待處理"]);
    // 重新整理反映新內容（不快取）
    stub.items.push(makeIssue("DEF-999-301", { severityRank: 1, updatedAt: "2026-10-01" }));
    await user.click(screen.getByTestId("issues-refresh"));
    await waitFor(() => expect(rowIds()).toContain("DEF-999-301"));
    expect(summaryText("pending")).toBe("待處理 6");
  });

  it("AT_IC_12_5_1 只用鍵盤：方向鍵切分頁、Enter 開詳情並以 Esc 收起（焦點還給編號鈕）；ADMIN 可開排序與決定對話框並以 Esc 關閉、焦點回到觸發鈕", async () => {
    const { user } = await open({ role: "ADMIN" });
    await screen.findByTestId("issues-table");
    // PillTabs：方向鍵切換並移動焦點
    act(() => tabButton("待處理").focus());
    await user.keyboard("{ArrowRight}");
    await waitFor(() => expect(tabButton("待您決定")).toHaveAttribute("aria-selected", "true"));
    expect(tabButton("待您決定")).toHaveFocus();
    await user.keyboard("{Home}");
    await waitFor(() => expect(tabButton("待處理")).toHaveAttribute("aria-selected", "true"));
    await screen.findByTestId("issues-table");
    await waitFor(() => expect(rowIds()).toEqual(PENDING));

    // 清單列：編號鈕 Enter 開詳情（焦點移進面板）、Esc 收起並還焦點
    const opener = screen.getByRole("button", { name: "OBS-SI-006" });
    act(() => opener.focus());
    await user.keyboard("{Enter}");
    const detail = await screen.findByTestId("issue-detail");
    await waitFor(() => expect(detail).toHaveFocus());
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("issue-detail")).toBeNull());
    expect(opener).toHaveFocus();

    // 排序對話框：Enter 開、Esc 關、焦點回到「排序」鈕
    const rank = screen.getByRole("button", { name: "排序 OBS-SI-006" });
    act(() => rank.focus());
    await user.keyboard("{Enter}");
    await screen.findByTestId("issue-priority-dialog");
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("issue-priority-dialog")).toBeNull());
    expect(rank).toHaveFocus();

    // 決定對話框（待您決定分頁）：Enter 開（取快照之後）、Esc 關、焦點回到「決定」鈕
    await goTo(user, "待您決定");
    const decide = screen.getByRole("button", { name: "決定 PROP-SI-004" });
    act(() => decide.focus());
    await user.keyboard("{Enter}");
    await screen.findByTestId("si-decide-dialog");
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("si-decide-dialog")).toBeNull());
    expect(decide).toHaveFocus();
    // 關閉觀察對話框
    const close = screen.getByRole("button", { name: "關閉並裁決 OBS-SI-005" });
    act(() => close.focus());
    await user.keyboard("{Enter}");
    await screen.findByTestId("si-obs-close-dialog");
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("si-obs-close-dialog")).toBeNull());
    expect(close).toHaveFocus();
  });
});

describe("頁面骨架與狀態說明", () => {
  it("標題、說明鈕與重新整理鈕；載入完成前「狀態說明」停用，載入後可開；載入中顯示「載入中」", async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const { user } = await open({ stub: newStub({ overrides: { list: () => gate.then(() => undefined) } }) });
    expect(screen.getByRole("heading", { level: 1, name: "議題中心" })).toBeInTheDocument();
    expect(await screen.findByTestId("issues-loading")).toHaveTextContent("議題載入中…");
    expect(screen.getByTestId("issues-legend-open")).toBeDisabled();
    expect(summaryText("pending")).toBe("待處理 —");
    await act(async () => release());
    await screen.findByTestId("issues-table");
    expect(screen.getByTestId("issues-legend-open")).toBeEnabled();
    await user.click(screen.getByTestId("issues-legend-open"));
    expect(await screen.findByTestId("issues-legend-dialog")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("issues-legend-dialog")).toBeNull());
    expect(screen.getByTestId("issues-legend-open")).toHaveFocus();
  });

  it("欄位值為 null 的議題照常成列（來源、嚴重度、日期各顯示「—」），關鍵字仍以編號找得到", async () => {
    const stub = stubOf([makeIssue("DEF-999-401", { source: null, severity: null, severityRank: null, updatedAt: null })]);
    await open({ stub });
    await screen.findByTestId("issues-table");
    expect(
      within(row("DEF-999-401"))
        .getAllByRole("cell")
        .map((c) => c.textContent),
    ).toEqual(["DEF-999-401", "—", "DEF-999-401 的標題", "—", "待解", "—", "—", "已成立，尚無人接手"]);
    fireEvent.change(screen.getByTestId("issues-filter-keyword"), { target: { value: "DEF-999-401" } });
    expect(rowIds()).toEqual(["DEF-999-401"]);
  });
});
