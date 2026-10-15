package com.aisdlc.console.domain.model.execution;

/**
 * 執行批次的六態（寫入 PG 的值域；PRD 附錄 B／§5.3.5）。Bridge 的八態折疊見 {@link BridgeStatus#fold()}。
 */
public enum RunStatus {
    INITIALIZING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED;

    /** 終態：COMPLETED／FAILED／CANCELLED（restore 可讓終態 run 重新進行）。 */
    public boolean terminal() {
        return this == COMPLETED || this == FAILED || this == CANCELLED;
    }
}
