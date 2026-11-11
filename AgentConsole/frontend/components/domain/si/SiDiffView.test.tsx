/**
 * 「變更內容」分頁（TCS-SiFlowVisibility AC-966-7：AT-966-7-1～7-5、7-E-1、7-E-2）。直接渲染 SiDiffView（純顯示元件，沒有網路請求）。
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SI_FLOW_TEXTS, parseDiff } from "@/lib/domain/siFlow";
import { patchMixed } from "@/tests/helpers/siFlow";
import { SiDiffView } from "./SiDiffView";

const REL = "docs/06_quality/SelfImproving_Proposals/PROP-SI-901/r2.patch";
const patch = (text: string, truncated = false) => ({ rel: REL, bytes: Buffer.byteLength(text), text, truncated });
const view = (p: unknown, ne: Array<{ field: string; reason: string; text?: unknown }> = []) => render(<SiDiffView propId="PROP-SI-901" rev={2} patch={p} ne={ne} />);
const lines = () => Array.from(document.querySelectorAll<HTMLElement>("[data-diff-kind]"));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("AT_966_7_1 逐行原文、種類與計數句", () => {
  it("每行一個 data-diff-kind 元素，原文以換行連接逐字等於輸入，計數句與位元組數", () => {
    view(patch(patchMixed));
    const els = lines();
    const expected = parseDiff(patchMixed);
    expect(els.map((e) => e.dataset.diffKind)).toEqual(expected.lines.map((l) => l.kind));
    expect(new Set(els.map((e) => e.dataset.diffKind))).toEqual(new Set(["add", "del", "hunk", "file", "meta", "ctx"]));
    expect(els.map((e) => e.querySelector(".diff-text")?.textContent).join("\n") + "\n").toBe(patchMixed);
    expect(screen.getByTestId("si-diff-summary")).toHaveTextContent(`新增 ${expected.addCount} 行、刪除 ${expected.delCount} 行`);
    expect(screen.getByTestId("si-diff-view")).toHaveTextContent(REL);
    expect(screen.getByTestId("si-diff-view")).toHaveTextContent(`${Buffer.byteLength(patchMixed)} 位元組`);
  });
});

describe("AT_966_7_2 顏色以外的標示", () => {
  it("符號、邊框形狀與讀屏前綴足以分類（移除全部顏色 class 後結果不變）", () => {
    view(patch("@@ -1 +1 @@\n 上下文\n-舊\n+新\n"));
    const els = lines();
    const byKind = (k: string) => els.find((e) => e.dataset.diffKind === k) as HTMLElement;
    expect(byKind("add").querySelector(".diff-text")?.textContent?.startsWith("+")).toBe(true);
    expect(byKind("add").className).toContain("border-solid");
    expect(byKind("add").querySelector(".sr-only")).toHaveTextContent("新增：");
    expect(byKind("del").querySelector(".diff-text")?.textContent?.startsWith("-")).toBe(true);
    expect(byKind("del").className).toContain("border-dashed");
    expect(byKind("del").querySelector(".sr-only")).toHaveTextContent("刪除：");
    expect(byKind("hunk").querySelector(".diff-text")?.textContent?.startsWith("@@")).toBe(true);
    expect(byKind("hunk").className).toContain("font-bold");
    expect(byKind("hunk").querySelector(".sr-only")).toHaveTextContent("區段：");
    expect(byKind("ctx").querySelector(".sr-only")).toBeNull();
    // 去掉顏色 class（bg-、text-wg-）後，只靠符號、邊框形狀、讀屏前綴重新分類，結果與原分類全等
    const reclassify = (e: HTMLElement) => {
      const classes = e.className.split(/\s+/).filter((c) => !/^bg-/.test(c) && !/^text-wg-/.test(c));
      const text = e.querySelector(".diff-text")?.textContent ?? "";
      const prefix = e.querySelector(".sr-only")?.textContent ?? "";
      if (prefix === "區段：" && text.startsWith("@@")) return "hunk";
      if (prefix === "新增：" && text.startsWith("+") && classes.includes("border-solid")) return "add";
      if (prefix === "刪除：" && text.startsWith("-") && classes.includes("border-dashed")) return "del";
      return "ctx";
    };
    expect(els.map(reclassify)).toEqual(els.map((e) => e.dataset.diffKind));
    for (const e of els) expect(e.querySelector(".diff-text")?.textContent).not.toMatch(/新增：|刪除：|區段：/);
  });
});

describe("AT_966_7_3 截斷提示與下載", () => {
  function stubDownload() {
    const created: Blob[] = [];
    const revoke = vi.fn();
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: (b: Blob) => (created.push(b), "blob:test"), revokeObjectURL: revoke }));
    const names: string[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      names.push(this.download);
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    return { created, revoke, names, fetchSpy };
  }
  it("未截斷：無提示、檔名與內容逐字", async () => {
    const d = stubDownload();
    view(patch("+a\n"));
    expect(screen.queryByTestId("si-diff-truncated")).toBeNull();
    await userEvent.setup({ delay: null }).click(screen.getByRole("button", { name: "下載 patch 檔" }));
    expect(d.names).toEqual(["PROP-SI-901-r2.patch"]);
    expect(await d.created[0].text()).toBe("+a\n");
    expect(d.created[0].type).toBe("text/plain;charset=utf-8");
    expect(d.revoke).toHaveBeenCalledTimes(1);
    expect(d.fetchSpy).not.toHaveBeenCalled();
  });
  it("已截斷：提示含完整檔路徑、檔名帶 truncated、旁註明說是截斷後的內容", async () => {
    const d = stubDownload();
    view(patch("+a\n", true));
    expect(screen.getByTestId("si-diff-truncated")).toHaveTextContent(`內容過長已截斷，完整檔在 ${REL}`);
    expect(screen.getByText("這是截斷後的內容")).toBeInTheDocument();
    await userEvent.setup({ delay: null }).click(screen.getByRole("button", { name: "下載 patch 檔" }));
    expect(d.names).toEqual(["PROP-SI-901-r2.truncated.patch"]);
    expect(d.revoke).toHaveBeenCalledTimes(1);
    expect(d.fetchSpy).not.toHaveBeenCalled();
  });
});

describe("AT_966_7_4 400 行視窗與展開", () => {
  const big = (n: number) => Array.from({ length: n }, (_, i) => `+行${i}`).join("\n");
  it("1000 行：初始 400、展開 1000、再收合 400，aria-expanded 與狀態一致", async () => {
    const user = userEvent.setup({ delay: null });
    view(patch(big(1000)));
    expect(lines()).toHaveLength(400);
    const toggle = screen.getByRole("button", { name: "展開全部（1000 行）" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await user.click(toggle);
    expect(lines()).toHaveLength(1000);
    const collapse = screen.getByRole("button", { name: "只看前 400 行" });
    expect(collapse).toHaveAttribute("aria-expanded", "true");
    await user.click(collapse);
    expect(lines()).toHaveLength(400);
  });
  it("400 行沒有展開鈕；401 行顯示『展開全部（401 行）』", () => {
    view(patch(big(400)));
    expect(screen.queryByRole("button", { name: /展開全部/ })).toBeNull();
    cleanup();
    view(patch(big(401)));
    expect(screen.getByRole("button", { name: "展開全部（401 行）" })).toBeInTheDocument();
  });
});

describe("AT_966_7_5 patch 為 null、空字串", () => {
  it("(a) null 且有對應 ne：量不到加原因（無 text 用保底句），沒有下載鈕與計數句", () => {
    view(null, [{ field: "proposals.PROP-SI-901.detail.patch", reason: "PATCH-UNREADABLE" }]);
    expect(screen.getByText("變更內容量不到")).toBeInTheDocument();
    expect(screen.getByTestId("si-diff-missing")).toHaveTextContent("主機沒有提供白話說明（原因碼 PATCH-UNREADABLE）。");
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.queryByTestId("si-diff-summary")).toBeNull();
  });
  it("(a2) ne 帶白話 text 時逐字顯示", () => {
    view(null, [{ field: "proposals.PROP-SI-901.detail.patch", reason: "PATCH-UNREADABLE", text: "修補檔讀不到" }]);
    expect(screen.getByTestId("si-diff-missing")).toHaveTextContent("修補檔讀不到");
  });
  it("(b) 空字串：這個提案沒有變更內容", () => {
    view(patch(""));
    expect(screen.getByText("這個提案沒有變更內容")).toBeInTheDocument();
    expect(screen.queryByText("變更內容量不到")).toBeNull();
  });
  it("(c) null 且沒有對應 ne：仍是量不到，不改說沒有變更", () => {
    view(null, []);
    expect(screen.getByText("變更內容量不到")).toBeInTheDocument();
    expect(screen.queryByText("這個提案沒有變更內容")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });
});

describe("AT_966_7_E_1 256 KiB 夾具視窗化", () => {
  it("初始 400 行、DOM 節點數 < 5000；展開後等於解析行數；不丟例外", async () => {
    const text = Array.from({ length: 6000 }, (_, i) => (i % 3 === 0 ? `+新增行 ${i}` : i % 3 === 1 ? `-刪除行 ${i}` : ` 上下文 ${i}`)).join("\n");
    const { container } = view(patch(text));
    expect(lines()).toHaveLength(400);
    expect(container.querySelectorAll("*").length).toBeLessThan(5000);
    await userEvent.setup({ delay: null }).click(screen.getByRole("button", { name: /展開全部/ }));
    expect(lines()).toHaveLength(parseDiff(text).lines.length);
  });
});

describe("AT_966_7_E_2 單行超長", () => {
  it("恰一個 add 元素、容器可橫向捲動且不換行、200001 字元完整", () => {
    const { container } = view(patch("+" + "x".repeat(200000)));
    const els = lines();
    expect(els).toHaveLength(1);
    expect(els[0].dataset.diffKind).toBe("add");
    expect(els[0].querySelector(".diff-text")?.textContent).toHaveLength(200001);
    const scroller = within(container).getByTestId("si-diff-lines");
    expect(scroller.className).toContain("overflow-x-auto");
    expect(scroller.className).toContain("whitespace-pre");
    // 可捲動容器須能用鍵盤聚焦並有名稱（TCS 勘誤 E-16；axe scrollable-region-focusable）
    expect(scroller).toHaveAttribute("role", "region");
    expect(scroller).toHaveAttribute("tabindex", "0");
    expect(scroller).toHaveAttribute("aria-label", SI_FLOW_TEXTS.diffScroll);
  });
});
