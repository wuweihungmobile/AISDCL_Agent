import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { initialRouteForm } from "@/lib/domain/research";
import { RouteCardA } from "./RouteCardA";

const form = initialRouteForm({ rpNo: "RP-0003", targetScope: "AISDLC_MODULE", topic: "x", slug: "x" }, "A", undefined);
const baseProps = { form, onChange: () => undefined, errors: {}, defaultModule: "autoclaude" as const, onSelect: () => undefined };

/** 卡 A（AT-961-17-3 的元件載具）：選取、欄位、停用說明。 */
describe("RouteCardA", () => {
  it("未選取時只顯示標題與說明，不渲染欄位；選取後顯示分支名、基底 ref、掛載目標、出處清單與登記預覽", () => {
    const { rerender } = render(<RouteCardA {...baseProps} selected={false} disabled={false} />);
    expect(screen.getByRole("radio", { name: /軌道 A/ })).toHaveAttribute("aria-checked", "false");
    expect(screen.queryByLabelText(/分支名/)).toBeNull();
    rerender(<RouteCardA {...baseProps} selected disabled={false} />);
    expect(screen.getByLabelText(/分支名/)).toHaveValue("feature/issue-0003");
    expect(screen.getAllByRole("listitem")).toHaveLength(4);
    expect(screen.getByTestId("module-registry-preview")).toHaveTextContent("模組登錄預覽");
  });

  it("輸入與選擇以 patch 交給 onChange；選卡呼叫 onSelect", async () => {
    const onChange = vi.fn();
    const onSelect = vi.fn();
    render(<RouteCardA {...baseProps} onChange={onChange} onSelect={onSelect} selected disabled={false} />);
    fireEvent.change(screen.getByLabelText(/基底 ref/), { target: { value: "develop" } });
    expect(onChange).toHaveBeenCalledWith({ baseRef: "develop" });
    await userEvent.setup().selectOptions(screen.getByRole("combobox", { name: /掛載目標/ }), "monorepo");
    expect(onChange).toHaveBeenCalledWith({ targetModule: "monorepo" });
    await userEvent.setup().click(screen.getByRole("radio", { name: /軌道 A/ }));
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("停用時卡停用、title 與說明為停用原因、不渲染欄位，點擊不呼叫 onSelect", async () => {
    const onSelect = vi.fn();
    render(<RouteCardA {...baseProps} onSelect={onSelect} selected disabled disabledReason="此部署無法寫入 monorepo（容器模式）；請改用本機模式" />);
    const radio = screen.getByRole("radio", { name: /軌道 A/ });
    expect(radio).toBeDisabled();
    expect(radio).toHaveAttribute("title", "此部署無法寫入 monorepo（容器模式）；請改用本機模式");
    expect(screen.getByTestId("route-card-a-disabled")).toBeInTheDocument();
    expect(screen.queryByLabelText(/分支名/)).toBeNull();
    await userEvent.setup().click(radio);
    expect(onSelect).not.toHaveBeenCalled();
  });
});
