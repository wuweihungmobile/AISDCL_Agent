package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Optional;

/**
 * Engine Bridge 的健康探測環（契約 §3.1：每 30 秒 {@code GET {healthCheckPath}}、逾時 3 秒；console-api 啟動時與每個 run 開始時
 * 各立即探測一次；結果存記憶體環形緩衝，容量 2,880 筆＝24 小時）。供三處使用：Agent 可用率 KPI（{@code agentAvailability}）、
 * 頂列「Engine Bridge · 已連線」燈（{@code /notifications/summary} 的 {@code bridgeConnected}／{@code bridgeCheckedAt}）、
 * 「Agent 無回應」告警（最近一次探測失敗才告警）。Redis 本輪不做，重啟即清空。
 */
@Component
public class BridgeHealthMonitor {

    /** 一次探測的結果。 */
    public record Probe(Instant at, boolean ok) {
    }

    private final AgentBridge bridge;
    private final Clock clock;
    private final int capacity;
    private final Deque<Probe> ring = new ArrayDeque<>();

    public BridgeHealthMonitor(AgentBridge bridge, RuntimeSettings settings, Clock clock) {
        this.bridge = bridge;
        this.clock = clock;
        this.capacity = Math.max(1, settings.healthProbeCapacity());
    }

    /** 立即探測一次並記入環（{@code AgentBridge#health} 不丟例外：連不上就是 ok=false）。 */
    public Probe probeNow() {
        AgentBridge.BridgeHealth health = bridge.health();
        Probe probe = new Probe(clock.instant(), health.ok());
        record(probe);
        return probe;
    }

    public synchronized void record(Probe probe) {
        if (ring.size() >= capacity) {
            ring.removeFirst();
        }
        ring.addLast(probe);
    }

    /** 最近一次探測；從未探測過回 empty（頂列燈顯示「未知」）。 */
    public synchronized Optional<Probe> last() {
        return ring.isEmpty() ? Optional.empty() : Optional.of(ring.peekLast());
    }

    /** 最近一次探測是否失敗（從未探測過視為「沒有失敗證據」，回 false）。 */
    public boolean lastProbeFailed() {
        return last().map(p -> !p.ok()).orElse(false);
    }

    /**
     * 視窗 {@code [from, to)} 內成功的探測數 ÷ 探測總數 × 100（0～100，未四捨五入）；視窗內沒有樣本時用全部現有樣本
     * （環只保留 24 小時，較長的視窗就是「現有樣本」）；完全沒有樣本回 empty。
     */
    public synchronized Optional<Double> availability(Instant from, Instant to) {
        long total = 0;
        long ok = 0;
        for (Probe p : ring) {
            if (!p.at().isBefore(from) && p.at().isBefore(to)) {
                total++;
                ok += p.ok() ? 1 : 0;
            }
        }
        if (total == 0) {
            for (Probe p : ring) {
                total++;
                ok += p.ok() ? 1 : 0;
            }
        }
        return total == 0 ? Optional.empty() : Optional.of(ok * 100.0 / total);
    }

    public synchronized int size() {
        return ring.size();
    }
}
