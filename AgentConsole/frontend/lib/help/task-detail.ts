import type { PageHelp } from "./types";

/** 佔位（輪 1a）：任務詳情（`/projects/[projectId]/goals/[goalId]/tasks/[taskId]`）的說明尚未撰寫，列在 registry.ts 的 PENDING_HELP_PAGES；輪 2 寫實並登記進 HELP_PAGES。路由鎖已涵蓋它的路由。 */
export const taskDetail: PageHelp = { id: "task-detail", title: "任務詳情", purpose: [], steps: [], fields: [], states: [], sourceFiles: [] };
