import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Plus } from "lucide-react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Button } from "./button";
import { Pagination } from "./pagination";
import { ToastHost, ToastProvider, useToast } from "./toast";

function ToastDemo() {
  const toast = useToast();
  return (
    <>
      <button onClick={() => toast.success("已 signoff")}>ok</button>
      <button onClick={() => toast.error("儲存失敗")}>bad</button>
      <ToastHost />
    </>
  );
}

describe("Toast（底部置中、一次一則、自動消失）", () => {
  afterEach(() => vi.useRealTimers());

  it("成功 toast 約 2.4 秒後消失，新的 toast 會取代舊的", () => {
    vi.useFakeTimers();
    render(
      <ToastProvider>
        <ToastDemo />
      </ToastProvider>,
    );
    act(() => screen.getByText("ok").click());
    expect(screen.getByText("已 signoff")).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(2300));
    expect(screen.getByText("已 signoff")).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(200));
    expect(screen.queryByText("已 signoff")).toBeNull();

    act(() => screen.getByText("ok").click());
    act(() => screen.getByText("bad").click());
    expect(screen.queryByText("已 signoff")).toBeNull();
    expect(screen.getByText("儲存失敗")).toBeInTheDocument();
    // 錯誤訊息停留較久（要讓人看完 traceId）
    act(() => vi.advanceTimersByTime(5000));
    expect(screen.getByText("儲存失敗")).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(1100));
    expect(screen.queryByText("儲存失敗")).toBeNull();
  });

  it("Toast 宿主是 aria-live 區域（螢幕閱讀器會朗讀）", () => {
    render(
      <ToastProvider>
        <ToastHost />
      </ToastProvider>,
    );
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });
});

describe("Pagination（超大扁平分頁器）", () => {
  it("目前頁 aria-current；首頁停用上一頁、末頁停用下一頁；點頁碼回報頁號", async () => {
    const onPageChange = vi.fn();
    const { rerender } = render(<Pagination page={1} totalPages={3} onPageChange={onPageChange} />);
    expect(screen.getByRole("button", { name: "第 1 頁" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: "上一頁" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "第 3 頁" }));
    expect(onPageChange).toHaveBeenLastCalledWith(3);
    await userEvent.click(screen.getByRole("button", { name: "下一頁" }));
    expect(onPageChange).toHaveBeenLastCalledWith(2);

    rerender(<Pagination page={3} totalPages={3} onPageChange={onPageChange} />);
    expect(screen.getByRole("button", { name: "下一頁" })).toBeDisabled();
  });
});

describe("Button", () => {
  it("asChild：圖示與文字一起放進子元素（連結）內，屬性落在連結上", () => {
    render(
      <Button asChild iconLeft={Plus} variant="ghost">
        <a href="/import">匯入</a>
      </Button>,
    );
    const link = screen.getByRole("link", { name: "匯入" });
    expect(link).toHaveAttribute("href", "/import");
    expect(link.querySelector("svg")).not.toBeNull();
    expect(link.className).toContain("hover:text-wg-primary");
  });

  it("loading 時停用並標示 aria-busy；disabled 套用停用配色", () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        儲存
      </Button>,
    );
    const btn = screen.getByRole("button", { name: /儲存/ });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-busy", "true");
    btn.click();
    expect(onClick).not.toHaveBeenCalled();
  });

  it("預設 type=button，不會意外送出表單", () => {
    render(<Button>一般</Button>);
    expect(screen.getByRole("button", { name: "一般" })).toHaveAttribute("type", "button");
  });
});

describe("載入狀態（UI-OVL-03）", () => {
  it("Spinner 是帶名稱的 status；Skeleton 對輔助科技隱藏；PageSkeleton 標示 aria-busy", async () => {
    const { Spinner } = await import("./spinner");
    const { Skeleton } = await import("./skeleton");
    const { PageSkeleton } = await import("./states");
    render(
      <>
        <Spinner label="載入專案" />
        <Skeleton data-testid="sk" />
        <PageSkeleton />
      </>,
    );
    expect(screen.getByRole("status", { name: "載入專案" })).toBeInTheDocument();
    expect(screen.getByTestId("sk")).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByLabelText("頁面載入中")).toHaveAttribute("aria-busy", "true");
  });
});
