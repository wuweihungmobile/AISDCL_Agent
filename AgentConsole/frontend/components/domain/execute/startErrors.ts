/**
 * 啟動執行失敗時，把後端的 409／400／422／502 變成人看得懂的說明（契約 §1.2.1 驗證順序表、附錄 B.2「執行」列）。
 * reason 是前後端共用的逐字常數（lib/api/reasons.ts），程式判斷一律比對 reason，不拿 message 判斷；
 * details 的 id 以 nameOf 轉成名稱（目標與任務名稱只存在前端已載入的資料裡，轉不出來就顯示 id 前 8 碼）。
 */
import { ApiError } from "@/lib/api/client";
import { REASONS } from "@/lib/api/reasons";
import { SDD_EXECUTE_REASONS, describeSddError } from "@/lib/domain/sddErrors";

export type StartErrorView = {
  /** 一句話標題（通常是 reason） */
  title: string;
  /** 補充說明（每行一條） */
  lines: string[];
  /** 是否因為草案未 signoff（畫面據此顯示「前往審批」） */
  unsigned: boolean;
  traceId?: string;
};

const asIds = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : []);

export function describeStartError(error: unknown, nameOf: (id: string) => string | undefined): StartErrorView {
  if (!(error instanceof ApiError)) {
    return { title: error instanceof Error ? error.message : "啟動失敗", lines: [], unsigned: false };
  }
  // v1.5（整合輪 115；契約 §1.2.1 加註、§1.10.6、附錄 B.5）：SDD 批次的預檢失敗——白話標題與逐項說明；英文 reason 另附「代碼」行方便回報
  if (error.reason && SDD_EXECUTE_REASONS.includes(error.reason)) {
    const sdd = describeSddError(error, "execute");
    const code = /^[a-z_]+$/.test(error.reason) ? [`代碼：${error.reason}`] : [];
    return { title: sdd.title, lines: [...sdd.lines, ...code], unsigned: false, traceId: error.traceId };
  }
  const d = error.details ?? {};
  const label = (id: string) => nameOf(id) ?? id.slice(0, 8);
  const names = (key: string) => asIds(d[key]).map(label);
  const lines: string[] = [];
  const reason = error.reason ?? error.message;
  let unsigned = false;

  switch (error.reason) {
    case REASONS.EXEC_UNSIGNED_DRAFT: {
      unsigned = true;
      if (typeof d.unsignedProjectId === "string") lines.push("專案本身尚未 signoff");
      const goals = names("unsignedGoalIds");
      const tasks = names("unsignedTaskIds");
      if (goals.length) lines.push(`未審批的目標：${goals.join("、")}`);
      if (tasks.length) lines.push(`未審批的任務：${tasks.join("、")}`);
      break;
    }
    case REASONS.EXEC_PROJECT_RUNNING:
      lines.push("這個專案已有進行中的批次；請等它結束，或先取消。");
      break;
    case REASONS.EXEC_PROJECT_STATE_NOT_ALLOWED:
      if (typeof d.status === "string") lines.push(`專案目前狀態：${d.status}`);
      break;
    case REASONS.EXEC_SCOPE_INVALID: {
      const g = names("invalidGoalIds");
      const t = names("invalidTaskIds");
      if (g.length) lines.push(`不屬於此專案的目標：${g.join("、")}`);
      if (t.length) lines.push(`不屬於此專案的任務：${t.join("、")}`);
      break;
    }
    case REASONS.EXEC_SCOPE_ALREADY_COMPLETED: {
      const g = names("goalIds");
      const t = names("taskIds");
      if (g.length) lines.push(`已完成的目標：${g.join("、")}`);
      if (t.length) lines.push(`已完成的任務：${t.join("、")}`);
      break;
    }
    case REASONS.EXEC_SCOPE_MISSING_DEPENDENCIES: {
      const g = names("missingGoalIds");
      if (g.length) lines.push(`需要一併選取的前置目標：${g.join("、")}`);
      break;
    }
    case REASONS.EXEC_NO_RUNNABLE_TASKS:
      lines.push("所選範圍內沒有可執行的任務（都已完成或跳過）。");
      break;
    case REASONS.EXEC_PATH_LOCKED:
      lines.push("同一個專案路徑已有執行中的批次，請等它結束再啟動。");
      break;
    case REASONS.EXEC_PROMPT_TOO_LONG:
      lines.push(`步驟 ${String(d.stepId ?? "")} 的 prompt 長度 ${String(d.length ?? "?")} 超過上限 ${String(d.limit ?? 20000)} 字元。`);
      break;
    case REASONS.EXEC_EVALUATOR_FORBIDDEN_CHARS:
      lines.push(`任務「${label(String(d.taskId ?? ""))}」的評估指令含禁用字元：${asIds(d.chars).join(" ")}`);
      break;
    case REASONS.EXEC_EVALUATOR_NOT_WHITELISTED:
      lines.push(`任務「${label(String(d.taskId ?? ""))}」的評估指令 ${String(d.executable ?? "")} 不在可執行檔白名單。`);
      break;
    case REASONS.EXEC_REGEX_INVALID:
      lines.push(`任務「${label(String(d.taskId ?? ""))}」的 expectedOutputRegex 無法編譯。`);
      break;
    case REASONS.EXEC_TOO_MANY_TASKS:
      lines.push(`範圍內有 ${String(d.count ?? "?")} 個任務，超過單一批次上限 ${String(d.limit ?? 500)}。`);
      break;
    case REASONS.EXEC_MAX_RETRIES_EXCEEDED:
      lines.push(`任務「${label(String(d.taskId ?? ""))}」的最大重試次數 ${String(d.maxRetries ?? "?")} 超過上限 ${String(d.limit ?? 20)}。`);
      break;
    case REASONS.EXEC_ENGINE_REJECTED:
      if (typeof d.bridgeReason === "string") lines.push(`引擎回報：${d.bridgeReason}`);
      break;
    default:
      if (error.errors.length > 0) for (const e of error.errors) lines.push(`${e.field}：${e.message}`);
      else if (error.reason && error.message !== error.reason) lines.push(error.message);
  }

  return { title: reason, lines, unsigned, traceId: error.traceId };
}
