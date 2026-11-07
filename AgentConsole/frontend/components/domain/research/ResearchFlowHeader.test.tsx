import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ResearchEvent, ResearchProjectDetail } from "@/lib/api/types";
import { LAMP_META } from "@/lib/domain/research";
import { CONSOLE_PROJECT_NAME, R1, R2, R3, T0 } from "@/tests/fixtures/research/ids";
import { eventPage } from "@/tests/fixtures/research/events";
import { detailVariant, SUMMARY_R1, SUMMARY_R3 } from "@/tests/fixtures/research/projects";
import { renderResearch, stubResearchApi } from "@/tests/helpers/research";
import { ResearchFlowHeader } from "./ResearchFlowHeader";

/**
 * 工作流頁首列（TCS-ResearchToPRD-P0-20261102 AT-960-20-1；AC-R2P-22-1～22-4）：
 * 研究專案切換下拉（列出可見專案並顯示關聯的 Console 專案名；選擇後導向該專案游標所在步）、狀態燈、Token 速率與預算；
 * 全工作區唯一一份、不動全站頂列與底列。純函式（`lampOf`、`tokenRate`、`budgetState`）的窮舉在 `lib/domain/research.test.ts`（AT-960-20-2、20-3），
 * 這裡驗「接線」：燈號取自後端衍生的 `flow.effective`、速率與已用量取自事件帳、預算取自系統參數。
 * 判定指令：npx vitest run components/domain/research/ResearchFlowHeader.test.tsx -t AT_960_20_1
 */
const nav = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: nav.push, replace: nav.replace, back: vi.fn() }),
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(),
}));

/** 固定「現在」：夾具的事件落在 2026-11-02 10:01～10:13（+08:00）；取 10:08 時近五分鐘窗為 10:03～10:08。 */
const NOW = new Date("2026-11-02T10:08:00+08:00");

beforeEach(() => {
  nav.push.mockClear();
  nav.replace.mockClear();
  vi.useFakeTimers({ toFake: ["Date"], now: NOW });
});
afterEach(() => {
  vi.useRealTimers();
});

const withEffective = (base: ResearchProjectDetail, patch: Partial<ResearchProjectDetail["flow"]["effective"]>): ResearchProjectDetail => ({
  ...base,
  flow: { ...base.flow, effective: { ...base.flow.effective, ...patch } },
});

const lamp = () => screen.getByTestId("flow-lamp");

async function renderHeader(project: ResearchProjectDetail, stub: Parameters<typeof stubResearchApi>[0] = {}) {
  const api = stubResearchApi(stub);
  const view = renderResearch(<ResearchFlowHeader project={project} />);
  // 先等事件帳與預算都回來：速率與已用量不再是破折號之前，斷言都是在量「載入中」
  await screen.findByRole("combobox", { name: "切換研究專案" });
  return { ...view, ...api };
}

describe("AT_960_20_1 頁首列三個區塊：切換下拉、狀態燈、Token 速率與預算", () => {
  it("AT_960_20_1 切換下拉列出可見專案（RP 編號、名稱），關聯 Console 專案者標出專案名；目前專案被選取；三個區塊都在", async () => {
    await renderHeader(detailVariant("studio"));
    const select = screen.getByRole("combobox", { name: "切換研究專案" });
    await waitFor(() => expect(within(select).getAllByRole("option")).toHaveLength(3));
    expect(select).toHaveValue(R2);
    const options = within(select).getAllByRole("option");
    expect(options[0]).toHaveTextContent("RP-0001 · Agent 記憶體回收策略研究");
    expect(options[1]).toHaveTextContent("RP-0002 · 向量資料庫選型");
    // 只有第三個專案有關聯的 Console 專案；專案名取自 Console 專案清單（要等它回來）
    await waitFor(() => expect(within(select).getByRole("option", { name: new RegExp(`Console：${CONSOLE_PROJECT_NAME}`) })).toBeInTheDocument());
    expect(options[2]).toHaveTextContent(`RP-0003 · RAG 評測基準（Console：${CONSOLE_PROJECT_NAME}）`);
    expect(options[0].textContent).not.toContain("Console：");
    expect(options[1].textContent).not.toContain("Console：");
    // 三個區塊
    expect(screen.getByTestId("research-flow-header")).toBeInTheDocument();
    expect(lamp()).toBeInTheDocument();
    expect(screen.getByTestId("token-rate")).toHaveTextContent("Token 速率");
    expect(screen.getByTestId("token-budget")).toHaveTextContent("預算");
    expect(screen.getByRole("progressbar", { name: "Token 預算進度" })).toBeInTheDocument();
  });

  it("AT_960_20_1 選另一個專案：router.push 到該專案游標所在步（/research/<id>?step=<游標步>），一次選擇恰一次導向、不送任何寫入請求", async () => {
    const user = userEvent.setup();
    const { calls } = await renderHeader(detailVariant("studio"));
    const select = screen.getByRole("combobox", { name: "切換研究專案" });
    await waitFor(() => expect(within(select).getAllByRole("option")).toHaveLength(3));

    await user.selectOptions(select, R3);
    expect(nav.push).toHaveBeenCalledTimes(1);
    expect(nav.push).toHaveBeenLastCalledWith(`/research/${R3}?step=route`);
    await user.selectOptions(select, R1);
    expect(nav.push).toHaveBeenCalledTimes(2);
    expect(nav.push).toHaveBeenLastCalledWith(`/research/${R1}?step=topic`);
    expect(nav.replace, "切換用 push（留歷史），不用 replace").not.toHaveBeenCalled();
    expect(calls.filter((c) => c.method !== "GET")).toEqual([]);
  });

  it("AT_960_20_1 目前專案不在清單（還在載入或已封存）也要出現在下拉的第一項；已封存的專案不列", async () => {
    const archived = { ...SUMMARY_R3, archivedAt: T0 };
    // 真後端的預設清單本來就不含已封存的；這裡刻意讓它回一筆已封存的，驗證頁首自己也不列（防守性過濾）
    await renderHeader(detailVariant("studio"), { overrides: (c) => (c.method === "GET" && c.path === "/api/v1/research/projects" ? { data: [SUMMARY_R1, archived] } : undefined) });
    const select = screen.getByRole("combobox", { name: "切換研究專案" });
    await waitFor(() => expect(within(select).getAllByRole("option")).toHaveLength(2));
    const options = within(select).getAllByRole("option");
    expect(options[0]).toHaveAttribute("value", R2);
    expect(options[1]).toHaveAttribute("value", R1);
    expect(within(select).queryByRole("option", { name: /RP-0003/ })).toBeNull();
    expect(select).toHaveValue(R2);
  });

  it("AT_960_20_1 單一元件：ResearchFlowHeader.tsx 是全工作區唯一份（只有工作區殼渲染一次），也不碰全站頂列與底列", () => {
    const dir = path.join(process.cwd(), "components", "domain", "research");
    const sources = Object.fromEntries(
      readdirSync(dir)
        .filter((name) => /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name))
        .map((name) => [name, readFileSync(path.join(dir, name), "utf-8")] as const),
    );
    const rendering = Object.entries(sources)
      .filter(([, text]) => text.includes("<ResearchFlowHeader"))
      .map(([name]) => name);
    expect(rendering, "只有工作區殼渲染頁首列（五步共用同一份）").toEqual(["ResearchWorkspaceView.tsx"]);
    expect(sources["ResearchWorkspaceView.tsx"].match(/<ResearchFlowHeader/g)).toHaveLength(1);
    const owners = Object.entries(sources)
      .filter(([, text]) => text.includes('data-testid="research-flow-header"') || text.includes("切換研究專案") || text.includes('data-testid="flow-lamp"'))
      .map(([name]) => name);
    expect(owners, "頁首列的三個區塊只定義在一個檔案").toEqual(["ResearchFlowHeader.tsx"]);
    // 正規式以字串拼接組成：使本檔原始碼不含四個區塊名的字面，AT_960_20_4（全站四區塊只在 app/layout.tsx 組裝的字面掃描）不再自我命中（P0 R-3、AT-962-25-4）；語意不變
    const regionNames = new RegExp(["Top", "Bottom", "Tools", "Content"].map((part) => `${part}Region`).join("|"));
    for (const [name, text] of Object.entries(sources)) expect(text, `${name} 不得提到全站區塊`).not.toMatch(regionNames);
  });

  it("AT_962_25_4 P0 殘留 R-3：反向斷言的正則以字串拼接組成——本檔原始碼不含四個全站區塊名的字面（字面掃描不再自我命中）；斷言語意不變（仍抓得到引用）", () => {
    const parts = ["Top", "Bottom", "Tools", "Content"];
    const own = readFileSync(path.join(process.cwd(), "components", "domain", "research", "ResearchFlowHeader.test.tsx"), "utf-8");
    for (const part of parts) expect(own.includes(`${part}Region`), `${part}Region 不得以字面出現在本檔`).toBe(false);
    const regionNames = new RegExp(parts.map((part) => `${part}Region`).join("|"));
    expect(regionNames.test(`import { ${parts[0]}Region } from "@/components/layout/x";`)).toBe(true);
    expect(regionNames.test("import { ResearchFlowHeader } from './x';")).toBe(false);
  });
});

describe("AT_960_20_1 狀態燈：取自後端衍生的 flow.effective，文字標籤為準", () => {
  const CASES: ReadonlyArray<{ name: string; project: () => ResearchProjectDetail; lamp: keyof typeof LAMP_META }> = [
    { name: "閒置（IDLE）", project: () => detailVariant("studio"), lamp: "Idle" },
    { name: "研究中（RUNNING）", project: () => detailVariant("topicRunning"), lamp: "Running" },
    { name: "審查中（RUNNING）", project: () => detailVariant("reviewing"), lamp: "Running" },
    { name: "自癒中（RUNNING 且衍生相態 HEALING）", project: () => withEffective(detailVariant("topicRunning"), { phase: "HEALING" }), lamp: "Healing" },
    { name: "已暫停（衍生狀態 PAUSED）", project: () => withEffective(detailVariant("topicRunning"), { status: "PAUSED" }), lamp: "Paused" },
    { name: "升級給人工（ESCALATED）", project: () => detailVariant("escalated"), lamp: "Escalated" },
    { name: "等人工（WAITING_HUMAN）仍是閒置", project: () => detailVariant("gate0"), lamp: "Idle" },
  ];

  it.each(CASES)("AT_960_20_1 $name → 燈號 $lamp", async ({ project, lamp: kind }) => {
    await renderHeader(project());
    const el = lamp();
    expect(el).toHaveAttribute("role", "status");
    expect(el).toHaveAttribute("data-lamp", kind);
    expect(el, "燈號有文字標籤，不只靠顏色").toHaveTextContent(LAMP_META[kind].label);
  });

  it("AT_960_20_1 優先序：同時 RUNNING 且衍生相態 HEALING 取 Healing；ESCALATED 即使相態是 HEALING 也取 Escalated（Escalated 高於 Healing）", async () => {
    await renderHeader(withEffective(detailVariant("escalated"), { phase: "HEALING" }));
    expect(lamp()).toHaveAttribute("data-lamp", "Escalated");
  });
});

describe("AT_960_20_1 Token 速率與預算（AC-R2P-22-3）：事件帳與系統參數接線", () => {
  it("AT_960_20_1 近五分鐘的增量除以五：夾具事件在 10:03～10:08 窗內的累計從 0 升到 5200，速率 1,040 tokens/min；已用量為各 stage run 峰值加總 7,000", async () => {
    await renderHeader(detailVariant("topicRunning"));
    await waitFor(() => expect(screen.getByTestId("token-rate")).toHaveTextContent("1,040 tokens/min"));
    const budget = screen.getByTestId("token-budget");
    await waitFor(() => expect(budget).toHaveTextContent("已用 7,000 / 1,000,000（1%）"));
    expect(budget).toHaveAttribute("data-level", "ok");
    expect(screen.queryByText("已達預算警示閾值")).toBeNull();
  });

  it("AT_960_20_1 無事件：速率顯示「—」（不是 0）；已用量 0", async () => {
    await renderHeader(detailVariant("topicRunning"), { events: [] });
    await waitFor(() => expect(screen.getByTestId("token-budget")).toHaveTextContent("已用 0 / 1,000,000（0%）"));
    expect(screen.getByTestId("token-rate")).toHaveTextContent("—");
    expect(screen.getByTestId("token-rate")).not.toHaveTextContent("tokens/min");
  });

  it("AT_960_20_1 視窗外的事件不算速率：現在是 10:30 時，近五分鐘沒有任何 research.run 事件，速率回到「—」，已用量仍是 7,000", async () => {
    vi.setSystemTime(new Date("2026-11-02T10:30:00+08:00"));
    await renderHeader(detailVariant("topicRunning"));
    await waitFor(() => expect(screen.getByTestId("token-budget")).toHaveTextContent("已用 7,000"));
    expect(screen.getByTestId("token-rate")).toHaveTextContent("—");
  });

  it.each([
    { budget: "8750", warn: "0.8", level: "warn", pct: "（80%）", note: "用量剛好達預算的 0.8 倍即警示（邊界值含等號）" },
    { budget: "7500", warn: "0.9", level: "warn", pct: "（93%）", note: "閾值取自系統參數 0.9，用量 93% 已越過" },
    { budget: "7500", warn: "0.95", level: "ok", pct: "（93%）", note: "同樣用量，閾值調到 0.95 就不警示：閾值確實取自系統參數而不是寫死 0.8" },
    { budget: "10000", warn: "0.8", level: "ok", pct: "（70%）", note: "70% 未達 0.8" },
    { budget: "5000", warn: "0.8", level: "warn", pct: "（140%）", note: "超出預算（百分比可超過 100）仍是警示，不會被夾掉" },
  ])("AT_960_20_1 預算警示：預算 $budget、閾值 $warn → $level $pct（$note）", async ({ budget, warn, level, pct }) => {
    await renderHeader(detailVariant("topicRunning"), { execution: { globalTokenBudget: budget, tokenBudgetWarningThreshold: warn } });
    const box = screen.getByTestId("token-budget");
    await waitFor(() => expect(box).toHaveTextContent(pct));
    expect(box).toHaveAttribute("data-level", level);
    if (level === "warn") expect(within(box).getByRole("status")).toHaveTextContent("已達預算警示閾值");
    else expect(within(box).queryByRole("status")).toBeNull();
  });

  it("AT_960_20_1 預算取自系統參數 execution.globalTokenBudget：參數取不到（503）時預算顯示「—」、不判警示、已用量照常", async () => {
    await renderHeader(detailVariant("topicRunning"), { execution: null });
    await waitFor(() => expect(screen.getByTestId("token-budget")).toHaveTextContent("已用 7,000 / —"));
    expect(screen.getByTestId("token-budget")).toHaveAttribute("data-level", "unknown");
    expect(screen.queryByText("已達預算警示閾值")).toBeNull();
  });

  it("AT_960_20_1 事件帳分頁：事件超過一頁（limit 500）時合併全部頁面再計算，已用量不漏頁", async () => {
    const many: ResearchEvent[] = [];
    for (let i = 0; i < 600; i++) {
      many.push({
        seq: i + 1,
        eventType: "research.run",
        step: "topic",
        actor: "bridge",
        refKind: null,
        refId: null,
        payload: { stageRunId: `run-${i}`, tokensUsed: 10 },
        occurredAt: "2026-11-02T09:00:00+08:00",
      });
    }
    const { calls } = await renderHeader(detailVariant("topicRunning"), { events: many });
    await waitFor(() => expect(screen.getByTestId("token-budget")).toHaveTextContent("已用 6,000 / 1,000,000"));
    const eventCalls = calls.filter((c) => c.path === `/api/v1/research/projects/${R1}/events`);
    expect(eventCalls.length, "600 筆事件需要兩頁以上").toBeGreaterThanOrEqual(2);
    expect(eventPage(many, 0, 500).truncated, "夾具確實會截斷第一頁").toBe(true);
  });
});
