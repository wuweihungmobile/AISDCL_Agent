package com.aisdlc.console.application.port.in;

import com.aisdlc.console.domain.model.si.SiValidation;

/**
 * SelfImproving 的寫入載體（TCS-SelfImprovingDecide-P2b W10、W11；PRD AC-SI-33-1、AC-SI-35-1、35-2）：Console <b>不寫帳本</b>——每個請求
 * 簽一份稽核 JSON（HMAC）、先寫自己的稽核列、再經 Bridge 把那份位元組落成稽核檔，由主機端根層 CLI（{@code --carrier console}）驗簽入帳。
 *
 * <p><b>閘門序</b>（四個方法同一關，含預檢；先中者定案）：授權（帳號須在 {@code console.si.deciders}，否則 403 {@code si_write_forbidden}）
 * → 寫入面停用（503 {@code si_write_disabled}，{@code details.cause}＝{@code audit_key_unset}｜{@code bridge_token_unset}）→ 輸入閘
 * （422 {@code invalid_request}，{@code details.violations} 一次全列；含帳號名值域）→ 執行。角色（須為 ADMIN）由安全層先擋（403
 * {@code ACCESS_DENIED}）。輸入閘先於<b>一切</b>副作用（取 ref、簽章、資料庫、Bridge）。
 *
 * <p>每個請求至多一次 Bridge 呼叫、不重試；重送一律新 {@code auditRef}。Bridge 明確拒絕或確定未落檔時補償刪除稽核列；結果不明（讀取逾時、
 * 送出後連線重設、2xx 本文無法解析）時<b>保留</b>該列並在錯誤的 {@code details.outcomeUnknown} 標明。
 */
public interface SiWriteUseCase {

    /**
     * 決定的請求欄位（路徑 {@code id} 另給）：全部<b>未驗證</b>，由輸入閘判。
     *
     * @param unverifiedAck 晉升後式（verdict 為 NE 的晉升）的勾選；只有 promote 可為 {@code true}
     */
    record DecideInput(String dkind, String digest, String reason, String reasonClass, Boolean unverifiedAck) {
    }

    /** 新增觀察的請求欄位（obs-add 與預檢共用；未驗證）。刻意沒有 {@code marks_extra}。 */
    record ObservationInput(String context, String symptom, String evidence, String category, String severity, String face,
                            String exposure, Boolean externalDerived, String corrects) {
    }

    /** 關閉觀察的請求欄位（路徑 {@code id} 另給；未驗證）：{@code ref} 與 {@code text} 恰擇一（依終值）。 */
    record CloseInput(String terminal, String ref, String text) {
    }

    /**
     * 成功收據（不含 body 與 mac）。
     *
     * @param kind    {@code decide}｜{@code obs-add}｜{@code obs-close}
     * @param subject decide＝PROP 號（resume 為 RUN 號）、obs-close＝OBS 號、obs-add＝{@code null}
     * @param time    稽核 body 的 {@code time}（秒精度、{@code ±HH:MM}）
     * @param keyId   簽章金鑰的 sha256 前 8 碼
     */
    record Receipt(String auditRef, String kind, String subject, String time, String keyId) {
    }

    /** 對 PROP 號（resume 為 RUN 號）下決定。 */
    Receipt decide(String user, String id, DecideInput input);

    /** 新增觀察列。 */
    Receipt addObservation(String user, ObservationInput input);

    /** 把處置為 open 的觀察列一次關成終值。 */
    Receipt closeObservation(String user, String id, CloseInput input);

    /** 唯讀預檢（根層 {@code obs-add --dry-run}）：不取 ref、不簽章、不寫資料庫、不落檔。 */
    SiValidation validateObservation(String user, ObservationInput input);
}
