import type { Metadata } from "next";
import { Suspense } from "react";

import { ProjectsView } from "@/components/domain/views/ProjectsView";

export const metadata: Metadata = { title: "專案管理" };

export default function ProjectsPage() {
  // ProjectsView 讀 useSearchParams（?q= 搜尋），靜態預先渲染時需要 Suspense 邊界
  return (
    <Suspense>
      <ProjectsView />
    </Suspense>
  );
}
