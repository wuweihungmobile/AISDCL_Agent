"use client";

import { usePathname } from "next/navigation";
import { useEffect, useSyncExternalStore } from "react";

import { useAllProjects } from "@/lib/api/queries";
import { forgetProjectId, getLastProjectId, projectIdFromPath, rememberProjectId, resolveCurrentProjectId, subscribeLastProject } from "@/lib/nav/lastProject";

/**
 * 目前專案 id：網址 → 最近造訪 → 列表第一筆；都沒有回 null。
 * 最近造訪若不在「已載入且完整」的列表內（專案已被刪除或封存，DEF-AC-035）即失效：遺忘並退到列表第一筆。
 */
export function useCurrentProjectId(): string | null {
  const pathname = usePathname();
  const all = useAllProjects();
  const fromPath = projectIdFromPath(pathname);
  const last = useSyncExternalStore(subscribeLastProject, getLastProjectId, () => null);
  const { id, stale } = resolveCurrentProjectId({ fromPath, last, page: all.data });

  useEffect(() => {
    if (fromPath) rememberProjectId(fromPath);
  }, [fromPath]);

  // 遺忘是副作用（會通知訂閱者），不能在 render 期間做
  useEffect(() => {
    if (stale && last) forgetProjectId(last);
  }, [stale, last]);

  return id;
}
