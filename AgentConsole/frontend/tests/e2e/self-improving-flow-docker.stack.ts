import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { expectNoA11yViolations } from "./a11y";
import { call, dataOf, ensureQuota, signIn } from "./realBackend";

/**
 * 自我進化核准流程全程可見（TCS-SiFlowVisibility AC-966-17）——Docker 全棧（拋棄式棧，經 nginx 同源）**實機冒煙，不是每個 commit 的閘**
 * （沿 self-improving-docker.stack.ts 與 research-docker.stack.spec.ts 的形態）。起棧、沙盒快照與收尾步驟見
 * 交棒清單 E2E_FULLSTACK_PLAN.md；本檔只描述「棧已起來之後」要驗的事。
 *
 * 環境變數（缺任何一項＝直接失敗，不略過：TCS §2 禁止 skip）：
 *   E2E_API_URL            nginx 入口（與瀏覽器 baseURL 同源）
 *   E2E_BRIDGE_CONTAINER   engine-bridge 容器名稱
 *   E2E_SI_REPORT_DIR      主機端 console_report 目錄（唯讀掛進 Bridge 的 /si-report；內有「真根層巡邏器在沙盒產生」的 patrol.json）
 *   E2E_SI_SANDBOX_ROOT    沙盒的 AUTOSDD_SI_DIR 根（17-3：掛載來源必須在它底下）
 *   E2E_SI_CANARY          合成評估集哨兵字串（沙盒內 heldout 目錄裡；17-2 斷言它不出現在回應與 DOM）
 *   E2E_REPO_ROOT          （選配）讀 repo 內追蹤檔 docs/06_quality/SelfImproving_Proposals 的根；預設取本檔往上三層（worktree 根）
 * 兩階段（各以 -g 選擇；17-E-1 需要「不設 BRIDGE_SI_REPORT_DIR」的 Bridge，與前三支的 Bridge 不同形態）：
 *   階段 A：-g "AT_966_17_(1|2|3)"；階段 B：重建 Bridge 去掉環境變數與掛載後 -g AT_966_17_E_1。
 */
test.describe.configure({ mode: "serial" });

function need(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`缺環境變數 ${name}（見 E2E_FULLSTACK_PLAN.md；全棧 AT 不得略過）`);
  return v;
}

const BRIDGE = (): string => need("E2E_BRIDGE_CONTAINER");
const REPORT_DIR = (): string => need("E2E_SI_REPORT_DIR");
const REPO_ROOT = (): string => process.env.E2E_REPO_ROOT ?? path.resolve(process.cwd(), "..", "..");
const PATROL_FILE = (): string => path.join(REPORT_DIR(), "patrol.json");

/** 以「寫新檔→rename」覆寫 patrol.json（模擬主機端原子更新）；Windows 上 renameSync 會取代既有檔。 */
function writePatrolAtomically(obj: Record<string, unknown>): void {
  const tmp = `${PATROL_FILE()}.tmp`;
  writeFileSync(tmp, JSON.stringify(obj), { encoding: "utf-8" });
  try {
    renameSync(tmp, PATROL_FILE());
  } catch (error) {
    rmSync(tmp, { force: true });
    throw error;
  }
}

/** 把 generated_at 設成「現在減 minutes 分」（帶 offset），其餘欄位原樣（鍵名是 Bridge 層的 snake_case）。 */
function withGeneratedAt(base: Record<string, unknown>, minutesAgo: number): Record<string, unknown> {
  const gen = new Date(Date.now() - minutesAgo * 60_000).toISOString().replace(/\.\d{3}Z$/, "+00:00");
  return { ...base, generated_at: gen };
}

const docker = (args: string[]): string => execFileSync("docker", args, { encoding: "utf-8", timeout: 30_000 }).trim();

/** Docker Desktop（WSL2）把 Windows 路徑回報成 /run/desktop/mnt/host/<磁碟>/…；統一成小寫正斜線的 `d:/…` 形態才能比對。 */
function normalizeHostPath(p: string): string {
  let s = p.replaceAll("\\", "/").toLowerCase();
  const m = /^\/(?:run\/desktop\/mnt\/host|host_mnt|mnt)\/([a-z])\//.exec(s);
  if (m) s = `${m[1]}:/${s.slice(m[0].length)}`;
  return s.replace(/\/+$/, "");
}

async function openSiPage(page: Page, request: Parameters<typeof signIn>[1]) {
  await ensureQuota(request, "admin", 40);
  await signIn(page, request, "admin");
  await page.goto("/self-improving");
  await expect(page.getByRole("heading", { level: 1, name: "自我進化" })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("si-patrol-card")).toBeVisible({ timeout: 60_000 });
}

/** 點頁首「重新整理」（使 patrol 查詢重抓），等該次 patrol 請求回來。 */
async function refresh(page: Page) {
  const done = page.waitForResponse((r) => r.url().includes("/api/v1/si/patrol"));
  await page.getByRole("button", { name: "重新整理" }).click();
  await done;
}

test.describe("Docker 全棧：核准流程全程可見（AC-966-17）", () => {
  test.setTimeout(300_000);

  test("AT_966_17_1 新鮮、過時、缺席三畫面；對快照目錄全程只讀（Bridge 不快取、掛載唯讀）", async ({ page, request }) => {
    const base = JSON.parse(readFileSync(PATROL_FILE(), "utf-8")) as Record<string, unknown>;
    const heartbeat = typeof base.heartbeat_minutes === "number" ? base.heartbeat_minutes : 15;
    // 過時門檻是 2×週期＋5 分；TCS 取 40 分，週期較大時加大以確保「超過門檻」
    const staleMinutes = Math.max(40, 2 * heartbeat + 15);
    try {
      // (a) 新鮮：generated_at＝現在減 3 分（避免落在「剛剛」字樣）
      writePatrolAtomically(withGeneratedAt(base, 3));
      await openSiPage(page, request);
      await expect(page.getByTestId("si-patrol-card")).toContainText(/上次心跳：\s*\d+\s*分鐘前/);
      await expect(page.getByTestId("si-patrol-stale")).toHaveCount(0);

      // (b) 過時：改檔後按「重新整理」（Bridge 每請求重讀，畫面必須跟著變）
      writePatrolAtomically(withGeneratedAt(base, staleMinutes));
      await refresh(page);
      await expect(page.getByTestId("si-patrol-stale")).toContainText("巡邏可能沒在跑");

      // (c) 缺席：刪檔後重新整理
      rmSync(PATROL_FILE(), { force: true });
      await refresh(page);
      await expect(page.getByTestId("si-patrol-missing")).toContainText("還沒有收到巡邏回報");

      // 全程只讀：Bridge 容器內對 /si-report 寫入必須失敗（唯讀掛載）
      let wrote = true;
      try {
        docker(["exec", BRIDGE(), "sh", "-c", "touch /si-report/x"]);
      } catch {
        wrote = false;
      }
      expect(wrote, "Bridge 容器內 touch /si-report/x 竟然成功：掛載不是唯讀").toBe(false);
    } finally {
      // 還原為新鮮的真快照，讓後面的 AT 與人工檢視看到一致的狀態
      writePatrolAtomically(withGeneratedAt(base, 3));
    }
  });

  test("AT_966_17_2 真提案詳情冒煙：變更內容逐行等於 repo 內追蹤檔、「下一步」非空、哨兵不出現在回應與 DOM、全程零非 GET（冒煙檢查，不宣稱可被造成紅燈）", async ({ page, request }) => {
    const canary = need("E2E_SI_CANARY");
    const listed = await call(request, "admin", "GET", "/api/v1/si/proposals");
    expect(listed.status, "GET /api/v1/si/proposals").toBe(200);
    const items = (dataOf<{ items: Array<Record<string, unknown>> }>(listed).items ?? []).filter((i) => typeof i.id === "string");
    // 取第一個「repo 內有對應 rN.patch 追蹤檔」的真提案（比對對象是檔案系統讀取結果）
    const picked = items
      .map((i) => ({ id: String(i.id), rev: Number(i.rev) }))
      .find((i) => Number.isInteger(i.rev) && existsSync(path.join(REPO_ROOT(), "docs", "06_quality", "SelfImproving_Proposals", i.id, `r${i.rev}.patch`)));
    expect(picked, "全棧沒有任何帶 rN.patch 追蹤檔的真提案；無法驗 AT-966-17-2").toBeTruthy();
    const { id, rev } = picked!;
    const patchText = readFileSync(path.join(REPO_ROOT(), "docs", "06_quality", "SelfImproving_Proposals", id, `r${rev}.patch`), "utf-8");

    const writes: string[] = [];
    const bodies: string[] = [];
    page.on("request", (req) => {
      if (req.url().includes("/api/v1/si/") && !["GET", "HEAD", "OPTIONS"].includes(req.method())) writes.push(`${req.method()} ${req.url()}`);
    });
    page.on("response", (res) => {
      if (res.url().includes(`/api/v1/si/proposals/${id}`))
        void res
          .text()
          .then((t) => bodies.push(t))
          .catch(() => undefined);
    });

    await openSiPage(page, request);
    await page.getByRole("tab", { name: /^提案/ }).click();
    await page.getByTestId(`si-detail-open-${id}`).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByTestId("si-next-step")).toBeVisible({ timeout: 60_000 });
    // 「下一步」非空，且不是「量不到」
    const next = (await dialog.getByTestId("si-next-step").innerText()).trim();
    expect(next.length, "下一步為空").toBeGreaterThan(0);
    expect(next, "下一步顯示「量不到」：根層 detail.next 缺失").not.toContain("量不到");

    // 逐一切五分頁；變更內容逐行比對
    for (const name of ["卡面", "變更內容", "提案本文", "評估集與驗證", "時間線"]) {
      await dialog.getByRole("tab", { name }).click();
      await expect(dialog.getByRole("tab", { name })).toHaveAttribute("aria-selected", "true");
      if (name === "變更內容") {
        await expect(dialog.getByTestId("si-diff-view")).toBeVisible();
        if ((await dialog.getByTestId("si-diff-expand").count()) > 0) {
          await dialog.getByTestId("si-diff-expand").click();
          await expect(dialog.getByTestId("si-diff-expand")).toHaveAttribute("aria-expanded", "true");
        }
        const shown = await dialog.locator("[data-diff-kind] .diff-text").allInnerTexts();
        const expected = patchText.split("\n");
        if (expected[expected.length - 1] === "") expected.pop();
        const truncated = (await dialog.getByTestId("si-diff-truncated").count()) > 0;
        const compare = truncated ? expected.slice(0, shown.length) : expected;
        expect(shown.length, "變更內容行數與追蹤檔不同").toBe(compare.length);
        expect(shown, "變更內容與 repo 追蹤檔逐行不同").toEqual(compare);
      }
    }

    await page.waitForTimeout(500); // 讓最後一個回應的 text() 落進 bodies
    const domText = await page.evaluate(() => document.body.textContent ?? "");
    expect(bodies.length, "沒有攔到單筆提案回應").toBeGreaterThan(0);
    expect(bodies.join("\n"), "單筆提案回應含評估集哨兵").not.toContain(canary);
    expect(domText, "DOM 含評估集哨兵").not.toContain(canary);
    expect(writes, "全程不得有非 GET 的 /api/v1/si/ 請求").toEqual([]);
    await expectNoA11yViolations(page, "全棧：提案詳情（評估集與驗證…五分頁走完後）");
  });

  test("AT_966_17_3 hermetic 掛載：/si-report 唯讀且來源在沙盒下、/si-audit 來源亦在沙盒下、BRIDGE_SI_REPORT_DIR=/si-report", async () => {
    const sandbox = normalizeHostPath(need("E2E_SI_SANDBOX_ROOT"));
    const mounts = JSON.parse(docker(["inspect", BRIDGE(), "--format", "{{json .Mounts}}"])) as Array<{ Destination: string; Source: string; RW: boolean }>;
    const byDest = (dest: string) => mounts.find((m) => m.Destination === dest);

    const report = byDest("/si-report");
    expect(report, "Bridge 沒有 /si-report 掛載").toBeTruthy();
    expect(report!.RW, "/si-report 必須唯讀（RW=false）").toBe(false);
    const reportSrc = normalizeHostPath(report!.Source);
    expect(reportSrc.startsWith(`${sandbox}/`), `/si-report 來源不在沙盒下：${reportSrc}（沙盒 ${sandbox}）`).toBe(true);
    expect(reportSrc, "/si-report 來源落在真 SI 家目錄（.autosdd）").not.toContain("/.autosdd");

    const audit = byDest("/si-audit");
    expect(audit, "Bridge 沒有 /si-audit 掛載").toBeTruthy();
    const auditSrc = normalizeHostPath(audit!.Source);
    expect(auditSrc.startsWith(`${sandbox}/`), `/si-audit 來源不在沙盒下：${auditSrc}`).toBe(true);
    expect(auditSrc, "/si-audit 來源落在真 SI 家目錄（.autosdd）").not.toContain("/.autosdd");

    const env = JSON.parse(docker(["inspect", BRIDGE(), "--format", "{{json .Config.Env}}"])) as string[];
    expect(env, "BRIDGE_SI_REPORT_DIR 須為 /si-report").toContain("BRIDGE_SI_REPORT_DIR=/si-report");
  });

  test("AT_966_17_E_1 未掛載部署（Bridge 不設 BRIDGE_SI_REPORT_DIR）：巡邏卡說明、其他自我進化功能照常、詳情仍可開、待入帳面板說明量不到原因", async ({ page, request }) => {
    // 待入帳面板的「拒收原因量不到」說明只在「有待入帳列」時出現（SiWritesPanel：evaluable && pending.length > 0）；
    // 乾淨棧沒有待入帳列，所以先經真 console-api 送一筆立即啟動要求（只落稽核檔到沙盒的 console_audit，沒有主機端入帳者，列會一直待入帳；
    // 沙盒不得是真 SI 家目錄，17-3 已斷言來源在沙盒下）。TCS 17-E-1 的 Given 未列此前置，見 E2E_FULLSTACK_REPORT 的勘誤建議。
    await ensureQuota(request, "admin", 40);
    const sent = await call(request, "admin", "POST", "/api/v1/si/runs/request", {});
    expect(sent.status, "建立待入帳列失敗（寫入面未啟用？）").toBe(201);
    await openSiPage(page, request);
    await expect(page.getByTestId("si-patrol-unmounted")).toContainText("這個部署沒有掛載巡邏回報目錄");

    // 其餘功能照常：狀態橫幅 ok、提案分頁有表（或空狀態）、對帳面板有終態
    const banner = page.getByTestId("si-status-banner");
    await expect(banner.getByTestId("si-loading")).toHaveCount(0, { timeout: 90_000 });
    await expect(banner.getByTestId("si-error"), "未掛載不得拖垮狀態橫幅").toHaveCount(0);
    await expect(banner.getByTestId("si-head-sha")).toBeVisible();
    const writes = page.getByTestId("si-writes-panel");
    await expect(writes).toBeVisible();
    await expect(writes.getByTestId("si-loading")).toHaveCount(0, { timeout: 90_000 });
    await expect(writes.getByTestId("si-ingest-unavailable")).toContainText("拒收原因量不到：這個部署沒有掛載巡邏回報目錄");

    await page.getByRole("tab", { name: /^提案/ }).click();
    const panel = page.getByTestId("si-panel-proposals");
    await expect(panel.getByTestId("si-loading")).toHaveCount(0, { timeout: 90_000 });
    await expect(panel.getByTestId("si-error")).toHaveCount(0);
    await expect(panel.locator('[data-testid="si-prop-table"], [data-testid="si-empty"]')).toHaveCount(1);

    // 詳情對話框仍可開（下一步取詳情 next；沒有任何提案列時此段由 17-2 的前置保證，這裡以第一個詳情鈕為準）
    const firstDetail = panel.locator('[data-testid^="si-detail-open-"]').first();
    await expect(firstDetail, "全棧沒有任何提案列，無法驗「詳情仍可開」").toBeVisible();
    await firstDetail.click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByTestId("si-next-step")).toBeVisible({ timeout: 60_000 });
    await expect(dialog.getByTestId("si-next-step")).not.toHaveText("");
  });
});
