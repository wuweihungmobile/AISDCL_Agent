import { describe, expect, it } from "vitest";

import { FREEZE_DOCS_MAX, FREEZE_REASON_MAX, SDD_PROJECT_MAX, docPathProblem, parseDocsInput, relativeSpecDoc, validateFreezeForm, validateSddProjectInput } from "./sddFreeze";

const TCS = "docs/03_testing/contracts/TCS-Alpha-20261017.md";

describe("核准凍結：docs 輸入（契約 §1.10.2、§4.7.1）", () => {
  it("多行輸入：一行一個路徑、去前後空白、忽略空行（CRLF 也行）", () => {
    expect(parseDocsInput(`  ${TCS}  \r\n\r\n docs/01_requirements/FRD.md\n   \n`)).toEqual([TCS, "docs/01_requirements/FRD.md"]);
    expect(parseDocsInput("")).toEqual([]);
    expect(parseDocsInput(" \n \n")).toEqual([]);
  });

  it("單一路徑只做格式檢查：相對、POSIX、不含 .. 段；合格回 null（是否含 TCS、檔案是否存在由 Bridge 判定）", () => {
    expect(docPathProblem(TCS)).toBeNull();
    expect(docPathProblem("a/b..c/TCS-x.md")).toBeNull(); // 檔名裡的 .. 不是 .. 段
    expect(docPathProblem("TCS-1.md")).toBeNull();
    expect(docPathProblem("/etc/passwd")).toContain("相對專案根");
    expect(docPathProblem("\\\\server\\share\\a.md")).toContain("相對專案根");
    expect(docPathProblem("C:/proj/a.md")).toContain("相對專案根");
    expect(docPathProblem("c:\\proj\\a.md")).toContain("相對專案根");
    expect(docPathProblem("../secret.md")).toContain("不得含 ..");
    expect(docPathProblem("docs/../../x.md")).toContain("不得含 ..");
    expect(docPathProblem("docs\\..\\x.md")).toContain("不得含 ..");
    expect(docPathProblem("docs\\TCS-a.md")).toContain("請用 / 分隔");
    expect(docPathProblem("docs/a\tb.md")).toContain("控制字元");
  });

  it("專案已有規格檔：預填＝它相對 executionPath 的 POSIX 路徑（POSIX、Windows 混用分隔符、磁碟機代號大小寫皆可）", () => {
    expect(relativeSpecDoc(`/work/core/${TCS}`, "/work/core")).toBe(TCS);
    expect(relativeSpecDoc(`/work/core/${TCS}`, "/work/core/")).toBe(TCS);
    expect(relativeSpecDoc("D:\\proj\\docs\\TCS-a.md", "D:\\proj")).toBe("docs/TCS-a.md");
    expect(relativeSpecDoc("d:\\Proj\\docs\\TCS-a.md", "D:/proj/")).toBe("docs/TCS-a.md"); // Windows 路徑不分大小寫
    expect(relativeSpecDoc("\\\\srv\\share\\p\\TCS-a.md", "\\\\SRV\\share\\p")).toBe("TCS-a.md");
    expect(relativeSpecDoc("/work/Core/docs/a.md", "/work/core")).toBeNull(); // POSIX 路徑分大小寫
  });

  it("規格檔不在專案根之下、與專案根同名前綴、缺值：回 null（預填留空，由後端回 400）", () => {
    expect(relativeSpecDoc("/elsewhere/TCS-a.md", "/work/core")).toBeNull();
    expect(relativeSpecDoc("/work/core2/TCS-a.md", "/work/core")).toBeNull();
    expect(relativeSpecDoc("/work/core", "/work/core")).toBeNull();
    expect(relativeSpecDoc("/work/core/", "/work/core")).toBeNull();
    expect(relativeSpecDoc(null, "/work/core")).toBeNull();
    expect(relativeSpecDoc(undefined, "/work/core")).toBeNull();
    expect(relativeSpecDoc("   ", "/work/core")).toBeNull();
    expect(relativeSpecDoc("/work/core/a.md", "")).toBeNull();
  });
});

describe("核准凍結表單檢查（契約 §4.7.1）", () => {
  const ok = { reason: "規格已走完 SCG-0～3，核准凍結", docsText: TCS };

  it("合格：reason 去前後空白、docs 逐行；stage 空白不送、approver 與 binding 不在請求內（approver 取 JWT subject）", () => {
    const result = validateFreezeForm({ ...ok, reason: `  ${ok.reason}\n`, docsText: `${TCS}\n docs/FRD.md `, stage: "  " });
    expect(result).toEqual({ ok: true, request: { reason: ok.reason, docs: [TCS, "docs/FRD.md"] } });
    if (result.ok) {
      expect(result.request).not.toHaveProperty("stage");
      expect(result.request).not.toHaveProperty("approver");
      expect(result.request).not.toHaveProperty("binding");
      expect(result.request).not.toHaveProperty("expectedDigests");
    }
  });

  it("有填階段名：符合 ^[A-Za-z0-9._-]{1,64}$ 才送（前後空白去掉）；不符不得送出", () => {
    expect(validateFreezeForm({ ...ok, stage: " Stage-2 " })).toEqual({ ok: true, request: { reason: ok.reason, docs: [TCS], stage: "Stage-2" } });
    const bad = validateFreezeForm({ ...ok, stage: "階段 一" });
    expect(bad).toEqual({ ok: false, errors: { stage: "階段名稱只能含英數字與 . _ -（1～64 字元）" } });
    expect(validateFreezeForm({ ...ok, stage: "x".repeat(65) }).ok).toBe(false);
    expect(validateFreezeForm({ ...ok, stage: "x".repeat(64) }).ok).toBe(true);
  });

  it("理由必填（去前後空白後 1～500 字元，不得含換行或控制字元）：空白、過長、含換行都不得送出，不靜默截斷", () => {
    expect(validateFreezeForm({ ...ok, reason: "" })).toEqual({ ok: false, errors: { reason: "請填寫核准理由" } });
    expect(validateFreezeForm({ ...ok, reason: "  \n  " })).toEqual({ ok: false, errors: { reason: "請填寫核准理由" } });
    expect(validateFreezeForm({ ...ok, reason: "第一行\n第二行" })).toEqual({ ok: false, errors: { reason: "理由不得含換行或控制字元" } });
    expect(validateFreezeForm({ ...ok, reason: "有\t定位" }).ok).toBe(false);
    expect(validateFreezeForm({ ...ok, reason: "字".repeat(FREEZE_REASON_MAX) }).ok).toBe(true);
    const tooLong = validateFreezeForm({ ...ok, reason: "字".repeat(FREEZE_REASON_MAX + 1) });
    expect(tooLong).toEqual({ ok: false, errors: { reason: `理由最多 ${FREEZE_REASON_MAX} 字元（目前 ${FREEZE_REASON_MAX + 1}）` } });
    expect(validateFreezeForm({ ...ok, reason: ` ${"字".repeat(FREEZE_REASON_MAX)} ` }).ok).toBe(true); // 長度是去前後空白之後算
  });

  it("docs 必填且 1～20 行：空白、超過 20 份、含絕對路徑／.. 、重複都不得送出；多個問題以「；」串在同一欄", () => {
    expect(validateFreezeForm({ ...ok, docsText: " \n " })).toEqual({ ok: false, errors: { docs: "請至少填寫一份規格文件（每行一個相對專案根的路徑）" } });
    const many = Array.from({ length: FREEZE_DOCS_MAX + 1 }, (_, i) => `docs/f${i}.md`).join("\n");
    expect(validateFreezeForm({ ...ok, docsText: many })).toEqual({ ok: false, errors: { docs: `最多 ${FREEZE_DOCS_MAX} 份規格文件（目前 ${FREEZE_DOCS_MAX + 1} 份）` } });
    expect(validateFreezeForm({ ...ok, docsText: Array.from({ length: FREEZE_DOCS_MAX }, (_, i) => `docs/f${i}.md`).join("\n") }).ok).toBe(true);
    const problems = validateFreezeForm({ ...ok, docsText: `${TCS}\n/abs/x.md\n../y.md\n${TCS}` });
    expect(problems.ok).toBe(false);
    if (!problems.ok) {
      expect(problems.errors.docs).toContain("「/abs/x.md」必須是相對專案根的路徑");
      expect(problems.errors.docs).toContain("「../y.md」不得含 ..");
      expect(problems.errors.docs).toContain(`有重複的路徑：${TCS}`);
      expect(problems.errors.docs?.split("；")).toHaveLength(3);
    }
  });

  it("全部欄位同時有問題：一次回報逐欄錯誤（畫面逐欄顯示）", () => {
    const result = validateFreezeForm({ reason: "", docsText: "", stage: "壞 階段" });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(Object.keys(result.errors).sort()).toEqual(["docs", "reason", "stage"]);
  });
});

describe("編輯 SDD 專案（契約 §1.10.7）", () => {
  it("留白（含只有空白）＝清除：送 null、回到「用預設」；有值去前後空白", () => {
    expect(validateSddProjectInput("")).toEqual({ ok: true, value: null });
    expect(validateSddProjectInput("   ")).toEqual({ ok: true, value: null });
    expect(validateSddProjectInput("  e2e17-alpha ")).toEqual({ ok: true, value: "e2e17-alpha" });
    expect(validateSddProjectInput("我的 專案（含空白與括號）")).toEqual({ ok: true, value: "我的 專案（含空白與括號）" }); // 自由輸入，由 Bridge 淨化
  });

  it("1～100 字元、不含控制字元；超過或含換行不得送出", () => {
    expect(validateSddProjectInput("a".repeat(SDD_PROJECT_MAX))).toEqual({ ok: true, value: "a".repeat(SDD_PROJECT_MAX) });
    expect(validateSddProjectInput("a".repeat(SDD_PROJECT_MAX + 1))).toEqual({ ok: false, error: `最多 ${SDD_PROJECT_MAX} 字元（目前 ${SDD_PROJECT_MAX + 1}）` });
    expect(validateSddProjectInput("a\nb")).toEqual({ ok: false, error: "不得含換行或控制字元" });
    expect(validateSddProjectInput("a\u007fb").ok).toBe(false);
  });
});
