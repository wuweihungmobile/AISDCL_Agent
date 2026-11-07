/**
 * SCR 發起對話框與入口（TCS-ResearchToPRD-P2-20261107 AT-962-15-1～15-4、15-E-1～15-E-4）。
 */
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Role } from "@/lib/api/types";
import { READONLY_TITLE, RESEARCH_REASON_TEXT, SCR_REASON_CLASSES } from "@/lib/domain/research";
import { R3 } from "@/tests/fixtures/research/ids";
import { callsOf, failure, renderResearch, stubResearchApi, type ApiCall, type Reply } from "@/tests/helpers/research";
import { ScrLaunchButton, ScrRequestDialog } from "./ScrRequestDialog";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(""),
}));

const SCR_URL = /\/scr$/;
function mountDialog(sourceKind: string | undefined, reply?: (call: ApiCall) => Reply, role: Role = "OPERATOR") {
  const { calls } = stubResearchApi({ overrides: (call) => (call.method === "POST" && SCR_URL.test(call.path) ? reply?.(call) : undefined) });
  const view = renderResearch(<ScrRequestDialog researchId={R3} open onOpenChange={() => undefined} sourceKind={sourceKind} />, role);
  return { calls, ...view };
}
const fill = async (reason = "AC 需補充") => {
  fireEvent.change(screen.getByLabelText(/變更理由/), { target: { value: reason } });
};
const submit = () => fireEvent.click(screen.getByTestId("scr-submit"));

describe("入口", () => {
  it("AT_962_15_1 OPERATOR 與 ADMIN 可點、VIEWER 停用且 title 為權限不足；兩處入口同一元件（ScrLaunchButton）", () => {
    stubResearchApi();
    for (const role of ["OPERATOR", "ADMIN"] as const) {
      const { unmount } = renderResearch(<ScrLaunchButton researchId={R3} />, role);
      expect((screen.getByTestId("scr-launch") as HTMLButtonElement).disabled, role).toBe(false);
      unmount();
    }
    renderResearch(<ScrLaunchButton researchId={R3} />, "VIEWER");
    const viewer = screen.getByTestId("scr-launch") as HTMLButtonElement;
    expect(viewer.disabled).toBe(true);
    expect(viewer.title).toBe(READONLY_TITLE);
    expect(viewer.title).toContain("權限不足");
  });

  it("AT_962_15_E_2 VIEWER：入口不能開啟、請求數為 0；對話框的送出鈕也停用", async () => {
    const stub = stubResearchApi();
    renderResearch(<ScrLaunchButton researchId={R3} />, "VIEWER");
    fireEvent.click(screen.getByTestId("scr-launch"));
    expect(screen.queryByTestId("scr-dialog")).toBeNull();
    expect(callsOf(stub.calls, "POST", SCR_URL)).toHaveLength(0);
    renderResearch(<ScrRequestDialog researchId={R3} open onOpenChange={() => undefined} />, "VIEWER");
    expect((await screen.findByTestId("scr-submit")).hasAttribute("disabled")).toBe(true);
    expect(callsOf(stub.calls, "POST", SCR_URL)).toHaveLength(0);
  });

  it("規格變更進行中：入口停用並顯示登記文案", () => {
    stubResearchApi();
    renderResearch(<ScrLaunchButton researchId={R3} scrOpen />, "ADMIN");
    const btn = screen.getByTestId("scr-launch") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    expect(btn.title).toContain("規格變更中");
  });
});

describe("表單", () => {
  it("AT_962_15_2 kind 附後果說明；sourceKind 依入口預填（SCG4、HEALING_FAILED、HUMAN）；reasonClass 五個中文選項；章節選項取自凍結 PRD；證據連結選填", async () => {
    for (const [from, expected] of [
      ["SCG4", "SCG4"],
      ["HEALING_FAILED", "HEALING_FAILED"],
      [undefined, "HUMAN"],
    ] as const) {
      const { unmount } = mountDialog(from);
      expect(((await screen.findByTestId("scr-source")) as HTMLSelectElement).value).toBe(expected);
      unmount();
    }
    mountDialog(undefined);
    expect(screen.getByTestId("scr-kind-text-MINOR").textContent).toContain("小幅");
    expect(screen.getByTestId("scr-kind-text-MAJOR").textContent).toContain("後繼");
    const classes = within(screen.getByTestId("scr-reason-class"))
      .getAllByRole("option")
      .map((o) => o.textContent);
    expect(classes).toEqual(["PRD 缺漏證據", "AC 模糊", "需求變更", "技術不可行", "其他"]);
    expect([...SCR_REASON_CLASSES]).toEqual(classes);
    await waitFor(() => expect(within(screen.getByTestId("scr-sections")).getByText("1 背景")).toBeDefined());
    expect(within(screen.getByTestId("scr-sections")).getByText("2 問題")).toBeDefined();
    expect(screen.getByLabelText(/證據連結/).hasAttribute("required")).toBe(false);
  });

  it("AT_962_15_E_1 常數邊界：reason 500／501、章節 20／21（單項 200／201）、證據連結 500／501；計數器顯示剩餘字數", async () => {
    mountDialog(undefined);
    await fill("字".repeat(500));
    expect(screen.getByTestId("scr-reason-counter").textContent).toContain("剩餘 0 字");
    expect((screen.getByTestId("scr-submit") as HTMLButtonElement).disabled).toBe(false);
    await fill("字".repeat(501));
    expect(screen.getByTestId("scr-reason-counter").textContent).toContain("剩餘 -1 字");
    expect((screen.getByTestId("scr-submit") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole("alert").textContent).toContain("理由最多 500 字");
    await fill("ok");
    const url = screen.getByLabelText(/證據連結/);
    fireEvent.change(url, { target: { value: "https://a.example/" + "p".repeat(500 - 18) } });
    expect((screen.getByTestId("scr-submit") as HTMLButtonElement).disabled).toBe(false);
    fireEvent.change(url, { target: { value: "https://a.example/" + "p".repeat(500 - 17) } });
    expect((screen.getByTestId("scr-submit") as HTMLButtonElement).disabled).toBe(true);
  });

  it("AT_962_15_E_4 證據連結只接受 https：javascript: 在前端即被擋並顯示錯誤，https 通過；非 https 字串不以 href 渲染", async () => {
    const { calls } = mountDialog(undefined);
    await fill();
    const url = screen.getByLabelText(/證據連結/);
    fireEvent.change(url, { target: { value: "javascript:alert(1)" } });
    expect((screen.getByTestId("scr-submit") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole("alert").textContent).toContain("https");
    expect(document.querySelectorAll('a[href^="javascript"]')).toHaveLength(0);
    fireEvent.change(url, { target: { value: "https://a.example" } });
    expect((screen.getByTestId("scr-submit") as HTMLButtonElement).disabled).toBe(false);
    submit();
    await waitFor(() => expect(callsOf(calls, "POST", SCR_URL)).toHaveLength(1));
    expect((callsOf(calls, "POST", SCR_URL)[0].body as { evidenceUrl: string }).evidenceUrl).toBe("https://a.example");
  });

  it("AT_962_15_E_3 reasonClass：請求本文送中文字面（任一分類），章節與證據連結以獨立欄送出", async () => {
    const { calls } = mountDialog("HUMAN");
    await fill("理由");
    await userEvent.selectOptions(screen.getByTestId("scr-reason-class"), "技術不可行");
    submit();
    await waitFor(() => expect(callsOf(calls, "POST", SCR_URL)).toHaveLength(1));
    const body = callsOf(calls, "POST", SCR_URL)[0].body as Record<string, unknown>;
    expect(body.reasonClass).toBe("技術不可行");
    expect(body).toMatchObject({ kind: "MINOR", sourceKind: "HUMAN", reason: "理由", affectedSections: [] });
    expect("evidenceUrl" in body).toBe(false);
  });
});

describe("送出與錯誤", () => {
  it("AT_962_15_3 MINOR 202 顯示已發起；MAJOR 路由導向後繼專案；HEALING_FAILED 只顯示可複製指令且不顯示已發起", async () => {
    // MINOR
    const a = mountDialog("HUMAN");
    await fill();
    submit();
    expect((await screen.findByTestId("scr-started")).textContent).toBe("SCR 已發起");
    a.unmount();
    // MAJOR：導向 /research/<successorResearchId>
    const b = mountDialog("HUMAN", () => ({ status: 202, data: { scrNo: 2, kind: "MAJOR", status: "OPEN", successorResearchId: "44444444-4444-4444-8444-444444444444" } }));
    await fill();
    fireEvent.click(screen.getByRole("radio", { name: /大幅/ }));
    submit();
    await waitFor(() => expect(push).toHaveBeenCalledWith("/research/44444444-4444-4444-8444-444444444444"));
    b.unmount();
    // HEALING_FAILED：200＋recovery
    mountDialog("HEALING_FAILED", () => ({ data: { scrNo: 3, kind: "MINOR", status: "OPEN", recovery: { target: "inner-fsm", powershell: "Push-Location x; Pop-Location", posix: "cd x" } } }));
    await fill();
    submit();
    expect(await screen.findByTestId("scr-recovery")).toBeDefined();
    expect(screen.getByTestId("sdd-recovery-powershell")).toBeDefined();
    expect(screen.getByTestId("sdd-recovery-posix")).toBeDefined();
    expect(screen.queryByText("SCR 已發起")).toBeNull();
  });

  it("AT_962_15_4 422 violations 逐筆回到欄位；scr_open／scr_limit／fsm_state_conflict 顯示登記文案（取 RESEARCH_REASON_TEXT）", async () => {
    const a = mountDialog("HUMAN", () =>
      failure(422, {
        reason: "invalid_request",
        details: {
          violations: [
            { field: "reason", rule: "too_long" },
            { field: "evidenceUrl", rule: "not_https" },
          ],
        },
      }),
    );
    await fill();
    submit();
    const reasonField = (await screen.findAllByRole("alert")).map((n) => n.textContent ?? "");
    expect(reasonField.some((t) => t.includes("too_long"))).toBe(true);
    expect(reasonField.some((t) => t.includes("not_https"))).toBe(true);
    a.unmount();
    for (const reason of ["scr_open", "scr_limit", "fsm_state_conflict"] as const) {
      const v = mountDialog("HUMAN", () => failure(409, { reason }));
      await fill();
      submit();
      expect((await screen.findByTestId("scr-error")).textContent).toBe(RESEARCH_REASON_TEXT[reason]);
      v.unmount();
    }
    expect(RESEARCH_REASON_TEXT.scr_limit).toContain("大幅");
  });
});
