"use client";

/**
 * Content 區（UI-LAY-03）＝設計稿 Main：路由內容容器，負責捲動（右欄獨立垂直捲動）與登入閘。
 * children 由 app/layout.tsx 傳入；容器 max-width 1440 與左右欄 gap 32px 的外框同樣在 layout 組裝。
 * 登入閘：未登入者導向 /login?next=…（後端才是真正的授權邊界，這裡只做體驗層）。
 */
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/AuthProvider";

export function ContentRegion({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const isLogin = pathname === "/login";

  useEffect(() => {
    if (status === "anon" && !isLogin) {
      const here = window.location.pathname + window.location.search;
      router.replace(`/login?next=${encodeURIComponent(here)}`);
    }
  }, [status, isLogin, router]);

  const blocked = !isLogin && status !== "authed";

  return (
    <main id="main-content" data-region="content" className="min-w-0 flex-1 overflow-y-auto pb-12 max-md:pb-6">
      {blocked ? (
        <div className="flex h-64 items-center justify-center">
          <Spinner />
        </div>
      ) : (
        children
      )}
    </main>
  );
}
