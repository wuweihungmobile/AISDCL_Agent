import type { PageHelp } from "./types";

/** 佔位（輪 1a）：目標詳情（`/projects/[projectId]/goals/[goalId]`）的說明尚未撰寫，列在 registry.ts 的 PENDING_HELP_PAGES；輪 2 寫實並登記進 HELP_PAGES。路由鎖已涵蓋它的路由。 */
export const goalDetail: PageHelp = { id: "goal-detail", title: "目標詳情", purpose: [], steps: [], fields: [], states: [], sourceFiles: [] };
