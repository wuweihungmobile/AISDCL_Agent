package com.aisdlc.console.application.port.in;

import com.aisdlc.console.domain.model.si.SiValidation;

/**
 * SelfImproving 的寫入載體（TCS-SelfImprovingDecide-P2b W10、W11；PRD AC-SI-33-1、AC-SI-35-1、35-2）：Console <b>不寫帳本</b>——每個請求
 * 簽一份稽核 JSON（HMAC）、先寫自己的稽核列、再經 Bridge 把那份位元組落成稽核檔，由主機端根層 CLI（{@code --carrier console}）驗簽入帳。
 *
 * <p><b>閘門序</b>（四個方法同一關，含預檢；先中者定案）：授權（帳號須在 {@code console.si.deciders}，否則 403 {@code si_write_forbidden}）
 * → 寫入面停用（503 {@code si_write_disabled}，{@code details.cause}＝{@code audit_key_unset}｜{@code bridge_token_unset}）→ 輸入閘
 * （422 {@code invalid_request}，{@code details.violations} 一次全列；含帳號名值域）→（<b>只有 {@link #decide} 的六個帶卡面 digest 的動詞</b>：重送閘，
 * 同 subject＋digest＋dkind 已有 decide 列＝409 {@code si_decision_duplicate}，TCS-SelfImprovingDecideDedupe W-D1）→ 執行。角色（須為 ADMIN）由安全層先擋
 * （403 {@code ACCESS_DENIED}）。輸入閘與重送閘先於<b>一切</b>副作用（取 ref、簽章、資料庫、Bridge）。
 *
 * <p>每個請求至多一次 Bridge 呼叫、不重試；重送一律新 {@code auditRef}（帶 digest 的決定動詞除外：同一決定已被重送閘擋下，不會取新 ref）。Bridge 明確拒絕或
 * 確定未落檔時補償刪除稽核列；結果不明（讀取逾時、送出後連線重設、2xx 本文無法解析）時<b>保留</b>該列並在錯誤的 {@code details.outcomeUnknown} 標明
 * （帶 digest 的決定，保留的列也會擋住同一決定的重送）。
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
     * 排程設定的請求欄位（P4；未驗證）。欄位刻意保留 JSON 解出的原始型別（{@code Object}），使「字串 {@code "true"}」「小數」「布林充當整數」
     * 都能被輸入閘當成違規回報（422），而不是被序列化器悄悄轉型。
     */
    record ScheduleSetInput(Object enabled, Object periodMinutes, Object reason) {
    }

    /** 立即啟動請求的欄位（P4；未驗證；同 {@link ScheduleSetInput} 保留原始型別）。 */
    record RunRequestInput(Object note) {
    }

    /**
     * 成功收據（不含 body 與 mac）。
     *
     * @param kind    {@code decide}｜{@code obs-add}｜{@code obs-close}｜{@code sched-set}｜{@code run-request}
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

    /**
     * 排程設定（P4；{@code sched-set}）：閘門序同上，輸入閘（序 5）之後多一關序 5′——自 {@code GET status} 取
     * {@code schedule.period_min／period_max} 驗 {@code periodMinutes}（讀取、零副作用）；取不到界＝503 {@code si_unavailable}
     * （{@code details.cause=schedule_bounds_unavailable}）。<b>不走重送閘</b>（沒有卡面 digest）。
     */
    Receipt setSchedule(String user, ScheduleSetInput input);

    /** 立即啟動請求（P4；{@code run-request}）：閘門序同上，沒有序 5′、<b>不走重送閘</b>（防連點只靠前端的軟停用）。 */
    Receipt requestRun(String user, RunRequestInput input);

    /** 唯讀預檢（根層 {@code obs-add --dry-run}）：不取 ref、不簽章、不寫資料庫、不落檔。 */
    SiValidation validateObservation(String user, ObservationInput input);

    // ── 研究來源單一化（API 契約 §5A.4；API-SI-14、API-SI-15）──────────────────────────────────────

    /**
     * 登記同步的結果。
     *
     * @param outcome        {@code written}（201；新稽核檔已落地）｜{@code unchanged}（200；零副作用）
     * @param state          {@code pending}（稽核檔已落地、待入帳）｜{@code synced}（只有 unchanged 且已入帳時）
     * @param registrySha256 本次同步的登記快照 digest
     * @param auditRef       written＝新稽核檔的編號；unchanged＝已存在那一份（待入帳者或最新已入帳者）的編號
     * @param kind           {@code src-registry}（unchanged 時 null）
     * @param time           稽核 body 的 time（unchanged 時 null）
     * @param keyId          簽章金鑰 sha256 前 8 碼（unchanged 時 null）
     */
    record RegistrySyncResult(String outcome, String state, String registrySha256, String auditRef, String kind, String time, String keyId) {
    }

    /** 登記同步狀態（API-SI-14）：{@code state}＝{@code synced｜unsynced｜pending｜unknown}；{@code unknown} 時 {@code unknownCause} 非 null、其餘欄皆 null（{@code currentSha256} 除外）。 */
    record RegistrySyncStatus(String state, String unknownCause, String currentSha256, String ingestedSha256, String ingestedAuditRef,
                              String pendingAuditRef, String pendingTime, Integer researchFetchMax) {
    }

    /**
     * 把 Bridge 當下的登記快照簽成稽核檔送去落地（API-SI-15）。閘門序（先中者定案）：授權→停用→取 Bridge 快照→冪等檢查（讀鏡像與表內列）→外層檔位元組數→取 ref、簽章、INSERT、單次
     * Bridge 落檔；序 4 至 6 任一拒絕＝零副作用。冪等只比「最新」：有更新的待入帳寫入時，當前 digest 須等於它才算 {@code unchanged}。
     */
    RegistrySyncResult syncResearchRegistry(String user);

    /** 登記同步狀態（API-SI-14；VIEWER 以上可讀）：沒有當前 digest 就沒有狀態——取快照失敗照 502／503／504 丟出，不降級成 unknown。 */
    RegistrySyncStatus researchRegistryStatus();
}
