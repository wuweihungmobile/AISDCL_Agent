/**
 * 關閉觀察對話框的元件測試（TCS-SelfImprovingDecide-P2b：AT-935-2-2／2-E-1；W17、W20；表 M-C）。
 * 為什麼重要：關閉＝把觀察列的處置從 open 改成終值，是帳本裡唯一會「改既有列」的寫入。終值與附加欄位（ref 或 text）的組合錯了，
 * 入帳後該列的處置文法就不合（`check` 轉紅）；而且稽核檔簽章落地後無法撤回。所以七個終值的欄位與本文、以及每一種違規（open 不可選、
 * 必填文字、ref 格式、豎線與「之後再看」、長度上限）都要在送出前擋下。根層 ref.obs 會掃整個 repo 的 OBS／PROP 號字面：不在帳本的壞號一律執行期組字串。
 */
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ingestCommands } from "@/lib/domain/si";
import type { SiObservation } from "@/lib/api/types";
import { GA, renderSi, type SiStub } from "@/tests/helpers/si";

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

type User = ReturnType<typeof userEvent.setup>;
const OBS = "OBS-SI-005";
const obsId = (digits: string) => `OBS-SI-${digits}`;
const propId = (digits: string) => `PROP-SI-${digits}`;

const posts = (stub: SiStub) => stub.calls.filter((c) => c.method === "POST");
const optionValues = (select: HTMLElement) => Array.from(select.querySelectorAll("option")).map((o) => o.getAttribute("value") ?? "");

async function setField(user: User, dialog: HTMLElement, testId: string, text: string) {
  const el = within(dialog).getByTestId(testId);
  await user.clear(el);
  if (text !== "") {
    await user.click(el);
    await user.paste(text);
  }
}

/** 以 ADMIN 對處置為 open 的 OBS-SI-005 開啟關閉對話框。 */
async function openClose(user: User) {
  await user.click(await screen.findByTestId(`si-close-open-${OBS}`));
  return screen.findByTestId("si-obs-close-dialog");
}

describe("AT_935_2_2 關閉對話框：七個終值、各自欄位與送出本文", () => {
  const M_C: Array<[terminal: string, field: "ref" | "text", value: string]> = [
    ["fixed", "ref", "2b2b0b3d"],
    ["def", "ref", "DEF-200-559"],
    ["deferred", "text", "等 P3 輪"],
    ["retired", "text", "docs/06_quality/SelfImproving_Protocol/params.json"],
    ["decided", "text", "夾具關閉"],
    ["merged", "ref", "OBS-SI-001"],
    ["proposed", "ref", "PROP-SI-004"],
  ];

  it("AT_935_2_2 終值下拉恰七項且無 open；七個終值各填欄後送出：POST 網址為 /api/v1/si/observations/OBS-SI-005/close，本文為 {terminal, ref|text}（鍵序與值逐項如表 M-C）；缺必填欄時送出鈕停用", async () => {
    const user = userEvent.setup();
    const view = renderSi({ role: "ADMIN", username: "admin" });
    await screen.findByTestId("si-obs-table");
    for (const [index, [terminal, field, value]] of M_C.entries()) {
      const dialog = await openClose(user);
      const select = within(dialog).getByTestId("si-close-terminal");
      expect(
        optionValues(select).filter((v) => v !== ""),
        "七個終值、沒有 open",
      ).toEqual(["fixed", "def", "deferred", "retired", "decided", "merged", "proposed"]);
      const submit = within(dialog).getByTestId("si-close-submit");
      expect(submit, "未選終值").toBeDisabled();
      expect(within(dialog).getByTestId("si-close-blocked")).toHaveTextContent("請選擇終值");

      await user.selectOptions(select, terminal);
      // 只有該終值需要的那一欄存在
      expect(within(dialog).queryByTestId("si-close-ref") !== null, `${terminal} 的 ref 欄`).toBe(field === "ref");
      expect(within(dialog).queryByTestId("si-close-text") !== null, `${terminal} 的 text 欄`).toBe(field === "text");
      expect(submit, `${terminal} 缺必填欄`).toBeDisabled();
      await setField(user, dialog, `si-close-${field}`, value);
      expect(submit, `${terminal} 填妥`).toBeEnabled();

      await user.click(submit);
      await waitFor(() => expect(posts(view.stub)).toHaveLength(index + 1));
      const call = posts(view.stub)[index];
      expect(call.path).toBe(`/api/v1/si/observations/${OBS}/close`);
      expect(call.body, terminal).toBe(JSON.stringify({ terminal, [field]: value }));
      const result = await within(dialog).findByTestId("si-close-result");
      const auditRef = `a1000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`;
      expect(result).toHaveTextContent(auditRef);
      expect(result).toHaveTextContent("待入帳");
      expect(within(result).getByTestId("sdd-recovery-command-powershell").textContent).toBe(ingestCommands("obs-close", OBS, auditRef).powershell);
      expect(screen.getByTestId("si-obs-close-dialog"), "不自動關閉").toBeInTheDocument();
      const closers = within(dialog).getAllByRole("button", { name: "關閉" });
      await user.click(closers[closers.length - 1]);
      await waitFor(() => expect(screen.queryByTestId("si-obs-close-dialog")).toBeNull());
    }
    expect(posts(view.stub)).toHaveLength(7);
  });

  it("AT_935_2_2 只對處置恰為 open 的有效列提供關閉入口；其餘列沒有關閉鈕（仍有更正鈕）；沒有 open 之外的處置被誤判成 open（decided、deferred、merged 開頭的處置）", async () => {
    renderSi({ role: "ADMIN", username: "admin" });
    const table = await screen.findByTestId("si-obs-table");
    const valid = GA.observations.items.filter((r): r is SiObservation => r.valid !== false);
    const open = valid.filter((r) => r.disposition === "open").map((r) => r.id);
    expect(open, "夾具有 open 與非 open 兩類列").toEqual(["OBS-SI-005", "OBS-SI-007", "OBS-SI-009"]);
    expect(valid.length - open.length).toBeGreaterThan(5);
    const closers = Array.from(table.querySelectorAll<HTMLElement>('[data-testid^="si-close-open-"]')).map((el) => el.dataset.testid?.replace("si-close-open-", ""));
    expect(closers).toEqual(open);
    for (const row of valid.filter((r) => r.disposition !== "open")) {
      expect(within(table).queryByTestId(`si-close-open-${row.id}`), `${row.id}（${row.disposition.slice(0, 12)}）不得有關閉鈕`).toBeNull();
      expect(within(table).getByTestId(`si-obs-correct-${row.id}`), `${row.id} 仍可更正`).toBeInTheDocument();
    }
  });
});

describe("AT_935_2_E_1 關閉驗證：open 不可選、必填文字、ref 格式、豎線與之後再看", () => {
  it("AT_935_2_E_1 text 為空、含豎線、含「之後再看」、含換行、121 個字元：各自在欄位下顯示錯誤且送出鈕停用、零請求；恰 120 個字元與合格文字解除停用", async () => {
    const user = userEvent.setup();
    const view = renderSi({ role: "ADMIN", username: "admin" });
    await screen.findByTestId("si-obs-table");
    const dialog = await openClose(user);
    await user.selectOptions(within(dialog).getByTestId("si-close-terminal"), "decided");
    const submit = within(dialog).getByTestId("si-close-submit");
    for (const [label, text, hint] of [
      ["空白", "   ", "必填"],
      ["豎線", "含|豎線", "豎線"],
      ["之後再看", "等一下之後再看看", "之後再看"],
      ["換行", "第一行\n第二行", "控制字元"],
      ["121 個字元", "字".repeat(121), "121"],
    ] as const) {
      await setField(user, dialog, "si-close-text", text);
      expect(submit, label).toBeDisabled();
      expect(
        within(dialog)
          .getAllByRole("alert")
          .some((a) => (a.textContent ?? "").includes(hint)),
        `${label}：欄位下的錯誤`,
      ).toBe(true);
    }
    expect(posts(view.stub), "零請求").toHaveLength(0);
    await setField(user, dialog, "si-close-text", "字".repeat(120));
    expect(submit, "恰 120 個字元").toBeEnabled();
    await setField(user, dialog, "si-close-text", "夾具關閉");
    expect(submit).toBeEnabled();
    expect(within(dialog).queryAllByRole("alert")).toHaveLength(0);
  });

  it("AT_935_2_E_1 ref 不合格式：fixed（過短、大寫、非十六進位、過長）、def、merged、proposed 各自停用且零請求；合格式解除停用；換終值時殘值被清掉", async () => {
    const user = userEvent.setup();
    const view = renderSi({ role: "ADMIN", username: "admin" });
    await screen.findByTestId("si-obs-table");
    const dialog = await openClose(user);
    const select = within(dialog).getByTestId("si-close-terminal");
    const submit = within(dialog).getByTestId("si-close-submit");
    const CASES: Array<[terminal: string, bad: string[], good: string]> = [
      ["fixed", ["2b2b0b", "2B2B0B3D", "ghijklmn", "a".repeat(41)], "2b2b0b3d"],
      ["def", ["DEF-200", "def-200-559", "DEF-x-1"], "DEF-200-559"],
      ["merged", [obsId("01"), "OBS-SI-ABC", propId("004")], "OBS-SI-001"],
      ["proposed", [propId("04"), "PROP-SI-X", "OBS-SI-001"], "PROP-SI-004"],
    ];
    for (const [terminal, bad, good] of CASES) {
      await user.selectOptions(select, terminal);
      expect(within(dialog).getByTestId("si-close-ref"), "換終值清掉殘值").toHaveValue("");
      for (const ref of bad) {
        await setField(user, dialog, "si-close-ref", ref);
        expect(submit, `${terminal}＝${ref}`).toBeDisabled();
        expect(within(dialog).getAllByRole("alert").length, `${terminal}＝${ref} 有錯誤字樣`).toBeGreaterThan(0);
      }
      await setField(user, dialog, "si-close-ref", good);
      expect(submit, `${terminal}＝${good}`).toBeEnabled();
    }
    expect(posts(view.stub)).toHaveLength(0);
  });

  it("AT_935_2_E_1 終值沒有 open 這個選項；改選另一類終值時前一類的欄位消失（ref 與 text 恰擇一）", async () => {
    const user = userEvent.setup();
    renderSi({ role: "ADMIN", username: "admin" });
    await screen.findByTestId("si-obs-table");
    const dialog = await openClose(user);
    const select = within(dialog).getByTestId("si-close-terminal");
    expect(optionValues(select)).not.toContain("open");
    await user.selectOptions(select, "fixed");
    await setField(user, dialog, "si-close-ref", "2b2b0b3d");
    await user.selectOptions(select, "decided");
    expect(within(dialog).queryByTestId("si-close-ref")).toBeNull();
    expect(within(dialog).getByTestId("si-close-text")).toHaveValue("");
    expect(within(dialog).getByTestId("si-close-submit"), "換終值後必填欄是空的").toBeDisabled();
  });
});
