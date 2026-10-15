import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { CONFIG_CATEGORIES } from "@/lib/api/types";
import { CATEGORY_META, SETTING_LABELS, isMonoSetting, settingLabel } from "./labels";

/**
 * 前端的 50 鍵字典必須與契約附錄 C 的鍵目錄逐鍵一致（契約 §4.6 G-S1：label 由前端字典提供，附錄 C 的鍵名即索引）。
 * 期望值取自契約本身，後端新增或改名鍵時這支測試會轉紅，逼著字典同步。
 */
const md = readFileSync(path.join(process.cwd(), "..", "docs", "02_architecture", "API_Contract_P3-6.md"), "utf-8");

function catalogKeys(): Record<string, string[]> {
  const start = md.indexOf("## 附錄 C");
  const end = md.indexOf("## 附錄 D", start);
  expect(start, "找不到契約附錄 C").toBeGreaterThan(-1);
  expect(end, "找不到契約附錄 D（附錄 C 的結尾）").toBeGreaterThan(start);
  const out: Record<string, string[]> = {};
  let current: string | null = null;
  for (const line of md.slice(start, end).split("\n")) {
    const section = /^### C\.\d+ `(\w+)`/.exec(line);
    if (section) {
      current = section[1];
      out[current] = [];
      continue;
    }
    const row = /^\| `(\w+)` \|/.exec(line);
    if (current && row) out[current].push(row[1]);
  }
  return out;
}

describe("設定頁字典與契約附錄 C 一致", () => {
  const catalog = catalogKeys();

  it("六個分類與鍵數量：model 10、agent 9、execution 10、monitor 6、autoclaude 11、sdd 4（共 50）", () => {
    expect(Object.keys(catalog)).toEqual([...CONFIG_CATEGORIES]);
    expect(Object.fromEntries(Object.entries(catalog).map(([k, v]) => [k, v.length]))).toEqual({
      model: 10,
      agent: 9,
      execution: 10,
      monitor: 6,
      autoclaude: 11,
      sdd: 4,
    });
  });

  it("契約的每個鍵都有中文名稱；字典沒有契約以外的鍵", () => {
    const contractIds = Object.entries(catalog).flatMap(([cat, keys]) => keys.map((k) => `${cat}.${k}`));
    expect(contractIds).toHaveLength(50);
    expect(contractIds.filter((id) => !(id in SETTING_LABELS))).toEqual([]);
    expect(Object.keys(SETTING_LABELS).filter((id) => !contractIds.includes(id))).toEqual([]);
  });

  it("名稱互不重複（同一分類內兩列不能看起來一樣）；每個分類 tab 有標籤與圖示", () => {
    for (const [cat, keys] of Object.entries(catalog)) {
      const labels = keys.map((k) => settingLabel(cat, k));
      expect(new Set(labels).size, `${cat} 的名稱重複`).toBe(labels.length);
    }
    expect(CONFIG_CATEGORIES.map((c) => CATEGORY_META[c].label)).toEqual(["模型", "Agent", "執行", "監控", "AutoClaude", "SDD"]);
    for (const c of CONFIG_CATEGORIES) expect(CATEGORY_META[c].icon).toBeTruthy();
  });

  it("字典沒有的鍵退回鍵名（後端新增鍵不崩潰）；技術字串（URL、命令、DSN）用等寬字體", () => {
    expect(settingLabel("model", "futureKey")).toBe("futureKey");
    expect(isMonoSetting("model", "apiUrl")).toBe(true);
    expect(isMonoSetting("autoclaude", "claudeCommand")).toBe(true);
    expect(isMonoSetting("agent", "maxRetries")).toBe(false);
  });
});
