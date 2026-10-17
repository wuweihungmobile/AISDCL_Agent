import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ImportRecordDetail } from "@/lib/api/types";
import { SourceCard, type TargetProjectOption } from "./SourceCard";

type Props = Parameters<typeof SourceCard>[0];

/**
 * 匯入步驟 1 的「匯入到既有專案」（契約 §1.10.8；整合輪 115，API-IMP-12）：
 * 選了目標專案＝parse 帶 targetProjectId，執行路徑一律取自該專案（唯讀）；規格目錄、規格檔、FSM 專案由後端取自目標專案，畫面不送。
 */
const CORE: TargetProjectOption = { id: "0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02", name: "AISDLC Core Platform", executionPath: "/work/core" };
const OTHER: TargetProjectOption = { id: "1a2b3c4d-0000-4000-8000-000000000001", name: "第二個專案", executionPath: "D:\\work\\second" };

function setup(over: Partial<Props> = {}) {
  const props: Props = {
    existing: null,
    canWrite: true,
    busy: false,
    defaultAutonomy: 3,
    failure: null,
    sourceError: null,
    fieldErrors: {},
    projects: [CORE, OTHER],
    onStart: vi.fn(),
    onLeaveExisting: vi.fn(),
    onOpenFromHistory: vi.fn(),
    ...over,
  };
  const view = render(<SourceCard {...props} />);
  return Object.assign(props, { rerender: (next: Partial<Props>) => view.rerender(<SourceCard {...props} {...next} />) });
}

const mdFile = () => new File(["# TCS\n規格"], "TCS-Alpha.md", { type: "text/markdown" });
const pickFile = () => fireEvent.change(screen.getByTestId("import-file-input"), { target: { files: [mdFile()] } });
const select = () => screen.getByLabelText(/^匯入到既有專案/) as HTMLSelectElement;
const start = () => userEvent.click(screen.getByRole("button", { name: "開始解析" }));
const lastOptions = (props: Props) => (props.onStart as ReturnType<typeof vi.fn>).mock.calls.at(-1)?.[0].options;

describe("匯入到既有專案：選擇器", () => {
  it("預設「建立新專案（預設）」；選項依序列出未刪除的專案名；說明文字講清楚兩種結果", () => {
    setup();
    expect(select().value).toBe("");
    expect([...select().options].map((o) => o.text)).toEqual(["建立新專案（預設）", "AISDLC Core Platform", "第二個專案"]);
    expect(screen.getByTestId("import-target-hint")).toHaveTextContent("不選：建立新專案");
    expect(screen.getByLabelText("執行路徑")).not.toHaveAttribute("readonly");
  });

  it("沒有給專案清單（頁面還在載入、或讀不到）：選擇器只有「建立新專案」，其餘行為不變", () => {
    setup({ projects: undefined });
    expect([...select().options].map((o) => o.text)).toEqual(["建立新專案（預設）"]);
  });

  it("選了專案：執行路徑換成該專案的路徑並唯讀、顯示「取自目標專案」說明；說明文字改成併入規則", async () => {
    setup();
    await userEvent.selectOptions(select(), CORE.id);
    expect(screen.getByLabelText("執行路徑")).toHaveValue("/work/core");
    expect(screen.getByLabelText("執行路徑")).toHaveAttribute("readonly");
    expect(screen.getByTestId("import-target-path-note")).toHaveTextContent("執行路徑取自目標專案「AISDLC Core Platform」，不可修改");
    expect(screen.getByTestId("import-target-hint")).toHaveTextContent("把這份規格編譯出的目標與任務併入它");
    expect(screen.getByTestId("import-target-hint")).toHaveTextContent("專案層簽核不動");
    await userEvent.selectOptions(select(), OTHER.id);
    expect(screen.getByLabelText("執行路徑")).toHaveValue("D:\\work\\second"); // 換目標跟著換
  });

  it("改回「建立新專案」：執行路徑欄位恢復成使用者自己打的值（選目標前打的字沒有被吃掉）", async () => {
    setup();
    await userEvent.type(screen.getByLabelText("執行路徑"), "/home/user/mine");
    await userEvent.selectOptions(select(), CORE.id);
    expect(screen.getByLabelText("執行路徑")).toHaveValue("/work/core");
    await userEvent.selectOptions(select(), "");
    expect(screen.getByLabelText("執行路徑")).toHaveValue("/home/user/mine");
    expect(screen.getByLabelText("執行路徑")).not.toHaveAttribute("readonly");
    expect(screen.queryByTestId("import-target-path-note")).toBeNull();
  });
});

describe("匯入到既有專案：開始解析送出的選項", () => {
  it("選了目標：帶 targetProjectId 與取自目標專案的執行路徑（不用打路徑也能送出）；不帶 specDir／specFile／sddProject", async () => {
    const props = setup();
    pickFile();
    await userEvent.selectOptions(select(), CORE.id);
    await start();
    expect(lastOptions(props)).toEqual({ autonomyLevel: 3, executionPath: "/work/core", additionalPrompt: undefined, targetProjectId: CORE.id });
    expect(lastOptions(props)).not.toHaveProperty("specDir");
    expect(lastOptions(props)).not.toHaveProperty("specFile");
    expect(lastOptions(props)).not.toHaveProperty("sddProject");
  });

  it("沒選目標：維持原本的選項形狀（沒有 targetProjectId 這個鍵）", async () => {
    const props = setup();
    pickFile();
    await userEvent.type(screen.getByLabelText("執行路徑"), "/home/user/new-service");
    await start();
    expect(lastOptions(props)).toEqual({ autonomyLevel: 3, executionPath: "/home/user/new-service", additionalPrompt: undefined });
    expect(lastOptions(props)).not.toHaveProperty("targetProjectId");
  });

  it("目標專案的路徑不是絕對路徑（壞資料）：照一般規則擋下、不送出", async () => {
    const props = setup({ projects: [{ id: "x1", name: "壞路徑", executionPath: "relative/path" }] });
    pickFile();
    await userEvent.selectOptions(select(), "x1");
    await start();
    expect(screen.getByText(/必須是絕對路徑/)).toBeInTheDocument();
    expect(props.onStart).not.toHaveBeenCalled();
  });
});

describe("匯入到既有專案：沿用既有記錄（從歷史重開、或解析被擋下後）", () => {
  const existing = (parseOptions: ImportRecordDetail["parseOptions"]): ImportRecordDetail => ({
    id: "I1",
    sourceType: "MARKDOWN",
    sourceFileName: "TCS-Alpha.md",
    status: "UPLOADED",
    signedOff: false,
    createdAt: "2026-10-17T08:30:12Z",
    sourceContent: "# TCS",
    parsedResult: null,
    warnings: [],
    parseOptions,
  });

  it("記錄上存的 targetProjectId 填回選擇器與路徑；重新解析原樣帶回 targetProjectId（且不帶 specDir 等）", async () => {
    const props = setup({ existing: existing({ autonomyLevel: 3, executionPath: "/work/core", targetProjectId: CORE.id, specDir: "/work/core/docs" }) });
    expect(select().value).toBe(CORE.id);
    expect(screen.getByLabelText("執行路徑")).toHaveValue("/work/core");
    await start();
    expect(lastOptions(props)).toEqual({ autonomyLevel: 3, executionPath: "/work/core", additionalPrompt: undefined, targetProjectId: CORE.id });
  });

  it("記錄的目標專案不在清單內（清單最多 100 筆、或專案剛被刪）：選擇器多一個「（專案 xxxxxxxx，不在清單內）」選項保留它，路徑沿用還原值，送出時仍帶它（由後端 404／409 說話）", async () => {
    const props = setup({ projects: [OTHER], existing: existing({ autonomyLevel: 3, executionPath: "/work/core", targetProjectId: CORE.id }) });
    expect(select().value).toBe(CORE.id);
    expect([...select().options].map((o) => o.text)).toEqual(["建立新專案（預設）", "第二個專案", "（專案 0b8c5d1e，不在清單內）"]);
    expect(screen.getByLabelText("執行路徑")).toHaveValue("/work/core");
    expect(screen.getByLabelText("執行路徑")).not.toHaveAttribute("readonly");
    await start();
    expect(lastOptions(props)).toEqual({ autonomyLevel: 3, executionPath: "/work/core", additionalPrompt: undefined, targetProjectId: CORE.id });
  });

  it("沒有目標：API 呼叫端設過的 specDir／specFile／sddProject 在重新解析時原樣帶回（不因為從畫面重試而被丟掉）", async () => {
    const props = setup({ existing: existing({ autonomyLevel: 3, executionPath: "/work/core", specDir: "/work/core/docs", specFile: "TCS-Alpha.md", sddProject: "core-fsm" }) });
    expect(select().value).toBe("");
    await start();
    expect(lastOptions(props)).toEqual({ autonomyLevel: 3, executionPath: "/work/core", additionalPrompt: undefined, specDir: "/work/core/docs", specFile: "TCS-Alpha.md", sddProject: "core-fsm" });
  });

  it("使用者在記錄上改選目標：以草稿為準（不再帶還原的 specDir 等）；改選回「建立新專案」才恢復帶回", async () => {
    const props = setup({ existing: existing({ autonomyLevel: 3, executionPath: "/work/core", specDir: "/work/core/docs", sddProject: "core-fsm" }) });
    await userEvent.selectOptions(select(), OTHER.id);
    await start();
    expect(lastOptions(props)).toEqual({ autonomyLevel: 3, executionPath: "D:\\work\\second", additionalPrompt: undefined, targetProjectId: OTHER.id });
    await userEvent.selectOptions(select(), "");
    await start();
    expect(lastOptions(props)).toEqual({ autonomyLevel: 3, executionPath: "/work/core", additionalPrompt: undefined, specDir: "/work/core/docs", sddProject: "core-fsm" });
  });

  it("改用其他來源：目標專案的選擇與路徑留給新來源用（不必重選）", async () => {
    const view = setup({ existing: existing({ autonomyLevel: 3, executionPath: "/work/core", targetProjectId: CORE.id }) });
    await userEvent.click(screen.getByRole("button", { name: "改用其他來源" }));
    view.rerender({ existing: null });
    expect(select().value).toBe(CORE.id);
    expect(screen.getByLabelText("執行路徑")).toHaveValue("/work/core");
    await userEvent.click(screen.getByRole("button", { name: "開始解析" }));
    expect(lastOptions(view)).toMatchObject({ targetProjectId: CORE.id, executionPath: "/work/core" });
  });
});

describe("匯入到既有專案：唯讀角色", () => {
  it("選擇器停用（與其他欄位一樣）", () => {
    setup({ canWrite: false });
    expect(select()).toBeDisabled();
  });
});
