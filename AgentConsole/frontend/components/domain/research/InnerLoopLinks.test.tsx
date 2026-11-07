/**
 * 內環連結帶 researchId（TCS-ResearchToPRD-P2-20261107 AT-962-16-4）：看板與 InnerLoopLinks 開啟執行中心與監控中心的 href 一律帶 `?researchId=<uuid>`（UUID 驗證，非 UUID 一律忽略）。
 * 看板那一半在 KanbanBoard.test.tsx（AT_962_11_6）；這裡驗連結端與兩元件在同一個研究專案下 href 一致。
 */
import { render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { consoleCenterHref, isResearchUuid } from "@/lib/domain/research";
import { CONSOLE_PROJECT_ID, R3 } from "@/tests/fixtures/research/ids";
import { KANBAN } from "@/tests/fixtures/research/p2";
import { renderResearch, stubResearchApi } from "@/tests/helpers/research";
import { InnerLoopLinks } from "./InnerLoopLinks";
import { KanbanBoard } from "./KanbanBoard";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
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

describe("深連結的 researchId", () => {
  it("AT_962_16_4 已綁 Console 專案：InnerLoopLinks 與看板所有開啟執行中心與監控中心的 href 皆含 ?researchId=<uuid>，UUID 格式驗證通過", async () => {
    stubResearchApi({ kanban: KANBAN });
    renderResearch(
      <>
        <InnerLoopLinks consoleProjectId={CONSOLE_PROJECT_ID} block={null} researchId={R3} />
        <KanbanBoard researchId={R3} />
      </>,
      "OPERATOR",
    );
    await screen.findByTestId("kanban-board");
    const links = within(screen.getByTestId("inner-loop-links"));
    const hrefs = [
      links.getByRole("link", { name: "執行中心" }).getAttribute("href"),
      links.getByRole("link", { name: "監控中心" }).getAttribute("href"),
      ...screen.getAllByTestId(/^kanban-(exec|monitor)-/).map((el) => el.getAttribute("href")),
    ];
    expect(hrefs.length).toBe(12);
    for (const href of hrefs) {
      expect(href).toMatch(/^\/projects\/[^/?]+\/(execute|monitor)\?researchId=[0-9a-f-]{36}$/);
      expect(isResearchUuid(new URL(href as string, "http://x").searchParams.get("researchId"))).toBe(true);
    }
    expect(new Set(hrefs).size).toBe(2); // 同一個專案只有兩條不同的深連結
  });

  it("AT_962_16_4 非 UUID 的 researchId 一律忽略（不帶 query）；專案頁（凍結與匯入）不是中心連結，不帶", () => {
    for (const bad of ["../x", "<script>", "123", "g".repeat(36), "", null, undefined]) {
      expect(consoleCenterHref("p1", "execute", bad)).toBe("/projects/p1/execute");
    }
    const view = render(<InnerLoopLinks consoleProjectId="p1" block={null} researchId="<script>" />);
    expect(within(view.container).getByRole("link", { name: "監控中心" }).getAttribute("href")).toBe("/projects/p1/monitor");
    expect(within(view.container).getByRole("link", { name: "專案頁（凍結與匯入）" }).getAttribute("href")).toBe("/projects/p1");
  });
});
