import { describe, expect, it } from "vitest";

import { contrastRatio, resolveVar, tokenHex } from "@/tests/helpers/tokens";
import {
  ALERT_RULE_LABEL,
  ALERT_SEVERITY,
  GOAL_STATUS,
  IMPORT_STATUS,
  LOG_LEVEL_COLOR,
  PROJECT_STATUS,
  PROJECT_STATUS_TABS,
  REVIEW_DECISION_LABEL,
  REVIEW_DECISION_ORDER,
  REVIEW_KIND,
  RUN_STATUS,
  RUN_TERMINAL,
  STEP_STATUS,
  TASK_STATUS,
  alertSeverity,
  alertSeverityTextColor,
  goalStatus,
  importStatus,
  isImportReopenable,
  isLive,
  isRetryable,
  isRunTerminal,
  projectStatus,
  reviewKind,
  runStatusMeta,
  stepStatus,
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

/**
 * 無障礙覆寫（W5 C-18；DEF-AC-004）：設計稿的三個語意色拿來當文字時對比不足 WCAG AA，
 * styles/tokens.console.css 的「無障礙覆寫」一節把它們改深（原因與逐底色的數字在該檔；styles/tokens.test.ts 鎖對比）。
 * 上面的抄錄表維持設計稿原值；比對時只有這三個色碼套用覆寫，其餘一律要與設計稿相同——偏離面因此只有這三格，不會悄悄變大。
 */
const A11Y_OVERRIDE: Record<string, string> = {
  "#7A8775": "#5F6B5A", // --color-text-muted（草稿、暫停的狀態色）
  "#E55B3C": "#B93F22", // --color-accent（待人工）
  "#D35B58": "#B8433F", // --color-error（失敗）
};

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
      expect(resolveVar(meta.color), `${kind}.${status} 色碼`).toBe(A11Y_OVERRIDE[hex] ?? hex);
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

describe("執行批次與審核項標籤（契約 §1.2、§3.6、附錄 A.1；RunStatus／ReviewKind）", () => {
  it("RunStatus 六態都有中文標籤，鍵集合恰等於契約（後端新增狀態時這裡會紅），標籤互不重複", () => {
    expect(Object.keys(RUN_STATUS).sort()).toEqual(["CANCELLED", "COMPLETED", "FAILED", "INITIALIZING", "PAUSED", "RUNNING"]);
    expect(Object.fromEntries(Object.entries(RUN_STATUS).map(([k, v]) => [k, v.label]))).toEqual({
      INITIALIZING: "啟動中",
      RUNNING: "執行中",
      PAUSED: "已暫停",
      COMPLETED: "已完成",
      FAILED: "失敗",
      CANCELLED: "已取消",
    });
    const labels = Object.values(RUN_STATUS).map((m) => m.label);
    expect(new Set(labels).size).toBe(labels.length);
  });

  it("終態＝COMPLETED／FAILED／CANCELLED（SSE 到此關閉、重連回 204）；PAUSED 不是終態", () => {
    expect([...RUN_TERMINAL].sort()).toEqual(["CANCELLED", "COMPLETED", "FAILED"]);
    for (const s of Object.keys(RUN_STATUS)) expect(isRunTerminal(s), s).toBe(RUN_TERMINAL.includes(s as never));
    expect(isRunTerminal("PAUSED")).toBe(false);
    expect(isRunTerminal(undefined)).toBe(false);
  });

  it("RUNNING＋Bridge 過渡態：PAUSING 顯示「暫停中」、CANCELLING 顯示「取消中」；其餘照 RunStatus", () => {
    expect(runStatusMeta("RUNNING", "PAUSING").label).toBe("暫停中");
    expect(runStatusMeta("RUNNING", "CANCELLING").label).toBe("取消中");
    expect(runStatusMeta("RUNNING", "RUNNING").label).toBe("執行中");
    expect(runStatusMeta("RUNNING").label).toBe("執行中");
    // 過渡態只在 RUNNING 底下才成立（PAUSED 的 run 不會再有 PAUSING）
    expect(runStatusMeta("PAUSED", "PAUSING").label).toBe("已暫停");
    expect(runStatusMeta("NEW_STATE").label).toBe("NEW_STATE");
  });

  it("狀態點會呼吸的狀態含啟動中與執行中", () => {
    expect(isLive("RUNNING")).toBe(true);
    expect(isLive("INITIALIZING")).toBe(true);
    expect(isLive("PAUSED")).toBe(false);
  });

  it("ReviewKind 四種都有中文標籤（V3 的 CHECK 不擴充）；未知種類不崩潰", () => {
    expect(Object.fromEntries(Object.entries(REVIEW_KIND).map(([k, v]) => [k, v.label]))).toEqual({
      TASK_CONFIRM: "確認任務",
      GOAL_CONFIRM: "確認目標",
      GOAL_COMPLETED: "目標完成審核",
      ESCALATED: "需人工介入",
    });
    expect(reviewKind("FUTURE_KIND").label).toBe("FUTURE_KIND");
  });

  it("審核決定四顆按鈕的文字與順序＝設計稿（通過／重試／跳過／拒絕）", () => {
    expect(REVIEW_DECISION_ORDER.map((d) => REVIEW_DECISION_LABEL[d])).toEqual(["通過", "重試", "跳過", "拒絕"]);
    expect(Object.keys(REVIEW_DECISION_LABEL).sort()).toEqual(["APPROVE", "REJECT", "RETRY", "SKIP"]);
  });

  it("步驟事件四態、告警嚴重度與八條規則、日誌等級色：標籤齊全、顏色一律引用 token", () => {
    expect(Object.keys(STEP_STATUS).sort()).toEqual(["COMPLETED", "FAILED", "RETRYING", "STARTED"]);
    expect(stepStatus("RETRYING").label).toBe("重試");
    expect(alertSeverity("CRITICAL").label).toBe("嚴重");
    expect(alertSeverity("WARNING").label).toBe("警告");
    expect(Object.keys(ALERT_RULE_LABEL)).toHaveLength(8);
    for (const label of Object.values(ALERT_RULE_LABEL)) expect(label).toMatch(/\S/);
    const tables: Array<Record<string, { color: string }>> = [RUN_STATUS, REVIEW_KIND, STEP_STATUS, ALERT_SEVERITY];
    for (const table of tables) {
      for (const [k, meta] of Object.entries(table)) {
        expect(meta.color, `${k} 色碼應引用 token`).toMatch(/^var\(--color-[a-z-]+\)$/);
        expect(resolveVar(meta.color), `${k} 色碼`).toMatch(/^#[0-9A-F]{6}$/);
      }
    }
    for (const [level, color] of Object.entries(LOG_LEVEL_COLOR)) {
      expect(resolveVar(color), `${level} 色碼`).toMatch(/^#[0-9A-F]{6}$/);
    }
  });

  it("拿來當「文字」的顏色（日誌等級、告警規則名稱）在它們的底色上 ≥ 4.5:1（WCAG AA；DEF-AC-004）——狀態點的顏色不能直接當文字用", () => {
    // 日誌查詢列放在 bg-base 上；告警列放在 alert-bg 上
    for (const [level, color] of Object.entries(LOG_LEVEL_COLOR)) {
      expect(contrastRatio(resolveVar(color)!, tokenHex("color-bg-base")!), `日誌等級 ${level}`).toBeGreaterThanOrEqual(4.5);
    }
    for (const severity of ["INFO", "WARNING", "CRITICAL", "UNKNOWN"]) {
      const color = alertSeverityTextColor(severity);
      expect(color, `${severity} 應引用 token`).toMatch(/^var\(--color-[a-z-]+\)$/);
      expect(contrastRatio(resolveVar(color)!, tokenHex("color-alert-bg")!), `告警 ${severity}`).toBeGreaterThanOrEqual(4.5);
    }
    // 反面：狀態點用的 WARNING／INFO 顏色當文字在告警底上確實不過，所以才需要另一組文字色
    expect(contrastRatio(resolveVar(ALERT_SEVERITY.WARNING.color)!, tokenHex("color-alert-bg")!)).toBeLessThan(4.5);
    expect(contrastRatio(resolveVar(ALERT_SEVERITY.INFO.color)!, tokenHex("color-alert-bg")!)).toBeLessThan(4.5);
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
