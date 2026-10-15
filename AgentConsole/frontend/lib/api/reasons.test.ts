import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { REASONS, URL_VIOLATION_LABEL } from "./reasons";

/**
 * 為什麼要解析契約而不是抄一份期望值：reason 是前後端「逐字相同」的常數，E2E 以字串逐字比對，
 * 少一個全形標點或多一個空白就整批對不上。期望值一律取自契約附錄 B 本身（SSOT），
 * 契約改字、新增常數時這支測試會轉紅，逼著 lib/api/reasons.ts 同步。
 */
const CONTRACT = path.join(process.cwd(), "..", "docs", "02_architecture", "API_Contract_P3-6.md");
const md = readFileSync(CONTRACT, "utf-8");

function appendixB(): string {
  const start = md.indexOf("## 附錄 B");
  const end = md.indexOf("### B.3", start);
  expect(start, "找不到契約的附錄 B").toBeGreaterThan(-1);
  expect(end, "找不到契約的 B.3（附錄 B 的結尾）").toBeGreaterThan(start);
  return md.slice(start, end);
}

const backticked = (cell: string): string[] => [...cell.matchAll(/`([^`]+)`/g)].map((m) => m[1]);

/** B.1 表：| HTTP | reason |；B.2 表：| 區 | HTTP | reason | details |。 */
function contractReasons(): string[] {
  const out: string[] = [];
  for (const line of appendixB().split("\n")) {
    if (!line.startsWith("|")) continue;
    const cells = line.split("|").slice(1, -1).map((c) => c.trim());
    if (cells.length < 2 || /^-+$/.test(cells[0]) || cells[0] === "HTTP" || cells[0] === "區") continue;
    const reasonCell = cells.length === 2 ? cells[1] : cells[2];
    out.push(...backticked(reasonCell));
  }
  return out;
}

describe("lib/api/reasons.ts 與契約附錄 B 逐字一致", () => {
  it("契約附錄 B 的每個 reason 都有對應常數（契約有、前端沒有＝紅）", () => {
    const contract = contractReasons();
    expect(contract.length, "附錄 B 解析不到足夠的 reason，表格格式可能變了").toBeGreaterThan(50);
    const have = new Set<string>(Object.values(REASONS));
    expect(contract.filter((r) => !have.has(r))).toEqual([]);
  });

  it("前端沒有契約之外的常數（不得自己造英文代碼）", () => {
    const contract = new Set(contractReasons());
    expect(Object.values(REASONS).filter((r) => !contract.has(r))).toEqual([]);
  });

  it("常數值互不重複（同一個字串不會對到兩個意思）", () => {
    const values = Object.values(REASONS);
    expect(new Set(values).size).toBe(values.length);
  });

  it("PRD 逐字指定的兩個 reason 沒被改寫", () => {
    expect(REASONS.EXEC_UNSIGNED_DRAFT).toBe("未經人工審批的草案不可執行");
    expect(REASONS.SETTINGS_TOKEN_GUARD_ORDER).toBe("halt_threshold_pct 必須大於 compact_threshold_pct");
  });

  it("URL_VIOLATION_LABEL 涵蓋契約列出的 details.violation 全部值", () => {
    const m = /`violation` ∈ `([^`]+)`/.exec(appendixB());
    expect(m, "附錄 B 找不到 violation 值域").not.toBeNull();
    const violations = (m as RegExpExecArray)[1].split(",").map((s) => s.trim());
    expect(Object.keys(URL_VIOLATION_LABEL).sort()).toEqual(violations.sort());
  });
});
