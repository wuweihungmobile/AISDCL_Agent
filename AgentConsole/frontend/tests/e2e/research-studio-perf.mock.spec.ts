import { expect, test, type Page, type TestInfo } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";

import { eventPage, EVENTS } from "../fixtures/research/events";
import { fsmView } from "../fixtures/research/fsm";
import { R2, sha } from "../fixtures/research/ids";
import { CAPABILITIES_LOCAL } from "../fixtures/research/misc";
import { detailVariant, PROJECT_LIST } from "../fixtures/research/projects";
import { FAIL3_SCORES, defect, makeRound } from "../fixtures/research/reviews";
import { formatViolations, type AxeFinding } from "./a11y";
import { collectConsoleErrors, compose, installApiMock, shellHandler, signInAs, type MockHandler } from "./mockApi";

/**
 * 工作室效能量測（TCS-ResearchToPRD-P0-20261102 AT-960-17-1；AC-R2P-09-8；ADR-003 D9）——route mock 版，真瀏覽器（Chromium）對 production 建置：
 * 載入一份 200KB 的 PRD（`genPrd` 以固定種子在測試時產生、不入庫）與其稍改版本，量三件事（量測值逐字落進 `testInfo.outputPath` 的 JSON 與主控台的 `[perf]` 行，供證據與 ADR-003 §D9 引用）：
 *  ① 輸入延遲：在編輯器輸入 50 個字元，每鍵量「keydown → 下一次畫面更新」（輸入事件處理完、下一個影格繪製之後）的毫秒數；3 輪共 150 鍵，
 *     門檻：150 鍵合併的 P95 與三輪各自 P95 的中位數都小於 100 毫秒（單輪的離群值不致讓整支紅，也不會被合併掩蓋）；
 *  ② Diff 計算：切到 Diff 模式，取元件自量的 `data-diff-ms`（`diff` 函式庫逐行比對＋展開逐行結果；門檻：小於 1 秒）；另量「點分頁到差異畫完」的端到端時間（參考）；
 *  ③ 預覽首次渲染：切到預覽，量「點分頁到第一批區塊畫出」（門檻：不超過 2 秒）與「全部區塊畫完」（參考；分批渲染排在瀏覽器閒置時）。
 * 預覽與 Diff 各做 5 次切換（第 1 次含延遲載入的 chunk＝冷啟動，其後為熱），報告取中位數與最大值；輸入延遲在最後量（會改動編輯中的內容）。
 * 第二支量「編輯器套件」（`MarkdownEditor`，左右分欄的即時預覽）的輸入延遲隨文件大小成長的情形，作為「超過 RICH_EDIT_MAX_BYTES 改用精簡輸入框」這個門檻的實測依據。
 * 這支**不斷言絕對毫秒數**（本 spec 在 GitHub 的 ubuntu runner 上也會跑，那台比量測機慢兩三倍，絕對值只屬於量測機、已寫進 StudioPanel.tsx 的註解與報告），
 * 只斷言與機器無關的事實：每個大小都真的量到 50 鍵、編輯器套件的延遲隨文件大小成長（最大的大小至少是最小的 1.3 倍）——它變得與大小無關時，這個門檻就該重新評估。
 * 大小清單預設 10、30、60（KB），本機要完整的表格就設 `E2E_PERF_SIZES_KB=10,20,30,40,60`；門檻值取自 StudioPanel.tsx 的原始碼（不寫第二份），一定會一併量。
 * 同一支檔另有三組「真瀏覽器」的驗證（jsdom 做不到：沒有排版、沒有真的 CSS 與 matchMedia、mermaid 在單元測試裡是替身）：
 *  - AT_960_16_1 版面：1440 三欄並排、視窗即時縮到 1000 左欄收成圖示、再縮到 600 改分頁籤；三個模式切得過去；axe 掃描（只掃工作室面板，WCAG 2.0／2.1 A 與 AA，有負控）八個狀態零違規；
 *  - AT_960_16_3 Mermaid：真函式庫＋production 建置，預覽合法圖／語法錯誤／含 script、click 回呼與外部圖片網址的圖——不執行任何東西、不對外發任何請求。
 * 量測機規格（CPU、核數、記憶體、作業系統、瀏覽器版本）一併寫入報告。跑法（cwd＝AgentConsole/frontend；先 npm run build，standalone 產物）：
 *   $env:E2E_MODE="standalone"; $env:E2E_WEB_PORT="3207"; npx playwright test tests/e2e/research-studio-perf.mock.spec.ts -g AT_960_17_1 --output=<各自目錄>
 * 不需要後端與資料庫；不連任何外部網路。
 */

// ── 夾具：200KB PRD 與其稍改版本 ─────────────────────────────────────────────────────────

/** 固定種子的偽隨機（mulberry32）：同一個種子在任何機器上產生同一份文件。 */
function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const TERMS = [
  "向量索引",
  "近似最近鄰",
  "召回率",
  "查詢延遲",
  "寫入吞吐",
  "資料分片",
  "副本同步",
  "一致性模型",
  "備援切換",
  "維運成本",
  "授權條款",
  "資料落地",
  "權限控管",
  "稽核紀錄",
  "批次匯入",
  "冷熱分層",
];
const VERBS = ["必須支援", "應該提供", "需要評估", "不得依賴", "可以選用", "建議採用"];

/**
 * 約 `targetBytes` 位元組的 PRD（UTF-8，恰好等於 `targetBytes`）：標題與子標題、含 `[E-NNN]` 引用的段落、清單、GFM 表格與程式碼圍欄混合——
 * 與真實 PRD 同形（預覽的渲染成本主要在這些元素），不含 Mermaid 圍欄（圖的渲染另有延遲載入與 3 秒逾時，不屬於這支量測）。
 */
function genPrd(targetBytes: number, seed: number): string {
  const r = rng(seed);
  const pick = <T>(xs: readonly T[]): T => xs[Math.floor(r() * xs.length)];
  const sentence = () => `${pick(TERMS)}${pick(VERBS)}${pick(TERMS)}，並以${pick(TERMS)}作為驗收依據 [E-${String(1 + Math.floor(r() * 40)).padStart(3, "0")}]。`;
  const paragraph = () => Array.from({ length: 3 + Math.floor(r() * 3) }, sentence).join("");
  const section = (i: number): string[] => {
    const out: string[] = [`<!-- r2p:section=${((i - 1) % 6) + 1} -->`, `## ${i}. ${pick(TERMS)}與${pick(TERMS)}`, "", paragraph(), ""];
    for (let k = 1; k <= 3; k += 1) {
      out.push(`### ${i}.${k} ${pick(TERMS)}`, "", paragraph(), "");
      if (k === 2) out.push(...Array.from({ length: 5 }, () => `- ${sentence()}`), "");
      if (k === 3) {
        out.push("| 項目 | 現況 | 目標 |", "| --- | --- | --- |", ...Array.from({ length: 4 }, () => `| ${pick(TERMS)} | ${Math.floor(r() * 90) + 10} 毫秒 | ${Math.floor(r() * 9) + 1} 毫秒 |`), "");
        out.push(
          "```gherkin",
          `Feature: ${pick(TERMS)}`,
          `  Scenario: ${pick(TERMS)}${pick(VERBS)}`,
          `    Given ${pick(TERMS)}已就緒`,
          `    When 使用者送出${pick(TERMS)}`,
          `    Then 系統回應不超過 ${Math.floor(r() * 9) + 1} 秒`,
          "```",
          "",
        );
      }
    }
    return out;
  };
  const lines: string[] = ["# PRD — 向量資料庫選型（效能量測用夾具）", ""];
  let bytes = Buffer.byteLength(lines.join("\n"));
  // 加一段（前面接一個換行）；加了會超過「目標減 80」就不加，回 false
  const add = (chunk: string[]): boolean => {
    const size = Buffer.byteLength(`\n${chunk.join("\n")}`);
    if (bytes + size > targetBytes - 80) return false;
    lines.push(...chunk);
    bytes += size;
    return true;
  };
  let next = 1;
  while (add(section(next))) next += 1;
  let filled = true;
  while (filled) filled = add(["", sentence()]);
  // 收尾：「附註：」之後補 ASCII，湊到恰好 targetBytes
  const head = `${lines.join("\n")}\n附註：`;
  const pad = targetBytes - Buffer.byteLength(head);
  if (pad < 1) throw new Error(`夾具超過目標大小 ${targetBytes}`);
  return `${head}${"a".repeat(pad)}`;
}

/** 稍改版本：約 1.5% 的行換一個詞、約 1% 的行刪掉、約 0.8% 的行後面插一行新的（只動內文行，不動標題）。 */
function tweak(doc: string): string {
  const out: string[] = [];
  doc.split("\n").forEach((line, i) => {
    const heading = /^(#|<!--|\||```)/.test(line) || line === "";
    if (!heading && i % 67 === 7) out.push(line.replace("必須支援", "應該提供"));
    else if (!heading && i % 97 === 3) return;
    else out.push(line);
    if (!heading && i % 127 === 5) out.push(`（新增的一行 ${i}）`);
  });
  return out.join("\n");
}

const PRD_BYTES = 200 * 1024;
const V2 = genPrd(PRD_BYTES, 20261102);
const V1 = tweak(V2);

const versionRow = (versionNo: number, content: string) => ({
  versionNo,
  semver: `v0.${versionNo}.0-draft`,
  kind: "DRAFT",
  authorKind: "AGENT",
  author: "spec-engineer",
  parentVersionNo: versionNo === 1 ? null : versionNo - 1,
  sha256: sha(String(versionNo)),
  bytes: Buffer.byteLength(content),
  evidenceRefs: ["E-001", "E-002"],
  changeSummary: versionNo === 1 ? "初稿" : "依審查修訂",
  createdAt: "2026-11-02T10:00:00+08:00",
});

const ROUND = makeRound(1, FAIL3_SCORES[0], 2, { defects: [defect(1, 1)] });
const configRow = (key: string, value: string) => ({ id: `cfg-${key}`, category: "execution", key, value, valueType: "LONG", isEncrypted: false, hasValue: true, effect: "CONSOLE" });

/** 研究端點的 mock（只列工作室步驟會打的 GET；寫入端點這支量測不碰）。 */
const researchBackend: MockHandler = (call) => {
  if (call.method !== "GET") return undefined;
  const p = call.path;
  const base = `/api/v1/research/projects/${R2}`;
  if (p === "/api/v1/research/capabilities") return { data: CAPABILITIES_LOCAL };
  if (p === "/api/v1/research/allowlist") return { data: [] };
  if (p === "/api/v1/research/projects") return { data: call.query.get("archived") === "true" ? [] : PROJECT_LIST };
  if (p === "/api/v1/settings/execution") return { data: [configRow("globalTokenBudget", "1000000"), configRow("tokenBudgetWarningThreshold", "0.8")] };
  if (p === base) return { data: detailVariant("studio") };
  if (p === `${base}/events`) return { data: eventPage(EVENTS, Number(call.query.get("afterSeq") ?? 0), Number(call.query.get("limit") ?? 500)) };
  if (p === `${base}/prd/versions`) return { data: [versionRow(1, V1), versionRow(2, V2)] };
  if (p === `${base}/prd/versions/1`) return { data: { ...versionRow(1, V1), content: V1 } };
  if (p === `${base}/prd/versions/2`) return { data: { ...versionRow(2, V2), content: V2 } };
  if (p === `${base}/review-rounds`) return { data: [ROUND] };
  if (p === `${base}/fsm`) return { data: fsmView("SPEC_DRAFTING", {}, 1) };
  // 串流：回 204（契約：終態批次）＝瀏覽器放棄連線，動態資料改走 REST；這支量測不需要即時事件
  if (p.startsWith("/api/v1/stream/research/")) return { status: 204 };
  return undefined;
};

// ── 量測工具 ─────────────────────────────────────────────────────────────────────────────

const percentile = (xs: readonly number[], p: number): number => {
  const sorted = [...xs].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.ceil(p * sorted.length) - 1)];
};
const median = (xs: readonly number[]): number => {
  const sorted = [...xs].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
};
const round1 = (x: number): number => Math.round(x * 10) / 10;

type Typing = { count: number; p95: number; median: number; max: number; longTasks: number; slowEvents: number };
/** 一輪輸入的結果：統計（落報告）與每鍵的原始延遲（合併多輪算 P95 用）。 */
type TypingRun = Typing & { samples: number[] };
const stats = (run: TypingRun): Typing => ({ count: run.count, p95: run.p95, median: run.median, max: run.max, longTasks: run.longTasks, slowEvents: run.slowEvents });

/** 在頁面內裝輸入延遲探針：keydown 記起點，input 之後等「下一個影格繪製完」（rAF 之後的 setTimeout）記終點。 */
async function installTypingProbe(page: Page): Promise<void> {
  await page.evaluate(() => {
    const w = window as unknown as { __lat: number[]; __long: number; __slow: number; __typingProbe?: boolean };
    w.__lat = [];
    w.__long = 0;
    w.__slow = 0;
    if (w.__typingProbe) return;
    w.__typingProbe = true;
    let t0 = 0;
    document.addEventListener("keydown", () => (t0 = performance.now()), true);
    document.addEventListener(
      "input",
      () => {
        const start = t0;
        requestAnimationFrame(() => setTimeout(() => w.__lat.push(performance.now() - start), 0));
      },
      true,
    );
    try {
      new PerformanceObserver((list) => (w.__long += list.getEntries().length)).observe({ type: "longtask" });
    } catch {
      // 不支援 longtask：只少一欄參考資料
    }
    try {
      new PerformanceObserver((list) => (w.__slow += list.getEntries().length)).observe({ type: "event", durationThreshold: 16 } as PerformanceObserverInit);
    } catch {
      // 不支援 Event Timing：同上
    }
  });
}

/** 把游標放到文字區的正中間（最壞情況之一：不在尾端也不在開頭），輸入 `count` 個字元，回每鍵延遲的統計。 */
async function typeInMiddle(page: Page, textarea: ReturnType<Page["locator"]>, count: number): Promise<TypingRun> {
  await installTypingProbe(page);
  await page.evaluate(() => {
    const w = window as unknown as { __lat: number[]; __long: number; __slow: number };
    w.__lat.length = 0;
    w.__long = 0;
    w.__slow = 0;
  });
  await textarea.evaluate((el) => {
    const area = el as HTMLTextAreaElement;
    area.focus();
    const mid = Math.floor(area.value.length / 2);
    area.setSelectionRange(mid, mid);
    area.scrollTop = Math.max(0, (area.scrollHeight - area.clientHeight) / 2);
  });
  await page.keyboard.type("abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwx".slice(0, count), { delay: 60 });
  await page.waitForFunction((n) => (window as unknown as { __lat: number[] }).__lat.length >= n, count, { timeout: 60_000 });
  const got = await page.evaluate(() => {
    const w = window as unknown as { __lat: number[]; __long: number; __slow: number };
    return { lat: [...w.__lat], long: w.__long, slow: w.__slow };
  });
  return {
    count: got.lat.length,
    p95: round1(percentile(got.lat, 0.95)),
    median: round1(median(got.lat)),
    max: round1(Math.max(...got.lat)),
    longTasks: got.long,
    slowEvents: got.slow,
    samples: got.lat,
  };
}

type ModeSample = { previewFirst: number | null; previewAll: number | null; blocks: number; diffShown: number | null; diffMs: number | null; diffEngine: string | null; longTasks: number[] };

/** 頁面內的模式切換探針：每次點擊（捕獲階段）重設起點；預覽與 Diff 畫出的當下（下一個影格繪製之後）記終點。 */
async function installModeProbe(page: Page): Promise<void> {
  await page.evaluate(() => {
    const w = window as unknown as { __mode: ModeSample & { t0: number } };
    const fresh = (): ModeSample & { t0: number } => ({ t0: performance.now(), previewFirst: null, previewAll: null, blocks: 0, diffShown: null, diffMs: null, diffEngine: null, longTasks: [] });
    w.__mode = fresh();
    const settle = (fn: () => void) => requestAnimationFrame(() => setTimeout(fn, 0));
    const check = () => {
      const p = w.__mode;
      const preview = document.querySelector('[data-testid="prd-preview"]');
      if (preview !== null) {
        const rendered = Number(preview.getAttribute("data-rendered"));
        p.blocks = Number(preview.getAttribute("data-blocks"));
        if (p.previewFirst === null && rendered > 0) {
          p.previewFirst = -1;
          settle(() => (p.previewFirst = performance.now() - p.t0));
        }
        if (p.previewAll === null && rendered > 0 && rendered === p.blocks) {
          p.previewAll = -1;
          settle(() => (p.previewAll = performance.now() - p.t0));
        }
      }
      const diff = document.querySelector('[data-testid="prd-diff"]');
      if (diff !== null && p.diffShown === null && document.querySelector('[data-testid="diff-summary"]') !== null) {
        p.diffShown = -1;
        p.diffMs = Number(diff.getAttribute("data-diff-ms"));
        p.diffEngine = diff.getAttribute("data-diff-engine");
        settle(() => (p.diffShown = performance.now() - p.t0));
      }
    };
    document.addEventListener("click", () => (w.__mode = fresh()), true);
    new MutationObserver(check).observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ["data-rendered", "data-diff-ms"] });
    try {
      new PerformanceObserver((list) => list.getEntries().forEach((e) => w.__mode.longTasks.push(e.duration))).observe({ type: "longtask" });
    } catch {
      // 不支援 longtask：只少一欄參考資料
    }
  });
}

const readMode = (page: Page): Promise<ModeSample> => page.evaluate(() => structuredClone((window as unknown as { __mode: ModeSample }).__mode));

function machine(testInfo: TestInfo, browserVersion: string) {
  const cpus = os.cpus();
  return {
    cpu: cpus[0]?.model ?? "unknown",
    logicalCores: cpus.length,
    memoryGB: Math.round((os.totalmem() / 1024 ** 3) * 10) / 10,
    os: `${os.platform()} ${os.release()}`,
    node: process.version,
    browser: `Chromium ${browserVersion}`,
    project: testInfo.project.name,
    viewport: "1440x900",
  };
}

const requireFromApp = createRequire(path.join(process.cwd(), "package.json"));

/**
 * 只掃工作室面板（`studio-panel`）的 axe 掃描（WCAG 2.0／2.1 A 與 AA；做法同 `a11y.ts` 的 `axeViolations`，但範圍收到本包的元件）：
 * 共用的輔助掃整頁，會把頁面其他部分（例如步驟列）的違規算進來，那不是這個測試要守的面；範圍收窄是「這支測試的主題就是工作室」，不是壓制——
 * 整頁掃描仍由 a11y.mock.spec.ts 與各頁自己的 spec 負責。
 */
async function expectStudioA11y(page: Page, label: string): Promise<void> {
  const axeSource = readFileSync(requireFromApp.resolve("axe-core/axe.min.js"), "utf-8");
  const original = page.viewportSize();
  if (original) await page.setViewportSize({ width: original.width, height: Math.max(original.height, 2400) });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.mouse.move(0, 0);
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running"), undefined, { timeout: 5000 }).catch(() => undefined);
  try {
    await page.evaluate(axeSource);
    const findings: AxeFinding[] = await page.evaluate(async () => {
      type Raw = { id: string; impact?: string | null; help: string; nodes: Array<{ target: unknown[]; html: string; failureSummary?: string }> };
      const axe = (window as unknown as { axe: { run: (ctx: unknown, opts: unknown) => Promise<{ violations: Raw[] }> } }).axe;
      const result = await axe.run({ include: [['[data-testid="studio-panel"]']] }, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] } });
      return result.violations.map((v) => ({
        id: v.id,
        impact: v.impact ?? null,
        help: v.help,
        nodes: v.nodes.map((n) => ({ target: n.target.map(String).join(" "), html: n.html.slice(0, 160), summary: (n.failureSummary ?? "").replace(/\s+/g, " ").slice(0, 220) })),
      }));
    });
    expect(findings, `${label}：無障礙違規\n${formatViolations(findings)}`).toEqual([]);
  } finally {
    await page.emulateMedia({ reducedMotion: null });
    if (original) await page.setViewportSize(original);
  }
}

function writeReport(testInfo: TestInfo, name: string, report: unknown): void {
  const file = testInfo.outputPath(name);
  writeFileSync(file, `${JSON.stringify(report, null, 2)}\n`, "utf-8");
  // 逐字落在主控台：證據與 ADR-003 §D9 直接引用這一行
  console.log(`[perf] ${name} ${JSON.stringify(report)}`);
}

// ── 測試 ─────────────────────────────────────────────────────────────────────────────────

test.describe("AT_960_17_1 工作室效能量測（200KB PRD；route mock；真瀏覽器）", () => {
  test("AT_960_17_1 200KB：預覽首次渲染不超過 2 秒、Diff 計算小於 1 秒、輸入延遲 P95 小於 100 毫秒（量測值與機器規格落報告）", async ({ page, browser }, testInfo) => {
    test.setTimeout(300_000);
    expect(Buffer.byteLength(V2), "夾具恰為 200KB（位元組）").toBe(PRD_BYTES);
    expect(V1).not.toBe(V2);
    const errors = collectConsoleErrors(page);
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(shellHandler(), researchBackend));
    await page.goto(`/research/${R2}?step=studio`);
    const textarea = page.getByTestId("prd-textarea");
    await expect(textarea, "超過精簡編輯器門檻：編輯器是純文字輸入框").toBeVisible({ timeout: 60_000 });
    await expect(textarea).toHaveValue(V2);
    await expect(page.getByTestId("gatekeeper-panel")).toBeVisible();
    await installModeProbe(page);

    // ② 預覽、③ Diff：各 5 次切換（第 1 次含延遲載入的 chunk）
    const previews: ModeSample[] = [];
    const diffs: ModeSample[] = [];
    let domNodesInPreview = 0;
    for (let i = 0; i < 5; i += 1) {
      await page.getByRole("tab", { name: "預覽" }).click();
      await page.waitForFunction(
        () => (window as unknown as { __mode: ModeSample }).__mode.previewAll !== null && ((window as unknown as { __mode: ModeSample }).__mode.previewAll ?? -1) >= 0,
        undefined,
        {
          timeout: 120_000,
        },
      );
      previews.push(await readMode(page));
      if (i === 0) domNodesInPreview = await page.evaluate(() => document.querySelectorAll("*").length);
      await page.getByRole("tab", { name: "編輯" }).click();
      await expect(textarea).toBeVisible();
      await page.getByRole("tab", { name: "Diff" }).click();
      await page.waitForFunction(() => ((window as unknown as { __mode: ModeSample }).__mode.diffShown ?? -1) >= 0, undefined, { timeout: 60_000 });
      diffs.push(await readMode(page));
      await page.getByRole("tab", { name: "編輯" }).click();
      await expect(textarea).toBeVisible();
      await page.waitForTimeout(300);
    }

    // ① 輸入延遲：3 輪，每輪 50 個字元（最後量；輸入會改動編輯中的內容）
    const runs: TypingRun[] = [];
    for (let i = 0; i < 3; i += 1) {
      runs.push(await typeInMiddle(page, textarea, 50));
      await page.waitForTimeout(300);
    }
    const pooledP95 = round1(
      percentile(
        runs.flatMap((r) => r.samples),
        0.95,
      ),
    );
    const p95PerRunMedian = round1(median(runs.map((r) => r.p95)));

    const previewFirst = previews.map((s) => s.previewFirst as number);
    const previewAll = previews.map((s) => s.previewAll as number);
    const diffMs = diffs.map((s) => s.diffMs as number);
    const diffShown = diffs.map((s) => s.diffShown as number);
    const report = {
      at: "AT-960-17-1",
      machine: machine(testInfo, browser.version()),
      fixture: { v2Bytes: Buffer.byteLength(V2), v1Bytes: Buffer.byteLength(V1), lines: V2.split("\n").length, blocks: previews[0].blocks, diffEngine: diffs[0].diffEngine },
      typing: {
        keystrokesPerRun: 50,
        runs: runs.map(stats),
        pooledP95Of150: pooledP95,
        p95PerRunMedian,
        p95PerRunMax: round1(Math.max(...runs.map((r) => r.p95))),
        budgetMs: 100,
      },
      diff: {
        trials: diffMs.length,
        computeMsPerTrial: diffMs,
        computeMsMedian: round1(median(diffMs)),
        computeMsMax: round1(Math.max(...diffMs)),
        clickToShownMsMedian: round1(median(diffShown)),
        clickToShownMsMax: round1(Math.max(...diffShown)),
        coldClickToShownMs: round1(diffShown[0]),
        budgetMs: 1000,
      },
      preview: {
        trials: previewFirst.length,
        firstRenderMsPerTrial: previewFirst.map(round1),
        firstRenderMsMedian: round1(median(previewFirst)),
        firstRenderMsMax: round1(Math.max(...previewFirst)),
        coldFirstRenderMs: round1(previewFirst[0]),
        allBlocksMsMedian: round1(median(previewAll)),
        allBlocksMsMax: round1(Math.max(...previewAll)),
        longTasksPerTrial: previews.map((s) => s.longTasks.length),
        longestTaskMs: round1(Math.max(0, ...previews.flatMap((s) => s.longTasks))),
        budgetMs: 2000,
      },
      domNodesInFullPreview: domNodesInPreview,
    };
    writeReport(testInfo, "perf-AT_960_17_1-200KB.json", report);
    await testInfo.attach("perf-AT_960_17_1-200KB.json", { body: JSON.stringify(report, null, 2), contentType: "application/json" });

    expect(pooledP95, `輸入延遲 P95（150 鍵合併；各輪：${JSON.stringify(runs.map(stats))}）`).toBeLessThan(100);
    expect(p95PerRunMedian, "輸入延遲 P95（三輪各自 P95 的中位數）").toBeLessThan(100);
    for (const ms of diffMs) expect(ms, "Diff 計算（元件自量，函式庫逐行比對加展開結果）").toBeLessThan(1000);
    for (const ms of previewFirst) expect(ms, "預覽首次渲染（點分頁到第一批區塊畫出）").toBeLessThanOrEqual(2000);
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("AT_960_17_1 編輯器套件的輸入延遲隨文件大小成長（精簡編輯器門檻 RICH_EDIT_MAX_BYTES 的實測依據；絕對毫秒數只落報告）", async ({ page, browser }, testInfo) => {
    test.setTimeout(480_000);
    // 門檻值唯一出處是 StudioPanel.tsx（這裡只讀它，不寫第二份）
    const source = readFileSync(path.join(process.cwd(), "components", "domain", "research", "StudioPanel.tsx"), "utf-8");
    const match = /export const RICH_EDIT_MAX_BYTES = (\d+) \* 1024;/.exec(source);
    expect(match, "StudioPanel.tsx 要有 RICH_EDIT_MAX_BYTES = N * 1024").not.toBeNull();
    const thresholdKb = Number(match?.[1]);
    const requested = (process.env.E2E_PERF_SIZES_KB ?? "10,30,60")
      .split(",")
      .map((s) => Number(s.trim()))
      .filter((n) => Number.isInteger(n) && n > 0);
    const sizesKb = [...new Set([...requested, thresholdKb])].sort((a, b) => a - b);
    expect(sizesKb.length, "至少量兩個大小（成長才比得出來）").toBeGreaterThanOrEqual(2);

    const errors = collectConsoleErrors(page);
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(shellHandler()));
    const rows: Array<{ sizeKb: number; typing: Typing; withinBudget: boolean }> = [];
    for (const kb of sizesKb) {
      const doc = genPrd(kb * 1024, 1000 + kb);
      await page.goto("/projects");
      await page.getByRole("button", { name: "新建專案" }).click();
      const dialog = page.getByRole("dialog", { name: "新建專案" });
      const box = dialog.getByRole("textbox", { name: "說明描述", exact: true });
      await box.fill(doc);
      await expect(dialog.locator(".w-md-editor-preview").first()).toContainText("附註：", { timeout: 120_000 });
      await page.waitForTimeout(500);
      const typing = stats(await typeInMiddle(page, box, 50));
      rows.push({ sizeKb: kb, typing, withinBudget: typing.p95 < 100 });
    }
    const report = { at: "AT-960-17-1（編輯器套件，決定精簡編輯器的門檻）", machine: machine(testInfo, browser.version()), thresholdKb, budgetMs: 100, rows };
    writeReport(testInfo, "perf-AT_960_17_1-rich-editor.json", report);
    await testInfo.attach("perf-AT_960_17_1-rich-editor.json", { body: JSON.stringify(report, null, 2), contentType: "application/json" });

    for (const row of rows) expect(row.typing.count, `${row.sizeKb}KB：量到 50 鍵`).toBe(50);
    const smallest = rows[0];
    const largest = rows[rows.length - 1];
    expect(
      largest.typing.p95,
      `編輯器套件的輸入延遲隨文件大小成長（${smallest.sizeKb}KB：${smallest.typing.p95}ms → ${largest.sizeKb}KB：${largest.typing.p95}ms）；不成長就該重新評估精簡編輯器門檻`,
    ).toBeGreaterThanOrEqual(smallest.typing.p95 * 1.3);
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });
});

/** 三種 Mermaid 圍欄的 PRD：合法圖、語法錯誤、含 `<script>` 與 click 回呼（securityLevel strict 要把它們當成文字、停用回呼）。 */
const MERMAID_DOC = [
  "# 圖表驗證",
  "",
  "## 合法圖",
  "```mermaid",
  "graph TD",
  "  A[需求] --> B[設計]",
  "  B --> C[實作]",
  "```",
  "",
  "## 語法錯誤",
  "```mermaid",
  "graph TD",
  "  A[需求 --> ",
  "```",
  "",
  "## 含腳本與事件",
  "```mermaid",
  "graph TD",
  `  A["<script>window.__mm = 'script'</script>"] --> B`,
  "  click A call window.__mmClick()",
  `  B["<img src='https://evil.example/pixel.png' onerror=window.__mm='img'>"]`,
  "```",
].join("\n");
const diagramBackend: MockHandler = (call) => {
  if (call.method !== "GET") return undefined;
  const match = new RegExp(`^/api/v1/research/projects/${R2}/prd/versions/(\\d+)$`).exec(call.path);
  return match === null ? undefined : { data: { ...versionRow(Number(match[1]), MERMAID_DOC), content: MERMAID_DOC } };
};

test.describe("AT_960_16_3 真瀏覽器的 Mermaid（真函式庫、production 建置）", () => {
  test("AT_960_16_3 預覽裡的三種圖：合法圖畫成 SVG、語法錯誤顯示訊息與原始碼、含 script 與 click 回呼者不執行任何東西；整頁不崩潰、主控台沒有錯誤", async ({ page }, testInfo) => {
    test.setTimeout(120_000);
    const errors = collectConsoleErrors(page);
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(shellHandler(), diagramBackend, researchBackend));
    // 預覽一張圖不該對外發任何請求（圖內文字是 AI 產生的、可能來自不可信的網頁內容；外送網址＝資料外洩管道）
    const outbound: string[] = [];
    await page.route("https://evil.example/**", async (route) => {
      outbound.push(route.request().url());
      await route.abort();
    });
    await page.goto(`/research/${R2}?step=studio`);
    await expect(page.getByTestId("rich-editor-stub").or(page.locator(".w-md-editor-text-input")).first()).toBeVisible({ timeout: 60_000 });
    await page.getByRole("tab", { name: "預覽" }).click();
    const blocks = page.getByTestId("mermaid-block");
    await expect(blocks).toHaveCount(3, { timeout: 60_000 });
    // 三張圖都在 3 秒渲染逾時內有了結果（不是停在「渲染中」）
    await expect(blocks.nth(0)).toHaveAttribute("data-state", "ready", { timeout: 30_000 });
    await expect(blocks.nth(1)).toHaveAttribute("data-state", "error", { timeout: 30_000 });
    await expect(blocks.nth(2)).not.toHaveAttribute("data-state", "loading", { timeout: 30_000 });

    // 合法圖：SVG 在區域內、內含節點文字；附原始碼文字替代
    const canvas = blocks.nth(0).getByTestId("mermaid-canvas");
    await expect(canvas.locator("svg")).toHaveCount(1);
    await expect(canvas.locator("svg")).toContainText("需求");
    await expect(canvas.locator("svg")).toContainText("實作");
    expect(await canvas.locator("svg").evaluate((el) => el.querySelectorAll("script, iframe, [onclick], [onerror]").length), "合法圖的 SVG 沒有可執行節點").toBe(0);
    await expect(blocks.nth(0).locator("details")).toContainText("graph TD");

    // 語法錯誤：訊息與原始碼、其餘兩張不受影響
    await expect(blocks.nth(1).getByTestId("mermaid-error")).not.toBeEmpty();
    await expect(blocks.nth(1).getByTestId("mermaid-source")).toContainText("A[需求 -->");
    await expect(blocks.nth(1).getByTestId("mermaid-canvas")).toBeHidden();

    // 含 script 與 click 回呼：沒有任何腳本執行、輸出裡沒有可執行節點
    await page.waitForTimeout(500);
    const fired = await page.evaluate(() => (window as unknown as { __mm?: string; __mmClicked?: boolean }).__mm ?? null);
    expect(fired, "沒有任何腳本執行").toBeNull();
    const hostile = blocks.nth(2);
    expect(await hostile.evaluate((el) => el.querySelectorAll("script, iframe, [onclick], [onerror], [srcdoc]").length), "第三張圖的輸出沒有可執行節點").toBe(0);
    expect(await hostile.evaluate((el) => el.querySelectorAll("img, image, video, audio, picture, source, [src], [srcset]").length), "第三張圖的輸出沒有會載入外部資源的節點").toBe(0);
    expect(outbound, "預覽這三張圖沒有對外發任何請求").toEqual([]);
    const anyNode = hostile.getByTestId("mermaid-canvas").locator("g.node, .node").first();
    if ((await hostile.getAttribute("data-state")) === "ready" && (await anyNode.count()) > 0) {
      await anyNode.click({ force: true }); // click 回呼已停用：點節點不會呼叫 window.__mmClick
    }
    expect(await page.evaluate(() => (window as unknown as { __mm?: string }).__mm ?? null), "點節點之後仍沒有任何腳本執行").toBeNull();

    // 頁面其餘部分照常：審批欄與目錄還在，可以切回編輯
    await page.screenshot({ path: testInfo.outputPath("mermaid-three-blocks.png") });
    await blocks.nth(0).screenshot({ path: testInfo.outputPath("mermaid-valid-block.png") });
    testInfo.annotations.push({ type: "states", description: JSON.stringify(await blocks.evaluateAll((els) => els.map((el) => el.getAttribute("data-state")))) });
    await expect(page.getByTestId("gatekeeper-panel")).toBeVisible();
    await page.getByRole("tab", { name: "編輯" }).click();
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });
});

test.describe("AT_960_16_1 工作室版面（route mock；真瀏覽器）", () => {
  test("AT_960_16_1 真瀏覽器的響應式版面：1440 三欄並排；視窗即時縮到 1000 左欄收成圖示；再縮到 600 改分頁籤一次顯示一個（jsdom 的單元測試以 matchMedia 替身驗行為，這裡驗真的 CSS 與 matchMedia）", async ({
    page,
  }, testInfo) => {
    test.setTimeout(120_000);
    const errors = collectConsoleErrors(page);
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(shellHandler(), researchBackend));
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`/research/${R2}?step=studio`);
    await expect(page.getByTestId("prd-textarea")).toBeVisible({ timeout: 60_000 });
    const studio = page.getByTestId("studio-panel");
    const box = async (id: string) => {
      const found = await page.getByTestId(id).boundingBox();
      if (found === null) throw new Error(`${id} 沒有排版方塊（被隱藏？）`);
      return found;
    };
    // 截圖只落在這次執行的輸出目錄（`--output`），不進 repo（tests/e2e/__screenshots__ 是既有 spec 的提交證據，不在本包允許集合內）
    const shot = async (name: string) => {
      const file = testInfo.outputPath(name);
      await page.screenshot({ path: file });
      await testInfo.attach(name, { path: file, contentType: "image/png" });
    };

    // 1440：三欄並排（目錄、編輯器、審批由左到右、頂端對齊）
    await expect(studio).toHaveAttribute("data-tier", "wide");
    await expect(page.getByTestId("prd-outline")).toBeVisible();
    await expect(page.getByTestId("prd-editor")).toBeVisible();
    await expect(page.getByTestId("gatekeeper-panel")).toBeVisible();
    const [o1, e1, g1] = [await box("prd-outline"), await box("prd-editor"), await box("gatekeeper-panel")];
    expect(o1.x + o1.width, "目錄在編輯器左邊").toBeLessThanOrEqual(e1.x + 1);
    expect(e1.x + e1.width, "編輯器在審批欄左邊").toBeLessThanOrEqual(g1.x + 1);
    expect(Math.abs(o1.y - e1.y), "目錄與編輯器頂端對齊").toBeLessThan(6);
    expect(Math.abs(g1.y - e1.y), "審批欄與編輯器頂端對齊").toBeLessThan(6);
    await expect(page.getByRole("tab", { name: "目錄" }), "寬螢幕沒有欄位分頁籤").toHaveCount(0);
    await shot("tier-wide-1440.png");
    // 三個模式（編輯、預覽、Diff）在真瀏覽器切得過去、各自畫出內容
    await page.getByRole("tab", { name: "預覽" }).click();
    await expect(page.getByTestId("prd-preview")).toBeVisible();
    await expect(page.getByTestId("prd-block").first()).toBeVisible();
    await shot("mode-preview-1440.png");
    await page.getByRole("tab", { name: "Diff" }).click();
    await expect(page.getByTestId("diff-summary")).toBeVisible();
    await expect(page.getByTestId("diff-row").first()).toBeVisible();
    await shot("mode-diff-1440.png");
    await page.getByRole("tab", { name: "編輯" }).click();
    await expect(page.getByTestId("prd-textarea")).toBeVisible();

    // 1000：同一份頁面即時縮窄（不重新載入）——目錄收成圖示鈕，編輯器與審批欄仍並排
    await page.setViewportSize({ width: 1000, height: 900 });
    await expect(studio).toHaveAttribute("data-tier", "medium");
    await expect(page.getByTestId("prd-outline")).toHaveAttribute("data-collapsed", "true");
    await expect(page.getByRole("button", { name: "展開 PRD 目錄" })).toBeVisible();
    const [o2, e2, g2] = [await box("prd-outline"), await box("prd-editor"), await box("gatekeeper-panel")];
    expect(o2.width, "收合的目錄只佔一顆圖示鈕的寬").toBeLessThan(80);
    expect(e2.x + e2.width, "編輯器仍在審批欄左邊").toBeLessThanOrEqual(g2.x + 1);
    await page.getByRole("button", { name: "展開 PRD 目錄" }).click();
    await expect(page.getByTestId("prd-outline-panel")).toBeVisible();
    expect(await page.getByTestId("outline-item").count(), "收合模式展開後目錄仍可操作").toBeGreaterThan(10);
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("prd-outline-panel")).toBeHidden();
    await shot("tier-medium-1000.png");

    // 600：分頁籤（目錄、編輯器、審批）一次只顯示一個；頁面沒有橫向捲動
    await page.setViewportSize({ width: 600, height: 900 });
    await expect(studio).toHaveAttribute("data-tier", "narrow");
    for (const name of ["目錄", "編輯器", "審批"]) await expect(page.getByRole("tab", { name, exact: true })).toBeVisible();
    await expect(page.getByTestId("prd-editor")).toBeVisible();
    await expect(page.getByTestId("prd-outline")).toBeHidden();
    await expect(page.getByTestId("gatekeeper-panel")).toBeHidden();
    await page.getByRole("tab", { name: "審批", exact: true }).click();
    await expect(page.getByTestId("gatekeeper-panel")).toBeVisible();
    await expect(page.getByTestId("prd-editor")).toBeHidden();
    await shot("tier-narrow-600-review.png");
    await page.getByRole("tab", { name: "目錄", exact: true }).click();
    await expect(page.getByTestId("prd-outline")).toBeVisible();
    await expect(page.getByTestId("gatekeeper-panel")).toBeHidden();
    await page.getByTestId("outline-item").nth(3).click();
    await expect(page.getByTestId("prd-editor"), "選了目錄項：回到編輯器").toBeVisible();
    await expect(page.getByRole("tab", { name: "編輯器", exact: true })).toHaveAttribute("aria-selected", "true");
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, "窄螢幕頁面沒有橫向捲動").toBeLessThanOrEqual(1);

    // 回到 1440：同一份頁面即時回到三欄
    await page.setViewportSize({ width: 1440, height: 900 });
    await expect(studio).toHaveAttribute("data-tier", "wide");
    await expect(page.getByTestId("gatekeeper-panel")).toBeVisible();
    expect(errors, "瀏覽器主控台不應有錯誤").toEqual([]);
  });

  test("AT_960_16_1 真瀏覽器的無障礙掃描（axe；WCAG 2.0／2.1 A 與 AA）：三種寬度、三個模式、收合目錄展開、窄螢幕三個分頁籤皆零違規（色彩對比與可見名稱只有真瀏覽器量得到）", async ({ page }) => {
    test.setTimeout(180_000);
    await signInAs(page, "OPERATOR");
    await installApiMock(page, compose(shellHandler(), diagramBackend, researchBackend));
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`/research/${R2}?step=studio`);
    await expect(page.getByTestId("rich-editor-stub").or(page.getByTestId("prd-textarea")).or(page.locator(".w-md-editor-text-input")).first()).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("review-score")).toBeVisible();

    // 1440 三個模式（預覽含三種 Mermaid 圖：合法、錯誤、含腳本）
    await expectStudioA11y(page, "工作室 1440 編輯模式");
    await page.getByRole("tab", { name: "預覽" }).click();
    await expect(page.getByTestId("mermaid-block")).toHaveCount(3, { timeout: 60_000 });
    for (let i = 0; i < 3; i += 1) await expect(page.getByTestId("mermaid-block").nth(i)).not.toHaveAttribute("data-state", "loading", { timeout: 30_000 });
    await expectStudioA11y(page, "工作室 1440 預覽模式（三種 Mermaid 圖）");
    await page.getByRole("tab", { name: "Diff" }).click();
    await expect(page.getByTestId("diff-summary")).toBeVisible();
    await expectStudioA11y(page, "工作室 1440 Diff 模式");
    await page.getByRole("tab", { name: "編輯" }).click();

    // 1000：收合的目錄展開
    await page.setViewportSize({ width: 1000, height: 900 });
    await expect(page.getByTestId("studio-panel")).toHaveAttribute("data-tier", "medium");
    await expectStudioA11y(page, "工作室 1000 目錄收合");
    await page.getByRole("button", { name: "展開 PRD 目錄" }).click();
    await expect(page.getByTestId("prd-outline-panel")).toBeVisible();
    await expectStudioA11y(page, "工作室 1000 目錄展開");

    // 600：三個分頁籤各掃一次
    await page.setViewportSize({ width: 600, height: 900 });
    await expect(page.getByTestId("studio-panel")).toHaveAttribute("data-tier", "narrow");
    await expectStudioA11y(page, "工作室 600 編輯器分頁");
    await page.getByRole("tab", { name: "審批", exact: true }).click();
    await expect(page.getByTestId("gatekeeper-panel")).toBeVisible();
    await expectStudioA11y(page, "工作室 600 審批分頁");
    await page.getByRole("tab", { name: "目錄", exact: true }).click();
    await expect(page.getByTestId("prd-outline")).toBeVisible();
    await expectStudioA11y(page, "工作室 600 目錄分頁");

    // 負控：在工作室裡注入一段低對比的文字，掃描必須抓到（證明範圍選擇器真的涵蓋工作室、掃描沒有空轉）
    await page.evaluate(() => {
      const span = document.createElement("span");
      span.textContent = "低對比負控";
      span.style.cssText = "color:#bbbbbb;background:#ffffff;font-size:14px";
      document.querySelector('[data-testid="prd-outline"]')?.appendChild(span);
    });
    await expect(expectStudioA11y(page, "負控")).rejects.toThrow(/color-contrast/);
  });
});
