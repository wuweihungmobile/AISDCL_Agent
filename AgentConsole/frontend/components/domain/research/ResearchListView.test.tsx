import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import path from "node:path";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ResearchPage, { metadata as listPageMetadata } from "@/app/research/page";
import type { ResearchProjectSummary, Role } from "@/lib/api/types";
import { DEFAULT_APPLICABILITY_AXES, READONLY_TITLE, SLUG_PATTERN, type ProjectBadgeId } from "@/lib/domain/research";
import { R1, R2, R3, T1, T2 } from "@/tests/fixtures/research/ids";
import { CAPABILITIES_LOCAL } from "@/tests/fixtures/research/misc";
import { PROJECT_LIST, SUMMARY_R1 } from "@/tests/fixtures/research/projects";
import { callsOf, failure, renderResearch, stubResearchApi, writeCalls } from "@/tests/helpers/research";
import { contrastRatio, tokenHex } from "@/tests/helpers/tokens";
import { ResearchListView } from "./ResearchListView";

/**
 * 研究專案清單頁（TCS-ResearchToPRD-P0-20261102 AT-960-19-1、19-2；AC-R2P-01-10、21-4、03-2）：
 * 空狀態與新建入口、VIEWER 停用而不隱藏、不自動跳轉（Console PRD §0.8 的靜默退回教訓）、每列內容、清單三態、篩選、封存與復原；
 * 新建對話框的 zod 驗證、代號自動產生、檢索深度三值、Web 層停用、合法送出的本文形狀、後端錯誤對應回欄位。
 * 判定指令：npx vitest run components/domain/research/ResearchListView.test.tsx -t "<AT 底線形>"
 */
const nav = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: nav.push, replace: nav.replace, back: vi.fn() }),
  usePathname: () => "/research",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

type StubPatch = Parameters<typeof stubResearchApi>[0];

const R4 = "44444444-4444-4444-8444-444444444444";
const ARCHIVED = { ...SUMMARY_R1, id: R4, rpNo: "RP-0004", slug: "old-topic", title: "舊的研究", archivedAt: T1 };
const NEW_ID = "99999999-9999-4999-8999-999999999999";
const PROJECTS_PATH = /^\/api\/v1\/research\/projects$/;

beforeEach(() => {
  nav.push.mockClear();
  nav.replace.mockClear();
});

function renderList(role: Role = "OPERATOR", stub: StubPatch = {}, props: { extraActions?: ReactNode } = {}) {
  const api = stubResearchApi(stub);
  const view = renderResearch(<ResearchListView {...props} />, role);
  return { ...view, ...api };
}

const createButton = () => screen.getByRole("button", { name: "新建研究專案" });

describe("AT_960_19_1 清單：空狀態、新建入口、VIEWER 停用、每列內容、三態", () => {
  it("AT_960_19_1 零研究專案（OPERATOR）：標題「研發工作流」、空狀態「還沒有任何研究專案」、按鈕「新建研究專案」可按；沒有列、沒有篩選列；不自動跳轉、不送任何寫入", async () => {
    const { calls } = renderList("OPERATOR", { projects: [] });
    expect(await screen.findByText("還沒有任何研究專案")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "研發工作流" })).toBeInTheDocument();
    expect(createButton()).toBeEnabled();
    expect(createButton()).not.toHaveAttribute("title");
    expect(screen.queryByTestId("research-row")).toBeNull();
    expect(screen.queryByRole("textbox", { name: "搜尋研究專案" }), "沒有研究專案時不顯示篩選列").toBeNull();
    expect(screen.getByText("按右上「新建研究專案」，輸入研究命題後開始。")).toBeInTheDocument();
    // 空狀態另有通往「已封存」的入口，但「新建研究專案」只有標題列那一顆（getByRole 會在重名時丟錯）
    expect(screen.getByRole("button", { name: "查看已封存的研究專案" })).toBeEnabled();
    expect(nav.push, "零研究專案不自動跳轉").not.toHaveBeenCalled();
    expect(nav.replace, "零研究專案不退回他頁").not.toHaveBeenCalled();
    expect(writeCalls(calls)).toEqual([]);
    expect(
      callsOf(calls, "GET", PROJECTS_PATH).filter((c) => c.query.has("archived")),
      "進頁不請求已封存的那一份",
    ).toEqual([]);
  });

  it("AT_960_19_1 零研究專案（VIEWER）：按鈕仍在（停用而不隱藏）、disabled 且 title 為「權限不足（唯讀角色）」；點它不會開對話框", async () => {
    const user = userEvent.setup();
    renderList("VIEWER", { projects: [] });
    await screen.findByText("還沒有任何研究專案");
    expect(createButton()).toBeDisabled();
    expect(createButton()).toHaveAttribute("title", "權限不足（唯讀角色）");
    expect(READONLY_TITLE).toBe("權限不足（唯讀角色）");
    await user.click(createButton());
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(nav.push).not.toHaveBeenCalled();
    expect(nav.replace).not.toHaveBeenCalled();
  });

  it("AT_960_19_1 有資料：每列含 RP 編號、命題摘要、當前步驟的迷你步驟列、狀態徽章、帶時區的更新時間、主連結「繼續（第 k 步：名稱）」直達 /research/<id>；沒有任何導向呼叫", async () => {
    renderList();
    const rows = await screen.findAllByTestId("research-row");
    expect(rows).toHaveLength(3);
    expect(screen.getByText("共 3 個研究專案", { exact: false })).toBeInTheDocument();
    const expected = [
      { id: R1, rp: "RP-0001", title: "Agent 記憶體回收策略研究", badge: "進行中", states: ["CURRENT", "TODO", "TODO", "TODO", "TODO"], updated: T2, link: "繼續（第 1 步：研究）" },
      { id: R2, rp: "RP-0002", title: "向量資料庫選型", badge: "進行中", states: ["DONE", "CURRENT", "TODO", "TODO", "TODO"], updated: T2, link: "繼續（第 2 步：規格工作室）" },
      { id: R3, rp: "RP-0003", title: "RAG 評測基準", badge: "Gate 0 已核准", states: ["DONE", "DONE", "CURRENT", "TODO", "TODO"], updated: T1, link: "繼續（第 3 步：分流）" },
    ];
    rows.forEach((row, i) => {
      const want = expected[i];
      expect(row).toHaveAttribute("data-research-id", want.id);
      expect(within(row).getByText(want.rp)).toBeInTheDocument();
      expect(within(row).getByText(want.title)).toBeInTheDocument();
      expect(within(row).getByTestId("research-badge")).toHaveTextContent(want.badge);
      const mini = within(row).getByRole("list", { name: `${want.rp} 的步驟` });
      const items = within(mini).getAllByRole("listitem");
      expect(items).toHaveLength(5);
      expect(items.map((item) => item.getAttribute("data-state"))).toEqual(want.states);
      const time = row.querySelector("time");
      expect(time, "每列有更新時間").not.toBeNull();
      expect(time).toHaveAttribute("datetime", want.updated);
      expect(time?.textContent, "時間帶時區，不顯示 naive 時間").toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC[+-]\d{2}:\d{2}$/);
      const link = within(row).getByRole("link", { name: want.link });
      expect(link).toHaveAttribute("href", `/research/${want.id}`);
    });
    expect(nav.push).not.toHaveBeenCalled();
    expect(nav.replace).not.toHaveBeenCalled();
  });

  it("AT_960_19_1 清單三態之一，載入中：顯示骨架（aria-busy），沒有空狀態也沒有列；新建入口照常", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>(() => {})),
    );
    renderResearch(<ResearchListView />);
    expect(screen.getByLabelText("研究專案清單載入中")).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByText("還沒有任何研究專案")).toBeNull();
    expect(screen.queryByTestId("research-row")).toBeNull();
    expect(createButton()).toBeEnabled();
  });

  it("AT_960_19_1 清單三態之二，錯誤：顯示原因（含後端的 reason）與「重試」；重試後清單出現", async () => {
    const user = userEvent.setup();
    let broken = true;
    renderList("OPERATOR", {
      overrides: (c) => (broken && c.method === "GET" && c.path === "/api/v1/research/projects" ? failure(503, { message: "Bridge 不可用", reason: "bridge_unreachable" }) : undefined),
    });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("無法載入研究專案清單");
    expect(alert).toHaveTextContent("Bridge 不可用：bridge_unreachable");
    expect(screen.queryByText("還沒有任何研究專案"), "失敗不能被當成空清單").toBeNull();
    broken = false;
    await user.click(within(alert).getByRole("button", { name: "重試" }));
    expect(await screen.findAllByTestId("research-row")).toHaveLength(3);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("AT_960_19_1 清單三態之三，資料：已封存的專案預設不列；「新建研究專案」入口與外部接入的動作（extraActions）同在標題列，外部動作在前", async () => {
    renderList("ADMIN", { projects: [...PROJECT_LIST, ARCHIVED] }, { extraActions: <button type="button">研究來源設定</button> });
    expect(await screen.findAllByTestId("research-row")).toHaveLength(3);
    expect(screen.queryByText("舊的研究")).toBeNull();
    const extra = screen.getByRole("button", { name: "研究來源設定" });
    expect(extra.compareDocumentPosition(createButton()) & Node.DOCUMENT_POSITION_FOLLOWING, "外部動作排在新建鈕之前").toBeTruthy();
  });

  it("AT_960_19_1 清單頁自己從不導向：原始碼只有「新建成功」一處 router.push，沒有 router.replace、redirect()（零專案靜默退回他頁的設計教訓）", () => {
    const source = readFileSync(path.join(process.cwd(), "components", "domain", "research", "ResearchListView.tsx"), "utf-8");
    expect(source.match(/router\.push\(/g)).toHaveLength(1);
    expect(source).not.toMatch(/router\.replace\(|redirect\(/);
  });
});

describe("AT_960_19_1 篩選與搜尋（全在已載入的清單上做）", () => {
  it("AT_960_19_1 搜尋：比對 RP 編號、名稱與代號，不分大小寫；沒有符合時顯示「沒有符合條件的研究專案」，清掉搜尋回到全部", async () => {
    // 逐字輸入多組搜尋字再清除：userEvent 預設每個動作之間等一個巨集任務（delay: 0），同機高負載時累積超過 vitest 預設 5 秒單案上限而偶發逾時；
    // 沒有真實時序要等，所以關掉動作間等待並放寬單案上限到 30 秒，斷言不變。
    const user = userEvent.setup({ delay: null });
    renderList();
    await screen.findAllByTestId("research-row");
    const search = screen.getByRole("textbox", { name: "搜尋研究專案" });
    await user.type(search, "向量");
    expect((await screen.findAllByTestId("research-row")).map((r) => r.getAttribute("data-research-id"))).toEqual([R2]);
    await user.clear(search);
    await user.type(search, "rp-0003");
    expect(screen.getAllByTestId("research-row").map((r) => r.getAttribute("data-research-id"))).toEqual([R3]);
    await user.clear(search);
    await user.type(search, "AGENT-MEMORY");
    expect(
      screen.getAllByTestId("research-row").map((r) => r.getAttribute("data-research-id")),
      "代號 agent-memory-gc 不分大小寫",
    ).toEqual([R1]);
    await user.clear(search);
    await user.type(search, "agent-memory");
    expect(screen.getAllByTestId("research-row").map((r) => r.getAttribute("data-research-id"))).toEqual([R1]);
    await user.clear(search);
    await user.type(search, "完全不存在的字");
    expect(await screen.findByText("沒有符合條件的研究專案")).toBeInTheDocument();
    expect(screen.getByText("調整篩選條件或清除搜尋看看。")).toBeInTheDocument();
    expect(screen.queryByText("還沒有任何研究專案")).toBeNull();
    await user.clear(search);
    expect(await screen.findAllByTestId("research-row")).toHaveLength(3);
  }, 30_000);

  it("AT_960_19_1 狀態與步驟篩選：選「Gate 0 已核准」只剩 R3、選步驟「研究」只剩 R1；兩者疊加取交集", async () => {
    const user = userEvent.setup();
    renderList();
    await screen.findAllByTestId("research-row");
    const status = screen.getByRole("combobox", { name: "狀態篩選" });
    const step = screen.getByRole("combobox", { name: "步驟篩選" });
    await user.selectOptions(status, "frozen");
    expect(screen.getAllByTestId("research-row").map((r) => r.getAttribute("data-research-id"))).toEqual([R3]);
    await user.selectOptions(status, "all");
    await user.selectOptions(step, "topic");
    expect(screen.getAllByTestId("research-row").map((r) => r.getAttribute("data-research-id"))).toEqual([R1]);
    await user.selectOptions(status, "frozen");
    expect(await screen.findByText("沒有符合條件的研究專案"), "R1 在第 1 步、不是 Gate 0 已核准：交集為空").toBeInTheDocument();
  });

  it("AT_960_19_1 狀態篩選「已封存」才看得到封存的專案：選到才另外請求 ?archived=true 那一份（後端清單預設不含已封存）；列只有「復原」、沒有「封存」", async () => {
    const user = userEvent.setup();
    const { calls } = renderList("OPERATOR", { projects: [...PROJECT_LIST, ARCHIVED] });
    await screen.findAllByTestId("research-row");
    expect(
      callsOf(calls, "GET", PROJECTS_PATH).filter((c) => c.query.has("archived")),
      "進頁只抓未封存的那一份",
    ).toEqual([]);
    await user.selectOptions(screen.getByRole("combobox", { name: "狀態篩選" }), "archived");
    const restoreButton = await screen.findByRole("button", { name: "復原 RP-0004" });
    const rows = screen.getAllByTestId("research-row");
    expect(rows.map((r) => r.getAttribute("data-research-id"))).toEqual([R4]);
    expect(within(rows[0]).getByTestId("research-badge")).toHaveTextContent("已封存");
    expect(restoreButton).toBeEnabled();
    expect(within(rows[0]).queryByRole("button", { name: "封存 RP-0004" })).toBeNull();
    expect(callsOf(calls, "GET", PROJECTS_PATH).filter((c) => c.query.get("archived") === "true")).toHaveLength(1);
    // 切回「全部狀態」：又是未封存的那一份（不再顯示已封存的專案）
    await user.selectOptions(screen.getByRole("combobox", { name: "狀態篩選" }), "all");
    await waitFor(() => expect(screen.getAllByTestId("research-row").map((r) => r.getAttribute("data-research-id"))).toEqual([R1, R2, R3]));
    expect(screen.queryByText("舊的研究")).toBeNull();
  });

  it("AT_960_19_1 已封存那一份載入失敗：顯示原因與重試、篩選列仍在（能切回全部狀態）；重試成功後列出已封存的專案", async () => {
    const user = userEvent.setup();
    let broken = true;
    renderList("OPERATOR", {
      projects: [...PROJECT_LIST, ARCHIVED],
      overrides: (c) =>
        broken && c.method === "GET" && c.path === "/api/v1/research/projects" && c.query.get("archived") === "true"
          ? failure(503, { message: "Bridge 不可用", reason: "bridge_unreachable" })
          : undefined,
    });
    await screen.findAllByTestId("research-row");
    await user.selectOptions(screen.getByRole("combobox", { name: "狀態篩選" }), "archived");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("無法載入研究專案清單");
    expect(screen.getByRole("combobox", { name: "狀態篩選" }), "篩選列不因這一份失敗而消失").toBeInTheDocument();
    broken = false;
    await user.click(within(alert).getByRole("button", { name: "重試" }));
    expect(await screen.findByRole("button", { name: "復原 RP-0004" })).toBeInTheDocument();
  });

  it("AT_960_19_1 只有已封存的專案（沒有任何未封存的）：空狀態的「查看已封存的研究專案」進同一個篩選，列出已封存的專案、篩選列此時出現；選回「全部狀態」又回到空狀態", async () => {
    const user = userEvent.setup();
    renderList("OPERATOR", { projects: [ARCHIVED] });
    expect(await screen.findByText("還沒有任何研究專案")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "狀態篩選" }), "未封存的都沒有時篩選列不出現").toBeNull();
    await user.click(screen.getByRole("button", { name: "查看已封存的研究專案" }));
    expect(await screen.findByRole("button", { name: "復原 RP-0004" })).toBeInTheDocument();
    const status = screen.getByRole("combobox", { name: "狀態篩選" });
    expect(status).toHaveValue("archived");
    expect(screen.queryByText("還沒有任何研究專案")).toBeNull();
    await user.selectOptions(status, "all");
    expect(await screen.findByText("還沒有任何研究專案")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "狀態篩選" })).toBeNull();
  });

  it("AT_960_19_1 已封存那一份是空的：顯示「沒有符合條件的研究專案」（不是「還沒有任何研究專案」），篩選列仍在", async () => {
    const user = userEvent.setup();
    renderList();
    await screen.findAllByTestId("research-row");
    await user.selectOptions(screen.getByRole("combobox", { name: "狀態篩選" }), "archived");
    expect(await screen.findByText("沒有符合條件的研究專案")).toBeInTheDocument();
    expect(screen.queryByText("還沒有任何研究專案")).toBeNull();
    expect(screen.getByRole("combobox", { name: "狀態篩選" })).toBeInTheDocument();
  });
});

// ── F-08／INT-14⑥ 狀態徽章：文字、class（設計 token）與對比 ─────────────────────────────────

/** 每種徽章的樣本專案（除已封存外，都在預設的未封存清單裡）。 */
const BADGE_SAMPLES: ReadonlyArray<{ badge: ProjectBadgeId; label: string; patch: Partial<ResearchProjectSummary>; fg: string; bg: string }> = [
  { badge: "active", label: "進行中", patch: { flowStep: "topic", flowPhase: "RESEARCHING", flowStatus: "RUNNING" }, fg: "color-primary-strong", bg: "color-bg-base" },
  { badge: "frozen", label: "Gate 0 已核准", patch: { flowStep: "route", flowPhase: "FROZEN", flowStatus: "IDLE" }, fg: "color-primary-strong", bg: "color-bg-base" },
  { badge: "delivered", label: "已交付", patch: { flowStep: "deliver", flowPhase: "DELIVERED", flowStatus: "COMPLETED" }, fg: "color-primary-strong", bg: "color-bg-base" },
  { badge: "scr", label: "SCR 進行中", patch: { flowStep: "studio", flowPhase: "SCR_OPEN", flowStatus: "RUNNING" }, fg: "color-warning-text", bg: "color-alert-bg" },
  { badge: "failed", label: "失敗", patch: { flowStep: "topic", flowPhase: "INGESTED", flowStatus: "FAILED", flowDetail: "no_evidence" }, fg: "color-accent", bg: "color-draft-bg" },
  { badge: "init_failed", label: "初始化失敗", patch: { flowStep: "topic", flowPhase: "INGESTED", flowStatus: "FAILED", flowDetail: "init_failed:fsm" }, fg: "color-accent", bg: "color-draft-bg" },
];
/** 徽章字色的 Tailwind class（token 名稱）：每一列的字色與它坐的底色必須對比 ≥ 4.5:1（WCAG AA 一般文字；真瀏覽器層級另由 a11y.mock.spec.ts 的 axe 掃描把關）。 */
const BADGE_TEXT_CLASS: Readonly<Record<string, string>> = {
  "color-primary-strong": "text-wg-primary-strong",
  "color-warning-text": "text-wg-warning-text",
  "color-accent": "text-wg-accent",
};

describe("F-08／INT-14⑥ 清單徽章：每種徽章的文字、字色 class 與底色對比", () => {
  it("六種徽章各有一列：徽章文字與 data-badge 對得上；失敗與取消的專案標「失敗」、不標「進行中」", async () => {
    const projects: ResearchProjectSummary[] = BADGE_SAMPLES.map((sample, i) => ({
      ...SUMMARY_R1,
      id: `0000000${i}-0000-4000-8000-000000000000`,
      rpNo: `RP-010${i}`,
      slug: `badge-${sample.badge}`,
      ...sample.patch,
    }));
    projects.push({
      ...SUMMARY_R1,
      id: "0000000c-0000-4000-8000-000000000000",
      rpNo: "RP-0109",
      slug: "badge-cancelled",
      flowStep: "topic",
      flowPhase: "INGESTED",
      flowStatus: "FAILED",
      flowDetail: "cancelled",
    });
    renderList("OPERATOR", { projects });
    const rows = await screen.findAllByTestId("research-row");
    expect(rows).toHaveLength(BADGE_SAMPLES.length + 1);
    BADGE_SAMPLES.forEach((sample, i) => {
      expect(rows[i], sample.badge).toHaveAttribute("data-badge", sample.badge);
      expect(within(rows[i]).getByTestId("research-badge"), sample.badge).toHaveTextContent(new RegExp(`^${sample.label}$`));
    });
    expect(within(rows[BADGE_SAMPLES.length]).getByTestId("research-badge"), "被取消（FAILED／cancelled）").toHaveTextContent(/^失敗$/);
    expect(
      screen.getAllByTestId("research-badge").filter((badge) => badge.textContent === "進行中"),
      "只有真的在進行的那一列標進行中",
    ).toHaveLength(1);
  });

  it.each(BADGE_SAMPLES)("F-08 $badge 徽章（$label）：字色是 $fg 對應的 token class、底色是 $bg，兩者對比 ≥ 4.5:1；主色字（對比 4.21）不得出現", async ({ badge, patch, fg, bg }) => {
    renderList("OPERATOR", { projects: [{ ...SUMMARY_R1, ...patch }] });
    const element = await screen.findByTestId("research-badge");
    const classes = element.className.split(/\s+/);
    expect(element.closest("[data-research-id]")).toHaveAttribute("data-badge", badge);
    expect(classes, `${badge} 的字色 class`).toContain(BADGE_TEXT_CLASS[fg]);
    expect(classes, `${badge} 的底色 class`).toContain({ "color-bg-base": "bg-wg-base", "color-alert-bg": "bg-wg-alert-bg", "color-draft-bg": "bg-wg-draft-bg" }[bg]);
    expect(classes, "主色字坐在 bg-base 上只有 4.21:1（axe color-contrast serious）").not.toContain("text-wg-primary");
    const fgHex = tokenHex(fg);
    const bgHex = tokenHex(bg);
    expect(fgHex, `找不到前景 token ${fg}`).toBeDefined();
    expect(bgHex, `找不到底色 token ${bg}`).toBeDefined();
    expect(contrastRatio(fgHex as string, bgHex as string), `${badge}：${fg} 坐在 ${bg} 上`).toBeGreaterThanOrEqual(4.5);
  });

  it("F-08 已封存徽章（在「已封存」篩選才看得到）：字色 text-wg-muted、底色 bg-wg-base，對比 ≥ 4.5:1", async () => {
    const user = userEvent.setup();
    renderList("OPERATOR", { projects: [...PROJECT_LIST, ARCHIVED] });
    await screen.findAllByTestId("research-row");
    await user.selectOptions(screen.getByRole("combobox", { name: "狀態篩選" }), "archived");
    await screen.findByRole("button", { name: "復原 RP-0004" });
    const classes = screen.getByTestId("research-badge").className.split(/\s+/);
    expect(classes).toEqual(expect.arrayContaining(["bg-wg-base", "text-wg-muted"]));
    expect(contrastRatio(tokenHex("color-text-muted") as string, tokenHex("color-bg-base") as string)).toBeGreaterThanOrEqual(4.5);
  });

  it("INT-14⑥ 狀態篩選有「失敗」選項：只列失敗與取消的專案", async () => {
    const user = userEvent.setup();
    const failed: ResearchProjectSummary = {
      ...SUMMARY_R1,
      id: R4,
      rpNo: "RP-0004",
      slug: "failed-one",
      title: "失敗的研究",
      flowPhase: "INGESTED",
      flowStatus: "FAILED",
      flowDetail: "evaluator_failed",
    };
    renderList("OPERATOR", { projects: [...PROJECT_LIST, failed] });
    await screen.findAllByTestId("research-row");
    const status = screen.getByRole("combobox", { name: "狀態篩選" });
    expect(within(status).getByRole("option", { name: "失敗" })).toBeInTheDocument();
    await user.selectOptions(status, "failed");
    expect(screen.getAllByTestId("research-row").map((r) => r.getAttribute("data-research-id"))).toEqual([R4]);
  });
});

describe("AT_960_19_1 封存與復原（OPERATOR 以上；VIEWER 停用）", () => {
  it("AT_960_19_1 封存：先確認；取消不送請求；確認後 POST archive 恰一次、顯示成功提示並重抓清單", async () => {
    const user = userEvent.setup();
    const { calls } = renderList();
    await screen.findAllByTestId("research-row");
    await user.click(screen.getByRole("button", { name: "封存 RP-0001" }));
    const dialog = await screen.findByRole("dialog", { name: "封存研究專案" });
    expect(dialog).toHaveTextContent("封存「Agent 記憶體回收策略研究」後，它會從清單消失；30 天內可在狀態篩選選「已封存」後復原。");
    await user.click(within(dialog).getByRole("button", { name: "取消" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(writeCalls(calls), "取消不送任何寫入").toEqual([]);

    await user.click(screen.getByRole("button", { name: "封存 RP-0001" }));
    const again = await screen.findByRole("dialog", { name: "封存研究專案" });
    await user.click(within(again).getByRole("button", { name: "封存" }));
    expect(await screen.findByText("已封存研究專案 RP-0001，30 天內可復原")).toBeInTheDocument();
    expect(callsOf(calls, "POST", new RegExp(`^/api/v1/research/projects/${R1}/archive$`))).toHaveLength(1);
    expect(writeCalls(calls)).toHaveLength(1);
    await waitFor(() => expect(callsOf(calls, "GET", PROJECTS_PATH).length, "成功後清單重抓").toBeGreaterThanOrEqual(2));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("AT_960_19_1 封存失敗：錯誤原因（白話）顯示在對話框內、對話框不關閉、不顯示成功提示", async () => {
    const user = userEvent.setup();
    renderList("OPERATOR", { overrides: (c) => (c.method === "POST" && c.path.endsWith("/archive") ? failure(409, { message: "衝突", reason: "stage_conflict" }) : undefined) });
    await screen.findAllByTestId("research-row");
    await user.click(screen.getByRole("button", { name: "封存 RP-0002" }));
    const dialog = await screen.findByRole("dialog", { name: "封存研究專案" });
    await user.click(within(dialog).getByRole("button", { name: "封存" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("目前狀態不允許這個動作（可能已有進行中的階段），請重新整理後再試");
    expect(screen.getByRole("dialog", { name: "封存研究專案" })).toBeInTheDocument();
    expect(screen.queryByText(/已封存研究專案/)).toBeNull();
  });

  it("AT_960_19_1 復原：已封存的專案按「復原」→ POST restore 恰一次、顯示成功提示；失敗顯示錯誤提示", async () => {
    const user = userEvent.setup();
    let fail = false;
    const { calls } = renderList("OPERATOR", {
      projects: [...PROJECT_LIST, ARCHIVED],
      overrides: (c) => (fail && c.method === "POST" && c.path.endsWith("/restore") ? failure(404, { message: "找不到", reason: "research_not_found" }) : undefined),
    });
    await screen.findAllByTestId("research-row");
    await user.selectOptions(screen.getByRole("combobox", { name: "狀態篩選" }), "archived");
    await user.click(await screen.findByRole("button", { name: "復原 RP-0004" }));
    expect(await screen.findByText("已復原研究專案 RP-0004")).toBeInTheDocument();
    expect(callsOf(calls, "POST", new RegExp(`^/api/v1/research/projects/${R4}/restore$`))).toHaveLength(1);

    fail = true;
    await user.click(screen.getByRole("button", { name: "復原 RP-0004" }));
    expect(await screen.findByText(/復原失敗：找不到這個研究專案/)).toBeInTheDocument();
  });

  it("AT_960_19_1 VIEWER：每一列的封存鈕 disabled 且 title 為「權限不足（唯讀角色）」，點了不開對話框、不送寫入；列內容與「繼續」連結照常", async () => {
    const user = userEvent.setup();
    const { calls } = renderList("VIEWER");
    const rows = await screen.findAllByTestId("research-row");
    for (const row of rows) {
      const archive = within(row).getByRole("button", { name: /^封存 RP-\d{4}$/ });
      expect(archive).toBeDisabled();
      expect(archive).toHaveAttribute("title", "權限不足（唯讀角色）");
      expect(within(row).getByRole("link", { name: /^繼續（第 \d 步：/ })).toBeInTheDocument();
    }
    await user.click(within(rows[0]).getByRole("button", { name: "封存 RP-0001" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(writeCalls(calls)).toEqual([]);
  });
});

// ── AT_960_19_2：新建對話框 ──────────────────────────────────────────────────────────

async function openCreateDialog(opts: { role?: Role; stub?: StubPatch } = {}) {
  const user = userEvent.setup();
  const api = renderList(opts.role ?? "OPERATOR", opts.stub ?? {});
  await screen.findAllByTestId("research-row");
  await user.click(createButton());
  const dialog = await screen.findByRole("dialog", { name: "新建研究專案" });
  return { user, dialog, ...api };
}

const topicBox = (dialog: HTMLElement) => within(dialog).getByLabelText("研究命題") as HTMLTextAreaElement;
const slugBox = (dialog: HTMLElement) => within(dialog).getByLabelText("網址代號") as HTMLInputElement;
const setValue = (el: HTMLElement, value: string) => fireEvent.change(el, { target: { value } });
const submitButton = (dialog: HTMLElement) => within(dialog).getByRole("button", { name: "建立" });
const posts = (calls: Parameters<typeof callsOf>[0]) => callsOf(calls, "POST", PROJECTS_PATH);

describe("AT_960_19_2 新建對話框：zod 驗證逐欄顯示且不送出、代號自動產生可改、檢索深度三值、Web 層停用", () => {
  it("AT_960_19_2 命題空：在欄位旁顯示「命題不能為空」，不呼叫 API、對話框不關閉", async () => {
    const { user, dialog, calls } = await openCreateDialog();
    await user.click(submitButton(dialog));
    expect(await within(dialog).findByText("命題不能為空")).toBeInTheDocument();
    expect(posts(calls)).toHaveLength(0);
    expect(screen.getByRole("dialog", { name: "新建研究專案" })).toBeInTheDocument();
    expect(nav.push).not.toHaveBeenCalled();
  });

  it("AT_960_19_2 命題 501 字：顯示「命題最多 500 個字元」、不呼叫 API；500 字（邊界）可送出，title 取前 60 字加「…」、inScope 取前 200 字", async () => {
    const { user, dialog, calls } = await openCreateDialog();
    setValue(topicBox(dialog), "字".repeat(501));
    setValue(slugBox(dialog), "long-topic");
    await user.click(submitButton(dialog));
    expect(await within(dialog).findByText("命題最多 500 個字元")).toBeInTheDocument();
    expect(posts(calls)).toHaveLength(0);

    setValue(topicBox(dialog), "字".repeat(500));
    await user.click(submitButton(dialog));
    await waitFor(() => expect(posts(calls)).toHaveLength(1));
    const body = posts(calls)[0].body as { title: string; topic: string; scope: { inScope: string[] } };
    expect(body.topic).toHaveLength(500);
    expect(body.title).toBe(`${"字".repeat(60)}…`);
    expect(body.scope.inScope).toEqual(["字".repeat(200)]);
  });

  it("AT_960_19_2 四個來源層全關：顯示「至少要勾選一個來源層」、不呼叫 API（官方文獻與業界預設就是關的，所以只需關掉另外三個）", async () => {
    const { user, dialog, calls } = await openCreateDialog();
    setValue(topicBox(dialog), "向量資料庫選型 vector db");
    for (const name of ["論文", "開源 Repo", "社群"]) {
      const box = within(dialog).getByRole("checkbox", { name });
      expect(box).toBeChecked();
      await user.click(box);
      expect(box).not.toBeChecked();
    }
    expect(within(dialog).getByRole("checkbox", { name: "官方文獻與業界" })).not.toBeChecked();
    await user.click(submitButton(dialog));
    expect(await within(dialog).findByText("至少要勾選一個來源層")).toBeInTheDocument();
    expect(posts(calls)).toHaveLength(0);
    // 勾回一個就能送出（錯誤不是永久的）
    await user.click(within(dialog).getByRole("checkbox", { name: "論文" }));
    await user.click(submitButton(dialog));
    await waitFor(() => expect(posts(calls)).toHaveLength(1));
    expect((posts(calls)[0].body as { scope: { layers: unknown } }).scope.layers).toEqual({ academic: true, industry: false, oss: false, community: false });
  });

  it.each(["Abc", "-abc", "has space", "底線_不行", "a".repeat(31), ""])("AT_960_19_2 代號手改為 %j（不合 ^[a-z0-9][a-z0-9-]{0,29}$）：顯示代號錯誤、不呼叫 API", async (bad) => {
    const { user, dialog, calls } = await openCreateDialog();
    setValue(topicBox(dialog), "向量資料庫選型 vector db");
    setValue(slugBox(dialog), bad);
    await user.click(submitButton(dialog));
    expect(await within(dialog).findByText("代號須為小寫英數與連字號、1 至 30 字，且以英數開頭")).toBeInTheDocument();
    expect(posts(calls)).toHaveLength(0);
    expect(SLUG_PATTERN.test(bad)).toBe(false);
  });

  it("AT_960_19_2 代號由命題自動產生：ASCII 英數轉小寫、其餘（連續者）以一個連字號連接、截至 30 字元；手改後不再被命題覆蓋；說明寫明建立後不可改", async () => {
    const { dialog } = await openCreateDialog();
    expect(slugBox(dialog)).toHaveValue("");
    setValue(topicBox(dialog), "Vector DB 選型 2026");
    expect(slugBox(dialog)).toHaveValue("vector-db-2026");
    setValue(topicBox(dialog), "Use pgvector!");
    expect(slugBox(dialog)).toHaveValue("use-pgvector");
    setValue(topicBox(dialog), "a".repeat(40));
    expect(slugBox(dialog)).toHaveValue("a".repeat(30));
    setValue(topicBox(dialog), "");
    expect(slugBox(dialog), "命題清空時代號也清空").toHaveValue("");

    setValue(topicBox(dialog), "Vector DB");
    setValue(slugBox(dialog), "my-own-slug");
    setValue(topicBox(dialog), "Another topic entirely");
    expect(slugBox(dialog), "使用者改過的代號不被覆蓋").toHaveValue("my-own-slug");
    expect(dialog).toHaveTextContent("建立後不可改");
  });

  it("AT_960_19_2 命題不含任何 ASCII 英數（純中文）：代號退回 rp- 加四位小寫英數，且符合代號規則（⚖22）；同一命題恆得同一代號", async () => {
    const { dialog } = await openCreateDialog();
    setValue(topicBox(dialog), "向量資料庫選型");
    const first = slugBox(dialog).value;
    expect(first).toMatch(/^rp-[a-z0-9]{4}$/);
    expect(SLUG_PATTERN.test(first)).toBe(true);
    setValue(topicBox(dialog), "完全不同的命題");
    setValue(topicBox(dialog), "向量資料庫選型");
    expect(slugBox(dialog).value, "輸入時不閃動：同一命題同一代號").toBe(first);
  });

  it.each([
    ["快速", "QUICK"],
    ["標準", "STANDARD"],
    ["深入", "DEEP"],
  ])("AT_960_19_2 檢索深度選「%s」：送出本文的 depthLevel 為 %s（預設為標準）", async (label, value) => {
    const { user, dialog, calls } = await openCreateDialog();
    expect(within(dialog).getByRole("radio", { name: /標準/ })).toBeChecked();
    setValue(topicBox(dialog), "Vector DB 選型 2026");
    await user.click(within(dialog).getByRole("radio", { name: new RegExp(label) }));
    expect(within(dialog).getByRole("radio", { name: new RegExp(label) })).toBeChecked();
    await user.click(submitButton(dialog));
    await waitFor(() => expect(posts(calls)).toHaveLength(1));
    expect((posts(calls)[0].body as { depthLevel: string }).depthLevel).toBe(value);
  });

  it("AT_960_19_2 合法送出：POST /api/v1/research/projects 恰一次，本文欄位全為 camelCase、值域正確；成功後顯示提示、關閉對話框並導向 /research/<新 id>", async () => {
    const { user, dialog, calls } = await openCreateDialog();
    setValue(topicBox(dialog), "Vector DB 選型 2026");
    await user.click(submitButton(dialog));
    expect(await screen.findByText("已建立研究專案 RP-0099")).toBeInTheDocument();
    expect(posts(calls)).toHaveLength(1);
    expect(writeCalls(calls)).toHaveLength(1);
    const body = posts(calls)[0].body;
    expect(body).toEqual({
      slug: "vector-db-2026",
      title: "Vector DB 選型 2026",
      topic: "Vector DB 選型 2026",
      scope: {
        layers: { academic: true, industry: false, oss: true, community: true },
        techStack: "",
        inScope: ["Vector DB 選型 2026"],
        outOfScope: [],
        recencyYears: 3,
        applicabilityAxes: [...DEFAULT_APPLICABILITY_AXES],
      },
      depthLevel: "STANDARD",
    });
    expect(JSON.stringify(body), "沒有任何 snake_case 欄位").not.toMatch(/"[a-z]+_[a-z_]+"\s*:/);
    expect(nav.push).toHaveBeenCalledTimes(1);
    expect(nav.push).toHaveBeenCalledWith(`/research/${NEW_ID}`);
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("AT_960_19_2 取消：關閉對話框、不送請求；再開一次是乾淨的表單（命題與代號都是空的）", async () => {
    const { user, dialog, calls } = await openCreateDialog();
    setValue(topicBox(dialog), "寫到一半的命題 half-written");
    await user.click(within(dialog).getByRole("button", { name: "取消" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(writeCalls(calls)).toEqual([]);
    await user.click(createButton());
    const reopened = await screen.findByRole("dialog", { name: "新建研究專案" });
    expect(topicBox(reopened)).toHaveValue("");
    expect(slugBox(reopened)).toHaveValue("");
  });

  it("AT_960_19_2 官方文獻與業界（industry，Web 層）：capabilities.webLayerEnabled 為假時勾選停用並說明，送出的 industry 恆為 false", async () => {
    const { user, dialog, calls } = await openCreateDialog({ stub: { capabilities: { ...CAPABILITIES_LOCAL, webLayerEnabled: false } } });
    const industry = within(dialog).getByRole("checkbox", { name: "官方文獻與業界" });
    expect(industry).toBeDisabled();
    expect(industry).not.toBeChecked();
    expect(dialog).toHaveTextContent("「官方文獻與業界」需要先啟用 Web 層");
    await user.click(industry);
    expect(industry, "停用的勾選點了沒有反應").not.toBeChecked();
    setValue(topicBox(dialog), "向量資料庫選型 vector db");
    await user.click(submitButton(dialog));
    await waitFor(() => expect(posts(calls)).toHaveLength(1));
    expect((posts(calls)[0].body as { scope: { layers: { industry: boolean } } }).scope.layers.industry).toBe(false);
  });

  it("AT_960_19_2 能力探針失敗（連不上 Bridge）時無從確認，industry 同樣停用（寧可停用，伺服器端另有 layer_unavailable 再擋一次）", async () => {
    const { dialog } = await openCreateDialog({ stub: { capabilities: "error" } });
    expect(within(dialog).getByRole("checkbox", { name: "官方文獻與業界" })).toBeDisabled();
    expect(dialog).toHaveTextContent("「官方文獻與業界」需要先啟用 Web 層");
  });

  it("AT_960_19_2 Web 層已啟用：industry 可勾選且沒有說明文字；勾選後送出的 industry 為 true", async () => {
    const { user, dialog, calls } = await openCreateDialog({ stub: { capabilities: { ...CAPABILITIES_LOCAL, webLayerEnabled: true } } });
    const industry = within(dialog).getByRole("checkbox", { name: "官方文獻與業界" });
    await waitFor(() => expect(industry).toBeEnabled());
    expect(dialog).not.toHaveTextContent("需要先啟用 Web 層");
    await user.click(industry);
    expect(industry).toBeChecked();
    setValue(topicBox(dialog), "向量資料庫選型 vector db");
    await user.click(submitButton(dialog));
    await waitFor(() => expect(posts(calls)).toHaveLength(1));
    expect((posts(calls)[0].body as { scope: { layers: { industry: boolean } } }).scope.layers.industry).toBe(true);
  });

  it("AT_960_19_2 後端回 409 slug_in_use：錯誤顯示在代號欄位旁（白話原因）、對話框不關閉、不導向", async () => {
    const { user, dialog } = await openCreateDialog({
      stub: { overrides: (c) => (c.method === "POST" && c.path === "/api/v1/research/projects" ? failure(409, { message: "衝突", reason: "slug_in_use" }) : undefined) },
    });
    setValue(topicBox(dialog), "Vector DB 選型 2026");
    await user.click(submitButton(dialog));
    expect(await within(dialog).findByText("這個代號已被未封存的研究專案使用，請換一個")).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "新建研究專案" })).toBeInTheDocument();
    expect(nav.push).not.toHaveBeenCalled();
  });

  it("AT_960_19_2 後端回 400 帶欄位錯誤：topic、scope 的錯誤對應回欄位，對不上的欄位併入對話框頂端的說明", async () => {
    const { user, dialog } = await openCreateDialog({
      stub: {
        overrides: (c) =>
          c.method === "POST" && c.path === "/api/v1/research/projects"
            ? failure(400, {
                message: "參數錯誤",
                errors: [
                  { field: "topic", message: "命題含不允許的內容" },
                  { field: "scope.layers", message: "來源層設定不合法" },
                  { field: "extra.field", message: "不認得的欄位" },
                ],
              })
            : undefined,
      },
    });
    setValue(topicBox(dialog), "Vector DB 選型 2026");
    await user.click(submitButton(dialog));
    expect(await within(dialog).findByText("命題含不允許的內容")).toBeInTheDocument();
    expect(within(dialog).getByText("來源層設定不合法")).toBeInTheDocument();
    expect(within(dialog).getByTestId("create-error")).toHaveTextContent("extra.field：不認得的欄位");
    expect(nav.push).not.toHaveBeenCalled();
  });

  it("AT_960_19_2 後端不可用（503 bridge_unreachable）：顯示白話原因於對話框頂端，不導向", async () => {
    const { user, dialog } = await openCreateDialog({
      stub: { overrides: (c) => (c.method === "POST" && c.path === "/api/v1/research/projects" ? failure(503, { message: "不可用", reason: "bridge_unreachable" }) : undefined) },
    });
    setValue(topicBox(dialog), "Vector DB 選型 2026");
    await user.click(submitButton(dialog));
    expect(await within(dialog).findByTestId("create-error")).toHaveTextContent("連不上 Engine Bridge，請確認它是否在線");
    expect(nav.push).not.toHaveBeenCalled();
  });
});

// ── 頁殼 ───────────────────────────────────────────────────────────────────────────────

describe("AT_960_19_1 頁殼 app/research/page.tsx：只組裝清單元件", () => {
  it("AT_960_19_1 metadata.title 為「研發工作流」；預設匯出渲染清單頁；頁殼不自己讀資料、不含任何寫入", async () => {
    expect(listPageMetadata.title).toBe("研發工作流");
    const api = stubResearchApi({ projects: [] });
    renderResearch(<ResearchPage />, "OPERATOR");
    expect(await screen.findByTestId("research-list-view")).toBeInTheDocument();
    expect(await screen.findByText("還沒有任何研究專案")).toBeInTheDocument();
    expect(writeCalls(api.calls)).toEqual([]);
    const source = readFileSync(path.join(process.cwd(), "app", "research", "page.tsx"), "utf-8");
    expect(source, "頁殼只 import 清單元件，不 import 任何查詢 hook 或端點函式").not.toMatch(/@\/lib\/api/);
  });
});

// TCS-ConsoleUxSortHelp-20261108 AC-963-4（L2 研究專案列；W-UX5）
describe("AT_963_4 研究專案列：排序控制列（預設編號自然序升冪）", () => {
  const mk = (id: string, rpNo: string, title: string, patch: Partial<ResearchProjectSummary>): ResearchProjectSummary => ({
    ...SUMMARY_R1,
    id,
    rpNo,
    slug: `s-${rpNo.toLowerCase()}`,
    title,
    ...patch,
  });
  // API 序與編號序不同；步驟 route、topic、deliver 各一；更新時間：P100＝11-01 16:00Z、P9＝11-01 23:00Z、P10＝11-03 02:00Z
  const P10 = mk(R1, "RP-0010", "乙研究", { flowStep: "route", flowPhase: "FROZEN", flowStatus: "IDLE", updatedAt: "2026-11-03T10:00:00+08:00" });
  const P9 = mk(R2, "RP-0009", "丙研究", { flowStep: "topic", updatedAt: "2026-11-01T23:00:00Z" });
  const P100 = mk(R3, "RP-0100", "甲研究", { flowStep: "deliver", flowPhase: "DELIVERED", flowStatus: "COMPLETED", updatedAt: "2026-11-02T00:00:00+08:00" });
  const zh = new Intl.Collator("zh-Hant", { numeric: true });
  const rpNos = () => screen.getAllByTestId("research-row").map((row) => within(row).getByText(/^RP-\d{4}$/).textContent);
  const group = () => screen.getByRole("group", { name: "研究專案排序" });
  const pickSort = async (user: ReturnType<typeof userEvent.setup>, label: string) => user.selectOptions(within(group()).getByRole("combobox", { name: "排序" }), label);
  const toggleDir = async (user: ReturnType<typeof userEvent.setup>) => user.click(within(group()).getByRole("button", { name: /^目前由/ }));

  it("AT_963_4_3 預設依編號自然序升冪（RP-0009、RP-0010、RP-0100）；選標題、最近更新（ISO 時刻）、狀態（徽章文字）、步驟（步驟順序）各依語意；方向鈕切換後整列反序", async () => {
    const user = userEvent.setup();
    renderList("OPERATOR", { projects: [P10, P9, P100] });
    await screen.findAllByTestId("research-row");
    expect(rpNos()).toEqual(["RP-0009", "RP-0010", "RP-0100"]);
    expect(
      within(group())
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["編號", "標題", "狀態", "步驟", "最近更新"]);

    await pickSort(user, "標題");
    expect(rpNos()).toEqual([P10, P9, P100].sort((a, b) => zh.compare(a.title, b.title)).map((p) => p.rpNo));
    await pickSort(user, "最近更新");
    expect(rpNos()).toEqual(["RP-0100", "RP-0009", "RP-0010"]);
    await pickSort(user, "狀態");
    const badge = { "RP-0010": "Gate 0 已核准", "RP-0009": "進行中", "RP-0100": "已交付" } as Record<string, string>;
    expect(rpNos()).toEqual(Object.keys(badge).sort((a, b) => zh.compare(badge[a], badge[b])));
    await pickSort(user, "步驟");
    expect(rpNos()).toEqual(["RP-0009", "RP-0010", "RP-0100"]); // 研究、分流、交付
    await toggleDir(user);
    expect(rpNos()).toEqual(["RP-0100", "RP-0010", "RP-0009"]);
    await pickSort(user, "編號");
    expect(rpNos()).toEqual(["RP-0100", "RP-0010", "RP-0009"]); // 方向保留（降冪）
  });

  it("AT_963_4_4 已選標題降冪：切到「已封存」再切回排序保持；搜尋縮小清單後結果仍依目前排序", async () => {
    const user = userEvent.setup();
    renderList("OPERATOR", { projects: [P10, P9, P100, { ...P100, id: R4, rpNo: "RP-0004", slug: "old-topic", title: "舊的研究", archivedAt: T1 }] });
    await screen.findAllByTestId("research-row");
    await pickSort(user, "標題");
    await toggleDir(user);
    const byTitleDesc = (ps: ResearchProjectSummary[]) => ps.sort((a, b) => zh.compare(b.title, a.title)).map((p) => p.rpNo);
    expect(rpNos()).toEqual(byTitleDesc([P10, P9, P100]));

    await user.selectOptions(screen.getByRole("combobox", { name: "狀態篩選" }), "archived");
    await waitFor(() => expect(rpNos()).toEqual(["RP-0004"]));
    await user.selectOptions(screen.getByRole("combobox", { name: "狀態篩選" }), "all");
    await waitFor(() => expect(rpNos()).toHaveLength(3));
    expect(rpNos()).toEqual(byTitleDesc([P10, P9, P100]));
    expect(within(group()).getByRole("combobox", { name: "排序" })).toHaveValue("title");
    expect(within(group()).getByRole("button", { name: "目前由大到小，按一下改由小到大" })).toBeInTheDocument();

    // 搜尋「rp-00」只留 RP-0009、RP-0010（RP-0100 不含），仍依標題降冪
    await user.type(screen.getByRole("textbox", { name: "搜尋研究專案" }), "rp-00");
    await waitFor(() => expect(rpNos()).toHaveLength(2));
    expect(rpNos()).toEqual(byTitleDesc([P10, P9]));
  });
});
