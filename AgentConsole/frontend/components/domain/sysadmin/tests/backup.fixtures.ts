/**
 * 備份頁的測試夾具（TCS-SysAdminBackup-20261027 §5.1、§5.6）：API 形（camelCase）的總覽與各狀態的卡片、repos、walArchive，加「假後端＋Provider」的渲染小工具。
 * 數值取自 TCS §5.1 的 INFO_2REPO／LOGICAL_2 與「對應的 API 值」（2026-10-26 02:00 起的兩個 repo 各一份全備與差異加兩個離站邏輯備份）；全是假值，沒有任何機密。
 * 放在 `tests/` 子目錄：設計系統的靜態守衛（`tests/design-rules.test.ts`）掃原始碼時略過名為 tests 的目錄。
 */
import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";

import type { BackupCard, BackupControl, BackupJobName, BackupOverview, BackupRepo, BackupRow, BackupSchedule, Role } from "@/lib/api/types";
import { clearSession, resetSessionCache } from "@/lib/auth/store";
import { makeClient, signIn, stubApi, type ApiCall, type Reply } from "@/tests/helpers/api";
import { withProviders } from "./withProviders";

/** 深拷貝（測試要改寫資料時用，不污染共用的夾具）。 */
export function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

/** 總覽端點的路徑。 */
export const OVERVIEW_PATH = "/api/v1/sysadmin/backups";

// ── 備份清單（TCS §5.1：INFO_2REPO＋LOGICAL_2 合併後新到舊的六列）──────────────────────────────────

const backup = (patch: Partial<BackupRow> & Pick<BackupRow, "kind" | "label" | "location">): BackupRow => ({
  startedAt: null,
  finishedAt: null,
  durationSeconds: null,
  databaseSizeBytes: null,
  repoSizeBytes: null,
  baseLabel: null,
  result: "ok",
  ...patch,
});

/** 新到舊：邏輯 10-26、repo2 差異、repo1 差異、邏輯 10-25、repo2 全備、repo1 全備。 */
export const BACKUPS: ReadonlyArray<BackupRow> = [
  backup({ kind: "logical", label: "aisdlc-20261026-183000.dump", location: "logical", finishedAt: "2026-10-26T18:30:05Z", repoSizeBytes: 1049600 }),
  backup({
    kind: "diff",
    label: "20261026-020002F_20261027-020001D",
    location: "repo2",
    startedAt: "2026-10-26T18:00:01Z",
    finishedAt: "2026-10-26T18:03:00Z",
    durationSeconds: 179,
    databaseSizeBytes: 33619968,
    repoSizeBytes: 524544,
    baseLabel: "20261026-020002F",
  }),
  backup({
    kind: "diff",
    label: "20261026-020000F_20261027-020000D",
    location: "repo1",
    startedAt: "2026-10-26T18:00:00Z",
    finishedAt: "2026-10-26T18:02:00Z",
    durationSeconds: 120,
    databaseSizeBytes: 33619968,
    repoSizeBytes: 524288,
    baseLabel: "20261026-020000F",
  }),
  backup({ kind: "logical", label: "aisdlc-20261025-183000.dump", location: "logical", finishedAt: "2026-10-25T18:30:05Z", repoSizeBytes: 1048576 }),
  backup({
    kind: "full",
    label: "20261026-020002F",
    location: "repo2",
    startedAt: "2026-10-25T18:00:02Z",
    finishedAt: "2026-10-25T18:12:00Z",
    durationSeconds: 718,
    databaseSizeBytes: 33554432,
    repoSizeBytes: 4194816,
  }),
  backup({
    kind: "full",
    label: "20261026-020000F",
    location: "repo1",
    startedAt: "2026-10-25T18:00:00Z",
    finishedAt: "2026-10-25T18:10:00Z",
    durationSeconds: 600,
    databaseSizeBytes: 33554432,
    repoSizeBytes: 4194304,
  }),
];

/** repo1 是本機磁碟（沒有端點主機）；repo2 是本機 MinIO（端點主機 minio、local＝true＝與主機同碟）。 */
export const REPOS: ReadonlyArray<BackupRepo> = [
  { repo: 1, endpointHost: null, local: true, statusCode: 0, statusMessage: "ok" },
  { repo: 2, endpointHost: "minio", local: true, statusCode: 0, statusMessage: "ok" },
];

/** 兩個離站端點的對照組（TCS AT-BK-02-6-2）：本機 MinIO 與外部 S3。 */
export const REPO2_LOCAL: BackupRepo = { repo: 2, endpointHost: "minio", local: true, statusCode: 0, statusMessage: "ok" };
export const REPO2_EXTERNAL: BackupRepo = { repo: 2, endpointHost: "s3.amazonaws.com", local: false, statusCode: 0, statusMessage: "ok" };

// ── 排程與保留（TCS AT-BK-03-1-1／03-3-1：now＝2026-10-27T10:00:00+08:00 的下次執行時間）─────────────

export const SCHEDULE: BackupSchedule = {
  entries: [
    { job: "full", cron: "0 2 * * 0", nextRunAt: "2026-10-31T18:00:00Z" },
    { job: "diff", cron: "0 2 * * 1-6", nextRunAt: "2026-10-27T18:00:00Z" },
    { job: "dump", cron: "30 2 * * *", nextRunAt: "2026-10-27T18:30:00Z" },
    { job: "verify", cron: "0 4 * * 3", nextRunAt: "2026-10-27T20:00:00Z" },
    { job: "expire", cron: "0 3 * * *", nextRunAt: "2026-10-27T19:00:00Z" },
    { job: "wal_clean", cron: "30 3 * * *", nextRunAt: "2026-10-27T19:30:00Z" },
  ],
  retention: { repo1: { full: 4, diff: 7 }, repo2: { full: 4, diff: null }, logicalDays: 28 },
};

// ── 狀態卡 ───────────────────────────────────────────────────────────────────────────────────────

/** 一張卡：預設是「排程、成功、10 分鐘」；full、diff 卡另帶 `latestBackup`（只有這兩張有此鍵，與 API 一致）。`patch` 逐欄覆寫。 */
export function makeCard(job: BackupJobName, patch: Partial<BackupCard> = {}): BackupCard {
  const card: BackupCard = {
    job,
    status: "succeeded",
    trigger: "scheduled",
    startedAt: "2026-10-26T18:00:00Z",
    finishedAt: "2026-10-26T18:10:00Z",
    durationSeconds: 600,
    lastSuccessAt: "2026-10-26T18:10:00Z",
    lastDueAt: "2026-10-26T18:00:00Z",
    overdue: false,
    never: false,
    reason: null,
  };
  if (job === "full") card.latestBackup = { label: "20261026-020002F", finishedAt: "2026-10-25T18:12:00Z", source: "pgbackrest" };
  if (job === "diff") card.latestBackup = { label: "20261026-020002F_20261027-020001D", finishedAt: "2026-10-26T18:03:00Z", source: "pgbackrest" };
  return { ...card, ...patch };
}

/** 驗證卡：從未執行（沒有狀態檔）。 */
export const VERIFY_NO_RUN: Partial<BackupCard> = {
  status: "no_run",
  trigger: null,
  startedAt: null,
  finishedAt: null,
  durationSeconds: null,
  lastSuccessAt: null,
  never: true,
  reason: null,
};

/** 四張卡（依序 full、diff、dump、verify）：前三張成功、驗證從未執行。`patches` 依工作名覆寫。 */
export function makeCards(patches: Partial<Record<BackupJobName, Partial<BackupCard>>> = {}): BackupCard[] {
  return (["full", "diff", "dump", "verify"] as const).map((job) => makeCard(job, { ...(job === "verify" ? VERIFY_NO_RUN : {}), ...patches[job] }));
}

// ── 總覽 ─────────────────────────────────────────────────────────────────────────────────────────

export const EXPORT_AT = "2026-10-27T06:39:08Z";

/** 一份完整、健康的總覽（心跳新鮮、匯出新鮮、沒有警告）。`patch` 覆寫資料區塊、`control` 覆寫 control 的欄位。 */
export function makeOverview(patch: Partial<BackupOverview> = {}, control: Partial<BackupControl> = {}): BackupOverview {
  return {
    control: { available: true, canTrigger: false, reason: null, heartbeatAgeSeconds: 5, exportAgeSeconds: 12, exportGeneratedAt: EXPORT_AT, warnings: [], ...control },
    timezone: "Asia/Taipei",
    activeJob: null,
    cards: makeCards(),
    backups: clone(BACKUPS) as BackupRow[],
    schedule: clone(SCHEDULE),
    repos: clone(REPOS) as BackupRepo[],
    walArchive: { lastArchivedAt: "2026-10-27T02:15:00Z", failedCount: 0, lastFailedAt: null },
    ...patch,
  };
}

/** `control.reason` 讓資料區塊缺席的總覽（not_configured、schema_mismatch、export_unreadable）：所有資料區塊都是 null（不是空陣列或 0）。 */
export function blockedOverview(reason: string, control: Partial<BackupControl> = {}): BackupOverview {
  return {
    control: { available: reason !== "not_configured", canTrigger: false, reason, heartbeatAgeSeconds: null, exportAgeSeconds: null, exportGeneratedAt: null, warnings: [], ...control },
    timezone: null,
    activeJob: null,
    cards: null,
    backups: null,
    schedule: null,
    repos: null,
    walArchive: null,
  };
}

/** 完全沒有備份的合法空狀態（TCS AT-BK-02-5-1）：清單空、四張卡皆從未執行、沒有逾期。 */
export function emptyOverview(): BackupOverview {
  const empty: Partial<BackupCard> = { ...VERIFY_NO_RUN, latestBackup: null };
  return makeOverview({
    backups: [],
    cards: (["full", "diff", "dump", "verify"] as const).map((job) => makeCard(job, job === "full" || job === "diff" ? empty : { ...VERIFY_NO_RUN })),
    repos: [],
    schedule: { entries: clone(SCHEDULE.entries), retention: null },
  });
}

// ── 渲染 ─────────────────────────────────────────────────────────────────────────────────────────

export type BackupRender = RenderResult & {
  /** 假後端記下的全部請求 */
  calls: ApiCall[];
  /** 打向 `/api/v1/sysadmin/**` 的請求 */
  backupCalls: () => ApiCall[];
};

/** 登入為 `role`、假後端對總覽回 `overview`（或 `reply` 原樣回，用來造失敗），再渲染 `ui`。 */
export function renderBackup(ui: ReactElement, options: { role?: Role; overview?: BackupOverview; reply?: Reply } = {}): BackupRender {
  const role = options.role ?? "VIEWER";
  signIn(role, role === "ADMIN" ? "admin" : role.toLowerCase());
  const stub = stubApi((call) => (call.path === OVERVIEW_PATH ? (options.reply ?? { data: options.overview ?? makeOverview() }) : undefined));
  const view = render(withProviders(ui, makeClient()));
  return { ...view, calls: stub.calls, backupCalls: () => stub.calls.filter((c) => c.path.startsWith("/api/v1/sysadmin/")) };
}

/** 未登入（`status` 為 anon）渲染：假後端照樣掛著，用來證明沒有任何備份請求被送出。 */
export function renderBackupAnon(ui: ReactElement): BackupRender {
  resetSessionCache();
  clearSession();
  const stub = stubApi((call) => (call.path === OVERVIEW_PATH ? { data: makeOverview() } : undefined));
  const view = render(withProviders(ui, makeClient()));
  return { ...view, calls: stub.calls, backupCalls: () => stub.calls.filter((c) => c.path.startsWith("/api/v1/sysadmin/")) };
}
