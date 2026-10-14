import type { Metadata } from "next";

import { GoalDetailView } from "@/components/domain/views/GoalDetailView";

export const metadata: Metadata = { title: "目標詳情" };

export default function GoalDetailPage() {
  return <GoalDetailView />;
}
