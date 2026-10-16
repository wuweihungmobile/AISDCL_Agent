package com.aisdlc.console.domain.model.engine;

/**
 * {@code GET /engines/sdd} 回應欄位 {@code reason} 的值域（契約 §1.7.1；<b>回應欄位的值，不是 {@code ApiError.reason}</b>）。
 * {@code BRIDGE_UNREACHABLE}／{@code SDD_UNAVAILABLE}／{@code BRIDGE_ERROR} 時 {@code available=false}；
 * {@code FSM_NOT_FOUND}／{@code FSM_STATE_UNREADABLE} 時 {@code available=true}、{@code fsm=null}。
 */
public enum SddEngineReason {

    /** 任一 Bridge 呼叫連線失敗或逾時。 */
    BRIDGE_UNREACHABLE("bridge_unreachable", false),
    /** {@code /sdd/version} 或 {@code /sdd/fsm} 回 503 {@code sdd_unavailable}（{@code SDD_ROOT} 無效、找不到 SDD 版本目錄）。 */
    SDD_UNAVAILABLE("sdd_unavailable", false),
    /** 其餘非 2xx，或 2xx 但本文不是預期的 JSON 形狀。 */
    BRIDGE_ERROR("bridge_error", false),
    /** 帶了 {@code project}，{@code GET /sdd/fsm/{project}} 回 404（{@code fsm_not_found}）。 */
    FSM_NOT_FOUND("fsm_not_found", true),
    /** 帶了 {@code project}，Bridge 回 422（{@code fsm_state_unreadable}：YAML 壞掉、或缺 {@code fsm_state} 根節點）。 */
    FSM_STATE_UNREADABLE("fsm_state_unreadable", true);

    private final String wire;
    private final boolean engineAvailable;

    SddEngineReason(String wire, boolean engineAvailable) {
        this.wire = wire;
        this.engineAvailable = engineAvailable;
    }

    /** 回應裡的字面值（小寫底線）。 */
    public String wire() {
        return wire;
    }

    /** 這個原因發生時，{@code available} 是否仍為 true。 */
    public boolean engineAvailable() {
        return engineAvailable;
    }
}
