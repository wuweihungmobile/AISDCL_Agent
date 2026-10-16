import { describe, expect, it } from "vitest";

import type { PendingSignoffItem } from "@/lib/api/types";
import { PENDING_KIND_LABEL, pendingHref, pendingKindLabel, pendingMeta, pendingSignoffTarget, pendingTruncatedNote } from "./signoff";

/** 契約 §1.8.1 的範例形狀：IMPORT 的 projectId／projectName／parentId 為 null，PROJECT 的 projectId 是自己的 id。 */
const item = (patch: Partial<PendingSignoffItem> & Pick<PendingSignoffItem, "kind">): PendingSignoffItem => ({
  id: "i1",
  projectId: "p1",
  projectName: "新專案",
  parentId: null,
  title: "標題",
  createdAt: "2026-10-15T08:30:12Z",
  ...patch,
});

describe("待簽核草案的顯示規則（契約 §1.8.1、§4.5 G-10；v1.4 D-18）", () => {
  it("四種種類的中文標籤：專案／目標／任務／匯入草案（與 SignoffDialog 的標題一致）；未知種類退回原值", () => {
    expect(PENDING_KIND_LABEL).toEqual({ PROJECT: "專案", GOAL: "目標", TASK: "任務", IMPORT: "匯入草案" });
    expect(pendingKindLabel("GOAL")).toBe("目標");
    expect(pendingKindLabel("FUTURE_KIND")).toBe("FUTURE_KIND");
  });

  it("副標：專案草案／目標草案・{專案名}／任務草案・{專案名}／匯入草案（全形中點，契約 G-10）", () => {
    expect(pendingMeta(item({ kind: "PROJECT" }))).toBe("專案草案");
    expect(pendingMeta(item({ kind: "GOAL", projectName: "核心平台" }))).toBe("目標草案・核心平台");
    expect(pendingMeta(item({ kind: "TASK", projectName: "核心平台" }))).toBe("任務草案・核心平台");
    expect(pendingMeta(item({ kind: "IMPORT", projectId: null, projectName: null }))).toBe("匯入草案");
  });

  it("目標或任務缺專案名（契約保證有；防禦性）：只寫「目標草案」，不印出 null", () => {
    expect(pendingMeta(item({ kind: "GOAL", projectName: null }))).toBe("目標草案");
    expect(pendingMeta(item({ kind: "TASK", projectName: null }))).toBe("任務草案");
  });

  it("連結落點：專案→專案詳情、目標→目標詳情、任務→任務詳情（經所屬目標）、匯入草案→匯入頁（沒有深連結）", () => {
    expect(pendingHref(item({ kind: "PROJECT", id: "P", projectId: "P" }))).toBe("/projects/P");
    expect(pendingHref(item({ kind: "GOAL", id: "G", projectId: "P", parentId: "P" }))).toBe("/projects/P/goals/G");
    expect(pendingHref(item({ kind: "TASK", id: "T", projectId: "P", parentId: "G" }))).toBe("/projects/P/goals/G/tasks/T");
    expect(pendingHref(item({ kind: "IMPORT", id: "I", projectId: null, parentId: null }))).toBe("/import");
  });

  it("欄位缺漏（防禦性）：目標或任務的連結退回專案列表，不產生 /projects/null/…", () => {
    expect(pendingHref(item({ kind: "GOAL", id: "G", projectId: null }))).toBe("/projects");
    expect(pendingHref(item({ kind: "TASK", id: "T", projectId: "P", parentId: null }))).toBe("/projects");
    expect(pendingHref(item({ kind: "TASK", id: "T", projectId: null, parentId: "G" }))).toBe("/projects");
  });

  it("「審批」鈕開 SignoffDialog 的目標：kind 轉小寫（project／goal／task／import）、名稱取 title", () => {
    expect(pendingSignoffTarget(item({ kind: "PROJECT", id: "P", title: "專案甲" }))).toEqual({ kind: "project", id: "P", name: "專案甲" });
    expect(pendingSignoffTarget(item({ kind: "GOAL", id: "G", title: "基礎" }))).toEqual({ kind: "goal", id: "G", name: "基礎" });
    expect(pendingSignoffTarget(item({ kind: "TASK", id: "T", title: "初始化" }))).toEqual({ kind: "task", id: "T", name: "初始化" });
    expect(pendingSignoffTarget(item({ kind: "IMPORT", id: "I", title: "需求文件.md" }))).toEqual({ kind: "import", id: "I", name: "需求文件.md" });
  });

  it("清單被 limit 截斷時寫「僅列出最早的 N 筆，共 M 筆」；沒截斷（含剛好等於）不寫", () => {
    expect(pendingTruncatedNote(50, 63)).toBe("僅列出最早的 50 筆，共 63 筆");
    expect(pendingTruncatedNote(50, 50)).toBeNull();
    expect(pendingTruncatedNote(0, 0)).toBeNull();
  });
});
