import { focusManager } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ProjectDetail, SddFsmState } from "@/lib/api/types";
import { Providers, failure, makeClient, signIn, stubApi, type ApiCall, type Reply } from "@/tests/helpers/api";
import { PROJECT_ID, engineStatus, escalatedFsm, fsmState, POSIX_RECOVERY } from "@/tests/helpers/sddFixtures";
import { projectDetail } from "@/tests/helpers/runFixtures";
import { SddGovernanceCard } from "./SddGovernanceCard";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => `/projects/${PROJECT_ID}`,
  useSearchParams: () => new URLSearchParams(),
}));

/**
 * 專案詳情「SDD 治理」區（契約 §4.7.1；UI-SDD-01；整合輪 115）：
 * 假後端依契約回 `GET /engines/sdd?projectId=`（專案模式：省略 project 時後端取有效 FSM 專案，一個請求就帶回 fsm）。
 */
const ENGINE = "/api/v1/engines/sdd";
const FREEZE = `/api/v1/projects/${PROJECT_ID}/sdd/freeze`;
const BINDING = `/api/v1/projects/${PROJECT_ID}/sdd-binding`;

const USED = projectDetail({
  id: PROJECT_ID,
  name: "AISDLC Core Platform",
  executionPath: "/work/core",
  sddProject: "core-fsm",
  sddSpecDir: "/work/core/docs/03_testing/contracts",
  sddSpecFile: "/work/core/docs/03_testing/contracts/TCS-Alpha.md",
});
const UNUSED = projectDetail({ id: PROJECT_ID, name: "AISDLC Core Platform", executionPath: "/work/core" });

type Handler = (c: ApiCall) => Reply;

/** 預設的假後端：engines/sdd 回 world.fsm；呼叫端可用 extra 覆寫任一端點（freeze、sdd-binding…）。 */
function backend(world: { fsm: SddFsmState | null; status?: ReturnType<typeof engineStatus> }, extra: Handler = () => undefined) {
  return stubApi((c) => {
    const custom = extra(c);
    if (custom) return custom;
    if (c.method === "GET" && c.path === ENGINE) return { data: world.status ?? engineStatus(world.fsm) };
    if (c.method === "GET" && c.path === `/api/v1/projects/${PROJECT_ID}`) return { data: USED };
    return undefined;
  });
}

const engineCalls = (calls: ApiCall[]) => calls.filter((c) => c.path === ENGINE);

function view(project: ProjectDetail = USED, canWrite = true) {
  return render(
    <Providers client={makeClient()}>
      <SddGovernanceCard project={project} canWrite={canWrite} />
    </Providers>,
  );
}

const text = (testid: string) => screen.getByTestId(testid).textContent ?? "";

beforeEach(() => signIn("OPERATOR", "operator"));

describe("SDD 治理區：已使用的專案（預設展開；契約 §4.7.1）", () => {
  it("標題「SDD 治理」、預設展開；請求恰一個 GET /engines/sdd?projectId=（不帶 project：由後端取有效 FSM 專案）", async () => {
    const { calls } = backend({ fsm: fsmState() });
    view();
    expect(screen.getByRole("button", { name: "SDD 治理" })).toHaveAttribute("aria-expanded", "true");
    await screen.findByText("HUMAN_PENDING");
    expect(engineCalls(calls)).toHaveLength(1);
    expect(engineCalls(calls)[0].url).toBe(`${ENGINE}?projectId=${PROJECT_ID}`);
    expect(engineCalls(calls)[0].query.has("project")).toBe(false);
    expect(screen.getByTestId("sdd-governance")).toHaveAttribute("data-used", "true");
  });

  it("各列與契約逐值一致：SDD 專案（等寬）、標準鍵、規格目錄、規格檔、目前狀態、階段、凍結狀態、待人工；靜態提示在底部", async () => {
    backend({ fsm: fsmState() });
    view();
    await screen.findByTestId("sdd-phase");
    expect(text("sdd-gov-project")).toContain("core-fsm");
    expect(screen.getByTestId("sdd-gov-project").querySelector("span.font-mono")).not.toBeNull();
    expect(text("sdd-gov-key")).toBe("core-fsm");
    expect(text("sdd-gov-dir")).toBe("/work/core/docs/03_testing/contracts");
    expect(text("sdd-gov-file")).toBe("/work/core/docs/03_testing/contracts/TCS-Alpha.md");
    expect(text("sdd-gov-state")).toBe("HUMAN_PENDING");
    expect(screen.getByTestId("sdd-phase-label")).toHaveTextContent("人工確認");
    expect(screen.getByTestId("sdd-phase")).toHaveAttribute("data-phase", "HUMAN_GATE");
    expect(screen.getByTestId("sdd-phase")).toHaveAttribute("data-order", "3");
    expect(text("sdd-gov-frozen")).toBe("尚未凍結");
    expect(text("sdd-gov-pending")).toBe("等待人工確認");
    expect(text("sdd-gov-note")).toBe("FSM 狀態檔位於專案根的 build/reports/fsm，請把 build/reports/ 加入該專案的 .gitignore。");
    const all = screen.getByTestId("sdd-governance").textContent ?? "";
    for (const bad of ["undefined", "null", "NaN", "[object Object]"]) expect(all).not.toContain(bad);
  });

  it("已凍結：「已凍結：<最後一筆 stage>（<frozen_at 本機時區>）」；不解讀 spec_doc_digests（不顯示摘要）", async () => {
    backend({
      fsm: fsmState({
        currentState: "SPEC_FROZEN",
        phase: { name: "FROZEN", order: 4, blocking: false, observation: false },
        frozenStages: [{ stage: "Stage-1", frozen_at: "2026-10-17T01:02:03+00:00", approved_by: "operator", spec_doc_digests: { "docs/TCS-Alpha.md": `sha256:${"a".repeat(64)}` } }],
      }),
    });
    view();
    await screen.findByTestId("sdd-phase");
    expect(text("sdd-gov-frozen")).toMatch(/^已凍結：Stage-1（2026-10-1[67] \d{2}:\d{2}:\d{2}）$/);
    expect(screen.getByTestId("sdd-governance").textContent).not.toContain("sha256:");
  });

  it("標準鍵與檔內原名不同：兩者並列，原名加註「檔內原名」", async () => {
    backend({ fsm: fsmState({ project: "我的/專案", fsmProject: "我的_專案" }) });
    view();
    await screen.findByTestId("sdd-phase");
    expect(text("sdd-gov-key")).toContain("我的_專案");
    expect(screen.getByTestId("sdd-gov-original-name")).toHaveTextContent("我的/專案（檔內原名）");
  });

  it("缺值一律單一的「—」：fsm 各欄為 null、標準鍵缺、phase 缺席（階段欄「—」仍顯示 currentState）；規格目錄與規格檔缺值也是「—」", async () => {
    backend({ fsm: fsmState({ fsmProject: null, phase: null, frozenStages: undefined as never, humanPending: undefined as never }) });
    view(projectDetail({ id: PROJECT_ID, executionPath: "/work/core", sddProject: "core-fsm", sddSpecDir: null, sddSpecFile: "" }));
    await screen.findByText("HUMAN_PENDING");
    expect(text("sdd-gov-key")).toBe("—");
    expect(text("sdd-gov-dir")).toBe("—");
    expect(text("sdd-gov-file")).toBe("—");
    expect(text("sdd-gov-frozen")).toBe("—");
    expect(text("sdd-gov-pending")).toBe("無");
    expect(screen.getByTestId("sdd-phase-label")).toHaveTextContent("—");
    expect(screen.getByTestId("sdd-phase")).toHaveAttribute("data-order", "0");
    expect(screen.queryByTestId("sdd-phase-steps")).toBeNull(); // 缺 phase：不畫步驟
    expect(text("sdd-gov-state")).toBe("HUMAN_PENDING"); // 仍顯示 currentState
  });
});

describe("SDD 治理區：從未使用的專案（預設收合；沒有「未綁定」狀態）", () => {
  it("標題「SDD 治理（尚未使用）」、預設收合、不發任何請求；「SDD 專案」缺值＝「（預設：專案名）」而不是「—」", async () => {
    const { calls } = backend({ fsm: null });
    view(UNUSED);
    const toggle = screen.getByRole("button", { name: "SDD 治理（尚未使用）" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByTestId("sdd-governance-body")).toBeNull();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(engineCalls(calls)).toHaveLength(0); // 收合時不輪詢
    expect(screen.getByTestId("sdd-governance")).toHaveAttribute("data-used", "false");

    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(text("sdd-gov-project")).toContain("（預設：AISDLC Core Platform）");
    await waitFor(() => expect(engineCalls(calls)).toHaveLength(1));
  });

  it("展開後 fsm 為 null（尚無狀態檔、reason=null）：「目前狀態」顯示「尚無 FSM 狀態檔…」並加註建立位置；其餘 FSM 欄位全部「—」", async () => {
    backend({ fsm: null });
    view(UNUSED);
    await userEvent.click(screen.getByRole("button", { name: "SDD 治理（尚未使用）" }));
    const message = await screen.findByTestId("sdd-gov-message");
    expect(message).toHaveTextContent("尚無 FSM 狀態檔（SDD runtime 執行後才會產生）");
    expect(screen.getByTestId("sdd-gov-hint")).toHaveTextContent("請在專案根的 SDD session 建立：/work/core/build/reports/fsm");
    for (const id of ["sdd-gov-key", "sdd-gov-phase", "sdd-gov-frozen", "sdd-gov-pending"]) expect(text(id), id).toBe("—");
    expect(text("sdd-gov-dir")).toBe("—");
    expect(text("sdd-gov-file")).toBe("—");
  });

  it("已使用的專案可手動收合再展開；收合後不再請求", async () => {
    const { calls } = backend({ fsm: fsmState() });
    view();
    await screen.findByText("HUMAN_PENDING");
    const toggle = screen.getByRole("button", { name: "SDD 治理" });
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByTestId("sdd-governance-body")).toBeNull();
    const before = engineCalls(calls).length;
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(engineCalls(calls)).toHaveLength(before);
  });
});

describe("SDD 治理區：FSM 取不到的各種原因（M-20／M-21 文案）", () => {
  it.each([
    ["fsm_not_found", "找不到所選專案的 FSM 狀態檔", true],
    ["fsm_state_unreadable", "FSM 狀態檔無法讀取", false],
    ["sdd_root_rejected", "專案路徑不在 Bridge 允許的根目錄內（或已不存在）", false],
  ] as const)("reason=%s：顯示「%s」（%s 加註建立位置）；引擎仍是可用", async (reason, message, withHint) => {
    backend({ fsm: null, status: engineStatus(null, { reason }) });
    view();
    const note = await screen.findByTestId("sdd-gov-message");
    expect(note).toHaveTextContent(message);
    expect(note).toHaveAttribute("data-reason", reason);
    expect(screen.queryByTestId("sdd-gov-hint") !== null).toBe(withHint);
    expect(text("sdd-gov-key")).toBe("—");
  });

  it.each([
    ["bridge_unreachable", "Engine Bridge 無法連線"],
    ["sdd_unavailable", "找不到 AISDLC_SDD 目錄（請檢查 Bridge 的 SDD_ROOT）"],
    ["bridge_error", "Engine Bridge 回應異常"],
  ] as const)("引擎不可用（reason=%s）：顯示「%s」，沒有 FSM 欄位（200 不是錯誤頁）", async (reason, message) => {
    backend({ fsm: null, status: engineStatus(null, { available: false, reason, version: null, projects: [] }) });
    view();
    expect(await screen.findByTestId("sdd-gov-message")).toHaveTextContent(message);
    expect(screen.queryByText("無法取得 SDD 治理狀態")).toBeNull();
  });

  it("後端日後新增 reason：顯示「引擎回報：<原值>」，不崩潰也不吞掉", async () => {
    backend({ fsm: null, status: engineStatus(null, { reason: "future_reason" as never }) });
    view();
    expect(await screen.findByTestId("sdd-gov-message")).toHaveTextContent("引擎回報：future_reason");
  });

  it("console-api 自己回錯（例如 404 專案已被刪除、500）：顯示錯誤與重試（不編造狀態）；重試成功後恢復", async () => {
    let ok = false;
    backend({ fsm: fsmState() }, (c) => (c.path === ENGINE && !ok ? failure(500, { message: "伺服器錯誤" }) : undefined));
    view();
    expect(await screen.findByText("無法取得 SDD 治理狀態")).toBeInTheDocument();
    expect(text("sdd-gov-state")).toBe("—");
    ok = true;
    await userEvent.click(screen.getByRole("button", { name: "重試" }));
    expect(await screen.findByText("HUMAN_PENDING")).toBeInTheDocument();
    expect(screen.queryByText("無法取得 SDD 治理狀態")).toBeNull();
  });
});

describe("SDD 治理區：ESCALATION（契約 §4.7.3）", () => {
  it("阻塞態：紅色橫幅、八個步驟全灰、ESCALATION 區塊（末筆摘要、來源行）與兩段恢復指令各有複製鈕；核准凍結停用", async () => {
    backend({ fsm: escalatedFsm() });
    view();
    expect(await screen.findByTestId("sdd-blocked-banner")).toHaveTextContent("阻塞：ESCALATION（需人工恢復）");
    expect(screen.getByTestId("sdd-phase")).toHaveAttribute("data-blocking", "true");
    expect(screen.getAllByTestId("sdd-phase-step").every((li) => li.getAttribute("data-state") === "upcoming")).toBe(true);
    const block = screen.getByTestId("sdd-escalation");
    expect(within(block).getByTestId("sdd-escalation-summary")).toHaveTextContent(/^ESCALATION・2026-10-17 09:02:03・AutoClaude 委派失敗：評估未通過$/);
    expect(within(block).getByTestId("sdd-escalation-source")).toHaveTextContent("來源：autoclaude_delegated_failed・AutoClaude 委派失敗（引擎升級）");
    const recovery = within(block).getByTestId("sdd-recovery");
    expect(recovery.querySelectorAll("[data-shell]")).toHaveLength(2);
    expect(within(recovery).getByTestId("sdd-recovery-command-posix")).toHaveTextContent(POSIX_RECOVERY);
    expect(within(recovery).getByRole("button", { name: "複製 PowerShell 指令" })).toBeInTheDocument();
    expect(within(recovery).getByRole("button", { name: "複製 POSIX（bash／zsh） 指令" })).toBeInTheDocument();
    expect(screen.getByTestId("sdd-freeze-button")).toBeDisabled();
  });
});

describe("SDD 治理區：角色與按鈕啟用條件", () => {
  it("VIEWER：看得到內容，但「編輯」與「核准凍結」都不顯示（不是停用）", async () => {
    signIn("VIEWER", "viewer");
    backend({ fsm: fsmState() });
    view(USED, false);
    await screen.findByText("HUMAN_PENDING");
    expect(screen.queryByTestId("sdd-binding-edit")).toBeNull();
    expect(screen.queryByTestId("sdd-freeze-button")).toBeNull();
    expect(screen.queryByRole("button", { name: /核准凍結|編輯/ })).toBeNull();
  });

  it("核准凍結：currentState＝HUMAN_PENDING 時啟用、沒有停用說明（其他狀態停用，見下一組）", async () => {
    backend({ fsm: fsmState() });
    view();
    await screen.findByText("HUMAN_PENDING");
    expect(screen.getByTestId("sdd-freeze-button")).toBeEnabled();
    expect(screen.getByTestId("sdd-freeze-button")).not.toHaveAttribute("title");
    expect(screen.queryByTestId("sdd-freeze-hint")).toBeNull();
  });

  it.each([
    ["IMPLEMENTATION", "FSM 目前不在 HUMAN_PENDING（目前：IMPLEMENTATION）"],
    ["SPEC_FROZEN", "FSM 目前不在 HUMAN_PENDING（目前：SPEC_FROZEN）"],
    [null, "FSM 目前不在 HUMAN_PENDING（目前：—）"],
  ] as const)("currentState＝%s：停用，說明「%s」", async (state, hint) => {
    backend({ fsm: fsmState({ currentState: state, phase: null }) });
    view();
    await waitFor(() => expect(screen.getByTestId("sdd-freeze-hint")).toHaveTextContent(hint));
    const button = screen.getByTestId("sdd-freeze-button");
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("title", hint);
    expect(button).toHaveAttribute("aria-describedby", screen.getByTestId("sdd-freeze-hint").id);
  });

  it("fsm 為 null（取不到）時一律停用", async () => {
    backend({ fsm: null });
    view();
    await screen.findByTestId("sdd-gov-message");
    expect(screen.getByTestId("sdd-freeze-button")).toBeDisabled();
    expect(screen.getByTestId("sdd-freeze-hint")).toHaveTextContent("目前：—");
  });
});

describe("SDD 治理區：輪詢（契約 §4.7.1：30 秒、分頁不可見時暫停、收合時不輪詢）", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });
  afterEach(() => {
    focusManager.setFocused(undefined);
    vi.useRealTimers();
  });

  it("展開時每 30 秒一個請求；分頁失焦停止；收合停止", async () => {
    const { calls } = backend({ fsm: fsmState() });
    view();
    await screen.findByText("HUMAN_PENDING");
    expect(engineCalls(calls)).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(29_000);
    expect(engineCalls(calls)).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(2_000);
    await waitFor(() => expect(engineCalls(calls)).toHaveLength(2));

    focusManager.setFocused(false);
    await vi.advanceTimersByTimeAsync(30_000 * 3);
    expect(engineCalls(calls)).toHaveLength(2);
    focusManager.setFocused(undefined);

    await userEvent.click(screen.getByRole("button", { name: "SDD 治理" }));
    const after = engineCalls(calls).length;
    await vi.advanceTimersByTimeAsync(30_000 * 3);
    expect(engineCalls(calls)).toHaveLength(after);
  });

  it("下一輪輪詢跟上 FSM 變動（沒有整頁重載）", async () => {
    const world = { fsm: fsmState() as SddFsmState | null };
    backend(world);
    view();
    await screen.findByText("HUMAN_PENDING");
    world.fsm = fsmState({ currentState: "SPEC_FROZEN", phase: { name: "FROZEN", order: 4, blocking: false, observation: false } });
    await vi.advanceTimersByTimeAsync(31_000);
    await waitFor(() => expect(text("sdd-gov-state")).toBe("SPEC_FROZEN"));
    expect(screen.getByTestId("sdd-phase-label")).toHaveTextContent("規格凍結");
  });
});

describe("編輯 SDD 專案對話框（契約 §1.10.7、§4.7.1；API-PRJ-08）", () => {
  async function openEditor() {
    await screen.findByText("HUMAN_PENDING");
    await userEvent.click(screen.getByRole("button", { name: "編輯 SDD 專案" }));
    return screen.findByRole("dialog", { name: "編輯 SDD 專案" });
  }

  it("預填目前值；輸入新值儲存：PUT 帶 {sddProject}、toast「已更新 SDD 專案」、對話框關閉、重取專案詳情與 engines/sdd", async () => {
    const { calls } = backend({ fsm: fsmState() }, (c) => (c.method === "PUT" && c.path === BINDING ? { data: { ...USED, sddProject: "core-new" } } : undefined));
    view();
    const dialog = await openEditor();
    const input = within(dialog).getByLabelText(/^SDD 專案/);
    expect(input).toHaveValue("core-fsm");
    expect(dialog).toHaveTextContent("值會交給引擎橋接淨化後生效；改綁不搬移 FSM 狀態檔，也不影響進行中的批次");
    await userEvent.clear(input);
    await userEvent.type(input, "  core-new  ");
    const enginesBefore = engineCalls(calls).length;
    await userEvent.click(within(dialog).getByRole("button", { name: "儲存" }));
    expect(await screen.findByText("已更新 SDD 專案")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    const put = calls.find((c) => c.method === "PUT" && c.path === BINDING);
    expect(put?.body).toEqual({ sddProject: "core-new" });
    await waitFor(() => expect(engineCalls(calls).length).toBeGreaterThan(enginesBefore)); // 成功後 FSM 狀態重取
  });

  it("留空並儲存＝清除：送 {sddProject: null}（不是空字串、不是缺欄位）", async () => {
    const { calls } = backend({ fsm: fsmState() }, (c) => (c.method === "PUT" && c.path === BINDING ? { data: { ...USED, sddProject: null } } : undefined));
    view();
    const dialog = await openEditor();
    await userEvent.clear(within(dialog).getByLabelText(/^SDD 專案/));
    await userEvent.click(within(dialog).getByRole("button", { name: "儲存" }));
    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    expect(calls.find((c) => c.method === "PUT")?.body).toEqual({ sddProject: null });
  });

  it("格式不合（超過 100 字元、含控制字元）：欄位下顯示說明、不送請求", async () => {
    const { calls } = backend({ fsm: fsmState() });
    view();
    const dialog = await openEditor();
    const input = within(dialog).getByLabelText(/^SDD 專案/);
    await userEvent.clear(input);
    await userEvent.click(input);
    await userEvent.paste("x".repeat(101));
    await userEvent.click(within(dialog).getByRole("button", { name: "儲存" }));
    expect(await within(dialog).findByText("最多 100 字元（目前 101）")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "PUT")).toBe(false);
  });

  it("400：在欄位下顯示 errors[0].message；409 sdd_binding_conflict：「同一個專案根下已有另一個專案（<holder 前 8 碼>）綁定了這個 FSM 專案」＋traceId", async () => {
    let mode: "400" | "409" = "400";
    backend({ fsm: fsmState() }, (c) => {
      if (c.method !== "PUT" || c.path !== BINDING) return undefined;
      return mode === "400"
        ? failure(400, { message: "請求參數錯誤", errors: [{ field: "sddProject", message: "不可含控制字元" }] })
        : failure(409, {
            message: "綁定衝突",
            reason: "sdd_binding_conflict",
            details: { cause: "already_bound_elsewhere", sddProject: "core-fsm", holderProjectId: "1a2b3c4d-0000-4000-8000-000000000000" },
          });
    });
    view();
    const dialog = await openEditor();
    const input = within(dialog).getByLabelText(/^SDD 專案/);
    await userEvent.click(within(dialog).getByRole("button", { name: "儲存" }));
    expect(await within(dialog).findByText("不可含控制字元")).toBeInTheDocument();
    expect(within(dialog).queryByTestId("sdd-binding-error")).toBeNull(); // 400 以欄位錯誤為主，沒有其餘項目就不另外開訊息區
    expect(input).toHaveAttribute("aria-invalid", "true");

    mode = "409";
    await userEvent.click(within(dialog).getByRole("button", { name: "儲存" }));
    const error = await within(dialog).findByTestId("sdd-binding-error");
    expect(error).toHaveTextContent("同一個專案根下已有另一個專案（1a2b3c4d）綁定了這個 FSM 專案");
    expect(error).toHaveTextContent("traceId：tr-409");
    expect(screen.getByRole("dialog", { name: "編輯 SDD 專案" })).toBeInTheDocument(); // 失敗不關閉
  });

  it("其餘錯誤（例如 502）照一般錯誤顯示 message 與 traceId", async () => {
    backend({ fsm: fsmState() }, (c) => (c.method === "PUT" && c.path === BINDING ? failure(500, { message: "伺服器暫時無法處理" }) : undefined));
    view();
    const dialog = await openEditor();
    await userEvent.click(within(dialog).getByRole("button", { name: "儲存" }));
    const error = await within(dialog).findByTestId("sdd-binding-error");
    expect(error).toHaveTextContent("伺服器暫時無法處理");
    expect(error).toHaveTextContent("traceId：tr-500");
  });

  it.each(["Esc", "取消鈕"] as const)("以「%s」關閉：焦點回到「編輯」鈕（W6 的焦點歸還）", async (how) => {
    backend({ fsm: fsmState() });
    view();
    await screen.findByText("HUMAN_PENDING");
    const trigger = screen.getByRole("button", { name: "編輯 SDD 專案" });
    trigger.focus();
    await userEvent.keyboard("{Enter}");
    const dialog = await screen.findByRole("dialog", { name: "編輯 SDD 專案" });
    await waitFor(() => expect(dialog).toContainElement(document.activeElement as HTMLElement));
    if (how === "Esc") await userEvent.keyboard("{Escape}");
    else await userEvent.click(within(dialog).getByRole("button", { name: "取消" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(trigger).toHaveFocus());
  });
});

describe("核准凍結對話框（人工閘；契約 §1.10.2、§4.7.1；API-SGN-06）", () => {
  async function openFreeze() {
    await screen.findByText("HUMAN_PENDING");
    await userEvent.click(screen.getByTestId("sdd-freeze-button"));
    return screen.findByRole("dialog", { name: "核准凍結規格" });
  }
  const fill = async (dialog: HTMLElement, reason: string) => {
    await userEvent.type(within(dialog).getByTestId("sdd-freeze-reason"), reason);
  };

  it("說明文字、預填 docs＝已綁定規格檔相對專案根的路徑、「核准人：<登入者>」唯讀、理由即時字數", async () => {
    backend({ fsm: fsmState() });
    view();
    const dialog = await openFreeze();
    expect(dialog).toHaveTextContent("核准後 FSM 進入 SPEC_FROZEN，規格內容將被摘要綁定；此動作無法由 Console 退回");
    expect(within(dialog).getByTestId("sdd-freeze-docs")).toHaveValue("docs/03_testing/contracts/TCS-Alpha.md");
    expect(within(dialog).getByTestId("sdd-freeze-approver")).toHaveTextContent("核准人：operator");
    expect(within(dialog).getByTestId("sdd-freeze-reason-count")).toHaveTextContent(/^0 \/ 500/);
    await fill(dialog, "  核准凍結  ");
    expect(within(dialog).getByTestId("sdd-freeze-reason-count")).toHaveTextContent(/^4 \/ 500/); // 去前後空白後計算
    expect(within(dialog).queryByRole("textbox", { name: /核准人|approver/i })).toBeNull(); // approver 不是輸入欄
  });

  it("理由必填：空白不得送出（顯示「請填寫核准理由」、沒有任何請求）；含換行、超過 500 字元同樣擋下", async () => {
    const { calls } = backend({ fsm: fsmState() });
    view();
    const dialog = await openFreeze();
    await userEvent.click(within(dialog).getByRole("button", { name: "核准凍結" }));
    expect(await within(dialog).findByText("請填寫核准理由")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);

    const reason = within(dialog).getByTestId("sdd-freeze-reason");
    await userEvent.type(reason, "第一行{Enter}第二行");
    await userEvent.click(within(dialog).getByRole("button", { name: "核准凍結" }));
    expect(await within(dialog).findByText("理由不得含換行或控制字元")).toBeInTheDocument();

    await userEvent.clear(reason);
    await userEvent.click(reason);
    await userEvent.paste("字".repeat(501));
    expect(within(dialog).getByTestId("sdd-freeze-reason-count")).toHaveTextContent(/^501 \/ 500/);
    await userEvent.click(within(dialog).getByRole("button", { name: "核准凍結" }));
    expect(await within(dialog).findByText("理由最多 500 字元（目前 501）")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("docs 格式：絕對路徑、含 ..、重複、空白都不得送出（每項顯示在欄位下）", async () => {
    const { calls } = backend({ fsm: fsmState() });
    view();
    const dialog = await openFreeze();
    await fill(dialog, "核准");
    const docs = within(dialog).getByTestId("sdd-freeze-docs");
    await userEvent.clear(docs);
    await userEvent.type(docs, "/etc/passwd{Enter}../x.md{Enter}docs/a.md{Enter}docs/a.md");
    await userEvent.click(within(dialog).getByRole("button", { name: "核准凍結" }));
    const error = await within(dialog).findByText(/必須是相對專案根的路徑/);
    expect(error).toHaveTextContent("不得含 ..");
    expect(error).toHaveTextContent("有重複的路徑：docs/a.md");
    expect(calls.some((c) => c.method === "POST")).toBe(false);
    await userEvent.clear(docs);
    await userEvent.click(within(dialog).getByRole("button", { name: "核准凍結" }));
    expect(await within(dialog).findByText("請至少填寫一份規格文件（每行一個相對專案根的路徑）")).toBeInTheDocument();
  });

  it("成功：POST 的 body 只有 reason 與 docs（沒有 stage、approver、binding、expectedDigests）；toast「已核准凍結」、對話框關閉、重取專案詳情與 engines/sdd", async () => {
    const { calls } = backend({ fsm: fsmState() }, (c) =>
      c.method === "POST" && c.path === FREEZE ? { data: fsmState({ currentState: "SPEC_FROZEN", frozenStages: [{ stage: "Stage-1", approved_by: "operator" }] }) } : undefined,
    );
    view();
    const dialog = await openFreeze();
    await fill(dialog, "規格已走完 SCG-0～3，核准凍結");
    const enginesBefore = engineCalls(calls).length;
    await userEvent.click(within(dialog).getByRole("button", { name: "核准凍結" }));
    expect(await screen.findByText("已核准凍結")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    const post = calls.find((c) => c.method === "POST" && c.path === FREEZE);
    expect(post?.body).toEqual({ reason: "規格已走完 SCG-0～3，核准凍結", docs: ["docs/03_testing/contracts/TCS-Alpha.md"] });
    await waitFor(() => expect(engineCalls(calls).length).toBeGreaterThan(enginesBefore)); // 成功後 FSM 狀態立即重取（不等 30 秒輪詢）
  });

  it("進階：階段名稱有填才送 stage（去前後空白）；格式不合不得送出", async () => {
    const { calls } = backend({ fsm: fsmState() }, (c) => (c.method === "POST" && c.path === FREEZE ? { data: fsmState({ currentState: "SPEC_FROZEN" }) } : undefined));
    view();
    const dialog = await openFreeze();
    await fill(dialog, "核准");
    await userEvent.click(within(dialog).getByText("進階：階段名稱（選填）"));
    const stage = within(dialog).getByTestId("sdd-freeze-stage");
    await userEvent.type(stage, "階段 一");
    await userEvent.click(within(dialog).getByRole("button", { name: "核准凍結" }));
    expect(await within(dialog).findByText("階段名稱只能含英數字與 . _ -（1～64 字元）")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);
    await userEvent.clear(stage);
    await userEvent.type(stage, " Stage-2 ");
    await userEvent.click(within(dialog).getByRole("button", { name: "核准凍結" }));
    await waitFor(() => expect(calls.some((c) => c.method === "POST")).toBe(true));
    expect(calls.find((c) => c.method === "POST")?.body).toMatchObject({ stage: "Stage-2" });
  });

  it.each([
    ["503 sdd_write_disabled", 503, "sdd_write_disabled", undefined, "SDD 寫入功能未啟用（需管理員設定寫入權杖）"],
    ["409 sdd_fsm_state_conflict", 409, "sdd_fsm_state_conflict", { currentState: "SPEC_FROZEN", expectedState: "HUMAN_PENDING" }, "FSM 目前不在 HUMAN_PENDING（目前：SPEC_FROZEN）"],
    ["409 sdd_fsm_not_found", 409, "sdd_fsm_not_found", { sddProject: "core-fsm" }, "找不到 FSM 專案狀態檔（core-fsm）；請先在專案根的 SDD session 建立"],
    [
      "409 sdd_binding_conflict",
      409,
      "sdd_binding_conflict",
      { cause: "already_bound_elsewhere", sddProject: "core-fsm", holderProjectId: "1a2b3c4d-0000" },
      "同一個專案根下已有另一個專案綁定了這個 FSM 專案",
    ],
    ["409 sdd_spec_digest_changed", 409, "sdd_spec_digest_changed", { pair: "expected_vs_file", doc: "docs/03_testing/contracts/TCS-Alpha.md" }, "規格檔在凍結前已被改動，請重新確認內容"],
  ] as const)("%s：對話框不關閉，顯示契約逐字的白話句子與 traceId", async (_name, status, reason, details, sentence) => {
    backend({ fsm: fsmState() }, (c) =>
      c.method === "POST" && c.path === FREEZE ? failure(status, { message: "後端訊息", reason, details: details as Record<string, unknown> | undefined }) : undefined,
    );
    view();
    const dialog = await openFreeze();
    await fill(dialog, "核准");
    await userEvent.click(within(dialog).getByRole("button", { name: "核准凍結" }));
    const error = await within(dialog).findByTestId("sdd-freeze-error");
    expect(error).toHaveTextContent(sentence);
    expect(error).toHaveTextContent(`traceId：tr-${status}`);
    expect(screen.getByRole("dialog", { name: "核准凍結規格" })).toBeInTheDocument();
    expect(screen.queryByText("已核准凍結")).toBeNull();
  });

  it("422 引擎拒絕此請求：列出 violations 的 field／rule（missing_tcs 附「規格文件須含至少一份 TCS」）", async () => {
    backend({ fsm: fsmState() }, (c) =>
      c.method === "POST" && c.path === FREEZE
        ? failure(422, { message: "引擎拒絕", reason: "引擎拒絕此請求", details: { bridgeReason: "sdd_invalid_argument", violations: [{ field: "docs", rule: "missing_tcs" }] } })
        : undefined,
    );
    view();
    const dialog = await openFreeze();
    await fill(dialog, "核准");
    await userEvent.click(within(dialog).getByRole("button", { name: "核准凍結" }));
    const error = await within(dialog).findByTestId("sdd-freeze-error");
    expect(error).toHaveTextContent("docs／missing_tcs「規格文件須含至少一份 TCS」");
    expect(error).toHaveTextContent("引擎回報：");
  });

  it("後端 400 的欄位錯誤落在對應欄位下（docs、reason）；不在本對話框的欄位（expectedDigests）照原樣列在訊息區", async () => {
    backend({ fsm: fsmState() }, (c) =>
      c.method === "POST" && c.path === FREEZE
        ? failure(400, {
            message: "請求參數錯誤",
            errors: [
              { field: "docs", message: "docs 不含已綁定的規格檔" },
              { field: "expectedDigests", message: "鍵須都在 docs 內" },
            ],
          })
        : undefined,
    );
    view();
    const dialog = await openFreeze();
    await fill(dialog, "核准");
    await userEvent.click(within(dialog).getByRole("button", { name: "核准凍結" }));
    expect(await within(dialog).findByText("docs 不含已綁定的規格檔")).toBeInTheDocument();
    expect(within(dialog).getByTestId("sdd-freeze-error")).toHaveTextContent("expectedDigests：鍵須都在 docs 內");
  });

  it.each(["Esc", "取消鈕"] as const)("以「%s」關閉：焦點回到「核准凍結」鈕（W6 的焦點歸還）", async (how) => {
    backend({ fsm: fsmState() });
    view();
    await screen.findByText("HUMAN_PENDING");
    const trigger = screen.getByTestId("sdd-freeze-button");
    trigger.focus();
    await userEvent.keyboard("{Enter}");
    const dialog = await screen.findByRole("dialog", { name: "核准凍結規格" });
    await waitFor(() => expect(dialog).toContainElement(document.activeElement as HTMLElement));
    if (how === "Esc") await userEvent.keyboard("{Escape}");
    else await userEvent.click(within(dialog).getByRole("button", { name: "取消" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("專案沒有已綁定的規格檔：docs 不預填（由使用者填）", async () => {
    backend({ fsm: fsmState() });
    view(projectDetail({ id: PROJECT_ID, name: "AISDLC Core Platform", executionPath: "/work/core", sddProject: "core-fsm", sddSpecFile: null }));
    const dialog = await openFreeze();
    expect(within(dialog).getByTestId("sdd-freeze-docs")).toHaveValue("");
  });
});
