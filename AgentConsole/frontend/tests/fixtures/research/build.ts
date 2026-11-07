import type { ResearchDecomposition, ResearchProjectDetail, ResearchRouteDecision } from "@/lib/api/types";
import { CONSOLE_PROJECT_ID, R3, sha } from "./ids";
import { detailVariant, flowOf } from "./projects";
import { ROUTE_SUCCEEDED } from "./route";

/**
 * 步驟 4 前半（TCS-ResearchToPRD-P1-20261107 AT-961-18-*、20-E-4、25-4）的夾具：游標在 build 步的專案、拆解的各種情境、對帳回應。
 * 拆解樹的鍵用 PRD §5.1.6 的原樣 snake_case（`goal_id`、`task_id`、`covers_ac`）。型別化 DTO 黃金資料，不被 vitest 收集。
 */

/** 游標在 build 步、指定相態與狀態的專案（`stage2Frozen` 這類 FSM 事實由後端衍生進 `flow.effective.phase`：BUILD_READY 即 TCS 已凍結）。 */
export function buildProject(phase: string, status: ResearchProjectDetail["flowStatus"] = "IDLE", patch: { detail?: string; consoleProjectId?: string | null } = {}): ResearchProjectDetail {
  const base = detailVariant("frozen");
  return {
    ...base,
    flowStep: "build",
    flowPhase: phase,
    flowStatus: status,
    flowDetail: patch.detail ?? "",
    consoleProjectId: patch.consoleProjectId === undefined ? CONSOLE_PROJECT_ID : patch.consoleProjectId,
    flow: flowOf(R3, "build", phase, status, { detail: patch.detail }),
  };
}

/** 內環鍵已採納（分流成功、有 Console 專案）的分流列。 */
export const ROUTE_ADOPTED: ResearchRouteDecision = { ...ROUTE_SUCCEEDED, status: "SUCCEEDED", implFsmProject: "demo-app", consoleProjectId: CONSOLE_PROJECT_ID };
/** 分流尚未成功（內環鍵未採納）。 */
export const ROUTE_NOT_ADOPTED: ResearchRouteDecision = { ...ROUTE_SUCCEEDED, status: "FAILED", failureStep: "GIT_SWITCH", implFsmProject: null, consoleProjectId: null };

const task = (id: string, name: string, covers: string[]) => ({ task_id: id, name, prompt: `做${name}`, covers_us: ["US-001"], covers_ac: covers });

/** 5 個 AC：AC-001-1、001-2、002-1 已覆蓋；AC-003-1、AC-004-1 未覆蓋（任務樹只涵蓋前三個）。 */
export const DECOMPOSITION_DRAFT: ResearchDecomposition = {
  id: "decomp-0001",
  status: "DRAFTED",
  tasksCount: 3,
  coverage: { total: 5, covered: 3, uncovered: ["AC-003-1", "AC-004-1"] },
  prdSha256: sha("a"),
  stale: false,
  tcs: { relPath: null, sha256: null },
  goals: [
    { goal_id: "G-1", name: "建立資料層", tasks: [task("T-1", "建表", ["AC-001-1"]), task("T-2", "寫入介面", ["AC-001-2", "AC-002-1"])] },
    { goal_id: "G-2", name: "建立 API", tasks: [task("T-3", "查詢端點", ["AC-001-1"])] },
  ],
  waivers: [],
};

/** 全部覆蓋的草稿（簽核不需豁免）。 */
export const DECOMPOSITION_COVERED: ResearchDecomposition = {
  ...DECOMPOSITION_DRAFT,
  id: "decomp-0002",
  coverage: { total: 3, covered: 3, uncovered: [] },
};

/** 已簽核、未過期。 */
export const DECOMPOSITION_SIGNED: ResearchDecomposition = {
  ...DECOMPOSITION_DRAFT,
  id: "decomp-0003",
  status: "SIGNED_OFF",
  waivers: [
    { ac: "AC-003-1", reason: "由上游服務負責，本專案不實作" },
    { ac: "AC-004-1", reason: "屬後續階段" },
  ],
  signedOffBy: "operator",
  signedOffAt: "2026-11-07T10:00:00+08:00",
};

/** 簽核後 PRD 又更新：`stale` 為真。 */
export const DECOMPOSITION_STALE: ResearchDecomposition = { ...DECOMPOSITION_SIGNED, id: "decomp-0004", stale: true };

/** 草稿且已有 TCS（待凍結／已凍結用）。 */
export const DECOMPOSITION_WITH_TCS: ResearchDecomposition = {
  ...DECOMPOSITION_SIGNED,
  id: "decomp-0005",
  tcs: { relPath: "docs/03_testing/contracts/TCS-rag-eval-20261107.md", sha256: sha("c") },
};

/** 大型 PRD：`acCount` 個 AC、`taskCount` 個 task（每個 AC 被 `i % taskCount` 號 task 涵蓋，最後五個未覆蓋）。 */
export function bigDecomposition(acCount: number, taskCount: number): ResearchDecomposition {
  const acs = Array.from({ length: acCount }, (_, i) => `AC-${String(Math.floor(i / 5) + 1).padStart(3, "0")}-${(i % 5) + 1}`);
  const uncovered = acs.slice(acCount - 5);
  const tasks = Array.from({ length: taskCount }, (_, t) =>
    task(
      `T-${t + 1}`,
      `任務${t + 1}`,
      acs.slice(0, acCount - 5).filter((_, i) => i % taskCount === t),
    ),
  );
  return {
    ...DECOMPOSITION_DRAFT,
    id: "decomp-big",
    tasksCount: taskCount,
    coverage: { total: acCount, covered: acCount - 5, uncovered },
    goals: [{ goal_id: "G-1", name: "大型拆解", tasks }],
  };
}

/** 對帳回應：fsm_flow_mapping 的三種結果（`pending_correction` 是 P1 新增的第三態，型別未含，故以斷言轉型）。 */
export const reconcileWith = (status: "pending_correction" | "drift" | "NOT_EVALUABLE" | "ok") => ({
  consistent: status === "ok",
  checks: [
    { name: "fsm_flow_mapping", status },
    { name: "prd_sha256", status: "ok" },
  ],
});
