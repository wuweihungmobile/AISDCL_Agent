import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ResearchCapabilities, ResearchEvidenceItem, ResearchEvidenceMatrix, ResearchProjectDetail, ResearchSource, Role } from "@/lib/api/types";
import { MIN_EVIDENCE_ROWS, MOCK_ONLY_NOTICE, READONLY_TITLE, evidenceGate, readResearchScope, researchEnvironmentBlock, researchFailureOf } from "@/lib/domain/research";
import { R1 } from "@/tests/fixtures/research/ids";
import { CAPABILITIES_LOCAL, CAPABILITIES_MOCK_ONLY, EVIDENCE, SOURCES } from "@/tests/fixtures/research/misc";
import { detailVariant } from "@/tests/fixtures/research/projects";
import { FakeEventSource } from "@/tests/helpers/fakeEventSource";
import { callsOf, failure, renderResearch, stubResearchApi, writeCalls } from "@/tests/helpers/research";
import { TopicPanel } from "./TopicPanel";

/**
 * 議題面板（TCS-ResearchToPRD-P0-20261102 AT-960-19-7；AC-R2P-04-11、04-5）：mock-only 停用「啟動深研」並顯示說明、Web 層關時「官方文獻與業界」停用並說明、
 * 研究未完成顯示橫幅與「續跑」（再 POST research、不顯示為完成）、證據閘過時「生成 PRD 初稿」啟用、不過時停用並說明缺什麼；另驗角色與唯讀檢視、分頁籤與純文字。
 * 判定指令：npx vitest run components/domain/research/TopicPanel.test.tsx -t AT_960_19_7
 */
const nav = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: nav.push, replace: nav.replace, back: vi.fn() }),
  usePathname: () => `/research/x`,
  useSearchParams: () => new URLSearchParams("step=topic"),
}));

beforeEach(() => {
  nav.push.mockClear();
  nav.replace.mockClear();
  FakeEventSource.reset();
  vi.stubGlobal("EventSource", FakeEventSource);
});

// ── 夾具 ─────────────────────────────────────────────────────────────────────────────

const BASE_ITEM = EVIDENCE.items[0];
const item = (evidenceNo: string, patch: Partial<ResearchEvidenceItem> = {}): ResearchEvidenceItem => ({
  ...BASE_ITEM,
  evidenceNo,
  sourceNo: `S-${evidenceNo.slice(2)}`,
  candidate: "候選 A",
  ...patch,
});
const source = (sourceNo: string, patch: Partial<ResearchSource> = {}): ResearchSource => ({ ...SOURCES[0], sourceNo, fetches: [], ...patch });
const matrixOf = (items: ResearchEvidenceItem[]): ResearchEvidenceMatrix => ({ ...EVIDENCE, items, counterEvidence: [] });

/** 證據閘過：三列層級 V2 以上、已錨定、非線索（`MIN_EVIDENCE_ROWS` 為 3）。 */
const GATE_OK = {
  evidence: matrixOf([item("E-001", { f7Verification: "V2" }), item("E-002", { f7Verification: "V3" }), item("E-003", { f7Verification: "V2" })]),
  sources: [source("S-001"), source("S-002"), source("S-003")],
};
/** 證據閘不過：四列裡只有一列合格（一列 UNANCHORED、一列 V1、一列來源是線索）。 */
const GATE_SHORT = {
  evidence: matrixOf([
    item("E-001", { f7Verification: "V2" }),
    item("E-002", { f7Verification: "V3", unanchored: true }),
    item("E-003", { f7Verification: "V1" }),
    item("E-004", { f7Verification: "V2" }),
  ]),
  sources: [source("S-001"), source("S-002"), source("S-003"), source("S-004", { clueOnly: true })],
};

type Stub = Parameters<typeof stubResearchApi>[0];

function renderTopic(project: ResearchProjectDetail, opts: { role?: Role; stub?: Stub; completed?: boolean } = {}) {
  const api = stubResearchApi({ details: { [R1]: project }, ...GATE_OK, ...opts.stub });
  const ui = renderResearch(<TopicPanel researchId={R1} project={project} completed={opts.completed === true} />, opts.role ?? "OPERATOR");
  return { ...ui, ...api };
}

const startButton = () => screen.getByRole("button", { name: "啟動深研" });
const draftButton = () => screen.getByRole("button", { name: "生成 PRD 初稿" });
const stagePosts = (calls: Parameters<typeof callsOf>[0], stage: string) => callsOf(calls, "POST", new RegExp(`/stages/${stage}$`));

const READY = (patch: Partial<ResearchProjectDetail> = {}) => detailVariant("topicReady", patch);
const INITIAL = (patch: Partial<ResearchProjectDetail> = {}) => detailVariant("topicReady", { flowPhase: "INGESTED", flowStatus: "IDLE", ...patch });
const FAILED = (detail: string) => detailVariant("topicRunning", { flowPhase: "RESEARCHING", flowStatus: "FAILED", flowDetail: detail });

// ── AT_960_19_7 ────────────────────────────────────────────────────────────────────────

describe("AT_960_19_7 議題面板：環境閘（mock-only、Web 層、探針）", () => {
  it("AT_960_19_7 capabilities 為 mock-only：「啟動深研」disabled 並顯示「容器模式只跑 mock claude 的驗收；真研究限本機模式」，點了不送出任何請求", async () => {
    const user = userEvent.setup();
    const { calls } = renderTopic(INITIAL(), { stub: { capabilities: CAPABILITIES_MOCK_ONLY } });
    await waitFor(() => expect(screen.getByTestId("launch-hint")).toHaveTextContent(MOCK_ONLY_NOTICE));
    expect(MOCK_ONLY_NOTICE).toBe("容器模式只跑 mock claude 的驗收；真研究限本機模式");
    expect(startButton()).toBeDisabled();
    await user.click(startButton());
    expect(stagePosts(calls, "research")).toHaveLength(0);
    expect(writeCalls(calls)).toEqual([]);
  });

  it("AT_960_19_7 local 模式且 claude 可用：「啟動深研」啟用，點了恰一次 POST stages/research（本文為空物件）並提示已送出；沒有說明橫幅", async () => {
    const user = userEvent.setup();
    const { calls } = renderTopic(INITIAL(), { stub: { capabilities: CAPABILITIES_LOCAL } });
    await waitFor(() => expect(startButton()).toBeEnabled());
    expect(screen.queryByTestId("launch-hint")).toBeNull();
    expect(startButton()).not.toHaveAttribute("title");
    await user.click(startButton());
    await waitFor(() => expect(stagePosts(calls, "research")).toHaveLength(1));
    expect(stagePosts(calls, "research")[0].path).toBe(`/api/v1/research/projects/${R1}/stages/research`);
    expect(stagePosts(calls, "research")[0].body).toEqual({});
    expect(await screen.findByText("啟動深研：已送出，動態欄會即時更新")).toBeInTheDocument();
  });

  it("AT_960_19_7 其他環境缺件各有白話說明：找不到 claude、Bridge 沒連資料庫；探針失敗時顯示橫幅（證據與動態仍取自資料庫）並可重新檢查", async () => {
    const user = userEvent.setup();
    const noClaude: ResearchCapabilities = { ...CAPABILITIES_LOCAL, claudeCli: { ok: false } };
    const first = renderTopic(INITIAL(), { stub: { capabilities: noClaude } });
    await waitFor(() => expect(screen.getByTestId("launch-hint")).toHaveTextContent("找不到 claude 命令列工具"));
    expect(startButton()).toBeDisabled();
    first.unmount();

    const second = renderTopic(INITIAL(), { stub: { capabilities: { ...CAPABILITIES_LOCAL, db: false } } });
    await waitFor(() => expect(screen.getByTestId("launch-hint")).toHaveTextContent("Bridge 沒有連上資料庫"));
    second.unmount();

    const third = renderTopic(INITIAL(), { stub: { capabilities: "error" } });
    const banner = await screen.findByTestId("capabilities-error");
    expect(banner).toHaveTextContent("無法取得研究環境狀態");
    expect(startButton()).toBeDisabled();
    expect(screen.getByTestId("launch-hint")).toHaveTextContent("無法確認研究環境");
    expect(screen.getByTestId("topic-text"), "資料庫內容照常顯示").toBeInTheDocument();
    third.options.capabilities = CAPABILITIES_LOCAL;
    await user.click(within(banner).getByRole("button", { name: "重新檢查" }));
    await waitFor(() => expect(startButton()).toBeEnabled());
    expect(screen.queryByTestId("capabilities-error")).toBeNull();
  });

  it("AT_960_19_7 環境閘判定（純函式）：探針失敗＞尚未載入＞沒連資料庫＞容器模式＞找不到 claude＞放行", () => {
    const ok = { mode: "local" as const, db: true, claudeCli: { ok: true } };
    expect(researchEnvironmentBlock(undefined, true)).toMatch(/無法確認研究環境/);
    expect(researchEnvironmentBlock(undefined, false)).toMatch(/正在檢查/);
    expect(researchEnvironmentBlock({ ...ok, db: false, mode: "mock-only" }, false)).toMatch(/沒有連上資料庫/);
    expect(researchEnvironmentBlock({ ...ok, mode: "mock-only", claudeCli: { ok: false } }, false)).toBe(MOCK_ONLY_NOTICE);
    expect(researchEnvironmentBlock({ ...ok, claudeCli: { ok: false } }, false)).toMatch(/找不到 claude/);
    expect(researchEnvironmentBlock(ok, false)).toBeNull();
  });

  it("AT_960_19_7 Web 層關：「官方文獻與業界」勾選停用並說明（指向說明文字）；Web 層開時沒有說明；其餘三層照資料庫值唯讀顯示", async () => {
    const off = renderTopic(INITIAL(), { stub: { capabilities: { ...CAPABILITIES_LOCAL, webLayerEnabled: false } } });
    const industry = await screen.findByRole("checkbox", { name: /官方文獻與業界/ });
    expect(industry).toBeDisabled();
    expect(industry).not.toBeChecked();
    const note = await screen.findByTestId("web-layer-note");
    expect(note).toHaveTextContent("Web 層未啟用");
    expect(industry.getAttribute("aria-describedby")).toBe(note.id);
    // 夾具的範圍：論文、開源 Repo、社群為真——全部唯讀（P0 沒有範圍修訂端點）
    for (const [name, checked] of [
      ["論文", true],
      ["開源 Repo", true],
      ["社群", true],
    ] as const) {
      const box = screen.getByRole("checkbox", { name });
      expect(box, name).toBeDisabled();
      if (checked) expect(box, name).toBeChecked();
    }
    off.unmount();

    // 範圍要求產業層、Web 層又未啟用：勾著但停用並說明（研究不會跑這一層）
    const stale = renderTopic(INITIAL({ scope: { ...INITIAL().scope, layers: { academic: true, industry: true, oss: false, community: false } } }), {
      stub: { capabilities: { ...CAPABILITIES_LOCAL, webLayerEnabled: false } },
    });
    expect(await screen.findByRole("checkbox", { name: /官方文獻與業界/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /官方文獻與業界/ })).toBeDisabled();
    expect(await screen.findByTestId("web-layer-note")).toBeInTheDocument();
    stale.unmount();

    renderTopic(INITIAL(), { stub: { capabilities: { ...CAPABILITIES_LOCAL, webLayerEnabled: true } } });
    await waitFor(() => expect(startButton()).toBeEnabled());
    expect(screen.queryByTestId("web-layer-note")).toBeNull();
    expect(screen.getByRole("checkbox", { name: "官方文獻與業界" })).toBeDisabled();
  });
});

describe("AT_960_19_7 議題面板：研究未完成（續跑、重試）不顯示為完成", () => {
  it("AT_960_19_7 stage 失敗（exit_reason 為 step_timeout）：橫幅「研究未完成：step_timeout」與「續跑」鈕；沒有「啟動深研」；續跑再 POST research；「生成 PRD 初稿」停用且不顯示為完成", async () => {
    const user = userEvent.setup();
    const { calls } = renderTopic(FAILED("step_timeout"));
    const banner = await screen.findByTestId("research-failure");
    expect(banner).toHaveTextContent("研究未完成：step_timeout");
    expect(banner).toHaveAttribute("role", "alert");
    expect(screen.queryByRole("button", { name: "啟動深研" })).toBeNull();
    expect(screen.getByTestId("topic-status")).toHaveTextContent("研究中（失敗）");
    expect(draftButton()).toBeDisabled();
    expect(screen.getByTestId("draft-hint")).toHaveTextContent("研究尚未完成");
    expect(screen.queryByText(/證據已足夠/), "失敗不能被當成完成").toBeNull();
    const resume = within(banner).getByRole("button", { name: "續跑" });
    await waitFor(() => expect(resume).toBeEnabled());
    await user.click(resume);
    await waitFor(() => expect(stagePosts(calls, "research")).toHaveLength(1));
    expect(await screen.findByText("續跑：已送出，動態欄會即時更新")).toBeInTheDocument();
    expect(stagePosts(calls, "draft")).toHaveLength(0);
  });

  it("AT_960_19_7 no_evidence（沒有任何來源取得成功）：橫幅「研究失敗」與「重試」鈕（沒有 checkpoint 可續）；初始化失敗不算研究失敗，只說明要先重試初始化", async () => {
    const first = renderTopic(FAILED("no_evidence"));
    const banner = await screen.findByTestId("research-failure");
    expect(banner).toHaveTextContent("研究失敗：沒有任何來源取得成功（no_evidence）");
    expect(within(banner).getByRole("button", { name: "重試" })).toBeInTheDocument();
    expect(within(banner).queryByRole("button", { name: "續跑" })).toBeNull();
    first.unmount();

    renderTopic(detailVariant("initFailed"));
    expect(await screen.findByTestId("launch-hint")).toHaveTextContent("工作區尚未初始化完成");
    expect(screen.queryByTestId("research-failure")).toBeNull();
    expect(startButton()).toBeDisabled();
    expect(researchFailureOf({ flowStep: "topic", flowStatus: "FAILED", flowDetail: "init_failed:fsm" })).toBeNull();
    expect(researchFailureOf({ flowStep: "topic", flowStatus: "FAILED", flowDetail: "" })).toMatchObject({ action: "resume", text: "研究未完成：後端沒有提供原因" });
    expect(researchFailureOf({ flowStep: "studio", flowStatus: "FAILED", flowDetail: "step_timeout" }), "步驟 2 的失敗不是研究失敗").toBeNull();
    expect(researchFailureOf({ flowStep: "topic", flowStatus: "IDLE", flowDetail: "" })).toBeNull();
  });

  it("INT-04 evaluator_failed（引擎的 evaluator 判研究輸出不合格）：游標是 FAILED 加原因代碼——橫幅「研究未完成：evaluator_failed」與「續跑」鈕，不是安靜的「議題已受理（閒置）」；「生成 PRD 初稿」停用", async () => {
    const user = userEvent.setup();
    const { calls } = renderTopic(detailVariant("topicReady", { flowPhase: "INGESTED", flowStatus: "FAILED", flowDetail: "evaluator_failed" }));
    const banner = await screen.findByTestId("research-failure");
    expect(banner).toHaveAttribute("role", "alert");
    expect(banner).toHaveTextContent("研究未完成：evaluator_failed");
    expect(screen.getByTestId("topic-status")).toHaveTextContent("議題已受理（失敗）");
    expect(screen.queryByRole("button", { name: "啟動深研" }), "失敗橫幅取代主動作鈕").toBeNull();
    expect(draftButton()).toBeDisabled();
    const resume = within(banner).getByRole("button", { name: "續跑" });
    await waitFor(() => expect(resume).toBeEnabled());
    await user.click(resume);
    await waitFor(() => expect(stagePosts(calls, "research")).toHaveLength(1));
  });

  it("INT-04 cancelled（研究被取消；D-77：取消也是 FAILED 加 exit_reason）：橫幅「研究已取消」與「重試」鈕（沒有「續跑」、不寫成研究未完成）；重試再 POST research", async () => {
    const user = userEvent.setup();
    const { calls } = renderTopic(detailVariant("topicReady", { flowPhase: "INGESTED", flowStatus: "FAILED", flowDetail: "cancelled" }));
    const banner = await screen.findByTestId("research-failure");
    expect(banner).toHaveTextContent("研究已取消");
    expect(banner).not.toHaveTextContent("研究未完成");
    expect(within(banner).queryByRole("button", { name: "續跑" })).toBeNull();
    expect(screen.queryByRole("button", { name: "啟動深研" })).toBeNull();
    expect(draftButton()).toBeDisabled();
    const retry = within(banner).getByRole("button", { name: "重試" });
    await waitFor(() => expect(retry).toBeEnabled());
    await user.click(retry);
    await waitFor(() => expect(stagePosts(calls, "research")).toHaveLength(1));
    expect(await screen.findByText("重試：已送出，動態欄會即時更新")).toBeInTheDocument();
  });

  it("AT_960_19_7 續跑失敗（Bridge 尚未實作的 502）：以白話原因提示、橫幅仍在、不假裝成功", async () => {
    const user = userEvent.setup();
    const { calls } = renderTopic(FAILED("token_guard_halt"), {
      stub: {
        overrides: (c) =>
          c.method === "POST" && /\/stages\/research$/.test(c.path)
            ? failure(502, { message: "Bridge 端點尚未實作", reason: "not_implemented", details: { endpoint: "POST /research/projects/{id}/stages/research:start" } })
            : undefined,
      },
    });
    const resume = await screen.findByRole("button", { name: "續跑" });
    await waitFor(() => expect(resume).toBeEnabled());
    await user.click(resume);
    expect(await screen.findByText(/續跑失敗：這個功能尚未開放/)).toBeInTheDocument();
    expect(screen.getByTestId("research-failure")).toHaveTextContent("研究未完成：token_guard_halt");
    expect(stagePosts(calls, "research")).toHaveLength(1);
  });

  it("AT_960_19_7 研究進行中：顯示「停止研究」（POST cancel）、沒有「啟動深研」；草擬停用", async () => {
    const user = userEvent.setup();
    const { calls } = renderTopic(detailVariant("topicRunning"));
    const stop = await screen.findByRole("button", { name: "停止研究" });
    expect(screen.queryByRole("button", { name: "啟動深研" })).toBeNull();
    expect(screen.getByText("研究進行中，動態欄會即時更新。")).toBeInTheDocument();
    expect(draftButton()).toBeDisabled();
    await user.click(stop);
    await waitFor(() => expect(callsOf(calls, "POST", /\/cancel$/)).toHaveLength(1));
    expect(await screen.findByText("已要求停止研究，已入庫的證據會保留")).toBeInTheDocument();
  });
});

describe("AT_960_19_7 議題面板：證據閘與「生成 PRD 初稿」", () => {
  it("AT_960_19_7 研究完成且證據閘過（3 列合格）：「生成 PRD 初稿」啟用；點了 POST stages/draft 並導向步驟 2", async () => {
    const user = userEvent.setup();
    const { calls } = renderTopic(READY());
    await waitFor(() => expect(draftButton()).toBeEnabled());
    expect(screen.getByTestId("draft-hint")).toHaveTextContent("證據已足夠：3 列合格");
    expect(draftButton()).not.toHaveAttribute("title");
    // 研究已完成：主動作變成「再次深研」（補充證據），不再是「啟動深研」
    expect(screen.getByRole("button", { name: "再次深研" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "啟動深研" })).toBeNull();
    await user.click(draftButton());
    await waitFor(() => expect(stagePosts(calls, "draft")).toHaveLength(1));
    expect(stagePosts(calls, "draft")[0].body).toEqual({});
    await waitFor(() => expect(nav.push).toHaveBeenCalledWith(`/research/${R1}?step=studio`));
    expect(stagePosts(calls, "research")).toHaveLength(0);
  });

  it("AT_960_19_7 證據閘不過（四列只有 1 列合格：一列 UNANCHORED、一列 V1、一列來源是線索）：「生成 PRD 初稿」停用並說明缺什麼；點了不送出", async () => {
    const user = userEvent.setup();
    const { calls } = renderTopic(READY(), { stub: GATE_SHORT });
    const hint = await screen.findByTestId("draft-hint");
    await waitFor(() => expect(hint).toHaveTextContent("證據不足：目前只有 1 列合格"));
    expect(hint).toHaveTextContent(`至少需要 ${MIN_EVIDENCE_ROWS} 列`);
    expect(hint).toHaveTextContent("層級 V2 以上、已錨定、非線索");
    expect(draftButton()).toBeDisabled();
    await user.click(draftButton());
    expect(stagePosts(calls, "draft")).toHaveLength(0);
    expect(nav.push).not.toHaveBeenCalled();
  });

  it("AT_960_19_7 證據閘純函式：層級 V2 以上、非 UNANCHORED、非線索各自獨立判定；來源清單找不到的列視為非線索；恰好 3 列才過", () => {
    const rows = GATE_SHORT.evidence.items;
    expect(evidenceGate(rows, GATE_SHORT.sources)).toMatchObject({ ok: false, qualified: 1, required: 3 });
    expect(evidenceGate(rows, [])).toMatchObject({ qualified: 2 });
    expect(evidenceGate(GATE_OK.evidence.items, GATE_OK.sources)).toMatchObject({ ok: true, qualified: 3 });
    expect(evidenceGate(GATE_OK.evidence.items.slice(0, 2), GATE_OK.sources)).toMatchObject({ ok: false, qualified: 2 });
    expect(evidenceGate([], [])).toMatchObject({ ok: false, qualified: 0 });
  });

  it("AT_960_19_7 研究尚未開始或未完成：「生成 PRD 初稿」停用並說明要先完成研究（即使資料庫已有證據列）", async () => {
    renderTopic(INITIAL());
    const hint = await screen.findByTestId("draft-hint");
    expect(hint).toHaveTextContent("研究尚未完成");
    expect(draftButton()).toBeDisabled();
  });

  it("AT_960_19_7 草擬失敗（Bridge 尚未實作的 502）：以白話原因提示、留在步驟 1、不導向", async () => {
    const user = userEvent.setup();
    renderTopic(READY(), {
      stub: { overrides: (c) => (c.method === "POST" && /\/stages\/draft$/.test(c.path) ? failure(502, { message: "Bridge 端點尚未實作", reason: "not_implemented" }) : undefined) },
    });
    await waitFor(() => expect(draftButton()).toBeEnabled());
    await user.click(draftButton());
    expect(await screen.findByText(/生成 PRD 初稿失敗：這個功能尚未開放/)).toBeInTheDocument();
    expect(nav.push).not.toHaveBeenCalled();
  });
});

describe("AT_960_19_7 議題面板：角色、唯讀檢視、分頁籤與純文字", () => {
  it("AT_960_19_7 VIEWER：啟動、續跑、停止、草擬全部 disabled 且 title 為「權限不足（唯讀角色）」；內容與動態照常可讀；渲染期間沒有任何寫入", async () => {
    const first = renderTopic(INITIAL(), { role: "VIEWER" });
    await waitFor(() => expect(screen.getByTestId("topic-text")).toBeInTheDocument());
    expect(startButton()).toBeDisabled();
    expect(startButton()).toHaveAttribute("title", READONLY_TITLE);
    expect(draftButton()).toBeDisabled();
    expect(draftButton()).toHaveAttribute("title", READONLY_TITLE);
    await waitFor(() => expect(screen.getAllByTestId("timeline-event").length).toBeGreaterThan(0));
    expect(writeCalls(first.calls)).toEqual([]);
    first.unmount();

    const failed = renderTopic(FAILED("step_timeout"), { role: "VIEWER" });
    const resume = await screen.findByRole("button", { name: "續跑" });
    expect(resume).toBeDisabled();
    expect(resume).toHaveAttribute("title", READONLY_TITLE);
    expect(writeCalls(failed.calls)).toEqual([]);
    failed.unmount();

    const running = renderTopic(detailVariant("topicRunning"), { role: "VIEWER" });
    const stop = await screen.findByRole("button", { name: "停止研究" });
    expect(stop).toBeDisabled();
    expect(stop).toHaveAttribute("title", READONLY_TITLE);
    expect(writeCalls(running.calls)).toEqual([]);
  });

  it("AT_960_19_7 已完成步驟的唯讀檢視（completed）：所有寫入動作 disabled 並說明「這一步已完成，唯讀」；VIEWER 的說明優先", async () => {
    const view = renderTopic(READY(), { completed: true });
    await waitFor(() => expect(screen.getByTestId("topic-text")).toBeInTheDocument());
    for (const name of ["再次深研", "生成 PRD 初稿"]) {
      const button = screen.getByRole("button", { name });
      expect(button, name).toBeDisabled();
      expect(button, name).toHaveAttribute("title", "這一步已完成，唯讀");
    }
    expect(writeCalls(view.calls)).toEqual([]);
    view.unmount();

    renderTopic(READY(), { completed: true, role: "VIEWER" });
    await waitFor(() => expect(screen.getByRole("button", { name: "生成 PRD 初稿" })).toHaveAttribute("title", READONLY_TITLE));
  });

  it("AT_960_19_7 議題內容取自資料庫且純文字：命題逐字顯示（含 script 與 Markdown）、檢索深度與納入排除範圍唯讀、DOM 沒有 script／img／strong", async () => {
    const hostile = "<script>alert(1)</script> **粗體** <img src=x onerror=alert(1)>";
    const { container } = renderTopic(INITIAL({ topic: hostile, depthLevel: "DEEP", scope: { ...INITIAL().scope, inScope: ["<b>納入</b>一"], outOfScope: ["排除一"] } }));
    expect(await screen.findByTestId("topic-text")).toHaveTextContent(hostile);
    expect(screen.getByTestId("topic-text").textContent).toBe(hostile);
    expect(screen.getByText("<b>納入</b>一")).toBeInTheDocument();
    expect(container.querySelector("script, img, strong, b, iframe")).toBeNull();
    const deep = screen.getByRole("radio", { name: /深入/ });
    expect(deep).toBeChecked();
    expect(deep).toBeDisabled();
    expect(screen.getByRole("radio", { name: /標準/ })).not.toBeChecked();
    expect(readResearchScope({ layers: "壞的", inScope: [1, "ok", " "], recencyYears: "3" })).toEqual({
      layers: { academic: false, industry: false, oss: false, community: false },
      techStack: "",
      inScope: ["ok"],
      outOfScope: [],
      recencyYears: null,
      applicabilityAxes: [],
    });
  });

  it("AT_960_19_7 三個分頁籤（動態欄、證據矩陣表、技術優缺點矩陣）：預設動態欄；切換只顯示對應視圖；每個分頁籤的 aria-controls 都指向存在的面板；優缺點的 [E-NNN] 連結切到矩陣表並展開該列", async () => {
    const user = userEvent.setup();
    renderTopic(READY());
    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((t) => t.textContent)).toEqual(["動態欄", "證據矩陣表", "技術優缺點矩陣"]);
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    await screen.findByTestId("evidence-matrix");
    for (const tab of tabs) expect(document.getElementById(tab.getAttribute("aria-controls") ?? ""), `${tab.textContent} 的面板存在`).not.toBeNull();
    await waitFor(() => expect(screen.getByTestId("research-timeline")).toBeVisible());
    expect(await screen.findByTestId("evidence-matrix")).not.toBeVisible();

    await user.click(tabs[1]);
    expect(tabs[1]).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByTestId("evidence-table")).toBeVisible();
    expect(screen.getByTestId("research-timeline")).not.toBeVisible();
    expect(screen.getByRole("tabpanel", { name: "證據矩陣表" })).toBeVisible();

    await user.click(tabs[2]);
    const matrix = await screen.findByRole("table", { name: "技術優缺點矩陣" });
    expect(matrix).toBeVisible();
    expect(screen.getByTestId("evidence-table-view")).not.toBeVisible();
    await user.click(within(matrix).getAllByRole("link", { name: /^\[E-\d{3}\]$/ })[0]);
    await waitFor(() => expect(tabs[1]).toHaveAttribute("aria-selected", "true"));
    expect(screen.getByTestId("evidence-table")).toBeVisible();
    expect(screen.getAllByTestId("evidence-row").some((row) => row.getAttribute("data-expanded") === "true")).toBe(true);
  });
});
