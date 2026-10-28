import type { Metadata } from "next";

import { BackupView } from "@/components/domain/sysadmin/BackupView";

export const metadata: Metadata = { title: "資料庫備份" };

export default function SysAdminBackupPage() {
  return <BackupView />;
}
