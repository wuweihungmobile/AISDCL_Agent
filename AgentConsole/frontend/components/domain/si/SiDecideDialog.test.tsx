/**
 * 決定對話框的元件測試（TCS-SelfImprovingDecide-P2b：AT-933-1-2／1-3／1-E-1／1-E-2；W17、W18）。
 * 為什麼重要：這個對話框把「掌舵者的決定」變成會被簽章、落檔、由主機端 CLI 入帳的稽核檔——送錯動詞、漏綁 digest、對狀態不符的卡下決定、連點送出兩筆，
 * 都會在帳本留下無法撤回的紀錄（入帳後只能再下一個決定去補）。所以這裡逐項驗：九個動詞各自送出的本文（鍵集合與鍵序逐位元組）、綁定的是開啟當下的卡面、
 * 預設拒絕（沒選動詞或缺必填欄＝停用且零請求）、失敗不關窗且原因逐字、連點只送一次。
 * 資料來自 tests/helpers/si.tsx 的 fetch 替身（狀態 A 的黃金檔；以 clone 改寫成表 M-V 各列情境）；每個寫入以真 Providers 與真 AuthProvider 走完整條路。
 */
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { SiProposal } from "@/lib/api/types";
import { ingestCommands } from "@/lib/domain/si";
import { failure } from "@/tests/helpers/api";
import { GA, clone, renderSi, type SiFixture, type SiStub } from "@/tests/helpers/si";

// 測試環境沒有 App Router：AuthProvider 要的 useRouter 換成穩定的替身
const router = vi.hoisted(() => ({ push: () => undefined, replace: () => undefined, back: () => undefined }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/self-improving",
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));
// 多步驟的對話框流程（開關對話框、貼上長字串、逐欄量測）在整套平行跑時比單檔慢：給寬一點的逾時，不靠重試掩蓋真的卡住
vi.setConfig({ testTimeout: 30_000 });

const PROP = "PROP-SI-004";
/** 狀態 A 的 PROP-SI-004 卡面 digest（TCS §5.3 的 D0）。 */
const D0 = GA.proposals.items[0].digest;

/** 把 PROP-SI-004 改寫成表 M-V 的某個情境（state、route、verdict、cooldown）。 */
function proposalFixture(patch: Partial<SiProposal>): SiFixture {
  const fixture = clone(GA);
  fixture.proposals.items[0] = { ...fixture.proposals.items[0], ...patch };
  return fixture;
}

/** 橫幅帶暫停狀態的黃金檔變體（恢復綁 `suspended.run`）。 */
function suspendedFixture(run = "RUN-SI-001"): SiFixture {
  const fixture = clone(GA);
  fixture.status.items[0].suspended = { run };
  return fixture;
}

const posts = (stub: SiStub) => stub.calls.filter((c) => c.method === "POST");
const toastText = () => document.querySelector('[data-slot="toast-host"]')?.textContent ?? "";

/** 以 ADMIN 開啟 PROP-SI-004 的決定對話框（切到提案分頁、點該列的決定鈕）。 */
async function openProposalDecide(user: ReturnType<typeof userEvent.setup>, fixture: SiFixture = GA, overrides: SiStub["overrides"] = {}) {
  const view = renderSi({ role: "ADMIN", username: "admin", fixture, overrides });
  await user.click(await screen.findByRole("tab", { name: /^提案/ }));
  await user.click(await screen.findByTestId(`si-decide-open-${PROP}`));
  const dialog = await screen.findByTestId("si-decide-dialog");
  return { ...view, dialog };
}

describe("AT_933_1_2 各動詞送出的請求：方法、網址、JSON 本文逐欄，且綁定開啟時的卡面 digest", () => {
  type Row = {
    dkind: string;
    /** 情境（表 M-V 的列）；缺＝狀態 A 的原樣（proposed、loop） */
    patch?: Partial<SiProposal>;
    /** 恢復由狀態橫幅開啟、綁運轉號 */
    resume?: boolean;
    fill: (user: ReturnType<typeof userEvent.setup>, dialog: HTMLElement) => Promise<void>;
    /** 表 M-D 的期望本文（鍵序即送出的鍵序） */
    expected: Record<string, unknown>;
  };
  const pickVerb = (user: ReturnType<typeof userEvent.setup>, dialog: HTMLElement, dkind: string) => user.selectOptions(within(dialog).getByTestId("si-decide-verb"), dkind);
  const reasoned = async (user: ReturnType<typeof userEvent.setup>, dialog: HTMLElement, dkind: string, reason: string, reasonClass?: string) => {
    await pickVerb(user, dialog, dkind);
    await user.type(within(dialog).getByTestId("si-decide-reason"), reason);
    if (reasonClass) await user.selectOptions(within(dialog).getByTestId("si-decide-class"), reasonClass);
  };
  const VERIFIED = { state: "verified", verdict: "PASS" };
  const ROWS: Row[] = [
    { dkind: "approve", fill: (u, d) => pickVerb(u, d, "approve"), expected: { dkind: "approve", digest: D0 } },
    {
      dkind: "reject",
      fill: (u, d) => reasoned(u, d, "reject", "證據座標不足，無法判定", "證據不足"),
      expected: { dkind: "reject", digest: D0, reason: "證據座標不足，無法判定", reasonClass: "證據不足" },
    },
    { dkind: "return", fill: (u, d) => reasoned(u, d, "return", "改用 M 類", "工件類別錯"), expected: { dkind: "return", digest: D0, reason: "改用 M 類", reasonClass: "工件類別錯" } },
    { dkind: "promote", patch: VERIFIED, fill: (u, d) => pickVerb(u, d, "promote"), expected: { dkind: "promote", digest: D0 } },
    {
      dkind: "promote（晉升後式）",
      patch: { state: "verified", verdict: "NE" },
      fill: async (u, d) => {
        await pickVerb(u, d, "promote");
        await u.click(within(d).getByTestId("si-decide-ack"));
      },
      expected: { dkind: "promote", digest: D0, unverifiedAck: true },
    },
    {
      dkind: "decline-promote",
      patch: VERIFIED,
      fill: (u, d) => reasoned(u, d, "decline-promote", "風險太高", "風險過高"),
      expected: { dkind: "decline-promote", digest: D0, reason: "風險太高", reasonClass: "風險過高" },
    },
    { dkind: "rollback", patch: { state: "promoted", verdict: "PASS" }, fill: (u, d) => reasoned(u, d, "rollback", "太慢"), expected: { dkind: "rollback", reason: "太慢" } },
    { dkind: "unblock", patch: { state: "rejected", verdict: "FAIL", cooldown: { class: "M" } }, fill: (u, d) => pickVerb(u, d, "unblock"), expected: { dkind: "unblock" } },
    { dkind: "ack-handoff", patch: { route: "handoff:T1" }, fill: (u, d) => pickVerb(u, d, "ack-handoff"), expected: { dkind: "ack-handoff", digest: D0 } },
    { dkind: "resume", resume: true, fill: (u, d) => reasoned(u, d, "resume", "兩個壞窗已人工檢視"), expected: { dkind: "resume", reason: "兩個壞窗已人工檢視" } },
  ];

  it("AT_933_1_2 九個 dkind 各填必填欄後送出：每次恰一個 POST，網址為 /api/v1/si/proposals/<id>/decide，本文鍵集合、鍵序與值逐項等於表 M-D；resume 的 id 為 RUN 號且無 digest；unverifiedAck 只在晉升後式出現且為 true", async () => {
    const user = userEvent.setup();
    for (const row of ROWS) {
      const label = row.dkind;
      let view: ReturnType<typeof renderSi>;
      let dialog: HTMLElement;
      if (row.resume) {
        view = renderSi({ role: "ADMIN", username: "admin", fixture: suspendedFixture() });
        await user.click(await screen.findByTestId("si-resume-open"));
        dialog = await screen.findByTestId("si-decide-dialog");
      } else {
        ({ dialog, ...view } = await openProposalDecide(user, row.patch ? proposalFixture(row.patch) : GA));
      }
      await row.fill(user, dialog);
      await user.click(within(dialog).getByTestId("si-decide-submit"));
      await waitFor(() => expect(posts(view.stub), label).toHaveLength(1));

      const call = posts(view.stub)[0];
      expect(call.path, label).toBe(`/api/v1/si/proposals/${row.resume ? "RUN-SI-001" : PROP}/decide`);
      expect(call.body, `${label} 的本文逐位元組`).toBe(JSON.stringify(row.expected));
      expect(Object.keys(JSON.parse(call.body as string)), label).toEqual(Object.keys(row.expected));
      await within(dialog).findByTestId("si-decide-result");
      view.unmount();
    }
    // 防反空轉：九個動詞加晉升後式共十列都跑過（resume 有 RUN 號、其餘有 PROP 號）
    expect(ROWS.map((r) => (r.dkind.startsWith("promote") ? "promote" : r.dkind)).sort()).toEqual([
      "ack-handoff",
      "approve",
      "decline-promote",
      "promote",
      "promote",
      "reject",
      "resume",
      "return",
      "rollback",
      "unblock",
    ]);
  });

  it("AT_933_1_2 digest 綁定開啟當下的卡面：對話框開著時卡面被重抓成另一個 digest，送出的仍是開啟時的值；畫面顯示前 8 碼、全文在 title", async () => {
    const user = userEvent.setup();
    const { stub, dialog } = await openProposalDecide(user);
    const shown = within(dialog).getByTestId("si-decide-digest");
    expect(shown).toHaveTextContent(D0.replace(/^sha256:/, "").slice(0, 8));
    expect(shown).toHaveAttribute("title", D0);

    const changed = `sha256:${"e".repeat(64)}`;
    stub.fixture = proposalFixture({ digest: changed });
    fireEvent.click(screen.getByTestId("si-refresh")); // 對話框是 modal：直接派送事件，等同背景資料被重抓
    await waitFor(() => expect(within(screen.getByTestId(`si-prop-row-${PROP}`)).getByText("eeeeeeee")).toBeInTheDocument());

    await user.selectOptions(within(dialog).getByTestId("si-decide-verb"), "approve");
    await user.click(within(dialog).getByTestId("si-decide-submit"));
    await waitFor(() => expect(posts(stub)).toHaveLength(1));
    expect(JSON.parse(posts(stub)[0].body as string)).toEqual({ dkind: "approve", digest: D0 });
    expect(posts(stub)[0].body).not.toContain("eeeeeeee");
  });

  it("AT_933_1_2 切換動詞會清掉隱藏欄位的殘值：先填 reject 的理由與類別再改選 approve，本文只有 dkind 與 digest", async () => {
    const user = userEvent.setup();
    const { stub, dialog } = await openProposalDecide(user);
    await user.selectOptions(within(dialog).getByTestId("si-decide-verb"), "reject");
    await user.type(within(dialog).getByTestId("si-decide-reason"), "先寫了理由");
    await user.selectOptions(within(dialog).getByTestId("si-decide-class"), "未說明");
    await user.selectOptions(within(dialog).getByTestId("si-decide-verb"), "approve");
    expect(within(dialog).queryByTestId("si-decide-reason")).toBeNull();
    expect(within(dialog).queryByTestId("si-decide-class")).toBeNull();
    // 改回 reject：欄位是空的（殘值已清），所以仍不可送出——殘值不會被偷偷帶進下一個動詞
    await user.selectOptions(within(dialog).getByTestId("si-decide-verb"), "reject");
    expect(within(dialog).getByTestId("si-decide-reason")).toHaveValue("");
    expect(within(dialog).getByTestId("si-decide-class")).toHaveValue("");
    expect(within(dialog).getByTestId("si-decide-submit")).toBeDisabled();
    await user.selectOptions(within(dialog).getByTestId("si-decide-verb"), "approve");
    await user.click(within(dialog).getByTestId("si-decide-submit"));
    await waitFor(() => expect(posts(stub)).toHaveLength(1));
    expect(posts(stub)[0].body).toBe(JSON.stringify({ dkind: "approve", digest: D0 }));
  });
});

describe("AT_933_1_3 送出成功後顯示 auditRef 與待入帳指令（兩個 CopyCommand），對話框不自動關閉", () => {
  it("AT_933_1_3 收據含 auditRef 與待入帳字樣，兩個指令逐字等於 ingestCommands(decide, PROP-SI-004, auditRef)；對話框仍開；關閉後重開同一張卡不沿用上次結果", async () => {
    const user = userEvent.setup();
    const { stub, dialog } = await openProposalDecide(user);
    await user.selectOptions(within(dialog).getByTestId("si-decide-verb"), "approve");
    await user.click(within(dialog).getByTestId("si-decide-submit"));

    const result = await within(dialog).findByTestId("si-decide-result");
    const receipt = { auditRef: "a1000000-0000-4000-8000-000000000001" };
    expect(result).toHaveTextContent(receipt.auditRef);
    expect(result).toHaveTextContent("待入帳");
    const expected = ingestCommands("decide", PROP, receipt.auditRef);
    expect(within(result).getByTestId("sdd-recovery-command-powershell").textContent).toBe(expected.powershell);
    expect(within(result).getByTestId("sdd-recovery-command-posix").textContent).toBe(expected.posix);
    expect(expected.powershell).toBe(`python tools/selfimproving.py decide ${PROP} --carrier console --audit-ref ${receipt.auditRef}`);
    expect(screen.getByTestId("si-decide-dialog"), "不自動關閉").toBeInTheDocument();
    expect(posts(stub)).toHaveLength(1);
    // 收據之後表單收起：同一張卡不會被誤送出第二筆決定
    expect(within(dialog).queryByTestId("si-decide-submit")).toBeNull();

    // 標題列的 X 與收據下方的「關閉」同名同義：點收據下方的那個（最後一個）
    const closers = within(dialog).getAllByRole("button", { name: "關閉" });
    expect(closers).toHaveLength(2);
    await user.click(closers[closers.length - 1]);
    await waitFor(() => expect(screen.queryByTestId("si-decide-dialog")).toBeNull());
    await user.click(screen.getByTestId(`si-decide-open-${PROP}`));
    const again = await screen.findByTestId("si-decide-dialog");
    expect(within(again).queryByTestId("si-decide-result"), "不沿用上次結果").toBeNull();
    expect(within(again).getByTestId("si-decide-verb")).toHaveValue("");
  });

  it("AT_933_1_3 成功後重取 SI 查詢（含 PROP 清單）但不碰 notifications 家族：寫入後多出的 GET 都在 /api/v1/si/ 之下", async () => {
    const user = userEvent.setup();
    const { stub, dialog } = await openProposalDecide(user);
    const before = stub.calls.length;
    await user.selectOptions(within(dialog).getByTestId("si-decide-verb"), "approve");
    await user.click(within(dialog).getByTestId("si-decide-submit"));
    await within(dialog).findByTestId("si-decide-result");
    await waitFor(() => expect(stub.calls.slice(before).some((c) => c.method === "GET" && c.path === "/api/v1/si/proposals")).toBe(true));
    for (const call of stub.calls.slice(before)) expect(call.path.startsWith("/api/v1/si/"), call.url).toBe(true);
  });
});

describe("AT_933_1_E_1 預設拒絕：未選動詞或缺必填欄時送出鈕停用且零請求，沒有批次核准", () => {
  const TWO_CARDS = (() => {
    const fixture = proposalFixture({ state: "verified", verdict: "PASS" });
    const ne = clone(fixture.proposals.items[0]);
    ne.id = "PROP-SI-005";
    ne.verdict = "NE";
    fixture.proposals.items.push(ne);
    return fixture;
  })();

  it("AT_933_1_E_1 不選動詞按送出：停用、有原因文字、零個 POST；逐一選動詞各缺理由或理由類別：仍停用；補齊後才可送", async () => {
    const user = userEvent.setup();
    const { stub, dialog } = await openProposalDecide(user, proposalFixture({ state: "proposed" }));
    const submit = within(dialog).getByTestId("si-decide-submit");
    expect(submit).toBeDisabled();
    expect(within(dialog).getByTestId("si-decide-blocked")).toHaveTextContent("請選擇決定動詞");
    await user.click(submit);
    expect(posts(stub)).toHaveLength(0);

    await user.selectOptions(within(dialog).getByTestId("si-decide-verb"), "reject");
    expect(submit).toBeDisabled();
    expect(within(dialog).getByTestId("si-decide-blocked")).toHaveTextContent("理由");
    await user.type(within(dialog).getByTestId("si-decide-reason"), "證據不足");
    expect(submit, "有理由但缺理由類別").toBeDisabled();
    expect(within(dialog).getByTestId("si-decide-blocked")).toHaveTextContent("理由類別");
    await user.selectOptions(within(dialog).getByTestId("si-decide-class"), "證據不足");
    expect(submit).toBeEnabled();
    expect(within(dialog).queryByTestId("si-decide-blocked")).toBeNull();
    expect(posts(stub), "補齊之前一個 POST 都沒有").toHaveLength(0);

    // 理由含換行（貼上）：即使欄位有內容，仍停用並指出理由
    await user.clear(within(dialog).getByTestId("si-decide-reason"));
    await user.click(within(dialog).getByTestId("si-decide-reason"));
    await user.paste("第一行\n第二行");
    expect(submit).toBeDisabled();
    expect(within(dialog).getByTestId("si-decide-blocked")).toHaveTextContent("控制字元");
    expect(posts(stub)).toHaveLength(0);
  });

  it("AT_933_1_E_1 PASS 的晉升沒有勾選框；NE 的晉升後式在未勾選時停用、勾選後才可送", async () => {
    const user = userEvent.setup();
    const pass = await openProposalDecide(user, TWO_CARDS);
    await user.selectOptions(within(pass.dialog).getByTestId("si-decide-verb"), "promote");
    expect(within(pass.dialog).queryByTestId("si-decide-ack"), "PASS 的晉升不需要勾選").toBeNull();
    expect(within(pass.dialog).getByTestId("si-decide-submit")).toBeEnabled();
    pass.unmount();

    const view = renderSi({ role: "ADMIN", username: "admin", fixture: TWO_CARDS });
    await user.click(await screen.findByRole("tab", { name: /^提案/ }));
    await user.click(await screen.findByTestId("si-decide-open-PROP-SI-005"));
    const dialog = await screen.findByTestId("si-decide-dialog");
    await user.selectOptions(within(dialog).getByTestId("si-decide-verb"), "promote");
    const submit = within(dialog).getByTestId("si-decide-submit");
    expect(within(dialog).getByTestId("si-decide-ack")).toBeInTheDocument();
    expect(submit, "未勾選").toBeDisabled();
    expect(within(dialog).getByTestId("si-decide-blocked")).toHaveTextContent("NE");
    await user.click(within(dialog).getByTestId("si-decide-ack"));
    expect(submit).toBeEnabled();
    await user.click(within(dialog).getByTestId("si-decide-ack"));
    expect(submit, "取消勾選後又停用").toBeDisabled();
    expect(posts(view.stub)).toHaveLength(0);
  });

  it("AT_933_1_E_1 掃描整個 si-view：沒有全部核准、批次核准或不帶 ID 的決定控件；每個決定入口的 testid 都帶提案號", async () => {
    const user = userEvent.setup();
    const view = renderSi({ role: "ADMIN", username: "admin", fixture: TWO_CARDS });
    await user.click(await screen.findByRole("tab", { name: /^提案/ }));
    await screen.findByTestId("si-decide-open-PROP-SI-005");
    const root = view.container.querySelector('[data-testid="si-view"]') as HTMLElement;
    for (const el of Array.from(root.querySelectorAll<HTMLElement>("button, a, [role='button']"))) {
      const name = `${el.getAttribute("aria-label") ?? ""} ${el.textContent ?? ""}`;
      expect(name, `批次控件：${name}`).not.toMatch(/全部核准|批次|核准全部|全部決定|一鍵/);
    }
    const openers = Array.from(root.querySelectorAll<HTMLElement>('[data-testid^="si-decide-open"]')).map((el) => el.dataset.testid as string);
    expect(openers.length).toBeGreaterThan(0);
    for (const id of openers) expect(id, "決定入口必須帶提案號").toMatch(/^si-decide-open-PROP-SI-\d{3,}$/);
  });
});

describe("AT_933_1_E_2 失敗不關窗、原因逐字：403、409、503、422 各一次，連點只送一次", () => {
  it("AT_933_1_E_2 四種失敗各送一次（每次連點送出鈕兩下）：toast 含 reason 逐字（422 另含每筆 violation 的 message）、對話框不關、送出鈕請求中停用且結束後恢復、每次點擊序列恰一個 POST", async () => {
    // delay: null＝兩下點擊之間不讓出事件迴圈（比一次網路往返更快的連點）；有延遲的 dblClick 可能在第一個請求結束後才點第二下，那是合法的重送、不是連點
    const user = userEvent.setup({ delay: null });
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const replies: Array<() => Response> = [
      () => failure(403, { message: "帳號不在決定者名單內", reason: "si_write_forbidden" }),
      () => failure(409, { message: "稽核檔已存在", reason: "si_audit_exists" }),
      () => failure(503, { message: "寫入面已停用", reason: "si_write_disabled", details: { cause: "audit_key_unset" } }),
      () =>
        failure(422, {
          message: "請求欄位未通過檢查（2 項）",
          reason: "invalid_request",
          errors: [
            { field: "reason", message: "理由為必填" },
            { field: "reasonClass", message: "理由類別為必填" },
          ],
          details: {
            violations: [
              { field: "reason", message: "理由為必填" },
              { field: "reasonClass", message: "理由類別為必填" },
            ],
          },
        }),
    ];
    let served = 0;
    const { stub, dialog } = await openProposalDecide(user, GA, {
      decide: async () => {
        if (served === 0) await gate; // 第一次：把回應卡住，驗證請求中停用
        return replies[served++]();
      },
    });
    await user.selectOptions(within(dialog).getByTestId("si-decide-verb"), "approve");
    const submit = within(dialog).getByTestId("si-decide-submit");

    const expectations: Array<[reason: string, extra: string[]]> = [
      ["si_write_forbidden", []],
      ["si_audit_exists", []],
      ["si_write_disabled", []],
      ["invalid_request", ["理由為必填", "理由類別為必填"]],
    ];
    for (const [index, [reason, extra]] of expectations.entries()) {
      await user.dblClick(submit);
      if (index === 0) {
        await waitFor(() => expect(submit, "請求中停用").toBeDisabled());
        expect(posts(stub), "連點只送一次（第一個回應還沒回來）").toHaveLength(1);
        release?.();
      }
      await waitFor(() => expect(toastText()).toContain(reason));
      for (const message of extra) expect(toastText()).toContain(message);
      expect(posts(stub), `第 ${index + 1} 次點擊序列恰一個 POST`).toHaveLength(index + 1);
      expect(screen.getByTestId("si-decide-dialog"), "失敗不關窗").toBeInTheDocument();
      await waitFor(() => expect(submit, "結束後恢復").toBeEnabled());
      expect(within(dialog).queryByTestId("si-decide-result"), "失敗不顯示收據").toBeNull();
    }
  });
});
