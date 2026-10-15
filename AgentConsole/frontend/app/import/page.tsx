import type { Metadata } from "next";
import { Suspense } from "react";

import { ImportView } from "@/components/domain/import/ImportView";

export const metadata: Metadata = { title: "BRD/PRD 智能匯入" };

export default function ImportPage() {
  // ImportView 讀 useSearchParams（?id= 目前操作的匯入記錄），靜態預先渲染時需要 Suspense 邊界
  return (
    <Suspense>
      <ImportView />
    </Suspense>
  );
}
