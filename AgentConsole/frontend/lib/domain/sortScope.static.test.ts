import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

/**
 * 排序範圍的靜態守衛（TCS-ConsoleUxSortHelp-20261108 AT-963-3-E-1；§2.1 十一張表住九個檔、§2.3 排除項）：
 * 掃 `components/domain/**` 的非測試檔，import 了 `SortableHeader` 的檔集合必須恰為 §2.1 列的九個——
 * 範圍外的表（批次比較、雷達等效表、覆蓋矩陣、路由評分、說明對話框的表、備份說明表…）不得被悄悄加上排序；
 * 要新增可排序的表＝先改規格（TCS §2.1）再改這份清單，兩處同改才綠。掃描器是純函式，附負控樣本。
 */
const ROOT = process.cwd();
const rel = (file: string) => path.relative(ROOT, file).split(path.sep).join("/");
const SKIP_DIRS = new Set(["node_modules", ".next", "tests", "coverage", "test-results", "playwright-report"]);

const EXPECTED = [
  "components/domain/import/HistoryPanel.tsx",
  "components/domain/issues/IssueTable.tsx",
  "components/domain/research/AllowlistDialog.tsx",
  "components/domain/research/EvidenceMatrixTable.tsx",
  "components/domain/research/TraceabilityTable.tsx",
  "components/domain/si/SiEventsPanel.tsx",
  "components/domain/si/SiObservationsPanel.tsx",
  "components/domain/si/SiProposalsPanel.tsx",
  "components/domain/sysadmin/BackupList.tsx",
];

/** 掃描對象：ts／tsx、非測試檔、非 .d.ts、非 `*.fixtures.ts`。 */
function isScannedFile(name: string): boolean {
  return /\.(ts|tsx)$/.test(name) && !/\.test\.tsx?$/.test(name) && !/\.d\.ts$/.test(name) && !/\.fixtures\.ts$/.test(name);
}

function walk(dir: string, out: string[] = []): string[] {
  if (!existsSync(dir)) return out;
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) {
      if (!SKIP_DIRS.has(name)) walk(full, out);
    } else if (isScannedFile(name)) {
      out.push(full);
    }
  }
  return out;
}

/** 純函式：原始碼是否 import 了 `SortableHeader`（具名 import，來源不限路徑寫法）。 */
export function importsSortableHeader(source: string): boolean {
  return /import\s+(?:type\s+)?\{[^}]*\bSortableHeader\b[^}]*\}\s+from\s+["'][^"']+["']/.test(source);
}

describe("AT_963_3_E_1 排序範圍：只有 §2.1 的九個檔 import SortableHeader", () => {
  it("AT_963_3_E_1 components/domain 非測試檔中 import SortableHeader 的檔集合恰為九個", () => {
    const files = walk(path.join(ROOT, "components/domain"));
    expect(files.length, "防反空轉：掃描範圍要真的有檔").toBeGreaterThan(50);
    const hits = files
      .filter((f) => importsSortableHeader(readFileSync(f, "utf-8")))
      .map(rel)
      .sort();
    expect(hits).toEqual([...EXPECTED].sort());
  });

  it("AT_963_3_E_1 範圍外的元件（CompareCard、GatekeeperPanel、CoverageList、RouteDrawer、PageHelpDialog、BackupHelp）都不在集合內", () => {
    const hits = new Set(
      walk(path.join(ROOT, "components/domain"))
        .filter((f) => importsSortableHeader(readFileSync(f, "utf-8")))
        .map((f) => path.basename(f)),
    );
    for (const name of ["CompareCard.tsx", "GatekeeperPanel.tsx", "CoverageList.tsx", "RouteDrawer.tsx", "PageHelpDialog.tsx", "BackupHelp.tsx"]) expect(hits.has(name), name).toBe(false);
  });

  it("AT_963_3_E_1 負控：掃描器認得具名 import（含 type 修飾與多名稱），不誤判註解與只提到字樣的檔", () => {
    expect(importsSortableHeader('import { SortableHeader } from "@/components/domain/common/SortableHeader";')).toBe(true);
    expect(importsSortableHeader('import { A, SortableHeader as S } from "../common/SortableHeader";')).toBe(true);
    expect(importsSortableHeader('// 這裡的表不用 SortableHeader\nimport { Other } from "x";')).toBe(false);
    expect(importsSortableHeader("const SortableHeaderLike = 1;")).toBe(false);
  });
});
