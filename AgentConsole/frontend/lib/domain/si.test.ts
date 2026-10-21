import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { REASONS } from "@/lib/api/reasons";
import { ApiError } from "@/lib/api/client";
import type { SiInvalidRow, SiNeEntry, SiObservation, SiObservationRow } from "@/lib/api/types";
import {
  BUCKET_DISPLAY_ORDER,
  DATE_WINDOW_OPTIONS,
  EMPTY_OBS_FILTERS,
  SI_PAGE_LIMIT,
  SI_REASONS,
  SI_STATUS_KNOWN_KEYS,
  TOUCHED_NE_REASON,
  bucketOptions,
  cardNeEntries,
  describeTouched,
  describeValue,
  digest8,
  dispositionKey,
  distinctValues,
  filterEvents,
  filterObservations,
  filterProposals,
  formatNe,
  formatProblem,
  hasBucketData,
  identityKey,
  inDateWindow,
  isInvalidRow,
  isNotEvaluable,
  mergeNotes,
  mergePages,
  noEventText,
  notEvaluableText,
  prettyJson,
  siErrorParts,
  siErrorSummary,
  type DateWindow,
} from "./si";

/** 觀察列的最小夾具：只填各測試關心的欄位，其餘給固定值（九欄形狀見 lib/api/types.ts 的 SiObservation）。 */
function obs(id: string, patch: Partial<SiObservation> = {}): SiObservation {
  return { id, time: "2026-10-21 08:00", context: "ctx", symptom: "s", evidence: "e", category: "bug", severity: "P3", disposition: "open", marks: "", marksKv: {}, line: 1, ...patch };
}
const BAD_ROW: SiInvalidRow = { line: 22, raw: "| OBS-SI-012 | 欄數不足 |", valid: false };

describe("AT_932_1_7 lib/domain/si.ts 純函式表驅動（R15、R17）", () => {
  it("AT_932_1_7 mergePages：依序串接、依身分鍵去重且保留先到者、不丟任何一筆；空頁與單頁不出錯", () => {
    type Item = { id: string; v: string };
    const keyOf = (i: Item) => i.id;
    const p1: Item[] = [
      { id: "a", v: "1" },
      { id: "b", v: "1" },
    ];
    const p2: Item[] = [
      { id: "b", v: "重送（不得覆寫先到者）" },
      { id: "c", v: "2" },
    ];
    const p3: Item[] = [
      { id: "d", v: "3" },
      { id: "a", v: "再重送" },
    ];
    expect(mergePages([p1, p2, p3], keyOf)).toEqual([
      { id: "a", v: "1" },
      { id: "b", v: "1" },
      { id: "c", v: "2" },
      { id: "d", v: "3" },
    ]);
    expect(mergePages<Item>([], keyOf)).toEqual([]);
    expect(mergePages<Item>([[], p1, []], keyOf)).toEqual(p1);
    expect(mergePages([p1], keyOf)).toEqual(p1);
    // 數字鍵（事件 seq）與字串鍵互不相等
    expect(mergePages([[{ seq: 1 }], [{ seq: 1 }, { seq: 2 }]], (e) => e.seq).map((e) => e.seq)).toEqual([1, 2]);
  });

  it.each([
    ["open", "open"],
    ["decided：寫成某檔", "decided"],
    ["deferred；再開症狀：x", "deferred"],
    ["retired：座標", "retired"],
    ["fixed@abc1234", "fixed"],
    ["DEF-AC-003", "DEF-*"],
    ["DEF-AC-023", "DEF-*"],
    ["merged@OBS-SI-010", "merged"],
    ["proposed@PROP-SI-004", "proposed"],
    ["decided: x", "decided"],
    ["decided x", "decided"],
    ["decided;x", "decided"],
    ["", ""],
  ])("AT_932_1_7 dispositionKey(%j) → %j", (text, expected) => {
    expect(dispositionKey(text)).toBe(expected);
  });

  describe("AT_932_1_7 inDateWindow", () => {
    const ANCHOR = "2026-10-21T09:30:00+08:00";
    const cases: Array<[string, string | null, DateWindow, "in" | "out" | "unparsable"]> = [
      // today：日期等於錨點日
      ["today 同日", "2026-10-21 08:00", "today", "in"],
      ["today 前一日 23:59", "2026-10-20 23:59", "today", "out"],
      ["today 隔日", "2026-10-22 00:01", "today", "out"],
      // 7d：窗起點 2026-10-15（含）
      ["7d 起點當日", "2026-10-15 00:00", "7d", "in"],
      ["7d 起點前一日", "2026-10-14 23:00", "7d", "out"],
      ["7d 錨點日", "2026-10-21 23:59", "7d", "in"],
      ["7d 錨點日之後", "2026-10-22 00:00", "7d", "out"],
      // 30d：窗起點 2026-09-22（含）
      ["30d 起點當日", "2026-09-22", "30d", "in"],
      ["30d 起點前一日", "2026-09-21", "30d", "out"],
      // 區間寫法取前 10 字元
      ["區間寫法", "2026-10-18 21:20～22:05", "7d", "in"],
      // 無法解析：在受限窗為 unparsable；all 恆為 in
      ["文字日期 7d", "約一週前", "7d", "unparsable"],
      ["null 30d", null, "30d", "unparsable"],
      ["文字日期 today", "約一週前", "today", "unparsable"],
      ["不存在的日期 2026-02-30", "2026-02-30 10:00", "7d", "unparsable"],
      ["格式不足 2026-10-2", "2026-10-2", "7d", "unparsable"],
      ["all 文字日期", "約一週前", "all", "in"],
      ["all null", null, "all", "in"],
      ["all 很舊的日期", "2020-01-01", "all", "in"],
    ];
    it.each(cases)("AT_932_1_7 錨點 2026-10-21：%s", (_name, date, win, expected) => {
      expect(inDateWindow(date, ANCHOR, win)).toBe(expected);
    });

    it("AT_932_1_7 跨年錨點（2027-01-02）的 7d 起點為 2026-12-27；閏年錨點（2028-03-01）的 30d 起點為 2028-02-01", () => {
      const newYear = "2027-01-02T00:30:00+00:00";
      expect(inDateWindow("2026-12-27", newYear, "7d")).toBe("in");
      expect(inDateWindow("2026-12-26", newYear, "7d")).toBe("out");
      const leap = "2028-03-01T10:00:00+08:00";
      expect(inDateWindow("2028-02-01", leap, "30d")).toBe("in");
      expect(inDateWindow("2028-01-31", leap, "30d")).toBe("out");
      // 閏日本身是真實存在的日期
      expect(inDateWindow("2028-02-29 12:00", leap, "7d")).toBe("in");
    });

    it("AT_932_1_7 錨點無法解析時，受限窗一律 unparsable（不假裝在窗內也不假裝不在）；all 仍為 in", () => {
      expect(inDateWindow("2026-10-21", null, "today")).toBe("unparsable");
      expect(inDateWindow("2026-10-21", "not-a-date", "7d")).toBe("unparsable");
      expect(inDateWindow("2026-10-21", undefined, "all")).toBe("in");
    });

    it("AT_932_1_7 時間窗選項的 id 與標籤：全部、今天、近 7 天、近 30 天", () => {
      expect(DATE_WINDOW_OPTIONS.map((o) => [o.id, o.label])).toEqual([
        ["all", "全部"],
        ["today", "今天"],
        ["7d", "近 7 天"],
        ["30d", "近 30 天"],
      ]);
    });
  });

  describe("AT_932_1_7 filterObservations 與 bucketOptions", () => {
    const ANCHOR = "2026-10-21T09:30:00+08:00";
    const rows: SiObservationRow[] = [
      obs("OBS-SI-001", { category: "bug", severity: "P1", disposition: "open", time: "2026-10-21 08:00", buckets: ["AutoClaude"] }),
      obs("OBS-SI-002", { category: "bug", severity: "P3", disposition: "decided：x", time: "2026-10-20 23:59", buckets: ["SelfImproving", "AgentConsole"] }),
      obs("OBS-SI-003", { category: "doc", severity: "P3", disposition: "DEF-AC-003", time: "2026-10-05 09:00", buckets: ["未分類"] }),
      obs("OBS-SI-004", { category: "doc", severity: "P4", disposition: "DEF-AC-023", time: "約一週前" }),
      BAD_ROW,
    ];
    const ids = (list: SiObservationRow[]) => list.map((r) => (isInvalidRow(r) ? `line:${r.line}` : r.id));

    it("AT_932_1_7 無條件時全部保留；壞列在任何篩選下都保留", () => {
      expect(ids(filterObservations(rows, EMPTY_OBS_FILTERS, ANCHOR))).toEqual(["OBS-SI-001", "OBS-SI-002", "OBS-SI-003", "OBS-SI-004", "line:22"]);
      expect(ids(filterObservations(rows, { severity: "P9" }, ANCHOR))).toEqual(["line:22"]);
    });

    it("AT_932_1_7 分類、嚴重度、處置鍵、模組桶、時間窗取交集（全部條件同時成立才保留）", () => {
      expect(ids(filterObservations(rows, { severity: "P3" }, ANCHOR))).toEqual(["OBS-SI-002", "OBS-SI-003", "line:22"]);
      expect(ids(filterObservations(rows, { severity: "P3", category: "doc" }, ANCHOR))).toEqual(["OBS-SI-003", "line:22"]);
      expect(ids(filterObservations(rows, { disposition: "DEF-*" }, ANCHOR))).toEqual(["OBS-SI-003", "OBS-SI-004", "line:22"]);
      expect(ids(filterObservations(rows, { disposition: "decided" }, ANCHOR))).toEqual(["OBS-SI-002", "line:22"]);
      expect(ids(filterObservations(rows, { bucket: "AgentConsole" }, ANCHOR))).toEqual(["OBS-SI-002", "line:22"]);
      expect(ids(filterObservations(rows, { window: "today" }, ANCHOR))).toEqual(["OBS-SI-001", "OBS-SI-004", "line:22"]);
      expect(ids(filterObservations(rows, { window: "7d", category: "bug" }, ANCHOR))).toEqual(["OBS-SI-001", "OBS-SI-002", "line:22"]);
    });

    it("AT_932_1_7 時間無法解析的列不被時間窗篩除；沒有 buckets 欄的列不符合任何選定的模組桶", () => {
      expect(ids(filterObservations(rows, { window: "30d" }, ANCHOR))).toContain("OBS-SI-004");
      const noBucket = filterObservations(rows, { bucket: "AutoClaude" }, ANCHOR);
      expect(ids(noBucket)).toEqual(["OBS-SI-001", "line:22"]);
      // 證據座標含 AutoClaude/ 路徑也不會被歸桶（前端不自證據文字推算）
      const byText = [obs("OBS-SI-009", { evidence: "`AutoClaude/autoclaude/plugins/x.py`" }), BAD_ROW];
      expect(ids(filterObservations(byText, { bucket: "AutoClaude" }, ANCHOR))).toEqual(["line:22"]);
    });

    it("AT_932_1_7 bucketOptions 依 BUCKET_DISPLAY_ORDER 排序，未知值依出現序附後；無 buckets 欄回空", () => {
      const withBuckets = [obs("a", { buckets: ["未分類"] }), obs("b", { buckets: ["AutoClaude", "Foo"] }), obs("c", { buckets: ["SelfImproving", "Bar"] }), BAD_ROW];
      expect(bucketOptions(withBuckets)).toEqual(["SelfImproving", "AutoClaude", "未分類", "Foo", "Bar"]);
      expect(bucketOptions([obs("a", { buckets: ["未分類"] }), obs("b", { buckets: ["AutoClaude"] }), obs("c", { buckets: ["SelfImproving"] }), obs("d", { buckets: ["Foo"] })])).toEqual([
        "SelfImproving",
        "AutoClaude",
        "未分類",
        "Foo",
      ]);
      expect(bucketOptions(rows.slice(3))).toEqual([]);
      expect(BUCKET_DISPLAY_ORDER).toEqual(["SelfImproving", "AutoClaude", "AISDLC_SDD", "AgentConsole", "根層", "未分類"]);
    });

    it("AT_932_1_7 hasBucketData：任一有效列帶 buckets 欄即為真；壞列與缺席為假", () => {
      expect(hasBucketData([obs("a"), BAD_ROW])).toBe(false);
      expect(hasBucketData([obs("a"), obs("b", { buckets: [] })])).toBe(true);
    });

    it("AT_932_1_7 SI_PAGE_LIMIT 為 100；SI_REASONS 恰兩個鍵", () => {
      expect(SI_PAGE_LIMIT).toBe(100);
      expect(Object.keys(SI_REASONS)).toEqual(["UNAVAILABLE", "NOT_FOUND"]);
    });
  });
});

describe("lib/domain/si.ts 的補充單元（身分鍵、選項、提案與事件篩選、量不到的呈現）", () => {
  it("identityKey：seq → id → line，帶型別前綴；沒有身分欄時以內容當鍵（不誤併）", () => {
    expect(identityKey({ id: "OBS-SI-001", line: 11 })).toBe("id:OBS-SI-001");
    expect(identityKey({ seq: 5 })).toBe("seq:5");
    // 事件物件本身可能帶 id（同一個提案的後續事件共用 id）：身分是 seq，不是 id，否則第二筆會被誤併掉
    expect(identityKey({ seq: 5, id: "PROP-SI-004" })).toBe("seq:5");
    expect(identityKey({ seq: 9, id: "PROP-SI-004" })).not.toBe(identityKey({ seq: 5, id: "PROP-SI-004" }));
    expect(identityKey(BAD_ROW)).toBe("line:22");
    expect(identityKey({ a: 1 } as never)).not.toBe(identityKey({ a: 2 } as never));
    // 同一個數字在不同欄位不撞鍵
    expect(identityKey({ seq: 22 })).not.toBe(identityKey({ line: 22 }));
  });

  it("mergeNotes：多頁重複的 ne／problems 依內容去重，保留首見順序", () => {
    const a: SiNeEntry = { field: "head_sha", reason: "git-unavailable" };
    const b: SiNeEntry = { field: "events", reason: "carrier-not-established" };
    expect(mergeNotes([[a], [a, b], []])).toEqual([a, b]);
  });

  it("distinctValues：相異非空值、依字碼排序、略過 null 與 undefined", () => {
    expect(distinctValues(["b", "a", "b", "", null, undefined, "C"], (v) => v)).toEqual(["C", "a", "b"]);
  });

  it("filterProposals：狀態與類別取交集；空條件全留", () => {
    const props = [
      { id: "PROP-SI-001", state: "proposed", cls: "M" },
      { id: "PROP-SI-002", state: "verified", cls: "M" },
      { id: "PROP-SI-003", state: "proposed", cls: "C" },
    ] as never[];
    const ids = (list: ReturnType<typeof filterProposals>) => list.map((p) => p.id);
    expect(ids(filterProposals(props, {}))).toEqual(["PROP-SI-001", "PROP-SI-002", "PROP-SI-003"]);
    expect(ids(filterProposals(props, { state: "proposed" }))).toEqual(["PROP-SI-001", "PROP-SI-003"]);
    expect(ids(filterProposals(props, { state: "proposed", cls: "C" }))).toEqual(["PROP-SI-003"]);
  });

  it("filterEvents：種類與時間窗（以 t 的日期）取交集；t 無法解析者不被篩除", () => {
    const events = [
      { seq: 1, t: "2026-10-21T01:00:00+08:00", kind: "run.open", by: "x" },
      { seq: 2, t: "2026-10-14T22:31:25+08:00", kind: "attr", by: "x" },
      { seq: 3, t: "壞掉的時間", kind: "attr", by: "x" },
    ];
    const seqs = (list: ReturnType<typeof filterEvents>) => list.map((e) => e.seq);
    const anchor = "2026-10-21T09:30:00+08:00";
    expect(seqs(filterEvents(events, { kind: "attr" }, anchor))).toEqual([2, 3]);
    expect(seqs(filterEvents(events, { window: "today" }, anchor))).toEqual([1, 3]);
    expect(seqs(filterEvents(events, { kind: "attr", window: "7d" }, anchor))).toEqual([3]);
  });

  it("量不到的呈現：NE 物件、null、一般值、陣列與物件各自的純文字；不把量不到寫成 0 或無", () => {
    expect(isNotEvaluable({ status: "NOT-EVALUABLE", reason: "x" })).toBe(true);
    expect(isNotEvaluable({ status: "OK" })).toBe(false);
    expect(isNotEvaluable(null)).toBe(false);
    expect(isNotEvaluable(["NOT-EVALUABLE"])).toBe(false);
    expect(describeValue({ status: "NOT-EVALUABLE", reason: "capacity-verb-not-established" })).toBe("量不到（NOT-EVALUABLE）：capacity-verb-not-established");
    expect(describeValue({ status: "NOT-EVALUABLE" })).toBe("量不到（NOT-EVALUABLE）");
    expect(describeValue(null)).toBe("無");
    expect(describeValue(0)).toBe("0");
    expect(describeValue("x")).toBe("x");
    expect(describeValue(true)).toBe("true");
    expect(describeValue({ unsettled: 0 })).toBe('{"unsettled":0}');
    expect(describeValue([])).toBe("[]");
    expect(notEvaluableText("g")).toBe("量不到（NOT-EVALUABLE）：g");
    expect(notEvaluableText()).toBe("量不到（NOT-EVALUABLE）");
    expect(noEventText(0)).toBe("無事件");
    expect(noEventText(1)).toBe("無事件（尚有 1 項量不到）");
    expect(noEventText(3)).toBe("無事件（尚有 3 項量不到）");
  });

  it("touched_null describeTouched（R16）：null 與缺席是量不到、不是「無」；空陣列與 0 是真值；其餘值同 describeValue", () => {
    const ne = "量不到（NOT-EVALUABLE）：patch 讀不到或無法解析";
    expect(TOUCHED_NE_REASON).toBe("patch 讀不到或無法解析");
    expect(describeTouched(null)).toBe(ne);
    expect(describeTouched(undefined)).toBe(ne);
    expect(describeTouched(null)).not.toBe(describeValue(null)); // describeValue(null) 是「無」（例：suspended 的「沒有暫停」）；touched 的 null 不是這個語意
    expect(describeTouched([])).toBe("[]");
    expect(describeTouched(0)).toBe("0");
    expect(describeTouched(3)).toBe("3");
    expect(describeTouched(["memory/guard-ratchet-repin-ritual.md"])).toBe('["memory/guard-ratchet-repin-ritual.md"]');
  });

  it("ne／problems／digest／卡面 ne 的格式化", () => {
    expect(formatNe({ field: "head_sha", reason: "git-unavailable" })).toBe("head_sha：git-unavailable");
    expect(formatProblem({ subject: "OBS-SI-012", code: "ROW-ARITY", detail: "欄數不是 9" })).toBe("OBS-SI-012 ROW-ARITY 欄數不是 9");
    expect(digest8("sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c")).toBe("d21ae6f5");
    expect(digest8("abc")).toBe("abc");
    const ne: SiNeEntry[] = [
      { field: "proposals.PROP-SI-004.card", reason: "git-unavailable" },
      { field: "proposals.PROP-SI-005.card", reason: "x" },
      { field: "head_sha", reason: "y" },
    ];
    expect(cardNeEntries(ne, "PROP-SI-004")).toEqual([ne[0]]);
    expect(cardNeEntries(ne, "PROP-SI-099")).toEqual([]);
    expect(prettyJson({ a: 1 })).toBe('{\n  "a": 1\n}');
  });

  it("SI_STATUS_KNOWN_KEYS 恰為 R13 列的九個已知鍵（其餘鍵走 si-status-extra）", () => {
    expect([...SI_STATUS_KNOWN_KEYS]).toEqual(["eventsDetected", "unavailable", "openRuns", "pendingProps", "suspended", "cooldowns", "skipReasons", "capacity", "frictionReconcile"]);
  });
});

/** 解析凍結 Architecture §11.1〈SelfImproving 相關的 reason〉表（體例同 lib/api/reasons.test.ts：期望值取自文件本身，不抄一份）。 */
function siReasonTable(): Array<{ reason: string; when: string }> {
  const md = readFileSync(path.join(process.cwd(), "..", "docs", "02_architecture", "Architecture.md"), "utf-8");
  const start = md.indexOf("**SelfImproving 相關的 `reason`**");
  expect(start, "找不到 Architecture §11.1 的 SelfImproving reason 表").toBeGreaterThan(-1);
  const lines = md.slice(start).split("\n");
  const first = lines.findIndex((l) => l.startsWith("|"));
  expect(first, "SelfImproving reason 表找不到表格列").toBeGreaterThan(-1);
  const out: Array<{ reason: string; when: string }> = [];
  for (const line of lines.slice(first)) {
    if (!line.startsWith("|")) break;
    const cells = line
      .split("|")
      .slice(1, -1)
      .map((c) => c.trim());
    if (cells[0] === "HTTP" || /^-+$/.test(cells[0])) continue;
    const reason = /`([^`]+)`/.exec(cells[1])?.[1];
    expect(reason, `表列沒有 reason：${line}`).toBeTruthy();
    out.push({ reason: reason as string, when: cells[2] });
  }
  return out;
}

describe("AT_940_5_1 SI reason 常數與凍結的 Architecture §11.1 對拍，且不進 REASONS（R19）", () => {
  it("AT_940_5_1 SI_REASONS 恰為兩個鍵、兩值都在表的 reason 欄；表中 si_ 起頭且標 P1b 者全數有對應常數，只標 P2b 者不需要", () => {
    const rows = siReasonTable();
    expect(rows.length, "表解析不到足夠的列，格式可能變了").toBeGreaterThanOrEqual(5);
    expect(SI_REASONS.UNAVAILABLE).toBe("si_unavailable");
    expect(SI_REASONS.NOT_FOUND).toBe("si_not_found");
    expect(Object.keys(SI_REASONS).sort()).toEqual(["NOT_FOUND", "UNAVAILABLE"]);
    const inTable = new Set(rows.map((r) => r.reason));
    for (const value of Object.values(SI_REASONS)) expect(inTable.has(value), `${value} 不在 Architecture §11.1 的表內`).toBe(true);
    const p1b = rows.filter((r) => r.reason.startsWith("si_") && r.when.includes("P1b")).map((r) => r.reason);
    expect(p1b.sort()).toEqual(Object.values(SI_REASONS).sort());
    // 只標 P2b 的 si_ 起頭 reason 不需要常數（P1b 零寫入）
    const p2bOnly = rows.filter((r) => r.reason.startsWith("si_") && !r.when.includes("P1b")).map((r) => r.reason);
    expect(p2bOnly.length).toBeGreaterThan(0);
    for (const reason of p2bOnly) expect(Object.values(SI_REASONS)).not.toContain(reason);
  });

  it("AT_940_5_1 422 invalid_request 是 Bridge 層的 reason：在表內，但不進 SI_REASONS 也不進 REASONS", () => {
    expect(siReasonTable().map((r) => r.reason)).toContain("invalid_request");
    expect(Object.values(SI_REASONS)).not.toContain("invalid_request");
    expect(Object.values(REASONS)).not.toContain("invalid_request");
  });

  it("AT_940_5_1 REASONS 不含這兩值；reasons.ts 原始碼不再稱 rtm_not_found 為唯一例外，也不寫 SI reason 的字面值（只指向 SI_REASONS）；RTM_NOT_FOUND 常數不變", () => {
    const values: string[] = Object.values(REASONS);
    for (const value of Object.values(SI_REASONS)) expect(values).not.toContain(value);
    const source = readFileSync(path.join(process.cwd(), "lib", "api", "reasons.ts"), "utf-8");
    // 以布林＋訊息斷言：失敗時不把整支原始碼印進輸出
    expect(source.includes("唯一例外"), "reasons.ts 的 RTM_NOT_FOUND 註解仍稱它是唯一例外（SI 的 404 是第二個帶 reason 的例外）").toBe(false);
    expect(source.includes("si_unavailable"), "reasons.ts 不得寫 SI reason 的字面值（只指向 SI_REASONS）").toBe(false);
    expect(source.includes("si_not_found"), "reasons.ts 不得寫 SI reason 的字面值（只指向 SI_REASONS）").toBe(false);
    expect(source.includes("SI_REASONS"), "reasons.ts 的註解應指向 SI_REASONS").toBe(true);
    expect(REASONS.RTM_NOT_FOUND).toBe("rtm_not_found");
  });

  it("AT_940_5_1 錯誤文案純函式：503＋si_unavailable＝SI 資料面不可用；404＋si_not_found＝查無此筆；其餘沿 describeError（含 traceId）", () => {
    expect(siErrorSummary(new ApiError({ status: 503, message: "x", reason: "si_unavailable" }))).toBe("SI 資料面不可用");
    expect(siErrorSummary(new ApiError({ status: 404, message: "x", reason: "si_not_found" }))).toBe("查無此筆");
    // reason 與狀態碼必須同時相符：同一個 reason 配別的狀態碼、或別的 reason 配這兩個狀態碼，都走 describeError
    expect(siErrorSummary(new ApiError({ status: 502, message: "上游錯誤", reason: "si_unavailable" }))).toBe("上游錯誤：si_unavailable");
    expect(siErrorSummary(new ApiError({ status: 503, message: "忙線", reason: "別的原因" }))).toBe("忙線：別的原因");
    expect(siErrorSummary(new ApiError({ status: 404, message: "找不到" }))).toBe("找不到");
    expect(siErrorSummary(new ApiError({ status: 500, message: "壞了", traceId: "tr-1" }))).toBe("壞了（traceId：tr-1）");
    expect(siErrorSummary(new Error("網路"))).toBe("網路");
    expect(siErrorSummary("字串")).toBe("發生未知錯誤");
  });

  it("AT_940_5_1 siErrorParts：reason、details.detail、details.cause 逐字取出；缺者不出現；非 ApiError 回空物件", () => {
    const err = new ApiError({ status: 503, message: "m", reason: "si_unavailable", details: { cause: "nonzero_rc", detail: "rc=2; stderr=boom 全形字元", extra: 1 } });
    expect(siErrorParts(err)).toEqual({ reason: "si_unavailable", detail: "rc=2; stderr=boom 全形字元", cause: "nonzero_rc" });
    expect(siErrorParts(new ApiError({ status: 404, message: "m" }))).toEqual({ reason: undefined, detail: undefined, cause: undefined });
    expect(siErrorParts(new ApiError({ status: 503, message: "m", details: { detail: 5, cause: null } }))).toEqual({ reason: undefined, detail: undefined, cause: undefined });
    expect(siErrorParts(new Error("x"))).toEqual({});
  });
});
