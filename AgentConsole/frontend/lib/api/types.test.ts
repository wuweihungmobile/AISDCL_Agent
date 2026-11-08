/**
 * 手寫型別與生成型別（schema.d.ts）的對拍。型別層的鎖（`expectTypeOf`、`satisfies`）由 `tsc --noEmit` 承擔——
 * vitest 不做型別檢查，這些斷言在 vitest 裡是 no-op（SCG-4 一審 F-09：W3 五個型別突變全由 tsc 殺掉、本檔 0 個）；
 * 本檔的**執行期**斷言只鎖鍵集合（兩側欄名相等）。改型別時兩者都要跑：`npx tsc --noEmit` 與 `npx vitest run lib/api/types.test.ts`。
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, expectTypeOf, it } from "vitest";

import type { components } from "./schema";
import type {
  ResearchDecomposition,
  ResearchDelivery,
  ResearchDeliveryOverview,
  ResearchGateRegisterRequest,
  ResearchGateRegisterResult,
  ResearchHealing,
  ResearchHealingRow,
  ResearchKanban,
  ResearchKanbanGate,
  ResearchKanbanRtm,
  ResearchKanbanTaskCounts,
  ResearchPendingReview,
  ResearchPrRequest,
  ResearchPrResult,
  ResearchScr,
  ResearchScrOpenRequest,
  ResearchTagRequest,
  ResearchTagResult,
  ResearchTraceRow,
  ResearchTraceability,
} from "./types";

/**
 * AT-962-27-2／27-3（TCS-ResearchToPRD-P2 §3.3）：P2 手寫型與重產後的 `schema.d.ts` 不得漂移。
 *
 * P2 手寫型一律引生成型（D-160：API-P2 FIX 起後端逐欄宣告 required／nullable）；值域收窄與五處 `| null`（springdoc 對 `$ref` 欄位不輸出 nullable）是僅有的手寫部分。
 * 本檔以型別層鎖兩件事——
 *   ① 欄名集合與生成型逐層相等（後端增減欄位，這裡紅）；
 *   ② 去掉 null 之後，手寫型可指派給生成型（欄位型別方向沒反）。
 * 型別斷言由 `tsc --noEmit` 判定（vitest 執行期不檢查型別）；靜態掃描另守「夾具不以放寬型別蒙混」。
 */
type S = components["schemas"];

/** 遞迴去掉 null（生成型沒有 null 這個值域）。 */
type StripNull<T> = T extends null ? never : T extends Array<infer U> ? Array<StripNull<U>> : T extends object ? { [K in keyof T]: StripNull<T[K]> } : T;
type KeysOf<T> = keyof NonNullable<T>;

describe("AT-962-27-2 P2 手寫型與生成型欄名集合相等（型別層）", () => {
  it("看板 DTO 與各欄", () => {
    expectTypeOf<KeysOf<ResearchKanban>>().toEqualTypeOf<KeysOf<S["KanbanDto"]>>();
    expectTypeOf<KeysOf<ResearchKanban["columns"]>>().toEqualTypeOf<KeysOf<S["Columns"]>>();
    expectTypeOf<KeysOf<ResearchKanban["columns"]["decompose"]>>().toEqualTypeOf<KeysOf<S["KanbanDecompose"]>>();
    expectTypeOf<KeysOf<ResearchKanban["columns"]["tcs"]>>().toEqualTypeOf<KeysOf<S["KanbanTcs"]>>();
    expectTypeOf<KeysOf<ResearchKanban["columns"]["implement"]>>().toEqualTypeOf<KeysOf<S["KanbanImplement"]>>();
    expectTypeOf<KeysOf<ResearchKanbanTaskCounts>>().toEqualTypeOf<KeysOf<S["KanbanTaskCounts"]>>();
    expectTypeOf<KeysOf<ResearchKanban["columns"]["healing"]>>().toEqualTypeOf<KeysOf<S["KanbanHealing"]>>();
    expectTypeOf<KeysOf<ResearchKanban["columns"]["regression"]>>().toEqualTypeOf<KeysOf<S["KanbanRegression"]>>();
    expectTypeOf<KeysOf<ResearchKanbanRtm>>().toEqualTypeOf<KeysOf<S["KanbanRtm"]>>();
    expectTypeOf<KeysOf<ResearchPendingReview>>().toEqualTypeOf<KeysOf<S["KanbanPendingReview"]>>();
    expectTypeOf<KeysOf<ResearchKanbanGate>>().toEqualTypeOf<KeysOf<S["KanbanGate"]>>();
  });

  it("SCG 登錄請求與回應", () => {
    expectTypeOf<KeysOf<ResearchGateRegisterRequest>>().toEqualTypeOf<KeysOf<S["GateRegisterRequest"]>>();
    expectTypeOf<KeysOf<ResearchGateRegisterResult>>().toEqualTypeOf<KeysOf<S["GateRegisterResult"]>>();
    expectTypeOf<ResearchGateRegisterRequest["gate"]>().toEqualTypeOf<NonNullable<S["GateRegisterRequest"]["gate"]>>();
    expectTypeOf<ResearchGateRegisterRequest["result"]>().toEqualTypeOf<NonNullable<S["GateRegisterRequest"]["result"]>>();
  });

  it("自癒", () => {
    expectTypeOf<KeysOf<ResearchHealing>>().toEqualTypeOf<KeysOf<S["HealingDto"]>>();
    expectTypeOf<KeysOf<ResearchHealingRow>>().toEqualTypeOf<KeysOf<S["HealingRow"]>>();
    expectTypeOf<KeysOf<S["HealingSpecChange"]>>().toEqualTypeOf<"paths" | "detectedAt">();
  });

  it("交付總覽、Tag、PR", () => {
    expectTypeOf<KeysOf<ResearchDeliveryOverview>>().toEqualTypeOf<KeysOf<S["DeliveryOverviewDto"]>>();
    expectTypeOf<KeysOf<ResearchDelivery>>().toEqualTypeOf<KeysOf<S["DeliveryDto"]>>();
    expectTypeOf<KeysOf<ResearchDeliveryOverview["preconditions"]>>().toEqualTypeOf<KeysOf<S["DeliveryPreconditions"]>>();
    expectTypeOf<KeysOf<NonNullable<ResearchDeliveryOverview["snapshot"]>>>().toEqualTypeOf<KeysOf<S["DeliverySnapshot"]>>();
    expectTypeOf<KeysOf<ResearchTagRequest>>().toEqualTypeOf<KeysOf<S["TagRequest"]>>();
    expectTypeOf<KeysOf<ResearchTagResult>>().toEqualTypeOf<KeysOf<S["TagResult"]>>();
    expectTypeOf<KeysOf<ResearchPrRequest>>().toEqualTypeOf<KeysOf<S["PrRequest"]>>();
    expectTypeOf<KeysOf<ResearchPrResult>>().toEqualTypeOf<KeysOf<S["PrResult"]>>();
  });

  it("追溯表", () => {
    expectTypeOf<KeysOf<ResearchTraceability>>().toEqualTypeOf<KeysOf<S["TraceabilityDto"]>>();
    expectTypeOf<KeysOf<ResearchTraceRow>>().toEqualTypeOf<KeysOf<S["TraceabilityRow"]>>();
    expectTypeOf<KeysOf<ResearchTraceRow["gherkinSummary"]>>().toEqualTypeOf<KeysOf<S["TraceabilityGherkin"]>>();
    expectTypeOf<KeysOf<ResearchTraceability["totals"]>>().toEqualTypeOf<KeysOf<S["TraceabilityTotals"]>>();
    expectTypeOf<KeysOf<NonNullable<ResearchTraceability["rtm"]>>>().toEqualTypeOf<KeysOf<S["TraceabilityRtm"]>>();
  });

  it("去 null 後手寫型可指派給生成型（欄位型別方向沒反）", () => {
    expectTypeOf<StripNull<ResearchKanban>>().toExtend<S["KanbanDto"]>();
    expectTypeOf<StripNull<ResearchGateRegisterRequest>>().toExtend<S["GateRegisterRequest"]>();
    expectTypeOf<StripNull<ResearchGateRegisterResult>>().toExtend<S["GateRegisterResult"]>();
    expectTypeOf<StripNull<ResearchHealing>>().toExtend<S["HealingDto"]>();
    expectTypeOf<StripNull<ResearchDeliveryOverview>>().toExtend<S["DeliveryOverviewDto"]>();
    expectTypeOf<StripNull<ResearchTagRequest>>().toExtend<S["TagRequest"]>();
    expectTypeOf<StripNull<ResearchTagResult>>().toExtend<S["TagResult"]>();
    expectTypeOf<StripNull<ResearchPrRequest>>().toExtend<S["PrRequest"]>();
    expectTypeOf<StripNull<ResearchPrResult>>().toExtend<S["PrResult"]>();
    expectTypeOf<StripNull<ResearchTraceability>>().toExtend<S["TraceabilityDto"]>();
  });

  it("evidenceUrl 與 prdSha256 取自生成型", () => {
    expectTypeOf<ResearchScrOpenRequest["evidenceUrl"]>().toEqualTypeOf<S["ScrOpenRequest"]["evidenceUrl"]>();
    expectTypeOf<ResearchScr["evidenceUrl"]>().toEqualTypeOf<S["ScrDto"]["evidenceUrl"]>();
    // 決策（D-152#3 第二分支）：生成型為 string | null，手寫型保留非空收窄
    expectTypeOf<S["DecompositionDto"]["prdSha256"]>().toEqualTypeOf<string | null>();
    expectTypeOf<ResearchDecomposition["prdSha256"]>().toEqualTypeOf<string>();
  });
});

const FRONTEND_ROOT = resolve(import.meta.dirname, "..", "..");
const read = (rel: string) => readFileSync(resolve(FRONTEND_ROOT, rel), "utf-8");

/** 夾具與型別檔不得以放寬型別蒙混（D-135）：回傳違規字樣清單。 */
function looseningViolations(source: string): string[] {
  const body = source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");
  const banned: Array<[string, RegExp]> = [
    ["as unknown as", /\bas unknown as\b/],
    ["as any", /\bas any\b/],
    ["@ts-ignore／@ts-expect-error", /@ts-(ignore|expect-error)/],
  ];
  return banned.filter(([, re]) => re.test(body)).map(([name]) => name);
}

describe("AT-962-27-3 夾具補必填欄、不放寬（靜態掃描）", () => {
  it("P2 夾具與型別檔沒有放寬字樣", () => {
    for (const rel of ["tests/fixtures/research/p2.ts", "lib/api/types.ts"]) {
      expect(looseningViolations(read(rel)), rel).toEqual([]);
    }
  });

  it("負控：放寬字樣的樣本會被判違規", () => {
    expect(looseningViolations("const x = {} as unknown as Foo;")).toEqual(["as unknown as"]);
    expect(looseningViolations("const z = value as any;")).toEqual(["as any"]);
    expect(looseningViolations("// Partial<Foo> 只在註解裡\nconst y = 1;")).toEqual([]);
  });
});

describe("AT-962-27-1 重產結果命中七路徑與 DTO（靜態）", () => {
  const schema = read("lib/api/schema.d.ts");
  it("七條路徑", () => {
    for (const tail of ["/kanban", "/gates", "/healing", "/delivery", "/delivery/tag", "/delivery/pr", "/delivery/traceability"]) {
      expect(schema, tail).toContain(`"/api/v1/research/projects/{id}${tail}": {`);
    }
  });
  it("DTO 名與 evidenceUrl", () => {
    for (const name of ["KanbanDto", "GateRegisterRequest", "GateRegisterResult", "HealingDto", "DeliveryOverviewDto", "DeliveryDto", "TagRequest", "PrRequest", "TraceabilityDto"]) {
      expect(schema, name).toContain(`        ${name}: {`);
    }
    // ScrOpenRequest 選填、ScrDto 必填可空（API-P2 FIX）
    expect(schema).toContain("evidenceUrl?: string;");
    expect(schema).toContain("evidenceUrl: string | null;");
  });
});
