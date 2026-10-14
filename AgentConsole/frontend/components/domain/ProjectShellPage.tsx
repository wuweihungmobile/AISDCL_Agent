"use client";

import { Activity, Play } from "lucide-react";
import { useParams } from "next/navigation";

import { BackLink, PageTitle } from "@/components/domain/PageHeader";
import { PlaceholderCard } from "@/components/domain/PlaceholderCard";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/states";
import { useProject } from "@/lib/api/queries";

const COPY = {
  execute: {
    icon: Play,
    title: "專案執行",
    subtitle: "漸進式自治 · DAG 排程 · 斷點續行",
    phase: "Phase 4",
    body: "執行控制（自治等級、Token 預算、執行範圍、啟動／暫停／恢復／取消）、執行進度、DAG 依賴視覺化、即時日誌（SSE）與待審核項目將在這裡呈現。",
  },
  monitor: {
    icon: Activity,
    title: "專案監控",
    subtitle: "指標 · 趨勢 · 日誌 · 告警",
    phase: "Phase 5",
    body: "KPI 指標卡、Token 使用趨勢、任務狀態與執行時間分佈、執行日誌查詢與告警將在這裡呈現。",
  },
} as const;

/** 執行／監控頁的路由殼：只顯示設計稿標題列與占位卡（W4 填內容）。 */
export function ProjectShellPage({ kind }: { kind: keyof typeof COPY }) {
  const { projectId } = useParams<{ projectId: string }>();
  const project = useProject(projectId);
  const c = COPY[kind];

  return (
    <div>
      <BackLink href={`/projects/${projectId}`}>返回專案</BackLink>
      {project.isError ? (
        <ErrorState error={project.error} onRetry={() => project.refetch()} />
      ) : (
        <>
          <PageTitle
            icon={c.icon}
            title={
              <>
                {c.title}：
                {project.data ? project.data.name : <Skeleton className="inline-block h-7 w-48 align-middle" />}
              </>
            }
            subtitle={c.subtitle}
            className="[&_h2]:text-[28px]"
          />
          <PlaceholderCard phase={c.phase}>{c.body}</PlaceholderCard>
        </>
      )}
    </div>
  );
}
