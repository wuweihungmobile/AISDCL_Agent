package com.aisdlc.console.domain.model.monitor;

import java.time.Instant;
import java.util.UUID;

/**
 * 一則持久化的告警（{@code alerts} 的一列；契約 §3.7）。{@code subject} 對規則型告警永遠非 null
 * （否則 partial unique index 對 NULL 失效）：{@code run:<uuid>}／{@code task:<uuid>}／{@code goal:<uuid>}／{@code step:<step_id>}。
 *
 * @param eventSeq 重播錨點（建立當下已處理到的最後一則 Bridge 事件 seq）
 * @param eventSub 子序號；0＝Bridge 告警事件的持久化鏡像（SSE 不重播它）
 */
public record Alert(UUID id, UUID projectId, UUID runId, AlertRule rule, AlertSeverity severity, String subject,
                    String message, Instant createdAt, boolean acknowledged, String acknowledgedBy,
                    Instant acknowledgedAt, int eventSeq, int eventSub) {
}
