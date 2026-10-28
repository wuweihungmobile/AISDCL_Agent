import { execFile } from "node:child_process";
import { promisify } from "node:util";

import { expect, test } from "@playwright/test";

import { call, dataOf, ensureQuota, signIn } from "./realBackend";

/**
 * 系統管理／資料庫備份（Docker 全棧，經 nginx 同源；TCS-SysAdminBackup-20261027 AT-BK-02-1-R-1、AT-BK-05-2-R-1；PRD §11 真機 V2、V5 之二）——**實機證據，不是每個 commit 的閘**（TCS D-BK-T24）：
 * `docker compose --profile db --profile app --profile full up -d --build`、sidecar 已跑過至少一次備份之後，以
 * `$env:E2E_API_URL = "http://localhost"; npx playwright test -c tests/e2e/docker.config.ts -g "AT_BK_"` 執行（需要 docker CLI）。
 *  · AT-BK-02-1-R-1（V2）：備份頁「備份清單」的標籤集合、類型、結束時間、大小，與 `pgbackrest info`（唯讀）的真值逐份相符；離站邏輯備份與 MinIO 資料目錄的 `.dump` 檔一致；
 *  · AT-BK-05-2-R-1（V5 之二）：`docker stop` sidecar 後 ≤90 秒（心跳 30 秒加一個輪詢週期）出現紅橫幅（role=alert）且資料標示「可能已過期」、停止期間 GET 仍 200 並回已知資料；
 *    `docker start` 後橫幅消失、資料恢復。測完一定把 sidecar 啟回來（finally）。
 * 階段二的真機項（AT-BK-06-3-R-1、06-4-R-1、06-7-R-1：手動觸發、併發、權限）屬階段二，尚未做。容器名稱預設為 compose 的 container_name。
 * 只下唯讀指令（`pgbackrest info`、`ls`）加 sidecar 的停啟；不寫備份、不刪卷。
 */
const execFileAsync = promisify(execFile);
const SIDECAR = process.env.E2E_PGBACKREST_CONTAINER ?? "aisdlc-pgbackrest";
const MINIO = process.env.E2E_MINIO_CONTAINER ?? "aisdlc-minio";
const BUCKET = process.env.E2E_OFFSITE_BUCKET ?? "aisdlc-db-backup";

async function docker(...args: string[]): Promise<{ stdout: string; stderr: string }> {
  return execFileAsync("docker", args, { timeout: 180_000, maxBuffer: 64 * 1024 * 1024 });
}

type InfoBackup = { label: string; type: string; timestamp: { start: number; stop: number }; info: { size: number; repository: { size: number } }; database: { "repo-key": number } };

/** `pgbackrest info` 的真值（唯讀）：第一個 stanza 的全部備份。 */
async function realInfo(): Promise<InfoBackup[]> {
  const { stdout } = await docker("exec", SIDECAR, "pgbackrest", "--stanza=aisdlc", "--output=json", "--log-level-console=off", "info");
  const start = stdout.indexOf("[");
  const parsed = JSON.parse(stdout.slice(start)) as Array<{ backup?: InfoBackup[] }>;
  return parsed[0]?.backup ?? [];
}

const pad = (n: number) => String(n).padStart(2, "0");
/** 與前端 `formatDateTime` 同形（瀏覽器本機時區；測試行程與瀏覽器同一台機器）。 */
function localDateTime(epochSeconds: number): string {
  const d = new Date(epochSeconds * 1000);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
/** 與前端 `formatBytes` 同形。 */
function bytesText(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
const KIND_TEXT: Record<string, string> = { full: "全備", diff: "增備（差異）", incr: "增量" };

test.describe.configure({ mode: "serial" });

test.describe("Docker 全棧：系統管理／資料庫備份", () => {
  test.setTimeout(600_000);

  test("AT_BK_02_1_R_1 備份清單與 pgbackrest info 逐份相符（標籤集合、類型、結束時間、大小），離站邏輯備份與 MinIO 資料目錄的 .dump 檔一致", async ({ page, request }) => {
    await ensureQuota(request, "viewer", 40);
    await signIn(page, request, "viewer");
    await page.goto("/sysadmin/backup");
    await expect(page.getByRole("heading", { level: 1, name: "資料庫備份" })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("bk-table"), "全棧至少要有一份備份才驗得了：請先跑過全備（docker/README.md〈4.2〉）").toBeVisible({ timeout: 60_000 });

    // 真值：pgbackrest info（逐份）
    const real = await realInfo();
    expect(real.length, "pgbackrest info 至少一份備份").toBeGreaterThan(0);
    for (const backup of real) {
      const row = page.getByTestId(`bk-row-${backup.label}`).first();
      await expect(row, `備份清單缺 ${backup.label}`).toBeVisible();
      const cells = await row.locator("td").allTextContents();
      expect(cells[0].trim(), `${backup.label} 類型`).toBe(KIND_TEXT[backup.type] ?? backup.type);
      expect(cells[1].trim()).toBe(backup.label);
      expect(cells[2].trim(), `${backup.label} 儲存位置`).toBe(`${backup.database["repo-key"] === 1 ? "本地" : "離站"} repo${backup.database["repo-key"]}`);
      expect(cells[4].trim(), `${backup.label} 結束時間`).toBe(localDateTime(backup.timestamp.stop));
      expect(cells[6].trim(), `${backup.label} 資料庫大小`).toBe(bytesText(backup.info.size));
      expect(cells[7].trim(), `${backup.label} 備份大小`).toBe(bytesText(backup.info.repository.size));
    }
    // 標籤集合：pgBackRest 的備份＝清單上類型不是邏輯備份的列（逐一相等，沒有多出也沒有少掉）
    const shown = (await page.locator('[data-testid^="bk-row-"]').evaluateAll((els) => els.map((el) => (el as HTMLElement).dataset.testid ?? ""))).map((id) => id.replace("bk-row-", ""));
    const uiPg = (await page.locator('[data-testid^="bk-row-"]').evaluateAll((els) => els.map((el) => (el.querySelectorAll("td")[0] as HTMLElement).textContent ?? ""))).map((t) => t.trim());
    const pgLabels = shown.filter((_, i) => uiPg[i] !== "邏輯備份");
    expect([...pgLabels].sort()).toEqual(real.map((b) => b.label).sort());

    // 離站邏輯備份：與 MinIO 資料目錄的 .dump 檔一致（唯讀 ls）
    const { stdout } = await docker("exec", MINIO, "sh", "-c", `ls /data/${BUCKET}/logical/ 2>/dev/null || true`);
    const dumps = stdout
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter((s) => s.endsWith(".dump"));
    const logicalShown = shown.filter((_, i) => uiPg[i] === "邏輯備份");
    expect([...logicalShown].sort(), "備份清單的邏輯備份＝MinIO 資料目錄的 .dump 檔").toEqual([...dumps].sort());
    console.log(`[sysadmin-backup-docker] AT-BK-02-1-R-1：pgBackRest ${real.length} 份、離站邏輯備份 ${dumps.length} 個，清單與真值逐份相符`);
  });

  test("AT_BK_05_2_R_1 停 sidecar 後 ≤90 秒出現紅橫幅（role=alert）與「可能已過期」，停止期間 GET 仍 200 回已知資料；啟回來後橫幅消失、資料恢復", async ({ page, request }) => {
    await ensureQuota(request, "viewer", 40);
    await signIn(page, request, "viewer");
    await page.goto("/sysadmin/backup");
    await expect(page.getByTestId("bk-cards")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("bk-banner-offline"), "測試前提：sidecar 在線，沒有離線橫幅").toHaveCount(0);

    try {
      await docker("stop", SIDECAR);
      // 心跳逾 30 秒即離線；頁面每 30 秒重抓一次：給 90 秒
      const banner = page.getByTestId("bk-banner-offline");
      await expect(banner).toBeVisible({ timeout: 90_000 });
      await expect(banner).toHaveAttribute("role", "alert");
      await expect(banner).toContainText("備份控制面無回應");
      await expect(page.getByTestId("bk-stale-mark")).toHaveText("可能已過期");
      // 離線時資料照回：卡片與清單仍在、API 仍是 200 並帶 runner_offline
      await expect(page.getByTestId("bk-cards")).toBeVisible();
      const reply = await call(request, "viewer", "GET", "/api/v1/sysadmin/backups");
      expect(reply.status, JSON.stringify(reply.json).slice(0, 300)).toBe(200);
      const data = dataOf<{ control: { reason: string | null; canTrigger: boolean }; cards: unknown[] | null; backups: unknown[] | null }>(reply);
      expect(data.control.reason).toBe("runner_offline");
      expect(data.control.canTrigger).toBe(false);
      expect(data.cards, "離線時資料區塊照回（非 null）").not.toBeNull();
      expect(data.backups).not.toBeNull();
    } finally {
      // 一定把 sidecar 啟回來（排程備份與控制面都靠它），再等橫幅消失
      await docker("start", SIDECAR);
    }
    await expect(page.getByTestId("bk-banner-offline"), "sidecar 啟回後橫幅消失").toHaveCount(0, { timeout: 180_000 });
    await expect(page.getByTestId("bk-cards")).toBeVisible();
    await expect(page.getByTestId("bk-stale-mark")).toHaveCount(0);
    console.log("[sysadmin-backup-docker] AT-BK-05-2-R-1：停止後出現離線橫幅、啟回後恢復");
  });
});
