package com.aisdlc.console.application.port.in;

import com.aisdlc.console.domain.model.signoff.PendingSignoffs;

/** 待審批清單（API-SGN-05／US-E-07；契約 §1.8.1；D-18）：儀表板「待人工審批」卡的清單與徽章。 */
public interface SignoffQueueUseCase {

    /** 清單最多回幾筆的上限（契約：預設 50、範圍 1～200）。 */
    int MAX_LIMIT = 200;

    /**
     * @param limit 清單最多回幾筆（1～{@value #MAX_LIMIT}）；超出範圍 {@code ValidationException}（{@code errors[0].field=limit}，HTTP 400）。
     *              只截斷 {@code items}，不影響 {@code counts}
     */
    PendingSignoffs pending(int limit);
}
