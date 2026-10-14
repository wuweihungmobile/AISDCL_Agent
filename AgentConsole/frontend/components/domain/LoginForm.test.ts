import { describe, expect, it } from "vitest";

import { safeNext } from "./LoginForm";

describe("登入後導回（next 參數）", () => {
  it("只接受站內相對路徑，避免開放式轉址", () => {
    expect(safeNext("/projects?q=a")).toBe("/projects?q=a");
    expect(safeNext(null)).toBe("/");
    expect(safeNext("")).toBe("/");
    expect(safeNext("https://evil.example/")).toBe("/");
    expect(safeNext("//evil.example/x")).toBe("/");
    expect(safeNext("javascript:alert(1)")).toBe("/");
  });
});
