import type { Metadata } from "next";

import { EntityFormPage } from "@/components/domain/entity/EntityFormPage";

export const metadata: Metadata = { title: "編輯專案" };

export default function EditProjectPage() {
  return <EntityFormPage kind="project" mode="edit" />;
}
