import { beforeEach, describe, expect, it, vi } from "vitest";

import { SESSION_KEY, canWrite, clearSession, getAccessToken, jwtSubject, loadSession, resetSessionCache, saveSession, subscribeSession, type Session } from "./store";

const S: Session = { accessToken: "a", refreshToken: "r", expiresAt: 1, role: "ADMIN", username: "admin" };

beforeEach(() => {
  resetSessionCache();
  clearSession();
});

describe("auth store（sessionStorage）", () => {
  it("存、讀、清；token 存在 sessionStorage 而不是 localStorage", () => {
    expect(loadSession()).toBeNull();
    saveSession(S);
    expect(JSON.parse(window.sessionStorage.getItem(SESSION_KEY) ?? "{}")).toMatchObject({ accessToken: "a" });
    expect(window.localStorage.getItem(SESSION_KEY)).toBeNull();
    expect(getAccessToken()).toBe("a");
    clearSession();
    expect(loadSession()).toBeNull();
  });

  it("快照引用穩定（useSyncExternalStore 不會無限重繪）", () => {
    saveSession(S);
    expect(loadSession()).toBe(loadSession());
  });

  it("訂閱者在存／清時被通知", () => {
    const fn = vi.fn();
    const off = subscribeSession(fn);
    saveSession(S);
    clearSession();
    expect(fn).toHaveBeenCalledTimes(2);
    off();
    saveSession(S);
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it("損毀的 sessionStorage 內容視為未登入", () => {
    window.sessionStorage.setItem(SESSION_KEY, "{not json");
    resetSessionCache();
    expect(loadSession()).toBeNull();
  });

  it("只有 ADMIN／OPERATOR 可寫入（VIEWER 唯讀）", () => {
    expect(canWrite("ADMIN")).toBe(true);
    expect(canWrite("OPERATOR")).toBe(true);
    expect(canWrite("VIEWER")).toBe(false);
    expect(canWrite(undefined)).toBe(false);
  });

  it("解 JWT 的 sub 只用於顯示", () => {
    const payload = btoa(JSON.stringify({ sub: "operator", role: "OPERATOR" }));
    expect(jwtSubject(`h.${payload}.s`)).toBe("operator");
    expect(jwtSubject("garbage")).toBeNull();
  });
});
