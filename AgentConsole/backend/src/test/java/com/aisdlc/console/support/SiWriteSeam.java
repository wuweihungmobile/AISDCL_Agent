package com.aisdlc.console.support;

import com.aisdlc.console.adapter.out.bridge.RequestFactoryProvider;
import com.aisdlc.console.application.port.out.SiAuditRefSource;
import com.aisdlc.console.application.port.out.SiWriteSettings;
import com.aisdlc.console.application.service.SiAuditSigner;
import com.aisdlc.console.domain.model.si.SiAuditKeyRing;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.http.client.JdkClientHttpRequestFactory;

import java.net.http.HttpClient;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Queue;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * SelfImproving 寫入整合測試的接縫（TCS-SelfImprovingDecide-P2b §5.4 的 {@code SEAM}）。三件事，全部以 {@code @Primary} 換掉同型的正式 Bean——
 * <b>不換全域的 {@code Clock}</b>：JWT 的簽發與驗證、限流都吃它，把它固定在 2026-10-24 會讓同一個 JVM 裡其他整合測試共用的 token 全部過期。
 * <ul>
 *   <li>固定時間的簽章器：{@code Clock.fixed(2026-10-24T14:30:15Z, +08:00)}，故稽核 body 的 {@code time} 為 {@code 2026-10-24T22:30:15+08:00}。</li>
 *   <li>佇列式稽核編號來源：測試先排入該 AT 要的 ref（黃金檔的 ref 固定）；佇列耗盡時大聲失敗，不退回隨機值。</li>
 *   <li>可切換的設定：預設委派給<b>正式的設定實作</b>（由 {@code @DynamicPropertySource} 設的 deciders、金鑰與權杖），測試可臨時改名單、金鑰環與權杖狀態
 *       來驗閘門序；每個測試開始前復原。</li>
 *   <li>可縮短的讀取逾時：預設不縮；造逾時的 AT 設 1 秒，免得等滿 20 秒。</li>
 * </ul>
 */
@TestConfiguration(proxyBeanMethods = false)
public class SiWriteSeam {

    /** §5.1 的向量金鑰（公開的測試金鑰；字面刻意不用 {@code sk-} 形態）。 */
    public static final String K0 = "si-p2-vector-key-0123456789-abcdefghijklmnopqrstuvwxyz";
    /** 測試用的 Bridge 寫入權杖（42 字元；{@code mock}-free 的假值，但夠長）。 */
    public static final String T0 = "si-write-token-for-tests-0123456789-abcdef";
    public static final Instant FIXED_INSTANT = Instant.parse("2026-10-24T14:30:15Z");
    public static final ZoneOffset FIXED_ZONE = ZoneOffset.ofHours(8);
    /** 固定時鐘下稽核 body 的 time。 */
    public static final String FIXED_TIME = "2026-10-24T22:30:15+08:00";

    @Bean
    @Primary
    Switchable switchableSiWriteSettings(@Qualifier("siWriteSettingsAdapter") SiWriteSettings real) {
        return new Switchable(real);
    }

    @Bean
    @Primary
    SiAuditSigner fixedClockSiAuditSigner() {
        return new SiAuditSigner(Clock.fixed(FIXED_INSTANT, FIXED_ZONE));
    }

    @Bean
    @Primary
    QueueRefs queueSiAuditRefSource() {
        return new QueueRefs();
    }

    @Bean
    @Primary
    ReadTimeoutCap readTimeoutCap() {
        return new ReadTimeoutCap();
    }

    /** 預設委派給正式實作；測試可個別覆寫名單、金鑰環、權杖狀態。 */
    public static final class Switchable implements SiWriteSettings {

        private final SiWriteSettings real;
        private volatile List<String> deciders;
        private volatile SiAuditKeyRing ring;
        private volatile Boolean tokenConfigured;

        Switchable(SiWriteSettings real) {
            this.real = real;
        }

        public Switchable deciders(String... names) {
            this.deciders = List.of(names);
            return this;
        }

        /** 名單設為空（無人可寫）。 */
        public Switchable noDeciders() {
            this.deciders = List.of();
            return this;
        }

        public Switchable noKey() {
            this.ring = SiAuditKeyRing.EMPTY;
            return this;
        }

        public Switchable noToken() {
            this.tokenConfigured = false;
            return this;
        }

        /** 回到「委派給正式實作」。 */
        public void reset() {
            deciders = null;
            ring = null;
            tokenConfigured = null;
        }

        @Override
        public List<String> deciders() {
            List<String> override = deciders;
            return override != null ? override : real.deciders();
        }

        @Override
        public SiAuditKeyRing keyRing() {
            SiAuditKeyRing override = ring;
            return override != null ? override : real.keyRing();
        }

        @Override
        public boolean bridgeWriteTokenConfigured() {
            Boolean override = tokenConfigured;
            return override != null ? override : real.bridgeWriteTokenConfigured();
        }
    }

    /** 佇列式稽核編號來源；{@link #taken()} 供「零次取用」的斷言。 */
    public static final class QueueRefs implements SiAuditRefSource {

        private final Queue<String> queue = new ConcurrentLinkedQueue<>();
        private final AtomicInteger taken = new AtomicInteger();

        public QueueRefs refs(String... refs) {
            queue.addAll(List.of(refs));
            return this;
        }

        @Override
        public String next() {
            String ref = queue.poll();
            if (ref == null) {
                throw new IllegalStateException("稽核編號佇列已耗盡：這個測試沒有排入足夠的 ref（不退回隨機值）");
            }
            taken.incrementAndGet();
            return ref;
        }

        public int taken() {
            return taken.get();
        }

        public void reset() {
            queue.clear();
            taken.set(0);
        }
    }

    /** 與正式的 JDK 請求工廠同形，但讀取逾時可被縮短（預設不縮）。 */
    public static final class ReadTimeoutCap implements RequestFactoryProvider {

        private volatile Duration cap;

        public void cap(Duration readTimeout) {
            this.cap = readTimeout;
        }

        public void reset() {
            this.cap = null;
        }

        @Override
        public ClientHttpRequestFactory create(Duration connectTimeout, Duration readTimeout) {
            Duration limit = cap;
            HttpClient client = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).connectTimeout(connectTimeout).build();
            JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(client);
            factory.setReadTimeout(limit != null && limit.compareTo(readTimeout) < 0 ? limit : readTimeout);
            return factory;
        }
    }
}
