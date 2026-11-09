/**
 * 立即啟動對話框的元件測試（TCS-SelfImprovingSchedule：AT-964-4-1／4-2／4-3／4-E-1；W-S4）。
 * 為什麼重要：backend 對「立即啟動」沒有重送閘（連送兩次各得一份稽核檔），防連點與誤重送只靠這個對話框——對帳面板已有待入帳的同類請求時必須停用主鈕；
 * 但停用只能讀既有快取（對話框不發任何新請求），快取缺席、對帳量不到或該筆已入帳時絕不能誤停用，否則掌舵者會被一個假狀態擋住。收據同樣不得宣稱「已啟動」。
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ingestCommands } from "@/lib/domain/si";
import { ADMIN_UI, fixtureWithStatus, renderSi, sched, statusItem, writeItem, type SiStub } from "@/tests/helpers/si";

// 測試環境沒有 App Router：AuthProvider 要的 useRouter 換成穩定的替身
const router = vi.hoisted(() => ({ push: () => undefined, replace: () => undefined, back: () => undefined }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/self-improving",
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));
vi.setConfig({ testTimeout: 30_000 });

type User = ReturnType<typeof userEvent.setup>;
const U1 = "a1000000-0000-4000-8000-0000000000a1";
const posts = (stub: SiStub) => stub.calls.filter((c) => c.method === "POST" && c.path.endsWith("/runs/request"));
const writesGets = (stub: SiStub) => stub.calls.filter((c) => c.method === "GET" && c.path.endsWith("/si/console-writes"));

type Writes = { items: ReturnType<typeof writeItem>[]; status?: "ok" | "NOT-EVALUABLE" };
const writesReply = ({ items, status = "ok" }: Writes) => ({
  data: { items, truncated: false, orphans: status === "ok" ? [] : null, reconcile: { status, reason: status === "ok" ? null : "si_unavailable", backfilled: 0 } },
});

function mount(overrides: SiStub["overrides"] = {}) {
  return renderSi({ ...ADMIN_UI, fixture: fixtureWithStatus(statusItem({ schedule: sched() })), overrides });
}
async function openDialog(user: User) {
  await user.click(await screen.findByTestId("si-run-request-open"));
  return screen.findByTestId("si-run-request-dialog");
}
const submit = (dialog: HTMLElement) => within(dialog).getByTestId("si-run-request-submit") as HTMLButtonElement;

describe("AT_964_4_1 送出的請求本文與收據、入帳指令、待入帳文案", () => {
  it("AT_964_4_1 備註一行送出：本文為 { note }；收據顯示稽核檔已落地，待入帳（不含已啟動字樣）與 run-open 入帳指令；備註留空再送本文為 {}", async () => {
    const user = userEvent.setup();
    const view = mount();
    let dialog = await openDialog(user);
    expect(within(dialog).getByTestId("si-run-request-summary").textContent).toContain("黑窗");
    await user.type(within(dialog).getByTestId("si-run-request-note"), "先跑一次看看");
    await user.click(submit(dialog));
    const result = await within(dialog).findByTestId("si-run-request-result");
    expect(posts(view.stub)).toHaveLength(1);
    expect(posts(view.stub)[0].path).toBe("/api/v1/si/runs/request");
    expect(posts(view.stub)[0].body).toBe(JSON.stringify({ note: "先跑一次看看" }));
    expect(result.textContent).toContain("稽核檔已落地，待入帳");
    expect(result.textContent).not.toMatch(/已生效|已啟用|已啟動/);
    const ref = within(result).getByTestId("si-audit-ref").textContent as string;
    expect(within(result).getByTestId("si-receipt-kind").textContent).toBe("run-request");
    const cmd = `python tools/selfimproving.py run-open --trigger a --carrier console --audit-ref ${ref} --coord console_audit/${ref}.json --by console`;
    expect(ingestCommands("run-request", null, ref).posix).toBe(cmd);
    expect(within(result).getAllByText(cmd), "兩個 shell 同一字串").toHaveLength(2);
    expect(within(result).getByTestId("si-receipt-extra").textContent).toContain("15");

    const closeBtn = within(dialog)
      .getAllByRole("button", { name: "關閉" })
      .find((b) => b.textContent === "關閉") as HTMLElement;
    await user.click(closeBtn);
    dialog = await openDialog(user);
    await user.click(submit(dialog));
    await within(dialog).findByTestId("si-run-request-result");
    expect(posts(view.stub)[1].body, "備註留空本文為空物件").toBe("{}");
  });
});

describe("AT_964_4_2 對帳快取有待入帳的 run-request：主鈕停用並顯示稽核編號", () => {
  it("AT_964_4_2 對帳回一筆 ingested 為 false 的 run-request、reconcile ok：主鈕 disabled，顯示 已送出待入帳（稽核編號 …）；備註欄仍可編輯、取消鈕可用", async () => {
    const user = userEvent.setup();
    mount({ "console-writes": () => writesReply({ items: [writeItem({ auditRef: U1, kind: "run-request", ingested: false })] }) });
    await within(await screen.findByTestId("si-writes-panel")).findByTestId(`si-pending-${U1}`);
    const dialog = await openDialog(user);
    expect(submit(dialog)).toBeDisabled();
    expect(within(dialog).getByTestId("si-run-request-dup").textContent).toBe(`已送出待入帳（稽核編號 ${U1}）`);
    const note = within(dialog).getByTestId("si-run-request-note") as HTMLInputElement;
    await user.type(note, "還能打字");
    expect(note.value).toBe("還能打字");
    expect(within(dialog).getByRole("button", { name: "取消" })).toBeEnabled();
  });
});

describe("AT_964_4_3 快取缺席、對帳量不到、已入帳、只有 sched-set 待入帳：皆不停用", () => {
  it.each([
    ["無該查詢快取（對帳請求還沒回來）", () => new Promise<never>(() => undefined)],
    ["reconcile 為 NOT-EVALUABLE（即使有列）", () => writesReply({ status: "NOT-EVALUABLE", items: [writeItem({ auditRef: U1, kind: "run-request", ingested: null })] })],
    ["run-request 已入帳", () => writesReply({ items: [writeItem({ auditRef: U1, kind: "run-request", ingested: true })] })],
    ["只有 sched-set 待入帳", () => writesReply({ items: [writeItem({ auditRef: U1, kind: "sched-set", ingested: false })] })],
  ] as Array<[string, () => unknown]>)("AT_964_4_3 %s", async (_name, reply) => {
    const user = userEvent.setup();
    const view = mount({ "console-writes": reply as SiStub["overrides"]["console-writes"] });
    await waitFor(() => expect(writesGets(view.stub).length).toBeGreaterThanOrEqual(1));
    if (_name.startsWith("reconcile")) await within(await screen.findByTestId("si-writes-panel")).findByTestId("si-reconcile-ne");
    if (_name.startsWith("run-request 已入帳") || _name.startsWith("只有"))
      await within(await screen.findByTestId("si-writes-panel")).findByTestId(_name.startsWith("只有") ? `si-pending-${U1}` : "si-writes-empty");
    const dialog = await openDialog(user);
    expect(submit(dialog)).toBeEnabled();
    expect(within(dialog).queryByTestId("si-run-request-dup")).toBeNull();
    expect(dialog.textContent).not.toContain("已送出待入帳");
  });
});

describe("AT_964_4_E_1 軟停用只讀快取：開啟對話框前後 console-writes 的 GET 次數不變", () => {
  it("AT_964_4_E_1 對帳面板已載入一次後，開啟、關閉、再開啟兩次：GET 仍為一次；對話框 import 的快取 hook 名稱不以寫入動詞前綴起頭", async () => {
    const user = userEvent.setup();
    const view = mount({ "console-writes": () => writesReply({ items: [] }) });
    await within(await screen.findByTestId("si-writes-panel")).findByTestId("si-writes-empty");
    expect(writesGets(view.stub)).toHaveLength(1);
    let dialog = await openDialog(user);
    await user.click(within(dialog).getByRole("button", { name: "取消" }));
    await waitFor(() => expect(screen.queryByTestId("si-run-request-dialog")).toBeNull());
    dialog = await openDialog(user);
    await user.click(within(dialog).getByRole("button", { name: "取消" }));
    await openDialog(user);
    expect(writesGets(view.stub), "對話框只讀快取、不發新請求").toHaveLength(1);

    const source = readFileSync(path.join(process.cwd(), "components", "domain", "si", "SiRunRequestDialog.tsx"), "utf-8");
    const imported =
      /import\s*\{([^}]*)\}\s*from\s*"@\/lib\/api\/queries"/
        .exec(source)?.[1]
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean) ?? [];
    expect(imported).toContain("useSiConsoleWritesCache");
    const WRITE_PREFIX = /^use(Create|Update|Delete|Post|Put|Patch|Retry|Approve|Signoff|Execute|Si(Create|Update|Delete|Post|Put|Patch|Retry|Approve|Signoff|Execute))/;
    expect(imported.filter((n) => WRITE_PREFIX.test(n))).toEqual(["usePostSiRunRequest"]);
    expect("useSiConsoleWritesCache").not.toMatch(WRITE_PREFIX);
  });
});
