import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import path from "node:path";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ResearchWorkspacePage, { metadata as workspacePageMetadata } from "@/app/research/[researchId]/page";
import { qk, usePrdVersions, useResearchEvidence, useReviewRounds } from "@/lib/api/queries";
import type { ResearchFlowStepId, ResearchProjectDetail, Role } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { FLOW_PHASE_LABEL, FLOW_STATUS_LABEL, FLOW_STEP_IDS, FLOW_STEP_LABEL, READONLY_TITLE, RECONCILE_CHECK_LABEL, reconcileDriftView, resolveViewStep, stepReachable } from "@/lib/domain/research";
import { R1, R2, R3, sha } from "@/tests/fixtures/research/ids";
import { RECONCILE_DRIFT, RECONCILE_OK } from "@/tests/fixtures/research/misc";
import { detailVariant } from "@/tests/fixtures/research/projects";
import { failure, renderResearch, stubResearchApi, writeCalls, callsOf } from "@/tests/helpers/research";
import { ResearchWorkspaceView, type ResearchPanelProps, type ResearchPanels } from "./ResearchWorkspaceView";

/**
 * 研究工作區殼層（TCS-ResearchToPRD-P0-20261102 AT-960-19-4、19-5、19-6、19-E-2、21-6；AC-R2P-01-2、01-4、01-5、01-7、01-8、21-5、23-2；ADR-003 D5）：
 * 網址 `?step=` 超前導回游標所在步、已完成步驟唯讀檢視、步驟 3～5 占位面板、VIEWER 全面停用、游標取自 API 而非瀏覽器儲存、對帳漂移橫幅只顯示不修。
 * 步驟 1、2 的真面板（議題面板、PRD 工作室）由另兩個包交付、在波次二接進頁殼，所以本檔以**替身面板**經 `panels` 屬性注入——殼層的契約是
 * 「傳對屬性（researchId、project、completed）、在對的步驟顯示、已完成與 VIEWER 兩種唯讀互不取代」，替身只需照這份契約停用自己的寫入鈕。
 * 判定指令：npx vitest run components/domain/research/ResearchWorkspaceView.test.tsx -t "<AT 底線形>"
 */
const nav = vi.hoisted(() => {
  const router = { push: vi.fn(), replace: vi.fn(), back: vi.fn() };
  return { router, params: {} as { researchId?: string | string[] }, search: "" };
});
vi.mock("next/navigation", () => ({
  // 與 Next 一樣回傳穩定的 router 物件（工作區的導回 effect 以它為相依）
  useRouter: () => nav.router,
  useParams: () => nav.params,
  usePathname: () => `/research/${String(nav.params.researchId)}`,
  useSearchParams: () => new URLSearchParams(nav.search),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

// ── 替身面板（照殼層契約停用自己的寫入鈕）─────────────────────────────────────────────────

function TopicStub({ researchId, project, completed }: ResearchPanelProps) {
  const { canWrite } = useAuth();
  return (
    <div data-testid="topic-stub" data-research-id={researchId} data-project-id={project.id} data-completed={String(completed)}>
      <span>議題面板替身 {project.rpNo}</span>
      <button type="button" disabled={completed || !canWrite} title={canWrite ? undefined : READONLY_TITLE}>
        啟動深研
      </button>
    </div>
  );
}

/** 以真的查詢 hook 讀 PRD 版本、審查輪、證據列：驗證「已存產物取自 API、殼層傳對 researchId」。 */
function StudioStub({ researchId, completed }: ResearchPanelProps) {
  const { canWrite } = useAuth();
  const versions = usePrdVersions(researchId);
  const rounds = useReviewRounds(researchId);
  const evidence = useResearchEvidence(researchId);
  return (
    <div data-testid="studio-stub" data-research-id={researchId} data-completed={String(completed)}>
      <p data-testid="stub-versions">{versions.data ? `PRD 版本 ${versions.data.length} 個` : "載入中"}</p>
      <p data-testid="stub-rounds">{rounds.data ? `審查 ${rounds.data.length} 輪` : "載入中"}</p>
      <p data-testid="stub-evidence">{evidence.data ? `證據 ${evidence.data.items.length} 列` : "載入中"}</p>
      <button type="button" disabled={completed || !canWrite} title={canWrite ? undefined : READONLY_TITLE}>
        送出審查
      </button>
    </div>
  );
}

const PANELS: ResearchPanels = { topic: TopicStub, studio: StudioStub };

type StubPatch = Parameters<typeof stubResearchApi>[0];

function renderWorkspace(opts: { id?: string | string[]; search?: string; role?: Role; stub?: StubPatch; panels?: ResearchPanels | null } = {}) {
  // 明確傳入 undefined 代表「網址沒有編號」，不要被預設值蓋掉
  nav.params = { researchId: "id" in opts ? opts.id : R2 };
  nav.search = opts.search ?? "";
  const api = stubResearchApi(opts.stub);
  const view = renderResearch(<ResearchWorkspaceView panels={opts.panels === null ? undefined : (opts.panels ?? PANELS)} />, opts.role ?? "OPERATOR");
  return { ...view, ...api };
}

/** 游標在第 3 步（Gate 0 已核准）、最遠到第 5 步：三個占位步驟與已完成的前兩步都可達。 */
const frozenFurthestDeliver = (): ResearchProjectDetail => {
  const base = detailVariant("frozen");
  return { ...base, flow: { ...base.flow, furthestStep: "deliver" } };
};

const workspace = () => screen.getByTestId("research-workspace");
const REPLACE = (id: string, step: ResearchFlowStepId) => `/research/${id}?step=${step}`;

beforeEach(() => {
  nav.router.push.mockClear();
  nav.router.replace.mockClear();
  nav.params = {};
  nav.search = "";
});
afterEach(() => {
  // tests/setup.ts 只清 sessionStorage；矛盾游標的測試塞過 localStorage，不能漏到別的測試
  window.localStorage.clear();
});

// ── AT_960_19_4：超前導回、已完成步驟唯讀 ─────────────────────────────────────────────────

/** 游標與最遠步都在 studio：每個網址參數該顯示哪一步、要不要導回。 */
const STEP_TABLE: ReadonlyArray<{ search: string; viewed: ResearchFlowStepId; replace: ResearchFlowStepId | null; completed: boolean }> = [
  { search: "step=deliver", viewed: "studio", replace: "studio", completed: false },
  { search: "step=build", viewed: "studio", replace: "studio", completed: false },
  { search: "step=route", viewed: "studio", replace: "studio", completed: false },
  { search: "step=topic", viewed: "topic", replace: null, completed: true },
  { search: "step=studio", viewed: "studio", replace: null, completed: false },
  { search: "", viewed: "studio", replace: "studio", completed: false },
  { search: "step=", viewed: "studio", replace: "studio", completed: false },
  { search: "step=bogus", viewed: "studio", replace: "studio", completed: false },
  { search: "step=TOPIC", viewed: "studio", replace: "studio", completed: false },
];

describe("AT_960_19_4 網址 step 超前導回游標所在步；已完成步驟為唯讀檢視", () => {
  it.each(STEP_TABLE)("AT_960_19_4 游標與最遠步在 studio、網址「?$search」→ 顯示 $viewed 步，導回＝$replace，唯讀檢視＝$completed", async ({ search, viewed, replace, completed }) => {
    renderWorkspace({ search });
    await screen.findByTestId("research-workspace");
    expect(workspace()).toHaveAttribute("data-step", viewed);
    expect(screen.getByTestId(`research-panel-${viewed}`)).toBeInTheDocument();
    if (replace === null) {
      await new Promise((resolve) => setTimeout(resolve, 30));
      expect(nav.router.replace, "合法且可達的網址不導回").not.toHaveBeenCalled();
    } else {
      await waitFor(() => expect(nav.router.replace).toHaveBeenCalledTimes(1));
      expect(nav.router.replace).toHaveBeenCalledWith(REPLACE(R2, replace));
    }
    expect(nav.router.push, "導回用 replace，不留無效網址在歷史").not.toHaveBeenCalled();
    if (completed) expect(screen.getByTestId("completed-readonly-banner")).toHaveTextContent("已完成，唯讀");
    else expect(screen.queryByTestId("completed-readonly-banner")).toBeNull();
  });

  it("AT_960_19_4 stepReachable／resolveViewStep 純函式表驅動得到同樣結果（游標與最遠步都在 studio）", () => {
    for (const { search, viewed, replace } of STEP_TABLE) {
      const param = new URLSearchParams(search).get("step");
      const resolved = resolveViewStep(param, "studio", "studio");
      expect(resolved, `?${search}`).toEqual({ step: viewed, redirect: replace !== null });
    }
    expect(FLOW_STEP_IDS.map((step) => stepReachable(step, "studio"))).toEqual([true, true, false, false, false]);
    expect(FLOW_STEP_IDS.map((step) => stepReachable(step, "deliver"))).toEqual([true, true, true, true, true]);
    expect(FLOW_STEP_IDS.map((step) => stepReachable(step, "topic"))).toEqual([true, false, false, false, false]);
  });

  it("AT_960_19_4 唯讀檢視已完成的 topic 步：替身面板收到 completed、寫入鈕停用；「對帳」鈕也停用（說明請回游標所在步）；回到游標所在步後恢復", async () => {
    renderWorkspace({ search: "step=topic" });
    await screen.findByTestId("topic-stub");
    expect(screen.getByTestId("topic-stub")).toHaveAttribute("data-completed", "true");
    for (const button of within(workspace()).getAllByRole("button")) expect(button, `「${button.textContent}」`).toBeDisabled();
    expect(screen.getByRole("button", { name: "對帳" })).toHaveAttribute("title", "這一步已完成，唯讀；請回到游標所在步再對帳");
  });

  it("AT_960_19_4 游標所在步不是唯讀：替身面板收到 completed=false、寫入鈕與「對帳」鈕啟用（OPERATOR）", async () => {
    renderWorkspace({ search: "step=studio" });
    await screen.findByTestId("studio-stub");
    expect(screen.getByTestId("studio-stub")).toHaveAttribute("data-completed", "false");
    expect(screen.getByRole("button", { name: "送出審查" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "對帳" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "對帳" })).toHaveAttribute("title", "比對檔案、資料庫與狀態機是否一致（只報告，不修正）");
  });

  it("AT_960_19_4 步驟列：可達的步驟（不超前於最遠步）是連結且帶 ?step=、超前的只顯示文字；目前顯示的那一步標 aria-current", async () => {
    renderWorkspace({ search: "step=studio" });
    await screen.findByTestId("studio-stub");
    const stepper = screen.getByTestId("flow-stepper");
    const links = within(stepper).getAllByRole("link");
    expect(links.map((a) => a.getAttribute("href"))).toEqual([REPLACE(R2, "topic"), REPLACE(R2, "studio")]);
    expect(links[1]).toHaveAttribute("aria-current", "step");
    expect(links[0]).not.toHaveAttribute("aria-current");
    for (const id of ["route", "build", "deliver"] as const) expect(within(screen.getByTestId(`flow-step-${id}`)).queryByRole("link")).toBeNull();
    // 游標步（studio）進行中、topic 已完成
    expect(screen.getByTestId("flow-step-topic")).toHaveAttribute("data-state", "DONE");
    expect(screen.getByTestId("flow-step-studio")).toHaveAttribute("data-state", "CURRENT");
  });

  it("AT_960_19_4 最遠步在游標之後（例如退回修改後）：超前於游標、但不超前於最遠步的步驟可達，不導回", async () => {
    const base = detailVariant("studio");
    renderWorkspace({ search: "step=deliver", stub: { details: { [R2]: { ...base, flow: { ...base.flow, furthestStep: "deliver" } } } } });
    await screen.findByTestId("research-placeholder");
    expect(workspace()).toHaveAttribute("data-step", "deliver");
    await new Promise((resolve) => setTimeout(resolve, 30));
    expect(nav.router.replace).not.toHaveBeenCalled();
  });

  it("AT_960_19_4 網址的研究專案編號為陣列時取第一個；缺編號時顯示錯誤、不送請求", async () => {
    const first = renderWorkspace({ id: [R2, "extra"] });
    await screen.findByTestId("research-workspace");
    expect(first.calls.some((c) => c.path === `/api/v1/research/projects/${R2}`)).toBe(true);
    first.unmount();

    const none = renderWorkspace({ id: undefined });
    expect(await screen.findByText("缺少研究專案編號")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("無法載入研究專案");
    expect(none.calls.filter((c) => c.path.startsWith("/api/v1/research/projects/"))).toEqual([]);
  });
});

// ── AT_960_19_5：步驟 3～5 占位面板 ────────────────────────────────────────────────────

describe("AT_960_19_5 步驟 5 為占位面板（P1 起；步驟 3、4 已是真面板）：說明、唯讀、無寫入、回游標步連結，不假裝有執行中心連結", () => {
  // P1 起只有步驟 5 仍是占位面板；步驟 3、4 改驗真面板（AT_961_19_1；TCS-ResearchToPRD-P1-20261107 §4 第 25 列）
  const PLACEHOLDERS: ReadonlyArray<{ step: ResearchFlowStepId; heading: string }> = [{ step: "deliver", heading: "第 5 步：交付" }];
  const AHEAD_STEPS: readonly { step: ResearchFlowStepId }[] = [{ step: "route" }, { step: "build" }, { step: "deliver" }];

  it.each(PLACEHOLDERS)(
    "AT_960_19_5 Gate 0 已核准（可達）、網址 ?step=$step：顯示「$heading」、「本步驟於後續階段提供」、目前進度、回到游標所在步連結；沒有任何寫入按鈕與表單",
    async ({ step, heading }) => {
      renderWorkspace({ id: R3, search: `step=${step}`, stub: { details: { [R3]: frozenFurthestDeliver() } } });
      const panel = await screen.findByTestId("research-placeholder");
      expect(panel).toHaveAttribute("data-step", step);
      expect(screen.getByTestId(`research-panel-${step}`)).toBeInTheDocument();
      expect(within(panel).getByRole("heading", { name: heading })).toBeInTheDocument();
      expect(panel).toHaveTextContent("本步驟於後續階段提供");
      expect(panel).toHaveTextContent(`目前進度：第 3 步「${FLOW_STEP_LABEL.route}」，${FLOW_PHASE_LABEL.FROZEN}（${FLOW_STATUS_LABEL.IDLE}）。`);
      expect(within(panel).getByRole("link", { name: "回到游標所在步" })).toHaveAttribute("href", REPLACE(R3, "route"));
      // 占位面板唯讀：沒有按鈕、表單、輸入控件
      expect(within(panel).queryAllByRole("button")).toHaveLength(0);
      expect(panel.querySelector("form, input, textarea, select")).toBeNull();
      // 不假裝有執行中心或監控中心的連結（那是 P2 的 ResearchBackLink）；整個工作區都沒有
      for (const link of within(workspace()).queryAllByRole("link")) {
        expect(link.getAttribute("href") ?? "", "連結不指向執行中心或監控中心").not.toMatch(/\/execute|\/monitor/);
        expect(link.textContent ?? "").not.toMatch(/開啟執行中心|開啟監控中心|執行中心|監控中心/);
      }
      expect(workspace().textContent).not.toMatch(/ResearchBackLink|開啟執行中心|開啟監控中心/);
      // 網址合法、可達：不導回
      expect(nav.router.replace).not.toHaveBeenCalled();
    },
  );

  it.each(AHEAD_STEPS)("AT_960_19_5 游標在 studio（步驟 $step 超前）：導回游標所在步，不顯示占位面板（超前不可達）", async ({ step }) => {
    renderWorkspace({ search: `step=${step}` });
    await screen.findByTestId("studio-stub");
    await waitFor(() => expect(nav.router.replace).toHaveBeenCalledWith(REPLACE(R2, "studio")));
    expect(screen.queryByTestId("research-placeholder")).toBeNull();
  });

  it("AT_960_19_5 占位面板的目前進度取自後端衍生的相態：游標在 studio 且最遠步到 deliver 時，進度寫「第 2 步」並連回 studio", async () => {
    const base = detailVariant("studio");
    renderWorkspace({ search: "step=deliver", stub: { details: { [R2]: { ...base, flow: { ...base.flow, furthestStep: "deliver" } } } } });
    const panel = await screen.findByTestId("research-placeholder");
    expect(panel).toHaveTextContent(`目前進度：第 2 步「${FLOW_STEP_LABEL.studio}」，${FLOW_PHASE_LABEL.DRAFTING}（${FLOW_STATUS_LABEL.IDLE}）。`);
    expect(within(panel).getByRole("link", { name: "回到游標所在步" })).toHaveAttribute("href", REPLACE(R2, "studio"));
  });

  it("AT_960_19_5 沒有注入面板的步驟 1、2 顯示「這一步的操作面板尚未接入。」，不是空白", async () => {
    renderWorkspace({ search: "step=studio", panels: null });
    expect(await screen.findByTestId("research-panel-missing")).toHaveTextContent("這一步的操作面板尚未接入。");
    expect(screen.getByTestId("research-panel-studio")).toBeInTheDocument();
  });
});

// ── AT_961_19_1：步驟 3、4 接真面板 ─────────────────────────────────────────────────────

describe("AT_961_19_1 ?step=route 與 ?step=build 不再是占位，?step=deliver 仍為占位；Gate 0 未完成時超前導回", () => {
  it("AT_961_19_1 Gate 0 已核准（最遠到第 5 步）：route 顯示 RoutePanel、build 顯示 BuildFrontPanel，兩者都沒有 research-placeholder；deliver 仍是占位面板", async () => {
    const route = renderWorkspace({ id: R3, search: "step=route", stub: { details: { [R3]: frozenFurthestDeliver() } } });
    expect(await screen.findByTestId("route-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("research-placeholder")).toBeNull();
    route.unmount();

    const build = renderWorkspace({ id: R3, search: "step=build", stub: { details: { [R3]: frozenFurthestDeliver() } } });
    expect(await screen.findByTestId("build-front-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("research-placeholder")).toBeNull();
    build.unmount();

    renderWorkspace({ id: R3, search: "step=deliver", stub: { details: { [R3]: frozenFurthestDeliver() } } });
    const placeholder = await screen.findByTestId("research-placeholder");
    expect(placeholder).toHaveTextContent("本步驟於後續階段提供");
    expect(within(placeholder).queryAllByRole("button")).toHaveLength(0);
  });

  it("AT_961_19_1 游標在 studio（外環未凍結）：?step=route 導回 studio，不顯示 RoutePanel（超前不可達）", async () => {
    renderWorkspace({ search: "step=route" });
    await screen.findByTestId("studio-stub");
    await waitFor(() => expect(nav.router.replace).toHaveBeenCalledWith(REPLACE(R2, "studio")));
    expect(screen.queryByTestId("route-panel")).toBeNull();
    expect(screen.queryByTestId("research-placeholder")).toBeNull();
  });

  it("AT_961_19_1 分流執行中（ROUTING／RUNNING）步驟 3 為進行中；SCR_OPEN 時步驟列尾端標示「SCR 進行中」", async () => {
    const base = detailVariant("frozen");
    const routing = { ...base, flowPhase: "ROUTING", flowStatus: "RUNNING" as const, flow: { ...base.flow, effective: { ...base.flow.effective, phase: "ROUTING", status: "RUNNING" as const } } };
    const view = renderWorkspace({ id: R3, search: "step=route", stub: { details: { [R3]: routing } } });
    await screen.findByTestId("route-panel");
    expect(screen.getByTestId("flow-step-route")).toHaveAttribute("data-state", "CURRENT");
    expect(FLOW_PHASE_LABEL.ROUTING).toBe("分流中");
    view.unmount();
    const scr = { ...base, flow: { ...base.flow, effective: { ...base.flow.effective, phase: "SCR_OPEN" } } };
    renderWorkspace({ id: R3, search: "step=route", stub: { details: { [R3]: scr } } });
    await screen.findByTestId("route-panel");
    expect(screen.getByTestId("flow-scr-open")).toHaveTextContent("SCR 進行中");
  });
});
// ── AT_960_19_6：VIEWER ───────────────────────────────────────────────────────────────

describe("AT_960_19_6 VIEWER 於每個步驟都可讀，所有寫入與推進動作停用且 title 為權限不足", () => {
  it.each(FLOW_STEP_IDS.map((step) => [step] as const))(
    "AT_960_19_6 VIEWER、Gate 0 已核准且最遠步到 deliver、?step=%s：步驟列與面板可見；殼層與面板的每個按鈕都停用，title 為「權限不足（唯讀角色）」",
    async (step) => {
      renderWorkspace({ id: R3, search: `step=${step}`, role: "VIEWER", stub: { details: { [R3]: frozenFurthestDeliver() } } });
      await screen.findByTestId(`research-panel-${step}`);
      expect(screen.getByTestId("flow-stepper")).toBeInTheDocument();
      expect(screen.getByTestId("research-flow-header")).toBeInTheDocument();
      if (step === "route") await screen.findByTestId("route-panel");
      const buttons = within(workspace()).getAllByRole("button");
      expect(buttons.length, "至少有「對帳」鈕").toBeGreaterThanOrEqual(1);
      for (const button of buttons) {
        expect(button, `「${button.textContent}」`).toBeDisabled();
        expect(button, `「${button.textContent}」的 title`).toHaveAttribute("title", "權限不足（唯讀角色）");
      }
      expect(within(workspace()).queryAllByRole("textbox")).toHaveLength(0);
      // 可讀：替身面板（步驟 1、2）與占位面板（步驟 3～5）的內容都在
      if (step === "topic") expect(screen.getByTestId("topic-stub")).toBeInTheDocument();
      if (step === "studio") await waitFor(() => expect(screen.getByTestId("stub-versions")).toHaveTextContent("PRD 版本 2 個"));
      if (step === "route") expect(screen.getByTestId("route-panel")).toBeInTheDocument();
      if (step === "build") expect(screen.getByTestId("build-front-panel")).toBeInTheDocument();
      if (step === "deliver") expect(screen.getByTestId("research-placeholder")).toBeInTheDocument();
    },
  );

  it("AT_960_19_6 VIEWER 在游標所在步（非已完成）：替身面板的寫入鈕同樣因唯讀角色停用——兩種唯讀（已完成、角色）各自成立，互不取代", async () => {
    renderWorkspace({ search: "step=studio", role: "VIEWER" });
    await screen.findByTestId("studio-stub");
    expect(screen.getByTestId("studio-stub")).toHaveAttribute("data-completed", "false");
    expect(screen.getByRole("button", { name: "送出審查" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "送出審查" })).toHaveAttribute("title", "權限不足（唯讀角色）");
    expect(screen.getByRole("button", { name: "對帳" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "對帳" })).toHaveAttribute("title", "權限不足（唯讀角色）");
    expect(screen.queryByTestId("completed-readonly-banner")).toBeNull();
  });

  it("AT_960_19_6 VIEWER 點被停用的鈕不送任何寫入請求", async () => {
    const user = userEvent.setup();
    const { calls } = renderWorkspace({ search: "step=studio", role: "VIEWER" });
    await screen.findByTestId("studio-stub");
    await user.click(screen.getByRole("button", { name: "對帳" }));
    await user.click(screen.getByRole("button", { name: "送出審查" }));
    expect(writeCalls(calls)).toEqual([]);
  });
});

// ── AT_960_19_E_2：游標取自 API，不取自瀏覽器儲存 ───────────────────────────────────────

const CONTRADICTORY_KEYS = ["step", "flowStep", "research.step", "research-step", "researchStep", "lastStep", `research:${R2}`, `research.${R2}.step`, `step:${R2}`];

function seedContradictoryBrowserStorage(): void {
  for (const key of CONTRADICTORY_KEYS) {
    window.localStorage.setItem(key, "deliver");
    window.sessionStorage.setItem(key, "deliver");
  }
  window.localStorage.setItem("research", JSON.stringify({ [R2]: { step: "deliver", furthestStep: "deliver" } }));
}

describe("AT_960_19_E_2 離開再回來：游標取自 API 而非瀏覽器儲存，已存產物完整", () => {
  it.each([
    ["瀏覽器儲存是空的", () => window.localStorage.clear()],
    ["瀏覽器儲存塞滿矛盾的游標（deliver）", seedContradictoryBrowserStorage],
  ])("AT_960_19_E_2 %s：渲染兩次都顯示 API 回的 studio 步，已存的 PRD 版本、審查輪、證據列完整可見", async (_name, prepare) => {
    prepare();
    for (let visit = 1; visit <= 2; visit += 1) {
      const { unmount } = renderWorkspace({});
      await screen.findByTestId("studio-stub");
      expect(workspace(), `第 ${visit} 次`).toHaveAttribute("data-step", "studio");
      await waitFor(() => expect(screen.getByTestId("stub-versions")).toHaveTextContent("PRD 版本 2 個"));
      await waitFor(() => expect(screen.getByTestId("stub-rounds")).toHaveTextContent("審查 3 輪"));
      await waitFor(() => expect(screen.getByTestId("stub-evidence")).toHaveTextContent("證據 2 列"));
      await waitFor(() => expect(nav.router.replace).toHaveBeenCalledWith(REPLACE(R2, "studio")));
      expect(nav.router.replace, "矛盾的瀏覽器值沒有影響導向").not.toHaveBeenCalledWith(REPLACE(R2, "deliver"));
      unmount();
      nav.router.replace.mockClear();
    }
  });

  it("AT_960_19_E_2 localStorage 不可用（讀取即丟例外）時頁面仍正常顯示", async () => {
    const original = Object.getOwnPropertyDescriptor(window, "localStorage");
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      get() {
        throw new DOMException("denied", "SecurityError");
      },
    });
    try {
      expect(() => window.localStorage).toThrow();
      renderWorkspace({});
      await screen.findByTestId("studio-stub");
      expect(workspace()).toHaveAttribute("data-step", "studio");
      await waitFor(() => expect(screen.getByTestId("stub-versions")).toHaveTextContent("PRD 版本 2 個"));
    } finally {
      if (original) Object.defineProperty(window, "localStorage", original);
      else delete (window as unknown as Record<string, unknown>).localStorage;
    }
  });

  it("AT_960_19_E_2 原始碼不讀不寫瀏覽器儲存（localStorage、sessionStorage、cookie）", () => {
    const source = readFileSync(path.join(process.cwd(), "components", "domain", "research", "ResearchWorkspaceView.tsx"), "utf-8");
    // 註解會提到「不讀也不寫 localStorage」，只掃去掉註解後的程式碼
    const code = source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
    expect(code).not.toMatch(/localStorage|sessionStorage|document\.cookie/);
  });
});

// ── AT_960_21_6：對帳漂移橫幅 ───────────────────────────────────────────────────────────

describe("AT_960_21_6 漂移橫幅：以資料庫為準、紅色提示檔名、不送出任何寫入請求", () => {
  it("AT_960_21_6 對帳結果含 drift（一個 PRD sha 不符、一個 FSM 對映不合）：紅色「檔案與資料庫不一致」、檔名與雙方 sha 前 8 碼、對映警示；橫幅沒有任何動作鈕；渲染期間沒有任何寫入請求", async () => {
    const { client, calls } = renderWorkspace({ search: "step=studio" });
    await screen.findByTestId("studio-stub");
    expect(screen.queryByTestId("drift-banner"), "沒有對帳結果時沒有橫幅").toBeNull();

    act(() => {
      client.setQueryData(qk.researchReconcile(R2), RECONCILE_DRIFT);
    });
    const banner = await screen.findByTestId("drift-banner");
    expect(banner).toHaveAttribute("role", "alert");
    expect(banner).toHaveAttribute("data-drift", "true");
    expect(banner).toHaveTextContent("檔案與資料庫不一致");
    expect(banner).toHaveTextContent("畫面上的內容一律取自資料庫版本");
    expect(banner).toHaveTextContent("不會自動修正任何一邊");
    // 檔名與雙方 sha256（前 8 碼）：資料庫在前、檔案在後
    const files = within(banner).getByTestId("drift-files");
    expect(files).toHaveTextContent("01_specs/PRD-v0.2.0-draft.md");
    expect(files).toHaveTextContent("PRD 檔案");
    expect(files).toHaveTextContent("資料庫 22222222，檔案 99999999");
    // FSM 對映不合另顯示對映警示（不是檔案列）
    expect(within(banner).getByTestId("fsm-mapping-warning")).toHaveTextContent("狀態機的現態與流程游標的對映不合");
    expect(files).not.toHaveTextContent("FSM-STATE-research-vector-db.yaml");
    // 沒有任何「修正」類動作（橫幅文字只說「不會自動修正」，沒有可按的東西）
    expect(within(banner).queryAllByRole("button")).toHaveLength(0);
    expect(within(banner).queryAllByRole("link")).toHaveLength(0);
    expect(within(banner).queryAllByRole("checkbox")).toHaveLength(0);
    expect(banner.textContent).not.toMatch(/以檔案為準|覆寫資料庫/);
    // 渲染期間（含橫幅顯示後）沒有任何寫入請求，也沒有打過對帳端點
    expect(writeCalls(calls)).toEqual([]);
    expect(calls.some((c) => c.path.endsWith("/reconcile"))).toBe(false);
  });

  it("AT_960_21_6 對帳全一致：不渲染橫幅", async () => {
    const { client } = renderWorkspace({ search: "step=studio" });
    await screen.findByTestId("studio-stub");
    act(() => {
      client.setQueryData(qk.researchReconcile(R2), RECONCILE_OK);
    });
    await new Promise((resolve) => setTimeout(resolve, 30));
    expect(screen.queryByTestId("drift-banner")).toBeNull();
  });

  it("AT_960_21_6 只有「量不到」（NOT_EVALUABLE）的檢查：不判成一致也不判成漂移——顯示黃色「對帳沒有完成」並列出量不到的項目，不顯示紅色不一致", async () => {
    const { client } = renderWorkspace({ search: "step=studio" });
    await screen.findByTestId("studio-stub");
    act(() => {
      client.setQueryData(qk.researchReconcile(R2), {
        consistent: false,
        checks: [
          { name: "fsm_flow_mapping", status: "NOT_EVALUABLE" },
          { name: "prd_sha256", status: "ok" },
        ],
      });
    });
    const banner = await screen.findByTestId("drift-banner");
    expect(banner).toHaveTextContent("對帳沒有完成");
    expect(banner).toHaveTextContent("無法比對的項目：狀態機與流程游標的對映");
    expect(banner).not.toHaveTextContent("檔案與資料庫不一致");
    expect(banner).not.toHaveAttribute("data-drift");
    expect(within(banner).queryByTestId("fsm-mapping-warning")).toBeNull();
  });

  it("AT_960_21_6 按「對帳」才送 POST（恰一次）：回傳含 drift 時橫幅出現並提示；回傳一致時顯示一致提示、沒有橫幅", async () => {
    const user = userEvent.setup();
    let result = RECONCILE_DRIFT;
    const { calls } = renderWorkspace({
      search: "step=studio",
      stub: { overrides: (c) => (c.method === "POST" && c.path === `/api/v1/research/projects/${R2}/reconcile` ? { data: result } : undefined) },
    });
    await screen.findByTestId("studio-stub");
    expect(callsOf(calls, "POST", /reconcile$/), "進頁不自動對帳").toHaveLength(0);

    await user.click(screen.getByRole("button", { name: "對帳" }));
    expect(await screen.findByText("對帳完成：發現不一致，請看頁面上方的提示")).toBeInTheDocument();
    expect(await screen.findByTestId("drift-banner")).toHaveTextContent("檔案與資料庫不一致");
    expect(callsOf(calls, "POST", /reconcile$/)).toHaveLength(1);
    expect(writeCalls(calls)).toHaveLength(1);

    result = RECONCILE_OK;
    await user.click(screen.getByRole("button", { name: "對帳" }));
    expect(await screen.findByText("對帳完成：檔案、資料庫與狀態機一致")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByTestId("drift-banner"), "新結果一致時舊的紅色提示要消失").toBeNull());
    expect(callsOf(calls, "POST", /reconcile$/)).toHaveLength(2);
  });

  it("AT_960_21_6 之後有別的寫入成功：舊的對帳結果被丟掉、橫幅消失（過期的紅色提示比沒有提示更糟）；對帳端點沒有被重打", async () => {
    const user = userEvent.setup();
    const { client, calls, options } = renderWorkspace({ id: R1, search: "step=topic", stub: { details: { [R1]: detailVariant("initFailed") } } });
    const initBanner = await screen.findByTestId("init-failed-banner");
    act(() => {
      client.setQueryData(qk.researchReconcile(R1), RECONCILE_DRIFT);
    });
    expect(await screen.findByTestId("drift-banner")).toBeInTheDocument();

    options.details[R1] = detailVariant("topicReady");
    await user.click(within(initBanner).getByRole("button", { name: "重試初始化" }));
    await waitFor(() => expect(screen.queryByTestId("drift-banner")).toBeNull());
    expect(client.getQueryData(qk.researchReconcile(R1))).toBeUndefined();
    expect(callsOf(calls, "POST", /reconcile$/)).toHaveLength(0);
  });

  it("AT_960_21_6 對帳失敗：顯示白話原因的錯誤提示、沒有橫幅", async () => {
    const user = userEvent.setup();
    renderWorkspace({
      search: "step=studio",
      stub: { overrides: (c) => (c.method === "POST" && c.path.endsWith("/reconcile") ? failure(503, { message: "不可用", reason: "bridge_unreachable" }) : undefined) },
    });
    await screen.findByTestId("studio-stub");
    await user.click(screen.getByRole("button", { name: "對帳" }));
    expect(await screen.findByText(/對帳失敗：連不上 Engine Bridge/)).toBeInTheDocument();
    expect(screen.queryByTestId("drift-banner")).toBeNull();
  });
});

// ── AT_962_23_7：對帳第七項 delivery（交付快照）漂移，由單一橫幅顯示 ──────────────────────────

describe("AT_962_23_7 交付項對帳：RECONCILE_CHECK_LABEL 含 delivery＝交付；單一橫幅列出交付漂移", () => {
  it("AT_962_23_7 標籤表恰七個鍵且 delivery 為『交付』；reconcileDriftView 對 delivery drift 回檔案漂移列（label 交付、帶雙方 sha）", () => {
    expect(Object.keys(RECONCILE_CHECK_LABEL).sort()).toEqual(["delivery", "evidence_matrix", "fsm_flow_mapping", "prd_sha256", "review_card", "route_decision", "task_decomposition"]);
    expect(RECONCILE_CHECK_LABEL.delivery).toBe("交付");
    const view = reconcileDriftView({
      consistent: false,
      checks: [{ name: "delivery", status: "drift", drift: [{ kind: "sha256_mismatch", path: "03_execution/traceability_matrix.json", expectedSha256: sha("a"), actualSha256: sha("b") }] }],
    });
    expect(view.hasDrift).toBe(true);
    expect(view.files).toEqual([{ check: "delivery", label: "交付", path: "03_execution/traceability_matrix.json", expectedSha256: sha("a"), actualSha256: sha("b") }]);
  });

  it("AT_962_23_7 工作區單一 drift-banner 列出『交付』漂移：檔名、標籤與雙方 sha 前 8 碼；整個畫面只有一個橫幅", async () => {
    const { client } = renderWorkspace({ search: "step=studio" });
    await screen.findByTestId("studio-stub");
    act(() => {
      client.setQueryData(qk.researchReconcile(R2), {
        consistent: false,
        checks: [
          { name: "prd_sha256", status: "ok" },
          { name: "delivery", status: "drift", drift: [{ kind: "sha256_mismatch", path: "03_execution/traceability_matrix.json", expectedSha256: sha("a"), actualSha256: sha("b") }] },
        ],
      });
    });
    const banners = await screen.findAllByTestId("drift-banner");
    expect(banners).toHaveLength(1);
    expect(banners[0]).toHaveAttribute("data-drift", "true");
    const files = within(banners[0]).getByTestId("drift-files");
    expect(files).toHaveTextContent("03_execution/traceability_matrix.json");
    expect(files).toHaveTextContent("（交付）");
    expect(files).toHaveTextContent("資料庫 aaaaaaaa，檔案 bbbbbbbb");
    expect(screen.queryByTestId("build-drift-banner")).toBeNull();
  });
});
// ── 殼層的其他狀態：載入、錯誤、初始化失敗、受阻、標題 ──────────────────────────────────────

describe("研究工作區殼層：載入中、載入失敗、初始化失敗、受阻、標題", () => {
  it("載入中：顯示頁面骨架（aria-busy），沒有工作區內容", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>(() => {})),
    );
    nav.params = { researchId: R2 };
    renderResearch(<ResearchWorkspaceView panels={PANELS} />);
    expect(screen.getByLabelText("頁面載入中")).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByTestId("research-workspace")).toBeNull();
  });

  it("載入失敗（404 找不到）：顯示「無法載入研究專案」與白話原因、可重試、有回清單的連結；不導向", async () => {
    const user = userEvent.setup();
    const { calls } = renderWorkspace({ stub: { details: {} } });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("無法載入研究專案");
    expect(alert).toHaveTextContent("找不到研究專案：research_not_found");
    expect(screen.getByRole("link", { name: "研發工作流" })).toHaveAttribute("href", "/research");
    expect(screen.queryByTestId("research-workspace")).toBeNull();
    const before = calls.filter((c) => c.path === `/api/v1/research/projects/${R2}`).length;
    await user.click(within(alert).getByRole("button", { name: "重試" }));
    await waitFor(() => expect(calls.filter((c) => c.path === `/api/v1/research/projects/${R2}`).length).toBeGreaterThan(before));
    expect(nav.router.replace).not.toHaveBeenCalled();
  });

  it("標題列與回清單連結：標題「RP 編號 名稱」、副標寫代號與檢索深度；頁首列與步驟列各只有一份", async () => {
    renderWorkspace({ search: "step=studio" });
    await screen.findByTestId("studio-stub");
    expect(screen.getByRole("heading", { name: "RP-0002 向量資料庫選型" })).toBeInTheDocument();
    expect(screen.getByText("代號 vector-db · 檢索深度 標準")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "研發工作流" })).toHaveAttribute("href", "/research");
    expect(screen.getAllByTestId("research-flow-header")).toHaveLength(1);
    expect(screen.getAllByTestId("flow-stepper").filter((el) => el.getAttribute("data-compact") === null)).toHaveLength(1);
  });

  it("初始化失敗：顯示紅色橫幅與原因、「重試初始化」鈕（OPERATOR 可按，POST reinit 恰一次，成功後重抓詳情、橫幅消失）；沒有「受阻」橫幅", async () => {
    const user = userEvent.setup();
    const { calls, options } = renderWorkspace({ id: R1, search: "step=topic", stub: { details: { [R1]: detailVariant("initFailed") } } });
    const banner = await screen.findByTestId("init-failed-banner");
    expect(banner).toHaveAttribute("role", "alert");
    expect(banner).toHaveTextContent("初始化失敗：init_failed:fsm");
    expect(banner).toHaveTextContent("重試是冪等的");
    expect(screen.queryByTestId("blocked-banner"), "初始化失敗不另顯示受阻橫幅").toBeNull();
    // 第 1 步在初始化失敗時標「受阻」
    expect(screen.getByTestId("flow-step-topic")).toHaveAttribute("data-state", "BLOCKED");

    options.details[R1] = detailVariant("topicReady");
    await user.click(within(banner).getByRole("button", { name: "重試初始化" }));
    expect(await screen.findByText("已重試初始化")).toBeInTheDocument();
    expect(callsOf(calls, "POST", new RegExp(`/projects/${R1}/reinit$`))).toHaveLength(1);
    await waitFor(() => expect(screen.queryByTestId("init-failed-banner")).toBeNull());
  });

  it("初始化失敗（VIEWER）：「重試初始化」停用、title 為權限不足，點了不送請求", async () => {
    const user = userEvent.setup();
    const { calls } = renderWorkspace({ id: R1, search: "step=topic", role: "VIEWER", stub: { details: { [R1]: detailVariant("initFailed") } } });
    const banner = await screen.findByTestId("init-failed-banner");
    const retry = within(banner).getByRole("button", { name: "重試初始化" });
    expect(retry).toBeDisabled();
    expect(retry).toHaveAttribute("title", "權限不足（唯讀角色）");
    await user.click(retry);
    expect(writeCalls(calls)).toEqual([]);
  });

  it("重試初始化失敗：顯示白話原因的錯誤提示，橫幅仍在", async () => {
    const user = userEvent.setup();
    renderWorkspace({
      id: R1,
      search: "step=topic",
      stub: {
        details: { [R1]: detailVariant("initFailed") },
        overrides: (c) => (c.method === "POST" && c.path.endsWith("/reinit") ? failure(409, { message: "衝突", reason: "stage_conflict" }) : undefined),
      },
    });
    const banner = await screen.findByTestId("init-failed-banner");
    await user.click(within(banner).getByRole("button", { name: "重試初始化" }));
    expect(await screen.findByText(/重試初始化失敗：目前狀態不允許這個動作/)).toBeInTheDocument();
    expect(screen.getByTestId("init-failed-banner")).toBeInTheDocument();
  });

  it("受阻（BLOCKED，非初始化失敗）：顯示受阻橫幅與後端的原因（BLOCKED_DB），步驟列的當前步標「受阻」；沒有初始化失敗橫幅", async () => {
    renderWorkspace({ search: "step=studio", stub: { details: { [R2]: detailVariant("blocked") } } });
    const banner = await screen.findByTestId("blocked-banner");
    expect(banner).toHaveAttribute("role", "alert");
    expect(banner).toHaveTextContent(`目前${FLOW_STATUS_LABEL.BLOCKED}：BLOCKED_DB`);
    expect(screen.queryByTestId("init-failed-banner")).toBeNull();
    expect(screen.getByTestId("flow-step-studio")).toHaveAttribute("data-state", "BLOCKED");
  });

  it("受阻但後端沒給原因：明說「後端沒有提供原因」，不留空白", async () => {
    const base = detailVariant("blocked");
    renderWorkspace({ search: "step=studio", stub: { details: { [R2]: { ...base, flow: { ...base.flow, effective: { ...base.flow.effective, detail: "" } } } } } });
    expect(await screen.findByTestId("blocked-banner")).toHaveTextContent("後端沒有提供原因");
  });

  it("升級給人工（ESCALATED）：步驟列標「受阻」、頁首燈號是待人工；不顯示受阻橫幅（升級由工作室處理）", async () => {
    renderWorkspace({ search: "step=studio", stub: { details: { [R2]: detailVariant("escalated") } } });
    await screen.findByTestId("studio-stub");
    expect(screen.getByTestId("flow-step-studio")).toHaveAttribute("data-state", "BLOCKED");
    expect(screen.getByTestId("flow-lamp")).toHaveAttribute("data-lamp", "Escalated");
    expect(screen.queryByTestId("blocked-banner")).toBeNull();
  });

  it("替身面板收到殼層傳入的 researchId、project、completed：步驟 1 與 2 各自渲染各自的面板，一次只渲染目前步的那一個", async () => {
    renderWorkspace({ id: R3, search: "step=topic", stub: { details: { [R3]: frozenFurthestDeliver() } } });
    const topic = await screen.findByTestId("topic-stub");
    expect(topic).toHaveAttribute("data-research-id", R3);
    expect(topic).toHaveAttribute("data-project-id", R3);
    expect(topic).toHaveAttribute("data-completed", "true");
    expect(topic).toHaveTextContent("議題面板替身 RP-0003");
    expect(screen.queryByTestId("studio-stub")).toBeNull();
    expect(screen.queryByTestId("research-placeholder")).toBeNull();
  });
});

// ── 頁殼 ───────────────────────────────────────────────────────────────────────────────

describe("AT_960_19_4 頁殼 app/research/[researchId]/page.tsx：只殼，Suspense 內組裝工作區元件", () => {
  it("AT_960_19_4 metadata.title 為「研究工作區」；預設匯出渲染工作區（讀網址的 researchId 與 ?step=）；頁殼以 Suspense 包住（useSearchParams 的靜態預渲染需要）", async () => {
    expect(workspacePageMetadata.title).toBe("研究工作區");
    nav.params = { researchId: R2 };
    nav.search = "step=studio";
    stubResearchApi();
    renderResearch(<ResearchWorkspacePage />, "OPERATOR");
    expect(await screen.findByTestId("research-workspace")).toHaveAttribute("data-step", "studio");
    const source = readFileSync(path.join(process.cwd(), "app", "research", "[researchId]", "page.tsx"), "utf-8");
    expect(source).toContain("<Suspense>");
    expect(source, "頁殼只組裝：不 import 查詢 hook 或端點函式").not.toMatch(/@\/lib\/api/);
  });
});
