import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { REASONS } from "@/lib/api/reasons";
import type { Config, ConfigCategory, ConfigHistory } from "@/lib/api/types";
import { Providers, envelope, failure, makeClient, signIn, stubApi, type ApiCall } from "@/tests/helpers/api";
import { FIXTURE, MASKED } from "@/tests/helpers/settingsFixtures";
import { SettingsView } from "./SettingsView";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/settings",
  useSearchParams: () => new URLSearchParams(),
}));

const CATEGORIES: ConfigCategory[] = ["model", "agent", "execution", "monitor", "autoclaude", "sdd"];

/** 記憶體內的假後端：契約 §1.5 的寫入端點行為（角色、confirm、跨鍵校驗、歷史）。 */
let store: Record<ConfigCategory, Config[]>;
let history: ConfigHistory[];
let calls: ApiCall[];
/** 讓特定端點回傳指定的回應（優先於預設行為） */
let overrides: Array<(call: ApiCall) => Response | undefined>;

function fresh(): Record<ConfigCategory, Config[]> {
  return {
    model: [FIXTURE.provider(), FIXTURE.apiUrl(), FIXTURE.apiKey(true), FIXTURE.name(), FIXTURE.maxTokensPerRequest(), FIXTURE.temperature(), FIXTURE.enableKernelBrain()],
    agent: [FIXTURE.defaultAutonomyLevel(), FIXTURE.maxConcurrentTasks(), FIXTURE.enableAutoMutation()],
    execution: [FIXTURE.globalTokenBudget("2000000"), FIXTURE.dagSchedulerStrategy(), FIXTURE.compactThresholdPct("80"), FIXTURE.haltThresholdPct("90")],
    monitor: [FIXTURE.refreshIntervalMs("15000"), FIXTURE.notificationEmail()],
    autoclaude: [FIXTURE.dbDsn()],
    sdd: [FIXTURE.specFormat()],
  };
}

const find = (cat: string, key: string) => store[cat as ConfigCategory].find((c) => c.key === key);

function installServer(role: "ADMIN" | "OPERATOR" | "VIEWER" = "ADMIN") {
  const api = stubApi((call) => {
    for (const o of overrides) {
      const r = o(call);
      if (r) return r;
    }
    const { method, path } = call;
    let m: RegExpExecArray | null;
    if (method === "GET" && path === "/api/v1/settings") return { data: store };
    if (method === "GET" && (m = /^\/api\/v1\/settings\/(\w+)$/.exec(path)) && m[1] !== "history") {
      const list = store[m[1] as ConfigCategory];
      if (call.query.get("reveal") === "true") {
        if (role !== "ADMIN") return failure(403, { message: "僅 ADMIN 可揭露敏感參數", reason: REASONS.SETTINGS_REVEAL_ADMIN_ONLY });
        return { data: list.map((c) => (c.isEncrypted && c.hasValue ? { ...c, value: "sk-plain-secret" } : c)) };
      }
      return { data: list };
    }
    if (method === "GET" && path === "/api/v1/settings/history") return { data: { content: history, page: 0, size: 20, totalElements: history.length, totalPages: 1 } };
    if (role !== "ADMIN" && method !== "GET") return failure(403, { message: "權限不足", reason: "ACCESS_DENIED" });
    if (method === "PUT" && path === "/api/v1/settings/execution/token-guard") {
      const { compactThresholdPct: c, haltThresholdPct: h } = call.body as { compactThresholdPct: number; haltThresholdPct: number };
      if (h <= c) return failure(400, { message: "跨鍵校驗失敗", reason: REASONS.SETTINGS_TOKEN_GUARD_ORDER, errors: [{ field: "haltThresholdPct", message: "必須大於 compactThresholdPct" }], details: { compactThresholdPct: c, haltThresholdPct: h } });
      find("execution", "compactThresholdPct")!.value = String(c);
      find("execution", "haltThresholdPct")!.value = String(h);
      return { data: [find("execution", "compactThresholdPct"), find("execution", "haltThresholdPct")] };
    }
    if (method === "PUT" && (m = /^\/api\/v1\/settings\/(\w+)\/(\w+)$/.exec(path))) {
      const c = find(m[1], m[2]);
      if (!c) return failure(404, { message: `設定鍵不存在：${m[1]}.${m[2]}` });
      const body = call.body as { value: string; confirm?: boolean };
      if (c.isEncrypted && body.confirm !== true) return failure(409, { message: "需二次確認", reason: REASONS.SETTINGS_UPDATE_NEEDS_CONFIRM, details: { category: m[1], key: m[2] } });
      if (c.key === "maxTokensPerRequest" && Number(body.value) > 200000) return failure(400, { message: "參數驗證失敗", reason: REASONS.SETTINGS_VALUE_INVALID, errors: [{ field: "value", message: "需為整數（1～200000）" }] });
      const next = c.isEncrypted ? { ...c, hasValue: body.value !== "" } : { ...c, value: body.value };
      store[c.category] = store[c.category].map((x) => (x.key === c.key ? next : x));
      return { data: next };
    }
    if (method === "POST" && (m = /^\/api\/v1\/settings\/(\w+)\/(\w+)\/reset$/.exec(path))) {
      const c = find(m[1], m[2])!;
      if (c.isEncrypted && call.query.get("confirm") !== "true") return failure(409, { message: "需二次確認", reason: REASONS.SETTINGS_RESET_NEEDS_CONFIRM });
      const next = c.isEncrypted ? { ...c, hasValue: false } : { ...c, value: c.defaultValue ?? "" };
      store[c.category] = store[c.category].map((x) => (x.key === c.key ? next : x));
      return { data: next };
    }
    if (method === "POST" && (m = /^\/api\/v1\/settings\/(\w+)\/reset$/.exec(path))) {
      const cat = m[1] as ConfigCategory;
      const confirm = call.query.get("confirm") === "true";
      store[cat] = store[cat].map((c) => (c.isEncrypted ? (confirm ? { ...c, hasValue: false } : c) : { ...c, value: c.defaultValue ?? "" }));
      return { data: store[cat] };
    }
    return undefined;
  });
  calls = api.calls;
}

async function mount(role: "ADMIN" | "OPERATOR" | "VIEWER" = "ADMIN") {
  signIn(role, role.toLowerCase());
  store = fresh();
  history = [
    { id: "h1", configId: "c1", category: "model", key: "temperature", oldValue: "0.5", newValue: "0.3", changedAt: "2026-10-15T15:30:00", changedBy: "admin" },
    { id: "h2", configId: "c2", category: "model", key: "apiKey", oldValue: MASKED, newValue: MASKED, changedAt: "2026-10-14T10:00:00", changedBy: "admin" },
  ];
  overrides = [];
  installServer(role);
  render(
    <Providers client={makeClient()}>
      <SettingsView />
    </Providers>,
  );
  await screen.findByTestId("settings-panel");
}

const row = (id: string) => document.querySelector<HTMLElement>(`[data-setting="${id}"]`)!;
const inRow = (id: string) => within(row(id));
const putCalls = () => calls.filter((c) => c.method === "PUT");

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("版面與分類 tab（US-S-01）", () => {
  it("標題列、匯出／匯入設定、六個分類 tab（模型／Agent／執行／監控／AutoClaude／SDD），預設在模型", async () => {
    await mount();
    expect(screen.getByRole("heading", { name: "系統參數設定" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "匯出設定" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "匯入設定" })).toBeEnabled();
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["模型", "Agent", "執行", "監控", "AutoClaude", "SDD"]);
    expect(screen.getByRole("tab", { name: "模型" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "模型設定" })).toBeInTheDocument();
  });

  it("每列：中文名稱、說明、誠實標示（僅儲存／尚未驗證）、影響範圍提示、數值範圍；API URL 提示完整端點", async () => {
    await mount();
    const provider = inRow("model.provider");
    expect(provider.getByText("模型提供者")).toBeInTheDocument();
    expect(provider.getByTestId("effect-tag")).toHaveTextContent("僅儲存、不影響引擎");
    expect(provider.getByTestId("impact-note")).toHaveTextContent("僅為 Console 抽象層欄位");
    expect(inRow("model.apiUrl").getByTestId("setting-hint")).toHaveTextContent("完整的 chat-completions 端點 URL");
    expect(inRow("model.maxTokensPerRequest").getByTestId("setting-hint")).toHaveTextContent("範圍 1～200000");
    expect(inRow("model.name").queryByTestId("effect-tag")).toBeNull();

    await userEvent.click(screen.getByRole("tab", { name: "AutoClaude" }));
    expect(row("autoclaude.dbDsn")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Agent" }));
    expect(inRow("agent.enableAutoMutation").getByTestId("effect-tag")).toHaveTextContent("尚未驗證對映");
  });

  it("監控 tab：refreshIntervalMs 的提示寫明最小 10000", async () => {
    await mount();
    await userEvent.click(screen.getByRole("tab", { name: "監控" }));
    const hint = inRow("monitor.refreshIntervalMs").getByTestId("setting-hint");
    expect(hint).toHaveTextContent("最小 10000");
    expect(hint).toHaveTextContent("範圍 10000～60000");
  });

  it("控制項依 valueType：模型 tab 的 ENUM／STRING／ENCRYPTED／INTEGER／FLOAT／BOOLEAN 各有對應元件", async () => {
    await mount();
    expect(inRow("model.provider").getByRole("combobox")).toBeInTheDocument();
    expect(inRow("model.apiUrl").getByRole("textbox")).toHaveClass("font-mono");
    expect(inRow("model.apiKey").getByLabelText("API Key")).toHaveAttribute("type", "password");
    expect(inRow("model.maxTokensPerRequest").getByRole("textbox")).toHaveAttribute("inputmode", "numeric");
    expect(inRow("model.temperature").getByRole("textbox")).toHaveAttribute("inputmode", "decimal");
    expect(inRow("model.enableKernelBrain").getByRole("switch")).toBeInTheDocument();
  });
});

describe("修改與儲存（US-S-02）", () => {
  it("改一個數值再儲存：只送有變動的鍵（PUT 單鍵、不帶 confirm），成功 toast、未儲存提示消失、值保持新值", async () => {
    await mount();
    const save = screen.getByRole("button", { name: "儲存變更" });
    expect(save).toBeDisabled();
    const input = inRow("model.maxTokensPerRequest").getByRole("textbox");
    await userEvent.clear(input);
    await userEvent.type(input, "4096");
    expect(screen.getByTestId("unsaved-count")).toHaveTextContent("1 項變更尚未儲存");
    expect(row("model.maxTokensPerRequest")).toHaveAttribute("data-dirty");
    await userEvent.click(save);

    expect(await screen.findByText("已儲存 1 項參數")).toBeInTheDocument();
    expect(putCalls()).toHaveLength(1);
    expect(putCalls()[0].path).toBe("/api/v1/settings/model/maxTokensPerRequest");
    expect(putCalls()[0].body).toEqual({ value: "4096" });
    await waitFor(() => expect(screen.queryByTestId("unsaved-count")).toBeNull());
    expect(inRow("model.maxTokensPerRequest").getByRole("textbox")).toHaveValue("4096");
  });

  it("本地驗證紅字：超出範圍就地提示，儲存被擋（不送任何請求）", async () => {
    await mount();
    const input = inRow("model.temperature").getByRole("textbox");
    await userEvent.clear(input);
    await userEvent.type(input, "3");
    expect(inRow("model.temperature").getByTestId("setting-error")).toHaveTextContent("需為數字（0～2）");
    await userEvent.click(screen.getByRole("button", { name: "儲存變更" }));
    expect(await screen.findByText("有 1 項參數不合法，請先修正紅字欄位")).toBeInTheDocument();
    expect(putCalls()).toHaveLength(0);
  });

  it("後端 400 的 reason／errors 對應到該列（逐字常數＋欄位訊息＋traceId），並停在失敗的鍵", async () => {
    await mount();
    // 本地範圍較寬鬆：201000 本地通過、後端（契約上限 200000）拒絕
    overrides.push((c) =>
      c.method === "PUT" && c.path.endsWith("/maxTokensPerRequest")
        ? failure(400, { message: "參數驗證失敗", reason: REASONS.SETTINGS_VALUE_INVALID, errors: [{ field: "value", message: "需為整數（1～200000）" }] })
        : undefined,
    );
    await userEvent.clear(inRow("model.temperature").getByRole("textbox"));
    await userEvent.type(inRow("model.temperature").getByRole("textbox"), "0.5");
    await userEvent.clear(inRow("model.maxTokensPerRequest").getByRole("textbox"));
    await userEvent.type(inRow("model.maxTokensPerRequest").getByRole("textbox"), "100000");
    await userEvent.click(screen.getByRole("button", { name: "儲存變更" }));

    const error = await inRow("model.maxTokensPerRequest").findByTestId("setting-error");
    expect(error).toHaveTextContent("參數值不符合型別或驗證規則：需為整數（1～200000）");
    expect(error).toHaveTextContent("traceId：tr-400");
    // 失敗不顯示成功 toast；已先存的溫度仍存了（逐鍵儲存），之後的鍵沒送
    expect(screen.queryByText(/^已儲存 \d+ 項參數$/)).toBeNull();
    expect(await screen.findByText(/儲存失敗：最大 Token／請求（已儲存 0 項，其餘未送出）/)).toBeInTheDocument();
    expect(putCalls().map((c) => c.path)).toEqual(["/api/v1/settings/model/maxTokensPerRequest"]);
    // 使用者的草稿還在，改正後可再存
    expect(inRow("model.temperature").getByRole("textbox")).toHaveValue("0.5");
    expect(screen.getByTestId("unsaved-count")).toHaveTextContent("2 項變更尚未儲存");
  });

  it("BOOLEAN：toggle 點一下變髒，儲存送 \"true\"", async () => {
    await mount();
    await userEvent.click(inRow("model.enableKernelBrain").getByRole("switch"));
    expect(inRow("model.enableKernelBrain").getByRole("switch")).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByRole("button", { name: "儲存變更" }));
    await screen.findByText("已儲存 1 項參數");
    expect(putCalls()[0].body).toEqual({ value: "true" });
  });
});

describe("敏感參數（US-S-02、US-S-04）", () => {
  it("儲存前二次確認：取消不送、確認才以 confirm=true 送出；歷史只記遮罩", async () => {
    await mount();
    const key = inRow("model.apiKey").getByLabelText("API Key");
    await userEvent.click(key);
    await userEvent.keyboard("sk-new-key");
    await userEvent.click(screen.getByRole("button", { name: "儲存變更" }));

    const dialog = screen.getByRole("dialog", { name: "確認更新敏感參數" });
    expect(dialog).toHaveTextContent("API Key");
    expect(within(dialog).getByTestId("confirm-impact-notes")).toHaveTextContent("加密儲存；新批次起使用新金鑰");
    await userEvent.click(within(dialog).getByRole("button", { name: "取消" }));
    expect(putCalls()).toHaveLength(0);
    expect(screen.getByTestId("unsaved-count")).toBeInTheDocument(); // 草稿保留

    await userEvent.click(screen.getByRole("button", { name: "儲存變更" }));
    await userEvent.click(within(screen.getByRole("dialog", { name: "確認更新敏感參數" })).getByRole("button", { name: "確認儲存" }));
    await screen.findByText("已儲存 1 項參數");
    expect(putCalls()).toHaveLength(1);
    expect(putCalls()[0].body).toEqual({ value: "sk-new-key", confirm: true });
  });

  it("沒改過的遮罩不會被送出；非敏感參數的儲存不會跳確認框", async () => {
    await mount();
    await userEvent.click(inRow("model.apiKey").getByLabelText("API Key")); // 聚焦但沒輸入
    expect(screen.queryByTestId("unsaved-count")).toBeNull();
    await userEvent.click(inRow("model.enableKernelBrain").getByRole("switch"));
    await userEvent.click(screen.getByRole("button", { name: "儲存變更" }));
    expect(screen.queryByRole("dialog", { name: "確認更新敏感參數" })).toBeNull();
    await screen.findByText("已儲存 1 項參數");
  });

  it("顯示：ADMIN 以 reveal=true 取明文；再按「隱藏」回到遮罩（不再請求）", async () => {
    await mount();
    await userEvent.click(inRow("model.apiKey").getByRole("button", { name: "顯示：API Key" }));
    const input = inRow("model.apiKey").getByLabelText("API Key");
    await waitFor(() => expect(input).toHaveValue("sk-plain-secret"));
    expect(input).toHaveAttribute("type", "text");
    const reveal = calls.filter((c) => c.query.get("reveal") === "true");
    expect(reveal).toHaveLength(1);
    expect(reveal[0].path).toBe("/api/v1/settings/model");
    // 揭露後沒改 → 不算變更
    expect(screen.queryByTestId("unsaved-count")).toBeNull();

    await userEvent.click(inRow("model.apiKey").getByRole("button", { name: "隱藏：API Key" }));
    expect(inRow("model.apiKey").getByLabelText("API Key")).toHaveAttribute("type", "password");
    await userEvent.click(inRow("model.apiKey").getByRole("button", { name: "顯示：API Key" }));
    expect(calls.filter((c) => c.query.get("reveal") === "true")).toHaveLength(1); // 已有明文快取，不重打
  });

  it("尚未設定的加密鍵：顯示鈕停用、輸入框提示「尚未設定」", async () => {
    await mount();
    await userEvent.click(screen.getByRole("tab", { name: "AutoClaude" }));
    expect(inRow("autoclaude.dbDsn").getByRole("button", { name: "顯示：資料庫連線字串（DSN）" })).toBeDisabled();
    expect(inRow("autoclaude.dbDsn").getByLabelText("資料庫連線字串（DSN）")).toHaveAttribute("placeholder", "尚未設定");
  });
});

describe("重置（US-S-03）", () => {
  it("一般參數：每列尾端「重置」，直接 POST reset（不帶 confirm）；已是預設值時停用", async () => {
    await mount();
    await userEvent.click(screen.getByRole("tab", { name: "執行" }));
    expect(inRow("execution.globalTokenBudget").getByRole("button", { name: "重置：全域 Token 預算" })).toBeEnabled();
    expect(inRow("execution.dagSchedulerStrategy").getByRole("button", { name: "重置：DAG 排程策略" })).toBeDisabled();
    await userEvent.click(inRow("execution.globalTokenBudget").getByRole("button", { name: "重置：全域 Token 預算" }));
    await screen.findByText("已重置為預設值：全域 Token 預算");
    const post = calls.find((c) => c.method === "POST");
    expect(post?.url).toBe("/api/v1/settings/execution/globalTokenBudget/reset");
    await waitFor(() => expect(inRow("execution.globalTokenBudget").getByRole("textbox")).toHaveValue("1000000"));
  });

  it("敏感參數：先確認，再以 ?confirm=true 重置", async () => {
    await mount();
    await userEvent.click(inRow("model.apiKey").getByRole("button", { name: "重置：API Key" }));
    const dialog = screen.getByRole("dialog", { name: "確認重置敏感參數" });
    expect(calls.some((c) => c.method === "POST")).toBe(false);
    await userEvent.click(within(dialog).getByRole("button", { name: "確認重置" }));
    await screen.findByText("已重置為預設值：API Key");
    expect(calls.find((c) => c.method === "POST")?.url).toBe("/api/v1/settings/model/apiKey/reset?confirm=true");
  });

  it("全部重置為預設值：對六個分類各呼叫一次分類級 reset；加密參數預設不含，勾選才帶 confirm=true", async () => {
    await mount();
    await userEvent.click(screen.getByRole("button", { name: "全部重置為預設值" }));
    let dialog = screen.getByRole("dialog", { name: "全部重置為預設值" });
    await userEvent.click(within(dialog).getByRole("button", { name: "全部重置" }));
    await screen.findByText("已把全部分類重置為預設值");
    const resets = calls.filter((c) => c.method === "POST");
    expect(resets.map((c) => c.url)).toEqual(CATEGORIES.map((c) => `/api/v1/settings/${c}/reset`));

    calls.length = 0;
    await userEvent.click(screen.getByRole("button", { name: "全部重置為預設值" }));
    dialog = screen.getByRole("dialog", { name: "全部重置為預設值" });
    await userEvent.click(within(dialog).getByRole("checkbox"));
    await userEvent.click(within(dialog).getByRole("button", { name: "全部重置" }));
    await waitFor(() => expect(calls.filter((c) => c.method === "POST")).toHaveLength(6));
    expect(calls.filter((c) => c.method === "POST").every((c) => c.url.endsWith("/reset?confirm=true"))).toBe(true);
  });

  it("全部重置中途失敗：停下並顯示原因，後面的分類不送", async () => {
    await mount();
    overrides.push((c) => (c.url === "/api/v1/settings/execution/reset" ? failure(400, { message: "跨鍵校驗失敗", reason: REASONS.SETTINGS_TOKEN_GUARD_ORDER }) : undefined));
    await userEvent.click(screen.getByRole("button", { name: "全部重置為預設值" }));
    const dialog = screen.getByRole("dialog", { name: "全部重置為預設值" });
    await userEvent.click(within(dialog).getByRole("button", { name: "全部重置" }));
    expect(await within(dialog).findByText(/重置「執行」失敗：halt_threshold_pct 必須大於 compact_threshold_pct/)).toBeInTheDocument();
    expect(calls.filter((c) => c.method === "POST").map((c) => c.url)).toEqual([
      "/api/v1/settings/model/reset",
      "/api/v1/settings/agent/reset",
      "/api/v1/settings/execution/reset",
    ]);
    expect(dialog).toBeInTheDocument(); // 不關閉，讓使用者看到原因
  });
});

describe("Token Guard 小卡（NFR-SEC-05）", () => {
  it("執行 tab：兩個門檻鍵成對放在 Token Guard 卡，不重複出現在一般列", async () => {
    await mount();
    await userEvent.click(screen.getByRole("tab", { name: "執行" }));
    const card = within(screen.getByTestId("token-guard-card"));
    expect(card.getByLabelText("壓縮門檻（%）")).toHaveValue("80");
    expect(card.getByLabelText("停機門檻（%）")).toHaveValue("90");
    expect(screen.getAllByTestId("setting-row").filter((r) => r.getAttribute("data-setting") === "execution.compactThresholdPct")).toHaveLength(1);
    expect(within(screen.getByTestId("settings-panel")).getAllByLabelText("壓縮門檻（%）")).toHaveLength(1);
  });

  it("成對套用：一次 PUT /settings/execution/token-guard，帶兩個整數", async () => {
    await mount();
    await userEvent.click(screen.getByRole("tab", { name: "執行" }));
    const card = within(screen.getByTestId("token-guard-card"));
    await userEvent.clear(card.getByLabelText("壓縮門檻（%）"));
    await userEvent.type(card.getByLabelText("壓縮門檻（%）"), "70");
    await userEvent.clear(card.getByLabelText("停機門檻（%）"));
    await userEvent.type(card.getByLabelText("停機門檻（%）"), "95");
    await userEvent.click(card.getByRole("button", { name: "套用 Token Guard" }));
    await screen.findByText("已套用 Token Guard");
    expect(putCalls()).toHaveLength(1);
    expect(putCalls()[0].path).toBe("/api/v1/settings/execution/token-guard");
    expect(putCalls()[0].body).toEqual({ compactThresholdPct: 70, haltThresholdPct: 95 });
  });

  it("前端鏡射跨鍵規則：halt 不大於 compact 就地顯示逐字 reason，套用停用、不送請求", async () => {
    await mount();
    await userEvent.click(screen.getByRole("tab", { name: "執行" }));
    const card = within(screen.getByTestId("token-guard-card"));
    await userEvent.clear(card.getByLabelText("停機門檻（%）"));
    await userEvent.type(card.getByLabelText("停機門檻（%）"), "60");
    expect(card.getByTestId("token-guard-error")).toHaveTextContent("halt_threshold_pct 必須大於 compact_threshold_pct");
    expect(card.getByRole("button", { name: "套用 Token Guard" })).toBeDisabled();
    expect(putCalls()).toHaveLength(0);
  });

  it("後端 400：顯示 reason（伺服器端狀態與前端不同步時，例如別人剛改過）", async () => {
    await mount();
    await userEvent.click(screen.getByRole("tab", { name: "執行" }));
    overrides.push((c) =>
      c.method === "PUT" && c.path.endsWith("/token-guard")
        ? failure(400, { message: "跨鍵校驗失敗", reason: REASONS.SETTINGS_TOKEN_GUARD_ORDER, errors: [{ field: "haltThresholdPct", message: "必須大於 compactThresholdPct" }], details: { compactThresholdPct: 70, haltThresholdPct: 95 } })
        : undefined,
    );
    const card = within(screen.getByTestId("token-guard-card"));
    await userEvent.clear(card.getByLabelText("壓縮門檻（%）"));
    await userEvent.type(card.getByLabelText("壓縮門檻（%）"), "70");
    await userEvent.clear(card.getByLabelText("停機門檻（%）"));
    await userEvent.type(card.getByLabelText("停機門檻（%）"), "95");
    await userEvent.click(card.getByRole("button", { name: "套用 Token Guard" }));
    const error = await card.findByTestId("token-guard-error");
    expect(error).toHaveTextContent("halt_threshold_pct 必須大於 compact_threshold_pct");
    expect(error).toHaveTextContent("必須大於 compactThresholdPct");
    expect(error).toHaveTextContent("traceId：tr-400");
    expect(screen.queryByText("已套用 Token Guard")).toBeNull();
    // 草稿保留，使用者可修正後重試
    expect(card.getByLabelText("停機門檻（%）")).toHaveValue("95");
  });

  it("儲存變更時兩鍵都改了：合成一次原子 PUT；只改一鍵：一樣走群組端點，對端帶畫面上的目前值", async () => {
    await mount();
    await userEvent.click(screen.getByRole("tab", { name: "執行" }));
    const card = within(screen.getByTestId("token-guard-card"));
    await userEvent.clear(card.getByLabelText("壓縮門檻（%）"));
    await userEvent.type(card.getByLabelText("壓縮門檻（%）"), "60");
    await userEvent.clear(card.getByLabelText("停機門檻（%）"));
    await userEvent.type(card.getByLabelText("停機門檻（%）"), "85");
    await userEvent.click(screen.getByRole("button", { name: "儲存變更" }));
    await screen.findByText("已儲存 2 項參數");
    expect(putCalls().map((c) => c.path)).toEqual(["/api/v1/settings/execution/token-guard"]);

    calls.length = 0;
    await userEvent.clear(card.getByLabelText("停機門檻（%）"));
    await userEvent.type(card.getByLabelText("停機門檻（%）"), "88");
    await userEvent.click(screen.getByRole("button", { name: "儲存變更" }));
    await screen.findByText("已儲存 1 項參數");
    expect(putCalls().map((c) => c.path)).toEqual(["/api/v1/settings/execution/token-guard"]);
    expect(putCalls()[0].body).toEqual({ compactThresholdPct: 60, haltThresholdPct: 88 });
  });
});

describe("測試連線（US-S-05）", () => {
  it("成功：測試中 spinner → 綠勾「連線成功（延遲 230ms）」；沒改過的欄位不送（空 body）", async () => {
    await mount();
    let release!: (r: Response) => void;
    overrides.push((c) => (c.path === "/api/v1/settings/test-connection" ? undefined : undefined));
    vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
      if (String(input).endsWith("/test-connection")) {
        calls.push({ method: init?.method ?? "GET", url: input, path: input, query: new URLSearchParams(), body: init?.body });
        return new Promise<Response>((resolve) => (release = resolve));
      }
      return Promise.resolve(failure(404));
    }));
    await userEvent.click(screen.getByRole("button", { name: "測試連線" }));
    expect(await screen.findByText("測試中…")).toBeInTheDocument();
    expect(calls.at(-1)?.body).toBeUndefined();
    release(envelope({ success: true, latencyMs: 230, message: "連線成功", resolvedHost: "api.minimax.io", httpStatus: 200 }));
    expect(await screen.findByText("連線成功（延遲 230ms）")).toBeInTheDocument();
  });

  it("帶表單內尚未儲存的 apiUrl／apiKey／model；失敗顯示紅字原因", async () => {
    await mount();
    overrides.push((c) =>
      c.path === "/api/v1/settings/test-connection"
        ? envelope({ success: false, latencyMs: null, message: "認證失敗（HTTP 401）", resolvedHost: "api.minimax.io", httpStatus: 401 })
        : undefined,
    );
    const url = inRow("model.apiUrl").getByRole("textbox");
    await userEvent.clear(url);
    await userEvent.type(url, "https://api.minimax.io/v1/chat");
    await userEvent.click(inRow("model.apiKey").getByLabelText("API Key"));
    await userEvent.keyboard("sk-typed");
    await userEvent.click(screen.getByRole("button", { name: "測試連線" }));
    expect(await screen.findByText(/連線失敗：認證失敗（HTTP 401）/)).toBeInTheDocument();
    const call = calls.find((c) => c.path === "/api/v1/settings/test-connection");
    expect(call?.body).toEqual({ apiUrl: "https://api.minimax.io/v1/chat", apiKey: "sk-typed" });
  });

  it("422 SSRF／allowlist：顯示 reason 與違規類別、host", async () => {
    await mount();
    overrides.push((c) =>
      c.path === "/api/v1/settings/test-connection"
        ? failure(422, { message: "位址被拒", reason: REASONS.SETTINGS_URL_REJECTED, details: { host: "10.0.0.5", violation: "private_ip" } })
        : undefined,
    );
    await userEvent.click(screen.getByRole("button", { name: "測試連線" }));
    const result = await screen.findByTestId("test-connection-result");
    await waitFor(() => expect(result).toHaveTextContent("目標位址未通過 SSRF／allowlist 檢查（不可連到私有網段位址；host：10.0.0.5）"));
  });
});

describe("修改歷史（US-S-07）", () => {
  it("等寬字體逐列：時間／參數／舊值 → 新值／@使用者；加密參數只有遮罩", async () => {
    await mount();
    const lines = await screen.findAllByTestId("history-line");
    expect(lines).toHaveLength(2);
    expect(lines[0]).toHaveTextContent("2026-10-15 15:30");
    expect(lines[0]).toHaveTextContent("model.temperature");
    expect(lines[0]).toHaveTextContent("0.5 → 0.3");
    expect(lines[0]).toHaveTextContent("@admin");
    expect(lines[1]).toHaveTextContent(`${MASKED} → ${MASKED}`);
    expect(lines[0].parentElement).toHaveClass("font-mono");
    const historyCall = calls.find((c) => c.path === "/api/v1/settings/history");
    expect(historyCall?.url).toBe("/api/v1/settings/history?category=model&page=0&size=20");
  });

  it("換分類 tab：歷史改查該分類", async () => {
    await mount();
    await screen.findAllByTestId("history-line");
    await userEvent.click(screen.getByRole("tab", { name: "執行" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/api/v1/settings/history?category=execution&page=0&size=20")).toBe(true));
  });
});

describe("匯出／匯入設定（US-S-06）", () => {
  it("匯出：POST export，以 Content-Disposition 的檔名下載 JSON（不包封包）", async () => {
    await mount();
    let downloaded: string | undefined;
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:settings");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      downloaded = this.download;
    });
    overrides.push((c) =>
      c.path === "/api/v1/settings/export"
        ? new Response('{"version":1,"exportedAt":"2026-10-15T08:45:00Z","configs":[]}', {
            status: 200,
            headers: { "content-type": "application/json", "content-disposition": 'attachment; filename="aisdlc-settings-20261015.json"' },
          })
        : undefined,
    );
    await userEvent.click(screen.getByRole("button", { name: "匯出設定" }));
    expect(await screen.findByText(/已匯出設定/)).toBeInTheDocument();
    expect(calls.find((c) => c.path === "/api/v1/settings/export")?.method).toBe("POST");
    expect(downloaded).toBe("aisdlc-settings-20261015.json");
  });

  it("匯入：選 JSON 檔上傳（multipart），顯示 applied／skipped／errors[]；非 .json 與超過 1MB 當場擋下", async () => {
    await mount();
    overrides.push((c) =>
      c.path === "/api/v1/settings/import"
        ? envelope({ applied: 1, skipped: 47, errors: [{ category: "monitor", key: "refreshIntervalMs", reason: REASONS.SETTINGS_VALUE_INVALID }, { category: "model", key: "ghost", reason: "設定鍵不存在" }] })
        : undefined,
    );
    await userEvent.click(screen.getByRole("button", { name: "匯入設定" }));
    const dialog = screen.getByRole("dialog", { name: "匯入設定" });
    const input = within(dialog).getByTestId("settings-file-input");

    await userEvent.setup({ applyAccept: false }).upload(input, new File(["x"], "notes.txt"));
    expect(within(dialog).getByRole("alert")).toHaveTextContent(REASONS.SETTINGS_FILE_NOT_JSON);
    expect(within(dialog).getByRole("button", { name: "匯入" })).toBeDisabled();

    const file = new File(['{"version":1,"configs":[]}'], "aisdlc-settings.json", { type: "application/json" });
    await userEvent.upload(input, file);
    expect(within(dialog).getByTestId("settings-selected-file")).toHaveTextContent("aisdlc-settings.json");
    await userEvent.click(within(dialog).getByRole("button", { name: "匯入" }));

    const result = await within(dialog).findByTestId("settings-import-result");
    expect(within(result).getByTestId("import-applied")).toHaveTextContent("1");
    expect(within(result).getByTestId("import-skipped")).toHaveTextContent("47");
    expect(within(result).getByTestId("import-failed")).toHaveTextContent("2");
    const errors = within(result).getAllByTestId("settings-import-error");
    expect(errors[0]).toHaveTextContent("monitor.refreshIntervalMs — 參數值不符合型別或驗證規則");
    expect(errors[1]).toHaveTextContent("model.ghost — 設定鍵不存在");
    const post = calls.find((c) => c.path === "/api/v1/settings/import");
    expect((post?.body as FormData).get("file")).toBe(file);
  });
});

describe("角色（契約 §4.6 G-S2）：非 ADMIN 整頁唯讀", () => {
  it.each(["OPERATOR", "VIEWER"] as const)("%s：看得到參數與歷史，但輸入、重置、儲存、匯出入、測試連線全部停用並附說明", async (role) => {
    await mount(role);
    expect(screen.getByTestId("readonly-banner")).toHaveTextContent(`目前角色（${role}）只能檢視系統參數`);
    expect(inRow("model.maxTokensPerRequest").getByRole("textbox")).toBeDisabled();
    expect(inRow("model.enableKernelBrain").getByRole("switch")).toBeDisabled();
    expect(inRow("model.provider").getByRole("combobox")).toBeDisabled();
    expect(inRow("model.apiKey").getByRole("button", { name: "顯示：API Key" })).toBeDisabled();
    expect(inRow("model.apiKey").getByRole("button", { name: "顯示：API Key" })).toHaveAttribute("title", "僅 ADMIN 可揭露敏感參數");
    expect(inRow("model.apiKey").getByRole("button", { name: "重置：API Key" })).toBeDisabled();
    for (const name of ["儲存變更", "全部重置為預設值", "匯出設定", "匯入設定", "測試連線"]) {
      expect(screen.getByRole("button", { name })).toBeDisabled();
      expect(screen.getByRole("button", { name })).toHaveAttribute("title", expect.stringContaining("ADMIN"));
    }
    expect(await screen.findAllByTestId("history-line")).toHaveLength(2);
    expect(putCalls()).toHaveLength(0);
  });

  it("ADMIN 沒有唯讀提示", async () => {
    await mount("ADMIN");
    expect(screen.queryByTestId("readonly-banner")).toBeNull();
  });
});

describe("載入與錯誤", () => {
  it("載入失敗：顯示錯誤與 traceId，可重試", async () => {
    signIn("ADMIN");
    stubApi(() => failure(500, { message: "伺服器錯誤" }));
    render(
      <Providers client={makeClient()}>
        <SettingsView />
      </Providers>,
    );
    expect(await screen.findByText("無法載入系統參數")).toBeInTheDocument();
    expect(screen.getByText("traceId：tr-500")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重試" })).toBeInTheDocument();
  });
});
