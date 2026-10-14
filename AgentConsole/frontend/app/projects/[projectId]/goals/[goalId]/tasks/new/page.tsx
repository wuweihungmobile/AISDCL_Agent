import type { Metadata } from "next";

import { EntityFormPage } from "@/components/domain/entity/EntityFormPage";

export const metadata: Metadata = { title: "新建任務" };

export default function NewTaskPage() {
  return <EntityFormPage kind="task" mode="create" />;
}
