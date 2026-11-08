import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SortBar } from "@/components/domain/common/SortBar";

const OPTIONS = [
  { key: "a", label: "甲" },
  { key: "b", label: "乙" },
];

describe("SortBar", () => {
  it("AT_963_4_E_1 控制列照常渲染、切換不丟例外；方向鈕 aria-label 兩句擇一", async () => {
    const onChange = vi.fn();
    const { rerender } = render(<SortBar options={OPTIONS} state={{ key: "a", dir: "asc" }} onChange={onChange} label="測試排序" />);
    expect(screen.getByRole("group", { name: "測試排序" })).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "排序" }), "b");
    expect(onChange).toHaveBeenLastCalledWith({ key: "b", dir: "asc" });
    await userEvent.click(screen.getByRole("button", { name: "目前由小到大，按一下改由大到小" }));
    expect(onChange).toHaveBeenLastCalledWith({ key: "a", dir: "desc" });
    rerender(<SortBar options={OPTIONS} state={{ key: "a", dir: "desc" }} onChange={onChange} label="測試排序" />);
    expect(screen.getByRole("button", { name: "目前由大到小，按一下改由小到大" })).toBeInTheDocument();
  });

  it("AT_963_4_E_1 options 為空陣列時不渲染下拉", () => {
    const { container } = render(<SortBar options={[]} state={{ key: "a", dir: "asc" }} onChange={() => {}} label="空" />);
    expect(container.querySelector("select")).toBeNull();
    expect(screen.getByRole("group", { name: "空" })).toBeInTheDocument();
  });
});
