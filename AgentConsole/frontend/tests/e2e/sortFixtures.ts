import { readFileSync } from "node:fs";
import path from "node:path";

import { paged, type MockHandler } from "./mockApi";

/**
 * console-sort.mock.spec.ts 的自帶夾具（TCS-ConsoleUxSortHelp §7.1 PKG-E2E）：專案、議題、備份、研究專案清單四組。
 * 既有 spec 的夾具都是各檔內部函式、不可重用，這裡各自重寫一份最小集合；不改 mockApi.ts。
 * 專案 mock 依請求的 `sort` 參數真的排序（AT-963-8-2 要看到順序真的改變）。
 */
type Row = Record<string, unknown>;

// ── 專案（AT-963-8-2）──────────────────────────────────────────────
/** 建立順序＝陣列順序：Charlie、Alpha、Bravo（名稱升冪＝Alpha、Bravo、Charlie，與建立順序不同）。 */
export const PROJECT_NAMES_BY_CREATION = ["Charlie", "Alpha", "Bravo"] as const;

const projectRow = (name: string, i: number): Row => ({
  id: `c0000000-0000-4000-8000-00000000000${i + 1}`,
  name,
  executionPath: `/work/${name}`,
  status: "READY",
  autonomyLevel: 3,
  signedOff: true,
  goalsCount: 1,
  tasksCount: 2,
  tasksDone: 0,
  updatedAt: `2026-11-0${3 - i}T00:00:00Z`,
  createdAt: `2026-11-0${i + 1}T00:00:00Z`,
});

/** `GET /api/v1/projects`：依 `sort=<欄>,<方向>` 排序（createdAt／name／status／updatedAt／autonomyLevel；同值以 createdAt 升冪）。 */
export const projectsBackend: MockHandler = (call) => {
  if (call.method !== "GET" || call.path !== "/api/v1/projects") return undefined;
  const [key = "createdAt", dir = "asc"] = (call.query.get("sort") ?? "createdAt,asc").split(",");
  const rows = PROJECT_NAMES_BY_CREATION.map(projectRow);
  const sign = dir === "desc" ? -1 : 1;
  rows.sort((a, b) => {
    const av = String(a[key] ?? "");
    const bv = String(b[key] ?? "");
    return av < bv ? -sign : av > bv ? sign : String(a.createdAt) < String(b.createdAt) ? -1 : 1;
  });
  return { data: paged(rows, Number(call.query.get("size") ?? 10)) };
};

// ── 議題（AT-963-8-3）──────────────────────────────────────────────
export const LEGEND = (
  JSON.parse(readFileSync(path.join(process.cwd(), "tests", "fixtures", "si", "A.camel.json"), "utf-8")) as { issues: { legend: Row & { statuses: Array<{ name: string; tab: string | null }> } } }
).issues.legend;

function issue(id: string, patch: Row): Row {
  return {
    id,
    source: "系統缺陷",
    title: `${id} 的標題`,
    severity: "中",
    severityRank: 3,
    status: "待解",
    result: null,
    updatedAt: "2026-10-20",
    nextStep: "已成立，尚無人接手",
    origin: { ledger: "缺陷帳本", file: "docs/06_quality/AutoSDD_Defect_Log.md", line: 10 },
    links: [],
    rankable: true,
    action: null,
    priority: null,
    priorityNote: null,
    ...patch,
  };
}

/** 兩列置頂（待您決定）：OBS-SI-005、PROP-SI-004；其餘三列（編號 001、006、007）在「全部」分頁受使用者排序。 */
export const ISSUES: Row[] = [
  issue("OBS-SI-001", { status: "已完成", result: "已裁決", rankable: false, updatedAt: "2026-10-18", severity: "低", severityRank: 4, source: "系統改善" }),
  issue("OBS-SI-005", { status: "待您決定", action: "close-observation", source: "使用者提案", nextStep: "等掌舵者決定：在此關閉並寫下裁決", updatedAt: "2026-10-21" }),
  issue("OBS-SI-006", { title: "緊急的缺陷", severity: "緊急", severityRank: 1, updatedAt: "2026-10-10", links: ["OBS-SI-001"] }),
  issue("OBS-SI-007", { status: "進行中", severity: "高", severityRank: 2, nextStep: "已分流待修", updatedAt: "2026-10-12", source: "系統改善" }),
  issue("PROP-SI-004", {
    status: "待您決定",
    action: "decide-proposal",
    source: "使用者提案",
    severity: null,
    severityRank: null,
    nextStep: "等掌舵者決定：核准、否決或退回",
    updatedAt: "2026-10-20",
  }),
];

const metaOf = () => ({ schemaRev: 1, kind: "issues", generatedAt: "2026-11-08T10:00:00+08:00", headSha: "0".repeat(40), nextSince: null, truncated: false, ne: [], problems: [] });

export const issuesBackend: MockHandler = (call) => {
  if (call.method !== "GET" || call.path !== "/api/v1/issues") return undefined;
  const tabOf = (status: string) => LEGEND.statuses.find((s) => s.name === status)?.tab ?? null;
  const wanted = call.query.get("status");
  const items = ISSUES.filter((i) => wanted === null || wanted.split(",").some((w) => w === i.status || w === tabOf(String(i.status))));
  const byStatus = Object.fromEntries(LEGEND.statuses.map((s) => [s.name, ISSUES.filter((i) => i.status === s.name).length]));
  const count = (tab: string) => ISSUES.filter((i) => tabOf(String(i.status)) === tab).length;
  return {
    data: { ...metaOf(), items, legend: LEGEND, summary: { total: ISSUES.length, byStatus, byTab: { 待處理: count("待處理"), 待您決定: count("待您決定"), 已完成: count("已完成") }, unmapped: 0 } },
  };
};

// ── 備份（AT-963-8-5）──────────────────────────────────────────────
const card = (job: string) => ({
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
});

/** 清單依結束時間新到舊（API 回應序＝預設序）：差異備份、邏輯備份、全備。 */
export const BACKUP_LABELS_DEFAULT = ["20261026-020000F_20261027-020000D", "aisdlc-20261025-183000.dump", "20261026-020000F"] as const;

const backupRow = (kind: string, label: string, location: string, finishedAt: string): Row => ({
  kind,
  label,
  location,
  startedAt: kind === "logical" ? null : finishedAt.replace(/T\d\d/, "T18"),
  finishedAt,
  durationSeconds: kind === "logical" ? null : 120,
  databaseSizeBytes: kind === "logical" ? null : 33554432,
  repoSizeBytes: 1048576,
  baseLabel: null,
  result: "ok",
});

export const backupBackend: MockHandler = (call) => {
  if (call.method !== "GET" || call.path !== "/api/v1/sysadmin/backups") return undefined;
  return {
    data: {
      control: { available: true, canTrigger: false, reason: null, heartbeatAgeSeconds: 5, exportAgeSeconds: 12, exportGeneratedAt: "2026-10-27T06:39:08Z", warnings: [] },
      timezone: "Asia/Taipei",
      activeJob: null,
      cards: ["full", "diff", "dump", "verify"].map(card),
      backups: [
        backupRow("diff", BACKUP_LABELS_DEFAULT[0], "repo1", "2026-10-26T18:02:00Z"),
        backupRow("logical", BACKUP_LABELS_DEFAULT[1], "logical", "2026-10-25T18:30:05Z"),
        backupRow("full", BACKUP_LABELS_DEFAULT[2], "repo1", "2026-10-25T18:10:00Z"),
      ],
      schedule: { entries: [], retention: null },
      repos: [],
      walArchive: { lastArchivedAt: "2026-10-27T02:15:00Z", failedCount: 0, lastFailedAt: null },
    },
  };
};

// ── 研究專案清單（AT-963-8-4）────────────────────────────────────────
const research = (id: string, rpNo: string, title: string, updatedAt: string): Row => ({
  id,
  rpNo,
  slug: title.toLowerCase(),
  title,
  depthLevel: "STANDARD",
  targetScope: "UNDECIDED",
  flowStep: "topic",
  flowPhase: "RESEARCHING",
  flowStatus: "RUNNING",
  flowDetail: "",
  consoleProjectId: null,
  createdBy: "operator",
  createdAt: "2026-11-01T00:00:00Z",
  updatedAt,
  archivedAt: null,
});

/** API 回應序＝最近更新新到舊（RP-0003、RP-0001、RP-0002）；UI 預設依編號升冪；標題升冪＝Alpha(RP-0002)、Mid(RP-0003)、Zeta(RP-0001)。 */
export const RESEARCH_RPNOS_BY_RP = ["RP-0001", "RP-0002", "RP-0003"] as const;
export const RESEARCH_RPNOS_BY_TITLE = ["RP-0002", "RP-0003", "RP-0001"] as const;
export const RESEARCH_LIST: Row[] = [
  research("d0000000-0000-4000-8000-000000000003", "RP-0003", "Mid", "2026-11-05T00:00:00Z"),
  research("d0000000-0000-4000-8000-000000000001", "RP-0001", "Zeta", "2026-11-03T00:00:00Z"),
  research("d0000000-0000-4000-8000-000000000002", "RP-0002", "Alpha", "2026-11-02T00:00:00Z"),
];
