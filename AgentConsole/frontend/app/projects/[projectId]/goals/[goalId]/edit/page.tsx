import type { Metadata } from "next";

import { EntityFormPage } from "@/components/domain/entity/EntityFormPage";

export const metadata: Metadata = { title: "編輯目標" };

export default function EditGoalPage() {
  return <EntityFormPage kind="goal" mode="edit" />;
}
