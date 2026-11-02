import type { Metadata } from "next";

import { AllowlistDialog } from "@/components/domain/research/AllowlistDialog";
import { ResearchListView } from "@/components/domain/research/ResearchListView";

export const metadata: Metadata = { title: "研發工作流" };

export default function ResearchPage() {
  // 「研究來源設定」入口接在清單標題列（外部動作；元件自己判定 ADMIN 才顯示）
  return <ResearchListView extraActions={<AllowlistDialog />} />;
}
