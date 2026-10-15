import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import { REASONS } from "@/lib/api/reasons";
import type { ImportRecordDetail } from "@/lib/api/types";
import { parseFailureFromError } from "./gateErrors";
import { SourceCard } from "./SourceCard";

type Props = Parameters<typeof SourceCard>[0];

function setup(over: Partial<Props> = {}) {
  const props: Props = {
    existing: null,
    canWrite: true,
    busy: false,
    defaultAutonomy: 3,
    failure: null,
    sourceError: null,
    fieldErrors: {},
    onStart: vi.fn(),
    onLeaveExisting: vi.fn(),
    onOpenFromHistory: vi.fn(),
    ...over,
  };
  const view = render(<SourceCard {...props} />);
  return Object.assign(props, { rerender: (next: Partial<Props>) => view.rerender(<SourceCard {...props} {...next} />) });
}

const mdFile = () => new File(["# BRD\n需求"], "brd.md", { type: "text/markdown" });
const pickFile = (file: File) => fireEvent.change(screen.getByTestId("import-file-input"), { target: { files: [file] } });
const fillPath = (value = "/home/user/projects/new-service") => userEvent.type(screen.getByLabelText("執行路徑"), value);

describe("步驟 1：來源 tab（US-I-01／02／06）", () => {
  it("三個 tab：上傳檔案、貼上文字、歷史記錄；預設在上傳檔案，拖放區說明格式與 10MB 上限", () => {
    setup();
    const tabs = screen.getAllByRole("tab").map((t) => t.textContent);
    expect(tabs).toEqual(["上傳檔案", "貼上文字", "歷史記錄"]);
    expect(screen.getByRole("tab", { name: "上傳檔案" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("import-dropzone")).toHaveTextContent("拖曳檔案至此，或點擊選擇");
    expect(screen.getByTestId("import-dropzone")).toHaveTextContent(".md · .pdf · .docx");
    expect(screen.getByTestId("import-dropzone")).toHaveTextContent("10MB");
  });

  it("拖放區：拖曳經過時有 hover 態，放下檔案後顯示檔名與大小，可移除", async () => {
    setup();
    const zone = screen.getByTestId("import-dropzone");
    fireEvent.dragOver(zone);
    expect(zone.className).toContain("border-wg-primary");
    fireEvent.dragLeave(zone);
    expect(zone.className).not.toContain("bg-wg-tertiary");
    fireEvent.drop(zone, { dataTransfer: { files: [mdFile()] } });
    expect(screen.getByTestId("selected-file")).toHaveTextContent("brd.md");
    await userEvent.click(screen.getByRole("button", { name: "移除檔案" }));
    expect(screen.queryByTestId("selected-file")).toBeNull();
  });

  it("副檔名不支援、超過 10MB、空檔：當場以契約 reason 逐字提示，不收下檔案", () => {
    setup();
    pickFile(new File(["x"], "notes.txt"));
    expect(screen.getByTestId("source-error")).toHaveTextContent(REASONS.IMPORT_UNSUPPORTED_EXTENSION);
    expect(screen.queryByTestId("selected-file")).toBeNull();

    const big = new File(["x"], "big.pdf");
    Object.defineProperty(big, "size", { value: 10 * 1024 * 1024 + 1 });
    pickFile(big);
    expect(screen.getByTestId("source-error")).toHaveTextContent(REASONS.IMPORT_FILE_TOO_LARGE);

    pickFile(new File([], "empty.md"));
    expect(screen.getByTestId("source-error")).toHaveTextContent(REASONS.IMPORT_EMPTY_FILE);

    pickFile(mdFile());
    expect(screen.queryByTestId("source-error")).toBeNull();
    expect(screen.getByTestId("selected-file")).toBeInTheDocument();
  });
});

describe("步驟 1：解析選項與開始解析（US-I-05／07／08）", () => {
  it("沒有來源或沒有路徑：行內錯誤、不呼叫 onStart", async () => {
    const props = setup();
    await userEvent.click(screen.getByRole("button", { name: "開始解析" }));
    expect(screen.getByTestId("source-error")).toHaveTextContent("請選擇要上傳的檔案");
    expect(screen.getByText("執行路徑不能為空")).toBeInTheDocument();
    expect(props.onStart).not.toHaveBeenCalled();
  });

  it("執行路徑必須是絕對路徑（POSIX、磁碟機代號、UNC 都可）；相對路徑擋下", async () => {
    const props = setup();
    pickFile(mdFile());
    await fillPath("relative/path");
    await userEvent.click(screen.getByRole("button", { name: "開始解析" }));
    expect(screen.getByText(/必須是絕對路徑/)).toBeInTheDocument();
    expect(props.onStart).not.toHaveBeenCalled();

    await userEvent.clear(screen.getByLabelText("執行路徑"));
    await fillPath("C:\\Projects\\new-service");
    await userEvent.click(screen.getByRole("button", { name: "開始解析" }));
    expect(props.onStart).toHaveBeenCalledTimes(1);
  });

  it("檔案來源：以預設自治等級與路徑送出（補充說明去頭尾空白；空白不送）", async () => {
    const props = setup({ defaultAutonomy: 5 });
    const file = mdFile();
    pickFile(file);
    await fillPath();
    await userEvent.click(screen.getByRole("button", { name: "開始解析" }));
    expect(props.onStart).toHaveBeenCalledWith({
      source: { kind: "file", file },
      options: { autonomyLevel: 5, executionPath: "/home/user/projects/new-service", additionalPrompt: undefined },
    });
  });

  it("自治等級下拉 Level 1～10，改選後帶入；補充說明一併送出", async () => {
    const props = setup();
    const select = screen.getByLabelText(/^自治等級/);
    expect(within(select).getAllByRole("option")).toHaveLength(10);
    expect(select).toHaveValue("3");
    await userEvent.selectOptions(select, "7");
    pickFile(mdFile());
    await fillPath();
    await userEvent.type(screen.getByLabelText(/^補充說明/), " 盡量少於 5 個任務 ");
    await userEvent.click(screen.getByRole("button", { name: "開始解析" }));
    expect(props.onStart).toHaveBeenCalledWith(
      expect.objectContaining({ options: { autonomyLevel: 7, executionPath: "/home/user/projects/new-service", additionalPrompt: "盡量少於 5 個任務" } }),
    );
  });

  it("貼上文字：空白擋下；填入後連同來源名稱與格式送出", async () => {
    const props = setup();
    await userEvent.click(screen.getByRole("tab", { name: "貼上文字" }));
    await fillPath();
    await userEvent.click(screen.getByRole("button", { name: "開始解析" }));
    expect(screen.getByText("請貼上需求文字")).toBeInTheDocument();
    expect(props.onStart).not.toHaveBeenCalled();

    await userEvent.type(screen.getByLabelText(/^需求文字/), "# BRD 內容");
    await userEvent.type(screen.getByLabelText(/^來源名稱/), "e2e-brd.md");
    await userEvent.selectOptions(screen.getByLabelText(/^格式/), "MARKDOWN");
    await userEvent.click(screen.getByRole("button", { name: "開始解析" }));
    expect(props.onStart).toHaveBeenCalledWith({
      source: { kind: "text", content: "# BRD 內容", sourceFileName: "e2e-brd.md", sourceType: "MARKDOWN" },
      options: { autonomyLevel: 3, executionPath: "/home/user/projects/new-service", additionalPrompt: undefined },
    });
  });

  it("路徑欄位提示本機與 Docker 兩種寫法（Architecture L-8）", () => {
    setup();
    expect(screen.getByLabelText("執行路徑")).toHaveClass("font-mono");
    expect(screen.getByText(/Docker 全棧填 Bridge 容器內的路徑/)).toBeInTheDocument();
    expect(screen.getByText(/本機開發填主機路徑/)).toBeInTheDocument();
  });
});

describe("步驟 1：解析失敗後重試（US-I-10）", () => {
  it("失敗清單顯示在卡內（逐項、完整）；後端 400 的欄位錯誤顯示在對應欄位", () => {
    const failure = parseFailureFromError(
      new ApiError({
        status: 422,
        message: "解析結果未通過有界閘",
        reason: REASONS.IMPORT_GATE_REJECTED,
        errors: [
          { field: "goals[0].tasks", message: "m", gate: "max_steps", detail: "目標「A」的任務數 25 超過上限 24", location: "goals[0].tasks" },
          { field: "goals[1].dependsOn", message: "m", gate: "cycle", detail: "目標依賴成環：A -> B -> A", location: "goals[1].dependsOn" },
        ] as never,
      }),
    );
    setup({ failure, fieldErrors: { executionPath: "必須是絕對路徑" } });
    expect(screen.getAllByTestId("gate-error-row")).toHaveLength(2);
    expect(screen.getByText("目標依賴成環：A -> B -> A")).toBeInTheDocument();
    expect(screen.getByText("必須是絕對路徑")).toBeInTheDocument();
  });

  it("建立記錄階段（上傳／貼上）的失敗說明：按過開始解析才出現，且只顯示在當時的 tab，切走就不跟過去", async () => {
    setup({ sourceError: "檔案超過 10MB 上限（traceId：tr-413）" });
    expect(screen.queryByTestId("source-error")).toBeNull(); // 還沒按過，不顯示上一輪的殘留
    pickFile(mdFile());
    await fillPath();
    await userEvent.click(screen.getByRole("button", { name: "開始解析" }));
    expect(screen.getByTestId("source-error")).toHaveTextContent("檔案超過 10MB 上限（traceId：tr-413）");
    await userEvent.click(screen.getByRole("tab", { name: "貼上文字" }));
    expect(screen.queryByText(/檔案超過 10MB 上限/)).toBeNull();
  });
});

describe("步驟 1：沿用既有記錄（從歷史重開，或解析被擋下後）", () => {
  const existing: ImportRecordDetail = {
    id: "I1",
    sourceType: "MARKDOWN",
    sourceFileName: "e2e-brd.md",
    status: "UPLOADED",
    signedOff: false,
    createdAt: "2026-10-15T08:30:12Z",
    sourceContent: "# BRD\n這是上一次貼上的需求原文",
    parsedResult: null,
  };

  it("顯示來源摘要而非拖放區；開始解析只送解析選項（不重複上傳）", async () => {
    const props = setup({ existing });
    const panel = screen.getByTestId("existing-source");
    expect(panel).toHaveTextContent("e2e-brd.md");
    expect(panel).toHaveTextContent("Markdown");
    expect(panel).toHaveTextContent("這是上一次貼上的需求原文");
    expect(screen.queryByTestId("import-dropzone")).toBeNull();
    await fillPath();
    await userEvent.click(screen.getByRole("button", { name: "開始解析" }));
    expect(props.onStart).toHaveBeenCalledWith({
      source: { kind: "existing" },
      options: { autonomyLevel: 3, executionPath: "/home/user/projects/new-service", additionalPrompt: undefined },
    });
  });

  it("改用其他來源：原文帶回「貼上文字」供修改，並通知父層清掉目前記錄", async () => {
    const view = setup({ existing });
    await userEvent.click(screen.getByRole("button", { name: "改用其他來源" }));
    expect(view.onLeaveExisting).toHaveBeenCalledTimes(1);
    view.rerender({ existing: null }); // 父層收到通知後清掉目前記錄
    expect(screen.getByRole("tab", { name: "貼上文字" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByLabelText(/^需求文字/)).toHaveValue("# BRD\n這是上一次貼上的需求原文");
    expect(screen.getByLabelText(/^來源名稱/)).toHaveValue("e2e-brd.md");
  });
});

describe("唯讀角色", () => {
  it("拖放區、欄位與「開始解析」全部停用並附說明", () => {
    setup({ canWrite: false });
    expect(screen.getByTestId("import-dropzone")).toBeDisabled();
    expect(screen.getByRole("button", { name: "開始解析" })).toBeDisabled();
    expect(screen.getByLabelText("執行路徑")).toBeDisabled();
    expect(screen.getByRole("button", { name: "開始解析" })).toHaveAttribute("title", "權限不足（唯讀角色）");
  });
});
