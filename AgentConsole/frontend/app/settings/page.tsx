import { Settings } from "lucide-react";
import type { Metadata } from "next";

import { PageTitle } from "@/components/domain/PageHeader";
import { PlaceholderCard } from "@/components/domain/PlaceholderCard";

export const metadata: Metadata = { title: "系統參數設定" };

export default function SettingsPage() {
  return (
    <div>
      <PageTitle title="系統參數設定" icon={Settings} />
      <PlaceholderCard phase="Phase 6">
        模型／Agent／執行／監控／AutoClaude／SDD 六類參數、測試連線、修改歷史與匯出匯入設定將在這裡呈現。
      </PlaceholderCard>
    </div>
  );
}
