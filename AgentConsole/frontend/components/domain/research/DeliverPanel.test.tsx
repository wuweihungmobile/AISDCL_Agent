/**
 * 步驟 5 交付面板（TCS-ResearchToPRD-P2-20261107 AT-962-21-2；AC-R2P-20-1）：追溯表、發布動作列、已建立交付清單、最近對帳 delivery 項；未授權角色沒有寫入控件。
 * 判定指令：npx vitest run components/domain/research/DeliverPanel.test.tsx -t AT_962_21_2
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { qk } from "@/lib/api/queries";
import type { ResearchDelivery, ResearchDeliveryOverview, ResearchReconcileResult, ResearchTraceability, Role } from "@/lib/api/types";
import { READONLY_TITLE } from "@/lib/domain/research";
import { R3, sha } from "@/tests/fixtures/research/ids";
import { DELIVERY_OVERVIEW, TRACEABILITY } from "@/tests/fixtures/research/p2";
import { detailVariant } from "@/tests/fixtures/research/projects";
import { failure, renderResearch, stubResearchApi } from "@/tests/helpers/research";
import { DeliverPanel } from "./DeliverPanel";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(""),
}));

const TAG_ROW: ResearchDelivery = {
  kind: "RELEASE_TAG",
  ref: "v1.2.3",
  commitSha: "0123456789abcdef0123456789abcdef01234567",
  url: null,
  rtmReportRef: "03_execution/traceability_matrix.json@sha256:abc",
  fsmStateAfter: "RELEASE_READY",
  status: "CREATED",
  createdBy: "admin",
  createdAt: "2026-11-07T10:00:00+08:00",
  snapshotSha256: sha("a"),
};
const PR_ROW: ResearchDelivery = {
  ...TAG_ROW,
  kind: "PULL_REQUEST",
  ref: "42",
  commitSha: "fedcba9876543210fedcba9876543210fedcba98",
  url: "https://github.com/acme/alpha/pull/42",
  snapshotSha256: null,
};
const OVERVIEW: ResearchDeliveryOverview = { ...DELIVERY_OVERVIEW, deliveries: [TAG_ROW, PR_ROW], snapshot: { relPath: "03_execution/traceability_matrix.json", sha256: sha("a") } };
const RECONCILE = (status: "ok" | "drift"): ResearchReconcileResult => ({
  consistent: status === "ok",
  checks: [
    {
      name: "delivery",
      status,
      ...(status === "drift" ? { drift: [{ kind: "sha256_mismatch", path: "03_execution/traceability_matrix.json", expectedSha256: sha("a"), actualSha256: sha("b") }] } : {}),
    },
  ],
});

function mount(role: Role = "ADMIN", opts: { delivery?: ResearchDeliveryOverview; traceability?: ResearchTraceability; completed?: boolean; overrides?: Parameters<typeof stubResearchApi>[0] } = {}) {
  const stub = stubResearchApi({ delivery: opts.delivery ?? OVERVIEW, traceability: opts.traceability ?? TRACEABILITY, ...opts.overrides });
  const view = renderResearch(<DeliverPanel researchId={R3} project={detailVariant("frozen")} completed={opts.completed ?? false} />, role);
  return { ...stub, ...view };
}

describe("AT_962_21_2 DeliverPanel 整體呈現", () => {
  it("AT_962_21_2 含追溯表、發布動作列（Tag 鈕、PR、開啟本地專案）、已建立交付清單（Tag、PR 各一列）、最近對帳 delivery 項", async () => {
    const { client } = mount("ADMIN");
    const panel = await screen.findByTestId("deliver-panel");
    expect(panel).toHaveAttribute("data-research-id", R3);
    await within(panel).findByTestId("traceability-table");
    expect(within(panel).getAllByTestId("trace-row")).toHaveLength(3);
    expect(within(panel).getByTestId("release-actions")).toBeInTheDocument();
    expect(within(panel).getByTestId("tag-create")).toBeInTheDocument();
    expect(within(panel).getByTestId("pr-block")).toBeInTheDocument();
    expect(within(panel).getByTestId("open-local")).toBeInTheDocument();

    const records = within(panel).getAllByTestId("delivery-record");
    expect(records.map((r) => r.getAttribute("data-kind"))).toEqual(["RELEASE_TAG", "PULL_REQUEST"]);
    expect(records[0]).toHaveTextContent("v1.2.3");
    expect(records[0]).toHaveTextContent("提交 0123456789ab"); // 前 12 碼
    expect(records[0]).toHaveTextContent("2026-11-07T10:00:00+08:00");
    expect(records[1]).toHaveTextContent("42");
    expect(within(records[1]).getByRole("link", { name: "https://github.com/acme/alpha/pull/42" })).toHaveAttribute("href", "https://github.com/acme/alpha/pull/42");

    // 沒有對帳結果：如實說尚無
    expect(within(panel).getByTestId("deliver-reconcile")).toHaveTextContent("尚無對帳結果");
    act(() => client.setQueryData(qk.researchReconcile(R3), RECONCILE("ok")));
    await waitFor(() => expect(within(panel).getByTestId("deliver-reconcile")).toHaveTextContent("最近對帳「交付」：一致"));
  });

  it("AT_962_21_2 對帳 delivery 漂移：只在這裡顯示一行文字，不另造橫幅、沒有修正鈕（橫幅只有工作區那一個）", async () => {
    const { client } = mount("ADMIN");
    const panel = await screen.findByTestId("deliver-panel");
    await within(panel).findByTestId("traceability-table");
    act(() => client.setQueryData(qk.researchReconcile(R3), RECONCILE("drift")));
    await waitFor(() => expect(within(panel).getByTestId("deliver-reconcile")).toHaveAttribute("data-status", "drift"));
    expect(within(panel).getByTestId("deliver-reconcile")).toHaveTextContent("不一致");
    expect(screen.queryByTestId("drift-banner")).toBeNull();
    expect(within(panel).queryByRole("alert")).toBeNull();
    expect(within(panel).queryByRole("button", { name: /修正|同步|重新對帳/ })).toBeNull();
  });

  it("AT_962_21_2 沒有交付紀錄：顯示「還沒有交付紀錄」", async () => {
    mount("ADMIN", { delivery: DELIVERY_OVERVIEW });
    expect(await screen.findByTestId("delivery-records-empty")).toHaveTextContent("還沒有交付紀錄");
  });

  it("AT_962_21_2 VIEWER：沒有任何可用的寫入控件——每個按鈕都停用且 title 逐字為「權限不足（唯讀角色）」；沒有 PR 建立鈕、沒有複製鈕", async () => {
    mount("VIEWER", { delivery: DELIVERY_OVERVIEW });
    const panel = await screen.findByTestId("deliver-panel");
    await within(panel).findByTestId("traceability-table");
    expect(within(panel).queryByTestId("pr-create")).toBeNull();
    expect(within(panel).queryByTestId("project-root-copy")).toBeNull();
    const buttons = within(panel).getAllByRole("button");
    expect(buttons.length).toBeGreaterThanOrEqual(1);
    for (const button of buttons) {
      expect(button, `「${button.textContent}」`).toBeDisabled();
      expect(button).toHaveAttribute("title", READONLY_TITLE);
    }
  });

  it("AT_962_21_2 OPERATOR：Tag 鈕停用（僅 ADMIN）、沒有 PR 建立鈕（顯示尚未建立與原因）；ADMIN 且條件齊備才看得到可按的建立 PR", async () => {
    const operator = mount("OPERATOR", { delivery: DELIVERY_OVERVIEW });
    const panel = await screen.findByTestId("deliver-panel");
    await within(panel).findByTestId("traceability-table");
    expect(within(panel).getByTestId("tag-create")).toBeDisabled();
    expect(within(panel).queryByTestId("pr-create")).toBeNull();
    expect(within(panel).getByTestId("pr-none")).toHaveTextContent("尚未建立");
    operator.unmount();
    mount("ADMIN", { delivery: DELIVERY_OVERVIEW });
    expect(await screen.findByTestId("pr-create")).toBeEnabled();
  });

  it("AT_962_21_2 已交付（流程相態 DELIVERED、有 Tag 列）：Tag 鈕顯示已建立並停用", async () => {
    const base = detailVariant("frozen");
    const delivered = { ...base, flow: { ...base.flow, effective: { ...base.flow.effective, phase: "DELIVERED", status: "COMPLETED" as const } } };
    mount("ADMIN", { overrides: { details: { [R3]: delivered } } });
    await screen.findByTestId("traceability-table");
    await waitFor(() => expect(screen.getByTestId("tag-create")).toHaveTextContent("已建立 v1.2.3"));
    expect(screen.getByTestId("tag-create")).toBeDisabled();
  });

  it("AT_962_21_2 completed（已完成步驟的唯讀檢視）：Tag 鈕停用並說明", async () => {
    mount("ADMIN", {
      completed: true,
      delivery: { ...DELIVERY_OVERVIEW, preconditions: { ...DELIVERY_OVERVIEW.preconditions, releaseReady: true } },
      traceability: { ...TRACEABILITY, totals: { acTotal: 3, covered: 3, uncovered: 0, frTotal: 2 }, rows: TRACEABILITY.rows.map((r) => ({ ...r, unitStatus: "PASS" as const })) },
    });
    const tag = await screen.findByTestId("tag-create");
    expect(tag).toBeDisabled();
    expect(screen.getByTestId("tag-block")).toHaveTextContent("這一步已完成，唯讀");
  });

  it("AT_962_21_2 追溯表載入失敗：顯示錯誤態與重試（不是空白），重試會重抓；仍沒有 Tag 鈕", async () => {
    let fail = true;
    const { calls } = mount("ADMIN", {
      overrides: {
        overrides: (call) =>
          call.method === "GET" && /\/delivery\/traceability$/.test(call.path) && fail ? failure(409, { reason: "fsm_state_conflict", details: { unmet: ["prd_not_frozen"] } }) : undefined,
      },
    });
    const panel = await screen.findByTestId("deliver-panel");
    expect(await within(panel).findByText("無法載入交付資料")).toBeInTheDocument();
    expect(within(panel).queryByTestId("tag-create")).toBeNull();
    fail = false;
    const before = calls.filter((c) => /\/delivery\/traceability$/.test(c.path)).length;
    await act(async () => within(panel).getByRole("button", { name: "重試" }).click());
    await within(panel).findByTestId("traceability-table");
    expect(calls.filter((c) => /\/delivery\/traceability$/.test(c.path)).length).toBeGreaterThan(before);
  });

  it("AT_962_21_2 整個面板沒有通往執行中心或監控中心的字樣或連結（P0 反向釘）", async () => {
    mount("ADMIN", { delivery: { ...OVERVIEW, containerMode: true } });
    const panel = await screen.findByTestId("deliver-panel");
    await within(panel).findByTestId("traceability-table");
    expect(panel.textContent).not.toMatch(/ResearchBackLink|開啟執行中心|開啟監控中心|執行中心|監控中心/);
    for (const link of within(panel).queryAllByRole("link")) expect(link.getAttribute("href") ?? "").not.toMatch(/\/execute|\/monitor/);
  });
});
