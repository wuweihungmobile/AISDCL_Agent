import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { BULK_EDIT_CHARS, DEFER_ABOVE_CHARS, MAX_IMPORT_BYTES, MarkdownEditorImpl, SYNC_RENDER_MAX_CHARS, safeFileName, shouldDeferPreview } from "./MarkdownEditorImpl";
import { MarkdownView } from "./MarkdownView";

/**
 * PRD §5.1.4 Markdown 編輯器八項功能的行為測試（RTM：UI-MD-01～08）。
 * 渲染端（表格、程式碼高亮、checklist）測 MarkdownView；編輯端（Split View、工具列、語法高亮、匯入匯出）測編輯器本體。
 */

function Harness({ initial = "", onNotify }: { initial?: string; onNotify?: (m: string, t: "success" | "error") => void }) {
  const [value, setValue] = useState(initial);
  return (
    <>
      <MarkdownEditorImpl value={value} onChange={setValue} label="說明描述" exportName="專案說明" onNotify={onNotify} />
      <output data-testid="value">{value}</output>
    </>
  );
}
const textarea = () => screen.getByRole("textbox", { name: "說明描述" });

describe("UI-MD-01 即時預覽（Split View）", () => {
  it("預設是左原始碼、右預覽的 live 模式；輸入後預覽即時渲染", async () => {
    const { container } = render(<Harness />);
    expect(container.querySelector(".w-md-editor-show-live")).not.toBeNull();
    expect(container.querySelector(".w-md-editor-input")).not.toBeNull();
    expect(container.querySelector(".w-md-editor-preview")).not.toBeNull();

    fireEvent.change(textarea(), { target: { value: "# 標題一\n\n**粗體**" } });
    const preview = container.querySelector(".w-md-editor-preview") as HTMLElement;
    await waitFor(() => expect(within(preview).getByRole("heading", { level: 1, name: "標題一" })).toBeInTheDocument());
    expect(preview.querySelector("strong")?.textContent).toBe("粗體");
  });
});

describe("UI-MD-02 語法高亮（編輯區原始碼著色）", () => {
  it("Markdown 標題／粗體在編輯區被切成帶 token 類別的節點", async () => {
    const { container } = render(<Harness initial={"# 標題\n\n**粗體**"} />);
    await waitFor(() => expect(container.querySelector(".w-md-editor-text-pre .token.title")).not.toBeNull());
    expect(container.querySelector(".w-md-editor-text-pre .token.bold")).not.toBeNull();
  });
});

describe("UI-MD-03 常用語法工具列", () => {
  it("工具列含 粗體、斜體、標題、清單、表格、程式碼區塊 等快捷按鈕，點粗體會在游標處插入語法", () => {
    const { container } = render(<Harness />);
    const toolbar = container.querySelector(".w-md-editor-toolbar") as HTMLElement;
    expect(toolbar).not.toBeNull();
    const labels = Array.from(toolbar.querySelectorAll("button")).map((b) => (b.getAttribute("aria-label") ?? "").toLowerCase());
    for (const keyword of ["bold", "italic", "title", "unordered list", "ordered list", "checked list", "table", "code"]) {
      expect(
        labels.some((l) => l.includes(keyword)),
        `工具列缺少「${keyword}」`,
      ).toBe(true);
    }
    const bold = Array.from(toolbar.querySelectorAll("button")).find((b) => /bold/i.test(b.getAttribute("aria-label") ?? ""))!;
    fireEvent.click(bold);
    expect(screen.getByTestId("value").textContent).toContain("****");
  });
});

describe("UI-A11Y-01 工具列圖示是裝飾（axe svg-img-alt；DEF-AC-005）", () => {
  it("工具列（左側指令與右側模式切換）的 svg 圖示全部 aria-hidden，沒有會被讀出卻沒有名字的 role=img", () => {
    const { container } = render(<Harness />);
    const svgs = Array.from(container.querySelectorAll(".w-md-editor-toolbar svg"));
    expect(svgs.length, "工具列應有圖示").toBeGreaterThan(10);
    for (const svg of svgs) expect(svg.getAttribute("aria-hidden"), svg.outerHTML.slice(0, 90)).toBe("true");
    expect(container.querySelectorAll('svg[role="img"]:not([aria-hidden="true"])')).toHaveLength(0);
  });

  it("圖示藏起來之後，每顆工具列按鈕仍靠自己的 aria-label 有名字（不能讓按鈕變成無名按鈕）", () => {
    const { container } = render(<Harness />);
    const buttons = Array.from(container.querySelectorAll(".w-md-editor-toolbar button"));
    expect(buttons.length).toBeGreaterThan(10);
    for (const b of buttons) expect(b.getAttribute("aria-label") || b.textContent, b.outerHTML.slice(0, 90)).toBeTruthy();
  });
});

describe("預覽窗（C-19／NFR-9.1-05：輸入與預覽分開排程；DEF-AC-005 同類：鍵盤可達）", () => {
  it("預覽窗是 tabIndex=0 的區域，名稱含欄位名（同頁多個編輯器各自唯一），並且還在套件的 .w-md-editor-preview 底下（捲動同步與外部選取器不受影響）", () => {
    const { container } = render(<Harness />);
    const region = screen.getByRole("region", { name: "說明描述 預覽" });
    expect(region).toHaveAttribute("tabindex", "0");
    expect(region.closest(".w-md-editor-preview")).not.toBeNull();
    expect(container.querySelectorAll(".w-md-editor-preview")).toHaveLength(1);
    // 預覽內容仍是套件的 Markdown 渲染（wmde-markdown），不是自己另寫的容器
    expect(region.querySelector(".wmde-markdown")).not.toBeNull();
  });

  it("輸入後輸入框立刻是新值，預覽稍後（deferred）跟上；預覽內容仍含 GFM 表格、程式碼高亮（hljs＋prism token）", async () => {
    const { container } = render(<Harness />);
    fireEvent.change(textarea(), { target: { value: "## 新標題\n\n```ts\nconst a = 1;\n```" } });
    expect((textarea() as HTMLTextAreaElement).value).toContain("新標題"); // 輸入框是急件：不等預覽
    const preview = container.querySelector(".w-md-editor-preview") as HTMLElement;
    await waitFor(() => expect(within(preview).getByRole("heading", { level: 2, name: "新標題" })).toBeInTheDocument());
    const code = preview.querySelector("pre code.language-ts") as HTMLElement;
    expect(code).not.toBeNull();
    expect(code.className).toContain("hljs"); // rehype-highlight（真後端 spec markdown-editor.spec.ts 也斷言這個 class）
  });
});

describe("預覽窗：大文件（超過 DEFER_ABOVE_CHARS 才分開排程）也要正確跟上輸入", () => {
  it("超過門檻的文件：預覽最終顯示最後一次輸入的內容（中間的值可以被跳過，但最終值不能丟）", async () => {
    const big = "## 大文件\n\n" + "這是一段說明文字，用來把文件撐到門檻以上。\n\n".repeat(Math.ceil(DEFER_ABOVE_CHARS / 20));
    expect(big.length).toBeGreaterThan(DEFER_ABOVE_CHARS);
    const { container } = render(<Harness initial={big} />);
    const preview = container.querySelector(".w-md-editor-preview") as HTMLElement;
    await waitFor(() => expect(within(preview).getByRole("heading", { level: 2, name: "大文件" })).toBeInTheDocument(), { timeout: 5000 });
    // 連續兩次輸入（模擬打字）：最終預覽必須是第二次的內容
    fireEvent.change(textarea(), { target: { value: big + "\n\n第一次" } });
    fireEvent.change(textarea(), { target: { value: big + "\n\n## 最終標題" } });
    await waitFor(() => expect(within(preview).getByRole("heading", { level: 2, name: "最終標題" })).toBeInTheDocument(), { timeout: 5000 });
    expect(within(preview).queryByText("第一次")).toBeNull();
  });

  it("批次貼入（一次差上萬字，例如把 20KB 文件貼進空欄位）：預覽一次到位，內容與區塊數都正確", async () => {
    const section = (i: number) => `## 區塊 ${i}\n\n\`\`\`python\nprint(${i})\n\`\`\`\n\n`;
    const pasted = Array.from({ length: 300 }, (_, i) => section(i + 1)).join("");
    expect(pasted.length).toBeGreaterThan(DEFER_ABOVE_CHARS);
    expect(pasted.length).toBeLessThanOrEqual(SYNC_RENDER_MAX_CHARS);
    expect(pasted.length).toBeGreaterThan(BULK_EDIT_CHARS);
    const { container } = render(<Harness />);
    fireEvent.change(textarea(), { target: { value: pasted } });
    const preview = container.querySelector(".w-md-editor-preview") as HTMLElement;
    await waitFor(() => expect(within(preview).getByRole("heading", { level: 2, name: "區塊 300" })).toBeInTheDocument(), { timeout: 15000 });
    expect(within(preview).getAllByRole("heading", { level: 2 })).toHaveLength(300);
    expect(preview.querySelectorAll("pre code.language-python")).toHaveLength(300);
    // 之後回到連續打字：落後只有幾個字，仍走排程（deferred），最終值不能丟
    fireEvent.change(textarea(), { target: { value: `${pasted}## 打字加的標題\n` } });
    await waitFor(() => expect(within(preview).getByRole("heading", { level: 2, name: "打字加的標題" })).toBeInTheDocument(), { timeout: 15000 });
  }, 30000);
});

describe("預覽何時排到輸入之後（NFR-9.1-05：shouldDeferPreview）", () => {
  const DOC_20KB = 14000; // p9 量法的 20KB 文件約 14,000 字

  it("小文件不排：一幀內就渲染完，分兩段只會多等一個畫面", () => {
    expect(shouldDeferPreview(DEFER_ABOVE_CHARS, 0)).toBe(false);
    expect(shouldDeferPreview(500, 499)).toBe(false);
  });

  it("大文件連續打字（預覽只落後幾個字）要排：連續輸入時中間的值直接被跳過；剛好在批次門檻上還不算批次", () => {
    expect(shouldDeferPreview(DOC_20KB, DOC_20KB - 1)).toBe(true);
    expect(shouldDeferPreview(DOC_20KB, DOC_20KB)).toBe(true); // 已追上：shown 與 source 相同，排不排結果一樣
    expect(shouldDeferPreview(DOC_20KB, DOC_20KB - BULK_EDIT_CHARS)).toBe(true);
    expect(shouldDeferPreview(DOC_20KB - BULK_EDIT_CHARS, DOC_20KB)).toBe(true); // 刪掉一整段但沒超過門檻
  });

  it("批次變更（貼上、匯入、復原）一次渲染到位：預覽落後超過門檻，不再多插一個畫面", () => {
    expect(shouldDeferPreview(DOC_20KB, 0)).toBe(false); // 20KB 貼進空欄位（p9 的量法）
    expect(shouldDeferPreview(DOC_20KB, DOC_20KB - BULK_EDIT_CHARS - 1)).toBe(false);
    expect(shouldDeferPreview(DOC_20KB, DOC_20KB + 5000)).toBe(false); // 刪掉一大段後仍是大文件
  });

  it("批次但文件太大（超過 SYNC_RENDER_MAX_CHARS）：仍然排，免得一次貼進超大文件時整頁卡住", () => {
    expect(shouldDeferPreview(SYNC_RENDER_MAX_CHARS, 0)).toBe(false);
    expect(shouldDeferPreview(SYNC_RENDER_MAX_CHARS + 1, 0)).toBe(true);
    expect(shouldDeferPreview(1_000_000, 0)).toBe(true);
  });
});

describe("UI-A11Y-01 核取清單的核取方塊要有名稱（axe aria-toggle-field-name；DEF-AC-005 同類）", () => {
  it("唯讀渲染：每個核取方塊的名稱＝該項目的文字；巢狀子清單的文字不混進父項目的名稱", () => {
    render(<MarkdownView source={"- [ ] 父項目\n  - [x] 子項目一\n  - [ ] 子項目二\n- [x] **粗體** 與 `code` 的項目"} />);
    expect(screen.getByRole("checkbox", { name: "父項目" })).toHaveAttribute("aria-checked", "false");
    expect(screen.getByRole("checkbox", { name: "子項目一" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("checkbox", { name: "子項目二" })).toHaveAttribute("aria-checked", "false");
    expect(screen.getByRole("checkbox", { name: "粗體 與 code 的項目" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getAllByRole("checkbox")).toHaveLength(4);
  });

  it("鬆散清單（項目之間有空行，核取方塊在 <p> 裡）也有名稱；一般清單不受影響", () => {
    render(<MarkdownView source={"- [ ] 第一項\n\n- [x] 第二項\n\n- 普通項目"} />);
    expect(screen.getByRole("checkbox", { name: "第一項" })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "第二項" })).toBeInTheDocument();
    expect(screen.getAllByRole("checkbox")).toHaveLength(2);
    expect(screen.getByText("普通項目")).toBeInTheDocument();
  });

  it("編輯器預覽端的核取方塊（原生 input）同樣有名稱", async () => {
    const { container } = render(<Harness initial={"- [ ] 預覽中的待辦\n- [x] 預覽中的完成項"} />);
    const preview = container.querySelector(".w-md-editor-preview") as HTMLElement;
    await waitFor(() => expect(within(preview).getByRole("checkbox", { name: "預覽中的待辦" })).toBeInTheDocument());
    expect(within(preview).getByRole("checkbox", { name: "預覽中的完成項" })).toBeChecked();
  });
});

describe("UI-MD-04／05／06 渲染端：GFM 表格、程式碼區塊語言高亮、Checklist", () => {
  it("GFM 表格渲染成 <table>（含表頭與資料列）", () => {
    const { container } = render(<MarkdownView source={"| 欄位 | 說明 |\n| --- | --- |\n| id | 唯一識別碼 |"} />);
    const table = container.querySelector("table") as HTMLElement;
    expect(table).not.toBeNull();
    expect(within(table).getByRole("columnheader", { name: "欄位" })).toBeInTheDocument();
    expect(within(table).getByRole("cell", { name: "唯一識別碼" })).toBeInTheDocument();
  });

  it("帶語言標示的程式碼區塊有語法高亮（highlight.js 類別）；沒標語言則不亂猜", () => {
    const { container } = render(<MarkdownView source={"```ts\nconst answer: number = 42;\n```\n\n```\nplain text\n```"} />);
    const blocks = container.querySelectorAll("pre code");
    expect(blocks).toHaveLength(2);
    expect(blocks[0].className).toContain("language-ts");
    expect(blocks[0].querySelector(".hljs-keyword")?.textContent).toBe("const");
    expect(blocks[1].querySelector("[class^='hljs-']")).toBeNull();
  });

  it("checklist（- [ ] / - [x]）渲染成 18px 唯讀核取方塊，勾選狀態正確", () => {
    render(<MarkdownView variant="criteria" source={"- [ ] 所有核心模組通過單元測試\n- [x] API 契約驗證通過"} />);
    const boxes = screen.getAllByRole("checkbox");
    expect(boxes).toHaveLength(2);
    expect(boxes[0]).toHaveAttribute("aria-checked", "false");
    expect(boxes[1]).toHaveAttribute("aria-checked", "true");
    expect(boxes[1]).toHaveAttribute("aria-readonly", "true");
    expect(boxes[1].className).toContain("size-[18px]");
    expect(screen.getByText("API 契約驗證通過")).toBeInTheDocument();
  });

  it("不渲染原始 HTML（避免 XSS），空內容顯示占位文字", () => {
    const { container } = render(<MarkdownView source={'<img src=x onerror="alert(1)"><script>alert(1)</script>安全'} />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
    render(<MarkdownView source="   " empty="（尚未填寫）" />);
    expect(screen.getByText("（尚未填寫）")).toBeInTheDocument();
  });

  it("外部連結以新分頁開啟並帶 noopener", () => {
    render(<MarkdownView source="[官網](https://example.com) 與 [站內](/projects)" />);
    expect(screen.getByRole("link", { name: "官網" })).toHaveAttribute("target", "_blank");
    expect(screen.getByRole("link", { name: "官網" })).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByRole("link", { name: "站內" })).not.toHaveAttribute("target");
  });
});

describe("UI-MD-07 匯入 .md 檔案", () => {
  const file = (content: string, name = "spec.md", type = "text/markdown") => new File([content], name, { type });

  it("選擇 .md 檔後內容直接填入編輯器並通知成功", async () => {
    const onNotify = vi.fn();
    render(<Harness initial="舊內容" onNotify={onNotify} />);
    await userEvent.upload(screen.getByTestId("md-import-input"), file("# 匯入的標題\n\n- [x] 完成"));
    await waitFor(() => expect(screen.getByTestId("value").textContent).toBe("# 匯入的標題\n\n- [x] 完成"));
    expect(onNotify).toHaveBeenCalledWith("已匯入 spec.md", "success");
  });

  it("拒絕非文字副檔名與超過上限的檔案，編輯器內容不變", async () => {
    const onNotify = vi.fn();
    render(<Harness initial="保持不變" onNotify={onNotify} />);
    const input = screen.getByTestId("md-import-input");
    // userEvent.upload 會依 accept 過濾；改用 fireEvent 才能模擬「使用者硬選了不合規的檔」
    fireEvent.change(input, { target: { files: [file("x", "malware.exe", "application/octet-stream")] } });
    expect(onNotify).toHaveBeenLastCalledWith("只支援 .md／.markdown／.txt 文字檔", "error");
    const big = file("x".repeat(10), "big.md");
    Object.defineProperty(big, "size", { value: MAX_IMPORT_BYTES + 1 });
    fireEvent.change(input, { target: { files: [big] } });
    expect(onNotify).toHaveBeenLastCalledWith("檔案超過 1 MB 上限", "error");
    expect(screen.getByTestId("value").textContent).toBe("保持不變");
  });
});

describe("UI-MD-08 匯出 .md 檔案", () => {
  it("按「匯出 .md」以 Blob 下載，檔名為「<名稱>.md」且內容等於編輯器內容；空內容時停用", async () => {
    const createObjectURL = vi.fn(() => "blob:mock");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL, revokeObjectURL }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      expect(this.download).toBe("專案說明.md");
      expect(this.href).toContain("blob:mock");
    });
    const onNotify = vi.fn();
    render(<Harness initial="" onNotify={onNotify} />);
    expect(screen.getByRole("button", { name: "匯出 .md" })).toBeDisabled();

    fireEvent.change(textarea(), { target: { value: "# 匯出內容\n\n中文也 OK" } });
    await userEvent.click(screen.getByRole("button", { name: "匯出 .md" }));
    expect(click).toHaveBeenCalledTimes(1);
    const blob = (createObjectURL.mock.calls[0] as unknown as [Blob])[0];
    expect(blob.type).toContain("text/markdown");
    expect(await blob.text()).toBe("# 匯出內容\n\n中文也 OK");
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:mock");
    expect(onNotify).toHaveBeenCalledWith("已匯出 專案說明.md", "success");
  });

  it("檔名只留安全字元（路徑穿越與跨平台非法字元）", () => {
    expect(safeFileName("../../etc/passwd")).toBe("_.._etc_passwd");
    expect(safeFileName('a:b*c?"d')).toBe("a_b_c__d");
    expect(safeFileName("   ")).toBe("content");
  });
});
