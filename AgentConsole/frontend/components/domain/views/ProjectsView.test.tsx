import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { REASONS } from "@/lib/api/reasons";
import { Providers, failure, makeClient, signIn, stubApi, type ApiCall, type Reply } from "@/tests/helpers/api";
import { ProjectsView } from "./ProjectsView";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/projects",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
// Markdown 編輯器本體很重且與本測試無關（建立／編輯對話框不會被打開）
vi.mock("@/components/markdown/MarkdownEditor", () => ({
  MarkdownEditor: ({ value, label }: { value: string; label: string }) => <textarea aria-label={label} defaultValue={value} />,
}));

const TS = "2026-10-15T08:30:12Z";
const summary = (id: string, name: string, patch: Record<string, unknown> = {}) => ({
  id,
  name,
  executionPath: `/work/${name}`,
  status: "READY",
  autonomyLevel: 3,
  signedOff: true,
  goalsCount: 2,
  tasksCount: 3,
  tasksDone: 1,
  updatedAt: TS,
  ...patch,
});
const page = (content: object[]) => ({ content, page: 0, size: 10, totalElements: content.length, totalPages: 1 });

const LIVE = [summary("p1", "專案甲"), summary("p2", "專案乙", { status: "EXECUTING" })];
const DELETED = [summary("p9", "已刪除專案丙", { status: "ARCHIVED", deletedAt: "2026-10-10T06:00:00Z" }), summary("p8", "已刪除專案丁", { status: "ARCHIVED", deletedAt: "2026-09-01T06:00:00Z" })];

function backend(extra: (c: ApiCall) => Reply = () => undefined) {
  return stubApi((c) => {
    const custom = extra(c);
    if (custom) return custom;
    if (c.method === "GET" && c.path === "/api/v1/projects") return { data: page(c.query.get("deleted") === "true" ? DELETED : LIVE) };
    return undefined;
  });
}

function view() {
  return render(
    <Providers client={makeClient()}>
      <ProjectsView />
    </Providers>,
  );
}

const listCalls = (calls: ApiCall[]) => calls.filter((c) => c.method === "GET" && c.path === "/api/v1/projects");

beforeEach(() => signIn("OPERATOR", "operator"));

describe("專案列表：「已刪除」篩選（C-3；契約 §1.6.2、§4.5 G-09）", () => {
  it("OPERATOR 以上才有「已刪除」鈕；VIEWER 看不到（後端對 VIEWER 的 deleted=true 回 403）", async () => {
    backend();
    const first = view();
    expect(await screen.findByTestId("deleted-filter")).toHaveTextContent("已刪除");
    first.unmount();

    signIn("VIEWER", "viewer");
    backend();
    view();
    await screen.findByTestId("project-list");
    expect(screen.queryByTestId("deleted-filter")).toBeNull();
  });

  it("按「已刪除」：改打 GET /projects?deleted=true（不帶 status）；卡片顯示「已刪除」標籤與刪除時間、只有「復原」鈕（沒有查看／編輯／執行／監控）；再按一次回一般清單", async () => {
    const { calls } = backend();
    view();
    await screen.findByTestId("project-list");
    expect(screen.getAllByTestId("project-card")).toHaveLength(2);
    expect(listCalls(calls).at(-1)?.query.has("deleted")).toBe(false); // 一般清單：不帶 deleted

    await userEvent.click(screen.getByTestId("deleted-filter"));
    await waitFor(() => expect(screen.getAllByTestId("project-card")).toHaveLength(2));
    const last = listCalls(calls).at(-1)!;
    expect(last.query.get("deleted")).toBe("true");
    expect(last.query.has("status")).toBe(false);
    expect(screen.getByTestId("deleted-filter")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("deleted-hint")).toHaveTextContent("保留一段時間（預設 30 天）");
    expect(screen.queryByRole("group", { name: "狀態篩選" })).toBeNull();

    const card = screen.getAllByTestId("project-card")[0];
    expect(card).toHaveAttribute("data-deleted", "true");
    expect(within(card).getByText("已刪除專案丙")).toBeInTheDocument();
    expect(within(card).queryByRole("link", { name: "已刪除專案丙" })).toBeNull(); // 詳情頁已 404：不是連結
    expect(within(card).getByTestId("deleted-tag")).toHaveTextContent("已刪除");
    expect(within(card).getByTestId("deleted-at")).toHaveTextContent(/^刪除於 \d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
    expect(within(card).getByTestId("project-restore")).toBeEnabled();
    for (const name of ["查看", "編輯", "執行", "監控"]) expect(within(card).queryByRole("button", { name }) ?? within(card).queryByRole("link", { name })).toBeNull();

    await userEvent.click(screen.getByTestId("deleted-filter"));
    await waitFor(() => expect(screen.getAllByTestId("project-card")[0]).not.toHaveAttribute("data-deleted"));
    expect(listCalls(calls).at(-1)?.query.has("deleted")).toBe(false);
    expect(screen.getByRole("group", { name: "狀態篩選" })).toBeInTheDocument();
  });

  it("沒有已刪除專案：空狀態說明保留期內可復原", async () => {
    backend((c) => (c.path === "/api/v1/projects" && c.query.get("deleted") === "true" ? { data: page([]) } : undefined));
    view();
    await userEvent.click(await screen.findByTestId("deleted-filter"));
    expect(await screen.findByText("沒有已刪除的專案")).toBeInTheDocument();
    expect(screen.getByText("刪除的專案會出現在這裡，保留期內可以復原。")).toBeInTheDocument();
  });
});

describe("專案列表：復原（POST /projects/{id}/restore；C-3）", () => {
  async function openDeleted() {
    view();
    await userEvent.click(await screen.findByTestId("deleted-filter"));
    await waitFor(() => expect(screen.getAllByTestId("project-card")).toHaveLength(2));
  }

  it("成功：送出 POST、toast 說明已復原並帶目標／任務數、清單重抓（復原的專案不再出現在已刪除清單）", async () => {
    let restored = false;
    const { calls } = backend((c) => {
      if (c.method === "POST" && c.path === "/api/v1/projects/p9/restore") {
        restored = true;
        return { data: { ...summary("p9", "已刪除專案丙"), goals: [], createdAt: TS, passCriteria: "- ok" } };
      }
      if (c.method === "GET" && c.path === "/api/v1/projects" && c.query.get("deleted") === "true") return { data: page(restored ? [DELETED[1]] : DELETED) };
      return undefined;
    });
    await openDeleted();
    await userEvent.click(within(screen.getAllByTestId("project-card")[0]).getByTestId("project-restore"));

    expect(await screen.findByText(/已復原專案「已刪除專案丙」（2 個目標、3 個任務）/)).toBeInTheDocument();
    expect(calls.filter((c) => c.method === "POST" && c.path === "/api/v1/projects/p9/restore")).toHaveLength(1);
    await waitFor(() => expect(screen.getAllByTestId("project-card")).toHaveLength(1));
    expect(screen.getByText("已刪除專案丁")).toBeInTheDocument();
  });

  it("409 project_not_deleted：說明「目前沒有被刪除」，並重抓清單（它其實已被復原）", async () => {
    const { calls } = backend((c) =>
      c.method === "POST" && c.path === "/api/v1/projects/p9/restore"
        ? failure(409, { message: "專案未被刪除", reason: REASONS.PROJECT_NOT_DELETED, details: { projectId: "p9", status: "READY" } })
        : undefined,
    );
    await openDeleted();
    const before = listCalls(calls).length;
    await userEvent.click(within(screen.getAllByTestId("project-card")[0]).getByTestId("project-restore"));
    expect(await screen.findByText(/復原失敗：這個專案目前沒有被刪除（可能已被其他人復原），不需要復原。/)).toBeInTheDocument();
    await waitFor(() => expect(listCalls(calls).length).toBeGreaterThan(before));
  });

  it("409 restore_window_expired：說明超過保留期（帶 retentionDays）；清單不動、專案仍在清單上", async () => {
    const { calls } = backend((c) =>
      c.method === "POST" && c.path === "/api/v1/projects/p8/restore"
        ? failure(409, { message: "已逾保留期", reason: REASONS.RESTORE_WINDOW_EXPIRED, details: { projectId: "p8", deletedAt: "2026-09-01T06:00:00Z", retentionDays: 30 } })
        : undefined,
    );
    await openDeleted();
    const before = listCalls(calls).length;
    await userEvent.click(within(screen.getAllByTestId("project-card")[1]).getByTestId("project-restore"));
    expect(await screen.findByText(/復原失敗：這個專案刪除已超過保留期（30 天），無法復原。/)).toBeInTheDocument();
    expect(listCalls(calls)).toHaveLength(before); // 專案還在、沒有理由重抓
    expect(screen.getAllByTestId("project-card")).toHaveLength(2);
  });

  it("404（已被清除）：說明無法復原並重抓清單；403 等其他錯誤照一般訊息", async () => {
    let status: 404 | 403 = 404;
    const { calls } = backend((c) => {
      if (c.method === "POST" && c.path === "/api/v1/projects/p9/restore") {
        return status === 404 ? failure(404, { message: "專案不存在或已清除：p9" }) : failure(403, { message: "權限不足", reason: REASONS.ACCESS_DENIED });
      }
      return undefined;
    });
    await openDeleted();
    const before = listCalls(calls).length;
    await userEvent.click(within(screen.getAllByTestId("project-card")[0]).getByTestId("project-restore"));
    expect(await screen.findByText(/復原失敗：找不到這個專案：它可能已被永久清除，無法復原。/)).toBeInTheDocument();
    await waitFor(() => expect(listCalls(calls).length).toBeGreaterThan(before));

    status = 403;
    await userEvent.click(within(screen.getAllByTestId("project-card")[0]).getByTestId("project-restore"));
    expect(await screen.findByText(/復原失敗：權限不足：ACCESS_DENIED/)).toBeInTheDocument();
  });
});
