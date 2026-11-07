import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { initialRouteForm } from "@/lib/domain/research";
import { RouteCardB } from "./RouteCardB";

const form = { ...initialRouteForm({ rpNo: "RP-0003", targetScope: "STANDALONE_PROJECT", topic: "x", slug: "x" }, "B", { scaffoldTemplates: ["python-fastapi"] }), projectName: "demo-app" };
const baseProps = { form, onChange: () => undefined, errors: {}, templates: ["python-fastapi"], onSelect: () => undefined };

/** 卡 B（AT-961-17-4 的元件載具）：欄位、Public 確認、GitHub 勾選停用。 */
describe("RouteCardB", () => {
  it("選取後顯示專案名稱、範本、owner、庫名、可見度與三個勾選；可見度預設 Private、CI 與 compose 預設勾選；Private 不出現公開確認", () => {
    render(<RouteCardB {...baseProps} selected disabled={false} />);
    expect(screen.getByLabelText(/^專案名稱/)).toHaveValue("demo-app");
    expect(screen.getByRole("combobox", { name: /可見度/ })).toHaveValue("PRIVATE");
    expect(screen.getByRole("checkbox", { name: "產生 CI 設定" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "產生 docker compose" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "建立 GitHub 遠端" })).not.toBeChecked();
    expect(screen.queryByTestId("public-repo-confirm")).toBeNull();
  });

  it("切到 Public 時以一次 patch 交出可見度並清掉確認名；Public 狀態下渲染公開確認", async () => {
    const onChange = vi.fn();
    const { rerender } = render(<RouteCardB {...baseProps} onChange={onChange} selected disabled={false} />);
    await userEvent.setup().selectOptions(screen.getByRole("combobox", { name: /可見度/ }), "PUBLIC");
    expect(onChange).toHaveBeenCalledWith({ visibility: "PUBLIC", confirmRepoName: "" });
    rerender(<RouteCardB {...baseProps} form={{ ...form, visibility: "PUBLIC" }} onChange={onChange} selected disabled={false} />);
    expect(screen.getByTestId("public-repo-confirm")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/重新輸入庫名/), { target: { value: "demo-app" } });
    expect(onChange).toHaveBeenCalledWith({ confirmRepoName: "demo-app" });
  });

  it("GitHub 勾選被停用時顯示說明且不可勾；整張卡停用時不渲染欄位", () => {
    const { rerender } = render(<RouteCardB {...baseProps} form={{ ...form, createGithub: true }} selected disabled={false} githubDisabledReason="找不到 gh；可先建本地專案，之後自行推送" />);
    const box = screen.getByRole("checkbox", { name: "建立 GitHub 遠端" });
    expect(box).toBeDisabled();
    expect(box).not.toBeChecked();
    expect(screen.getByTestId("github-disabled")).toHaveTextContent("找不到 gh");
    rerender(<RouteCardB {...baseProps} selected disabled disabledReason="尚未設定 BRIDGE_SCAFFOLD_ROOT 或無可用範本" />);
    expect(screen.getByRole("radio", { name: /軌道 B/ })).toBeDisabled();
    expect(screen.queryByLabelText(/^專案名稱/)).toBeNull();
    expect(screen.getByTestId("route-card-b-disabled")).toBeInTheDocument();
  });
});
