package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.signoff.PendingSignoffCounts;
import com.aisdlc.console.domain.model.signoff.PendingSignoffItem;

import java.util.List;

/**
 * 待簽核草案的跨專案佇列（只讀；契約 §1.8.1；D-18）。判準與通知摘要的 {@link NotificationCounts#pendingSignoffs()} <b>完全相同</b>
 * ——計數與清單的述詞由同一處產生，所以 {@code counts().total()} 恆等於 {@code NotificationCounts.pendingSignoffs()}。
 */
public interface SignoffQueue {

    /** 四種草案各自的待簽核數（一個 SQL 敘述取出，同一個快照）。 */
    PendingSignoffCounts counts();

    /** 依 {@code created_at} 升冪（同值以 {@code id}；NULL 排最後）的前 {@code limit} 筆。 */
    List<PendingSignoffItem> items(int limit);
}
