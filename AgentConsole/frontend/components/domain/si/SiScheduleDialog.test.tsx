/**
 * 排程設定對話框的元件測試（TCS-SelfImprovingSchedule：AT-964-2-2／2-3／2-E-1／2-E-2、3-1／3-3／3-E-1／3-E-2、6-2／6-3／6-4；W-S2、W-S3、W-S6）。
 * 為什麼重要：這個對話框把「掌舵者要的週期」簽成稽核檔落到主機端——週期界外的值送出去，主機入帳時才被根層 CLI 拒收（掌舵者以為排好了其實沒有）；
 * 收據若寫成「已生效」就是對掌舵者說謊（入帳前什麼都沒變）；連點會落兩份稽核檔；失敗若關窗或改寫原因，掌舵者就查不到缺哪一項設定。
 * 所以這裡逐項驗：界只取自橫幅（夾具值導出，不寫死）、端點與界外各種輸入、停用方向仍須帶界內週期、本文逐位元組、收據文案與入帳指令、失敗逐字且不關窗、連點只送一次。
 */
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { failure } from "@/tests/helpers/api";
import { ingestCommands, validateScheduleForm } from "@/lib/domain/si";
import { ADMIN_UI, BOUNDS, DROP, fixtureWithStatus, renderSi, sched, statusItem, type SiStub } from "@/tests/helpers/si";

// 測試環境沒有 App Router：AuthProvider 要的 useRouter 換成穩定的替身
const router = vi.hoisted(() => ({ push: () => undefined, replace: () => undefined, back: () => undefined }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/self-improving",
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));
// 多步驟的對話框流程在整套平行跑時比單檔慢：給寬一點的逾時，不靠重試掩蓋真的卡住
vi.setConfig({ testTimeout: 30_000 });

type User = ReturnType<typeof userEvent.setup>;
const posts = (stub: SiStub, endsWith = "/schedule/set") => stub.calls.filter((c) => c.method === "POST" && c.path.endsWith(endsWith));
const gets = (stub: SiStub, endsWith: string) => stub.calls.filter((c) => c.method === "GET" && c.path.endsWith(endsWith));

/** 以 ADMIN 渲染含給定 `schedule` 的頁面。 */
function mount(schedule: unknown, overrides: SiStub["overrides"] = {}) {
  return renderSi({ ...ADMIN_UI, fixture: fixtureWithStatus(statusItem({ schedule })), overrides });
}

/** 點面板的設定鈕（改週期＝帶現值的啟用狀態；啟用或停用鈕＝與現值相反）開對話框。 */
async function openDialog(user: User, which: "si-schedule-period-open" | "si-schedule-toggle-open" = "si-schedule-period-open") {
  await user.click(await screen.findByTestId(which));
  return screen.findByTestId("si-schedule-dialog");
}
const periodInput = (dialog: HTMLElement) => within(dialog).getByTestId("si-schedule-period") as HTMLInputElement;
const submitButton = (dialog: HTMLElement) => within(dialog).getByTestId("si-schedule-submit") as HTMLButtonElement;
/** 收據畫面的「關閉」鈕（對話框右上另有一個叉叉也叫關閉，取有文字的那個）。 */
async function closeResult(user: User, dialog: HTMLElement) {
  const button = within(dialog)
    .getAllByRole("button", { name: "關閉" })
    .find((b) => b.textContent === "關閉");
  if (!button) throw new Error("找不到收據畫面的關閉鈕");
  await user.click(button);
}
async function typePeriod(user: User, dialog: HTMLElement, text: string) {
  const input = periodInput(dialog);
  await user.clear(input);
  if (text !== "") await user.type(input, text);
}

describe("AT_964_2_2 界取自橫幅的 periodMin／periodMax，改界後行為隨之改變", () => {
  it("AT_964_2_2 甲的界 60～10080、乙的界 30～120：各填 45，甲的送出鈕停用且錯誤文字指出甲的界、乙的可用；validateScheduleForm 沒給界時回量不到界值", async () => {
    const user = userEvent.setup();
    const jia = { periodMin: 60, periodMax: 10080 };
    const yi = { periodMin: 30, periodMax: 120 };
    const first = mount(sched(jia));
    let dialog = await openDialog(user);
    await typePeriod(user, dialog, "45");
    expect(submitButton(dialog)).toBeDisabled();
    expect(dialog.textContent).toContain(String(jia.periodMin));
    expect(dialog.textContent).toContain(String(jia.periodMax));
    expect(periodInput(dialog)).toHaveAttribute("aria-invalid", "true");
    first.unmount();

    mount(sched(yi));
    dialog = await openDialog(user);
    await typePeriod(user, dialog, "45");
    expect(submitButton(dialog)).toBeEnabled();
    expect(periodInput(dialog)).not.toHaveAttribute("aria-invalid");

    expect(validateScheduleForm({ enabled: true, periodText: "45", reason: "" }).periodMinutes).toBe("量不到界值");
  });
});

describe("AT_964_2_3 預填目前週期；停用時週期仍必填並可送出", () => {
  it("AT_964_2_3 現值 720、啟用：預填 720；切為停用送出的本文為 enabled false 加 periodMinutes 720；清空週期時送出停用且標紅", async () => {
    const user = userEvent.setup();
    const view = mount(sched({ periodMinutes: 720, enabled: true }));
    let dialog = await openDialog(user);
    expect(periodInput(dialog).value).toBe("720");
    await user.click(within(dialog).getByTestId("si-schedule-enabled"));
    await user.click(submitButton(dialog));
    await within(dialog).findByTestId("si-schedule-result");
    expect(posts(view.stub)).toHaveLength(1);
    expect(posts(view.stub)[0].body).toBe(JSON.stringify({ enabled: false, periodMinutes: 720 }));
    await closeResult(user, dialog);

    // 停用方向清空週期：不開例外，送出停用且標紅
    dialog = await openDialog(user);
    await user.click(within(dialog).getByTestId("si-schedule-enabled"));
    await typePeriod(user, dialog, "");
    expect(submitButton(dialog)).toBeDisabled();
    expect(periodInput(dialog)).toHaveAttribute("aria-invalid", "true");
    expect(posts(view.stub), "沒有再多送一個").toHaveLength(1);
  });
});

describe("AT_964_2_E_1 週期的界外、端點、非整數、小數、空白、負數、零", () => {
  const CASES: Array<[string, string, boolean]> = [
    ["端點下", String(BOUNDS.periodMin), true],
    ["端點上", String(BOUNDS.periodMax), true],
    ["界下一", String(BOUNDS.periodMin - 1), false],
    ["界上一", String(BOUNDS.periodMax + 1), false],
    ["小數", "90.5", false],
    ["非數字", "abc", false],
    ["空字串", "", false],
    ["全空白", "   ", false],
    ["負數", "-60", false],
    ["零", "0", false],
    ["科學記號 1e3（不當作整數 1000）", "1e3", false],
  ];
  it.each(CASES)("AT_964_2_E_1 %s（輸入 %j）：%s", async (_name, text, accepted) => {
    const user = userEvent.setup();
    mount(sched());
    const dialog = await openDialog(user);
    await typePeriod(user, dialog, text);
    const label = `輸入 ${JSON.stringify(text)}`;
    if (accepted) {
      expect(submitButton(dialog), label).toBeEnabled();
      expect(periodInput(dialog), label).not.toHaveAttribute("aria-invalid");
    } else {
      expect(submitButton(dialog), label).toBeDisabled();
      expect(periodInput(dialog), label).toHaveAttribute("aria-invalid", "true");
    }
  });
});

describe("AT_964_2_E_2 界取不到：送出停用並說明量不到界值；現值落界外時預填標紅", () => {
  it.each([
    ["periodMin 缺席", { periodMin: DROP }],
    ["periodMax 為字串", { periodMax: "10080" }],
    ["periodMin 大於 periodMax", { periodMin: 200, periodMax: 100 }],
  ] as Array<[string, Record<string, unknown>]>)("AT_964_2_E_2 %s", async (_name, over) => {
    const user = userEvent.setup();
    mount(sched(over));
    const dialog = await openDialog(user);
    expect(submitButton(dialog)).toBeDisabled();
    expect(dialog.textContent).toContain("量不到界值");
  });

  it("AT_964_2_E_2 schedule 整鍵缺席：面板仍可開對話框，送出停用並說明量不到界值", async () => {
    const user = userEvent.setup();
    mount(DROP);
    const dialog = await openDialog(user);
    expect(submitButton(dialog)).toBeDisabled();
    expect(dialog.textContent).toContain("量不到界值");
  });

  it("AT_964_2_E_2 現值 30、界 60～10080：預填 30 標紅，提示請先改成界內週期，送出停用", async () => {
    const user = userEvent.setup();
    mount(sched({ periodMinutes: 30 }));
    const dialog = await openDialog(user);
    expect(periodInput(dialog).value).toBe("30");
    expect(periodInput(dialog)).toHaveAttribute("aria-invalid", "true");
    expect(dialog.textContent).toContain("請先改成界內週期");
    expect(submitButton(dialog)).toBeDisabled();
  });
});

describe("AT_964_3_1 送出的請求本文與 201 收據、待入帳文案、入帳指令、查詢失效重取", () => {
  it("AT_964_3_1 填啟用、週期 120、理由一行送出：本文恰為三鍵；收據顯示稽核編號、sched-set、時間與稽核檔已落地，待入帳（不含已生效字樣）；兩處入帳指令相同；含心跳 15 的說明；status 與 console-writes 各重取一次", async () => {
    const user = userEvent.setup();
    const view = mount(sched({ heartbeatMinutes: 15 }));
    const dialog = await openDialog(user);
    await typePeriod(user, dialog, "120");
    await user.type(within(dialog).getByTestId("si-schedule-reason"), "一行理由");
    const statusBefore = gets(view.stub, "/si/status").length;
    const writesBefore = gets(view.stub, "/si/console-writes").length;
    await user.click(submitButton(dialog));
    const result = await within(dialog).findByTestId("si-schedule-result");

    expect(posts(view.stub)).toHaveLength(1);
    expect(posts(view.stub)[0].path).toBe("/api/v1/si/schedule/set");
    expect(posts(view.stub)[0].body).toBe(JSON.stringify({ enabled: true, periodMinutes: 120, reason: "一行理由" }));

    const ref = within(result).getByTestId("si-audit-ref").textContent as string;
    expect(ref).toMatch(/^[0-9a-f-]{36}$/);
    expect(within(result).getByTestId("si-receipt-kind").textContent).toBe("sched-set");
    expect(within(result).getByTestId("si-receipt-time").textContent).toBe("2026-10-24T22:30:15+08:00");
    expect(result.textContent).toContain("稽核檔已落地，待入帳");
    expect(result.textContent).not.toMatch(/已生效|已啟用|已啟動/);
    const cmd = ingestCommands("sched-set", null, ref);
    expect(cmd.powershell).toBe(`python tools/selfimproving.py sched set --carrier console --audit-ref ${ref}`);
    expect(within(result).getAllByText(cmd.powershell), "PowerShell 與 POSIX 兩處字串相同").toHaveLength(2);
    expect(within(result).getByTestId("si-receipt-extra").textContent).toContain("15");

    await waitFor(() => expect(gets(view.stub, "/si/status")).toHaveLength(statusBefore + 1));
    await waitFor(() => expect(gets(view.stub, "/si/console-writes")).toHaveLength(writesBefore + 1));
  });
});

describe("AT_964_3_3 確認摘要文字與理由選填：空理由時本文不含 reason", () => {
  it("AT_964_3_3 停用、週期 1440、理由留空：摘要說明改成停用並列出週期與 ≈1 天；本文恰為兩鍵；理由填入一行後本文才含 reason", async () => {
    const user = userEvent.setup();
    const view = mount(sched());
    let dialog = await openDialog(user, "si-schedule-toggle-open");
    // 現值為啟用，啟用或停用鈕帶相反值＝停用
    const summary = within(dialog).getByTestId("si-schedule-summary").textContent as string;
    expect(summary).toContain("停用");
    expect(summary).toContain("1440");
    expect(summary).toContain("≈1 天");
    await user.click(submitButton(dialog));
    await within(dialog).findByTestId("si-schedule-result");
    expect(posts(view.stub)[0].body).toBe(JSON.stringify({ enabled: false, periodMinutes: 1440 }));
    expect(JSON.parse(posts(view.stub)[0].body as string)).not.toHaveProperty("reason");
    await closeResult(user, dialog);

    dialog = await openDialog(user, "si-schedule-toggle-open");
    await user.type(within(dialog).getByTestId("si-schedule-reason"), "夜間先停");
    await user.click(submitButton(dialog));
    await within(dialog).findByTestId("si-schedule-result");
    expect(posts(view.stub)[1].body).toBe(JSON.stringify({ enabled: false, periodMinutes: 1440, reason: "夜間先停" }));
  });
});

describe("AT_964_3_E_1 失敗不關窗：409、502、504 與網路錯誤逐字顯示 reason 與 message", () => {
  it("AT_964_3_E_1 四種失敗各送出一次：對話框仍開、表單內容保留、送出鈕恢復可用、畫面逐字顯示該次 reason 與 message、沒有收據區", async () => {
    const user = userEvent.setup();
    const replies: Array<() => Response> = [
      () => failure(409, { message: "稽核檔已存在-夾具", reason: "si_audit_exists" }),
      () => failure(502, { message: "Bridge 回應錯誤-夾具", reason: "bridge_error" }),
      () => failure(504, { message: "Bridge 逾時-夾具", reason: "bridge_timeout" }),
      () => {
        throw new TypeError("Failed to fetch");
      },
    ];
    let n = 0;
    const view = mount(sched(), { "schedule-set": () => replies[n++]() });
    const dialog = await openDialog(user);
    await typePeriod(user, dialog, "180");
    await user.type(within(dialog).getByTestId("si-schedule-reason"), "保留的理由");
    const expected = [
      ["稽核檔已存在-夾具", "si_audit_exists"],
      ["Bridge 回應錯誤-夾具", "bridge_error"],
      ["Bridge 逾時-夾具", "bridge_timeout"],
    ];
    for (let i = 0; i < replies.length; i++) {
      await user.click(submitButton(dialog));
      const error = await within(dialog).findByTestId("si-schedule-error");
      await waitFor(() => expect(submitButton(dialog)).toBeEnabled());
      if (i < expected.length) {
        expect(error.textContent, `第 ${i + 1} 次`).toContain(expected[i][0]);
        expect(error.textContent, `第 ${i + 1} 次`).toContain(expected[i][1]);
      } else {
        expect((error.textContent ?? "").length, "網路錯誤也要有說明").toBeGreaterThan(0);
      }
      expect(screen.getByTestId("si-schedule-dialog")).toBe(dialog);
      expect(periodInput(dialog).value, "表單內容保留").toBe("180");
      expect((within(dialog).getByTestId("si-schedule-reason") as HTMLTextAreaElement).value).toBe("保留的理由");
      expect(within(dialog).queryByTestId("si-schedule-result")).toBeNull();
    }
    expect(posts(view.stub)).toHaveLength(replies.length);
  });
});

describe("AT_964_3_E_2 連點只送一次；缺必填停用送出", () => {
  it("AT_964_3_E_2 POST 延遲回應時連點三次：只送一次、回應前送出鈕停用；另一次清空週期再點：POST 為零次", async () => {
    const user = userEvent.setup();
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const view = mount(sched(), {
      "schedule-set": async () => {
        await gate;
        return undefined;
      },
    });
    let dialog = await openDialog(user);
    await user.click(submitButton(dialog));
    await user.click(submitButton(dialog));
    await user.click(submitButton(dialog));
    await waitFor(() => expect(posts(view.stub)).toHaveLength(1));
    expect(submitButton(dialog), "回應前送出鈕為停用").toBeDisabled();
    release();
    await within(dialog).findByTestId("si-schedule-result");
    expect(posts(view.stub), "連點只送一次").toHaveLength(1);
    await closeResult(user, dialog);

    dialog = await openDialog(user);
    await typePeriod(user, dialog, "");
    expect(submitButton(dialog)).toBeDisabled();
    await user.click(submitButton(dialog));
    expect(posts(view.stub), "缺必填時沒有新請求").toHaveLength(1);
  });
});

describe("AT_964_6_2 名單外 ADMIN 的 403 si_write_forbidden 逐字顯示且不關窗", () => {
  it("AT_964_6_2 設定對話框與立即啟動對話框各送出一次：兩者逐字顯示 reason 與 message、對話框不關、送出鈕恢復", async () => {
    const user = userEvent.setup();
    const forbidden = () => failure(403, { message: "帳號不在決定者名單內-夾具", reason: "si_write_forbidden" });
    mount(sched(), { "schedule-set": forbidden, "run-request": forbidden });
    const dialog = await openDialog(user);
    await user.click(submitButton(dialog));
    let error = await within(dialog).findByTestId("si-schedule-error");
    expect(error.textContent).toContain("帳號不在決定者名單內-夾具");
    expect(error.textContent).toContain("si_write_forbidden");
    await waitFor(() => expect(submitButton(dialog)).toBeEnabled());
    expect(screen.getByTestId("si-schedule-dialog")).toBe(dialog);
    await user.click(within(dialog).getByRole("button", { name: "取消" }));

    await user.click(await screen.findByTestId("si-run-request-open"));
    const run = await screen.findByTestId("si-run-request-dialog");
    await user.click(within(run).getByTestId("si-run-request-submit"));
    error = await within(run).findByTestId("si-run-request-error");
    expect(error.textContent).toContain("帳號不在決定者名單內-夾具");
    expect(error.textContent).toContain("si_write_forbidden");
    await waitFor(() => expect(within(run).getByTestId("si-run-request-submit")).toBeEnabled());
    expect(screen.getByTestId("si-run-request-dialog")).toBe(run);
  });
});

describe("AT_964_6_3 503 si_write_disabled 與 503 si_unavailable 的 cause 與 detail 逐字顯示", () => {
  it("AT_964_6_3 兩種 503 各送出一次：畫面逐字顯示 reason、cause 與 detail；schedule_bounds_unavailable 不被改寫或隱藏；對話框不關", async () => {
    const user = userEvent.setup();
    const replies = [
      () => failure(503, { message: "寫入面已停用-夾具", reason: "si_write_disabled", details: { cause: "audit_key_unset" } }),
      () => failure(503, { message: "SI 資料面不可用-夾具", reason: "si_unavailable", details: { cause: "schedule_bounds_unavailable", detail: "schedule 缺 periodMax-夾具" } }),
    ];
    let n = 0;
    mount(sched(), { "schedule-set": () => replies[n++]() });
    const dialog = await openDialog(user);
    await user.click(submitButton(dialog));
    let error = await within(dialog).findByTestId("si-schedule-error");
    for (const part of ["寫入面已停用-夾具", "si_write_disabled", "audit_key_unset"]) expect(error.textContent, part).toContain(part);
    await waitFor(() => expect(submitButton(dialog)).toBeEnabled());
    await user.click(submitButton(dialog));
    await waitFor(() => expect(within(dialog).getByTestId("si-schedule-error").textContent).toContain("si_unavailable"));
    error = within(dialog).getByTestId("si-schedule-error");
    for (const part of ["SI 資料面不可用-夾具", "si_unavailable", "schedule_bounds_unavailable", "schedule 缺 periodMax-夾具"]) expect(error.textContent, part).toContain(part);
    expect(screen.getByTestId("si-schedule-dialog")).toBe(dialog);
  });
});

describe("AT_964_6_4 422 invalid_request 的 violations 逐項顯示", () => {
  it("AT_964_6_4 兩項 violation：畫面逐項顯示欄名與訊息、對話框不關、表單內容保留", async () => {
    const user = userEvent.setup();
    const violations = [
      { field: "periodMinutes", message: "須在 60～10080 分鐘之間-m1" },
      { field: "reason", message: "reason 不可含控制字元-m2" },
    ];
    mount(sched(), { "schedule-set": () => failure(422, { message: "請求欄位未通過檢查（2 項）", reason: "invalid_request", errors: violations, details: { violations } }) });
    const dialog = await openDialog(user);
    await typePeriod(user, dialog, "200");
    await user.click(submitButton(dialog));
    const error = await within(dialog).findByTestId("si-schedule-error");
    for (const part of ["periodMinutes：須在 60～10080 分鐘之間-m1", "reason：reason 不可含控制字元-m2"]) expect(error.textContent, part).toContain(part);
    expect(screen.getByTestId("si-schedule-dialog")).toBe(dialog);
    expect(periodInput(dialog).value).toBe("200");
  });
});
