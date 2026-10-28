package com.aisdlc.console.support;

import com.aisdlc.console.application.port.out.AuditTrail;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.jdbc.core.JdbcTemplate;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * 備份整合測試的接縫（TCS-SysAdminBackup-20261027 §5.2、D-BK-T3）。兩件事，全部以 {@code @Primary} 換掉同型的正式 Bean——
 * <b>不換全域的 {@code Clock}</b>：JWT 的簽發與驗證、限流、審計都吃它，撥動它會讓同一個 JVM 裡共用的 access token 全部過期（先例 {@link SiWriteSeam}）。
 * <ul>
 *   <li>可撥動的專屬時鐘 {@link MutableClock}（只換 {@code BackupClock}）；預設停在 2026-10-27T02:00:00Z（＝台北週二 10:00）。</li>
 *   <li>審計觀察包裝：<b>委派正式實作</b>，並在每次 {@code system("backup.finished", …)} 被呼叫的<b>當下</b>，以獨立連線讀該列的 {@code status} 並記錄——
 *       用來驗「審計在交易提交之後才寫」（提交前寫會讀到 RUNNING）。</li>
 * </ul>
 */
@TestConfiguration(proxyBeanMethods = false)
public class BackupSeam {

    /** 預設的「現在」：2026-10-27T02:00:00Z（台北週二 10:00）。 */
    public static final Instant DEFAULT_NOW = Instant.parse("2026-10-27T02:00:00Z");

    @Bean
    @Primary
    MutableClock mutableBackupClock() {
        return new MutableClock(DEFAULT_NOW);
    }

    @Bean
    @Primary
    ObservedAuditTrail observedAuditTrail(@Qualifier("requestAuditTrail") AuditTrail real, JdbcTemplate jdbc) {
        return new ObservedAuditTrail(real, jdbc);
    }

    /** 委派給正式實作的審計包裝；記錄 {@code backup.finished} 被呼叫當下的資料列狀態。 */
    public static final class ObservedAuditTrail implements AuditTrail {

        private final AuditTrail real;
        private final JdbcTemplate jdbc;
        private final List<String> statusesSeenAtFinish = new CopyOnWriteArrayList<>();

        ObservedAuditTrail(AuditTrail real, JdbcTemplate jdbc) {
            this.real = real;
            this.jdbc = jdbc;
        }

        /** 每次 {@code backup.finished} 被呼叫時，該列在資料庫裡的 status（獨立連線讀）。 */
        public List<String> statusesSeenAtFinish() {
            return statusesSeenAtFinish;
        }

        public void reset() {
            statusesSeenAtFinish.clear();
        }

        @Override
        public void note(String action, String entityType, String entityId) {
            real.note(action, entityType, entityId);
        }

        @Override
        public void note(String action, String entityType, String entityId, Map<String, Object> extra) {
            real.note(action, entityType, entityId, extra);
        }

        @Override
        public void event(String action, Map<String, Object> details) {
            real.event(action, details);
        }

        @Override
        public void system(String action, String entityType, String entityId, Map<String, Object> details) {
            if ("backup.finished".equals(action) && entityId != null) {
                statusesSeenAtFinish.add(jdbc.queryForObject("select status from console.backup_jobs where id = ?::uuid",
                        String.class, entityId));
            }
            real.system(action, entityType, entityId, details);
        }
    }
}
