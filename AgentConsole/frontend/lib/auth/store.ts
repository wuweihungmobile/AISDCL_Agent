/**
 * 登入狀態存放（ADR-001 D4：token 存 sessionStorage，關分頁即失效）。
 * 這裡只做「讀／寫／清除／訂閱」，不碰網路；換 token 的流程在 lib/api/client.ts。
 *  - SSR 安全：沒有 window 時一律回 null，不丟例外。
 *  - 以模組內快取提供「引用穩定」的快照，讓 React 的 useSyncExternalStore 不會無限重繪。
 */
import type { Role } from "@/lib/api/types";

export type Session = {
  accessToken: string;
  refreshToken: string;
  /** access token 到期的 epoch 毫秒（登入時以 expiresIn 推算） */
  expiresAt: number;
  role: Role;
  username: string;
};

export const SESSION_KEY = "aisdlc.console.session";

type Listener = () => void;
const listeners = new Set<Listener>();

/** undefined＝尚未從 sessionStorage 讀過 */
let cache: Session | null | undefined;

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    // 隱私模式或被禁用時 sessionStorage 存取會丟例外；視為沒有登入狀態
    return null;
  }
}

function readFromStorage(): Session | null {
  const raw = storage()?.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<Session>;
    if (typeof parsed.accessToken === "string" && typeof parsed.refreshToken === "string" && typeof parsed.username === "string") {
      return {
        accessToken: parsed.accessToken,
        refreshToken: parsed.refreshToken,
        expiresAt: typeof parsed.expiresAt === "number" ? parsed.expiresAt : 0,
        role: (parsed.role as Role) ?? "VIEWER",
        username: parsed.username,
      };
    }
  } catch {
    // 損毀的內容當作未登入
  }
  return null;
}

function notify(): void {
  listeners.forEach((fn) => fn());
}

/** 目前登入狀態（引用穩定；寫入／清除才會換新物件）。 */
export function loadSession(): Session | null {
  if (cache === undefined) cache = readFromStorage();
  return cache;
}

export function saveSession(session: Session): void {
  cache = session;
  storage()?.setItem(SESSION_KEY, JSON.stringify(session));
  notify();
}

export function clearSession(): void {
  cache = null;
  storage()?.removeItem(SESSION_KEY);
  notify();
}

/** 丟掉快取、下次重新讀 sessionStorage（測試與跨頁籤同步用，不通知訂閱者）。 */
export function resetSessionCache(): void {
  cache = undefined;
}

export function subscribeSession(fn: Listener): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

export function getAccessToken(): string | null {
  return loadSession()?.accessToken ?? null;
}

/** 寫入類操作需要的角色（VIEWER 唯讀；後端另有 RBAC 二次校驗，前端只做體驗層）。 */
export function canWrite(role: Role | undefined): boolean {
  return role === "ADMIN" || role === "OPERATOR";
}

/** 解 JWT 的 sub（只用於顯示使用者名稱，不驗簽；驗證在後端）。 */
export function jwtSubject(token: string): string | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    const sub = (JSON.parse(json) as { sub?: unknown }).sub;
    return typeof sub === "string" ? sub : null;
  } catch {
    return null;
  }
}
