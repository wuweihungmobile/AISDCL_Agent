/**
 * BackupView 的元件測試（TCS-SysAdminBackup-20261027 載具 FV；FR-BK-02～05、08 的前端畫面 AT；R-BK-04～09、R-BK-10～13、R-BK-15～16、R-BK-22～26、R-BK-43～44）：
 * 整頁（最近狀態卡、WAL 歸檔單行、資料更新時間、離線橫幅、提示條、三個分頁）對 backup.fixtures.ts 的假後端（API 形的 JSON）渲染。
 * 畫面的 DOM 契約（data-testid）見 TCS §5.3：bk-page／bk-reason-panel／bk-banner-offline／bk-stale-mark／bk-wal-line、bk-cards／bk-card-<job>／bk-badge-<job>／bk-last-success-<job>／
 * bk-latest-<job>／bk-overdue-<job>／bk-tail-<job>、bk-list／bk-list-note／bk-list-empty／bk-row-<label>／bk-result-<label>／bk-repo-<n>／bk-repo-status-<n>／bk-repo-badge-<n>、
 * bk-sched-<job>／bk-sched-fixed-wal／bk-retention、bk-restore-steps／bk-restore-checks／bk-no-restore-note／bk-coverage／bk-coverage-row-<volume>。
 * 判定指令：npx vitest run components/domain/sysadmin/BackupView.test.tsx -t "<AT 底線形>"
 */
import type { ReactNode } from "react";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { BackupCard, BackupOverview, BackupRepo, Role } from "@/lib/api/types";
import { formatDuration } from "@/lib/domain/metrics";
import { CHECKS_POWERSHELL_NOTE, COVERAGE_CATEGORY_LABEL, KEY_LOSS_NOTE, NO_RESTORE_BUTTON_NOTE, RESTORE_CHECKS, RESTORE_STEPS, REPO_STATUS_ZH, VOLUME_COVERAGE } from "@/lib/domain/sysadminBackup";
import { formatBytes, formatClock, formatDateTime } from "@/lib/format";
import { failure } from "@/tests/helpers/api";
import { BackupSchedule } from "./BackupSchedule";
import { BackupView } from "./BackupView";
import { BACKUPS, EXPORT_AT, REPO2_EXTERNAL, REPO2_LOCAL, SCHEDULE, blockedOverview, clone, emptyOverview, makeCards, makeOverview, renderBackup } from "./tests/backup.fixtures";

// 測試環境沒有 App Router：AuthProvider 要的 useRouter 換成替身；Link 換成一般連結
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/sysadmin/backup",
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

// ── 小工具 ────────────────────────────────────────────────────────────────────

const text = (el: HTMLElement | null | undefined): string => (el?.textContent ?? "").replace(/\s+/g, " ").trim();
const testId = (id: string) => screen.getByTestId(id);
const rowLabels = () => Array.from(document.querySelectorAll<HTMLElement>('[data-testid^="bk-row-"]')).map((el) => (el.dataset.testid as string).replace("bk-row-", ""));

/** 開頁並等資料載入（有資料區才有 bk-cards；被原因面板遮住時改等 bk-reason-panel）。 */
async function open(options: { overview?: BackupOverview; role?: Role } = {}) {
  const user = userEvent.setup();
  const view = renderBackup(<BackupView />, options);
  await waitFor(() => expect(screen.queryByTestId("bk-cards") ?? screen.queryByTestId("bk-reason-panel")).not.toBeNull());
  return { user, ...view };
}
const goTo = async (user: ReturnType<typeof userEvent.setup>, name: string) => {
  await user.click(screen.getByRole("tab", { name }));
  await waitFor(() => expect(screen.getByRole("tab", { name })).toHaveAttribute("aria-selected", "true"));
};

// ── 載入與整頁讀取失敗 ───────────────────────────────────────────────────────────

describe("載入與整頁失敗（fail-loud）", () => {
  it("載入中只顯示載入文字（不顯示任何卡片或表格）；載入後出現資料；標題、麵包屑與連回系統管理的連結都在", async () => {
    renderBackup(<BackupView />);
    expect(testId("bk-loading")).toHaveTextContent("備份資料載入中");
    expect(screen.queryByTestId("bk-cards")).toBeNull();
    await screen.findByTestId("bk-cards");
    expect(screen.queryByTestId("bk-loading")).toBeNull();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("資料庫備份");
    expect(screen.getByRole("link", { name: "系統管理" })).toHaveAttribute("href", "/sysadmin");
  });

  it("整頁讀取失敗（HTTP 503）：整片顯示原因與「重試」，不渲染卡片、表格或舊資料；按重試會再請求一次", async () => {
    const user = userEvent.setup();
    const view = renderBackup(<BackupView />, { reply: failure(503, { message: "備份控制面目前無法使用", reason: "backup_control_unavailable" }) });
    const panel = await screen.findByTestId("bk-error-panel");
    expect(panel).toHaveTextContent("備份資料無法取得");
    expect(panel).toHaveTextContent("備份控制面目前無法使用");
    expect(screen.queryByTestId("bk-cards")).toBeNull();
    expect(screen.queryByTestId("bk-list")).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();
    const before = view.backupCalls().length;
    await user.click(within(panel).getByRole("button", { name: "重試" }));
    await waitFor(() => expect(view.backupCalls().length).toBeGreaterThan(before));
  });
});

// ── FR-BK-02 備份清單 ────────────────────────────────────────────────────────────

describe("AT_BK_02_1 清單新到舊十欄", () => {
  it("AT_BK_02_1_2 「備份清單」分頁表頭依序為 類型｜標籤｜儲存位置｜開始｜結束｜耗時｜資料庫｜備份｜基準｜結果；類型與儲存位置文字符規格；非差異的基準欄為「—」；列序與 API 回應序完全相同（前端不另排序）", async () => {
    const incr = { ...clone(BACKUPS[4]), kind: "incr", label: "20261026-020002F_incr-sample", location: "repo2", baseLabel: null };
    const backups = [...clone(BACKUPS), incr];
    await open({ overview: makeOverview({ backups }) });
    expect(screen.getByRole("tab", { name: "備份清單" })).toHaveAttribute("aria-selected", "true");
    const table = testId("bk-table");
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((th) => text(th)),
    ).toEqual(["類型", "標籤", "儲存位置", "開始", "結束", "耗時", "資料庫", "備份", "基準", "結果"]);
    expect(rowLabels(), "列序＝API 回應序（前端不另排序）").toEqual(backups.map((b) => b.label));
    const cells = (label: string) => within(testId(`bk-row-${label}`)).getAllByRole("cell");
    const expectedKind: Record<string, string> = { full: "全備", diff: "增備（差異）", incr: "增量", logical: "邏輯備份" };
    const expectedWhere: Record<string, string> = { repo1: "本地 repo1", repo2: "離站 repo2", logical: "離站邏輯" };
    for (const b of backups) {
      const c = cells(b.label);
      expect(text(c[0]), `${b.label} 類型`).toBe(expectedKind[b.kind]);
      expect(text(c[1]), `${b.label} 標籤`).toBe(b.label);
      expect(text(c[2]), `${b.label} 儲存位置`).toBe(expectedWhere[b.location]);
      expect(text(c[8]), `${b.label} 基準`).toBe(b.kind === "diff" ? (b.baseLabel as string) : "—");
    }
  });

  it("AT_BK_02_1_3 十欄表的外層容器是可用鍵盤捲動的區域（窄螢幕橫向溢出；axe scrollable-region-focusable，SCG-4 F11）：role=region、tabindex=0、名稱「備份清單（可橫向捲動）」，且恰好包著 bk-table", async () => {
    await open();
    const region = screen.getByRole("region", { name: "備份清單（可橫向捲動）" });
    expect(region).toHaveAttribute("tabindex", "0");
    expect(region).toContainElement(testId("bk-table"));
    expect(region.querySelectorAll("table")).toHaveLength(1);
  });
});

describe("AT_BK_02_2 校驗錯誤警示色", () => {
  it("AT_BK_02_2_2 ok_with_errors 的結果為「成功，但有校驗錯誤」並帶警示色；ok 的結果恰為「成功」；bk-list-note 含「失敗的工作看狀態卡與工作紀錄」", async () => {
    const backups = clone(BACKUPS) as (typeof BACKUPS)[number][];
    backups[2] = { ...backups[2], result: "ok_with_errors" };
    await open({ overview: makeOverview({ backups }) });
    const bad = testId(`bk-result-${backups[2].label}`);
    expect(bad).toHaveTextContent("成功，但有校驗錯誤");
    expect(bad).toHaveAttribute("data-tone", "warn");
    const good = testId(`bk-result-${backups[5].label}`);
    expect(text(good)).toBe("成功");
    expect(good).toHaveAttribute("data-tone", "ok");
    expect(testId("bk-list-note")).toHaveTextContent("失敗的工作看狀態卡與工作紀錄");
    expect(testId("bk-list-note"), "說明列可見（不只存在於 DOM）").toBeVisible();
  });

  it("AT_BK_02_2_E_1 只有 ok 的資料：畫面任何處都不出現「校驗錯誤」；bk-list-note 仍在（說明恆在）", async () => {
    await open();
    expect(document.body.textContent).not.toContain("校驗錯誤");
    expect(testId("bk-list-note")).toHaveTextContent("失敗的工作看狀態卡與工作紀錄");
    expect(testId("bk-list-note"), "說明列可見（不只存在於 DOM）").toBeVisible();
  });
});

describe("AT_BK_02_3 格式化沿用既有函式", () => {
  it("AT_BK_02_3_1 開始、結束、耗時、兩個大小欄逐字等於 formatDateTime／formatDuration／formatBytes 的回傳；分頁標題旁有文字含排程時區 Asia/Taipei", async () => {
    await open();
    const row = BACKUPS[5]; // repo1 全備：開始、結束、耗時、資料庫、備份皆有值
    const c = within(testId(`bk-row-${row.label}`)).getAllByRole("cell");
    expect(text(c[3])).toBe(formatDateTime(row.startedAt));
    expect(text(c[4])).toBe(formatDateTime(row.finishedAt));
    expect(text(c[5])).toBe(formatDuration(row.durationSeconds));
    expect(text(c[6])).toBe(formatBytes(row.databaseSizeBytes as number));
    expect(text(c[7])).toBe(formatBytes(row.repoSizeBytes as number));
    expect(testId("bk-timezone-note")).toHaveTextContent("Asia/Taipei");
  });

  it("AT_BK_02_3_E_1 邏輯備份形（開始、耗時、資料庫大小為 null）：對應儲存格恰為「—」；不出現「0 B」「0s」「Invalid Date」或空白", async () => {
    await open();
    const logical = BACKUPS[0];
    const c = within(testId(`bk-row-${logical.label}`)).getAllByRole("cell");
    expect(text(c[3]), "開始").toBe("—");
    expect(text(c[5]), "耗時").toBe("—");
    expect(text(c[6]), "資料庫").toBe("—");
    expect(text(c[8]), "基準").toBe("—");
    for (const cell of c) expect(text(cell), "沒有空白儲存格").not.toBe("");
    // 邏輯備份那一列：缺值只寫「—」，不寫成「0 B」「0s」（整頁別列的「10m 00s」是真值，不在此列）
    for (const bad of ["0 B", "0s", "Invalid Date"]) expect(testId(`bk-row-${logical.label}`).textContent, bad).not.toContain(bad);
  });
});

describe("AT_BK_02_4 repo 異常不當成空", () => {
  it("AT_BK_02_4_2 repo2 的狀態碼 99：bk-repo-status-2 顯示「狀態碼 99」與 REPO_STATUS_ZH[99]；repo1 照常列出 2 列；整頁不出現「沒有備份」「尚無備份」；repo2 沒有備份也不顯示成空表", async () => {
    const repos: BackupRepo[] = [
      { repo: 1, endpointHost: null, local: true, statusCode: 0, statusMessage: "ok" },
      { repo: 2, endpointHost: "minio", local: true, statusCode: 99, statusMessage: "other" },
    ];
    const backups = clone(BACKUPS).filter((b) => b.location !== "repo2" && b.kind !== "logical");
    expect(backups).toHaveLength(2);
    await open({ overview: makeOverview({ repos, backups }) });
    const status = testId("bk-repo-status-2");
    expect(status).toHaveTextContent("狀態碼 99");
    expect(status).toHaveTextContent(REPO_STATUS_ZH[99]);
    expect(status).toHaveAttribute("data-tone", "danger");
    expect(testId("bk-repo-status-1")).toHaveTextContent("正常");
    const where = rowLabels().map((label) => text(within(testId(`bk-row-${label}`)).getAllByRole("cell")[2]));
    expect(where, "repo1 的 2 列照常列出、repo2 不補佔位列").toEqual(["本地 repo1", "本地 repo1"]);
    expect(document.body.textContent).not.toContain("沒有備份");
    expect(document.body.textContent).not.toContain("尚無備份");
    expect(screen.queryByTestId("bk-list-empty")).toBeNull();
  });
});

describe("AT_BK_02_5 空狀態不顯示 0", () => {
  it("AT_BK_02_5_2 沒有任何備份的合法空狀態：bk-list-empty 恰為「尚無備份：首次部署後請立刻做第一份全備」；四張卡的徽章文字皆為「從未執行」；畫面不出現「0 B」「0 份」「0s」", async () => {
    await open({ overview: emptyOverview() });
    expect(text(testId("bk-list-empty"))).toBe("尚無備份：首次部署後請立刻做第一份全備");
    expect(screen.queryByTestId("bk-table")).toBeNull();
    for (const job of ["full", "diff", "dump", "verify"]) expect(text(testId(`bk-badge-${job}`)), job).toBe("從未執行");
    for (const bad of ["0 B", "0 份", "0s"]) expect(document.body.textContent, bad).not.toContain(bad);
  });

  it("備份清單為 null（來源讀不到，例如 info 與 logical 都不可用）：顯示原因文字、不顯示「尚無備份」，也不渲染空表", async () => {
    await open({ overview: makeOverview({ backups: null }, { warnings: ["info_unavailable", "logical_unavailable"] }) });
    expect(testId("bk-list-unavailable")).toHaveTextContent("備份清單目前無法取得");
    expect(document.body.textContent).not.toContain("尚無備份");
    expect(screen.queryByTestId("bk-table")).toBeNull();
    expect(screen.queryByTestId("bk-list-empty")).toBeNull();
  });
});

describe("AT_BK_02_6 本機 MinIO 標與主機同碟", () => {
  it("AT_BK_02_6_2 A＝repo2 端點 minio 且 local：徽章含「本機 MinIO・與主機同碟，主機損毀時一併消失」、dump 卡同樣標「與主機同碟」、任何處不含「已安全」「離站已備」；B＝外部 S3：徽章為「外部 S3」且不含「與主機同碟」；兩者徽章文字不同；repo1 固定顯示「本地」沒有 S3 徽章", async () => {
    const repo1: BackupRepo = { repo: 1, endpointHost: null, local: true, statusCode: 0, statusMessage: "ok" };
    const a = await open({ overview: makeOverview({ repos: [repo1, REPO2_LOCAL] }) });
    const badgeA = text(testId("bk-repo-badge-2"));
    expect(badgeA).toContain("本機 MinIO・與主機同碟，主機損毀時一併消失");
    expect(testId("bk-card-dump")).toHaveTextContent("與主機同碟");
    expect(document.body.textContent).not.toContain("已安全");
    expect(document.body.textContent).not.toContain("離站已備");
    expect(screen.queryByTestId("bk-repo-badge-1")).toBeNull();
    expect(testId("bk-repo-1")).toHaveTextContent("本地");
    a.unmount();

    await open({ overview: makeOverview({ repos: [repo1, REPO2_EXTERNAL] }) });
    const badgeB = text(testId("bk-repo-badge-2"));
    expect(badgeB).toBe("外部 S3");
    expect(badgeB).not.toContain("與主機同碟");
    expect(badgeB).not.toBe(badgeA);
    expect(testId("bk-card-dump")).not.toHaveTextContent("與主機同碟");
    expect(document.body.textContent).not.toContain("已安全");
    expect(document.body.textContent).not.toContain("離站已備");
  });
});

// ── FR-BK-03 排程與保留 ──────────────────────────────────────────────────────────

describe("AT_BK_03_1 六條 cron 白話列", () => {
  it("AT_BK_03_1_1 六列文字依序為指定的白話；每列另顯示原 cron 與 Asia/Taipei；固定列「WAL 持續歸檔（有寫入時約每 60 秒一段）」；只有 expire 與 wal_clean 兩列帶「維護工作」", async () => {
    const { user } = await open();
    await goTo(user, "排程與保留");
    const expected: Array<[string, string, string]> = [
      ["full", "每週日 02:00・全備", "0 2 * * 0"],
      ["diff", "每週一至週六 02:00・增備（差異）", "0 2 * * 1-6"],
      ["dump", "每日 02:30・離站 pg_dump", "30 2 * * *"],
      ["verify", "每週三 04:00・驗證", "0 4 * * 3"],
      ["expire", "每日 03:00・清理過期備份（維護工作）", "0 3 * * *"],
      ["wal_clean", "每日 03:30・清理 WAL 複本（維護工作）", "30 3 * * *"],
    ];
    const rows = within(testId("bk-schedule")).getAllByRole("listitem");
    expect(rows.map((r) => r.dataset.testid)).toEqual([...expected.map(([job]) => `bk-sched-${job}`), "bk-sched-fixed-wal"]);
    for (const [job, main, cron] of expected) {
      const row = testId(`bk-sched-${job}`);
      expect(within(row).getByText(main), job).toBeInTheDocument();
      expect(row, job).toHaveTextContent(cron);
      expect(row, job).toHaveTextContent("Asia/Taipei");
      expect(row.textContent?.includes("維護工作"), `${job} 的維護工作標記`).toBe(job === "expire" || job === "wal_clean");
    }
    expect(text(testId("bk-sched-fixed-wal"))).toBe("WAL 持續歸檔（有寫入時約每 60 秒一段）");
  });

  it("AT_BK_03_1_E_1 只有四條工作列（缺 expire、wal_clean）：只渲染四列加固定 WAL 列、不補出缺的兩列、不丟例外；schedule 為 null 時整個分頁顯示原因文字（由 control.reason 決定）、不顯示空表", async () => {
    const schedule = { entries: clone(SCHEDULE.entries).slice(0, 4), retention: clone(SCHEDULE.retention) };
    const { user, unmount } = await open({ overview: makeOverview({ schedule }) });
    await goTo(user, "排程與保留");
    expect(within(testId("bk-schedule")).getAllByRole("listitem")).toHaveLength(5);
    expect(screen.queryByTestId("bk-sched-expire")).toBeNull();
    expect(screen.queryByTestId("bk-sched-wal_clean")).toBeNull();
    unmount();

    // schedule 為 null：分頁元件顯示原因，不顯示空表
    renderBackup(<BackupSchedule schedule={null} timezone={null} reason="export_unreadable" />);
    expect(testId("bk-sched-unavailable")).toHaveTextContent("排程資料目前無法取得");
    expect(testId("bk-sched-unavailable")).toHaveTextContent("匯出檔無法讀取");
    expect(screen.queryByRole("list")).toBeNull();
    expect(screen.queryByTestId("bk-retention")).toBeNull();
  });
});

describe("AT_BK_03_2 不認得的 cron 原樣退回", () => {
  it("AT_BK_03_2_E_1 dump 列的 cron 為 */7 * * * *：該列顯示原表達式（不含「每」字白話）、其餘列照常、console.error 呼叫數為 0", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const schedule = clone(SCHEDULE);
    schedule.entries[2] = { job: "dump", cron: "*/7 * * * *", nextRunAt: null };
    const { user } = await open({ overview: makeOverview({ schedule }) });
    await goTo(user, "排程與保留");
    const row = testId("bk-sched-dump");
    expect(row).toHaveTextContent("*/7 * * * *");
    expect(row.textContent).not.toContain("每");
    expect(within(testId("bk-sched-full")).getByText("每週日 02:00・全備")).toBeInTheDocument();
    expect(testId("bk-sched-wal_clean")).toHaveTextContent("每日 03:30");
    expect(spy).not.toHaveBeenCalled();
  });
});

describe("AT_BK_03_4 保留唯讀、null 入警告", () => {
  it("AT_BK_03_4_3 retention 為 {repo1:{4,7}, repo2:{4,null}, logicalDays:28}：bk-retention 文字恰為「本地：全備 4、差異 7；離站：全備 4、差異隨全備到期；邏輯備份 28 天」；本地差異為 null 顯示「差異 未設」；邏輯備份天數為 null 顯示「邏輯備份 —」", async () => {
    const { user, unmount } = await open();
    await goTo(user, "排程與保留");
    expect(text(testId("bk-retention"))).toBe("本地：全備 4、差異 7；離站：全備 4、差異隨全備到期；邏輯備份 28 天");
    unmount();

    const schedule = clone(SCHEDULE);
    schedule.retention = { repo1: { full: 4, diff: null }, repo2: { full: 4, diff: null }, logicalDays: null };
    const second = await open({ overview: makeOverview({ schedule }) });
    await goTo(second.user, "排程與保留");
    expect(testId("bk-retention")).toHaveTextContent("差異 未設");
    expect(testId("bk-retention")).toHaveTextContent("邏輯備份 —");
  });

  it("AT_BK_03_4_E_1 retention 為 null：bk-retention 文字為「—」、不出現 4、7、28；control.warnings 含 retention_unavailable 時提示條說明保留設定讀不到", async () => {
    const schedule = { entries: clone(SCHEDULE.entries), retention: null };
    const { user } = await open({ overview: makeOverview({ schedule }, { warnings: ["retention_unavailable"] }) });
    expect(testId("bk-hint-bar")).toHaveTextContent("保留設定讀不到");
    await goTo(user, "排程與保留");
    expect(text(testId("bk-retention"))).toBe("—");
    for (const digit of ["4", "7", "28"]) expect(testId("bk-retention").textContent, digit).not.toContain(digit);
  });

  it("AT_BK_03_4_E_2 「排程與保留」分頁的整個 DOM 子樹（ADMIN）：沒有 input、textarea、select、可編輯元素，沒有名稱含「編輯」「儲存」「修改」「套用」的按鈕；沒有任何 PUT、PATCH、DELETE（也沒有 POST）請求被發出", async () => {
    const { user, calls } = await open({ role: "ADMIN" });
    await goTo(user, "排程與保留");
    const panel = testId("bk-panel-schedule");
    expect(panel.querySelectorAll("input, textarea, select, [contenteditable]")).toHaveLength(0);
    expect(within(panel).queryAllByRole("button")).toHaveLength(0);
    for (const name of [/編輯/, /儲存/, /修改/, /套用/]) expect(within(panel).queryByRole("button", { name }), String(name)).toBeNull();
    expect(
      calls.filter((c) => c.method !== "GET"),
      "沒有任何寫入請求",
    ).toEqual([]);
  });
});

// ── FR-BK-04 最近狀態卡 ──────────────────────────────────────────────────────────

describe("AT_BK_04_1 四張卡與最近備份", () => {
  it("AT_BK_04_1_2 五種狀態各有徽章文字（成功／失敗／進行中／中斷／從未執行）、data-status 為對應值、徽章內含一個 aria-hidden 的 svg（文字加圖示、不只有顏色）；每張卡顯示最近一次執行的觸發、開始時間、耗時與「最近一次成功」", async () => {
    const cards = makeCards({
      full: { status: "succeeded", trigger: "scheduled" },
      diff: { status: "failed", trigger: "manual", reason: "script_failed" },
      dump: { status: "running", trigger: "scheduled", finishedAt: null, durationSeconds: null },
      verify: { status: "interrupted", trigger: "manual", never: false, lastSuccessAt: "2026-10-21T20:05:00Z", reason: "interrupted" },
    });
    const first = await open({ overview: makeOverview({ cards }) });
    const expected: Array<[string, string, string]> = [
      ["full", "succeeded", "成功"],
      ["diff", "failed", "失敗"],
      ["dump", "running", "進行中"],
      ["verify", "interrupted", "中斷"],
    ];
    for (const [job, status, label] of expected) {
      const badge = testId(`bk-badge-${job}`);
      expect(text(badge), job).toBe(label);
      expect(badge, job).toHaveAttribute("data-status", status);
      const svg = badge.querySelector("svg");
      expect(svg, `${job} 的圖示`).not.toBeNull();
      expect(svg).toHaveAttribute("aria-hidden", "true");
    }
    const diff = cards[1] as BackupCard;
    expect(testId("bk-run-diff")).toHaveTextContent(`手動・${formatDateTime(diff.startedAt)}・耗時 ${formatDuration(diff.durationSeconds)}`);
    expect(testId("bk-run-full")).toHaveTextContent("排程");
    expect(testId("bk-last-success-full")).toHaveTextContent(`最近一次成功：${formatDateTime("2026-10-26T18:10:00Z")}`);
    first.unmount();

    await open();
    const noRun = testId("bk-badge-verify");
    expect(text(noRun)).toBe("從未執行");
    expect(noRun).toHaveAttribute("data-status", "no_run");
    expect(noRun.querySelector("svg")).not.toBeNull();
    expect(testId("bk-run-verify")).toHaveTextContent("最近一次執行：—");
  });

  it("AT_BK_04_1_E_1 F-04 形：全備卡沒有狀態檔（no_run）但清單有全備：徽章「從未執行」，同時顯示「最近一份備份：20261026-020002F」與「來源：pgBackRest 清單」——不得只顯示「從未執行」", async () => {
    const cards = makeCards({ full: { status: "no_run", trigger: null, startedAt: null, finishedAt: null, durationSeconds: null, lastSuccessAt: "2026-10-25T18:10:00Z", never: false } });
    await open({ overview: makeOverview({ cards }) });
    expect(text(testId("bk-badge-full"))).toBe("從未執行");
    const latest = testId("bk-latest-full");
    expect(latest).toHaveTextContent("最近一份備份：20261026-020002F");
    expect(latest).toHaveTextContent("來源：pgBackRest 清單");
    // 最近一次成功取自清單端（never=false）
    expect(testId("bk-last-success-full")).toHaveTextContent(`最近一次成功：${formatDateTime("2026-10-25T18:10:00Z")}`);
    // 只有全備與增備卡有「最近一份備份」；離站 pg_dump 與驗證卡沒有
    expect(screen.queryByTestId("bk-latest-dump")).toBeNull();
    expect(screen.queryByTestId("bk-latest-verify")).toBeNull();
  });

  it("全備或增備卡的 latestBackup 為 null（尚無備份）：顯示「最近一份備份：—」，不顯示成功也不顯示 0", async () => {
    await open({ overview: emptyOverview() });
    expect(text(testId("bk-latest-full"))).toBe("最近一份備份：—");
    expect(text(testId("bk-latest-diff"))).toBe("最近一份備份：—");
  });
});

describe("AT_BK_04_2 失敗色與最近成功", () => {
  const failedDump = (patch: Partial<BackupCard> = {}) =>
    makeOverview({
      cards: makeCards({
        dump: {
          status: "failed",
          trigger: "scheduled",
          startedAt: "2026-10-27T18:30:00Z",
          finishedAt: "2026-10-27T18:30:40Z",
          durationSeconds: 40,
          lastSuccessAt: "2026-10-26T18:30:30Z",
          reason: "script_failed",
          detailTail: "line1\nline2",
          ...patch,
        },
      }),
    });

  it("AT_BK_04_2_2 失敗卡為失敗色並顯示「最近一次成功：<時間>」；輸出尾段只對 ADMIN 顯示（OPERATOR 的 DOM 內沒有 bk-tail-dump，即使回應帶了 detailTail）", async () => {
    const admin = await open({ overview: failedDump(), role: "ADMIN" });
    expect(testId("bk-badge-dump")).toHaveAttribute("data-tone", "danger");
    expect(testId("bk-last-success-dump")).toHaveTextContent(`最近一次成功：${formatDateTime("2026-10-26T18:30:30Z")}`);
    expect(testId("bk-tail-dump")).toHaveTextContent("line1");
    expect(testId("bk-tail-dump")).toHaveTextContent("line2");
    admin.unmount();

    for (const role of ["OPERATOR", "VIEWER"] as const) {
      const other = await open({ overview: failedDump(), role });
      expect(testId("bk-badge-dump"), role).toHaveAttribute("data-tone", "danger");
      expect(testId("bk-last-success-dump"), role).toHaveTextContent(`最近一次成功：${formatDateTime("2026-10-26T18:30:30Z")}`);
      expect(screen.queryByTestId("bk-tail-dump"), `${role} 的 DOM 內沒有 bk-tail-dump`).toBeNull();
      expect(document.body.textContent, `${role} 看不到尾段文字`).not.toContain("line1");
      other.unmount();
    }
  });

  it("AT_BK_04_2_E_1 失敗卡的 lastSuccessAt 為 null（從未成功）：「最近一次成功：從未成功」、徽章仍為失敗色、不出現任何時間字串", async () => {
    await open({ overview: failedDump({ lastSuccessAt: null, never: true }) });
    expect(text(testId("bk-last-success-dump"))).toBe("最近一次成功：從未成功");
    expect(testId("bk-badge-dump")).toHaveAttribute("data-tone", "danger");
    expect(testId("bk-last-success-dump").textContent).not.toMatch(/\d{4}-\d{2}-\d{2}/);
  });

  it("輸出尾段是純文字：含 HTML 標籤與 script 的尾段原樣以文字顯示，不被當成標記執行", async () => {
    await open({ overview: failedDump({ detailTail: '<img src=x onerror="window.__xss=1"><script>window.__xss=2</script>' }), role: "ADMIN" });
    const tail = testId("bk-tail-dump");
    expect(tail.textContent).toContain("<img src=x");
    expect(tail.querySelector("img, script")).toBeNull();
    expect((window as unknown as Record<string, unknown>).__xss).toBeUndefined();
  });

  it("AT_BK_04_2_3 ADMIN 的輸出尾段（max-h-48 的可捲動 pre）可用鍵盤抵達（axe scrollable-region-focusable，SCG-4 F11）：60 行長尾段時仍是 role=region、tabindex=0，名稱帶工作名且三張卡互不相同、不含尾段內容；非 ADMIN 沒有任何輸出尾段區域", async () => {
    const longTail = Array.from({ length: 60 }, (_, i) => `輸出第 ${i + 1} 行`).join("\n");
    const overview = makeOverview({ cards: makeCards({ full: { detailTail: longTail }, diff: { detailTail: longTail }, dump: { detailTail: longTail } }) });
    const admin = await open({ overview, role: "ADMIN" });
    const regions = screen.getAllByRole("region", { name: /輸出尾段（可捲動）$/ });
    expect(regions, "full、diff、dump 三張卡各一個（verify 從未執行、沒有尾段）").toEqual([testId("bk-tail-full"), testId("bk-tail-diff"), testId("bk-tail-dump")]);
    for (const region of regions) {
      expect(region.tagName).toBe("PRE");
      expect(region).toHaveAttribute("tabindex", "0");
      expect(region).toHaveTextContent("輸出第 60 行");
    }
    const names = regions.map((region) => region.getAttribute("aria-label"));
    expect(names).toEqual(["全備 輸出尾段（可捲動）", "增備（差異） 輸出尾段（可捲動）", "離站 pg_dump 輸出尾段（可捲動）"]);
    expect(new Set(names).size, "三個名稱互不相同").toBe(3);
    for (const name of names) expect(name, "名稱是固定字串，不夾帶輸出內容").not.toContain("輸出第");
    admin.unmount();

    await open({ overview, role: "OPERATOR" });
    expect(screen.queryAllByRole("region", { name: /輸出尾段/ }), "非 ADMIN 的 DOM 內沒有任何輸出尾段區域").toHaveLength(0);
  });
});

describe("AT_BK_04_3 逾期只顯示 card.overdue", () => {
  it("overdue 為 true 的卡顯示「逾期」標記、為 false 的不顯示；前端不自己重算（lastDueAt 很久以前但 overdue 為 false 仍不標）", async () => {
    const cards = makeCards({ diff: { overdue: true, lastDueAt: "2026-11-01T18:00:00Z" }, full: { overdue: false, lastDueAt: "2020-01-01T00:00:00Z" } });
    await open({ overview: makeOverview({ cards }) });
    expect(text(testId("bk-overdue-diff"))).toBe("逾期");
    for (const job of ["full", "dump", "verify"]) expect(screen.queryByTestId(`bk-overdue-${job}`), job).toBeNull();
  });
});

describe("AT_BK_04_6 WAL 歸檔一行", () => {
  const T = "2026-10-27T02:15:00Z";
  const LATER = "2026-10-27T02:20:00Z";

  it("AT_BK_04_6_3 (a) 失敗 0 次：「WAL 歸檔：最近 <時間>・失敗 0 次」、ok；(b) 失敗 3 次且最近失敗較晚：含「失敗 3 次」與最近失敗時間、danger；(c) null：恰為「WAL 歸檔：—」、不出現「失敗 0 次」；三者皆為單行唯讀（沒有按鈕、輸入）", async () => {
    const a = await open({ overview: makeOverview({ walArchive: { lastArchivedAt: T, failedCount: 0, lastFailedAt: null } }) });
    expect(text(testId("bk-wal-line"))).toBe(`WAL 歸檔：最近 ${formatDateTime(T)}・失敗 0 次`);
    expect(testId("bk-wal-line")).toHaveAttribute("data-tone", "ok");
    a.unmount();

    const b = await open({ overview: makeOverview({ walArchive: { lastArchivedAt: T, failedCount: 3, lastFailedAt: LATER } }) });
    expect(testId("bk-wal-line")).toHaveTextContent("失敗 3 次");
    expect(testId("bk-wal-line")).toHaveTextContent(formatDateTime(LATER));
    expect(testId("bk-wal-line")).toHaveAttribute("data-tone", "danger");
    b.unmount();

    await open({ overview: makeOverview({ walArchive: null }, { warnings: ["db_unavailable"] }) });
    expect(text(testId("bk-wal-line"))).toBe("WAL 歸檔：—");
    expect(testId("bk-wal-line").textContent).not.toContain("失敗 0 次");
    expect(testId("bk-wal-line").querySelectorAll("button, input, a")).toHaveLength(0);
    // walArchive 讀不到只影響這一行：其餘區塊完整
    expect(testId("bk-cards")).toBeInTheDocument();
    expect(testId("bk-hint-bar")).toHaveTextContent("資料庫讀取失敗");
  });
});

// ── FR-BK-05 控制面健康與資料新鮮度 ──────────────────────────────────────────────

describe("AT_BK_05_1 控制面未設定整頁說明", () => {
  it("AT_BK_05_1_3 control.reason 為 not_configured、其餘區塊皆 null：整頁只顯示 bk-reason-panel（文字「備份控制面未設定（不在 Docker 全棧）」）；沒有 bk-cards、bk-list、分頁內容；沒有任何數字 0、「0 份」或空表", async () => {
    await open({ overview: blockedOverview("not_configured") });
    const panel = testId("bk-reason-panel");
    expect(text(panel)).toBe("備份控制面未設定（不在 Docker 全棧）");
    expect(screen.queryByTestId("bk-cards")).toBeNull();
    expect(screen.queryByTestId("bk-list")).toBeNull();
    expect(screen.queryByRole("tablist")).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.queryByTestId("bk-wal-line")).toBeNull();
    expect(document.body.textContent).not.toMatch(/\b0\b/);
    expect(document.body.textContent).not.toContain("0 份");
  });
});

describe("AT_BK_05_2 心跳離線橫幅", () => {
  it("AT_BK_05_2_2 runner_offline 且心跳 95 秒：bk-banner-offline（role=alert）「備份控制面無回應（上次心跳 95 秒前）」；資料區有 bk-stale-mark「可能已過期」；心跳缺席（null）時為「（尚未收到心跳）」；資料照回（卡片仍在）", async () => {
    const first = await open({ overview: makeOverview({}, { reason: "runner_offline", heartbeatAgeSeconds: 95, canTrigger: false }) });
    const banner = testId("bk-banner-offline");
    expect(banner).toHaveAttribute("role", "alert");
    expect(text(banner)).toBe("備份控制面無回應（上次心跳 95 秒前）");
    expect(text(testId("bk-stale-mark"))).toBe("可能已過期");
    expect(testId("bk-cards"), "離線時資料照回、不遮住").toBeInTheDocument();
    expect(testId("bk-list")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toBe(banner);
    first.unmount();

    await open({ overview: makeOverview({}, { reason: "runner_offline", heartbeatAgeSeconds: null }) });
    expect(text(testId("bk-banner-offline"))).toBe("備份控制面無回應（尚未收到心跳）");
  });

  it("沒有 reason 時不出現離線橫幅，也沒有 role=alert", async () => {
    await open();
    expect(screen.queryByTestId("bk-banner-offline")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("AT_BK_05_3 壞檔顯示原因", () => {
  it("AT_BK_05_3_2 schema_mismatch 與 export_unreadable（區塊皆 null）：bk-reason-panel 文字分別含「匯出檔格式版本不符」「匯出檔無法讀取」；不渲染任何表格、卡片；不出現「尚無備份」、不出現數字 0", async () => {
    for (const [reason, expected] of [
      ["schema_mismatch", "匯出檔格式版本不符"],
      ["export_unreadable", "匯出檔無法讀取"],
    ] as const) {
      const view = await open({ overview: blockedOverview(reason) });
      expect(testId("bk-reason-panel"), reason).toHaveTextContent(expected);
      expect(screen.queryByRole("table"), reason).toBeNull();
      expect(screen.queryByTestId("bk-cards"), reason).toBeNull();
      expect(document.body.textContent, reason).not.toContain("尚無備份");
      expect(document.body.textContent, reason).not.toMatch(/\b0\b/);
      view.unmount();
    }
  });

  it("日後新增的 reason（資料區塊皆 null）：原因面板原樣顯示該值，不吞掉、不當成沒事", async () => {
    await open({ overview: blockedOverview("brand_new_reason") });
    expect(testId("bk-reason-panel")).toHaveTextContent("brand_new_reason");
    expect(screen.queryByTestId("bk-cards")).toBeNull();
  });

  it("AT_BK_05_3_E_1 info 的 ok:false：repos 為 null、清單只含邏輯備份、各卡 latestBackup 為 null；提示條明說 pgBackRest 備份資訊讀不到；logical 的 ok:false：提示條明說邏輯備份清單讀不到；兩者 control.reason 皆為 null（不遮住資料）", async () => {
    const logicalOnly = clone(BACKUPS).filter((b) => b.kind === "logical");
    const cards = makeCards({ full: { latestBackup: null }, diff: { latestBackup: null } });
    const first = await open({
      overview: makeOverview(
        { repos: null, backups: logicalOnly, cards, schedule: { entries: clone(SCHEDULE.entries), retention: null } },
        { warnings: ["info_unavailable", "retention_unavailable"] },
      ),
    });
    expect(testId("bk-hint-bar")).toHaveTextContent("pgBackRest 備份資訊暫時讀不到");
    expect(rowLabels()).toEqual(logicalOnly.map((b) => b.label));
    expect(screen.queryByTestId("bk-repo-1")).toBeNull();
    expect(text(testId("bk-latest-full"))).toBe("最近一份備份：—");
    expect(screen.queryByTestId("bk-reason-panel")).toBeNull();
    first.unmount();

    const pgOnly = clone(BACKUPS).filter((b) => b.kind !== "logical");
    await open({ overview: makeOverview({ backups: pgOnly }, { warnings: ["logical_unavailable"] }) });
    expect(testId("bk-hint-bar")).toHaveTextContent("邏輯備份清單暫時讀不到");
    expect(rowLabels()).toEqual(pgOnly.map((b) => b.label));
  });

  it("cron_unparsable:<job> 的警告：提示條帶工作名；封閉詞彙以外的警告原樣顯示；沒有警告時不出現提示條", async () => {
    const first = await open({ overview: makeOverview({}, { warnings: ["cron_unparsable:diff", "something_new"] }) });
    const bar = testId("bk-hint-bar");
    expect(bar).toHaveAttribute("role", "note");
    expect(bar).toHaveTextContent("「增備（差異）」的排程表達式無法解析");
    expect(bar).toHaveTextContent("something_new");
    first.unmount();
    await open();
    expect(screen.queryByTestId("bk-hint-bar")).toBeNull();
  });
});

describe("AT_BK_05_4 資料已過期標記", () => {
  it("AT_BK_05_4_2 exportAgeSeconds 為 180 與 181：兩者皆顯示「資料更新於 <formatClock(exportGeneratedAt)>」；181 者另有「已過期」標記（bk-stale-mark），180 者沒有", async () => {
    const at = await open({ overview: makeOverview({}, { exportAgeSeconds: 180, exportGeneratedAt: EXPORT_AT }) });
    expect(testId("bk-updated")).toHaveTextContent(`資料更新於 ${formatClock(EXPORT_AT)}`);
    expect(screen.queryByTestId("bk-stale-mark")).toBeNull();
    at.unmount();

    await open({ overview: makeOverview({}, { exportAgeSeconds: 181, exportGeneratedAt: EXPORT_AT }) });
    expect(testId("bk-updated")).toHaveTextContent(`資料更新於 ${formatClock(EXPORT_AT)}`);
    expect(text(testId("bk-stale-mark"))).toBe("已過期");
  });

  it("AT_BK_05_4_E_1 exportAgeSeconds 與 exportGeneratedAt 皆為 null 而 reason 為 null（防禦：不應發生）：不顯示「已過期」、不丟例外；時間文字為「資料更新於 —」", async () => {
    await open({ overview: makeOverview({}, { exportAgeSeconds: null, exportGeneratedAt: null }) });
    expect(text(testId("bk-updated"))).toBe("資料更新於 —");
    expect(document.body.textContent).not.toContain("已過期");
  });
});

// ── FR-BK-08 說明區 ───────────────────────────────────────────────────────────────

describe("AT_BK_08_1 還原三步與核對", () => {
  it("AT_BK_08_1_2 「還原與說明」分頁：bk-restore-steps 顯示三步、每步同時有 bash 與 PowerShell；bk-restore-checks 列出核對三項（列數、時間軸、pgbackrest check）；有一句明寫「本頁不提供還原按鈕」並含原因；核對三項的 PowerShell 形態以一句說明（前綴與後綴）呈現", async () => {
    const { user } = await open();
    await goTo(user, "還原與說明");
    const steps = within(testId("bk-restore-steps")).getAllByRole("listitem");
    expect(steps).toHaveLength(3);
    RESTORE_STEPS.forEach((step, i) => {
      const item = steps[i];
      expect(item).toHaveTextContent(step.title);
      expect(within(item).getByText("bash")).toBeInTheDocument();
      expect(within(item).getByText("PowerShell")).toBeInTheDocument();
      for (const line of [...step.bash, ...step.powershell]) expect(item.textContent, line).toContain(line);
    });
    expect(steps[0]).toHaveTextContent("停止 primary");
    expect(steps[1]).toHaveTextContent("restore.sh");
    expect(steps[2]).toHaveTextContent("核對");
    const checks = within(testId("bk-restore-checks")).getAllByRole("listitem");
    expect(checks).toHaveLength(3);
    expect(checks.map((li) => text(within(li).getAllByText(/.+/)[0]))).toEqual(RESTORE_CHECKS.map((c) => c.title));
    for (const [i, check] of RESTORE_CHECKS.entries()) expect(checks[i].textContent).toContain(check.command);
    expect(text(testId("bk-no-restore-note"))).toBe(NO_RESTORE_BUTTON_NOTE);
    expect(testId("bk-no-restore-note")).toHaveTextContent("本頁不提供還原按鈕");
    for (const reason of ["先停止 primary", "restore.sh 在 primary 仍運作時會拒絕執行", "replica 的時間軸也會分岔、必須重建"]) expect(testId("bk-no-restore-note"), reason).toHaveTextContent(reason);
    const panel = testId("bk-panel-help");
    expect(panel).toHaveTextContent(CHECKS_POWERSHELL_NOTE);
    expect(panel).toHaveTextContent("Push-Location AgentConsole;");
    expect(panel).toHaveTextContent("; Pop-Location");
  });

  it("AT_BK_08_1_E_2 「還原與說明」分頁的全部可聚焦元素：沒有名稱符合 /還原/ 的 button（分頁標籤「還原與說明」是 tab 角色，不計）；沒有任何元素在點擊時送出請求；ADMIN 亦然", async () => {
    const { user, calls } = await open({ role: "ADMIN" });
    await goTo(user, "還原與說明");
    const panel = testId("bk-panel-help");
    expect(within(panel).queryByRole("button", { name: /還原/ })).toBeNull();
    // 分頁標籤本身是 tab 角色：整頁名稱含「還原」的 button 同樣沒有
    expect(screen.queryByRole("button", { name: /還原/ })).toBeNull();
    expect(within(panel).queryAllByRole("button")).toHaveLength(0);
    expect(panel.querySelectorAll("a[href], input, select, textarea, button")).toHaveLength(0);
    const before = calls.length;
    for (const el of Array.from(panel.querySelectorAll<HTMLElement>("*"))) fireEvent.click(el);
    expect(
      calls.slice(before).filter((c) => c.method !== "GET"),
      "點擊說明區任何元素都不送出寫入請求",
    ).toEqual([]);
  });
});

describe("AT_BK_08_2 涵蓋範圍表", () => {
  it("AT_BK_08_2_1 bk-coverage-row-<volume> 逐卷分類：pg_data＝已備份（含 console schema）；pg_backup、minio_data、pg_wal_archive、pg_socket、backup_out、backup_req＝備份機制本身；pg_replica_data＝可由 primary 重建；其餘六卷＝未涵蓋（engine_workspace 明寫「未涵蓋」、minio_certs 註「缺時由 minio-certs job 重產」）；表下方一句含兩把金鑰遺失的後果", async () => {
    const { user } = await open();
    await goTo(user, "還原與說明");
    const rows = Array.from(document.querySelectorAll<HTMLElement>('[data-testid^="bk-coverage-row-"]'));
    expect(rows.map((r) => (r.dataset.testid as string).replace("bk-coverage-row-", "")).sort()).toEqual(Object.keys(VOLUME_COVERAGE).sort());
    expect(rows).toHaveLength(14);
    const row = (volume: string) => testId(`bk-coverage-row-${volume}`);
    expect(row("pg_data")).toHaveTextContent("已備份");
    expect(row("pg_data")).toHaveTextContent("console schema");
    for (const volume of ["pg_backup", "minio_data", "pg_wal_archive", "pg_socket", "backup_out", "backup_req"]) expect(row(volume), volume).toHaveTextContent("備份機制本身");
    expect(row("pg_replica_data")).toHaveTextContent("可由 primary 重建");
    for (const volume of ["engine_workspace", "app_logs", "redis_data", "prometheus_data", "nginx_certs", "minio_certs"]) expect(row(volume), volume).toHaveTextContent("未涵蓋");
    expect(row("engine_workspace")).toHaveTextContent(COVERAGE_CATEGORY_LABEL.not_covered);
    expect(row("minio_certs")).toHaveTextContent("缺時由 minio-certs job 重產");
    const note = testId("bk-key-loss-note");
    expect(note).toHaveTextContent("PGBACKREST_CIPHER_PASS 遺失＝備份無法還原");
    expect(note).toHaveTextContent("CONSOLE_ENCRYPTION_KEY 遺失＝敏感參數無法解密，請另行保管");
    expect(text(note)).toBe(KEY_LOSS_NOTE);
  });

  it("AT_BK_08_2_2 涵蓋範圍表的外層容器是可用鍵盤捲動的區域（窄螢幕橫向溢出；axe scrollable-region-focusable，SCG-4 F11）：role=region、tabindex=0、名稱「涵蓋範圍表（可橫向捲動）」且包著 bk-coverage；說明分頁唯一帶 tabindex 的元素就是它（仍沒有按鈕、連結、輸入）", async () => {
    const { user } = await open({ role: "ADMIN" });
    await goTo(user, "還原與說明");
    const panel = testId("bk-panel-help");
    const region = within(panel).getByRole("region", { name: "涵蓋範圍表（可橫向捲動）" });
    expect(region).toHaveAttribute("tabindex", "0");
    expect(region).toContainElement(testId("bk-coverage"));
    expect(Array.from(panel.querySelectorAll<HTMLElement>("[tabindex]")), "說明分頁唯一可聚焦的是這個捲動區域").toEqual([region]);
    expect(panel.querySelectorAll("a[href], input, select, textarea, button")).toHaveLength(0);
  });
});
