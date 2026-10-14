import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginForm } from "@/components/domain/LoginForm";

export const metadata: Metadata = { title: "登入" };

export default function LoginPage() {
  // LoginForm 讀 useSearchParams（next 參數），靜態預先渲染時需要 Suspense 邊界
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
