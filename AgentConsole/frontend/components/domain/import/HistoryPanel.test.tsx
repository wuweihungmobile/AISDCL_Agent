import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ImportRecord, ImportStatus } from "@/lib/api/types";
import { Providers, failure, makeClient, signIn, stubApi } from "@/tests/helpers/api";
import { HistoryPanel } from "./HistoryPanel";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/import",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

function record(id: string, status: ImportStatus, over: Partial<ImportRecord> = {}): ImportRecord {
  return { id, sourceType: "MARKDOWN", sourceFileName: `${id}.md`, status, signedOff: false, createdAt: "2026-10-15T08:30:00Z", ...over };
}

const ROWS: ImportRecord[] = [
  record("uploaded", "UPLOADED"),
  record("parsing", "PARSING"),
  record("parsed", "PARSED", { aiModel: "e2e-model", tokenUsed: 1152 }),
  record("reviewing", "REVIEWING"),
  record("imported", "IMPORTED", { projectId: "P9", signedOff: true, aiModel: "e2e-model", tokenUsed: 2048 }),
  record("rejected", "REJECTED", { sourceFileName: undefined }),
];

function renderPanel(onOpen = vi.fn()) {
  render(
    <Providers client={makeClient()}>
      <HistoryPanel onOpen={onOpen} />
    </Providers>,
  );
  return onOpen;
}

beforeEach(() => signIn());

describe("歷史記錄（US-I-06）", () => {
  it("每列顯示：匯入時間、來源檔名、狀態中文標籤、專案連結、aiModel／tokenUsed", async () => {
    const { calls } = stubApi(() => ({ data: { content: ROWS, page: 0, size: 10, totalElements: 6, totalPages: 1 } }));
    renderPanel();
    const rows = await screen.findAllByTestId("import-history-row");
    expect(rows).toHaveLength(6);

    const imported = rows[4];
    expect(imported).toHaveTextContent("imported.md");
    expect(imported).toHaveTextContent("已匯入");
    expect(within(imported).getByRole("link", { name: "查看專案" })).toHaveAttribute("href", "/projects/P9");
    expect(imported).toHaveTextContent("e2e-model · 2,048");
    expect(rows[2]).toHaveTextContent("已解析");
    expect(rows[2]).toHaveTextContent("e2e-model · 1,152");
    expect(rows[5]).toHaveTextContent("（貼上文字）");
    expect(rows[5]).toHaveTextContent("已放棄");
    expect(screen.getByText("共 6 筆匯入記錄")).toBeInTheDocument();
    // 預設依建立時間新到舊、每頁 10 筆
    expect(calls[0].url).toBe("/api/v1/import?page=0&size=10&sort=createdAt%2Cdesc");
  });

  it("只有仍有下一步的記錄（已上傳、已解析、審核中）能「開啟」；解析中與終態沒有開啟鈕", async () => {
    stubApi(() => ({ data: { content: ROWS, page: 0, size: 10, totalElements: 6, totalPages: 1 } }));
    const onOpen = renderPanel();
    const rows = await screen.findAllByTestId("import-history-row");
    const openable = rows.filter((r) => within(r).queryByRole("button", { name: /^開啟匯入記錄/ }));
    expect(openable.map((r) => r.getAttribute("data-status"))).toEqual(["UPLOADED", "PARSED", "REVIEWING"]);
    await userEvent.click(within(rows[2]).getByRole("button", { name: "開啟匯入記錄：parsed.md" }));
    expect(onOpen).toHaveBeenCalledWith("parsed");
  });

  it("依狀態篩選：換條件重新查詢並回到第 1 頁；分頁切換帶對頁碼（後端 0 起算）", async () => {
    const { calls } = stubApi((c) =>
      c.query.get("status") === "PARSED"
        ? { data: { content: [ROWS[2]], page: 0, size: 10, totalElements: 1, totalPages: 1 } }
        : { data: { content: ROWS, page: Number(c.query.get("page")), size: 10, totalElements: 25, totalPages: 3 } },
    );
    renderPanel();
    await screen.findAllByTestId("import-history-row");
    await userEvent.click(screen.getByRole("button", { name: "第 2 頁" }));
    await waitFor(() => expect(calls.some((c) => c.query.get("page") === "1")).toBe(true));
    await userEvent.selectOptions(screen.getByLabelText("依狀態篩選"), "PARSED");
    await waitFor(() => expect(screen.getAllByTestId("import-history-row")).toHaveLength(1));
    const last = calls.at(-1)!;
    expect(last.query.get("status")).toBe("PARSED");
    expect(last.query.get("page")).toBe("0");
  });

  it("沒有記錄：空狀態；載入失敗：顯示錯誤與 traceId，可重試", async () => {
    stubApi(() => ({ data: { content: [], page: 0, size: 10, totalElements: 0, totalPages: 0 } }));
    const { unmount } = render(
      <Providers client={makeClient()}>
        <HistoryPanel onOpen={vi.fn()} />
      </Providers>,
    );
    expect(await screen.findByText("還沒有匯入記錄")).toBeInTheDocument();
    unmount();

    stubApi(() => failure(500, { message: "伺服器錯誤" }));
    render(
      <Providers client={makeClient()}>
        <HistoryPanel onOpen={vi.fn()} />
      </Providers>,
    );
    expect(await screen.findByText("無法載入匯入歷史")).toBeInTheDocument();
    expect(screen.getByText("traceId：tr-500")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重試" })).toBeInTheDocument();
  });
});
