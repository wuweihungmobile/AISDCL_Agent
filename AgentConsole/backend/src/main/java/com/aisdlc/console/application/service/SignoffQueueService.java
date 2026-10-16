package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.SignoffQueueUseCase;
import com.aisdlc.console.application.port.out.SignoffQueue;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.model.signoff.PendingSignoffs;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 待審批清單（API-SGN-05；契約 §1.8.1；D-18）。只讀；計數與清單在<b>同一個唯讀交易</b>裡取（兩個敘述之間資料變動的機會縮到最小），
 * 判準由 {@link SignoffQueue} 的實作與通知摘要共用同一組述詞。
 */
@Service
@Transactional(readOnly = true)
public class SignoffQueueService implements SignoffQueueUseCase {

    private final SignoffQueue queue;

    public SignoffQueueService(SignoffQueue queue) {
        this.queue = queue;
    }

    @Override
    public PendingSignoffs pending(int limit) {
        if (limit < 1 || limit > MAX_LIMIT) {
            throw ValidationException.of("limit", "limit 必須介於 1 到 " + MAX_LIMIT);
        }
        return new PendingSignoffs(queue.counts(), queue.items(limit));
    }
}
