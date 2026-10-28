/**
 * SysAdminHome（`/sysadmin` 入口頁）的元件測試（TCS-SysAdminBackup-20261027 載具 FH；AC-BK-01-2；R-BK-02）：
 *  - AT-BK-01-2-1：任一角色都看得到「資料庫備份」入口卡（標題、一句說明、最近全備摘要），整張卡是連到 /sysadmin/backup 的連結，入口頁只有這一張卡；
 *  - AT-BK-01-2-3：摘要量不到（失敗、從未執行、cards 為 null、請求失敗）時寫「失敗」「從未執行」「—」並帶原因，任何情況都不顯示「成功」或數字 0；
 *  - AT-BK-01-2-E-1：未登入（anon）與登入狀態水合中（loading）：入口頁與備份頁都不渲染入口卡與任何備份資料，對 /api/v1/sysadmin/ 的請求數為 0。
 * 判定指令：npx vitest run components/domain/sysadmin/SysAdminHome.test.tsx -t "<AT 底線形>"
 */
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { Role } from "@/lib/api/types";
import { cardStatusText } from "@/lib/domain/sysadminBackup";
import { formatDateTime } from "@/lib/format";
import { Providers, failure, makeClient, signIn, stubApi } from "@/tests/helpers/api";
import { BackupView } from "./BackupView";
import { SysAdminHome } from "./SysAdminHome";
import { OVERVIEW_PATH, blockedOverview, makeCards, makeOverview, renderBackup, renderBackupAnon } from "./tests/backup.fixtures";

// 測試環境沒有 App Router：AuthProvider 要的 useRouter 換成替身；Link 換成一般連結
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/sysadmin",
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const card = () => screen.getByTestId("sysadmin-card-backup");
const summary = () => screen.getByTestId("sysadmin-backup-summary");
const text = (el: HTMLElement) => (el.textContent ?? "").replace(/\s+/g, " ").trim();

describe("AT_BK_01_2 入口頁與最近全備摘要", () => {
  it("AT_BK_01_2_1 ADMIN、OPERATOR、VIEWER 皆渲染 sysadmin-card-backup：標題「資料庫備份」、一句說明（非空）、最近全備摘要＝狀態文字「成功」與 formatDateTime(finishedAt)；卡片是連結、href 為 /sysadmin/backup；入口頁只有這一張卡", async () => {
    const finishedAt = "2026-10-26T18:10:00Z";
    for (const role of ["ADMIN", "OPERATOR", "VIEWER"] as const satisfies readonly Role[]) {
      const view = renderBackup(<SysAdminHome />, { role, overview: makeOverview({ cards: makeCards({ full: { status: "succeeded", finishedAt } }) }) });
      await waitFor(() => expect(text(summary())).toBe("成功"));
      expect(card(), role).toHaveAttribute("href", "/sysadmin/backup");
      expect(card().tagName, "整張卡就是連結").toBe("A");
      expect(card().querySelector("h2"), role).toHaveTextContent("資料庫備份");
      const description = card().querySelector("p");
      expect((description?.textContent ?? "").trim().length, `${role} 的一句說明非空`).toBeGreaterThan(0);
      expect(card(), role).toHaveTextContent("最近全備：");
      expect(card(), role).toHaveTextContent(formatDateTime(finishedAt));
      expect(screen.getByTestId("sysadmin-backup-summary-time")).toHaveTextContent(formatDateTime(finishedAt));
      expect(document.querySelectorAll('[data-testid^="sysadmin-card-"]'), `${role}：入口頁只有一張卡`).toHaveLength(1);
      expect(screen.getByTestId("sysadmin-home")).toHaveTextContent("系統管理");
      view.unmount();
    }
  });

  it("AT_BK_01_2_3 全備為 failed：摘要「失敗」（data-tone=danger）；no_run（從未執行）：「從未執行」；cards 為 null（control.reason=export_unreadable）：摘要「—」並帶原因文字；GET 失敗：摘要「—」並帶原因；任何情況都不顯示「成功」或數字 0", async () => {
    const failed = renderBackup(<SysAdminHome />, { overview: makeOverview({ cards: makeCards({ full: { status: "failed", finishedAt: "2026-10-27T18:10:00Z" } }) }) });
    await waitFor(() => expect(text(summary())).toBe("失敗"));
    expect(summary()).toHaveAttribute("data-tone", "danger");
    expect(card().textContent).not.toContain("成功");
    failed.unmount();

    const noRun = renderBackup(<SysAdminHome />, {
      overview: makeOverview({ cards: makeCards({ full: { status: "no_run", trigger: null, startedAt: null, finishedAt: null, durationSeconds: null, lastSuccessAt: null, never: true } }) }),
    });
    await waitFor(() => expect(text(summary())).toBe("從未執行"));
    expect(screen.queryByTestId("sysadmin-backup-summary-time"), "從未執行沒有時間").toBeNull();
    expect(card().textContent).not.toContain("成功");
    expect(card().textContent).not.toMatch(/\b0\b/);
    noRun.unmount();

    const blocked = renderBackup(<SysAdminHome />, { overview: blockedOverview("export_unreadable") });
    await waitFor(() => expect(text(summary())).toBe("—"));
    expect(screen.getByTestId("sysadmin-backup-summary-note")).toHaveTextContent("匯出檔無法讀取");
    expect(card().textContent).not.toContain("成功");
    expect(card().textContent).not.toMatch(/\b0\b/);
    blocked.unmount();

    // 控制面未設定也一樣：「—」加原因
    const unconfigured = renderBackup(<SysAdminHome />, { overview: blockedOverview("not_configured") });
    await waitFor(() => expect(text(summary())).toBe("—"));
    expect(screen.getByTestId("sysadmin-backup-summary-note")).toHaveTextContent("備份控制面未設定");
    unconfigured.unmount();

    // 網路層失敗（fetch 丟例外）
    signIn("VIEWER");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    render(
      <Providers client={makeClient()}>
        <SysAdminHome />
      </Providers>,
    );
    await waitFor(() => expect(text(summary())).toBe("—"));
    expect(screen.getByTestId("sysadmin-backup-summary-note")).toHaveTextContent("備份狀態暫時無法取得");
    expect(card().textContent).not.toContain("成功");
    expect(card().textContent).not.toMatch(/\b0\b/);
  });

  it("HTTP 5xx 失敗：摘要「—」並帶原因，不拿快取或上一次的資料頂替", async () => {
    renderBackup(<SysAdminHome />, { reply: failure(503, { message: "備份控制面目前無法使用", reason: "backup_control_unavailable" }) });
    await waitFor(() => expect(text(summary())).toBe("—"));
    expect(screen.getByTestId("sysadmin-backup-summary-note")).toHaveTextContent("備份狀態暫時無法取得");
  });

  it("控制面離線（runner_offline）時資料照回：摘要照常顯示全備的狀態與時間", async () => {
    renderBackup(<SysAdminHome />, { overview: makeOverview({}, { reason: "runner_offline", heartbeatAgeSeconds: 95 }) });
    await waitFor(() => expect(text(summary())).toBe(cardStatusText("succeeded")));
  });

  it("載入中：摘要寫「載入中…」，不顯示成功也不顯示 0", () => {
    renderBackup(<SysAdminHome />);
    expect(text(summary())).toBe("載入中…");
    expect(card().textContent).not.toContain("成功");
  });
});

describe("AT_BK_01_2_E_1 未登入不渲染入口卡也不發請求", () => {
  it("AT_BK_01_2_E_1 status 為 anon：SysAdminHome 與 BackupView 皆不渲染 sysadmin-card-backup、不渲染任何備份資料；對 /api/v1/sysadmin/ 的請求數為 0", async () => {
    const home = renderBackupAnon(<SysAdminHome />);
    expect(screen.getByTestId("sysadmin-home")).toBeInTheDocument();
    expect(screen.queryByTestId("sysadmin-card-backup")).toBeNull();
    expect(screen.queryByTestId("sysadmin-backup-summary")).toBeNull();
    // 等一下讓任何（不該有的）請求有機會送出
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(home.backupCalls()).toHaveLength(0);
    home.unmount();

    const backup = renderBackupAnon(<BackupView />);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(screen.queryByTestId("sysadmin-card-backup")).toBeNull();
    expect(screen.queryByTestId("bk-cards")).toBeNull();
    expect(screen.queryByTestId("bk-list")).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.queryByTestId("bk-wal-line")).toBeNull();
    expect(backup.backupCalls()).toHaveLength(0);
  });

  it("AT_BK_01_2_E_1 登入狀態尚在水合（loading；伺服器端渲染的第一個畫面）：兩個元件的輸出都沒有入口卡與備份資料，也沒有任何請求", () => {
    const calls = stubApi(() => ({ data: makeOverview() })).calls;
    for (const ui of [<SysAdminHome key="home" />, <BackupView key="view" />]) {
      const html = renderToString(<Providers client={makeClient()}>{ui}</Providers>);
      expect(html).not.toContain("sysadmin-card-backup");
      expect(html).not.toContain("bk-cards");
      expect(html).not.toContain("bk-list");
      expect(html).not.toContain("<table");
    }
    expect(calls.filter((c) => c.path === OVERVIEW_PATH || c.path.startsWith("/api/v1/sysadmin/"))).toHaveLength(0);
  });
});
