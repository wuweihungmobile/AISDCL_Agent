import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { REASONS } from "@/lib/api/reasons";
import { Providers, failure, makeClient, signIn, stubApi, type ApiCall, type Reply } from "@/tests/helpers/api";
import { projectDetail } from "@/tests/helpers/runFixtures";
import { GoalDetailView } from "./GoalDetailView";
import { TaskDetailView } from "./TaskDetailView";

const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }));
vi.mock("next/navigation", () => ({
  useParams: () => ({ projectId: "p1", goalId: "g1", taskId: "t1" }),
  useRouter: () => router,
  usePathname: () => "/projects/p1/goals/g1/tasks/t1",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
// Markdown 編輯器本體很重且與本測試無關（編輯對話框不會被打開）
vi.mock("@/components/markdown/MarkdownEditor", () => ({
  MarkdownEditor: ({ value, label }: { value: string; label: string }) => <textarea aria-label={label} defaultValue={value} />,
}));

const TS = "2026-10-15T08:30:12Z";
const task = (patch: Record<string, unknown> = {}) => ({
  id: "t1",
  goalId: "g1",
  name: "實作",
  description: "請輸出 [T3_DONE]",
  passCriteria: "- ok",
  sortOrder: 0,
  status: "ESCALATED",
  retryCount: 1,
  maxRetries: 1,
  executionHistory: [],
  signedOff: true,
  createdAt: TS,
  updatedAt: TS,
  ...patch,
});
const goal = (patch: Record<string, unknown> = {}) => ({
  id: "g1",
  projectId: "p1",
  name: "核心",
  description: "核心功能",
  passCriteria: "- ok",
  sortOrder: 0,
  status: "IN_PROGRESS",
  dependsOn: [],
  signedOff: true,
  taskCount: 1,
  completedTaskCount: 0,
  completionRatio: 0,
  tasks: [{ id: "t1", name: "實作", status: "ESCALATED", sortOrder: 0, retryCount: 1, maxRetries: 1, signedOff: true }],
  createdAt: TS,
  updatedAt: TS,
  ...patch,
});

function backend(extra: (c: ApiCall) => Reply) {
  return stubApi((c) => {
    const custom = extra(c);
    if (custom) return custom;
    if (c.method !== "GET") return undefined;
    if (c.path === "/api/v1/tasks/t1") return { data: task() };
    if (c.path === "/api/v1/goals/g1") return { data: goal() };
    if (c.path === "/api/v1/projects/p1") return { data: projectDetail() };
    return undefined;
  });
}

const view = (node: ReactNode) => render(<Providers client={makeClient()}>{node}</Providers>);

beforeEach(() => {
  router.replace.mockClear();
  signIn("OPERATOR", "operator");
});

describe("任務詳情：手動重試的 toast（C-9；契約 §1.6.4、QA O-04）", () => {
  it("手動重試不受 maxRetries 限制：retryCount 3 > maxRetries 1 時文案是「手動重試第 3 次（不計入自動重試上限 1）」，不是「3 / 1」", async () => {
    const { calls } = backend((c) => (c.method === "POST" && c.path === "/api/v1/tasks/t1/retry" ? { data: task({ status: "QUEUED", retryCount: 3, maxRetries: 1 }) } : undefined));
    view(<TaskDetailView />);
    await userEvent.click(await screen.findByRole("button", { name: "重試" }));
    expect(await screen.findByText("已重新排入佇列：手動重試第 3 次（不計入自動重試上限 1）")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST" && c.path === "/api/v1/tasks/t1/retry")).toBe(true);
    expect(screen.queryByText(/重試 3 \/ 1/)).toBeNull();
  });
});

describe("刪除任務／目標遇到 409 project_executing（C-8；契約 §1.6.3、QA O-05）", () => {
  const blocked = () =>
    failure(409, {
      message: "專案有進行中批次",
      reason: REASONS.PROJECT_EXECUTING,
      details: { projectId: "p1", runId: "r1" },
    });

  it("任務：確認刪除後對話框顯示白話原因（含 traceId），不關閉、不導頁；批次結束後同一請求成功才導回", async () => {
    let executing = true;
    const { calls } = backend((c) => {
      if (c.method === "DELETE" && c.path === "/api/v1/tasks/t1") return executing ? blocked() : { status: 204 };
      return undefined;
    });
    view(<TaskDetailView />);
    await userEvent.click(await screen.findByRole("button", { name: "刪除" }));
    const dialog = await screen.findByRole("dialog", { name: "刪除任務" });
    await userEvent.click(within(dialog).getByRole("button", { name: "確認刪除" }));

    const alert = await within(dialog).findByRole("alert");
    expect(alert).toHaveTextContent("專案目前有進行中的執行批次");
    expect(alert).toHaveTextContent("到執行頁取消批次後再刪除");
    expect(alert).toHaveTextContent("traceId：tr-409");
    expect(alert).not.toHaveTextContent("project_executing");
    expect(router.replace).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog", { name: "刪除任務" })).toBeInTheDocument();

    // 批次結束後同一個動作成功
    executing = false;
    await userEvent.click(within(dialog).getByRole("button", { name: "確認刪除" }));
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/projects/p1/goals/g1"));
    expect(calls.filter((c) => c.method === "DELETE")).toHaveLength(2);
  });

  it("目標：同樣顯示白話原因；既有的 409「RUNNING 狀態的任務不可刪除」維持原訊息（含 reason 字串）", async () => {
    let reply: "project" | "running" = "project";
    backend((c) => {
      if (c.method === "DELETE" && c.path === "/api/v1/goals/g1") {
        return reply === "project" ? blocked() : failure(409, { message: "目標含執行中任務", reason: REASONS.TASK_RUNNING_NOT_DELETABLE });
      }
      return undefined;
    });
    view(<GoalDetailView />);
    await userEvent.click(await screen.findByRole("button", { name: "刪除目標" }));
    const dialog = await screen.findByRole("dialog", { name: "刪除目標" });
    await userEvent.click(within(dialog).getByRole("button", { name: "確認刪除" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("專案目前有進行中的執行批次");
    expect(router.replace).not.toHaveBeenCalled();

    reply = "running";
    await userEvent.click(within(dialog).getByRole("button", { name: "確認刪除" }));
    await waitFor(() => expect(within(dialog).getByRole("alert")).toHaveTextContent("目標含執行中任務：RUNNING 狀態的任務不可刪除"));
  });
});
