import type { Metadata } from "next";

import { EntityFormPage } from "@/components/domain/entity/EntityFormPage";

export const metadata: Metadata = { title: "新建目標" };

export default function NewGoalPage() {
  return <EntityFormPage kind="goal" mode="create" />;
}
