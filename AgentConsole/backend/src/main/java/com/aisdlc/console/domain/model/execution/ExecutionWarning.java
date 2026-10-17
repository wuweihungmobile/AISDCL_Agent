package com.aisdlc.console.domain.model.execution;

/**
 * execute 的 201 回應的警告項（v1.5，D-115-06；契約 §1.10.6）。<b>只有 execute 的 201 帶它</b>。目前兩種 {@code code}：
 * <ul>
 *   <li>{@link #GOVERNANCE_INACTIVE}：範圍內至少有一個 SDD 來源任務，但本批次<b>沒有</b>啟用 SDD 治理（沒有預檢、沒有 FSM 同步、
 *       step_id 維持 {@code G<g>-T<t>}、事後也不會有追溯報告）；{@code cause} 是下方五個常數之一；</li>
 *   <li>{@link #FROZEN_DIGEST_ABSENT}：已啟用治理，但凍結時沒有記錄內容摘要（舊狀態檔）——放行，<b>無法偵測凍結後改檔</b>
 *       （Bridge 回的 201 {@code warnings} 原樣轉入，沒有 {@code cause}）。</li>
 * </ul>
 *
 * @param code   警告碼
 * @param cause  只有 {@link #GOVERNANCE_INACTIVE} 帶；其餘為 null
 * @param detail 給人看的中文說明
 */
public record ExecutionWarning(String code, String cause, String detail) {

    public static final String GOVERNANCE_INACTIVE = "sdd_governance_inactive";
    public static final String FROZEN_DIGEST_ABSENT = "sdd_frozen_digest_absent";

    /** {@link #GOVERNANCE_INACTIVE} 的 {@code cause} 值域（契約 §1.10.5 的五項資格，依表的順序）。 */
    public static final String NOT_BOUND = "not_bound";
    public static final String TOKEN_NOT_CONFIGURED = "token_not_configured";
    public static final String MIXED_SCOPE = "mixed_scope";
    public static final String SPEC_MISMATCH = "spec_mismatch";
    public static final String DUPLICATE_STEP_ID = "duplicate_step_id";

    /** 治理未啟用的警告。 */
    public static ExecutionWarning inactive(String cause, String detail) {
        return new ExecutionWarning(GOVERNANCE_INACTIVE, cause, detail);
    }
}
