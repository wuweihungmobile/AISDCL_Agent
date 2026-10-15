import { describe, expect, it } from "vitest";

import { resolveVar } from "@/tests/helpers/tokens";
import {
  GOAL_STATUS,
  IMPORT_STATUS,
  PROJECT_STATUS,
  PROJECT_STATUS_TABS,
  TASK_STATUS,
  goalStatus,
  importStatus,
  isImportReopenable,
  isLive,
  isRetryable,
  projectStatus,
  taskStatus,
} from "./status";

/**
 * 設計稿 README〈狀態 enum〉的逐項抄錄（值 → [中文標籤, 色碼]）。
 * 這張表故意與 status.ts 分開寫一份：兩份必須一致，status.ts 才算「照設計稿」。
 */
const README = {
  project: {
    DRAFT: ["草稿", "#7A8775"],
    READY: ["就緒", "#80B155"],
    EXECUTING: ["執行中", "#498428"],
    COMPLETED: ["完成", "#498428"],
    FAILED: ["失敗", "#D35B58"],
    ARCHIVED: ["封存", "#A6B0A1"],
  },
  goal: {
    PENDING: ["待處理", "#A6B0A1"],
    IN_PROGRESS: ["進行中", "#498428"],
    COMPLETED: ["完成", "#498428"],
    FAILED: ["失敗", "#D35B58"],
    SKIPPED: ["跳過", "#A6B0A1"],
  },
  task: {
    PENDING: ["待處理", "#A6B0A1"],
    QUEUED: ["排程中", "#80B155"],
    BLOCKED: ["阻塞", "#F5A623"],
    RUNNING: ["執行中", "#498428"],
    VALIDATING: ["驗證中", "#80B155"],
    COMPLETED: ["完成", "#498428"],
    FAILED: ["失敗", "#D35B58"],
    ESCALATED: ["待人工", "#E55B3C"],
    PAUSED: ["暫停", "#7A8775"],
    SKIPPED: ["跳過", "#A6B0A1"],
    CANCELLED: ["取消", "#A6B0A1"],
  },
} as const;

describe("狀態 enum 對照表（lib/domain/status.ts 是唯一出處）", () => {
  it("專案 6／目標 5／任務 11 個狀態都有中文標籤", () => {
    expect(Object.keys(PROJECT_STATUS)).toHaveLength(6);
    expect(Object.keys(GOAL_STATUS)).toHaveLength(5);
    expect(Object.keys(TASK_STATUS)).toHaveLength(11);
    for (const table of [PROJECT_STATUS, GOAL_STATUS, TASK_STATUS]) {
      for (const meta of Object.values(table)) expect(meta.label).toMatch(/\S/);
    }
  });

  it.each([
    ["project", PROJECT_STATUS],
    ["goal", GOAL_STATUS],
    ["task", TASK_STATUS],
  ] as const)("%s：鍵集合、標籤與解析後的色碼逐項等於設計稿", (kind, table) => {
    const expected = README[kind] as Record<string, readonly [string, string]>;
    expect(Object.keys(table).sort()).toEqual(Object.keys(expected).sort());
    for (const [status, [label, hex]] of Object.entries(expected)) {
      const meta = (table as Record<string, { label: string; color: string }>)[status];
      expect(meta.label, `${kind}.${status} 標籤`).toBe(label);
      // 顏色必須是 token 引用（不寫死色碼），且 token 解析後等於設計稿色碼
      expect(meta.color, `${kind}.${status} 色碼應引用 token`).toMatch(/^var\(--color-[a-z-]+\)$/);
      expect(resolveVar(meta.color), `${kind}.${status} 色碼`).toBe(hex);
    }
  });

  it("後端若新增未知狀態：顯示原值與灰點，不崩潰", () => {
    expect(projectStatus("SOMETHING_NEW").label).toBe("SOMETHING_NEW");
    expect(goalStatus("").label).toBe("未知");
    expect(taskStatus("X").color).toBe("var(--color-text-muted)");
  });

  it("專案狀態 tab 為 全部／草稿／就緒／執行中／完成／失敗（封存不列）", () => {
    expect(PROJECT_STATUS_TABS.map((t) => t.label)).toEqual(["全部", "草稿", "就緒", "執行中", "完成", "失敗"]);
  });

  it("只有 FAILED／ESCALATED 的任務可重試（與後端 409 規則一致）", () => {
    const retryable = Object.keys(TASK_STATUS).filter(isRetryable);
    expect(retryable.sort()).toEqual(["ESCALATED", "FAILED"]);
  });
});

describe("匯入記錄狀態表（契約 §1.1；ImportStatus 六態，lib/domain/status.ts 是唯一出處）", () => {
  const CONTRACT_STATES = ["UPLOADED", "PARSING", "PARSED", "REVIEWING", "IMPORTED", "REJECTED"];

  it("六個狀態都有中文標籤，鍵集合恰等於契約（後端新增狀態時這裡會紅）", () => {
    expect(Object.keys(IMPORT_STATUS).sort()).toEqual([...CONTRACT_STATES].sort());
    for (const meta of Object.values(IMPORT_STATUS)) expect(meta.label).toMatch(/\S/);
    // 標籤互不重複：同一個畫面上兩個狀態不能看起來一樣
    const labels = Object.values(IMPORT_STATUS).map((m) => m.label);
    expect(new Set(labels).size).toBe(labels.length);
  });

  it("顏色一律引用設計 token，且 token 解析得到色碼（不寫死色碼）", () => {
    for (const [status, meta] of Object.entries(IMPORT_STATUS)) {
      expect(meta.color, `${status} 色碼應引用 token`).toMatch(/^var\(--color-[a-z-]+\)$/);
      expect(resolveVar(meta.color), `${status} 色碼`).toMatch(/^#[0-9A-F]{6}$/);
    }
  });

  it("標籤逐項對映（歷史列表與步驟 2 卡直接顯示這些字）", () => {
    expect(Object.fromEntries(Object.entries(IMPORT_STATUS).map(([k, v]) => [k, v.label]))).toEqual({
      UPLOADED: "已上傳",
      PARSING: "解析中",
      PARSED: "已解析",
      REVIEWING: "審核中",
      IMPORTED: "已匯入",
      REJECTED: "已放棄",
    });
  });

  it("未知狀態不崩潰；PARSING 的狀態點會呼吸；只有 UPLOADED／PARSED／REVIEWING 可從歷史重新開啟", () => {
    expect(importStatus("FUTURE_STATE").label).toBe("FUTURE_STATE");
    expect(isLive("PARSING")).toBe(true);
    expect(isLive("PARSED")).toBe(false);
    const reopenable = CONTRACT_STATES.filter(isImportReopenable);
    expect(reopenable.sort()).toEqual(["PARSED", "REVIEWING", "UPLOADED"]);
  });
});
