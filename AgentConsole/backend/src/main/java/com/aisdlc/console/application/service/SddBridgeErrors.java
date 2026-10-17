package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.DomainException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.UpstreamException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * SDD 迴圈專屬的 Bridge 拒絕 → Console 回應（契約 §3.2 的 v1.5 各列；適用核准凍結、帶 {@code sdd} 的 execute、SDD run 的 resume／restore）。
 * 不是 SDD 專屬的拒絕回 empty，由呼叫端走原本的轉譯（{@link BridgeErrors}）。
 *
 * <p>Bridge 的 {@code fsm_state_conflict}、{@code spec_digest_changed} 把結構化資訊放在 {@code detail} <b>物件</b>裡
 * （契約 §6.8.6 靜默處 #8）；本類別一律只讀 {@code detail}，不依賴封包頂層的同名過渡欄位。權杖值不經手：這裡看得到的只有狀態碼與 reason。
 */
final class SddBridgeErrors {

    private static final Logger LOG = LoggerFactory.getLogger(SddBridgeErrors.class);

    /** 規格存在但被拒（422）：與路徑 A 同一個轉譯（{@code SDD 規格檢查未通過}）。 */
    private static final Set<String> SPEC_REJECTED = Set.of("spec_not_frozen", "spec_tainted",
            "spec_format_version_unsupported", "spec_not_found", "spec_ambiguous");
    /** 請求或狀態檔本身不合（422）：{@code 引擎拒絕此請求}。 */
    private static final Set<String> ENGINE_REJECTED = Set.of("fsm_state_unreadable", "sanitization_failed",
            "sdd_invalid_argument", "sdd_block_invalid");

    private SddBridgeErrors() {
    }

    /**
     * @param sddProject 這次送出的有效 FSM 專案（放進 {@code sdd_fsm_not_found} 的 {@code details.sddProject}）；呼叫端不知道時為 null，
     *                   改取 Bridge 回的 {@code project}
     */
    static Optional<DomainException> map(BridgeRejectedException e, String sddProject) {
        String reason = e.reason() == null ? "" : e.reason();
        return switch (e.status()) {
            case 409 -> switch (reason) {
                case "fsm_state_conflict" -> Optional.of(new ConflictException(
                        "FSM 目前狀態不允許這個操作（" + String.valueOf(e.detailObject().get("current_state")) + "）",
                        ErrorReasons.SDD_FSM_STATE_CONFLICT, stateConflictDetails(e.detailObject())));
                case "spec_digest_changed" -> Optional.of(new ConflictException(
                        "規格內容與凍結時（或核准人看到的、匯入時的）不同，拒絕繼續", ErrorReasons.SDD_SPEC_DIGEST_CHANGED,
                        digestDetails(e.detailObject())));
                default -> Optional.empty();
            };
            case 404 -> "fsm_not_found".equals(reason) ? Optional.of(fsmNotFound(e, sddProject)) : Optional.empty();
            case 422 -> unprocessable(e, reason);
            case 503 -> "sdd_write_disabled".equals(reason)
                    ? Optional.of(new ServiceUnavailableException("SDD 寫入面停用：Bridge 沒有設定寫入權杖（BRIDGE_SDD_WRITE_TOKEN）",
                            ErrorReasons.SDD_WRITE_DISABLED))
                    : Optional.empty();
            case 403 -> "sdd_write_forbidden".equals(reason) ? Optional.of(writeForbidden()) : Optional.empty();
            default -> Optional.empty();
        };
    }

    private static DomainException fsmNotFound(BridgeRejectedException e, String sddProject) {
        Map<String, Object> details = new LinkedHashMap<>();
        Object project = sddProject != null ? sddProject : e.body().get("project");
        if (project != null) {
            details.put("sddProject", project.toString());
        }
        return new ConflictException("找不到 FSM 專案的狀態檔：要先在專案根的 SDD session 建立", ErrorReasons.SDD_FSM_NOT_FOUND,
                details);
    }

    private static Optional<DomainException> unprocessable(BridgeRejectedException e, String reason) {
        if (SPEC_REJECTED.contains(reason)) {
            String detail = e.detail() == null ? "" : e.detail();
            return Optional.of(new UnprocessableException("SDD 規格檢查未通過（" + reason + "）：" + detail,
                    ErrorReasons.SDD_SPEC_REJECTED, Map.of("bridgeReason", reason, "detail", detail)));
        }
        // 契約 §3.2：fsm_state_unreadable／sanitization_failed／sdd_invalid_argument／sdd_block_invalid ⇒ 引擎拒絕此請求（不帶 detail 的才補 detail）
        if (ENGINE_REJECTED.contains(reason)) {
            Map<String, Object> details = new LinkedHashMap<>();
            details.put("bridgeReason", reason);
            details.put("violations", e.violations());
            if (e.violations().isEmpty() && e.detail() != null && !e.detail().isBlank()) {
                details.put("detail", e.detail());
            }
            return Optional.of(new UnprocessableException("Engine Bridge 拒絕此請求（HTTP 422，" + reason + "）",
                    ErrorReasons.BRIDGE_REJECTED, details));
        }
        return Optional.empty();
    }

    /** 403：兩端的權杖設定不一致＝設定缺陷，不是使用者錯誤——記 ERROR，回 502（details 只帶狀態與 reason，不含任何權杖資訊）。 */
    private static DomainException writeForbidden() {
        LOG.error("Bridge 以 403 sdd_write_forbidden 拒絕寫入：backend 與 Bridge 的 BRIDGE_SDD_WRITE_TOKEN 設定不一致（設定缺陷）");
        return new UpstreamException.Failure("Bridge 拒絕 SDD 寫入（權杖不符；兩端的 BRIDGE_SDD_WRITE_TOKEN 設定不一致）",
                Map.of("bridgeStatus", 403, "bridgeReason", "sdd_write_forbidden"));
    }

    private static Map<String, Object> stateConflictDetails(Map<String, Object> detail) {
        Map<String, Object> out = new LinkedHashMap<>();
        copy(out, "currentState", detail.get("current_state"));
        copy(out, "expectedState", detail.get("expected_state"));       // 字串或陣列，原樣帶出
        copy(out, "runId", detail.get("run_id"));
        copy(out, "runStatus", detail.get("run_status"));
        copy(out, "cause", detail.get("reason"));                       // foreign_delegation
        return out;
    }

    private static Map<String, Object> digestDetails(Map<String, Object> detail) {
        Map<String, Object> out = new LinkedHashMap<>();
        copy(out, "pair", detail.get("pair"));
        copy(out, "doc", detail.get("doc"));
        copy(out, "expectedDigest", detail.get("expected_digest"));
        copy(out, "frozenDigest", detail.get("frozen_digest"));
        copy(out, "importDigest", detail.get("import_digest"));
        copy(out, "currentDigest", detail.get("current_digest"));
        return out;
    }

    /** {@code details} 內不輸出 null 值（契約 §0.2）：沒有值的鍵省略。 */
    private static void copy(Map<String, Object> out, String key, Object value) {
        if (value != null) {
            out.put(key, value);
        }
    }
}
