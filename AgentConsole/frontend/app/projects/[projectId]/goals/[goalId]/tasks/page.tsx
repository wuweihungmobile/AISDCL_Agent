import type { Metadata } from "next";

import { TasksListPage } from "@/components/domain/views/ListPages";

export const metadata: Metadata = { title: "任務列表" };

export default function TasksPage() {
  return <TasksListPage />;
}
