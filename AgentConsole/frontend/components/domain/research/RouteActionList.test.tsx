import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PREVIEW_A, PREVIEW_B } from "@/tests/fixtures/research/route";
import { RouteActionList } from "./RouteActionList";

/** 預演動作清單（AT-961-17-5 的元件載具）：純文字、外部系統徽章、警示、預期入版控檔案。 */
describe("RouteActionList 預演結果", () => {
  it("每個動作列出序號、步驟中文名、動作碼與目標；只有觸及外部系統者有「外部系統」徽章；沒有警示與檔案清單時不渲染該區", () => {
    render(<RouteActionList preview={PREVIEW_A} />);
    const items = within(screen.getByTestId("route-actions")).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("1. 驗證目標");
    expect(items[1]).toHaveTextContent("worktree_add");
    expect(screen.queryByText("外部系統")).toBeNull();
    expect(screen.queryByTestId("route-warnings")).toBeNull();
    expect(screen.queryByTestId("route-tracked-files")).toBeNull();
    expect(screen.getByTestId("route-preview")).toHaveTextContent("預演沒有改動任何東西");
  });

  it("軌道 B：外部系統徽章、警示、預期入版控檔案；target 內的 <script> 以純文字顯示且不產生元素", () => {
    const { container } = render(<RouteActionList preview={PREVIEW_B} />);
    const items = within(screen.getByTestId("route-actions")).getAllByRole("listitem");
    expect(items[1]).toHaveAttribute("data-external", "true");
    expect(items[1]).toHaveTextContent("外部系統");
    expect(items[0]).toHaveTextContent("<script>alert(1)</script>/demo-app");
    expect(container.querySelector("script")).toBeNull();
    expect(screen.getByTestId("route-warnings")).toHaveTextContent("PRD 與證據矩陣將公開");
    expect(screen.getByTestId("route-tracked-files")).toHaveTextContent("pyproject.toml");
  });

  it("別名 external 為真也標外部系統；未登記步驟名原樣顯示", () => {
    render(<RouteActionList preview={{ ...PREVIEW_A, actions: [{ seq: 1, action: "x", step: "NEW_STEP", target: "t", touchesExternal: false, external: true, detail: "" }] }} />);
    const item = within(screen.getByTestId("route-actions")).getByRole("listitem");
    expect(item).toHaveTextContent("外部系統");
    expect(item).toHaveTextContent("NEW_STEP");
  });
});
