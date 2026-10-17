import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { EXECUTION_WARNING_CODES, GOVERNANCE_INACTIVE_CAUSES, PARSE_WARNING_CODES, REASONS, URL_VIOLATION_LABEL } from "./reasons";

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

/**
 * B.5（v1.5，整合輪 115）第一張表「console-api 的 ApiError.reason」：| HTTP | reason | details 鍵 | 端點與觸發 |。
 * 同節後面的「Bridge 自己的錯誤封包 reason」表與「回應本文的警告碼」不是 ApiError.reason，不在這裡（另有專屬斷言）。
 */
function b5ApiErrorReasons(): string[] {
  const start = md.indexOf("### B.5");
  expect(start, "找不到契約的 B.5").toBeGreaterThan(-1);
  const lines = md.slice(start).split("\n");
  const first = lines.findIndex((l) => l.startsWith("|"));
  expect(first, "B.5 找不到第一張表").toBeGreaterThan(-1);
  const out: string[] = [];
  for (const line of lines.slice(first)) {
    if (!line.startsWith("|")) break;
    const cells = line
      .split("|")
      .slice(1, -1)
      .map((c) => c.trim());
    if (/^-+$/.test(cells[0]) || cells[0] === "HTTP") continue;
    out.push(...backticked(cells[1]));
  }
  return out;
}

/** B.1 表：| HTTP | reason |；B.2 表：| 區 | HTTP | reason | details |；B.5 第一張表見 b5ApiErrorReasons。 */
function contractReasons(): string[] {
  const out: string[] = [];
  for (const line of appendixB().split("\n")) {
    if (!line.startsWith("|")) continue;
    const cells = line
      .split("|")
      .slice(1, -1)
      .map((c) => c.trim());
    if (cells.length < 2 || /^-+$/.test(cells[0]) || cells[0] === "HTTP" || cells[0] === "區") continue;
    const reasonCell = cells.length === 2 ? cells[1] : cells[2];
    out.push(...backticked(reasonCell));
  }
  return [...out, ...b5ApiErrorReasons()];
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

describe("v1.5 SDD 治理常數（契約 §0.3 第 8 點、附錄 B.5；整合輪 115）", () => {
  it("B.5 第一張表恰好是六個 console-api 的 ApiError.reason：五個 sdd_* 與 404 的例外 rtm_not_found（逐字，各有常數）", () => {
    const b5 = b5ApiErrorReasons();
    expect([...b5].sort()).toEqual(["rtm_not_found", "sdd_binding_conflict", "sdd_fsm_not_found", "sdd_fsm_state_conflict", "sdd_spec_digest_changed", "sdd_write_disabled"]);
    const have = new Set<string>(Object.values(REASONS));
    expect(b5.filter((r) => !have.has(r))).toEqual([]);
    expect(REASONS.SDD_FSM_STATE_CONFLICT).toBe("sdd_fsm_state_conflict");
    expect(REASONS.SDD_FSM_NOT_FOUND).toBe("sdd_fsm_not_found");
    expect(REASONS.SDD_SPEC_DIGEST_CHANGED).toBe("sdd_spec_digest_changed");
    expect(REASONS.SDD_BINDING_CONFLICT).toBe("sdd_binding_conflict");
    expect(REASONS.SDD_WRITE_DISABLED).toBe("sdd_write_disabled");
    expect(REASONS.RTM_NOT_FOUND).toBe("rtm_not_found");
  });

  it("警告碼不是 ApiError.reason：不進 REASONS，但每個碼都在契約的〈回應本文的警告碼〉段與 §1.10.5 的 cause 表裡（契約改字就轉紅）", () => {
    const reasonValues = new Set<string>(Object.values(REASONS));
    for (const code of [...Object.values(EXECUTION_WARNING_CODES), ...Object.values(PARSE_WARNING_CODES)]) {
      expect(reasonValues.has(code), `${code} 不該進 REASONS`).toBe(false);
      expect(md, `契約找不到警告碼 ${code}`).toContain(`\`${code}\``);
    }
    const start = md.indexOf("**回應本文的警告碼與 alert 碼**");
    expect(start, "找不到〈回應本文的警告碼與 alert 碼〉段").toBeGreaterThan(-1);
    const paragraph = md.slice(start, md.indexOf("\n", start));
    for (const code of [...Object.values(EXECUTION_WARNING_CODES), ...Object.values(PARSE_WARNING_CODES)]) expect(paragraph, `警告碼段沒有 ${code}`).toContain(`\`${code}\``);
    for (const cause of GOVERNANCE_INACTIVE_CAUSES) expect(paragraph, `警告碼段的 cause 沒有 ${cause}`).toContain(`\`${cause}\``);
    expect(new Set(GOVERNANCE_INACTIVE_CAUSES).size).toBe(GOVERNANCE_INACTIVE_CAUSES.length);
  });
});
