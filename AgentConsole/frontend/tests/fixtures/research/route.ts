import type { ResearchCapabilities, ResearchRouteDecision, ResearchRoutePreview, ResearchRouteStep } from "@/lib/api/types";
import { CONSOLE_PROJECT_ID, T0, T1 } from "./ids";
import { CAPABILITIES_LOCAL } from "./misc";

/** 分流全可用的能力探針（git、gh、可寫 monorepo、有骨架根與範本）：TCS-ResearchToPRD-P1-20261107 AT-961-16-5 的「全可用」組。 */
export const CAPABILITIES_ROUTE_READY: ResearchCapabilities = {
  ...CAPABILITIES_LOCAL,
  ghCli: { ok: true, authenticated: false },
  scaffoldRoot: "<骨架根>",
  scaffoldTemplates: ["python-fastapi"],
  repoWritable: true,
};

/** 能力探針各缺項（AT-961-16-5 的七組）：名稱即停用條件。 */
export const CAPABILITIES_ROUTE_VARIANTS = {
  full: CAPABILITIES_ROUTE_READY,
  noGit: { ...CAPABILITIES_ROUTE_READY, git: { ok: false } },
  repoReadOnly: { ...CAPABILITIES_ROUTE_READY, repoWritable: false },
  noGh: { ...CAPABILITIES_ROUTE_READY, ghCli: { ok: false, authenticated: false } },
  noScaffoldRoot: { ...CAPABILITIES_ROUTE_READY, scaffoldRoot: null },
  noTemplates: { ...CAPABILITIES_ROUTE_READY, scaffoldTemplates: [] },
  mockOnly: { ...CAPABILITIES_ROUTE_READY, mode: "mock-only", claudeCli: { ok: false } },
} as const satisfies Record<string, ResearchCapabilities>;

const PRD = { versionNo: 4, semver: "v1.0.0", sha256: "a".repeat(64), targetScope: "AISDLC_MODULE", scopeDiffers: false };

/** 軌道 A 預演：只有本地動作。 */
export const PREVIEW_A: ResearchRoutePreview = {
  track: "A",
  prd: PRD,
  implFsmProject: "autoclaude-rag-eval",
  actions: [
    { seq: 1, action: "validate_target", step: "VALIDATE_TARGET", target: "AutoClaude", touchesExternal: false, detail: "驗證目標模組與分支名" },
    { seq: 2, action: "worktree_add", step: "GIT_SWITCH", target: "feature/issue-0003", touchesExternal: false, detail: "在獨立工作樹建立分支" },
  ],
  expectedTrackedFiles: [],
  warnings: [],
};

/** 軌道 B 預演：含觸及外部系統的建遠端動作，與一個內含 `<script>` 字串的目標（驗證純文字渲染）。 */
export const PREVIEW_B: ResearchRoutePreview = {
  track: "B",
  prd: { ...PRD, targetScope: "STANDALONE_PROJECT" },
  implFsmProject: "demo-app",
  actions: [
    { seq: 1, action: "scaffold_render", step: "SCAFFOLD_FILES", target: "<script>alert(1)</script>/demo-app", touchesExternal: false, detail: "展開 python-fastapi 範本" },
    { seq: 2, action: "gh_repo_create", step: "GH_REPO_CREATE", target: "acme/demo-app", touchesExternal: true, detail: "建立 GitHub 遠端" },
  ],
  expectedTrackedFiles: ["README.md", "pyproject.toml"],
  warnings: [{ code: "public_repo_warning", message: "PRD 與證據矩陣將公開" }],
};

const step = (stepNo: number, name: string, status: ResearchRouteStep["status"], extra: Partial<ResearchRouteStep> = {}): ResearchRouteStep => ({
  stepNo,
  step: name,
  status,
  argvRedacted: "git worktree add",
  exitCode: status === "OK" ? 0 : null,
  stdoutTail: "",
  stderrTail: "",
  startedAt: T0,
  finishedAt: status === "RUNNING" ? null : T1,
  ...extra,
});

const ROW = {
  routeId: "route-0001",
  track: "A",
  targetKind: "MODULE",
  targetModule: "autoclaude",
  targetPath: "AutoClaude",
  gitBranch: "feature/issue-0003",
  baseRef: "main",
  repoUrl: null,
  repoVisibility: null,
  stackTemplate: null,
  consoleProjectId: null,
  implFsmProject: "autoclaude-rag-eval",
} as const;

export const ROUTE_RUNNING: ResearchRouteDecision = { ...ROW, status: "RUNNING", failureStep: null, steps: [step(1, "VALIDATE_TARGET", "OK"), step(2, "GIT_SWITCH", "RUNNING")] };

/** 失敗：第二步失敗（`stderrTail` 為脫敏後原因），第一步已成功。 */
export const ROUTE_FAILED: ResearchRouteDecision = {
  ...ROW,
  status: "FAILED",
  failureStep: "GIT_SWITCH",
  steps: [step(1, "VALIDATE_TARGET", "OK"), step(2, "GIT_SWITCH", "FAILED", { exitCode: 128, stderrTail: "fatal: 分支已存在（路徑已脫敏）" })],
};

export const ROUTE_SUCCEEDED: ResearchRouteDecision = {
  ...ROW,
  track: "B",
  targetKind: "STANDALONE",
  targetModule: null,
  targetPath: "demo-app",
  gitBranch: "main",
  baseRef: null,
  repoUrl: "https://github.com/acme/demo-app",
  repoVisibility: "PRIVATE",
  stackTemplate: "python-fastapi",
  consoleProjectId: CONSOLE_PROJECT_ID,
  implFsmProject: "demo-app",
  status: "SUCCEEDED",
  failureStep: null,
  steps: [step(1, "VALIDATE_TARGET", "OK"), step(2, "SCAFFOLD_FILES", "OK"), step(3, "GH_REPO_CREATE", "OK")],
};
