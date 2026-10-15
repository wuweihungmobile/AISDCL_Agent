package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.DomainException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.UpstreamException;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Bridge 的 4xx → Console 回應的轉譯（契約 §3.2）。5xx、連線失敗與逾時已由介面卡轉成 {@link UpstreamException}（502／504），
 * 這裡只處理「Bridge 明確拒絕」的情形。
 */
final class BridgeErrors {

    private BridgeErrors() {
    }

    /** execute／審核開後續批次時 {@code startRun} 被拒：409 鎖被持有、422 消毒或格式、其餘 4xx 一律當成「引擎拒絕此請求」。 */
    static DomainException forStart(BridgeRejectedException e) {
        if (e.status() == 409 && "advisory_lock_held".equals(e.reason())) {
            return lockHeld(e);
        }
        if (e.status() == 409 && "run_exists".equals(e.reason())) {
            return new UpstreamException.Failure("Bridge 回報 run_id 重複（console 的 id 是新 UUID，不應發生）",
                    Map.of("bridgeStatus", e.status(), "bridgeReason", e.reason()));
        }
        return rejected(e);
    }

    /**
     * pause／resume／stop／restore 被拒。
     *
     * @param action    {@code pause}／{@code resume}／{@code cancel}／{@code restore}／{@code review}
     * @param runStatus Console 認定的批次狀態（DB 欄位值）
     */
    static DomainException forControl(BridgeRejectedException e, String action, UUID runId, String runStatus) {
        String reason = e.reason();
        if (e.status() == 409 && "invalid_state".equals(reason)) {
            Map<String, Object> details = new LinkedHashMap<>();
            details.put("action", action);
            details.put("runStatus", runStatus);
            Object bridgeStatus = e.body().get("status");
            if (bridgeStatus != null) {
                details.put("bridgeStatus", bridgeStatus.toString());
            }
            return new ConflictException("Bridge 不允許在目前狀態執行 " + action, ErrorReasons.RUN_STATE_NOT_ALLOWED,
                    details);
        }
        if (e.status() == 409 && "no_checkpoint".equals(reason)) {
            return new ConflictException("找不到可續跑的 checkpoint", ErrorReasons.NO_CHECKPOINT);
        }
        if (e.status() == 409 && "advisory_lock_held".equals(reason)) {
            return lockHeld(e);
        }
        if (e.status() == 404 && "run_not_found".equals(reason)) {
            return new ConflictException("引擎端已無此執行（工作區可能已清除）", ErrorReasons.RUN_UNKNOWN_AT_BRIDGE,
                    Map.of("runId", runId.toString()));
        }
        if (e.status() == 404 && "checkpoint_not_found".equals(reason)) {
            Object id = e.body().get("checkpoint_id");
            return new NotFoundException("checkpoint 不存在或不屬於此執行：" + (id == null ? "" : id));
        }
        return rejected(e);
    }

    private static DomainException lockHeld(BridgeRejectedException e) {
        Map<String, Object> details = new LinkedHashMap<>();
        Object holder = e.body().get("holder_run_id");
        if (holder != null) {
            details.put("holderRunId", holder.toString());
        }
        return new ConflictException("同專案同路徑已有執行中的批次", ErrorReasons.LOCK_HELD, details);
    }

    /** 422（消毒／格式）與其餘 4xx：{@code 引擎拒絕此請求}，{@code bridgeReason}、{@code violations} 逐項原樣帶出。 */
    private static DomainException rejected(BridgeRejectedException e) {
        Map<String, Object> details = new LinkedHashMap<>();
        details.put("bridgeReason", e.reason());
        details.put("violations", e.violations());
        return new UnprocessableException("Engine Bridge 拒絕此請求（HTTP " + e.status() + "，" + e.reason() + "）",
                ErrorReasons.BRIDGE_REJECTED, details);
    }
}
