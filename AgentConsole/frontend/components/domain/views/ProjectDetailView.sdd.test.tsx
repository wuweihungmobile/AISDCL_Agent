import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ProjectDetail } from "@/lib/api/types";
import { Providers, makeClient, signIn, stubApi, type ApiCall, type Reply } from "@/tests/helpers/api";
import { projectDetail } from "@/tests/helpers/runFixtures";
import { engineStatus, fsmState } from "@/tests/helpers/sddFixtures";
import { ProjectDetailView } from "./ProjectDetailView";

vi.mock("next/navigation", () => ({
  useParams: () => ({ projectId: "p1" }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/projects/p1",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
vi.mock("@/components/markdown/MarkdownEditor", () => ({
  MarkdownEditor: ({ value, label }: { value: string; label: string }) => <textarea aria-label={label} defaultValue={value} readOnly />,
}));

/**
 * 專案詳情頁的 SDD 治理區接線（契約 §4.7.1；整合輪 115）：位置（目標清單之下、行動列之上）、預設展開／收合、
 * 寫入成功後專案詳情與 FSM 狀態立即重取（綁定三欄在專案詳情，核准凍結第 5 項可能寫回 sddProject）。
 */
const USED = (patch: Partial<ProjectDetail> = {}) => projectDetail({ id: "p1", sddProject: "core-fsm", sddSpecDir: "/work/core/docs", sddSpecFile: "/work/core/docs/TCS-A.md", ...patch });

function backend(world: { project: ProjectDetail; fsm: ReturnType<typeof fsmState> | null }, extra: (c: ApiCall) => Reply = () => undefined) {
  return stubApi((c) => {
    const custom = extra(c);
    if (custom) return custom;
    if (c.method === "GET" && c.path === "/api/v1/projects/p1") return { data: world.project };
    if (c.method === "GET" && c.path === "/api/v1/engines/sdd") return { data: engineStatus(world.fsm) };
    return undefined;
  });
}

const view = () =>
  render(
    <Providers client={makeClient()}>
      <ProjectDetailView />
    </Providers>,
  );

const projectGets = (calls: ApiCall[]) => calls.filter((c) => c.method === "GET" && c.path === "/api/v1/projects/p1");

beforeEach(() => signIn("OPERATOR", "operator"));

describe("專案詳情頁：SDD 治理區的位置與預設狀態（契約 §4.7.1）", () => {
  it("位置在目標清單卡之後、行動列（執行專案、編輯專案、刪除專案…）之前", async () => {
    backend({ project: USED(), fsm: fsmState() });
    view();
    const goals = await screen.findByTestId("goal-list-card");
    const gov = await screen.findByTestId("sdd-governance");
    const del = screen.getByRole("button", { name: "刪除專案" });
    expect(goals.compareDocumentPosition(gov) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(gov.compareDocumentPosition(del) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("已使用 SDD 的專案預設展開並載入 FSM；從未使用的專案預設收合（標題帶「（尚未使用）」）且不發 engines/sdd 請求", async () => {
    const used = backend({ project: USED(), fsm: fsmState() });
    const first = view();
    expect(await screen.findByText("HUMAN_PENDING")).toBeInTheDocument();
    expect(used.calls.filter((c) => c.path === "/api/v1/engines/sdd")).toHaveLength(1);
    first.unmount();

    const unused = backend({ project: projectDetail({ id: "p1" }), fsm: null });
    view();
    expect(await screen.findByRole("button", { name: "SDD 治理（尚未使用）" })).toHaveAttribute("aria-expanded", "false");
    await new Promise((resolve) => setTimeout(resolve, 80));
    expect(unused.calls.filter((c) => c.path === "/api/v1/engines/sdd")).toHaveLength(0);
  });
});

describe("專案詳情頁：寫入成功後重取（契約 §1.10.2 第 5 項寫回標準鍵、§1.10.7）", () => {
  it("核准凍結成功：專案詳情與 FSM 狀態都重取，畫面換成新狀態（SPEC_FROZEN、已凍結）", async () => {
    const world = { project: USED({ sddProject: null }), fsm: fsmState() as ReturnType<typeof fsmState> | null };
    const { calls } = backend(world, (c) => {
      if (c.method === "POST" && c.path === "/api/v1/projects/p1/sdd/freeze") {
        // 後端：先把標準鍵寫回 sddProject，再凍結（契約 §1.10.2 第 5、6 項）
        world.project = USED({ sddProject: "core-fsm" });
        world.fsm = fsmState({
          currentState: "SPEC_FROZEN",
          phase: { name: "FROZEN", order: 4, blocking: false, observation: false },
          frozenStages: [{ stage: "Stage-1", frozen_at: "2026-10-17T01:02:03+00:00", approved_by: "operator" }],
        });
        return { data: world.fsm };
      }
      return undefined;
    });
    view();
    await screen.findByText("HUMAN_PENDING");
    expect(screen.getByTestId("sdd-gov-project")).toHaveTextContent("（預設：AISDLC Core Platform）"); // 凍結前 sddProject 為 NULL
    const projectBefore = projectGets(calls).length;

    await userEvent.click(screen.getByTestId("sdd-freeze-button"));
    const dialog = await screen.findByRole("dialog", { name: "核准凍結規格" });
    await userEvent.type(within(dialog).getByTestId("sdd-freeze-reason"), "規格已走完 SCG-0～3");
    await userEvent.click(within(dialog).getByRole("button", { name: "核准凍結" }));

    expect(await screen.findByText("已核准凍結")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("sdd-gov-state")).toHaveTextContent("SPEC_FROZEN"));
    expect(projectGets(calls).length).toBeGreaterThan(projectBefore); // 專案詳情重取
    await waitFor(() => expect(screen.getByTestId("sdd-gov-project")).toHaveTextContent("core-fsm")); // 標準鍵已寫回，畫面不再是「預設」
    expect(screen.getByTestId("sdd-gov-frozen")).toHaveTextContent(/^已凍結：Stage-1/);
    expect(screen.getByTestId("sdd-freeze-button")).toBeDisabled(); // 已不在 HUMAN_PENDING
    expect(screen.getByTestId("sdd-freeze-hint")).toHaveTextContent("目前：SPEC_FROZEN");
  });

  it("編輯 SDD 專案成功：專案詳情重取、「SDD 專案」列換成新值", async () => {
    const world = { project: USED({ sddProject: "core-fsm" }), fsm: fsmState() as ReturnType<typeof fsmState> | null };
    const { calls } = backend(world, (c) => {
      if (c.method === "PUT" && c.path === "/api/v1/projects/p1/sdd-binding") {
        world.project = USED({ sddProject: (c.body as { sddProject: string | null }).sddProject });
        return { data: world.project };
      }
      return undefined;
    });
    view();
    await screen.findByText("HUMAN_PENDING");
    const before = projectGets(calls).length;
    await userEvent.click(screen.getByRole("button", { name: "編輯 SDD 專案" }));
    const dialog = await screen.findByRole("dialog", { name: "編輯 SDD 專案" });
    const input = within(dialog).getByLabelText(/^SDD 專案/);
    await userEvent.clear(input);
    await userEvent.type(input, "core-new");
    await userEvent.click(within(dialog).getByRole("button", { name: "儲存" }));
    expect(await screen.findByText("已更新 SDD 專案")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("sdd-gov-project")).toHaveTextContent("core-new"));
    expect(projectGets(calls).length).toBeGreaterThan(before);
  });

  it("VIEWER：整區唯讀（看得到綁定與狀態，沒有編輯與核准凍結）", async () => {
    signIn("VIEWER", "viewer");
    backend({ project: USED(), fsm: fsmState() });
    view();
    await screen.findByText("HUMAN_PENDING");
    const gov = screen.getByTestId("sdd-governance");
    expect(within(gov).queryByRole("button", { name: /編輯|核准凍結/ })).toBeNull();
    expect(within(gov).getByTestId("sdd-gov-project")).toHaveTextContent("core-fsm");
  });
});
