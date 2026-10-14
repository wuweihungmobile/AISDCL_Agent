import type { Metadata } from "next";

import { ProjectDetailView } from "@/components/domain/views/ProjectDetailView";

export const metadata: Metadata = { title: "專案詳情" };

export default function ProjectDetailPage() {
  return <ProjectDetailView />;
}
