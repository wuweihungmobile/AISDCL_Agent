import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { MAX_IMPORT_BYTES, MarkdownEditorImpl, safeFileName } from "./MarkdownEditorImpl";
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
      expect(labels.some((l) => l.includes(keyword)), `工具列缺少「${keyword}」`).toBe(true);
    }
    const bold = Array.from(toolbar.querySelectorAll("button")).find((b) => /bold/i.test(b.getAttribute("aria-label") ?? ""))!;
    fireEvent.click(bold);
    expect(screen.getByTestId("value").textContent).toContain("****");
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
