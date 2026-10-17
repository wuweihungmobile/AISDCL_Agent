import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { invalidateRuns } from "@/lib/api/queries";
import type { RunStatus } from "@/lib/api/types";
import { Providers, failure, makeClient, signIn, stubApi, type ApiCall, type Reply } from "@/tests/helpers/api";
import { rtmReport } from "@/tests/helpers/sddFixtures";
import { RtmPanel } from "./RtmPanel";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/projects/p1/execute",
  useSearchParams: () => new URLSearchParams(),
}));

/**
 * 執行詳情「追溯覆蓋（諮詢）」面板（契約 §1.10.3、§4.7.2；UI-SDD-02；整合輪 115 G-05）。
 * 假後端只回 GET /executions/{runId}/rtm；其他請求一律記下來（面板不該打任何別的端點）。
 */
const RTM = "/api/v1/executions/r1/rtm";

function backend(reply: (c: ApiCall) => Reply) {
  return stubApi((c) => (c.method === "GET" && c.path === RTM ? reply(c) : undefined));
}

const rtmCalls = (calls: ApiCall[]) => calls.filter((c) => c.path === RTM);

function view(props: { runId?: string | null; runStatus?: RunStatus; bound?: boolean } = {}) {
  const merged = { runId: "r1", runStatus: "COMPLETED" as RunStatus | undefined, bound: true, ...props };
  const client = makeClient();
  const ui = (p: typeof merged): ReactNode => (
    <Providers client={client}>
      <RtmPanel runId={p.runId} runStatus={p.runStatus} bound={p.bound} />
    </Providers>
  );
  const result = render(ui(merged));
  return { ...result, client, update: (next: Partial<typeof merged>) => result.rerender(ui({ ...merged, ...next })) };
}

beforeEach(() => signIn("VIEWER", "viewer"));

describe("追溯覆蓋面板：何時出現、何時呼叫端點", () => {
  it("專案沒有 SDD 規格綁定（bound=false）：整個面板不顯示、也不呼叫端點（即使批次已終態）", async () => {
    const { calls } = backend(() => ({ data: rtmReport() }));
    view({ bound: false });
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(screen.queryByTestId("rtm-panel")).toBeNull();
    expect(rtmCalls(calls)).toHaveLength(0);
  });

  it("沒有批次（runId 缺）：不顯示、不呼叫", async () => {
    const { calls } = backend(() => ({ data: rtmReport() }));
    view({ runId: null });
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(screen.queryByTestId("rtm-panel")).toBeNull();
    expect(calls).toHaveLength(0);
  });

  it.each(["INITIALIZING", "RUNNING", "PAUSED"] as const)("批次非終態（%s）：只顯示一行「批次結束後才會有追溯覆蓋報告」，不呼叫端點、沒有徽章", async (status) => {
    const { calls } = backend(() => ({ data: rtmReport() }));
    view({ runStatus: status });
    expect(await screen.findByTestId("rtm-pending")).toHaveTextContent("批次結束後才會有追溯覆蓋報告");
    expect(screen.getByRole("heading", { name: "追溯覆蓋" })).toBeInTheDocument();
    expect(screen.queryByTestId("rtm-advisory-badge")).toBeNull();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(rtmCalls(calls)).toHaveLength(0);
  });

  it("批次狀態還沒載入（undefined）：顯示載入骨架，不誤報「批次結束後才會有…」，也不呼叫", async () => {
    const { calls } = backend(() => ({ data: rtmReport() }));
    view({ runStatus: undefined });
    expect(screen.getByTestId("rtm-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("rtm-pending")).toBeNull();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(rtmCalls(calls)).toHaveLength(0);
  });

  it.each(["COMPLETED", "FAILED", "CANCELLED"] as const)("批次進入終態（%s）：取一次，不輪詢", async (status) => {
    const { calls } = backend(() => ({ data: rtmReport() }));
    view({ runStatus: status });
    expect(await screen.findByTestId("rtm-at")).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 80));
    expect(rtmCalls(calls)).toHaveLength(1);
  });

  it("批次相關的失效（SSE 終態回放、控制動作都會 invalidateRuns）不會讓已取得的報告再被請求一次——報告只在進入終態時取", async () => {
    const { calls } = backend(() => ({ data: rtmReport() }));
    const { client } = view({ runStatus: "COMPLETED" });
    await screen.findByTestId("rtm-at");
    expect(rtmCalls(calls)).toHaveLength(1);
    await invalidateRuns(client);
    await client.invalidateQueries({ queryKey: ["executions"] });
    await new Promise((resolve) => setTimeout(resolve, 80));
    expect(rtmCalls(calls)).toHaveLength(1);
    expect(screen.getByTestId("rtm-at")).toBeInTheDocument(); // 失效期間也沒有回到骨架或錯誤
  });

  it("批次由進行中轉終態：這時才發出請求；之後再度離開終態（例如還原重跑）又回到終態會重抓一次", async () => {
    const { calls } = backend(() => ({ data: rtmReport() }));
    const { update } = view({ runStatus: "RUNNING" });
    await screen.findByTestId("rtm-pending");
    expect(rtmCalls(calls)).toHaveLength(0);
    update({ runStatus: "COMPLETED" });
    await screen.findByTestId("rtm-at");
    expect(rtmCalls(calls)).toHaveLength(1);
    update({ runStatus: "RUNNING" });
    await screen.findByTestId("rtm-pending");
    update({ runStatus: "COMPLETED" });
    await waitFor(() => expect(rtmCalls(calls)).toHaveLength(2));
  });
});

describe("追溯覆蓋面板：有資料（契約 §4.7.2 的顯示規則）", () => {
  it("標題＋徽章「諮詢視圖」＋固定說明；契約範例逐列：「4／4（100.0%）」「2／2（100.0%）」「AC 已達 100% 覆蓋」", async () => {
    backend(() => ({ data: rtmReport() }));
    view();
    await screen.findByTestId("rtm-at"); // 面板先以骨架出現，報告回來後才有徽章與各列
    const panel = screen.getByTestId("rtm-panel");
    expect(within(panel).getByRole("heading", { name: "追溯覆蓋" })).toBeInTheDocument();
    expect(within(panel).getByTestId("rtm-advisory-badge")).toHaveTextContent("諮詢視圖");
    expect(within(panel).getByTestId("rtm-advisory-note")).toHaveTextContent("AT 通過只代表評估指令與驗收 regex 皆通過，不等於規格被滿足；SCG-4 的人工審查才是真閘。");
    expect(screen.getByTestId("rtm-at")).toHaveTextContent("4／4（100.0%）");
    expect(screen.getByTestId("rtm-ac")).toHaveTextContent("2／2（100.0%）");
    expect(screen.getByTestId("rtm-scg5")).toHaveTextContent("AC 已達 100% 覆蓋");
    expect(screen.getByTestId("rtm-scenario")).toHaveTextContent("greenfield");
    expect(screen.getByTestId("rtm-failed")).toHaveTextContent("無");
    expect(screen.getByTestId("rtm-weak")).toHaveTextContent("無");
    expect(screen.getByTestId("rtm-unmapped")).toHaveTextContent("無");
    expect(screen.queryByTestId("rtm-at-note")).toBeNull();
    expect(screen.queryByTestId("rtm-weak-note")).toBeNull();
    expect(screen.queryByTestId("rtm-unmapped-note")).toBeNull();
  });

  it("規格摘要：前 19 碼加「…」，全值在 tooltip；規格摘要與場景空字串「—」", async () => {
    backend(() => ({ data: rtmReport() }));
    view();
    const digest = await screen.findByTestId("rtm-digest");
    expect(digest).toHaveTextContent("sha256:1f0e2b7a9c4d…");
    expect(digest).toHaveAttribute("title", "sha256:1f0e2b7a9c4d8e3f6a1b5c7d9e0f2a4b6c8d0e1f3a5b7c9d1e3f5a7b9c0d2e4f");
  });

  it("空字串的摘要與場景顯示單一的「—」（不顯示 undefined、null）", async () => {
    backend(() => ({ data: rtmReport({ specDigest: "", scenario: "" }) }));
    view();
    await screen.findByTestId("rtm-at");
    expect(screen.getByTestId("rtm-digest")).toHaveTextContent(/^—$/);
    expect(screen.getByTestId("rtm-digest")).not.toHaveAttribute("title");
    expect(screen.getByTestId("rtm-scenario")).toHaveTextContent(/^—$/);
    const all = screen.getByTestId("rtm-panel").textContent ?? "";
    for (const bad of ["undefined", "null", "NaN"]) expect(all).not.toContain(bad);
  });

  it("有失敗的 AT、偏弱 regex、無法歸屬 AC 的 AT：逗號分隔列出，並附契約的說明句；AT 列加註「其中 n 個無法歸屬到 AC」；SCG-5 不視為全覆蓋", async () => {
    backend(() => ({
      data: rtmReport({
        at: { passed: 4, total: 5, unmapped: 1, pct: 80 },
        ac: { covered: 2, total: 2, pct: 100 },
        failedAtIds: ["AT-002-1"],
        weakRegexAtIds: ["AT-001-1", "AT-001-2"],
        unmappedAtIds: ["AT-9-X"],
        fullyCovered: false,
      }),
    }));
    view({ runStatus: "FAILED" });
    await screen.findByTestId("rtm-at");
    expect(screen.getByTestId("rtm-at")).toHaveTextContent("4／5（80.0%）");
    expect(screen.getByTestId("rtm-at-note")).toHaveTextContent("其中 1 個無法歸屬到 AC");
    expect(screen.getByTestId("rtm-scg5")).toHaveTextContent("AC 已達 100%，但有無法歸屬的 AT，不視為全覆蓋");
    expect(screen.getByTestId("rtm-failed")).toHaveTextContent("AT-002-1");
    expect(screen.getByTestId("rtm-weak")).toHaveTextContent("AT-001-1, AT-001-2");
    expect(screen.getByTestId("rtm-weak-note")).toHaveTextContent("規格的 Then 沒有可推導的引號字面值，驗收可能偏鬆");
    expect(screen.getByTestId("rtm-unmapped")).toHaveTextContent("AT-9-X");
    expect(screen.getByTestId("rtm-unmapped-note")).toHaveTextContent("這些 AT 的編號不符 AT-NNN-Y-… 文法或 AC 對不上，已計入 AT 總數但不計入任何 AC");
  });

  it("缺席的欄位（舊報告缺 at／ac）顯示「—」、不崩潰", async () => {
    backend(() => ({ data: { scenario: "g", specDigest: "", failedAtIds: [], weakRegexAtIds: [], unmappedAtIds: [], advisory: true } }));
    view();
    await screen.findByTestId("rtm-scg5");
    expect(screen.getByTestId("rtm-at")).toHaveTextContent(/^—$/);
    expect(screen.getByTestId("rtm-ac")).toHaveTextContent(/^—$/);
    expect(screen.getByTestId("rtm-scg5")).toHaveTextContent(/^—$/);
  });
});

describe("追溯覆蓋面板：404 與錯誤（契約 §1.10.3、§4.7.2）", () => {
  it("404 rtm_not_found：中性文字「此批次沒有追溯覆蓋報告」＋常見原因，不是錯誤樣式（沒有 alert、沒有重試、沒有徽章）", async () => {
    backend(() => failure(404, { message: "此批次沒有追溯報告", reason: "rtm_not_found", details: { runId: "r1" } }));
    view();
    const empty = await screen.findByTestId("rtm-empty");
    expect(empty).toHaveTextContent("此批次沒有追溯覆蓋報告");
    expect(empty).toHaveTextContent("批次不是正常走完");
    expect(empty).toHaveAttribute("role", "status");
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByRole("button", { name: "重試" })).toBeNull();
    expect(screen.queryByTestId("rtm-advisory-badge")).toBeNull();
  });

  it("404 但沒有 reason（批次不存在）：是一般錯誤區塊，不是中性文字（兩種 404 必須能區分）", async () => {
    backend(() => failure(404, { message: "執行批次不存在或已刪除：r1" }));
    view();
    expect(await screen.findByRole("alert")).toHaveTextContent("執行批次不存在或已刪除：r1");
    expect(screen.queryByTestId("rtm-empty")).toBeNull();
  });

  it.each([
    [422, "引擎拒絕此請求", { bridgeReason: "rtm_unreadable", violations: [] }],
    [502, "引擎橋接服務無法連線", undefined],
    [504, "引擎橋接服務逾時", undefined],
  ] as const)("%s：一般錯誤區塊（reason 與 traceId）加「重試」；重試成功後顯示報告", async (status, reason, details) => {
    let broken = true;
    const { calls } = backend(() => (broken ? failure(status, { message: "失敗了", reason, details: details as Record<string, unknown> | undefined }) : { data: rtmReport() }));
    view();
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("無法載入追溯覆蓋");
    expect(alert).toHaveTextContent(reason);
    expect(alert).toHaveTextContent(`traceId：tr-${status}`);
    expect(screen.queryByTestId("rtm-empty")).toBeNull();
    broken = false;
    await userEvent.click(screen.getByRole("button", { name: "重試" }));
    expect(await screen.findByTestId("rtm-at")).toHaveTextContent("4／4（100.0%）");
    expect(rtmCalls(calls)).toHaveLength(2);
  });
});
