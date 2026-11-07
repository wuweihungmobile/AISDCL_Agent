import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { EventSourceCtor } from "@/lib/api/sse";
import { ROUTE_FAILED, ROUTE_RUNNING } from "@/tests/fixtures/research/route";
import { FakeEventSource } from "@/tests/helpers/fakeEventSource";
import { signIn } from "@/tests/helpers/research";
import { RouteStepsTimeline, stepDuration } from "./RouteStepsTimeline";

/** 分流逐步進度（AT-961-17-7 的元件載具）：REST 初始化、SSE 逐步更新並觸發重抓、斷線不重複連線、耗時與失敗原因。 */
const FRAME = FakeEventSource as unknown as EventSourceCtor;

function mount(ui: React.ReactElement, client = new QueryClient()) {
  signIn("ADMIN", "admin");
  return { client, ...render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>) };
}

beforeEach(() => FakeEventSource.reset());

describe("RouteStepsTimeline", () => {
  it("尚無步驟列時顯示等待說明；有列時逐步渲染步驟名、狀態文字與耗時", () => {
    const { unmount } = mount(<RouteStepsTimeline researchId="r1" route={null} streaming={false} />);
    expect(screen.getByTestId("route-steps-empty")).toHaveTextContent("等待第一個步驟回報");
    unmount();
    mount(<RouteStepsTimeline researchId="r1" route={ROUTE_RUNNING} streaming={false} />);
    expect(screen.getByTestId("route-step-1")).toHaveTextContent("驗證目標");
    expect(screen.getByTestId("route-step-1")).toHaveTextContent("完成");
    expect(screen.getByTestId("route-step-2")).toHaveTextContent("執行中");
    expect(screen.getByTestId("route-step-1")).toHaveTextContent("耗時 1800.0 秒");
    expect(screen.getByTestId("route-step-2")).toHaveTextContent("耗時 —");
  });

  it("失敗步驟顯示失敗原因（純文字）；streaming 為假時不連串流", () => {
    mount(<RouteStepsTimeline researchId="r1" route={ROUTE_FAILED} streaming={false} EventSourceCtor={FRAME} />);
    expect(screen.getByTestId("route-step-reason")).toHaveTextContent("失敗原因：fatal: 分支已存在（路徑已脫敏）");
    expect(FakeEventSource.instances).toHaveLength(0);
  });

  it("訂 research.route：事件覆蓋該步狀態並使分流查詢過期；格式損毀的事件略過；卸載時關閉連線", async () => {
    const { client, unmount } = mount(<RouteStepsTimeline researchId="r1" route={ROUTE_RUNNING} EventSourceCtor={FRAME} />);
    const spy = vi.spyOn(client, "invalidateQueries");
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
    expect(FakeEventSource.last.names).toContain("research.route");
    act(() => FakeEventSource.last.emit("research.route", "不是 JSON"));
    expect(screen.getByTestId("route-step-2")).toHaveAttribute("data-status", "RUNNING");
    act(() => FakeEventSource.last.emit("research.route", { stepNo: 2, step: "GIT_SWITCH", status: "FAILED" }));
    await waitFor(() => expect(screen.getByTestId("route-step-2")).toHaveAttribute("data-status", "FAILED"));
    expect(spy).toHaveBeenCalledWith({ queryKey: ["research", "project", "r1", "route"] });
    const es = FakeEventSource.last;
    unmount();
    expect(es.closed).toBe(true);
  });

  it("stepDuration：有起訖回秒數（一位小數）；沒有結束時間或時間錯亂回「—」", () => {
    expect(stepDuration({ startedAt: "2026-11-02T10:00:00+08:00", finishedAt: "2026-11-02T10:00:01.500+08:00" })).toBe("1.5 秒");
    expect(stepDuration({ startedAt: "2026-11-02T10:00:00+08:00", finishedAt: null })).toBe("—");
    expect(stepDuration({ startedAt: "2026-11-02T10:00:05+08:00", finishedAt: "2026-11-02T10:00:00+08:00" })).toBe("—");
    expect(stepDuration({ startedAt: "壞", finishedAt: "壞" })).toBe("—");
  });
});
