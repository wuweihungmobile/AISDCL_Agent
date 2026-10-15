package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.ImportRecordRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * 啟動復原：{@code parse} 是同步呼叫，PARSING 狀態只存在於「處理該請求的執行緒」活著的期間。行程若在解析途中終止
 * （重啟、當機），資料庫裡會留下永遠的 PARSING——之後 parse 回 409「解析中」、reject 也回 409，這筆記錄就死了。
 * 啟動完成時一律把殘留的 PARSING 退回 UPLOADED（console-api 是單一實例，重啟後不可能還有解析在進行）。
 */
@Component
class ImportStartupRecovery {

    private static final Logger LOG = LoggerFactory.getLogger(ImportStartupRecovery.class);

    private final ImportRecordRepository records;
    private final TransactionTemplate tx;

    ImportStartupRecovery(ImportRecordRepository records, TransactionTemplate tx) {
        this.records = records;
        this.tx = tx;
    }

    @EventListener(ApplicationReadyEvent.class)
    void resetStaleParsing() {
        Integer reset = tx.execute(status -> records.resetStaleParsing());
        if (reset != null && reset > 0) {
            LOG.warn("啟動復原：{} 筆停在 PARSING 的匯入記錄已退回 UPLOADED（上次執行中斷於解析途中）", reset);
        }
    }
}
