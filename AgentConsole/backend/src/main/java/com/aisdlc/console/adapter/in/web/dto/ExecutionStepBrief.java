package com.aisdlc.console.adapter.in.web.dto;

import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

/**
 * 任務詳情的「執行歷史」單筆（US-T-02；由 execution_steps 依 task_id 衍生）。
 * Phase 2 沒有執行資料，{@code executionHistory} 為空清單；欄位在此定義好，Phase 4 起由執行引擎事件填入。
 */
public record ExecutionStepBrief(
        @NotNull UUID id,
        @NotNull int stepNumber,
        @NotNull String action,
        @NotNull String status,
        Long tokensUsed,
        String errorMessage,
        Instant timestamp) {
}
