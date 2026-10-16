import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SDD_PROJECT_STORAGE_KEY, getRememberedSddProject, getServerRememberedSddProject, rememberSddProject, resetSddProjectCache, subscribeSddProject } from "./sddProject";

beforeEach(() => {
  window.localStorage.clear();
  resetSddProjectCache();
});
afterEach(() => {
  vi.restoreAllMocks();
});

describe("AISDLC_SDD 卡記住上次選的 FSM 專案（契約 §4.3 M-20；localStorage 鍵 console.monitor.sddProject）", () => {
  it("鍵名固定；沒存過回 null；SSR 與水合第一次渲染永遠是 null", () => {
    expect(SDD_PROJECT_STORAGE_KEY).toBe("console.monitor.sddProject");
    expect(getRememberedSddProject()).toBeNull();
    expect(getServerRememberedSddProject()).toBeNull();
  });

  it("記住：寫進 localStorage、通知訂閱者、重新整理（丟快取）後讀得回來；取消訂閱後不再通知", () => {
    const listener = vi.fn();
    const off = subscribeSddProject(listener);
    rememberSddProject("e2e-bravo");
    expect(listener).toHaveBeenCalledTimes(1);
    expect(window.localStorage.getItem(SDD_PROJECT_STORAGE_KEY)).toBe("e2e-bravo");
    expect(getRememberedSddProject()).toBe("e2e-bravo");

    resetSddProjectCache(); // 模擬重新整理：從 localStorage 讀回
    expect(getRememberedSddProject()).toBe("e2e-bravo");

    off();
    rememberSddProject("e2e-alpha");
    expect(listener).toHaveBeenCalledTimes(1);
    expect(getRememberedSddProject()).toBe("e2e-alpha");
  });

  it("儲存內容是空字串：當作沒存過", () => {
    window.localStorage.setItem(SDD_PROJECT_STORAGE_KEY, "");
    expect(getRememberedSddProject()).toBeNull();
  });

  it("localStorage 不可用（隱私模式、額度用盡）：讀寫都吞掉例外，選擇仍活在記憶體裡", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("full", "QuotaExceededError");
    });
    expect(getRememberedSddProject()).toBeNull();
    expect(() => rememberSddProject("e2e-alpha")).not.toThrow();
    expect(getRememberedSddProject()).toBe("e2e-alpha");
  });
});
