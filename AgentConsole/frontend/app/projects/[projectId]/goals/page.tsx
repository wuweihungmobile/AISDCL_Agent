import type { Metadata } from "next";

import { GoalsListPage } from "@/components/domain/views/ListPages";

export const metadata: Metadata = { title: "目標列表" };

export default function GoalsPage() {
  return <GoalsListPage />;
}
