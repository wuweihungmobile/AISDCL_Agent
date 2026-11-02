package com.aisdlc.console.adapter.in.web;

import java.util.Map;

/**
 * 研究端點（ResearchToPRD P0；API 契約 §0.2 共通失敗表）在 OpenAPI 文件裡的專屬錯誤說明，供 {@link ErrorResponseDocumentation} 併入：每個研究操作補列它<b>實際會回</b>的
 * 409／422／502／503／504，與研究專屬的 403（{@code research_write_forbidden}）與 404（reason {@code research_not_found}）說明文字。reason 逐字取自契約
 * （{@code ResearchReasonsTest} 以 {@code ErrorReasons} 的研究常數、前端 {@code RESEARCH_REASONS} 與契約 reason 表三方雙向鎖住「每個 reason 都在說明裡出現」）。
 *
 * <p>鍵一律是「方法＋路徑」（同 {@link ErrorResponseDocumentation} 的 EXTRA）。研究讀取端點（GET）只有 404（有路徑變數者）與 Bridge 轉述端點的上游失敗。
 */
final class ResearchErrorDocs {

    /** 研究操作的 404 說明：「404 的 reason 省略」慣例的例外（AT-960-5-6）。 */
    static final String NOT_FOUND = "研究專案不存在，或指定的版本、輪、矩陣版本、條目不存在（reason research_not_found；「404 的 reason 省略」慣例的例外之一）。"
            + "已封存的專案仍可讀；Bridge 的 404（例：fsm_not_found）reason 逐字轉出";

    /** 研究寫入端點的 403：通用說明加研究專屬的 research_write_forbidden。 */
    static final String FORBIDDEN = "角色不足（reason ACCESS_DENIED：VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；approve、return 與 allowlist 的新增／停用僅 ADMIN）；"
            + "另有 research_write_forbidden：Bridge 拒絕 backend 附的研究寫入權杖（兩端的 BRIDGE_RESEARCH_WRITE_TOKEN 設定不一致），"
            + "或 OPERATOR 嘗試換世代（reinit 帶 generation=next 僅 ADMIN；服務層入口檢查、Bridge 請求數 0）";

    private static final String DISABLED = "research_write_disabled：backend 或 Bridge 沒有設定研究寫入權杖（BRIDGE_RESEARCH_WRITE_TOKEN），研究寫入面停用（backend 未設時不發出任何請求）；"
            + "research_requires_db：Bridge 沒有 BRIDGE_DB_DSN（研究端點不降級成純檔案模式）；db_blocked：研究資料庫暫時不可用";
    private static final String UNREACHABLE = "bridge_unreachable：連不上 Engine Bridge（連線階段失敗，請求確定沒有送達；連線 2 秒）；或 Bridge 回報上游失敗——"
            + "not_implemented（Bridge 端點本體尚未實作，details.endpoint，console-api 不假裝成功）、init_failed（專案初始化的某一步失敗，details.step；游標已標 FAILED，以 reinit 補建）；"
            + "其餘 5xx＝引擎橋接服務錯誤。寫入不重試";
    private static final String TIMEOUT = "bridge_timeout：讀取逾時（請求已送出、結果不明；寫入讀取 30 秒、不重試）";
    private static final String UNPROCESSABLE = "輸入閘未通過（reason invalid_request；details.violations[{field,rule,message}] 一次全列，errors[] 同內容），或 Bridge 拒絕此請求"
            + "（reason 逐字取自 Bridge：invalid_request｜terms_ack_required｜sanitization_failed｜layer_unavailable；details.violations）";

    /** 寫入端點共用的上游失敗與輸入閘。 */
    private static Map<String, String> writeFailures(String unprocessable) {
        return Map.of("422", unprocessable, "502", UNREACHABLE, "503", DISABLED, "504", TIMEOUT);
    }

    /** 會回 409 的研究操作及其說明（reason 逐字）。 */
    static final Map<String, String> CONFLICT = Map.of(
            "POST /api/v1/research/projects", "slug_in_use：slug 已被未封存的研究專案使用",
            "PUT /api/v1/research/projects/{id}/prd", "prd_version_conflict（baseVersion 不是目前 head 版號；details.headVersion）｜spec_frozen（Gate 0 之後不可再存新版）",
            "POST /api/v1/research/projects/{id}/stages/{stage}", "stage_conflict（同專案已有進行中的 stage〔details.activeStageRunId、activeStage〕、"
                    + "前置條件未滿足〔details.unmet 逐條列出 rule 與說明〕、或全站並行上限〔details.cause=max_concurrent_runs、limit、active〕；不排隊、不重試）"
                    + "｜fsm_state_conflict（details.current_state；afterEscalation 但 FSM 仍在 ESCALATION*）｜escalated（外環 FSM 在 ESCALATION*，details.recovery 帶恢復指令）"
                    + "｜spec_frozen（Gate 0 之後）",
            "POST /api/v1/research/projects/{id}/approve", "review_not_passed（head 版本沒有通過的審查輪）｜spec_digest_changed（檔案摘要與核准人看到的不同；details.pair）"
                    + "｜fsm_state_conflict（FSM 現態不是 HUMAN_PENDING，或已核准過——非冪等；details.expected_state、current_state）｜escalated（FSM 在 ESCALATION*）",
            "POST /api/v1/research/projects/{id}/return", "fsm_state_conflict（FSM 現態不是 HUMAN_PENDING；details.current_state）｜escalated（FSM 在 ESCALATION*）",
            "POST /api/v1/research/projects/{id}/archive", "stage_conflict（有進行中的 stage；details.reason=stage_running）",
            "POST /api/v1/research/projects/{id}/reinit", "stage_conflict（重試初始化：flowStatus 不是 FAILED，或 flowDetail 不以 init_failed: 起頭；"
                    + "details.flowStatus、flowDetail；零寫入）｜fsm_state_conflict（換世代：FSM 現態不在 ESCALATION*；details.current_state）",
            "POST /api/v1/research/allowlist", "allowlist_exists：同 listKind 與 host 已有條目");

    /** 研究操作的其餘狀態碼（422／502／503／504）：方法＋路徑 → 狀態碼與說明。 */
    static final Map<String, Map<String, String>> EXTRA = Map.ofEntries(
            Map.entry("GET /api/v1/research/capabilities", Map.of("502", UNREACHABLE, "504", TIMEOUT)),
            Map.entry("GET /api/v1/research/allowlist", Map.of("502", UNREACHABLE, "503", "db_blocked：研究資料庫暫時不可用；research_requires_db：Bridge 沒有 BRIDGE_DB_DSN",
                    "504", TIMEOUT)),
            Map.entry("GET /api/v1/research/projects/{id}/fsm", Map.of(
                    "422", "FSM 狀態檔壞掉（Bridge 的 fsm_state_unreadable）或 root 不合（sanitization_failed）；reason 逐字取自 Bridge",
                    "502", UNREACHABLE, "504", "bridge_timeout：讀取逾時（讀取 3 秒、不重試）")),
            Map.entry("POST /api/v1/research/projects", writeFailures(UNPROCESSABLE)),
            Map.entry("PUT /api/v1/research/projects/{id}/prd", writeFailures(UNPROCESSABLE)),
            Map.entry("POST /api/v1/research/projects/{id}/stages/{stage}", writeFailures("stage 不在 research｜draft｜review｜revise｜iterate｜tcs-draft（reason invalid_request），"
                    + "或 Bridge 拒絕此請求（reason 逐字取自 Bridge；details.violations）")),
            Map.entry("POST /api/v1/research/projects/{id}/approve", writeFailures(UNPROCESSABLE)),
            Map.entry("POST /api/v1/research/projects/{id}/return", writeFailures(UNPROCESSABLE)),
            Map.entry("POST /api/v1/research/projects/{id}/cancel", Map.of("502", UNREACHABLE, "503", DISABLED, "504", TIMEOUT)),
            Map.entry("POST /api/v1/research/projects/{id}/reconcile", Map.of("502", UNREACHABLE, "503", DISABLED, "504", TIMEOUT)),
            Map.entry("POST /api/v1/research/projects/{id}/archive", Map.of("502", UNREACHABLE, "503", DISABLED, "504", TIMEOUT)),
            Map.entry("POST /api/v1/research/projects/{id}/restore", Map.of("502", UNREACHABLE, "503", DISABLED, "504", TIMEOUT)),
            Map.entry("POST /api/v1/research/projects/{id}/reinit", writeFailures("換世代（generation=next）的 reason 缺、全為空白或超過 500 字，或 generation 不是 next（reason invalid_request）；"
                    + "或 Bridge 拒絕此請求（reason 逐字取自 Bridge）")),
            Map.entry("POST /api/v1/research/allowlist", writeFailures("輸入閘未通過（reason invalid_request：listKind、host、layer、purpose、minIntervalSeconds）；"
                    + "Reddit 網域未確認條款（reason terms_ack_required；tosAcknowledged 須為 true）；或 Bridge 拒絕此請求（reason 逐字取自 Bridge）")),
            Map.entry("PATCH /api/v1/research/allowlist/{id}", writeFailures("本文含 enabled 以外的鍵（含 minIntervalSeconds；建立後不可改）或 enabled 不是布林（reason invalid_request；條目不變）")));

    private ResearchErrorDocs() {
    }
}
