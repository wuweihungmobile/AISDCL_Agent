/**
 * SCG 登錄對話框（TCS-ResearchToPRD-P2-20261107 AT-962-4-7、4-8、4-E-6～4-E-9；D-144 F-05：≥3 負控）。
 */
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Role } from "@/lib/api/types";
import { BUILD_DISABLED_TEXT, RESEARCH_REASON_TEXT } from "@/lib/domain/research";
import { R3 } from "@/tests/fixtures/research/ids";
import { callsOf, failure, renderResearch, stubResearchApi, type ApiCall, type Reply } from "@/tests/helpers/research";
import { GateRegisterDialog } from "./GateRegisterDialog";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(""),
}));

const GATES_URL = /\/gates$/;
function mount(role: Role = "ADMIN", opts: { scrOpen?: boolean; reply?: (call: ApiCall) => Reply } = {}) {
  const stub = stubResearchApi({ overrides: (call) => (call.method === "POST" && GATES_URL.test(call.path) ? opts.reply?.(call) : undefined) });
  const view = renderResearch(<GateRegisterDialog researchId={R3} scrOpen={opts.scrOpen ?? false} />, role);
  return { ...stub, ...view };
}
const openDialog = () => fireEvent.click(screen.getByTestId("gate-register-trigger"));
const submitBtn = () => screen.getByTestId("gate-submit") as HTMLButtonElement;
const setGate = (gate: string) => fireEvent.change(screen.getByTestId("gate-select"), { target: { value: gate } });
const setReason = (v: string) => fireEvent.change(screen.getByLabelText(/^理由/), { target: { value: v } });
const posts = (calls: ApiCall[]) => callsOf(calls, "POST", GATES_URL);

describe("SCG 登錄對話框", () => {
  it("AT_962_4_7 三個 gate 選項；PR_REVIEW 顯示獨立聲明與報告參照；勾選後送出本文為 {gate,result,reason,reviewReportRef,reviewerIndependent:true}；成功顯示 nextState；escalated 顯示已升級且沒有恢復按鈕", async () => {
    let escalate = false;
    const { calls, client } = mount("ADMIN", {
      reply: () => ({
        data: escalate
          ? { gateDecisionId: "g2", gate: "PR_REVIEW", result: "FAIL", fsmStateBefore: "PR_REVIEW", nextState: "ESCALATION_FINAL", escalated: true }
          : { gateDecisionId: "g1", gate: "PR_REVIEW", result: "PASS", fsmStateBefore: "PR_REVIEW", nextState: "RTM_VERIFY", escalated: false },
      }),
    });
    const invalidate = vi.spyOn(client, "invalidateQueries");
    openDialog();
    expect(within(screen.getByTestId("gate-select")).getAllByRole("option")).toHaveLength(3);
    expect(screen.getByLabelText(/審查報告參照/)).toBeDefined();
    fireEvent.click(screen.getByTestId("gate-independent"));
    setReason("審查通過");
    fireEvent.change(screen.getByLabelText(/審查報告參照/), { target: { value: "docs/06_quality/review.md" } });
    fireEvent.click(submitBtn());
    expect((await screen.findByTestId("gate-done")).textContent).toContain("RTM_VERIFY");
    expect(posts(calls)[0].body).toEqual({ gate: "PR_REVIEW", result: "PASS", reason: "審查通過", reviewReportRef: "docs/06_quality/review.md", reviewerIndependent: true });
    await waitFor(() => expect(invalidate.mock.calls.some(([f]) => JSON.stringify((f as { queryKey?: unknown })?.queryKey) === JSON.stringify(["research", "kanban", R3]))).toBe(true));
    // escalated 回應
    escalate = true;
    fireEvent.click(screen.getByRole("radio", { name: /FAIL/ }));
    setReason("未通過");
    fireEvent.click(submitBtn());
    await waitFor(() => expect(screen.getByTestId("gate-escalated")).toBeDefined());
    expect(screen.getByTestId("gate-escalated").textContent).toContain("已升級，等待人工處理");
    expect(screen.getByTestId("gate-done").textContent).toContain("ESCALATION_FINAL");
    expect(screen.queryByRole("button", { name: /恢復|resume/i })).toBeNull();
  });

  it("AT_962_4_8 RELEASE_READY 只有 FAIL（PASS 不渲染並說明 PASS 由建立 Tag 完成）、理由計數 1 至 500；scrOpen 時送出停用並顯示登記文案", () => {
    mount("ADMIN");
    openDialog();
    setGate("RELEASE_READY");
    expect(screen.queryByRole("radio", { name: /PASS/ })).toBeNull();
    expect(screen.getByRole("radio", { name: /FAIL/ })).toBeDefined();
    expect(screen.getByTestId("gate-release-note").textContent).toContain("PASS 由建立 Tag 完成");
    expect(screen.getByTestId("gate-reason-counter").textContent).toContain("1 至 500");
  });

  it("AT_962_4_8 scrOpen=true：送出鈕停用且顯示 BUILD_DISABLED_TEXT.scrOpen", () => {
    mount("ADMIN", { scrOpen: true });
    openDialog();
    setReason("x");
    fireEvent.click(screen.getByTestId("gate-independent"));
    expect(submitBtn().disabled).toBe(true);
    expect(screen.getByTestId("gate-scr-open").textContent).toBe(BUILD_DISABLED_TEXT.scrOpen);
  });

  it("AT_962_4_E_6 未勾獨立聲明：PR_REVIEW 送出鈕停用、請求數 0 並顯示聲明必填說明；RTM_VERIFY 與 RELEASE_READY 不要求勾選即可送", () => {
    const { calls } = mount("ADMIN");
    openDialog();
    expect(submitBtn().disabled).toBe(true);
    fireEvent.click(submitBtn());
    expect(posts(calls)).toHaveLength(0);
    expect(screen.getByTestId("gate-independent-required").textContent).toContain("獨立聲明");
    setGate("RTM_VERIFY");
    expect(screen.queryByTestId("gate-independent")).toBeNull();
    expect(submitBtn().disabled).toBe(false);
    setGate("RELEASE_READY");
    expect(submitBtn().disabled).toBe(true); // RELEASE_READY 只有 FAIL：理由必填
    setReason("CI 紅");
    expect(submitBtn().disabled).toBe(false);
  });

  it("AT_962_4_E_7 FAIL 無理由不可送；理由 500／501、報告參照 300／301 邊界；PASS 時理由可空", () => {
    mount("ADMIN");
    openDialog();
    setGate("RTM_VERIFY");
    expect(submitBtn().disabled).toBe(false); // PASS：理由可空
    fireEvent.click(screen.getByRole("radio", { name: /FAIL/ }));
    expect(submitBtn().disabled).toBe(true);
    expect(screen.getAllByRole("alert").some((n) => n.textContent?.includes("必須填理由"))).toBe(true);
    setReason("字".repeat(500));
    expect(submitBtn().disabled).toBe(false);
    setReason("字".repeat(501));
    expect(submitBtn().disabled).toBe(true);
    expect(screen.getAllByRole("alert").some((n) => n.textContent?.includes("最多 500"))).toBe(true);
    setReason("ok");
    const ref = screen.getByLabelText(/審查報告參照/);
    fireEvent.change(ref, { target: { value: "r".repeat(300) } });
    expect(submitBtn().disabled).toBe(false);
    fireEvent.change(ref, { target: { value: "r".repeat(301) } });
    expect(submitBtn().disabled).toBe(true);
    expect(screen.getAllByRole("alert").some((n) => n.textContent?.includes("最多 300"))).toBe(true);
  });

  it("AT_962_4_E_8 非 ADMIN（OPERATOR、VIEWER）：觸發鈕停用、title 含權限不足、點擊不開對話框、請求數 0", () => {
    for (const role of ["OPERATOR", "VIEWER"] as const) {
      const { calls, unmount } = mount(role);
      const trigger = screen.getByTestId("gate-register-trigger") as HTMLButtonElement;
      expect(trigger.disabled, role).toBe(true);
      expect(trigger.title, role).toContain("權限不足");
      fireEvent.click(trigger);
      expect(screen.queryByTestId("gate-dialog"), role).toBeNull();
      expect(posts(calls), role).toHaveLength(0);
      unmount();
    }
  });

  it("AT_962_4_E_9 錯誤文案取登記表：409 unmet 逐項中文、409 scr_open、422 digest_mismatch 列漂移路徑並可發起 SCR（sourceKind 預填 SCG4）、502 取 RESEARCH_REASON_TEXT、403 ACCESS_DENIED 取通用權限不足", async () => {
    const replies: Reply[] = [
      failure(409, { reason: "fsm_state_conflict", details: { unmet: ["tasks_incomplete", "rtm_below_100"] } }),
      failure(409, { reason: "scr_open" }),
      failure(422, { reason: "digest_mismatch", details: { drift: [{ path: "docs/01_requirements/PRD.md" }, { path: "docs/03_testing/TCS.md" }] } }),
      failure(502, { reason: "bridge_unreachable" }),
      failure(403, { reason: "ACCESS_DENIED" }),
    ];
    let n = 0;
    mount("ADMIN", { reply: () => replies[n++] });
    openDialog();
    fireEvent.click(screen.getByTestId("gate-independent"));
    setReason("x");
    const send = async () => {
      fireEvent.click(submitBtn());
      return (await waitFor(() => screen.getByTestId("gate-error"))).textContent ?? "";
    };
    const first = await send();
    expect(first).toContain("仍有任務未完成或未跳過");
    expect(first).toContain("追溯覆蓋率未達 100%");
    await waitFor(() => expect(submitBtn().disabled).toBe(false));
    expect(await send()).toContain(RESEARCH_REASON_TEXT.scr_open);
    await waitFor(() => expect(submitBtn().disabled).toBe(false));
    const drift = await send();
    expect(drift).toContain("docs/01_requirements/PRD.md");
    expect(drift).toContain("docs/03_testing/TCS.md");
    fireEvent.click(screen.getByTestId("gate-offer-scr"));
    expect(((await screen.findByTestId("scr-source")) as HTMLSelectElement).value).toBe("SCG4");
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("scr-dialog")).toBeNull());
    await waitFor(() => expect(submitBtn().disabled).toBe(false));
    expect(await send()).toContain(RESEARCH_REASON_TEXT.bridge_unreachable);
    await waitFor(() => expect(submitBtn().disabled).toBe(false));
    const denied = await send();
    expect(denied).toContain("權限不足");
    expect(denied).not.toContain("research_");
  });
});
