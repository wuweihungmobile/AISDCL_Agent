/**
 * 議題中心元件測試的共用夾具與假後端（TCS-IssueCenter-20261027 §5.4、§5.6；測試支援檔，不被 vitest 收集）。
 * 檔名是 `*.fixtures.ts` 並放在 `tests/` 子目錄：靜態鎖（issues.static.test.ts；沿 si.static.test.ts 的 walk 略過 `tests` 目錄，另明寫排除 `*.fixtures.ts`）
 * 不會把夾具內的七個狀態詞當成違規——元件與 lib/domain/issues.ts 本身才受「不得持有狀態詞清單」約束。
 *
 * 內容：
 *  - LEGEND：取自入庫的黃金檔（tests/fixtures/si/A.camel.json 的 `issues.legend`，真 CLI 輸出）；測試要改字就 clone 後改，不污染共用的那份。
 *  - ISSUES：涵蓋七狀態、八結果、四來源、四嚴重度，以及 null 與表外值（「未歸類：…」）的議題；真帳本才有的 ID 只用黃金檔裡有的（OBS-SI-001～011、PROP-SI-004、PROP-SI-005），
 *    其餘合成缺陷一律 `DEF-999-nnn`（999 族為測試保留）。
 *  - stubIssuesApi／renderIssues：以 fetch 替身回放議題中心的四個端點（GET 清單與單筆、PUT 與 DELETE 優先順序）與決定、關閉對話框用到的三個自我進化端點；
 *    記錄每次呼叫的方法、網址與本文；清單的 `since`／`limit`／`status` 語意同 console-api（游標＝夾具陣列位置加一，篩選先於分頁）。
 */
import { render, type RenderResult } from "@testing-library/react";
import { readFileSync } from "node:fs";
import path from "node:path";
import { createElement, type ReactElement } from "react";
import { vi } from "vitest";

import { Providers } from "@/components/providers/Providers";
import { ToastHost } from "@/components/ui/toast";
import type { Issue, IssueLegend, IssueListPage, IssuePage, IssueSummary, Role, SiNeEntry, SiPage, SiProblem, SiProposal } from "@/lib/api/types";
import { clearSession, resetSessionCache, saveSession } from "@/lib/auth/store";
import { envelope, failure } from "@/tests/helpers/api";

type Golden = { issues: IssueListPage; proposals: SiPage<SiProposal> };
const GOLDEN: Golden = JSON.parse(readFileSync(path.join(process.cwd(), "tests", "fixtures", "si", "A.camel.json"), "utf-8")) as Golden;

/** 深拷貝（測試要改寫資料時用，不污染共用的夾具）。 */
export function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export const LEGEND: IssueLegend = GOLDEN.issues.legend;
/** 黃金檔的提案快照（PROP-SI-004：帶卡面與 digest；「決定」對話框綁它的 digest）。 */
export const PROPOSAL: SiProposal = GOLDEN.proposals.items[0];

// ── 議題夾具 ──────────────────────────────────────────────────────────────────────

const NEXT_BY_STATUS: Record<string, string> = {
  待解: "已成立，尚無人接手",
  進行中: "已分流待修",
  觀察中: "量測窗 1／5",
  待您決定: "等掌舵者決定：核准、否決或退回",
  候選: "等歸因確認（歸因者提出、審查者確認），或由掌舵者簽核成立",
  延後: "等再開症狀出現：同一症狀於另一輪再現（帳本原文 open、deferred 為英文節錄）",
};

/** 一個議題：預設是可排的「待解」缺陷（中嚴重度）；`patch` 逐欄覆寫。下一步依狀態給預設句。 */
export function makeIssue(id: string, patch: Partial<Issue> = {}): Issue {
  const status = patch.status ?? "待解";
  const result = patch.result ?? null;
  return {
    id,
    source: "系統缺陷",
    title: `${id} 的標題`,
    severity: "中",
    severityRank: 3,
    status,
    result,
    updatedAt: "2026-10-20",
    nextStep: result !== null ? `已結案（${result}）` : (NEXT_BY_STATUS[status] ?? "帳本值不在對照表內，請查原列"),
    origin: { ledger: "缺陷帳本", file: "docs/06_quality/AutoSDD_Defect_Log.md", line: 10 },
    links: [],
    rankable: true,
    action: null,
    priority: null,
    priorityNote: null,
    ...patch,
  };
}

/** 單筆才有的 raw 與 timeline 預設（原列值刻意是英文原值：它是唯一可見英文的地方）。 */
export const DEFAULT_RAW = [
  { label: "處置", value: "open" },
  { label: "症狀", value: "原列的症狀全文，含 deferred 與 handed-off 等英文原值" },
];
export const DEFAULT_TIMELINE = [{ seq: 3, t: "2026-10-18T10:00:00+08:00", by: "orchestrator", action: "新增觀察" }];

/** 十八個議題（游標序＝陣列序）：五個待處理、兩個待您決定、八個已完成（八種結果各一）、候選、延後與一個表外值各一。 */
export function makeIssues(): Issue[] {
  const done = (id: string, result: string, updatedAt: string, patch: Partial<Issue> = {}) => makeIssue(id, { status: "已完成", result, updatedAt, rankable: false, ...patch });
  return [
    done("OBS-SI-001", "已裁決", "2026-10-18", { source: "系統改善", severity: "低", severityRank: 4, title: "需求原文要求另一種副檔名" }),
    done("OBS-SI-002", "已合併", "2026-10-18", { source: "系統改善", title: "額度守衛回報的並行數太小", links: ["OBS-SI-001", "DEF-999-404"] }),
    makeIssue("OBS-SI-003", { source: "使用者提案", severity: "低", severityRank: 4, status: "延後", rankable: false, updatedAt: "2026-10-18", title: "探針要用拋棄式狀態目錄" }),
    makeIssue("OBS-SI-004", { source: "研究提案", severity: "低", severityRank: 4, status: "候選", rankable: false, updatedAt: "2026-10-19", title: "外部文章建議以多代理互審降低誤判" }),
    makeIssue("OBS-SI-005", {
      source: "使用者提案",
      status: "待您決定",
      updatedAt: "2026-10-21",
      action: "close-observation",
      title: "症狀含腳本字樣 <script>window.__xss=1</script> 與 **粗體**、`行內碼` 與 [連結](https://example.invalid/x)",
      nextStep: "等掌舵者決定：在此關閉並寫下裁決",
    }),
    makeIssue("OBS-SI-006", { source: "系統缺陷", severity: "緊急", severityRank: 1, status: "待解", updatedAt: "2026-10-10", title: "緊急的缺陷" }),
    makeIssue("OBS-SI-007", { source: "系統改善", severity: "高", severityRank: 2, status: "進行中", updatedAt: "2026-10-12", title: "有人在修的改善" }),
    makeIssue("OBS-SI-008", { source: "系統改善", severity: null, severityRank: null, status: "觀察中", rankable: false, updatedAt: "2026-10-15", title: "嚴重度量不到的觀察" }),
    makeIssue("OBS-SI-009", { source: "系統缺陷", severity: "未歸類：P5", severityRank: null, status: "待解", updatedAt: null, title: "嚴重度為表外值、日期解不出" }),
    done("OBS-SI-010", "已修復", "2026-10-05", { source: "使用者提案", severity: "高", severityRank: 2, title: "已修好的問題" }),
    done("OBS-SI-011", "已採納", "2026-10-25", { source: "研究提案", title: "已採納的提案相關觀察" }),
    makeIssue("PROP-SI-004", {
      source: "使用者提案",
      severity: null,
      severityRank: null,
      status: "待您決定",
      updatedAt: "2026-10-20",
      action: "decide-proposal",
      title: "新測試檔撞棘輪、守門誤判、重釘輪號走錯",
      origin: { ledger: "事件帳本", file: "docs/06_quality/SelfImproving_Event_Ledger.jsonl", seq: 5 },
      links: ["OBS-SI-009", "DEF-999-404"],
    }),
    done("PROP-SI-005", "已否決", "2026-10-22", {
      source: "系統改善",
      severity: "低",
      severityRank: 4,
      title: "已否決的提案",
      origin: { ledger: "事件帳本", file: "docs/06_quality/SelfImproving_Event_Ledger.jsonl", seq: 9 },
    }),
    done("DEF-999-001", "已退役", "2026-10-01", { severity: "緊急", severityRank: 1, title: "已退役的缺陷" }),
    done("DEF-999-002", "已轉交", "2026-10-02", { severity: "低", severityRank: 4, title: "已轉交的缺陷" }),
    done("DEF-999-003", "已回滾", "2026-10-03", { title: "已回滾的缺陷" }),
    makeIssue("DEF-999-004", { source: "未歸類：later", status: "未歸類：later", rankable: false, updatedAt: "2026-10-04", title: "狀態是表外值的缺陷" }),
    makeIssue("DEF-999-005", { source: null, severity: "高", severityRank: 2, status: "待解", updatedAt: "2026-10-09", title: "來源讀不到的缺陷" }),
  ];
}

// ── 假後端 ─────────────────────────────────────────────────────────────────────────

export type IssuesCall = { method: string; url: string; path: string; query: URLSearchParams; body: string | null };
export type IssuesEndpoint = "list" | "one" | "put" | "delete" | "proposal" | "decide" | "close";
/** 逐端點覆寫：回 Response（原樣）、或回 { status, data }（包成封包）；回 undefined＝照夾具回放。可為 async（延遲回應）。 */
export type IssuesOverride = (call: IssuesCall) => Response | { status?: number; data?: unknown } | undefined | Promise<Response | { status?: number; data?: unknown } | undefined>;

export type IssuesStub = {
  /** 游標序的議題（游標＝位置加一）；測試可在中途改寫 */
  items: Issue[];
  legend: IssueLegend;
  ne: SiNeEntry[];
  problems: SiProblem[];
  /** 已設定的順位（議題編號→{rank, note}）：PUT、DELETE 會改它；清單與單筆的 priority 取自它（僅可排的列） */
  priorities: Map<string, { rank: number; note: string }>;
  /** 摘要的覆寫（例：把某格設為 null）；缺＝依 items 與 legend 計算 */
  summary?: (computed: IssueSummary) => IssueSummary;
  overrides: Partial<Record<IssuesEndpoint, IssuesOverride>>;
  calls: IssuesCall[];
  /** 預設收據的 auditRef 序號 */
  auditSeq: number;
};

export function newStub(options: { items?: Issue[]; legend?: IssueLegend; overrides?: IssuesStub["overrides"] } = {}): IssuesStub {
  return { items: options.items ?? makeIssues(), legend: options.legend ?? LEGEND, ne: [], problems: [], priorities: new Map(), overrides: { ...options.overrides }, calls: [], auditSeq: 0 };
}

/** 摘要：整本帳計數（不受篩選與游標影響）；`byTab` 的三格依圖例的 tab 欄加總。 */
export function summaryOf(items: ReadonlyArray<Issue>, legend: IssueLegend): IssueSummary {
  const byStatus: Record<string, number> = {};
  for (const s of legend.statuses) byStatus[s.name] = items.filter((i) => i.status === s.name).length;
  const sumTab = (tab: string) => legend.statuses.filter((s) => s.tab === tab).reduce((n, s) => n + (byStatus[s.name] ?? 0), 0);
  const unmapped = items.filter((i) => i.status.startsWith(legend.unmappedLabel)).length;
  return {
    total: Object.values(byStatus).reduce((a, b) => a + b, 0) + unmapped,
    byStatus,
    byTab: { 待處理: sumTab("待處理"), 待您決定: sumTab("待您決定"), 已完成: sumTab("已完成") },
    unmapped,
  };
}

function inFilter(item: Issue, stub: IssuesStub, status: string | null, source: string | null): boolean {
  const tab = stub.legend.statuses.find((s) => s.name === item.status)?.tab ?? null;
  const statusOk = status === null || status.split(",").some((w) => w === item.status || (tab !== null && w === tab));
  const sourceOk = source === null || source.split(",").some((w) => w === item.source);
  return statusOk && sourceOk;
}

/** 可排的列取假後端記下的順位；不可排的列原樣（夾具可自帶遺留順位，用來驗證前端不顯示它、不拿它排序）。 */
function withPriority(stub: IssuesStub, item: Issue): Issue {
  if (!item.rankable) return item;
  const row = stub.priorities.get(item.id);
  return { ...item, priority: row ? row.rank : null, priorityNote: row ? row.note : null };
}

function pageMeta() {
  return { schemaRev: 1, kind: "issues" as const, generatedAt: "2026-10-27T10:00:00+08:00", headSha: "0".repeat(40) };
}

function listPage(stub: IssuesStub, query: URLSearchParams): IssueListPage {
  const since = query.has("since") ? Number(query.get("since")) : 0;
  const limit = query.has("limit") ? Number(query.get("limit")) : Infinity;
  const indexed = stub.items.map((item, i) => ({ item, cursor: i + 1 })).filter(({ item }) => inFilter(item, stub, query.get("status"), query.get("source")));
  const after = indexed.filter(({ cursor }) => cursor > since);
  const page = after.slice(0, limit);
  const truncated = after.length > page.length;
  const computed = summaryOf(stub.items, stub.legend);
  return {
    ...pageMeta(),
    items: page.map(({ item }) => withPriority(stub, item)),
    nextSince: truncated ? page[page.length - 1].cursor : null,
    truncated,
    ne: stub.ne,
    problems: stub.problems,
    legend: stub.legend,
    summary: stub.summary ? stub.summary(computed) : computed,
  };
}

function onePage(stub: IssuesStub, id: string): IssuePage | null {
  const item = stub.items.find((i) => i.id === id);
  if (!item) return null;
  return { ...pageMeta(), items: [{ ...withPriority(stub, item), raw: DEFAULT_RAW, timeline: DEFAULT_TIMELINE }], nextSince: null, truncated: false, ne: stub.ne, problems: stub.problems };
}

export function notFound(id: string): Response {
  return failure(404, { message: "查無此議題", reason: "si_not_found", details: { id } });
}

export function unavailable(cause = "nonzero_rc", detail = "rc=2; stderr=boom 全形字元"): Response {
  return failure(503, { message: "SI 資料面不可用", reason: "si_unavailable", details: { cause, detail } });
}

/** 409 的逐字訊息（與契約 reason 表、ISSUE_REASONS 相同）。 */
const ISSUE_NOT_RANKABLE_MESSAGE = "此議題目前的狀態不能設定優先順序";

type Target = { endpoint: IssuesEndpoint; id?: string };

/** 方法加路徑→端點。 */
function endpointOf(method: string, pathname: string): Target | null {
  const issue = /^\/api\/v1\/issues\/([^/]+)(\/priority)?$/.exec(pathname);
  if (method === "GET" && pathname === "/api/v1/issues") return { endpoint: "list" };
  if (method === "GET" && issue && !issue[2]) return { endpoint: "one", id: decodeURIComponent(issue[1]) };
  if (method === "PUT" && issue?.[2]) return { endpoint: "put", id: decodeURIComponent(issue[1]) };
  if (method === "DELETE" && issue?.[2]) return { endpoint: "delete", id: decodeURIComponent(issue[1]) };
  const proposal = /^\/api\/v1\/si\/proposals\/([^/]+)(\/decide)?$/.exec(pathname);
  if (method === "GET" && proposal && !proposal[2]) return { endpoint: "proposal", id: decodeURIComponent(proposal[1]) };
  if (method === "POST" && proposal?.[2]) return { endpoint: "decide", id: decodeURIComponent(proposal[1]) };
  const close = /^\/api\/v1\/si\/observations\/([^/]+)\/close$/.exec(pathname);
  if (method === "POST" && close) return { endpoint: "close", id: decodeURIComponent(close[1]) };
  return null;
}

function receipt(stub: IssuesStub, kind: "decide" | "obs-close", subject: string): Response {
  stub.auditSeq += 1;
  return envelope({ auditRef: `a1000000-0000-4000-8000-${String(stub.auditSeq).padStart(12, "0")}`, kind, subject, time: "2026-10-27T10:00:15+08:00", keyId: "f076edf0" }, 201);
}

function replay(stub: IssuesStub, target: Target, call: IssuesCall, username: string): Response {
  const id = target.id ?? "";
  switch (target.endpoint) {
    case "list":
      return envelope(listPage(stub, call.query));
    case "one": {
      const page = onePage(stub, id);
      return page ? envelope(page) : notFound(id);
    }
    case "put": {
      const item = stub.items.find((i) => i.id === id);
      if (!item) return notFound(id);
      if (!item.rankable) return failure(409, { message: ISSUE_NOT_RANKABLE_MESSAGE, reason: "issue_not_rankable", details: { id, status: item.status } });
      const body = JSON.parse(call.body ?? "{}") as { rank: number; note?: string };
      stub.priorities.set(id, { rank: body.rank, note: body.note ?? "" });
      return envelope({ id, rank: body.rank, note: body.note ?? "", setBy: username, setAt: "2026-10-27T10:00:30+08:00" });
    }
    case "delete":
      stub.priorities.delete(id);
      return envelope(null, 204);
    case "proposal":
      return id === PROPOSAL.id
        ? envelope({ ...pageMeta(), kind: "proposals", items: [PROPOSAL], nextSince: null, truncated: false, ne: [], problems: [] })
        : failure(404, { message: "查無此提案", reason: "si_not_found", details: { id } });
    case "decide":
      return receipt(stub, "decide", id);
    case "close":
      return receipt(stub, "obs-close", id);
  }
}

/** 以 fetch 替身取代全域 fetch：每次呼叫先記錄，再依覆寫或夾具回應；沒有對應端點回 404。 */
export function stubIssuesApi(stub: IssuesStub, username = "admin"): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init: RequestInit = {}) => {
      const url = new URL(input, "http://api.test");
      const method = init.method ?? "GET";
      const call: IssuesCall = { method, url: url.pathname + url.search, path: url.pathname, query: url.searchParams, body: typeof init.body === "string" ? init.body : null };
      stub.calls.push(call);
      const target = endpointOf(method, url.pathname);
      if (!target) return failure(404, { message: `測試沒有處理 ${call.method} ${call.url}` });
      const override = stub.overrides[target.endpoint];
      const reply = override ? await override(call) : undefined;
      if (reply instanceof Response) return reply;
      if (reply) return envelope(reply.data, reply.status ?? 200);
      return replay(stub, target, call, username);
    }),
  );
}

/** 寫入已登入狀態（sessionStorage）。 */
export function signInAs(role: Role, username = role === "ADMIN" ? "admin" : "viewer"): void {
  resetSessionCache();
  clearSession();
  saveSession({ accessToken: "a", refreshToken: "r", expiresAt: Date.now() + 1e6, role, username });
}

/** 渲染（真 Providers＋ToastHost）：登入指定角色、掛假後端；回傳 testing-library 的結果加上 stub 與 urls()（已發出的網址）。 */
export function renderIssues(
  ui: ReactElement,
  options: { role?: Role; username?: string; stub?: IssuesStub } = {},
): RenderResult & { stub: IssuesStub; urls: () => string[]; writes: () => IssuesCall[] } {
  const role = options.role ?? "VIEWER";
  const stub = options.stub ?? newStub();
  signInAs(role, options.username);
  stubIssuesApi(stub, options.username ?? (role === "ADMIN" ? "admin" : "viewer"));
  const view = render(createElement(Providers, null, ui, createElement(ToastHost)));
  return { ...view, stub, urls: () => stub.calls.map((c) => c.url), writes: () => stub.calls.filter((c) => c.method !== "GET") };
}
