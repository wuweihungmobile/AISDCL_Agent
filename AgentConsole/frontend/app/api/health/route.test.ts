import { describe, expect, it } from "vitest";

import { GET } from "./route";

describe("前端健康檢查（API-HLT-03）", () => {
  it("回 200 與 {status:'ok'}，不依賴後端（Docker HEALTHCHECK 只問這個 Next 行程活著）", async () => {
    const res = GET();
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ status: "ok" });
  });
});
