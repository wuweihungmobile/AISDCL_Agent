import { describe, expect, it } from "vitest";

import { REASONS } from "@/lib/api/reasons";
import type { ConfigHistory } from "@/lib/api/types";
import { FIXTURE, MASKED } from "@/tests/helpers/settingsFixtures";
import { MASK, baselineOf, buildSavePlan, configId, formatHistoryLine, isDirty, isTokenGuardKey, pendingChanges, sensitiveChanges, validateTokenGuard, validateValue, valueOf } from "./settingsModel";

describe("遮罩與基準值", () => {
  it("遮罩字串是 U+2022 共八個（契約 §1.5 通則）", () => {
    expect(MASK).toBe("••••••••");
    expect(MASK).toBe(MASKED);
    expect([...MASK]).toHaveLength(8);
  });

  it("加密參數：有值＝遮罩、沒值＝空字串；揭露後以明文為基準；一般參數就是 value", () => {
    expect(baselineOf(FIXTURE.apiKey(true))).toBe(MASK);
    expect(baselineOf(FIXTURE.apiKey(false))).toBe("");
    expect(baselineOf(FIXTURE.apiKey(true), "sk-plain")).toBe("sk-plain");
    expect(baselineOf(FIXTURE.temperature())).toBe("0.3");
  });

  it("草稿：沒改的鍵讀伺服器值；改過且不同才算髒；改回原值就不髒", () => {
    const t = FIXTURE.temperature();
    const id = configId(t);
    expect(valueOf(t, {}, {})).toBe("0.3");
    expect(valueOf(t, { [id]: "0.5" }, {})).toBe("0.5");
    expect(isDirty(t, {}, {})).toBe(false);
    expect(isDirty(t, { [id]: "0.5" }, {})).toBe(true);
    expect(isDirty(t, { [id]: "0.3" }, {})).toBe(false);
    // 伺服器值更新後（例如儲存成功重抓），舊草稿與新基準相同就自動不髒
    expect(isDirty({ ...t, value: "0.5" }, { [id]: "0.5" }, {})).toBe(false);
  });

  it("加密參數：把遮罩改成空字串＝清除（髒）；沒動遮罩不髒", () => {
    const k = FIXTURE.apiKey(true);
    expect(isDirty(k, { [configId(k)]: MASK }, {})).toBe(false);
    expect(isDirty(k, { [configId(k)]: "" }, {})).toBe(true);
    expect(isDirty(k, { [configId(k)]: "sk-new" }, {})).toBe(true);
  });
});

describe("七種 valueType 的前端驗證（鏡射契約 §1.5 通則；範圍與選項取自 ConfigResponse）", () => {
  it("INTEGER：整數且在 min～max；訊息與後端同風格", () => {
    const c = FIXTURE.defaultAutonomyLevel();
    expect(validateValue(c, "5")).toBeNull();
    expect(validateValue(c, "1")).toBeNull();
    expect(validateValue(c, "10")).toBeNull();
    for (const bad of ["0", "11", "abc", "1.5", "", "-3", "007"]) expect(validateValue(c, bad), bad).toBe("需為整數（1～10）");
  });

  it("LONG：同整數規則，大範圍；FLOAT：小數與範圍", () => {
    const l = FIXTURE.globalTokenBudget();
    expect(validateValue(l, "1000000000000")).toBeNull();
    expect(validateValue(l, "1000000000001")).toBe("需為整數（1～1000000000000）");
    const f = FIXTURE.temperature();
    expect(validateValue(f, "0.3")).toBeNull();
    expect(validateValue(f, "2")).toBeNull();
    expect(validateValue(f, "2.1")).toBe("需為數字（0～2）");
    expect(validateValue(f, "x")).toBe("需為數字（0～2）");
    expect(validateValue(f, "-0.1")).toBe("需為數字（0～2）");
  });

  it("monitor.refreshIntervalMs 最小 10000（輪詢地板）：9999 擋下、10000 通過", () => {
    const c = FIXTURE.refreshIntervalMs();
    expect(validateValue(c, "9999")).toBe("需為整數（10000～60000）");
    expect(validateValue(c, "10000")).toBeNull();
    expect(validateValue(c, "60001")).toBe("需為整數（10000～60000）");
  });

  it("BOOLEAN 只收小寫 true／false；ENUM 只收選項之一（區分大小寫）", () => {
    const b = FIXTURE.enableKernelBrain();
    expect(validateValue(b, "true")).toBeNull();
    expect(validateValue(b, "false")).toBeNull();
    expect(validateValue(b, "True")).toBe("需為 true 或 false");
    const e = FIXTURE.dagSchedulerStrategy();
    expect(validateValue(e, "PRIORITY")).toBeNull();
    expect(validateValue(e, "priority")).toBe("需為下列之一：TOPOLOGICAL、PRIORITY、SHORTEST_FIRST");
  });

  it("STRING：套用 validationRule；空字串在允許空值的規則下通過（通知信箱）", () => {
    const url = FIXTURE.apiUrl();
    expect(validateValue(url, "https://api.minimax.io/v1/text/chatcompletion_v2")).toBeNull();
    expect(validateValue(url, "ftp://x")).toBe("格式不符合規則");
    expect(validateValue(url, "https://a b")).toBe("格式不符合規則");
    const mail = FIXTURE.notificationEmail();
    expect(validateValue(mail, "")).toBeNull();
    expect(validateValue(mail, "ops@example.com")).toBeNull();
    expect(validateValue(mail, "not-an-email")).toBe("格式不符合規則");
    expect(validateValue(FIXTURE.name(), "a".repeat(4001))).toBe("最多 4,000 個字元");
  });

  it("ENCRYPTED：≤512 字元；空字串（清除）通過", () => {
    const k = FIXTURE.apiKey();
    expect(validateValue(k, "")).toBeNull();
    expect(validateValue(k, "sk-new")).toBeNull();
    expect(validateValue(k, "x".repeat(513))).toBe("最多 512 個字元");
  });

  it("後端日後加了前端不認得的規則語法：放行交給後端，不誤擋", () => {
    const odd = { ...FIXTURE.name(), validationRule: "(?<n>[" };
    expect(validateValue(odd, "anything")).toBeNull();
  });
});

describe("Token Guard 跨鍵規則（NFR-SEC-05 第 ③ 道）", () => {
  it("halt 必須大於 compact：相等與反向都回契約逐字 reason", () => {
    expect(validateTokenGuard("70", "95")).toBeNull();
    expect(validateTokenGuard("80", "81")).toBeNull();
    expect(validateTokenGuard("90", "80")).toBe(REASONS.SETTINGS_TOKEN_GUARD_ORDER);
    expect(validateTokenGuard("80", "80")).toBe("halt_threshold_pct 必須大於 compact_threshold_pct");
  });

  it("範圍：compact 1～99、halt 2～100、皆整數", () => {
    expect(validateTokenGuard("0", "50")).toBe("壓縮門檻需為 1～99 的整數");
    expect(validateTokenGuard("100", "100")).toBe("壓縮門檻需為 1～99 的整數");
    expect(validateTokenGuard("abc", "90")).toBe("壓縮門檻需為 1～99 的整數");
    expect(validateTokenGuard("50", "1")).toBe("停機門檻需為 2～100 的整數");
    expect(validateTokenGuard("50", "101")).toBe("停機門檻需為 2～100 的整數");
    expect(validateTokenGuard("1", "2")).toBeNull();
    expect(validateTokenGuard("99", "100")).toBeNull();
  });

  it("isTokenGuardKey：只認 execution 的兩個門檻鍵（別的分類同名鍵不算）", () => {
    expect(isTokenGuardKey(FIXTURE.compactThresholdPct())).toBe(true);
    expect(isTokenGuardKey(FIXTURE.haltThresholdPct())).toBe(true);
    expect(isTokenGuardKey(FIXTURE.globalTokenBudget())).toBe(false);
    expect(isTokenGuardKey({ category: "model", key: "compactThresholdPct" })).toBe(false);
  });
});

describe("儲存計畫", () => {
  const configs = [FIXTURE.temperature(), FIXTURE.apiKey(), FIXTURE.compactThresholdPct(), FIXTURE.haltThresholdPct(), FIXTURE.globalTokenBudget()];
  const id = (i: number) => configId(configs[i]);

  it("只挑改過的鍵，順序依傳入順序", () => {
    const changes = pendingChanges(configs, { [id(4)]: "2000000", [id(0)]: "0.5", [id(1)]: MASK }, {});
    expect(changes.map((c) => c.id)).toEqual(["model.temperature", "execution.globalTokenBudget"]);
    expect(changes.map((c) => c.value)).toEqual(["0.5", "2000000"]);
  });

  it("兩個 token_guard 鍵都改：合成一次原子操作（放在第一個出現的位置）；其餘照舊逐鍵", () => {
    const changes = pendingChanges(configs, { [id(0)]: "0.5", [id(2)]: "70", [id(3)]: "95", [id(4)]: "5" }, {});
    const plan = buildSavePlan(changes, { compact: "70", halt: "95" });
    expect(plan.map((p) => p.kind)).toEqual(["single", "tokenGuard", "single"]);
    const guard = plan[1];
    expect(guard.kind === "tokenGuard" && [guard.compact, guard.halt, guard.ids]).toEqual(["70", "95", ["execution.compactThresholdPct", "execution.haltThresholdPct"]]);
  });

  it("只改了 token_guard 其中一鍵：一樣走群組端點，對端帶畫面上的目前值（PRD §7.1.8：群組鍵改走群組端點）", () => {
    const plan = buildSavePlan(pendingChanges(configs, { [id(3)]: "95" }, {}), { compact: "80", halt: "95" });
    expect(plan).toHaveLength(1);
    expect(plan[0]).toEqual({ kind: "tokenGuard", compact: "80", halt: "95", ids: ["execution.haltThresholdPct"] });
  });

  it("參數尚未載入（拿不到門檻目前值）：退回單鍵 PUT，由後端讀對端現值校驗", () => {
    const plan = buildSavePlan(pendingChanges(configs, { [id(3)]: "95" }, {}), null);
    expect(plan.map((p) => p.kind)).toEqual(["single"]);
  });

  it("敏感參數（加密儲存者）要二次確認", () => {
    const changes = pendingChanges(configs, { [id(0)]: "0.5", [id(1)]: "sk-new" }, {});
    expect(sensitiveChanges(changes).map((c) => c.id)).toEqual(["model.apiKey"]);
    expect(sensitiveChanges(pendingChanges(configs, { [id(0)]: "0.5" }, {}))).toEqual([]);
  });
});

describe("修改歷史格式（US-S-07）", () => {
  const h = (over: Partial<ConfigHistory> = {}): ConfigHistory => ({
    id: "h1",
    configId: "c1",
    category: "model",
    key: "temperature",
    oldValue: "0.5",
    newValue: "0.3",
    changedAt: "2026-10-15T15:30:00",
    changedBy: "admin",
    ...over,
  });

  it("時間／參數／舊值 → 新值／@使用者", () => {
    expect(formatHistoryLine(h())).toEqual({ time: "2026-10-15 15:30", param: "model.temperature", change: "0.5 → 0.3", by: "@admin" });
  });

  it("沒有舊值或使用者時有可讀的替代字；加密值是後端回的遮罩，原樣顯示", () => {
    expect(formatHistoryLine(h({ oldValue: undefined, changedBy: undefined }))).toMatchObject({ change: "（無） → 0.3", by: "@系統" });
    expect(formatHistoryLine(h({ key: "apiKey", oldValue: MASK, newValue: MASK })).change).toBe(`${MASK} → ${MASK}`);
  });
});
