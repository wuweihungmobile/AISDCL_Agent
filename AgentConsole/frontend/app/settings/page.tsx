import type { Metadata } from "next";

import { SettingsView } from "@/components/domain/settings/SettingsView";

export const metadata: Metadata = { title: "系統參數設定" };

export default function SettingsPage() {
  return <SettingsView />;
}
