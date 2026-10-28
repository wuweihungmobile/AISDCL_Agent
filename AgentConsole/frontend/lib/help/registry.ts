/**
 * 說明登記表（TCS-PageHelp-20261027 C2、D-PH-2、D-PH-14；PRD §8.1、FR-PH-03、FR-PH-08）：路由樣板→說明 id、已寫頁、待寫頁與路由解析。
 * 三道雙向鎖都以這張表為準（registry.test.ts）：
 *  - 路由鎖：`app/**\/page.tsx` 的路由樣板（括號群組不進網址）減 `/login` ＝ `HELP_ROUTES` 的鍵；新增頁面忘了登記，`npx vitest run` 轉紅並指出修法；
 *  - 導覽鎖：`NAV_REGISTRY` 每個啟用項的 `href` 都解得到說明 id；
 *  - 頁檔鎖：`lib/help/<id>.ts` 的 id 集合＝ `HELP_PAGES` 的鍵 ∪ `PENDING_HELP_PAGES`。
 * 新增頁面的接入步驟：在 `lib/help/<id>.ts` 新增一個 `PageHelp`，把它加進 `HELP_PAGES`，並在 `HELP_ROUTES` 登記路由樣板（樣板用 Next 的資料夾名，例 `[projectId]`）。
 *
 * 分輪：輪 1a 只寫 issues、projects、settings 三頁，其餘 13 頁的頁檔是佔位並列在 `PENDING_HELP_PAGES`（路由鎖在所有輪次都成立，所以 `HELP_ROUTES` 含它們的路由；
 * 沒有已寫內容的頁不渲染「本頁說明」鈕——由按鈕以 `HELP_PAGES[id]` 判，缺＝不渲染）。每一棒把寫好的頁自 `PENDING_HELP_PAGES` 移進 `HELP_PAGES`，
 * 並同 commit 下修 registry.test.ts 的 `PENDING_CEILING`；輪 3 出口為空（G-F8）。輪 2 已寫 dashboard、project-detail、goals、goal-detail、tasks、task-detail、
 * 三個表單頁與 import（天花板 13→3）；輪 3 寫完 execute、monitor、self-improving，`PENDING_HELP_PAGES` 清空、天花板 3→0，十六頁全數已寫。
 * 清空之後，姊妹案新增頁面若先列 pending，須同 commit 上修天花板並於 PR 說明 WHY（D-PH-14）。
 */
import { dashboard } from "./dashboard";
import { execute } from "./execute";
import { goalDetail } from "./goal-detail";
import { goalForm } from "./goal-form";
import { goals } from "./goals";
import { importPage } from "./import";
import { issues } from "./issues";
import { monitor } from "./monitor";
import { projectDetail } from "./project-detail";
import { projectForm } from "./project-form";
import { projects } from "./projects";
import { selfImproving } from "./self-improving";
import { settings } from "./settings";
import { taskDetail } from "./task-detail";
import { taskForm } from "./task-form";
import { tasks } from "./tasks";
import type { HelpId, PageHelp } from "./types";

/** 已寫頁（不含 `PENDING_HELP_PAGES`）；鍵＝`PageHelp.id`。 */
export const HELP_PAGES: Readonly<Partial<Record<HelpId, PageHelp>>> = {
  dashboard,
  projects,
  "project-detail": projectDetail,
  goals,
  "goal-detail": goalDetail,
  tasks,
  "task-detail": taskDetail,
  "project-form": projectForm,
  "goal-form": goalForm,
  "task-form": taskForm,
  execute,
  monitor,
  import: importPage,
  settings,
  "self-improving": selfImproving,
  issues,
};

/**
 * 尚未寫的頁（頁檔為佔位）；每輪只准縮小，輪 3 為空（十六頁全數已寫）。
 * 2026-10-28 姊妹案「系統管理／資料庫備份」（TCS-SysAdminBackup-20261027 AT-BK-01-2-4、D-PH-14）新增 /sysadmin、/sysadmin/backup 兩頁，先以佔位列入 pending
 * （同 commit 上修 registry.test.ts 的 PENDING_CEILING 0→2）；由每頁說明補頁棒寫實、移進 HELP_PAGES 並把天花板下修回 0。
 */
export const PENDING_HELP_PAGES: readonly HelpId[] = ["sysadmin", "sysadmin-backup"];

/** `states` 為空的頁（沒有會變動的狀態；對話框的狀態段只顯示固定一句）。與頁內容雙向相等：states 為空者必在這裡，這裡的頁 states 必為空。 */
export const NO_STATE_PAGES: readonly HelpId[] = ["project-form", "task-form", "settings"];

/** 路由樣板→說明 id（含 pending 頁的路由；不含 `/login`：登入頁沒有說明）。樣板是 Next 的資料夾名，根路由為 `/`。 */
export const HELP_ROUTES: Readonly<Record<string, HelpId>> = {
  "/": "dashboard",
  "/projects": "projects",
  "/projects/[projectId]": "project-detail",
  "/projects/[projectId]/goals": "goals",
  "/projects/[projectId]/goals/[goalId]": "goal-detail",
  "/projects/[projectId]/goals/[goalId]/tasks": "tasks",
  "/projects/[projectId]/goals/[goalId]/tasks/[taskId]": "task-detail",
  "/projects/new": "project-form",
  "/projects/[projectId]/edit": "project-form",
  "/projects/[projectId]/goals/new": "goal-form",
  "/projects/[projectId]/goals/[goalId]/edit": "goal-form",
  "/projects/[projectId]/goals/[goalId]/tasks/new": "task-form",
  "/projects/[projectId]/goals/[goalId]/tasks/[taskId]/edit": "task-form",
  "/projects/[projectId]/execute": "execute",
  "/projects/[projectId]/monitor": "monitor",
  "/import": "import",
  "/settings": "settings",
  "/self-improving": "self-improving",
  "/issues": "issues",
  "/sysadmin": "sysadmin",
  "/sysadmin/backup": "sysadmin-backup",
};

const DYNAMIC_SEGMENT = /^\[[^\]]+\]$/;

/** `/a/b/` → ["a", "b"]；根路徑 `/` → []；不是以 `/` 起頭（含空字串）→ null。只去掉一個尾斜線。 */
function segmentsOf(pathname: string): string[] | null {
  if (!pathname.startsWith("/")) return null;
  const parts = pathname.split("/").slice(1);
  if (parts.length > 0 && parts[parts.length - 1] === "") parts.pop();
  return parts;
}

const PATTERNS: ReadonlyArray<{ id: HelpId; segments: readonly string[]; statics: number }> = Object.entries(HELP_ROUTES).map(([template, id]) => {
  const segments = segmentsOf(template) ?? [];
  return { id, segments, statics: segments.filter((segment) => !DYNAMIC_SEGMENT.test(segment)).length };
});

/**
 * 路由→說明 id，只做解析（D-PH-2）：靜態段優先於動態段（`/projects/new` 取 `project-form`，不被 `[projectId]` 吃掉）、去尾斜線、大小寫敏感、每個路徑恰一個 id；
 * 動態段只要求非空（URL 編碼或中文的 id 也算）。空字串、未知路徑、前綴相似（`/projects-x`）、多一段、`/login` 都回 `null`。
 * 與 `PENDING_HELP_PAGES` 無關：待寫頁的路由照樣回它的 id（「這頁有沒有已寫的說明」由呼叫端以 `HELP_PAGES[id]` 判）。
 * 同樣符合的樣板取靜態段最多者；平手取登記在前者（現行路由表沒有平手，測試鎖「最具體者唯一」）。
 */
export function helpForPath(pathname: string): HelpId | null {
  const concrete = segmentsOf(pathname);
  if (concrete === null) return null;
  let best: { id: HelpId; statics: number } | null = null;
  for (const pattern of PATTERNS) {
    if (pattern.segments.length !== concrete.length) continue;
    const matches = pattern.segments.every((segment, i) => (DYNAMIC_SEGMENT.test(segment) ? concrete[i] !== "" : segment === concrete[i]));
    if (matches && (best === null || pattern.statics > best.statics)) best = pattern;
  }
  return best?.id ?? null;
}
