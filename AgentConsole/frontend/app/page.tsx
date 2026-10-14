import type { Metadata } from "next";

import { DashboardView } from "@/components/domain/views/DashboardView";

export const metadata: Metadata = { title: "總覽儀表板" };

export default function DashboardPage() {
  return <DashboardView />;
}
