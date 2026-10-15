import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_LAYOUT,
  LAYOUT_STORAGE_KEY,
  SECTION_IDS,
  SECTION_TITLE,
  getLayout,
  getServerLayout,
  moveSection,
  resetLayout,
  resetLayoutCache,
  sanitizeLayout,
  saveLayout,
  subscribeLayout,
  type SectionId,
} from "./monitorLayout";

beforeEach(() => {
  window.localStorage.clear();
  resetLayoutCache();
});
afterEach(() => {
  vi.restoreAllMocks();
});

describe("監控頁版面順序（US-M-08；localStorage 鍵 console.monitor.layout）", () => {
  it("鍵名固定；九個區塊都有標題", () => {
    expect(LAYOUT_STORAGE_KEY).toBe("console.monitor.layout");
    expect(SECTION_IDS).toHaveLength(9);
    for (const id of SECTION_IDS) expect(SECTION_TITLE[id]).toMatch(/\S/);
  });

  it("沒存過：預設順序（同一個常數，引用穩定；SSR 也是它）", () => {
    expect(getLayout()).toBe(DEFAULT_LAYOUT);
    expect(getLayout()).toBe(getLayout());
    expect(getServerLayout()).toBe(DEFAULT_LAYOUT);
  });

  it("淨化：丟未知 id 與重複、保留使用者順序、缺的依預設順序補在尾端；非陣列回預設", () => {
    expect(sanitizeLayout(["logs", "kpi", "logs", "不存在", 42, null])).toEqual(["logs", "kpi", "token", "distribution", "trends", "timeline", "alerts", "compare", "agent"]);
    for (const bad of [null, undefined, "kpi", { kpi: 1 }, 7]) expect(sanitizeLayout(bad)).toEqual([...DEFAULT_LAYOUT]);
  });

  it("拖曳放下：moveSection 把 from 位置的區塊移到 to；越界或相同不變，不修改輸入", () => {
    const order = [...DEFAULT_LAYOUT];
    expect(moveSection(order, 0, 2).slice(0, 3)).toEqual(["token", "distribution", "kpi"]);
    expect(moveSection(order, 8, 0)[0]).toBe("agent");
    expect(moveSection(order, 3, 3)).toEqual(order);
    expect(moveSection(order, -1, 2)).toEqual(order);
    expect(moveSection(order, 2, 99)).toEqual(order);
    expect(order).toEqual([...DEFAULT_LAYOUT]);
  });

  it("存檔：寫進 localStorage、通知訂閱者、下次讀得回來；存回預設順序時用同一個常數", () => {
    const listener = vi.fn();
    const off = subscribeLayout(listener);
    const custom: SectionId[] = ["alerts", ...DEFAULT_LAYOUT.filter((id) => id !== "alerts")];
    saveLayout(custom);
    expect(listener).toHaveBeenCalledTimes(1);
    expect(JSON.parse(window.localStorage.getItem(LAYOUT_STORAGE_KEY) ?? "null")).toEqual(custom);
    expect(getLayout()).toEqual(custom);

    resetLayoutCache(); // 模擬重新整理：從 localStorage 讀回
    expect(getLayout()).toEqual(custom);

    saveLayout([...DEFAULT_LAYOUT]);
    expect(getLayout()).toBe(DEFAULT_LAYOUT);
    off();
    saveLayout(custom);
    expect(listener).toHaveBeenCalledTimes(2); // 取消訂閱後不再通知
  });

  it("重設：移除儲存、回預設、通知訂閱者", () => {
    saveLayout(["agent", ...DEFAULT_LAYOUT.filter((id) => id !== "agent")]);
    const listener = vi.fn();
    subscribeLayout(listener);
    resetLayout();
    expect(window.localStorage.getItem(LAYOUT_STORAGE_KEY)).toBeNull();
    expect(getLayout()).toBe(DEFAULT_LAYOUT);
    expect(listener).toHaveBeenCalled();
  });

  it("儲存內容損毀（不是 JSON、或內容是別的東西）：退回預設，不丟例外", () => {
    window.localStorage.setItem(LAYOUT_STORAGE_KEY, "{not json");
    expect(getLayout()).toBe(DEFAULT_LAYOUT);
    resetLayoutCache();
    window.localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify({ order: ["kpi"] }));
    expect(getLayout()).toBe(DEFAULT_LAYOUT);
    resetLayoutCache();
    window.localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(["agent", "kpi"]));
    expect(getLayout().slice(0, 2)).toEqual(["agent", "kpi"]);
    expect(getLayout()).toHaveLength(9);
  });

  it("localStorage 不可用（隱私模式、額度用盡）：讀寫都吞掉例外，順序仍活在記憶體裡", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("full", "QuotaExceededError");
    });
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });
    expect(getLayout()).toBe(DEFAULT_LAYOUT);
    const custom: SectionId[] = ["logs", ...DEFAULT_LAYOUT.filter((id) => id !== "logs")];
    expect(() => saveLayout(custom)).not.toThrow();
    expect(getLayout()).toEqual(custom);
    expect(() => resetLayout()).not.toThrow();
    expect(getLayout()).toBe(DEFAULT_LAYOUT);
  });
});
