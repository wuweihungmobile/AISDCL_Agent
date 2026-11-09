import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { forgetProjectId, getLastProjectId, rememberProjectId } from "@/lib/nav/lastProject";
import { Providers, makeClient, signIn, stubApi } from "@/tests/helpers/api";
import { projectDetail } from "@/tests/helpers/runFixtures";
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
 * 專案刪除成功即遺忘最近造訪（DEF-AC-035；TCS-ExecMonitorEntry 勘誤 11 W-E8、AT_953_6_8）。
 * 註：專案「刪除」入口住專案詳情頁（專案管理頁只有「復原」），所以 AT 落在本檔而非 ProjectsView.test.tsx（勘誤 11 的落點更正）。
 * 判定指令：npx vitest run components/domain/views/ProjectDetailView.forget.test.tsx
 */
beforeEach(() => signIn("OPERATOR", "operator"));
afterEach(() => {
  forgetProjectId("p1");
  forgetProjectId("p2");
});

async function deleteThisProject() {
  stubApi((c) => {
    if (c.method === "GET" && c.path === "/api/v1/projects/p1") return { data: projectDetail({ id: "p1" }) };
    if (c.method === "DELETE" && c.path === "/api/v1/projects/p1") return { status: 204 };
    return undefined;
  });
  render(
    <Providers client={makeClient()}>
      <ProjectDetailView />
    </Providers>,
  );
  await userEvent.click(await screen.findByRole("button", { name: "刪除專案" }));
  await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "確認刪除" }));
  await screen.findByText(/已刪除專案「/);
}

describe("AT_953_6_8 專案刪除成功即遺忘最近造訪", () => {
  it("最近造訪＝p1，刪除 p1 成功：鍵被移除", async () => {
    rememberProjectId("p1");
    await deleteThisProject();
    await waitFor(() => expect(getLastProjectId()).toBeNull());
  });

  it("最近造訪＝p2，刪除 p1 成功：鍵仍是 p2（只清相等的 id）", async () => {
    rememberProjectId("p2");
    await deleteThisProject();
    expect(getLastProjectId()).toBe("p2");
  });
});
