import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  window.sessionStorage.clear();
});

// jsdom 沒有的瀏覽器 API：Markdown 編輯器與 Radix 元件會用到
if (typeof window.matchMedia !== "function") {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
if (!("ResizeObserver" in globalThis)) {
  // 直接定義而不用 vi.stubGlobal：上面的 afterEach 會 unstubAllGlobals，stub 版只有第一個測試看得到，
  // 後面的測試遇到 Radix 的 Checkbox／Popover（use-size）就會丟「ResizeObserver is not defined」
  Object.defineProperty(globalThis, "ResizeObserver", { value: ResizeObserverStub, writable: true, configurable: true });
}
