package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.NotificationUseCase;
import com.aisdlc.console.application.port.out.NotificationCounts;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

/**
 * 通知摘要（API-NTF-01；契約 §1.4.1）。只讀、跨專案的三個計數，加上 Engine Bridge 最近一次健康探測的結果與時間
 * （{@link BridgeHealthMonitor}；頂列「Engine Bridge · 已連線」燈）。從未探測過（探測環還是空的）兩欄為 null，
 * 前端顯示「未知」灰點（AR-08：W3-B1 階段恆為 null，W3-B2 在同一支 controller 補實值）。
 */
@Service
@Transactional(readOnly = true)
public class NotificationService implements NotificationUseCase {

    private final NotificationCounts counts;
    private final BridgeHealthMonitor health;

    public NotificationService(NotificationCounts counts, BridgeHealthMonitor health) {
        this.counts = counts;
        this.health = health;
    }

    @Override
    public NotificationSummary summary() {
        Optional<BridgeHealthMonitor.Probe> probe = health.last();
        return new NotificationSummary(counts.pendingSignoffs(), counts.pendingReviews(),
                counts.unacknowledgedAlerts(), probe.map(BridgeHealthMonitor.Probe::ok).orElse(null),
                probe.map(BridgeHealthMonitor.Probe::at).orElse(null));
    }
}
