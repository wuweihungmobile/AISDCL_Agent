/**
 * 發布動作（TCS-ResearchToPRD-P2-20261107 AT-962-21-3、21-6、21-E-1、21-E-4；AC-R2P-20-2、20-3、20-5；D-148 FE-3；D-150 #1）。
 * 判定指令：npx vitest run components/domain/research/ReleaseActions.test.tsx -t "<AT 底線形>"
 */
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ResearchDelivery, ResearchDeliveryOverview, ResearchTraceability, Role } from "@/lib/api/types";
import { BUILD_DISABLED_TEXT, READONLY_TITLE, TAG_ADMIN_ONLY_TEXT } from "@/lib/domain/research";
import { R3, sha } from "@/tests/fixtures/research/ids";
import { DELIVERY_OVERVIEW, TRACEABILITY } from "@/tests/fixtures/research/p2";
import { renderResearch, stubResearchApi, writeCalls } from "@/tests/helpers/research";
import { ReleaseActions } from "./ReleaseActions";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(""),
}));

afterEach(() => {
  vi.restoreAllMocks();
});

const ALL_PASS: ResearchTraceability = {
  ...TRACEABILITY,
  rows: TRACEABILITY.rows.map((r) => ({ ...r, unitStatus: "PASS" as const })),
  totals: { acTotal: 3, covered: 3, uncovered: 0, frTotal: 2 },
  rtm: { runId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", fullyCovered: true, acPct: 100, advisory: true },
};
const READY: ResearchDeliveryOverview = { ...DELIVERY_OVERVIEW, preconditions: { ...DELIVERY_OVERVIEW.preconditions, releaseReady: true, rtmFull: true } };
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
  snapshotSha256: sha("snap"),
};

type Props = { overview?: ResearchDeliveryOverview; traceability?: ResearchTraceability; fsmRelease?: boolean; scrOpen?: boolean; completed?: boolean };
function mount(role: Role, props: Props = {}) {
  const stub = stubResearchApi();
  const view = renderResearch(
    <ReleaseActions
      researchId={R3}
      overview={props.overview ?? READY}
      traceability={props.traceability ?? ALL_PASS}
      fsmRelease={props.fsmRelease ?? false}
      scrOpen={props.scrOpen ?? false}
      completed={props.completed}
    />,
    role,
  );
  return { ...stub, ...view };
}
const tagBtn = () => screen.getByTestId("tag-create") as HTMLButtonElement;

describe("AT_962_21_3 建立 Tag 鈕停用規則（六種組合）", () => {
  it("AT_962_21_3 全部條件成立（ADMIN、RELEASE_READY、未覆蓋 0、無 SCR）才啟用；啟用時沒有停用原因區塊", () => {
    mount("ADMIN");
    expect(tagBtn()).toBeEnabled();
    expect(tagBtn()).not.toHaveAttribute("title");
    expect(screen.queryByTestId("tag-block")).toBeNull();
  });

  it("AT_962_21_3 未覆蓋大於 0：停用，原因逐 AC 列出（含狀態文字）", () => {
    mount("ADMIN", { traceability: TRACEABILITY });
    expect(tagBtn()).toBeDisabled();
    const list = screen.getByTestId("tag-uncovered-list");
    expect(
      within(list)
        .getAllByRole("listitem")
        .map((li) => li.getAttribute("data-ac")),
    ).toEqual(["AC-R2P-01-2", "AC-R2P-02-1"]);
    expect(list).toHaveTextContent("AC-R2P-01-2（失敗）");
    expect(list).toHaveTextContent("AC-R2P-02-1（無覆蓋任務）");
    expect(screen.getByTestId("tag-block")).toHaveTextContent("仍有 2 個未覆蓋的驗收條件");
  });

  it("AT_962_21_3 非 RELEASE_READY：停用並說明", () => {
    mount("ADMIN", { overview: DELIVERY_OVERVIEW });
    expect(tagBtn()).toBeDisabled();
    expect(screen.getByTestId("tag-block")).toHaveTextContent("尚未達 RELEASE_READY");
  });

  it("AT_962_21_3 SCR_OPEN：停用，文案取登記處 BUILD_DISABLED_TEXT.scrOpen", () => {
    mount("ADMIN", { scrOpen: true });
    expect(tagBtn()).toBeDisabled();
    expect(tagBtn()).toHaveAttribute("title", BUILD_DISABLED_TEXT.scrOpen);
    expect(screen.getByTestId("tag-block")).toHaveTextContent(BUILD_DISABLED_TEXT.scrOpen);
  });

  it("AT_962_21_3 非 ADMIN：OPERATOR 的 title 為「僅 ADMIN」說明、VIEWER 的 title 逐字為 READONLY_TITLE；兩者都停用", () => {
    const operator = mount("OPERATOR");
    expect(tagBtn()).toBeDisabled();
    expect(tagBtn()).toHaveAttribute("title", TAG_ADMIN_ONLY_TEXT);
    expect(TAG_ADMIN_ONLY_TEXT).toContain("權限不足");
    operator.unmount();
    mount("VIEWER");
    expect(tagBtn()).toBeDisabled();
    expect(tagBtn()).toHaveAttribute("title", READONLY_TITLE);
  });

  it("AT_962_21_3 六種組合表驅動：只有全部成立才啟用", () => {
    const cases: Array<{ name: string; role: Role; props: Props; enabled: boolean }> = [
      { name: "全成立", role: "ADMIN", props: {}, enabled: true },
      { name: "未覆蓋", role: "ADMIN", props: { traceability: TRACEABILITY }, enabled: false },
      { name: "非 RELEASE_READY", role: "ADMIN", props: { overview: DELIVERY_OVERVIEW }, enabled: false },
      { name: "SCR_OPEN", role: "ADMIN", props: { scrOpen: true }, enabled: false },
      { name: "OPERATOR", role: "OPERATOR", props: {}, enabled: false },
      { name: "已完成步驟的唯讀檢視", role: "ADMIN", props: { completed: true }, enabled: false },
    ];
    for (const c of cases) {
      const view = mount(c.role, c.props);
      expect(tagBtn().disabled, c.name).toBe(!c.enabled);
      view.unmount();
    }
  });

  it("AT_962_21_3 啟用時點擊開啟 Tag 確認框；停用時點擊不開", async () => {
    const enabled = mount("ADMIN");
    fireEvent.click(tagBtn());
    expect(await screen.findByTestId("tag-dialog")).toBeInTheDocument();
    enabled.unmount();
    mount("ADMIN", { scrOpen: true });
    fireEvent.click(tagBtn());
    expect(screen.queryByTestId("tag-dialog")).toBeNull();
  });

  it("AT_962_21_3 本元件沒有任何通往執行中心或監控中心的字樣或連結（P0 反向釘：步驟 5 不得出現）", () => {
    mount("ADMIN", { traceability: TRACEABILITY, scrOpen: true, overview: DELIVERY_OVERVIEW });
    const root = screen.getByTestId("release-actions");
    expect(root.textContent).not.toMatch(/執行中心|監控中心|ResearchBackLink/);
    expect(within(root).queryAllByRole("link")).toHaveLength(0);
  });
});

describe("AT_962_21_E_1 RTM 100% 但非 RELEASE_READY：仍停用", () => {
  it("AT_962_21_E_1 RTM 彙總 100%、全覆蓋、未覆蓋 0，但狀態機未達 RELEASE_READY：Tag 鈕停用，原因含「尚未達 RELEASE_READY」", () => {
    const notReady: ResearchDeliveryOverview = { ...DELIVERY_OVERVIEW, preconditions: { ...DELIVERY_OVERVIEW.preconditions, releaseReady: false, rtmFull: true } };
    expect(ALL_PASS.rtm?.acPct).toBe(100);
    mount("ADMIN", { overview: notReady });
    expect(tagBtn()).toBeDisabled();
    expect(screen.getByTestId("tag-block")).toHaveTextContent("尚未達 RELEASE_READY");
    expect(tagBtn().getAttribute("title")).toContain("尚未達 RELEASE_READY");
  });
});

describe("AT_962_21_E_4 已交付：Tag 鈕顯示已建立並停用，不可重複送出", () => {
  const delivered: ResearchDeliveryOverview = { ...READY, deliveries: [TAG_ROW] };

  it("AT_962_21_E_4 FSM 為 RELEASE 且有 RELEASE_TAG 列：顯示「已建立 v1.2.3」、鈕停用、點擊不開框、送出請求 0", () => {
    const { calls } = mount("ADMIN", { overview: delivered, fsmRelease: true });
    expect(tagBtn()).toBeDisabled();
    expect(tagBtn()).toHaveTextContent("已建立 v1.2.3");
    expect(screen.getByTestId("tag-delivered")).toBeInTheDocument();
    expect(screen.queryByTestId("tag-block")).toBeNull();
    fireEvent.click(tagBtn());
    expect(screen.queryByTestId("tag-dialog")).toBeNull();
    expect(writeCalls(calls)).toHaveLength(0);
  });

  it("AT_962_21_E_4 有 Tag 列但 FSM 還停在 RELEASE_READY（fsm_release 步驟失敗後重送的續跑情境）：不算已交付，仍可由 ADMIN 重送同一動作", () => {
    mount("ADMIN", { overview: delivered, fsmRelease: false });
    expect(tagBtn()).toBeEnabled();
    expect(tagBtn()).toHaveTextContent("建立 Tag");
  });

  it("AT_962_21_E_4 FAILED 的 Tag 列不算已建立", () => {
    mount("ADMIN", { overview: { ...READY, deliveries: [{ ...TAG_ROW, status: "FAILED" }] }, fsmRelease: true });
    expect(tagBtn()).toHaveTextContent("建立 Tag");
  });
});

describe("AT_962_21_6 開啟本地專案：顯示專案根路徑與複製鈕；容器模式標示；不假裝可開啟", () => {
  function stubClipboard() {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    return writeText;
  }

  it("AT_962_21_6 OPERATOR、containerMode=false：顯示 projectRoot 與複製鈕（CopyCommand）；點複製寫入剪貼簿；無容器內路徑加註", async () => {
    const writeText = stubClipboard();
    const open = vi.spyOn(window, "open");
    mount("OPERATOR");
    const copy = screen.getByTestId("project-root-copy");
    expect(copy).toHaveTextContent("/work/alpha");
    expect(screen.queryByTestId("project-root-container")).toBeNull();
    fireEvent.click(within(copy).getByRole("button", { name: /複製/ }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith("/work/alpha"));
    expect(open).not.toHaveBeenCalled();
  });

  it("AT_962_21_6 containerMode=true：加註「此為容器內路徑」", () => {
    mount("ADMIN", { overview: { ...READY, containerMode: true, projectRoot: "/workspace/alpha" } });
    expect(screen.getByTestId("project-root-container")).toHaveTextContent("此為容器內路徑");
    expect(screen.getByTestId("project-root-copy")).toHaveTextContent("/workspace/alpha");
  });

  it("AT_962_21_6 DOM 無 file:// 連結、沒有任何 <a>、不呼叫 window.open；說明系統不直接開啟", () => {
    const open = vi.spyOn(window, "open");
    mount("ADMIN", { overview: { ...READY, projectRoot: "C:\\work\\alpha" } });
    const root = screen.getByTestId("open-local");
    expect(root.querySelector('a, [href^="file:"], [src^="file:"]')).toBeNull();
    expect(root.innerHTML).not.toContain("file://");
    expect(screen.getByTestId("open-local-note")).toHaveTextContent("系統不會直接開啟資料夾");
    expect(open).not.toHaveBeenCalled();
  });

  it("AT_962_21_6 VIEWER（D-150 #1）：不渲染複製鈕（project-root-copy 不存在），只顯示可選取的路徑文字；整個「開啟本地專案」區沒有按鈕", () => {
    mount("VIEWER");
    expect(screen.queryByTestId("project-root-copy")).toBeNull();
    expect(screen.getByTestId("project-root")).toHaveTextContent("/work/alpha");
    expect(within(screen.getByTestId("open-local")).queryAllByRole("button")).toHaveLength(0);
  });

  it("AT_962_21_6 尚無專案根路徑（projectRoot 為 null）：顯示尚未分流說明、沒有複製鈕", () => {
    mount("ADMIN", { overview: { ...READY, projectRoot: null } });
    expect(screen.getByTestId("project-root-none")).toHaveTextContent("尚無專案根路徑");
    expect(screen.queryByTestId("project-root-copy")).toBeNull();
  });
});
