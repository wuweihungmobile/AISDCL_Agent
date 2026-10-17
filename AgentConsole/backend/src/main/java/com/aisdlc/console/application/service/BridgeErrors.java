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
import java.util.Optional;
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
        return forStart(e, null);
    }

    /**
     * 同上；{@code sddProject} 是這次送出的有效 FSM 專案（帶 {@code sdd} 區塊的批次才有，放進 {@code sdd_fsm_not_found} 的 details）。
     * SDD 專屬的拒絕（預檢的 409／422、503 {@code sdd_write_disabled}、403 {@code sdd_write_forbidden}；契約 §3.2）優先轉譯。
     */
    static DomainException forStart(BridgeRejectedException e, String sddProject) {
        Optional<DomainException> sdd = SddBridgeErrors.map(e, sddProject);
        if (sdd.isPresent()) {
            return sdd.get();
        }
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
     * 核准凍結（SDD 寫入面）的 Bridge 4xx（契約 §1.10.2 的 Bridge 失敗對映）：SDD 專屬轉譯優先，其餘一律「引擎拒絕此請求」。
     *
     * @param sddProject 這次送出的有效 FSM 專案（放進 {@code sdd_fsm_not_found} 的 {@code details.sddProject}）
     */
    static DomainException forSddWrite(BridgeRejectedException e, String sddProject) {
        return SddBridgeErrors.map(e, sddProject).orElseGet(() -> rejected(e));
    }

    /** 唯讀 Bridge 查詢（RTM）被拒：404 由呼叫端依端點語意處理，其餘 4xx 一律「引擎拒絕此請求」（契約 §1.10.3 的 422 列）。 */
    static DomainException forRead(BridgeRejectedException e) {
        return rejected(e);
    }

    /**
     * pause／resume／stop／restore 被拒。
     *
     * @param action    {@code pause}／{@code resume}／{@code cancel}／{@code restore}／{@code review}
     * @param runStatus Console 認定的批次狀態（DB 欄位值）
     */
    static DomainException forControl(BridgeRejectedException e, String action, UUID runId, String runStatus) {
        // SDD run 的 resume／restore（權杖、預檢、FSM 重進）失敗的轉譯同 execute（契約 §1.2.4～§1.2.6、§1.2.10；DB 與 FSM 狀態都不變）
        Optional<DomainException> sdd = SddBridgeErrors.map(e, null);
        if (sdd.isPresent()) {
            return sdd.get();
        }
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
