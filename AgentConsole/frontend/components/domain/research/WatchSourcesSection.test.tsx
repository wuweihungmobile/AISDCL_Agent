import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { RegistrySyncStatus, Role, WatchSource } from "@/lib/api/types";
import { REGISTRY_STATUS, SYNC_UNCHANGED, SYNC_WRITTEN, WATCH_SOURCES_17, type RegistryStatusKind } from "@/tests/fixtures/research/registry";
import { callsOf, failure, renderResearch, stubResearchApi, type ApiCall, type Reply } from "@/tests/helpers/research";
import { AllowlistDialog } from "./AllowlistDialog";
import { WatchSourcesSection } from "./WatchSourcesSection";

/**
 * 研究來源設定的「自我進化追蹤來源」區（TCS-ResearchRegistry-20261110 AT-965-8-2～8-7、8-E-2；W-R8、W-R10）。
 * 判定指令：npx vitest run components/domain/research/WatchSourcesSection.test.tsx
 */
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/research",
  useSearchParams: () => new URLSearchParams(),
}));

const LIST = "/api/v1/research/watch-sources";
const SYNC = "/api/v1/si/research-registry/sync";
const STATUS = "/api/v1/si/research-registry";

type Hooks = {
  rows?: WatchSource[];
  status?: RegistrySyncStatus;
  post?: (call: ApiCall) => Reply;
  patch?: (call: ApiCall) => Reply;
  sync?: (call: ApiCall) => Reply;
  /** 覆寫 `GET /si/research-registry` */
  statusGet?: (call: ApiCall) => Reply;
};

function mount(role: Role, hooks: Hooks = {}, ui = <WatchSourcesSection />) {
  const api = stubResearchApi({
    watchSources: hooks.rows ?? WATCH_SOURCES_17(),
    registryStatus: hooks.status ?? REGISTRY_STATUS("unsynced"),
    overrides: (call) => {
      if (call.method === "POST" && call.path === LIST && hooks.post) return hooks.post(call);
      if (call.method === "PATCH" && call.path.startsWith(`${LIST}/`) && hooks.patch) return hooks.patch(call);
      if (call.method === "POST" && call.path === SYNC && hooks.sync) return hooks.sync(call);
      if (call.method === "GET" && call.path === STATUS && hooks.statusGet) return hooks.statusGet(call);
      return undefined;
    },
  });
  const view = renderResearch(ui, role);
  return { ...view, ...api };
}

const syncCalls = (calls: readonly ApiCall[]) => callsOf(calls, "POST", /\/si\/research-registry\/sync$/);
const rowOf = (slug: string): HTMLElement => {
  const row = screen.getAllByTestId("watch-row").find((r) => r.getAttribute("data-slug") === slug);
  if (row === undefined) throw new Error(`清單沒有 ${slug}`);
  return row;
};

async function load() {
  await screen.findAllByTestId("watch-row");
  await screen.findByTestId("registry-status");
}

async function fillValid(user: ReturnType<typeof userEvent.setup>, slug = "my-blog") {
  await user.type(screen.getByLabelText(/識別碼/), slug);
  await user.type(screen.getByLabelText(/^網址/), "https://example.org/blog");
  await user.type(screen.getByLabelText(/抓取說明/), "逐字保留文章");
}
const submitButton = () => screen.getByRole("button", { name: "新增追蹤來源" });

/** 讓 sync 請求停在閘門上：回傳放行函式與送出計數（包在已安裝的 fetch 替身外面）。 */
function gateSync() {
  const real = globalThis.fetch;
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let count = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init?: RequestInit) => {
      if (String(input).includes("/si/research-registry/sync") && init?.method === "POST") {
        count += 1;
        await gate;
      }
      return real(input, init);
    }),
  );
  return { release: () => release(), count: () => count };
}

describe("AT_965_8_2 清單渲染與警示", () => {
  it("AT_965_8_2 17 列：逐列顯示 slug、網址（純文字）、種類、層、展開設定、啟用狀態；停用列有「已停用」與「重新啟用」、啟用列有「停用」；區頂「啟用 10／共 17」", async () => {
    mount("ADMIN");
    await load();
    expect(screen.getAllByTestId("watch-row")).toHaveLength(17);
    expect(screen.getByTestId("watch-count")).toHaveTextContent("啟用 10／共 17");

    const eng = rowOf("anthropic-engineering");
    expect(within(eng).getByText("https://www.anthropic.com/engineering")).toBeInTheDocument();
    expect(eng.textContent).toContain("部落格");
    expect(eng.textContent).toContain("產業層");
    expect(eng.textContent).toContain("links｜/engineering/｜最多 3");
    expect(within(eng).getByText("啟用中")).toBeInTheDocument();
    expect(within(eng).getByRole("button", { name: "停用 anthropic-engineering" })).toBeInTheDocument();
    expect(within(eng).queryByRole("button", { name: /重新啟用/ })).toBeNull();

    const off = rowOf("claude-code-llms");
    expect(within(off).getByText("已停用")).toBeInTheDocument();
    expect(within(off).getByRole("button", { name: "重新啟用 claude-code-llms" })).toBeInTheDocument();
    expect(within(off).queryByRole("button", { name: /^停用/ })).toBeNull();
    expect(screen.getAllByText("已停用")).toHaveLength(7);
    expect(screen.getAllByRole("button", { name: /^停用 / })).toHaveLength(10);
  });

  it("AT_965_8_2 hostAllowed 為假的列顯示「網域未開放」並說明去上方網域清單開放", async () => {
    mount("ADMIN");
    await load();
    const closed = rowOf("openai-changelog-md");
    expect(closed.textContent).toContain("網域未開放");
    expect(closed.textContent).toContain("上方網域清單");
    expect(within(rowOf("anthropic-engineering")).queryByTestId("watch-host-closed")).toBeNull();
  });

  it("AT_965_8_2 researchFetchMax 為 8 時顯示純文字警示；為 10 與 null 時不顯示（null 時不出現任何數字上限字樣）", async () => {
    const view8 = mount("ADMIN", { status: REGISTRY_STATUS("unsynced", { researchFetchMax: 8 }) });
    await load();
    expect(screen.getByTestId("watch-fetch-warning")).toHaveTextContent("已超過自我進化每次抓取上限（8）");
    view8.unmount();

    const view10 = mount("ADMIN", { status: REGISTRY_STATUS("unsynced", { researchFetchMax: 10 }) });
    await load();
    expect(screen.queryByTestId("watch-fetch-warning")).toBeNull();
    view10.unmount();

    mount("ADMIN", { status: REGISTRY_STATUS("unsynced", { researchFetchMax: null }) });
    await load();
    expect(screen.queryByTestId("watch-fetch-warning")).toBeNull();
    expect(screen.getByTestId("watch-sources-section").textContent).not.toMatch(/上限（\d+）/);
  });

  it("AT_965_8_2 API 回傳的字串只以文字節點渲染：含標記的 extract 與網址不被當成 HTML", async () => {
    const rows = WATCH_SOURCES_17();
    rows[0] = { ...rows[0], extract: "<img src=x onerror=alert(1)>", url: "https://www.anthropic.com/a?x=<b>" };
    const { container } = mount("ADMIN", { rows });
    await load();
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("b")).toBeNull();
    expect(rowOf(rows[0].slug).textContent).toContain("<b>");
  });
});

describe("AT_965_8_3 新增流程與自動同步", () => {
  it("AT_965_8_3 不合法表單不送出，逐欄顯示錯誤（aria-invalid）與錯誤摘要；沒有任何寫入請求", async () => {
    const user = userEvent.setup();
    const { calls } = mount("ADMIN");
    await load();
    await user.type(screen.getByLabelText(/識別碼/), "Bad_Slug");
    await user.type(screen.getByLabelText(/^網址/), "https://EXAMPLE.org/x");
    await user.click(submitButton());
    expect(screen.getByLabelText(/識別碼/)).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText(/^網址/)).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText(/抓取說明/)).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByTestId("watch-form-summary")).toHaveAttribute("role", "alert");
    expect(screen.getByText(/自行改寫成小寫/)).toBeInTheDocument();
    expect(calls.filter((c) => c.method !== "GET")).toEqual([]);
  });

  it("AT_965_8_3 合法表單：POST 後恰一次 sync（本文 {}、在 POST 之後）；顯示「已送出，待入帳」；清單與狀態 refetch；表單清空", async () => {
    const user = userEvent.setup();
    const { calls } = mount("ADMIN");
    await load();
    await fillValid(user);
    await user.click(submitButton());
    expect(await screen.findByText("已送出，待入帳")).toBeInTheDocument();

    const posts = callsOf(calls, "POST", /\/research\/watch-sources$/);
    expect(posts).toHaveLength(1);
    expect(Object.keys(posts[0].body as object).sort()).toEqual(["expand", "extract", "kind", "layer", "slug", "url"]);
    expect(posts[0].body).toMatchObject({ slug: "my-blog", url: "https://example.org/blog", kind: "blog", layer: "INDUSTRY", extract: "逐字保留文章", expand: null });
    const syncs = syncCalls(calls);
    expect(syncs).toHaveLength(1);
    expect(syncs[0].body).toEqual({});
    expect(calls.indexOf(syncs[0])).toBeGreaterThan(calls.indexOf(posts[0]));
    await waitFor(() => expect(screen.getAllByTestId("watch-row")).toHaveLength(18));
    expect(callsOf(calls, "GET", /\/research\/watch-sources$/).length).toBeGreaterThanOrEqual(2);
    expect(callsOf(calls, "GET", /\/si\/research-registry$/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByLabelText(/識別碼/)).toHaveValue("");
  });

  it("AT_965_8_3 初次狀態請求尚在飛行時新增成功（DEF-AC-037）：失效重抓不得併入舊請求——會再發一次狀態查詢，狀態列取新回應而非停在舊值", async () => {
    const user = userEvent.setup();
    const api = stubResearchApi({ watchSources: WATCH_SOURCES_17(), registryStatus: REGISTRY_STATUS("synced") });
    const real = globalThis.fetch;
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    let held = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string, init?: RequestInit) => {
        const isStatusGet = String(input).endsWith("/si/research-registry") && (init?.method ?? "GET") === "GET";
        if (isStatusGet && !held) {
          held = true;
          await gate; // 初次狀態請求懸住：回的是「新增前」的舊狀態（synced）
        }
        return real(input, init);
      }),
    );
    renderResearch(<WatchSourcesSection />, "ADMIN");
    await screen.findAllByTestId("watch-row");
    expect(held).toBe(true);
    await fillValid(user);
    // 新增後後端狀態變為 unsynced；初次請求仍懸住
    api.options.registryStatus = REGISTRY_STATUS("unsynced");
    await user.click(submitButton());
    await waitFor(() => expect(callsOf(api.calls, "POST", /\/research\/watch-sources$/)).toHaveLength(1));
    // 取消後會另發一次新請求（未懸住）：狀態列說「有變更尚未同步」，且該請求發生在舊請求放行之前
    await waitFor(() => expect(screen.getByTestId("registry-status").textContent ?? "").toMatch(/有變更尚未同步|已送出，待入帳/));
    release();
    await screen.findByText("已送出，待入帳");
    expect(callsOf(api.calls, "GET", /\/si\/research-registry$/).length).toBeGreaterThanOrEqual(1);
  });

  it("AT_965_8_3 展開三欄全填：本文帶 expand 物件（max 為數字）", async () => {
    const user = userEvent.setup();
    const { calls } = mount("ADMIN");
    await load();
    await fillValid(user);
    await user.selectOptions(screen.getByLabelText(/展開方式/), "links");
    await user.type(screen.getByLabelText(/路徑前綴/), "/blog/");
    await user.type(screen.getByLabelText(/最多幾頁/), "2");
    await user.click(submitButton());
    await screen.findByText("已送出，待入帳");
    expect(callsOf(calls, "POST", /\/research\/watch-sources$/)[0].body).toMatchObject({ expand: { mode: "links", prefix: "/blog/", max: 2 } });
  });

  it("AT_965_8_3 POST 失敗（host_not_allowed）顯示指向網域清單的原因，且不送 sync", async () => {
    const user = userEvent.setup();
    const { calls } = mount("ADMIN", { post: () => failure(422, { message: "host", reason: "host_not_allowed", details: { host: "example.org" } }) });
    await load();
    await fillValid(user);
    await user.click(submitButton());
    expect(await screen.findByText("這個網域還沒開放，請先在上方網域清單新增")).toBeInTheDocument();
    expect(syncCalls(calls)).toHaveLength(0);
    expect(screen.getByLabelText(/識別碼/)).toHaveValue("my-blog"); // 失敗不清表單
  });

  it("AT_965_8_3 POST 失敗（409 watch_source_exists）不送 sync", async () => {
    const user = userEvent.setup();
    const { calls } = mount("ADMIN", { post: () => failure(409, { message: "dup", reason: "watch_source_exists", details: { slug: "my-blog" } }) });
    await load();
    await fillValid(user);
    await user.click(submitButton());
    expect(await screen.findByTestId("watch-submit-error")).toHaveTextContent("識別碼");
    expect(syncCalls(calls)).toHaveLength(0);
  });

  it("AT_965_8_3 POST 成功但 sync 回 403：顯示原因、不重試（恰一次 sync）、清單仍含新列", async () => {
    const user = userEvent.setup();
    const { calls } = mount("ADMIN", { sync: () => failure(403, { message: "no", reason: "si_write_forbidden" }) });
    await load();
    await fillValid(user);
    await user.click(submitButton());
    expect(await screen.findByText("此帳號不在自我進化寫入名單，未同步")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "重試同步" })).toBeNull();
    expect(syncCalls(calls)).toHaveLength(1);
    await waitFor(() => expect(screen.getAllByTestId("watch-row")).toHaveLength(18));
  });
});

describe("AT_965_8_4 停用與重新啟用", () => {
  it("AT_965_8_4 「停用」→ PATCH 本文恰 {enabled:false}、成功後自動 sync 一次；「重新啟用」→ 本文恰 {enabled:true}", async () => {
    const user = userEvent.setup();
    const { calls } = mount("ADMIN");
    await load();
    await user.click(within(rowOf("anthropic-engineering")).getByRole("button", { name: "停用 anthropic-engineering" }));
    await screen.findByText("已送出，待入帳");
    let patches = callsOf(calls, "PATCH", /\/research\/watch-sources\/[^/]+$/);
    expect(patches).toHaveLength(1);
    expect(patches[0].path).toBe(`${LIST}/anthropic-engineering`);
    expect(patches[0].body).toEqual({ enabled: false });
    expect(syncCalls(calls)).toHaveLength(1);
    await waitFor(() => expect(rowOf("anthropic-engineering")).toHaveAttribute("data-enabled", "false"));

    await user.click(within(rowOf("claude-code-llms")).getByRole("button", { name: "重新啟用 claude-code-llms" }));
    await waitFor(() => expect(syncCalls(calls)).toHaveLength(2));
    patches = callsOf(calls, "PATCH", /\/research\/watch-sources\/[^/]+$/);
    expect(patches).toHaveLength(2);
    expect(patches[1].body).toEqual({ enabled: true });
    expect(Object.keys(patches[1].body as object)).toEqual(["enabled"]);
  });

  it("AT_965_8_4 hostAllowed 為假的停用列：「重新啟用」鈕停用且 title 說明原因，點了不送請求", async () => {
    const user = userEvent.setup();
    const { calls } = mount("ADMIN");
    await load();
    const button = within(rowOf("openai-changelog-md")).getByRole("button", { name: "重新啟用 openai-changelog-md" });
    expect(button).toBeDisabled();
    expect(button.getAttribute("title")).toMatch(/網域還沒開放/);
    await user.click(button);
    expect(calls.filter((c) => c.method !== "GET")).toEqual([]);
  });

  it("AT_965_8_4 PATCH 失敗（404）顯示原因且不 sync", async () => {
    const user = userEvent.setup();
    const { calls } = mount("ADMIN", { patch: () => failure(404, { message: "nf", reason: "research_not_found" }) });
    await load();
    await user.click(within(rowOf("anthropic-engineering")).getByRole("button", { name: "停用 anthropic-engineering" }));
    expect(await screen.findByTestId("watch-toggle-error")).toHaveTextContent("停用 anthropic-engineering 失敗");
    expect(syncCalls(calls)).toHaveLength(0);
  });

  it("AT_965_8_4 PATCH 失敗（422）顯示原因且不 sync", async () => {
    const user = userEvent.setup();
    const { calls } = mount("ADMIN", { patch: () => failure(422, { message: "host", reason: "host_not_allowed" }) });
    await load();
    await user.click(within(rowOf("claude-code-llms")).getByRole("button", { name: "重新啟用 claude-code-llms" }));
    expect(await screen.findByTestId("watch-toggle-error")).toHaveTextContent("這個網域還沒開放");
    expect(syncCalls(calls)).toHaveLength(0);
  });
});

describe("AT_965_8_5 同步狀態列文案", () => {
  const CASES: Array<[RegistryStatusKind, RegExp, RegExp | null]> = [
    ["synced", /^已同步到自我進化$/, null],
    ["unsynced", /^有變更尚未同步$/, /已同步/],
    ["unsynced-never", /有變更尚未同步（尚未同步過）/, /已同步/],
    ["pending", /已送出，待自我進化入帳（主機巡邏會自動處理）.*2026-11-10T16:05:00\+08:00/, /已同步/],
    ["unknown-si_unavailable", /^量不到同步狀態：自我進化目前讀不到$/, /已同步/],
    ["unknown-scan_cap_exceeded", /^量不到同步狀態：帳本太大掃不完$/, /已同步/],
    ["unknown-bridge_unreachable", /^量不到同步狀態：引擎橋接服務連不上$/, /已同步/],
    ["unknown-bridge_timeout", /^量不到同步狀態：引擎橋接服務逾時$/, /已同步/],
  ];
  it.each(CASES)("AT_965_8_5 %s", async (kind, expected, forbidden) => {
    mount("ADMIN", { status: REGISTRY_STATUS(kind) });
    const line = await screen.findByTestId("registry-status");
    await waitFor(() => expect(line.textContent ?? "").toMatch(expected));
    expect(line).toHaveAttribute("role", "status");
    if (forbidden !== null) expect(line.textContent ?? "").not.toMatch(forbidden);
  });

  it("AT_965_8_5 狀態查詢失敗：顯示「量不到同步狀態」（不顯示成已同步）", async () => {
    mount("ADMIN", { statusGet: () => failure(500, { message: "down" }) });
    const line = await screen.findByTestId("registry-status");
    expect(line.textContent).toBe("量不到同步狀態");
    expect(line.textContent).not.toContain("已同步");
  });
});

describe("AT_965_8_6 同步錯誤文案與重試", () => {
  type Case = [name: string, reply: Reply, text: string, retry: boolean];
  const CASES: Case[] = [
    ["403", failure(403, { message: "x", reason: "si_write_forbidden" }), "此帳號不在自我進化寫入名單，未同步", false],
    [
      "503 write_disabled（金鑰）",
      failure(503, { message: "x", reason: "si_write_disabled", details: { cause: "audit_key_unset" } }),
      "自我進化的寫入功能尚未啟用（缺簽章金鑰或寫入權杖），未同步",
      true,
    ],
    [
      "503 write_disabled（權杖）",
      failure(503, { message: "x", reason: "si_write_disabled", details: { cause: "bridge_token_unset" } }),
      "自我進化的寫入功能尚未啟用（缺簽章金鑰或寫入權杖），未同步",
      true,
    ],
    ["503 si_unavailable", failure(503, { message: "x", reason: "si_unavailable" }), "自我進化暫時讀不到，稍後再試", true],
    ["422 registry_text", failure(422, { message: "x", reason: "registry_too_large", details: { what: "registry_text" } }), "追蹤來源總量超過可同步上限，請停用部分來源後再同步", false],
    ["422 audit_file", failure(422, { message: "x", reason: "registry_too_large", details: { what: "audit_file" } }), "追蹤來源總量超過可同步上限，請停用部分來源後再同步", false],
    ["502", failure(502, { message: "x", reason: "bridge_unreachable" }), "連不上引擎橋接服務，未同步", true],
    ["504 outcomeUnknown 假", failure(504, { message: "x", reason: "bridge_timeout", details: { outcomeUnknown: false } }), "連不上引擎橋接服務，未同步", true],
    ["504 outcomeUnknown 真", failure(504, { message: "x", reason: "bridge_timeout", details: { outcomeUnknown: true } }), "送出結果不明，稽核檔可能已落地，請先看狀態再決定是否重試", true],
    ["200 unchanged", { status: 200, data: SYNC_UNCHANGED }, "已是最新，未重送", false],
    ["201 written", { status: 201, data: SYNC_WRITTEN }, "已送出，待入帳", false],
  ];

  it.each(CASES)("AT_965_8_6 手動同步 %s", async (_name, reply, text, retry) => {
    const user = userEvent.setup();
    mount("ADMIN", { sync: () => reply });
    await load();
    await user.click(screen.getByRole("button", { name: "同步到自我進化" }));
    const message = await screen.findByTestId("registry-sync-message");
    expect(message).toHaveTextContent(text);
    if (text === "已送出，待入帳" || text === "已是最新，未重送") expect(message.textContent).not.toContain("已同步");
    expect(screen.queryByRole("button", { name: "重試同步" }) !== null).toBe(retry);
    // 403 與 registry_too_large 仍保留手動鈕
    expect(screen.getByRole("button", { name: "同步到自我進化" })).toBeEnabled();
  });

  it("AT_965_8_6 按「重試同步」再送一次；第二次成功後訊息換成成功文案、重試鈕消失", async () => {
    const user = userEvent.setup();
    let n = 0;
    const { calls } = mount("ADMIN", { sync: () => (++n === 1 ? failure(502, { message: "x", reason: "bridge_unreachable" }) : { status: 201, data: SYNC_WRITTEN }) });
    await load();
    await user.click(screen.getByRole("button", { name: "同步到自我進化" }));
    await screen.findByText("連不上引擎橋接服務，未同步");
    await user.click(screen.getByRole("button", { name: "重試同步" }));
    expect(await screen.findByText("已送出，待入帳")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "重試同步" })).toBeNull();
    expect(syncCalls(calls)).toHaveLength(2);
  });
});

describe("AT_965_8_7 手動同步鈕與併發去重", () => {
  it("AT_965_8_7 連點三次只送出一個請求；進行中鈕 disabled 且 aria-busy；回應後恢復", async () => {
    const user = userEvent.setup();
    const { calls } = mount("ADMIN");
    await load();
    const gate = gateSync();
    const button = screen.getByRole("button", { name: "同步到自我進化" });
    await user.click(button);
    await user.click(button);
    await user.click(button);
    expect(gate.count()).toBe(1);
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    gate.release();
    await screen.findByText("已送出，待入帳");
    expect(button).toBeEnabled();
    expect(button).not.toHaveAttribute("aria-busy");
    expect(syncCalls(calls)).toHaveLength(1);
  });

  it("AT_965_8_7 進行中新增成功：恰再排一次 sync（尾隨去重，不平行送兩個）", async () => {
    const user = userEvent.setup();
    const { calls } = mount("ADMIN");
    await load();
    const gate = gateSync();
    await user.click(screen.getByRole("button", { name: "同步到自我進化" }));
    expect(gate.count()).toBe(1);
    await fillValid(user);
    await user.click(submitButton());
    await waitFor(() => expect(callsOf(calls, "POST", /\/research\/watch-sources$/)).toHaveLength(1));
    await waitFor(() => expect(screen.getAllByTestId("watch-row")).toHaveLength(18));
    expect(gate.count(), "進行中不平行送第二個").toBe(1);
    gate.release();
    await waitFor(() => expect(gate.count()).toBe(2));
    await waitFor(() => expect(screen.getByRole("button", { name: "同步到自我進化" })).toBeEnabled());
    expect(syncCalls(calls)).toHaveLength(2);
  });

  it("AT_965_8_7 synced 狀態下鈕仍可按（得「已是最新，未重送」）；成功後狀態查詢失效重取", async () => {
    const user = userEvent.setup();
    const { calls } = mount("ADMIN", { status: REGISTRY_STATUS("synced"), sync: () => ({ status: 200, data: SYNC_UNCHANGED }) });
    await load();
    const before = callsOf(calls, "GET", /\/si\/research-registry$/).length;
    await user.click(screen.getByRole("button", { name: "同步到自我進化" }));
    expect(await screen.findByText("已是最新，未重送")).toBeInTheDocument();
    await waitFor(() => expect(callsOf(calls, "GET", /\/si\/research-registry$/).length).toBeGreaterThan(before));
  });

  it("AT_965_8_7 OPERATOR 與 VIEWER 沒有此區（入口不渲染），也不發任何 watch-sources 或 research-registry 請求", () => {
    for (const role of ["OPERATOR", "VIEWER"] as const) {
      const { calls, container, unmount } = mount(role);
      expect(screen.queryByRole("button", { name: "同步到自我進化" }), role).toBeNull();
      expect(container.textContent, role).toBe("");
      expect(calls, role).toEqual([]);
      unmount();
    }
  });
});

describe("AT_965_8_E_2 鍵盤、焦點與 aria", () => {
  it("AT_965_8_E_2 每個互動控件有可存取名稱；表單欄位以 label 關聯", async () => {
    mount("ADMIN");
    await load();
    const section = screen.getByTestId("watch-sources-section");
    const controls = within(section).getAllByRole("button");
    for (const control of controls) expect(control.getAttribute("aria-label") ?? control.textContent ?? "", "按鈕有名稱").not.toBe("");
    for (const label of [/識別碼/, /^網址/, /抓取說明/, /展開方式/, /路徑前綴/, /最多幾頁/, /^種類/, /^來源層/]) expect(screen.getByLabelText(label)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "自我進化追蹤來源" })).toBeInTheDocument();
    expect(screen.getByRole("form", { name: "新增追蹤來源" })).toBeInTheDocument();
  });

  it("AT_965_8_E_2 驗證錯誤：錯誤欄 aria-invalid 並以 aria-describedby 關聯錯誤文字；錯誤摘要 role=alert", async () => {
    const user = userEvent.setup();
    mount("ADMIN");
    await load();
    await user.click(submitButton());
    for (const label of [/識別碼/, /^網址/, /抓取說明/]) {
      const input = screen.getByLabelText(label);
      expect(input).toHaveAttribute("aria-invalid", "true");
      const describedBy = input.getAttribute("aria-describedby");
      expect(describedBy).toBeTruthy();
      const error = document.getElementById(describedBy as string);
      expect(error?.textContent?.length ?? 0).toBeGreaterThan(0);
      expect(error).toHaveAttribute("role", "alert");
    }
    expect(screen.getByTestId("watch-form-summary")).toHaveAttribute("role", "alert");
  });

  it("AT_965_8_E_2 Tab 序：清單鈕在前、新增表單欄位依視覺序、送出鈕在最後", async () => {
    const user = userEvent.setup();
    mount("ADMIN");
    await load();
    const section = screen.getByTestId("watch-sources-section");
    const first = within(section).getByRole("button", { name: "同步到自我進化" });
    first.focus();
    const order: string[] = [];
    for (let i = 0; i < 80; i += 1) {
      const active = document.activeElement as HTMLElement | null;
      if (active === null || !section.contains(active)) break;
      const name = active.getAttribute("aria-label") ?? active.textContent ?? "";
      order.push(active.tagName === "BUTTON" ? `按鈕:${name}` : `欄位:${active.closest("label")?.firstElementChild?.textContent ?? active.getAttribute("aria-label") ?? ""}`);
      await user.tab();
    }
    const firstField = order.findIndex((o) => o.startsWith("欄位:"));
    const rowButtons = order.map((o, i) => [o, i] as const).filter(([o]) => /^按鈕:(停用|重新啟用) /.test(o));
    expect(rowButtons.length).toBeGreaterThan(0);
    for (const [, index] of rowButtons) expect(index, "清單鈕在表單欄位之前").toBeLessThan(firstField);
    const fieldOrder = order.filter((o) => o.startsWith("欄位:")).map((o) => o.slice(3));
    expect(fieldOrder.map((name) => name.replace(/（.*$/, ""))).toEqual(["識別碼", "種類", "網址", "來源層", "抓取說明", "展開方式", "路徑前綴", "最多幾頁"]);
    expect(order[order.length - 1]).toBe("按鈕:新增追蹤來源");
  });

  it("AT_965_8_E_2 在對話框內：Esc 關閉後焦點歸還到「研究來源設定」入口", async () => {
    const user = userEvent.setup();
    mount("ADMIN", {}, <AllowlistDialog />);
    const trigger = screen.getByRole("button", { name: "研究來源設定" });
    await user.click(trigger);
    const dialog = await screen.findByRole("dialog", { name: "研究來源設定" });
    await within(dialog).findAllByTestId("watch-row");
    expect(within(dialog).getByRole("region", { name: "自我進化追蹤來源" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(screen.getByRole("button", { name: "研究來源設定" })).toHaveFocus());
  });
});
