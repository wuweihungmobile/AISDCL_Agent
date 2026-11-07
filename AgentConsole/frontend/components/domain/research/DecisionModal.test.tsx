/**
 * 決策彈窗 (b)～(d)（TCS-ResearchToPRD-P2-20261107 AT-962-14-1～14-7、14-E-1～14-E-4）：單一彈窗殼、allowedDecisions 驅動按鈕、走既有審核端點不寫 gates、
 * 稍後處理只關窗並記 sessionStorage、去重、他人已決定、無逾時自動處理。
 */
import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DECISION_SNOOZE_STORAGE_KEY, decisionKey } from "@/lib/domain/research";
import { R3 } from "@/tests/fixtures/research/ids";
import { KANBAN, PENDING_AGENT, PENDING_ESCALATED, REVIEW_ESCALATED, RUN_ID, kanbanPending } from "@/tests/fixtures/research/p2";
import { FakeEventSource } from "@/tests/helpers/fakeEventSource";
import { failure, renderResearch, stubResearchApi, type ApiCall } from "@/tests/helpers/research";
import { DecisionCenter } from "./DecisionModal";
import { KanbanBoard } from "./KanbanBoard";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  useParams: () => ({}),
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(""),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const REVIEW_URL = (reviewId: string) => `/api/v1/executions/${RUN_ID}/review/${reviewId}`;
const reviewPosts = (calls: ApiCall[]) => calls.filter((c) => c.method === "POST" && /\/review\//.test(c.path));
const kanbanGets = (calls: ApiCall[]) => calls.filter((c) => c.method === "GET" && c.path === `/api/v1/research/projects/${R3}/kanban`).length;
const modals = () => screen.queryAllByTestId("decision-modal");

beforeEach(() => {
  FakeEventSource.reset();
  vi.stubGlobal("EventSource", FakeEventSource);
  window.sessionStorage.clear();
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function center(role: "ADMIN" | "OPERATOR" | "VIEWER", pending = [PENDING_ESCALATED], overrides?: (call: ApiCall) => ReturnType<NonNullable<Parameters<typeof stubResearchApi>[0]>["overrides"] & {}>) {
  const stub = stubResearchApi({ overrides });
  const view = renderResearch(<DecisionCenter researchId={R3} pendingReviews={pending} />, role);
  return { ...stub, ...view };
}

async function board(kanban = KANBAN, overrides?: Parameters<typeof stubResearchApi>[0] extends infer P ? (P extends { overrides?: infer O } ? O : never) : never) {
  const stub = stubResearchApi({ kanban, overrides });
  const view = renderResearch(<KanbanBoard researchId={R3} />, "OPERATOR");
  await screen.findByTestId("kanban-board");
  return { ...stub, ...view };
}
const runLogs = async () => {
  await waitFor(() => expect(FakeEventSource.lastOf("logs")).toBeDefined());
  return FakeEventSource.lastOf("logs")!;
};
const reviewFrame = (review: typeof PENDING_AGENT, id = review.reviewId) => ({
  seq: 5,
  sub: 1,
  ts: "t",
  review: { id, runId: review.runId, kind: review.kind, status: "PENDING", reason: review.reason, requestedAt: "t", allowedDecisions: review.allowedDecisions, taskId: review.taskId ?? undefined },
});

describe("彈窗類型", () => {
  it("AT_962_14_1 類型 (b) 自癒耗盡：ESCALATED 待審開彈窗，顯示原因與四顆按鈕（通過、拒絕、重試、跳過），按鈕集合恰等於 allowedDecisions", () => {
    center("OPERATOR");
    const modal = screen.getByTestId("decision-modal");
    expect(within(modal).getByTestId("decision-reason").textContent).toBe(PENDING_ESCALATED.reason);
    const group = within(modal).getByTestId("decision-buttons");
    expect([...group.querySelectorAll("button")].map((b) => b.textContent)).toEqual(["通過", "拒絕", "重試", "跳過"]);
    expect([...group.querySelectorAll("button")].map((b) => b.getAttribute("data-testid"))).toEqual(PENDING_ESCALATED.allowedDecisions.map((d) => `decision-${d}`));
  });

  it("AT_962_14_2 類型 (c) Agent 請求審核：待審 kind 非 ESCALATED 與 review-request 幀同殼處理，按鈕依 allowedDecisions，不另開第二種元件", async () => {
    await board(kanbanPending(PENDING_AGENT));
    const modal = await screen.findByTestId("decision-modal");
    expect(within(modal).getByTestId("decision-kind").getAttribute("data-kind")).toBe("AGENT_REQUEST");
    expect([...within(modal).getByTestId("decision-buttons").querySelectorAll("button")].map((b) => b.textContent)).toEqual(["通過", "拒絕"]);
    fireEvent.click(within(modal).getByTestId("decision-snooze"));
    await waitFor(() => expect(modals()).toHaveLength(0));
    // SSE review-request 幀（另一個 reviewId）進同一個殼
    const logs = await runLogs();
    const other = { ...PENDING_AGENT, reviewId: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", reason: "幀送來的審核請求" };
    act(() => logs.emit("review-request", reviewFrame(other), "5.1"));
    const framed = await screen.findByTestId("decision-modal");
    expect(within(framed).getByTestId("decision-reason").textContent).toBe("幀送來的審核請求");
    expect(modals()).toHaveLength(1);
  });

  it("AT_962_14_3 類型 (d)：alert（ESCALATION）幀與 review-request 皆開彈窗；去重鍵 reviewId、無則用 alert 幀 seq；Console 沒有判斷事情大小的程式", async () => {
    expect(decisionKey({ reviewId: "r1", alertSeq: 9 })).toBe("review:r1");
    expect(decisionKey({ alertSeq: 9 })).toBe("alert:9");
    expect(decisionKey({})).toBeNull();
    await board();
    const logs = await runLogs();
    act(() => logs.emit("alert", { seq: 77, origin: "ENGINE", ts: "t", code: "ESCALATION", message: "引擎要求人工決定架構方向" }, "77"));
    const modal = await screen.findByTestId("decision-modal");
    expect(within(modal).getByTestId("decision-kind").getAttribute("data-kind")).toBe("ALERT");
    expect(within(modal).getByTestId("decision-reason").textContent).toBe("引擎要求人工決定架構方向");
    expect(within(modal).getByTestId("decision-info-only")).toBeDefined();
    expect(screen.getByTestId("pending-review").getAttribute("data-key")).toBe("alert:77");
    // 非 ESCALATION 的 alert 不開窗；重播同一幀不重開第二窗
    act(() => logs.emit("alert", { seq: 78, origin: "ENGINE", ts: "t", code: "TOKEN_HALT", message: "額度" }, "78"));
    act(() => logs.emit("alert", { seq: 77, origin: "ENGINE", ts: "t", code: "ESCALATION", message: "引擎要求人工決定架構方向" }, "77"));
    expect(screen.getAllByTestId("pending-review")).toHaveLength(1);
    expect(modals()).toHaveLength(1);
    // 靜態：兩個檔案沒有任何「事情大不大」的判斷詞彙
    const dir = path.resolve(process.cwd(), "components", "domain", "research");
    for (const name of ["DecisionModal.tsx", "PendingReviewList.tsx", "KanbanBoard.tsx"]) {
      const code = readFileSync(path.join(dir, name), "utf8")
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .replace(/(^|[^:\\"'`])\/\/.*$/gm, "$1");
      expect(code, name).not.toMatch(/重大|significan|critical|major|severity|importan/i);
    }
  });
});

describe("決定與稍後處理", () => {
  it("AT_962_14_4 選 RETRY 並填理由、按確認：POST 既有審核端點，body 為 {decision, comment}；關窗並使 kanban 重抓；不呼叫 /gates", async () => {
    const { calls } = await board(kanbanPending(PENDING_ESCALATED));
    const modal = await screen.findByTestId("decision-modal");
    const base = kanbanGets(calls);
    fireEvent.click(within(modal).getByTestId("decision-RETRY"));
    fireEvent.change(within(modal).getByRole("textbox"), { target: { value: "環境已修好" } });
    fireEvent.click(within(modal).getByTestId("decision-confirm"));
    await waitFor(() => expect(modals()).toHaveLength(0));
    const posts = reviewPosts(calls);
    expect(posts).toHaveLength(1);
    expect(posts[0].path).toBe(REVIEW_URL(REVIEW_ESCALATED));
    expect(posts[0].body).toEqual({ decision: "RETRY", comment: "環境已修好" });
    await waitFor(() => expect(kanbanGets(calls)).toBeGreaterThan(base));
    expect(calls.some((c) => c.path.endsWith("/gates"))).toBe(false);
  });

  it("AT_962_14_5 稍後處理：只關窗並以 sessionStorage 記 key；待辦仍在列表；重載後不再自動彈出、列表仍有；不呼叫決定端點與 /signoffs/pending", () => {
    const { calls, unmount } = center("OPERATOR");
    fireEvent.click(within(screen.getByTestId("decision-modal")).getByTestId("decision-snooze"));
    expect(modals()).toHaveLength(0);
    expect(JSON.parse(window.sessionStorage.getItem(DECISION_SNOOZE_STORAGE_KEY) ?? "[]")).toEqual([`review:${REVIEW_ESCALATED}`]);
    expect(screen.getAllByTestId("pending-review")).toHaveLength(1);
    unmount();
    renderResearch(<DecisionCenter researchId={R3} pendingReviews={[PENDING_ESCALATED]} />, "OPERATOR");
    expect(modals()).toHaveLength(0); // 本分頁不再自動彈出同 key
    expect(screen.getAllByTestId("pending-review")).toHaveLength(1); // 步驟 4 待辦列仍有
    expect(calls.filter((c) => c.method !== "GET")).toHaveLength(0);
    expect(calls.some((c) => c.path.includes("signoffs"))).toBe(false);
    // 從列表按「處理」可再次開窗
    fireEvent.click(screen.getByRole("button", { name: "處理" }));
    expect(modals()).toHaveLength(1);
  });

  it("AT_962_14_6 去重：同 reviewId 的 review-request 幀連送三次只有一個彈窗；重載後由 pendingReviews 重建仍只有一個", async () => {
    const first = await board(kanbanPending(PENDING_AGENT));
    await screen.findByTestId("decision-modal");
    const logs = await runLogs();
    for (let i = 0; i < 3; i += 1) act(() => logs.emit("review-request", reviewFrame(PENDING_AGENT), "5.1"));
    expect(modals()).toHaveLength(1);
    expect(screen.getAllByTestId("pending-review")).toHaveLength(1);
    first.unmount();
    FakeEventSource.reset();
    await board(kanbanPending(PENDING_AGENT));
    await screen.findByTestId("decision-modal");
    expect(modals()).toHaveLength(1);
    expect(screen.getAllByTestId("pending-review")).toHaveLength(1);
  });

  it("AT_962_14_E_3 他人已決定：決定端點回 409 時顯示錯誤並重抓待審清單；按確認兩次 POST 只有一次", async () => {
    const { calls } = await board(kanbanPending(PENDING_ESCALATED), (call) =>
      call.method === "POST" && /\/review\//.test(call.path) ? failure(409, { message: "已被他人決定", reason: "fsm_state_conflict" }) : undefined,
    );
    const modal = await screen.findByTestId("decision-modal");
    const base = kanbanGets(calls);
    fireEvent.click(within(modal).getByTestId("decision-APPROVE"));
    fireEvent.click(within(modal).getByTestId("decision-confirm"));
    const error = await within(modal).findByTestId("decision-error");
    expect(error.textContent).toContain("已經有人處理過");
    fireEvent.click(within(modal).getByTestId("decision-confirm"));
    fireEvent.click(within(modal).getByTestId("decision-confirm"));
    await waitFor(() => expect(kanbanGets(calls)).toBe(base + 1));
    expect(reviewPosts(calls)).toHaveLength(1);
    expect((within(modal).getByTestId("decision-confirm") as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("單一彈窗殼與權限", () => {
  it("AT_962_14_7 研究面只有一個決策彈窗殼（DecisionModal）；審核端點 hook 只被它使用；P0 類型 (a) 仍重用 SddEscalationBlock", () => {
    const dir = path.resolve(process.cwd(), "components", "domain", "research");
    const sources = readdirSync(dir)
      .filter((n) => /\.tsx$/.test(n) && !/\.test\.tsx$/.test(n))
      .map((n) => ({ name: n, src: readFileSync(path.join(dir, n), "utf8") }));
    const where = (needle: RegExp) => sources.filter((s) => needle.test(s.src)).map((s) => s.name);
    expect(where(/export function DecisionModal\b/)).toEqual(["DecisionModal.tsx"]);
    expect(where(/data-testid="decision-modal"/)).toEqual(["DecisionModal.tsx"]);
    expect(where(/useReviewExecution|reviewExecution/)).toEqual(["DecisionModal.tsx"]);
    expect(where(/import \{ SddEscalationBlock \}/)).toEqual(["GatekeeperPanel.tsx"]);
  });

  it("AT_962_14_E_1 VIEWER：內容可讀；所有決定鈕停用且 title 為權限不足；送出請求 0", () => {
    const { calls } = center("VIEWER");
    const modal = screen.getByTestId("decision-modal");
    expect(within(modal).getByTestId("decision-reason").textContent).toBe(PENDING_ESCALATED.reason);
    for (const button of within(modal).getByTestId("decision-buttons").querySelectorAll("button")) {
      expect((button as HTMLButtonElement).disabled).toBe(true);
      expect(button.getAttribute("title")).toBe("權限不足");
      fireEvent.click(button);
    }
    expect((within(modal).getByTestId("decision-confirm") as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(within(modal).getByTestId("decision-confirm"));
    expect(calls.filter((c) => c.method !== "GET")).toHaveLength(0);
  });

  it("AT_962_14_E_2 allowedDecisions 只有 APPROVE、REJECT：沒有重試與跳過按鈕", () => {
    center("OPERATOR", [{ ...PENDING_ESCALATED, allowedDecisions: ["APPROVE", "REJECT"] }]);
    const modal = screen.getByTestId("decision-modal");
    expect([...within(modal).getByTestId("decision-buttons").querySelectorAll("button")].map((b) => b.textContent)).toEqual(["通過", "拒絕"]);
    expect(within(modal).queryByTestId("decision-RETRY")).toBeNull();
    expect(within(modal).queryByTestId("decision-SKIP")).toBeNull();
  });

  it("AT_962_14_E_4 無逾時自動處理：時間前進 72 小時仍無自動決定請求，彈窗仍在", async () => {
    vi.useFakeTimers();
    const { calls } = center("OPERATOR");
    expect(modals()).toHaveLength(1);
    await act(async () => void (await vi.advanceTimersByTimeAsync(72 * 60 * 60 * 1000)));
    expect(reviewPosts(calls)).toHaveLength(0);
    expect(calls.filter((c) => c.method !== "GET")).toHaveLength(0);
    expect(modals()).toHaveLength(1);
  });
});
