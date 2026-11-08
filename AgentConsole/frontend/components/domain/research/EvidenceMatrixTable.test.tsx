import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ResearchEvidenceItem, ResearchEvidenceMatrix, ResearchSource } from "@/lib/api/types";
import { prosConsMatrix } from "@/lib/domain/research";
import { R1 } from "@/tests/fixtures/research/ids";
import { EVIDENCE, SOURCES } from "@/tests/fixtures/research/misc";
import { callsOf, failure, renderResearch, stubResearchApi, writeCalls } from "@/tests/helpers/research";
import { EvidenceMatrixTable, type EvidenceMatrixView } from "./EvidenceMatrixTable";

/**
 * 證據矩陣表與技術優缺點矩陣（TCS-ResearchToPRD-P0-20261102 AT-960-10-6；AC-R2P-06-5、05-3、05-5、05-4；D-66）：
 * 優缺點矩陣只列有證據列的候選、每格帶 `[E-NNN]` 連結且連結目標列存在於矩陣表；矩陣表的標記計數、七欄展開、抓取紀錄、外部文字的純文字渲染與安全連結、版本切換與空狀態。
 * 判定指令：npx vitest run components/domain/research/EvidenceMatrixTable.test.tsx -t AT_960_10_6
 */
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(),
}));

const BASE = EVIDENCE.items[0];

const item = (evidenceNo: string, patch: Partial<ResearchEvidenceItem> = {}): ResearchEvidenceItem => ({ ...BASE, evidenceNo, sourceNo: "S-001", f3Critique: "未見", f6Limits: "未見", ...patch });
const matrixOf = (items: ResearchEvidenceItem[], patch: Partial<ResearchEvidenceMatrix> = {}): ResearchEvidenceMatrix => ({ ...EVIDENCE, items, counterEvidence: [], ...patch });
const sourceOf = (sourceNo: string, patch: Partial<ResearchSource> = {}): ResearchSource => ({ ...SOURCES[0], sourceNo, fetches: [], ...patch });

/** 候選 A 兩列、候選 B 一列、一列沒有候選名；候選 C 沒有任何證據列（只存在於範圍），所以不在 items 裡。 */
const PROS_CONS = matrixOf(
  [
    item("E-001", { candidate: "候選 A", claim: "A 的優點一", f3Critique: "A 的批評", f6Limits: "A 的限制" }),
    item("E-002", { candidate: "候選 A", claim: "A 的優點二" }),
    item("E-003", { candidate: "候選 B", claim: "B 的優點", f3Critique: "B 的批評" }),
    item("E-004", { candidate: null, claim: "沒有候選名的論點" }),
  ],
  {
    counterEvidence: [
      { evidenceNo: "E-002", searchId: "Q-001", conclusion: "LIMIT", sourceNo: "S-001", note: "A 在大規模時退化" },
      { evidenceNo: "E-003", searchId: "Q-002", conclusion: "IRRELEVANT", sourceNo: null, note: "與 B 無關的反證" },
    ],
  },
);

function render(view: EvidenceMatrixView, stub: Parameters<typeof stubResearchApi>[0] = {}, onViewChange?: (view: EvidenceMatrixView) => void) {
  const api = stubResearchApi({ evidence: PROS_CONS, ...stub });
  const ui = renderResearch(<EvidenceMatrixTable researchId={R1} view={view} onViewChange={onViewChange} />);
  return { ...ui, ...api };
}

const rowOf = (evidenceNo: string): HTMLElement => {
  const found = screen.getAllByTestId("evidence-row").find((row) => row.getAttribute("data-evidence-no") === evidenceNo);
  if (found === undefined) throw new Error(`矩陣表沒有 ${evidenceNo} 列`);
  return found;
};

afterEach(() => {
  Reflect.deleteProperty(HTMLElement.prototype, "scrollIntoView");
});

describe("AT_960_10_6 技術優缺點矩陣：只列有證據列的候選，每格帶 [E-NNN] 連結且目標列存在", () => {
  it("AT_960_10_6 候選 A（2 列）與 B（1 列）各一列、候選 C（0 列，只存在於範圍）與沒有候選名的證據列不出現；沒有憑空列出的候選", async () => {
    const { calls } = render("proscons");
    const table = await screen.findByRole("table", { name: "技術優缺點矩陣" });
    const candidates = within(table).getAllByTestId("proscons-candidate");
    expect(candidates.map((row) => row.getAttribute("data-candidate"))).toEqual(["候選 A", "候選 B"]);
    expect(within(candidates[0]).getByText("2 列證據")).toBeInTheDocument();
    expect(within(candidates[1]).getByText("1 列證據")).toBeInTheDocument();
    expect(within(table).queryByText("候選 C")).toBeNull();
    expect(within(table).queryByText("沒有候選名的論點"), "沒有候選名的列不歸任何組").toBeNull();
    expect(writeCalls(calls), "唯讀視圖不送任何寫入").toEqual([]);
    // 純函式與畫面同一份結果：候選名單恰等於「有證據列的候選」
    expect(prosConsMatrix(PROS_CONS).map((c) => c.candidate)).toEqual(["候選 A", "候選 B"]);
  });

  it("AT_960_10_6 優點取自論點；缺點取自 F3 批評、F6 限制與判為削弱／限縮的反證（無關的反證與「未見」不入）；每格恰一個 [E-NNN] 連結", async () => {
    render("proscons");
    const table = await screen.findByRole("table", { name: "技術優缺點矩陣" });
    const [a, b] = within(table).getAllByTestId("proscons-candidate");
    const cells = (row: HTMLElement, kind: "pro" | "con") =>
      within(row)
        .queryAllByTestId("proscons-cell")
        .filter((cell) => cell.getAttribute("data-kind") === kind)
        .map((cell) => `${cell.getAttribute("data-evidence-no")}｜${cell.querySelector("span")?.textContent}`);
    expect(cells(a, "pro")).toEqual(["E-001｜A 的優點一", "E-002｜A 的優點二"]);
    expect(cells(a, "con")).toEqual(["E-001｜A 的批評", "E-001｜A 的限制", "E-002｜A 在大規模時退化"]);
    expect(cells(b, "pro")).toEqual(["E-003｜B 的優點"]);
    expect(cells(b, "con")).toEqual(["E-003｜B 的批評"]);
    expect(within(table).queryByText("與 B 無關的反證"), "IRRELEVANT 的反證不是缺點").toBeNull();
    for (const cell of within(table).getAllByTestId("proscons-cell")) {
      const links = within(cell).getAllByRole("link");
      expect(links).toHaveLength(1);
      expect(links[0]).toHaveTextContent(`[${cell.getAttribute("data-evidence-no")}]`);
    }
  });

  it("AT_960_10_6 每個連結的目標列都存在於矩陣表（即使目前顯示的是優缺點視圖，矩陣表仍在 DOM、只是 hidden）", async () => {
    const { container } = render("proscons");
    const table = await screen.findByRole("table", { name: "技術優缺點矩陣" });
    const links = within(table).getAllByRole("link");
    expect(links.length).toBeGreaterThanOrEqual(6);
    const matrixTable = container.querySelector('[data-testid="evidence-table"]');
    expect(matrixTable, "矩陣表在 DOM 內").not.toBeNull();
    expect(screen.getByTestId("evidence-table-view")).toHaveAttribute("hidden");
    for (const link of links) {
      const href = link.getAttribute("href") ?? "";
      expect(href).toMatch(/^#evidence-row-E-\d{3}$/);
      const target = (matrixTable as HTMLElement).querySelector(href);
      expect(target, `${href} 的目標列存在於矩陣表`).not.toBeNull();
      expect(target).toHaveAttribute("data-testid", "evidence-row");
    }
  });

  it("AT_960_10_6 點 [E-NNN]：通知呼叫端切到矩陣表；矩陣表可見後該列被展開、聚焦並捲到可見處", async () => {
    const scrollIntoView = vi.fn();
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", { value: scrollIntoView, configurable: true, writable: true });
    const user = userEvent.setup();
    const seen: EvidenceMatrixView[] = [];
    function Host() {
      const [view, setView] = useState<EvidenceMatrixView>("proscons");
      return (
        <EvidenceMatrixTable
          researchId={R1}
          view={view}
          onViewChange={(next) => {
            seen.push(next);
            setView(next);
          }}
        />
      );
    }
    stubResearchApi({ evidence: PROS_CONS });
    renderResearch(<Host />);
    const table = await screen.findByRole("table", { name: "技術優缺點矩陣" });
    const cell = within(table)
      .getAllByTestId("proscons-cell")
      .find((c) => c.getAttribute("data-evidence-no") === "E-002");
    await user.click(within(cell as HTMLElement).getByRole("link", { name: "[E-002]" }));
    expect(seen).toEqual(["table"]);
    await waitFor(() => expect(rowOf("E-002")).toHaveFocus());
    expect(rowOf("E-002")).toHaveAttribute("data-expanded", "true");
    expect(scrollIntoView).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("evidence-table-view")).not.toHaveAttribute("hidden");
    expect(screen.getByTestId("proscons-view")).toHaveAttribute("hidden");
    expect(within(rowOf("E-002").closest("tbody") as HTMLElement).getByTestId("evidence-detail")).toBeInTheDocument();
  });

  it("AT_960_10_6 沒有任何候選名（證據列都沒填候選技術）：顯示「沒有可分組的候選技術」，不列任何優缺點", async () => {
    render("proscons", { evidence: matrixOf([item("E-001", { candidate: null }), item("E-002", { candidate: "  " })]) });
    expect(await screen.findByText("沒有可分組的候選技術")).toBeInTheDocument();
    expect(screen.queryByTestId("proscons-candidate")).toBeNull();
  });
});

describe("AT_960_10_6 證據矩陣表：標記計數、七欄展開、抓取紀錄、純文字與安全連結、版本、空狀態", () => {
  const HOSTILE = "<script>alert(1)</script> **粗體** <img src=x onerror=alert(1)>";
  const TABLE_MATRIX = matrixOf([
    item("E-010", { candidate: null, claim: HOSTILE, sourceNo: "S-010", f7Verification: "V2", strength: "STRONG" }),
    item("E-011", { candidate: "候選 X", claim: "被標 UNANCHORED 的論點", sourceNo: "S-011", f7Verification: "V3", strength: "WEAK", unanchored: true, f4RiskTags: ["SELF", "STALE"] }),
    item("E-012", { candidate: "候選 X", claim: "只有宣告的論點", sourceNo: "S-012", f7Verification: "V1", strength: "CANDIDATE" }),
  ]);
  const TABLE_SOURCES: ResearchSource[] = [
    sourceOf("S-010", { title: "公開的 https 來源", url: "https://example.com/a", licenseSpdx: "MIT", tier: "T1", verification: "V2" }),
    sourceOf("S-011", {
      title: "危險網址的來源",
      url: "javascript:alert(1)",
      licenseSpdx: "GPL-3.0-only",
      tier: "T2",
      verification: "V3",
      fetches: [
        {
          fetchNo: "F-0007",
          method: "GET",
          observedBy: "BRIDGE",
          host: "(unparsed)",
          httpStatus: null,
          outcome: "DENIED_ALLOWLIST",
          rawSha256: null,
          rawBytes: null,
          fetchedAt: "2026-11-02T10:00:00+08:00",
        },
      ],
    }),
    sourceOf("S-012", { title: "DOI 定位的來源", url: null, doi: "10.1000/xyz", anchorKind: "DOI", licenseSpdx: null, tier: "T1", verification: "V1" }),
  ];

  it("AT_960_10_6 頁頂：版本、列數、合格列數（V2 以上且非 UNANCHORED）、UNANCHORED 筆數與授權待查列數（GPL 系與缺授權；MIT 不算）", async () => {
    const { calls } = render("table", { evidence: TABLE_MATRIX, sources: TABLE_SOURCES });
    await screen.findAllByTestId("evidence-row");
    const summary = screen.getByTestId("evidence-summary");
    expect(summary).toHaveTextContent("矩陣 v1 · 共 3 列");
    await waitFor(() => expect(summary).toHaveTextContent("合格 1 列"));
    expect(screen.getByTestId("unanchored-count")).toHaveTextContent("UNANCHORED：1 筆");
    expect(screen.getByTestId("license-pending-count")).toHaveTextContent("授權待查：2 列");
    expect(within(rowOf("E-011")).getByText("UNANCHORED")).toBeInTheDocument();
    expect(within(rowOf("E-010")).queryByText("UNANCHORED")).toBeNull();
    expect(within(rowOf("E-011")).getByText("授權待查")).toBeInTheDocument();
    expect(within(rowOf("E-012")).getByText("授權待查")).toBeInTheDocument();
    expect(within(rowOf("E-010")).queryByText("授權待查")).toBeNull();
    expect(within(rowOf("E-010")).getByText("—"), "沒有候選名顯示破折號").toBeInTheDocument();
    expect(within(rowOf("E-010")).getByText(/T1 · V2/)).toBeInTheDocument();
    expect(within(rowOf("E-011")).getByText("弱")).toBeInTheDocument();
    expect(writeCalls(calls)).toEqual([]);
  });

  it("AT_960_10_6 授權待查（D-80，與 Bridge 同一條規則）：UNKNOWN（含大小寫）、null、GPL／AGPL 系＝待查；LGPL、複合式（OR／AND／WITH）、MIT＝不待查——頁頂計數與每列旗標一致", async () => {
    const cases: Array<[string, string | null, boolean]> = [
      ["E-021", "UNKNOWN", true],
      ["E-022", "unknown", true],
      ["E-023", null, true],
      ["E-024", "未見", true],
      ["E-025", "GPL-3.0-only", true],
      ["E-026", "agpl-3.0", true],
      ["E-027", "LGPL-3.0", false],
      ["E-028", "MIT OR GPL-2.0", false],
      ["E-029", "Apache-2.0 AND GPL-3.0-only", false],
      ["E-030", "GPL-2.0 WITH Classpath-exception-2.0", false],
      ["E-031", "MIT", false],
    ];
    const items = cases.map(([no], i) => item(no, { sourceNo: `S-0${i + 21}`, f7Verification: "V2", strength: "MEDIUM" }));
    const sources = cases.map(([, license], i) => sourceOf(`S-0${i + 21}`, { licenseSpdx: license, tier: "T1", verification: "V2" }));
    render("table", { evidence: matrixOf(items), sources });
    await screen.findAllByTestId("evidence-row");
    await waitFor(() => expect(screen.getByTestId("license-pending-count")).toHaveTextContent(`授權待查：${cases.filter(([, , pending]) => pending).length} 列`));
    for (const [no, license, pending] of cases) {
      const flag = within(rowOf(no)).queryByText("授權待查");
      expect(flag !== null, `${no}（${JSON.stringify(license)}）的旗標`).toBe(pending);
    }
  });

  it("AT_960_10_6 外部文字一律純文字：含 script、Markdown 與 img 的論點逐字顯示，DOM 沒有 script／img／strong／iframe 元素", async () => {
    const { container } = render("table", { evidence: TABLE_MATRIX, sources: TABLE_SOURCES });
    await screen.findAllByTestId("evidence-row");
    expect(within(rowOf("E-010")).getByText(HOSTILE)).toBeInTheDocument();
    expect(container.querySelector("script, img, strong, iframe, svg[onload]")).toBeNull();
  });

  it("AT_960_10_6 來源連結：合法 https 才是連結（target=_blank、rel 含 noopener 與 noreferrer）；javascript:、沒有網址者只顯示文字", async () => {
    render("table", { evidence: TABLE_MATRIX, sources: TABLE_SOURCES });
    await screen.findAllByTestId("evidence-row");
    const link = within(rowOf("E-010")).getByRole("link", { name: "公開的 https 來源" });
    expect(link).toHaveAttribute("href", "https://example.com/a");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link.getAttribute("rel")).toContain("noopener");
    expect(link.getAttribute("rel")).toContain("noreferrer");
    expect(within(rowOf("E-011")).getByText("危險網址的來源")).toBeInTheDocument();
    expect(within(rowOf("E-011")).queryByRole("link"), "javascript: 不成為連結").toBeNull();
    expect(within(rowOf("E-012")).getByText("DOI 定位的來源")).toBeInTheDocument();
    expect(within(rowOf("E-012")).getByText("DOI 10.1000/xyz")).toBeInTheDocument();
    expect(within(rowOf("E-012")).queryByRole("link")).toBeNull();
  });

  it("AT_960_10_6 展開一列：F1～F7 七欄、風險標籤、反證；抓取紀錄的解析不出 host 者顯示保留字 (unparsed)（原樣、不加連結）、狀態碼缺席顯示破折號；宣告型來源顯示「無（宣告型）」", async () => {
    const user = userEvent.setup();
    render("table", {
      evidence: { ...TABLE_MATRIX, counterEvidence: [{ evidenceNo: "E-011", searchId: "Q-009", conclusion: "WEAKEN", sourceNo: null, note: "另一份報告削弱了這個數字" }] },
      sources: TABLE_SOURCES,
    });
    await screen.findAllByTestId("evidence-row");
    const toggle = within(rowOf("E-011")).getByRole("button", { name: "展開 E-011 的七欄與抓取紀錄" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    const detail = within(rowOf("E-011").closest("tbody") as HTMLElement).getByTestId("evidence-detail");
    for (const label of ["F1 機制", "F2 證據", "F3 失敗與批評", "F4 風險標籤", "F5 適用性", "F6 限制", "F7 查證層級"]) expect(within(detail).getByText(label)).toBeInTheDocument();
    expect(within(detail).getByText("SELF、STALE")).toBeInTheDocument();
    expect(within(detail).getByText("削弱：另一份報告削弱了這個數字")).toBeInTheDocument();
    const fetchRow = within(detail).getByTestId("fetch-record");
    const host = within(fetchRow).getByText("(unparsed)");
    expect(host.closest("a"), "保留字 host 不加連結").toBeNull();
    expect(within(fetchRow).getByText("DENIED_ALLOWLIST")).toBeInTheDocument();
    expect(within(fetchRow).getAllByText("—").length, "狀態碼、sha256、位元組缺席都顯示破折號").toBeGreaterThanOrEqual(3);
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(within(rowOf("E-011").closest("tbody") as HTMLElement).queryByTestId("evidence-detail")).toBeNull();
    await user.click(within(rowOf("E-012")).getByRole("button", { name: "展開 E-012 的七欄與抓取紀錄" }));
    expect(screen.getByText(/無（宣告型）/)).toBeInTheDocument();
  });

  it("AT_960_10_6 版本切換：多個版本時可選舊版（請求帶 matrixVersion、顯示「舊版，唯讀」與說明），選回最新版回到最新請求", async () => {
    const user = userEvent.setup();
    const v3 = matrixOf([item("E-030", { candidate: "候選 N", claim: "最新版的論點" })], { matrixVersion: 3 });
    const v2 = matrixOf([item("E-020", { candidate: "候選 O", claim: "舊版的論點" })], { matrixVersion: 2 });
    const { calls } = render("table", {
      evidence: v3,
      overrides: (call) => (call.method === "GET" && call.path.endsWith("/evidence") && call.query.get("matrixVersion") === "2" ? { data: v2 } : undefined),
    });
    // 兩種視圖同在 DOM：限定在矩陣表視圖內找
    const tableView = () => within(screen.getByTestId("evidence-table-view"));
    await screen.findByTestId("evidence-table-view");
    expect(await tableView().findByText("最新版的論點")).toBeInTheDocument();
    const select = screen.getByRole("combobox", { name: "矩陣版本" });
    expect(
      within(select)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["v3（最新）", "v2", "v1"]);
    await user.selectOptions(select, "2");
    expect(await tableView().findByText("舊版的論點")).toBeInTheDocument();
    expect(tableView().queryByText("最新版的論點")).toBeNull();
    expect(screen.getByTestId("evidence-summary")).toHaveTextContent("矩陣 v2（舊版，唯讀）");
    expect(screen.getByRole("note")).toHaveTextContent("最新版是 v3");
    expect(callsOf(calls, "GET", /\/evidence$/).some((c) => c.query.get("matrixVersion") === "2")).toBe(true);
    await user.selectOptions(select, "3");
    expect(await tableView().findByText("最新版的論點")).toBeInTheDocument();
    expect(screen.queryByRole("note")).toBeNull();
    expect(writeCalls(calls)).toEqual([]);
  });

  it("AT_960_10_6 尚無矩陣版本（後端回 matrixVersion 0 的空矩陣）：矩陣表與優缺點矩陣各顯示空狀態，不是錯誤", async () => {
    render("table", { evidence: matrixOf([], { matrixVersion: 0 }) });
    expect(await screen.findByText("尚無矩陣版本", { exact: false })).toBeInTheDocument();
    expect(within(screen.getByTestId("evidence-table-view")).getByText("還沒有證據列")).toBeInTheDocument();
    expect(within(screen.getByTestId("proscons-view")).getByText("還沒有證據列")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByRole("combobox", { name: "矩陣版本" })).toBeNull();
  });

  it("AT_960_10_6 載入失敗：顯示原因與「重試」，不當成空矩陣；重試後列出現", async () => {
    const user = userEvent.setup();
    let broken = true;
    render("table", { overrides: (call) => (broken && call.method === "GET" && call.path.endsWith("/evidence") ? failure(500, { message: "證據矩陣讀取失敗" }) : undefined) });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("無法載入證據矩陣");
    expect(alert).toHaveTextContent("證據矩陣讀取失敗");
    expect(screen.queryByText("還沒有證據列")).toBeNull();
    broken = false;
    await user.click(within(alert).getByRole("button", { name: "重試" }));
    expect(await screen.findAllByTestId("evidence-row")).toHaveLength(4);
  });

  it("AT_960_10_6 載入中：顯示載入骨架（aria-busy），沒有列也沒有空狀態", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>(() => {})),
    );
    renderResearch(<EvidenceMatrixTable researchId={R1} view="table" />);
    expect(screen.getByLabelText("證據矩陣載入中")).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByTestId("evidence-row")).toBeNull();
    expect(screen.queryByText("還沒有證據列")).toBeNull();
  });
});

// TCS-ConsoleUxSortHelp-20261108 AT-963-3-12／3-13（T10 抓取紀錄、T11 證據表）
describe("AT_963_3_12／3_13 證據矩陣：預設編號自然序升冪與表頭排序", () => {
  const zh = new Intl.Collator("zh-Hant", { numeric: true });
  const ids = () => screen.getAllByTestId("evidence-row").map((r) => r.getAttribute("data-evidence-no"));
  const pressIn = async (user: ReturnType<typeof userEvent.setup>, root: HTMLElement, name: string) =>
    user.click(within(within(root).getByRole("columnheader", { name })).getByRole("button", { name }));
  const MATRIX = matrixOf([
    item("E-10", { candidate: "乙技術", claim: "丙論點", sourceNo: "S-010", f7Verification: "V3", strength: "WEAK" }),
    item("E-100", { candidate: "甲技術", claim: "甲論點", sourceNo: "S-009", f7Verification: "V1", strength: "STRONG" }),
    item("E-9", { candidate: "丙技術", claim: "乙論點", sourceNo: "S-100", f7Verification: "V2", strength: "MEDIUM" }),
  ]);
  const fetchOf = (n: string, patch: Partial<ResearchSource["fetches"][number]>): ResearchSource["fetches"][number] => ({
    fetchNo: n,
    method: "GET",
    observedBy: "BRIDGE",
    host: "example.com",
    httpStatus: 200,
    outcome: "OK",
    rawSha256: "ab".repeat(32),
    rawBytes: 100,
    fetchedAt: "2026-11-02T10:00:00+08:00",
    ...patch,
  });
  const SRC = [
    sourceOf("S-010", { fetches: [] }),
    sourceOf("S-009", { fetches: [] }),
    sourceOf("S-100", {
      fetches: [
        fetchOf("F-10", { httpStatus: 404, rawBytes: 5, host: "b.example.com", method: "POST", outcome: "HTTP_ERROR", fetchedAt: "2026-11-02T00:00:00+08:00" }),
        fetchOf("F-9", { httpStatus: 200, rawBytes: 900, host: "c.example.com", fetchedAt: "2026-11-01T23:00:00Z" }),
        fetchOf("F-100", { httpStatus: null, rawBytes: null, rawSha256: null, host: "a.example.com", outcome: "DENIED_ALLOWLIST", fetchedAt: "2026-10-30T00:00:00Z" }),
      ],
    }),
  ];

  it("AT_963_3_13 證據表：預設編號自然序（E-9 < E-10 < E-100）、編號欄 ascending；層級依 V 序；強度與論點依文字；標記欄不可排；七欄字樣不變；優缺點矩陣表頭無排序", async () => {
    const user = userEvent.setup();
    render("table", { evidence: MATRIX, sources: SRC });
    await screen.findAllByTestId("evidence-row");
    const table = screen.getByTestId("evidence-table");
    expect(ids()).toEqual(["E-9", "E-10", "E-100"]);
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["編號", "候選技術", "論點", "來源", "層級", "強度", "標記"]);
    expect(within(table).getByRole("columnheader", { name: "編號" })).toHaveAttribute("aria-sort", "ascending");
    const flag = within(table).getByRole("columnheader", { name: "標記" });
    expect(flag.querySelector("button")).toBeNull();
    expect(flag.hasAttribute("aria-sort")).toBe(false);

    await pressIn(user, table, "層級");
    expect(ids()).toEqual(["E-100", "E-9", "E-10"]); // V1、V2、V3
    await pressIn(user, table, "層級");
    expect(ids()).toEqual(["E-10", "E-9", "E-100"]);
    await pressIn(user, table, "論點");
    const claimOf = { "E-10": "丙論點", "E-100": "甲論點", "E-9": "乙論點" } as Record<string, string>;
    expect(ids()).toEqual(["E-10", "E-100", "E-9"].sort((a, b) => zh.compare(claimOf[a], claimOf[b])));
    await pressIn(user, table, "強度");
    expect(ids().sort()).toEqual(["E-10", "E-100", "E-9"].sort());
    // 第一次點預設欄（編號）即降冪
    await pressIn(user, table, "編號");
    expect(ids()).toEqual(["E-9", "E-10", "E-100"]);
    await pressIn(user, table, "編號");
    expect(ids()).toEqual(["E-100", "E-10", "E-9"]);
  });

  it("AT_963_3_13 同檔的優缺點矩陣（範圍外）thead 內沒有 aria-sort、沒有按鈕", async () => {
    render("proscons");
    const table = await screen.findByRole("table", { name: "技術優缺點矩陣" });
    const head = table.querySelector("thead") as HTMLElement;
    expect(head.querySelector("[aria-sort]")).toBeNull();
    expect(head.querySelector("button")).toBeNull();
  });

  it("AT_963_3_12 抓取紀錄：預設編號自然序升冪；狀態碼與位元組依數字（空值最後）、時間依時刻、方法、觀測者、主機、結果、sha256 依文字", async () => {
    const user = userEvent.setup();
    render("table", { evidence: MATRIX, sources: SRC });
    await screen.findAllByTestId("evidence-row");
    await user.click(within(rowOf("E-9")).getByRole("button", { name: "展開 E-9 的七欄與抓取紀錄" }));
    const table = await screen.findByTestId("fetch-records");
    const nos = () =>
      within(table)
        .getAllByTestId("fetch-record")
        .map((r) => within(r).getAllByRole("cell")[0].textContent);
    expect(nos()).toEqual(["F-9", "F-10", "F-100"]);
    expect(within(table).getByRole("columnheader", { name: "編號" })).toHaveAttribute("aria-sort", "ascending");
    await pressIn(user, table, "狀態碼");
    expect(nos()).toEqual(["F-9", "F-10", "F-100"]); // 200、404、空
    await pressIn(user, table, "狀態碼");
    expect(nos()).toEqual(["F-10", "F-9", "F-100"]); // 404、200、空值仍最後
    await pressIn(user, table, "位元組");
    expect(nos()).toEqual(["F-10", "F-9", "F-100"]); // 5、900、空
    await pressIn(user, table, "位元組");
    expect(nos()).toEqual(["F-9", "F-10", "F-100"]);
    await pressIn(user, table, "時間");
    expect(nos()).toEqual(["F-100", "F-10", "F-9"]); // 10-30、11-01 16:00Z、11-01 23:00Z
    await pressIn(user, table, "主機");
    expect(nos()).toEqual(["F-100", "F-10", "F-9"]); // a、b、c
    await pressIn(user, table, "方法");
    expect(nos()).toEqual(["F-9", "F-100", "F-10"]); // GET、GET（同值依編號）、POST
    await pressIn(user, table, "結果");
    expect(nos()).toEqual(["F-100", "F-10", "F-9"]); // DENIED_ALLOWLIST、HTTP_ERROR、OK
    await pressIn(user, table, "觀測者");
    expect(nos()).toEqual(["F-9", "F-10", "F-100"]); // 三列同值：依編號升冪
    await pressIn(user, table, "原文 sha256");
    expect(nos().at(-1)).toBe("F-100"); // sha256 缺值排最後
    await pressIn(user, table, "原文 sha256");
    expect(nos().at(-1)).toBe("F-100");
  });
});
