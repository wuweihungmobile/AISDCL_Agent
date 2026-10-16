import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrictMode, useState, type ComponentProps, type ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { Dialog, DialogBody, DialogClose, DialogContent, DialogFooter, DialogTrigger } from "./dialog";

/**
 * DEF-AC-011（P3，WCAG 2.4.3 焦點順序）的共用層單元測試。
 * 根因：Radix 的 DialogContent 關閉時一律 preventDefault，再只把焦點還給它自己的 DialogTrigger；本專案的對話框全由頁面狀態
 * （open／target）控制、沒有 DialogTrigger，焦點就掉到 <body>。DialogContent 改為在開啟時記下 document.activeElement、關閉時歸還。
 */
type FocusHandlers = Pick<ComponentProps<typeof DialogContent>, "onOpenAutoFocus" | "onCloseAutoFocus">;

/** 與四個真實呼叫端同形：頁面持有 open 狀態、條件渲染 DialogContent、沒有 DialogTrigger。 */
function Page({ handlers, beside, keepMounted = false, autoFocusField = false }: { handlers?: FocusHandlers; beside?: ReactNode; keepMounted?: boolean; autoFocusField?: boolean }) {
  const [open, setOpen] = useState(false);
  const content = (
    <DialogContent title="範例對話框" description="共用層測試" {...handlers}>
      <DialogBody>
        <input aria-label="名稱" autoFocus={autoFocusField} />
      </DialogBody>
      <DialogFooter>
        <DialogClose asChild>
          <button type="button">取消</button>
        </DialogClose>
      </DialogFooter>
    </DialogContent>
  );
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        開啟
      </button>
      {beside}
      <Dialog open={open} onOpenChange={setOpen}>
        {keepMounted || open ? content : null}
      </Dialog>
    </>
  );
}

const opener = () => screen.getByRole("button", { name: "開啟" });
const dialogGone = () => waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
/** 鍵盤開啟：按鈕先取得焦點再按 Enter，並確認焦點已被搬進對話框。 */
async function openByKeyboard(user: ReturnType<typeof userEvent.setup>, trigger: HTMLElement = opener()) {
  trigger.focus();
  await user.keyboard("{Enter}");
  const dialog = await screen.findByRole("dialog", { name: "範例對話框" });
  await waitFor(() => expect(dialog).toContainElement(document.activeElement as HTMLElement));
  expect(trigger).not.toHaveFocus();
  return dialog;
}

describe("Dialog 共用層：關閉後把焦點還給開啟它的元素（程式控制開啟、沒有 DialogTrigger）", () => {
  it.each([
    ["Esc", async (user: ReturnType<typeof userEvent.setup>) => user.keyboard("{Escape}")],
    ["右上角關閉鈕", async (user: ReturnType<typeof userEvent.setup>) => user.click(screen.getByRole("button", { name: "關閉" }))],
    ["內容裡的 DialogClose（取消）", async (user: ReturnType<typeof userEvent.setup>) => user.click(screen.getByRole("button", { name: "取消" }))],
  ])("以鍵盤開啟、%s 關閉 → 焦點回到開啟的按鈕", async (_name, close) => {
    const user = userEvent.setup();
    render(<Page />);
    await openByKeyboard(user);
    await close(user);
    await dialogGone();
    await waitFor(() => expect(opener()).toHaveFocus());
  });

  it("以滑鼠點擊開啟（按鈕因點擊取得焦點）、Esc 關閉 → 焦點回到開啟的按鈕", async () => {
    const user = userEvent.setup();
    render(<Page />);
    await user.click(opener());
    await screen.findByRole("dialog", { name: "範例對話框" });
    await user.keyboard("{Escape}");
    await dialogGone();
    await waitFor(() => expect(opener()).toHaveFocus());
  });

  it("DialogContent 常駐、只切 open（由 Radix 的 Presence 掛卸）時同樣歸還", async () => {
    const user = userEvent.setup();
    render(<Page keepMounted />);
    await openByKeyboard(user);
    await user.keyboard("{Escape}");
    await dialogGone();
    await waitFor(() => expect(opener()).toHaveFocus());
  });

  it.each([
    ["條件渲染（{open ? <DialogContent /> : null}）", false],
    ["常駐（只切 open）", true],
  ])("內容裡有 autoFocus 欄位（焦點在 Radix 的 FocusScope 之前就進了內容，不會發 onOpenAutoFocus）、%s：仍歸還", async (_name, keepMounted) => {
    const user = userEvent.setup();
    const onOpenAutoFocus = vi.fn();
    render(<Page keepMounted={keepMounted} autoFocusField handlers={{ onOpenAutoFocus }} />);
    opener().focus();
    await user.keyboard("{Enter}");
    await screen.findByRole("dialog", { name: "範例對話框" });
    expect(screen.getByRole("textbox", { name: "名稱" })).toHaveFocus();
    expect(onOpenAutoFocus).not.toHaveBeenCalled(); // 證明這條路徑真的繞過了 onOpenAutoFocus
    await user.keyboard("{Escape}");
    await dialogGone();
    await waitFor(() => expect(opener()).toHaveFocus());
  });

  it("連續開關兩次、第二次從另一顆按鈕開：歸還給第二顆（每次開啟重新記錄，不沿用上一次）", async () => {
    const user = userEvent.setup();
    function Two() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>
            甲
          </button>
          <button type="button" onClick={() => setOpen(true)}>
            乙
          </button>
          <Dialog open={open} onOpenChange={setOpen}>
            {open ? <DialogContent title="範例對話框" description="d" /> : null}
          </Dialog>
        </>
      );
    }
    render(<Two />);
    const a = screen.getByRole("button", { name: "甲" });
    const b = screen.getByRole("button", { name: "乙" });
    await openByKeyboard(user, a);
    await user.keyboard("{Escape}");
    await dialogGone();
    await waitFor(() => expect(a).toHaveFocus());
    await openByKeyboard(user, b);
    await user.keyboard("{Escape}");
    await dialogGone();
    await waitFor(() => expect(b).toHaveFocus());
  });

  it("StrictMode（開發模式的 effect 重跑）：對話框開著時焦點不被搶走、onCloseAutoFocus 不會提早觸發；關閉後仍歸還", async () => {
    const user = userEvent.setup();
    const onCloseAutoFocus = vi.fn();
    render(
      <StrictMode>
        <Page handlers={{ onCloseAutoFocus }} />
      </StrictMode>,
    );
    const dialog = await openByKeyboard(user);
    await new Promise((resolve) => setTimeout(resolve, 50)); // Radix 的卸載焦點事件排在 setTimeout(0)：等它有機會（錯誤地）在對話框開著時觸發
    expect(onCloseAutoFocus).not.toHaveBeenCalled();
    expect(dialog).toContainElement(document.activeElement as HTMLElement);
    await user.keyboard("{Escape}");
    await dialogGone();
    await waitFor(() => expect(opener()).toHaveFocus());
    expect(onCloseAutoFocus).toHaveBeenCalledTimes(1);
  });
});

describe("Dialog 共用層：觸發鈕已不能聚焦或根本沒有焦點時（不拋錯、不亂聚焦）", () => {
  /** 呼叫端的 onCloseAutoFocus 與共用層的歸還在同一次同步派發裡：spy 被呼叫時，歸還與否的決定已經做完，不必靠固定睡眠。 */
  const closeHandled = (spy: ReturnType<typeof vi.fn>) => waitFor(() => expect(spy).toHaveBeenCalledTimes(1));

  it("對話框開著時觸發鈕被拆下（頁面重繪換了節點）：關閉不拋錯，焦點不落在已拆下的節點、而是留在 <body>", async () => {
    const user = userEvent.setup();
    const onCloseAutoFocus = vi.fn();
    const errors: unknown[] = [];
    const onError = (e: ErrorEvent) => errors.push(e.error);
    window.addEventListener("error", onError);
    function Removable() {
      const [open, setOpen] = useState(false);
      const [shown, setShown] = useState(true);
      return (
        <>
          {shown ? (
            <button type="button" onClick={() => setOpen(true)}>
              開啟
            </button>
          ) : null}
          <Dialog open={open} onOpenChange={setOpen}>
            {open ? (
              <DialogContent title="範例對話框" description="d" onCloseAutoFocus={onCloseAutoFocus}>
                <DialogBody>
                  <button type="button" onClick={() => setShown(false)}>
                    對話框內移除觸發鈕
                  </button>
                </DialogBody>
              </DialogContent>
            ) : null}
          </Dialog>
        </>
      );
    }
    render(<Removable />);
    const trigger = opener();
    const focusSpy = vi.spyOn(trigger, "focus");
    try {
      await openByKeyboard(user, trigger);
      await user.click(screen.getByRole("button", { name: "對話框內移除觸發鈕" }));
      expect(trigger.isConnected).toBe(false);
      await user.keyboard("{Escape}");
      await dialogGone();
      await closeHandled(onCloseAutoFocus);
      expect(focusSpy.mock.calls.length, "已拆下的節點不該被呼叫 focus()").toBe(1); // 只有測試自己開啟前的那一次 trigger.focus()
      expect(document.activeElement).toBe(document.body);
      expect(document.activeElement).not.toBe(trigger);
      expect(errors).toEqual([]);
    } finally {
      window.removeEventListener("error", onError);
    }
  });

  it("對話框開著時觸發鈕被停用：不去聚焦停用的按鈕（焦點留在 <body>）", async () => {
    const user = userEvent.setup();
    const onCloseAutoFocus = vi.fn();
    function Disable() {
      const [open, setOpen] = useState(false);
      const [disabled, setDisabled] = useState(false);
      return (
        <>
          <button type="button" disabled={disabled} onClick={() => setOpen(true)}>
            開啟
          </button>
          <Dialog open={open} onOpenChange={setOpen}>
            {open ? (
              <DialogContent title="範例對話框" description="d" onCloseAutoFocus={onCloseAutoFocus}>
                <DialogBody>
                  <button type="button" onClick={() => setDisabled(true)}>
                    停用觸發鈕
                  </button>
                </DialogBody>
              </DialogContent>
            ) : null}
          </Dialog>
        </>
      );
    }
    render(<Disable />);
    const focusSpy = vi.spyOn(opener(), "focus");
    await openByKeyboard(user);
    await user.click(screen.getByRole("button", { name: "停用觸發鈕" }));
    await user.keyboard("{Escape}");
    await dialogGone();
    await closeHandled(onCloseAutoFocus);
    expect(opener()).toBeDisabled();
    expect(focusSpy.mock.calls.length, "停用的按鈕不該被呼叫 focus()").toBe(1); // 只有測試自己開啟前的那一次 trigger.focus()
    expect(document.activeElement).toBe(document.body);
  });

  it("開啟當下沒有任何元素持有焦點（<body>：Safari 與 macOS 版 Firefox 點擊按鈕不會讓它取得焦點）：關閉不拋錯、不亂聚焦", async () => {
    const user = userEvent.setup();
    const onCloseAutoFocus = vi.fn();
    render(<Page handlers={{ onCloseAutoFocus }} />);
    expect(document.activeElement).toBe(document.body);
    fireEvent.click(opener()); // 只送 click、不經過 mousedown，按鈕不會取得焦點
    const dialog = await screen.findByRole("dialog", { name: "範例對話框" });
    await waitFor(() => expect(dialog).toContainElement(document.activeElement as HTMLElement));
    await user.keyboard("{Escape}");
    await dialogGone();
    await closeHandled(onCloseAutoFocus);
    expect(document.activeElement).toBe(document.body);
  });
});

describe("Dialog 共用層：尊重呼叫端自己傳的 onOpenAutoFocus／onCloseAutoFocus", () => {
  it("onCloseAutoFocus 先被呼叫（此時焦點還沒歸還）；沒有 preventDefault 時共用層接著歸還", async () => {
    const user = userEvent.setup();
    const seen: boolean[] = [];
    const onCloseAutoFocus = vi.fn(() => seen.push(document.activeElement === opener()));
    render(<Page handlers={{ onCloseAutoFocus }} />);
    await openByKeyboard(user);
    await user.keyboard("{Escape}");
    await dialogGone();
    await waitFor(() => expect(opener()).toHaveFocus());
    expect(onCloseAutoFocus).toHaveBeenCalledTimes(1);
    expect(seen).toEqual([false]);
  });

  it("onCloseAutoFocus 呼叫 preventDefault()：共用層放手，焦點由呼叫端決定", async () => {
    const user = userEvent.setup();
    const onCloseAutoFocus = vi.fn((event: Event) => {
      event.preventDefault();
      screen.getByRole("button", { name: "別處" }).focus();
    });
    render(<Page handlers={{ onCloseAutoFocus }} beside={<button type="button">別處</button>} />);
    await openByKeyboard(user);
    await user.keyboard("{Escape}");
    await dialogGone();
    await waitFor(() => expect(onCloseAutoFocus).toHaveBeenCalledTimes(1)); // 呼叫端的處理與共用層的歸還在同一次同步派發裡，這之後不會再有人動焦點
    expect(screen.getByRole("button", { name: "別處" })).toHaveFocus();
    expect(opener()).not.toHaveFocus();
  });

  it("onOpenAutoFocus 被呼叫；它自己把焦點移到對話框內的欄位（preventDefault）時，仍記得開啟前的按鈕、關閉後歸還", async () => {
    const user = userEvent.setup();
    const onOpenAutoFocus = vi.fn((event: Event) => {
      event.preventDefault();
      screen.getByRole("textbox", { name: "名稱" }).focus();
    });
    render(<Page handlers={{ onOpenAutoFocus }} />);
    opener().focus();
    await user.keyboard("{Enter}");
    await screen.findByRole("dialog", { name: "範例對話框" });
    expect(onOpenAutoFocus).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.getByRole("textbox", { name: "名稱" })).toHaveFocus());
    await user.keyboard("{Escape}");
    await dialogGone();
    await waitFor(() => expect(opener()).toHaveFocus());
  });
});

describe("Dialog 共用層：Radix 原生的 DialogTrigger 路徑照舊", () => {
  it("用 DialogTrigger 開啟（uncontrolled）：Esc 關閉後焦點回到 Trigger", async () => {
    const user = userEvent.setup();
    render(
      <Dialog>
        <DialogTrigger asChild>
          <button type="button">原生觸發鈕</button>
        </DialogTrigger>
        <DialogContent title="範例對話框" description="d" />
      </Dialog>,
    );
    const trigger = screen.getByRole("button", { name: "原生觸發鈕" });
    trigger.focus();
    await user.keyboard("{Enter}");
    await screen.findByRole("dialog", { name: "範例對話框" });
    await user.keyboard("{Escape}");
    await dialogGone();
    await waitFor(() => expect(trigger).toHaveFocus());
  });
});
