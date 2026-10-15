import type { Metadata } from "next";

import { ExecuteView } from "@/components/domain/execute/ExecuteView";

export const metadata: Metadata = { title: "專案執行" };

export default function ExecutePage() {
  return <ExecuteView />;
}
