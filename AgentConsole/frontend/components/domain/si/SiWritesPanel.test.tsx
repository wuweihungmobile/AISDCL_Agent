/**
 * 待入帳面板的入帳結果（TCS-SiFlowVisibility AC-966-13：AT-966-13-1～13-6、13-E-1、13-E-2）。
 * ADMIN 才有這個面板：整個 SiView 以 renderFlow 渲染；對帳資料（console-writes）與巡邏快照（patrol）各自以 overrides 給。
 * 入帳結果以前端結合：用稽核編號對照快照 `ingest[]`，只結合未入帳的列。
 */
import { cleanup, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { failure } from "@/tests/helpers/api";
import { ADMIN_UI, siUnavailable, writeItem } from "@/tests/helpers/si";
import { PATROL, iso, renderFlow, type FlowOptions } from "@/tests/helpers/siFlow";

vi.setConfig({ testTimeout: 30_000 });
const router = vi.hoisted(() => ({ push: () => undefined, replace: () => undefined, back: () => undefined }));
vi.mock("next/navigation", () => ({ usePathname: () => "/self-improving", useRouter: () => router, useSearchParams: () => new URLSearchParams(), useParams: () => ({}) }));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const A = (n: number) => `a1000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const text = (el: HTMLElement) => el.textContent ?? "";
const ing = (over: Record<string, unknown>) => ({
  auditRef: A(1),
  kind: "decide",
  status: "rejected",
  code: "STALE-CARD",
  text: "提案卡面已更新，你按的是舊卡面；請看新卡面重新決定",
  permanent: true,
  ...over,
});
type Writes = { items: ReturnType<typeof writeItem>[]; reconcile?: Record<string, unknown> };
const writes = (w: Writes) => () => ({ data: { items: w.items, truncated: false, orphans: [], reconcile: w.reconcile ?? { status: "ok", reason: null, backfilled: 0 } } });
const pending = (n: number, over: Partial<Parameters<typeof writeItem>[0]> = {}) => writeItem({ auditRef: A(n), kind: "decide", dkind: "promote", ingested: false, ...over });

async function panel(opts: { items: ReturnType<typeof writeItem>[]; reconcile?: Record<string, unknown>; patrol?: FlowOptions["patrol"] }) {
  const view = renderFlow({ ...ADMIN_UI, patrol: opts.patrol, overrides: { "console-writes": writes({ items: opts.items, reconcile: opts.reconcile }) } });
  const el = await screen.findByTestId("si-writes-panel");
  await waitFor(() => expect(el.querySelector("[data-testid='si-loading']")).toBeNull());
  // 巡邏回報是另一個查詢：等它落定（成功或失敗）再斷言
  await waitFor(() => expect(view.stub.calls.some((c) => c.path === "/api/v1/si/patrol")).toBe(true));
  await new Promise((r) => setTimeout(r, 50));
  return { el, ...view };
}
const row = (el: HTMLElement, n: number) => within(el).getByTestId(`si-pending-${A(n)}`);

describe("AT_966_13_1 永久拒收", () => {
  it("待入帳列另有被拒收標籤、原因碼、白話原因與需要人處理句；仍保有入帳指令鈕", async () => {
    const { el } = await panel({ items: [pending(1)], patrol: () => ({ data: PATROL({ ingest: [ing({})] }) }) });
    const r = row(el, 1);
    expect(r).toHaveTextContent("待入帳");
    expect(r).toHaveTextContent("被拒收");
    expect(r).toHaveTextContent("STALE-CARD");
    expect(r).toHaveTextContent("提案卡面已更新，你按的是舊卡面；請看新卡面重新決定");
    expect(r).toHaveTextContent("需要人處理：這筆不會自動入帳。請看最新卡面後重新送出決定；目前畫面沒有取消功能，這筆會留在清單。");
    expect(within(r).getByRole("button", { name: "入帳指令" })).toBeInTheDocument();
    expect(r).toHaveTextContent(A(1));
  });
});

describe("AT_966_13_2 暫時延後、重複送出與不明", () => {
  it("各列的結果標籤與自動入帳句", async () => {
    const items = [1, 2, 3, 4, 5, 6].map((n) => pending(n));
    const entries = [
      ing({ auditRef: A(1), status: "deferred", code: "AUDIT-KEY-MISSING", text: "主機還沒設定簽章金鑰", permanent: false }),
      ing({ auditRef: A(2), status: "rejected", code: "R2", text: "暫時被拒", permanent: false }),
      Object.fromEntries(Object.entries(ing({ auditRef: A(3), code: "R3", text: "不確定" })).filter(([k]) => k !== "permanent")),
      ing({ auditRef: A(4), code: "R4", text: "字串旗標", permanent: "yes" }),
      ing({ auditRef: A(5), code: "AUDIT-REF-REUSED", text: "這個稽核編號已經入帳過，不會再入帳", permanent: true }),
      ing({ auditRef: A(6), status: "zzz", code: "R6", text: "怪狀態", permanent: false }),
    ];
    const { el } = await panel({ items, patrol: () => ({ data: PATROL({ ingest: entries }) }) });
    expect(row(el, 1)).toHaveTextContent("延後");
    expect(row(el, 1)).toHaveTextContent("條件解除後下一次心跳會自動入帳");
    expect(row(el, 2)).toHaveTextContent("被拒收");
    expect(row(el, 2)).toHaveTextContent("條件解除後下一次心跳會自動入帳");
    expect(row(el, 3)).toHaveTextContent("是否會自動入帳不明");
    expect(row(el, 4)).toHaveTextContent("是否會自動入帳不明");
    expect(row(el, 5)).toHaveTextContent("被拒收");
    expect(row(el, 5)).toHaveTextContent("需要人處理");
    expect(row(el, 5)).toHaveTextContent("這個稽核編號已經入帳過，不會再入帳");
    expect(row(el, 6)).toHaveTextContent("未知狀態『zzz』");
  });
});

describe("AT_966_13_3 無對應項與快照過時", () => {
  it("(a) 新鮮：無對應項只說主機還沒處理", async () => {
    const { el } = await panel({ items: [pending(2)], patrol: () => ({ data: PATROL({ ingest: [] }) }) });
    expect(row(el, 2)).toHaveTextContent("待入帳");
    expect(row(el, 2)).toHaveTextContent("主機還沒處理這筆");
    expect(within(el).queryByTestId("si-ingest-stale")).toBeNull();
  });
  it("(b) 過時：面板層級提示，A1 的拒收原因仍顯示", async () => {
    const { el } = await panel({ items: [pending(1), pending(2)], patrol: () => ({ data: PATROL({ generatedAt: iso(40), ingest: [ing({})] }) }) });
    expect(within(el).getByTestId("si-ingest-stale")).toHaveTextContent("巡邏回報已過時（40 分鐘前）：下面的原因可能已經改變");
    expect(row(el, 1)).toHaveTextContent("STALE-CARD");
  });
});

describe("AT_966_13_4 回報量不到的四種原因", () => {
  it.each([
    ["report_dir_unset", () => siUnavailable("report_dir_unset"), "拒收原因量不到：這個部署沒有掛載巡邏回報目錄"],
    ["report_missing", () => siUnavailable("report_missing"), "拒收原因量不到：還沒有收到巡邏回報"],
    ["report_invalid", () => siUnavailable("report_invalid"), "拒收原因量不到：巡邏回報檔有問題"],
    ["502", () => failure(502, { message: "後端服務無法連線", reason: "bridge_unreachable" }), "拒收原因量不到：連不上後端服務"],
  ])("%s", async (_name, patrol, expected) => {
    const user = userEvent.setup({ delay: null });
    const { el } = await panel({ items: [pending(1)], patrol });
    expect(within(el).getByTestId("si-ingest-unavailable")).toHaveTextContent(expected);
    expect(row(el, 1)).toHaveTextContent("待入帳");
    expect(row(el, 1)).not.toHaveTextContent("被拒收");
    expect(row(el, 1)).not.toHaveTextContent("主機還沒處理");
    expect(text(el)).not.toContain("Bridge");
    await user.click(within(row(el, 1)).getByRole("button", { name: "入帳指令" }));
    expect(within(row(el, 1)).getAllByRole("button").length).toBeGreaterThan(1);
  });
});

describe("AT_966_13_5 最近已入帳", () => {
  it("常駐顯示、沒有展開鈕；只列時間最新的 5 筆；段內沒有任何按鈕", async () => {
    const done = Array.from({ length: 8 }, (_, i) => writeItem({ auditRef: A(100 + i), kind: "decide", dkind: "approve", ingested: true, time: `2026-11-0${i + 1}T10:00:00Z` }));
    const { el } = await panel({ items: [...done, pending(1), pending(2)], patrol: () => ({ data: PATROL() }) });
    const section = within(el).getByTestId("si-recent-ingested");
    expect(section).toHaveTextContent("最近已入帳（8）");
    expect(within(section).queryAllByRole("button")).toHaveLength(0);
    expect(el.querySelector("[data-testid='si-recent-ingested-toggle']")).toBeNull();
    expect(within(el).queryByTestId(`si-ingested-${A(102)}`)).toBeNull();
    const shown = Array.from(el.querySelectorAll<HTMLElement>("[data-testid^='si-ingested-']")).map((li) => li.dataset.testid);
    expect(shown).toEqual([107, 106, 105, 104, 103].map((n) => `si-ingested-${A(n)}`));
    expect(text(within(el).getByTestId("si-recent-ingested"))).toContain("只列最近 5 筆");
    const first = within(el).getByTestId(`si-ingested-${A(107)}`);
    expect(first).toHaveTextContent("已入帳");
    expect(first).toHaveTextContent(A(107));
    expect(first).toHaveTextContent("2026-11-08T10:00:00Z");
    expect(within(first).queryByRole("button", { name: "入帳指令" })).toBeNull();
  });
  it("ingested 為 null（對帳量不到）時整段不出現", async () => {
    const items = [writeItem({ auditRef: A(1), kind: "decide", ingested: null }), writeItem({ auditRef: A(2), kind: "decide", ingested: null })];
    const { el } = await panel({ items, reconcile: { status: "NOT-EVALUABLE", reason: "bridge_unreachable", backfilled: 0 } });
    expect(within(el).queryByTestId("si-recent-ingested")).toBeNull();
    expect(within(el).getByTestId("si-reconcile-ne")).toBeInTheDocument();
  });
});

describe("AT_966_13_6 只結合未入帳列", () => {
  it("已入帳的列沒有拒收標籤，只在最近已入帳", async () => {
    const items = [pending(1), writeItem({ auditRef: A(3), kind: "decide", dkind: "approve", ingested: true })];
    const { el } = await panel({ items, patrol: () => ({ data: PATROL({ ingest: [ing({ auditRef: A(3) }), ing({})] }) }) });
    expect(within(el).queryByTestId(`si-pending-${A(3)}`)).toBeNull();
    const done = within(el).getByTestId(`si-ingested-${A(3)}`);
    expect(done).not.toHaveTextContent("被拒收");
    expect(done).not.toHaveTextContent("STALE-CARD");
  });
});

describe("AT_966_13_E_1 重複稽核編號與缺原因碼", () => {
  it("取第一筆；無 code 與 text 者顯示沒有提供原因", async () => {
    const entries = [ing({ code: "STALE-CARD", text: "第一筆" }), ing({ code: "DIGEST-MISMATCH", text: "第二筆" }), { auditRef: A(2), status: "rejected" }];
    const { el } = await panel({ items: [pending(1), pending(2)], patrol: () => ({ data: PATROL({ ingest: entries }) }) });
    expect(row(el, 1)).toHaveTextContent("STALE-CARD");
    expect(row(el, 1)).toHaveTextContent("第一筆");
    expect(row(el, 1)).not.toHaveTextContent("DIGEST-MISMATCH");
    expect(row(el, 2)).toHaveTextContent("主機沒有提供原因。");
    expect(row(el, 2)).toHaveTextContent("被拒收");
  });
});

describe("AT_966_13_E_2 對帳量不到與既有行為回歸", () => {
  it("(a) 對帳量不到：沿既有訊息，不結合拒收原因、沒有最近已入帳", async () => {
    const { el } = await panel({ items: [pending(1)], reconcile: { status: "NOT-EVALUABLE", reason: "bridge_timeout", backfilled: 0 }, patrol: () => ({ data: PATROL({ ingest: [ing({})] }) }) });
    expect(within(el).getByTestId("si-reconcile-ne")).toHaveTextContent("對帳量不到");
    expect(text(el)).not.toContain("STALE-CARD");
    expect(within(el).queryByTestId("si-recent-ingested")).toBeNull();
  });
  it("(b) 既有的待入帳列、被取代群組與對帳警示 testid 與文字不變", async () => {
    const user = userEvent.setup({ delay: null });
    const items = [pending(1), pending(2, { supersededBy: A(9) }), writeItem({ auditRef: A(9), kind: "decide", dkind: "promote", ingested: true })];
    const view = renderFlow({
      ...ADMIN_UI,
      overrides: {
        "console-writes": () => ({
          data: { items, truncated: false, orphans: [{ auditRef: A(7), kind: "decide", subject: "PROP-SI-004" }], reconcile: { status: "ok", reason: null, backfilled: 0 } },
        }),
      },
    });
    const el = await screen.findByTestId("si-writes-panel");
    expect(await within(el).findByTestId("si-write-alerts")).toHaveTextContent("對帳警示：帳本有 Console 載體的項目，Console 的稽核表卻沒有對應的列");
    expect(within(el).getByTestId(`si-pending-${A(1)}`)).toBeInTheDocument();
    await user.click(within(el).getByTestId("si-superseded-toggle"));
    expect(within(el).getByTestId(`si-superseded-by-${A(2)}`)).toHaveTextContent(`取代者：${A(9)}`);
    await user.click(within(within(el).getByTestId(`si-pending-${A(1)}`)).getByRole("button", { name: "入帳指令" }));
    expect(
      within(el)
        .getByTestId(`si-pending-${A(1)}`)
        .querySelector("[data-testid='si-ingest-commands']"),
    ).not.toBeNull();
    view.unmount();
  });
});
