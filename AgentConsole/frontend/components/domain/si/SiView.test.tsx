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
import type { SiEvent, SiObservation, SiObservationRow, SiProposal } from "@/lib/api/types";
import { GA, GB, clone, renderSi, signInAs, siUnavailable, stubSiApi, type SiStub } from "@/tests/helpers/si";
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
    renderSi();
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

    // 模組桶：狀態 A 沒有 buckets 欄 → 停用、說明，選項只有「全部」；證據含 AutoClaude/ 路徑的列不被歸桶
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
    expect(afterOrder.slice(0, 12)).toEqual(beforeOrder);
    expect(afterOrder[12]).toBe("si-obs-row-OBS-SI-013");
    expect(afterOrder.slice(0, 12).map((t) => textOf(within(obs).getByTestId(t)))).toEqual(beforeTexts);
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
