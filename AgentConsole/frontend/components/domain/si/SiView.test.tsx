/**
 * SiView 的元件測試（TCS-SelfImprovingMirror-P1b：AT-932-1-5／1-6／1-8／1-E-5／1-E-6／1-E-7、2-6、3-6／3-7／3-E-4／3-E-5／3-E-6）。
 * 資料來自 tests/helpers/si.tsx 的 fetch 替身（回放狀態 A／B 的黃金檔，since／limit 語意同 CLI），畫面的 DOM 契約（data-testid）：
 *   橫幅 si-status-banner（si-head-sha、si-generated-at、si-events-detected／si-no-event、si-unavailable、si-open-runs、si-pending-props、
 *   si-suspended、si-cooldowns、si-skip-reasons、si-capacity、si-friction、si-status-extra；每個 status 鍵都有 data-status-key 的呈現）；
 *   面板 si-panel-<observations|proposals|events>（觀察 si-obs-row-<ID>／si-obs-fields-<ID>／si-obs-invalid-<line>、提案 si-prop-row-<ID>／si-card-<ID>、
 *   運轉 si-runs-table、事件 si-events-table／si-event-json-<seq>）；錯誤態 si-error（si-error-summary／reason／detail／cause、si-retry）；
 *   載入中 si-loading（role=status）；篩選為 aria-label 即欄名的原生 select；si-refresh 為頁首的重新整理。
 */
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Providers } from "@/components/providers/Providers";
import { ApiError } from "@/lib/api/client";
import { SI_QUERY_OPTIONS } from "@/lib/api/queries";
import type { SiConsoleWrites, SiEvent, SiObservation, SiObservationRow, SiProposal } from "@/lib/api/types";
import { SI_STATUS_KNOWN_KEYS, ingestCommands } from "@/lib/domain/si";
import { GA, GB, clone, fixtureWithStatus, renderSi, sched, signInAs, siUnavailable, statusItem, stubSiApi, writeItem, type SiStub } from "@/tests/helpers/si";
import { SiView } from "./SiView";
import { SiError } from "./siParts";

// SI_PAGE_LIMIT 可由測試局部覆寫（AT_932_1_8 以 5 切頁）；其餘測試維持正式值，以 getter 在每次讀取時回傳
const limits = vi.hoisted(() => ({ value: 100 }));
vi.mock("@/lib/domain/si", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/domain/si")>();
  return {
    ...mod,
    get SI_PAGE_LIMIT() {
      return limits.value;
    },
  };
});
// 測試環境沒有 App Router：AuthProvider 要的 useRouter 換成穩定的替身（SiView 本身不導覽）
const router = vi.hoisted(() => ({ push: () => undefined, replace: () => undefined, back: () => undefined }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/self-improving",
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));
afterEach(() => {
  limits.value = 100;
  delete (window as unknown as Record<string, unknown>).__si_xss;
});

// ── 小工具 ────────────────────────────────────────────────────────────────

const isValid = (r: SiObservationRow): r is SiObservation => r.valid !== false;
const GOLDEN_OBS = GA.observations.items.filter(isValid);
const BAD = GA.observations.items.find((r) => !isValid(r));

/** 面板內依文件順序列出的觀察列（有效列與壞列）的 data-testid。 */
function obsOrder(root: HTMLElement): string[] {
  return Array.from(root.querySelectorAll<HTMLElement>('[data-testid^="si-obs-row-"],[data-testid^="si-obs-invalid-"]')).map((el) => el.dataset.testid as string);
}
const validRowIds = (root: HTMLElement) =>
  obsOrder(root)
    .filter((t) => t.startsWith("si-obs-row-"))
    .map((t) => t.replace("si-obs-row-", ""));
const panel = (tab: "observations" | "proposals" | "events") => screen.getByTestId(`si-panel-${tab}`);
const tabButton = (name: RegExp | string) => screen.getByRole("tab", { name });
const textOf = (el: HTMLElement) => el.textContent ?? "";

async function waitForObservations() {
  return screen.findByTestId("si-obs-table");
}

/** 所有 button 的可及名稱（aria-label 優先，否則文字）。 */
function buttonNames(root: HTMLElement = document.body): string[] {
  return within(root)
    .queryAllByRole("button")
    .map((b) => b.getAttribute("aria-label") ?? b.textContent ?? "");
}

/** 取代某端點的資料：回傳 { data }，等同後端 200 封包。 */
const serve = (data: unknown) => () => ({ data });

/** 三條帶特殊字元的卡面（全形標點、半形與全形 box 字元、縮排、連續空行、結尾換行）。 */
const VERIFIED_CARD =
  "[PROP-SI-005] 設定｜modify｜目標：config/x.json｜digest：ab12cd34｜驗證：通過\n\n  一、症狀：全形標點，。！？「」（）『』\n┌──────┬──────┐\n│ 欄一 │ 欄二 │\n├──────┼──────┤\n│ ─ ━ │ ｜＋－ │\n└──────┴──────┘\n+------+------+\n| a    | b    |\n\n\n    縮排四格　全形空白　行尾空白  \n決定：核准 ／ 否決＋一句理由\n";
const REJECTED_CARD = "[PROP-SI-006] 已否決的提案\n第二行\n";

function proposalOf(patch: Partial<SiProposal>): SiProposal {
  return { ...clone(GA.proposals.items[0]), ...patch };
}

describe("AT_932_1_5 頁面逐欄顯示黃金檔資料（R12～R14）", () => {
  it("AT_932_1_5 橫幅、觀察九欄、壞列、運轉與事件的文字逐欄等於 camelCase 黃金檔，且請求網址集合恰為所需", async () => {
    const user = userEvent.setup();
    const { urls } = renderSi();
    const L = limits.value;

    // 橫幅
    const banner = await screen.findByTestId("si-status-banner");
    await within(banner).findByTestId("si-head-sha");
    const status = GA.status.items[0];
    expect(within(banner).getByTestId("si-head-sha")).toHaveTextContent((GA.status.headSha as string).slice(0, 8));
    expect(within(banner).getByTestId("si-head-sha")).toHaveAttribute("title", GA.status.headSha as string);
    expect(textOf(within(banner).getByTestId("si-generated-at"))).toBe(GA.status.generatedAt);
    const pending = within(banner).getByTestId("si-pending-props");
    expect(pending).toHaveTextContent("PROP-SI-004");
    expect(pending).toHaveTextContent(status.pendingProps[0].digest8);
    for (const u of status.unavailable) {
      expect(within(banner).getByTestId("si-unavailable")).toHaveTextContent(u.trigger);
      expect(within(banner).getByTestId("si-unavailable")).toHaveTextContent(u.reason);
    }
    const friction = status.frictionReconcile as { status: string; reason: string };
    expect(within(banner).getByTestId("si-friction")).toHaveTextContent("NOT-EVALUABLE");
    expect(within(banner).getByTestId("si-friction")).toHaveTextContent(friction.reason);
    // 橫幅頂層的每個鍵都至少有一個可見呈現（已知九鍵各有固定位置，其餘鍵列在 si-status-extra）
    for (const key of Object.keys(status)) {
      const place = banner.querySelector(`[data-status-key="${key}"]`);
      expect(place, `status 的鍵 ${key} 在橫幅沒有可見呈現`).not.toBeNull();
      expect(textOf(place as HTMLElement).trim().length, `status 的鍵 ${key} 的呈現是空的`).toBeGreaterThan(0);
    }
    expect(within(banner).getByTestId("si-status-extra")).toHaveTextContent("noEvent：true");

    // 觀察分頁：12 個項目（11 個有效列加 1 個壞列）
    await waitForObservations();
    const obs = panel("observations");
    expect(obsOrder(obs)).toHaveLength(12);
    expect(validRowIds(obs)).toEqual(GOLDEN_OBS.map((o) => o.id));
    expect(obs.querySelectorAll('[data-testid^="si-obs-invalid-"]')).toHaveLength(1);
    for (const o of GOLDEN_OBS) {
      await user.click(within(obs).getByRole("button", { name: `展開 ${o.id}` }));
      const fields = within(obs).getByTestId(`si-obs-fields-${o.id}`);
      for (const key of ["id", "time", "context", "symptom", "evidence", "category", "severity", "disposition", "marks"] as const) {
        // 精確字串比對，不做正規化
        expect(textOf(within(fields).getByTestId(`si-obs-field-${o.id}-${key}`)), `${o.id}.${key}`).toBe(o[key]);
      }
    }
    // 壞列：原文逐字顯示
    const bad = within(obs).getByTestId(`si-obs-invalid-${(BAD as { line: number }).line}`);
    expect(bad).toHaveTextContent(`無法解析的列（第 ${(BAD as { line: number }).line} 行）`);
    expect(textOf(bad.querySelector("pre") as HTMLElement)).toBe((BAD as { raw: string }).raw);
    // 該面板頂端列出黃金檔 problems 的每一項
    const problems = within(obs).getByTestId("si-problems-list");
    for (const p of GA.observations.problems) expect(problems).toHaveTextContent(`${p.subject} ${p.code} ${p.detail}`);

    // 事件分頁：運轉表與事件帳本
    await user.click(tabButton(/^事件/));
    const runsTable = await screen.findByTestId("si-runs-table");
    for (const r of GA.runs.items) {
      const row = within(runsTable).getByTestId(`si-run-row-${r.id}`);
      const cell = (field: string) => textOf(row.querySelector(`[data-field="${field}"]`) as HTMLElement);
      expect(cell("id")).toBe(r.id);
      expect(cell("trigger")).toBe(r.trigger);
      expect(cell("openedSeq")).toBe(String(r.openedSeq));
      expect(cell("closedSeq")).toBe(r.closedSeq === null ? "未結束" : String(r.closedSeq));
      expect(cell("outcome")).toBe(
        Object.entries(r.outcome)
          .map(([k, v]) => `${k}：${v}`)
          .join("；"),
      );
      expect(cell("propIds")).toBe(r.propIds.join("、"));
      expect(cell("research")).toBe(r.research ? `${r.research.kind} #${r.research.seq}` : "無");
    }
    const eventsTable = await screen.findByTestId("si-events-table");
    const eventRows = Array.from(eventsTable.querySelectorAll<HTMLElement>('[data-testid^="si-event-row-"]'));
    expect(eventRows).toHaveLength(6);
    GA.events.items.forEach((e, i) => {
      const cell = (field: string) => textOf(eventRows[i].querySelector(`[data-field="${field}"]`) as HTMLElement);
      expect([cell("seq"), cell("t"), cell("kind"), cell("by")]).toEqual([String(e.seq), e.t, e.kind, e.by]);
    });
    const e5 = GA.events.items.find((e) => e.seq === 5) as SiEvent;
    await user.click(within(eventsTable).getByRole("button", { name: "展開 事件 5" }));
    expect(textOf(screen.getByTestId("si-event-json-5"))).toBe(JSON.stringify(e5, null, 2));

    // 請求：status（無查詢參數）、observations、runs、events；沒打開的提案分頁不發請求
    expect([...urls()].sort()).toEqual([`/api/v1/si/events?limit=${L}`, `/api/v1/si/observations?limit=${L}`, `/api/v1/si/runs?limit=${L}`, "/api/v1/si/status"].sort());
  });
});

describe("AT_932_1_6 提案卡面逐位元組顯示（R14）", () => {
  it("AT_932_1_6 待決提案預設展開、卡面 textContent 逐位元組等於 card（含全形字元、box 字元、空行與結尾換行）；null 卡面顯示量不到並指向 ne 項", async () => {
    const user = userEvent.setup();
    const fixture = clone(GA);
    const nullCard = proposalOf({ id: "PROP-SI-099", state: "proposed", card: null });
    fixture.proposals.items = [
      GA.proposals.items[0],
      proposalOf({ id: "PROP-SI-005", state: "verified", card: VERIFIED_CARD }),
      proposalOf({ id: "PROP-SI-006", state: "rejected", card: REJECTED_CARD }),
      nullCard,
    ];
    fixture.proposals.ne = [{ field: "proposals.PROP-SI-099.card", reason: "git-unavailable" }];
    renderSi({ fixture });
    await user.click(await screen.findByRole("tab", { name: /^提案/ }));
    await screen.findByTestId("si-prop-table");

    // 兩個待決提案（proposed 與 verified）預設已展開；不經 trim，精確相等
    expect(textOf(screen.getByTestId("si-card-PROP-SI-004"))).toBe(GA.proposals.items[0].card);
    const verified = screen.getByTestId("si-card-PROP-SI-005");
    expect(textOf(verified)).toBe(VERIFIED_CARD);
    // 卡面區是 <pre>，內容為單一文字節點（無子元素、無 <br>、無 <code>、無前後綴）
    for (const pre of [screen.getByTestId("si-card-PROP-SI-004"), verified]) {
      expect(pre.tagName).toBe("PRE");
      expect(pre.childNodes).toHaveLength(1);
      expect(pre.firstChild?.nodeType).toBe(Node.TEXT_NODE);
      expect(pre.querySelector("*")).toBeNull();
    }
    // rejected 預設不展開；點擊後同樣逐位元組相等
    expect(screen.queryByTestId("si-card-PROP-SI-006")).toBeNull();
    const toggle = screen.getByRole("button", { name: "展開 PROP-SI-006" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(textOf(screen.getByTestId("si-card-PROP-SI-006"))).toBe(REJECTED_CARD);
    // null 卡面：顯示量不到並指向對應的 ne 項，不渲染空的卡面區
    expect(screen.queryByTestId("si-card-PROP-SI-099")).toBeNull();
    const row = screen.getByTestId("si-prop-row-PROP-SI-099");
    expect(row).toHaveTextContent("卡面量不到（NOT-EVALUABLE）");
    expect(row).toHaveTextContent("proposals.PROP-SI-099.card：git-unavailable");
  });
});

describe("AT_932_1_8 載入更多以 since 游標併頁（R15）", () => {
  it("AT_932_1_8 三頁合併不漏不重，按鈕於末頁消失；篩選範圍說明隨已載入筆數更新", async () => {
    limits.value = 5;
    const user = userEvent.setup();
    const { urls } = renderSi();
    await screen.findByRole("tab", { name: "觀察 (5+)" });
    expect(screen.getByTestId("si-filter-scope-note")).toHaveTextContent("篩選只作用於已載入的 5 筆，尚有更多未載入");
    expect(urls().filter((u) => u.includes("observations"))).toEqual(["/api/v1/si/observations?limit=5"]);

    await user.click(screen.getByRole("button", { name: "載入更多" }));
    await screen.findByRole("tab", { name: "觀察 (10+)" });
    expect(screen.getByTestId("si-filter-scope-note")).toHaveTextContent("篩選只作用於已載入的 10 筆，尚有更多未載入");

    await user.click(screen.getByRole("button", { name: "載入更多" }));
    await screen.findByRole("tab", { name: "觀察 (12)" }); // 壞列算一筆
    expect(screen.queryByRole("button", { name: "載入更多" })).toBeNull();
    expect(screen.queryByTestId("si-filter-scope-note")).toBeNull();
    // 三次請求：第一頁只有 limit；之後 since 取自上一頁回應的 nextSince
    expect(urls().filter((u) => u.includes("observations"))).toEqual(["/api/v1/si/observations?limit=5", "/api/v1/si/observations?since=5&limit=5", "/api/v1/si/observations?since=10&limit=5"]);
    // 最終 DOM 的列順序與黃金檔 12 筆完全相同（不漏、不重複）
    const expected = GA.observations.items.map((r) => (isValid(r) ? `si-obs-row-${r.id}` : `si-obs-invalid-${r.line}`));
    expect(obsOrder(panel("observations"))).toEqual(expected);
  });

  it("AT_932_1_8 第二頁重送一筆已出現的 ID（替身故障注入）：該筆只顯示一次且保留先到者的內容", async () => {
    limits.value = 5;
    const user = userEvent.setup();
    const dup: SiObservation = { ...clone(GOLDEN_OBS[1]), symptom: "重送的內容（不得覆寫先到者）" };
    const page2 = clone(GA.observations);
    page2.items = [dup, ...clone(GA.observations.items.slice(5, 10))];
    page2.truncated = true;
    page2.nextSince = 10;
    renderSi({ overrides: { observations: (call) => (call.query.get("since") === "5" ? { data: page2 } : undefined) } });
    await screen.findByRole("tab", { name: "觀察 (5+)" });
    await user.click(screen.getByRole("button", { name: "載入更多" }));
    // 去重後：第一頁 5 筆＋第二頁 6 筆（重送者 1 筆＋新的 5 筆）扣掉重複的 1 筆＝10 筆；第二頁仍標 truncated，所以帶「+」
    await screen.findByRole("tab", { name: "觀察 (10+)" });
    const obs = panel("observations");
    expect(validRowIds(obs).filter((id) => id === dup.id)).toHaveLength(1);
    await user.click(within(obs).getByRole("button", { name: `展開 ${dup.id}` }));
    expect(textOf(within(obs).getByTestId(`si-obs-field-${dup.id}-symptom`))).toBe(GOLDEN_OBS[1].symptom);
  });

  it("AT_932_1_8 回應標示 truncated 卻沒有 nextSince（契約被違反）：不假裝已載入全部，顯示缺少游標的警示", async () => {
    limits.value = 5;
    const page1 = clone(GA.observations);
    page1.items = page1.items.slice(0, 5);
    page1.truncated = true;
    page1.nextSince = null;
    renderSi({ overrides: { observations: serve(page1) } });
    await screen.findByRole("tab", { name: "觀察 (5+)" });
    expect(screen.getByTestId("si-cursor-missing")).toHaveTextContent("沒有下一頁的游標");
    expect(screen.queryByRole("button", { name: "載入更多" })).toBeNull();
  });
});

describe("AT_932_1_E_5 純文字渲染的執行期負控（R18）", () => {
  it("AT_932_1_E_5 script、Markdown 語法與 HTML 實體字樣皆以字面文字顯示，不執行、不轉格式、不二次解碼", async () => {
    const user = userEvent.setup();
    const scriptText = "<script>window.__si_xss=1</script>";
    const markdownText = "**粗體** 與 [連結](https://example.invalid/x) 與 `行內程式碼` 與 &lt;b&gt;x&lt;/b&gt; 字樣";
    const imgText = "<img src=x onerror=window.__si_xss=1>";
    const cardText = "第一行 <b>卡面</b>\n第二行 **加粗** 與 &amp; 實體\n";
    const fixture = clone(GA);
    const items = fixture.observations.items.filter(isValid);
    items[0].symptom = scriptText;
    items[1].symptom = markdownText;
    items[2].context = imgText;
    fixture.proposals.items[0].card = cardText;
    const scriptsBefore = document.querySelectorAll("script").length;
    renderSi({ fixture });
    await waitForObservations();
    const obs = panel("observations");
    for (const o of items.slice(0, 3)) await user.click(within(obs).getByRole("button", { name: `展開 ${o.id}` }));
    const sym1 = within(obs).getByTestId(`si-obs-field-${items[0].id}-symptom`);
    const sym2 = within(obs).getByTestId(`si-obs-field-${items[1].id}-symptom`);
    const ctx3 = within(obs).getByTestId(`si-obs-field-${items[2].id}-context`);
    expect(textOf(sym1)).toBe(scriptText);
    expect(textOf(sym2)).toBe(markdownText);
    expect(textOf(ctx3)).toBe(imgText);
    // &lt;b&gt; 仍是這七個字元，沒有被二次解碼成 <b>
    expect(textOf(sym2)).toContain("&lt;b&gt;x&lt;/b&gt;");
    // 欄位內沒有任何子元素（純文字節點），整個面板沒有出自這些字串的 img／b／strong／em／a
    for (const field of [sym1, sym2, ctx3]) expect(field.querySelector("*"), "欄位內不得有任何子元素").toBeNull();
    expect(obs.querySelectorAll("img, b, strong, em, a")).toHaveLength(0);
    // 表格列內（截斷的症狀欄）同樣是純文字
    expect(textOf(within(obs).getByTestId(`si-obs-row-${items[0].id}`))).toContain(scriptText);

    await user.click(tabButton(/^提案/));
    const card = await screen.findByTestId(`si-card-${fixture.proposals.items[0].id}`);
    expect(textOf(card)).toBe(cardText);
    expect(card.querySelector("*")).toBeNull();
    expect(panel("proposals").querySelectorAll("img, b, strong, em, a")).toHaveLength(0);

    expect(document.querySelectorAll("script")).toHaveLength(scriptsBefore);
    expect((window as unknown as Record<string, unknown>).__si_xss).toBeUndefined();
  });
});

describe("AT_932_1_E_6 篩選控制項與模組桶降級（R17）", () => {
  const optionValues = (select: HTMLElement) => Array.from((select as HTMLSelectElement).options).map((o) => o.value);

  it("AT_932_1_E_6 選項取自已載入資料的相異值；壞列不被篩除；模組桶缺席時停用、說明且不由證據文字推算", async () => {
    const user = userEvent.setup();
    // 真 CLI 自根層 P2 起每列都帶 buckets（黃金檔 2026-10-25 重產後亦然）：降級路徑以去掉該欄的狀態 A 複本驗
    const fixture = clone(GA);
    fixture.observations.items.forEach((o) => {
      delete (o as { buckets?: unknown }).buckets;
    });
    renderSi({ fixture });
    await waitForObservations();
    const obs = panel("observations");
    const sorted = (values: string[]) => [...new Set(values)].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
    const dispositionKeys = GOLDEN_OBS.map((o) => (/^DEF-/.test(o.disposition) ? "DEF-*" : o.disposition.split(/[：；;:@\s]/)[0]));

    expect(optionValues(within(obs).getByLabelText("分類"))).toEqual(["", ...sorted(GOLDEN_OBS.map((o) => o.category))]);
    expect(optionValues(within(obs).getByLabelText("嚴重度"))).toEqual(["", ...sorted(GOLDEN_OBS.map((o) => o.severity))]);
    expect(optionValues(within(obs).getByLabelText("處置"))).toEqual(["", ...sorted(dispositionKeys)]);
    expect(optionValues(within(obs).getByLabelText("時間窗"))).toEqual(["all", "today", "7d", "30d"]);
    // 五個控制項（含停用的模組桶）預設都選「全部」
    expect(within(obs).getAllByRole("option", { name: "全部", selected: true })).toHaveLength(5);

    // 嚴重度為 P3：只剩 severity 為 P3 的有效列，壞列仍顯示
    await user.selectOptions(within(obs).getByLabelText("嚴重度"), "P3");
    const p3 = GOLDEN_OBS.filter((o) => o.severity === "P3").map((o) => o.id);
    expect(p3.length).toBeGreaterThan(1);
    expect(validRowIds(obs)).toEqual(p3);
    expect(obs.querySelectorAll('[data-testid^="si-obs-invalid-"]')).toHaveLength(1);
    // 疊加分類：兩者交集
    await user.selectOptions(within(obs).getByLabelText("分類"), "process");
    expect(validRowIds(obs)).toEqual(GOLDEN_OBS.filter((o) => o.severity === "P3" && o.category === "process").map((o) => o.id));
    // 處置鍵 DEF-*：選項取自資料，這份黃金檔沒有 DEF 處置，所以沒有 DEF-* 選項；改選 deferred
    await user.selectOptions(within(obs).getByLabelText("嚴重度"), "");
    await user.selectOptions(within(obs).getByLabelText("分類"), "");
    await user.selectOptions(within(obs).getByLabelText("處置"), "deferred");
    expect(validRowIds(obs)).toEqual(GOLDEN_OBS.filter((o) => o.disposition.startsWith("deferred")).map((o) => o.id));
    await user.selectOptions(within(obs).getByLabelText("處置"), "");
    // 時間窗今天：只剩日期等於錨點日（2026-10-21）的列
    await user.selectOptions(within(obs).getByLabelText("時間窗"), "today");
    expect(validRowIds(obs)).toEqual(GOLDEN_OBS.filter((o) => o.time.startsWith("2026-10-21")).map((o) => o.id));
    expect(validRowIds(obs).length).toBeGreaterThan(0);
    expect(obs.querySelectorAll('[data-testid^="si-obs-invalid-"]')).toHaveLength(1);
    // 全部清回「全部」後 12 項全數回來
    await user.selectOptions(within(obs).getByLabelText("時間窗"), "all");
    expect(obsOrder(obs)).toHaveLength(12);

    // 模組桶：去掉 buckets 欄的狀態 A 複本 → 停用、說明，選項只有「全部」；證據含 AutoClaude/ 路徑的列不被歸桶
    const bucket = within(obs).getByLabelText("模組桶");
    expect(bucket).toBeDisabled();
    expect(optionValues(bucket)).toEqual([""]);
    expect(screen.getByTestId("si-bucket-note")).toHaveTextContent("此版本的 export 尚無模組桶欄（待根層 P2 交付）");
    expect(GOLDEN_OBS.some((o) => o.evidence.includes("AutoClaude/"))).toBe(true);
  });

  it("AT_932_1_E_6 每筆都帶 buckets 時模組桶啟用、選項依 BUCKET_DISPLAY_ORDER、只依資料自帶的 buckets 篩選；事件與提案分頁各有自己的篩選", async () => {
    const user = userEvent.setup();
    const fixture = clone(GA);
    const valid = fixture.observations.items.filter(isValid);
    valid.forEach((o, i) => {
      o.buckets = i === 0 ? ["SelfImproving", "AgentConsole"] : i === 8 ? ["AutoClaude"] : ["未分類"];
    });
    renderSi({ fixture });
    await waitForObservations();
    const obs = panel("observations");
    const bucket = within(obs).getByLabelText("模組桶");
    expect(bucket).toBeEnabled();
    expect(screen.queryByTestId("si-bucket-note")).toBeNull();
    expect(optionValues(bucket)).toEqual(["", "SelfImproving", "AutoClaude", "AgentConsole", "未分類"]);
    await user.selectOptions(bucket, "AgentConsole");
    expect(validRowIds(obs)).toEqual([valid[0].id]);
    expect(obs.querySelectorAll('[data-testid^="si-obs-invalid-"]')).toHaveLength(1);
    // 展開後顯示 buckets
    await user.click(within(obs).getByRole("button", { name: `展開 ${valid[0].id}` }));
    expect(within(obs).getByTestId(`si-obs-field-${valid[0].id}-buckets`)).toHaveTextContent("SelfImproving、AgentConsole");

    // 事件分頁：種類選項取自事件 kind 的相異值；時間窗以 t 的日期比對（事件都在 2026-10-20，錨點日 2026-10-21）
    await user.click(tabButton(/^事件/));
    const events = await screen.findByTestId("si-events-table");
    const eventPanel = panel("events");
    const kinds = [...new Set(GA.events.items.map((e) => e.kind))].sort();
    expect(optionValues(within(eventPanel).getByLabelText("種類"))).toEqual(["", ...kinds]);
    await user.selectOptions(within(eventPanel).getByLabelText("種類"), "attr");
    expect(events.querySelectorAll('[data-testid^="si-event-row-"]')).toHaveLength(GA.events.items.filter((e) => e.kind === "attr").length);
    await user.selectOptions(within(eventPanel).getByLabelText("種類"), "");
    await user.selectOptions(within(eventPanel).getByLabelText("時間窗"), "today");
    expect(eventPanel.querySelectorAll('[data-testid^="si-event-row-"]')).toHaveLength(0);
    expect(eventPanel).toHaveTextContent("沒有符合目前篩選的事件");
    await user.selectOptions(within(eventPanel).getByLabelText("時間窗"), "7d");
    expect(eventPanel.querySelectorAll('[data-testid^="si-event-row-"]')).toHaveLength(GA.events.items.length);

    // 提案分頁：狀態與類別，沒有時間窗控制項
    await user.click(tabButton(/^提案/));
    await screen.findByTestId("si-prop-table");
    const propPanel = panel("proposals");
    expect(within(propPanel).getByLabelText("狀態")).toBeInTheDocument();
    expect(within(propPanel).getByLabelText("類別")).toBeInTheDocument();
    expect(within(propPanel).queryByLabelText("時間窗")).toBeNull();
  });
});

describe("AT_932_1_E_7 帳本推進後頁面隨之改變（R12、R14）", () => {
  it("AT_932_1_E_7 把替身從狀態 A 換成 B 並重新整理：多出 OBS-SI-013 與 RUN-SI-002、事件 seq 7，共同項目逐項不變", async () => {
    const user = userEvent.setup();
    const { stub } = renderSi();
    await waitForObservations();
    const obs = panel("observations");
    const beforeOrder = obsOrder(obs);
    expect(beforeOrder).toHaveLength(12);
    const beforeTexts = beforeOrder.map((t) => textOf(within(obs).getByTestId(t)));
    expect(textOf(within(screen.getByTestId("si-status-banner")).getByTestId("si-open-runs"))).toBe("無");

    stub.fixture = GB;
    await user.click(screen.getByTestId("si-refresh"));
    await within(obs).findByTestId("si-obs-row-OBS-SI-013");
    const afterOrder = obsOrder(obs);
    expect(afterOrder).toHaveLength(13);
    // 共同項目逐項文字相同、順序不變；多出的一項為 OBS-SI-013
    // TCS-ConsoleUxSortHelp W-UX3：預設 ID 升冪、壞列恆在有效列之後，所以 OBS-SI-013 落在壞列之前（改預期值，斷言數不變）
    expect([...afterOrder.slice(0, 11), afterOrder[12]]).toEqual(beforeOrder);
    expect(afterOrder[11]).toBe("si-obs-row-OBS-SI-013");
    expect([...afterOrder.slice(0, 11), afterOrder[12]].map((t) => textOf(within(obs).getByTestId(t)))).toEqual(beforeTexts);
    const b13 = GB.observations.items.filter(isValid).find((o) => o.id === "OBS-SI-013") as SiObservation;
    await user.click(within(obs).getByRole("button", { name: "展開 OBS-SI-013" }));
    for (const key of ["id", "time", "context", "symptom", "evidence", "category", "severity", "disposition", "marks"] as const) {
      expect(textOf(within(obs).getByTestId(`si-obs-field-OBS-SI-013-${key}`)), key).toBe(b13[key]);
    }
    // 橫幅：進行中的運轉多出 RUN-SI-002，head 為狀態 B 的前 8 碼
    const banner = screen.getByTestId("si-status-banner");
    await waitFor(() => expect(within(banner).getByTestId("si-open-runs")).toHaveTextContent("RUN-SI-002"));
    expect(textOf(within(banner).getByTestId("si-head-sha"))).toBe((GB.status.headSha as string).slice(0, 8));

    // 事件分頁：多一列 seq 為 7 的事件與一筆 RUN-SI-002 運轉；共同項逐項相同
    await user.click(tabButton(/^事件/));
    await screen.findByTestId("si-events-table");
    const seqs = Array.from(panel("events").querySelectorAll('[data-testid^="si-event-row-"]')).map((el) => (el as HTMLElement).dataset.testid);
    expect(seqs).toEqual(GB.events.items.map((e) => `si-event-row-${e.seq}`));
    expect(seqs).toHaveLength(7);
    expect(seqs.slice(0, 6)).toEqual(GA.events.items.map((e) => `si-event-row-${e.seq}`));
    const runIds = Array.from(panel("events").querySelectorAll('[data-testid^="si-run-row-"]')).map((el) => (el as HTMLElement).dataset.testid);
    expect(runIds).toEqual(["si-run-row-RUN-SI-001", "si-run-row-RUN-SI-002"]);
    expect(within(panel("events")).getByTestId("si-run-row-RUN-SI-002").querySelector('[data-field="closedSeq"]')).toHaveTextContent("未結束");
  });
});

describe("AT_932_2_6 完整操作序列只產生 GET 請求，沒有寫入型控制項（R11、R12）", () => {
  it("AT_932_2_6 分頁、篩選、展開、載入更多、重新整理與錯誤重試之後，每個 fetch 都是不帶本文的 GET，畫面沒有表單與寫入型按鈕", async () => {
    limits.value = 5;
    const user = userEvent.setup();
    const { stub, container } = renderSi();
    const forbidden = /新增|刪除|核准|否決|決定|儲存|送出/;
    const seenButtons = new Set<string>();
    const sweep = () => {
      expect(container.querySelector("form"), "不得有表單").toBeNull();
      expect(container.querySelector('button[type="submit"], input[type="submit"]'), "不得有 submit").toBeNull();
      expect(container.querySelector('input[type="file"]'), "不得有檔案輸入").toBeNull();
      for (const name of buttonNames(container)) {
        seenButtons.add(name);
        expect(forbidden.test(name), `寫入型按鈕名稱：${name}`).toBe(false);
      }
    };

    await waitForObservations();
    sweep();
    // 篩選、展開全部、載入更多兩次
    await user.selectOptions(screen.getByLabelText("嚴重度"), "P3");
    await user.selectOptions(screen.getByLabelText("嚴重度"), "");
    for (const o of GOLDEN_OBS.slice(0, 5)) await user.click(screen.getByRole("button", { name: `展開 ${o.id}` }));
    await user.click(screen.getByRole("button", { name: "載入更多" }));
    await screen.findByRole("tab", { name: "觀察 (10+)" });
    await user.click(screen.getByRole("button", { name: "載入更多" }));
    await screen.findByRole("tab", { name: "觀察 (12)" });
    sweep();
    // 切換三個分頁，展開事件與提案
    await user.click(tabButton(/^提案/));
    await screen.findByTestId("si-prop-table");
    await user.selectOptions(screen.getByLabelText("狀態"), "proposed");
    await user.click(screen.getByRole("button", { name: "展開 PROP-SI-004" }));
    sweep();
    await user.click(tabButton(/^事件/));
    await screen.findByTestId("si-events-table");
    await user.click(screen.getByRole("button", { name: "展開 事件 1" }));
    sweep();
    await user.selectOptions(screen.getByLabelText("種類"), "attr");
    sweep();
    await user.click(tabButton(/^觀察/));
    await waitForObservations();
    // 重新整理，再令一次請求失敗並在錯誤態點重試
    await user.click(screen.getByTestId("si-refresh"));
    stub.overrides.observations = () => siUnavailable();
    await user.click(screen.getByTestId("si-refresh"));
    await within(panel("observations")).findByTestId("si-error");
    sweep();
    delete stub.overrides.observations;
    await user.click(within(panel("observations")).getByTestId("si-retry"));
    await waitForObservations();
    sweep();

    expect(stub.calls.length).toBeGreaterThan(10);
    for (const call of stub.calls) {
      expect(call.method, `${call.url} 的方法`).toBe("GET");
      expect(call.path.startsWith("/api/v1/si/"), `${call.url} 的路徑`).toBe(true);
      expect(call.hasBody, `${call.url} 不得帶本文`).toBe(false);
    }
    // 防反空轉：序列確實出現過這些按鈕（展開、載入更多、重新整理、重試）
    for (const must of ["重新整理", "重試", "展開 事件 1", "展開 PROP-SI-004"]) expect(seenButtons.has(must), `序列中沒看到按鈕 ${must}`).toBe(true);
  });
});

describe("AT_932_3_6 SI 全面失敗時各面板顯示錯誤態與原因（R12、R19）", () => {
  const ALL_503 = { status: () => siUnavailable(), observations: () => siUnavailable() };

  it("AT_932_3_6 橫幅與觀察分頁各自顯示 reason、detail、cause 逐字與摘要；沒有空表或零筆字樣；分頁標籤不帶筆數；重試可恢復", async () => {
    const user = userEvent.setup();
    const { stub, urls, container } = renderSi({ overrides: ALL_503 });
    const banner = screen.getByTestId("si-status-banner");
    const obs = screen.getByTestId("si-panel-observations");
    for (const area of [banner, obs]) {
      const err = await within(area).findByTestId("si-error");
      expect(within(err).getByText("自我進化資料無法取得")).toBeInTheDocument();
      expect(textOf(within(err).getByTestId("si-error-reason"))).toBe("si_unavailable");
      expect(textOf(within(err).getByTestId("si-error-detail"))).toBe("rc=2; stderr=boom 全形字元");
      expect(textOf(within(err).getByTestId("si-error-cause"))).toBe("nonzero_rc");
      expect(textOf(within(err).getByTestId("si-error-summary"))).toBe("SI 資料面不可用");
    }
    // 沒有空表、零筆或無事件字樣；分頁標籤不帶筆數
    expect(screen.queryByTestId("si-no-event")).toBeNull();
    expect(container.querySelector('[data-testid^="si-obs-row-"]')).toBeNull();
    expect(screen.queryByTestId("si-obs-table")).toBeNull();
    expect(screen.queryByTestId("si-empty")).toBeNull();
    for (const bad of ["0 筆", "無事件", "沒有資料", "目前沒有觀察", "(0)"]) expect(container.textContent).not.toContain(bad);
    expect(tabButton("觀察")).toBeInTheDocument();

    // 重試：該面板的請求再發一次；替身改回成功時面板轉為 ok 態
    const before = urls().filter((u) => u.includes("/observations")).length;
    delete stub.overrides.observations;
    await user.click(within(obs).getByTestId("si-retry"));
    await waitForObservations();
    expect(urls().filter((u) => u.includes("/observations")).length).toBe(before + 1);
    // 橫幅仍是錯誤態（各面板獨立）；它的重試也可恢復
    expect(within(banner).getByTestId("si-error")).toBeInTheDocument();
    delete stub.overrides.status;
    await user.click(within(banner).getByTestId("si-retry"));
    await within(banner).findByTestId("si-head-sha");
    expect(within(banner).queryByTestId("si-error")).toBeNull();
  });

  it("AT_932_3_6 單筆 404 si_not_found 的錯誤態摘要為查無此筆；reason 逐字；沒有 detail 與 cause 就不顯示", () => {
    render(<SiError error={new ApiError({ status: 404, message: "查無此筆", reason: "si_not_found", details: { id: "PROP-SI-404" } })} onRetry={vi.fn()} />);
    expect(textOf(screen.getByTestId("si-error-summary"))).toBe("查無此筆");
    expect(textOf(screen.getByTestId("si-error-reason"))).toBe("si_not_found");
    expect(screen.queryByTestId("si-error-detail")).toBeNull();
    expect(screen.queryByTestId("si-error-cause")).toBeNull();
    expect(screen.getByTestId("si-retry")).toBeInTheDocument();
  });

  it("AT_932_3_6 網路層失敗（沒有 reason）：只顯示摘要與標題，不編造 reason", () => {
    render(<SiError error={new ApiError({ status: 0, message: "無法連線到伺服器，請確認 console-api 是否在線" })} onRetry={vi.fn()} />);
    expect(screen.getByTestId("si-error-summary")).toHaveTextContent("無法連線到伺服器");
    expect(screen.queryByTestId("si-error-reason")).toBeNull();
  });
});

/** 卸載後重掛要用同一個 QueryClient 才能證明快取被丟棄（renderSi 每次建新的 Providers）；Harness 讓同一個 Providers 內切換 SiView 的掛載。 */
let capturedClient: QueryClient | null = null;
function Harness() {
  const qc = useQueryClient();
  const [shown, setShown] = useState(true);
  useEffect(() => {
    capturedClient = qc;
  }, [qc]);
  return (
    <>
      <button type="button" onClick={() => setShown((s) => !s)}>
        切換掛載
      </button>
      {shown ? <SiView /> : <p data-testid="harness-hidden">已卸載</p>}
    </>
  );
}

describe("AT_932_3_7 SI 查詢不重試、不留快取（R11、R12）", () => {
  it("AT_932_3_7 失敗端點只呼叫一次：SI 查詢覆寫了 Providers 預設的「5xx 重試一次」", async () => {
    const { urls } = renderSi({ overrides: { status: () => siUnavailable(), observations: () => siUnavailable() } });
    await within(screen.getByTestId("si-status-banner")).findByTestId("si-error");
    await within(screen.getByTestId("si-panel-observations")).findByTestId("si-error");
    // 預設的重試延遲是 1 秒；等超過它再數（若沒有覆寫，這時第二次請求早已發出）
    await new Promise((resolve) => setTimeout(resolve, 1600));
    expect(urls().filter((u) => u.endsWith("/api/v1/si/status"))).toHaveLength(1);
    expect(urls().filter((u) => u.includes("/api/v1/si/observations"))).toHaveLength(1);
  });

  it("AT_932_3_7 卸載後重掛：先顯示載入中、不先顯示上一次的資料，且重新發出新請求（gcTime 與 staleTime 皆為 0）", async () => {
    const user = userEvent.setup();
    const stub: SiStub = { fixture: GA, overrides: {}, calls: [] };
    signInAs("OPERATOR");
    stubSiApi(stub);
    render(
      <Providers>
        <Harness />
      </Providers>,
    );
    await screen.findByTestId("si-head-sha");
    await waitForObservations();
    const statusCalls = () => stub.calls.filter((c) => c.path === "/api/v1/si/status").length;
    expect(statusCalls()).toBe(1);

    await user.click(screen.getByRole("button", { name: "切換掛載" }));
    expect(screen.getByTestId("harness-hidden")).toBeInTheDocument();
    // gcTime 為 0：沒有任何 observer 的 SI 查詢隨即從快取移除
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 30));
    });
    expect((capturedClient as QueryClient).getQueryCache().findAll({ queryKey: ["si"] })).toHaveLength(0);

    // 重掛時替身延遲回應：先看到載入中，沒有舊資料
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    stub.overrides.status = async () => {
      await gate;
      return undefined;
    };
    stub.overrides.observations = async () => {
      await gate;
      return undefined;
    };
    await user.click(screen.getByRole("button", { name: "切換掛載" }));
    expect(screen.queryByTestId("si-head-sha")).toBeNull();
    expect(screen.queryByTestId("si-obs-table")).toBeNull();
    expect(screen.getAllByRole("status").filter((el) => el.textContent?.includes("載入中")).length).toBeGreaterThanOrEqual(2);
    await waitFor(() => expect(statusCalls()).toBe(2)); // 重新發出新請求，不是沿用舊快取
    release();
    await screen.findByTestId("si-head-sha");
    await waitForObservations();
  });

  it("AT_932_3_7 queries.ts 的 SI 查詢設定：retry 為假值、staleTime 與 gcTime 為 0，不輪詢、不因視窗聚焦重抓", () => {
    expect(SI_QUERY_OPTIONS.retry).toBe(false);
    expect(SI_QUERY_OPTIONS.staleTime).toBe(0);
    expect(SI_QUERY_OPTIONS.gcTime).toBe(0);
    expect(SI_QUERY_OPTIONS.refetchInterval).toBe(false);
    expect(SI_QUERY_OPTIONS.refetchOnWindowFocus).toBe(false);
  });
});

describe("AT_932_3_E_4 成功轉失敗時舊資料消失（R12）", () => {
  it("AT_932_3_E_4 重新整理失敗後舊列與橫幅內容全部移除只剩錯誤態；改回成功並重試後內容恢復為狀態 A", async () => {
    const user = userEvent.setup();
    const { stub, container } = renderSi();
    await screen.findByTestId("si-head-sha");
    await waitForObservations();
    expect(obsOrder(panel("observations"))).toHaveLength(12);

    stub.overrides.status = () => siUnavailable();
    stub.overrides.observations = () => siUnavailable();
    await user.click(screen.getByTestId("si-refresh"));
    await within(screen.getByTestId("si-status-banner")).findByTestId("si-error");
    await within(panel("observations")).findByTestId("si-error");
    // 沒有上一次成功的資料殘留（isError 時不渲染 data）
    expect(screen.queryByTestId("si-head-sha")).toBeNull();
    expect(screen.queryByTestId("si-pending-props")).toBeNull();
    expect(container.querySelector('[data-testid^="si-obs-row-"]')).toBeNull();
    expect(container.querySelector('[data-testid^="si-obs-invalid-"]')).toBeNull();

    delete stub.overrides.status;
    delete stub.overrides.observations;
    await user.click(within(screen.getByTestId("si-status-banner")).getByTestId("si-retry"));
    await user.click(within(panel("observations")).getByTestId("si-retry"));
    await waitForObservations();
    await screen.findByTestId("si-head-sha");
    expect(obsOrder(panel("observations"))).toEqual(GA.observations.items.map((r) => (isValid(r) ? `si-obs-row-${r.id}` : `si-obs-invalid-${r.line}`)));
    expect(textOf(screen.getByTestId("si-pending-props"))).toContain("PROP-SI-004");
  });
});

describe("AT_932_3_E_5 各面板失敗互相獨立且不渲染成空（R12、R13）", () => {
  it("AT_932_3_E_5 status 失敗：橫幅是錯誤而不是無事件，觀察分頁仍正常顯示 12 項", async () => {
    renderSi({ overrides: { status: () => siUnavailable() } });
    const banner = screen.getByTestId("si-status-banner");
    await within(banner).findByTestId("si-error");
    expect(screen.queryByTestId("si-no-event")).toBeNull();
    expect(screen.queryByTestId("si-pending-props")).toBeNull();
    await waitForObservations();
    expect(obsOrder(panel("observations"))).toHaveLength(12);
  });

  it("AT_932_3_E_5 觀察清單失敗：橫幅正常，觀察分頁是錯誤態而非空表；切到提案分頁（成功）正常顯示，錯誤只限失敗的面板", async () => {
    const user = userEvent.setup();
    renderSi({ overrides: { observations: () => siUnavailable() } });
    await screen.findByTestId("si-head-sha");
    const obs = panel("observations");
    await within(obs).findByTestId("si-error");
    expect(screen.queryByTestId("si-obs-table")).toBeNull();
    expect(screen.queryByTestId("si-empty")).toBeNull();
    expect(within(screen.getByTestId("si-status-banner")).queryByTestId("si-error")).toBeNull();
    await user.click(tabButton(/^提案/));
    await screen.findByTestId("si-prop-table");
    expect(within(panel("proposals")).queryByTestId("si-error")).toBeNull();
    expect(screen.getByTestId("si-prop-row-PROP-SI-004")).toBeInTheDocument();
  });

  it("AT_932_3_E_5 事件分頁的運轉與事件帳本各自獨立：運轉失敗不影響事件列表，反之亦然", async () => {
    const user = userEvent.setup();
    renderSi({ overrides: { runs: () => siUnavailable() } });
    await user.click(await screen.findByRole("tab", { name: /^事件/ }));
    await within(screen.getByTestId("si-runs-section")).findByTestId("si-error");
    await screen.findByTestId("si-events-table");
    expect(within(screen.getByTestId("si-events-section")).queryByTestId("si-error")).toBeNull();
    expect(screen.queryByTestId("si-runs-table")).toBeNull();
  });
});

describe("AT_932_3_E_6 NOT-EVALUABLE 與量不到的呈現規則（R13、R16）", () => {
  it("AT_932_3_E_6 NE 物件、headSha 為 null、ne、unavailable、空事件加 carrier NE 與 card 為 null 一律以量不到加原因呈現", async () => {
    const user = userEvent.setup();
    const fixture = clone(GA);
    fixture.status.headSha = null;
    fixture.status.ne = [{ field: "head_sha", reason: "git-unavailable" }];
    const item = fixture.status.items[0];
    item.capacity = { status: "NOT-EVALUABLE", reason: "capacity-verb-not-established" };
    item.unavailable = [{ trigger: "c", reason: "ledger-missing" }];
    item.eventsDetected = [];
    fixture.events.items = [];
    fixture.events.ne = [{ field: "events", reason: "carrier-not-established" }];
    fixture.proposals.items[0].card = null;
    fixture.proposals.ne = [{ field: "proposals.PROP-SI-004.card", reason: "git-unavailable" }];
    renderSi({ fixture });

    const banner = screen.getByTestId("si-status-banner");
    await within(banner).findByTestId("si-head-sha");
    const capacity = textOf(within(banner).getByTestId("si-capacity"));
    expect(capacity).toContain("NOT-EVALUABLE");
    expect(capacity).toContain("capacity-verb-not-established");
    expect(capacity).not.toContain("通過");
    expect(capacity).not.toContain("正常");
    expect(capacity.trim()).not.toBe("0");
    expect(textOf(within(banner).getByTestId("si-head-sha"))).toBe("量不到（NOT-EVALUABLE）");
    expect(within(banner).getByTestId("si-ne-list")).toHaveTextContent("head_sha：git-unavailable");
    expect(textOf(within(banner).getByTestId("si-no-event"))).toBe("無事件（尚有 1 項量不到）");
    expect(within(banner).getByTestId("si-unavailable")).toHaveTextContent("ledger-missing");

    // 事件分頁：顯示 carrier-not-established 的說明，不得只顯示沒有事件
    await user.click(tabButton(/^事件/));
    const events = await within(panel("events")).findByTestId("si-events-section");
    expect(within(events).getByTestId("si-ne-list")).toHaveTextContent("events：carrier-not-established");
    expect(within(events).getByTestId("si-events-ne")).toHaveTextContent("量不到（NOT-EVALUABLE）");
    expect(within(events).queryByTestId("si-empty")).toBeNull();
    expect(events.textContent).not.toContain("沒有事件");

    // 提案列：卡面量不到
    await user.click(tabButton(/^提案/));
    const row = await screen.findByTestId("si-prop-row-PROP-SI-004");
    expect(row).toHaveTextContent("卡面量不到（NOT-EVALUABLE）");
    expect(screen.queryByTestId("si-card-PROP-SI-004")).toBeNull();
  });

  it("touched_null（R16；掛在 AC-932-3 之下）：提案的 touched 與 touchedCount 為 null＝量不到，顯示量不到（NOT-EVALUABLE）而不是「無」；空陣列與 0 是真值，照常顯示", async () => {
    const user = userEvent.setup();
    const fixture = clone(GA);
    // 根層 export 在 rN.patch 讀不到或無法解析時，touched 與 touchedCount 為 null 且不附 ne 項；真的沒有觸及檔案時才是 [] 與 0
    fixture.proposals.items = [proposalOf({ id: "PROP-SI-004", touched: null, touchedCount: null }), proposalOf({ id: "PROP-SI-005", touched: [], touchedCount: 0 })];
    renderSi({ fixture });
    await user.click(await screen.findByRole("tab", { name: /^提案/ }));
    await screen.findByTestId("si-prop-table");

    for (const key of ["touched", "touchedCount"]) {
      const text = textOf(screen.getByTestId(`si-prop-field-PROP-SI-004-${key}`));
      expect(text, key).toBe("量不到（NOT-EVALUABLE）：patch 讀不到或無法解析");
      expect(text, key).not.toBe("無");
    }
    // 對照：空集合與 0 是真值，不是量不到
    expect(textOf(screen.getByTestId("si-prop-field-PROP-SI-005-touched"))).toBe("[]");
    expect(textOf(screen.getByTestId("si-prop-field-PROP-SI-005-touchedCount"))).toBe("0");
  });

  it("AT_932_3_E_6 problems 非空時逐項顯示 <subject> <code> <detail>；ne 與 problems 皆為空時兩個區塊都不渲染", async () => {
    const user = userEvent.setup();
    renderSi();
    await waitForObservations();
    const obs = panel("observations");
    expect(textOf(within(obs).getByTestId("si-problems-list"))).toContain("OBS-SI-012 ROW-ARITY 欄數不是 9 或行未以 | 結尾");
    expect(within(obs).queryByTestId("si-ne-list")).toBeNull(); // ne 為空：不顯示該區（不顯示「0 項」）
    await user.click(tabButton(/^提案/));
    await screen.findByTestId("si-prop-table");
    const props = panel("proposals");
    expect(within(props).queryByTestId("si-ne-list")).toBeNull();
    expect(within(props).queryByTestId("si-problems-list")).toBeNull();
  });

  it("AT_932_3_E_6 status 沒有任何項目（不該發生）：橫幅顯示量不到的說明，不假裝一切正常", async () => {
    const fixture = clone(GA);
    fixture.status.items = [];
    renderSi({ fixture });
    const banner = screen.getByTestId("si-status-banner");
    await within(banner).findByTestId("si-head-sha");
    expect(banner).toHaveTextContent("量不到（NOT-EVALUABLE）：status 回應沒有任何項目");
    expect(within(banner).queryByTestId("si-no-event")).toBeNull();
  });
});

describe("SiView 補充：骨架、分頁標籤與狀態橫幅各欄", () => {
  it("頁首有 h1「自我進化」與「重新整理」按鈕；tablist 的名稱為「自我進化資料」，預設分頁為觀察，分頁依序為觀察、提案、事件", async () => {
    renderSi();
    expect(screen.getByTestId("si-view")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "自我進化" })).toBeInTheDocument();
    expect(screen.getByTestId("si-refresh")).toHaveTextContent("重新整理");
    const tablist = screen.getByRole("tablist", { name: "自我進化資料" });
    const tabs = within(tablist).getAllByRole("tab");
    expect(tabs.map((t) => t.getAttribute("aria-selected"))).toEqual(["true", "false", "false"]);
    await screen.findByRole("tab", { name: "觀察 (12)" });
    expect(tabs.map((t) => t.textContent)).toEqual(["觀察 (12)", "提案", "事件"]);
    expect(screen.getByRole("tabpanel")).toHaveAttribute("data-testid", "si-panel-observations");
  });

  it("狀態橫幅各欄：暫停為無、冷卻與略過原因逐項、事件偵測非空時逐筆列出、openRuns 物件帶其餘鍵", async () => {
    const fixture = clone(GA);
    const item = fixture.status.items[0];
    item.eventsDetected = [{ trigger: "a", subject: "OBS-SI-010", detail: "同一症狀再現" }];
    item.suspended = { since: "2026-10-21", reason: "額度" };
    item.cooldowns = [{ id: "PROP-SI-004", until: "2026-10-30" }];
    item.openRuns = [{ run: "RUN-SI-009", openedSeq: 12, research: null, props: [] }];
    item.consolePending = [{ id: "DEC-1" }];
    renderSi({ fixture });
    const banner = await screen.findByTestId("si-status-banner");
    await within(banner).findByTestId("si-head-sha");
    expect(within(banner).getByTestId("si-events-detected")).toHaveTextContent("a｜OBS-SI-010｜同一症狀再現");
    expect(within(banner).queryByTestId("si-no-event")).toBeNull();
    expect(textOf(within(banner).getByTestId("si-suspended"))).toBe('{"since":"2026-10-21","reason":"額度"}');
    expect(within(banner).getByTestId("si-cooldowns")).toHaveTextContent('{"id":"PROP-SI-004","until":"2026-10-30"}');
    expect(within(banner).getByTestId("si-skip-reasons")).toHaveTextContent("quota-band：0");
    expect(within(banner).getByTestId("si-open-runs")).toHaveTextContent("RUN-SI-009（openedSeq：12；research：無；props：[]）");
    // 不認得的鍵（日後根層加的 consolePending）原樣列出，不丟欄位
    expect(within(banner).getByTestId("si-status-extra")).toHaveTextContent('consolePending：[{"id":"DEC-1"}]');
    expect(banner.querySelector('[data-status-key="consolePending"]')).not.toBeNull();
  });

  it("狀態橫幅：suspended 為 null 顯示「無」，空的 openRuns 與冷卻也顯示「無」（真的為空才顯示無；量不到的欄位另有固定句型）", async () => {
    renderSi();
    const banner = await screen.findByTestId("si-status-banner");
    await within(banner).findByTestId("si-head-sha");
    expect(textOf(within(banner).getByTestId("si-suspended"))).toBe("無");
    expect(textOf(within(banner).getByTestId("si-open-runs"))).toBe("無");
    expect(textOf(within(banner).getByTestId("si-cooldowns"))).toBe("無");
  });

  it("狀態橫幅的已知欄位缺席或型別不符（根層 schema 變動時才會發生）：照量不到呈現，不假裝是「無」或「無事件」；null 的 suspended 仍是合法的「無」", async () => {
    const fixture = clone(GA);
    const item = fixture.status.items[0] as Record<string, unknown>;
    delete item.eventsDetected; // 缺席：不得被讀成「無事件」
    item.pendingProps = "not-a-list"; // 型別不符
    delete item.capacity; // 缺席
    item.skipReasons = ["x"]; // 陣列不是物件
    renderSi({ fixture });
    const banner = await screen.findByTestId("si-status-banner");
    await within(banner).findByTestId("si-head-sha");
    const missing = "量不到（NOT-EVALUABLE）：欄位缺席或型別不符";
    expect(textOf(within(banner).getByTestId("si-events-detected"))).toBe(missing);
    expect(within(banner).queryByTestId("si-no-event")).toBeNull();
    expect(textOf(within(banner).getByTestId("si-pending-props"))).toBe(missing);
    expect(textOf(within(banner).getByTestId("si-capacity"))).toBe(missing);
    expect(textOf(within(banner).getByTestId("si-skip-reasons"))).toBe(missing);
    expect(textOf(within(banner).getByTestId("si-suspended"))).toBe("無"); // 沒被動到的欄位照常
  });

  it("狀態橫幅：沒有事件且 unavailable 缺席時，無事件的說明帶上「量不到的項數不明」，不只說無事件", async () => {
    const fixture = clone(GA);
    const item = fixture.status.items[0] as Record<string, unknown>;
    delete item.unavailable;
    renderSi({ fixture });
    const banner = await screen.findByTestId("si-status-banner");
    await within(banner).findByTestId("si-head-sha");
    expect(textOf(within(banner).getByTestId("si-no-event"))).toBe("無事件（unavailable 欄位缺席或型別不符，量不到的項數不明）");
    expect(textOf(within(banner).getByTestId("si-unavailable"))).toBe("量不到（NOT-EVALUABLE）：欄位缺席或型別不符");
  });

  it("觀察列的展開與收合：按鈕名稱固定為「展開 <ID>」，狀態用 aria-expanded 表達；marksKv、行號逐項顯示；時間窗下無法解析的時間被標示而不被篩掉", async () => {
    const user = userEvent.setup();
    const fixture = clone(GA);
    const first = fixture.observations.items.filter(isValid)[0];
    first.time = "約一週前";
    renderSi({ fixture });
    await waitForObservations();
    const obs = panel("observations");
    const toggle = within(obs).getByRole("button", { name: `展開 ${first.id}` });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(within(obs).queryByTestId(`si-obs-fields-${first.id}`)).toBeNull();
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(within(obs).getByRole("button", { name: `展開 ${first.id}` })).toBe(toggle);
    const marksKv = within(obs).getByTestId(`si-obs-field-${first.id}-marksKv`);
    for (const [k, v] of Object.entries(first.marksKv)) expect(marksKv).toHaveTextContent(`${k}：${v}`);
    expect(textOf(within(obs).getByTestId(`si-obs-field-${first.id}-line`))).toBe(String(first.line));
    await user.click(toggle);
    expect(within(obs).queryByTestId(`si-obs-fields-${first.id}`)).toBeNull();
    // 時間無法解析：選了時間窗仍顯示該列並標「時間無法解析」
    expect(within(obs).queryByTestId(`si-time-unparsable-${first.id}`)).toBeNull();
    await user.selectOptions(within(obs).getByLabelText("時間窗"), "7d");
    expect(within(obs).getByTestId(`si-obs-row-${first.id}`)).toBeInTheDocument();
    expect(within(obs).getByTestId(`si-time-unparsable-${first.id}`)).toHaveTextContent("時間無法解析");
  });

  it("重新整理後已選的篩選值不在資料裡：控制項仍顯示該值（如實反映仍在生效的篩選），不會顯示成「全部」卻繼續篩；清回全部後列都回來", async () => {
    const user = userEvent.setup();
    const { stub } = renderSi();
    await waitForObservations();
    const obs = panel("observations");
    await user.selectOptions(within(obs).getByLabelText("嚴重度"), "P1");
    expect(validRowIds(obs)).toEqual(["OBS-SI-008"]);

    const next = clone(GA);
    for (const o of next.observations.items.filter(isValid)) if (o.severity === "P1") o.severity = "P2";
    stub.fixture = next;
    await user.click(screen.getByTestId("si-refresh"));
    await waitFor(() => expect(validRowIds(obs)).toEqual([]));
    const select = within(obs).getByLabelText("嚴重度") as HTMLSelectElement;
    expect(select.value).toBe("P1");
    expect(within(select).getByRole("option", { name: "P1" })).toBeInTheDocument();
    expect(obs).toHaveTextContent("沒有符合目前篩選的觀察列");
    await user.selectOptions(select, "");
    expect(obsOrder(obs)).toHaveLength(12);
  });

  it("提案列的欄位：digest 前 8 碼（完整值在 title）、verdict 與 cooldown 為 null 顯示無；事件詳情是縮排 JSON 純文字", async () => {
    const user = userEvent.setup();
    renderSi();
    await user.click(await screen.findByRole("tab", { name: /^提案/ }));
    const row = await screen.findByTestId("si-prop-row-PROP-SI-004");
    const cells = within(row).getAllByRole("cell");
    const p = GA.proposals.items[0];
    expect(cells.map((c) => c.textContent)).toEqual(["", p.id, p.state, p.cls, p.route, String(p.rev), "d21ae6f5", "無", "無"]);
    expect(within(row).getByTitle(p.digest)).toHaveTextContent("d21ae6f5");
    await screen.findByRole("tab", { name: "提案 (1)" });
    // 展開區另列其餘欄位
    expect(textOf(screen.getByTestId("si-prop-field-PROP-SI-004-sources"))).toBe(JSON.stringify(p.sources));
  });

  it("事件分頁標籤帶事件筆數（運轉另有自己的表）；沒有運轉紀錄時顯示說明而不是空表", async () => {
    const user = userEvent.setup();
    const fixture = clone(GA);
    fixture.runs.items = [];
    renderSi({ fixture });
    await user.click(await screen.findByRole("tab", { name: /^事件/ }));
    await screen.findByRole("tab", { name: "事件 (6)" });
    expect(screen.getByTestId("si-runs-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("si-runs-table")).toBeNull();
  });

  it("切換分頁時舊面板卸載：回到觀察分頁會重新請求（不顯示上一次的資料）", async () => {
    const user = userEvent.setup();
    const { urls } = renderSi();
    await waitForObservations();
    await user.click(tabButton(/^提案/));
    await screen.findByTestId("si-prop-table");
    await user.click(tabButton(/^觀察/));
    await waitForObservations();
    expect(urls().filter((u) => u.includes("/si/observations"))).toHaveLength(2);
    expect(urls().filter((u) => u.includes("/si/proposals"))).toHaveLength(1);
  });
});

// ══ P2b：寫入入口與對帳面板（TCS-SelfImprovingDecide-P2b：AT-935-3-2／4-2／4-E-3／5-3／5-E-4；W21）═══════════════════════════════════
// 為什麼重要：寫入入口只該給 ADMIN——非 ADMIN 多看到一個「決定」鈕，就多一條會被 403 的路、也多一個誤按的風險；而對帳面板若把「量不到」顯示成「無待入帳」，
// 掌舵者會以為所有決定都已入帳。所以這裡逐角色驗控件與請求，並釘住「量不到不是沒有」。控件的 testid 前綴＝W21：si-decide-open-、si-resume-open、si-obs-new、si-obs-correct-、si-close-open-。

const WRITE_TESTID = /^si-(decide-open-|resume-open|obs-new|obs-correct-|close-open-|schedule-toggle-open|schedule-period-open|run-request-open)/;
const FORBIDDEN_NAME = /刪除|移除|清除|delete|remove/i;
const consoleWriteCalls = (stub: SiStub) => stub.calls.filter((c) => c.path === "/api/v1/si/console-writes");
const AUDIT_A = "b2000000-0000-4000-8000-00000000000a";
const AUDIT_B = "b2000000-0000-4000-8000-00000000000b";
const AUDIT_C = "b2000000-0000-4000-8000-00000000000c";
/** 決定重送去重（TCS-SelfImprovingDecideDedupe）的夾具：AUDIT_E 已入帳、AUDIT_S 是被它取代的同一決定；DIGEST_X 為該決定的卡面 digest。 */
const AUDIT_E = "b2000000-0000-4000-8000-0000000000e1";
const AUDIT_S = "b2000000-0000-4000-8000-0000000000e2";
const DIGEST_X = `sha256:${"a".repeat(64)}`;

/** console-writes 的回應物件（預設：已對帳、沒有 orphans）；測試以 overrides 回它。 */
function writesData(patch: Partial<SiConsoleWrites> = {}): { data: SiConsoleWrites } {
  return { data: { items: [], truncated: false, orphans: [], reconcile: { status: "ok", reason: null, backfilled: 0 }, ...patch } };
}

describe("AT_935_4_2 ADMIN 看得到全部寫入控件並發出 console-writes 查詢", () => {
  it("AT_935_4_2 觀察分頁：有 si-obs-new、每個有效列的 si-obs-correct-<ID>、處置為 open 的列的 si-close-open-<ID>；另有 si-writes-panel；請求集合含恰一個 console-writes GET", async () => {
    const user = userEvent.setup();
    const { stub } = renderSi({ role: "ADMIN", username: "admin" });
    const table = await waitForObservations();
    expect(screen.getByTestId("si-obs-new")).toBeInTheDocument();
    for (const o of GOLDEN_OBS) expect(within(table).getByTestId(`si-obs-correct-${o.id}`), o.id).toBeInTheDocument();
    const open = GOLDEN_OBS.filter((o) => o.disposition === "open").map((o) => o.id);
    expect(open.length).toBeGreaterThan(0);
    expect(Array.from(table.querySelectorAll<HTMLElement>('[data-testid^="si-close-open-"]')).map((el) => el.dataset.testid?.replace("si-close-open-", ""))).toEqual(open);
    expect(await screen.findByTestId("si-writes-panel")).toBeInTheDocument();

    // 提案分頁：待決卡有 si-decide-open-<ID>（面板常駐，切分頁不重取對帳）
    await user.click(tabButton(/^提案/));
    await screen.findByTestId("si-prop-table");
    expect(screen.getByTestId("si-decide-open-PROP-SI-004")).toBeInTheDocument();
    expect(consoleWriteCalls(stub)).toHaveLength(1);
    expect(consoleWriteCalls(stub)[0].method).toBe("GET");
    expect(consoleWriteCalls(stub)[0].query.get("limit")).toBe("100");
  });

  it("AT_935_4_2 橫幅 suspended 帶運轉號時有 si-resume-open（綁該運轉）；suspended 為 null 時沒有", async () => {
    const withRun = clone(GA);
    withRun.status.items[0].suspended = { run: "RUN-SI-001" };
    const view = renderSi({ role: "ADMIN", username: "admin", fixture: withRun });
    expect(await screen.findByTestId("si-resume-open")).toHaveAccessibleName("恢復運轉 RUN-SI-001");
    view.unmount();
    renderSi({ role: "ADMIN", username: "admin" });
    await screen.findByTestId("si-head-sha");
    expect(screen.queryByTestId("si-resume-open")).toBeNull();
  });

  it("AT_935_4_2 沒有可下決定的提案（狀態為 approved）沒有決定鈕；每個決定鈕的 testid 都帶該列的提案號", async () => {
    const user = userEvent.setup();
    const approved = clone(GA);
    approved.proposals.items[0].state = "approved";
    renderSi({ role: "ADMIN", username: "admin", fixture: approved });
    await user.click(await screen.findByRole("tab", { name: /^提案/ }));
    await screen.findByTestId("si-prop-table");
    expect(screen.queryByTestId("si-decide-open-PROP-SI-004")).toBeNull();
  });
});

describe("AT_935_4_E_3 非 ADMIN 沒有寫入面：VIEWER 與 OPERATOR 零控件、零 POST、零 console-writes 請求", () => {
  it.each(["VIEWER", "OPERATOR"] as const)(
    "AT_935_4_E_3 %s 完整操作（切分頁、篩選、展開、重新整理）後：DOM 沒有任何寫入控件與對帳面板，全部請求為不帶本文的 GET 且不含 console-writes，沒有待入帳或警示字樣",
    async (role) => {
      const user = userEvent.setup();
      const withRun = clone(GA);
      withRun.status.items[0].suspended = { run: "RUN-SI-001" };
      const { stub, container } = renderSi({ role, fixture: withRun });
      const sweep = () => {
        expect(
          container.querySelector(
            "[data-testid^='si-decide-open-'], [data-testid='si-resume-open'], [data-testid='si-obs-new'], [data-testid^='si-obs-correct-'], [data-testid^='si-close-open-'], [data-testid='si-writes-panel']",
          ),
        ).toBeNull();
        expect(container.querySelector("form")).toBeNull();
        expect(document.body.textContent ?? "").not.toMatch(/待入帳|對帳警示|無待入帳/);
      };
      await waitForObservations();
      await screen.findByTestId("si-suspended");
      sweep();
      await user.selectOptions(screen.getByLabelText("嚴重度"), "P3");
      const shownRow = GOLDEN_OBS.find((o) => o.severity === "P3") as SiObservation; // 篩選之後仍看得到的第一列
      await user.click(screen.getByRole("button", { name: `展開 ${shownRow.id}` }));
      sweep();
      await user.click(tabButton(/^提案/));
      await screen.findByTestId("si-prop-table");
      await user.click(screen.getByRole("button", { name: "展開 PROP-SI-004" }));
      sweep();
      await user.click(tabButton(/^事件/));
      await screen.findByTestId("si-events-table");
      await user.click(screen.getByTestId("si-refresh"));
      sweep();

      expect(stub.calls.length).toBeGreaterThan(5);
      for (const call of stub.calls) {
        expect(call.method, call.url).toBe("GET");
        expect(call.hasBody, `${call.url} 不得帶本文`).toBe(false);
        expect(call.path, "零 console-writes 請求").not.toBe("/api/v1/si/console-writes");
      }
    },
  );
});

describe("AT_935_3_2 沒有刪除 UI：ADMIN 畫面無刪除、移除、清除類控件，操作只有決定、新增、更正、關閉", () => {
  it("AT_935_3_2 三分頁與狀態橫幅（含 suspended 變體）與對帳面板的全部按鈕與連結：名稱與 testid 不含刪除、移除、清除、delete、remove；寫入類控件的 testid 前綴恰為五個", async () => {
    const user = userEvent.setup();
    const withRun = clone(GA);
    withRun.status.items[0].suspended = { run: "RUN-SI-001" };
    // 對帳面板另有「已被取代」群組（TCS-SelfImprovingDecideDedupe）：資料含一組被取代的決定（AUDIT_S 被已入帳的 AUDIT_E 取代），群組的展開鈕才會出現在掃描範圍內
    const { container } = renderSi({
      role: "ADMIN",
      username: "admin",
      fixture: withRun,
      overrides: {
        "console-writes": () =>
          writesData({
            items: [
              writeItem({ auditRef: AUDIT_A, kind: "decide" }),
              writeItem({ auditRef: AUDIT_E, kind: "decide", subjectId: "PROP-SI-006", dkind: "promote", digest: DIGEST_X, ingested: true }),
              writeItem({ auditRef: AUDIT_S, kind: "decide", subjectId: "PROP-SI-006", dkind: "promote", digest: DIGEST_X, ingested: false, supersededBy: AUDIT_E }),
            ],
          }),
      },
    });
    const seenPrefixes = new Set<string>();
    const seenReadOnly = new Set<string>();
    const READ_ONLY_TESTIDS = new Set([
      "si-refresh",
      "si-retry",
      "si-load-more",
      // 對帳面板「已被取代」群組的展開鈕：只改畫面上的展開狀態，不送寫入請求、不落檔；封閉集合逐個列名（名稱與 testid 仍受 FORBIDDEN_NAME 掃描）
      "si-superseded-toggle",
      // 狀態快篩的 pill（觀察與提案各四顆）：只改畫面上的篩選條件，不送寫入請求、不落檔；以封閉集合逐個列名，不放寬成 si-status- 前綴
      "si-status-observations-all",
      "si-status-observations-open",
      "si-status-observations-deferred",
      "si-status-observations-done",
      "si-status-proposals-all",
      "si-status-proposals-pending",
      "si-status-proposals-active",
      "si-status-proposals-done",
    ]);
    const sweep = () => {
      for (const el of Array.from(container.querySelectorAll<HTMLElement>("button, a"))) {
        const name = `${el.getAttribute("aria-label") ?? ""} ${el.textContent ?? ""}`;
        const testId = el.dataset.testid ?? "";
        expect(name, `按鈕名稱：${name}`).not.toMatch(FORBIDDEN_NAME);
        expect(testId, `testid：${testId}`).not.toMatch(FORBIDDEN_NAME);
        if (READ_ONLY_TESTIDS.has(testId)) seenReadOnly.add(testId);
        if (el.tagName === "BUTTON" && testId.startsWith("si-") && !READ_ONLY_TESTIDS.has(testId)) {
          expect(testId, `未列名的 si- 按鈕 testid：${testId}`).toMatch(WRITE_TESTID);
          seenPrefixes.add(/^si-(decide-open-|resume-open|obs-new|obs-correct-|close-open-|schedule-toggle-open|schedule-period-open|run-request-open)/.exec(testId)?.[1] as string);
        }
      }
    };
    await waitForObservations();
    await screen.findByTestId("si-resume-open");
    await within(await screen.findByTestId("si-writes-panel")).findByTestId(`si-pending-${AUDIT_A}`);
    sweep();
    // 展開「已被取代」群組後再掃一次：群組內的列沒有任何按鈕或連結，掃描面不會多出刪除類控件
    await user.click(within(screen.getByTestId("si-writes-panel")).getByTestId("si-superseded-toggle"));
    await within(screen.getByTestId("si-writes-panel")).findByTestId(`si-superseded-${AUDIT_S}`);
    sweep();
    await user.click(tabButton(/^提案/));
    await screen.findByTestId("si-prop-table");
    sweep();
    await user.click(tabButton(/^事件/));
    await screen.findByTestId("si-events-table");
    sweep();
    // 防反空轉：八個前綴（P4 加排程面板的三個控件鈕）都真的出現過；狀態快篩的八顆 pill 也都真的被掃到（觀察分頁四顆、提案分頁四顆）——否則上面的封閉集合是死名單
    expect([...seenPrefixes].sort()).toEqual(["close-open-", "decide-open-", "obs-correct-", "obs-new", "resume-open", "run-request-open", "schedule-period-open", "schedule-toggle-open"].sort());
    expect([...seenReadOnly].filter((id) => id.startsWith("si-status-")).sort()).toEqual(
      [
        "si-status-observations-all",
        "si-status-observations-open",
        "si-status-observations-deferred",
        "si-status-observations-done",
        "si-status-proposals-all",
        "si-status-proposals-pending",
        "si-status-proposals-active",
        "si-status-proposals-done",
      ].sort(),
    );
    // 防反空轉：群組的展開鈕真的被掃到（否則上面的封閉集合與名稱掃描對它是死名單）
    expect(seenReadOnly.has("si-superseded-toggle"), "si-superseded-toggle 被掃到").toBe(true);
    // 對帳面板只有「入帳指令」展開鈕與「已被取代」群組的展開鈕（沒有刪除、移除、清除）
    const panel = screen.getByTestId("si-writes-panel");
    expect(
      within(panel)
        .getAllByRole("button")
        .map((b) => b.textContent),
    ).toEqual(["入帳指令", "另有 1 筆已被取代（同一張卡的同一決定已由其他稽核檔入帳）"]);
  });
});

describe("AT_935_5_3 待入帳面板：項目、三種 kind 的入帳指令、入帳後消失", () => {
  const T1 = "2026-10-24T14:30:10Z";
  const T2 = "2026-10-24T14:30:12Z";
  const T3 = "2026-10-24T14:30:15Z";
  const items = (ingested: boolean) => [
    writeItem({ auditRef: AUDIT_C, kind: "obs-close", subjectId: "OBS-SI-005", time: T3, ingested }),
    writeItem({ auditRef: AUDIT_A, kind: "decide", subjectId: "PROP-SI-004", time: T1, ingested }),
    writeItem({ auditRef: AUDIT_B, kind: "obs-add", subjectId: null, time: T2, ingested }),
  ];

  it("AT_935_5_3 三個待入帳項（decide、obs-add、obs-close）依 time 升冪列出 kind、對象（obs-add 為破折號）與 time；展開後指令逐字等於 ingestCommands；改為已入帳後重新整理，si-writes-empty 顯示無待入帳且沒有警示", async () => {
    const user = userEvent.setup();
    let ingested = false;
    const { stub } = renderSi({ role: "ADMIN", username: "admin", overrides: { "console-writes": () => writesData({ items: items(ingested) }) } });
    const panel = await screen.findByTestId("si-writes-panel");
    const list = await within(panel).findByTestId("si-pending-list");
    expect(Array.from(list.querySelectorAll<HTMLElement>('[data-testid^="si-pending-"]')).map((li) => li.dataset.testid)).toEqual([AUDIT_A, AUDIT_B, AUDIT_C].map((r) => `si-pending-${r}`));

    const expected: Array<[string, "decide" | "obs-add" | "obs-close", string | null, string, string]> = [
      [AUDIT_A, "decide", "PROP-SI-004", T1, "PROP-SI-004"],
      [AUDIT_B, "obs-add", null, T2, "—"],
      [AUDIT_C, "obs-close", "OBS-SI-005", T3, "OBS-SI-005"],
    ];
    for (const [auditRef, kind, subject, time, shownSubject] of expected) {
      const row = within(panel).getByTestId(`si-pending-${auditRef}`);
      expect(row).toHaveTextContent(kind);
      expect(row).toHaveTextContent("待入帳");
      expect(row).toHaveTextContent(`對象：${shownSubject}`);
      expect(row).toHaveTextContent(time);
      expect(within(row).queryByTestId("sdd-recovery-command-posix"), "預設收合").toBeNull();
      await user.click(within(row).getByRole("button", { name: "入帳指令" }));
      const commands = ingestCommands(kind, subject, auditRef);
      expect(within(row).getByTestId("sdd-recovery-command-powershell").textContent).toBe(commands.powershell);
      expect(within(row).getByTestId("sdd-recovery-command-posix").textContent).toBe(commands.posix);
    }
    expect(within(panel).queryByTestId("si-writes-empty")).toBeNull();
    expect(within(panel).queryByTestId("si-write-alerts")).toBeNull();

    ingested = true;
    await user.click(screen.getByTestId("si-refresh"));
    const empty = await within(panel).findByTestId("si-writes-empty");
    expect(empty).toHaveTextContent("無待入帳");
    expect(within(panel).queryByTestId("si-pending-list")).toBeNull();
    expect(within(panel).queryByTestId("si-write-alerts")).toBeNull();
    expect(consoleWriteCalls(stub).length, "初次加重新整理各一個").toBe(2);
  });

  it("AT_935_5_3 已入帳（true）與量不到（null）的列不算待入帳；回傳 truncated 時說明只涵蓋最新一百筆", async () => {
    renderSi({
      role: "ADMIN",
      username: "admin",
      overrides: {
        "console-writes": () =>
          writesData({ items: [writeItem({ auditRef: AUDIT_A, kind: "decide", ingested: true }), writeItem({ auditRef: AUDIT_B, kind: "obs-add", ingested: null })], truncated: true }),
      },
    });
    const panel = await screen.findByTestId("si-writes-panel");
    expect(await within(panel).findByTestId("si-writes-empty")).toHaveTextContent("無待入帳（僅涵蓋最新 100 筆稽核列）");
    expect(within(panel).queryByTestId("si-pending-list")).toBeNull();
    expect(within(panel).getByTestId("si-writes-truncated")).toBeInTheDocument();
  });
});

describe("AT_935_5_E_4 紅色警示與量不到：orphans 顯示警示，NOT-EVALUABLE 時不顯示無待入帳", () => {
  it("AT_935_5_E_4 兩個 orphans：si-write-alerts 為 role alert 並逐項顯示 auditRef、kind、對象（null 為破折號）；有警示時不顯示無待入帳", async () => {
    renderSi({
      role: "ADMIN",
      username: "admin",
      overrides: {
        "console-writes": () =>
          writesData({
            orphans: [
              { auditRef: AUDIT_A, kind: "decide", subject: "PROP-SI-004" },
              { auditRef: AUDIT_B, kind: "obs-add", subject: null },
            ],
          }),
      },
    });
    const alerts = await screen.findByTestId("si-write-alerts");
    expect(alerts).toHaveAttribute("role", "alert");
    expect(within(alerts).getByTestId(`si-orphan-${AUDIT_A}`)).toHaveTextContent(`${AUDIT_A}｜decide｜PROP-SI-004`);
    expect(within(alerts).getByTestId(`si-orphan-${AUDIT_B}`)).toHaveTextContent(`${AUDIT_B}｜obs-add｜—`);
    expect(screen.queryByTestId("si-writes-empty"), "有警示就不是「無」").toBeNull();
  });

  it("AT_935_5_E_4 reconcile 為 NOT-EVALUABLE（reason 為 si_unavailable）：顯示 si-reconcile-ne 與 reason 逐字，整頁沒有「無待入帳」、沒有待入帳清單與警示——量不到不是沒有", async () => {
    renderSi({
      role: "ADMIN",
      username: "admin",
      overrides: {
        "console-writes": () =>
          writesData({
            items: [writeItem({ auditRef: AUDIT_A, kind: "decide", ingested: null })],
            orphans: null,
            reconcile: { status: "NOT-EVALUABLE", reason: "si_unavailable", backfilled: 0 },
          }),
      },
    });
    const ne = await screen.findByTestId("si-reconcile-ne");
    expect(ne).toHaveTextContent("量不到（NOT-EVALUABLE）：si_unavailable");
    expect(screen.queryByTestId("si-writes-empty")).toBeNull();
    expect(screen.queryByTestId("si-pending-list")).toBeNull();
    expect(screen.queryByTestId("si-write-alerts")).toBeNull();
    expect(document.body.textContent ?? "").not.toContain("無待入帳");
  });

  it.each(["bridge_unreachable", "bridge_timeout", "scan_cap_exceeded"] as const)("AT_935_5_E_4 NOT-EVALUABLE 的原因 %s 逐字顯示", async (reason) => {
    renderSi({ role: "ADMIN", username: "admin", overrides: { "console-writes": () => writesData({ orphans: null, reconcile: { status: "NOT-EVALUABLE", reason, backfilled: 0 } }) } });
    expect(await screen.findByTestId("si-reconcile-ne")).toHaveTextContent(reason);
    expect(screen.queryByTestId("si-writes-empty")).toBeNull();
  });

  it("AT_935_5_E_4 reconcile 為 ok 且沒有待入帳與 orphans 時才顯示 si-writes-empty；對帳查詢本身失敗（503 si_unavailable）顯示錯誤態與 reason，不顯示無待入帳", async () => {
    const ok = renderSi({ role: "ADMIN", username: "admin" });
    expect(await within(await screen.findByTestId("si-writes-panel")).findByTestId("si-writes-empty")).toHaveTextContent("無待入帳");
    ok.unmount();

    renderSi({ role: "ADMIN", username: "admin", overrides: { "console-writes": () => siUnavailable("bridge_down", "connect refused") } });
    const panel = await screen.findByTestId("si-writes-panel");
    const error = await within(panel).findByTestId("si-error");
    expect(error).toHaveTextContent("si_unavailable");
    expect(within(panel).queryByTestId("si-writes-empty")).toBeNull();
  });
});

// ══ 決定重送去重：對帳面板的「已被取代」群組（TCS-SelfImprovingDecideDedupe：AT-951-4-1、4-E-1、4-E-2；W-D4；NFR-DD-3）══════════════════════
// 為什麼重要：OBS-SI-348——同一決定的多份稽核檔只有一份能入帳，其餘永遠顯示待入帳而誤導掌舵者。面板要把被取代的列移出待入帳清單、收進預設收合的群組（不是刪除、
// 也不冒充已入帳），且「量不到」時不得顯示群組或「無待入帳」；被取代的筆數也不能讓真正的待入帳或 orphans 警示被吞掉。
const SUPERSEDED_TITLE = (n: number) => `另有 ${n} 筆已被取代（同一張卡的同一決定已由其他稽核檔入帳）`;
const AUDIT_S2 = "b2000000-0000-4000-8000-0000000000e3";
const AUDIT_S3 = "b2000000-0000-4000-8000-0000000000e4";

describe("AT_951_4_1 對帳面板：待入帳清單排除被取代列，被取代列進預設收合的群組，兩處都顯示 dkind，群組列沒有入帳指令鈕，面板內沒有刪除類控件", () => {
  it("AT_951_4_1 si-pending-list 恰含 P1 與 P2（P1 顯示 核准 approve、P2 沒有 dkind 元素）；si-superseded-list 在其後、預設收合、標題為另有 2 筆已被取代；展開後 S1、S2 依 time 升冪、各列含 dkind、對象、time、auditRef 與取代者且沒有入帳指令鈕；面板內沒有刪除類控件", async () => {
    const user = userEvent.setup();
    const P1 = "b2000000-0000-4000-8000-0000000000a1";
    const P2 = "b2000000-0000-4000-8000-0000000000a2";
    renderSi({
      role: "ADMIN",
      username: "admin",
      overrides: {
        "console-writes": () =>
          writesData({
            items: [
              writeItem({ auditRef: AUDIT_S2, kind: "decide", subjectId: "PROP-SI-006", dkind: "promote", digest: DIGEST_X, supersededBy: AUDIT_E, time: "2026-10-31T10:21:00Z" }),
              writeItem({ auditRef: P1, kind: "decide", subjectId: "PROP-SI-004", dkind: "approve", digest: DIGEST_X, time: "2026-10-31T10:00:00Z" }),
              writeItem({ auditRef: AUDIT_E, kind: "decide", subjectId: "PROP-SI-006", dkind: "promote", digest: DIGEST_X, ingested: true, time: "2026-10-31T10:19:51Z" }),
              writeItem({ auditRef: P2, kind: "obs-add", subjectId: null, time: "2026-10-31T10:05:00Z" }),
              writeItem({ auditRef: AUDIT_S, kind: "decide", subjectId: "PROP-SI-006", dkind: "promote", digest: DIGEST_X, supersededBy: AUDIT_E, time: "2026-10-31T10:20:30Z" }),
            ],
          }),
      },
    });
    const panelEl = await screen.findByTestId("si-writes-panel");
    const panel = within(panelEl);

    const pendingList = await panel.findByTestId("si-pending-list");
    expect(Array.from(pendingList.querySelectorAll<HTMLElement>('[data-testid^="si-pending-"]')).map((li) => li.dataset.testid)).toEqual([`si-pending-${P1}`, `si-pending-${P2}`]);
    expect(within(pendingList).queryByTestId(`si-pending-${AUDIT_S}`)).toBeNull();
    expect(within(pendingList).queryByTestId(`si-pending-${AUDIT_S2}`)).toBeNull();
    expect(within(pendingList).getByTestId(`si-dkind-${P1}`)).toHaveTextContent(/核准.*approve/);
    expect(within(pendingList).queryByTestId(`si-dkind-${P2}`), "非 decide 列沒有 dkind 元素").toBeNull();

    const group = panel.getByTestId("si-superseded-list");
    expect(pendingList.compareDocumentPosition(group) & Node.DOCUMENT_POSITION_FOLLOWING, "群組在待入帳清單之後").toBeTruthy();
    const toggle = within(group).getByTestId("si-superseded-toggle");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(toggle, "一審 F-05：展開鈕以 aria-controls 指向它控制的清單（輔助技術靠它找到展開後的內容）").toHaveAttribute("aria-controls", "si-superseded-items");
    expect(toggle.textContent).toBe(SUPERSEDED_TITLE(2));
    expect(within(group).queryByTestId(`si-superseded-${AUDIT_S}`), "預設收合：沒有任何被取代列").toBeNull();
    expect(within(group).queryByTestId(`si-superseded-${AUDIT_S2}`)).toBeNull();

    await user.click(toggle);

    expect(toggle).toHaveAttribute("aria-expanded", "true");
    const controlled = panelEl.querySelector(`#${toggle.getAttribute("aria-controls") ?? "none"}`);
    expect(controlled, "展開後 aria-controls 指向的元素存在").not.toBeNull();
    expect(controlled?.querySelectorAll('li[data-testid^="si-superseded-"]').length, "它就是裝著被取代列的清單").toBe(2);
    expect(
      Array.from(group.querySelectorAll<HTMLElement>('li[data-testid^="si-superseded-"]')).map((li) => li.dataset.testid),
      "依 time 升冪",
    ).toEqual([`si-superseded-${AUDIT_S}`, `si-superseded-${AUDIT_S2}`]);
    for (const [ref, time] of [
      [AUDIT_S, "2026-10-31T10:20:30Z"],
      [AUDIT_S2, "2026-10-31T10:21:00Z"],
    ]) {
      const row = within(group).getByTestId(`si-superseded-${ref}`);
      expect(within(row).getByTestId(`si-dkind-${ref}`)).toHaveTextContent(/晉升.*promote/);
      expect(row).toHaveTextContent("對象：PROP-SI-006");
      expect(row).toHaveTextContent(time);
      expect(row).toHaveTextContent(ref);
      expect(within(row).getByTestId(`si-superseded-by-${ref}`)).toHaveTextContent(`取代者：${AUDIT_E}`);
      expect(within(row).queryAllByRole("button"), "群組列沒有入帳指令鈕或任何按鈕").toEqual([]);
      expect(within(row).queryAllByRole("link")).toEqual([]);
      expect(within(row).queryByRole("button", { name: "入帳指令" })).toBeNull();
    }
    // 對帳面板內（含展開後的群組）所有按鈕與連結：名稱與 testid 都不含刪除、移除、清除、delete、remove
    const controls = Array.from(panelEl.querySelectorAll<HTMLElement>("button, a"));
    expect(controls.length, "防反空轉：面板內確實有按鈕被掃到（兩個待入帳列的入帳指令鈕加群組的展開鈕）").toBe(3);
    for (const el of controls) {
      expect(`${el.getAttribute("aria-label") ?? ""} ${el.textContent ?? ""}`, `按鈕名稱：${el.textContent}`).not.toMatch(FORBIDDEN_NAME);
      expect(el.dataset.testid ?? "", "testid").not.toMatch(FORBIDDEN_NAME);
    }
  });
});

describe("AT_951_4_E_1 對帳量不到時不渲染被取代群組，也不顯示無待入帳", () => {
  it("AT_951_4_E_1 NOT-EVALUABLE（bridge_timeout）：顯示 si-reconcile-ne 與 reason；沒有 si-superseded-list、si-pending-list、si-writes-empty；整頁文字不含已被取代——群組由對帳狀態而非資料控制", async () => {
    renderSi({
      role: "ADMIN",
      username: "admin",
      overrides: {
        "console-writes": () =>
          writesData({
            items: [
              writeItem({ auditRef: AUDIT_A, kind: "decide", dkind: "approve", digest: DIGEST_X, ingested: null }),
              // 契約外輸入：量不到時 supersededBy 本應為 null；刻意給字串，證明不渲染群組是由對帳狀態決定的
              writeItem({ auditRef: AUDIT_S, kind: "decide", dkind: "promote", digest: DIGEST_X, ingested: false, supersededBy: AUDIT_E }),
            ],
            orphans: null,
            reconcile: { status: "NOT-EVALUABLE", reason: "bridge_timeout", backfilled: 0 },
          }),
      },
    });

    const ne = await screen.findByTestId("si-reconcile-ne");

    expect(ne).toHaveTextContent("bridge_timeout");
    expect(screen.queryByTestId("si-superseded-list")).toBeNull();
    expect(screen.queryByTestId("si-pending-list")).toBeNull();
    expect(screen.queryByTestId("si-writes-empty")).toBeNull();
    expect(document.body.textContent ?? "").not.toContain("已被取代");
  });
});

describe("AT_951_4_E_2 被取代筆數不影響無待入帳的判定，orphans 與一般待入帳仍各自生效", () => {
  const supersededRows = [
    writeItem({ auditRef: AUDIT_S, kind: "decide", dkind: "promote", digest: DIGEST_X, supersededBy: AUDIT_E, time: "2026-10-31T10:20:30Z" }),
    writeItem({ auditRef: AUDIT_S2, kind: "decide", dkind: "promote", digest: DIGEST_X, supersededBy: AUDIT_E, time: "2026-10-31T10:21:00Z" }),
    writeItem({ auditRef: AUDIT_S3, kind: "decide", dkind: "promote", digest: DIGEST_X, supersededBy: AUDIT_E, time: "2026-10-31T10:21:26Z" }),
  ];

  it("AT_951_4_E_2 (a) 只有被取代的待入帳列、orphans 為空：顯示無待入帳、沒有 si-pending-list，群組標題為另有 3 筆", async () => {
    renderSi({ role: "ADMIN", username: "admin", overrides: { "console-writes": () => writesData({ items: supersededRows, orphans: [] }) } });
    const panel = within(await screen.findByTestId("si-writes-panel"));
    expect(await panel.findByTestId("si-writes-empty")).toHaveTextContent("無待入帳");
    expect(panel.queryByTestId("si-pending-list")).toBeNull();
    expect(panel.getByTestId("si-superseded-toggle").textContent).toBe(SUPERSEDED_TITLE(3));
  });

  it("AT_951_4_E_2 (b) 同 (a) 但 orphans 有一筆：沒有 si-writes-empty、有 si-write-alerts，群組仍在", async () => {
    renderSi({
      role: "ADMIN",
      username: "admin",
      overrides: { "console-writes": () => writesData({ items: supersededRows, orphans: [{ auditRef: AUDIT_B, kind: "decide", subject: "PROP-SI-004" }] }) },
    });
    const panel = within(await screen.findByTestId("si-writes-panel"));
    expect(await panel.findByTestId("si-write-alerts")).toBeInTheDocument();
    expect(panel.queryByTestId("si-writes-empty")).toBeNull();
    expect(panel.getByTestId("si-superseded-toggle").textContent).toBe(SUPERSEDED_TITLE(3));
  });

  it("AT_951_4_E_2 (c) 一列一般待入帳加兩列被取代的待入帳列、orphans 為空：si-pending-list 恰一列、沒有 si-writes-empty，群組標題為另有 2 筆", async () => {
    renderSi({
      role: "ADMIN",
      username: "admin",
      overrides: { "console-writes": () => writesData({ items: [writeItem({ auditRef: AUDIT_A, kind: "decide", dkind: "approve", digest: DIGEST_X }), ...supersededRows.slice(0, 2)], orphans: [] }) },
    });
    const panel = within(await screen.findByTestId("si-writes-panel"));
    const list = await panel.findByTestId("si-pending-list");
    expect(Array.from(list.querySelectorAll<HTMLElement>('[data-testid^="si-pending-"]')).map((li) => li.dataset.testid)).toEqual([`si-pending-${AUDIT_A}`]);
    expect(panel.queryByTestId("si-writes-empty")).toBeNull();
    expect(panel.getByTestId("si-superseded-toggle").textContent).toBe(SUPERSEDED_TITLE(2));
  });

  // 一審 F-04：(a)～(c) 都至少有一列被取代，分不出「被取代列數為 0 時不渲染群組」與「對帳 ok 就渲染群組」；
  // 沒有任何被取代列時，群組、展開鈕與「已被取代」字樣都不該出現（否則畫面會出現「另有 0 筆已被取代」的空群組）
  it("AT_951_4_E_2 (d) 對帳 ok、只有一般待入帳列、orphans 為空、沒有任何被取代列：沒有 si-superseded-list 與 si-superseded-toggle，面板文字不含已被取代", async () => {
    renderSi({
      role: "ADMIN",
      username: "admin",
      overrides: { "console-writes": () => writesData({ items: [writeItem({ auditRef: AUDIT_A, kind: "decide", dkind: "approve", digest: DIGEST_X })], orphans: [] }) },
    });
    const panelEl = await screen.findByTestId("si-writes-panel");
    const panel = within(panelEl);
    const list = await panel.findByTestId("si-pending-list");
    expect(
      Array.from(list.querySelectorAll<HTMLElement>('[data-testid^="si-pending-"]')).map((li) => li.dataset.testid),
      "防反空轉：一般待入帳列確實渲染",
    ).toEqual([`si-pending-${AUDIT_A}`]);
    expect(panel.queryByTestId("si-superseded-list"), "被取代列數為 0：不渲染群組").toBeNull();
    expect(panel.queryByTestId("si-superseded-toggle"), "也沒有展開鈕").toBeNull();
    expect(panelEl.textContent ?? "", "面板文字不含已被取代").not.toContain("已被取代");
  });
});

// ── TCS-ConsoleUxSortHelp-20261108 AC-963-3（T3～T6 SI 四表；W-UX3、D-UX-17；排序只作用於已載入列） ─────────────────────

describe("AT_963_3 SI 四表：預設 ID／seq 升冪與表頭排序", () => {
  const zh = new Intl.Collator("zh-Hant", { numeric: true });
  const obsRow = (id: string, line: number, patch: Partial<SiObservation>): SiObservation => ({ ...clone(GOLDEN_OBS[0]), id, line, ...patch });
  const obsPage = (items: SiObservationRow[], extra: Record<string, unknown> = {}) => ({ ...clone(GA.observations), items, truncated: false, nextSince: null, ...extra });
  const headerOf = (root: HTMLElement, name: string) => within(root).getByRole("columnheader", { name });
  const pressIn = async (user: ReturnType<typeof userEvent.setup>, root: HTMLElement, name: string) => user.click(within(headerOf(root, name)).getByRole("button", { name }));
  const idsByTestId = (root: HTMLElement, prefix: string) =>
    Array.from(root.querySelectorAll<HTMLElement>(`[data-testid^="${prefix}"]`)).map((el) => (el.dataset.testid as string).replace(prefix, ""));
  /** 依某欄值排好的 ID（空值最後，同值依 ID 升冪）。 */
  const expectIds = (rows: Array<{ id: string; v: string }>, dir: "asc" | "desc") =>
    [...rows].sort((a, b) => (dir === "asc" ? zh.compare(a.v, b.v) : zh.compare(b.v, a.v)) || zh.compare(a.id, b.id)).map((r) => r.id);

  const CRAFTED = [
    obsRow("OBS-SI-003", 3, { time: "2025-12-31 23:00", category: "a", severity: "中", disposition: "deferred", symptom: "乙" }),
    obsRow("OBS-SI-001", 1, { time: "2026-01-31 23:59", category: "b", severity: "高", disposition: "open", symptom: "丙" }),
    obsRow("OBS-SI-004", 4, { time: "2026-12-01 00:00", category: "a", severity: "緊急", disposition: "adopted", symptom: "丁" }),
    obsRow("OBS-SI-002", 2, { time: "2026-02-01 00:01", category: "c", severity: "低", disposition: "closed", symptom: "甲" }),
  ];

  it("AT_963_3_5 觀察表：預設 ID 升冪（ID 欄 ascending）；第一次點 ID 即降冪；五欄各依語意排；時間跨月跨年依時刻；壞列恆在有效列之後；操作欄無按鈕；展開列排序後仍是同一列", async () => {
    const user = userEvent.setup();
    // 兩個壞列、輸入序 line 降冪（30 在 20 前）：壞列恆在全部有效列之後、彼此依 line 升冪，升降冪相同
    const invalidHi = { ...clone(BAD)!, line: 30 } as SiObservationRow;
    const invalidLo = { ...clone(BAD)!, line: 20 } as SiObservationRow;
    // API 序刻意亂排，壞列夾在中間
    renderSi({ overrides: { observations: serve(obsPage([CRAFTED[0], CRAFTED[1], invalidHi, CRAFTED[2], invalidLo, CRAFTED[3]])) } });
    await waitForObservations();
    const obs = panel("observations");
    const invalidTids = ["si-obs-invalid-20", "si-obs-invalid-30"];
    expect(obsOrder(obs)).toEqual(["si-obs-row-OBS-SI-001", "si-obs-row-OBS-SI-002", "si-obs-row-OBS-SI-003", "si-obs-row-OBS-SI-004", ...invalidTids]);
    expect(headerOf(obs, "ID")).toHaveAttribute("aria-sort", "ascending");
    // 操作欄（sr-only 動作欄）沒有按鈕、沒有 aria-sort
    const heads = within(obs).getAllByRole("columnheader");
    expect(heads[0].querySelector("button")).toBeNull();
    expect(heads[0].hasAttribute("aria-sort")).toBe(false);

    await pressIn(user, obs, "ID");
    expect(headerOf(obs, "ID")).toHaveAttribute("aria-sort", "descending");
    expect(obsOrder(obs)).toEqual(["si-obs-row-OBS-SI-004", "si-obs-row-OBS-SI-003", "si-obs-row-OBS-SI-002", "si-obs-row-OBS-SI-001", ...invalidTids]);

    // 時間：跨年、跨月依時刻（003 的 2025-12 在 001 的 2026-01 之前）
    await pressIn(user, obs, "時間");
    expect(validRowIds(obs)).toEqual(["OBS-SI-003", "OBS-SI-001", "OBS-SI-002", "OBS-SI-004"]);
    expect(obsOrder(obs).slice(-2)).toEqual(invalidTids);
    await pressIn(user, obs, "時間");
    expect(validRowIds(obs)).toEqual(["OBS-SI-004", "OBS-SI-002", "OBS-SI-001", "OBS-SI-003"]);
    expect(obsOrder(obs).slice(-2)).toEqual(invalidTids);

    for (const [name, field] of [
      ["分類", "category"],
      ["嚴重度", "severity"],
      ["處置", "disposition"],
      ["症狀", "symptom"],
    ] as const) {
      await pressIn(user, obs, name);
      const rows = CRAFTED.map((r) => ({ id: r.id, v: r[field] }));
      expect(validRowIds(obs), `${name} 升冪`).toEqual(expectIds(rows, "asc"));
      expect(obsOrder(obs).slice(-2)).toEqual(invalidTids);
      await pressIn(user, obs, name);
      expect(validRowIds(obs), `${name} 降冪`).toEqual(expectIds(rows, "desc"));
      expect(obsOrder(obs).slice(-2)).toEqual(invalidTids);
    }

    // 展開 OBS-SI-003 後排序：展開的仍是同一列
    await user.click(within(obs).getByRole("button", { name: "展開 OBS-SI-003" }));
    expect(within(obs).getByTestId("si-obs-fields-OBS-SI-003")).toBeInTheDocument();
    await pressIn(user, obs, "時間");
    expect(within(obs).getByTestId("si-obs-fields-OBS-SI-003")).toBeInTheDocument();
    expect(within(obs).queryByTestId("si-obs-fields-OBS-SI-001")).toBeNull();
    expect(within(within(obs).getByTestId("si-obs-row-OBS-SI-003")).getByRole("button", { name: /OBS-SI-003/ })).toHaveAttribute("aria-expanded", "true");
  });

  it("AT_963_3_E_2 觀察表載入更多：新列併入後依目前排序重排（時間降冪下新列不接尾）；預設序下新列自然接尾", async () => {
    limits.value = 5;
    const user = userEvent.setup();
    const t = (day: number) => `2026-03-0${day} 08:00`;
    const page1 = [1, 2, 3, 4, 5].map((n) => obsRow("OBS-SI-" + `00${n}`, n, { time: t(n * 2 - 1) })); // 03-01、03-03、03-05、03-07、03-09（前綴與數字分開寫：根層 si check 會把「前綴接數字」的字面當帳本引用）
    const page2 = [obsRow("OBS-SI-006", 6, { time: t(4) }), obsRow("OBS-SI-007", 7, { time: t(8) })];
    renderSi({
      overrides: {
        observations: (call) => ({ data: call.query.get("since") === "5" ? obsPage(page2) : obsPage(page1, { truncated: true, nextSince: 5 }) }),
      },
    });
    await screen.findByRole("tab", { name: "觀察 (5+)" });
    const obs = panel("observations");
    await pressIn(user, obs, "時間");
    await pressIn(user, obs, "時間"); // 降冪
    expect(validRowIds(obs)).toEqual(["OBS-SI-005", "OBS-SI-004", "OBS-SI-003", "OBS-SI-002", "OBS-SI-001"]);
    await user.click(screen.getByRole("button", { name: "載入更多" }));
    await screen.findByRole("tab", { name: "觀察 (7)" });
    // 新列 006（03-04）、007（03-08）依時間降冪插入既有列之間，而不是接在尾端
    expect(validRowIds(obs)).toEqual(["OBS-SI-005", "OBS-SI-007", "OBS-SI-004", "OBS-SI-003", "OBS-SI-006", "OBS-SI-002", "OBS-SI-001"]);
  });

  it("AT_963_3_E_2 預設序下新列自然接尾（ID 升冪與游標序一致）", async () => {
    limits.value = 5;
    const user = userEvent.setup();
    const page1 = [1, 2, 3, 4, 5].map((n) => obsRow("OBS-SI-" + `00${n}`, n, {}));
    const page2 = [obsRow("OBS-SI-006", 6, {}), obsRow("OBS-SI-007", 7, {})];
    renderSi({ overrides: { observations: (call) => ({ data: call.query.get("since") === "5" ? obsPage(page2) : obsPage(page1, { truncated: true, nextSince: 5 }) }) } });
    await screen.findByRole("tab", { name: "觀察 (5+)" });
    await user.click(screen.getByRole("button", { name: "載入更多" }));
    await screen.findByRole("tab", { name: "觀察 (7)" });
    expect(validRowIds(panel("observations"))).toEqual(["OBS-SI-001", "OBS-SI-002", "OBS-SI-003", "OBS-SI-004", "OBS-SI-005", "OBS-SI-006", "OBS-SI-007"]);
  });

  it("AT_963_3_6 提案表：預設 ID 自然序升冪；rev 依數字（9 < 10 < 100）；digest、verdict、cooldown、狀態、類別、route 依文字；操作欄無按鈕", async () => {
    const user = userEvent.setup();
    const mk = (id: string, patch: Partial<SiProposal>) => proposalOf({ id, card: null, ...patch });
    const items = [
      mk("PX-10", { state: "zz", cls: "b", route: "r2", rev: 10, digest: "bbbb1111", verdict: "v3", cooldown: "c2" }),
      mk("PX-100", { state: "mm", cls: "a", route: "r3", rev: 100, digest: "aaaa2222", verdict: "v1", cooldown: "c3" }),
      mk("PX-9", { state: "aa", cls: "c", route: "r1", rev: 9, digest: "cccc3333", verdict: "v2", cooldown: "c1" }),
    ];
    renderSi({ overrides: { proposals: serve({ ...clone(GA.proposals), items, truncated: false, nextSince: null }) } });
    await user.click(tabButton(/提案/));
    const root = await screen.findByTestId("si-prop-table");
    const ids = () => idsByTestId(root, "si-prop-row-");
    expect(ids()).toEqual(["PX-9", "PX-10", "PX-100"]);
    expect(headerOf(root, "ID")).toHaveAttribute("aria-sort", "ascending");
    expect(within(root).getAllByRole("columnheader")[0].querySelector("button")).toBeNull();
    await pressIn(user, root, "rev");
    expect(ids()).toEqual(["PX-9", "PX-10", "PX-100"]);
    await pressIn(user, root, "rev");
    expect(ids()).toEqual(["PX-100", "PX-10", "PX-9"]);
    const text = (name: string, field: keyof SiProposal) => items.map((p) => ({ id: p.id, v: String(p[field]) }));
    for (const [name, field] of [
      ["狀態", "state"],
      ["類別", "cls"],
      ["route", "route"],
      ["digest", "digest"],
      ["verdict", "verdict"],
      ["cooldown", "cooldown"],
    ] as const) {
      await pressIn(user, root, name);
      expect(ids(), `${name} 升冪`).toEqual(expectIds(text(name, field), "asc"));
      await pressIn(user, root, name);
      expect(ids(), `${name} 降冪`).toEqual(expectIds(text(name, field), "desc"));
    }
  });

  it("AT_963_3_7／3_8 事件表與運轉表：預設 seq／ID 升冪（9 在 10 前）；t 依時刻；closedSeq 空值兩個方向都在最後；操作欄無按鈕", async () => {
    const user = userEvent.setup();
    const events: SiEvent[] = [
      { seq: 10, t: "2026-02-01T00:00:00Z", kind: "b", by: "y" },
      { seq: 9, t: "2026-03-01T00:00:00Z", kind: "c", by: "x" },
      { seq: 100, t: "2026-01-01T00:00:00Z", kind: "a", by: "z" },
      // kind 相同的兩列、輸入序 seq 大者在前：同值時兩個方向都依 seq 升冪（tie-break＝seq）
      { seq: 51, t: "2026-04-01T00:00:00Z", kind: "d", by: "w" },
      { seq: 50, t: "2026-04-02T00:00:00Z", kind: "d", by: "v" },
    ];
    const run = (
      id: string,
      openedSeq: number,
      closedSeq: number | null,
      trigger: string,
      extra: { outcome?: Record<string, string>; propIds?: string[]; research?: { kind: string; seq: number } | null } = {},
    ) => ({
      id,
      openedSeq,
      closedSeq,
      trigger,
      headSha: null,
      research: extra.research ?? null,
      propIds: extra.propIds ?? ([] as string[]),
      outcome: extra.outcome ?? ({} as Record<string, string>),
    });
    // outcome、propIds、research 三欄的值刻意讓三種排序結果彼此不同；RX-5 的 outcome 與 propIds 為空、RX-100 的 research 為空（空值兩個方向都在最後）
    const runs = [
      run("RX-10", 5, null, "t2", { outcome: { "PX-1": "b-state" }, propIds: ["PX-3"], research: { kind: "c", seq: 1 } }),
      run("RX-9", 3, 7, "t1", { outcome: { "PX-1": "c-state" }, propIds: ["PX-1"], research: { kind: "a", seq: 2 } }),
      run("RX-100", 4, 6, "t3", { outcome: { "PX-1": "a-state" }, propIds: ["PX-2"] }),
      run("RX-5", 1, null, "t4", { research: { kind: "b", seq: 3 } }),
    ];
    renderSi({
      overrides: {
        events: serve({ ...clone(GA.events), items: events, truncated: false, nextSince: null }),
        runs: serve({ ...clone(GA.runs), items: runs, truncated: false, nextSince: null }),
      },
    });
    await user.click(tabButton(/事件/));
    const evRoot = await screen.findByTestId("si-events-table");
    const runRoot = await screen.findByTestId("si-runs-table");
    const evIds = () => idsByTestId(evRoot, "si-event-row-");
    const runIds = () => idsByTestId(runRoot, "si-run-row-");

    expect(evIds()).toEqual(["9", "10", "50", "51", "100"]);
    expect(headerOf(evRoot, "seq")).toHaveAttribute("aria-sort", "ascending");
    expect(within(evRoot).getAllByRole("columnheader")[0].querySelector("button")).toBeNull();
    await pressIn(user, evRoot, "t");
    expect(evIds()).toEqual(["100", "10", "9", "51", "50"]);
    await pressIn(user, evRoot, "kind");
    expect(evIds()).toEqual(["100", "10", "9", "50", "51"]); // kind 相同的 50、51：依 seq 升冪
    await pressIn(user, evRoot, "kind");
    expect(evIds()).toEqual(["50", "51", "9", "10", "100"]); // 降冪時同值兩列仍依 seq 升冪
    await pressIn(user, evRoot, "by");
    expect(evIds()).toEqual(["50", "51", "9", "10", "100"]);
    await pressIn(user, evRoot, "by");
    expect(evIds()).toEqual(["100", "10", "9", "51", "50"]);

    expect(runIds()).toEqual(["RX-5", "RX-9", "RX-10", "RX-100"]);
    expect(headerOf(runRoot, "ID")).toHaveAttribute("aria-sort", "ascending");
    await pressIn(user, runRoot, "closedSeq");
    expect(runIds()).toEqual(["RX-100", "RX-9", "RX-5", "RX-10"]);
    await pressIn(user, runRoot, "closedSeq");
    expect(runIds()).toEqual(["RX-9", "RX-100", "RX-5", "RX-10"]);
    await pressIn(user, runRoot, "openedSeq");
    expect(runIds()).toEqual(["RX-5", "RX-9", "RX-100", "RX-10"]);
    await pressIn(user, runRoot, "trigger");
    expect(runIds()).toEqual(["RX-9", "RX-10", "RX-100", "RX-5"]);
    await pressIn(user, runRoot, "outcome");
    expect(runIds()).toEqual(["RX-100", "RX-10", "RX-9", "RX-5"]); // a-state、b-state、c-state、空值最後
    await pressIn(user, runRoot, "outcome");
    expect(runIds()).toEqual(["RX-9", "RX-10", "RX-100", "RX-5"]); // 降冪，空值仍最後
    await pressIn(user, runRoot, "propIds");
    expect(runIds()).toEqual(["RX-9", "RX-100", "RX-10", "RX-5"]); // PX-1、PX-2、PX-3、空值最後
    await pressIn(user, runRoot, "propIds");
    expect(runIds()).toEqual(["RX-10", "RX-100", "RX-9", "RX-5"]);
    await pressIn(user, runRoot, "research");
    expect(runIds()).toEqual(["RX-9", "RX-5", "RX-10", "RX-100"]); // a #2、b #3、c #1、空值最後
    await pressIn(user, runRoot, "research");
    expect(runIds()).toEqual(["RX-10", "RX-5", "RX-9", "RX-100"]);
  });
});

// ── 自動演化排程的橫幅欄位組（P4；TCS-SelfImprovingSchedule AT-964-1-3、1-E-2；W-S1 (d)(e)）──────────────────────

describe("AT_964_1_3 SI_STATUS_KNOWN_KEYS 含 schedule：不再列入其他欄位，其餘未知鍵仍列入", () => {
  it("AT_964_1_3 status 帶 schedule 與虛構未知鍵 futureKey：其他欄位區含 futureKey、不含 schedule；已知鍵含 schedule 且既有九鍵一個不少", async () => {
    renderSi({ fixture: fixtureWithStatus(statusItem({ schedule: sched(), extra: { futureKey: { a: 1 } } })) });
    const banner = await screen.findByTestId("si-status-banner");
    const extra = await within(banner).findByTestId("si-status-extra");
    expect(extra.textContent).toContain("futureKey");
    expect(extra.querySelector('[data-status-key="schedule"]'), "schedule 不在其他欄位區").toBeNull();
    expect(extra.textContent).not.toContain("schedule：");
    // schedule 仍有自己的可見位置（具名欄位組）
    expect(banner.querySelector('[data-status-key="schedule"]')).not.toBeNull();
    expect([...SI_STATUS_KNOWN_KEYS]).toEqual(
      expect.arrayContaining(["eventsDetected", "unavailable", "openRuns", "pendingProps", "suspended", "cooldowns", "skipReasons", "capacity", "frictionReconcile", "schedule"]),
    );
  });
});

describe("AT_964_1_E_2 schedule 整鍵缺席：整組量不到，橫幅其餘欄位不受影響", () => {
  it("AT_964_1_E_2 status 不含 schedule：排程欄位組每個欄位皆量不到；橫幅其餘具名欄位與缺席前（含 schedule 時）逐字相同；頁面不丟例外、不空白", async () => {
    const withSchedule = renderSi({ fixture: fixtureWithStatus(statusItem({ schedule: sched() })) });
    const bannerWith = await screen.findByTestId("si-status-banner");
    await within(bannerWith).findByTestId("si-schedule-fields-banner");
    const otherKeys = ["eventsDetected", "unavailable", "openRuns", "pendingProps", "suspended", "cooldowns", "skipReasons", "capacity", "frictionReconcile"];
    const before = otherKeys.map((k) => textOf(bannerWith.querySelector(`[data-status-key="${k}"]`) as HTMLElement));
    withSchedule.unmount();

    renderSi({ fixture: fixtureWithStatus(statusItem()) });
    const banner = await screen.findByTestId("si-status-banner");
    const group = await within(banner).findByTestId("si-schedule-fields-banner");
    const values = Array.from(group.querySelectorAll<HTMLElement>("[data-schedule-field]"));
    expect(values.length).toBeGreaterThanOrEqual(8);
    for (const el of values) expect(textOf(el.querySelector("dd") as HTMLElement), `欄位 ${el.dataset.scheduleField}`).toMatch(/^量不到/);
    expect(within(group).queryAllByRole("alert")).toHaveLength(0);
    const after = otherKeys.map((k) => textOf(banner.querySelector(`[data-status-key="${k}"]`) as HTMLElement));
    expect(after, "橫幅其餘欄位不受影響").toEqual(before);
    expect(textOf(banner).trim().length).toBeGreaterThan(0);
  });
});
