import type { Metadata } from "next";

import { ResearchListView } from "@/components/domain/research/ResearchListView";

export const metadata: Metadata = { title: "研發工作流" };

export default function ResearchPage() {
  return <ResearchListView />;
}
