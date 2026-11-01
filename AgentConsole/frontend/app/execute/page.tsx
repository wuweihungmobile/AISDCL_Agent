import type { Metadata } from "next";

import { CenterEntryView } from "@/components/domain/entry/CenterEntryView";

export const metadata: Metadata = { title: "執行中心" };

export default function ExecuteEntryPage() {
  return <CenterEntryView kind="execute" />;
}
