package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.NotificationUseCase;
import com.aisdlc.console.application.port.out.NotificationCounts;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 通知摘要（API-NTF-01；契約 §1.4.1）。只讀、跨專案的三個計數；{@code bridgeConnected}／{@code bridgeCheckedAt} 在
 * W3-B1 階段一律 null（探測環還不存在，AR-08）——W3-B2 建好探測環後在<b>同一支 controller</b> 補實值，不新增端點。
 */
@Service
@Transactional(readOnly = true)
public class NotificationService implements NotificationUseCase {

    private final NotificationCounts counts;

    public NotificationService(NotificationCounts counts) {
        this.counts = counts;
    }

    @Override
    public NotificationSummary summary() {
        return new NotificationSummary(counts.pendingSignoffs(), counts.pendingReviews(),
                counts.unacknowledgedAlerts(), null, null);
    }
}
