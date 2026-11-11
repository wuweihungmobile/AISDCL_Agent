/**
 * 黃金樣本複本的先行測試（TCS-SiFlowVisibility §5.1、勘誤 E-18；AT-966-12-1、12-7、9-1、9-4 的黃金列取用 `camelKeys` 轉換後的樣本）：
 * 前端複本 `tests/fixtures/si/flow/{patrol,detail}.golden.json` 必須與根層檔 `tools/tests/fixtures/selfimproving/p7/` 逐位元組相等，
 * 且根層樣本（snake_case 原樣）經 `camelKeys` 轉換後的鍵集合與 `PATROL()`／`DETAIL()` 建構函式夾具一致。硬斷言：樣本缺席即紅。
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { DETAIL, PATROL, goldenProposalItem, goldenReport } from "@/tests/helpers/siFlow";

const FRONT = process.cwd();
const ROOT_DIR = path.join(FRONT, "..", "..", "tools", "tests", "fixtures", "selfimproving", "p7");
const COPY_DIR = path.join(FRONT, "tests", "fixtures", "si", "flow");

describe.each([["patrol"], ["detail"]])("黃金樣本 %s", (name) => {
  it(`${name}：前端複本與根層檔逐位元組相等`, () => {
    const a = readFileSync(path.join(ROOT_DIR, `${name}.golden.json`));
    const b = readFileSync(path.join(COPY_DIR, `${name}.golden.json`));
    expect(Buffer.compare(a, b), "複本與根層檔不是逐位元組相等").toBe(0);
  });
});

describe("黃金樣本轉成 camelCase 後的鍵集合與建構函式夾具一致", () => {
  it("巡邏快照：頂層（扣掉 schemaRev）與 push 的鍵集合", () => {
    const report = goldenReport();
    expect(
      Object.keys(report)
        .filter((k) => k !== "schemaRev")
        .sort(),
    ).toEqual(Object.keys(PATROL().report).sort());
    expect(Object.keys(report.push as object).sort()).toEqual(Object.keys(PATROL().report.push as object).sort());
    expect(Object.keys((report.schedule as { lastSkip: object }).lastSkip).sort()).toEqual(["auditRef", "code", "seq", "t", "text"]);
  });
  it("單筆提案：detail 的鍵集合與 heldout、sandbox、verify 內層鍵", () => {
    const detail = goldenProposalItem().detail as Record<string, Record<string, unknown>>;
    const base = DETAIL() as Record<string, Record<string, unknown>>;
    expect(Object.keys(detail).sort()).toEqual(Object.keys(base).sort());
    for (const key of ["heldout", "sandbox", "verify"]) expect(Object.keys(detail[key]).sort(), key).toEqual(Object.keys(base[key]).sort());
  });
});
