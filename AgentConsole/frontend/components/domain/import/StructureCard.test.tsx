import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { REASONS } from "@/lib/api/reasons";
import { useImportDetail } from "@/lib/api/queries";
import type { ImportRecordDetail, ParsedResult } from "@/lib/api/types";
import { Providers, failure, makeClient, signIn, stubApi, type ApiCall } from "@/tests/helpers/api";
import { StructureCard } from "./StructureCard";

const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/import",
  useSearchParams: () => new URLSearchParams("id=I1"),
}));
// Markdown 編輯器本體很重且與本測試無關：換成同名的簡單 textarea
vi.mock("@/components/markdown/MarkdownEditor", () => ({
  MarkdownEditor: ({ value, onChange, label }: { value: string; onChange: (v: string) => void; label: string }) => (
    <textarea aria-label={label} value={value} onChange={(e) => onChange(e.target.value)} />
  ),
}));

const TREE: ParsedResult = {
  project: { name: "E2E 匯入專案", executionPath: "/e2e/proj-import", passCriteria: "三個目標全部完成", description: "由 BRD 匯入", autonomyLevel: 3 },
  goals: [
    {
      key: "g1",
      name: "基礎",
      passCriteria: "基礎任務完成",
      sortOrder: 0,
      dependsOn: [],
      tasks: [
        { name: "初始化", description: "請輸出 [T1_DONE]", passCriteria: "輸出含 [T1_DONE]", sortOrder: 0 },
        { name: "設定", description: "請輸出 [T2_DONE]", passCriteria: "輸出含 [T2_DONE]", sortOrder: 1 },
      ],
    },
    {
      key: "g2",
      name: "核心",
      passCriteria: "核心任務完成",
      sortOrder: 1,
      dependsOn: ["g1"],
      tasks: [{ name: "實作", description: "請輸出 [T3_DONE]", passCriteria: "輸出含 [T3_DONE]", sortOrder: 0 }],
    },
  ],
  path: "LLM",
  aiModel: "e2e-model",
  tokenUsed: 1152,
};

function baseRecord(over: Partial<ImportRecordDetail> = {}): ImportRecordDetail {
  return {
    id: "I1",
    sourceType: "MARKDOWN",
    sourceFileName: "e2e-brd.md",
    status: "PARSED",
    signedOff: false,
    createdAt: "2026-10-15T08:30:12Z",
    aiModel: "e2e-model",
    tokenUsed: 1152,
    parsePath: "LLM",
    sourceContent: "# BRD",
    parsedResult: TREE,
    ...over,
  };
}

/** 記憶體內的假後端：端點的狀態轉移照契約 §1.1。 */
let server: { record: ImportRecordDetail };
let calls: ApiCall[];
let putReply: (call: ApiCall) => Response | undefined;

function installServer() {
  const api = stubApi((call) => {
    const { method, path } = call;
    if (method === "GET" && path === "/api/v1/import/I1") return { data: server.record };
    if (method === "PUT" && path === "/api/v1/import/I1/result") {
      const forced = putReply(call);
      if (forced) return forced;
      const parsedResult = (call.body as { parsedResult: ParsedResult }).parsedResult;
      server.record = { ...server.record, status: "REVIEWING", signedOff: false, signedOffBy: undefined, signedOffAt: undefined, parsedResult };
      return { data: { importId: "I1", status: "REVIEWING", path: "LLM", parsedResult, signedOff: false, errors: [], warnings: [{ code: "passcriteria_placeholder", detail: "佔位", location: "goals[1].tasks[0]" }] } };
    }
    if (method === "POST" && path === "/api/v1/import/I1/signoff") {
      const approver = (call.body as { approver: string }).approver;
      server.record = { ...server.record, signedOff: true, signedOffBy: approver, signedOffAt: "2026-10-15T09:00:00Z" };
      return { data: { ...server.record, parsedResult: undefined, sourceContent: undefined } };
    }
    if (method === "POST" && path === "/api/v1/import/I1/confirm") return { status: 201, data: { id: "P1", name: "E2E 匯入專案" } };
    if (method === "POST" && path === "/api/v1/import/I1/reject") {
      server.record = { ...server.record, status: "REJECTED" };
      return { data: { ...server.record } };
    }
    return undefined;
  });
  calls = api.calls;
}

const onWarnings = vi.fn();
const onDiscarded = vi.fn();

/** 與頁面相同的接法：記錄來自 useImportDetail（會被 mutation 的快取合併更新），StructureCard 讀它。 */
function Host({ canWrite = true }: { canWrite?: boolean }) {
  const detail = useImportDetail("I1");
  if (!detail.data?.parsedResult) return <p>載入中</p>;
  return <StructureCard key="I1" record={detail.data} canWrite={canWrite} warnings={[]} onWarnings={onWarnings} onDiscarded={onDiscarded} />;
}

async function mount(opts: { role?: "ADMIN" | "VIEWER"; record?: Partial<ImportRecordDetail>; canWrite?: boolean } = {}) {
  signIn(opts.role ?? "ADMIN", opts.role === "VIEWER" ? "viewer" : "admin");
  server = { record: baseRecord(opts.record) };
  putReply = () => undefined;
  installServer();
  const client = makeClient();
  render(
    <Providers client={client}>
      <Host canWrite={opts.canWrite ?? true} />
    </Providers>,
  );
  await screen.findByTestId("import-step2");
  return client;
}

/** 開「編輯任務」對話框改任務名後按確定 */
async function renameTask(from: string, to: string) {
  await userEvent.click(screen.getByRole("button", { name: `編輯任務：${from}` }));
  const dialog = screen.getByRole("dialog", { name: "編輯任務" });
  const input = within(dialog).getByLabelText("任務名稱");
  await userEvent.clear(input);
  await userEvent.type(input, to);
  await userEvent.click(within(dialog).getByRole("button", { name: "確定" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
}

beforeEach(() => {
  router.push.mockClear();
  onWarnings.mockClear();
  onDiscarded.mockClear();
});

describe("步驟 2：signoff 硬閘（US-I-09）", () => {
  it("未 signoff：顯示含 signed_off=false 字樣的警示橫幅與「signoff 審批」；「確認匯入」禁用並說明原因", async () => {
    await mount();
    const banner = screen.getByTestId("import-signoff-banner");
    expect(banner).toHaveTextContent("signed_off=false");
    expect(within(banner).getByRole("button", { name: "signoff 審批" })).toBeEnabled();
    const confirm = screen.getByRole("button", { name: "確認匯入" });
    expect(confirm).toBeDisabled();
    expect(confirm).toHaveAttribute("title", "須先 signoff 才能確認匯入");
    expect(screen.queryByTestId("import-signed-off")).toBeNull();
  });

  it("signoff：approver 預設帶目前使用者；成功後橫幅換成綠勾「已 signoff」、確認匯入可按", async () => {
    await mount();
    await userEvent.click(screen.getByRole("button", { name: "signoff 審批" }));
    const dialog = screen.getByRole("dialog", { name: "審批 signoff：匯入草案" });
    expect(within(dialog).getByLabelText("審批者")).toHaveValue("admin");
    await userEvent.click(within(dialog).getByRole("button", { name: "確認 signoff" }));

    const ok = await screen.findByTestId("import-signed-off");
    expect(ok).toHaveTextContent("已 signoff");
    expect(ok).toHaveTextContent("審批者 admin");
    expect(screen.queryByTestId("import-signoff-banner")).toBeNull();
    expect(screen.getByRole("button", { name: "確認匯入" })).toBeEnabled();
    const post = calls.find((c) => c.path === "/api/v1/import/I1/signoff");
    expect(post?.body).toEqual({ approver: "admin" });
  });

  it("確認匯入：POST confirm，成功後導向 /projects/[id]", async () => {
    await mount({ record: { signedOff: true, signedOffBy: "someone", signedOffAt: "2026-10-15T09:00:00Z" } });
    await userEvent.click(screen.getByRole("button", { name: "確認匯入" }));
    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/projects/P1"));
    expect(calls.some((c) => c.method === "POST" && c.path === "/api/v1/import/I1/confirm")).toBe(true);
    expect(await screen.findByText("已匯入專案：E2E 匯入專案")).toBeInTheDocument();
  });

  it("確認匯入被後端擋下（409 草案尚未 signoff）：錯誤與 reason 顯示在卡內，不導頁", async () => {
    await mount({ record: { signedOff: true, signedOffBy: "someone" } });
    // 換成「確認匯入一律 409」的後端（讀取仍回目前記錄）
    stubApi((call) =>
      call.method === "GET"
        ? { data: server.record }
        : failure(409, { message: "草案尚未 signoff", reason: REASONS.IMPORT_NOT_SIGNED_OFF, details: { status: "PARSED", signedOff: false } }),
    );
    await userEvent.click(screen.getByRole("button", { name: "確認匯入" }));
    const alert = await screen.findByText(/草案尚未 signoff，不可確認匯入/);
    expect(alert).toHaveTextContent("traceId：tr-409");
    expect(router.push).not.toHaveBeenCalled();
  });

  it("放棄：確認對話框 → POST reject → 回報頁面清掉目前記錄", async () => {
    await mount();
    await userEvent.click(screen.getByRole("button", { name: "放棄" }));
    const dialog = screen.getByRole("dialog", { name: "放棄這份匯入草案？" });
    await userEvent.click(within(dialog).getByRole("button", { name: "放棄" }));
    await waitFor(() => expect(onDiscarded).toHaveBeenCalledTimes(1));
    expect(calls.some((c) => c.method === "POST" && c.path === "/api/v1/import/I1/reject")).toBe(true);
  });
});

describe("步驟 2：編輯（US-I-04）", () => {
  it("改一個任務名：只有該節點變、出現未儲存提示；此時 signoff 與確認匯入都停用（不能簽到舊版本）", async () => {
    await mount({ record: { signedOff: true, signedOffBy: "someone", signedOffAt: "2026-10-15T09:00:00Z" } });
    expect(screen.getByRole("button", { name: "確認匯入" })).toBeEnabled();
    await renameTask("設定", "設定環境");

    expect(screen.getAllByTestId("task-name").map((n) => n.textContent)).toEqual(["初始化", "設定環境", "實作"]);
    const notice = screen.getByTestId("dirty-notice");
    expect(notice).toHaveTextContent("有未儲存的編輯");
    expect(notice).toHaveTextContent("會撤銷目前的 signoff");
    expect(screen.getByRole("button", { name: "確認匯入" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "確認匯入" })).toHaveAttribute("title", "有未儲存的編輯，請先儲存編輯");
  });

  it("還原：丟掉本地編輯回到伺服器版本，提示消失", async () => {
    await mount();
    await renameTask("設定", "設定環境");
    await userEvent.click(screen.getByRole("button", { name: "還原" }));
    expect(screen.getAllByTestId("task-name").map((n) => n.textContent)).toEqual(["初始化", "設定", "實作"]);
    expect(screen.queryByTestId("dirty-notice")).toBeNull();
  });

  it("儲存編輯：PUT 整樹覆寫（sortOrder 重編、不帶伺服器欄位）→ 成功 toast、不再是未儲存、signoff 被撤銷", async () => {
    await mount({ record: { signedOff: true, signedOffBy: "someone", signedOffAt: "2026-10-15T09:00:00Z" } });
    await renameTask("設定", "設定環境");
    await userEvent.click(screen.getByRole("button", { name: "儲存編輯" }));

    expect(await screen.findByText("已儲存編輯；先前的 signoff 已撤銷，請重新審批")).toBeInTheDocument();
    const put = calls.find((c) => c.method === "PUT" && c.path === "/api/v1/import/I1/result");
    const sent = (put?.body as { parsedResult: ParsedResult }).parsedResult;
    expect(sent.goals[0].tasks.map((t) => [t.name, t.sortOrder])).toEqual([["初始化", 0], ["設定環境", 1]]);
    expect(sent.goals[1].dependsOn).toEqual(["g1"]);
    for (const key of ["path", "aiModel", "tokenUsed"]) expect(sent).not.toHaveProperty(key);
    await waitFor(() => expect(screen.queryByTestId("dirty-notice")).toBeNull());
    // 編輯撤銷 signoff：橫幅回來、確認匯入停用
    expect(await screen.findByTestId("import-signoff-banner")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "確認匯入" })).toBeDisabled();
    expect(onWarnings).toHaveBeenCalledWith([{ code: "passcriteria_placeholder", detail: "佔位", location: "goals[1].tasks[0]" }]);
  });

  it("儲存遇到 422 有界閘：三條違規完整列出、指到的節點標紅、保留編輯讓使用者修改後重試", async () => {
    await mount();
    putReply = () =>
      failure(422, {
        message: "解析結果未通過有界閘（3 項）",
        reason: REASONS.IMPORT_GATE_REJECTED,
        errors: [
          { field: "goals[0].tasks[1].description", message: "m", gate: "empty_prompt", detail: "任務「設定」的描述為空（goals[0].tasks[1]）", location: "goals[0].tasks[1].description" },
          { field: "goals[0].tasks", message: "m", gate: "max_steps", detail: "目標「基礎」的任務數 25 超過上限 24（不截斷、不修剪）", location: "goals[0].tasks" },
          { field: "goals[1].dependsOn", message: "m", gate: "cycle", detail: "目標依賴成環：基礎 -> 核心 -> 基礎", location: "goals[1].dependsOn" },
        ],
        details: { path: "LLM" },
      });
    await renameTask("設定", "設定環境");
    await userEvent.click(screen.getByRole("button", { name: "儲存編輯" }));

    const rows = await screen.findAllByTestId("gate-error-row");
    expect(rows).toHaveLength(3);
    expect(rows.map((r) => within(r).getByTestId("gate-error-detail").textContent)).toEqual([
      "任務「設定」的描述為空（goals[0].tasks[1]）",
      "目標「基礎」的任務數 25 超過上限 24（不截斷、不修剪）",
      "目標依賴成環：基礎 -> 核心 -> 基礎",
    ]);
    // 標紅：goals[0].tasks[1] 與 goals[0]（任務數）與 goals[1]（依賴）
    const goals = screen.getAllByTestId("tree-goal");
    expect(goals[0]).toHaveAttribute("data-highlighted");
    expect(goals[1]).toHaveAttribute("data-highlighted");
    expect(within(goals[0]).getAllByTestId("tree-task")[1]).toHaveAttribute("data-highlighted");
    // 編輯仍在、仍可重試
    expect(screen.getByTestId("dirty-notice")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "儲存編輯" })).toBeEnabled();

    // 再動一下樹：索引已不可信，標紅收起，但清單仍留著給使用者對照
    await renameTask("初始化", "初始化專案");
    expect(screen.getAllByTestId("tree-goal")[0]).not.toHaveAttribute("data-highlighted");
    expect(screen.getAllByTestId("gate-error-row")).toHaveLength(3);
  });

  it("新增目標：先開對話框填寫，確定後才進樹（取消不留空白節點）；新目標附一個空白任務", async () => {
    await mount();
    await userEvent.click(screen.getByRole("button", { name: "新增目標" }));
    let dialog = screen.getByRole("dialog", { name: "新增目標" });
    await userEvent.click(within(dialog).getByRole("button", { name: "取消" }));
    expect(screen.getAllByTestId("tree-goal")).toHaveLength(2);

    await userEvent.click(screen.getByRole("button", { name: "新增目標" }));
    dialog = screen.getByRole("dialog", { name: "新增目標" });
    // 名稱與通過標準必填：空白送出 → 行內錯誤、不進樹
    await userEvent.click(within(dialog).getByRole("button", { name: "確定" }));
    expect(await within(dialog).findByText("目標名稱不能為空")).toBeInTheDocument();
    expect(screen.getAllByTestId("tree-goal")).toHaveLength(2);

    await userEvent.type(within(dialog).getByLabelText("目標名稱"), "收尾");
    await userEvent.type(within(dialog).getByLabelText("通過標準"), "全部完成");
    await userEvent.click(within(dialog).getByRole("button", { name: "確定" }));
    await waitFor(() => expect(screen.getAllByTestId("tree-goal")).toHaveLength(3));
    const added = screen.getAllByTestId("tree-goal")[2];
    expect(added).toHaveTextContent("收尾");
    expect(within(added).getAllByTestId("tree-task")).toHaveLength(1);
    expect(within(added).getByTestId("task-name")).toHaveTextContent("（未命名）");
    expect(screen.getByTestId("dirty-notice")).toBeInTheDocument();
  });

  it("刪除任務與目標：樹立即更新；刪掉被依賴的目標，依賴一併清掉", async () => {
    await mount();
    await userEvent.click(screen.getByRole("button", { name: "刪除任務：初始化" }));
    expect(screen.getAllByTestId("task-name").map((n) => n.textContent)).toEqual(["設定", "實作"]);
    await userEvent.click(screen.getByRole("button", { name: "刪除目標：基礎" }));
    expect(screen.getAllByTestId("tree-goal")).toHaveLength(1);
    await userEvent.click(screen.getByRole("button", { name: "儲存編輯" }));
    await screen.findByText("已儲存編輯");
    const put = calls.find((c) => c.method === "PUT")?.body as { parsedResult: ParsedResult };
    expect(put.parsedResult.goals.map((g) => [g.key, g.dependsOn])).toEqual([["g2", []]]);
  });
});

describe("唯讀角色（VIEWER）", () => {
  it("可以看樹，但編輯、儲存、signoff、確認匯入、放棄全部停用", async () => {
    await mount({ role: "VIEWER", canWrite: false });
    expect(screen.queryByRole("button", { name: /^編輯/ })).toBeNull();
    expect(screen.getByRole("button", { name: "signoff 審批" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "確認匯入" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "放棄" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "確認匯入" })).toHaveAttribute("title", "權限不足（唯讀角色）");
  });
});
