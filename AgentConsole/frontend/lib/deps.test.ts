import { createRequire } from "node:module";
import { describe, expect, it } from "vitest";

import { version as reactVersion } from "react";

/**
 * 守住 package.json 的 overrides["react-is"]：recharts 2.x 依賴 react-is 18，與 React 19 並用時
 * Area／YAxis 等子元件會「靜默不渲染」（沒有錯誤訊息，只有圖表缺一半）。overrides 被拿掉時這支要轉紅。
 */
describe("圖表相依：react-is 必須與 React 同主版本", () => {
  it("recharts 解析到的 react-is 主版本等於 React 主版本", () => {
    const req = createRequire(import.meta.url);
    const fromRecharts = createRequire(req.resolve("recharts"));
    const reactIs = fromRecharts("react-is/package.json") as { version: string };
    expect(reactIs.version.split(".")[0]).toBe(reactVersion.split(".")[0]);
  });
});
