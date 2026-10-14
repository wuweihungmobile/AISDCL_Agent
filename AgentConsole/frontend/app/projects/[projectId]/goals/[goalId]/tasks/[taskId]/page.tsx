import type { Metadata } from "next";

import { TaskDetailView } from "@/components/domain/views/TaskDetailView";

export const metadata: Metadata = { title: "任務詳情" };

export default function TaskDetailPage() {
  return <TaskDetailView />;
}
