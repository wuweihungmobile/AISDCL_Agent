import type { Metadata } from "next";

import { PageTitle } from "@/components/domain/PageHeader";
import { PlaceholderCard } from "@/components/domain/PlaceholderCard";

export const metadata: Metadata = { title: "BRD/PRD 智能匯入" };

export default function ImportPage() {
  return (
    <div className="max-w-[960px]">
      <PageTitle
        title="BRD / PRD 智能匯入"
        subtitle="AI 解析需求文件 → 自動拆解三層結構 → 人工 signoff 後落為正式專案"
      />
      <PlaceholderCard phase="Phase 3">
        輸入來源（上傳檔案／貼上文字／歷史記錄）、AI 解析、結構預覽與編輯、signoff 審批與確認匯入將在這裡呈現。
      </PlaceholderCard>
    </div>
  );
}
