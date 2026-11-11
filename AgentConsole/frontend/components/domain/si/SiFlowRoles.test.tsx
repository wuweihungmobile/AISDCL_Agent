/**
 * 角色一視同仁與零寫入（TCS-SiFlowVisibility AC-966-14、15：AT-966-14-1～14-3、14-E-1、15-E-1）。
 * 整個 SiView 以 renderFlow 渲染（真 Providers＋fetch 替身）；請求集合取自 fetch 替身的呼叫紀錄。
 */
import { cleanup, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import { failure } from "@/tests/helpers/api";
import { ADMIN_UI, OPERATOR_UI, VIEWER_UI } from "@/tests/helpers/si";
import { LAYOUT_BRANCH_CODES } from "@/lib/domain/siFlow";
import { DETAIL, NOW, PATROL, openDetail, proposalResponse, renderFlow } from "@/tests/helpers/siFlow";

vi.setConfig({ testTimeout: 120_000 });
const router = vi.hoisted(() => ({ push: () => undefined, replace: () => undefined, back: () => undefined }));
vi.mock("next/navigation", () => ({ usePathname: () => "/self-improving", useRouter: () => router, useSearchParams: () => new URLSearchParams(), useParams: () => ({}) }));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const text = (el: HTMLElement) => el.textContent ?? "";
const TABS = ["卡面", "變更內容", "提案本文", "評估集與驗證", "時間線"];
const bigPatch = Array.from({ length: 1000 }, (_, i) => `+行${i}`).join("\n");

describe("AT_966_14_1 VIEWER 與 OPERATOR 完整旅程", () => {
  it.each([
    ["VIEWER", VIEWER_UI],
    ["OPERATOR", OPERATOR_UI],
  ])("%s：請求只有五種唯讀 GET，零寫入、零對帳請求，沒有寫入控件", async (role, ui) => {
    const user = userEvent.setup({ delay: null });
    const downloads: string[] = [];
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: () => "blob:test", revokeObjectURL: () => undefined }));
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      downloads.push(this.download);
    });
    const detail = DETAIL({ patch: { rel: "docs/x/r2.patch", bytes: 9000, text: bigPatch, truncated: false } });
    const { stub } = renderFlow({ ...ui, proposal: () => ({ data: proposalResponse({ detail }) }) });
    const card = await screen.findByTestId("si-patrol-card");
    expect(card).toBeInTheDocument();
    const dialog = await openDetail(user);
    await within(dialog).findByTestId("si-next-step");
    for (const name of TABS.slice(1)) await user.click(within(dialog).getByRole("tab", { name }));
    await user.click(within(dialog).getByRole("tab", { name: "變更內容" }));
    await user.click(within(dialog).getByRole("button", { name: /展開全部/ }));
    await user.click(within(dialog).getByRole("button", { name: "下載 patch 檔" }));
    expect(downloads).toEqual(["PROP-SI-901-r2.patch"]);
    await user.click(within(dialog).getByRole("tab", { name: "時間線" }));
    await user.click(within(dialog).getByRole("tab", { name: "提案本文" }));
    await user.click(within(dialog).getByRole("button", { name: "看觀察 OBS-SI-050" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await user.click(screen.getByTestId("si-refresh"));
    await screen.findByTestId("si-obs-row-OBS-SI-050");

    const paths = new Set(stub.calls.map((c) => c.path.replace(/PROP-SI-\d+/, "{id}")));
    const allowed = new Set(["/api/v1/si/status", "/api/v1/si/observations", "/api/v1/si/proposals", "/api/v1/si/proposals/{id}", "/api/v1/si/patrol"]);
    for (const p of paths) expect(allowed.has(p), `${role} 多出的請求 ${p}`).toBe(true);
    expect(stub.calls.filter((c) => c.method !== "GET")).toEqual([]);
    expect(stub.calls.filter((c) => c.path.includes("console-writes") || c.path.includes("/issues"))).toEqual([]);
    expect(
      document.querySelectorAll("[data-testid^='si-decide-open-'], [data-testid='si-obs-new'], [data-testid^='si-obs-correct-'], [data-testid^='si-close-open-'], [data-testid='si-writes-panel']"),
    ).toHaveLength(0);
    expect(
      within(card)
        .getAllByRole("button")
        .every((b) => b.dataset.testid === "si-patrol-steps-toggle"),
    ).toBe(true);
  });
});

describe("AT_966_14_2 ADMIN 既有流程回歸", () => {
  it("決定流程與收據不變、詳情對話框沒有寫入鈕、寫入成功後 patrol 查詢也被重取", async () => {
    const user = userEvent.setup({ delay: null });
    const { stub } = renderFlow(ADMIN_UI);
    await screen.findByTestId("si-patrol-card");
    await user.click(screen.getByRole("tab", { name: /提案/ }));
    await user.click(await screen.findByTestId("si-decide-open-PROP-SI-901"));
    const decide = await screen.findByTestId("si-decide-dialog");
    await user.selectOptions(within(decide).getByTestId("si-decide-verb"), "promote");
    const patrolBefore = stub.calls.filter((c) => c.path === "/api/v1/si/patrol").length;
    await user.click(within(decide).getByTestId("si-decide-submit"));
    const result = await within(decide).findByTestId("si-decide-result");
    expect(result).toHaveTextContent("稽核檔已落地，待入帳");
    expect(stub.calls.filter((c) => c.method === "POST")).toHaveLength(1);
    await waitFor(() => expect(stub.calls.filter((c) => c.path === "/api/v1/si/patrol").length).toBeGreaterThan(patrolBefore));
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("si-decide-dialog")).toBeNull());
    await user.click(await screen.findByTestId("si-detail-open-PROP-SI-901"));
    const detail = await screen.findByRole("dialog", { name: "提案詳情 PROP-SI-901" });
    await within(detail).findByTestId("si-next-step");
    expect(
      within(detail)
        .queryAllByRole("button")
        .map((b) => b.textContent ?? ""),
    ).not.toContainEqual(expect.stringMatching(/決定|核准|晉升|送出/));
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });
});

describe("AT_966_14_3 新元件靜態無寫入引用", () => {
  const root = process.cwd();
  const read = (rel: string) => readFileSync(path.join(root, rel), "utf-8");
  it("不 import 寫入 hook 與 fetch、不含表單控件；siFlow.ts 是純函式庫", () => {
    for (const rel of ["components/domain/si/SiProposalDetail.tsx", "components/domain/si/SiDiffView.tsx", "components/domain/si/SiPatrolCard.tsx", "lib/domain/siFlow.ts"]) {
      const src = read(rel);
      expect(src, rel).not.toMatch(/\busePost\w*|\buseWrite\w*|\bpostSi\w*|\buseSi(Decide|AddObservation|CloseObservation|ValidateObservation)\b/);
      expect(src, rel).not.toMatch(/\bfetch\s*\(|XMLHttpRequest/);
      expect(src, rel).not.toMatch(/<form|<input|<textarea|type="submit"/);
    }
    const flow = read("lib/domain/siFlow.ts");
    expect(flow).not.toMatch(/from\s+["']react["']|from\s+["']@\/lib\/api\//);
  });
});

describe("AT_966_14_3 原因碼字面只准版面分支鍵（TCS 勘誤 E-20）", () => {
  // 原因碼形字面：全大寫字母段以連字號相連（至少兩段、首段 ≥ 3 字母）。排除：帳本編號前綴（OBS-SI 等）、既有的量不到狀態字 NOT-EVALUABLE；
  // 規格編號（AC-、AT-、W-F、NFR-；NFR- 字首另行排除）、UTF-8、SHA-256 與 data-testid 值（小寫）本來就不符合這個形態
  const CODE_LIKE = /\b[A-Z]{3,}(?:-[A-Z]{2,})+\b/g;
  const LEDGER_PREFIX = /^(OBS|PROP|APP|DEC|RUN|ATT)-SI$/;
  const SPEC_ID = /^NFR-/;
  const FILES = [
    "components/domain/si/SiProposalDetail.tsx",
    "components/domain/si/SiDiffView.tsx",
    "components/domain/si/SiPatrolCard.tsx",
    "components/domain/si/SiWritesPanel.tsx",
    "lib/domain/siFlow.ts",
  ];
  it("LAYOUT_BRANCH_CODES 恰兩個；五支原始碼的原因碼形字面只有這兩個", () => {
    expect([...LAYOUT_BRANCH_CODES]).toEqual(["OBS-LEDGER-UNREADABLE", "TIMELINE-TRUNCATED"]);
    expect(LAYOUT_BRANCH_CODES).toHaveLength(2);
    const allowed = new Set<string>(LAYOUT_BRANCH_CODES);
    for (const rel of FILES) {
      const hits = (readFileSync(path.join(process.cwd(), rel), "utf-8").match(CODE_LIKE) ?? []).filter((h) => !LEDGER_PREFIX.test(h) && !SPEC_ID.test(h) && h !== "NOT-EVALUABLE");
      const extra = hits.filter((h) => !allowed.has(h));
      expect(extra, `${rel} 出現不在版面分支鍵內的原因碼字面`).toEqual([]);
    }
    // 版面分支只在 SiProposalDetail 以常數引用，不再寫字面
    expect(readFileSync(path.join(process.cwd(), "components/domain/si/SiProposalDetail.tsx"), "utf-8")).not.toMatch(/OBS-LEDGER-UNREADABLE|TIMELINE-TRUNCATED/);
  });
});
describe("AT_966_14_E_1 角色一視同仁與 401", () => {
  it("三角色的詳情與巡邏卡文字逐字相同", async () => {
    const seen: Array<{ role: string; card: string; dialog: string }> = [];
    for (const [role, ui] of [
      ["VIEWER", VIEWER_UI],
      ["OPERATOR", OPERATOR_UI],
      ["ADMIN", ADMIN_UI],
    ] as const) {
      const user = userEvent.setup({ delay: null });
      renderFlow(ui);
      const card = await screen.findByTestId("si-patrol-card");
      await waitFor(() => expect(text(card)).toContain("上次心跳"));
      const dialog = await openDetail(user);
      await within(dialog).findByTestId("si-next-step");
      let all = "";
      for (const name of TABS) {
        await user.click(within(dialog).getByRole("tab", { name }));
        all += text(dialog);
      }
      seen.push({ role, card: text(card), dialog: all });
      cleanup();
    }
    expect(seen[1].card).toBe(seen[0].card);
    expect(seen[2].card).toBe(seen[0].card);
    expect(seen[1].dialog).toBe(seen[0].dialog);
    expect(seen[2].dialog).toBe(seen[0].dialog);
  });
  it("401 不顯示技術字樣、不丟例外（交給全域處理）", async () => {
    const user = userEvent.setup({ delay: null });
    renderFlow({ ...VIEWER_UI, patrol: () => failure(401, { message: "請重新登入", reason: "unauthorized" }), proposal: () => failure(401, { message: "請重新登入", reason: "unauthorized" }) });
    const card = await screen.findByTestId("si-patrol-card");
    await waitFor(() => expect(card.querySelector("[data-testid='si-loading']")).toBeNull());
    expect(text(card)).not.toMatch(/\bnull\b|undefined|NaN|\[object Object\]/);
    await user.click(screen.getByRole("tab", { name: /提案/ }));
    await user.click(await screen.findByTestId("si-detail-open-PROP-SI-901"));
    const dialog = await screen.findByRole("dialog");
    await waitFor(() => expect(dialog.querySelector("[data-testid='si-loading']")).toBeNull());
    expect(text(dialog)).not.toMatch(/\bnull\b|undefined|NaN|\[object Object\]/);
  });
});

// ── 垃圾輸入：固定種子的偽亂數（mulberry32）──────────────────────────────────────────────────────────────
function rngOf(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const GARBAGE: Array<() => unknown> = [() => null, () => undefined, () => 7, () => true, () => ({}), () => [], () => "超長".repeat(3000), () => Number.NaN, () => ({ a: 1 }), () => [1, "x"]];
/** 隨機把任一欄位換成垃圾值（遞迴；undefined＝刪鍵）。 */
function corrupt(value: unknown, rng: () => number, rate: number): unknown {
  if (Array.isArray(value)) return value.map((v) => corrupt(v, rng, rate));
  if (typeof value !== "object" || value === null) return value;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
    if (rng() < rate) {
      const g = GARBAGE[Math.floor(rng() * GARBAGE.length)]();
      if (g !== undefined) out[k] = g;
    } else out[k] = corrupt(v, rng, rate);
  }
  return out;
}

describe("AT_966_15_E_1 垃圾輸入不洩漏技術字樣", () => {
  it("固定種子 966 的 50 組垃圾快照與詳情：不丟例外、可見文字沒有 null／undefined／NaN／[object Object]／Invalid Date", async () => {
    const rng = rngOf(966);
    const BAD = /\bnull\b|\bundefined\b|NaN|\[object Object\]|Invalid Date/;
    for (let i = 0; i < 50; i += 1) {
      const user = userEvent.setup({ delay: null });
      const patrol = corrupt(PATROL(), rng, 0.2) as Record<string, unknown>;
      const detail = corrupt(DETAIL(), rng, 0.2) as Record<string, unknown>;
      renderFlow({ ...VIEWER_UI, patrol: () => ({ data: patrol }), proposal: () => ({ data: proposalResponse({ detail }) }) });
      const card = await screen.findByTestId("si-patrol-card");
      await waitFor(() => expect(card.querySelector("[data-testid='si-loading']")).toBeNull());
      const dialog = await openDetail(user);
      await waitFor(() => expect(dialog.querySelector("[data-testid='si-loading']")).toBeNull());
      let seen = text(card);
      for (const name of TABS) {
        await user.click(within(dialog).getByRole("tab", { name }));
        seen += text(dialog);
      }
      expect(seen, `第 ${i} 組垃圾輸入`).not.toMatch(BAD);
      cleanup();
    }
    expect(NOW).toBeTruthy();
  });
});
