import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ToastProvider } from "@/components/ui/toast";
import type { ParsedResult } from "@/lib/api/types";
import { NodeEditDialog, type NodeTarget } from "./NodeEditDialog";
import { EXECUTION_PATH_HINT } from "./sourceRules";
import { toTree } from "./tree";

// Markdown 編輯器本體很重且與本測試無關：換成同名的簡單 textarea（同 StructureCard.test.tsx 的做法）
vi.mock("@/components/markdown/MarkdownEditor", () => ({
  MarkdownEditor: ({ value, label }: { value: string; label: string }) => <textarea aria-label={label} defaultValue={value} readOnly />,
}));

const PARSED: ParsedResult = {
  project: { name: "E2E 匯入專案", executionPath: "/workspace/e2e", passCriteria: "三個目標全部完成", description: "由 BRD 匯入", autonomyLevel: 3 },
  goals: [
    { key: "g1", name: "基礎", passCriteria: "基礎任務完成", sortOrder: 0, dependsOn: [], tasks: [{ name: "初始化", description: "輸出 [T1_DONE]", passCriteria: "輸出含 [T1_DONE]", sortOrder: 0 }] },
  ],
};

function renderDialog(target: NodeTarget) {
  return render(
    <ToastProvider>
      <NodeEditDialog target={target} tree={toTree(PARSED)} dispatch={vi.fn()} onClose={vi.fn()} />
    </ToastProvider>,
  );
}

const ROOT = process.cwd();
const read = (rel: string) => readFileSync(path.join(ROOT, rel), "utf-8");

describe("AT_940_6_1 節點編輯對話框的執行路徑欄有兩模式說明（R27；OBS-SI-230）", () => {
  it("AT_940_6_1 專案節點：欄下顯示 EXECUTION_PATH_HINT（含本機與 Docker 全棧兩種寫法），輸入框以 aria-describedby 連到它，欄位標籤仍為精確的「執行路徑」", () => {
    renderDialog({ kind: "project" });
    const hint = screen.getByText(EXECUTION_PATH_HINT);
    expect(hint).toHaveTextContent("本機開發填主機路徑");
    expect(hint).toHaveTextContent("Docker 全棧填 Bridge 容器內的路徑");
    expect(hint).toHaveTextContent("/workspace/");
    expect(hint).toHaveTextContent("BRIDGE_ALLOWED_PATH_ROOTS");
    // 標籤不含說明文字（說明放在 Field 外、不進可及名稱），getByLabelText 用精確的「執行路徑」取得輸入框
    const input = screen.getByLabelText("執行路徑");
    expect(input.tagName).toBe("INPUT");
    expect(input).toHaveValue("/workspace/e2e");
    expect(input).toHaveAccessibleDescription(EXECUTION_PATH_HINT);
    expect(input.getAttribute("aria-describedby")).toBe(hint.id);
    expect(hint.id).not.toBe("");
  });

  it("AT_940_6_1 目標與任務節點的對話框沒有執行路徑欄，也沒有這段說明", () => {
    const goal = renderDialog({ kind: "goal", mode: "edit", key: "g1" });
    expect(screen.queryByLabelText("執行路徑")).toBeNull();
    expect(screen.queryByText(EXECUTION_PATH_HINT)).toBeNull();
    goal.unmount();
    renderDialog({ kind: "task", mode: "edit", goalKey: "g1", uid: "t-0-0" });
    expect(screen.queryByLabelText("執行路徑")).toBeNull();
    expect(screen.queryByText(EXECUTION_PATH_HINT)).toBeNull();
  });
});

describe("AT_940_6_E_1 執行路徑說明三處同源、不複製字串（R27）", () => {
  const IMPORT_FROM_SOURCE_RULES = /import\s*\{[^}]*\bEXECUTION_PATH_HINT\b[^}]*\}\s*from\s*["'](\.\/sourceRules|@\/components\/domain\/import\/sourceRules)["']/;

  it("AT_940_6_E_1 NodeEditDialog.tsx 自 sourceRules import EXECUTION_PATH_HINT，原始碼不含該常數字串的任何連續 10 字元以上的子串", () => {
    const source = read("components/domain/import/NodeEditDialog.tsx");
    expect(source).toMatch(IMPORT_FROM_SOURCE_RULES);
    expect(EXECUTION_PATH_HINT.length).toBeGreaterThan(40);
    for (let i = 0; i + 10 <= EXECUTION_PATH_HINT.length; i += 1) {
      const piece = EXECUTION_PATH_HINT.slice(i, i + 10);
      expect(source.includes(piece), `NodeEditDialog.tsx 複製了說明文字的片段：「${piece}」`).toBe(false);
    }
  });

  it("AT_940_6_E_1 三處使用者（SourceCard、EntityForms、NodeEditDialog）引用同一個檔案匯出的同一個常數，sourceRules.ts 是唯一定義處", () => {
    for (const user of ["components/domain/import/SourceCard.tsx", "components/domain/entity/EntityForms.tsx", "components/domain/import/NodeEditDialog.tsx"]) {
      expect(read(user), `${user} 沒有自 sourceRules 匯入 EXECUTION_PATH_HINT`).toMatch(IMPORT_FROM_SOURCE_RULES);
    }
    expect(read("components/domain/import/sourceRules.ts")).toMatch(/export const EXECUTION_PATH_HINT\s*=/);
    // 全站只有 sourceRules.ts 定義這段字串（不複製）：以說明文字的兩個特徵片段搜尋所有非測試原始碼
    for (const dir of ["components", "lib", "app", "hooks"]) {
      const hits = findSources(path.join(ROOT, dir)).filter((file) => /Docker 全棧填 Bridge 容器內的路徑/.test(readFileSync(file, "utf-8")));
      for (const file of hits) expect(path.relative(ROOT, file).split(path.sep).join("/"), "說明文字被複製到 sourceRules.ts 以外").toBe("components/domain/import/sourceRules.ts");
    }
  });
});

/** 非測試原始碼（遞迴；略過 node_modules 與 .next）。 */
function findSources(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) {
      if (name !== "node_modules" && name !== ".next") out.push(...findSources(full));
    } else if (/\.(ts|tsx)$/.test(name) && !/\.test\.tsx?$/.test(name)) {
      out.push(full);
    }
  }
  return out;
}
