import type { Metadata } from "next";

import { IssuesView } from "@/components/domain/issues/IssuesView";

export const metadata: Metadata = { title: "議題中心" };

export default function IssuesPage() {
  return <IssuesView />;
}
