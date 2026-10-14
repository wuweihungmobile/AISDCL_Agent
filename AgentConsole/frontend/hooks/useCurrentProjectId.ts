"use client";

import { usePathname } from "next/navigation";
import { useEffect, useSyncExternalStore } from "react";

import { useAllProjects } from "@/lib/api/queries";
import {
  getLastProjectId,
  projectIdFromPath,
  rememberProjectId,
  subscribeLastProject,
} from "@/lib/nav/lastProject";

/** 目前專案 id：網址 → 最近造訪 → 列表第一筆；都沒有回 null。 */
export function useCurrentProjectId(): string | null {
  const pathname = usePathname();
  const all = useAllProjects();
  const fromPath = projectIdFromPath(pathname);
  const last = useSyncExternalStore(subscribeLastProject, getLastProjectId, () => null);

  useEffect(() => {
    if (fromPath) rememberProjectId(fromPath);
  }, [fromPath]);

  return fromPath ?? last ?? all.data?.content[0]?.id ?? null;
}
