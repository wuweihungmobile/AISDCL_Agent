package com.aisdlc.console.support;

import com.aisdlc.console.application.port.out.BackupClock;

import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.atomic.AtomicReference;

/**
 * 可撥動的備份專屬時鐘（TCS-SysAdminBackup-20261027 §5.2）。<b>只實作 {@link BackupClock}、不是 {@code java.time.Clock}</b>：全域 {@code Clock}
 * （JWT、限流、審計都吃它）完全不被換掉，{@code AbstractApiIT} 的 JVM 靜態 token 因此不受撥動影響。執行緒安全（假 runner 與對帳執行緒同讀）。
 */
public final class MutableClock implements BackupClock {

    private final AtomicReference<Instant> now;

    public MutableClock(Instant start) {
        this.now = new AtomicReference<>(start);
    }

    @Override
    public Instant instant() {
        return now.get();
    }

    public void set(Instant instant) {
        now.set(instant);
    }

    public void advance(Duration duration) {
        now.updateAndGet(current -> current.plus(duration));
    }
}
