import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { COPY_FEEDBACK_MS, CopyCommand, copyText } from "./CopyCommand";

/**
 * 恢復指令的複製（契約 §4.7.3）：優先 Clipboard API；失敗退回選取＋execCommand；兩條都失敗就老實說，不假裝成功。
 * jsdom 沒有 navigator.clipboard 與 document.execCommand，測試各自安裝替身。
 */
const COMMAND = 'cd "/sdd" && python -m x resume-from-escalation --reason "<人工原因>"';

function stubClipboard(writeText: (text: string) => Promise<void>) {
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
}
function stubExecCommand(result: boolean | "throws") {
  const fn = vi.fn(() => {
    if (result === "throws") throw new Error("不支援");
    return result;
  });
  Object.defineProperty(document, "execCommand", { value: fn, configurable: true });
  return fn;
}

beforeEach(() => {
  Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
  Object.defineProperty(document, "execCommand", { value: undefined, configurable: true });
});
afterEach(() => {
  vi.useRealTimers();
});

describe("copyText", () => {
  it("有 Clipboard API：寫入原字串（含 <人工原因> 佔位，不替換）並回 true", async () => {
    const writeText = vi.fn(async () => undefined);
    stubClipboard(writeText);
    expect(await copyText(COMMAND)).toBe(true);
    expect(writeText).toHaveBeenCalledWith(COMMAND);
  });

  it("Clipboard API 被拒絕（權限、非安全情境）：退回暫存 textarea＋execCommand；textarea 事後移除、不留在頁面", async () => {
    stubClipboard(async () => {
      throw new DOMException("denied", "NotAllowedError");
    });
    const exec = stubExecCommand(true);
    expect(await copyText(COMMAND)).toBe(true);
    expect(exec).toHaveBeenCalledWith("copy");
    expect(document.querySelectorAll("textarea")).toHaveLength(0);
  });

  it("沒有 Clipboard API 也沒有 execCommand、或 execCommand 回 false／丟例外：回 false（不丟例外）", async () => {
    expect(await copyText(COMMAND)).toBe(false);
    stubExecCommand(false);
    expect(await copyText(COMMAND)).toBe(false);
    stubExecCommand("throws");
    expect(await copyText(COMMAND)).toBe(false);
    expect(document.querySelectorAll("textarea")).toHaveLength(0);
  });
});

describe("CopyCommand 元件", () => {
  it("原樣顯示指令（等寬、不經 innerHTML）、標籤與 data-shell；按鈕名稱含標籤", () => {
    render(<CopyCommand shell="posix" label="POSIX（bash／zsh）" command={COMMAND} />);
    const block = screen.getByTestId("sdd-recovery-posix");
    expect(block).toHaveAttribute("data-shell", "posix");
    expect(screen.getByTestId("sdd-recovery-command-posix")).toHaveTextContent(COMMAND);
    expect(screen.getByTestId("sdd-recovery-command-posix").className).toContain("font-mono");
    expect(screen.getByRole("button", { name: "複製 POSIX（bash／zsh） 指令" })).toHaveTextContent("複製");
  });

  it("指令含 HTML 字元也只當文字顯示（不會被解析成標籤）", () => {
    render(<CopyCommand shell="powershell" label="PowerShell" command={'echo "<img src=x onerror=alert(1)>"'} />);
    expect(screen.getByTestId("sdd-recovery-command-powershell").querySelector("img")).toBeNull();
    expect(screen.getByTestId("sdd-recovery-command-powershell")).toHaveTextContent('echo "<img src=x onerror=alert(1)>"');
  });

  it("複製成功：按鈕變「已複製」（名稱同步改為「已複製 … 指令」，可見文字永遠包含在名稱裡）、隱藏的 status 宣告；2.4 秒後回到「複製」", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const writeText = vi.fn(async () => undefined);
    stubClipboard(writeText);
    render(<CopyCommand shell="powershell" label="PowerShell" command={COMMAND} />);
    await userEvent.click(screen.getByRole("button", { name: "複製 PowerShell 指令" }));
    expect(writeText).toHaveBeenCalledWith(COMMAND);
    const done = await screen.findByRole("button", { name: "已複製 PowerShell 指令" });
    expect(done).toHaveTextContent("已複製");
    expect(screen.getByRole("status")).toHaveTextContent("已複製 PowerShell 指令");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(COPY_FEEDBACK_MS + 100);
    });
    expect(screen.getByRole("button", { name: "複製 PowerShell 指令" })).toHaveTextContent(/^複製$/);
    expect(screen.getByRole("status")).toHaveTextContent("");
  });

  it("複製失敗：不假裝成功——顯示「複製失敗，請手動選取」（alert），按鈕維持「複製」", async () => {
    render(<CopyCommand shell="posix" label="POSIX" command={COMMAND} />);
    await userEvent.click(screen.getByRole("button", { name: "複製 POSIX 指令" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("複製失敗，請手動選取上面的指令。");
    expect(screen.getByRole("button", { name: "複製 POSIX 指令" })).toHaveTextContent(/^複製$/);
    expect(screen.getByRole("status")).toHaveTextContent("複製失敗，請手動選取指令");
  });

  it("連按兩次：回復計時重新計算（不會被第一次的計時提早清掉）；卸載時清掉計時器（不留未清的 timeout）", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    stubClipboard(async () => undefined);
    const { unmount } = render(<CopyCommand shell="posix" label="POSIX" command={COMMAND} />);
    await userEvent.click(screen.getByRole("button", { name: "複製 POSIX 指令" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    await userEvent.click(screen.getByRole("button", { name: "已複製 POSIX 指令" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000); // 距第一次 3 秒、距第二次 1 秒：仍是「已複製」
    });
    expect(screen.getByRole("button", { name: "已複製 POSIX 指令" })).toBeInTheDocument();
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
});
