import { describe, expect, it } from "vitest";

import { nextSort, sortRows, type SortColumn, type SortState } from "@/lib/domain/sorting";

type R = { id: string; v: string | number | null | undefined };

const idCol: SortColumn<R> = { key: "id", kind: "id", get: (r) => r.id };
const col = (kind: SortColumn<R>["kind"], extra: Partial<SortColumn<R>> = {}): SortColumn<R> => ({ key: "v", kind, get: (r) => r.v, ...extra });
const rowsOf = (...vs: Array<R["v"]>): R[] => vs.map((v, i) => ({ id: `R-${i + 1}`, v }));
const vals = (rs: R[]) => rs.map((r) => r.v);

describe("AT_963_1_1 排序語意（id／text／number／iso）", () => {
  it("id 欄用自然序：RP-0009 < RP-0010 < RP-0100；ID-99 < ID-100", () => {
    const a = sortRows(
      [
        { id: "RP-0010", v: 0 },
        { id: "RP-0009", v: 0 },
        { id: "RP-0100", v: 0 },
      ],
      [idCol],
      { key: "id", dir: "asc" },
    ).map((r) => r.id);
    expect(a).toEqual(["RP-0009", "RP-0010", "RP-0100"]);
    const b = sortRows(
      [
        { id: "ID-100", v: 0 },
        { id: "ID-99", v: 0 },
      ],
      [idCol],
      { key: "id", dir: "asc" },
    ).map((r) => r.id);
    expect(b).toEqual(["ID-99", "ID-100"]);
    const d = sortRows(
      [
        { id: "RP-0010", v: 0 },
        { id: "RP-0009", v: 0 },
        { id: "RP-0100", v: 0 },
      ],
      [idCol],
      { key: "id", dir: "desc" },
    ).map((r) => r.id);
    expect(d).toEqual(["RP-0100", "RP-0010", "RP-0009"]);
  });

  it("text 欄與 Intl.Collator('zh-Hant') 逐元素一致；number 欄數值序", () => {
    const words = ["丙", "甲", "乙"];
    const got = vals(sortRows(rowsOf(...words), [col("text")], { key: "v", dir: "asc" }));
    expect(got).toEqual([...words].sort(new Intl.Collator("zh-Hant", { numeric: true }).compare));
    expect(vals(sortRows(rowsOf(10, 9, 100), [col("number")], { key: "v", dir: "asc" }))).toEqual([9, 10, 100]);
    expect(vals(sortRows(rowsOf(10, 9, 100), [col("number")], { key: "v", dir: "desc" }))).toEqual([100, 10, 9]);
  });

  it("iso 欄依實際時刻（+08:00 較早）", () => {
    const a = "2026-11-02T00:00:00+08:00";
    const b = "2026-11-01T23:00:00Z";
    expect(vals(sortRows(rowsOf(b, a), [col("iso")], { key: "v", dir: "asc" }))).toEqual([a, b]);
    expect(vals(sortRows(rowsOf(a, b), [col("iso")], { key: "v", dir: "desc" }))).toEqual([b, a]);
  });
});

describe("AT_963_1_2 空值與無法解析的 ISO", () => {
  it("空值（null／undefined／空字串）不論升降冪都在最後", () => {
    const rows = rowsOf("b", null, "a", undefined, "", "c");
    for (const dir of ["asc", "desc"] as const) {
      const out = vals(sortRows(rows, [col("text")], { key: "v", dir }));
      expect(out.slice(0, 3)).toEqual(dir === "asc" ? ["a", "b", "c"] : ["c", "b", "a"]);
      expect(out.slice(3).every((v) => v === null || v === undefined || v === "")).toBe(true);
    }
  });

  it("iso 含無法解析字串：不丟例外、退回文字比較落位", () => {
    const rows = rowsOf("2026-11-01T00:00:00Z", "不是時間", "2026-10-01T00:00:00Z");
    expect(() => sortRows(rows, [col("iso")], { key: "v", dir: "asc" })).not.toThrow();
    expect(sortRows(rows, [col("iso")], { key: "v", dir: "asc" })).toHaveLength(3);
  });
});

describe("AT_963_1_3 tie-break 與不可變", () => {
  it("主欄相等時兩個方向都由識別欄升冪決定；tieDir=desc 時兩方向都由識別欄降冪決定", () => {
    const rows: R[] = [
      { id: "R-2", v: "x" },
      { id: "R-1", v: "x" },
      { id: "R-3", v: "x" },
    ];
    for (const dir of ["asc", "desc"] as const) {
      expect(sortRows(rows, [idCol, col("text")], { key: "v", dir }).map((r) => r.id)).toEqual(["R-1", "R-2", "R-3"]);
      expect(sortRows(rows, [{ ...idCol, tieDir: "desc" }, col("text")], { key: "v", dir }).map((r) => r.id)).toEqual(["R-3", "R-2", "R-1"]);
    }
  });

  it("輸入凍結不丟例外、回傳新陣列；state=null 用 defaultCompare，未給＝原順序複本", () => {
    const rows = Object.freeze(rowsOf("b", "a").map((r) => Object.freeze(r))) as unknown as R[];
    const out = sortRows(rows, [col("text")], { key: "v", dir: "asc" });
    expect(out).not.toBe(rows);
    expect(vals(out)).toEqual(["a", "b"]);
    const dflt = sortRows(rows, [col("text")], null, (x, y) => String(y.v).localeCompare(String(x.v)));
    expect(vals(dflt)).toEqual(["b", "a"]);
    const orig = sortRows(rows, [col("text")], null);
    expect(orig).not.toBe(rows);
    expect(orig).toEqual([...rows]);
  });
});

describe("AT_963_1_4 nextSort 狀態機", () => {
  it("null 點 a、a、a、再點 b", () => {
    const s1 = nextSort(null, "a");
    const s2 = nextSort(s1, "a");
    const s3 = nextSort(s2, "a");
    const s4 = nextSort(s3, "b");
    expect([s1, s2, s3, s4]).toEqual([
      { key: "a", dir: "asc" },
      { key: "a", dir: "desc" },
      { key: "a", dir: "asc" },
      { key: "b", dir: "asc" },
    ]);
  });
});

describe("AT_963_1_5 nextSort 帶 defaultSort", () => {
  it("預設欄第一次點就反向", () => {
    const d1: SortState = { key: "id", dir: "asc" };
    expect(nextSort(null, "id", d1)).toEqual({ key: "id", dir: "desc" });
    expect(nextSort(null, "text", d1)).toEqual({ key: "text", dir: "asc" });
    const d2: SortState = { key: "finishedAt", dir: "desc" };
    expect(nextSort(null, "finishedAt", d2)).toEqual({ key: "finishedAt", dir: "asc" });
    expect(nextSort(null, "a")).toEqual({ key: "a", dir: "asc" });
  });
});

describe("AT_963_1_E_1 邊界", () => {
  it("不明欄＝null；空陣列與單筆；rank 回 null 的列排最後", () => {
    const rows = rowsOf("b", "a");
    expect(sortRows(rows, [col("text")], { key: "zzz", dir: "asc" })).toEqual(rows);
    expect(sortRows([], [col("text")], { key: "v", dir: "asc" })).toEqual([]);
    const one = rowsOf("a");
    expect(sortRows(one, [col("text")], { key: "v", dir: "desc" })).toEqual(one);
    const rank = (v: string) => ({ high: 2, low: 1 })[v as "high" | "low"] ?? null;
    const rr = rowsOf("high", "weird", "low");
    for (const dir of ["asc", "desc"] as const) {
      const out = vals(sortRows(rr, [col("rank", { rank })], { key: "v", dir }));
      expect(out[2]).toBe("weird");
    }
  });
});
