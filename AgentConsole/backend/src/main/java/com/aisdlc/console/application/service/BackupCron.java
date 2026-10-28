package com.aisdlc.console.application.service;

import org.springframework.scheduling.support.CronExpression;

import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.Optional;

/**
 * 排程表達式的「下一次」與「最近一次應跑」（TCS-SysAdminBackup-20261027 R-BK-12、R-BK-17；純函式）。住 {@code application/service}（它用 Spring 的
 * {@link CronExpression}，不得進 domain：ArchUnit A1）。時間一律由呼叫端傳入（取自 {@code BackupClock}）、時區一律取自
 * {@code schedule.json.tz}（<b>不依 JVM 預設時區</b>）：本類別不呼叫任何「現在」或預設時區的方法（{@code BackupArchTest} 掃描鎖住）。
 *
 * <p>cron 格式是 crontab 的五欄（分 時 日 月 星期；星期欄 0 為週日）；Spring 要六欄，前補秒欄 {@code 0}。解析不了（含 Spring 拒絕的形狀）一律回空，
 * 由呼叫端轉成 {@code nextRunAt:null}／{@code lastDueAt:null} 加 {@code cron_unparsable:<job>}，不丟例外。
 */
final class BackupCron {

    /** {@link #lastDue} 的回溯窗：8 天（涵蓋最稀疏的每週排程再多一天；週期工作的 lastDueAt 因此落在 7 天內）。 */
    static final Duration LOOKBACK = Duration.ofDays(8);

    private BackupCron() {
    }

    /** 解析五欄 cron；解析不了回空。 */
    static Optional<CronExpression> parse(String cron) {
        if (cron == null || cron.isBlank()) {
            return Optional.empty();
        }
        try {
            return Optional.of(CronExpression.parse("0 " + cron.strip()));
        } catch (IllegalArgumentException e) {
            return Optional.empty();
        }
    }

    /** 嚴格晚於 {@code now} 的下一次觸發時刻（以 {@code zone} 計算）；cron 解析不了或沒有下一次回空。 */
    static Optional<Instant> next(String cron, ZoneId zone, Instant now) {
        return parse(cron).flatMap(expression -> next(expression, zone, now));
    }

    private static Optional<Instant> next(CronExpression expression, ZoneId zone, Instant now) {
        ZonedDateTime next = expression.next(ZonedDateTime.ofInstant(now, zone));
        return Optional.ofNullable(next).map(ZonedDateTime::toInstant);
    }

    /**
     * 在 {@code now} 之前（含）最近一次應跑的時刻：自 {@code now − 8 天} 起逐次取「下一次」、取最後一個 ≤ now 者。
     * 增備（週一至週六）在週日沒有時段，所以週日的 lastDue 是週六 02:00。cron 解析不了、或回溯窗內沒有任何觸發回空。
     */
    static Optional<Instant> lastDue(String cron, ZoneId zone, Instant now) {
        Optional<CronExpression> parsed = parse(cron);
        if (parsed.isEmpty()) {
            return Optional.empty();
        }
        Instant cursor = now.minus(LOOKBACK);
        Instant last = null;
        while (true) {
            Optional<Instant> next = next(parsed.get(), zone, cursor);
            if (next.isEmpty() || next.get().isAfter(now)) {
                break;
            }
            last = next.get();
            cursor = last;
        }
        return Optional.ofNullable(last);
    }
}
