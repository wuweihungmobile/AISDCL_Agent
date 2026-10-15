package com.aisdlc.console.domain.model.execution;

/** 執行範圍模式（契約 §1.2.1）：ALL＝專案內全部可執行任務；SELECTED＝所選目標的可執行任務 ∪ 所選任務。 */
public enum ScopeMode {
    ALL, SELECTED
}
