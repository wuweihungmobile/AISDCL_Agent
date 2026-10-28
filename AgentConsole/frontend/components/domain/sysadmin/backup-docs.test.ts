import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { RESTORE_CHECKS, RESTORE_STEPS, VOLUME_COVERAGE } from "@/lib/domain/sysadminBackup";

/**
 * 備份頁的文件鎖（TCS-SysAdminBackup-20261027 載具 FK；AT-BK-08-1-1、08-1-E-1、08-3-1、08-3-E-1；R-BK-43、R-BK-45；PRD AC-BK-08-1、08-3；主控代決第 13 點）：
 *  - AT-BK-08-1-1：UI 的還原指令常數（`RESTORE_STEPS` 的 bash 與 PowerShell、`RESTORE_CHECKS`）的每一條都必須**整行**等於 `docker/README.md` 〈4.3〉節某個 code block 的某一行
 *    （兩邊去前後空白後比；README 的 code block 縮排兩格；**單向**：README 另增指令不紅、不鎖整段文字）；README 刪改任一行、或 UI 改一個字元＝紅；
 *  - AT-BK-08-3-1：涵蓋表 `VOLUME_COVERAGE` 的鍵集合與 `docker-compose.yml` 頂層 `volumes:` 的卷集合**雙向相等**（新增卷沒歸類、或表內有不存在的卷＝紅）；
 *    前端沒有 YAML 依賴，以規則式取頂層區塊並**自證**（取到的卷數須 ≥12，否則「解析失敗」而紅）；現為 14 卷（含備份控制面的 backup_out、backup_req）；
 *    另核對 README〈1.2〉卷表也與涵蓋表雙向相等（運維真相與畫面不得各說各話）；
 *  - AT-BK-08-1-E-1、08-3-E-1：兩個比對純函式 `restoreDocProblems`、`volumeCoverageProblems` 的負控。
 * 純函式放在本檔（只讀檔、只給測試用，不進正式 bundle）。判定指令：npx vitest run components/domain/sysadmin/backup-docs.test.ts -t "<AT 底線形>"
 */
const ROOT = process.cwd();
const AGENT_CONSOLE = path.join(ROOT, "..");
const README = readFileSync(path.join(AGENT_CONSOLE, "docker", "README.md"), "utf-8");
const COMPOSE = readFileSync(path.join(AGENT_CONSOLE, "docker-compose.yml"), "utf-8");

const lines = (text: string): string[] => text.split(/\r?\n/);

// ── AT-BK-08-1-1、08-1-E-1：還原指令與 README〈4.3〉單向相符 ──────────────────────────────

/** 〈4.3〉節（自 `^### 4.3 ` 標題起、到下一個 `^### ` 標題前）內所有 fenced code block 的每一行（去前後空白、丟空行）；沒有該節回 null。fence 行容許前導空白。 */
function restoreCodeLines(readmeText: string): string[] | null {
  const all = lines(readmeText);
  const start = all.findIndex((line) => /^### 4\.3 /.test(line));
  if (start < 0) return null;
  let end = all.findIndex((line, i) => i > start && /^### /.test(line));
  if (end < 0) end = all.length;
  const out: string[] = [];
  let inFence = false;
  for (const raw of all.slice(start + 1, end)) {
    if (/^\s*```/.test(raw)) {
      inFence = !inFence;
      continue;
    }
    if (inFence && raw.trim() !== "") out.push(raw.trim());
  }
  return out;
}

/** UI 指令不在〈4.3〉code block 的清單（空陣列＝全部相符）；找不到〈4.3〉節＝非空（不空過）。 */
function restoreDocProblems(readmeText: string, commands: readonly string[]): string[] {
  const codeLines = restoreCodeLines(readmeText);
  if (codeLines === null) return ["找不到 docker/README.md 的〈4.3〉節（自 `### 4.3 ` 標題起）"];
  const known = new Set(codeLines);
  return commands.filter((command) => !known.has(command.trim())).map((command) => `指令不在〈4.3〉的 code block：${command}`);
}

/** UI 的每一條還原指令字串（三步的 bash、三步的 PowerShell、核對三項）。 */
const uiCommands = (): string[] => [...RESTORE_STEPS.flatMap((step) => [...step.bash, ...step.powershell]), ...RESTORE_CHECKS.map((check) => check.command)];

describe("AT_BK_08_1 還原指令與 README〈4.3〉單向相符（R-BK-43）", () => {
  it("AT_BK_08_1_1 RESTORE_STEPS 的每條 bash 與 PowerShell 指令、RESTORE_CHECKS 的每條指令都整行等於 README〈4.3〉某個 code block 的某一行；步驟順序為停 primary → 容器內 restore.sh → 啟動並以 psql 核對", () => {
    const commands = uiCommands();
    expect(RESTORE_STEPS, "還原三步").toHaveLength(3);
    expect(RESTORE_CHECKS, "核對三項").toHaveLength(3);
    expect(commands.length, "防反空轉：指令數（三步 bash 4、PowerShell 4，核對 3）").toBe(11);
    const codeLines = restoreCodeLines(README) as string[];
    expect(codeLines.length, "防反空轉：〈4.3〉的 code block 行數").toBeGreaterThan(8);
    expect(restoreDocProblems(README, commands)).toEqual([]);
    for (const command of commands) expect(codeLines, command).toContain(command.trim());
    // 順序：第一步停 primary、第二步容器內 restore.sh、第三步啟動 primary 並以 psql 核對
    expect(RESTORE_STEPS[0].bash[0]).toContain("stop postgres-primary");
    expect(RESTORE_STEPS[1].bash[0]).toContain("restore.sh");
    expect(RESTORE_STEPS[2].bash[0]).toContain("start postgres-primary");
    expect(RESTORE_STEPS[2].bash.join("\n")).toContain("psql");
    for (const step of RESTORE_STEPS) {
      expect(step.bash.length, step.title).toBeGreaterThan(0);
      expect(step.powershell.length, `${step.title} 的 PowerShell 形態`).toBe(step.bash.length);
    }
    // PowerShell 形態都是 Push-Location … Pop-Location 成對（鐵律：不裸 cd）
    for (const command of RESTORE_STEPS.flatMap((step) => step.powershell)) {
      expect(command.startsWith("Push-Location AgentConsole;"), command).toBe(true);
      expect(command.endsWith("; Pop-Location"), command).toBe(true);
    }
    // 核對三項依序是列數、時間軸、pgbackrest check
    expect(RESTORE_CHECKS[0].command).toContain("row_count");
    expect(RESTORE_CHECKS[1].command).toContain("timeline_id");
    expect(RESTORE_CHECKS[2].command).toContain("pgbackrest --stanza=aisdlc check");
  });

  it("AT_BK_08_1_E_1 restoreDocProblems 負控：(a) 刪掉含 restore.sh 的 README 行、(b) 改 --target-time 例值的一個字元、(d) UI 常數改一個字元、(e) README 沒有〈4.3〉節各回非空；(c) README 另增一條無關指令行回空；真 README 與真常數回空", () => {
    const commands = uiCommands();
    expect(restoreDocProblems(README, commands), "對照組：真 README 與真常數").toEqual([]);

    // (a) 刪掉含 restore.sh 的那一行（bash 與 PowerShell 兩行都刪＝README 沒有任何 restore.sh 指令）
    const withoutRestore = lines(README)
      .filter((line) => !line.includes("restore.sh"))
      .join("\n");
    const a = restoreDocProblems(withoutRestore, commands);
    expect(a.length).toBeGreaterThanOrEqual(2);
    expect(a.every((problem) => problem.includes("restore.sh"))).toBe(true);

    // (b) 改 --target-time 例值的一個字元
    const changedExample = README.split("2026-10-14 16:39:17+00").join("2026-10-14 16:39:18+00");
    expect(changedExample).not.toBe(README);
    const b = restoreDocProblems(changedExample, commands);
    expect(b.length).toBeGreaterThanOrEqual(2);
    expect(b.join("\n")).toContain("--target-time");

    // (c) README 另增一條無關指令行：單向鎖，不紅
    const extra = README.replace("(cd AgentConsole && docker compose start postgres-primary)", "(cd AgentConsole && docker compose start postgres-primary)\n(cd AgentConsole && docker compose ps)");
    expect(extra).not.toBe(README);
    expect(restoreDocProblems(extra, commands)).toEqual([]);

    // (d) UI 常數改一個字元
    const mutated = commands.map((command, i) => (i === 3 ? command.replace("--yes", "--yez") : command));
    expect(mutated).not.toEqual(commands);
    expect(restoreDocProblems(README, mutated)).toHaveLength(1);

    // (e) README 沒有〈4.3〉節：找不到節＝紅，不空過
    const noSection = README.replace("### 4.3 還原", "### 4.9 還原");
    expect(noSection).not.toBe(README);
    expect(restoreDocProblems(noSection, commands)).toEqual(["找不到 docker/README.md 的〈4.3〉節（自 `### 4.3 ` 標題起）"]);
    // 〈4.3〉節以外的 code block 不算數（指令只出現在別節＝仍紅）
    const moved = ["### 4.2 別節", "```bash", ...commands, "```", "### 4.3 還原", "沒有 code block"].join("\n");
    expect(restoreDocProblems(moved, commands)).toHaveLength(commands.length);
    // fence 行縮排兩格也算（README 的核對三項 code block 縮排）
    expect(restoreDocProblems(["### 4.3 還原", "  ```bash", "  echo ok", "  ```"].join("\n"), ["echo ok"])).toEqual([]);
  });
});

// ── AT-BK-08-3-1、08-3-E-1：涵蓋表與 compose 的卷集合雙向相等 ─────────────────────────────

/** 頂層 `volumes:` 區塊的卷名（自行首 `volumes:` 到下一個頂格鍵或檔尾，取兩格縮排的鍵名；允許鍵後接空白與行尾註解；CRLF 容許）。沒有該區塊回空陣列。 */
function composeVolumes(composeText: string): string[] {
  const all = lines(composeText);
  const start = all.findIndex((line) => /^volumes:\s*(#.*)?$/.test(line));
  if (start < 0) return [];
  const names: string[] = [];
  for (const line of all.slice(start + 1)) {
    if (/^[^\s#]/.test(line)) break; // 下一個頂格鍵
    const m = /^ {2}([A-Za-z0-9_.-]+):\s*(#.*)?$/.exec(line);
    if (m) names.push(m[1]);
  }
  return names;
}

const MIN_VOLUMES = 12;

/** 兩個集合的差異與自證；空陣列＝雙向相等。卷數不足（含完全沒有區塊）＝「解析失敗」而非「兩集合皆空而相等」。 */
function volumeCoverageProblems(composeText: string, coverageKeys: readonly string[]): string[] {
  const volumes = composeVolumes(composeText);
  if (volumes.length < MIN_VOLUMES) return [`解析失敗：頂層 volumes 只取到 ${volumes.length} 個卷（至少 ${MIN_VOLUMES}）`];
  const out: string[] = [];
  for (const volume of volumes) if (!coverageKeys.includes(volume)) out.push(`卷 ${volume} 沒有歸類（涵蓋表缺它）`);
  for (const key of coverageKeys) if (!volumes.includes(key)) out.push(`涵蓋表的 ${key} 不是 compose 的卷`);
  return out;
}

/** README〈1.2 網路與卷〉的卷表（`| 卷 | 用途 |`）第一欄的全部卷名（一列可有多個，以「／」或「、」分隔）。 */
function readmeVolumeTable(readmeText: string): string[] {
  const all = lines(readmeText);
  const start = all.findIndex((line) => /^### 1\.2 /.test(line));
  const end = all.findIndex((line, i) => i > start && /^## /.test(line));
  const section = all.slice(start + 1, end < 0 ? all.length : end);
  const header = section.findIndex((line) => /^\|\s*卷\s*\|/.test(line));
  if (start < 0 || header < 0) return [];
  const names: string[] = [];
  for (const line of section.slice(header + 2)) {
    if (!line.startsWith("|")) break;
    const first = line.split("|")[1] ?? "";
    for (const name of first.split(/[／、]/)) if (name.trim() !== "") names.push(name.trim());
  }
  return names;
}

describe("AT_BK_08_3 涵蓋表與 compose 卷集合雙向相等（R-BK-45）", () => {
  const keys = Object.keys(VOLUME_COVERAGE);

  it("AT_BK_08_3_1 真 docker-compose.yml 頂層 volumes: 取到的卷數 ≥12（自證）；VOLUME_COVERAGE 的鍵集合與它雙向相等；現為 14 卷（含 backup_out 與 backup_req）", () => {
    const volumes = composeVolumes(COMPOSE);
    expect(volumes.length, "自證：取到的卷數").toBeGreaterThanOrEqual(MIN_VOLUMES);
    expect(volumeCoverageProblems(COMPOSE, keys)).toEqual([]);
    expect([...volumes].sort()).toEqual([...keys].sort());
    expect(volumes).toHaveLength(14);
    expect(volumes).toEqual(expect.arrayContaining(["backup_out", "backup_req"]));
  });

  it("AT_BK_08_3_1 README〈1.2〉卷表的卷名集合也與 VOLUME_COVERAGE 雙向相等（運維文件與畫面不得各說各話）", () => {
    const table = readmeVolumeTable(README);
    expect(table.length, "防反空轉：README 卷表取到的卷數").toBeGreaterThanOrEqual(MIN_VOLUMES);
    expect(new Set(table).size, "README 卷表沒有重複卷名").toBe(table.length);
    expect([...table].sort()).toEqual([...keys].sort());
  });

  it("AT_BK_08_3_E_1 volumeCoverageProblems 負控：(a) compose 多一個卷 foo、(b) 涵蓋表多一個鍵 ghost 各回非空並點名；(c) 完全沒有 volumes 區塊回「解析失敗」（卷數 0 < 12，不是兩集合皆空而相等）；(d) CRLF、(e) 鍵後帶行尾註解、(f) 區塊在檔尾的解析結果與 LF／無註解版相同；(g) 服務內縮排 4 格的 volumes: 不被當成頂層", () => {
    const base = composeVolumes(COMPOSE);
    expect(volumeCoverageProblems(COMPOSE, keys), "對照組").toEqual([]);

    // (a) compose 多一個卷 foo（接在區塊最後）
    const withFoo = `${COMPOSE.trimEnd()}\n  foo:\n    driver: local\n`;
    expect(volumeCoverageProblems(withFoo, keys)).toEqual(["卷 foo 沒有歸類（涵蓋表缺它）"]);
    // (b) 涵蓋表多一個鍵 ghost
    expect(volumeCoverageProblems(COMPOSE, [...keys, "ghost"])).toEqual(["涵蓋表的 ghost 不是 compose 的卷"]);
    // (c) 完全沒有 volumes 區塊
    const noBlock = lines(COMPOSE)
      .filter((line) => !/^volumes:/.test(line))
      .join("\n");
    expect(volumeCoverageProblems(noBlock, keys)).toEqual([`解析失敗：頂層 volumes 只取到 0 個卷（至少 ${MIN_VOLUMES}）`]);
    const onlyServices = "services:\n  a:\n    image: x\n    volumes:\n      - pg_data:/data\n";
    expect(volumeCoverageProblems(onlyServices, keys)).toEqual([`解析失敗：頂層 volumes 只取到 0 個卷（至少 ${MIN_VOLUMES}）`]);
    expect(volumeCoverageProblems("", [])).toEqual([`解析失敗：頂層 volumes 只取到 0 個卷（至少 ${MIN_VOLUMES}）`]);
    // (d) CRLF 行尾
    expect(composeVolumes(COMPOSE.replace(/\r?\n/g, "\r\n"))).toEqual(base);
    // (e) 鍵後帶行尾註解（pg_backup 在真檔就帶註解；再造一個「空白加註解」的）
    const commented = COMPOSE.replace(/^ {2}pg_data:\s*$/m, "  pg_data:            # 主資料");
    expect(commented).not.toBe(COMPOSE);
    expect(composeVolumes(commented)).toEqual(base);
    // (f) 區塊在檔尾、其後沒有下一個頂格鍵（HEAD 的實況）：最後一個卷也要取到
    expect(base[base.length - 1]).toBe("backup_req");
    expect(composeVolumes(`${COMPOSE.trimEnd()}`)).toEqual(base);
    // (g) 服務內縮排 4 格的 volumes: 不被當成頂層（它的兩格縮排鍵名也不會被誤取）
    const nested = ["services:", "  web:", "    volumes:", "      - a:/x", "  db:", "    volumes:", "      - b:/y"].join("\n");
    expect(composeVolumes(nested)).toEqual([]);
    // 頂層區塊之後若又有頂格鍵（例如 networks:），不把它底下的兩格縮排鍵當成卷
    const trailing = `${COMPOSE.trimEnd()}\nnetworks:\n  extra-net:\n    driver: bridge\n`;
    expect(composeVolumes(trailing)).toEqual(base);
  });

  it("README 卷表解析的負控：沒有〈1.2〉節或沒有卷表回空陣列（不空過：上面的測試要求 ≥12）；一列多個卷以「／」「、」切開", () => {
    expect(readmeVolumeTable("# 沒有該節")).toEqual([]);
    const sample = ["### 1.2 網路與卷", "", "| 卷 | 用途 |", "|----|------|", "| a／b | x |", "| c、d、e | y |", "| f | z |", "", "## 2. 下一章"].join("\n");
    expect(readmeVolumeTable(sample)).toEqual(["a", "b", "c", "d", "e", "f"]);
  });
});
