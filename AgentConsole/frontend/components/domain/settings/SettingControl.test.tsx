import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Config } from "@/lib/api/types";
import { FIXTURE, cfg } from "@/tests/helpers/settingsFixtures";
import { SettingControl } from "./SettingControl";
import { MASK } from "./settingsModel";

function setup(config: Config, over: Partial<Parameters<typeof SettingControl>[0]> = {}) {
  const onChange = vi.fn();
  const onToggleVisible = vi.fn();
  render(<SettingControl config={config} label="測試參數" value={config.value} onChange={onChange} onToggleVisible={onToggleVisible} {...over} />);
  return { onChange, onToggleVisible };
}

describe("設定控制項依 valueType 渲染（七種各一）", () => {
  it("STRING → 文字 input（技術字串可用等寬字體）", async () => {
    const { onChange } = setup(FIXTURE.name(), { mono: true });
    const input = screen.getByRole("textbox", { name: "測試參數" });
    expect(input).toHaveValue("MiniMax-M2.7");
    expect(input).toHaveAttribute("inputmode", "text");
    expect(input).toHaveClass("font-mono");
    await userEvent.type(input, "x");
    expect(onChange).toHaveBeenLastCalledWith("MiniMax-M2.7x");
  });

  it("INTEGER → input＋數字鍵盤（inputMode=numeric，不用 type=number，非法輸入也能被看見並驗證）", () => {
    setup(FIXTURE.maxTokensPerRequest());
    const input = screen.getByRole("textbox", { name: "測試參數" });
    expect(input).toHaveAttribute("inputmode", "numeric");
    expect(input).not.toHaveAttribute("type", "number");
    expect(input).toHaveValue("8192");
  });

  it("LONG → input＋numeric；FLOAT → input＋decimal", () => {
    const { unmount } = render(<SettingControl config={FIXTURE.globalTokenBudget()} label="預算" value="1000000" onChange={() => {}} />);
    expect(screen.getByRole("textbox", { name: "預算" })).toHaveAttribute("inputmode", "numeric");
    unmount();
    render(<SettingControl config={FIXTURE.temperature()} label="溫度" value="0.3" onChange={() => {}} />);
    expect(screen.getByRole("textbox", { name: "溫度" })).toHaveAttribute("inputmode", "decimal");
  });

  it("ENUM → select，選項取自 options；目前值不在選項內時仍顯示出來（不悄悄跳到第一項）", async () => {
    const { onChange } = setup(FIXTURE.dagSchedulerStrategy());
    const select = screen.getByRole("combobox", { name: "測試參數" });
    expect([...select.querySelectorAll("option")].map((o) => o.textContent)).toEqual(["TOPOLOGICAL", "PRIORITY", "SHORTEST_FIRST"]);
    await userEvent.selectOptions(select, "PRIORITY");
    expect(onChange).toHaveBeenCalledWith("PRIORITY");
  });

  it("ENUM 目前值是未知選項：附加成最後一項並維持選取", () => {
    setup({ ...FIXTURE.dagSchedulerStrategy(), value: "LEGACY" });
    const select = screen.getByRole("combobox", { name: "測試參數" }) as HTMLSelectElement;
    expect(select.value).toBe("LEGACY");
    expect([...select.options].map((o) => o.value)).toEqual(["TOPOLOGICAL", "PRIORITY", "SHORTEST_FIRST", "LEGACY"]);
  });

  it("BOOLEAN → toggle 開關（role=switch，46×26）：點一下切換 true／false", async () => {
    const { onChange } = setup(FIXTURE.enableKernelBrain());
    const toggle = screen.getByRole("switch", { name: "測試參數" });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    expect(toggle.className).toContain("h-[26px]");
    expect(toggle.className).toContain("w-[46px]");
    await userEvent.click(toggle);
    expect(onChange).toHaveBeenCalledWith("true");
  });

  it("BOOLEAN 已開啟：再點一下回報 false；鍵盤空白鍵也能切換", async () => {
    const { onChange } = setup({ ...FIXTURE.enableKernelBrain(), value: "true" });
    const toggle = screen.getByRole("switch", { name: "測試參數" });
    expect(toggle).toHaveAttribute("aria-checked", "true");
    toggle.focus();
    await userEvent.keyboard(" ");
    expect(onChange).toHaveBeenCalledWith("false");
  });

  it("ENCRYPTED → password input（預設遮罩）＋「顯示」按鈕；展開後改成明文輸入框、按鈕變「隱藏」", () => {
    const { unmount } = render(<SettingControl config={FIXTURE.apiKey()} label="金鑰" value={MASK} onChange={() => {}} canReveal />);
    const input = screen.getByLabelText("金鑰");
    expect(input).toHaveAttribute("type", "password");
    expect(input).toHaveValue(MASK);
    expect(screen.getByRole("button", { name: "顯示：金鑰" })).toBeEnabled();
    unmount();
    render(<SettingControl config={FIXTURE.apiKey()} label="金鑰" value="sk-plain" onChange={() => {}} canReveal visible />);
    expect(screen.getByLabelText("金鑰")).toHaveAttribute("type", "text");
    expect(screen.getByRole("button", { name: "隱藏：金鑰" })).toBeInTheDocument();
  });

  it("ENCRYPTED：非 ADMIN 不能揭露——按鈕停用並說明；尚未設定的鍵沒有可顯示的值", () => {
    const { unmount } = render(<SettingControl config={FIXTURE.apiKey()} label="金鑰" value={MASK} onChange={() => {}} canReveal={false} />);
    expect(screen.getByRole("button", { name: "顯示：金鑰" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "顯示：金鑰" })).toHaveAttribute("title", "僅 ADMIN 可揭露敏感參數");
    unmount();
    render(<SettingControl config={FIXTURE.apiKey(false)} label="金鑰" value="" onChange={() => {}} canReveal />);
    expect(screen.getByRole("button", { name: "顯示：金鑰" })).toBeDisabled();
    expect(screen.getByLabelText("金鑰")).toHaveAttribute("placeholder", "尚未設定");
  });

  it("ENCRYPTED：聚焦遮罩欄位就全選，輸入直接取代（不會接在 ●●●●●●●● 後面）", async () => {
    const onChange = vi.fn();
    render(<SettingControl config={FIXTURE.apiKey()} label="金鑰" value={MASK} onChange={onChange} canReveal />);
    const input = screen.getByLabelText("金鑰") as HTMLInputElement;
    await userEvent.click(input);
    expect(input.selectionStart).toBe(0);
    expect(input.selectionEnd).toBe(MASK.length);
    await userEvent.keyboard("s");
    expect(onChange).toHaveBeenLastCalledWith("s");
  });

  it("disabled 與 invalid：整個控制項停用；invalid 標 aria-invalid", () => {
    const { unmount } = render(<SettingControl config={FIXTURE.maxTokensPerRequest()} label="x" value="8192" onChange={() => {}} disabled invalid />);
    const input = screen.getByRole("textbox", { name: "x" });
    expect(input).toBeDisabled();
    expect(input).toHaveAttribute("aria-invalid", "true");
    unmount();
    render(<SettingControl config={cfg("model", "toggle", { valueType: "BOOLEAN", value: "true" })} label="t" value="true" onChange={() => {}} disabled />);
    expect(screen.getByRole("switch", { name: "t" })).toBeDisabled();
  });
});
