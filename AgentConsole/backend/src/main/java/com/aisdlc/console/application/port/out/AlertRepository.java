package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.monitor.Alert;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** 告警儲存埠（{@code alerts}；V4＋V7）。Console 擁有。 */
public interface AlertRepository {

    /**
     * 「未確認前不重複產生」（契約 §3.7）：{@code INSERT … ON CONFLICT DO NOTHING}（partial unique index
     * {@code uq_alerts_open_rule_subject}）。真的新增了才回該列，被去重擋下回 empty。
     */
    Optional<Alert> insertIfAbsent(Alert alert);

    Optional<Alert> findById(UUID id);

    /** 冪等：只有尚未確認者才寫確認人與時間，已確認者不改寫第一次的紀錄。 */
    void acknowledge(UUID id, String by, Instant at);

    /** 專案的告警，{@code createdAt} 由新到舊；{@code runId}、{@code acknowledged} 為 null 不篩。 */
    List<Alert> find(UUID projectId, UUID runIdOrNull, Boolean acknowledged, int limit);

    /** 事件錨點在 {@code (seq, sub)} 之後（嚴格大於）且 {@code event_sub ≥ 1} 的告警（{@code /logs} 重播用）。 */
    List<Alert> findAnchoredAfter(UUID runId, int seq, int sub);

    /** 該批次已有的告警（去重判斷與衍生日誌用）。 */
    List<Alert> findByRun(UUID runId);
}
