import type { Metadata } from "next";

import { CenterEntryView } from "@/components/domain/entry/CenterEntryView";

export const metadata: Metadata = { title: "監控中心" };

export default function MonitorEntryPage() {
  return <CenterEntryView kind="monitor" />;
}
