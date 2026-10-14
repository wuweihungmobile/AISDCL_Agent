import type { Metadata } from "next";

import { ProjectShellPage } from "@/components/domain/ProjectShellPage";

export const metadata: Metadata = { title: "專案執行" };

export default function ExecutePage() {
  return <ProjectShellPage kind="execute" />;
}
