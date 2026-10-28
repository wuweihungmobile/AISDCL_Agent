package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.application.port.out.BackupClock;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Clock;

/**
 * 備份專屬時間來源的正式實作（TCS-SysAdminBackup-20261027 §5.2）：<b>委派全域 {@link Clock}</b>。測試以 {@code @Primary} 只換這一支
 * （{@code support/BackupSeam}），全域 {@code Clock}——JWT、限流、審計都吃它——不動。
 */
@Configuration(proxyBeanMethods = false)
public class BackupClockConfig {

    @Bean
    BackupClock backupClock(Clock clock) {
        return clock::instant;
    }
}
