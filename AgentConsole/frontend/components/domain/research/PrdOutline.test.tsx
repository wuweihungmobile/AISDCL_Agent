import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PrdOutline, findOutlineSection, parsePrdOutline } from "./PrdOutline";

/**
 * PRD 目錄樹（TCS-ResearchToPRD-P0-20261102 AT-960-16-1；AC-R2P-09-1）：由標題與 `r2p:section` 錨點導出、程式碼圍欄內的 `#` 不算、點目錄項回報選了誰（捲動由工作室決定）、
 * 視窗 < 1280 時收合為圖示鈕仍可操作；缺陷卡的章節定位（`prdAnchor`）對應到目錄項。
 * 判定指令：npx vitest run components/domain/research/PrdOutline.test.tsx
 */

const lineOf = (markdown: string, item: { offset: number }): string => markdown.slice(item.offset).split("\n")[0];

const SAMPLE = [
  "# PRD — 文件批次渲染服務",
  "",
  "<!-- r2p:section=1 -->",
  "## 📋 文檔元數據",
  "內文",
  "## 1. 專案願景",
  "",
  "<!-- r2p:section=2 -->",
  "",
  "### 1.2 業務目標",
  "#### 研究依據",
  "<!-- r2p:section=3 -->",
  "這行文字打斷了錨點與標題的關係",
  "### 5.1 功能規格",
  "",
  "```gherkin",
  "# 這是 Gherkin 的註解不是標題",
  "Scenario: 提交合法批次",
  "```",
  "<!-- r2p:section=4 -->",
  "### 5.2 驗收標準",
  "",
  "~~~bash",
  "# shell 註解",
  "```",
  "# 仍在 ~~~ 圍欄內",
  "~~~",
  "## 9. 技術選型與架構 ##",
].join("\n");

describe("AT_960_16_1 目錄由標題與 r2p:section 錨點導出", () => {
  it("AT_960_16_1 依出現順序列出標題；層級、行索引、行首位移正確（位移處就是該標題行）；結尾的 # 與前後空白去掉", () => {
    const items = parsePrdOutline(SAMPLE);
    expect(items.map((i) => [i.level, i.text])).toEqual([
      [1, "PRD — 文件批次渲染服務"],
      [2, "📋 文檔元數據"],
      [2, "1. 專案願景"],
      [3, "1.2 業務目標"],
      [4, "研究依據"],
      [3, "5.1 功能規格"],
      [3, "5.2 驗收標準"],
      [2, "9. 技術選型與架構"],
    ]);
    for (const item of items) {
      expect(SAMPLE.split("\n")[item.line], item.text).toMatch(/^#{1,6} /);
      expect(lineOf(SAMPLE, item), `${item.text} 的位移`).toBe(SAMPLE.split("\n")[item.line]);
      expect(item.id).toBe(`outline-${item.line}`);
    }
  });

  it("AT_960_16_1 錨點只接在它之後第一個非空行的標題上（可隔空行）；後面先出現其他文字就失效；圍欄內的 # 行與錨點都不算", () => {
    const items = parsePrdOutline(SAMPLE);
    const sectionOf = (text: string) => items.find((i) => i.text === text)?.section;
    expect(sectionOf("📋 文檔元數據")).toBe(1);
    expect(sectionOf("1.2 業務目標"), "錨點與標題之間隔了空行仍接上").toBe(2);
    expect(sectionOf("5.1 功能規格"), "錨點後先有一行文字：不接").toBeNull();
    expect(sectionOf("5.2 驗收標準")).toBe(4);
    expect(
      items.some((i) => i.text.includes("Gherkin") || i.text.includes("shell") || i.text.includes("仍在")),
      "圍欄內的 # 行不是標題",
    ).toBe(false);
    expect(parsePrdOutline("```\n<!-- r2p:section=7 -->\n```\n# 標題")[0].section, "圍欄內的錨點不算").toBeNull();
  });

  it("AT_960_16_1 圍欄規則：結尾要同種字元且至少一樣長；沒有結尾的圍欄吃到文件尾；縮排 4 格是程式碼、不是標題", () => {
    expect(parsePrdOutline("````md\n```\n# 內層\n```\n# 仍在外層圍欄內\n````\n# 圍欄外").map((i) => i.text)).toEqual(["圍欄外"]);
    expect(parsePrdOutline("# 前\n```\n# 沒有結尾\n# 全部被吃掉").map((i) => i.text)).toEqual(["前"]);
    expect(parsePrdOutline("    # 縮排四格\n   # 縮排三格\n").map((i) => i.text)).toEqual(["縮排三格"]);
  });

  it("AT_960_16_1 不是標題的寫法：#hashtag、七個 #、空標題、行內的 #；是標題的寫法：標題文字含 C#、結尾的關閉序列", () => {
    expect(parsePrdOutline("#hashtag\n####### 七個\n# \n##\n文字 # 行內\n").length).toBe(0);
    expect(parsePrdOutline("## C#\n## 標題 ###\n### 含 # 號 的 標題").map((i) => i.text)).toEqual(["C#", "標題", "含 # 號 的 標題"]);
  });

  it("AT_960_16_1 CRLF 的文件：標題文字沒有 \\r、位移仍指到標題行首（以 \\n 切行，每行含其 \\r）", () => {
    const crlf = "# 一\r\n\r\n## 二\r\n內文\r\n### 三\r\n";
    const items = parsePrdOutline(crlf);
    expect(items.map((i) => i.text)).toEqual(["一", "二", "三"]);
    expect(items.map((i) => crlf.slice(i.offset, i.offset + 3))).toEqual(["# 一", "## ", "###"]);
    expect(parsePrdOutline("")).toEqual([]);
    expect(parsePrdOutline("只有內文沒有標題")).toEqual([]);
  });

  it("AT_960_16_1 200KB 等級的文件：導出一次在數十毫秒內（只是量級保險，不是效能驗收）", () => {
    const big = Array.from({ length: 4000 }, (_, i) => (i % 40 === 0 ? `## 章節 ${i}` : `這是第 ${i} 行的內文，沒有標題`)).join("\n");
    const start = performance.now();
    const items = parsePrdOutline(big);
    expect(performance.now() - start).toBeLessThan(500);
    expect(items).toHaveLength(100);
  });
});

describe("AT_960_16_1 目錄元件：點項目回報選了誰；收合時為圖示鈕、仍可操作", () => {
  it("AT_960_16_1 展開模式：每個標題一個按鈕（縮排依層級）、來源節錨點以標籤顯示；點一項回報該項（行索引與位移）", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<PrdOutline content={SAMPLE} onSelect={onSelect} />);
    const nav = screen.getByRole("navigation", { name: "PRD 目錄" });
    const buttons = within(nav).getAllByTestId("outline-item");
    expect(buttons).toHaveLength(8);
    expect(within(buttons[1]).getByText("來源第 1 節")).toBeInTheDocument();
    expect(within(buttons[5]).queryByText(/來源第/)).toBeNull();
    await user.click(within(nav).getByRole("button", { name: /1\.2 業務目標/ }));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0][0]).toMatchObject({ text: "1.2 業務目標", level: 3, section: 2, line: 9 });
  });

  it("AT_960_16_1 目前所在的章節以 aria-current 標示（不只靠底色）", () => {
    render(<PrdOutline content={SAMPLE} activeId="outline-5" onSelect={() => {}} />);
    const current = screen.getAllByTestId("outline-item").filter((b) => b.getAttribute("aria-current") === "location");
    expect(current).toHaveLength(1);
    expect(current[0]).toHaveTextContent("1. 專案願景");
  });

  it("AT_960_16_1 收合模式：只有一顆圖示鈕（展開／收合 PRD 目錄，aria-expanded 與之同步）；展開後清單仍可操作，選了項目就收回去並回報；Esc 收回並把焦點還給圖示鈕", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<PrdOutline content={SAMPLE} collapsed onSelect={onSelect} />);
    expect(screen.queryAllByTestId("outline-item")).toHaveLength(0);
    const trigger = screen.getByRole("button", { name: "展開 PRD 目錄" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    await user.click(trigger);
    expect(screen.getByRole("button", { name: "收合 PRD 目錄" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getAllByTestId("outline-item")).toHaveLength(8);
    await user.click(screen.getByRole("button", { name: /5\.2 驗收標準/ }));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0][0]).toMatchObject({ text: "5.2 驗收標準", section: 4 });
    expect(screen.queryByTestId("prd-outline-panel")).toBeNull();
    // Esc
    await user.click(screen.getByRole("button", { name: "展開 PRD 目錄" }));
    expect(screen.getByTestId("prd-outline-panel")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByTestId("prd-outline-panel")).toBeNull();
    expect(screen.getByRole("button", { name: "展開 PRD 目錄" })).toHaveFocus();
  });

  it("AT_960_16_1 沒有標題的 PRD：目錄顯示說明而不是空白", () => {
    render(<PrdOutline content="只有內文" onSelect={() => {}} />);
    expect(screen.getByText("PRD 還沒有標題，目錄是空的。")).toBeInTheDocument();
  });
});

describe("AT_960_16_1 缺陷卡的章節定位對應到目錄項（findOutlineSection）", () => {
  const items = parsePrdOutline(SAMPLE);
  const textOf = (anchor: string): string | null => findOutlineSection(items, anchor)?.text ?? null;

  it("AT_960_16_1 章節編號：「§5.2」與「5.2」都對到標題開頭的編號（「§」與空白略過）；整數編號只中「N.」、不誤中「N.M」", () => {
    expect(textOf("§5.2")).toBe("5.2 驗收標準");
    expect(textOf("5.2")).toBe("5.2 驗收標準");
    expect(textOf("§ 5.1")).toBe("5.1 功能規格");
    expect(textOf("§1")).toBe("1. 專案願景");
    expect(textOf("§1.2")).toBe("1.2 業務目標");
    expect(textOf("§9")).toBe("9. 技術選型與架構");
    expect(textOf("§7.7"), "沒有這個編號").toBeNull();
  });

  it("AT_960_16_1 編號比對是整段相等：4.2 不會誤中 4.20；標題開頭的符號（例如「§」）略過", () => {
    const own = parsePrdOutline("## 4.20 其他\n## 4.2 效能\n## §3.1 概述");
    expect(findOutlineSection(own, "§4.2")?.text).toBe("4.2 效能");
    expect(findOutlineSection(own, "4.20")?.text).toBe("4.20 其他");
    expect(findOutlineSection(own, "3.1")?.text).toBe("§3.1 概述");
    expect(findOutlineSection(own, "3"), "3 不等於 3.1").toBeNull();
  });

  it("AT_960_16_1 來源節錨點：「r2p:section=N」與「來源第 N 節」對到 `<!-- r2p:section=N -->` 之後的標題；沒有那一節回 null", () => {
    expect(textOf("r2p:section=4")).toBe("5.2 驗收標準");
    expect(textOf("來源第 2 節")).toBe("1.2 業務目標");
    expect(textOf("來源第2節")).toBe("1.2 業務目標");
    expect(textOf("§r2p:section=1")).toBe("📋 文檔元數據");
    expect(textOf("來源第 9 節")).toBeNull();
  });

  it("AT_960_16_1 其他文字（例如 AC 編號、標題字樣）對標題內容，不分大小寫；空白、單獨的「§」、找不到的文字回 null", () => {
    const own = parsePrdOutline("## 功能需求\n### AC-001-1 提交合法批次\n### Gherkin 驗收");
    expect(findOutlineSection(own, "ac-001-1")?.text).toBe("AC-001-1 提交合法批次");
    expect(findOutlineSection(own, "gherkin")?.text).toBe("Gherkin 驗收");
    expect(findOutlineSection(own, "功能")?.text).toBe("功能需求");
    expect(findOutlineSection(own, "")).toBeNull();
    expect(findOutlineSection(own, "   ")).toBeNull();
    expect(findOutlineSection(own, "§")).toBeNull();
    expect(findOutlineSection(own, "不存在的章節")).toBeNull();
    expect(findOutlineSection([], "§1")).toBeNull();
  });
});
