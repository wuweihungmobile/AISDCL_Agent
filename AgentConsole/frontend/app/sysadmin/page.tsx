import type { Metadata } from "next";

import { SysAdminHome } from "@/components/domain/sysadmin/SysAdminHome";

export const metadata: Metadata = { title: "系統管理" };

export default function SysAdminPage() {
  return <SysAdminHome />;
}
