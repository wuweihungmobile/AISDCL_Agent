/**
 * 研發工作流（ResearchToPRD P0）元件測試的共用輔助（TCS-ResearchToPRD-P0-20261102 §5.2「frontend 夾具」）：
 *  - `stubResearchApi`：假後端（fetch 替身），依方法與路徑回放 `tests/fixtures/research/**` 的黃金資料並記錄每次呼叫；測試以 `options` 換資料、
 *    以 `overrides` 逐請求覆寫（回 Response 原樣、回 `{ status, data }` 包成封包、回 undefined 照預設回放）。`options` 是活物件，測試中途改它即換回放內容。
 *  - `renderResearch`：以真 Providers（AuthProvider、TanStack Query、Toast）渲染，並以 `signIn` 設定角色；回傳 `client` 供預先塞快取（例如對帳結果）。
 *  - `writeCalls`／`callsOf`：斷言「沒有任何寫入請求」與取某端點的呼叫。
 * 三個面板包（FE-A 骨架、FE-B 研究面板、FE-C 工作室）共用；不被 vitest 收集、不在 design-rules 掃描面（tests/ 目錄；沿 tests/helpers/api.tsx 先例）。
 * `next/navigation` 與 `next/link` 的替身由各測試檔自己 `vi.mock`（vi.mock 只在宣告它的檔案內生效）。
 */
import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";

import type {
  Role,
  ResearchAllowlistEntry,
  ResearchDecomposition,
  ResearchCapabilities,
  ResearchEvent,
  ResearchEvidenceMatrix,
  ResearchFsmView,
  ResearchPrdVersion,
  ResearchProjectDetail,
  ResearchProjectSummary,
  ResearchRecordsAudit,
  ResearchReviewRound,
  ResearchRouteDecision,
  ResearchRoutePreview,
  ResearchSource,
} from "@/lib/api/types";
import { CONSOLE_PROJECT_ID, CONSOLE_PROJECT_NAME } from "@/tests/fixtures/research/ids";
import { eventPage, EVENTS } from "@/tests/fixtures/research/events";
import { FSM_HUMAN_PENDING } from "@/tests/fixtures/research/fsm";
import { ALLOWLIST, CAPABILITIES_LOCAL, EVIDENCE, RECORDS_AUDIT, SOURCES } from "@/tests/fixtures/research/misc";
import { detailVariant, PROJECT_LIST } from "@/tests/fixtures/research/projects";
import { PREVIEW_A } from "@/tests/fixtures/research/route";
import { FAIL3_ROUNDS, PRD_CONTENT, PRD_VERSIONS } from "@/tests/fixtures/research/reviews";
import { envelope, failure, makeClient, Providers, signIn, stubApi, type ApiCall, type Reply } from "./api";

export { envelope, failure, makeClient, Providers, signIn };
export type { ApiCall, Reply };

export type ResearchStubOptions = {
  /** `"error"`＝能力探針回 503（Bridge 連不上） */
  capabilities: ResearchCapabilities | "error";
  /** 含已封存者：預設的清單請求只回未封存的、帶 `archived=true` 的請求只回已封存的（同真後端） */
  projects: ResearchProjectSummary[];
  /** 依研究專案 id 取詳情；缺的 id 回 404 `research_not_found` */
  details: Record<string, ResearchProjectDetail>;
  events: ResearchEvent[];
  sources: ResearchSource[];
  evidence: ResearchEvidenceMatrix;
  prdVersions: ResearchPrdVersion[];
  /** 單一 PRD 版本的內容（缺省取共用的 PRD 夾具） */
  prdContent: (versionNo: number) => string;
  rounds: ResearchReviewRound[];
  fsm: ResearchFsmView;
  allowlist: ResearchAllowlistEntry[];
  audit: ResearchRecordsAudit;
  /** Console 專案清單（頁首依 `consoleProjectId` 顯示關聯的專案名） */
  consoleProjects: Array<{ id: string; name: string }>;
  /** 系統參數 `execution.*`（字串值，同真後端）；`null`＝該分類回 503 */
  execution: { globalTokenBudget: string; tokenBudgetWarningThreshold: string } | null;
  /** P1：`GET …/route` 回放的分流決定；`null`＝尚未分流（回 200 `null`，D-106） */
  route: ResearchRouteDecision | null;
  /** P1：`POST …/route/preview` 回放的預演結果 */
  preview: ResearchRoutePreview;
  /** P1：`GET …/decomposition` 回放的拆解；`null`＝尚無拆解（回 200 `null`，D-120） */
  decomposition: ResearchDecomposition | null;
  /** 先於預設回放；回 undefined＝照預設 */
  overrides?: (call: ApiCall) => Reply;
};

const DEFAULTS = (): ResearchStubOptions => ({
  capabilities: CAPABILITIES_LOCAL,
  projects: PROJECT_LIST,
  details: { [PROJECT_LIST[1].id]: detailVariant("studio"), [PROJECT_LIST[0].id]: detailVariant("topicRunning"), [PROJECT_LIST[2].id]: detailVariant("frozen") },
  events: EVENTS,
  sources: SOURCES,
  evidence: EVIDENCE,
  prdVersions: PRD_VERSIONS,
  prdContent: () => PRD_CONTENT,
  rounds: FAIL3_ROUNDS,
  fsm: FSM_HUMAN_PENDING,
  allowlist: ALLOWLIST,
  audit: RECORDS_AUDIT,
  consoleProjects: [{ id: CONSOLE_PROJECT_ID, name: CONSOLE_PROJECT_NAME }],
  execution: { globalTokenBudget: "1000000", tokenBudgetWarningThreshold: "0.8" },
  route: null,
  preview: PREVIEW_A,
  decomposition: null,
});

const configRow = (key: string, value: string) => ({ id: `cfg-${key}`, category: "execution", key, value, valueType: "LONG", isEncrypted: false, hasValue: true, effect: "CONSOLE" });

const consoleSummary = (id: string, name: string) => ({
  id,
  name,
  executionPath: `/work/${name}`,
  status: "READY",
  autonomyLevel: 3,
  signedOff: true,
  goalsCount: 1,
  tasksCount: 1,
  tasksDone: 0,
  updatedAt: "2026-11-02T10:00:00Z",
});

const ID = "([^/]+)";
const PROJECT_PATH = new RegExp(`^/api/v1/research/projects/${ID}(/.*)?$`);

/**
 * 假後端：研究端點依預設回放；寫入端點預設回 2xx 的最小收據（測試以 overrides 回特定結果或錯誤）。
 * 回傳的 `options` 是活物件，測試中途可改（例如換成別的詳情）。
 */
export function stubResearchApi(patch: Partial<ResearchStubOptions> = {}): { calls: ApiCall[]; options: ResearchStubOptions } {
  const options: ResearchStubOptions = { ...DEFAULTS(), ...patch };
  const handler = (call: ApiCall): Reply => {
    const custom = options.overrides?.(call);
    if (custom !== undefined) return custom;
    const { method, path } = call;

    if (method === "GET" && path === "/api/v1/projects") {
      const content = options.consoleProjects.map((p) => consoleSummary(p.id, p.name));
      return { data: { content, page: 0, size: 100, totalElements: content.length, totalPages: 1 } };
    }
    if (method === "GET" && path === "/api/v1/settings/execution") {
      if (options.execution === null) return failure(503, { message: "設定暫時不可用" });
      return { data: [configRow("globalTokenBudget", options.execution.globalTokenBudget), configRow("tokenBudgetWarningThreshold", options.execution.tokenBudgetWarningThreshold)] };
    }

    if (method === "GET" && path === "/api/v1/research/capabilities") {
      return options.capabilities === "error" ? failure(503, { message: "Bridge 不可用", reason: "bridge_unreachable" }) : { data: options.capabilities };
    }
    if (method === "GET" && path === "/api/v1/research/allowlist") return { data: options.allowlist };
    if (method === "GET" && path === "/api/v1/research/projects") {
      // 同真後端：清單預設不含已封存的專案，帶 `archived=true` 才列已封存的（TCS AT-960-4-6）
      const archived = call.query.get("archived") === "true";
      return { data: options.projects.filter((p) => (p.archivedAt !== null) === archived) };
    }
    if (method === "POST" && path === "/api/v1/research/projects") {
      const body = call.body as { slug: string; title: string; topic: string };
      return { status: 201, data: { ...detailVariant("topicReady"), id: "99999999-9999-4999-8999-999999999999", slug: body.slug, title: body.title, topic: body.topic, rpNo: "RP-0099" } };
    }

    const match = PROJECT_PATH.exec(path);
    if (match) {
      const id = decodeURIComponent(match[1]);
      const rest = match[2] ?? "";
      const detail = options.details[id];
      if (rest === "" && method === "GET") return detail ? { data: detail } : failure(404, { message: "找不到研究專案", reason: "research_not_found" });
      if (method === "GET") {
        if (rest === "/events") return { data: eventPage(options.events, Number(call.query.get("afterSeq") ?? 0), Number(call.query.get("limit") ?? 500)) };
        if (rest === "/sources") return { data: options.sources };
        if (rest === "/evidence") return { data: options.evidence };
        if (rest === "/prd/versions") return { data: options.prdVersions };
        const version = /^\/prd\/versions\/(\d+)$/.exec(rest);
        if (version) {
          const versionNo = Number(version[1]);
          const row = options.prdVersions.find((v) => v.versionNo === versionNo);
          return row ? { data: { ...row, content: options.prdContent(versionNo) } } : failure(404, { message: "找不到版本", reason: "research_not_found" });
        }
        if (rest === "/review-rounds") return { data: options.rounds };
        const round = /^\/review-rounds\/(\d+)$/.exec(rest);
        if (round) {
          const row = options.rounds.find((r) => r.roundNo === Number(round[1]));
          return row ? { data: row } : failure(404, { message: "找不到審查輪", reason: "research_not_found" });
        }
        if (rest === "/fsm") return { data: options.fsm };
        if (rest === "/records/audit") return { data: options.audit };
      }
      if (method === "GET" && rest === "/route") return { data: options.route };
      if (method === "GET" && rest === "/decomposition") return { data: options.decomposition };
      if (method === "POST" && rest === "/route/preview") return { data: options.preview };
      if (method === "POST" && rest === "/route") return { data: options.route ?? { routeId: "route-new", status: "SUCCEEDED", steps: [] } };
      if (method === "POST" && /^\/stages\/[^/]+$/.test(rest)) return { status: 202, data: { stageRunId: "run-new-1", flowPhase: "RESEARCHING", flowStatus: "RUNNING" } };
      if (method === "POST" && rest === "/reconcile") return { data: { consistent: true, checks: [] } };
      if (method === "POST" && rest === "/reinit") return { data: { flow: detail?.flow } };
      if (method === "POST" && ["/cancel", "/archive", "/restore"].includes(rest)) return { data: {} };
      if (method === "PUT" && rest === "/prd") return { status: 201, data: { ...options.prdVersions[options.prdVersions.length - 1], versionNo: options.prdVersions.length + 1 } };
    }
    return undefined;
  };
  const { calls } = stubApi(handler);
  return { calls, options };
}

/** 寫入類請求（POST、PUT、PATCH、DELETE）：斷言「渲染期間沒有任何寫入」用。 */
export const writeCalls = (calls: readonly ApiCall[]): ApiCall[] => calls.filter((c) => c.method !== "GET");

/** 某方法與路徑樣式的呼叫（路徑以正規式比對）。 */
export const callsOf = (calls: readonly ApiCall[], method: string, pattern: RegExp): ApiCall[] => calls.filter((c) => c.method === method && pattern.test(c.path));

/** 以真 Providers 渲染並登入指定角色；回傳 render 結果與 QueryClient（可預先塞快取）。 */
export function renderResearch(ui: ReactElement, role: Role = "OPERATOR"): RenderResult & { client: ReturnType<typeof makeClient> } {
  signIn(role, role.toLowerCase());
  const client = makeClient();
  return { ...render(<Providers client={client}>{ui}</Providers>), client };
}
