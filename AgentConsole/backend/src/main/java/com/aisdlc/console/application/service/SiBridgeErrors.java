package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.DomainException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ForbiddenException;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.exception.UpstreamException;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * SelfImproving 專屬的 Bridge 拒絕 → Console 回應（唯讀鏡像：TCS-SelfImprovingMirror-P1b R8 的對映表；寫入：{@link #mapWrite}）。連線失敗與讀取逾時、其餘 5xx
 * 已由介面卡轉成 {@code UpstreamException}（502／504），這裡只處理「Bridge 明確回了 4xx 或 503 {@code si_unavailable}」。
 *
 * <p>原因<b>逐字</b>轉出：{@code detail}（rc 與 stderr 末 1,000 字元，可含全形字元與換行）與 {@code cause} 不經任何改寫，
 * 使用者在畫面上看到的就是根層 CLI 的說法；任何失敗都不帶資料（不回空表、不回部分資料、不回上一次的結果）。
 */
final class SiBridgeErrors {

    private SiBridgeErrors() {
    }

    static DomainException map(BridgeRejectedException e) {
        String reason = e.reason() == null ? "" : e.reason();
        if (e.status() == 503 && ErrorReasons.SI_UNAVAILABLE.equals(reason)) {
            Map<String, Object> details = new LinkedHashMap<>();
            copy(details, "cause", e.body().get("cause"));
            copy(details, "detail", e.detail());
            return new ServiceUnavailableException("SelfImproving 資料面不可用：Bridge 無法取得 export 輸出",
                    ErrorReasons.SI_UNAVAILABLE, details);
        }
        if (e.status() == 404 && ErrorReasons.SI_NOT_FOUND.equals(reason)) {
            Map<String, Object> details = new LinkedHashMap<>();
            copy(details, "id", e.body().get("id"));
            return new NotFoundException("查無此提案", ErrorReasons.SI_NOT_FOUND, details);
        }
        if (e.status() == 422 && "invalid_request".equals(reason)) {
            // 沿 BridgeErrors.rejected() 與 SddBridgeErrors 的既有同形處理：頂層 reason 為「引擎拒絕此請求」，
            // Bridge 層的 invalid_request 只經 details.bridgeReason 帶出（前端不為它建 reason 常數）
            return BridgeErrors.forRead(e);
        }
        // 其餘 4xx（例：舊版 Bridge 沒有 /si/* 的 404、403）一律當作上游故障，不偽裝成使用者錯誤
        Map<String, Object> details = new LinkedHashMap<>();
        details.put("bridgeStatus", e.status());
        if (!reason.isEmpty()) {
            details.put("bridgeReason", reason);
        }
        return new UpstreamException.Failure("Bridge 回了非預期的錯誤（HTTP " + e.status()
                + (reason.isEmpty() ? "" : "，" + reason) + "）", details);
    }

    /**
     * 寫入端點（稽核檔落地與預檢；TCS-SelfImprovingDecide-P2b W15）的 Bridge 拒絕 → Console 回應：503 {@code si_write_disabled}（Bridge 沒設權杖或
     * 稽核目錄；{@code details.detail} 逐字）、403 {@code si_write_forbidden}（Bridge 拒絕 backend 附的權杖＝兩端設定不一致）、409
     * {@code si_audit_exists}，其餘（503 {@code si_unavailable}、422、其他 4xx）與唯讀鏡像同一張表（{@link #map}）。連線與逾時、5xx 已由介面卡
     * 轉成 {@code UpstreamException}，不經這裡。
     */
    static DomainException mapWrite(BridgeRejectedException e) {
        String reason = e.reason() == null ? "" : e.reason();
        if (e.status() == 503 && ErrorReasons.SI_WRITE_DISABLED.equals(reason)) {
            Map<String, Object> details = new LinkedHashMap<>();
            copy(details, "detail", e.detail());
            return new ServiceUnavailableException("SelfImproving 寫入面停用：Bridge 沒有設定寫入權杖或稽核目錄",
                    ErrorReasons.SI_WRITE_DISABLED, details);
        }
        if (e.status() == 403 && ErrorReasons.SI_WRITE_FORBIDDEN.equals(reason)) {
            return new ForbiddenException("Bridge 拒絕了 backend 的寫入權杖（兩端的 BRIDGE_SI_WRITE_TOKEN 設定不一致）",
                    ErrorReasons.SI_WRITE_FORBIDDEN);
        }
        if (e.status() == 409 && ErrorReasons.SI_AUDIT_EXISTS.equals(reason)) {
            return new ConflictException("稽核檔已存在（Bridge 以獨佔建檔拒絕覆寫）", ErrorReasons.SI_AUDIT_EXISTS);
        }
        return map(e);
    }

    /** {@code details} 內不輸出 null 值（契約 §0.2；{@code Map.copyOf} 也不收 null）：沒有值的鍵省略。 */
    private static void copy(Map<String, Object> out, String key, Object value) {
        if (value != null) {
            out.put(key, value);
        }
    }
}
