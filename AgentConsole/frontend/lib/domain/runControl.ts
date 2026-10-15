/**
 * 執行頁「執行控制」按鈕狀態機（契約 §1.2.4～1.2.6、§1.2.10、§4.2 E-07、E-08；設計稿畫面 7）。純函式、不依賴 React。
 *
 * 規則來源（每條都有對應測試）：
 *  - 沒有批次、或批次已終態（COMPLETED／FAILED／CANCELLED）→「啟動執行」；終態批次另可「從斷點恢復」（restore 接受終態，且只限專案最新批次）。
 *  - RUNNING → 「暫停」「取消」；Bridge 過渡態（bridgeStatus）：PAUSING 時暫停鈕停用並顯示處理中、CANCELLING 時兩顆都停用（契約 §4.2 E-07）。
 *  - PAUSED → 「恢復」「取消」「從斷點恢復」。
 *  - INITIALIZING（引擎啟動中）：暫停與取消都會被後端 409（pause 只收 RUNNING、cancel 只收 RUNNING／PAUSED），所以顯示但停用。
 *  - 唯讀角色（VIEWER）全部停用；有請求在途（busy）全部停用；
 *    「啟動執行」另受簽核鎖定（專案、所選目標或任務未 signoff → 後端 409；前端停用只是體驗）。
 */
import type { BridgeRunStatus, RunStatus } from "@/lib/api/types";
import { isRunTerminal } from "@/lib/domain/status";

export type ControlAction = "start" | "pause" | "resume" | "cancel" | "restore";

export type ControlButton = {
  action: ControlAction;
  label: string;
  enabled: boolean;
  /** 停用（或需要提醒）時的說明，給 title 與螢幕閱讀器 */
  hint?: string;
};

export type ControlInput = {
  run: { status: RunStatus; bridgeStatus?: BridgeRunStatus | null } | null | undefined;
  /** 角色可寫入（OPERATOR／ADMIN） */
  canWrite: boolean;
  /** 簽核鎖定：true＝不可啟動 */
  locked: boolean;
  /** 有請求在途（啟動、暫停、恢復、取消、還原、審核） */
  busy?: boolean;
  /** 這個批次是專案最新的一批（restore 只收最新批次）；未知視為是 */
  isLatest?: boolean;
  /** 已知沒有任何斷點（false 時還原鈕停用）；未知視為有 */
  hasCheckpoints?: boolean;
};

const READ_ONLY_HINT = "權限不足（唯讀角色）";

export function controlButtons(input: ControlInput): ControlButton[] {
  const { run, canWrite, locked, busy = false, isLatest = true, hasCheckpoints = true } = input;
  const base = (action: ControlAction, label: string, extra: { enabled?: boolean; hint?: string } = {}): ControlButton => {
    let enabled = extra.enabled ?? true;
    let hint = extra.hint;
    if (!canWrite) {
      enabled = false;
      hint = READ_ONLY_HINT;
    } else if (busy) {
      enabled = false;
      hint = "處理中，請稍候";
    }
    return { action, label, enabled, hint };
  };

  const restore = (): ControlButton => {
    if (!isLatest) return base("restore", "從斷點恢復", { enabled: false, hint: "只能還原專案最新的執行批次" });
    if (!hasCheckpoints) return base("restore", "從斷點恢復", { enabled: false, hint: "這個批次還沒有可用的斷點" });
    return base("restore", "從斷點恢復");
  };

  if (!run || isRunTerminal(run.status)) {
    const start = base("start", "啟動執行", locked ? { enabled: false, hint: "草案未經 signoff，禁止執行（後端會回 409）" } : {});
    return run ? [start, restore()] : [start];
  }

  const bridge = run.bridgeStatus ?? undefined;
  switch (run.status) {
    case "INITIALIZING":
      return [
        base("pause", "暫停", { enabled: false, hint: "引擎啟動中，啟動完成後才能暫停" }),
        base("cancel", "取消", { enabled: false, hint: "引擎啟動中，啟動完成後才能取消" }),
      ];
    case "RUNNING": {
      const pausing = bridge === "PAUSING";
      const cancelling = bridge === "CANCELLING";
      return [
        pausing
          ? base("pause", "暫停中…", { enabled: false, hint: "已要求暫停，會在下一個步驟邊界生效" })
          : base("pause", "暫停", cancelling ? { enabled: false, hint: "取消處理中" } : {}),
        cancelling ? base("cancel", "取消中…", { enabled: false, hint: "已要求取消，引擎收尾中" }) : base("cancel", "取消"),
      ];
    }
    case "PAUSED":
      return [base("resume", "恢復"), base("cancel", "取消"), restore()];
    default:
      return [base("start", "啟動執行", locked ? { enabled: false, hint: "草案未經 signoff，禁止執行" } : {})];
  }
}

/** 找某個動作的按鈕（元件與測試用）。 */
export function buttonFor(buttons: readonly ControlButton[], action: ControlAction): ControlButton | undefined {
  return buttons.find((b) => b.action === action);
}
