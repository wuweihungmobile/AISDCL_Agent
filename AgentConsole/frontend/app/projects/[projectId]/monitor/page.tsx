import type { Metadata } from "next";

import { ProjectShellPage } from "@/components/domain/ProjectShellPage";

export const metadata: Metadata = { title: "專案監控" };

export default function MonitorPage() {
  return <ProjectShellPage kind="monitor" />;
}
