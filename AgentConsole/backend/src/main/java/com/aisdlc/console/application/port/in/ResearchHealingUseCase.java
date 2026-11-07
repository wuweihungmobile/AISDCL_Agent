package com.aisdlc.console.application.port.in;

import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

/**
 * 自癒監視器用例（API-RP-27；AC-R2P-16；D-138 Q-6／Q-13、D-149#5）：{@code GET …/healing} 只讀 DB（視圖加遮蔽）與 {@code ResearchHealingNotifier}
 * 的記憶體快取，<b>零 Bridge 請求</b>；{@code attribution}、{@code patchResult} 沒有獨立資料來源，恆為 null（引擎未提供），不假造。
 */
public interface ResearchHealingUseCase {

    @Schema(name = "HealingRow", description = "自癒視圖的一列。excerpt＝error_message 先遮蔽再取尾端 300 字元；attribution、patchResult 引擎未提供，恆為 null")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Row(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) UUID runId, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) UUID taskId, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int stepNumber, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int attempt, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String status, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String excerpt, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) OffsetDateTime occurredAt, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean resolved, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean escalated, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean specChangeForbidden, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String attribution, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) String patchResult) {
    }

    @Schema(name = "HealingSpecChange", description = "最近一次 :healing-sync 偵測到的凍結規格漂移（只告警、不還原；唯一補救是發起 SCR）")
    @JsonInclude(JsonInclude.Include.ALWAYS) record SpecChange(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<String> paths, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) OffsetDateTime detectedAt) {
    }

    @Schema(name = "HealingDto", description = "自癒歷史；retryingSteps＝最新 run 內 RETRYING 且其後無同任務非 RETRYING 列者的列數、escalatedTasks＝ESCALATED 任務數（與看板 healing 欄同一份計算）；logSyncedThrough 與落後筆數來自記憶體快取（無同步紀錄＝null 與 0）")
    @JsonInclude(JsonInclude.Include.ALWAYS) record Healing(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) UUID researchId, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<Row> rows, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int maxRetries, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int retryingSteps, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int escalatedTasks, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) OffsetDateTime logSyncedThrough, @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int logLag, @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true) SpecChange specChange) {
    }

    /** 研究專案不存在丟 404；未綁 Console 專案回空列。 */
    Healing healing(UUID researchId);
}
