import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ImportRecordDetail, ParsedResult } from "@/lib/api/types";
import { Providers, makeClient, signIn, stubApi, type ApiCall } from "@/tests/helpers/api";
import { ImportView } from "./ImportView";

const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/import",
  useSearchParams: () => new URLSearchParams("id=I1"),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
// Markdown 編輯器本體很重且與本測試無關
vi.mock("@/components/markdown/MarkdownEditor", () => ({
  MarkdownEditor: ({ value, label }: { value: string; label: string }) => <textarea aria-label={label} defaultValue={value} readOnly />,
}));

const TREE: ParsedResult = {
  project: { name: "E2E 匯入專案", executionPath: "/e2e/proj-import", passCriteria: "完成", autonomyLevel: 3 },
  goals: [{ key: "g1", name: "基礎", passCriteria: "完成", sortOrder: 0, dependsOn: [], tasks: [{ name: "初始化", description: "d", passCriteria: "c", sortOrder: 0 }] }],
};

function record(over: Partial<ImportRecordDetail>): ImportRecordDetail {
  return {
    id: "I1",
    sourceType: "MARKDOWN",
    sourceFileName: "brd.md",
    status: "UPLOADED",
    signedOff: false,
    createdAt: "2026-10-15T08:30:12Z",
    sourceContent: "# BRD",
    parsedResult: null,
    warnings: [],
    parseOptions: null,
    ...over,
  };
}

function mount(rec: ImportRecordDetail): { calls: ApiCall[] } {
  const { calls } = stubApi((c) => {
    if (c.method === "GET" && c.path === "/api/v1/import/I1") return { data: rec };
    if (c.method === "GET" && c.path === "/api/v1/settings/agent") return { data: [] };
    return undefined;
  });
  render(
    <Providers client={makeClient()}>
      <ImportView />
    </Providers>,
  );
  return { calls };
}

beforeEach(() => {
  router.replace.mockClear();
  signIn("OPERATOR", "operator");
});

describe("匯入頁：重開記錄（v1.2，C-10；契約 §1.1.9、§4.1 I-12／I-18）", () => {
  it("PARSED 記錄：黃色解析提示由記錄上的 warnings 還原（沒有任何本次 parse／儲存的暫存），並且沒有呼叫 parse", async () => {
    const { calls } = mount(
      record({
        status: "PARSED",
        parsedResult: TREE,
        parsePath: "LLM",
        warnings: [
          { code: "passcriteria_placeholder", detail: "通過標準為佔位字串", location: "goals[0].tasks[0]" },
          { code: "regex_dropped", detail: "regex 無法編譯", location: "goals[0].tasks[0]" },
        ],
        parseOptions: { autonomyLevel: 3, executionPath: "/e2e/proj-import" },
      }),
    );
    expect(await screen.findByTestId("import-step2")).toBeInTheDocument();
    const items = screen.getAllByTestId("parse-warning");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("通過標準是佔位字串，signoff 前請補齊");
    expect(items[1]).toHaveTextContent("期望輸出 regex 無法編譯，已被清空");
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("沒有 warnings（空陣列）：不顯示黃色提示列", async () => {
    mount(record({ status: "REVIEWING", parsedResult: TREE, parsePath: "LLM", warnings: [] }));
    await screen.findByTestId("import-step2");
    expect(screen.queryByTestId("parse-warnings")).toBeNull();
  });

  it("UPLOADED 記錄（解析被有界閘擋下）：解析選項由記錄上的 parseOptions 填回步驟 1 表單；閘清單照舊還原", async () => {
    mount(
      record({
        lastParseErrors: [{ gate: "max_steps", detail: "目標「基礎」的任務數 25 超過上限 24", location: "goals[0].tasks" }],
        parseOptions: { autonomyLevel: 7, executionPath: "/work/restored-path", additionalPrompt: "只拆前端部分" },
      }),
    );
    expect(await screen.findByTestId("existing-source")).toBeInTheDocument();
    expect(screen.getByLabelText(/^自治等級/)).toHaveValue("7");
    expect(screen.getByLabelText("執行路徑")).toHaveValue("/work/restored-path");
    expect(screen.getByLabelText(/^補充說明/)).toHaveValue("只拆前端部分");
    expect(screen.getByTestId("parse-failure")).toBeInTheDocument();
  });
});
