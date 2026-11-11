import { describe, expect, it } from "vitest";

import { DROP, NOW, NOW_MS, PATROL, camelKeys, iso, keyPaths, patchMixed } from "@/tests/helpers/siFlow";
import { bannedFindings, longSentences } from "@/lib/help/readability";
import {
  DIFF_WINDOW_LINES,
  RECENT_INGESTED_SHOWN,
  SI_FLOW_TEXTS,
  STALE_FACTOR,
  STALE_GRACE_MINUTES,
  diffWindow,
  downloadSpec,
  fillText,
  heldoutView,
  joinHostRejections,
  labelOfIngestStatus,
  labelOfPurpose,
  labelOfVerdict,
  labelOfWho,
  maskCredentials,
  nextStepLine,
  parseDiff,
  patrolFreshness,
  pushStateInfo,
  pushView,
  reasonText,
  relativeMinutesText,
  resolveNextStep,
  sandboxView,
  scheduleView,
  sectionState,
  verifyView,
  waitingView,
} from "./siFlow";

const MIN = 60_000;
const T0 = 1_000_000_000_000;
const report = (generatedAt: string, heartbeatMinutes: unknown = 15) => ({ generatedAt, heartbeatMinutes });

describe("AT_966_5_1 新鮮度邊界表與隨時間前進", () => {
  it("常數值", () => {
    expect([STALE_FACTOR, STALE_GRACE_MINUTES, DIFF_WINDOW_LINES, RECENT_INGESTED_SHOWN]).toEqual([2, 5, 400, 5]);
  });
  it.each([
    ["早 0", iso(0), 15, "fresh", 35],
    ["早 34:59", iso(34, 59), 15, "fresh", 35],
    ["早 35:00", iso(35), 15, "fresh", 35],
    ["早 35:01", iso(35, 1), 15, "stale", 35],
    ["早 10 小時", iso(600), 15, "stale", 35],
    ["晚 4:59", iso(-4, -59), 15, "fresh", 35],
    ["晚 5:01", iso(-5, -1), 15, "clock-skew", 35],
    ["週期 5 限度 15", iso(15, 1), 5, "stale", 15],
    ["週期 5 限度 15（邊界）", iso(15), 5, "fresh", 15],
    ["週期 60 限度 125", iso(125), 60, "fresh", 125],
    ["週期 60 過 125", iso(125, 1), 60, "stale", 125],
  ])("%s", (label, generatedAt, hb, state, limit) => {
    const f = patrolFreshness(report(generatedAt, hb), NOW, T0, T0);
    expect(f.state, label).toBe(state);
    expect(f.limitMinutes, label).toBe(limit);
    expect(f.usedClientClock).toBe(false);
    expect(f.ageMinutes).not.toBeNull();
    expect(f.ageMinutes as number).toBeGreaterThanOrEqual(0);
  });
  it("頁面放著不動，跨過門檻就轉過時（與是否重新抓取無關）", () => {
    const r = report(iso(3));
    const at = (extraMs: number) => patrolFreshness(r, NOW, T0, T0 + extraMs).state;
    expect(at(0)).toBe("fresh");
    expect(at(31 * MIN + 59_000)).toBe("fresh");
    expect(at(32 * MIN)).toBe("fresh");
    expect(at(32 * MIN + 1000)).toBe("stale");
  });
  it("readAt 缺席或無法解析時改用瀏覽器時間", () => {
    const gen = new Date(NOW_MS - 3 * MIN).toISOString();
    for (const readAt of [undefined, null, "不是時間"]) {
      const f = patrolFreshness(report(gen), readAt, T0, NOW_MS);
      expect(f.usedClientClock).toBe(true);
      expect(f.state).toBe("fresh");
      expect(Math.round(f.ageMinutes as number)).toBe(3);
    }
  });
  it("週期非正整數＝無法判斷；時間無法解析＝量不到", () => {
    for (const hb of [undefined, 0, -5, "15", Number.NaN, 1.5]) expect(patrolFreshness({ generatedAt: iso(1), heartbeatMinutes: hb }, NOW, T0, T0).state, String(hb)).toBe("unknown-period");
    expect(patrolFreshness(report("昨天"), NOW, T0, T0).state).toBe("unknown-time");
    expect(patrolFreshness(null, NOW, T0, T0).state).toBe("unknown-time");
  });
});

describe("AT_966_5_2 resolveNextStep 來源序", () => {
  const detailNext = { code: "D", who: "巡邏器", text: "詳情說的" };
  const fresh = (seq = 130) => ({ report: PATROL({ ledgerSeq: seq }).report, freshness: patrolFreshness(PATROL().report, NOW, T0, T0) });
  const base = { proposalId: "PROP-SI-901", lastSeq: 120 };
  it("八個情境", () => {
    const a = fresh();
    expect(resolveNextStep({ ...base, ...a, detailNext })).toMatchObject({ source: "snapshot", who: "掌舵者", warnPatrolMayBeDown: false });
    expect(resolveNextStep({ ...base, report: PATROL({ props: [] }).report, freshness: a.freshness, detailNext }).source).toBe("detail");
    const stale = patrolFreshness(PATROL({ generatedAt: iso(40) }).report, NOW, T0, T0);
    expect(resolveNextStep({ ...base, report: a.report, freshness: stale, detailNext })).toMatchObject({ source: "detail", warnPatrolMayBeDown: true });
    expect(resolveNextStep({ ...base, ...fresh(119), detailNext }).source).toBe("detail");
    expect(resolveNextStep({ ...base, ...fresh(120), detailNext }).source).toBe("snapshot");
    expect(resolveNextStep({ ...base, report: null, freshness: null, detailNext }).source).toBe("detail");
    expect(resolveNextStep({ ...base, report: null, freshness: null, detailNext: undefined })).toMatchObject({ source: "none", text: "量不到" });
    expect(resolveNextStep({ ...base, ...a, detailNext: undefined }).source).toBe("snapshot");
  });
  it("警示只在 who 為巡邏器且快照過時時出現", () => {
    const stale = patrolFreshness(PATROL({ generatedAt: iso(40) }).report, NOW, T0, T0);
    const r = PATROL().report;
    expect(resolveNextStep({ ...base, report: r, freshness: stale, detailNext: { ...detailNext, who: "掌舵者" } }).warnPatrolMayBeDown).toBe(false);
    expect(resolveNextStep({ ...base, report: r, freshness: fresh().freshness, detailNext }).source).toBe("snapshot");
  });
});

describe("AT_966_5_3 列舉已知判定與未知值保底", () => {
  it("下一步那一行：未知等待對象走未知值保底、已知對象原樣、缺席為量不到", () => {
    const line = (who: unknown) => nextStepLine({ source: "detail", who, text: "說明", warnPatrolMayBeDown: false });
    expect(line("外星人")).toBe("下一步：等未知值『外星人』｜說明");
    expect(line("掌舵者")).toBe("下一步：等掌舵者｜說明");
    expect(line(undefined)).toBe("下一步：等量不到｜說明");
    expect(line("無")).toBe("目前不需要任何人動作：說明");
  });
  it("已知值", () => {
    expect(labelOfPurpose("scheduled")).toEqual({ known: true, text: "排程啟動" });
    expect(labelOfPurpose("console").text).toBe("從畫面按『立即啟動』");
    expect(labelOfPurpose("manual").text).toBe("手動啟動");
    expect(["PASS", "FAIL", "NE"].map((v) => labelOfVerdict(v).text)).toEqual(["通過", "未通過", "無法評估"]);
    expect(["rejected", "deferred"].map((v) => labelOfIngestStatus(v).text)).toEqual(["被拒收", "延後"]);
    for (const w of ["掌舵者", "巡邏器", "無人運轉", "主機管理者", "無"]) expect(labelOfWho(w)).toEqual({ known: true, text: w });
  });
  it("推送八態只回已知與樣式，不回標籤句", () => {
    const expected: Record<string, string> = { off: "neutral", idle: "neutral", pending: "neutral", "waiting-login": "neutral", running: "neutral", ok: "ok", failed: "warn", blocked: "warn" };
    for (const [state, tone] of Object.entries(expected)) expect(pushStateInfo(state), state).toEqual({ known: true, tone });
    expect(Object.keys(pushStateInfo("ok")).sort()).toEqual(["known", "tone"]);
  });
  it.each([["freeze"], ["revise"], ["propose"], ["zzz"]])("第二波與未知運轉目的 %s 一律未知值", (v) => {
    expect(labelOfPurpose(v)).toEqual({ known: false, text: `未知值『${v}』` });
  });
  it("skipped 與 zzz 推送態未知；空值量不到；數字與物件不漏 [object Object]", () => {
    expect(pushStateInfo("skipped").known).toBe(false);
    expect(pushStateInfo("zzz").known).toBe(false);
    for (const v of ["", null, undefined]) expect(labelOfPurpose(v)).toEqual({ known: false, text: "量不到" });
    expect(labelOfPurpose(7).text).toBe("未知值『7』");
    expect(labelOfPurpose({ a: 1 }).text).toBe("未知值『[物件]』");
    expect(labelOfWho({ a: 1 }).text).not.toContain("[object Object]");
    expect(labelOfWho("外星人")).toEqual({ known: false, text: "未知值『外星人』" });
  });
});

describe("AT_966_5_4 reasonText 與 maskCredentials", () => {
  it("原因句", () => {
    expect(reasonText("STALE-CARD", "卡面已過期")).toBe("卡面已過期");
    expect(reasonText("X-1", "")).toBe("主機沒有提供白話說明（原因碼 X-1）。");
    expect(reasonText("X-1", undefined)).toBe("主機沒有提供白話說明（原因碼 X-1）。");
    expect(reasonText("X-1", 42)).toBe("主機沒有提供白話說明（原因碼 X-1）。");
    expect(reasonText(undefined, "只有說明")).toBe("只有說明");
    expect(reasonText(undefined, undefined)).toBe("主機沒有提供原因。");
  });
  it("憑證遮罩（網址在執行期拼出）", () => {
    const a = "push " + "https://" + "user" + ":" + "p%40ss" + "@github.com/x.git" + " failed";
    const b = "git@github.com:a/b.git";
    const c = "http://" + "a" + ":" + "b" + "@c/d https://e@f/g";
    expect(maskCredentials(a)).toBe("push https://***@github.com/x.git failed");
    expect(maskCredentials(a)).not.toContain("p%40ss");
    expect(maskCredentials(b)).toBe(b);
    expect(maskCredentials(c)).toBe("http://***@c/d https://***@f/g");
  });
});

describe("AT_966_5_5 parseDiff 解析與計數", () => {
  it("夾具逐行", () => {
    const d = parseDiff(patchMixed);
    const kinds = d.lines.map((l) => l.kind);
    expect(kinds).toEqual(["file", "file", "file", "file", "hunk", "ctx", "del", "add", "add", "ctx", "hunk", "del", "add", "ctx", "meta"]);
    expect(d.lines[8].text).toBe("+++x");
    expect(d.addCount).toBe(3);
    expect(d.delCount).toBe(2);
    expect(d.lines.map((l) => l.text).join("\n") + "\n").toBe(patchMixed);
  });
  it("空輸入、僅換行、無結尾換行、CRLF 行", () => {
    expect(parseDiff("").lines).toHaveLength(0);
    expect(parseDiff("\n").lines).toHaveLength(0);
    expect(parseDiff("+a\n-b").lines.map((l) => l.text)).toEqual(["+a", "-b"]);
    const crlf = parseDiff("+一行\r\n 二行\r\n");
    expect(crlf.lines).toHaveLength(2);
    expect(crlf.lines[0].text).toBe("+一行\r");
    expect(crlf.lines[0].kind).toBe("add");
  });
});

describe("AT_966_5_6 diffWindow 與 downloadSpec", () => {
  const lines = (n: number) => Array.from({ length: n }, (_, i) => i);
  it.each([
    [399, 399, 0, false],
    [400, 400, 0, false],
    [401, 400, 1, true],
    [1000, 400, 600, true],
  ])("%i 行", (n, shown, hidden, canExpand) => {
    const w = diffWindow(lines(n), false);
    expect([w.shown.length, w.hiddenCount, w.canExpand]).toEqual([shown, hidden, canExpand]);
    expect(diffWindow(lines(n), true).shown).toHaveLength(n);
  });
  it("下載描述", () => {
    const rel = "docs/06_quality/SelfImproving_Proposals/PROP-SI-901/r2.patch";
    expect(downloadSpec("PROP-SI-901", 2, { rel, text: "x", truncated: false })).toEqual({ filename: "PROP-SI-901-r2.patch", content: "x", mime: "text/plain;charset=utf-8" });
    expect(downloadSpec("PROP-SI-901", 2, { rel, text: "x", truncated: true }).filename).toBe("PROP-SI-901-r2.truncated.patch");
    expect(downloadSpec("PROP-SI-901", 2, { text: "x" }).filename).toBe("PROP-SI-901-r2.patch");
    const evil = downloadSpec("..\\PROP/SI\u0007", 2, { rel: "..\\..\\evil.patch", text: "" }).filename;
    expect(evil).toMatch(/^[A-Za-z0-9._-]+$/);
    expect(evil).not.toContain("/");
    expect(evil).not.toContain("\\");
  });
});

describe("AT_966_5_7 joinHostRejections", () => {
  const ing = (over: Record<string, unknown>) => ({ auditRef: "A1", kind: "decide", status: "rejected", code: "STALE-CARD", text: "卡面已過期", permanent: true, ...over });
  it("只結合未入帳列、重複取第一筆、無對應回 null", () => {
    const items = [
      { auditRef: "A1", ingested: false },
      { auditRef: "A2", ingested: false },
      { auditRef: "A3", ingested: true },
      { auditRef: "A4", ingested: null },
    ];
    const rep = PATROL({ ingest: [ing({}), ing({ code: "SECOND" }), ing({ auditRef: "A3" })] }).report;
    const out = joinHostRejections(items, rep);
    expect(out.map((o) => o.auditRef)).toEqual(["A1", "A2"]);
    expect(out[0].join).toMatchObject({ code: "STALE-CARD", mode: "human" });
    expect(out[1].join).toBeNull();
  });
  it.each([
    [true, "human"],
    [false, "auto"],
    [undefined, "unknown"],
    ["yes", "unknown"],
  ])("permanent=%s → %s", (permanent, mode) => {
    const out = joinHostRejections([{ auditRef: "A1", ingested: false }], PATROL({ ingest: [ing({ permanent })] }).report);
    expect(out[0].join?.mode).toBe(mode);
  });
  it("report 為 null 全部 null；輸入不被修改；snake_case 鍵視為無對應", () => {
    expect(joinHostRejections([{ auditRef: "A1", ingested: false }], null)[0].join).toBeNull();
    const frozen = Object.freeze({ ingest: Object.freeze([Object.freeze(ing({}))]) });
    expect(() => joinHostRejections(Object.freeze([Object.freeze({ auditRef: "A1", ingested: false })]), frozen)).not.toThrow();
    const snake = { ingest: [{ audit_ref: "A1", status: "rejected", permanent: true }] };
    expect(joinHostRejections([{ auditRef: "A1", ingested: false }], snake)[0].join).toBeNull();
  });
});

describe("AT_966_5_8 評估集、驗證、隔離試跑檢視模型", () => {
  it("評估集", () => {
    expect(heldoutView({ frozen: false })).toMatchObject({ state: "unfrozen" });
    expect(heldoutView({ frozen: true, n: 7, min: 5, belowMin: false, frozenBy: "甲" })).toMatchObject({ state: "frozen", text: "已凍結：7 筆案例（下限 5），凍結者：甲", warning: null });
    expect(heldoutView({ frozen: true, n: 5, min: 5, belowMin: false })).toMatchObject({ warning: null });
    expect(heldoutView({ frozen: true, n: 4, min: 5, belowMin: true, neNote: "案例數 4 低於下限 5，驗證結果只能是 NE" })).toMatchObject({ warning: "案例數 4 低於下限 5，驗證結果只能是 NE" });
    for (const neNote of [null, "", undefined]) expect(heldoutView({ frozen: true, n: 4, min: 5, belowMin: true, neNote })).toMatchObject({ warning: "案例數低於下限，驗證結果只能是『無法評估』" });
    expect(heldoutView({ frozen: true, n: null })).toMatchObject({ text: "已凍結，案例數量不明" });
    expect(heldoutView(null)).toMatchObject({ state: "unknown" });
    const leaked = JSON.stringify(heldoutView({ frozen: true, n: 7, min: 5, digest8: "CANARY08", cases: ["CANARY-CASE"], probes: "CANARY-PROBE", digest: "CANARY" }));
    expect(leaked).not.toMatch(/CANARY|digest|cases|probes/);
  });
  it("驗證", () => {
    const v = verifyView({ verdict: "PASS", baselineRed: true, patchedGreen: true, mutatedRed: null, probesN: 6, carrierProof: true, reasons: [] });
    expect(v).toMatchObject({ state: "present", verdict: { known: true, text: "通過" }, probes: "6", carrier: "通過" });
    if (v.state !== "present") throw new Error("unreachable");
    expect(v.steps.map((s) => s.value)).toEqual(["是", "是", "量不到"]);
    expect(v.reasons.state).toBe("none-kept");
    const f = verifyView({ verdict: "FAIL", patchedGreen: false, carrierProof: false });
    if (f.state !== "present") throw new Error("unreachable");
    expect(f.steps[1]).toMatchObject({ value: "否", failed: true });
    expect(f.carrier).toBe("沒通過");
    expect(f.reasons.state).toBe("missing");
    const w = verifyView({ verdict: "WEIRD", carrierProof: null });
    if (w.state !== "present") throw new Error("unreachable");
    expect(w.verdict).toEqual({ known: false, text: "未知結果『WEIRD』" });
    expect(w.carrier).toBe("量不到");
    expect(verifyView(null).state).toBe("none");
  });
  it("隔離試跑", () => {
    expect(sandboxView({ applied: true, touchedOk: true, rollbackOk: true })).toMatchObject({ state: "ok" });
    expect(sandboxView({ applied: false, failCode: "SANDBOX-NOT-APPLIED", failText: "修補套不上去，請退回或修訂提案" })).toMatchObject({
      state: "fail",
      text: "修補套不上去，請退回或修訂提案",
      detail: "修補套不上去，請退回或修訂提案",
    });
    for (const failText of [null, "", undefined])
      expect(sandboxView({ applied: false, failCode: "SANDBOX-NOT-APPLIED", failText })).toMatchObject({ text: "隔離試跑沒有通過：SANDBOX-NOT-APPLIED（主機沒有提供白話說明）", detail: null });
    expect(sandboxView(null)).toMatchObject({ state: "none" });
  });
});

describe("AT_966_5_9 推送、排程、等待檢視模型與相對時間", () => {
  const p = (state: string, code: string, text: string, extra: Record<string, unknown> = {}) => ({ enabled: true, state, code, text, retry: null, ...extra });
  it("推送八態與新碼走同一條路徑", () => {
    const cases: Array<[Record<string, unknown>, string, string]> = [
      [p("off", "PUSH-OFF", "自動推送已關閉"), "neutral", "自動推送已關閉"],
      [p("idle", "PUSH-NOT-AHEAD", "沒有待推送的提交"), "neutral", "沒有待推送的提交"],
      [p("pending", "PUSH-PENDING", "等推送任務下一次執行（每個心跳一次）"), "neutral", "等推送任務下一次執行（每個心跳一次）"],
      [p("waiting-login", "PUSH-WAITING-LOGIN", "等使用者登入後自動推送"), "neutral", "等使用者登入後自動推送"],
      [p("running", "PUSH-RUNNING", "正在推送"), "neutral", "正在推送"],
      [p("ok", "PUSH-OK", "已推送", { sha: "abcdef0123456789", finishedAt: NOW }), "ok", "已推送"],
      [p("failed", "PUSH-FAILED", "推送失敗，稍後自動重試", { retry: "wait", attempts: 2 }), "warn", "推送失敗，稍後自動重試"],
      [p("blocked", "PUSH-DIRTY-TREE", "工作樹有未提交的修改"), "warn", "工作樹有未提交的修改"],
      [p("blocked", "PUSH-FOREIGN-COMMITS", "有別人的提交 abcdef01"), "warn", "有別人的提交 abcdef01"],
      [p("blocked", "PUSH-NOT-RECORDED", "這次提交還沒記進帳本，請由人推送"), "warn", "這次提交還沒記進帳本，請由人推送"],
      [p("blocked", "PUSH-RECORD-MISMATCH", "帳本記的提交與實際不符，請由人推送"), "warn", "帳本記的提交與實際不符，請由人推送"],
      [p("blocked", "PUSH-LEDGER-RULE", "帳本規則不允許自動推送，請由人推送"), "warn", "帳本規則不允許自動推送，請由人推送"],
    ];
    for (const [push, tone, text] of cases) {
      const v = pushView(push);
      expect(v, String(push.code)).toMatchObject({ known: true, tone, text });
    }
    expect(pushView(cases[5][0])).toMatchObject({ extras: ["（提交 abcdef01）"], time: NOW });
    expect(pushView(cases[6][0]).extras).toEqual(["已嘗試 2 次"]);
  });
  it("缺文字、未知態、null、憑證遮罩", () => {
    expect(pushView(p("blocked", "PUSH-X", ""))).toMatchObject({ text: "主機沒有提供白話說明（原因碼 PUSH-X）。" });
    expect(pushView({ enabled: true, state: "idle", code: "PUSH-X" }).text).toBe("主機沒有提供白話說明（原因碼 PUSH-X）。");
    const skipped = pushView({ state: "skipped", text: "略過" });
    expect(skipped).toMatchObject({ known: false, tone: "neutral" });
    expect(skipped.text).toContain("未知的推送狀態『skipped』");
    expect(skipped.text).toContain("略過");
    expect(pushView({ state: "zzz" }).text).toBe("未知的推送狀態『zzz』 主機沒有提供原因。".replace(" 主機沒有提供原因。", ""));
    expect(pushView(null).text).toBe("自動推送狀態量不到");
    const dirty = "https://" + "user" + ":" + "token123" + "@github.com/o/r.git";
    expect(pushView(p("failed", "PUSH-FAILED", `push ${dirty} failed`)).text).toBe("push https://***@github.com/o/r.git failed");
  });
  it("排程", () => {
    expect(scheduleView(null, true)).toEqual({ state: "paused", message: "巡邏已暫停，沒有排程資訊" });
    expect(scheduleView(null, false)).toEqual({ state: "absent", message: "這份回報沒有排程資訊" });
    expect(scheduleView(null, undefined)).toEqual({ state: "absent", message: "這份回報沒有排程資訊" });
    const off = scheduleView({ enabled: false, current: { code: "SCHED-DISABLED", text: "自動演化排程目前停用" }, lastSkip: null }, false);
    expect(off).toMatchObject({ state: "present", enabledText: "排程：已停用", current: { text: "自動演化排程目前停用" }, lastSkip: null });
    expect(scheduleView({ enabled: true, current: null, lastSkip: null }, false)).toMatchObject({ current: { text: "目前這一格的排程狀態量不到" } });
    const skip = { seq: 99, t: "2026-11-11T13:45:00+08:00", code: "SKIP-RUN-OPEN", text: "已有未關運轉", auditRef: null };
    const a = scheduleView({ enabled: true, current: { code: "C", text: "現況" }, lastSkip: skip }, false);
    if (a.state !== "present") throw new Error("unreachable");
    expect(a.lastSkip).toEqual({ line: "最近一次略過：2026-11-11T13:45:00+08:00 已有未關運轉", code: "SKIP-RUN-OPEN", note: null });
    const b = scheduleView({ enabled: true, current: { code: "C", text: "現況" }, lastSkip: { ...skip, auditRef: "a1000000-0000-4000-8000-000000000001" } }, false);
    if (b.state !== "present") throw new Error("unreachable");
    expect(b.lastSkip?.note).toBe("這次略過的是你從畫面按的『立即啟動』（稽核編號 a1000000-0000-4000-8000-000000000001）");
  });
  it("等待", () => {
    expect(waitingView([{ run: "RUN-SI-902", code: "SKIP-OTHER-DRIVER", text: "近期有人在互動視窗工作" }])).toMatchObject({
      state: "items",
      items: [{ text: "RUN-SI-902 等待中：近期有人在互動視窗工作" }],
    });
    expect(waitingView([])).toEqual({ state: "empty", text: "目前沒有在等待啟動的運轉" });
    expect(waitingView(undefined)).toEqual({ state: "unknown", text: "等待中的運轉量不到" });
  });
  it.each([
    [0, "剛剛"],
    [0.5, "剛剛"],
    [1, "1 分鐘前"],
    [59, "59 分鐘前"],
    [61, "1 小時 1 分鐘前"],
    [125, "2 小時 5 分鐘前"],
    [1500, "1 天 1 小時前"],
    [-1, "時間量不到"],
    [Number.NaN, "時間量不到"],
  ])("相對時間 %s", (m, text) => {
    expect(relativeMinutesText(m)).toBe(text);
  });
});

describe("AT_966_5_E_1 缺席、null、空陣列三者區分", () => {
  it("只有真的空陣列才是 empty", () => {
    for (const v of [undefined, null, "字串", 0, {}, true]) expect(sectionState(v), String(v)).toBe("unknown");
    expect(sectionState([])).toBe("empty");
    expect(sectionState([1])).toBe("items");
    const runs = PATROL({ runs: { queued: [] } }).report.runs as Record<string, unknown>;
    expect(sectionState(runs.live)).toBe("unknown");
    expect(sectionState(runs.queued)).toBe("empty");
    expect(pushView(PATROL({ push: DROP }).report.push).text).toBe("自動推送狀態量不到");
    expect(pushView({}).text).toContain("未知的推送狀態");
  });
});

describe("黃金樣本轉換（camelKeys 自檢；樣本檔由根層實作產生）", () => {
  it("camelKeys 規則", () => {
    expect(camelKeys({ audit_ref: 1, read_at: 2, runs: { wall_due_at: 3 }, list: [{ a_b: 1 }], keep: 4, "x-y": 5 })).toEqual({
      auditRef: 1,
      readAt: 2,
      runs: { wallDueAt: 3 },
      list: [{ aB: 1 }],
      keep: 4,
      "x-y": 5,
    });
    expect(keyPaths(camelKeys({ a_b: [{ c_d: 1 }] }))).toEqual([".aB", ".aB[].cD"]);
  });
});

describe("AT_966_15_2 新字串可讀性鎖與禁用技術詞", () => {
  const FORBIDDEN = ["Bridge", "carrierProof", "probe", "sandbox", "digest", "schema", "payload", "HMAC"];
  const values = (): string[] => Object.values(SI_FLOW_TEXTS).flatMap((v) => (Array.isArray(v) ? [...v] : [v as string]));
  const filled = (s: string) =>
    fillText(s, {
      code: "X-1",
      value: "Z",
      who: "掌舵者",
      text: "文字",
      count: 3,
      add: 2,
      del: 1,
      rel: "docs/a.patch",
      bytes: 10,
      id: "OBS-SI-050",
      n: 3,
      min: 5,
      by: "甲",
      label: "通過",
      ago: "3 分鐘前",
      time: "14:00",
      limit: 35,
      period: 15,
      run: "RUN-SI-901",
      purpose: "排程啟動",
      started: "3 分鐘前",
      due: "5 分鐘",
      ref: "A1",
      sha: "abcdef01",
      shown: 5,
      why: "原因",
    });
  it("每個值非空字串，代入後逐句過可讀性規則", () => {
    const vs = values();
    expect(vs.length).toBeGreaterThan(100);
    for (const v of vs) {
      expect(typeof v).toBe("string");
      expect(v.trim()).not.toBe("");
      const s = filled(v);
      expect(s, v).not.toMatch(/null|undefined|NaN|object/i);
      expect(longSentences(s), v).toEqual([]);
      expect(bannedFindings(s), v).toEqual([]);
      for (const bad of FORBIDDEN) expect(s.toLowerCase(), `${v} 含 ${bad}`).not.toContain(bad.toLowerCase());
      expect(s, v).not.toMatch(/\{\w+\}/);
    }
  });
  it("沙盒與探針只准以括號形態出現", () => {
    for (const v of values()) {
      for (const word of ["沙盒", "探針"]) {
        const i = v.indexOf(word);
        if (i >= 0) expect(v.slice(Math.max(0, i - 1), i + word.length + 1), v).toMatch(/[（(].*[）)]/);
      }
    }
  });
});
