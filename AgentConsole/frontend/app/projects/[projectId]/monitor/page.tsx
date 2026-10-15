import type { Metadata } from "next";

import { MonitorView } from "@/components/domain/monitor/MonitorView";

export const metadata: Metadata = { title: "專案監控" };

export default function MonitorPage() {
  return <MonitorView />;
}
