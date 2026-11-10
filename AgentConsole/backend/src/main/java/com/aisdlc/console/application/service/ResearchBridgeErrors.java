package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.DomainException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ForbiddenException;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.exception.Violation;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 研究呼叫的 Bridge 拒絕 → Console 回應（API 契約 §0.2 的共通失敗表）。連線失敗、讀取逾時與 Bridge 回報的上游失敗（501 {@code not_implemented}、502 {@code init_failed}）
 * 已由 {@code BridgeHttpAdapter} 轉成 {@code ResearchBridgeException}，這裡只處理「Bridge 明確回了 4xx 或明確拒絕的 503」。
 *
 * <p><b>reason 與 details 逐字轉出</b>（AT-960-4-4：console-api 轉出的 reason 逐字取自 Bridge）：Bridge 的 {@code details} 物件（{@code unmet}、
 * {@code activeStageRunId}、{@code headVersion}、{@code current_state}、{@code recovery}…）與頂層的補充欄位（{@code research_id}、{@code entry_id}…）原樣放進
 * {@code details}；{@code details} 內不輸出 null 值（契約 §0.2，{@code Map.copyOf} 也不收 null）。
 */
final class ResearchBridgeErrors {

    /** Bridge 錯誤本文中不當作「補充欄位」原樣搬進 details 的頂層鍵（已另行處理）。 */
    private static final Set<String> ENVELOPE_KEYS = Set.of("code", "reason", "details", "detail", "violations");
    /** Bridge 明確拒絕（而非故障）的 503 reason。 */
    private static final Set<String> EXPLICIT_503 = Set.of(ErrorReasons.RESEARCH_WRITE_DISABLED, ErrorReasons.RESEARCH_REQUIRES_DB,
            ErrorReasons.RESEARCH_DB_BLOCKED);

    private ResearchBridgeErrors() {
    }

    static DomainException map(BridgeRejectedException e) {
        String reason = e.reason() == null ? "" : e.reason();
        int status = e.status();
        Map<String, Object> details = details(e);
        if (status == 503 && EXPLICIT_503.contains(reason)) {
            return new ServiceUnavailableException(message503(reason), reason, details);
        }
        if (status == 403 && ErrorReasons.RESEARCH_WRITE_FORBIDDEN.equals(reason)) {
            return new ForbiddenException("Bridge 拒絕了 backend 的研究寫入權杖（兩端的 BRIDGE_RESEARCH_WRITE_TOKEN 設定不一致）", reason);
        }
        if (status == 404) {
            // D-123（P0 未結 R-1）：reason 仍是 research_not_found，文案依 details 區分——allowlist 條目的 404 帶 entry_id，其餘是研究專案
            String subject = details.containsKey("entry_id") ? "允許清單條目不存在" : details.containsKey("slug") ? "追蹤來源不存在" : "研究專案不存在或已刪除";
            return new NotFoundException(subject, reason.isEmpty() ? ErrorReasons.RESEARCH_NOT_FOUND : reason, details);
        }
        if (status == 409) {
            if (ErrorReasons.REGISTRY_WATCH_SOURCE_EXISTS.equals(reason)) {
                return new ConflictException("追蹤來源 slug 已存在（slug 永不重用，含已停用者）", reason, details);
            }
            return new ConflictException("與研究專案目前狀態衝突（" + reason + "）", reason, details);
        }
        if (status == 400 || status == 422) {
            return new UnprocessableException("研究引擎拒絕此請求（" + (reason.isEmpty() ? ResearchInputGates.INVALID_REQUEST : reason) + "）",
                    reason.isEmpty() ? ResearchInputGates.INVALID_REQUEST : reason, List.of(), violationsOf(e), details);
        }
        // 其餘 4xx（例：舊版 Bridge 沒有 /research/* 的 404、405）與未知的 503 一律當作上游故障，不偽裝成使用者錯誤
        Map<String, Object> failure = new LinkedHashMap<>();
        failure.put("bridgeStatus", status);
        if (!reason.isEmpty()) {
            failure.put("bridgeReason", reason);
        }
        return new UpstreamException.Failure("Bridge 回了非預期的錯誤（HTTP " + status + (reason.isEmpty() ? "" : "，" + reason) + "）", failure);
    }

    private static String message503(String reason) {
        return switch (reason) {
            case ErrorReasons.RESEARCH_WRITE_DISABLED -> "研究寫入面停用：Bridge 沒有設定研究寫入權杖（BRIDGE_RESEARCH_WRITE_TOKEN）";
            case ErrorReasons.RESEARCH_REQUIRES_DB -> "研究端點需要資料庫：Bridge 沒有設定 BRIDGE_DB_DSN";
            default -> "研究資料庫暫時不可用（db_blocked）";
        };
    }

    /** Bridge 本文 → details：{@code details} 物件、頂層補充欄位、{@code violations}、{@code detail} 文字；全部剝掉 null 值。 */
    private static Map<String, Object> details(BridgeRejectedException e) {
        Map<String, Object> out = new LinkedHashMap<>();
        e.body().forEach((key, value) -> {
            if (value != null && !ENVELOPE_KEYS.contains(key)) {
                out.put(key, value);
            }
        });
        if (e.body().get("details") instanceof Map<?, ?> nested) {
            nested.forEach((key, value) -> {
                if (key != null && value != null) {
                    out.put(String.valueOf(key), value);
                }
            });
        }
        if (!e.violations().isEmpty()) {
            out.put("violations", e.violations());
        }
        if (e.detail() != null && !e.detail().isBlank()) {
            out.put("detail", e.detail());
        }
        return out;
    }

    private static List<Violation> violationsOf(BridgeRejectedException e) {
        List<Violation> out = new ArrayList<>();
        for (Map<String, Object> violation : e.violations()) {
            Object field = violation.get("field");
            Object message = violation.get("message");
            out.add(new Violation(field == null ? "" : field.toString(), message == null ? "" : message.toString()));
        }
        return out;
    }
}
