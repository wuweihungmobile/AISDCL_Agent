import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PublicRepoConfirm } from "./PublicRepoConfirm";

/** Public 確認元件（AT-961-17-4、17-E-1 的元件載具）：警示文字、逐字比對、停用。 */
describe("PublicRepoConfirm 公開庫名確認", () => {
  it("顯示「PRD 與證據矩陣將公開」警示與「重新輸入庫名」欄；完全相同才標為已確認，不修剪、不正規化", () => {
    const { rerender } = render(<PublicRepoConfirm repoName="demo-app" value="" onChange={() => undefined} />);
    expect(screen.getByRole("note")).toHaveTextContent("PRD 與證據矩陣將公開");
    expect(screen.getByTestId("public-repo-confirm")).toHaveAttribute("data-confirmed", "false");
    for (const wrong of ["demo-ap", "Demo-App", "demo-app ", "demo-app\u200b"]) {
      rerender(<PublicRepoConfirm repoName="demo-app" value={wrong} onChange={() => undefined} />);
      expect(screen.getByTestId("public-repo-confirm"), JSON.stringify(wrong)).toHaveAttribute("data-confirmed", "false");
      expect(screen.getByRole("alert")).toHaveTextContent("與庫名不完全相同");
    }
    rerender(<PublicRepoConfirm repoName="demo-app" value="demo-app" onChange={() => undefined} />);
    expect(screen.getByTestId("public-repo-confirm")).toHaveAttribute("data-confirmed", "true");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("輸入原樣交給 onChange（不修剪）；停用時輸入框停用並帶說明", () => {
    const onChange = vi.fn();
    const { rerender } = render(<PublicRepoConfirm repoName="demo-app" value="" onChange={onChange} />);
    fireEvent.change(screen.getByLabelText(/重新輸入庫名/), { target: { value: " demo-app " } });
    expect(onChange).toHaveBeenCalledWith(" demo-app ");
    rerender(<PublicRepoConfirm repoName="demo-app" value="" onChange={onChange} disabled disabledTitle="權限不足" />);
    expect(screen.getByLabelText(/重新輸入庫名/)).toBeDisabled();
    expect(screen.getByLabelText(/重新輸入庫名/)).toHaveAttribute("title", "權限不足");
  });
});
