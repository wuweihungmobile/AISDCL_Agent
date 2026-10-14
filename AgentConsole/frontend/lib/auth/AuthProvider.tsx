"use client";

/**
 * 登入狀態的 React 介面。資料來源是 lib/auth/store.ts（sessionStorage）：
 *  - status：loading（尚未水合）／authed／anon，頁面據此決定顯示內容或導向 /login；
 *  - login／logout：登入寫入 session、登出清 session 與 TanStack Query 快取；
 *  - 向 lib/api/client.ts 註冊「登入失效」處理器，401 換新失敗時用 Next router 導向（不整頁重載）。
 * 沒有任何 setState：用 useSyncExternalStore 讀 store，避免「effect 內同步 setState」的重繪連鎖。
 */
import { useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";

import { setUnauthorizedHandler } from "@/lib/api/client";
import { login as apiLogin } from "@/lib/api/endpoints";
import type { Role } from "@/lib/api/types";
import {
  canWrite as roleCanWrite,
  clearSession,
  jwtSubject,
  loadSession,
  saveSession,
  subscribeSession,
  type Session,
} from "./store";

export type AuthStatus = "loading" | "authed" | "anon";

export type AuthContextValue = {
  status: AuthStatus;
  session: Session | null;
  username: string;
  role: Role | undefined;
  /** 寫入類按鈕是否可用（VIEWER 唯讀；後端另有 RBAC） */
  canWrite: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const noopSubscribe = () => () => {};

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();

  // 水合前（伺服器端與第一次 client render）一律視為 loading，避免已登入者被誤導去 /login
  const hydrated = useSyncExternalStore(
    noopSubscribe,
    () => true,
    () => false,
  );
  const session = useSyncExternalStore(subscribeSession, loadSession, () => null);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      queryClient.clear();
      const here = window.location.pathname + window.location.search;
      if (window.location.pathname !== "/login") {
        router.replace(`/login?next=${encodeURIComponent(here)}`);
      }
    });
    return () => setUnauthorizedHandler(null);
  }, [queryClient, router]);

  const login = useCallback(async (username: string, password: string) => {
    const name = username.trim();
    const tokens = await apiLogin(name, password);
    saveSession({
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
      expiresAt: Date.now() + tokens.expiresIn * 1000,
      role: tokens.role as Role,
      username: jwtSubject(tokens.accessToken) ?? name,
    });
  }, []);

  const logout = useCallback(() => {
    clearSession();
    queryClient.clear();
    router.replace("/login");
  }, [queryClient, router]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status: !hydrated ? "loading" : session ? "authed" : "anon",
      session,
      username: session?.username ?? "",
      role: session?.role,
      canWrite: roleCanWrite(session?.role),
      login,
      logout,
    }),
    [hydrated, session, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth 必須在 <AuthProvider> 之內使用");
  return ctx;
}

/** 登入頁用：已登入就導回 next（預設 /）。 */
export function useRedirectWhenAuthed(next: string): void {
  const { status } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (status === "authed" && pathname === "/login") router.replace(next);
  }, [status, pathname, next, router]);
}
