import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

import { expect, test } from "@playwright/test";

import { API_URL, RUN } from "./helpers";
import { collectConsoleErrors, snap } from "./mockApi";
import { E2E_ROOT, FakeLlm, LLM_MARKER, NEEDS_BRIDGE, bootstrapSettings, brd, call, dataOf, ensureQuota, signIn, tokenOf, waitRun, type Json } from "./realBackend";

/**
 * Phase 3 匯入（畫面 6）——對真後端（console-api＋PG）＋本檔自起的假 OpenAI 相容伺服器（綁 127.0.0.1）。
 * 契約 §5 E2E-01 的 UI 面：貼文字 → 路徑 B 解析 → 三道有界閘 422（三條全列）→ 修正重試 → 編輯 → signoff → confirm →
 * 專案頁全部 signedOff；另含上傳檔案、歷史記錄重開、放棄、唯讀角色。
 * 結束動作（契約 E2E-01）：清空 model.apiKey（執行類情境要求 apiKey 為空，關閉引擎演化）。
 */
test.skip(!E2E_ROOT, NEEDS_BRIDGE);

const FIRST_LOAD = { timeout: 60_000 };
const PROJECT_NAME = `E2E 匯入專案 ${RUN}`;
/** 路徑 C 要「假 Brain 版」Bridge（support/fake_brain_bridge.py）；一般 Bridge 沒有 Brain，路徑 C 一律 422 brain_unsupported。 */
const FAKE_BRAIN = process.env.E2E_FAKE_BRAIN === "1";
const MOCK_CLAUDE = path.resolve(process.cwd(), "..", "..", ".venv", process.platform === "win32" ? "Scripts/aisdlc-mock-claude.exe" : "bin/aisdlc-mock-claude");

let llm: FakeLlm;

/**
 * 路徑 A 夾具：在 dir 下寫一份最小的 SDD 規格（FSM 狀態檔＋測試合約 Markdown）。
 * frozen=false 時 FSM 停在 SPEC_DRAFTING 且沒有任何凍結階段，Bridge 的 /sdd/compile 回 422 spec_not_frozen。
 */
function writeSddSpec(dir: string, contracts: number, frozen: boolean): void {
  mkdirSync(path.join(dir, "build", "reports", "fsm"), { recursive: true });
  mkdirSync(path.join(dir, "docs", "03_testing", "contracts"), { recursive: true });
  const state = frozen ? "IMPLEMENTATION" : "SPEC_DRAFTING";
  const stages = frozen ? "  frozen_stages:\n  - stage: SCG-0\n" : "  frozen_stages: []\n";
  const fsm = `fsm_state:\n  project: demo\n  session_id: sid-1\n  current_state: ${state}\n  current_sprint: 2\n  updated_at: '2026-10-14T00:00:00+00:00'\n${stages}  decision_trace:\n  - {ts: t0, from: S0, to: S1, reason: r0}\n`;
  writeFileSync(path.join(dir, "build", "reports", "fsm", "FSM-STATE-demo.yaml"), fsm, "utf-8");
  const pad = (n: number) => String(n).padStart(3, "0");
  const rows = Array.from({ length: contracts }, (_, i) => `| AC-${pad(i + 1)}-1 | 驗收 ${i + 1} | AT-${pad(i + 1)}-1-1 | 情境 ${i + 1} | ✅ | Unit | □ |`);
  const blocks = Array.from({ length: contracts }, (_, i) => `\`\`\`gherkin\n# AT-${pad(i + 1)}-1-1\nScenario: 情境 ${i + 1}\n  Given 前置條件\n  When 執行動作\n  Then 回傳 201 Created\n\`\`\``);
  const md = `# Test Contract Specification — Demo\n\n場景：brownfield 既有系統改進\n\n## 1. AC → AT 映射表\n\n| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |\n|-------|---------|-------|---------|-------|---------|------|\n${rows.join("\n")}\n\n## 2. AT 格式\n\n${blocks.join("\n\n")}\n`;
  writeFileSync(path.join(dir, "docs", "03_testing", "contracts", "TEST-CONTRACT-SPEC-Demo.md"), md, "utf-8");
}

/** 獨立於後端測試夾具（PDFBox／POI）的最小 PDF：單頁、Helvetica、每行一個 Tj（只放 ASCII）。 */
function miniPdf(lines: string[]): Buffer {
  const esc = (s: string) => s.replace(/[\\()]/g, "\\$&");
  const content = `BT /F1 12 Tf 14 TL 50 700 Td ${lines.map((l) => `(${esc(l)}) Tj T*`).join(" ")} ET`;
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    `<< /Length ${Buffer.byteLength(content)} >>\nstream\n${content}\nendstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];
  let body = "%PDF-1.4\n";
  const offsets: number[] = [];
  objects.forEach((o, i) => {
    offsets.push(Buffer.byteLength(body));
    body += `${i + 1} 0 obj\n${o}\nendobj\n`;
  });
  const xref = Buffer.byteLength(body);
  const table = offsets.map((o) => `${String(o).padStart(10, "0")} 00000 n \n`).join("");
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${table}trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(body, "latin1");
}

const CRC_TABLE = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});
const crc32 = (buf: Buffer): number => {
  let c = 0xffffffff;
  for (const b of buf) c = CRC_TABLE[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
};

/** 最小 DOCX（OOXML＝ZIP，不壓縮、手寫 ZIP 結構）：每個字串一個段落。 */
function miniDocx(paragraphs: string[]): Buffer {
  const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const head = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>';
  const entries: Array<[string, string]> = [
    [
      "[Content_Types].xml",
      `${head}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>`,
    ],
    [
      "_rels/.rels",
      `${head}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>`,
    ],
    [
      "word/document.xml",
      `${head}<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>${paragraphs.map((p) => `<w:p><w:r><w:t>${esc(p)}</w:t></w:r></w:p>`).join("")}</w:body></w:document>`,
    ],
  ];
  const locals: Buffer[] = [];
  const centrals: Buffer[] = [];
  let offset = 0;
  for (const [name, text] of entries) {
    const n = Buffer.from(name, "utf-8");
    const data = Buffer.from(text, "utf-8");
    const crc = crc32(data);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0x0800, 6); // 檔名為 UTF-8
    local.writeUInt16LE(0x0021, 12); // DOS 日期 1980-01-01
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(data.length, 18);
    local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(n.length, 26);
    const entry = Buffer.concat([local, n, data]);
    locals.push(entry);
    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(0x0800, 8);
    central.writeUInt16LE(0x0021, 14);
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(data.length, 20);
    central.writeUInt32LE(data.length, 24);
    central.writeUInt16LE(n.length, 28);
    central.writeUInt32LE(offset, 42);
    centrals.push(Buffer.concat([central, n]));
    offset += entry.length;
  }
  const directory = Buffer.concat(centrals);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(entries.length, 8);
  end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(directory.length, 12);
  end.writeUInt32LE(offset, 16);
  return Buffer.concat([...locals, directory, end]);
}

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  // 契約 §5.0.2 的系統參數前置（model.name＝e2e-model、替身引擎…）：本檔自己做，不依賴其他 spec 先跑過（乾淨資料庫上單獨跑也要過）
  await bootstrapSettings(request, MOCK_CLAUDE);
  llm = new FakeLlm(PROJECT_NAME);
  await llm.listen();
});

test.afterAll(async () => {
  await llm.close();
});

test.beforeEach(async ({ request }) => {
  await ensureQuota(request, "operator");
  // 每個情境開始時：模型端點指向假伺服器、金鑰為 sk-e2e-dummy（契約 §5.0.2；confirm=true）
  const url = await call(request, "admin", "PUT", "/api/v1/settings/model/apiUrl", { value: llm.endpoint });
  expect(url.status, `PUT model.apiUrl → ${JSON.stringify(url.json)}`).toBe(200);
  const key = await call(request, "admin", "PUT", "/api/v1/settings/model/apiKey", { value: "sk-e2e-dummy", confirm: true });
  expect(key.status).toBe(200);
  llm.gatesOn = true;
  llm.delayMs = 0;
});

test.afterEach(async ({ request }) => {
  const reset = await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true");
  expect(reset.status).toBe(200);
});

test.describe("BRD/PRD 匯入（真後端＋假 OpenAI 相容伺服器）", () => {
  test.setTimeout(180_000);

  test("貼文字 → 路徑 B → 有界閘 422 三條 → 修正重試 → 編輯 → signoff → confirm → 專案全部 signedOff", async ({ page, request }) => {
    const consoleErrors = collectConsoleErrors(page);
    const projectDir = path.join(E2E_ROOT, "projects", `imp-${RUN}`);
    mkdirSync(projectDir, { recursive: true });
    await signIn(page, request, "operator");
    await page.goto("/import");
    await expect(page.getByRole("heading", { name: "BRD / PRD 智能匯入" })).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("import-step1")).toBeVisible();
    await snap(page, "p3-import-step1.png");

    // ── 步驟 1：貼上文字（文件帶 GATE_UI3 標記：假模型回三道有界閘都違規的樹）──
    await page.getByRole("tab", { name: "貼上文字" }).click();
    await page.getByLabel("需求文字").fill(brd("GATE_UI3"));
    await page.getByLabel("來源名稱").fill(`e2e-brd-${RUN}.md`);
    await page.getByLabel("格式").selectOption("MARKDOWN");
    await page.getByLabel("執行路徑").fill(projectDir);
    await page.getByLabel("補充說明").fill("盡量少於 5 個任務");
    llm.delayMs = 1200;
    await page.getByRole("button", { name: "開始解析" }).click();
    await expect(page.getByTestId("import-parsing")).toBeVisible();
    await snap(page, "p3-import-parsing.png");

    // ── 422：三道閘全部列出（順序 empty_prompt → max_steps → cycle，契約 §3.3.5），不截斷 ──
    const rows = page.getByTestId("gate-error-row");
    await expect(rows).toHaveCount(3);
    await expect(page.getByTestId("parse-failure-title")).toHaveText("解析結果未通過有界閘（共 3 項）");
    await expect(page.getByTestId("gate-error-gate")).toHaveText(["prompt 不可為空", "步驟上限（≤ 24）", "依賴成環（Kahn 無環）"]);
    await expect(page.getByTestId("gate-error-location")).toHaveText(["goals[0].tasks[1].description", "goals[0].tasks", "goals[0].dependsOn"]);
    await expect(page.getByTestId("gate-error-detail").nth(1)).toContainText("25");
    await expect(page.getByTestId("gate-error-detail").nth(1)).toContainText("24");
    await expect(page.getByTestId("gate-error-detail").nth(2)).toContainText("->");
    await expect(page.getByTestId("existing-source")).toContainText(`e2e-brd-${RUN}.md`);
    await expect(page.getByLabel("執行路徑")).toHaveValue(projectDir); // 先前輸入的選項還在
    await snap(page, "p3-import-gate-errors.png", { tall: true });
    expect(llm.count()).toBe(1);

    // 後端的記錄：UPLOADED、lastParseErrors 非空（AR-07）
    const list = await call(request, "viewer", "GET", `/api/v1/import?q=${encodeURIComponent(`e2e-brd-${RUN}`)}&sort=createdAt,desc`);
    expect(list.status).toBe(200);
    const rec = (dataOf<{ content: Json[] }>(list).content[0] ?? {}) as { id?: string; status?: string };
    expect(rec.status).toBe("UPLOADED");
    const detail = await call(request, "viewer", "GET", `/api/v1/import/${rec.id}`);
    expect((dataOf<{ lastParseErrors?: unknown[] }>(detail).lastParseErrors ?? []).length).toBe(3);
    expect(dataOf<{ parsedResult?: unknown }>(detail).parsedResult ?? null).toBeNull(); // 失敗不寫 parsedResult

    // ── 修正（假模型不再違規）後直接重試：不重複建立記錄 ──
    llm.gatesOn = false;
    llm.delayMs = 0;
    await page.getByLabel("補充說明").fill("少於 5 個任務");
    await page.getByRole("button", { name: "開始解析" }).click();
    await expect(page.getByTestId("import-step2")).toBeVisible();
    expect(llm.count()).toBe(2);
    const after = await call(request, "viewer", "GET", `/api/v1/import?q=${encodeURIComponent(`e2e-brd-${RUN}`)}`);
    expect(dataOf<{ totalElements: number }>(after).totalElements).toBe(1);

    // 假伺服器收到的請求（契約 E2E-01 步驟 2）：標頭、model、response_format、兩則訊息
    const last = llm.requests.filter((r) => r.url === "/v1/chat/completions").at(-1)!;
    expect(last.headers.authorization).toBe("Bearer sk-e2e-dummy");
    expect(last.body.model).toBe("e2e-model");
    expect(last.body.stream).toBe(false);
    expect((last.body.response_format as { type: string }).type).toBe("json_object");
    const messages = last.body.messages as Array<{ role: string; content: string }>;
    expect(messages[0].role).toBe("system");
    expect(messages[1].content).toContain("補充說明: 少於 5 個任務");
    expect(messages[1].content).toContain("需求文件內容");

    // ── 步驟 2：三層樹（2 個目標、3 個任務）、AI 解析（LLM）、signoff 橫幅、確認匯入停用 ──
    await expect(page).toHaveURL(new RegExp(`/import\\?id=${rec.id}$`));
    await expect(page.getByTestId("project-name")).toHaveText(PROJECT_NAME);
    await expect(page.getByTestId("tree-goal")).toHaveCount(2);
    await expect(page.getByTestId("tree-task")).toHaveCount(3);
    await expect(page.getByTestId("task-name")).toHaveText(["初始化", "設定", "實作"]);
    await expect(page.getByTestId("parse-path")).toHaveText("AI 解析（LLM）");
    await expect(page.getByTestId("parse-failure")).toHaveCount(0);
    await expect(page.getByTestId("import-signoff-banner")).toContainText("signed_off=false");
    await expect(page.getByRole("button", { name: "確認匯入" })).toBeDisabled();
    await expect(page.getByTestId("signoff-badge")).toBeVisible(); // 匯入草案計入頂列待簽核佇列
    await snap(page, "p3-import-step2.png", { tall: true });

    // ── 編輯：任務改名 → 儲存（撤銷 signoff、狀態轉審核中）──
    await page.getByRole("button", { name: "編輯任務：設定" }).click();
    const edit = page.getByRole("dialog", { name: "編輯任務" });
    await edit.getByLabel("任務名稱").fill("設定環境");
    // DEF-AC-001（W5 已修）：真後端對 AI 解析的任務回 maxRetries:null；對話框現在把 null 當成空白（不再顯示字面「null」），
    // 所以不必手動清空該欄就能按「確定」（W4 版在這裡得先 fill("") 繞過）
    await expect(edit.getByLabel("最大重試次數")).toHaveValue("");
    await edit.getByRole("button", { name: "確定" }).click();
    await expect(page.getByTestId("dirty-notice")).toBeVisible();
    await expect(page.getByRole("button", { name: "signoff 審批" })).toBeDisabled();
    await page.getByRole("button", { name: "儲存編輯" }).click();
    await expect(page.getByRole("status").filter({ hasText: "已儲存編輯" })).toBeVisible();
    await expect(page.getByTestId("import-status")).toHaveText("審核中");
    await expect(page.getByTestId("task-name")).toHaveText(["初始化", "設定環境", "實作"]);

    // ── signoff：approver 預設帶目前使用者；確認匯入在 signoff 前被後端 409（API 直打）──
    const early = await call(request, "operator", "POST", `/api/v1/import/${rec.id}/confirm`);
    expect(early.status).toBe(409);
    expect(early.json.reason).toBe("草案尚未 signoff，不可確認匯入");
    await page.getByRole("button", { name: "signoff 審批" }).click();
    const signoff = page.getByRole("dialog", { name: "審批 signoff：匯入草案" });
    await expect(signoff.getByLabel("審批者")).toHaveValue("operator");
    await snap(page, "p3-import-signoff-dialog.png");
    await signoff.getByRole("button", { name: "確認 signoff" }).click();
    await expect(page.getByTestId("import-signed-off")).toContainText("已 signoff");
    await expect(page.getByTestId("import-signed-off")).toContainText("審批者 operator");
    await expect(page.getByRole("button", { name: "確認匯入" })).toBeEnabled();
    await snap(page, "p3-import-signed-off.png", { tall: true });

    // ── 確認匯入 → 專案頁 ──
    await page.getByRole("button", { name: "確認匯入" }).click();
    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]{36}$/);
    const projectId = page.url().split("/").at(-1)!;
    await expect(page.getByTestId("project-title")).toHaveText(PROJECT_NAME);
    await expect(page.getByTestId("signoff-banner")).toHaveCount(0); // 匯入的草案經 signoff 後整案已簽
    await expect(page.getByTestId("goal-row")).toHaveCount(2);
    await snap(page, "p3-import-imported-project.png", { tall: true });

    // ── 後端落庫（契約 E2E-01 步驟 11～13）：專案／目標／任務全部 signedOff，簽核者承襲，依賴由 key 換成 id ──
    const project = dataOf<{ status: string; signedOff: boolean; signedOffBy: string; autonomyLevel: number; executionPath: string; goalsCount?: number; tasksCount?: number; createdBy: string }>(
      await call(request, "viewer", "GET", `/api/v1/projects/${projectId}`),
    );
    expect(project).toMatchObject({ status: "DRAFT", signedOff: true, signedOffBy: "operator", createdBy: "operator", executionPath: projectDir });
    // 清單端點只帶 signedOff（Phase 2 的摘要形狀），signedOffBy／At 在詳情端點（契約 E2E-01 步驟 12 的措辭對清單過寬）
    const goals = dataOf<Array<{ id: string; name: string; signedOff: boolean }>>(await call(request, "viewer", "GET", `/api/v1/projects/${projectId}/goals`));
    expect(goals).toHaveLength(2);
    for (const g of goals) {
      expect(g.signedOff).toBe(true);
      const d = dataOf<{ signedOffBy: string; signedOffAt: string; dependsOn: string[] }>(await call(request, "viewer", "GET", `/api/v1/goals/${g.id}`));
      expect(d.signedOffBy).toBe("operator");
      expect(d.signedOffAt).toBeTruthy();
      if (g.id === goals[1].id) expect(d.dependsOn).toEqual([goals[0].id]);
    }
    let tasks = 0;
    for (const g of goals) {
      const ts = dataOf<Array<{ id: string; signedOff: boolean }>>(await call(request, "viewer", "GET", `/api/v1/goals/${g.id}/tasks`));
      tasks += ts.length;
      for (const t of ts) {
        expect(t.signedOff).toBe(true);
        expect(dataOf<{ signedOffBy: string }>(await call(request, "viewer", "GET", `/api/v1/tasks/${t.id}`)).signedOffBy).toBe("operator");
      }
    }
    expect(tasks).toBe(3);
    const done = dataOf<{ status: string; projectId: string }>(await call(request, "viewer", "GET", `/api/v1/import/${rec.id}`));
    expect(done.status).toBe("IMPORTED");
    expect(done.projectId).toBe(projectId);
    expect(consoleErrors, "整段流程不應有主控台錯誤").toEqual([]);
  });

  test("上傳 .md 檔（multipart）→ 解析；副檔名不符當場擋下；歷史記錄重開並還原；放棄", async ({ page, request }) => {
    const projectDir = path.join(E2E_ROOT, "projects", `imp-up-${RUN}`);
    mkdirSync(projectDir, { recursive: true });
    await signIn(page, request, "operator");
    await page.goto("/import");
    await expect(page.getByTestId("import-dropzone")).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("import-dropzone")).toContainText("支援格式：.md · .pdf · .docx　|　檔案大小限制 10MB");
    await snap(page, "p3-import-dropzone.png");

    const input = page.getByTestId("import-file-input");
    await input.setInputFiles({ name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("x") });
    await expect(page.getByTestId("source-error")).toHaveText("只支援 .md／.pdf／.docx 檔案");

    const fileName = `upload-${RUN}.md`;
    await input.setInputFiles({ name: fileName, mimeType: "text/markdown", buffer: Buffer.from(brd(), "utf-8") });
    await expect(page.getByTestId("selected-file")).toContainText(fileName);
    await page.getByLabel("執行路徑").fill(projectDir);
    await page.getByRole("button", { name: "開始解析" }).click();
    await expect(page.getByTestId("import-step2")).toBeVisible();
    await expect(page.getByTestId("tree-task")).toHaveCount(3);

    // 後端：來源型別由副檔名決定（MARKDOWN）、sourceContent 是檔案的文字
    const rec = dataOf<{ content: Array<{ id: string; sourceType: string; status: string; sourceFileName: string }> }>(
      await call(request, "viewer", "GET", `/api/v1/import?q=${encodeURIComponent(`upload-${RUN}`)}`),
    ).content[0]!;
    expect(rec).toMatchObject({ sourceType: "MARKDOWN", status: "PARSED", sourceFileName: fileName });
    const detail = dataOf<{ sourceContent: string }>(await call(request, "viewer", "GET", `/api/v1/import/${rec.id}`));
    expect(detail.sourceContent).toContain("BRD：E2E 匯入專案");

    // 歷史記錄：列出並重開；重新整理後仍還原（?id= ＋ GET /import/{id}）
    await page.goto("/import");
    await page.getByRole("tab", { name: "歷史記錄" }).click();
    const row = page.getByTestId("import-history-row").filter({ hasText: fileName });
    await expect(row).toContainText("已解析");
    await expect(row).toContainText("e2e-model");
    await snap(page, "p3-import-history.png");
    await row.getByRole("button", { name: /^開啟匯入記錄/ }).click();
    await expect(page.getByTestId("import-step2")).toBeVisible();
    await page.reload();
    await expect(page.getByTestId("import-step2")).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("task-name")).toHaveText(["初始化", "設定", "實作"]);

    // 放棄：確認對話框 → REJECTED → 回到新的匯入
    await page.getByRole("button", { name: "放棄" }).click();
    await page.getByRole("dialog", { name: "放棄這份匯入草案？" }).getByRole("button", { name: "放棄" }).click();
    await expect(page.getByRole("status").filter({ hasText: "已放棄匯入" })).toBeVisible();
    await expect(page).toHaveURL(/\/import$/);
    const gone = dataOf<{ status: string }>(await call(request, "viewer", "GET", `/api/v1/import/${rec.id}`));
    expect(gone.status).toBe("REJECTED");
  });

  test("E2E-01 API 序列：有界閘變體（422、lastParseErrors、重試後清空）、消毒變體、signoff／confirm 序列與狀態機、上傳變體", async ({ request }) => {
    await ensureQuota(request, "operator", 80); // 本情境約用掉 operator 70 次呼叫；限流視窗 100 次／分鐘（前面的 UI 情境已用掉一部分）
    const dir = path.join(E2E_ROOT, "projects", `imp-api-${RUN}`);
    mkdirSync(dir, { recursive: true });
    const opts = { executionPath: dir, autonomyLevel: 3, additionalPrompt: "盡量少於 5 個任務" };
    const newRecord = async (marker = "", name = `api-${RUN}.md`) => {
      const r = await call(request, "operator", "POST", "/api/v1/import/text", { content: brd(marker), sourceFileName: name, sourceType: "MARKDOWN" });
      expect(r.status).toBe(201);
      expect(dataOf(r)).toMatchObject({ status: "UPLOADED", signedOff: false, sourceType: "MARKDOWN" });
      return dataOf<{ id: string }>(r).id;
    };
    type GateErr = { gate: string; location?: string; detail: string; field: string; message: string };
    const parse = (id: string) => call(request, "operator", "POST", `/api/v1/import/${id}/parse`, opts);

    // ── 有界閘變體：每筆都 422／reason／記錄退回 UPLOADED／lastParseErrors 非空；之後正常重解析 → 200 且清空 ──
    const variants: Array<[string, Array<[string, string | undefined, string[]]>]> = [
      [LLM_MARKER.max, [["max_steps", "goals[0].tasks", ["25", "24"]]]],
      [LLM_MARKER.cycle, [["cycle", "goals[0].dependsOn", ["->"]]]],
      [LLM_MARKER.empty, [["empty_prompt", "goals[0].tasks[1].description", []]]],
      [LLM_MARKER.emptyName, [["empty_prompt", "goals[0].tasks[0].name", []]]],
      [LLM_MARKER.long, [["prompt_too_long", "goals[0].tasks[0]", []]]],
      [
        LLM_MARKER.multi,
        [
          ["empty_prompt", "goals[0].tasks[1].description", []],
          ["max_steps", "goals[0].tasks", ["25"]],
        ],
      ],
      [LLM_MARKER.badJson, [["brain_failed", undefined, []]]],
      [LLM_MARKER.http500, [["brain_failed", undefined, ["500"]]]],
    ];
    for (const [marker, expected] of variants) {
      llm.gatesOn = true;
      const id = await newRecord(marker, `api-${marker}-${RUN}.md`);
      const r = await parse(id);
      expect(r.status, `${marker} → ${JSON.stringify(r.json).slice(0, 300)}`).toBe(422);
      expect(r.json.reason, marker).toBe("解析結果未通過有界閘");
      const errors = r.json.errors as GateErr[];
      expect(
        errors.map((e) => e.gate),
        marker,
      ).toEqual(expected.map((e) => e[0]));
      expected.forEach(([, location, detailParts], i) => {
        expect(errors[i].location, `${marker} location`).toBe(location);
        for (const part of detailParts) expect(errors[i].detail, `${marker} detail`).toContain(part);
        expect(errors[i].detail).not.toContain("sk-e2e-dummy"); // 不洩漏金鑰
      });
      const rec = dataOf<{ status: string; lastParseErrors?: unknown[]; parsedResult?: unknown }>(await call(request, "viewer", "GET", `/api/v1/import/${id}`));
      expect(rec.status, marker).toBe("UPLOADED");
      expect((rec.lastParseErrors ?? []).length, marker).toBeGreaterThan(0);
      expect(rec.parsedResult ?? null, marker).toBeNull();
      llm.gatesOn = false; // 假模型不再違規：同一筆記錄重新 parse
      const again = await parse(id);
      expect(again.status, marker).toBe(200);
      const cleared = dataOf<{ status: string; lastParseErrors?: unknown[] }>(await call(request, "viewer", "GET", `/api/v1/import/${id}`));
      expect([cleared.status, cleared.lastParseErrors ?? null], marker).toEqual(["PARSED", null]);
      await call(request, "operator", "POST", `/api/v1/import/${id}/reject`);
    }
    // 清空 model.apiKey → brain_unsupported（detail 點名 model.apiKey）
    expect((await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true")).status).toBe(200);
    const noKeyId = await newRecord("", `api-nokey-${RUN}.md`);
    const noKey = await parse(noKeyId);
    expect(noKey.status).toBe(422);
    expect((noKey.json.errors as GateErr[])[0]).toMatchObject({ gate: "brain_unsupported" });
    expect((noKey.json.errors as GateErr[])[0].detail).toContain("model.apiKey");
    await call(request, "operator", "POST", `/api/v1/import/${noKeyId}/reject`);
    // 狀態機：REJECTED 是終態，confirm 回 409 匯入記錄狀態不允許此操作（details.action）
    const afterReject = await call(request, "operator", "POST", `/api/v1/import/${noKeyId}/confirm`);
    expect([afterReject.status, afterReject.json.reason]).toEqual([409, "匯入記錄狀態不允許此操作"]);
    expect(afterReject.json.details as { action: string; status: string }).toMatchObject({ action: "confirm", status: "REJECTED" });
    expect((await call(request, "admin", "PUT", "/api/v1/settings/model/apiKey", { value: "sk-e2e-dummy", confirm: true })).status).toBe(200);

    // ── 主序列（E2E-01 步驟 1～14）：解析 → 編輯 → 消毒變體 → signoff／confirm 狀態機 ──
    llm.gatesOn = false;
    const id = await newRecord("", `api-main-${RUN}.md`);
    const parsed = await parse(id);
    expect(parsed.status).toBe(200);
    expect(dataOf(parsed)).toMatchObject({ status: "PARSED", path: "LLM", aiModel: "e2e-model", tokenUsed: 1152, signedOff: false, errors: [], warnings: [] });
    const tree = dataOf<{ parsedResult: { project: Json; goals: Array<{ key: string; name: string; dependsOn: string[]; tasks: Array<Json> }> } }>(parsed).parsedResult;
    expect(tree.goals).toHaveLength(2);
    expect([tree.goals[0].tasks.length, tree.goals[1].tasks.length]).toEqual([2, 1]);
    expect(tree.goals[1].dependsOn).toEqual(["g1"]);
    expect((tree.project as { executionPath: string }).executionPath).toBe(dir); // LLM 的 /ignored 被丟棄
    const put = (parsedResult: unknown) => call(request, "operator", "PUT", `/api/v1/import/${id}/result`, { parsedResult });
    const edited = structuredClone(tree);
    edited.goals[0].name = "基礎建設";
    edited.goals[1].tasks.push({ name: "新增任務", description: "請輸出 [T4_DONE]", passCriteria: "輸出含 [T4_DONE]" });
    const e1 = await put(edited);
    expect(e1.status, JSON.stringify(e1.json).slice(0, 300)).toBe(200);
    expect(dataOf(e1)).toMatchObject({ status: "REVIEWING", signedOff: false });
    // 消毒變體：禁用字元 → 400（命令含禁用字元＋violations）；regex 無法編譯 → 400；合法值 → 200
    const bad = structuredClone(edited);
    (bad.goals[0].tasks[0] as Json).evaluatorCommand = "pytest -q; echo done";
    const s1 = await put(bad);
    expect(s1.status).toBe(400);
    expect(s1.json.reason).toBe("命令含禁用字元");
    expect((s1.json.details as { violations: string[] }).violations).toContain(";");
    (bad.goals[0].tasks[0] as Json).evaluatorCommand = "pytest -q";
    (bad.goals[0].tasks[0] as Json).expectedOutputRegex = "([";
    expect((await put(bad)).status).toBe(400);
    (bad.goals[0].tasks[0] as Json).expectedOutputRegex = "\\[T1_DONE\\]";
    expect((await put(bad)).status).toBe(200);
    // 空白 name → 422 empty_prompt；缺欄位／null → 400
    const blank = structuredClone(edited);
    (blank.goals[0].tasks[0] as Json).name = "  ";
    const b1 = await put(blank);
    expect(b1.status).toBe(422);
    expect((b1.json.errors as GateErr[])[0]).toMatchObject({ gate: "empty_prompt", location: "goals[0].tasks[0].name" });
    const nul = structuredClone(edited);
    (nul.goals[0].tasks[0] as Json).name = null;
    expect((await put(nul)).status).toBe(400);
    // signoff／confirm 狀態機
    const early = await call(request, "operator", "POST", `/api/v1/import/${id}/confirm`);
    expect([early.status, early.json.reason]).toEqual([409, "草案尚未 signoff，不可確認匯入"]);
    const anon = await call(request, "operator", "POST", `/api/v1/import/${id}/signoff`, { approver: "  " });
    expect(anon.status).toBe(400);
    expect((anon.json.errors as Array<{ field: string }>)[0].field).toBe("approver");
    const so = await call(request, "operator", "POST", `/api/v1/import/${id}/signoff`, { approver: "e2e-approver" });
    expect(so.status).toBe(200);
    expect(dataOf(so)).toMatchObject({ signedOff: true, signedOffBy: "e2e-approver" });
    const dup = await call(request, "operator", "POST", `/api/v1/import/${id}/signoff`, { approver: "e2e-approver" });
    expect([dup.status, dup.json.reason]).toEqual([409, "已 signoff"]);
    expect((dup.json.details as { signedOffBy: string }).signedOffBy).toBe("e2e-approver");
    const re = await put(edited); // 編輯撤銷 signoff
    expect(dataOf(re)).toMatchObject({ signedOff: false });
    expect(dataOf<{ signedOffBy?: string | null }>(await call(request, "viewer", "GET", `/api/v1/import/${id}`)).signedOffBy ?? null).toBeNull();
    expect((await call(request, "operator", "POST", `/api/v1/import/${id}/signoff`, { approver: "e2e-approver" })).status).toBe(200);
    const resigned = await parse(id); // 已 signoff：不可重新解析
    expect([resigned.status, resigned.json.reason]).toEqual([409, "已 signoff，不可重新解析"]);
    const confirm = await call(request, "operator", "POST", `/api/v1/import/${id}/confirm`);
    expect(confirm.status).toBe(201);
    expect(dataOf(confirm)).toMatchObject({
      signedOff: true,
      signedOffBy: "e2e-approver",
      status: "DRAFT",
      goalsCount: 2,
      tasksCount: 4,
      autonomyLevel: 3,
      executionPath: dir,
      name: PROJECT_NAME,
      createdBy: "operator",
    });
    const again = await call(request, "operator", "POST", `/api/v1/import/${id}/confirm`);
    expect([again.status, again.json.reason], "再次 confirm").toEqual([409, "已匯入"]);
    expect((again.json.details as { projectId: string }).projectId).toBe(dataOf<{ id: string }>(confirm).id);
    const rej = await call(request, "operator", "POST", `/api/v1/import/${id}/reject`);
    expect([rej.status, rej.json.reason]).toEqual([409, "匯入記錄狀態不允許此操作"]);
    expect((rej.json.details as { action: string }).action).toBe("reject");
    // IMPORTED 是終態：parse／editResult／signoff 一律 409 匯入記錄狀態不允許此操作，details.action 帶動作名
    const stuck: Array<[string, Awaited<ReturnType<typeof parse>>]> = [
      ["parse", await parse(id)],
      ["editResult", await put(edited)],
      ["signoff", await call(request, "operator", "POST", `/api/v1/import/${id}/signoff`, { approver: "e2e-approver" })],
    ];
    for (const [action, r] of stuck) {
      expect([r.status, r.json.reason], action).toEqual([409, "匯入記錄狀態不允許此操作"]);
      expect(r.json.details as { action: string; status: string }, action).toMatchObject({ action, status: "IMPORTED" });
    }
    const listed = dataOf<{ content: Array<{ id: string; projectId?: string }> }>(await call(request, "viewer", "GET", "/api/v1/import?status=IMPORTED&sort=createdAt,desc&size=50"));
    expect(listed.content.find((x) => x.id === id)?.projectId).toBe(dataOf<{ id: string }>(confirm).id);
    // 角色：viewer 寫入 403、讀取 200
    expect((await call(request, "viewer", "POST", "/api/v1/import/text", { content: "x" })).status).toBe(403);
    expect((await call(request, "viewer", "GET", "/api/v1/import")).status).toBe(200);

    // ── 上傳變體 ──
    const token = await tokenOf(request, "operator");
    const upload = (name: string, buffer: Buffer, who = token) =>
      request.fetch(`${API_URL}/api/v1/import/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${who}` },
        multipart: { file: { name, mimeType: "application/octet-stream", buffer } },
        failOnStatusCode: false,
      });
    const ok = await upload(`up-${RUN}.md`, Buffer.from("# BRD\n\n## 一\n內容", "utf-8"));
    expect(ok.status()).toBe(201);
    expect(((await ok.json()) as { data: { sourceType: string; status: string } }).data).toMatchObject({ sourceType: "MARKDOWN", status: "UPLOADED" });
    const txt = await upload("a.txt", Buffer.from("hello"));
    expect([txt.status(), ((await txt.json()) as { reason: string }).reason]).toEqual([415, "只支援 .md／.pdf／.docx 檔案"]);
    const big = await upload("big.md", Buffer.alloc(11 * 1024 * 1024, 97));
    expect([big.status(), ((await big.json()) as { reason: string }).reason]).toEqual([413, "檔案超過 10MB 上限"]);
    const fakePdf = await upload("x.pdf", Buffer.from("hello"));
    expect([fakePdf.status(), ((await fakePdf.json()) as { reason: string }).reason]).toEqual([422, "檔案內容與副檔名不符"]);
    const empty = await upload("e.md", Buffer.alloc(0));
    expect([empty.status(), ((await empty.json()) as { reason: string }).reason]).toEqual([400, "檔案是空的"]);
    const viewerUpload = await upload("v.md", Buffer.from("# x"), await tokenOf(request, "viewer"));
    expect(viewerUpload.status()).toBe(403);
  });

  test("路徑 A（凍結 SDD 規格，真 Bridge 的 /sdd/compile）：探測與明示 specDir、不呼叫模型、30 個合約切成 24＋6 兩個目標、未凍結 fail-closed、signoff→confirm", async ({ request }) => {
    const modelCallsBefore = llm.count();
    type SpecTask = { name: string; evaluatorCommand?: string; expectedOutputRegex?: string; passCriteriaSpec?: { source: string; specDigest: string; stepId: string; weakRegex: boolean } };
    type SpecTree = { project: { executionPath: string; autonomyLevel: number }; goals: Array<{ key: string; name: string; dependsOn: string[]; tasks: SpecTask[] }>; specDigest?: string };
    type Parsed = { status: string; path: string; aiModel?: string | null; tokenUsed?: number | null; parsedResult: SpecTree };
    // 短文字（< 2000 字元、無標題）：若沒有被路徑 A 接走就會落到路徑 C；所以「path=SDD」本身就證明探測生效
    const newRecord = async () => dataOf<{ id: string }>(await call(request, "operator", "POST", "/api/v1/import/text", { content: "凍結規格匯入（短內容）", sourceType: "PLAIN_TEXT" })).id;
    const parse = (id: string, body: Json) => call(request, "operator", "POST", `/api/v1/import/${id}/parse`, body);

    // 1) 探測：executionPath 下有凍結規格 → 路徑 A
    const root = path.join(E2E_ROOT, "projects", `sdd-${RUN}`);
    writeSddSpec(root, 3, true);
    const id = await newRecord();
    const probe = await parse(id, { executionPath: root, autonomyLevel: 2 });
    expect(probe.status, JSON.stringify(probe.json).slice(0, 300)).toBe(200);
    const d = dataOf<Parsed>(probe);
    expect(d).toMatchObject({ status: "PARSED", path: "SDD" });
    expect([d.aiModel ?? null, d.tokenUsed ?? null], "路徑 A 不呼叫任何 Brain：aiModel／tokenUsed 皆 null").toEqual([null, null]);
    const tree = d.parsedResult;
    expect(tree.project).toMatchObject({ executionPath: root, autonomyLevel: 2 });
    expect(tree.goals).toHaveLength(1);
    expect(tree.goals[0].tasks.map((t) => t.name)).toEqual(["AT-001-1-1", "AT-002-1-1", "AT-003-1-1"]);
    expect(tree.specDigest).toMatch(/^sha256:[0-9a-f]{64}$/);
    for (const t of tree.goals[0].tasks) {
      expect(t.passCriteriaSpec, t.name).toMatchObject({ source: "sdd", specDigest: tree.specDigest, weakRegex: false });
      expect(t.passCriteriaSpec?.stepId, t.name).toMatch(/^sdd-/);
      expect(t.evaluatorCommand, t.name).toContain("pytest");
      expect(t.expectedOutputRegex, t.name).toBeTruthy();
    }
    // signoff → confirm：專案由規格匯入（status=DRAFT，1 個目標 3 個任務、自治等級沿用探測請求）
    expect((await call(request, "operator", "POST", `/api/v1/import/${id}/signoff`, { approver: "e2e-approver" })).status).toBe(200);
    const confirm = await call(request, "operator", "POST", `/api/v1/import/${id}/confirm`);
    expect(confirm.status, JSON.stringify(confirm.json).slice(0, 300)).toBe(201);
    expect(dataOf(confirm)).toMatchObject({ status: "DRAFT", goalsCount: 1, tasksCount: 3, autonomyLevel: 2, executionPath: root, signedOff: true, signedOffBy: "e2e-approver" });
    expect(dataOf<{ description: string }>(confirm).description).toContain("由凍結 SDD 規格匯入");

    // 2) 明示 specDir（executionPath 下沒有規格）→ 路徑 A；任何 Bridge 失敗都報錯
    const bare = path.join(E2E_ROOT, "projects", `sdd-bare-${RUN}`);
    mkdirSync(bare, { recursive: true });
    const idExplicit = await newRecord();
    const explicit = await parse(idExplicit, { executionPath: bare, autonomyLevel: 3, specDir: path.join(root, "docs") });
    expect(explicit.status, JSON.stringify(explicit.json).slice(0, 300)).toBe(200);
    expect(dataOf<Parsed>(explicit)).toMatchObject({ status: "PARSED", path: "SDD" });
    await call(request, "operator", "POST", `/api/v1/import/${idExplicit}/reject`);

    // 3) 30 個合約：AR-19 每 24 個切一個目標（24＋6），後一組 dependsOn 前一組，不得因合約數多而 422
    const big = path.join(E2E_ROOT, "projects", `sdd30-${RUN}`);
    writeSddSpec(big, 30, true);
    const idBig = await newRecord();
    const bigParse = await parse(idBig, { executionPath: big, autonomyLevel: 3 });
    expect(bigParse.status, JSON.stringify(bigParse.json).slice(0, 300)).toBe(200);
    const bigTree = dataOf<Parsed>(bigParse).parsedResult;
    expect(bigTree.goals.map((g) => g.tasks.length)).toEqual([24, 6]);
    expect(bigTree.goals.map((g) => g.name)).toEqual(["brownfield（第 1 批）", "brownfield（第 2 批）"]);
    expect(bigTree.goals.map((g) => g.dependsOn)).toEqual([[], [bigTree.goals[0].key]]);
    expect((await call(request, "operator", "POST", `/api/v1/import/${idBig}/signoff`, { approver: "e2e-approver" })).status).toBe(200);
    const bigConfirm = await call(request, "operator", "POST", `/api/v1/import/${idBig}/confirm`);
    expect(bigConfirm.status).toBe(201);
    expect(dataOf(bigConfirm)).toMatchObject({ goalsCount: 2, tasksCount: 30 });

    // 4) 規格存在但未凍結 → fail-closed：422「SDD 規格檢查未通過」，不退回 LLM 路徑瞎猜（PRD §0.4 凍結硬閘）
    const unfrozen = path.join(E2E_ROOT, "projects", `sdd-unfrozen-${RUN}`);
    writeSddSpec(unfrozen, 3, false);
    const idUnfrozen = await newRecord();
    const refused = await parse(idUnfrozen, { executionPath: unfrozen, autonomyLevel: 3 });
    expect(refused.status, JSON.stringify(refused.json).slice(0, 300)).toBe(422);
    expect(refused.json.reason).toBe("SDD 規格檢查未通過");
    expect((refused.json.details as { bridgeReason: string }).bridgeReason).toBe("spec_not_frozen");
    expect((refused.json.errors as Array<{ field: string }>)[0].field).toBe("specDir");
    expect(dataOf<{ status: string; parsedResult?: unknown }>(await call(request, "viewer", "GET", `/api/v1/import/${idUnfrozen}`))).toMatchObject({ status: "UPLOADED" });
    // 明示 specDir 指向不存在的目錄 → 422（spec_not_found 在明示模式也報錯）
    const missing = await parse(idUnfrozen, { executionPath: unfrozen, autonomyLevel: 3, specDir: path.join(E2E_ROOT, "projects", `no-such-${RUN}`) });
    expect(missing.status, JSON.stringify(missing.json).slice(0, 300)).toBe(422);
    expect(missing.json.reason).toBe("SDD 規格檢查未通過");
    await call(request, "operator", "POST", `/api/v1/import/${idUnfrozen}/reject`);

    expect(llm.count(), "路徑 A 與其 fail-closed 都不得呼叫模型").toBe(modelCallsBefore);
  });

  test("上傳 PDF 與 DOCX（本檔獨立產生的真檔，不是後端測試用的 PDFBox／POI 夾具）：擷取文字、sourceType、擷取結果進入路徑 B 的提示詞", async ({ request }) => {
    const token = await tokenOf(request, "operator");
    const upload = (name: string, buffer: Buffer) =>
      request.fetch(`${API_URL}/api/v1/import/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        multipart: { file: { name, mimeType: "application/octet-stream", buffer } },
        failOnStatusCode: false,
      });
    type Rec = { id: string; sourceType: string; status: string; sourceFileName: string };
    const detail = async (id: string) => dataOf<{ sourceContent: string }>(await call(request, "viewer", "GET", `/api/v1/import/${id}`));

    const pdf = await upload(`req-${RUN}.pdf`, miniPdf(["Requirement One", "Requirement (Two) with parentheses"]));
    expect(pdf.status(), await pdf.text()).toBe(201);
    const pdfRec = ((await pdf.json()) as { data: Rec }).data;
    expect(pdfRec).toMatchObject({ sourceType: "PDF", status: "UPLOADED", sourceFileName: `req-${RUN}.pdf` });
    const pdfText = (await detail(pdfRec.id)).sourceContent;
    expect(pdfText).toContain("Requirement One");
    expect(pdfText).toContain("Requirement (Two) with parentheses");

    const docx = await upload(`req-${RUN}.docx`, miniDocx(["需求標題 Heading", "第一段內容 & <特殊字元>", "第二段內容"]));
    expect(docx.status(), await docx.text()).toBe(201);
    const docxRec = ((await docx.json()) as { data: Rec }).data;
    expect(docxRec).toMatchObject({ sourceType: "DOCX", status: "UPLOADED" });
    const docxText = (await detail(docxRec.id)).sourceContent;
    for (const part of ["需求標題 Heading", "第一段內容 & <特殊字元>", "第二段內容"]) expect(docxText).toContain(part);

    // 擷取結果接著走路徑 B：假模型收到的提示詞含擷取出的文字
    const dir = path.join(E2E_ROOT, "projects", `imp-pdf-${RUN}`);
    mkdirSync(dir, { recursive: true });
    llm.gatesOn = false;
    const before = llm.count();
    const parsed = await call(request, "operator", "POST", `/api/v1/import/${pdfRec.id}/parse`, { executionPath: dir, autonomyLevel: 3 });
    expect(parsed.status, JSON.stringify(parsed.json).slice(0, 300)).toBe(200);
    expect(dataOf(parsed)).toMatchObject({ status: "PARSED", path: "LLM" });
    expect(llm.count()).toBe(before + 1);
    expect(JSON.stringify(llm.requests.filter((r) => r.url === "/v1/chat/completions").at(-1)?.body)).toContain("Requirement One");
    await call(request, "operator", "POST", `/api/v1/import/${pdfRec.id}/reject`);
    await call(request, "operator", "POST", `/api/v1/import/${docxRec.id}/reject`);
  });

  test("路徑 C（高階目標拆解，真 Bridge＋假 Brain）：三道有界閘與 brain_failed、decompose 結果、signoff 時 Bridge 草案才被 approve、confirm、專案可被引擎執行", async ({ request }) => {
    test.skip(!FAKE_BRAIN, "需要假 Brain 版 Bridge（support/fake_brain_bridge.py）：設 E2E_FAKE_BRAIN=1（見 README〈真 Bridge specs〉）");
    const dir = path.join(E2E_ROOT, "projects", `imp-c-${RUN}`);
    mkdirSync(dir, { recursive: true });
    // 路徑 C 只在 model.apiKey 非空時帶 minimax 覆寫（base_url＝model.apiUrl＝假伺服器，白名單內的 loopback）；beforeEach 已設好
    const newRecord = async (content: string) =>
      dataOf<{ id: string }>(await call(request, "operator", "POST", "/api/v1/import/text", { content, sourceType: "PLAIN_TEXT", sourceFileName: `c-${RUN}.txt` })).id;
    const parse = (id: string) => call(request, "operator", "POST", `/api/v1/import/${id}/parse`, { executionPath: dir, autonomyLevel: 4, additionalPrompt: "QA 補充說明" });
    // 三道有界閘＋Brain 失敗：Bridge 的 422 gate 對映到契約的 errors[].gate；全部不呼叫模型
    const callsBefore = llm.count();
    for (const [marker, gate] of [
      ["GATE_MAX", "max_steps"],
      ["GATE_CYCLE", "cycle"],
      ["GATE_EMPTY", "empty_prompt"],
      ["GATE_NONE", "brain_failed"],
    ] as const) {
      const id = await newRecord(`把使用者登入功能做完 ${marker}`);
      const r = await parse(id);
      expect(r.status, `${marker} → ${JSON.stringify(r.json).slice(0, 300)}`).toBe(422);
      expect(r.json.reason).toBe("解析結果未通過有界閘");
      expect((r.json.errors as Array<{ gate: string }>)[0].gate, marker).toBe(gate);
      await call(request, "operator", "POST", `/api/v1/import/${id}/reject`);
    }
    // 正常拆解（三步驟鏈；第二步帶評估指令、其餘沒有通過標準 → 佔位字串＋警告）
    const id = await newRecord("把使用者登入功能做完");
    const ok = await parse(id);
    expect(ok.status, JSON.stringify(ok.json).slice(0, 300)).toBe(200);
    type PathC = {
      path: string;
      aiModel?: string | null;
      tokenUsed?: number | null;
      reasoning?: string;
      warnings: Array<{ code: string }>;
      parsedResult: { draftIds: string[]; goals: Array<{ tasks: Array<{ name: string; evaluatorCommand?: string | null; passCriteriaSpec?: { source: string; draftId: string } }> }> };
    };
    const d = dataOf<PathC>(ok);
    expect(d.path).toBe("DECOMPOSE");
    expect([d.aiModel ?? null, d.tokenUsed ?? null]).toEqual([null, null]);
    expect(d.reasoning).toBe("QA 假 Brain 的拆解理由");
    expect(d.parsedResult.draftIds).toHaveLength(1);
    const tasks = d.parsedResult.goals[0].tasks;
    expect(tasks.map((t) => t.name)).toEqual(["步驟 1", "步驟 2", "步驟 3"]);
    expect(tasks[1].evaluatorCommand).toBe("python --version");
    expect(tasks.every((t) => t.passCriteriaSpec?.source === "decompose" && t.passCriteriaSpec.draftId === d.parsedResult.draftIds[0])).toBe(true);
    expect(d.warnings.filter((w) => w.code === "passcriteria_placeholder")).toHaveLength(2);
    expect(llm.count(), "路徑 C 走 Bridge 的 Brain，不呼叫 Console 設定的模型端點").toBe(callsBefore);
    // 🔴 signoff 硬閘：signoff 之前 Bridge 的草案是未批准；signoff 時 Console 才呼叫 Bridge approve（草案檔記下 approver）
    const draftFile = path.join(E2E_ROOT, "workspace", "_drafts", `${d.parsedResult.draftIds[0].replaceAll("-", "")}.json`);
    const draft = () => JSON.parse(readFileSync(draftFile, "utf-8")) as { signed_off: boolean; approver: string };
    expect(draft()).toMatchObject({ signed_off: false });
    const early = await call(request, "operator", "POST", `/api/v1/import/${id}/confirm`);
    expect([early.status, early.json.reason]).toEqual([409, "草案尚未 signoff，不可確認匯入"]);
    expect(draft().signed_off, "confirm 被擋下時 Bridge 草案仍未批准").toBe(false);
    expect((await call(request, "operator", "POST", `/api/v1/import/${id}/signoff`, { approver: "e2e-approver" })).status).toBe(200);
    expect(draft()).toMatchObject({ signed_off: true, approver: "e2e-approver" });
    const confirm = await call(request, "operator", "POST", `/api/v1/import/${id}/confirm`);
    expect(confirm.status).toBe(201);
    expect(dataOf(confirm)).toMatchObject({ status: "DRAFT", goalsCount: 1, tasksCount: 3, autonomyLevel: 4, executionPath: dir, signedOff: true });
    // 匯入的專案可被引擎執行（執行類情境要求 apiKey 為空）
    expect((await call(request, "admin", "POST", "/api/v1/settings/model/apiKey/reset?confirm=true")).status).toBe(200);
    await ensureQuota(request, "operator", 30);
    const started = await call(request, "operator", "POST", `/api/v1/projects/${dataOf<{ id: string }>(confirm).id}/execute`, { autonomyLevel: 4, tokenBudget: 100000, scope: { mode: "ALL" } });
    expect(started.status, JSON.stringify(started.json).slice(0, 300)).toBe(201);
    const run = await waitRun(request, dataOf<{ id: string }>(started).id, ["COMPLETED", "FAILED", "CANCELLED"], 120_000);
    expect(run, `run 終態＝${run.status}；reason＝${run.reason}`).toMatchObject({ status: "COMPLETED", completedSteps: 3, totalSteps: 3, totalTokensUsed: 3720 });
  });

  test("DEF-AC-001（W5 已修）：AI 解析結果裡值為 null 的欄位（maxRetries 等）在節點編輯對話框不得顯示成字面「null」，樹狀預覽也不印「最大重試次數：null」", async ({ page, request }) => {
    // 契約 §0.2：client 視 null 與缺席等價。真後端對 AI 解析的任務回 maxRetries／evaluatorCommand／expectedOutputRegex 皆為 null；
    // W4 的 NodeEditDialog 用 `=== undefined` 判斷空值，把 null 變成「null」並讓 zod 驗證（0～20 的整數）擋住「確定」（QA 報告 DEF-AC-001）。
    // W5-FE 改判 `== null`；本情境在 W5-QA 移除了 test.fail，改為正向斷言（E2E_DEFECTS_FIXED 不再需要）。
    const projectDir = path.join(E2E_ROOT, "projects", `imp-def001-${RUN}`);
    mkdirSync(projectDir, { recursive: true });
    const created = await call(request, "operator", "POST", "/api/v1/import/text", { content: brd(), sourceFileName: `def001-${RUN}.md`, sourceType: "MARKDOWN" });
    expect(created.status).toBe(201);
    const id = dataOf<{ id: string }>(created).id;
    const parsed = await call(request, "operator", "POST", `/api/v1/import/${id}/parse`, { executionPath: projectDir, autonomyLevel: 3 });
    expect(parsed.status).toBe(200);
    try {
      await signIn(page, request, "operator");
      await page.goto(`/import?id=${id}`);
      await expect(page.getByTestId("import-step2")).toBeVisible(FIRST_LOAD);
      // 樹狀預覽：maxRetries 為 null 的任務不印「最大重試次數」（W4 版印成「最大重試次數：null」）
      await expect(page.getByTestId("import-tree")).not.toContainText("null");
      await page.getByRole("button", { name: "編輯任務：設定" }).click();
      const dialog = page.getByRole("dialog", { name: "編輯任務" });
      const retries = dialog.getByLabel("最大重試次數");
      await expect(retries).toBeVisible();
      await expect(retries).toHaveValue(""); // W4：字面 "null"
      // 不改任何欄位就能按「確定」關閉對話框（W4：zod 擋住），且不算未儲存的編輯
      await dialog.getByRole("button", { name: "確定" }).click();
      await expect(dialog).toHaveCount(0);
      await expect(page.getByTestId("dirty-notice")).toHaveCount(0);
    } finally {
      await call(request, "operator", "POST", `/api/v1/import/${id}/reject`); // 不留待簽核的草案
    }
  });

  test("唯讀角色（VIEWER）：看得到頁面與歷史，但拖放區、欄位與開始解析全部停用；後端對 viewer 寫入 403", async ({ page, request }) => {
    await signIn(page, request, "viewer");
    await page.goto("/import");
    await expect(page.getByTestId("import-dropzone")).toBeVisible(FIRST_LOAD);
    await expect(page.getByTestId("import-dropzone")).toBeDisabled();
    await expect(page.getByRole("button", { name: "開始解析" })).toBeDisabled();
    await expect(page.getByLabel("執行路徑")).toBeDisabled();
    await page.getByRole("tab", { name: "歷史記錄" }).click();
    await expect(page.getByTestId("import-history-panel")).toBeVisible();
    await snap(page, "p3-import-viewer.png");
    const denied = await call(request, "viewer", "POST", "/api/v1/import/text", { content: "x" });
    expect(denied.status).toBe(403);
    expect(denied.json.reason).toBe("ACCESS_DENIED");
  });
});
