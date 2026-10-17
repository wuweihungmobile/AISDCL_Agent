import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useImportDetail } from "@/lib/api/queries";
import type { ImportRecordDetail, ParsedResult, ParseWarning } from "@/lib/api/types";
import { Providers, failure, makeClient, signIn, stubApi, type ApiCall } from "@/tests/helpers/api";
import { StructureCard } from "./StructureCard";

const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/import",
  useSearchParams: () => new URLSearchParams("id=I1"),
}));
vi.mock("@/components/markdown/MarkdownEditor", () => ({
  MarkdownEditor: ({ value, label }: { value: string; label: string }) => <textarea aria-label={label} defaultValue={value} readOnly />,
}));

/**
 * 匯入步驟 2 的 v1.5 接線（整合輪 115；契約 §3.3.2 第 5、6 點、§1.10.8）：
 * 路徑 A 的 ParsedResult 新欄位（specFormatVersion、sddProject、sddSpecDir、sddSpecFile）、三個新警告碼、「併入既有專案」的說明與 confirm 結果。
 */
const TARGET = "0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02";
const SDD_TREE: ParsedResult = {
  project: { name: "核心平台", executionPath: "/work/core", passCriteria: "規格「greenfield」的全部合約驗收通過", autonomyLevel: 3 },
  goals: [
    {
      key: "g1",
      name: "greenfield",
      passCriteria: "全部 1 個合約的驗收標準通過",
      sortOrder: 0,
      dependsOn: [],
      tasks: [
        {
          name: "AT-001-1",
          description: "請依規格實作",
          passCriteria: "輸出符合 DONE",
          sortOrder: 0,
          passCriteriaSpec: { source: "sdd", specDigest: "sha256:ab", stepId: "sdd-greenfield-at-001-1", weakRegex: false },
        },
      ],
    },
  ],
  path: "SDD",
  specDigest: "sha256:ab",
  specFormatVersion: "1.0",
  sddProject: "core-fsm",
  sddSpecDir: "/work/core/docs/03_testing/contracts",
  sddSpecFile: "/work/core/docs/03_testing/contracts/TCS-Alpha.md",
};

let record: ImportRecordDetail;
let calls: ApiCall[];

function baseRecord(over: Partial<ImportRecordDetail> = {}): ImportRecordDetail {
  return {
    id: "I1",
    sourceType: "MARKDOWN",
    sourceFileName: "TCS-Alpha.md",
    status: "PARSED",
    signedOff: true,
    signedOffBy: "operator",
    signedOffAt: "2026-10-17T09:00:00Z",
    createdAt: "2026-10-17T08:30:12Z",
    parsePath: "SDD",
    sourceContent: "# TCS",
    parsedResult: SDD_TREE,
    warnings: [],
    parseOptions: { autonomyLevel: 3, executionPath: "/work/core" },
    ...over,
  };
}

function Host({ warnings = [], targetName }: { warnings?: ParseWarning[]; targetName?: string | null }) {
  const detail = useImportDetail("I1");
  if (!detail.data?.parsedResult) return <p>載入中</p>;
  return <StructureCard key="I1" record={detail.data} canWrite warnings={warnings} onWarnings={() => undefined} onDiscarded={() => undefined} targetName={targetName} />;
}

async function mount(
  over: Partial<ImportRecordDetail> = {},
  props: { warnings?: ParseWarning[]; targetName?: string | null } = {},
  confirmReply?: () => Response | { status?: number; data?: unknown },
) {
  signIn("OPERATOR", "operator");
  record = baseRecord(over);
  const api = stubApi((c) => {
    if (c.method === "GET" && c.path === "/api/v1/import/I1") return { data: record };
    if (c.method === "POST" && c.path === "/api/v1/import/I1/confirm") return confirmReply ? confirmReply() : { status: 201, data: { id: TARGET, name: "核心平台" } };
    return undefined;
  });
  calls = api.calls;
  render(
    <Providers client={makeClient()}>
      <Host {...props} />
    </Providers>,
  );
  await screen.findByTestId("import-step2");
}

beforeEach(() => router.push.mockClear());

describe("匯入步驟 2：路徑 A 的 ParsedResult 新欄位（契約 §3.3.2 第 5 點）", () => {
  it("顯示規格格式版本、FSM 專案（標準鍵）、規格目錄、規格檔；說明「確認匯入才回填」；路徑標籤是「規格驅動（SDD）」", async () => {
    await mount();
    const info = screen.getByTestId("sdd-spec-info");
    expect(info).toHaveTextContent("規格資訊（規格驅動 SDD）");
    expect(screen.getByTestId("sdd-info-format")).toHaveTextContent("1.0");
    expect(screen.getByTestId("sdd-info-project")).toHaveTextContent("core-fsm");
    expect(screen.getByTestId("sdd-info-dir")).toHaveTextContent("/work/core/docs/03_testing/contracts");
    expect(screen.getByTestId("sdd-info-file")).toHaveTextContent("/work/core/docs/03_testing/contracts/TCS-Alpha.md");
    expect(info).toHaveTextContent("確認匯入」成功後才會回填到專案");
    expect(screen.getByTestId("parse-path")).toHaveTextContent("規格驅動（SDD）");
    expect(screen.queryByTestId("sdd-merge-note")).toBeNull(); // 沒帶 targetProjectId：不是併入
  });

  it("缺值的欄位顯示「—」（只有部分欄位時不崩潰、不顯示 undefined）", async () => {
    await mount({ parsedResult: { ...SDD_TREE, specFormatVersion: undefined, sddSpecFile: undefined } });
    expect(screen.getByTestId("sdd-info-format")).toHaveTextContent(/^—$/);
    expect(screen.getByTestId("sdd-info-file")).toHaveTextContent(/^—$/);
    expect(screen.getByTestId("sdd-spec-info").textContent).not.toContain("undefined");
  });

  it("路徑 B／C（沒有任何 SDD 欄位、也沒帶 targetProjectId）：整塊不顯示", async () => {
    await mount({
      parsePath: "LLM",
      parsedResult: { ...SDD_TREE, path: "LLM", specDigest: undefined, specFormatVersion: undefined, sddProject: undefined, sddSpecDir: undefined, sddSpecFile: undefined },
    });
    expect(screen.queryByTestId("sdd-spec-info")).toBeNull();
  });
});

describe("匯入步驟 2：警告（契約 §3.3.2 第 6 點）", () => {
  const WARNINGS: ParseWarning[] = [
    { code: "at_unmapped", detail: "規格出現但未編成步驟的 AT：AT-9-X、AT-010", location: "specDir" },
    { code: "frozen_digest_absent", detail: "規格凍結時沒有記錄內容摘要（舊狀態檔），無法偵測凍結後改檔", location: "specDir" },
    { code: "state_dir_not_ignored", detail: "build/reports/fsm/ 未被 git 忽略", location: "executionPath" },
  ];

  it("三個新警告碼以黃色提示列呈現（白話標題＋位置＋後端說明）；at_unmapped 的 detail 列出未編成步驟的 AT", async () => {
    await mount({}, { warnings: WARNINGS });
    const rows = screen.getAllByTestId("parse-warning");
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveTextContent("規格出現、但未編成步驟的 AT（不會被執行；signoff 前請確認編號是否合文法）");
    expect(rows[0]).toHaveTextContent("specDir");
    expect(rows[0]).toHaveTextContent("規格出現但未編成步驟的 AT：AT-9-X、AT-010");
    expect(rows[1]).toHaveTextContent("規格凍結時沒有記錄內容摘要（舊狀態檔），無法偵測凍結後改檔");
    expect(rows[2]).toHaveTextContent("build/reports/fsm/ 沒有被 git 忽略，請把 build/reports/ 加進該專案的 .gitignore");
    expect(rows[2]).toHaveTextContent("executionPath");
    expect(screen.getByTestId("parse-warnings")).toHaveTextContent("解析提示（共 3 項，不阻擋儲存）");
  });
});

describe("匯入步驟 2：併入既有專案（契約 §1.10.8；parse 帶了 targetProjectId）", () => {
  const MERGED = { parseOptions: { autonomyLevel: 3, executionPath: "/work/core", targetProjectId: TARGET } };

  it("顯示併入說明：不建立新專案、新目標接在既有目標之後、專案層簽核不動；有名稱用名稱，沒有就用 id 前 8 碼", async () => {
    await mount(MERGED, { targetName: "AISDLC Core Platform" });
    const note = screen.getByTestId("sdd-merge-note");
    expect(note).toHaveTextContent("併入既有專案");
    expect(note).toHaveTextContent("不會建立新專案");
    expect(note).toHaveTextContent("「AISDLC Core Platform」");
    expect(note).toHaveTextContent("新目標接在既有目標之後");
    expect(note).toHaveTextContent("專案層的簽核都不動");
    expect(note).toHaveTextContent("專案若尚未簽核，執行前仍須另外簽核");
  });

  it("目標名稱查不到（清單沒載到、專案剛被刪）：退回「專案 <id 前 8 碼>」，不顯示空白或 undefined", async () => {
    await mount(MERGED, { targetName: null });
    expect(screen.getByTestId("sdd-merge-note")).toHaveTextContent("「專案 0b8c5d1e」");
    expect(screen.getByTestId("sdd-merge-note").textContent).not.toContain("undefined");
  });

  it("沒有 SDD 欄位但有 targetProjectId：只顯示併入說明，不顯示規格資訊", async () => {
    await mount({ ...MERGED, parsedResult: { ...SDD_TREE, specFormatVersion: undefined, sddProject: undefined, sddSpecDir: undefined, sddSpecFile: undefined } }, { targetName: "X" });
    expect(screen.getByTestId("sdd-merge-note")).toBeInTheDocument();
    expect(screen.queryByText("規格資訊（規格驅動 SDD）")).toBeNull();
  });

  it("確認匯入成功（回傳的是目標專案）：toast 說「已併入專案」而不是「已匯入專案」，導向該專案", async () => {
    await mount(MERGED, { targetName: "核心平台" });
    await userEvent.click(screen.getByRole("button", { name: "確認匯入" }));
    await waitFor(() => expect(router.push).toHaveBeenCalledWith(`/projects/${TARGET}`));
    expect(await screen.findByText("已併入專案：核心平台")).toBeInTheDocument();
    expect(calls.filter((c) => c.method === "POST" && c.path === "/api/v1/import/I1/confirm")).toHaveLength(1);
  });

  it("不帶 targetProjectId 的 confirm 維持「已匯入專案」", async () => {
    await mount();
    await userEvent.click(screen.getByRole("button", { name: "確認匯入" }));
    expect(await screen.findByText("已匯入專案：核心平台")).toBeInTheDocument();
  });

  it.each([
    ["target_bound_differently", { cause: "target_bound_differently", sddProject: "beta" }, "目標專案已綁定了不同的 FSM 專案或規格根，這份規格不能併入它（目標專案目前綁定的 FSM 專案：beta）"],
    ["already_bound_elsewhere", { cause: "already_bound_elsewhere", sddProject: "core-fsm", holderProjectId: "1a2b3c4d-0000" }, "同一個專案根下已有另一個專案（1a2b3c4d）綁定了這個 FSM 專案"],
  ] as const)("confirm 409 sdd_binding_conflict（%s）：卡內顯示白話原因與 traceId（不是英文代碼），不導頁，確認匯入仍可再按", async (_cause, details, sentence) => {
    await mount(MERGED, { targetName: "核心平台" }, () => failure(409, { message: "綁定衝突", reason: "sdd_binding_conflict", details }));
    await userEvent.click(screen.getByRole("button", { name: "確認匯入" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(sentence);
    expect(alert).toHaveTextContent("traceId：tr-409");
    expect(alert.textContent).not.toContain("sdd_binding_conflict");
    expect(router.push).not.toHaveBeenCalled();
    expect(within(screen.getByTestId("import-step2")).getByRole("button", { name: "確認匯入" })).toBeEnabled();
  });

  it("confirm 其他失敗（例如 404 目標專案已被刪除）：照一般錯誤顯示 message 與 traceId", async () => {
    await mount(MERGED, { targetName: "核心平台" }, () => failure(404, { message: `專案不存在或已刪除：${TARGET}` }));
    await userEvent.click(screen.getByRole("button", { name: "確認匯入" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(`專案不存在或已刪除：${TARGET}`);
    expect(alert).toHaveTextContent("traceId：tr-404");
  });
});
