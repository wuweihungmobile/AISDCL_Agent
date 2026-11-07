/**
 * 建立 Tag 確認框（TCS-ResearchToPRD-P2-20261107 AT-962-21-4；AC-R2P-20-3；D-138 Q-4、Q-8；D-142 ⚖P2-9；D-144 F-09 界外對照）。
 * 判定指令：npx vitest run components/domain/research/TagConfirmDialog.test.tsx -t AT_962_21_4
 */
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ResearchDelivery, ResearchTagResult, Role } from "@/lib/api/types";
import { RESEARCH_REASON_TEXT, TAG_ADMIN_ONLY_TEXT, TAG_RULE_TEXT } from "@/lib/domain/research";
import { R3, sha } from "@/tests/fixtures/research/ids";
import { callsOf, failure, renderResearch, stubResearchApi, type ApiCall, type Reply } from "@/tests/helpers/research";
import { TagConfirmDialog, tagNameError } from "./TagConfirmDialog";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/research/x",
  useSearchParams: () => new URLSearchParams(""),
}));

const TAG_URL = /\/delivery\/tag$/;
const COMMIT = "0123456789abcdef0123456789abcdef01234567";
const DELIVERY: ResearchDelivery = {
  kind: "RELEASE_TAG",
  ref: "v1.2.3",
  commitSha: COMMIT,
  url: null,
  rtmReportRef: "03_execution/traceability_matrix.json@sha256:abc",
  fsmStateAfter: "RELEASE_READY",
  status: "CREATED",
  createdBy: "admin",
  createdAt: "2026-11-07T10:00:00+08:00",
  snapshotSha256: sha("snap"),
};
const RESULT: ResearchTagResult = {
  delivery: DELIVERY,
  snapshot: { relPath: "03_execution/traceability_matrix.json", sha256: sha("snap") },
  flow: { step: "deliver", phase: "DELIVERED", status: "COMPLETED", detail: "" },
  fsmState: "RELEASE",
};

function mount(role: Role = "ADMIN", reply?: (call: ApiCall) => Reply) {
  const stub = stubResearchApi({ overrides: (call) => (call.method === "POST" && TAG_URL.test(call.path) ? reply?.(call) : undefined) });
  const onOpenChange = vi.fn();
  const view = renderResearch(<TagConfirmDialog researchId={R3} open onOpenChange={onOpenChange} />, role);
  return { ...stub, ...view, onOpenChange };
}
const nameInput = () => screen.getByTestId("tag-name") as HTMLInputElement;
const submitBtn = () => screen.getByTestId("tag-submit") as HTMLButtonElement;
const type = (value: string) => fireEvent.change(nameInput(), { target: { value } });
const posts = (calls: ApiCall[]) => callsOf(calls, "POST", TAG_URL);

describe("AT_962_21_4 Tag 確認框", () => {
  it("AT_962_21_4 semver 即時驗證：不合時送出鈕停用並顯示規則；合法才啟用（表驅動）", () => {
    mount();
    expect(submitBtn()).toBeDisabled(); // 空白：停用但不顯示錯誤
    expect(screen.getByTestId("tag-rule")).toHaveTextContent(TAG_RULE_TEXT);
    for (const bad of ["v1.2", "1.2", "v01.2.3", "vv1.2.3", "v1.2.3.4", "abc", " v1.2.3", "v1.2.3 "]) {
      type(bad);
      expect(submitBtn(), bad).toBeDisabled();
      expect(screen.getByRole("alert"), bad).toHaveTextContent(TAG_RULE_TEXT);
    }
    for (const good of ["v1.2.3", "1.2.3", "v0.0.0", "v1.2.3-rc.1", "v1.2.3+build.5", "v1.2.3-rc.1+build.5"]) {
      type(good);
      expect(submitBtn(), good).toBeEnabled();
      expect(screen.queryByRole("alert"), good).toBeNull();
    }
  });

  it("AT_962_21_4 界外對照（D-144 F-09）：tagName 64 字合法、65 字不合；備註 200 字可送、201 字停用；純函式同值", () => {
    mount();
    const at64 = `v1.0.0-${"a".repeat(64 - 7)}`;
    expect(at64).toHaveLength(64);
    type(at64);
    expect(submitBtn()).toBeEnabled();
    type(`${at64}a`);
    expect(submitBtn()).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent("最多 64 字");
    expect(tagNameError(at64)).toBeNull();
    expect(tagNameError(`${at64}a`)).not.toBeNull();
    type("v1.0.0");
    const message = screen.getByTestId("tag-message");
    fireEvent.change(message, { target: { value: "字".repeat(200) } });
    expect(submitBtn()).toBeEnabled();
    expect(screen.getByTestId("tag-message-counter")).toHaveTextContent("剩餘 0 字");
    fireEvent.change(message, { target: { value: "字".repeat(201) } });
    expect(submitBtn()).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent("備註最多 200 字");
  });

  it("AT_962_21_4 push 勾選預設未勾並附說明；請求本文 push 對應勾選；不顯示也不送 createGithubRelease", async () => {
    const { calls } = mount("ADMIN", () => ({ status: 201, data: RESULT }));
    const push = screen.getByTestId("tag-push") as HTMLInputElement;
    expect(push.checked).toBe(false);
    expect(screen.getByTestId("tag-push-note")).toHaveTextContent("勾選且遠端 origin 存在才推送；不會 force");
    expect(within(screen.getByTestId("tag-dialog")).queryByText(/GitHub Release/i)).toBeNull();
    type("v1.2.3");
    fireEvent.click(submitBtn());
    await screen.findByTestId("tag-result");
    expect(posts(calls)).toHaveLength(1);
    expect(posts(calls)[0].body).toEqual({ tagName: "v1.2.3", push: false });
  });

  it("AT_962_21_4 勾 push 並填備註：本文 {tagName, push:true, message}；沒有 createGithubRelease 鍵", async () => {
    const { calls } = mount("ADMIN", () => ({ status: 201, data: RESULT }));
    fireEvent.click(screen.getByTestId("tag-push"));
    fireEvent.change(screen.getByTestId("tag-message"), { target: { value: "  第一版  " } });
    type("v1.2.3");
    fireEvent.click(submitBtn());
    await screen.findByTestId("tag-result");
    const body = posts(calls)[0].body as Record<string, unknown>;
    expect(body).toEqual({ tagName: "v1.2.3", push: true, message: "第一版" });
    expect("createGithubRelease" in body).toBe(false);
  });

  it("AT_962_21_4 成功：顯示 tag、commit sha 前 12 碼、snapshot sha256 與路徑；之後只剩「關閉」", async () => {
    mount("ADMIN", () => ({ status: 201, data: RESULT }));
    type("v1.2.3");
    fireEvent.click(submitBtn());
    await screen.findByTestId("tag-result");
    expect(screen.getByTestId("tag-result-ref")).toHaveTextContent("v1.2.3");
    expect(screen.getByTestId("tag-result-commit")).toHaveTextContent(COMMIT.slice(0, 12));
    expect(screen.getByTestId("tag-result-commit").textContent).toHaveLength(12);
    expect(screen.getByTestId("tag-result-sha")).toHaveTextContent(sha("snap"));
    expect(screen.getByTestId("tag-result-path")).toHaveTextContent("03_execution/traceability_matrix.json");
    expect(screen.queryByTestId("tag-submit")).toBeNull();
    // 右上角的 X 與底部文字鈕都叫「關閉」
    expect(screen.getAllByRole("button", { name: "關閉" })).toHaveLength(2);
  });

  it("AT_962_21_4 409 tag_exists、409 scr_open 顯示 RESEARCH_REASON_TEXT 文案", async () => {
    const replies: Reply[] = [failure(409, { reason: "tag_exists" }), failure(409, { reason: "scr_open" })];
    let n = 0;
    mount("ADMIN", () => replies[n++]);
    type("v1.2.3");
    fireEvent.click(submitBtn());
    expect((await screen.findByTestId("tag-error")).textContent).toContain(RESEARCH_REASON_TEXT.tag_exists);
    await waitFor(() => expect(submitBtn()).toBeEnabled());
    fireEvent.click(submitBtn());
    await waitFor(() => expect(screen.getByTestId("tag-error").textContent).toContain(RESEARCH_REASON_TEXT.scr_open));
  });

  it("AT_962_21_4 502 delivery_step_failed（failure_step=push）：顯示失敗步驟中文與「本地 Tag 已建立、可重送、不提供回滾」；不顯示成功態", async () => {
    mount("ADMIN", () => failure(502, { reason: "delivery_step_failed", details: { failure_step: "push" } }));
    type("v1.2.3");
    fireEvent.click(submitBtn());
    const error = await screen.findByTestId("tag-error");
    expect(error.textContent).toContain("推送到遠端");
    expect(screen.getByTestId("tag-push-failed-note")).toHaveTextContent("本地 Tag 已建立");
    expect(screen.getByTestId("tag-push-failed-note")).toHaveTextContent("不提供回滾");
    expect(screen.queryByTestId("tag-result")).toBeNull();
    expect(screen.queryByRole("button", { name: /回滾/ })).toBeNull();
  });

  it("AT_962_21_4 502 failure_step 為 fsm_release 時不顯示「本地 Tag 已建立」那句（只對 push）", async () => {
    mount("ADMIN", () => failure(502, { reason: "delivery_step_failed", details: { failureStep: "fsm_release" } }));
    type("v1.2.3");
    fireEvent.click(submitBtn());
    expect((await screen.findByTestId("tag-error")).textContent).toContain("狀態機進入 RELEASE");
    expect(screen.queryByTestId("tag-push-failed-note")).toBeNull();
  });

  it("AT_962_21_4 409 fsm_state_conflict：details.unmet 逐項中文", async () => {
    mount("ADMIN", () => failure(409, { reason: "fsm_state_conflict", details: { unmet: ["not_release_ready", "rtm_below_100"] } }));
    type("v1.2.3");
    fireEvent.click(submitBtn());
    const list = await screen.findByTestId("tag-unmet");
    expect(
      within(list)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["狀態機尚未達 RELEASE_READY", "追溯覆蓋率未達 100%"]);
  });

  it("AT_962_21_4 422 digest_mismatch：逐一列出漂移 path，並提供「發起 SCR」入口（sourceKind 預填 SCG4）", async () => {
    mount("ADMIN", () => failure(422, { reason: "digest_mismatch", details: { drift: [{ path: "docs/01_requirements/PRD.md" }, { path: "docs/03_testing/TCS.md" }] } }));
    type("v1.2.3");
    fireEvent.click(submitBtn());
    const drift = await screen.findByTestId("tag-drift");
    expect(
      within(drift)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["docs/01_requirements/PRD.md", "docs/03_testing/TCS.md"]);
    fireEvent.click(screen.getByRole("button", { name: "發起 SCR" }));
    expect(((await screen.findByTestId("scr-source")) as HTMLSelectElement).value).toBe("SCG4");
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("scr-dialog")).toBeNull());
  });

  it("AT_962_21_4 422 route_unsupported_in_deployment：如實列缺項（容器模式不假裝可行）", async () => {
    mount("ADMIN", () => failure(422, { reason: "route_unsupported_in_deployment", details: { missing: [{ item: "gh" }, { item: "repo_writable" }] } }));
    type("v1.2.3");
    fireEvent.click(submitBtn());
    const list = await screen.findByTestId("tag-missing");
    expect(
      within(list)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["gh 命令不可用", "無法寫入程式庫"]);
  });

  it("AT_962_21_4 403：顯示「僅 ADMIN 可建立 Tag」，不洩漏內部 reason", async () => {
    mount("ADMIN", () => failure(403, { reason: "ACCESS_DENIED" }));
    type("v1.2.3");
    fireEvent.click(submitBtn());
    const error = await screen.findByTestId("tag-error");
    expect(error.textContent).toContain(TAG_ADMIN_ONLY_TEXT);
    expect(error.textContent).not.toContain("ACCESS_DENIED");
  });

  it("AT_962_21_4 非 ADMIN（OPERATOR）：送出鈕停用且 title 說明；強按也不送請求", () => {
    const { calls } = mount("OPERATOR", () => ({ status: 201, data: RESULT }));
    type("v1.2.3");
    expect(submitBtn()).toBeDisabled();
    expect(submitBtn()).toHaveAttribute("title", TAG_ADMIN_ONLY_TEXT);
    fireEvent.click(submitBtn());
    expect(posts(calls)).toHaveLength(0);
  });

  it("AT_962_21_4 取消鈕呼叫 onOpenChange(false)", () => {
    const { onOpenChange } = mount();
    fireEvent.click(screen.getByRole("button", { name: "取消" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
