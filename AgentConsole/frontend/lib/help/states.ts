/**
 * 狀態詞的白話釋義（TCS-PageHelp-20261027 C3、R-PH-08～R-PH-10；PRD §8.2、D-5、D-11）：十八張表，每張表**全站只寫一份**，頁檔只用表 id 引用（lib/help/<id>.ts 的 states）。
 * 每列只有 `meaning`（這個狀態是什麼意思）與 `next`（通常的下一步）；**刻意沒有 label／name**——狀態名稱只取自既有常數表
 * （components/domain/help/stateSources.ts 的 STATE_SOURCES），說明不自持名稱，畫面改字說明就自動跟著改。
 *
 * 型別鎖（AC-PH-04-2）：物件字面值**逐表 `satisfies`**，外層再 `satisfies Record<StateTableId, …>`；**不得**用 `: Record<StateTableId, Record<string, StateRow>>` 型別註記宣告，
 * 註記會抹掉各表的字面鍵（`keyof typeof STATE_HELP.projectStatus` 退成 string），stateKeys.test.ts 的型別等式就無法成立。
 * 十張有後端 enum 的表以 `Record<該 enum, StateRow>` 為準：enum 經 schema 重產而新增值時，這裡即編譯紅（第一道鎖；執行期鍵集合雙向鎖是第二道）。
 * `serviceState`、`obsClass`、`propClass` 以字面值聯集宣告（lib 不 import hooks 與元件）；`sddPhase`、`sddFsmState`、`propState` 的鍵在執行期展開或無單一常數，只有字串鍵。
 * 每張表的鍵順序＝畫面顯示的列序。
 *
 * 白話規則（PRD §8.3，lint.ts 逐筆檢查）：對「您」說話、一句一事、每句不超過 60 個字、`meaning` 至多 2 句、`next` 恰 1 句；
 * 英文只用白名單詞，所以這裡不引用任何英文狀態名（要提別的狀態就用它的中文標籤）；數字不超過 2 位。
 * `next` 的依據：專案、目標、任務取 PRD 附錄 B 的「可轉移至」；批次與審核取契約附錄 A；匯入取契約 §1.1；連線狀態取 hooks/useServiceStatus.ts 檔頭；
 * SDD 階段取契約 §3.1.5；提案狀態取 SelfImproving PRD §5.1.2。內容是否與出處一致沒有機械判準，由 SCG-4 人讀對照。
 */
import type { AlertRule, ExecutionStepStatus, GateName, GoalStatus, ImportStatus, ProjectStatus, ReviewDecision, ReviewKind, RunStatus, TaskStatus } from "@/lib/api/types";
import type { StateRow, StateTableId } from "./types";

export const STATE_HELP = {
  // ── 專案、目標、任務 ────────────────────────────────────────────────────
  projectStatus: {
    DRAFT: { meaning: "專案剛建立，目標與任務還在設定中，現在不能執行。", next: "設定完成後，狀態會變成「就緒」。" },
    READY: { meaning: "目標與任務都設定好了，隨時可以開始執行。", next: "按下執行之後，狀態會變成「執行中」。" },
    EXECUTING: { meaning: "引擎正在執行這個專案的任務。", next: "做完會變成「完成」，出錯會變成「失敗」，暫停則回到「就緒」。" },
    COMPLETED: { meaning: "專案的任務都已經做完了。", next: "您可以把它封存，讓專案列表保持乾淨。" },
    FAILED: { meaning: "執行過程出錯，專案沒有做完。", next: "修正問題後可以重新執行，也可以直接封存。" },
    ARCHIVED: { meaning: "專案已被刪除並封存，平常的專案列表不會顯示它。", next: "保留期限內，可以在「已刪除」的篩選裡把它復原。" },
  } satisfies Record<ProjectStatus, StateRow>,

  goalStatus: {
    PENDING: { meaning: "目標還沒開始，正在等著輪到它。", next: "輪到時會變成「進行中」，您也可以選擇「跳過」。" },
    IN_PROGRESS: { meaning: "目標底下的任務正在執行。", next: "全部做完會變成「完成」，有任務失敗則變成「失敗」。" },
    COMPLETED: { meaning: "目標底下的任務都已完成，也通過了驗證。", next: "不會再變動，這個目標到此結束。" },
    FAILED: { meaning: "目標底下有任務失敗，目標沒有完成。", next: "重試之後會回到「待處理」，再重新執行。" },
    SKIPPED: { meaning: "您決定略過這個目標，它不會被執行。", next: "不會再變動，這個目標到此結束。" },
  } satisfies Record<GoalStatus, StateRow>,

  taskStatus: {
    PENDING: { meaning: "任務還沒有進入執行流程。", next: "開始執行後，會先變成「排程中」。" },
    QUEUED: { meaning: "任務已經排進佇列，等著輪到它。", next: "輪到時會變成「執行中」，前置任務沒做完則變成「阻塞」。" },
    BLOCKED: { meaning: "任務在等前置任務完成，暫時不能動。", next: "前置任務完成後，會回到「排程中」。" },
    RUNNING: { meaning: "引擎正在執行這個任務的步驟。", next: "做完會進入「驗證中」，出錯、暫停或取消則轉為對應的狀態。" },
    VALIDATING: { meaning: "任務做完了，系統正在檢查它有沒有達到通過標準。", next: "通過會變成「完成」，沒通過則變成「失敗」。" },
    COMPLETED: { meaning: "任務已完成，並且通過了驗證。", next: "不會再變動，這個任務到此結束。" },
    FAILED: { meaning: "任務執行失敗，或是沒有通過驗證。", next: "還能重試就回到「排程中」，重試用完則升級為「待人工」。" },
    ESCALATED: { meaning: "任務失敗且自動重試用完，需要您來處理。", next: "您可以決定重試，讓它回到「排程中」，也可以選擇「跳過」。" },
    PAUSED: { meaning: "任務被暫停，進度先保留著。", next: "繼續執行時，會回到「排程中」重新排隊。" },
    SKIPPED: { meaning: "您決定略過這個任務，它不會被執行。", next: "不會再變動，這個任務到此結束。" },
    CANCELLED: { meaning: "任務已被取消，不會再執行。", next: "不會再變動，這個任務到此結束。" },
  } satisfies Record<TaskStatus, StateRow>,

  // ── 執行與審核 ──────────────────────────────────────────────────────────
  stepStatus: {
    STARTED: { meaning: "引擎開始做這個步驟。", next: "步驟結束後，會再記一筆「完成」或「失敗」。" },
    COMPLETED: { meaning: "這個步驟順利做完了。", next: "引擎會接著開始下一個步驟。" },
    FAILED: { meaning: "這個步驟執行失敗。", next: "引擎會先重試，重試用完就升級給人工處理。" },
    RETRYING: { meaning: "步驟失敗之後，引擎正在重新嘗試。", next: "重試成功會記一筆「完成」，仍失敗就升級給人工處理。" },
  } satisfies Record<ExecutionStepStatus, StateRow>,

  runStatus: {
    INITIALIZING: { meaning: "批次正在啟動，引擎還在準備。", next: "準備好之後，會變成「執行中」。" },
    RUNNING: { meaning: "引擎正在跑這個批次的任務。", next: "做完變成「已完成」，您按暫停會變成「已暫停」，出錯則變成「失敗」。" },
    PAUSED: { meaning: "批次暫停了，可能是您按了暫停，也可能在等您審核。", next: "按「恢復」會回到「執行中」，您也可以選擇「取消」。" },
    COMPLETED: { meaning: "引擎正常跑完，這個批次結束了。", next: "結果可以到監控頁查看，要再做一次時請按「啟動執行」。" },
    FAILED: { meaning: "批次因為升級、額度停機或異常而結束。", next: "請先看審核項與告警，再決定重試、跳過或從斷點恢復。" },
    CANCELLED: { meaning: "批次已被取消，不會再繼續。", next: "想再做的話，請重新按「啟動執行」。" },
  } satisfies Record<RunStatus, StateRow>,

  runTransition: {
    PAUSING: { meaning: "您已按下暫停，引擎正在等目前這一步做完。", next: "做完之後，狀態通常會變成「已暫停」。" },
    CANCELLING: { meaning: "您已按下取消，引擎正在收尾。", next: "收尾之後，狀態通常會變成「已取消」。" },
  } satisfies Record<"PAUSING" | "CANCELLING", StateRow>,

  reviewKind: {
    TASK_CONFIRM: { meaning: "自治等級是 Level 1 時，每個任務開始前都要您確認。", next: "請確認後按「通過」讓批次繼續，或按「拒絕」。" },
    GOAL_CONFIRM: { meaning: "自治等級是 Level 2 時，每個目標開始前都要您確認。", next: "請確認後按「通過」讓批次繼續，或按「拒絕」。" },
    GOAL_COMPLETED: { meaning: "自治等級是 Level 3 時，每個目標完成後都要您審核。", next: "請審核結果，可以按「通過」繼續，也可以按「重試」重做這個目標。" },
    ESCALATED: { meaning: "任務重試用完仍然失敗，或批次失敗，需要您出面處理。", next: "請選擇「重試」、「跳過」或「拒絕」來處理這個失敗。" },
  } satisfies Record<ReviewKind, StateRow>,

  reviewDecision: {
    APPROVE: { meaning: "您同意讓批次照原本的計畫繼續。", next: "依審核項種類而定，按下前確認視窗會先寫明後果。" },
    RETRY: { meaning: "您要求把失敗或剛完成的部分重做一次。", next: "依審核項種類而定，按下前確認視窗會先寫明後果。" },
    SKIP: { meaning: "您決定略過失敗的任務，不再執行它。", next: "依審核項種類而定，按下前確認視窗會先寫明後果。" },
    REJECT: { meaning: "您不同意這個審核項，不讓它往下走。", next: "依審核項種類而定，按下前確認視窗會先寫明後果。" },
  } satisfies Record<ReviewDecision, StateRow>,

  // ── 告警 ────────────────────────────────────────────────────────────────
  alertSeverity: {
    INFO: { meaning: "只是通知您一件事，不影響執行。", next: "看過就好，不需要處理。" },
    WARNING: { meaning: "有些地方偏離了正常，但還不必立刻處理。", next: "請留意它，必要時再調整參數或暫停批次。" },
    CRITICAL: { meaning: "情況嚴重，可能需要您立刻處理。", next: "請盡快查看原因，部分告警會自動暫停批次。" },
  } satisfies Record<"INFO" | "WARNING" | "CRITICAL", StateRow>,

  alertRule: {
    TOKEN_BUDGET_WARNING: { meaning: "Token 用量接近批次的預算，預設達到八成就會提醒。", next: "請評估剩下的預算夠不夠，必要時調整系統參數。" },
    TOKEN_BUDGET_EXCEEDED: { meaning: "Token 用量已經超過預算，系統會要求暫停批次。", next: "請決定要繼續、調整預算，還是取消批次。" },
    CONSECUTIVE_FAILURES: { meaning: "同一個目標底下，連續有好幾個任務失敗。", next: "請先檢查失敗的原因，再決定重試或修改任務。" },
    AGENT_UNRESPONSIVE: { meaning: "引擎很久沒有任何動靜，連健康檢查也失敗。", next: "請確認 Engine Bridge 與引擎是不是還在運作。" },
    TASK_DURATION_EXCEEDED: { meaning: "有任務執行的時間，超過了預期的上限。", next: "請確認任務有沒有卡住，必要時暫停或取消。" },
    HIGH_RETRY_RATE: { meaning: "同一個目標裡，有很多任務都需要重試。", next: "請檢查任務的描述與通過標準是否合理。" },
    ENGINE_ESCALATION: { meaning: "引擎重試多次仍然失敗，已升級給人工處理。", next: "請到執行頁的審核項，決定重試、跳過或拒絕。" },
    ENGINE_TOKEN_HALT: { meaning: "引擎因為 Token 或額度達到門檻而停機。", next: "請確認額度夠不夠，再決定要不要重新執行。" },
  } satisfies Record<AlertRule, StateRow>,

  // ── 匯入 ────────────────────────────────────────────────────────────────
  importStatus: {
    UPLOADED: { meaning: "檔案或文字已經收下，還沒有解析。", next: "按「開始解析」就會拆解內容，解析失敗也會回到這個狀態。" },
    PARSING: { meaning: "系統正在把文件拆成目標與任務。", next: "成功會變成「已解析」，失敗則退回「已上傳」。" },
    PARSED: { meaning: "拆解完成了，等您檢查結果。", next: "您修改內容會變成「審核中」，簽核後即可確認匯入。" },
    REVIEWING: { meaning: "您正在審核或修改拆解的結果。", next: "簽核並確認之後會變成「已匯入」，也可以選擇放棄。" },
    IMPORTED: { meaning: "內容已經匯入，專案、目標與任務都建好了。", next: "不會再變動，請到專案管理查看結果。" },
    REJECTED: { meaning: "您已放棄這筆匯入，沒有建立任何專案。", next: "不會再變動，需要的話請重新上傳。" },
  } satisfies Record<ImportStatus, StateRow>,

  gateName: {
    max_steps: { meaning: "拆解出來的步驟太多，超過系統允許的上限。", next: "請縮小範圍或分批匯入，再重新解析。" },
    cycle: { meaning: "目標之間的前置依賴繞成了一圈，排不出先後。", next: "請修改依賴關係，讓它不再繞圈。" },
    empty_prompt: { meaning: "某個任務的內容是空的，引擎不知道要做什麼。", next: "請補上任務的描述，再重新解析或儲存。" },
    prompt_too_long: { meaning: "某個任務的內容太長，超過系統允許的長度。", next: "請把它拆成比較小的任務。" },
    brain_unsupported: { meaning: "目前設定的模型，不能用來做這項解析。", next: "請到系統設定檢查模型相關的參數。" },
    brain_failed: { meaning: "呼叫模型時失敗，沒有拿到解析結果。", next: "請稍後再試，或檢查模型的連線與金鑰。" },
  } satisfies Record<GateName, StateRow>,

  // ── SDD 引擎 ────────────────────────────────────────────────────────────
  sddPhase: {
    INTAKE: { meaning: "規格流程剛開始，正在判斷情境並把需求拆成待辦。", next: "完成後會進入「規格撰寫」。" },
    SPECIFICATION: { meaning: "正在撰寫規格，並跑規格閘門做檢查。", next: "檢查通過後會進入「人工確認」。" },
    HUMAN_GATE: { meaning: "規格已經通過檢查，正在等您確認。", next: "您核准凍結之後，會進入「規格凍結」。" },
    FROZEN: { meaning: "規格已經凍結，內容被摘要綁定，不能隨意再改。", next: "接著會進入「實作」。" },
    IMPLEMENTATION: { meaning: "正依凍結的規格開發，可能已交給 AutoClaude 執行。", next: "完成後會進入「審查」。" },
    REVIEW: { meaning: "正在審查實作有沒有符合規格。", next: "審查通過後會進入「追溯驗證」。" },
    VERIFICATION: { meaning: "正在核對需求、規格與測試是不是一一對得上。", next: "核對完成後會進入「發布」。" },
    RELEASE: { meaning: "流程已經走到發布，成果可以交付了。", next: "這是主要流程的最後一步。" },
    BLOCKED: { meaning: "流程被擋住了，必須由人工處理才能繼續。", next: "請到專案詳情查看原因，並照畫面上的恢復指令處理。" },
    TRANSIENT: { meaning: "流程正處在兩個階段之間的短暫過渡。", next: "稍後重新整理，通常就會進入下一個階段。" },
    OBSERVATION: { meaning: "這是背景觀測用的狀態，不是主要流程的步驟。", next: "不用處理，這個狀態還不知道會回到哪個階段，所以不畫階段步驟，請看「目前狀態」的原文。" },
    UNKNOWN: { meaning: "系統認不得目前的狀態，無法判斷流程走到哪裡。", next: "請看旁邊顯示的原始狀態文字，必要時回報給維護者。" },
  } satisfies Readonly<Record<string, StateRow>>,

  sddFsmState: {
    HUMAN_PENDING: { meaning: "流程停在人工確認點，等您核准規格。", next: "OPERATOR 以上的角色可以在專案詳情按「核准凍結」。" },
    SPEC_FROZEN: { meaning: "規格已經核准並凍結，內容用摘要綁定起來了。", next: "接著可以開始執行，這個核准無法在 Console 退回。" },
    AUTOCLAUDE_DELEGATED: { meaning: "實作工作已經交給 AutoClaude 執行，流程在旁觀測。", next: "批次結束後會交還控制權，失敗則進入升級狀態。" },
    ESCALATION: { meaning: "流程遇到問題，已經升級，需要人工處理。", next: "請照畫面上的恢復指令，到 SDD 的工作視窗處理。" },
    ESCALATION_FINAL: { meaning: "升級之後的自動處理也失敗了，流程完全停住。", next: "請由人工接手，照恢復指令處理並寫下原因。" },
  } satisfies Readonly<Record<string, StateRow>>,

  // ── 連線 ────────────────────────────────────────────────────────────────
  serviceState: {
    checking: { meaning: "正在檢查連線狀況，還沒有結果。", next: "稍等幾秒，會變成已連線、未連線或未知。" },
    online: { meaning: "連線正常，最近一次檢查是成功的。", next: "不需要處理。" },
    offline: { meaning: "連不上，或是服務回報了伺服器錯誤。", next: "請確認服務有沒有啟動，系統每 30 秒會再檢查一次。" },
    unknown: { meaning: "從來沒有探測過，或暫時拿不到結果，所以不下判斷。", next: "稍等一下，探測完成後就會更新。" },
    idle: { meaning: "您還沒有登入，所以不檢查連線。", next: "登入之後才會開始檢查。" },
  } satisfies Record<"checking" | "online" | "offline" | "unknown" | "idle", StateRow>,

  // ── 自我進化 ────────────────────────────────────────────────────────────
  obsClass: {
    open: { meaning: "這筆觀察還沒有結論，正等著處理。", next: "請決定要修復、要延後，還是直接結案。" },
    deferred: { meaning: "這筆觀察先擱置，等指定的條件出現再處理。", next: "指定的條件出現時，由主機端重新處理，要補充資料可以用「更正」再記一列。" },
    done: { meaning: "這筆觀察已經處理完畢，或已經有結論。", next: "不需要再處理，除非日後問題又出現。" },
  } satisfies Record<"open" | "deferred" | "done", StateRow>,

  propClass: {
    pending: { meaning: "提案已經寫好或驗證完畢，正等您看過卡面後下決定。", next: "請看過卡面後下決定，可能是核准、退回、晉升或否決。" },
    active: { meaning: "您已經做過決定，提案還在流程中往下走。", next: "請等後續步驟完成，需要您決定時它會再回到待決。" },
    done: { meaning: "提案已經有了終局，流程結束。", next: "不需要再處理。" },
  } satisfies Record<"pending" | "active" | "done", StateRow>,

  propState: {
    proposed: { meaning: "提案剛提出，還沒有人下決定。", next: "請看過卡面，決定核准、退回、轉交或否決。" },
    returned: { meaning: "提案被退回了，需要提案者修改後重新提出。", next: "修改完成後，會回到剛提出的狀態再審一次。" },
    approved: { meaning: "您已核准這個提案，接下來會在沙盒（與正式內容隔離的副本）試套用。", next: "系統會自動試套用，不需要您操作。" },
    sandboxed: { meaning: "提案已在沙盒試套用過，正在等驗證。", next: "驗證完成後會出現結果，再由您決定。" },
    verified: { meaning: "提案驗證完成，結果已經出來。", next: "請決定要不要晉升，沒通過的可以退回或否決。" },
    promoted: { meaning: "提案已經正式採納，進入量測期。", next: "接著會量測採納後的效果，期間不需要您操作。" },
    measuring: { meaning: "系統正在量測提案採納後的效果。", next: "量測期結束後會結案，結果是三種之一：沒再出問題、問題又出現，或採納被撤銷。" },
    closed: { meaning: "提案的量測期已經結束，並且有了結論。", next: "不會再變動，日後可以經審核後退役。" },
    rejected: { meaning: "提案已被否決，不會被採納。", next: "不會再變動，同型的提案要先解除冷卻才能再提。" },
    "handed-off": { meaning: "這個提案不能由自動流程處理，已轉交給人工。", next: "請由人工接手處理，不需要再走自動流程。" },
    retired: { meaning: "提案已經退役，日後不再套用。根層目前不會產生這個狀態，畫面為日後預留。", next: "目前不會出現，不需要處理。" },
  } satisfies Readonly<Record<string, StateRow>>,
} satisfies Record<StateTableId, Readonly<Record<string, StateRow>>>;
