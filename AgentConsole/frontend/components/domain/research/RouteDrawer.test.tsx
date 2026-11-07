import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import type { ResearchCapabilities, Role } from "@/lib/api/types";
import { PLACEMENT_TARGETS, READONLY_TITLE, ROUTE_DISABLED_TEXT, ROUTE_EVAL_TABLE } from "@/lib/domain/research";
import { R3 } from "@/tests/fixtures/research/ids";
import { detailVariant } from "@/tests/fixtures/research/projects";
import { CAPABILITIES_ROUTE_READY, CAPABILITIES_ROUTE_VARIANTS, PREVIEW_B } from "@/tests/fixtures/research/route";
import { callsOf, failure, renderResearch, stubResearchApi } from "@/tests/helpers/research";
import { RouteDrawer, type RouteDrawerProject } from "./RouteDrawer";
import { RoutePanel } from "./RoutePanel";

/**
 * 分流精靈抽屜（TCS-ResearchToPRD-P1-20261107 AT-961-16-5、16-E-2、17-1、17-3～17-6、17-E-1；AC-R2P-11-1～11-6、12-3、13-3、13-7）：
 * 三段（選卡填參數→預演→確認）、角色與缺項停用、Public 確認逐字比對、差異理由必填。
 * 判定指令：npx vitest run components/domain/research/RouteDrawer.test.tsx -t "<AT 底線形>"
 */
const nav = vi.hoisted(() => ({ router: { push: vi.fn(), replace: vi.fn(), back: vi.fn() } }));
vi.mock("next/navigation", () => ({
  useRouter: () => nav.router,
  useParams: () => ({}),
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(""),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const PROJECT: RouteDrawerProject = { rpNo: "RP-0007", targetScope: "UNDECIDED", topic: "Agent 記憶體回收", slug: "agent-memory-gc" };
const PREVIEW_URL = /\/route\/preview$/;
const ROUTE_URL = /\/route$/;

type StubPatch = Parameters<typeof stubResearchApi>[0];

function renderDrawer(opts: { role?: Role; caps?: ResearchCapabilities; project?: RouteDrawerProject; track?: "A" | "B" | null; stub?: StubPatch; readOnly?: boolean } = {}) {
  const api = stubResearchApi(opts.stub);
  const view = renderResearch(
    <RouteDrawer
      open
      onOpenChange={() => undefined}
      researchId={R3}
      project={opts.project ?? PROJECT}
      defaultTrack={opts.track === undefined ? "A" : opts.track}
      capabilities={opts.caps ?? CAPABILITIES_ROUTE_READY}
      readOnly={opts.readOnly}
    />,
    opts.role ?? "ADMIN",
  );
  return { ...view, ...api };
}

const radio = (name: RegExp) => screen.getByRole("radio", { name });
const button = (name: string) => screen.getByRole("button", { name });
const setValue = (label: RegExp, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const pickB = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(radio(/軌道 B/));
  setValue(/^專案名稱/, "demo-app");
};

describe("AT_961_16_5 前端依 capabilities 缺項停用控件並說明（D-114、IFACE §8.3）", () => {
  it("AT_961_16_5 全可用：兩卡可選、選卡 B 後「建立 GitHub 遠端」勾選可用；預演可按（欄位預設合規）", async () => {
    const user = userEvent.setup();
    renderDrawer({ track: null });
    expect(radio(/軌道 A/)).toBeEnabled();
    expect(radio(/軌道 B/)).toBeEnabled();
    await user.click(radio(/軌道 B/));
    expect(screen.getByRole("checkbox", { name: "建立 GitHub 遠端" })).toBeEnabled();
  });

  it("AT_961_16_5 git 缺：預演與確認兩軌皆停用並說明「此部署找不到 git，無法分流」；停用的控件不送出任何請求", async () => {
    const user = userEvent.setup();
    const { calls } = renderDrawer({ caps: CAPABILITIES_ROUTE_VARIANTS.noGit });
    expect(radio(/軌道 A/)).toBeDisabled();
    expect(radio(/軌道 B/)).toBeDisabled();
    expect(button("預演")).toBeDisabled();
    expect(button("預演")).toHaveAttribute("title", ROUTE_DISABLED_TEXT.git);
    expect(button("確認執行")).toBeDisabled();
    expect(screen.getAllByText("此部署找不到 git，無法分流").length).toBeGreaterThan(0);
    await user.click(button("預演"));
    expect(callsOf(calls, "POST", PREVIEW_URL)).toHaveLength(0);
  });

  it("AT_961_16_5 repoWritable 假：只有軌道 A 卡停用並說明「此部署無法寫入 monorepo（容器模式）；請改用本機模式」，軌道 B 卡照常", () => {
    renderDrawer({ caps: CAPABILITIES_ROUTE_VARIANTS.repoReadOnly, track: null });
    expect(radio(/軌道 A/)).toBeDisabled();
    expect(screen.getByTestId("route-card-a-disabled")).toHaveTextContent("此部署無法寫入 monorepo（容器模式）；請改用本機模式");
    expect(radio(/軌道 B/)).toBeEnabled();
  });

  it("AT_961_16_5 ghCli.ok 假：只有「建立 GitHub 遠端」勾選停用並說明「找不到 gh；可先建本地專案，之後自行推送」，本地骨架仍可預演", async () => {
    const user = userEvent.setup();
    renderDrawer({ caps: CAPABILITIES_ROUTE_VARIANTS.noGh, track: null });
    await pickB(user);
    expect(screen.getByRole("checkbox", { name: "建立 GitHub 遠端" })).toBeDisabled();
    expect(screen.getByTestId("github-disabled")).toHaveTextContent("找不到 gh；可先建本地專案，之後自行推送");
    expect(radio(/軌道 B/)).toBeEnabled();
    expect(button("預演")).toBeEnabled();
  });

  it.each([
    ["scaffoldRoot 為 null", CAPABILITIES_ROUTE_VARIANTS.noScaffoldRoot],
    ["scaffoldTemplates 為空", CAPABILITIES_ROUTE_VARIANTS.noTemplates],
  ] as const)("AT_961_16_5 %s：軌道 B 卡停用並說明「尚未設定 BRIDGE_SCAFFOLD_ROOT 或無可用範本」，軌道 A 卡照常", (_name, caps) => {
    renderDrawer({ caps, track: null });
    expect(radio(/軌道 B/)).toBeDisabled();
    expect(screen.getByTestId("route-card-b-disabled")).toHaveTextContent("尚未設定 BRIDGE_SCAFFOLD_ROOT 或無可用範本");
    expect(radio(/軌道 A/)).toBeEnabled();
  });

  it("AT_961_16_5 mock-only：兩軌皆停用並說明「容器模式只跑 mock claude 的驗收；真分流限本機模式」", () => {
    renderDrawer({ caps: CAPABILITIES_ROUTE_VARIANTS.mockOnly });
    expect(radio(/軌道 A/)).toBeDisabled();
    expect(radio(/軌道 B/)).toBeDisabled();
    expect(screen.getByTestId("route-card-a-disabled")).toHaveTextContent("容器模式只跑 mock claude 的驗收；真分流限本機模式");
    expect(button("預演")).toBeDisabled();
    expect(button("確認執行")).toBeDisabled();
  });

  it("AT_961_16_5 非 ADMIN 的確認停用，title 為「權限不足」；VIEWER 連預演都停用，title 為唯讀提示", () => {
    const operator = renderDrawer({ role: "OPERATOR" });
    expect(button("預演")).toBeEnabled();
    expect(button("確認執行")).toBeDisabled();
    expect(button("確認執行").getAttribute("title")).toContain("權限不足");
    operator.unmount();
    renderDrawer({ role: "VIEWER" });
    expect(button("預演")).toBeDisabled();
    expect(button("預演")).toHaveAttribute("title", READONLY_TITLE);
    expect(radio(/軌道 A/)).toBeDisabled();
    expect(button("確認執行")).toHaveAttribute("title", READONLY_TITLE);
  });
});

describe("AT_961_16_E_2 capabilities 載入失敗：錯誤態與重試，不假裝可用", () => {
  it.each([
    [502, "bridge_unreachable"],
    [503, "bridge_unreachable"],
  ])("AT_961_16_E_2 capabilities 回 %s：顯示錯誤與重試鈕，兩卡與預演、確認皆停用，沒有任何欄位；按重試會重新請求並恢復", async (status, reason) => {
    const user = userEvent.setup();
    const api = stubResearchApi({ details: { [R3]: detailVariant("frozen", { targetScope: "AISDLC_MODULE" }) } });
    let broken = true;
    api.options.overrides = (call) => (call.method === "GET" && call.path === "/api/v1/research/capabilities" && broken ? failure(status, { message: "Bridge 不可用", reason }) : undefined);
    renderResearch(<RoutePanel researchId={R3} project={detailVariant("frozen", { targetScope: "AISDLC_MODULE" })} completed={false} />, "ADMIN");
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText("無法載入部署能力")).toBeInTheDocument();
    expect(within(dialog).getByRole("radio", { name: /軌道 A/ })).toBeDisabled();
    expect(within(dialog).getByRole("radio", { name: /軌道 B/ })).toBeDisabled();
    expect(within(dialog).getByRole("button", { name: "預演" })).toBeDisabled();
    expect(within(dialog).getByRole("button", { name: "確認執行" })).toBeDisabled();
    expect(within(dialog).queryByLabelText(/分支名/)).toBeNull();
    broken = false;
    await user.click(within(dialog).getByRole("button", { name: "重試" }));
    await waitFor(() => expect(within(dialog).getByRole("radio", { name: /軌道 A/ })).toBeEnabled());
  });
});

describe("AT_961_17_1 Gate 0 核准後進入第 3 步：抽屜顯示兩卡與評估維度表，依 PRD target_scope 預選，可重開", () => {
  it.each([
    ["AISDLC_MODULE", "A"],
    ["STANDALONE_PROJECT", "B"],
    ["UNDECIDED", null],
  ] as const)("AT_961_17_1 targetScope 為 %s：抽屜自動開啟、預選 %s；評估維度表五列三欄；文字純文字", async (targetScope, picked) => {
    stubResearchApi();
    renderResearch(<RoutePanel researchId={R3} project={detailVariant("frozen", { targetScope })} completed={false} />, "ADMIN");
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByRole("radio", { name: /軌道 A/ })).toHaveAttribute("aria-checked", String(picked === "A"));
    expect(within(dialog).getByRole("radio", { name: /軌道 B/ })).toHaveAttribute("aria-checked", String(picked === "B"));
    const table = within(dialog).getByTestId("route-eval-table");
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(1 + ROUTE_EVAL_TABLE.length);
    expect(within(rows[0]).getAllByRole("columnheader")).toHaveLength(3);
    for (const row of ROUTE_EVAL_TABLE) expect(table).toHaveTextContent(row.dimension);
    expect(dialog.querySelector("[dangerouslysetinnerhtml]")).toBeNull();
  });

  it("AT_961_17_1 關閉抽屜後面板提供「重新開啟分流精靈」，按下再開", async () => {
    const user = userEvent.setup();
    stubResearchApi();
    renderResearch(<RoutePanel researchId={R3} project={detailVariant("frozen", { targetScope: "AISDLC_MODULE" })} completed={false} />, "ADMIN");
    await screen.findByRole("dialog");
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await user.click(screen.getByRole("button", { name: "重新開啟分流精靈" }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });
});

describe("AT_961_17_3 卡 A 欄位", () => {
  it("AT_961_17_3 分支名預設 feature/issue-0007、基底 ref 預設 main；掛載目標為下拉、四個模組各附出處句、標「預設」；改選後預演請求帶 targetModule", async () => {
    const user = userEvent.setup();
    const { calls } = renderDrawer({ track: null, project: { ...PROJECT, topic: "給 AgentConsole 增加頁面", slug: "console-page" } });
    await user.click(radio(/軌道 A/));
    expect(screen.getByLabelText(/分支名/)).toHaveValue("feature/issue-0007");
    expect(screen.getByLabelText(/基底 ref/)).toHaveValue("main");
    const select = screen.getByRole("combobox", { name: /掛載目標/ });
    expect(select.tagName).toBe("SELECT");
    const options = within(select)
      .getAllByRole("option")
      .filter((o) => (o as HTMLOptionElement).value !== "");
    expect(options.map((o) => (o as HTMLOptionElement).value)).toEqual(PLACEMENT_TARGETS.map((t) => t.id));
    expect(options.find((o) => o.textContent?.includes("（預設）"))).toHaveValue("agentconsole");
    const sources = within(screen.getByTestId("placement-sources")).getAllByRole("listitem");
    expect(sources).toHaveLength(4);
    for (const [i, target] of PLACEMENT_TARGETS.entries()) expect(sources[i]).toHaveTextContent(target.source);
    expect(screen.getByTestId("module-registry-preview")).toHaveTextContent("AgentConsole");
    await user.selectOptions(select, "sdd");
    await user.click(button("預演"));
    await waitFor(() => expect(callsOf(calls, "POST", PREVIEW_URL)).toHaveLength(1));
    expect(callsOf(calls, "POST", PREVIEW_URL)[0].body).toMatchObject({ track: "A", targetModule: "sdd", branchName: "feature/issue-0007", baseRef: "main" });
  });

  it("AT_961_17_3 分支名即時驗證：不合 ^feature/[a-z0-9-]{1,40}$ 顯示欄位錯誤並停用預演；合規後恢復", async () => {
    const user = userEvent.setup();
    renderDrawer({ track: null });
    await user.click(radio(/軌道 A/));
    setValue(/分支名/, "issue-7");
    expect(await screen.findByText(/分支名須為 feature\//)).toBeInTheDocument();
    expect(button("預演")).toBeDisabled();
    setValue(/分支名/, "feature/issue-7");
    expect(button("預演")).toBeEnabled();
  });
});

describe("AT_961_17_4 卡 B 欄位", () => {
  it("AT_961_17_4 範本只列 capabilities 的範本；可見度預設 Private；Public 顯示警告與「重新輸入庫名」，確認名不完全相同時預演與確認停用；CI 與 compose 預設勾選；請求不含 targetPath", async () => {
    const user = userEvent.setup();
    const { calls } = renderDrawer({ track: null });
    await pickB(user);
    setValue(/^owner/, "acme");
    const template = screen.getByRole("combobox", { name: /專案範本/ });
    expect(
      within(template)
        .getAllByRole("option")
        .map((o) => (o as HTMLOptionElement).value),
    ).toEqual(["python-fastapi"]);
    expect(screen.getByRole("combobox", { name: /可見度/ })).toHaveValue("PRIVATE");
    expect(screen.queryByTestId("public-repo-confirm")).toBeNull();
    expect(screen.getByRole("checkbox", { name: "產生 CI 設定" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "產生 docker compose" })).toBeChecked();
    await user.selectOptions(screen.getByRole("combobox", { name: /可見度/ }), "PUBLIC");
    expect(screen.getByTestId("public-repo-confirm")).toHaveTextContent("PRD 與證據矩陣將公開");
    expect(button("預演")).toBeDisabled();
    setValue(/重新輸入庫名/, "demo-app");
    expect(button("預演")).toBeEnabled();
    await user.click(screen.getByRole("checkbox", { name: "產生 CI 設定" }));
    await user.click(button("預演"));
    await waitFor(() => expect(callsOf(calls, "POST", PREVIEW_URL)).toHaveLength(1));
    const body = callsOf(calls, "POST", PREVIEW_URL)[0].body as Record<string, unknown>;
    expect(body).toMatchObject({
      track: "B",
      projectName: "demo-app",
      owner: "acme",
      repoName: "demo-app",
      visibility: "PUBLIC",
      confirmRepoName: "demo-app",
      createGithub: false,
      ci: false,
      dockerCompose: true,
    });
    expect(body).not.toHaveProperty("targetPath");
  });

  it("AT_961_17_4 專案名稱、owner、庫名即時驗證，錯誤顯示在欄位旁並停用預演", async () => {
    const user = userEvent.setup();
    renderDrawer({ track: null });
    await user.click(radio(/軌道 B/));
    setValue(/^專案名稱/, "Demo App");
    expect(await screen.findByText(/專案名稱須為小寫英文字母開頭/)).toBeInTheDocument();
    setValue(/^專案名稱/, "demo-app");
    setValue(/^庫名/, "Bad_Name");
    expect(await screen.findByText(/庫名須為小寫英文字母開頭/)).toBeInTheDocument();
    expect(button("預演")).toBeDisabled();
    setValue(/^庫名/, "");
    setValue(/^owner/, "-bad");
    expect(await screen.findByText(/owner 須為英數與連字號/)).toBeInTheDocument();
  });
});

describe("AT_961_17_5 預演面板", () => {
  it("AT_961_17_5 OPERATOR 預演一次：動作清單以純文字渲染並標示外部系統，預演後不發任何 POST route；預演前確認停用", async () => {
    const user = userEvent.setup();
    const { calls } = renderDrawer({ role: "OPERATOR", track: null, stub: { preview: PREVIEW_B } });
    await pickB(user);
    expect(button("確認執行")).toBeDisabled();
    await user.click(button("預演"));
    const list = await screen.findByTestId("route-actions");
    expect(callsOf(calls, "POST", PREVIEW_URL)).toHaveLength(1);
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[1]).toHaveTextContent("外部系統");
    expect(items[0]).not.toHaveTextContent("外部系統");
    expect(list).toHaveTextContent("<script>alert(1)</script>/demo-app");
    expect(document.querySelector("script[src], script:not([type])")?.textContent ?? "").not.toContain("alert(1)");
    expect(screen.getByTestId("route-warnings")).toHaveTextContent("PRD 與證據矩陣將公開");
    expect(screen.getByTestId("route-tracked-files")).toHaveTextContent("README.md");
    expect(callsOf(calls, "POST", ROUTE_URL)).toHaveLength(0);
  });

  it("AT_961_17_5 預演 422 時逐欄顯示違規，不顯示動作清單；確認維持停用", async () => {
    const user = userEvent.setup();
    renderDrawer({
      track: null,
      stub: {
        overrides: (call) =>
          call.method === "POST" && PREVIEW_URL.test(call.path)
            ? failure(422, { message: "參數不合", reason: "invalid_request", details: { violations: [{ field: "branchName", message: "格式不符" }] } })
            : undefined,
      },
    });
    await pickB(user);
    await user.click(button("預演"));
    expect(await screen.findByTestId("route-violations")).toHaveTextContent("branchName：格式不符");
    expect(screen.queryByTestId("route-actions")).toBeNull();
    expect(button("確認執行")).toBeDisabled();
  });
});

describe("AT_961_17_6 確認僅 ADMIN；差異警示與理由必填", () => {
  it("AT_961_17_6 分流與 PRD 不同：顯示差異警示並列兩者、理由 0 與 201 字停用、1 與 200 字啟用；確認送出帶 scopeDiffersReason、不含 approver", async () => {
    const user = userEvent.setup();
    const { calls } = renderDrawer({ role: "ADMIN", track: null, project: { ...PROJECT, targetScope: "AISDLC_MODULE" }, stub: { preview: PREVIEW_B } });
    await pickB(user);
    const warning = screen.getByTestId("scope-differs");
    expect(warning).toHaveTextContent("AISDLC_MODULE");
    expect(warning).toHaveTextContent("軌道 B：獨立專案");
    expect(button("預演")).toBeDisabled(); // 理由為 0 字
    const reasonOf = (n: number) => setValue(/差異理由/, "字".repeat(n));
    reasonOf(201);
    expect(screen.getByText("理由最多 200 個字")).toBeInTheDocument();
    expect(button("預演")).toBeDisabled();
    reasonOf(200);
    expect(button("預演")).toBeEnabled();
    reasonOf(1);
    expect(button("預演")).toBeEnabled();
    expect(button("確認執行")).toBeDisabled();
    await user.click(button("預演"));
    await screen.findByTestId("route-actions");
    await waitFor(() => expect(button("確認執行")).toBeEnabled());
    await user.click(button("確認執行"));
    await waitFor(() => expect(callsOf(calls, "POST", ROUTE_URL)).toHaveLength(1));
    const body = callsOf(calls, "POST", ROUTE_URL)[0].body as Record<string, unknown>;
    expect(body).toMatchObject({ track: "B", scopeDiffersReason: "字" });
    expect(body).not.toHaveProperty("approver");
    expect(body).not.toHaveProperty("targetPath");
  });

  it("AT_961_17_6 預演後再改任何參數，確認立刻失效，必須重新預演", async () => {
    const user = userEvent.setup();
    renderDrawer({ role: "ADMIN", track: "A" });
    await user.click(button("預演"));
    await screen.findByTestId("route-actions");
    await waitFor(() => expect(button("確認執行")).toBeEnabled());
    setValue(/基底 ref/, "develop");
    expect(button("確認執行")).toBeDisabled();
    expect(screen.queryByTestId("route-actions")).toBeNull();
  });

  it("AT_961_17_6 OPERATOR 可選卡、填參數、預演；確認停用且 title 說明僅 ADMIN；VIEWER 全部停用且 title 為權限不足（唯讀角色）", async () => {
    const user = userEvent.setup();
    const operator = renderDrawer({ role: "OPERATOR", track: null });
    await user.click(radio(/軌道 A/));
    expect(screen.getByLabelText(/分支名/)).toBeEnabled();
    expect(button("預演")).toBeEnabled();
    expect(button("確認執行").getAttribute("title")).toContain("ADMIN");
    operator.unmount();
    renderDrawer({ role: "VIEWER", track: "A" });
    for (const name of [/軌道 A/, /軌道 B/]) expect(radio(name)).toBeDisabled();
    expect(button("預演")).toHaveAttribute("title", READONLY_TITLE);
    expect(button("確認執行")).toHaveAttribute("title", READONLY_TITLE);
  });
});

describe("AT_961_17_E_1 Public 確認的邊界：逐字完全相等", () => {
  it("AT_961_17_E_1 庫名 demo-app：demo-ap、Demo-App、尾端空白、不可見字元皆不符（預演停用），完全相同才啟用", async () => {
    const user = userEvent.setup();
    renderDrawer({ track: null });
    await pickB(user);
    await user.selectOptions(screen.getByRole("combobox", { name: /可見度/ }), "PUBLIC");
    for (const wrong of ["demo-ap", "Demo-App", "demo-app ", "demo-app​"]) {
      setValue(/重新輸入庫名/, wrong);
      expect(button("預演"), JSON.stringify(wrong)).toBeDisabled();
    }
    setValue(/重新輸入庫名/, "demo-app");
    expect(button("預演")).toBeEnabled();
  });
});
