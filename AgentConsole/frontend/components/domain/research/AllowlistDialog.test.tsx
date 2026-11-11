import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ResearchAllowlistEntry, ResearchAllowlistRequest, ResearchCapabilities, Role } from "@/lib/api/types";
import { allowlistFormErrors, isRedditHost, normalizeAllowlistHost, toAllowlistRequest, type AllowlistForm } from "@/lib/domain/research";
import { T0 } from "@/tests/fixtures/research/ids";
import { CAPABILITIES_LOCAL } from "@/tests/fixtures/research/misc";
import { callsOf, failure, renderResearch, stubResearchApi, writeCalls, type ApiCall, type Reply } from "@/tests/helpers/research";
import { AllowlistDialog } from "./AllowlistDialog";

/**
 * 研究來源設定對話框（TCS-ResearchToPRD-P0-20261102 AT-960-19-8；AC-R2P-04-7）：僅 ADMIN 看得到入口（其他角色不渲染）、清單區分來源 ENV 與 ADMIN、
 * 新增產業網域、Reddit 未勾條款時送出鈕停用並提示、已勾送出本文含 tosAcknowledged: true、停用呼叫 PATCH 且本文只有 enabled、ENV 條目沒有停用鈕。
 * 判定指令：npx vitest run components/domain/research/AllowlistDialog.test.tsx -t AT_960_19_8
 */
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/research",
  useSearchParams: () => new URLSearchParams(),
}));

const envEntry = (host: string, minIntervalSeconds: number): ResearchAllowlistEntry => ({
  id: null,
  listKind: "FETCH",
  host,
  layer: null,
  purpose: "",
  tosNote: "",
  minIntervalSeconds,
  enabled: true,
  tosAcknowledged: false,
  source: "ENV",
  addedBy: null,
  addedAt: null,
});

/** 預設部署：四組基底主機（ENV，沒有資料列＝id 與 layer 為 null）加一個 ADMIN 新增的產業網域。 */
const BASE_HOSTS = ["export.arxiv.org", "api.semanticscholar.org", "api.github.com", "api.stackexchange.com"];
const ADMIN_ENTRY: ResearchAllowlistEntry = {
  id: "al-9",
  listKind: "WEB",
  host: "docs.example.com",
  layer: "INDUSTRY",
  purpose: "官方文件",
  tosNote: "",
  minIntervalSeconds: 5,
  enabled: true,
  tosAcknowledged: false,
  source: "ADMIN",
  addedBy: "admin",
  addedAt: T0,
};
const ENTRIES = (): ResearchAllowlistEntry[] => [...BASE_HOSTS.map((host, i) => envEntry(host, [3, 3, 1, 3][i])), { ...ADMIN_ENTRY }];

const LIST_PATH = "/api/v1/research/allowlist";
const CAPABILITIES_PATH = "/api/v1/research/capabilities";

/**
 * 假後端：GET 回活的清單；POST 依本文建立 ADMIN 條目（或由 `post` 覆寫）；PATCH 只改 enabled（或由 `patch` 覆寫）；
 * 能力探針預設回夾具，`capabilities` 可依「當下的清單」算出回應（有效主機隨新增與停用變動）或回 `"error"`＝503。
 */
function mountDialog(
  role: Role,
  hooks: {
    post?: (call: ApiCall) => Reply;
    patch?: (call: ApiCall) => Reply;
    list?: (call: ApiCall) => Reply;
    capabilities?: (allowlist: ResearchAllowlistEntry[]) => ResearchCapabilities | "error";
  } = {},
) {
  let nextId = 100;
  const api = stubResearchApi({
    allowlist: ENTRIES(),
    overrides: (call) => {
      if (call.path === CAPABILITIES_PATH && call.method === "GET" && hooks.capabilities !== undefined) {
        const caps = hooks.capabilities(api.options.allowlist);
        return caps === "error" ? failure(503, { message: "Bridge 不可用", reason: "bridge_unreachable" }) : { data: caps };
      }
      if (call.path === LIST_PATH && call.method === "GET" && hooks.list !== undefined) return hooks.list(call);
      if (call.method === "POST" && call.path === LIST_PATH) {
        const custom = hooks.post?.(call);
        if (custom !== undefined) return custom;
        const body = call.body as ResearchAllowlistRequest;
        const created: ResearchAllowlistEntry = { ...body, id: `al-${nextId++}`, enabled: true, source: "ADMIN", addedBy: "admin", addedAt: T0 };
        api.options.allowlist = [...api.options.allowlist, created];
        return { status: 201, data: created };
      }
      if (call.method === "PATCH" && call.path.startsWith(`${LIST_PATH}/`)) {
        const custom = hooks.patch?.(call);
        if (custom !== undefined) return custom;
        const id = decodeURIComponent(call.path.slice(LIST_PATH.length + 1));
        const patched = api.options.allowlist.map((entry) => (entry.id === id ? { ...entry, enabled: (call.body as { enabled: boolean }).enabled } : entry));
        api.options.allowlist = patched;
        return { data: patched.find((entry) => entry.id === id) };
      }
      return undefined;
    },
  });
  const ui = renderResearch(<AllowlistDialog />, role);
  return { ...ui, ...api };
}

const openButton = () => screen.queryByRole("button", { name: "研究來源設定" });

async function openDialog(user: ReturnType<typeof userEvent.setup>) {
  const trigger = openButton();
  if (trigger === null) throw new Error("沒有「研究來源設定」入口");
  await user.click(trigger);
  return await screen.findByRole("dialog", { name: "研究來源設定" });
}

const rowOf = (host: string): HTMLElement => {
  const row = screen.getAllByTestId("allowlist-row").find((r) => r.getAttribute("data-host") === host);
  if (row === undefined) throw new Error(`清單沒有 ${host}`);
  return row;
};
const field = (label: RegExp | string) => screen.getByLabelText(label);

describe("AT_960_19_8 研究來源設定：僅 ADMIN 看得到入口", () => {
  it("AT_960_19_8 OPERATOR 與 VIEWER 整個元件不渲染（不是停用），也不發任何請求；ADMIN 看得到入口", () => {
    for (const role of ["OPERATOR", "VIEWER"] as const) {
      const { calls, container, unmount } = mountDialog(role);
      expect(openButton(), role).toBeNull();
      expect(container.textContent, `${role} 不渲染任何內容`).toBe("");
      expect(calls, `${role} 沒有請求`).toEqual([]);
      unmount();
    }
    mountDialog("ADMIN");
    expect(openButton()).toBeEnabled();
  });
});

describe("AT_960_19_8 清單：區分來源 ENV 與 ADMIN；ENV 條目沒有停用鈕", () => {
  it("AT_960_19_8 開對話框才讀清單（開啟前沒有請求）；四組 ENV 基底（沒有資料列：層顯示破折號）與一個 ADMIN 條目；ENV 沒有任何動作鈕，ADMIN 條目有「停用」", async () => {
    const user = userEvent.setup();
    const { calls } = mountDialog("ADMIN");
    expect(callsOf(calls, "GET", /\/allowlist$/), "對話框開啟前不讀清單").toHaveLength(0);
    await openDialog(user);
    expect(await screen.findAllByTestId("allowlist-row")).toHaveLength(5);
    const sources = screen.getAllByTestId("allowlist-row").map((row) => `${row.getAttribute("data-host")}｜${row.getAttribute("data-source")}`);
    // 預設主機自然序升冪（TCS-ConsoleUxSortHelp D-UX-5；原為 API 回應序：基底在前、ADMIN 在後）
    expect(sources).toEqual([...BASE_HOSTS.map((host) => `${host}｜ENV`), "docs.example.com｜ADMIN"].sort(new Intl.Collator("zh-Hant", { numeric: true }).compare));
    for (const host of BASE_HOSTS) {
      const row = rowOf(host);
      expect(within(row).getByText("部署設定")).toBeInTheDocument(); // 精確比對：不得退回帶 ENV 英文縮寫的舊字面
      expect(within(row).queryByRole("button"), `${host} 沒有停用鈕`).toBeNull();
      expect(within(row).getByText("不可變更")).toBeInTheDocument();
      expect(within(row).getAllByText("—"), "ENV 條目沒有層與用途：兩格都是破折號").toHaveLength(2);
    }
    const admin = rowOf("docs.example.com");
    expect(within(admin).getByText("管理員新增")).toBeInTheDocument();
    // 白話文案（DEV-COPY S2／S3）：內部名詞「Bridge」不外露；「Web 層」有一句白話解釋
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("實際抓取間隔取系統內建下限與這裡填的值中較大者；間隔建立後不能改，要調整請停用後重建。")).toBeInTheDocument();
    expect(
      within(dialog).getByText(
        "有效清單＝部署環境變數設定的基底加上這裡啟用中的條目；每個階段開始執行時會記下當時的快照。「Web 層」是研究用網頁搜尋官方文獻與業界資料時可以用的產業網域清單；要先在這裡加入至少一個產業網域，研究才能勾選「官方文獻與業界」。",
      ),
    ).toBeInTheDocument();
    expect(within(admin).getByText("產業層")).toBeInTheDocument();
    expect(within(admin).getByRole("button", { name: "停用 docs.example.com" })).toBeEnabled();
    expect(within(rowOf("api.github.com")).getByText("1 秒")).toBeInTheDocument();
    expect(writeCalls(calls)).toEqual([]);
  });

  it("AT_960_19_8 清單載入失敗：顯示原因與「重試」（不當成空清單）；重試後清單出現", async () => {
    const user = userEvent.setup();
    let broken = true;
    mountDialog("ADMIN", { list: () => (broken ? failure(503, { message: "Bridge 不可用", reason: "bridge_unreachable" }) : undefined) });
    await openDialog(user);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("無法載入研究來源清單");
    expect(alert).toHaveTextContent("Bridge 不可用");
    expect(screen.queryAllByTestId("allowlist-row")).toHaveLength(0);
    broken = false;
    await user.click(within(alert).getByRole("button", { name: "重試" }));
    expect(await screen.findAllByTestId("allowlist-row")).toHaveLength(5);
  });
});

describe("INT-08 前端側：有效的抓取主機與研究環境事實（能力探針的 fetchHosts、sddRoot、scaffoldRoot、repoWritable）", () => {
  /** 有效主機＝部署基底加啟用中的 ADMIN 條目（停用即消失；同 Bridge 的 `fetch_hosts`）。 */
  const effective = (allowlist: ResearchAllowlistEntry[]): ResearchCapabilities => ({
    ...CAPABILITIES_LOCAL,
    fetchHosts: [...BASE_HOSTS, ...allowlist.filter((entry) => entry.source === "ADMIN" && entry.enabled).map((entry) => entry.host)],
  });
  const hostsShown = (): string[] =>
    within(screen.getByTestId("effective-hosts"))
      .getAllByRole("listitem")
      .map((li) => li.textContent ?? "");

  it("INT-08 開啟後列出有效的抓取主機與三個環境事實；只讀（沒有任何寫入請求）", async () => {
    const user = userEvent.setup();
    const { calls } = mountDialog("ADMIN");
    await openDialog(user);
    const section = await screen.findByTestId("effective-environment");
    expect(within(section).getByRole("heading", { name: "目前有效的抓取主機" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("effective-hosts")).toBeInTheDocument());
    expect(hostsShown()).toEqual(CAPABILITIES_LOCAL.fetchHosts);
    expect(screen.getByRole("list", { name: "有效的抓取主機" })).toBe(screen.getByTestId("effective-hosts"));
    expect(screen.getByTestId("fact-sdd-root")).toHaveTextContent("<AISDLC_SDD 框架樹>");
    expect(screen.getByTestId("fact-scaffold-root"), "scaffoldRoot 為 null").toHaveTextContent("未設定");
    expect(screen.getByTestId("fact-repo-writable")).toHaveTextContent("是");
    expect(callsOf(calls, "GET", /\/capabilities$/).length, "開對話框才讀能力探針").toBeGreaterThanOrEqual(1);
    expect(writeCalls(calls)).toEqual([]);
  });

  it("INT-08 新增 ADMIN 條目後有效主機跟著多一個、停用後少一個（新增與停用成功都會重抓能力探針）；已停用的條目仍在上面的清單裡", async () => {
    const user = userEvent.setup();
    mountDialog("ADMIN", { capabilities: effective });
    await openDialog(user);
    await waitFor(() => expect(hostsShown()).toEqual([...BASE_HOSTS, "docs.example.com"]));
    await user.type(field(/^主機名稱/), "blog.example.com");
    await user.click(screen.getByRole("button", { name: "新增" }));
    await waitFor(() => expect(hostsShown()).toEqual([...BASE_HOSTS, "docs.example.com", "blog.example.com"]));
    await user.click(within(rowOf("docs.example.com")).getByRole("button", { name: "停用 docs.example.com" }));
    await waitFor(() => expect(hostsShown()).toEqual([...BASE_HOSTS, "blog.example.com"]));
    expect(rowOf("docs.example.com"), "停用的條目仍在清單，只是不在有效主機裡").toHaveAttribute("data-enabled", "false");
  });

  it("INT-08 環境事實的各種值：框架樹解析不到＝「未解析到」、腳手架根有值照字顯示、repo 不可寫＝「否」；沒有任何有效主機時說明而不是空白", async () => {
    const user = userEvent.setup();
    mountDialog("ADMIN", { capabilities: () => ({ ...CAPABILITIES_LOCAL, sddRoot: null, scaffoldRoot: "/srv/scaffold", repoWritable: false, fetchHosts: [] }) });
    await openDialog(user);
    expect(await screen.findByTestId("effective-hosts-empty")).toHaveTextContent("目前沒有任何有效的抓取主機");
    expect(screen.queryByTestId("effective-hosts")).toBeNull();
    expect(screen.getByTestId("fact-sdd-root")).toHaveTextContent("未解析到");
    expect(screen.getByTestId("fact-scaffold-root")).toHaveTextContent("/srv/scaffold");
    expect(screen.getByTestId("fact-repo-writable")).toHaveTextContent("否");
  });

  it("INT-08 能力探針失敗（Bridge 連不上）：只有這一區顯示原因（不是 alert），上面的清單與新增表單照常可用", async () => {
    const user = userEvent.setup();
    mountDialog("ADMIN", { capabilities: () => "error" });
    await openDialog(user);
    expect(await screen.findByTestId("effective-environment-error")).toHaveTextContent("無法取得研究環境狀態");
    expect(screen.queryByTestId("effective-hosts")).toBeNull();
    expect(await screen.findAllByTestId("allowlist-row")).toHaveLength(5);
    expect(screen.getByRole("button", { name: "新增" })).toBeEnabled();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("AT_960_19_8 新增：產業網域與逐欄驗證", () => {
  it("AT_960_19_8 新增產業網域：主機名稱去空白並轉小寫；POST 本文為 camelCase 且欄位恰為契約欄位；成功後清單重抓、表單清空、顯示提示", async () => {
    const user = userEvent.setup();
    const { calls } = mountDialog("ADMIN");
    await openDialog(user);
    await screen.findAllByTestId("allowlist-row");
    await user.type(field(/^主機名稱/), "  Blog.Example.COM ");
    await user.type(field(/^用途/), "工程部落格");
    await user.click(screen.getByRole("button", { name: "新增" }));
    await waitFor(() => expect(callsOf(calls, "POST", /\/allowlist$/)).toHaveLength(1));
    const posted = callsOf(calls, "POST", /\/allowlist$/)[0];
    expect(posted.body).toEqual({ listKind: "WEB", host: "blog.example.com", layer: "INDUSTRY", purpose: "工程部落格", tosNote: "", minIntervalSeconds: 5, tosAcknowledged: false });
    expect(await screen.findByText("已新增 blog.example.com")).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByTestId("allowlist-row")).toHaveLength(6));
    expect(rowOf("blog.example.com")).toHaveAttribute("data-source", "ADMIN");
    expect(field(/^主機名稱/)).toHaveValue("");
    expect(callsOf(calls, "GET", /\/allowlist$/).length, "新增成功後清單重抓").toBeGreaterThanOrEqual(2);
    expect(callsOf(calls, "GET", /\/capabilities$/).length, "能力探針（Web 層是否啟用、有效主機）也重抓：開啟時一次、新增成功後再一次").toBeGreaterThanOrEqual(2);
  });

  it("AT_960_19_8 驗證：主機空白、帶 https:// 或路徑、含大寫以外的非法字元、間隔不是 1～3600 的整數、用途超過 200 字各在欄位旁顯示錯誤且不送出；改對後送出", async () => {
    const user = userEvent.setup();
    const { calls } = mountDialog("ADMIN");
    await openDialog(user);
    await screen.findAllByTestId("allowlist-row");
    const submit = () => user.click(screen.getByRole("button", { name: "新增" }));

    await submit();
    expect(await screen.findByText("請輸入主機名稱")).toBeInTheDocument();
    await user.type(field(/^主機名稱/), "https://blog.example.com/path");
    await submit();
    expect(await screen.findByText(/只輸入主機名稱，不要含 https:\/\//)).toBeInTheDocument();
    await user.clear(field(/^主機名稱/));
    await user.type(field(/^主機名稱/), "bad_host!.example.com");
    await submit();
    expect(await screen.findByText(/主機名稱只能是英數、點與連字號/)).toBeInTheDocument();
    await user.clear(field(/^主機名稱/));
    await user.type(field(/^主機名稱/), "blog.example.com");
    for (const bad of ["0", "3601", "1.5", ""]) {
      await user.clear(field("最小間隔（秒）"));
      if (bad !== "") await user.type(field("最小間隔（秒）"), bad);
      await submit();
      expect(await screen.findByText(/最小間隔須為 1 至 3600 的整數/), `間隔 ${JSON.stringify(bad)}`).toBeInTheDocument();
    }
    await user.clear(field("最小間隔（秒）"));
    await user.type(field("最小間隔（秒）"), "10");
    await user.click(field(/^用途/));
    await user.paste("字".repeat(201));
    await submit();
    expect(await screen.findByText("用途最多 200 個字")).toBeInTheDocument();
    expect(callsOf(calls, "POST", /\/allowlist$/), "任何一次驗證失敗都不送出").toHaveLength(0);

    await user.clear(field(/^用途/));
    await submit();
    await waitFor(() => expect(callsOf(calls, "POST", /\/allowlist$/)).toHaveLength(1));
    expect(callsOf(calls, "POST", /\/allowlist$/)[0].body).toMatchObject({ host: "blog.example.com", minIntervalSeconds: 10, purpose: "" });
  });

  it("AT_960_19_8 後端拒絕（重複條目 409、Bridge 尚未實作 502）：原因顯示在對話框內、不關閉、不假裝成功、表單內容保留", async () => {
    const user = userEvent.setup();
    let reply: Reply = failure(409, { message: "這個網域已在清單內", reason: "stage_conflict" });
    mountDialog("ADMIN", { post: () => reply });
    await openDialog(user);
    await screen.findAllByTestId("allowlist-row");
    await user.type(field(/^主機名稱/), "dup.example.com");
    await user.click(screen.getByRole("button", { name: "新增" }));
    expect(await screen.findByTestId("allowlist-error")).toHaveTextContent("目前狀態不允許這個動作");
    expect(field(/^主機名稱/)).toHaveValue("dup.example.com");
    reply = failure(502, { message: "Bridge 端點尚未實作", reason: "not_implemented", details: { endpoint: "POST /research/allowlist" } });
    await user.click(screen.getByRole("button", { name: "新增" }));
    await waitFor(() => expect(screen.getByTestId("allowlist-error")).toHaveTextContent("這個功能尚未開放"));
    expect(screen.getByRole("dialog", { name: "研究來源設定" })).toBeInTheDocument();
    expect(screen.queryByText("已新增 dup.example.com")).toBeNull();
    expect(screen.getAllByTestId("allowlist-row")).toHaveLength(5);
  });
});

describe("AT_960_19_8 Reddit 條款確認", () => {
  it("AT_960_19_8 填 reddit.com：出現條款勾選與提示、「新增」停用；Enter 也送不出去；勾選後啟用，送出本文含 tosAcknowledged: true", async () => {
    const user = userEvent.setup();
    const { calls } = mountDialog("ADMIN");
    await openDialog(user);
    await screen.findAllByTestId("allowlist-row");
    expect(screen.queryByRole("checkbox", { name: /已自建 Reddit 應用並接受其條款/ }), "不是 Reddit 網域時沒有條款勾選").toBeNull();
    await user.type(field(/^主機名稱/), "reddit.com");
    const checkbox = await screen.findByRole("checkbox", { name: /已自建 Reddit 應用並接受其條款/ });
    expect(checkbox).not.toBeChecked();
    expect(screen.getByTestId("reddit-hint")).toHaveTextContent("須先勾選");
    expect(screen.getByRole("button", { name: "新增" })).toBeDisabled();
    await user.type(field(/^用途/), "社群討論{Enter}");
    expect(callsOf(calls, "POST", /\/allowlist$/), "未勾條款時 Enter 也不會送出").toHaveLength(0);

    await user.click(checkbox);
    expect(checkbox).toBeChecked();
    expect(screen.queryByTestId("reddit-hint")).toBeNull();
    expect(screen.getByRole("button", { name: "新增" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "新增" }));
    await waitFor(() => expect(callsOf(calls, "POST", /\/allowlist$/)).toHaveLength(1));
    expect(callsOf(calls, "POST", /\/allowlist$/)[0].body).toEqual({
      listKind: "WEB",
      host: "reddit.com",
      layer: "INDUSTRY",
      purpose: "社群討論",
      tosNote: "",
      minIntervalSeconds: 5,
      tosAcknowledged: true,
    });
  });

  it("AT_960_19_8 後端仍回 422 terms_ack_required（例如條款確認被竄改）：顯示白話原因，條目不會出現在清單", async () => {
    const user = userEvent.setup();
    mountDialog("ADMIN", { post: () => failure(422, { message: "需要確認條款", reason: "terms_ack_required" }) });
    await openDialog(user);
    await screen.findAllByTestId("allowlist-row");
    await user.type(field(/^主機名稱/), "old.reddit.com");
    await user.click(await screen.findByRole("checkbox", { name: /已自建 Reddit 應用並接受其條款/ }));
    await user.click(screen.getByRole("button", { name: "新增" }));
    expect(await screen.findByTestId("allowlist-error")).toHaveTextContent("這個來源需要先勾選已接受服務條款");
    expect(screen.getAllByTestId("allowlist-row")).toHaveLength(5);
  });

  it("AT_960_19_8 Reddit 網域判斷（純函式）：reddit.com、子網域、redd.it 是；長得像的別人網域不是；tosAcknowledged 只有 Reddit 網域才可能為真", () => {
    for (const host of ["reddit.com", "www.reddit.com", "OLD.Reddit.com", " redd.it ", "api.reddit.com"]) expect(isRedditHost(host), host).toBe(true);
    for (const host of ["notreddit.com", "reddit.com.evil.test", "reddit.co", "myredd.it", "example.com", ""]) expect(isRedditHost(host), host).toBe(false);
    const form: AllowlistForm = { listKind: "WEB", host: "Example.com", layer: "INDUSTRY", purpose: "", tosNote: "", minIntervalSeconds: "5", tosAcknowledged: true };
    expect(toAllowlistRequest(form).tosAcknowledged, "勾了但不是 Reddit 網域：不送 true").toBe(false);
    expect(toAllowlistRequest({ ...form, host: "reddit.com" }).tosAcknowledged).toBe(true);
    expect(normalizeAllowlistHost("  Blog.EXAMPLE.com ")).toBe("blog.example.com");
    expect(allowlistFormErrors({ ...form, host: "reddit.com", tosAcknowledged: false }).tosAcknowledged).toMatch(/Reddit/);
    expect(allowlistFormErrors({ ...form, host: "reddit.com" })).toEqual({});
  });
});

describe("AT_960_19_8 停用與啟用：PATCH 本文只有 enabled", () => {
  it("AT_960_19_8 停用 ADMIN 條目：呼叫 PATCH …/allowlist/<id>，本文恰為 {enabled:false}；清單顯示已停用並提供「啟用」；再啟用本文為 {enabled:true}；ENV 條目全程沒有動作", async () => {
    const user = userEvent.setup();
    const { calls } = mountDialog("ADMIN");
    await openDialog(user);
    await screen.findAllByTestId("allowlist-row");
    await user.click(within(rowOf("docs.example.com")).getByRole("button", { name: "停用 docs.example.com" }));
    await waitFor(() => expect(callsOf(calls, "PATCH", /\/allowlist\/al-9$/)).toHaveLength(1));
    expect(callsOf(calls, "PATCH", /\/allowlist\/al-9$/)[0].body).toEqual({ enabled: false });
    expect(await screen.findByText("已停用 docs.example.com")).toBeInTheDocument();
    await waitFor(() => expect(rowOf("docs.example.com")).toHaveAttribute("data-enabled", "false"));
    expect(within(rowOf("docs.example.com")).getByText("已停用")).toBeInTheDocument();
    await user.click(within(rowOf("docs.example.com")).getByRole("button", { name: "啟用 docs.example.com" }));
    await waitFor(() => expect(callsOf(calls, "PATCH", /\/allowlist\/al-9$/)).toHaveLength(2));
    expect(callsOf(calls, "PATCH", /\/allowlist\/al-9$/)[1].body).toEqual({ enabled: true });
    await waitFor(() => expect(rowOf("docs.example.com")).toHaveAttribute("data-enabled", "true"));
    expect(callsOf(calls, "PATCH", /\/allowlist\//), "只對 ADMIN 條目送過 PATCH").toHaveLength(2);
    expect(
      writeCalls(calls).every((c) => c.method === "PATCH"),
      "全程只有 PATCH 寫入",
    ).toBe(true);
  });

  it("AT_960_19_8 停用失敗（後端 502 尚未實作）：以提示顯示原因、條目維持啟用、不假裝成功", async () => {
    const user = userEvent.setup();
    mountDialog("ADMIN", { patch: () => failure(502, { message: "Bridge 端點尚未實作", reason: "not_implemented" }) });
    await openDialog(user);
    await screen.findAllByTestId("allowlist-row");
    await user.click(within(rowOf("docs.example.com")).getByRole("button", { name: "停用 docs.example.com" }));
    expect(await screen.findByText(/停用失敗：這個功能尚未開放/)).toBeInTheDocument();
    expect(rowOf("docs.example.com")).toHaveAttribute("data-enabled", "true");
    expect(screen.queryByText("已停用 docs.example.com")).toBeNull();
  });

  it("AT_960_19_8 對話框可用鍵盤關閉（Esc），焦點歸還到「研究來源設定」入口", async () => {
    const user = userEvent.setup();
    mountDialog("ADMIN");
    await openDialog(user);
    await screen.findAllByTestId("allowlist-row");
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(openButton()).toHaveFocus();
  });
});

// TCS-ConsoleUxSortHelp-20261108 AT-963-3-10（T8 允許清單；D-UX-5：主機是識別欄）
describe("AT_965_8_8 角色、共用說明與追蹤來源區（TCS-ResearchRegistry-20261110；既有 AT_960_19_8 案例不退步）", () => {
  it("AT_965_8_8 OPERATOR 與 VIEWER 不渲染入口，也不發任何 watch-sources 或 research-registry 請求（含開啟前後）", () => {
    for (const role of ["OPERATOR", "VIEWER"] as const) {
      const { calls, unmount } = mountDialog(role);
      expect(openButton(), role).toBeNull();
      expect(
        calls.filter((c) => /\/watch-sources|\/research-registry/.test(c.path)),
        role,
      ).toEqual([]);
      unmount();
    }
  });

  it("AT_965_8_8 ADMIN 開啟後：網域清單區有說明句「研發工作流與自我進化共用這份網域清單」；追蹤來源區位於網域區之後且有獨立標題與 aria-labelledby", async () => {
    const user = userEvent.setup();
    mountDialog("ADMIN");
    const dialog = await openDialog(user);
    const note = await within(dialog).findByTestId("allowlist-shared-note");
    expect(note).toHaveTextContent("研發工作流與自我進化共用這份網域清單");
    const section = within(dialog).getByTestId("watch-sources-section");
    const heading = within(section).getByRole("heading", { name: "自我進化追蹤來源" });
    expect(section.getAttribute("aria-labelledby")).toBe(heading.id);
    // 文件順序：網域清單表、有效主機區、新增網域表單，最後才是追蹤來源區
    const domainTable = await within(dialog).findByTestId("allowlist-table");
    const addForm = within(dialog).getByRole("form", { name: "新增研究來源" });
    expect(domainTable.compareDocumentPosition(section) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(addForm.compareDocumentPosition(section) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(note.compareDocumentPosition(section) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("AT_965_8_8 ADMIN 開啟時會讀追蹤來源清單與同步狀態（各一次以上），開啟前不讀", async () => {
    const user = userEvent.setup();
    const { calls } = mountDialog("ADMIN");
    expect(calls.filter((c) => /\/watch-sources|\/research-registry/.test(c.path))).toEqual([]);
    await openDialog(user);
    await waitFor(() => expect(callsOf(calls, "GET", /\/research\/watch-sources$/).length).toBeGreaterThanOrEqual(1));
    await waitFor(() => expect(callsOf(calls, "GET", /\/si\/research-registry$/).length).toBeGreaterThanOrEqual(1));
  });
});

describe("AT_963_3_10 允許清單：預設主機自然序升冪與表頭排序", () => {
  const hosts = () => screen.getAllByTestId("allowlist-row").map((row) => row.getAttribute("data-host"));

  it("AT_963_3_10 預設主機升冪（主機欄 ascending）；最小間隔依數字排、同值依主機升冪；動作欄無按鈕；八欄字樣依序不變", async () => {
    const user = userEvent.setup();
    mountDialog("ADMIN");
    const dialog = await openDialog(user);
    await screen.findAllByTestId("allowlist-row");
    const table = within(dialog).getByTestId("allowlist-table");
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((th) => th.textContent),
    ).toEqual(["主機", "清單", "層", "用途", "來源", "最小間隔", "狀態", "動作"]);
    expect(hosts()).toEqual(["api.github.com", "api.semanticscholar.org", "api.stackexchange.com", "docs.example.com", "export.arxiv.org"]);
    expect(within(table).getByRole("columnheader", { name: "主機" })).toHaveAttribute("aria-sort", "ascending");
    const action = within(table).getByRole("columnheader", { name: "動作" });
    expect(action.querySelector("button")).toBeNull();
    expect(action.hasAttribute("aria-sort")).toBe(false);

    await user.click(within(within(table).getByRole("columnheader", { name: "最小間隔" })).getByRole("button"));
    expect(hosts()).toEqual(["api.github.com", "api.semanticscholar.org", "api.stackexchange.com", "export.arxiv.org", "docs.example.com"]);
    await user.click(within(within(table).getByRole("columnheader", { name: "最小間隔" })).getByRole("button"));
    expect(hosts()).toEqual(["docs.example.com", "api.semanticscholar.org", "api.stackexchange.com", "export.arxiv.org", "api.github.com"]);
    // 第一次點預設欄（主機）即反向
    await user.click(within(within(table).getByRole("columnheader", { name: "主機" })).getByRole("button"));
    expect(hosts()).toEqual(["api.github.com", "api.semanticscholar.org", "api.stackexchange.com", "docs.example.com", "export.arxiv.org"]);
    await user.click(within(within(table).getByRole("columnheader", { name: "主機" })).getByRole("button"));
    expect(hosts()).toEqual(["export.arxiv.org", "docs.example.com", "api.stackexchange.com", "api.semanticscholar.org", "api.github.com"]);

    // DEV-COPY：「來源」欄的排序鍵（SORT_COLUMNS.source.get）要與列內顯示字一致——升冪時「部署設定」（ENV）列全在「管理員新增」（ADMIN）列之前，
    // 再點一次相反。排序鍵不直接顯示，若它退回舊字面（「ENV …」「ADMIN …」，A 排在 E 前）順序會翻轉，沒有這條斷言就沒人發現。
    const sourcesOf = () => screen.getAllByTestId("allowlist-row").map((row) => row.getAttribute("data-source"));
    await user.click(within(within(table).getByRole("columnheader", { name: "來源" })).getByRole("button"));
    expect(sourcesOf()).toEqual(["ENV", "ENV", "ENV", "ENV", "ADMIN"]);
    await user.click(within(within(table).getByRole("columnheader", { name: "來源" })).getByRole("button"));
    expect(sourcesOf()).toEqual(["ADMIN", "ENV", "ENV", "ENV", "ENV"]);
  });
});
