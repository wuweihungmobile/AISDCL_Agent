import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { BACKUP_JOB_POLL_MS, BACKUP_OVERVIEW_POLL_MS, NOTIFICATION_POLL_FLOOR_MS } from "@/lib/api/queries";
import type { BackupRetention, BackupRow } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import {
  BACKUP_KIND_TEXT,
  BACKUP_REASONS,
  CARD_STATUS_TEXT,
  CONTROL_REASON_TEXT,
  COVERAGE_CATEGORY_LABEL,
  EXPORT_STALE_SECONDS,
  JOB_STATUS_TEXT,
  REPO_STATUS_ZH,
  SCHEDULE_JOB_LABELS,
  VOLUME_COVERAGE,
  backupKindText,
  backupLocationText,
  backupReasonText,
  backupResultText,
  cardStatusText,
  cardStatusTone,
  controlReasonText,
  dumpOffsiteNote,
  humanizeCron,
  isExportStale,
  lastSuccessText,
  offlineBannerText,
  reasonBlocksData,
  repoStatusLine,
  repoStatusText,
  retentionQuota,
  retentionText,
  scheduleRowText,
  staleMarkText,
  triggerText,
  walLine,
  warningText,
  type CoverageCategory,
} from "./sysadminBackup";

/**
 * 備份頁純函式與詞表（TCS-SysAdminBackup-20261027 載具 FL；R-BK-10～13、R-BK-22、R-BK-26、R-BK-44、R-BK-60）：
 *  - AT-BK-02-4-E-1：REPO_STATUS_ZH 與 repoStatusText；AT-BK-03-1-2、03-2-1：humanizeCron 的三式與不認得的原字串退回；
 *  - AT-BK-06-1-1：retentionQuota（QUOTA_CASES 七列）；AT-BK-06-5-5：BACKUP_REASONS 與契約檔〈backup 類 reason 表〉雙向鎖；AT-BK-06-11-1：輪詢常數；
 *  - AT-BK-08-2-E-1：VOLUME_COVERAGE 的類別封閉；
 *  - 另加：保留策略一行字、WAL 歸檔一行、離線橫幅、過期標記、警告文字、卡片與結果的詞表（同一份詞表元件與測試共用）。
 * 判定指令：npx vitest run lib/domain/sysadminBackup.test.ts -t "<AT 底線形>"
 */
const ROOT = process.cwd();

// ── AT-BK-02-4-E-1：repo 狀態碼 ───────────────────────────────────────────────────────────────

describe("AT_BK_02_4 repo 狀態碼的中文說明", () => {
  it("AT_BK_02_4_E_1 REPO_STATUS_ZH 的鍵集合恰為 {0,1,2,3,4,5,6,99}、每個值為非空中文；repoStatusText 對 0 回「正常」、對表外的碼（77、-1、NaN）回含該數字的「其他」兜底、不丟例外", () => {
    expect(
      Object.keys(REPO_STATUS_ZH)
        .map(Number)
        .sort((a, b) => a - b),
    ).toEqual([0, 1, 2, 3, 4, 5, 6, 99]);
    for (const [code, text] of Object.entries(REPO_STATUS_ZH)) expect(text, `碼 ${code}`).toMatch(/\S/);
    expect(REPO_STATUS_ZH[99]).toBe("其他");
    expect(repoStatusText(0, "ok")).toBe("正常");
    expect(repoStatusText(2)).toBe(REPO_STATUS_ZH[2]);
    expect(repoStatusText(99, "other")).toBe("其他");
    for (const code of [77, -1, Number.NaN]) {
      const text = repoStatusText(code, "mystery");
      expect(text, String(code)).toContain("其他");
      expect(text, String(code)).toContain(String(code));
    }
    // 表外的碼不得被誤判成表內的鍵（原型鏈上的 constructor、__proto__ 之類不是狀態碼）
    expect(() => repoStatusText(Number("constructor"))).not.toThrow();
  });

  it("repoStatusLine：0 回「正常」；已知的非零碼回「狀態碼 N：<中文>」；表外的碼回兜底（含狀態碼與原文，不重複寫兩次碼）", () => {
    expect(repoStatusLine(0, "ok")).toBe("正常");
    expect(repoStatusLine(99, "other")).toBe("狀態碼 99：其他");
    expect(repoStatusLine(2, "x")).toBe(`狀態碼 2：${REPO_STATUS_ZH[2]}`);
    expect(repoStatusLine(77, "mystery")).toBe("其他（狀態碼 77，原文：mystery）");
    expect(repoStatusLine(77)).toBe("其他（狀態碼 77）");
  });
});

// ── AT-BK-03-1-2、03-2-1：cron 白話化 ─────────────────────────────────────────────────────────

describe("AT_BK_03 cron 白話化", () => {
  it("AT_BK_03_1_2 三式表驅動：週日、範圍、每日、單一星期與補零；星期對照 0 日 1 一 2 二 3 三 4 四 5 五 6 六", () => {
    const table: Array<[string, string]> = [
      ["0 2 * * 0", "每週日 02:00"],
      ["0 2 * * 1-6", "每週一至週六 02:00"],
      ["30 2 * * *", "每日 02:30"],
      ["0 4 * * 3", "每週三 04:00"],
      ["5 14 * * 6", "每週六 14:05"],
      ["0 0 * * *", "每日 00:00"],
      ["59 23 * * *", "每日 23:59"],
      ["0 2 * * 0-6", "每週日至週六 02:00"],
      ["0 2 * * 2-3", "每週二至週三 02:00"],
    ];
    for (const [cron, text] of table) expect(humanizeCron(cron), cron).toBe(text);
    const names = ["日", "一", "二", "三", "四", "五", "六"];
    for (let day = 0; day <= 6; day += 1) expect(humanizeCron(`0 2 * * ${day}`), `星期 ${day}`).toBe(`每週${names[day]} 02:00`);
  });

  it("AT_BK_03_2_1 不認得的形狀一律回傳與輸入逐字相同的原字串（不 trim、不改大小寫、不丟例外、不回猜測的白話）；星期欄 7 也不認得", () => {
    const unknown = [
      "*/5 * * * *",
      "0 2 1 * *",
      "0 2 * 1 *",
      "0 2 * * 1,3",
      "0 2 * * MON",
      "@daily",
      "",
      "0 2 * * 1-6/2",
      "60 2 * * *",
      "0 24 * * *",
      "0 2 * * 8",
      "0 2 * * 6-1",
      "0 2 * *",
      "0 2 * * * *",
      "0 2 * * 7",
      " 0 2 * * 0",
      "0 2 * * 0 ",
      "0  2 * * 0",
      "0 2 * * mon",
      "0 2 * * 1-1",
      "0 2 * * 0-7",
      "00 02 * * *x",
    ];
    for (const cron of unknown) {
      let out: unknown;
      expect(() => {
        out = humanizeCron(cron);
      }, JSON.stringify(cron)).not.toThrow();
      expect(out, JSON.stringify(cron)).toBe(cron);
      expect(String(out), JSON.stringify(cron)).not.toContain("每");
    }
    // 非字串輸入（防禦）：不丟例外、回空字串
    expect(humanizeCron(undefined as unknown as string)).toBe("");
    expect(humanizeCron(null as unknown as string)).toBe("");
  });

  it("scheduleRowText：「<白話>・<工作名>」；不認得的 cron 顯示原表達式；不認得的工作名原樣顯示；六個工作名與 D-BK-T8 一致", () => {
    expect(SCHEDULE_JOB_LABELS).toEqual({
      full: "全備",
      diff: "增備（差異）",
      dump: "離站 pg_dump",
      verify: "驗證",
      expire: "清理過期備份（維護工作）",
      wal_clean: "清理 WAL 複本（維護工作）",
    });
    expect(scheduleRowText({ job: "full", cron: "0 2 * * 0" })).toBe("每週日 02:00・全備");
    expect(scheduleRowText({ job: "dump", cron: "*/7 * * * *" })).toBe("*/7 * * * *・離站 pg_dump");
    expect(scheduleRowText({ job: "future_job", cron: "0 1 * * *" })).toBe("每日 01:00・future_job");
    // 只有兩條清理類是「維護工作」
    expect(
      Object.entries(SCHEDULE_JOB_LABELS)
        .filter(([, label]) => label.includes("維護工作"))
        .map(([job]) => job),
    ).toEqual(["expire", "wal_clean"]);
  });
});

// ── 保留策略一行字 ─────────────────────────────────────────────────────────────────────────────

describe("AT_BK_03_4 保留策略一行字（retentionText）", () => {
  const full: BackupRetention = { repo1: { full: 4, diff: 7 }, repo2: { full: 4, diff: null }, logicalDays: 28 };

  it("「本地：全備 4、差異 7；離站：全備 4、差異隨全備到期；邏輯備份 28 天」", () => {
    expect(retentionText(full)).toBe("本地：全備 4、差異 7；離站：全備 4、差異隨全備到期；邏輯備份 28 天");
  });

  it("本地的差異為 null 顯示「差異 未設」；邏輯備份天數為 null 顯示「邏輯備份 —」；全備為 null 顯示「全備 未設」", () => {
    expect(retentionText({ repo1: { full: 4, diff: null }, repo2: { full: 4, diff: 7 }, logicalDays: 28 })).toBe("本地：全備 4、差異 未設；離站：全備 4、差異 7；邏輯備份 28 天");
    expect(retentionText({ ...full, logicalDays: null })).toContain("邏輯備份 —");
    expect(retentionText({ repo1: { full: null, diff: null }, logicalDays: 1 })).toBe("本地：全備 未設、差異 未設；邏輯備份 1 天");
  });

  it("整個為 null（量不到）回「—」，不出現任何數字（不填預設的 4、7、28）；repo 依編號由小到大，與物件鍵序無關", () => {
    expect(retentionText(null)).toBe("—");
    expect(retentionText(undefined)).toBe("—");
    expect(retentionText(null)).not.toMatch(/\d/);
    const reversed = { logicalDays: 28, repo2: { full: 4, diff: null }, repo1: { full: 4, diff: 7 } } as BackupRetention;
    expect(retentionText(reversed)).toBe(retentionText(full));
    // 第三個 repo（日後）原樣以鍵名稱呼，差異未設同離站「隨全備到期」
    expect(retentionText({ repo1: { full: 1, diff: 1 }, repo3: { full: 2, diff: null }, logicalDays: 7 } as BackupRetention)).toBe(
      "本地：全備 1、差異 1；repo3：全備 2、差異隨全備到期；邏輯備份 7 天",
    );
  });
});

// ── AT-BK-06-1-1：保留名額 ────────────────────────────────────────────────────────────────────

describe("AT_BK_06_1 保留名額（retentionQuota；QUOTA_CASES）", () => {
  const retention: BackupRetention = { repo1: { full: 4, diff: 7 }, repo2: { full: 4, diff: null }, logicalDays: 28 };
  const rows = (location: string, kind: "full" | "diff", labels: string[]): Array<Pick<BackupRow, "kind" | "label" | "location">> => labels.map((label) => ({ kind, label, location }));

  it("AT_BK_06_1_1 七列：全備滿額、全備未滿、差異（差異加全備合計）滿額、差異未滿、repo2 差異無上限不輸出、驗證回空、repo2 全備滿額", () => {
    // Q1：full、repo1 全備 4 份（舊→新）
    const q1 = rows("repo1", "full", ["20260928-020000F", "20261005-020000F", "20261012-020000F", "20261019-020000F"]);
    expect(retentionQuota("full", q1, retention).find((i) => i.repo === 1)).toEqual({ repo: 1, kind: "full", current: 4, limit: 4, willExpire: true, oldestLabel: "20260928-020000F" });
    // Q2：full、repo1 全備 3 份
    expect(retentionQuota("full", q1.slice(1), retention).find((i) => i.repo === 1)).toMatchObject({ current: 3, limit: 4, willExpire: false, oldestLabel: "20261005-020000F" });
    // Q3：diff、repo1 全備 2＋差異 5＝計 7、上限 7
    const q3 = [
      ...rows("repo1", "full", ["20261012-020000F", "20261019-020000F"]),
      ...rows("repo1", "diff", [
        "20261012-020000F_20261013-020000D",
        "20261012-020000F_20261014-020000D",
        "20261012-020000F_20261015-020000D",
        "20261019-020000F_20261020-020000D",
        "20261019-020000F_20261021-020000D",
      ]),
    ];
    expect(retentionQuota("diff", q3, retention).find((i) => i.repo === 1)).toEqual({
      repo: 1,
      kind: "diff",
      current: 7,
      limit: 7,
      willExpire: true,
      oldestLabel: "20261012-020000F_20261013-020000D",
    });
    // 全備計入差異份數：只算差異是 5（不會 willExpire），合計 7 才會
    expect(q3.filter((r) => r.kind === "diff")).toHaveLength(5);
    // Q4：diff、repo1 全備 1＋差異 2＝3
    const q4 = [...rows("repo1", "full", ["20261019-020000F"]), ...rows("repo1", "diff", ["20261019-020000F_20261020-020000D", "20261019-020000F_20261021-020000D"])];
    expect(retentionQuota("diff", q4, retention).find((i) => i.repo === 1)).toMatchObject({ current: 3, limit: 7, willExpire: false, oldestLabel: "20261019-020000F_20261020-020000D" });
    // Q5：repo2 的 diff 上限為 null ⇒ 該 repo 不輸出任何項
    const q5 = [...rows("repo2", "full", ["20261019-020002F"]), ...rows("repo2", "diff", ["20261019-020002F_20261020-020001D"])];
    expect(retentionQuota("diff", q5, retention).find((i) => i.repo === 2)).toBeUndefined();
    expect(retentionQuota("diff", q5, retention).map((i) => i.repo)).toEqual([1]);
    // Q6：verify 回空陣列
    expect(retentionQuota("verify", [...q1, ...q5], retention)).toEqual([]);
    // Q7：full、repo2 全備 4 份
    const q7 = rows("repo2", "full", ["20260928-020002F", "20261005-020002F", "20261012-020002F", "20261019-020002F"]);
    expect(retentionQuota("full", q7, retention).find((i) => i.repo === 2)).toEqual({ repo: 2, kind: "full", current: 4, limit: 4, willExpire: true, oldestLabel: "20260928-020002F" });
  });

  it("輸入順序不影響結果（最舊取標籤字典序最小者）；沒有該 repo 的備份時 current 為 0、oldestLabel 為 null；retention 為 null 回空陣列；其他 repo 與邏輯備份不混入", () => {
    const shuffled = rows("repo1", "full", ["20261019-020000F", "20260928-020000F", "20261012-020000F", "20261005-020000F"]);
    expect(retentionQuota("full", shuffled, retention).find((i) => i.repo === 1)?.oldestLabel).toBe("20260928-020000F");
    const none = retentionQuota("full", [], retention);
    expect(none.map((i) => [i.repo, i.current, i.willExpire, i.oldestLabel])).toEqual([
      [1, 0, false, null],
      [2, 0, false, null],
    ]);
    expect(retentionQuota("full", shuffled, null)).toEqual([]);
    const mixed = [...shuffled, { kind: "full", label: "aisdlc-x.dump", location: "logical" }, ...rows("repo2", "full", ["20261019-020002F"])];
    expect(retentionQuota("full", mixed, retention).find((i) => i.repo === 1)?.current).toBe(4);
    expect(retentionQuota("full", mixed, retention).find((i) => i.repo === 2)?.current).toBe(1);
  });
});

// ── AT-BK-06-5-5：reason 詞表與契約檔雙向鎖 ─────────────────────────────────────────────────────

/** 契約檔〈backup 類 reason 表〉：以標題之後的**第一張**表為準（欄序 reason｜狀態碼｜details｜中文訊息｜意義）；缺標題或缺表就丟例外（鎖不得空過）。 */
function parseReasonTable(markdown: string): Array<{ reason: string; status: string; message: string }> {
  const lines = markdown.split(/\r?\n/);
  const title = lines.findIndex((line) => /^#{1,6}\s*backup 類 reason 表/.test(line));
  if (title < 0) throw new Error("契約檔沒有〈backup 類 reason 表〉標題");
  let i = title + 1;
  while (i < lines.length && !lines[i].trim().startsWith("|")) i += 1;
  if (i >= lines.length) throw new Error("標題之後沒有表格");
  const table: string[][] = [];
  for (; i < lines.length && lines[i].trim().startsWith("|"); i += 1) {
    table.push(
      lines[i]
        .trim()
        .replace(/^\||\|$/g, "")
        .split("|")
        .map((cell) => cell.trim()),
    );
  }
  expect(table[0], "表頭欄序固定").toEqual(["reason", "狀態碼", "details", "中文訊息", "意義"]);
  return table.slice(2).map((cells) => ({ reason: cells[0].replace(/`/g, ""), status: cells[1], message: cells[3] }));
}

describe("AT_BK_06_5 reason 詞表與契約檔的雙向鎖", () => {
  const contract = readFileSync(path.join(ROOT, "..", "docs", "02_architecture", "API_Contract_SysAdminBackup.md"), "utf-8");

  it("AT_BK_06_5_5 BACKUP_REASONS 的鍵集合與契約表 reason 欄（十三列）雙向相等；每個鍵的訊息逐字等於「中文訊息」欄（含 busy＝「排程工作執行中，稍後再試」）；lib/api/reasons.ts 不含任何 backup 類 reason", () => {
    const table = parseReasonTable(contract);
    expect(table).toHaveLength(13);
    expect(Object.keys(BACKUP_REASONS).sort()).toEqual(table.map((row) => row.reason).sort());
    for (const row of table) expect((BACKUP_REASONS as Record<string, string>)[row.reason], row.reason).toBe(row.message);
    expect(BACKUP_REASONS.busy).toBe("排程工作執行中，稍後再試");
    // 狀態碼欄為數字者是 API 錯誤 reason（五個），為「—」者是工作理由（八個）
    expect(table.filter((row) => /^\d+$/.test(row.status)).map((row) => row.reason)).toEqual([
      "backup_control_unavailable",
      "backup_confirm_required",
      "backup_job_in_progress",
      "backup_too_frequent",
      "backup_job_not_found",
    ]);
    expect(table.filter((row) => row.status === "—")).toHaveLength(8);
    // 不入 reasons.ts（它與 API_Contract_P3-6.md 附錄 B 雙向鎖）；invalid_request 也不在表內
    const reasons = readFileSync(path.join(ROOT, "lib", "api", "reasons.ts"), "utf-8");
    for (const key of Object.keys(BACKUP_REASONS)) expect(reasons.includes(`"${key}"`) || reasons.includes(`'${key}'`) || reasons.includes(`${key}:`), `reasons.ts 不得含 ${key}`).toBe(false);
    expect(Object.keys(BACKUP_REASONS)).not.toContain("invalid_request");
  });

  it("AT_BK_06_5_E_2 解析器負控：缺標題、標題後沒有表格都丟例外（鎖不得空過）；標題之前或之後的別張表不影響結果（只取標題之後的第一張）", () => {
    const table = "| reason | 狀態碼 | details | 中文訊息 | 意義 |\n|---|---|---|---|---|\n| `a` | 503 | — | 訊息甲 | x |\n";
    expect(() => parseReasonTable("# 別的標題\n\n" + table)).toThrow("沒有〈backup 類 reason 表〉標題");
    expect(() => parseReasonTable("## backup 類 reason 表\n\n只有文字\n")).toThrow("沒有表格");
    const other = "| x | y |\n|---|---|\n| 1 | 2 |\n";
    const rows = parseReasonTable(`${other}\n## backup 類 reason 表\n\n${table}\n${other}`);
    expect(rows).toEqual([{ reason: "a", status: "503", message: "訊息甲" }]);
  });

  it("backupReasonText：已知 reason 取中文、表外的值原樣顯示、null 與空字串顯示「—」；原型鏈上的名字不是 reason", () => {
    expect(backupReasonText("busy")).toBe("排程工作執行中，稍後再試");
    expect(backupReasonText("backup_job_in_progress")).toBe("已有進行中的備份工作");
    expect(backupReasonText("weird_new_reason")).toBe("weird_new_reason");
    expect(backupReasonText(null)).toBe("—");
    expect(backupReasonText(undefined)).toBe("—");
    expect(backupReasonText("")).toBe("—");
    expect(backupReasonText("toString")).toBe("toString");
  });
});

// ── AT-BK-06-11-1：輪詢常數 ───────────────────────────────────────────────────────────────────

describe("AT_BK_06_11 輪詢常數", () => {
  it("AT_BK_06_11_1 BACKUP_JOB_POLL_MS＝10000、BACKUP_OVERVIEW_POLL_MS＝30000，兩者都不低於契約地板；BACKUP_JOB_POLL_MS 在原始碼以 NOTIFICATION_POLL_FLOOR_MS 定義（不是另寫 10_000）", () => {
    expect(BACKUP_JOB_POLL_MS).toBe(10_000);
    expect(BACKUP_OVERVIEW_POLL_MS).toBe(30_000);
    expect(BACKUP_JOB_POLL_MS).toBeGreaterThanOrEqual(NOTIFICATION_POLL_FLOOR_MS);
    expect(BACKUP_OVERVIEW_POLL_MS).toBeGreaterThanOrEqual(NOTIFICATION_POLL_FLOOR_MS);
    const source = readFileSync(path.join(ROOT, "lib", "api", "queries.ts"), "utf-8");
    expect(source).toMatch(/export const BACKUP_JOB_POLL_MS = NOTIFICATION_POLL_FLOOR_MS;/);
    expect(source).toMatch(/export const BACKUP_OVERVIEW_POLL_MS = POLL_MS;/);
  });
});

// ── AT-BK-08-2-E-1：涵蓋範圍分類 ───────────────────────────────────────────────────────────────

describe("AT_BK_08_2 涵蓋範圍分類（VOLUME_COVERAGE）", () => {
  const CATEGORIES: CoverageCategory[] = ["backed_up", "backup_mechanism", "rebuildable", "not_covered"];

  it("AT_BK_08_2_E_1 類別值域封閉為 {backed_up, backup_mechanism, rebuildable, not_covered}；每個卷恰一個類別；engine_workspace 為 not_covered；中文標籤表與值域逐值對應", () => {
    for (const [volume, coverage] of Object.entries(VOLUME_COVERAGE)) {
      expect(CATEGORIES, volume).toContain(coverage.category);
      expect(coverage.note, `${volume} 的說明`).toMatch(/\S/);
    }
    expect(VOLUME_COVERAGE.engine_workspace.category).toBe("not_covered");
    expect(Object.keys(COVERAGE_CATEGORY_LABEL).sort()).toEqual([...CATEGORIES].sort());
    expect(new Set(Object.values(COVERAGE_CATEGORY_LABEL)).size, "四個標籤互異").toBe(4);
    for (const label of Object.values(COVERAGE_CATEGORY_LABEL)) expect(label).toMatch(/\S/);
    // 原始碼裡每個卷名只出現一次（物件字面值的重複鍵會被後者蓋掉，本檢查讀原始碼而不是讀已合併的物件）
    const source = readFileSync(path.join(ROOT, "lib", "domain", "sysadminBackup.ts"), "utf-8");
    const block = source.slice(source.indexOf("export const VOLUME_COVERAGE"), source.indexOf("export const KEY_LOSS_NOTE"));
    const keys = [...block.matchAll(/^ {2}([a-z_]+): \{ category:/gm)].map((m) => m[1]);
    expect(keys.length).toBe(Object.keys(VOLUME_COVERAGE).length);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("R-BK-44 逐卷分類：已備份＝pg_data；備份機制本身＝pg_backup、minio_data、pg_wal_archive、pg_socket、backup_out、backup_req；可由 primary 重建＝pg_replica_data；未涵蓋＝其餘六卷（minio_certs 註明缺時由 minio-certs job 重產）", () => {
    const by = (category: CoverageCategory) =>
      Object.entries(VOLUME_COVERAGE)
        .filter(([, c]) => c.category === category)
        .map(([volume]) => volume)
        .sort();
    expect(by("backed_up")).toEqual(["pg_data"]);
    expect(by("backup_mechanism")).toEqual(["backup_out", "backup_req", "minio_data", "pg_backup", "pg_socket", "pg_wal_archive"]);
    expect(by("rebuildable")).toEqual(["pg_replica_data"]);
    expect(by("not_covered")).toEqual(["app_logs", "engine_workspace", "minio_certs", "nginx_certs", "prometheus_data", "redis_data"]);
    expect(VOLUME_COVERAGE.minio_certs.note).toContain("缺時由 minio-certs job 重產");
    expect(VOLUME_COVERAGE.pg_data.note).toContain("console schema");
    expect(Object.keys(VOLUME_COVERAGE)).toHaveLength(14);
  });
});

// ── WAL 歸檔一行（AC-BK-04-6）──────────────────────────────────────────────────────────────────

describe("AT_BK_04_6 WAL 歸檔一行（walLine）", () => {
  const T = "2026-10-27T02:15:00Z";
  const LATER = "2026-10-27T02:20:00Z";

  it("(a) 失敗 0 次：「WAL 歸檔：最近 <時間>・失敗 0 次」、ok；全新叢集（從未歸檔、零失敗）仍是物件：最近「—」、失敗 0 次、ok", () => {
    expect(walLine({ lastArchivedAt: T, failedCount: 0, lastFailedAt: null })).toEqual({ text: `WAL 歸檔：最近 ${formatDateTime(T)}・失敗 0 次`, tone: "ok" });
    expect(walLine({ lastArchivedAt: null, failedCount: 0, lastFailedAt: null })).toEqual({ text: "WAL 歸檔：最近 —・失敗 0 次", tone: "ok" });
  });

  it("(b) 失敗 3 次且最近失敗晚於最近歸檔：含「失敗 3 次」與最近失敗時間、danger；最近失敗早於最近歸檔（已恢復）不標警示；從未歸檔或缺失敗時間而有失敗＝警示", () => {
    const bad = walLine({ lastArchivedAt: T, failedCount: 3, lastFailedAt: LATER });
    expect(bad.tone).toBe("danger");
    expect(bad.text).toContain("失敗 3 次");
    expect(bad.text).toContain(formatDateTime(LATER));
    expect(walLine({ lastArchivedAt: LATER, failedCount: 3, lastFailedAt: T }).tone).toBe("ok");
    expect(walLine({ lastArchivedAt: T, failedCount: 3, lastFailedAt: T }).tone, "同時間：不能證明已恢復").toBe("ok");
    expect(walLine({ lastArchivedAt: null, failedCount: 2, lastFailedAt: T }).tone).toBe("danger");
    expect(walLine({ lastArchivedAt: T, failedCount: 2, lastFailedAt: null }).tone).toBe("danger");
  });

  it("(c) null（讀不到）：「WAL 歸檔：—」、muted，不出現「失敗 0 次」也不出現任何數字", () => {
    const missing = walLine(null);
    expect(missing).toEqual({ text: "WAL 歸檔：—", tone: "muted" });
    expect(missing.text).not.toContain("失敗");
    expect(walLine(undefined).text).toBe("WAL 歸檔：—");
  });
});

// ── 控制面健康、資料新鮮度與警告（AC-BK-05-1～05-4）──────────────────────────────────────────

describe("AT_BK_05 控制面健康與資料新鮮度的文字", () => {
  it("離線橫幅文字：有心跳年齡寫「上次心跳 N 秒前」、缺席（null）寫「尚未收到心跳」", () => {
    expect(offlineBannerText(95)).toBe("備份控制面無回應（上次心跳 95 秒前）");
    expect(offlineBannerText(31)).toBe("備份控制面無回應（上次心跳 31 秒前）");
    expect(offlineBannerText(null)).toBe("備份控制面無回應（尚未收到心跳）");
    expect(offlineBannerText(undefined)).toBe("備份控制面無回應（尚未收到心跳）");
  });

  it("資料過期：門檻 180 秒（嚴格大於）；null 與 NaN 不算過期；離線寫「可能已過期」優先於「已過期」", () => {
    expect(EXPORT_STALE_SECONDS).toBe(180);
    expect(isExportStale(180)).toBe(false);
    expect(isExportStale(181)).toBe(true);
    expect(isExportStale(null)).toBe(false);
    expect(isExportStale(undefined)).toBe(false);
    expect(isExportStale(Number.NaN)).toBe(false);
    expect(staleMarkText(null, 181)).toBe("已過期");
    expect(staleMarkText(null, 180)).toBeNull();
    expect(staleMarkText(null, null)).toBeNull();
    expect(staleMarkText("runner_offline", 5)).toBe("可能已過期");
    expect(staleMarkText("runner_offline", 999)).toBe("可能已過期");
  });

  it("整區原因：只有 runner_offline 與 null 不遮住資料；未設定、格式不符、無法讀取與日後新增的值都遮住；原因文字不含「尚無備份」也不含數字（避免被讀成沒有備份或 0 份）", () => {
    expect(reasonBlocksData(null)).toBe(false);
    expect(reasonBlocksData(undefined)).toBe(false);
    expect(reasonBlocksData("runner_offline")).toBe(false);
    for (const reason of ["not_configured", "schema_mismatch", "export_unreadable", "brand_new_reason"]) expect(reasonBlocksData(reason), reason).toBe(true);
    expect(controlReasonText("not_configured")).toBe("備份控制面未設定（不在 Docker 全棧）");
    expect(controlReasonText("schema_mismatch")).toContain("匯出檔格式版本不符");
    expect(controlReasonText("export_unreadable")).toContain("匯出檔無法讀取");
    for (const text of Object.values(CONTROL_REASON_TEXT)) {
      expect(text).not.toContain("尚無備份");
      expect(text).not.toMatch(/\d/);
    }
    expect(controlReasonText("brand_new_reason")).toContain("brand_new_reason");
  });

  it("warningText：封閉詞彙各有中文說明；cron_unparsable:<job> 帶工作名；日後新增的值原樣顯示", () => {
    for (const code of ["info_unavailable", "logical_unavailable", "retention_unavailable", "db_unavailable"]) expect(warningText(code), code).not.toBe(code);
    expect(warningText("info_unavailable")).toContain("pgBackRest");
    expect(warningText("logical_unavailable")).toContain("邏輯備份");
    expect(warningText("cron_unparsable:diff")).toContain("增備（差異）");
    expect(warningText("cron_unparsable:diff")).toContain("無法解析");
    expect(warningText("cron_unparsable:mystery")).toContain("mystery");
    expect(warningText("something_new")).toBe("something_new");
  });
});

// ── 卡片、清單與結果的詞表 ─────────────────────────────────────────────────────────────────────

describe("卡片、清單與結果的詞表", () => {
  it("卡片狀態文字與色階：成功／失敗／進行中／中斷／從未執行；失敗與中斷為警示色；不認得的狀態原樣顯示、不假裝成功", () => {
    expect(CARD_STATUS_TEXT).toEqual({ succeeded: "成功", failed: "失敗", running: "進行中", interrupted: "中斷", no_run: "從未執行" });
    expect(["succeeded", "failed", "running", "interrupted", "no_run"].map(cardStatusTone)).toEqual(["ok", "danger", "info", "danger", "muted"]);
    expect(cardStatusText("brand_new")).toBe("brand_new");
    expect(cardStatusTone("brand_new")).toBe("warn");
  });

  it("觸發與最近一次成功：排程／手動／—；失敗不覆蓋較早的成功；從未成功寫「從未成功」", () => {
    expect(triggerText("scheduled")).toBe("排程");
    expect(triggerText("manual")).toBe("手動");
    expect(triggerText(null)).toBe("—");
    expect(lastSuccessText({ lastSuccessAt: "2026-10-26T18:30:30Z" })).toBe(`最近一次成功：${formatDateTime("2026-10-26T18:30:30Z")}`);
    expect(lastSuccessText({ lastSuccessAt: null })).toBe("最近一次成功：從未成功");
  });

  it("備份種類、儲存位置與結果：全備／增備（差異）／增量／邏輯備份；本地 repo1／離站 repo2／離站邏輯；ok／ok_with_errors；表外的值原樣顯示", () => {
    expect(BACKUP_KIND_TEXT).toEqual({ full: "全備", diff: "增備（差異）", incr: "增量", logical: "邏輯備份" });
    expect(backupKindText("incr")).toBe("增量");
    expect(backupKindText("weird")).toBe("weird");
    expect(["repo1", "repo2", "logical", "repo3"].map(backupLocationText)).toEqual(["本地 repo1", "離站 repo2", "離站邏輯", "repo3"]);
    expect(backupResultText("ok")).toEqual({ text: "成功", tone: "ok" });
    expect(backupResultText("ok_with_errors")).toEqual({ text: "成功，但有校驗錯誤", tone: "warn" });
    expect(backupResultText("new_value")).toEqual({ text: "new_value", tone: "warn" });
  });

  it("工作狀態詞表（階段二用）與離站 pg_dump 的位置說明：本機 MinIO 標「與主機同碟」、外部 S3 不標；任一處都不稱「離站已安全」", () => {
    expect(JOB_STATUS_TEXT).toEqual({ QUEUED: "排隊中", RUNNING: "進行中", SUCCEEDED: "成功", FAILED: "失敗", REJECTED: "被拒絕", EXPIRED: "逾時未執行" });
    expect(dumpOffsiteNote(true)).toContain("與主機同碟");
    expect(dumpOffsiteNote(false)).toBe("離站位置：外部 S3");
    expect(dumpOffsiteNote(false)).not.toContain("與主機同碟");
    for (const text of [dumpOffsiteNote(true), dumpOffsiteNote(false)]) {
      expect(text).not.toContain("已安全");
      expect(text).not.toContain("離站已備");
    }
  });
});
