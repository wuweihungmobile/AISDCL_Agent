import type { Metadata } from "next";

import { EntityFormPage } from "@/components/domain/entity/EntityFormPage";

export const metadata: Metadata = { title: "編輯任務" };

export default function EditTaskPage() {
  return <EntityFormPage kind="task" mode="edit" />;
}
