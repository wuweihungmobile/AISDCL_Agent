import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import path from "node:path";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { qk } from "@/lib/api/queries";
import type { ResearchDecomposition, ResearchProjectDetail, ResearchRouteDecision } from "@/lib/api/types";
import { BUILD_DISABLED_TEXT } from "@/lib/domain/research";
import { CONSOLE_PROJECT_ID, R3 } from "@/tests/fixtures/research/ids";
import {
  DECOMPOSITION_COVERED,
  DECOMPOSITION_DRAFT,
  DECOMPOSITION_SIGNED,
  DECOMPOSITION_STALE,
  DECOMPOSITION_WITH_TCS,
  ROUTE_ADOPTED,
  ROUTE_NOT_ADOPTED,
  bigDecomposition,
  buildProject,
  reconcileWith,
} from "@/tests/fixtures/research/build";
import { callsOf, failure, renderResearch, stubResearchApi, writeCalls, type ApiCall, type Reply } from "@/tests/helpers/research";
import { BuildFrontPanel } from "./BuildFrontPanel";
import { ResearchWorkspaceView } from "./ResearchWorkspaceView";

/**
 * 步驟 4 前半面板（TCS-ResearchToPRD-P1-20261107 AT-961-18-1～18-7、18-E-1、20-E-4、25-4）。
 * 判定指令：npx vitest run components/domain/research/BuildFrontPanel.test.tsx -t "<AT 底線形>"
 */
// 與 ResearchWorkspaceView.test.tsx 同體例：可變的路由替身（AT-962-25-3 要渲染整個工作區）
const nav = vi.hoisted(() => {
  const router = { push: vi.fn(), replace: vi.fn(), back: vi.fn() };
  return { router, params: {} as { researchId?: string | string[] }, search: "" };
});
vi.mock("next/navigation", () => ({
  useRouter: () => nav.router,
  useParams: () => nav.params,
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(nav.search),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const DECOMP_URL = /\/decomposition$/;
const SIGNOFF_URL = /\/decomposition\/signoff$/;
const TCS_URL = /\/stages\/tcs-draft$/;
const RECONCILE_URL = /\/reconcile$/;

type Opts = {
  role?: "ADMIN" | "OPERATOR" | "VIEWER";
  project?: ResearchProjectDetail;
  route?: ResearchRouteDecision | null;
  decomposition?: ResearchDecomposition | null;
  completed?: boolean;
  /** 先於內建回放 */
  overrides?: (call: ApiCall) => Reply;
};

/** 假後端：拆解的 GET／POST 與簽核共用一個可變的 `state.decomposition`；POST 觸發後換成 `onTrigger`、簽核後換成 `onSignoff`。 */
function renderPanel(opts: Opts = {}, hooks: { onTrigger?: ResearchDecomposition; onSignoff?: ResearchDecomposition } = {}) {
  const project = opts.project ?? buildProject("ROUTED");
  const state = { decomposition: opts.decomposition === undefined ? null : opts.decomposition };
  const api = stubResearchApi({
    details: { [R3]: project },
    route: opts.route === undefined ? ROUTE_ADOPTED : opts.route,
    overrides: (call) => {
      const custom = opts.overrides?.(call);
      if (custom !== undefined) return custom;
      if (DECOMP_URL.test(call.path) && call.method === "GET") return { data: state.decomposition };
      if (DECOMP_URL.test(call.path) && call.method === "POST") {
        state.decomposition = hooks.onTrigger ?? DECOMPOSITION_DRAFT;
        return { data: state.decomposition };
      }
      if (SIGNOFF_URL.test(call.path) && call.method === "POST") {
        state.decomposition = hooks.onSignoff ?? DECOMPOSITION_SIGNED;
        return { data: state.decomposition };
      }
      return undefined;
    },
  });
  const view = renderResearch(<BuildFrontPanel researchId={R3} project={project} completed={opts.completed ?? false} />, opts.role ?? "OPERATOR");
  return { ...view, ...api, state };
}

const btn = (name: string | RegExp) => screen.findByRole("button", { name });

describe("AT_961_18_1 拆解面板：空狀態與觸發拆解、草稿樹、覆蓋矩陣與未覆蓋清單", () => {
  it("AT_961_18_1 尚無拆解：顯示說明與「觸發拆解」；OPERATOR 按下送一次 POST …/decomposition，之後顯示草稿樹、任務數、覆蓋矩陣與兩個未覆蓋 AC", async () => {
    const user = userEvent.setup();
    const { calls } = renderPanel({ decomposition: null });
    expect(await screen.findByTestId("decomposition-empty")).toHaveTextContent("尚未拆解");
    const trigger = await btn("觸發拆解");
    expect(trigger).toBeEnabled();
    await user.click(trigger);
    await waitFor(() => expect(callsOf(calls, "POST", DECOMP_URL)).toHaveLength(1));

    expect(await screen.findByTestId("decomposition-tree")).toBeInTheDocument();
    const count = screen.getByTestId("decomposition-tasks-count");
    expect(count).toHaveTextContent("3");
    expect(count.getAttribute("data-tree-count"), "tasksCount 與樹內 task 數一致").toBe("3");
    expect(screen.getByTestId("coverage-summary")).toHaveTextContent("已覆蓋 3 ／ 共 5");
    const matrix = screen.getByTestId("coverage-matrix");
    expect(
      within(matrix)
        .getAllByRole("row")
        .filter((r) => r.hasAttribute("data-ac")),
    ).toHaveLength(5);
    expect(
      within(matrix)
        .getAllByRole("columnheader")
        .filter((h) => h.getAttribute("aria-label")?.startsWith("任務 ")),
    ).toHaveLength(3);
    const uncovered = within(screen.getByTestId("uncovered-list")).getAllByRole("listitem");
    expect(uncovered.map((li) => li.getAttribute("data-ac"))).toEqual(["AC-003-1", "AC-004-1"]);
    // 涵蓋格有可及名稱
    expect(within(matrix).getByLabelText("AC-001-1 由 T-1 涵蓋")).toBeInTheDocument();
  });

  it("AT_961_18_1 VIEWER：「觸發拆解」停用且 title 為權限不足，不送任何寫入", async () => {
    const { calls } = renderPanel({ role: "VIEWER", decomposition: null });
    const trigger = await btn("觸發拆解");
    expect(trigger).toBeDisabled();
    expect(trigger.getAttribute("title")).toContain("權限不足");
    expect(writeCalls(calls)).toEqual([]);
  });

  it("AT_961_18_1 樹內文字一律純文字渲染：goal 與 task 名稱含標記字元時不產生元素", async () => {
    const hostile: ResearchDecomposition = {
      ...DECOMPOSITION_COVERED,
      goals: [{ goal_id: "G-1", name: "<b>粗體</b><script>x</script>", tasks: [{ task_id: "T-1", name: "<img src=x onerror=alert(1)>", covers_ac: ["AC-001-1"] }] }],
    };
    renderPanel({ decomposition: hostile });
    const tree = await screen.findByTestId("decomposition-tree");
    expect(tree).toHaveTextContent("<b>粗體</b><script>x</script>");
    expect(tree.querySelector("b, script, img")).toBeNull();
  });

  it("AT_961_18_1 422 結構化錯誤（max_steps、cycle、empty_prompt）：顯示閘別與說明、不顯示草稿；觸發為同步請求，進行中顯示忙碌狀態", async () => {
    const user = userEvent.setup();
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const { calls } = renderPanel({
      decomposition: null,
      overrides: (call) =>
        call.method === "POST" && DECOMP_URL.test(call.path)
          ? failure(422, {
              message: "拆解沒有通過",
              reason: "invalid_request",
              details: {
                violations: [
                  { field: "steps", rule: "max_steps" },
                  { field: "deps", rule: "cycle" },
                  { field: "prompt", rule: "empty_prompt" },
                ],
              },
            })
          : undefined,
    });
    const realFetch = globalThis.fetch;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string, init?: RequestInit) => {
        if (init?.method === "POST" && DECOMP_URL.test(String(input))) await gate;
        return realFetch(input, init);
      }),
    );
    await user.click(await btn("觸發拆解"));
    expect(await screen.findByTestId("decomposition-busy")).toHaveTextContent("拆解進行中");
    expect(screen.getByRole("button", { name: /觸發拆解/ })).toBeDisabled();
    release();
    const error = await screen.findByTestId("decomposition-error");
    expect(error).toHaveTextContent("閘別 max_steps");
    expect(error).toHaveTextContent("閘別 cycle");
    expect(error).toHaveTextContent("閘別 empty_prompt");
    expect(screen.queryByTestId("decomposition-tree")).toBeNull();
    expect(callsOf(calls, "POST", DECOMP_URL)).toHaveLength(1);
    expect(screen.queryByTestId("decomposition-busy")).toBeNull();
  });
});

describe("AT_961_18_2 簽核鈕：未覆蓋清零或各有豁免理由前停用", () => {
  const reason500 = "字".repeat(500);
  const reason501 = "字".repeat(501);
  const input = (ac: string) => screen.getByLabelText(new RegExp(`豁免理由：${ac}`));

  it("AT_961_18_2 兩個未覆蓋 AC：理由 0／501 字無效、1／500 字有效；全部有效才啟用；簽核送一次、豁免隨請求、不送 approver；成功後轉已簽核唯讀並顯示簽核者與時間", async () => {
    const user = userEvent.setup();
    const { calls } = renderPanel({ decomposition: DECOMPOSITION_DRAFT });
    const sign = await btn("簽核");
    expect(sign).toBeDisabled();
    const blockers = screen.getByTestId("signoff-blockers");
    expect(blockers).toHaveTextContent("AC-003-1");
    expect(blockers).toHaveTextContent("AC-004-1");

    fireEvent.change(input("AC-003-1"), { target: { value: reason501 } });
    expect(await screen.findByText("豁免理由最多 500 字")).toBeInTheDocument();
    expect(sign).toBeDisabled();
    fireEvent.change(input("AC-003-1"), { target: { value: "" } });
    expect(screen.queryByText("豁免理由最多 500 字")).toBeNull();
    expect(sign).toBeDisabled();
    fireEvent.change(input("AC-003-1"), { target: { value: "字" } });
    expect(screen.getByTestId("signoff-blockers")).not.toHaveTextContent("AC-003-1");
    expect(sign).toBeDisabled();
    fireEvent.change(input("AC-004-1"), { target: { value: reason500 } });
    expect(sign).toBeEnabled();
    expect(screen.queryByTestId("signoff-blockers")).toBeNull();

    await user.click(sign);
    await waitFor(() => expect(callsOf(calls, "POST", SIGNOFF_URL)).toHaveLength(1));
    const body = callsOf(calls, "POST", SIGNOFF_URL)[0].body as Record<string, unknown>;
    expect(body).toEqual({
      waivers: [
        { ac: "AC-003-1", reason: "字" },
        { ac: "AC-004-1", reason: reason500 },
      ],
    });
    expect(Object.keys(body)).not.toContain("approver");

    const signed = await screen.findByTestId("decomposition-signed");
    expect(signed).toHaveTextContent("簽核者 operator");
    expect(signed).toHaveTextContent("2026");
    expect(screen.queryByRole("button", { name: "簽核" })).toBeNull();
    expect(screen.queryByLabelText(/豁免理由：AC-003-1/)).toBeNull();
  });

  it("AT_961_18_2 空白字元不算有效理由；全覆蓋的草稿不需任何豁免即可簽核（waivers 為空陣列）", async () => {
    const user = userEvent.setup();
    const first = renderPanel({ decomposition: DECOMPOSITION_DRAFT });
    await screen.findByRole("button", { name: "簽核" });
    fireEvent.change(input("AC-003-1"), { target: { value: "   " } });
    fireEvent.change(input("AC-004-1"), { target: { value: "有理由" } });
    expect(screen.getByRole("button", { name: "簽核" })).toBeDisabled();
    first.unmount();

    const { calls } = renderPanel({ decomposition: DECOMPOSITION_COVERED });
    const sign = await btn("簽核");
    expect(sign).toBeEnabled();
    await user.click(sign);
    await waitFor(() => expect(callsOf(calls, "POST", SIGNOFF_URL)).toHaveLength(1));
    expect(callsOf(calls, "POST", SIGNOFF_URL)[0].body).toEqual({ waivers: [] });
  });

  it("AT_961_18_2 VIEWER 全停用：豁免輸入欄與簽核鈕都停用，title 為權限不足，不送任何寫入", async () => {
    const { calls } = renderPanel({ role: "VIEWER", decomposition: DECOMPOSITION_DRAFT });
    const sign = await btn("簽核");
    expect(sign).toBeDisabled();
    expect(sign.getAttribute("title")).toContain("權限不足");
    expect(input("AC-003-1")).toBeDisabled();
    expect(input("AC-004-1")).toBeDisabled();
    expect(writeCalls(calls)).toEqual([]);
  });

  it("AT_961_18_2 簽核被後端拒絕（缺 approver 400、VIEWER 403）：顯示錯誤文字、面板仍是草稿可再試", async () => {
    const user = userEvent.setup();
    renderPanel({
      decomposition: DECOMPOSITION_COVERED,
      overrides: (call) => (call.method === "POST" && SIGNOFF_URL.test(call.path) ? failure(403, { message: "沒有權限簽核" }) : undefined),
    });
    await user.click(await btn("簽核"));
    expect(await screen.findByTestId("decomposition-error")).toHaveTextContent("沒有權限簽核");
    expect(screen.getByRole("button", { name: "簽核" })).toBeEnabled();
    expect(screen.queryByTestId("decomposition-signed")).toBeNull();
  });
});

describe("AT_961_18_3 stale：PRD 更新後拆解標過期，已簽核後唯讀", () => {
  it("AT_961_18_3 stale 的已簽核版：顯示「PRD 已更新，拆解已過期」與「重新拆解」；沒有簽核鈕；執行中心停用並說明拆解已過期", async () => {
    const user = userEvent.setup();
    const { calls } = renderPanel({ decomposition: DECOMPOSITION_STALE, project: buildProject("BUILD_READY") });
    expect(await screen.findByTestId("decomposition-stale")).toHaveTextContent("PRD 已更新，拆解已過期");
    expect(screen.queryByRole("button", { name: "簽核" })).toBeNull();
    expect(screen.getByTestId("decomposition-status")).toHaveTextContent("已過期");
    const exec = screen.getByTestId("execute-disabled");
    expect(exec).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByTestId("execute-block-reason")).toHaveAttribute("data-block", "stale");
    expect(screen.getByTestId("execute-block-reason")).toHaveTextContent("拆解已過期");
    await user.click(screen.getByRole("button", { name: "重新拆解" }));
    await waitFor(() => expect(callsOf(calls, "POST", DECOMP_URL)).toHaveLength(1));
  });

  it("AT_961_18_3 VIEWER 看過期拆解：「重新拆解」停用", async () => {
    renderPanel({ role: "VIEWER", decomposition: DECOMPOSITION_STALE });
    const redo = await btn("重新拆解");
    expect(redo).toBeDisabled();
    expect(redo.getAttribute("title")).toContain("權限不足");
  });

  it("AT_961_18_3 已簽核且不過期：樹與矩陣唯讀（無輸入欄）、無簽核鈕，豁免理由以文字顯示", async () => {
    renderPanel({ decomposition: DECOMPOSITION_SIGNED, project: buildProject("BUILD_READY") });
    expect(await screen.findByTestId("decomposition-signed")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "簽核" })).toBeNull();
    expect(screen.queryByTestId("decomposition-stale")).toBeNull();
    expect(screen.queryByLabelText(/豁免理由：/)).toBeNull();
    expect(screen.getAllByTestId("waiver-readonly").map((n) => n.textContent)).toEqual(["豁免理由：由上游服務負責，本專案不實作", "豁免理由：屬後續階段"]);
  });
});

describe("AT_961_18_4 TCS 草擬面板：前置、三態與路徑雜湊、凍結導引", () => {
  const start = () => screen.findByRole("button", { name: "草擬測試規格" });

  it("AT_961_18_4 內環鍵未採納或尚無拆解列：「草擬測試規格」停用並說明需先完成分流並觸發拆解", async () => {
    const notAdopted = renderPanel({ route: ROUTE_NOT_ADOPTED, decomposition: DECOMPOSITION_DRAFT });
    const first = await start();
    await waitFor(() => expect(screen.getByTestId("tcs-disabled-reason")).toHaveTextContent("需先完成分流並觸發拆解"));
    expect(first).toBeDisabled();
    notAdopted.unmount();

    renderPanel({ route: ROUTE_ADOPTED, decomposition: null });
    const second = await start();
    await waitFor(() => expect(second.getAttribute("title")).toContain("需先完成分流並觸發拆解"));
    expect(second).toBeDisabled();
  });

  it("AT_961_18_4 前置齊備：OPERATOR 可按並送出 tcs-draft；VIEWER 停用", async () => {
    const user = userEvent.setup();
    const operator = renderPanel({ decomposition: DECOMPOSITION_SIGNED });
    const enabled = await start();
    await waitFor(() => expect(enabled).toBeEnabled());
    await user.click(enabled);
    await waitFor(() => expect(callsOf(operator.calls, "POST", TCS_URL)).toHaveLength(1));
    operator.unmount();

    const viewer = renderPanel({ role: "VIEWER", decomposition: DECOMPOSITION_SIGNED });
    const disabled = await start();
    expect(disabled).toBeDisabled();
    expect(disabled.getAttribute("title")).toContain("權限不足");
    expect(callsOf(viewer.calls, "POST", TCS_URL)).toHaveLength(0);
  });

  it("AT_961_18_4 啟動前置未成立的 409：列出後端 details.unmet[] 的缺項（字串與物件兩種元素）", async () => {
    const user = userEvent.setup();
    renderPanel({
      decomposition: DECOMPOSITION_SIGNED,
      overrides: (call) =>
        call.method === "POST" && TCS_URL.test(call.path)
          ? failure(409, { message: "前置未成立", reason: "fsm_state_conflict", details: { unmet: ["route_not_succeeded", { item: "decomposition_missing" }] } })
          : undefined,
    });
    await user.click(await start());
    const error = await screen.findByTestId("tcs-start-error");
    expect(error).toHaveTextContent("分流尚未完成");
    expect(error).toHaveTextContent("尚未觸發拆解");
  });

  it("AT_961_18_4 草擬中：顯示進行中、沒有草擬鈕", async () => {
    renderPanel({ project: buildProject("TCS_DRAFTING", "RUNNING"), decomposition: DECOMPOSITION_SIGNED });
    expect(await screen.findByTestId("tcs-stage-text")).toHaveTextContent("測試規格草擬中");
    expect(screen.getByTestId("tcs-card")).toHaveAttribute("data-stage", "drafting");
    expect(screen.queryByRole("button", { name: "草擬測試規格" })).toBeNull();
  });

  it("AT_961_18_4 待凍結：顯示 TCS 路徑與 sha256 前 12 碼，「前往凍結」連到既有專案頁，說明凍結後按重新對帳", async () => {
    renderPanel({ project: buildProject("TCS_PENDING", "WAITING_HUMAN"), decomposition: DECOMPOSITION_WITH_TCS });
    const facts = await screen.findByTestId("tcs-facts");
    await waitFor(() => expect(facts).toHaveTextContent("docs/03_testing/contracts/TCS-rag-eval-20261107.md"));
    expect(facts).toHaveTextContent("c".repeat(12));
    expect(facts).not.toHaveTextContent("c".repeat(13));
    expect(screen.getByRole("link", { name: "前往凍結" })).toHaveAttribute("href", `/projects/${CONSOLE_PROJECT_ID}`);
    expect(screen.getByTestId("tcs-freeze-guide")).toHaveTextContent("重新對帳");
  });

  it("AT_961_18_4 tcs_invalid 失敗：以純文字顯示缺項說明（缺的 AC、孤兒 AT），仍可重試", async () => {
    renderPanel({ project: buildProject("TCS_DRAFTING", "FAILED", { detail: "tcs_invalid: 缺 AC-003-1；孤兒 <b>AT-9-9</b>" }), decomposition: DECOMPOSITION_SIGNED });
    const failed = await screen.findByTestId("tcs-failed");
    expect(failed).toHaveTextContent("缺 AC-003-1；孤兒 <b>AT-9-9</b>");
    expect(failed.querySelector("b")).toBeNull();
    expect(await start()).toBeEnabled();
  });

  it("AT_961_18_4 已凍結：顯示完成與路徑雜湊，沒有草擬鈕與前往凍結", async () => {
    renderPanel({ project: buildProject("BUILD_READY"), decomposition: DECOMPOSITION_WITH_TCS });
    expect(await screen.findByTestId("tcs-stage-text")).toHaveTextContent("測試規格已凍結");
    await waitFor(() => expect(screen.getByTestId("tcs-facts")).toHaveTextContent("TCS-rag-eval-20261107.md"));
    expect(screen.queryByRole("button", { name: "草擬測試規格" })).toBeNull();
    expect(screen.queryByRole("link", { name: "前往凍結" })).toBeNull();
  });
});

describe("AT_961_18_5 到既有 freeze、import、execute 的連結與執行閘說明", () => {
  const exec = () => within(screen.getByTestId("inner-loop-links")).queryByRole("link", { name: "執行中心" });
  const reason = () => screen.queryByTestId("execute-block-reason");

  it("AT_961_18_5 四種組合：只有「已簽核、未 stale、TCS 已凍結、無 SCR」時執行連結啟用；其餘停用並顯示對應原因；連結指向既有路由", async () => {
    const cases: Array<{ name: string; project: ResearchProjectDetail; decomposition: ResearchDecomposition; block: string | null; text: string }> = [
      { name: "未簽核", project: buildProject("ROUTED"), decomposition: DECOMPOSITION_DRAFT, block: "unsigned", text: "草稿未經人工審批" },
      { name: "已簽核但 TCS 未凍結", project: buildProject("TCS_PENDING", "WAITING_HUMAN"), decomposition: DECOMPOSITION_SIGNED, block: "tcsUnfrozen", text: "測試規格尚未凍結" },
      { name: "stale", project: buildProject("BUILD_READY"), decomposition: DECOMPOSITION_STALE, block: "stale", text: "拆解已過期" },
      { name: "皆完成", project: buildProject("BUILD_READY"), decomposition: DECOMPOSITION_SIGNED, block: null, text: "" },
    ];
    for (const c of cases) {
      const view = renderPanel({ project: c.project, decomposition: c.decomposition });
      await screen.findByTestId("inner-loop-links");
      await waitFor(() => expect(screen.getByTestId("decomposition-card")).toBeInTheDocument());
      if (c.block === null) {
        expect(exec(), c.name).toHaveAttribute("href", `/projects/${CONSOLE_PROJECT_ID}/execute?researchId=${R3}`);
        expect(reason(), c.name).toBeNull();
      } else {
        expect(exec(), c.name).toBeNull();
        expect(screen.getByTestId("execute-disabled"), c.name).toHaveAttribute("aria-disabled", "true");
        expect(reason(), c.name).toHaveAttribute("data-block", c.block);
        expect(reason(), c.name).toHaveTextContent(c.text);
      }
      // 專案頁（凍結與匯入）、監控中心恆為連結
      const links = within(screen.getByTestId("inner-loop-links"));
      expect(links.getByRole("link", { name: "專案頁（凍結與匯入）" }), c.name).toHaveAttribute("href", `/projects/${CONSOLE_PROJECT_ID}`);
      expect(links.getByRole("link", { name: "監控中心" }), c.name).toHaveAttribute("href", `/projects/${CONSOLE_PROJECT_ID}/monitor?researchId=${R3}`);
      view.unmount();
    }
  });

  it("AT_961_18_5 看板、自癒與終端屬 P2：內環鍵尚未採納（route 未成功）時本面板不渲染（P2 起內環啟動後才掛，見 AT_962_25_3 的整合測試）", async () => {
    renderPanel({ project: buildProject("BUILD_READY"), route: ROUTE_NOT_ADOPTED, decomposition: DECOMPOSITION_SIGNED });
    await screen.findByTestId("inner-loop-links");
    const panel = screen.getByTestId("build-front-panel");
    for (const word of ["看板", "自癒", "終端", "交付"]) expect(panel).not.toHaveTextContent(word);
    expect(screen.queryByTestId("inner-loop-section")).toBeNull();
  });

  it("AT_962_25_3a 內環鍵已採納：面板掛看板、自癒監視器、終端窗格與頁頂的發起規格變更（SCR）", async () => {
    renderPanel({ project: buildProject("BUILD_READY"), decomposition: DECOMPOSITION_SIGNED });
    const section = await screen.findByTestId("inner-loop-section");
    await within(section).findByTestId("kanban-board");
    expect(within(section).getByTestId("healing-monitor")).toBeInTheDocument();
    expect(within(section).getByTestId("terminal-pane")).toBeInTheDocument();
    expect(screen.getAllByTestId("scr-launch").length).toBeGreaterThanOrEqual(1);
  });

  it("AT_961_18_5 尚無 Console 專案：不給任何連結，說明分流完成後才會建立", async () => {
    renderPanel({ project: buildProject("ROUTED", "IDLE", { consoleProjectId: null }), route: ROUTE_NOT_ADOPTED, decomposition: null });
    expect(await screen.findByTestId("inner-loop-links")).toHaveTextContent("尚無 Console 專案");
    expect(screen.queryByRole("link", { name: "執行中心" })).toBeNull();
  });
});

describe("AT_961_18_6 SCR 開啟時本面板的操作停用", () => {
  it("AT_961_18_6 SCR_OPEN：顯示「規格變更中」橫幅與「SCR 進行中」標籤；觸發拆解、簽核、草擬測試規格皆停用並說明；沒有發起 SCR 的鈕", async () => {
    const project = buildProject("SCR_OPEN", "IDLE");
    const empty = renderPanel({ project, decomposition: null });
    expect(await screen.findByTestId("scr-banner")).toHaveTextContent("規格變更中");
    expect(screen.getByTestId("scr-badge")).toHaveTextContent("SCR 進行中");
    const trigger = await btn("觸發拆解");
    expect(trigger).toBeDisabled();
    expect(trigger.getAttribute("title")).toContain("規格變更中");
    empty.unmount();

    const { calls } = renderPanel({ project, decomposition: DECOMPOSITION_COVERED });
    const sign = await btn("簽核");
    expect(sign).toBeDisabled();
    expect(sign.getAttribute("title")).toContain("規格變更中");
    expect(screen.getByRole("button", { name: "草擬測試規格" })).toBeDisabled();
    expect(screen.getByTestId("tcs-disabled-reason")).toHaveTextContent("規格變更中");
    expect(screen.getByTestId("execute-block-reason")).toHaveAttribute("data-block", "scrOpen");
    // P2 起頁頂有「發起規格變更（SCR）」入口：規格變更進行中停用並顯示登記文案（不可再發起第二個）
    const launch = await screen.findByTestId("scr-launch");
    expect(launch).toBeDisabled();
    expect(launch.getAttribute("title")).toBe(BUILD_DISABLED_TEXT.scrOpen);
    expect(writeCalls(calls)).toEqual([]);
  });
});

describe("AT_961_18_7 Bridge 或 API 不可用：錯誤態與快取，不顯示空白", () => {
  it("AT_961_18_7 拆解與專案詳情都 502／504：拆解區顯示錯誤態與重試、專案詳情顯示過期提示；VIEWER 唯讀不送寫入", async () => {
    const { calls } = renderPanel({
      role: "VIEWER",
      decomposition: null,
      overrides: (call) => {
        if (call.method === "GET" && DECOMP_URL.test(call.path)) return failure(504, { message: "Bridge 逾時", reason: "bridge_timeout" });
        if (call.method === "GET" && call.path === `/api/v1/research/projects/${R3}`) return failure(502, { message: "Bridge 不可用", reason: "bridge_unreachable" });
        return undefined;
      },
    });
    expect(await screen.findByText("無法載入拆解")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "重試" }).length).toBeGreaterThanOrEqual(1);
    expect(await screen.findByTestId("project-error")).toHaveTextContent("流程狀態");
    expect(screen.getByTestId("build-front-panel")).toBeInTheDocument();
    expect(writeCalls(calls)).toEqual([]);
  });

  it("AT_961_18_7 先前載入成功、重抓失敗：保留舊資料並標示「資料可能過期」；重試成功後標示消失", async () => {
    const user = userEvent.setup();
    let failing = false;
    renderPanel({
      decomposition: DECOMPOSITION_DRAFT,
      overrides: (call) => (failing && call.method === "GET" && DECOMP_URL.test(call.path) ? failure(504, { message: "逾時" }) : undefined),
    });
    await screen.findByTestId("decomposition-tree");
    failing = true;
    // 觸發重抓：按「重新對帳」會重抓專案；拆解則由重新拆解的寫入後失效重抓（POST 成功後 GET 失敗）
    await user.click(screen.getByRole("button", { name: "重新拆解" }));
    expect(await screen.findByTestId("decomposition-stale-data")).toHaveTextContent("資料可能過期");
    expect(screen.getByTestId("decomposition-tree")).toBeInTheDocument();
    failing = false;
    await user.click(within(screen.getByTestId("decomposition-stale-data")).getByRole("button", { name: "重試" }));
    await waitFor(() => expect(screen.queryByTestId("decomposition-stale-data")).toBeNull());
  });
});

describe("AT_961_18_E_1 覆蓋矩陣在大型 PRD 下仍可渲染", () => {
  it("AT_961_18_E_1 200 個 AC 乘 24 個 task：渲染完成、列與欄皆有可及名稱；切換「只看未覆蓋」不超過 200 毫秒（量測值印出，未校準）", async () => {
    const user = userEvent.setup();
    renderPanel({ decomposition: bigDecomposition(200, 24) });
    const matrix = await screen.findByTestId("coverage-matrix");
    const rowHeaders = within(matrix).getAllByRole("rowheader");
    const colHeaders = within(matrix)
      .getAllByRole("columnheader")
      .filter((h) => h.getAttribute("aria-label")?.startsWith("任務 "));
    expect(rowHeaders).toHaveLength(200);
    expect(colHeaders).toHaveLength(24);
    for (const h of colHeaders) expect(h.getAttribute("aria-label")).toMatch(/^任務 T-\d+/);
    expect(screen.getByRole("region", { name: "覆蓋矩陣（可捲動）" })).toHaveAttribute("tabindex", "0");

    const toggle = screen.getByRole("button", { name: "只看未覆蓋" });
    const t0 = performance.now();
    await act(async () => {
      fireEvent.click(toggle);
    });
    const elapsed = performance.now() - t0;
    console.info(`[AT_961_18_E_1] 切換「只看未覆蓋」耗時 ${elapsed.toFixed(1)} ms（200 AC × 24 task，jsdom，未校準）`);
    expect(elapsed).toBeLessThan(200);
    expect(within(screen.getByTestId("coverage-matrix")).getAllByRole("rowheader")).toHaveLength(5);
    await user.click(screen.getByRole("button", { name: "顯示全部" }));
    expect(within(screen.getByTestId("coverage-matrix")).getAllByRole("rowheader")).toHaveLength(200);
  });
});

describe("AT_961_20_E_4 步驟 4 面板渲染對帳結果（P2：漂移橫幅整併到工作區單一 drift-banner，D-131(6)）", () => {
  it("AT_961_20_E_4 pending_correction：顯示「待校正」說明、無漂移警示橫幅；drift 與 NOT_EVALUABLE：面板不再自己渲染橫幅或說明（改歸工作區 drift-banner，見 AT_962_25_3）；皆保留「重新對帳」鈕", async () => {
    const user = userEvent.setup();
    const run = async (status: "pending_correction" | "drift" | "NOT_EVALUABLE") => {
      const view = renderPanel({
        project: buildProject("TCS_PENDING", "WAITING_HUMAN"),
        decomposition: DECOMPOSITION_WITH_TCS,
        overrides: (call) => (call.method === "POST" && RECONCILE_URL.test(call.path) ? { data: reconcileWith(status) } : undefined),
      });
      await user.click(await btn("重新對帳"));
      await waitFor(() => expect(callsOf(view.calls, "POST", RECONCILE_URL)).toHaveLength(1));
      return view;
    };

    const pending = await run("pending_correction");
    expect(await screen.findByTestId("build-reconcile-note")).toBeInTheDocument();
    expect(screen.getByTestId("reconcile-pending")).toHaveTextContent("待校正");
    expect(screen.queryByTestId("build-drift-banner")).toBeNull();
    expect(screen.getByRole("button", { name: "重新對帳" })).toBeEnabled();
    pending.unmount();

    const drift = await run("drift");
    await waitFor(() => expect(screen.getByRole("button", { name: "重新對帳" })).toBeEnabled());
    expect(screen.queryByTestId("build-drift-banner")).toBeNull();
    expect(screen.queryByTestId("drift-banner")).toBeNull(); // 面板自己不渲染；橫幅只在工作區
    expect(screen.queryByTestId("build-reconcile-note")).toBeNull();
    expect(screen.queryByTestId("reconcile-pending")).toBeNull();
    drift.unmount();

    const missing = await run("NOT_EVALUABLE");
    await waitFor(() => expect(screen.getByRole("button", { name: "重新對帳" })).toBeEnabled());
    expect(screen.queryByTestId("build-reconcile-note")).toBeNull();
    expect(screen.queryByTestId("build-drift-banner")).toBeNull();
    expect(screen.queryByTestId("reconcile-pending")).toBeNull();
    missing.unmount();
  });
});

describe("AT_962_25_3 兩處漂移橫幅整併為工作區單一橫幅（D-131(6)）", () => {
  const renderWorkspaceBuild = (cache: ReturnType<typeof reconcileWith> | null) => {
    nav.params = { researchId: R3 };
    nav.search = "step=build";
    stubResearchApi({ details: { [R3]: buildProject("BUILD_READY") }, route: ROUTE_ADOPTED, decomposition: DECOMPOSITION_SIGNED });
    const view = renderResearch(<ResearchWorkspaceView />, "OPERATOR");
    if (cache !== null) act(() => void view.client.setQueryData(qk.researchReconcile(R3), cache));
    return view;
  };

  it("AT_962_25_3 步驟 4 在對帳 drift：整個畫面只有一個 drift-banner、build-drift-banner 不存在；一致：兩者皆無；量不到：只有工作區的黃色橫幅", async () => {
    const drift = renderWorkspaceBuild(reconcileWith("drift"));
    await screen.findByTestId("build-front-panel");
    expect(await screen.findAllByTestId("drift-banner")).toHaveLength(1);
    expect(screen.getByTestId("drift-banner")).toHaveTextContent("檔案與資料庫不一致");
    expect(screen.queryByTestId("build-drift-banner")).toBeNull();
    drift.unmount();

    const ok = renderWorkspaceBuild(reconcileWith("ok"));
    await screen.findByTestId("build-front-panel");
    await new Promise((resolve) => setTimeout(resolve, 30));
    expect(screen.queryByTestId("drift-banner")).toBeNull();
    expect(screen.queryByTestId("build-drift-banner")).toBeNull();
    ok.unmount();

    const missing = renderWorkspaceBuild(reconcileWith("NOT_EVALUABLE"));
    await screen.findByTestId("build-front-panel");
    expect(await screen.findAllByTestId("drift-banner")).toHaveLength(1);
    expect(screen.getByTestId("drift-banner")).toHaveTextContent("無法比對的項目：狀態機與流程游標的對映");
    expect(screen.queryByTestId("build-drift-banner")).toBeNull();
    missing.unmount();
  });

  it("AT_962_25_3 原始碼：BuildFrontPanel 不再含 build-drift-banner；工作區 ResearchWorkspaceView 恰一處 drift-banner", () => {
    const dir = path.resolve(process.cwd(), "components", "domain", "research");
    const panel = readFileSync(path.join(dir, "BuildFrontPanel.tsx"), "utf8");
    const workspace = readFileSync(path.join(dir, "ResearchWorkspaceView.tsx"), "utf8");
    expect(panel).not.toContain("build-drift-banner");
    expect(workspace.match(/data-testid="drift-banner"/g)).toHaveLength(1);
  });
});
describe("AT_961_25_4 步驟 4 面板的「重新對帳」", () => {
  it("AT_961_25_4 TCS 已在既有流程凍結而游標仍待凍結：OPERATOR 按下送一次 POST …/reconcile，回應後重抓專案詳情並顯示「可開始建置」；不呼叫任何其他寫入端點", async () => {
    const user = userEvent.setup();
    // 假後端的「對帳後游標被 Bridge 校正」：POST reconcile 一到就換掉詳情回放（活物件 options.details）
    const holder: { details?: Record<string, ResearchProjectDetail> } = {};
    const api = renderPanel({
      project: buildProject("TCS_PENDING", "WAITING_HUMAN"),
      decomposition: DECOMPOSITION_WITH_TCS,
      overrides: (call) => {
        if (call.method === "POST" && RECONCILE_URL.test(call.path) && holder.details) {
          holder.details[R3] = buildProject("BUILD_READY");
          return { data: reconcileWith("ok") };
        }
        return undefined;
      },
    });
    holder.details = api.options.details;
    expect(await screen.findByTestId("build-phase")).toHaveTextContent("測試規格待核准");
    await user.click(await btn("重新對帳"));
    await waitFor(() => expect(screen.getByTestId("build-phase")).toHaveTextContent("可開始建置"));
    const writes = writeCalls(api.calls);
    expect(writes.map((c) => `${c.method} ${c.path}`)).toEqual([`POST /api/v1/research/projects/${R3}/reconcile`]);
    expect(screen.getByTestId("tcs-card")).toHaveAttribute("data-stage", "frozen");
  });

  it("AT_961_25_4 VIEWER：「重新對帳」停用且 title 為權限不足，不送請求", async () => {
    const { calls } = renderPanel({ role: "VIEWER", project: buildProject("TCS_PENDING", "WAITING_HUMAN"), decomposition: DECOMPOSITION_WITH_TCS });
    const reconcile = await btn("重新對帳");
    expect(reconcile).toBeDisabled();
    expect(reconcile.getAttribute("title")).toContain("權限不足");
    expect(callsOf(calls, "POST", RECONCILE_URL)).toHaveLength(0);
  });

  it("AT_961_25_4 請求失敗：顯示錯誤文字，可再按一次重試", async () => {
    const user = userEvent.setup();
    let ok = false;
    const { calls } = renderPanel({
      project: buildProject("TCS_PENDING", "WAITING_HUMAN"),
      decomposition: DECOMPOSITION_WITH_TCS,
      overrides: (call) => (call.method === "POST" && RECONCILE_URL.test(call.path) && !ok ? failure(502, { message: "Bridge 不可用", reason: "bridge_unreachable" }) : undefined),
    });
    await user.click(await btn("重新對帳"));
    expect(await screen.findByTestId("reconcile-error")).toHaveTextContent("連不上 Engine Bridge");
    expect(screen.getByRole("button", { name: "重新對帳" })).toBeEnabled();
    ok = true;
    await user.click(screen.getByRole("button", { name: "重新對帳" }));
    await waitFor(() => expect(screen.queryByTestId("reconcile-error")).toBeNull());
    expect(callsOf(calls, "POST", RECONCILE_URL)).toHaveLength(2);
  });
});
