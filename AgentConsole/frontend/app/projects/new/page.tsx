import type { Metadata } from "next";

import { EntityFormPage } from "@/components/domain/entity/EntityFormPage";

export const metadata: Metadata = { title: "新建專案" };

export default function NewProjectPage() {
  return <EntityFormPage kind="project" mode="create" />;
}
