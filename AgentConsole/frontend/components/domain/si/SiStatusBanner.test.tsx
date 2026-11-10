import { screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SI_STATUS_KNOWN_KEYS, backtestStatusText, researchSourcesStatusText } from "@/lib/domain/si";
import { ADMIN_UI, fixtureWithStatus, renderSi, statusItem } from "@/tests/helpers/si";

/**
 * 狀態橫幅的研究來源與反事實回測欄位（TCS-ResearchRegistry-20261110 AT-965-9-5；W-R9、D-EQA-5；仿 AT_964_1_3）。
 * 欄名是 backend snake_case→camelCase 對映後的鍵（`research_fetch_max`→`researchFetchMax`；巢狀鍵同樣轉換）。
 * 判定指令：npx vitest run components/domain/si/SiStatusBanner.test.tsx -t AT_965_9_5
 */
vi.mock("next/navigation", () => ({
  usePathname: () => "/self-improving",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const SHA = `sha256:0123456789ab${"c".repeat(52)}`;
const REGISTRY = { seq: 412, auditRef: "11111111-1111-4111-8111-111111111111", registrySha256: SHA, watchEnabled: 10 };
const BACKTEST = {
  casesVersion: 3,
  casesSha256: SHA,
  n: 24,
  hit1: 9,
  hit3: 17,
  hit5: 20,
  precPm: 0.71,
  recPm: 0.65,
  contaminated: 2,
  hit5Trend: [18, 19, 20],
};
const FETCH_MAX = 10;

async function banner(extra: Record<string, unknown>) {
  renderSi({ ...ADMIN_UI, fixture: fixtureWithStatus(statusItem({ extra })) });
  const el = await screen.findByTestId("si-status-banner");
  await within(el).findByTestId("si-research-sources");
  return el;
}
const sources = (el: HTMLElement) => within(el).getByTestId("si-research-sources").textContent;
const backtest = (el: HTMLElement) => within(el).getByTestId("si-backtest").textContent;

describe("AT_965_9_5 SI_STATUS_KNOWN_KEYS 含三鍵：不落入「其他欄位」，並有具名欄位", () => {
  it("AT_965_9_5 已知鍵含 researchFetchMax、researchRegistry、backtest，既有十鍵一個不少", () => {
    expect([...SI_STATUS_KNOWN_KEYS]).toEqual(
      expect.arrayContaining([
        "eventsDetected",
        "unavailable",
        "openRuns",
        "pendingProps",
        "suspended",
        "cooldowns",
        "skipReasons",
        "capacity",
        "frictionReconcile",
        "schedule",
        "researchFetchMax",
        "researchRegistry",
        "backtest",
      ]),
    );
  });

  it("AT_965_9_5 組一：三鍵齊全 ⇒ 兩個具名欄位逐字；三鍵不出現在「其他欄位」；純文字節點", async () => {
    const el = await banner({ researchFetchMax: FETCH_MAX, researchRegistry: REGISTRY, backtest: BACKTEST, futureKey: { a: 1 } });
    expect(sources(el)).toBe("研究來源：啟用 10／上限 10；最近同步 seq 412（0123456789ab）");
    expect(backtest(el)).toBe("反事實回測：案例集 v3（0123456789ab）；hit@3＝17／24 案、污染 2");
    const extra = within(el).getByTestId("si-status-extra");
    expect(extra.textContent).toContain("futureKey");
    for (const key of ["researchFetchMax", "researchRegistry", "backtest"]) {
      expect(extra.textContent, `${key} 不在其他欄位`).not.toContain(`${key}：`);
      expect(el.querySelector(`[data-status-key="${key === "researchFetchMax" ? "researchRegistry" : key}"]`), `${key} 有具名欄位`).not.toBeNull();
    }
    expect(within(el).getByTestId("si-research-sources").children).toHaveLength(0);
    expect(within(el).getByTestId("si-backtest").children).toHaveLength(0);
  });

  it("AT_965_9_5 組二：researchRegistry 為 null ⇒ 「尚無」（不是 0、不是空白）；上限仍顯示鏡像值", async () => {
    const el = await banner({ researchFetchMax: FETCH_MAX, researchRegistry: null, backtest: BACKTEST });
    expect(sources(el)).toBe("研究來源：啟用 尚無／上限 10；最近同步 尚無");
    expect(sources(el)).not.toMatch(/啟用 0|量不到/);
    expect(backtest(el)).toContain("案例集 v3");
  });

  it("AT_965_9_5 組三：backtest 為 null ⇒ 「尚無」", async () => {
    const el = await banner({ researchFetchMax: FETCH_MAX, researchRegistry: REGISTRY, backtest: null });
    expect(backtest(el)).toBe("反事實回測：尚無");
    expect(sources(el)).toContain("seq 412");
  });

  it("AT_965_9_5 組四：researchFetchMax 缺鍵 ⇒ 上限「量不到」（不是「尚無」、不是 0）", async () => {
    const el = await banner({ researchRegistry: REGISTRY, backtest: BACKTEST });
    expect(sources(el)).toBe("研究來源：啟用 10／上限 量不到；最近同步 seq 412（0123456789ab）");
    expect(sources(el)).not.toMatch(/上限 (尚無|0)/);
  });

  it("AT_965_9_5 組五：三鍵全 null／缺 ⇒ null 者「尚無」、缺者「量不到」", async () => {
    const allNull = await banner({ researchFetchMax: null, researchRegistry: null, backtest: null });
    expect(sources(allNull)).toBe("研究來源：啟用 尚無／上限 尚無；最近同步 尚無");
    expect(backtest(allNull)).toBe("反事實回測：尚無");
  });

  it("AT_965_9_5 組五（缺鍵）：三鍵皆缺 ⇒ 全部「量不到」，橫幅其餘欄位不受影響", async () => {
    const el = await banner({});
    expect(sources(el)).toBe("研究來源：啟用 量不到／上限 量不到；最近同步 量不到");
    expect(backtest(el)).toBe("反事實回測：量不到");
    expect(el.querySelector('[data-status-key="eventsDetected"]')).not.toBeNull();
  });

  it("AT_965_9_5 組六：backtest 欄位型別不符（hit3 為字串）⇒ 「量不到」，不顯示成 0 或「尚無」", async () => {
    const el = await banner({ researchFetchMax: FETCH_MAX, researchRegistry: REGISTRY, backtest: { ...BACKTEST, hit3: "17" } });
    expect(backtest(el)).toBe("反事實回測：量不到");
  });

  it("AT_965_9_5 型別不符的其他組合：上限為字串 ⇒ 「量不到」；registry 缺 registrySha256 ⇒ 最近同步「量不到」；上限為 0 或負 ⇒ 「量不到」", () => {
    expect(researchSourcesStatusText({ researchFetchMax: "10", researchRegistry: REGISTRY })).toContain("上限 量不到");
    expect(researchSourcesStatusText({ researchFetchMax: 0, researchRegistry: REGISTRY })).toContain("上限 量不到");
    expect(researchSourcesStatusText({ researchFetchMax: -1, researchRegistry: REGISTRY })).toContain("上限 量不到");
    expect(researchSourcesStatusText({ researchFetchMax: 10, researchRegistry: { seq: 1, watchEnabled: 2 } })).toBe("研究來源：啟用 2／上限 10；最近同步 量不到");
    expect(backtestStatusText({ backtest: { ...BACKTEST, casesSha256: 5 } })).toBe("反事實回測：量不到");
    expect(backtestStatusText({ backtest: [] })).toBe("反事實回測：量不到");
  });

  it("AT_965_9_5 與研究來源設定的同步狀態文案互不混用：本欄位不出現「已同步」「有變更尚未同步」", async () => {
    const el = await banner({ researchFetchMax: FETCH_MAX, researchRegistry: REGISTRY, backtest: BACKTEST });
    const text = `${sources(el)}${backtest(el)}`;
    expect(text).not.toMatch(/已同步|尚未同步|待入帳/);
  });
});
