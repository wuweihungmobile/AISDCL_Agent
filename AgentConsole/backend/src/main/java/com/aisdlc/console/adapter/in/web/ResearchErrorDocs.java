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
            + "research_requires_db：Bridge 沒有 BRIDGE_DB_DSN（研究端點不降級成純檔案模式）；db_blocked：研究資料庫暫時不可用；"
            + "compile_failed：研究 stage 的 persona／playbook 編譯失敗（Bridge 逐字轉出）";
    private static final String UNREACHABLE = "bridge_unreachable：連不上 Engine Bridge（連線階段失敗，請求確定沒有送達；連線 2 秒）；或 Bridge 回報上游失敗——"
            + "not_implemented（Bridge 端點本體尚未實作，details.endpoint，console-api 不假裝成功）、init_failed（專案初始化的某一步失敗，details.step；游標已標 FAILED，以 reinit 補建）；"
            + "sdd_cli_failed（Bridge 的 SDD CLI 子行程失敗，逐字轉出）；其餘 5xx＝引擎橋接服務錯誤。寫入不重試";
    private static final String TIMEOUT = "bridge_timeout：讀取逾時（請求已送出、結果不明；寫入讀取 30 秒、不重試）";
    private static final String UNPROCESSABLE = "輸入閘未通過（reason invalid_request；details.violations[{field,rule,message}] 一次全列，errors[] 同內容），或 Bridge 拒絕此請求"
            + "（reason 逐字取自 Bridge：invalid_request｜terms_ack_required｜sanitization_failed｜layer_unavailable；details.violations）";

    /**
     * Gate 0 核准的 422（D-72：只比對前端送來的鍵）：輸入閘、一個鍵都沒送（missing_digests：盲核，單獨出現時由輸入閘回、零 Bridge 請求）、摘要不符（digest_mismatch；
     * details.files[{key,expected,current}]，current 為 null＝該檔不存在或不在凍結的四檔內；Bridge 逐字轉出）。取代原契約的 409 spec_digest_changed。
     */
    private static final String APPROVE_UNPROCESSABLE = "輸入閘未通過（reason invalid_request；details.violations[{field,rule,message}] 一次全列，errors[] 同內容）；"
            + "一個摘要鍵都沒送（reason missing_digests：盲核；expectedDigests 至少要送一鍵，單獨出現時由輸入閘回、details.violations、零 Bridge 請求）；"
            + "摘要不符（reason digest_mismatch，D-72：只比對 expectedDigests 送來的鍵；details.files[{key,expected,current}]，current 為 null＝該檔不存在或不在凍結的四檔內）；"
            + "或 Bridge 拒絕此請求（reason 逐字取自 Bridge：invalid_request｜sanitization_failed；details.violations）";

    /** 寫入端點共用的上游失敗與輸入閘。 */
    private static Map<String, String> writeFailures(String unprocessable) {
        return Map.of("422", unprocessable, "502", UNREACHABLE, "503", DISABLED, "504", TIMEOUT);
    }

    /** P1 分流、SCR、拆解的 422 說明（reason 逐字；Bridge 的 reason 與 details 原樣轉出）。 */
    private static final String ROUTE_UNPROCESSABLE = "輸入閘未通過（reason invalid_request；details.violations[{field,rule,message}]；分流軌道與 PRD target_scope 不同而缺 scopeDiffersReason＝"
            + "規則 scope_differs_reason_required），或 Bridge 拒絕（reason 逐字取自 Bridge）：route_unsupported_in_deployment（此部署不支援分流；details.missing[{item,reason}]）"
            + "｜sanitization_failed（路徑或名稱未通過安全檢查）｜target_not_empty（軌道 B 目標目錄非空；details.path 只回相對於 BRIDGE_SCAFFOLD_ROOT 的路徑）"
            + "｜public_confirmation_required（PUBLIC 遠端須重述庫名確認）";
    private static final String ROUTE_CONFLICTS = "route_conflict（已有 PENDING、RUNNING 或 SUCCEEDED 的分流，或重試前置不成立；details.route_id、status）"
            + "｜branch_exists（軌道 A 分支已存在；details.branch）｜fsm_state_conflict（外環鍵不在 SPEC_FROZEN＝Gate 0 未過；details.current_state）"
            + "｜sdd_binding_conflict（同一個執行路徑與內環鍵已綁定另一個 Console 專案）";
    private static final String SCR_UNPROCESSABLE = "輸入閘未通過（reason invalid_request；kind、sourceKind、reason〔1～500 字〕、reasonClass、affectedSections 的欄位級違規），"
            + "或 Bridge 拒絕此請求（reason 逐字取自 Bridge；details.violations）";
    private static final String DECOMPOSITION_UNPROCESSABLE = "invalid_request：觸發時 Bridge 的有界閘（details.violations[].rule＝max_steps｜cycle｜empty_prompt｜brain_failed｜brain_unsupported）；"
            + "簽核時覆蓋未清零（violations[{field:coverage,rule:uncovered_ac}]；每個未覆蓋 AC 須被 task 的 covers_ac 涵蓋或附人工豁免理由）";

    /** P1 新增操作的 409 說明。 */
    private static final Map<String, String> P1_CONFLICT = Map.of(
            "POST /api/v1/research/projects/{id}/route/preview", ROUTE_CONFLICTS,
            "POST /api/v1/research/projects/{id}/route", ROUTE_CONFLICTS,
            "POST /api/v1/research/projects/{id}/scr", "scr_open（已有開啟中的 SCR）｜scr_limit（同一研究專案的 MINOR SCR 已達上限）｜fsm_state_conflict（內環現態不在矩陣內；details.current_state）",
            "POST /api/v1/research/projects/{id}/scr/{scrNo}/apply", "fsm_state_conflict（SCR 不是 APPROVED，或內環現態不在矩陣內；details.current_state）",
            "POST /api/v1/research/projects/{id}/decomposition", "scr_open（SCR 開啟期間內環唯讀）｜stage_conflict｜fsm_state_conflict（外環鍵不在 SPEC_FROZEN 或尚未分流）",
            "POST /api/v1/research/projects/{id}/decomposition/signoff", "decomposition_stale（拆解綁定的 PRD 摘要與現行凍結摘要不符；details.expected_sha256、actual_sha256）"
                    + "｜fsm_state_conflict（尚未分流、尚無拆解，或拆解狀態不允許簽核；details.cause、status）");

    /** P2 新增操作的 409 說明（內環閘登錄、交付）。 */
    private static final String GATE_CONFLICTS = "fsm_state_conflict（details.unmet：no_console_project｜tasks_incomplete｜rtm_below_100｜rtm_unavailable；零 Bridge 請求）"
            + "｜scr_open（SCR 開啟期間內環唯讀）";
    private static final String TAG_CONFLICTS = "fsm_state_conflict（details.unmet：not_release_ready｜rtm_below_100｜scr_open｜no_console_project；零 Bridge 請求；"
            + "或凍結 PRD 讀不到 prd_not_frozen）｜tag_exists（Release Tag 名稱已存在；Bridge 回、原樣透傳）｜scr_open";
    private static final Map<String, String> P2_CONFLICT = Map.ofEntries(
            Map.entry("POST /api/v1/research/projects/{id}/gates", GATE_CONFLICTS),
            Map.entry("POST /api/v1/research/projects/{id}/delivery/tag", TAG_CONFLICTS),
            Map.entry("POST /api/v1/research/projects/{id}/delivery/pr", "fsm_state_conflict（分流尚未成功 details.cause＝route_not_succeeded；或凍結 PRD 讀不到）"
                    + "｜scr_open（SCR 開啟期間內環唯讀）"),
            Map.entry("GET /api/v1/research/projects/{id}/delivery/traceability", "fsm_state_conflict（凍結 PRD 讀不到；details.unmet：prd_not_frozen）"));

    /** P2 交付與內環閘寫入的 422／502／504 說明（Bridge 的 reason 與 details 原樣透傳）。 */
    private static final String DELIVERY_UNPROCESSABLE = "輸入閘未通過（reason invalid_request；details.violations[{field,rule,message}]：tagName not_semver、message message_too_long、"
            + "createGithubRelease release_not_supported、bodyPreviewAck preview_ack_required）；或 Bridge 拒絕（reason 逐字取自 Bridge）：digest_mismatch（凍結 digest 漂移；details.drift"
            + "[{path, expected_sha256, actual_sha256}]）｜route_unsupported_in_deployment（容器模式；details.missing[{item,reason}]）";
    private static final String DELIVERY_UPSTREAM = UNREACHABLE + "；delivery_step_failed：交付的某一步失敗（details.failure_step；Bridge 回、原樣透傳；失敗的 tag 不產生交付列）";
    private static final String LONG_TIMEOUT = "bridge_timeout：讀取逾時（內環閘登錄、Release Tag 與 Pull Request 的讀取逾時 330 秒、不重試；結果不明時請重新整理交付概覽再判斷）";
    private static final String GATE_UNPROCESSABLE = "輸入閘未通過（reason invalid_request；details.violations[{field,rule,message}]：gate invalid_gate、result invalid_result、reason reason_required｜"
            + "reason_too_long、reviewReportRef report_ref_too_long、result release_pass_via_tag、reviewerIndependent reviewer_independence_required）；或 Bridge 拒絕（reason 逐字取自 Bridge）："
            + "digest_mismatch（凍結 digest 漂移；details.drift[{path, expected_sha256, actual_sha256}]）";

    /** P0 會回 409 的研究操作及其說明（reason 逐字）。 */
    private static final Map<String, String> P0_CONFLICT = Map.of(
            "POST /api/v1/research/projects", "slug_in_use：slug 已被未封存的研究專案使用",
            "PUT /api/v1/research/projects/{id}/prd", "prd_version_conflict（baseVersion 不是目前 head 版號；details.headVersion）｜spec_frozen（Gate 0 之後不可再存新版）",
            "POST /api/v1/research/projects/{id}/stages/{stage}", "stage_conflict（同專案已有進行中的 stage〔details.activeStageRunId、activeStage〕、"
                    + "前置條件未滿足〔details.unmet 逐條列出 rule 與說明〕、或全站並行上限〔details.cause=max_concurrent_runs、limit、active〕；不排隊、不重試）"
                    + "｜fsm_state_conflict（details.current_state；afterEscalation 但 FSM 仍在 ESCALATION*）｜escalated（外環 FSM 在 ESCALATION*，details.recovery 帶恢復指令）"
                    + "｜spec_frozen（Gate 0 之後）",
            "POST /api/v1/research/projects/{id}/approve", "review_not_passed（head 版本沒有通過的審查輪）"
                    + "｜fsm_state_conflict（FSM 現態不是 HUMAN_PENDING，或已核准過——非冪等；details.expected_state、current_state）｜escalated（FSM 在 ESCALATION*）",
            "POST /api/v1/research/projects/{id}/return", "fsm_state_conflict（FSM 現態不是 HUMAN_PENDING；details.current_state）｜escalated（FSM 在 ESCALATION*）",
            "POST /api/v1/research/projects/{id}/archive", "stage_conflict（有進行中的 stage；details.reason=stage_running）",
            "POST /api/v1/research/projects/{id}/reinit", "stage_conflict（重試：flowStatus 不是 FAILED——初始化失敗與 stage 失敗、取消的專案都可重試，D-81；"
                    + "details.flowStatus、flowDetail；零寫入）｜fsm_state_conflict（換世代：FSM 現態不在 ESCALATION*；details.current_state）",
            "POST /api/v1/research/allowlist", "allowlist_exists：同 listKind 與 host 已有條目");

    /** 會回 409 的研究操作及其說明（reason 逐字）：P0 加 P1。 */
    static final Map<String, String> CONFLICT;

    static {
        Map<String, String> merged = new java.util.LinkedHashMap<>(P0_CONFLICT);
        merged.putAll(P1_CONFLICT);
        merged.putAll(P2_CONFLICT);
        CONFLICT = Map.copyOf(merged);
    }

    /** 研究操作的其餘狀態碼（422／502／503／504）：方法＋路徑 → 狀態碼與說明。 */
    static final Map<String, Map<String, String>> EXTRA = Map.ofEntries(
            Map.entry("GET /api/v1/research/capabilities", Map.of("502", UNREACHABLE, "504", TIMEOUT)),
            Map.entry("POST /api/v1/research/projects/{id}/route/preview", writeFailures(ROUTE_UNPROCESSABLE)),
            Map.entry("POST /api/v1/research/projects/{id}/route", Map.of("422", ROUTE_UNPROCESSABLE, "502", "route_step_failed：分流的某一步失敗（details.route_id、failure_step；"
                    + "該分流列已是 FAILED、游標 route／ROUTING／FAILED，Console 專案列已補償為 ARCHIVED，不自動清理）；" + UNREACHABLE, "503", DISABLED,
                    "504", "bridge_timeout：讀取逾時（分流與拆解的讀取逾時 330 秒、不重試；Console 專案列已補償為 ARCHIVED）")),
            Map.entry("GET /api/v1/research/projects/{id}/route", Map.of()),
            Map.entry("POST /api/v1/research/projects/{id}/scr", writeFailures(SCR_UNPROCESSABLE)),
            Map.entry("GET /api/v1/research/projects/{id}/scr", Map.of()),
            Map.entry("POST /api/v1/research/projects/{id}/scr/{scrNo}/apply", writeFailures("scrNo 不是 1 以上的整數（reason invalid_request），或 Bridge 拒絕此請求（reason 逐字取自 Bridge）")),
            Map.entry("GET /api/v1/research/projects/{id}/decomposition", Map.of()),
            Map.entry("POST /api/v1/research/projects/{id}/decomposition", Map.of("422", DECOMPOSITION_UNPROCESSABLE, "502", UNREACHABLE, "503", DISABLED,
                    "504", "bridge_timeout：讀取逾時（拆解的讀取逾時 330 秒、不重試）")),
            Map.entry("POST /api/v1/research/projects/{id}/decomposition/signoff", writeFailures(DECOMPOSITION_UNPROCESSABLE)),
            Map.entry("GET /api/v1/research/projects/{id}/kanban", Map.of()),
            Map.entry("GET /api/v1/research/projects/{id}/healing", Map.of()),
            Map.entry("GET /api/v1/research/projects/{id}/delivery", Map.of()),
            Map.entry("GET /api/v1/research/projects/{id}/delivery/traceability", Map.of("502", UNREACHABLE, "503", DISABLED, "504", TIMEOUT)),
            Map.entry("POST /api/v1/research/projects/{id}/gates", Map.of("422", GATE_UNPROCESSABLE, "502", UNREACHABLE, "503", DISABLED, "504", LONG_TIMEOUT)),
            Map.entry("POST /api/v1/research/projects/{id}/delivery/tag", Map.of("422", DELIVERY_UNPROCESSABLE, "502", DELIVERY_UPSTREAM, "503", DISABLED,
                    "504", LONG_TIMEOUT)),
            Map.entry("POST /api/v1/research/projects/{id}/delivery/pr", Map.of("422", DELIVERY_UNPROCESSABLE, "502", DELIVERY_UPSTREAM, "503", DISABLED,
                    "504", LONG_TIMEOUT)),
            Map.entry("GET /api/v1/research/allowlist", Map.of("502", UNREACHABLE, "503", "db_blocked：研究資料庫暫時不可用；research_requires_db：Bridge 沒有 BRIDGE_DB_DSN",
                    "504", TIMEOUT)),
            Map.entry("GET /api/v1/research/projects/{id}/fsm", Map.of(
                    "422", "FSM 狀態檔壞掉（Bridge 的 fsm_state_unreadable）或 root 不合（sanitization_failed）；reason 逐字取自 Bridge",
                    "502", UNREACHABLE, "504", "bridge_timeout：讀取逾時（讀取 3 秒、不重試）")),
            Map.entry("POST /api/v1/research/projects", writeFailures(UNPROCESSABLE)),
            Map.entry("PUT /api/v1/research/projects/{id}/prd", writeFailures(UNPROCESSABLE)),
            Map.entry("POST /api/v1/research/projects/{id}/stages/{stage}", writeFailures("stage 不在 research｜draft｜review｜revise｜iterate｜tcs-draft（reason invalid_request），"
                    + "或 Bridge 拒絕此請求（reason 逐字取自 Bridge；details.violations）")),
            Map.entry("POST /api/v1/research/projects/{id}/approve", writeFailures(APPROVE_UNPROCESSABLE)),
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
