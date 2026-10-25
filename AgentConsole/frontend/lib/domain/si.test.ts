import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { REASONS } from "@/lib/api/reasons";
import { ApiError } from "@/lib/api/client";
import type { SiConsoleWrite, SiInvalidRow, SiNeEntry, SiObservation, SiObservationRow } from "@/lib/api/types";
import {
  BUCKET_DISPLAY_ORDER,
  DATE_WINDOW_OPTIONS,
  DECIDE_FIELDS,
  EMPTY_OBS_FILTERS,
  EMPTY_OBSERVATION_FORM,
  SI_PAGE_LIMIT,
  SI_REASONS,
  SI_STATUS_KNOWN_KEYS,
  TOUCHED_NE_REASON,
  bucketOptions,
  buildCloseRequest,
  buildDecideRequest,
  buildObservationRequest,
  cardNeEntries,
  decideVerbOptions,
  describeTouched,
  describeValue,
  digest8,
  dispositionKey,
  distinctValues,
  estimateRowBytes,
  filterEvents,
  filterObservations,
  filterProposals,
  formatNe,
  formatProblem,
  hasBucketData,
  identityKey,
  inDateWindow,
  ingestCommands,
  isInvalidRow,
  isNotEvaluable,
  mergeNotes,
  mergePages,
  noEventText,
  notEvaluableText,
  pendingWrites,
  prettyJson,
  siErrorParts,
  siErrorSummary,
  siWriteErrorText,
  suspendedRun,
  validateCloseForm,
  validateDecideForm,
  validateObservationForm,
  type CloseForm,
  type DateWindow,
  type DecideCard,
  type DecideForm,
  type ObservationForm,
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

    it("AT_932_1_7 SI_PAGE_LIMIT 為 100；SI_REASONS 恰五個鍵（P1b 的兩個在前、P2b 的三個接後；TCS §4 漏列這一條，P2b 同步時補改）", () => {
      expect(SI_PAGE_LIMIT).toBe(100);
      expect(Object.keys(SI_REASONS)).toEqual(["UNAVAILABLE", "NOT_FOUND", "WRITE_DISABLED", "WRITE_FORBIDDEN", "AUDIT_EXISTS"]);
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
  it("AT_940_5_1 SI_REASONS 恰為五個鍵（P1b 兩個加 P2b 三個）、五值都在表的 reason 欄；表中 reason 以 si_ 起頭的全部列都有對應常數（P2b 起不再有「只標 P2b 者不需要」）", () => {
    const rows = siReasonTable();
    expect(rows.length, "表解析不到足夠的列，格式可能變了").toBeGreaterThanOrEqual(5);
    expect(SI_REASONS.UNAVAILABLE).toBe("si_unavailable");
    expect(SI_REASONS.NOT_FOUND).toBe("si_not_found");
    expect(SI_REASONS.WRITE_DISABLED).toBe("si_write_disabled");
    expect(SI_REASONS.WRITE_FORBIDDEN).toBe("si_write_forbidden");
    expect(SI_REASONS.AUDIT_EXISTS).toBe("si_audit_exists");
    expect(Object.keys(SI_REASONS).sort()).toEqual(["AUDIT_EXISTS", "NOT_FOUND", "UNAVAILABLE", "WRITE_DISABLED", "WRITE_FORBIDDEN"]);
    const inTable = new Set(rows.map((r) => r.reason));
    for (const value of Object.values(SI_REASONS)) expect(inTable.has(value), `${value} 不在 Architecture §11.1 的表內`).toBe(true);
    const siRows = rows.filter((r) => r.reason.startsWith("si_")).map((r) => r.reason);
    expect(siRows.sort()).toEqual(Object.values(SI_REASONS).sort());
  });

  it("AT_940_5_1 422 invalid_request 是 Bridge 層的 reason：在表內，但不進 SI_REASONS 也不進 REASONS", () => {
    expect(siReasonTable().map((r) => r.reason)).toContain("invalid_request");
    expect(Object.values(SI_REASONS)).not.toContain("invalid_request");
    expect(Object.values(REASONS)).not.toContain("invalid_request");
  });

  it("AT_940_5_1 REASONS 不含這五值；reasons.ts 原始碼不再稱 rtm_not_found 為唯一例外，也不寫 SI reason 的字面值（只指向 SI_REASONS）；RTM_NOT_FOUND 常數不變", () => {
    const values: string[] = Object.values(REASONS);
    for (const value of Object.values(SI_REASONS)) expect(values).not.toContain(value);
    const source = readFileSync(path.join(process.cwd(), "lib", "api", "reasons.ts"), "utf-8");
    // 以布林＋訊息斷言：失敗時不把整支原始碼印進輸出
    expect(source.includes("唯一例外"), "reasons.ts 的 RTM_NOT_FOUND 註解仍稱它是唯一例外（SI 的 404 是第二個帶 reason 的例外）").toBe(false);
    for (const value of Object.values(SI_REASONS)) expect(source.includes(value), `reasons.ts 不得寫 SI reason 的字面值 ${value}（只指向 SI_REASONS）`).toBe(false);
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

// ══ 寫入面（P2b；TCS-SelfImprovingDecide-P2b W17、§5.2 表 M-V／M-D／M-O／M-C）═══════════════════════════════════════
// 為什麼重要：這些純函式決定「畫面上哪些決定可下、哪些本文會被送出」。動詞集合錯一個＝讓掌舵者對狀態不符的卡下決定（入帳時才被 CLI 拒收，而 Console 永遠
// 顯示待入帳）；必填／禁止欄與 backend 的 SiWriteGates 不同步＝前端放行的本文被 422、或前端擋下 backend 其實接受的本文。所以期望值一律取自 TCS 的表，
// 不取自被測碼的常數（DECIDE_FIELDS 的對拍另在 AT-950-9-2）。根層 ref.obs 會掃整個 repo 的 OBS-SI-<數字> 字面：不在帳本的壞號一律執行期組字串。

const GOOD_DIGEST = `sha256:${"d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c"}`;
/** 位數不足或位數過多的壞號：執行期才組出（見上方註解）。 */
const obsId = (digits: string) => `OBS-SI-${digits}`;
const propId = (digits: string) => `PROP-SI-${digits}`;

describe("AT_933_1_1 decideVerbOptions 對卡片情境表 M-V 的動詞集合逐列相符，預設不選動詞", () => {
  type Row = { n: number; card: DecideCard; expected: Array<[label: string, dkind: string, needsAck: boolean]> };
  const COOLING = { class: "M", until: "2026-11-01" };
  const ROWS: Row[] = [
    {
      n: 1,
      card: { state: "proposed", route: "loop", verdict: null, cooldown: null },
      expected: [
        ["核准", "approve", false],
        ["否決", "reject", false],
        ["退回", "return", false],
      ],
    },
    {
      n: 2,
      card: { state: "proposed", route: "handoff:T1", verdict: null, cooldown: null },
      expected: [
        ["轉交", "ack-handoff", false],
        ["不轉交", "reject", false],
        ["退回", "return", false],
      ],
    },
    {
      n: 3,
      card: { state: "verified", route: "loop", verdict: "PASS", cooldown: null },
      expected: [
        ["晉升", "promote", false],
        ["不晉升", "decline-promote", false],
      ],
    },
    {
      n: 4,
      card: { state: "verified", route: "loop", verdict: "NE", cooldown: null },
      expected: [
        ["晉升（未驗採納）", "promote", true],
        ["不晉升", "decline-promote", false],
      ],
    },
    {
      n: 5,
      card: { state: "verified", route: "loop", verdict: "FAIL", cooldown: null },
      expected: [
        ["退回", "return", false],
        ["不晉升", "decline-promote", false],
      ],
    },
    { n: 6, card: { state: "rejected", route: "loop", verdict: "FAIL", cooldown: COOLING }, expected: [["解除", "unblock", false]] },
    { n: 7, card: { state: "rejected", route: "loop", verdict: "FAIL", cooldown: null }, expected: [] },
    { n: 8, card: { state: "promoted", route: "loop", verdict: "PASS", cooldown: null }, expected: [["回滾", "rollback", false]] },
    { n: 9, card: { state: "measuring", route: "loop", verdict: "PASS", cooldown: null }, expected: [["回滾", "rollback", false]] },
    { n: 10, card: { state: "approved", route: "loop", verdict: null, cooldown: null }, expected: [] },
    { n: 11, card: { suspended: { run: "RUN-SI-001" } }, expected: [["恢復", "resume", false]] },
  ];
  const asTriples = (card: DecideCard) => decideVerbOptions(card).map((v) => [v.label, v.dkind, v.needsAck]);

  it("AT_933_1_1 表 M-V 的十一列：每列回傳的 {label, dkind, needsAck} 序列與期望逐項相同", () => {
    for (const row of ROWS) expect(asTriples(row.card), `M-V 第 ${row.n} 列`).toEqual(row.expected);
  });

  it("AT_933_1_1 同表的同義列：closed 與 measuring 同、returned 與 handed-off 與 approved 同；冷卻中的 rejected 不看 verdict；已解除不論 verdict 都沒有控件", () => {
    expect(asTriples({ state: "closed", route: "loop", verdict: "PASS", cooldown: null })).toEqual([["回滾", "rollback", false]]);
    for (const state of ["approved", "returned", "handed-off"]) expect(asTriples({ state, route: "loop", verdict: null, cooldown: null }), state).toEqual([]);
    for (const verdict of ["PASS", "NE", "FAIL", null]) {
      expect(asTriples({ state: "rejected", route: "loop", verdict, cooldown: COOLING }), `冷卻中 ${String(verdict)}`).toEqual([["解除", "unblock", false]]);
      expect(asTriples({ state: "rejected", route: "loop", verdict, cooldown: null }), `已解除 ${String(verdict)}`).toEqual([]);
    }
  });

  it("AT_933_1_1 PROP 情境得到的 dkind 聯集恰為八個，加 resume 共九個，不多不少；任何列都沒有預設選取項（選項物件只有 label、dkind、needsAck 三鍵）", () => {
    const union = new Set(ROWS.filter((r) => r.n !== 11).flatMap((r) => decideVerbOptions(r.card).map((v) => v.dkind)));
    expect([...union].sort()).toEqual(["ack-handoff", "approve", "decline-promote", "promote", "reject", "return", "rollback", "unblock"]);
    const all = new Set([...union, ...decideVerbOptions({ suspended: { run: "RUN-SI-001" } }).map((v) => v.dkind)]);
    expect(all.size).toBe(9);
    for (const row of ROWS) for (const option of decideVerbOptions(row.card)) expect(Object.keys(option).sort(), `M-V 第 ${row.n} 列`).toEqual(["dkind", "label", "needsAck"]);
  });

  it("AT_933_1_1 負控：表外的組合一律沒有控件（前端不替根層猜前提）；NE 的卡沒有「退回」、FAIL 的卡沒有「晉升」、橫幅 suspended 為 null 或不是帶 run 的物件時沒有「恢復」", () => {
    expect(asTriples({ state: "proposed", route: "other", verdict: null, cooldown: null })).toEqual([]);
    expect(asTriples({ state: "proposed", route: undefined })).toEqual([]);
    expect(asTriples({ state: "verified", route: "loop", verdict: null, cooldown: null })).toEqual([]);
    expect(asTriples({ state: "verified", route: "loop", verdict: "待定", cooldown: null })).toEqual([]);
    expect(asTriples({ state: "applied", route: "loop", verdict: "PASS", cooldown: null })).toEqual([]);
    expect(asTriples({})).toEqual([]);
    expect(decideVerbOptions({ state: "verified", route: "loop", verdict: "NE" }).map((v) => v.dkind)).not.toContain("return");
    expect(decideVerbOptions({ state: "verified", route: "loop", verdict: "FAIL" }).map((v) => v.dkind)).not.toContain("promote");
    expect(decideVerbOptions({ state: "verified", route: "loop", verdict: "PASS" }).some((v) => v.needsAck)).toBe(false);
    for (const suspended of [null, "RUN-SI-001", ["RUN-SI-001"], {}, { run: 1 }, { run: "" }]) expect(asTriples({ suspended }), JSON.stringify(suspended)).toEqual([]);
    expect(suspendedRun({ run: "RUN-SI-001", extra: 1 })).toBe("RUN-SI-001");
    expect(suspendedRun(null)).toBeNull();
    expect(suspendedRun(undefined)).toBeNull();
  });
});

describe("AT_950_9_2 純函式：三個驗證函式、ingestCommands、pendingWrites、siWriteErrorText 與 SI_REASONS", () => {
  // ── 表 M-D（決定）：期望取自 TCS，不取自 DECIDE_FIELDS ──
  const M_D: Array<[dkind: string, required: string[], forbidden: string[]]> = [
    ["approve", ["digest"], ["reason", "reasonClass", "unverifiedAck"]],
    ["reject", ["digest", "reason", "reasonClass"], ["unverifiedAck"]],
    ["return", ["digest", "reason", "reasonClass"], ["unverifiedAck"]],
    ["promote", ["digest"], ["reason", "reasonClass"]],
    ["decline-promote", ["digest", "reason", "reasonClass"], ["unverifiedAck"]],
    ["rollback", ["reason"], ["digest", "reasonClass", "unverifiedAck"]],
    ["unblock", [], ["digest", "reason", "reasonClass", "unverifiedAck"]],
    ["resume", ["reason"], ["digest", "reasonClass", "unverifiedAck"]],
    ["ack-handoff", ["digest"], ["reason", "reasonClass", "unverifiedAck"]],
  ];
  const BLANK: DecideForm = { dkind: "", digest: "", reason: "", reasonClass: "", unverifiedAck: false };
  const FILLED: Record<string, Partial<DecideForm>> = {
    digest: { digest: GOOD_DIGEST },
    reason: { reason: "證據座標不足，無法判定" },
    reasonClass: { reasonClass: "證據不足" },
    unverifiedAck: { unverifiedAck: true },
  };
  const formFor = (dkind: string, fields: string[]): DecideForm => fields.reduce<DecideForm>((form, f) => ({ ...form, ...FILLED[f] }), { ...BLANK, dkind });
  const keys = (errors: Record<string, string>) => Object.keys(errors).sort();

  it("AT_950_9_2 validateDecideForm 對表 M-D 九列：填齊必填欄得空物件；逐欄清空只該欄報錯；逐一填入禁止欄只該欄報錯", () => {
    for (const [dkind, required, forbidden] of M_D) {
      expect(validateDecideForm(formFor(dkind, required)), `${dkind} 填齊`).toEqual({});
      for (const field of required) {
        const without = required.filter((f) => f !== field);
        expect(keys(validateDecideForm(formFor(dkind, without))), `${dkind} 缺 ${field}`).toEqual([field]);
      }
      for (const field of forbidden) {
        expect(keys(validateDecideForm(formFor(dkind, [...required, field]))), `${dkind} 多填 ${field}`).toEqual([field]);
      }
    }
  });

  it("AT_950_9_2 動詞未選回 dkind 錯（預設拒絕）；未知動詞同；晉升後式（needsAck）未勾選回 unverifiedAck 錯、勾選後通過；PASS 的晉升不可勾選", () => {
    expect(keys(validateDecideForm(BLANK))).toEqual(["dkind"]);
    expect(keys(validateDecideForm({ ...BLANK, dkind: "approve-all" }))).toEqual(["dkind"]);
    const promote = formFor("promote", ["digest"]);
    expect(keys(validateDecideForm(promote, { needsAck: true }))).toEqual(["unverifiedAck"]);
    expect(validateDecideForm({ ...promote, unverifiedAck: true }, { needsAck: true })).toEqual({});
    expect(keys(validateDecideForm({ ...promote, unverifiedAck: true }, { needsAck: false }))).toEqual(["unverifiedAck"]);
    expect(validateDecideForm(promote, { needsAck: false })).toEqual({});
  });

  it("AT_950_9_2 validateDecideForm 的格式與長度：digest 須為 sha256: 加 64 位小寫十六進位；理由含換行或 TAB（含首尾）、全空白、501 個 code point 皆錯，恰 500 與 500 個表情符號（各算 1）通過；理由類別限七個", () => {
    const base = formFor("reject", ["digest", "reasonClass"]);
    for (const digest of ["sha256:abc", `sha256:${"A".repeat(64)}`, `SHA256:${"a".repeat(64)}`, `sha256:${"a".repeat(63)}g`, `${GOOD_DIGEST} `]) {
      expect(keys(validateDecideForm({ ...base, digest, reason: "x" })), digest).toEqual(["digest"]);
    }
    for (const reason of ["第一行\n第二行", "\t理由", "理由\r", "   ", ""]) expect(keys(validateDecideForm({ ...base, reason })), JSON.stringify(reason)).toEqual(["reason"]);
    expect(keys(validateDecideForm({ ...base, reason: "字".repeat(501) }))).toEqual(["reason"]);
    expect(validateDecideForm({ ...base, reason: "字".repeat(500) })).toEqual({});
    expect(validateDecideForm({ ...base, reason: "😀".repeat(500) }), "表情符號以 code point 計").toEqual({});
    expect(keys(validateDecideForm({ ...base, reason: "😀".repeat(501) }))).toEqual(["reason"]);
    expect(keys(validateDecideForm({ ...base, reason: "壞\ud800字" })), "孤立的代理字元").toEqual(["reason"]);
    for (const reasonClass of ["", "其他", "證據不足 "]) expect(keys(validateDecideForm({ ...base, reason: "x", reasonClass })), reasonClass).toEqual(["reasonClass"]);
    for (const reasonClass of ["證據不足", "風險過高", "工件類別錯", "已被涵蓋", "範圍外", "卡面不清", "未說明"]) expect(validateDecideForm({ ...base, reason: "x", reasonClass })).toEqual({});
  });

  it("AT_950_9_2 buildDecideRequest：只帶該動詞的欄位（鍵序 dkind、digest、reason、reasonClass、unverifiedAck）、字串欄去前後空白；G1、G2 的固定輸入逐字相同", () => {
    expect(JSON.stringify(buildDecideRequest({ ...BLANK, dkind: "approve", digest: GOOD_DIGEST, reason: "不該帶", reasonClass: "未說明" }))).toBe(`{"dkind":"approve","digest":"${GOOD_DIGEST}"}`);
    expect(JSON.stringify(buildDecideRequest({ ...BLANK, dkind: "reject", digest: GOOD_DIGEST, reason: " 證據座標不足，無法判定 ", reasonClass: "證據不足" }))).toBe(
      `{"dkind":"reject","digest":"${GOOD_DIGEST}","reason":"證據座標不足，無法判定","reasonClass":"證據不足"}`,
    );
    expect(JSON.stringify(buildDecideRequest({ ...BLANK, dkind: "promote", digest: GOOD_DIGEST, unverifiedAck: true }))).toBe(`{"dkind":"promote","digest":"${GOOD_DIGEST}","unverifiedAck":true}`);
    expect(JSON.stringify(buildDecideRequest({ ...BLANK, dkind: "promote", digest: GOOD_DIGEST }))).toBe(`{"dkind":"promote","digest":"${GOOD_DIGEST}"}`);
    expect(JSON.stringify(buildDecideRequest({ ...BLANK, dkind: "unblock", digest: GOOD_DIGEST, reason: "x" }))).toBe('{"dkind":"unblock"}');
    expect(JSON.stringify(buildDecideRequest({ ...BLANK, dkind: "resume", reason: "兩個壞窗已人工檢視" }))).toBe('{"dkind":"resume","reason":"兩個壞窗已人工檢視"}');
    expect(() => buildDecideRequest({ ...BLANK, dkind: "nope" })).toThrow();
    // 與表 M-D 的必填欄逐列對拍：buildDecideRequest 的鍵集合恰為「dkind 加必填欄」
    for (const [dkind, required] of M_D) {
      const body = buildDecideRequest({ ...BLANK, ...formFor(dkind, [...required, "unverifiedAck"]), dkind, unverifiedAck: false });
      expect(Object.keys(body).sort(), dkind).toEqual(["dkind", ...required].sort());
      expect(Object.keys(DECIDE_FIELDS[dkind as keyof typeof DECIDE_FIELDS]).sort(), `DECIDE_FIELDS.${dkind} 的鍵`).toEqual(["digest", "reason", "reasonClass"]);
      expect(
        Object.entries(DECIDE_FIELDS[dkind as keyof typeof DECIDE_FIELDS])
          .filter(([, v]) => v)
          .map(([k]) => k)
          .sort(),
        `DECIDE_FIELDS.${dkind}`,
      ).toEqual([...required].sort());
    }
  });

  // ── 表 M-O（觀察）──
  const O1: ObservationForm = {
    context: "Console・自我進化頁",
    symptom: "待入帳徽章在入帳後仍顯示",
    evidence: "AgentConsole/frontend/components/domain/si/SiView.tsx:88",
    category: "bug",
    severity: "P3",
    face: "產品",
    exposure: "",
    externalDerived: false,
    corrects: "",
  };
  const O2: ObservationForm = { ...O1, category: "tooling", severity: "P2", face: "守衛", exposure: "b", externalDerived: true };
  const O3: ObservationForm = { ...O1, corrects: "OBS-SI-001" };

  it("AT_950_9_2 validateObservationForm：O1、O2、O3 通過；空表單六個必填欄全報錯；逐欄清空只該欄報錯（三字串欄加三列舉）", () => {
    for (const form of [O1, O2, O3]) expect(validateObservationForm(form)).toEqual({});
    expect(keys(validateObservationForm(EMPTY_OBSERVATION_FORM))).toEqual(["category", "context", "evidence", "face", "severity", "symptom"]);
    for (const field of ["context", "symptom", "evidence", "category", "severity", "face"] as const) {
      expect(keys(validateObservationForm({ ...O1, [field]: "" })), `清空 ${field}`).toEqual([field]);
    }
  });

  it("AT_950_9_2 validateObservationForm 的字串規則：豎線、換行、TAB、首尾換行、全空白各只該欄報錯；300 個 code point 通過、301 報錯；列舉外值報錯", () => {
    for (const field of ["context", "symptom", "evidence"] as const) {
      for (const bad of ["含|豎線", "兩行\n第二行", "含\tTAB", "\n開頭換行", "結尾換行\n", "   "]) {
        expect(keys(validateObservationForm({ ...O1, [field]: bad })), `${field}＝${JSON.stringify(bad)}`).toEqual([field]);
      }
      expect(keys(validateObservationForm({ ...O1, [field]: "字".repeat(301) })), `${field} 301`).toEqual([field]);
      expect(
        validateObservationForm({
          ...O1,
          [field]: "x".repeat(300),
          ...(field === "context" ? { symptom: "s", evidence: "e" } : field === "symptom" ? { context: "c", evidence: "e" } : { context: "c", symptom: "s" }),
        }),
      ).toEqual({});
    }
    for (const [field, value] of [
      ["category", "feature"],
      ["severity", "P5"],
      ["face", "產品線"],
      ["category", "Bug"],
    ] as const) {
      expect(keys(validateObservationForm({ ...O1, [field]: value })), `${field}＝${value}`).toEqual([field]);
    }
  });

  it("AT_950_9_2 validateObservationForm 的位元組和：三字串欄 UTF-8 位元組和恰 700 通過、701 三欄一併報錯（各欄本身都在 300 個 code point 內）", () => {
    const at700 = { ...O1, context: "a".repeat(300), symptom: "b".repeat(300), evidence: "c".repeat(100) };
    const at701 = { ...at700, evidence: "c".repeat(101) };
    expect(validateObservationForm(at700)).toEqual({});
    expect(keys(validateObservationForm(at701))).toEqual(["context", "evidence", "symptom"]);
    // 以位元組而非字元計：200 個 CJK 字（600 位元組）加 100 個 ASCII＝700 通過，再加 1 個 ASCII 就超過
    expect(validateObservationForm({ ...O1, context: "字".repeat(100), symptom: "字".repeat(100), evidence: "c".repeat(100) })).toEqual({});
    expect(keys(validateObservationForm({ ...O1, context: "字".repeat(100), symptom: "字".repeat(100), evidence: "c".repeat(101) }))).toEqual(["context", "evidence", "symptom"]);
  });

  it("AT_950_9_2 validateObservationForm 的暴露度與更正：守衛面必填且限 a、b、c、無；非守衛面禁止；corrects 選填、須為 OBS-SI- 接三位以上數字（四位數也合格）", () => {
    expect(keys(validateObservationForm({ ...O1, face: "守衛" }))).toEqual(["exposure"]);
    expect(keys(validateObservationForm({ ...O1, face: "守衛", exposure: "d" }))).toEqual(["exposure"]);
    for (const exposure of ["a", "b", "c", "無"]) expect(validateObservationForm({ ...O1, face: "守衛", exposure })).toEqual({});
    expect(keys(validateObservationForm({ ...O1, exposure: "a" })), "產品面帶暴露度").toEqual(["exposure"]);
    expect(validateObservationForm({ ...O1, face: "", exposure: "" })).toEqual({ face: expect.any(String) });
    for (const corrects of [obsId("01"), "obs-si-001", propId("001"), `${obsId("001")}x`, "OBS-SI-001\n", "ABC"]) {
      expect(keys(validateObservationForm({ ...O1, corrects })), JSON.stringify(corrects)).toEqual(["corrects"]);
    }
    for (const corrects of ["OBS-SI-001", obsId("1234"), "", "   "]) expect(validateObservationForm({ ...O1, corrects }), JSON.stringify(corrects)).toEqual({});
  });

  it("AT_950_9_2 buildObservationRequest：O1、O3 與黃金檔 G3、G4 的固定輸入逐字相同；O2 帶 exposure 與 externalDerived；守衛面以外不帶 exposure；corrects 空白不帶", () => {
    expect(JSON.stringify(buildObservationRequest(O1))).toBe(
      '{"context":"Console・自我進化頁","symptom":"待入帳徽章在入帳後仍顯示","evidence":"AgentConsole/frontend/components/domain/si/SiView.tsx:88","category":"bug","severity":"P3","face":"產品","externalDerived":false}',
    );
    expect(JSON.stringify(buildObservationRequest(O3))).toBe(
      '{"context":"Console・自我進化頁","symptom":"待入帳徽章在入帳後仍顯示","evidence":"AgentConsole/frontend/components/domain/si/SiView.tsx:88","category":"bug","severity":"P3","face":"產品","externalDerived":false,"corrects":"OBS-SI-001"}',
    );
    expect(buildObservationRequest(O2)).toEqual({
      ...JSON.parse(JSON.stringify(buildObservationRequest(O1))),
      category: "tooling",
      severity: "P2",
      face: "守衛",
      exposure: "b",
      externalDerived: true,
    });
    expect(buildObservationRequest({ ...O1, exposure: "a", corrects: "   ", context: " 情境 " })).toEqual({ ...buildObservationRequest(O1), context: "情境" });
  });

  // ── 表 M-C（關閉）──
  const M_C: Array<[terminal: string, form: CloseForm, disposition: string]> = [
    ["fixed", { terminal: "fixed", ref: "2b2b0b3d", text: "" }, "fixed@2b2b0b3d"],
    ["def", { terminal: "def", ref: "DEF-200-559", text: "" }, "DEF-200-559"],
    ["deferred", { terminal: "deferred", ref: "", text: "等 P3 輪" }, "deferred：等 P3 輪"],
    ["retired", { terminal: "retired", ref: "", text: "docs/06_quality/SelfImproving_Protocol/params.json" }, "retired：docs/06_quality/SelfImproving_Protocol/params.json"],
    ["decided", { terminal: "decided", ref: "", text: "夾具關閉" }, "decided：夾具關閉"],
    ["merged", { terminal: "merged", ref: "OBS-SI-001", text: "" }, "merged@OBS-SI-001"],
    ["proposed", { terminal: "proposed", ref: "PROP-SI-004", text: "" }, "proposed@PROP-SI-004"],
  ];

  it("AT_950_9_2 validateCloseForm 與 buildCloseRequest 對表 M-C 七列：有效輸入通過、請求本文為 {terminal, ref} 或 {terminal, text}；必填欄清空只該欄報錯；另一欄多填只該欄報錯", () => {
    for (const [terminal, form] of M_C) {
      expect(validateCloseForm(form), terminal).toEqual({});
      const takesRef = form.ref !== "";
      expect(buildCloseRequest(form), terminal).toEqual(takesRef ? { terminal, ref: form.ref } : { terminal, text: form.text });
      expect(keys(validateCloseForm({ ...form, [takesRef ? "ref" : "text"]: "" })), `${terminal} 缺必填`).toEqual([takesRef ? "ref" : "text"]);
      expect(keys(validateCloseForm({ ...form, [takesRef ? "text" : "ref"]: "多填" })), `${terminal} 多填`).toEqual([takesRef ? "text" : "ref"]);
    }
    expect(JSON.stringify(buildCloseRequest({ terminal: "decided", ref: "", text: "夾具關閉" }))).toBe('{"terminal":"decided","text":"夾具關閉"}');
    expect(buildCloseRequest({ terminal: "fixed", ref: " 2b2b0b3d ", text: "" })).toEqual({ terminal: "fixed", ref: "2b2b0b3d" });
  });

  it("AT_950_9_2 validateCloseForm 的終值與格式：open、未選、未知終值報 terminal；fixed 的 ref 限 7～40 碼小寫十六進位；def、merged、proposed 的格式；text 的豎線、之後再看、控制字元、121 個 code point 報錯、恰 120 通過", () => {
    for (const terminal of ["open", "", "closed", "FIXED"]) expect(keys(validateCloseForm({ terminal, ref: "2b2b0b3d", text: "" })), terminal).toEqual(["terminal"]);
    for (const ref of ["2b2b0b", "2b2b0b3D", "g2b2b0b3d", "a".repeat(41), "2b2b 0b3d"]) expect(keys(validateCloseForm({ terminal: "fixed", ref, text: "" })), `fixed ${ref}`).toEqual(["ref"]);
    for (const ref of ["a".repeat(7), "a".repeat(40)]) expect(validateCloseForm({ terminal: "fixed", ref, text: "" }), ref).toEqual({});
    for (const ref of ["DEF-200", "def-200-559", "DEF-x-1", "DEF-200-559 x"]) expect(keys(validateCloseForm({ terminal: "def", ref, text: "" })), `def ${ref}`).toEqual(["ref"]);
    for (const ref of [obsId("01"), "OBS-SI-ABC", propId("004")]) expect(keys(validateCloseForm({ terminal: "merged", ref, text: "" })), `merged ${ref}`).toEqual(["ref"]);
    for (const ref of [propId("04"), "PROP-SI-X", "OBS-SI-001"]) expect(keys(validateCloseForm({ terminal: "proposed", ref, text: "" })), `proposed ${ref}`).toEqual(["ref"]);
    for (const text of ["含|豎線", "之後再看", "等一下之後再看看", "兩行\n第二行", "\t", "   ", "字".repeat(121)]) {
      expect(keys(validateCloseForm({ terminal: "deferred", ref: "", text })), JSON.stringify(text)).toEqual(["text"]);
    }
    expect(validateCloseForm({ terminal: "decided", ref: "", text: "字".repeat(120) })).toEqual({});
    expect(validateCloseForm({ terminal: "decided", ref: "", text: "😀".repeat(120) }), "表情符號以 code point 計").toEqual({});
    expect(keys(validateCloseForm({ terminal: "decided", ref: "", text: "😀".repeat(121) }))).toEqual(["text"]);
  });

  it("AT_950_9_2 ingestCommands：三種 kind 的輸出逐字如 W17，PowerShell 與 POSIX 兩段字串相同；decide 帶對象（resume 為 RUN 號）、obs-add 與 obs-close 不帶", () => {
    const ref = "b2000000-0000-4000-8000-000000000001";
    expect(ingestCommands("decide", "PROP-SI-004", ref)).toEqual({
      powershell: `python tools/selfimproving.py decide PROP-SI-004 --carrier console --audit-ref ${ref}`,
      posix: `python tools/selfimproving.py decide PROP-SI-004 --carrier console --audit-ref ${ref}`,
    });
    expect(ingestCommands("decide", "RUN-SI-001", ref).posix).toBe(`python tools/selfimproving.py decide RUN-SI-001 --carrier console --audit-ref ${ref}`);
    expect(ingestCommands("obs-add", null, ref)).toEqual({
      powershell: `python tools/selfimproving.py obs-add --carrier console --audit-ref ${ref}`,
      posix: `python tools/selfimproving.py obs-add --carrier console --audit-ref ${ref}`,
    });
    expect(ingestCommands("obs-close", "OBS-SI-005", ref).powershell).toBe(`python tools/selfimproving.py obs-close --carrier console --audit-ref ${ref}`);
    for (const kind of ["decide", "obs-add", "obs-close"] as const) {
      const c = ingestCommands(kind, "PROP-SI-004", ref);
      expect(c.powershell).toBe(c.posix);
      expect(c.powershell, "金鑰不出現在指令").not.toMatch(/AUTOSDD_SI_AUDIT_KEY|key/i);
    }
  });

  it("AT_950_9_2 pendingWrites：只回 ingested 為 false 者、依 time 升冪（同刻依 auditRef）、null 與 true 不回；不改動輸入；空清單回空", () => {
    const item = (auditRef: string, time: string, ingested: boolean | null, kind: SiConsoleWrite["kind"] = "decide"): SiConsoleWrite => ({
      auditRef,
      kind,
      user: "admin",
      role: "ADMIN",
      time,
      subjectId: kind === "obs-add" ? null : "PROP-SI-004",
      digest: null,
      keyId: "f076edf0",
      ingested,
    });
    const items = [
      item("c0000000-0000-4000-8000-000000000003", "2026-10-24T14:30:15Z", false, "obs-close"),
      item("a0000000-0000-4000-8000-000000000001", "2026-10-24T14:30:17Z", true),
      item("b0000000-0000-4000-8000-000000000002", "2026-10-24T14:30:10Z", false, "obs-add"),
      item("d0000000-0000-4000-8000-000000000004", "2026-10-24T14:30:12Z", null),
      item("a1000000-0000-4000-8000-000000000005", "2026-10-24T14:30:15Z", false),
    ];
    const snapshot = JSON.stringify(items);
    expect(pendingWrites(items).map((i) => i.auditRef)).toEqual(["b0000000-0000-4000-8000-000000000002", "a1000000-0000-4000-8000-000000000005", "c0000000-0000-4000-8000-000000000003"]);
    expect(JSON.stringify(items), "輸入不被改動").toBe(snapshot);
    expect(pendingWrites([])).toEqual([]);
    expect(pendingWrites([item("a0000000-0000-4000-8000-000000000001", "2026-10-24T14:30:17Z", true), item("d0000000-0000-4000-8000-000000000004", "2026-10-24T14:30:12Z", null)])).toEqual([]);
  });

  it("AT_950_9_2 siWriteErrorText：主訊息含 reason 逐字；422 另列各 violation 的 欄位：訊息（取 details.violations，沒有時退回 errors[]）；503 si_unavailable 另列 cause 與 detail 逐字；其餘狀態不加料", () => {
    const forbidden = new ApiError({ status: 403, message: "帳號不在決定者名單內", reason: "si_write_forbidden", traceId: "tr-1" });
    expect(siWriteErrorText(forbidden)).toBe("帳號不在決定者名單內：si_write_forbidden（traceId：tr-1）");
    expect(siWriteErrorText(new ApiError({ status: 409, message: "稽核檔已存在", reason: "si_audit_exists" }))).toBe("稽核檔已存在：si_audit_exists");
    expect(siWriteErrorText(new ApiError({ status: 503, message: "寫入面已停用", reason: "si_write_disabled", details: { cause: "audit_key_unset" } }))).toBe("寫入面已停用：si_write_disabled");
    const unprocessable = new ApiError({
      status: 422,
      message: "請求欄位未通過檢查（2 項）",
      reason: "invalid_request",
      errors: [{ field: "reason", message: "reason 為必填" }],
      details: {
        violations: [
          { field: "reason", message: "理由為必填" },
          { field: "reasonClass", message: "理由類別為必填" },
        ],
      },
    });
    expect(siWriteErrorText(unprocessable)).toBe("請求欄位未通過檢查（2 項）：invalid_request；reason：理由為必填；reasonClass：理由類別為必填");
    const onlyErrors = new ApiError({ status: 422, message: "未通過", reason: "invalid_request", errors: [{ field: "context", message: "情境為必填" }] });
    expect(siWriteErrorText(onlyErrors)).toBe("未通過：invalid_request；context：情境為必填");
    const unavailable = new ApiError({ status: 503, message: "SI 資料面不可用", reason: "si_unavailable", details: { cause: "audit_write_failed", detail: "errno=13; PermissionError" } });
    expect(siWriteErrorText(unavailable)).toBe("SI 資料面不可用：si_unavailable；cause：audit_write_failed；detail：errno=13; PermissionError");
    // 結果不明（逾時、送出後通訊失敗）：reason 缺席，主訊息原樣；非 422 與非 si_unavailable 不加料
    expect(siWriteErrorText(new ApiError({ status: 504, message: "引擎橋接服務逾時；稽核檔可能已落地，稽核列已保留（結果不明）", details: { outcomeUnknown: true } }))).toBe(
      "引擎橋接服務逾時；稽核檔可能已落地，稽核列已保留（結果不明）",
    );
    expect(siWriteErrorText(new Error("網路"))).toBe("網路");
    expect(siWriteErrorText("字串")).toBe("發生未知錯誤");
  });
});

describe("AT_950_9_3 estimateRowBytes：受控輸入的估計值等於真 CLI 預覽的 row_bytes（O1、O2、O3 與組合例）", () => {
  const O1: ObservationForm = {
    context: "Console・自我進化頁",
    symptom: "待入帳徽章在入帳後仍顯示",
    evidence: "AgentConsole/frontend/components/domain/si/SiView.tsx:88",
    category: "bug",
    severity: "P3",
    face: "產品",
    exposure: "",
    externalDerived: false,
    corrects: "",
  };
  const ADMIN = { user: "admin" };

  it("AT_950_9_3 O1、O2、O3 的估計值依序為 287、317、311（真 CLI dry-run 的 row_bytes；TCS §5.2 實測）", () => {
    expect(estimateRowBytes(O1, ADMIN)).toBe(287);
    expect(estimateRowBytes({ ...O1, category: "tooling", severity: "P2", face: "守衛", exposure: "b", externalDerived: true }, ADMIN)).toBe(317);
    expect(estimateRowBytes({ ...O1, corrects: "OBS-SI-001" }, ADMIN)).toBe(311);
  });

  it("AT_950_9_3 組合例（真 CLI 當回合實測的 row_bytes）：守衛加外部衍生加更正 337、僅外部衍生 304、守衛暴露為無加更正 322、帳號 a.b_c-1 為 289、時間偏移不影響寬度 287", () => {
    expect(estimateRowBytes({ ...O1, face: "守衛", exposure: "a", externalDerived: true, corrects: "OBS-SI-001" }, ADMIN)).toBe(337);
    expect(estimateRowBytes({ ...O1, externalDerived: true }, ADMIN)).toBe(304);
    expect(estimateRowBytes({ ...O1, face: "守衛", exposure: "無", corrects: "OBS-SI-002" }, ADMIN)).toBe(322);
    expect(estimateRowBytes(O1, { user: "a.b_c-1" })).toBe(289);
  });

  it("AT_950_9_3 估計值逐項依欄位增減：字串欄去前後空白、OBS 號位數每多一位多一位元組、CJK 一字三位元組；缺的列舉算 0 位元組（邊打邊估）", () => {
    const base = estimateRowBytes(O1, ADMIN) as number;
    expect(estimateRowBytes({ ...O1, context: `  ${O1.context}  ` }, ADMIN)).toBe(base);
    expect(estimateRowBytes(O1, { ...ADMIN, obsDigits: 4 })).toBe(base + 1);
    expect(estimateRowBytes({ ...O1, symptom: `${O1.symptom}字` }, ADMIN)).toBe(base + 3);
    expect(estimateRowBytes({ ...O1, symptom: `${O1.symptom}a` }, ADMIN)).toBe(base + 1);
    expect(estimateRowBytes({ ...O1, category: "" }, ADMIN)).toBe(base - 3);
    expect(estimateRowBytes({ ...O1, exposure: "a" }, ADMIN), "非守衛面的暴露度不進標記欄").toBe(base);
  });

  it("AT_950_9_3 含豎線或控制字元（任一個字串欄）回 null，不給估計值；無關欄位的控制字元不影響", () => {
    for (const field of ["context", "symptom", "evidence"] as const) {
      for (const bad of ["含|豎線", "兩行\n第二行", "含\tTAB", "\u0000"]) expect(estimateRowBytes({ ...O1, [field]: bad }, ADMIN), `${field}＝${JSON.stringify(bad)}`).toBeNull();
    }
    expect(estimateRowBytes({ ...O1, corrects: "OBS-SI-001" }, ADMIN)).not.toBeNull();
  });
});
