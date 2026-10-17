import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ImportRecordDetail, ParsedResult } from "@/lib/api/types";
import { Providers, failure, makeClient, signIn, stubApi, type ApiCall } from "@/tests/helpers/api";
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

/** `/projects` 回的專案清單（匯入頁「匯入到既有專案」的候選；v1.5）；沒給＝空清單 */
const PROJECTS = [
  {
    id: "0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02",
    name: "AISDLC Core Platform",
    executionPath: "/work/core",
    status: "READY",
    autonomyLevel: 3,
    signedOff: true,
    goalsCount: 2,
    tasksCount: 3,
    tasksDone: 0,
    updatedAt: "2026-10-17T08:00:00Z",
  },
];

function mount(rec: ImportRecordDetail, opts: { projects?: unknown[]; projectsFail?: boolean; parse?: unknown; parseError?: Response } = {}): { calls: ApiCall[] } {
  const projects = opts.projects ?? [];
  let current = rec; // 假後端的記錄：parse 成功後狀態轉 PARSED（之後的 GET 與成功回應一致，否則 invalidate 的重抓會把畫面蓋回 UPLOADED）
  const { calls } = stubApi((c) => {
    if (c.method === "GET" && c.path === "/api/v1/import/I1") return { data: current };
    if (c.method === "GET" && c.path === "/api/v1/settings/agent") return { data: [] };
    if (c.method === "GET" && c.path === "/api/v1/projects")
      return opts.projectsFail ? failure(500, { message: "伺服器暫時無法處理" }) : { data: { content: projects, page: 0, size: 100, totalElements: projects.length, totalPages: 1 } };
    if (c.method === "POST" && c.path === "/api/v1/import/I1/parse") {
      if (opts.parseError) return opts.parseError;
      if (opts.parse) {
        const result = opts.parse as { status: ImportRecordDetail["status"]; path: ImportRecordDetail["parsePath"]; parsedResult: ParsedResult; warnings: ImportRecordDetail["warnings"] };
        current = {
          ...current,
          status: result.status,
          parsePath: result.path,
          parsedResult: result.parsedResult,
          warnings: result.warnings,
          parseOptions: c.body as ImportRecordDetail["parseOptions"],
        };
        return { data: opts.parse };
      }
    }
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

describe("匯入頁：匯入到既有專案（v1.5，契約 §1.10.8；API-IMP-12）", () => {
  const SDD_RESULT = {
    importId: "I1",
    status: "PARSED",
    path: "SDD",
    parsedResult: { ...TREE, path: "SDD", specFormatVersion: "1.0", sddProject: "core-fsm", sddSpecDir: "/work/core/docs", sddSpecFile: "/work/core/docs/TCS-A.md" },
    signedOff: false,
    errors: [],
    warnings: [{ code: "at_unmapped", detail: "規格出現但未編成步驟的 AT：AT-9-X", location: "specDir" }],
  };

  it("選擇器列出 /projects 的未刪除專案；選了目標後解析：POST parse 帶 targetProjectId 與取自目標專案的路徑；成功後顯示規格資訊、併入說明（用專案名）與 at_unmapped 警告", async () => {
    const { calls } = mount(record({}), { projects: PROJECTS, parse: SDD_RESULT });
    await screen.findByTestId("existing-source");
    const select = (await screen.findByLabelText(/^匯入到既有專案/)) as HTMLSelectElement;
    await waitFor(() => expect([...select.options].map((o) => o.text)).toEqual(["建立新專案（預設）", "AISDLC Core Platform"]));
    await userEvent.selectOptions(select, PROJECTS[0].id);
    expect(screen.getByLabelText("執行路徑")).toHaveValue("/work/core");
    await userEvent.click(screen.getByRole("button", { name: "開始解析" }));
    expect(await screen.findByTestId("import-step2")).toBeInTheDocument();
    const parse = calls.find((c) => c.method === "POST" && c.path === "/api/v1/import/I1/parse");
    expect(parse?.body).toEqual({ autonomyLevel: 3, executionPath: "/work/core", targetProjectId: PROJECTS[0].id });
    expect(screen.getByTestId("sdd-info-project")).toHaveTextContent("core-fsm");
    expect(screen.getByTestId("sdd-merge-note")).toHaveTextContent("「AISDLC Core Platform」");
    expect(screen.getByTestId("parse-warning")).toHaveTextContent("規格出現但未編成步驟的 AT：AT-9-X");
  });

  it("不選目標：parse 的請求沒有 targetProjectId；成功後沒有併入說明（維持「建立新專案」）", async () => {
    const { calls } = mount(record({}), {
      projects: PROJECTS,
      parse: {
        ...SDD_RESULT,
        parsedResult: { ...SDD_RESULT.parsedResult, sddProject: undefined, sddSpecDir: undefined, sddSpecFile: undefined, specFormatVersion: undefined, path: "LLM" },
        warnings: [],
      },
    });
    await screen.findByTestId("existing-source");
    await userEvent.type(screen.getByLabelText("執行路徑"), "/home/user/new-service");
    await userEvent.click(screen.getByRole("button", { name: "開始解析" }));
    await screen.findByTestId("import-step2");
    const parse = calls.find((c) => c.method === "POST" && c.path === "/api/v1/import/I1/parse");
    expect(parse?.body).toEqual({ autonomyLevel: 3, executionPath: "/home/user/new-service" });
    expect(screen.queryByTestId("sdd-merge-note")).toBeNull();
  });

  it("專案清單讀不到（console-api 暫時失敗）：選擇器只有「建立新專案」，匯入流程照常可用", async () => {
    mount(record({}), { projectsFail: true });
    await screen.findByTestId("existing-source");
    const select = (await screen.findByLabelText(/^匯入到既有專案/)) as HTMLSelectElement;
    expect([...select.options].map((o) => o.text)).toEqual(["建立新專案（預設）"]);
    expect(screen.getByRole("button", { name: "開始解析" })).toBeEnabled();
  });

  it("解析 409 sdd_binding_conflict（目標專案的綁定與請求不一致）：失敗面板標題是逐字 reason，白話原因在補充說明", async () => {
    mount(record({}), {
      projects: PROJECTS,
      parseError: failure(409, { message: "綁定衝突", reason: "sdd_binding_conflict", details: { cause: "request_differs_from_target", field: "executionPath" } }),
    });
    await screen.findByTestId("existing-source");
    await userEvent.selectOptions(await screen.findByLabelText(/^匯入到既有專案/), PROJECTS[0].id);
    await userEvent.click(screen.getByRole("button", { name: "開始解析" }));
    expect(await screen.findByTestId("parse-failure-title")).toHaveTextContent("sdd_binding_conflict");
    const failurePanel = screen.getByTestId("parse-failure");
    expect(failurePanel).toHaveTextContent("執行路徑與 SDD 綁定一律取自目標專案");
    expect(failurePanel).toHaveTextContent("不一致的欄位：executionPath");
  });
});
