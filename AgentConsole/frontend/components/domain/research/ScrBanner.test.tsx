/**
 * 規格變更橫幅與停用規則（TCS-ResearchToPRD-P2-20261107 AT-962-15-5）：`scrOpen=true` 時橫幅文字為「規格變更中：SCR-<n>（<kind>）」並連到工作室；
 * 看板、InnerLoopLinks、GateRegisterDialog 的啟動類動作一律停用並顯示同一句登記文案（`BUILD_DISABLED_TEXT.scrOpen`）；`executionBlock()` 簽名不變。
 * 第四處 ReleaseActions 是 PKG-FE-P2B 在波 2 才建的元件，它的 SCR_OPEN 停用由 `ReleaseActions.test.tsx`（AT-962-21-3）承接（任務書〈待裁決〉#3）。
 */
import { fireEvent, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { BUILD_DISABLED_TEXT, executionBlock } from "@/lib/domain/research";
import { CONSOLE_PROJECT_ID, R3 } from "@/tests/fixtures/research/ids";
import { kanbanWith } from "@/tests/fixtures/research/p2";
import { renderResearch, stubResearchApi } from "@/tests/helpers/research";
import { GateRegisterDialog } from "./GateRegisterDialog";
import { InnerLoopLinks } from "./InnerLoopLinks";
import { KanbanBoard } from "./KanbanBoard";
import { ScrBanner } from "./ScrBanner";

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

const SCR_LIST = [
  { scrNo: 1, kind: "MINOR", status: "CLOSED" },
  { scrNo: 3, kind: "MAJOR", status: "OPEN" },
];

describe("SCR_OPEN 橫幅與停用規則", () => {
  it("AT_962_15_5 scrOpen=true：橫幅『規格變更中：SCR-3（MAJOR）』並連到工作室；看板、InnerLoopLinks、GateRegisterDialog 的啟動類動作停用並顯示同一句登記文案；executionBlock 簽名不變", async () => {
    stubResearchApi({
      kanban: kanbanWith({ scrOpen: true }),
      overrides: (call) => (call.method === "GET" && call.path === `/api/v1/research/projects/${R3}/scr` ? { data: SCR_LIST } : undefined),
    });
    renderResearch(
      <>
        <ScrBanner researchId={R3} scrOpen />
        <KanbanBoard researchId={R3} />
        <InnerLoopLinks consoleProjectId={CONSOLE_PROJECT_ID} block={executionBlock({ scrOpen: true, decomposition: null, tcsFrozen: false })} researchId={R3} />
        <GateRegisterDialog researchId={R3} scrOpen />
      </>,
      "ADMIN",
    );
    await screen.findByTestId("kanban-board");

    // 橫幅：文字與連結（看板內另有一份同元件的橫幅，兩份文字一致）
    const banners = await screen.findAllByTestId("scr-banner");
    // 整併後看板內不再另渲染橫幅：本測試自己放的一個 ScrBanner 是頁面上唯一的 scr-banner（D-155）
    expect(banners).toHaveLength(1);
    for (const banner of banners) {
      await within(banner).findByText("規格變更中：SCR-3（MAJOR）");
      expect(within(banner).getByRole("link", { name: "前往規格工作室" }).getAttribute("href")).toBe(`/research/${R3}?step=studio`);
      expect(banner.textContent).toContain(BUILD_DISABLED_TEXT.scrOpen);
    }

    // 看板：執行中心連結停用、title 為登記文案
    expect(screen.getByTestId("kanban-exec-implement").getAttribute("href")).toBeNull();
    expect(screen.getByTestId("kanban-exec-implement").getAttribute("title")).toBe(BUILD_DISABLED_TEXT.scrOpen);
    // 看板的發起 SCR 入口也停用並說明
    expect(screen.getAllByTestId("scr-launch").every((b) => (b as HTMLButtonElement).disabled && b.getAttribute("title") === BUILD_DISABLED_TEXT.scrOpen)).toBe(true);
    // InnerLoopLinks：停用並顯示同一句
    const links = within(screen.getByTestId("inner-loop-links"));
    expect(links.getByTestId("execute-disabled").getAttribute("title")).toBe(BUILD_DISABLED_TEXT.scrOpen);
    expect(links.getByTestId("execute-block-reason").textContent).toContain(BUILD_DISABLED_TEXT.scrOpen);
    // GateRegisterDialog：開啟後送出停用並顯示同一句
    fireEvent.click(screen.getAllByTestId("gate-register-trigger")[0]);
    const dialog = await screen.findByTestId("gate-dialog");
    expect(within(dialog).getByTestId("gate-scr-open").textContent).toBe(BUILD_DISABLED_TEXT.scrOpen);
    expect((within(dialog).getByTestId("gate-submit") as HTMLButtonElement).disabled).toBe(true);

    // executionBlock 簽名不變：單一物件參數、scrOpen 優先、文案取登記處
    expect(executionBlock.length).toBe(1);
    expect(executionBlock({ scrOpen: true, decomposition: null, tcsFrozen: false })).toBe("scrOpen");
    expect(BUILD_DISABLED_TEXT[executionBlock({ scrOpen: true, decomposition: null, tcsFrozen: true }) ?? "scrOpen"]).toBe(BUILD_DISABLED_TEXT.scrOpen);
  });

  it("AT_962_15_5 scrOpen=false：橫幅不渲染", () => {
    stubResearchApi({});
    renderResearch(<ScrBanner researchId={R3} scrOpen={false} />, "OPERATOR");
    expect(screen.queryByTestId("scr-banner")).toBeNull();
  });
});
