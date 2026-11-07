/**
 * PR 區塊與確認框（TCS-ResearchToPRD-P2-20261107 AT-962-21-5、21-E-3；AC-R2P-20-4；D-138 Q-10；D-142 ⚖P2-13；D-151）。
 * 判定指令：npx vitest run components/domain/research/PrConfirmDialog.test.tsx -t "<AT 底線形>"
 */
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";

import type { ResearchDelivery, ResearchDeliveryOverview, ResearchPrResult, ResearchTraceability, Role } from "@/lib/api/types";
import { PR_ADMIN_ONLY_TEXT, READONLY_TITLE, RESEARCH_REASON_TEXT } from "@/lib/domain/research";
import { R3, sha } from "@/tests/fixtures/research/ids";
import { DELIVERY_OVERVIEW, TRACEABILITY } from "@/tests/fixtures/research/p2";
import { detailVariant } from "@/tests/fixtures/research/projects";
import { callsOf, failure, renderResearch, stubResearchApi, type ApiCall, type Reply } from "@/tests/helpers/research";
import { DeliverPanel } from "./DeliverPanel";
import { PrConfirmDialog, SafeExternalLink, prBodyPreview, prTitlePreview } from "./PrConfirmDialog";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(""),
}));

const PR_URL = /\/delivery\/pr$/;
const PR_ROW: ResearchDelivery = {
  kind: "PULL_REQUEST",
  ref: "42",
  commitSha: "fedcba9876543210fedcba9876543210fedcba98",
  url: "https://github.com/acme/alpha/pull/42",
  rtmReportRef: null,
  fsmStateAfter: "RELEASE",
  status: "CREATED",
  createdBy: "admin",
  createdAt: "2026-11-07T10:00:00+08:00",
  snapshotSha256: null,
};
const TAG_ROW: ResearchDelivery = { ...PR_ROW, kind: "RELEASE_TAG", ref: "v1.2.3", url: null, snapshotSha256: sha("a") };
/** 夾具帶 `frTotal`（D-151、D-158：Bridge 與 console-api 透傳，手寫型已必填）。 */
const TRACE: ResearchTraceability = { ...TRACEABILITY, totals: { acTotal: 10, covered: 8, uncovered: 2, frTotal: 4 } };
const OVERVIEW: ResearchDeliveryOverview = { ...DELIVERY_OVERVIEW, preconditions: { ...DELIVERY_OVERVIEW.preconditions, releaseReady: true, ghAvailable: true, hasOrigin: true } };
const RP = "RP-0003";
const TITLE = "向量資料庫評估";

function mount(role: Role, overview: ResearchDeliveryOverview, reply?: (call: ApiCall) => Reply, branch: string | null = "feature/issue-0003") {
  const base = detailVariant("frozen");
  const stub = stubResearchApi({
    overrides: (call) => {
      if (call.method === "POST" && PR_URL.test(call.path)) return reply?.(call);
      if (call.method === "GET" && /\/route$/.test(call.path))
        return {
          data:
            branch === null
              ? null
              : {
                  routeId: "r",
                  track: "A",
                  targetKind: "MODULE",
                  targetModule: null,
                  targetPath: "/work/alpha",
                  gitBranch: branch,
                  baseRef: null,
                  repoUrl: null,
                  repoVisibility: null,
                  stackTemplate: null,
                  consoleProjectId: null,
                  implFsmProject: null,
                  status: "SUCCEEDED",
                  failureStep: null,
                  publishedDocs: {},
                  scopeDiffersReason: null,
                  decidedBy: "admin",
                  createdAt: "t",
                  finishedAt: null,
                  steps: [],
                },
        };
      return undefined;
    },
  });
  const view = renderResearch(<PrConfirmDialog researchId={R3} rpNo={base.rpNo || RP} title={TITLE} overview={overview} traceability={TRACE} />, role);
  return { ...stub, ...view };
}
const posts = (calls: ApiCall[]) => callsOf(calls, "POST", PR_URL);
const openDialog = async () => {
  fireEvent.click(screen.getByTestId("pr-create"));
  return screen.findByTestId("pr-dialog");
};

describe("AT_962_21_5 PR：已記錄顯示 URL；無 PR 時 ADMIN 見建立 PR 並預覽；其餘顯示尚未建立與原因", () => {
  it("AT_962_21_5 已有 PR：顯示 PR 編號與 URL，連結 target=_blank 且 rel 含 noopener 與 noreferrer；沒有建立鈕", () => {
    mount("ADMIN", { ...OVERVIEW, deliveries: [TAG_ROW, PR_ROW] });
    const existing = screen.getByTestId("pr-existing");
    expect(existing).toHaveTextContent("PR #42");
    const link = within(existing).getByRole("link", { name: "https://github.com/acme/alpha/pull/42" });
    expect(link).toHaveAttribute("href", "https://github.com/acme/alpha/pull/42");
    expect(link).toHaveAttribute("target", "_blank");
    const rel = (link.getAttribute("rel") ?? "").split(/\s+/);
    expect(rel).toEqual(expect.arrayContaining(["noopener", "noreferrer"]));
    expect(screen.queryByTestId("pr-create")).toBeNull();
    expect(screen.queryByTestId("pr-none")).toBeNull();
  });

  it("AT_962_21_5 無 PR 且 gh 可用、ADMIN：見「建立 PR」；開確認框預覽標題（與模板同形）、內文四段與推送目標分支，全為純文字", async () => {
    mount("ADMIN", OVERVIEW);
    expect(screen.getByTestId("pr-none")).toHaveTextContent("尚未建立");
    const dialog = await openDialog();
    await waitFor(() => expect(within(dialog).getByTestId("pr-preview-branch")).toHaveTextContent("feature/issue-0003")); // 分支取自分流決定（非同步載入）
    expect(within(dialog).getByTestId("pr-preview-title").textContent).toBe(`feat: ${detailVariant("frozen").rpNo} ${TITLE}（4 FR／10 AC）`);
    const body = within(dialog).getByTestId("pr-preview-body").textContent ?? "";
    expect(body.match(/^## .+$/gm)).toEqual(["## 摘要", "## 追溯表摘要", "## 規格依據", "## 確認"]);
    expect(body).toContain("- 規模：4 FR／10 AC");
    expect(body).toContain("- AC 總數：10；已覆蓋：8；未覆蓋：2");
    expect(body).toContain("合併與雲端 CI 綠由人確認。");
    expect(within(dialog).getByTestId("pr-preview-note")).toHaveTextContent("實際標題與內文由後端");
    expect(dialog.querySelector("a, img, script")).toBeNull();
  });

  it("AT_962_21_5 標題預覽：專案標題截 60 字（碼點）；frTotal 為 0 也照實顯示；純函式與 Bridge 模板同形", () => {
    const long = "字".repeat(75);
    expect(prTitlePreview("RP-0007", long, 3, 12)).toBe(`feat: RP-0007 ${"字".repeat(60)}（3 FR／12 AC）`);
    expect(prTitlePreview("RP-0007", "標題", 0, 0)).toBe("feat: RP-0007 標題（0 FR／0 AC）");
    expect(prTitlePreview("RP-0007", "標題", 5, 0)).toBe("feat: RP-0007 標題（5 FR／0 AC）");
    expect(prBodyPreview("rid", "RP-0007", { acTotal: 5, covered: 4, uncovered: 1, frTotal: 3 })).toContain("- 規模：3 FR／5 AC");
    // 表情符號（代理對）以碼點計，不切半個字元
    expect(prTitlePreview("RP-1", "😀".repeat(61), 1, 1)).toBe(`feat: RP-1 ${"😀".repeat(60)}（1 FR／1 AC）`);
  });

  it("AT_962_21_5 確認需勾 ack 才可送：未勾時送出鈕停用、強按不送請求；勾選後送出本文 {bodyPreviewAck:true}", async () => {
    const result: ResearchPrResult = { delivery: PR_ROW, created: true };
    const { calls } = mount("ADMIN", OVERVIEW, () => ({ status: 201, data: result }));
    const dialog = await openDialog();
    const submit = within(dialog).getByTestId("pr-submit");
    expect(submit).toBeDisabled();
    fireEvent.click(submit);
    expect(posts(calls)).toHaveLength(0);
    fireEvent.click(within(dialog).getByTestId("pr-ack"));
    expect(submit).toBeEnabled();
    fireEvent.click(submit);
    const done = await within(dialog).findByTestId("pr-result");
    expect(posts(calls)).toHaveLength(1);
    expect(posts(calls)[0].body).toEqual({ bodyPreviewAck: true });
    expect(done).toHaveAttribute("data-created", "true");
    expect(done).toHaveTextContent("已建立 PR #42");
    const link = within(done).getByRole("link");
    expect(link.getAttribute("rel")).toContain("noreferrer");
  });

  it("AT_962_21_5 回應 created:false（該分支已有 PR）：顯示既有連結與「沒有重複建立」，不顯示「已建立 PR」", async () => {
    mount("ADMIN", OVERVIEW, () => ({ data: { delivery: PR_ROW, created: false } as ResearchPrResult }));
    const dialog = await openDialog();
    fireEvent.click(within(dialog).getByTestId("pr-ack"));
    fireEvent.click(within(dialog).getByTestId("pr-submit"));
    const done = await within(dialog).findByTestId("pr-result");
    expect(done).toHaveAttribute("data-created", "false");
    expect(done).toHaveTextContent("這個分支已有 PR #42（沒有重複建立）");
    expect(done.textContent).not.toContain("已建立 PR #");
    expect(within(done).getByRole("link")).toHaveAttribute("href", "https://github.com/acme/alpha/pull/42");
  });

  it("AT_962_21_5 502 delivery_step_failed（pr_create／push）：顯示失敗步驟與說明，不顯示成功態；錯誤後可重送", async () => {
    const replies: Reply[] = [
      failure(502, { reason: "delivery_step_failed", details: { failure_step: "pr_create" } }),
      failure(502, { reason: "delivery_step_failed", details: { failureStep: "push" } }),
    ];
    let n = 0;
    mount("ADMIN", OVERVIEW, () => replies[n++]);
    const dialog = await openDialog();
    fireEvent.click(within(dialog).getByTestId("pr-ack"));
    fireEvent.click(within(dialog).getByTestId("pr-submit"));
    expect(await within(dialog).findByTestId("pr-failed-step")).toHaveTextContent("失敗步驟：建立 PR");
    expect(within(dialog).getByTestId("pr-error")).toHaveTextContent("建立 PR");
    expect(within(dialog).queryByTestId("pr-result")).toBeNull();
    await waitFor(() => expect(within(dialog).getByTestId("pr-submit")).toBeEnabled());
    fireEvent.click(within(dialog).getByTestId("pr-submit"));
    await waitFor(() => expect(within(dialog).getByTestId("pr-failed-step")).toHaveTextContent("失敗步驟：推送到遠端"));
    expect(within(dialog).queryByTestId("pr-result")).toBeNull();
  });

  it("AT_962_21_5 422 route_unsupported_in_deployment：逐項列缺項（gh、gh_auth、origin、repo_writable）；422 preview_ack_required 取登記文案以外不洩漏 reason 鍵", async () => {
    mount("ADMIN", OVERVIEW, () =>
      failure(422, { reason: "route_unsupported_in_deployment", details: { missing: [{ item: "gh" }, { item: "gh_auth" }, { item: "origin" }, { item: "repo_writable" }] } }),
    );
    const dialog = await openDialog();
    fireEvent.click(within(dialog).getByTestId("pr-ack"));
    fireEvent.click(within(dialog).getByTestId("pr-submit"));
    const list = await within(dialog).findByTestId("pr-missing");
    expect(
      within(list)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["gh 命令不可用", "gh 尚未登入", "尚未設定遠端 origin", "無法寫入程式庫"]);
    expect(within(dialog).getByTestId("pr-error")).toHaveTextContent(RESEARCH_REASON_TEXT.route_unsupported_in_deployment);
  });

  it("AT_962_21_5 OPERATOR：沒有建立鈕，顯示「尚未建立」與原因（僅 ADMIN）", () => {
    mount("OPERATOR", OVERVIEW);
    expect(screen.queryByTestId("pr-create")).toBeNull();
    expect(screen.getByTestId("pr-none")).toHaveTextContent("尚未建立");
    expect(screen.getByTestId("pr-role-reason")).toHaveTextContent(PR_ADMIN_ONLY_TEXT);
  });

  it("AT_962_21_5 VIEWER：沒有任何按鈕；原因取 READONLY_TITLE", () => {
    mount("VIEWER", OVERVIEW);
    expect(within(screen.getByTestId("pr-block")).queryAllByRole("button")).toHaveLength(0);
    expect(screen.getByTestId("pr-role-reason")).toHaveTextContent(READONLY_TITLE);
  });

  it("AT_962_21_5 gh 缺失（ghAvailable=false）：顯示「尚未建立」與缺項原因；建立鈕停用、強按不開框", () => {
    mount("ADMIN", { ...OVERVIEW, preconditions: { ...OVERVIEW.preconditions, ghAvailable: false } });
    expect(screen.getByTestId("pr-none")).toHaveTextContent("尚未建立");
    expect(screen.getByTestId("pr-missing-block")).toHaveTextContent("gh 命令不可用");
    expect(screen.getByTestId("pr-create")).toBeDisabled();
    fireEvent.click(screen.getByTestId("pr-create"));
    expect(screen.queryByTestId("pr-dialog")).toBeNull();
  });

  it("AT_962_21_5 沒有 origin（hasOrigin=false）與 gh 缺失同時：兩項原因都列；未知（null）不算缺項", () => {
    const both = mount("ADMIN", { ...OVERVIEW, preconditions: { ...OVERVIEW.preconditions, ghAvailable: false, hasOrigin: false } });
    const items = within(screen.getByTestId("pr-missing-block"))
      .getAllByRole("listitem")
      .map((li) => li.textContent);
    expect(items).toEqual(["gh 命令不可用", "尚未設定遠端 origin"]);
    both.unmount();
    mount("ADMIN", { ...OVERVIEW, preconditions: { ...OVERVIEW.preconditions, ghAvailable: null, hasOrigin: null } });
    expect(screen.queryByTestId("pr-missing-block")).toBeNull();
    expect(screen.getByTestId("pr-create")).toBeEnabled();
  });

  it("AT_962_21_5 路由尚無分支（route 為 null）：推送目標寫「由後端依分流決定的分支」，不編造分支名", async () => {
    mount("ADMIN", OVERVIEW, undefined, null);
    const dialog = await openDialog();
    expect(within(dialog).getByTestId("pr-preview-branch")).toHaveTextContent("由後端依分流決定的分支");
  });
});

describe("AT_962_21_E_3 外部連結安全：所有外部連結帶 noopener noreferrer", () => {
  it("AT_962_21_E_3 全 DeliverPanel 的 <a>：每個 target=_blank 的 rel 皆含 noopener 與 noreferrer（至少有一個外部連結）", async () => {
    stubResearchApi({ delivery: { ...OVERVIEW, deliveries: [TAG_ROW, PR_ROW] }, traceability: TRACE });
    renderResearch(<DeliverPanel researchId={R3} project={detailVariant("frozen")} completed={false} />, "ADMIN");
    const panel = await screen.findByTestId("deliver-panel");
    await within(panel).findByTestId("delivery-records");
    const blanks = [...panel.querySelectorAll("a")].filter((a) => a.getAttribute("target") === "_blank");
    expect(blanks.length).toBeGreaterThanOrEqual(2); // 交付紀錄與 PR 區塊各一
    for (const a of blanks) {
      const rel = (a.getAttribute("rel") ?? "").split(/\s+/);
      expect(rel, a.outerHTML).toEqual(expect.arrayContaining(["noopener", "noreferrer"]));
    }
  });

  it("AT_962_21_E_3 非 https 的 URL（javascript:、http:）不成連結，只顯示純文字", () => {
    for (const bad of ["javascript:alert(1)", "http://insecure.example/pr/1", "//evil.example/x", "data:text/html,x"]) {
      const view = renderResearch(<SafeExternalLink href={bad}>{bad}</SafeExternalLink>, "ADMIN");
      expect(view.container.querySelector("a"), bad).toBeNull();
      expect(view.container).toHaveTextContent(bad);
      view.unmount();
    }
    const ok = renderResearch(<SafeExternalLink href="https://github.com/a/b/pull/1">x</SafeExternalLink>, "ADMIN");
    expect(ok.container.querySelector("a")).not.toBeNull();
  });

  it("AT_962_21_E_3 步驟 5 的元件原始碼沒有 window.open、file://、dangerouslySetInnerHTML、target=_blank 缺 rel（負控：掃描函式抓得到）", () => {
    const names = ["DeliverPanel", "ReleaseActions", "TagConfirmDialog", "PrConfirmDialog", "TraceabilityTable"];
    const strip = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");
    for (const name of names) {
      const code = strip(readFileSync(path.join(process.cwd(), `components/domain/research/${name}.tsx`), "utf8"));
      expect(code.length, name).toBeGreaterThan(300);
      for (const banned of ["window.open", "file://", "dangerouslySetInnerHTML", "innerHTML"]) expect(code, `${name}:${banned}`).not.toContain(banned);
      // 每個 target="_blank" 同一元素內都有 noopener 與 noreferrer
      for (const tag of code.match(/<a\b[^>]*>/g) ?? []) if (tag.includes('target="_blank"')) expect(tag, name).toMatch(/rel="noopener noreferrer"/);
    }
    expect(strip('x = window.open("u")')).toContain("window.open");
  });
});
