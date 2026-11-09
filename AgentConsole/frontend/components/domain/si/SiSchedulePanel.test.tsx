/**
 * 自動演化排程面板與橫幅欄位組的元件測試（TCS-SelfImprovingSchedule：AT-964-1-1／1-2／1-E-3、5-1／5-2／5-3、6-1；W-S1、W-S5、W-S6）。
 * 為什麼重要：這組欄位是掌舵者判斷「排程有沒有在跑」的唯一畫面，Console 又看不到主機上的 OS 排程任務——所以量不到必須說量不到（不是無、否或綠燈），
 * `armed` 絕不能被讀成已武裝，逾期只能說「逾期未巡邏」；非 ADMIN 一個控件都不能有。資料來自 tests/helpers/si.tsx 的 fetch 替身（狀態 A 加 `sched()`），
 * 以真 Providers 與真 AuthProvider 渲染整頁，橫幅與面板各取自己的 testid 容器逐字比對。
 */
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ADMIN_UI, DROP, OPERATOR_UI, VIEWER_UI, fixtureWithStatus, renderSi, sched, statusItem } from "@/tests/helpers/si";

// 測試環境沒有 App Router：AuthProvider 要的 useRouter 換成穩定的替身
const router = vi.hoisted(() => ({ push: () => undefined, replace: () => undefined, back: () => undefined }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/self-improving",
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));
vi.setConfig({ testTimeout: 30_000 });

type Ui = typeof ADMIN_UI | typeof VIEWER_UI | typeof OPERATOR_UI;
const mount = (schedule: unknown, ui: Ui = ADMIN_UI) => renderSi({ ...ui, fixture: fixtureWithStatus(statusItem({ schedule })) });
const fields = (scope: "banner" | "panel") => screen.findByTestId(`si-schedule-fields-${scope}`);
const value = (container: HTMLElement, scope: "banner" | "panel", key: string) => within(container).getByTestId(`si-schedule-${scope}-${key}`).textContent ?? "";

describe("AT_964_1_1 完整 schedule 的具名欄位組（橫幅與面板逐字相同）", () => {
  it("AT_964_1_1 啟用、週期與換算、最近設定、本格起訖、已執行、最近略過、逾期、武裝逐欄顯示；橫幅與面板的欄位組文字逐字相同（同一個 scheduleFields）", async () => {
    const s = sched({ lastSkip: { at: "2026-11-09T11:00:00+08:00", reason: "blackout", detail: "黑窗中" }, ranThisCell: true });
    mount(s);
    const banner = await fields("banner");
    const panel = await fields("panel");
    for (const [scope, root] of [
      ["banner", banner],
      ["panel", panel],
    ] as const) {
      expect(value(root, scope, "enabled")).toBe("是");
      expect(value(root, scope, "period")).toContain("1440");
      expect(value(root, scope, "period")).toContain("≈1 天");
      const lastSet = s.lastSet as { at: string; by: string; carrier: string };
      for (const part of [lastSet.at, lastSet.by, lastSet.carrier]) expect(value(root, scope, "lastSet")).toContain(part);
      expect(value(root, scope, "cell")).toContain(s.cellStart as string);
      expect(value(root, scope, "cell")).toContain(s.cellEnd as string);
      expect(value(root, scope, "ranThisCell")).toBe("是");
      for (const part of ["2026-11-09T11:00:00+08:00", "blackout", "黑窗中"]) expect(value(root, scope, "lastSkip")).toContain(part);
      expect(value(root, scope, "overdue")).toBe("否");
      expect(value(root, scope, "armed")).toBe("量不到：Console 看不到主機上的排程任務");
    }
    expect(banner.textContent, "兩處同一個欄位組、內容逐字相同").toBe(panel.textContent);
    // 每個欄位各有一個具名標籤
    for (const label of ["啟用", "週期（分鐘）", "最近一次設定", "本格起訖", "本格已執行", "本格最近一次略過", "逾期", "主機排程任務是否武裝"])
      expect(within(banner).getByText(label)).toBeInTheDocument();
  });
});

describe("AT_964_1_2 armed 恆為量不到文案", () => {
  it("AT_964_1_2 armed 依序為量不到字串、present 為真的物件、present 為假的物件、布林真：四次 armed 欄文字皆為固定文案，畫面任一處都不含已武裝與未武裝字樣", async () => {
    const armedValues: unknown[] = [
      "NOT-EVALUABLE：export-reads-no-home",
      { task: "AutoSDD_Sentinel_x", present: true, credential: "x" },
      { task: "AutoSDD_Sentinel_x", present: false, credential: "y" },
      true,
    ];
    for (const armed of armedValues) {
      const view = mount(sched({ armed }));
      const banner = await fields("banner");
      const panel = await fields("panel");
      expect(value(banner, "banner", "armed"), JSON.stringify(armed)).toBe("量不到：Console 看不到主機上的排程任務");
      expect(value(panel, "panel", "armed"), JSON.stringify(armed)).toBe("量不到：Console 看不到主機上的排程任務");
      expect(document.body.textContent ?? "", JSON.stringify(armed)).not.toMatch(/已武裝|未武裝/);
      view.unmount();
    }
  });
});

describe("AT_964_1_E_3 lastSkip.detail 含標記字樣時以純文字呈現", () => {
  it("AT_964_1_E_3 detail 含 img 與 script 字樣：畫面以文字顯示原文、容器內查無 img 與 script 元素；未知 reason 原樣顯示", async () => {
    const detail = "<img src=x onerror=alert(1)> 與 <script>alert(2)</script>";
    const view = mount(sched({ lastSkip: { at: "2026-11-09T11:00:00+08:00", reason: "weird-reason", detail } }));
    const banner = await fields("banner");
    const panel = await fields("panel");
    for (const [scope, root] of [
      ["banner", banner],
      ["panel", panel],
    ] as const) {
      expect(value(root, scope, "lastSkip")).toContain(detail);
      expect(value(root, scope, "lastSkip")).toContain("weird-reason");
    }
    expect(view.container.querySelector("img"), "不得產生 img 元素").toBeNull();
    expect(view.container.querySelector("script"), "不得產生 script 元素").toBeNull();
  });
});

describe("AT_964_5_1 overdue 為真：警示文案逐字含主機現查指令", () => {
  it("AT_964_5_1 橫幅與面板各有一個警示，文字含 逾期未巡邏：請在主機執行 python tools/selfimproving.py sched show，且帶 alert 角色", async () => {
    mount(sched({ overdue: true }));
    const banner = await fields("banner");
    const panel = await fields("panel");
    for (const [scope, root] of [
      ["banner", banner],
      ["panel", panel],
    ] as const) {
      const alerts = within(root).getAllByRole("alert");
      expect(alerts, `${scope} 恰一個警示`).toHaveLength(1);
      expect(alerts[0].textContent).toContain("逾期未巡邏：請在主機執行 python tools/selfimproving.py sched show");
      expect(value(root, scope, "overdue")).toBe("是");
    }
  });
});

describe("AT_964_5_2 overdue 為 null 或缺席顯示量不到與原因；為 false 不顯示警示", () => {
  it.each([
    ["null", null, true],
    ["缺席", DROP, true],
    ["false", false, false],
  ] as Array<[string, unknown, boolean]>)("AT_964_5_2 overdue 為 %s", async (_name, overdue, unknown) => {
    mount(sched({ overdue }));
    for (const scope of ["banner", "panel"] as const) {
      const root = await fields(scope);
      const text = value(root, scope, "overdue");
      if (unknown) {
        expect(text).toContain("量不到");
        expect(text).toContain("事件帳本");
        expect(text).not.toMatch(/沒有逾期|未逾期/);
      } else {
        expect(text).toBe("否");
      }
      expect(within(root).queryAllByRole("alert"), `${scope} 的警示`).toHaveLength(0);
    }
  });
});

describe("AT_964_5_3 lastSkip 非 null：顯示時間、原因、細節；顯示略過而非逾期", () => {
  it("AT_964_5_3 略過區顯示 at、blackout 與細節，無逾期警示；七個合法 reason 值逐一代入皆原樣顯示", async () => {
    const at = "2026-11-09T11:00:00+08:00";
    const view = mount(sched({ overdue: false, lastSkip: { at, reason: "blackout", detail: "d-夾具" } }));
    const banner = await fields("banner");
    for (const part of [at, "blackout", "d-夾具"]) expect(value(banner, "banner", "lastSkip")).toContain(part);
    expect(within(banner).queryAllByRole("alert")).toHaveLength(0);
    view.unmount();
    for (const reason of ["disabled", "blackout", "quota-band", "other-driver", "dirty-tree", "run-open", "spawn-failed"]) {
      const v = mount(sched({ lastSkip: { at, reason, detail: `細節-${reason}` } }));
      const root = await fields("panel");
      expect(value(root, "panel", "lastSkip"), reason).toContain(`｜${reason}｜`);
      expect(value(root, "panel", "lastSkip"), reason).toContain(`細節-${reason}`);
      v.unmount();
    }
  });
});

describe("AT_964_6_1 Viewer 與 Operator：零控件、零 POST、唯讀欄位組仍顯示", () => {
  it.each([
    ["VIEWER", VIEWER_UI],
    ["OPERATOR", OPERATOR_UI],
  ] as Array<[string, Ui]>)("AT_964_6_1 %s：查無面板與三個控件，橫幅的排程欄位組仍顯示；點重新整理後 POST 請求數為 0", async (_name, ui) => {
    const user = userEvent.setup();
    const view = mount(sched({ overdue: true }), ui);
    const banner = await fields("banner");
    expect(value(banner, "banner", "enabled")).toBe("是");
    expect(screen.queryByTestId("si-schedule-panel")).toBeNull();
    for (const id of ["si-schedule-toggle-open", "si-schedule-period-open", "si-run-request-open"]) expect(screen.queryByTestId(id), id).toBeNull();
    expect(screen.queryByRole("button", { name: /立即啟動|啟用排程|停用排程|修改週期/ })).toBeNull();
    expect(screen.queryByRole("checkbox")).toBeNull();
    await user.click(await screen.findByTestId("si-refresh"));
    expect(view.stub.calls.filter((c) => c.method === "POST")).toHaveLength(0);
    expect(
      view.stub.calls.filter((c) => c.path.endsWith("/console-writes")),
      "非 ADMIN 零對帳請求",
    ).toHaveLength(0);
  });
});
