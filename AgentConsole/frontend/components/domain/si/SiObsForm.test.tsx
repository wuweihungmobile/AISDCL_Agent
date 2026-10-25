/**
 * 新增觀察與更正表單的元件測試（TCS-SelfImprovingDecide-P2b：AT-935-1-1／1-2／1-E-1／1-E-2、AT-935-2-1、AT-950-9-3／9-E-3；W17、W19）。
 * 為什麼重要：觀察列是 Markdown 九欄表——欄位裡多一根豎線或一個換行，入帳後帳本就多一個壞列、`check` 轉紅，而且稽核檔已簽章落地、無法撤回。
 * 所以這支檔把「不讓必敗的輸入走到簽章」的每一道關都釘住：即時拒收（豎線、控制字元、空白必填欄、列舉外值）、先預檢再寫入（預檢不通過一個寫入 POST 都不送）、
 * 預檢結果以純文字呈現（detail 含 script 字樣也不執行）、邊打邊估的位元組數與真 CLI 預覽的 row_bytes 對得上，以及連點只送一次。
 */
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { estimateRowBytes, ingestCommands, type ObservationForm } from "@/lib/domain/si";
import { failure } from "@/tests/helpers/api";
import { VALIDATE_ROW, renderSi, type SiStub } from "@/tests/helpers/si";

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

/** TCS §5.2 的 O1（＝黃金檔 G3 的輸入）。 */
const O1 = {
  context: "Console・自我進化頁",
  symptom: "待入帳徽章在入帳後仍顯示",
  evidence: "AgentConsole/frontend/components/domain/si/SiView.tsx:88",
  category: "bug",
  severity: "P3",
  face: "產品",
};
const O1_BODY = JSON.stringify({ ...O1, externalDerived: false });

const posts = (stub: SiStub) => stub.calls.filter((c) => c.method === "POST");
const toastText = () => document.querySelector('[data-slot="toast-host"]')?.textContent ?? "";
const consoleWriteGets = (stub: SiStub) => stub.calls.filter((c) => c.method === "GET" && c.path === "/api/v1/si/console-writes").length;

/** 貼上文字（不逐字打：長字串與換行、TAB 才能原樣進欄位）；先清空。 */
async function setField(user: User, dialog: HTMLElement, testId: string, text: string) {
  const el = within(dialog).getByTestId(testId);
  await user.clear(el);
  if (text !== "") {
    await user.click(el);
    await user.paste(text);
  }
}

async function fillO1(user: User, dialog: HTMLElement, over: Partial<typeof O1> = {}) {
  const v = { ...O1, ...over };
  await setField(user, dialog, "si-obs-context", v.context);
  await setField(user, dialog, "si-obs-symptom", v.symptom);
  await setField(user, dialog, "si-obs-evidence", v.evidence);
  await user.selectOptions(within(dialog).getByTestId("si-obs-category"), v.category);
  await user.selectOptions(within(dialog).getByTestId("si-obs-severity"), v.severity);
  await user.selectOptions(within(dialog).getByTestId("si-obs-face"), v.face);
}

/** 以 ADMIN 開啟「新增觀察」（觀察分頁的工具列）。 */
async function openNew(user: User, overrides: SiStub["overrides"] = {}) {
  const view = renderSi({ role: "ADMIN", username: "admin", overrides });
  await screen.findByTestId("si-obs-table");
  await user.click(screen.getByTestId("si-obs-new"));
  const dialog = await screen.findByTestId("si-obs-dialog");
  return { ...view, dialog };
}

const optionValues = (select: HTMLElement) => Array.from(select.querySelectorAll("option")).map((o) => o.getAttribute("value") ?? "");

describe("AT_935_1_1 新增觀察表單：欄位與列舉、守衛面暴露，送出前先 validate 並顯示預估位元組", () => {
  it("AT_935_1_1 填六欄與列舉（face 為產品）後送出：依序一個 validate POST 與一個 /api/v1/si/observations POST，本文逐欄等於輸入（externalDerived 預設 false、無 exposure）；預覽列顯示 row、287 與 700", async () => {
    const user = userEvent.setup();
    const { stub, dialog } = await openNew(user);
    expect(within(dialog).queryByTestId("si-obs-exposure"), "非守衛面沒有暴露度").toBeNull();
    expect(within(dialog).queryByTestId("si-obs-corrects"), "新增模式沒有更正欄").toBeNull();
    await fillO1(user, dialog);
    expect(within(dialog).getByTestId("si-obs-external")).toHaveAttribute("aria-checked", "false");
    const submit = within(dialog).getByTestId("si-obs-submit");
    expect(submit).toBeEnabled();
    expect(posts(stub), "填寫途中零個 POST").toHaveLength(0);

    await user.click(submit);
    await within(dialog).findByTestId("si-obs-result");

    expect(posts(stub).map((c) => c.path)).toEqual(["/api/v1/si/observations/validate", "/api/v1/si/observations"]);
    expect(posts(stub)[0].body, "預檢與寫入送同一份本文").toBe(O1_BODY);
    expect(posts(stub)[1].body).toBe(O1_BODY);
    expect(JSON.parse(posts(stub)[1].body as string)).not.toHaveProperty("exposure");
    const preview = within(dialog).getByTestId("si-obs-preview");
    expect(preview).toHaveTextContent(VALIDATE_ROW);
    expect(preview).toHaveTextContent("287");
    expect(preview).toHaveTextContent("700");
  });

  it("AT_935_1_1 face 改為守衛：暴露度下拉出現且必填（缺則停用、說明原因），選定後本文帶 exposure；換回非守衛面則暴露度消失且不送", async () => {
    const user = userEvent.setup();
    const { stub, dialog } = await openNew(user);
    await fillO1(user, dialog, { face: "守衛", severity: "P2" });
    const exposure = within(dialog).getByTestId("si-obs-exposure");
    expect(optionValues(exposure).filter((v) => v !== "")).toEqual(["a", "b", "c", "無"]);
    expect(within(dialog).getByTestId("si-obs-submit")).toBeDisabled();
    expect(within(dialog).getByTestId("si-obs-blocked")).toHaveTextContent("暴露度");

    // 先選 b 再換回產品面：暴露度欄消失、值被清掉
    await user.selectOptions(exposure, "b");
    await user.selectOptions(within(dialog).getByTestId("si-obs-face"), "產品");
    expect(within(dialog).queryByTestId("si-obs-exposure")).toBeNull();
    await user.selectOptions(within(dialog).getByTestId("si-obs-face"), "守衛");
    expect(within(dialog).getByTestId("si-obs-exposure")).toHaveValue("");
    expect(within(dialog).getByTestId("si-obs-submit"), "殘值已清，仍要重選").toBeDisabled();

    await user.selectOptions(within(dialog).getByTestId("si-obs-exposure"), "b");
    await user.click(within(dialog).getByTestId("si-obs-external"));
    await user.click(within(dialog).getByTestId("si-obs-submit"));
    await within(dialog).findByTestId("si-obs-result");
    const body = JSON.parse(posts(stub)[1].body as string);
    expect(body).toEqual({ ...O1, severity: "P2", face: "守衛", exposure: "b", externalDerived: true });
    expect(Object.keys(body)).toEqual(["context", "symptom", "evidence", "category", "severity", "face", "exposure", "externalDerived"]);
  });

  it("AT_935_1_1 預檢回 422 或 503：toast 顯示原因逐字、一個寫入 POST 都不送、對話框不關、表單仍可改後重送", async () => {
    const user = userEvent.setup();
    const replies = [
      () => failure(503, { message: "SI 資料面不可用", reason: "si_unavailable", details: { cause: "nonzero_rc", detail: "rc=2; stderr=boom" } }),
      () =>
        failure(422, {
          message: "請求欄位未通過檢查（1 項）",
          reason: "invalid_request",
          errors: [{ field: "evidence", message: "證據座標不合" }],
          details: { violations: [{ field: "evidence", message: "證據座標不合" }] },
        }),
    ];
    let served = 0;
    const { stub, dialog } = await openNew(user, { validate: () => replies[served++]() });
    await fillO1(user, dialog);
    for (const [index, expected] of [
      ["si_unavailable", "nonzero_rc"],
      ["invalid_request", "證據座標不合"],
    ].entries()) {
      await user.click(within(dialog).getByTestId("si-obs-submit"));
      await waitFor(() => expect(toastText()).toContain(expected[0]));
      expect(toastText()).toContain(expected[1]);
      expect(
        posts(stub).filter((c) => c.path === "/api/v1/si/observations"),
        `第 ${index + 1} 次：沒有寫入 POST`,
      ).toHaveLength(0);
      expect(screen.getByTestId("si-obs-dialog")).toBeInTheDocument();
      await waitFor(() => expect(within(dialog).getByTestId("si-obs-submit")).toBeEnabled());
    }
  });
});

describe("AT_935_1_2 送出成功顯示待入帳與入帳指令，並重取對帳資料", () => {
  it("AT_935_1_2 收據含 auditRef 與兩個 CopyCommand，指令逐字等於 ingestCommands(obs-add, null, auditRef)；請求中送出鈕停用；成功後恰多一個 console-writes GET（預檢不觸發重取）", async () => {
    const user = userEvent.setup();
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const { stub, dialog } = await openNew(user, {
      validate: async () => {
        await gate;
        return undefined; // 放行後照預設回放
      },
    });
    await waitFor(() => expect(consoleWriteGets(stub)).toBe(1));
    await fillO1(user, dialog);
    const submit = within(dialog).getByTestId("si-obs-submit");
    await user.click(submit);
    await waitFor(() => expect(submit, "請求中停用").toBeDisabled());
    expect(consoleWriteGets(stub), "預檢送出途中不重取對帳").toBe(1);
    release?.();

    const result = await within(dialog).findByTestId("si-obs-result");
    const auditRef = "a1000000-0000-4000-8000-000000000001";
    expect(result).toHaveTextContent(auditRef);
    expect(result).toHaveTextContent("待入帳");
    const expected = ingestCommands("obs-add", null, auditRef);
    expect(within(result).getByTestId("sdd-recovery-command-powershell").textContent).toBe(expected.powershell);
    expect(within(result).getByTestId("sdd-recovery-command-posix").textContent).toBe(expected.posix);
    expect(expected.powershell).toBe(`python tools/selfimproving.py obs-add --carrier console --audit-ref ${auditRef}`);
    await waitFor(() => expect(consoleWriteGets(stub)).toBe(2));
    await new Promise((resolve) => setTimeout(resolve, 60));
    expect(consoleWriteGets(stub), "成功後恰多一個，不是兩個").toBe(2);
    // 收據之後表單收起：同一份內容不會被誤送出第二次；預覽列留在收據上方
    expect(within(dialog).queryByTestId("si-obs-submit")).toBeNull();
    expect(within(dialog).getByTestId("si-obs-preview")).toBeInTheDocument();
    expect(screen.getByTestId("si-obs-dialog"), "不自動關閉").toBeInTheDocument();
  });

  it("AT_935_1_2 連點送出鈕只送一次（預檢加寫入各一個 POST）", async () => {
    const user = userEvent.setup({ delay: null });
    const { stub, dialog } = await openNew(user);
    await fillO1(user, dialog);
    await user.dblClick(within(dialog).getByTestId("si-obs-submit"));
    await within(dialog).findByTestId("si-obs-result");
    expect(posts(stub).map((c) => c.path)).toEqual(["/api/v1/si/observations/validate", "/api/v1/si/observations"]);
  });
});

describe("AT_935_1_E_1 即時拒收：豎線與控制字元、空白必填欄、列舉外值", () => {
  it("AT_935_1_E_1 字串欄的豎線、貼上的換行與 TAB 立即在欄位下顯示錯誤（各一種），空白必填欄各有錯誤，送出鈕停用且零請求；三個下拉只有表 M-O 的選項", async () => {
    const user = userEvent.setup();
    const { stub, dialog } = await openNew(user);
    const submit = within(dialog).getByTestId("si-obs-submit");
    expect(submit, "第一次輸入前就停用，但還沒有滿版紅字").toBeDisabled();
    expect(within(dialog).queryAllByRole("alert")).toHaveLength(0);

    await setField(user, dialog, "si-obs-symptom", "含|豎線");
    await setField(user, dialog, "si-obs-evidence", "第一行\n第二行\tTAB");
    // context 留空白
    const alerts = within(dialog)
      .getAllByRole("alert")
      .map((a) => a.textContent ?? "");
    expect(
      alerts.some((t) => t.includes("症狀") && t.includes("豎線")),
      alerts.join("｜"),
    ).toBe(true);
    expect(
      alerts.some((t) => t.includes("證據座標") && t.includes("控制字元")),
      alerts.join("｜"),
    ).toBe(true);
    expect(
      alerts.some((t) => t.includes("情境") && t.includes("必填")),
      alerts.join("｜"),
    ).toBe(true);
    for (const select of ["si-obs-category", "si-obs-severity", "si-obs-face"]) {
      expect(
        alerts.some((t) => t.includes(select === "si-obs-category" ? "分類" : select === "si-obs-severity" ? "嚴重度" : "面")),
        `${select} 的必填錯誤`,
      ).toBe(true);
    }
    expect(submit).toBeDisabled();
    expect(posts(stub), "零請求（含預檢）").toHaveLength(0);

    expect(optionValues(within(dialog).getByTestId("si-obs-category")).filter((v) => v !== "")).toEqual(["process", "bug", "tooling", "doc", "decision"]);
    expect(optionValues(within(dialog).getByTestId("si-obs-severity")).filter((v) => v !== "")).toEqual(["P1", "P2", "P3", "P4"]);
    expect(optionValues(within(dialog).getByTestId("si-obs-face")).filter((v) => v !== "")).toEqual(["守衛", "產品", "文件", "流程"]);

    // 改正之後錯誤消失、可送出
    await fillO1(user, dialog);
    expect(within(dialog).queryAllByRole("alert")).toHaveLength(0);
    expect(submit).toBeEnabled();
  });

  it("AT_935_1_E_1 全空白的必填欄與首尾換行也拒收；每個字串欄 300 個字元通過、301 個報錯", async () => {
    const user = userEvent.setup();
    const { dialog } = await openNew(user);
    await fillO1(user, dialog);
    const submit = within(dialog).getByTestId("si-obs-submit");
    for (const field of ["si-obs-context", "si-obs-symptom", "si-obs-evidence"]) {
      await setField(user, dialog, field, "   ");
      expect(submit, `${field} 全空白`).toBeDisabled();
      await setField(user, dialog, field, "\n開頭換行");
      expect(submit, `${field} 首尾換行`).toBeDisabled();
      await setField(user, dialog, field, "字".repeat(301));
      expect(submit, `${field} 301 個字元`).toBeDisabled();
      expect(
        within(dialog)
          .getAllByRole("alert")
          .some((a) => (a.textContent ?? "").includes("301")),
      ).toBe(true);
      await setField(user, dialog, field, "x");
      expect(submit, `${field} 恢復正常`).toBeEnabled();
    }
  });
});

describe("AT_935_1_E_2 validate 回 ok=false 時不送出：findings 逐字、純文字渲染", () => {
  it("AT_935_1_E_2 第一次零個 /api/v1/si/observations POST；si-obs-findings 逐筆顯示 code 與 detail 的字面文字（含 script 標籤字樣不執行）；預覽仍顯示 row 與位元組；改正且替身回 ok 後再送得一個寫入 POST", async () => {
    const user = userEvent.setup();
    const findings = [
      { code: "COORD-NONE", detail: "證據欄沒有可定位的座標" },
      { code: "PIPE-IN-FIELD", detail: "<script>window.__si_xss = 1</script> 與 **粗體** 與 &amp; 都是字面文字" },
    ];
    let ok = false;
    const { stub, dialog } = await openNew(user, {
      validate: () => ({ data: ok ? { ok: true, row: VALIDATE_ROW, rowBytes: 287, rowMaxBytes: 700, findings: [] } : { ok: false, row: VALIDATE_ROW, rowBytes: 287, rowMaxBytes: 700, findings } }),
    });
    await fillO1(user, dialog);
    await user.click(within(dialog).getByTestId("si-obs-submit"));

    const box = await within(dialog).findByTestId("si-obs-findings");
    expect(
      posts(stub).map((c) => c.path),
      "預檢不通過：只有預檢 POST",
    ).toEqual(["/api/v1/si/observations/validate"]);
    for (const f of findings) {
      expect(box).toHaveTextContent(f.code);
      expect(box.textContent, "detail 逐字").toContain(f.detail);
    }
    expect(box.querySelector("script"), "不執行、不轉成元素").toBeNull();
    expect(box.querySelector("strong, b"), "不轉 Markdown").toBeNull();
    expect((window as unknown as Record<string, unknown>).__si_xss).toBeUndefined();
    const preview = within(dialog).getByTestId("si-obs-preview");
    expect(preview).toHaveTextContent(VALIDATE_ROW);
    expect(preview).toHaveTextContent("287");
    expect(within(dialog).queryByTestId("si-obs-result")).toBeNull();

    ok = true;
    await setField(user, dialog, "si-obs-evidence", "docs/06_quality/SelfImproving_Protocol/params.json:1");
    await user.click(within(dialog).getByTestId("si-obs-submit"));
    await within(dialog).findByTestId("si-obs-result");
    expect(posts(stub).filter((c) => c.path === "/api/v1/si/observations")).toHaveLength(1);
    expect(within(dialog).queryByTestId("si-obs-findings"), "通過後不再顯示舊 findings").toBeNull();
  });
});

describe("AT_935_2_1 更正列：從觀察列開啟，corrects 預填且唯讀，本文帶 corrects", () => {
  it("AT_935_2_1 按 si-obs-correct-OBS-SI-001：corrects 預填且唯讀、打字不改變；本文含 corrects（鍵序同黃金檔 G4）；壞列（無 id）沒有更正鈕，每個有效列都有", async () => {
    const user = userEvent.setup();
    const view = renderSi({ role: "ADMIN", username: "admin" });
    const table = await screen.findByTestId("si-obs-table");
    const validRows = Array.from(table.querySelectorAll('[data-testid^="si-obs-row-"]')).map((r) => (r as HTMLElement).dataset.testid?.replace("si-obs-row-", "") as string);
    expect(validRows).toHaveLength(11);
    for (const id of validRows) expect(within(table).getByTestId(`si-obs-correct-${id}`), id).toBeInTheDocument();
    expect(table.querySelectorAll('[data-testid^="si-obs-correct-"]')).toHaveLength(11);
    const bad = table.querySelector('[data-testid^="si-obs-invalid-"]') as HTMLElement;
    expect(bad, "夾具有一個壞列").not.toBeNull();
    expect(within(bad).queryByRole("button"), "壞列沒有任何操作鈕").toBeNull();

    await user.click(within(table).getByTestId("si-obs-correct-OBS-SI-001"));
    const dialog = await screen.findByTestId("si-obs-dialog");
    const corrects = within(dialog).getByTestId("si-obs-corrects");
    expect(corrects).toHaveValue("OBS-SI-001");
    expect(corrects).toHaveAttribute("readonly");
    await user.type(corrects, "x");
    expect(corrects, "唯讀：打字不改變").toHaveValue("OBS-SI-001");
    expect(dialog).toHaveTextContent("更正觀察：OBS-SI-001");

    await fillO1(user, dialog);
    await user.click(within(dialog).getByTestId("si-obs-submit"));
    await within(dialog).findByTestId("si-obs-result");
    expect(posts(view.stub)[1].body).toBe(JSON.stringify({ ...O1, externalDerived: false, corrects: "OBS-SI-001" }));
    expect(posts(view.stub)[0].body, "預檢也帶 corrects").toBe(posts(view.stub)[1].body);
  });
});

describe("AT_950_9_3 estimateRowBytes：表單邊打邊顯示估計值與 row_max_bytes，與真 CLI 預覽的 row_bytes 對得上", () => {
  const readEstimate = (dialog: HTMLElement) => {
    const m = /預估入帳列 (\d+) 位元組／上限 (\d+)/.exec(within(dialog).getByTestId("si-obs-estimate").textContent ?? "");
    return m ? { bytes: Number(m[1]), max: Number(m[2]) } : null;
  };

  it("AT_950_9_3 逐欄輸入 O1：每次輸入後 si-obs-estimate 隨之更新且同時顯示上限 700，輸入途中零個網路請求；全部填好是 287；送出後預覽的 rowBytes 等於估計值，預檢回 ok 之後才發出寫入 POST", async () => {
    const user = userEvent.setup();
    const { stub, dialog } = await openNew(user);
    const before = stub.calls.length;
    const seen: number[] = [];
    const initial = readEstimate(dialog);
    expect(initial?.max, "第一次預檢前的上限用 700").toBe(700);
    seen.push(initial?.bytes ?? -1);
    for (const [field, value] of [
      ["si-obs-context", O1.context],
      ["si-obs-symptom", O1.symptom],
      ["si-obs-evidence", O1.evidence],
    ] as const) {
      await setField(user, dialog, field, value);
      seen.push(readEstimate(dialog)?.bytes ?? -1);
    }
    for (const [field, value] of [
      ["si-obs-category", O1.category],
      ["si-obs-severity", O1.severity],
      ["si-obs-face", O1.face],
    ] as const) {
      await user.selectOptions(within(dialog).getByTestId(field), value);
      seen.push(readEstimate(dialog)?.bytes ?? -1);
    }
    expect(
      seen.every((n) => n > 0),
      JSON.stringify(seen),
    ).toBe(true);
    expect(
      [...seen].sort((a, b) => a - b),
      "每填一欄估計值只增不減",
    ).toEqual(seen);
    expect(new Set(seen).size, "每次輸入都有更新").toBe(seen.length);
    expect(readEstimate(dialog)).toEqual({ bytes: 287, max: 700 });
    expect(stub.calls.length, "輸入途中零個網路請求（含預檢）").toBe(before);

    await user.click(within(dialog).getByTestId("si-obs-submit"));
    await within(dialog).findByTestId("si-obs-result");
    expect(within(dialog).getByTestId("si-obs-preview")).toHaveTextContent("預覽列（287 位元組／上限 700）");
    expect(posts(stub).map((c) => c.path)).toEqual(["/api/v1/si/observations/validate", "/api/v1/si/observations"]);
  });

  it("AT_950_9_3 表單的估計值與純函式一致：守衛面加暴露度加外部衍生各自進標記欄（與 O2 的 317 位元組同形）", async () => {
    const user = userEvent.setup();
    const { dialog } = await openNew(user);
    await fillO1(user, dialog, { category: "tooling", severity: "P2", face: "守衛" });
    await user.selectOptions(within(dialog).getByTestId("si-obs-exposure"), "b");
    await user.click(within(dialog).getByTestId("si-obs-external"));
    expect(readEstimate(dialog)).toEqual({ bytes: 317, max: 700 });
    const form: ObservationForm = { ...O1, exposure: "b", externalDerived: true, corrects: "", category: "tooling", severity: "P2", face: "守衛" };
    expect(estimateRowBytes(form, { user: "admin" })).toBe(317);
  });
});

describe("AT_950_9_E_3 估計與即時拒收：含豎線或控制字元不給估計值也不送出，三欄位元組和超過 700 時停用送出", () => {
  it("AT_950_9_E_3 欄位含豎線、含換行與 TAB：不給估計值、欄位下顯示錯誤、送出鈕停用、零請求（含預檢）", async () => {
    const user = userEvent.setup();
    const { stub, dialog } = await openNew(user);
    await fillO1(user, dialog);
    const estimate = within(dialog).getByTestId("si-obs-estimate");
    expect(estimate).toHaveTextContent("287");
    for (const [field, bad] of [
      ["si-obs-context", "含|豎線"],
      ["si-obs-symptom", "換行\n第二行"],
      ["si-obs-evidence", "含\tTAB"],
    ] as const) {
      await setField(user, dialog, field, bad);
      expect(estimate, `${field}＝${JSON.stringify(bad)}`).toHaveTextContent("無法估計");
      expect(estimate.textContent).not.toMatch(/\d+ 位元組/);
      expect(within(dialog).getByTestId("si-obs-submit")).toBeDisabled();
      await setField(user, dialog, field, O1[field.replace("si-obs-", "") as "context" | "symptom" | "evidence"]);
    }
    expect(estimate).toHaveTextContent("287");
    expect(posts(stub)).toHaveLength(0);
  });

  it("AT_950_9_E_3 三欄位元組和 701：送出鈕停用並指出位元組；恰 700 的對照例送出鈕可用；估計值大於 rowMaxBytes 時顯示超限警示但不阻擋（送出時才走預檢）", async () => {
    const user = userEvent.setup();
    const { stub, dialog } = await openNew(user);
    await fillO1(user, dialog, { context: "a".repeat(300), symptom: "b".repeat(300), evidence: "c".repeat(101) });
    const submit = within(dialog).getByTestId("si-obs-submit");
    expect(submit, "701 位元組").toBeDisabled();
    expect(
      within(dialog)
        .getAllByRole("alert")
        .some((a) => (a.textContent ?? "").includes("701")),
      "錯誤訊息講出實際位元組數",
    ).toBe(true);
    expect(within(dialog).getByTestId("si-obs-estimate")).toHaveTextContent("超過上限");
    expect(posts(stub)).toHaveLength(0);

    await setField(user, dialog, "si-obs-evidence", "c".repeat(100));
    expect(submit, "恰 700 位元組").toBeEnabled();
    const estimate = within(dialog).getByTestId("si-obs-estimate");
    const bytes = Number(/預估入帳列 (\d+)/.exec(estimate.textContent ?? "")?.[1]);
    expect(bytes, "估計的是整列（含其他欄位），所以大於 700").toBeGreaterThan(700);
    expect(estimate, "超限警示不阻擋").toHaveTextContent("超過上限");
    await user.click(submit);
    await within(dialog).findByTestId("si-obs-result");
    expect(
      posts(stub).map((c) => c.path),
      "超限警示不阻擋：照樣走預檢與寫入",
    ).toEqual(["/api/v1/si/observations/validate", "/api/v1/si/observations"]);
  });
});
