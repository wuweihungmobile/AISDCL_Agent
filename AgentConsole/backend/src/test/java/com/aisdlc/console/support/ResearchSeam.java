package com.aisdlc.console.support;

import com.aisdlc.console.adapter.out.bridge.BridgeEndpoints;
import com.aisdlc.console.application.port.out.SettingValues;
import com.aisdlc.console.infrastructure.config.BridgeProperties;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;

import java.util.Optional;

/**
 * 研究整合測試的接縫（TCS-ResearchToPRD-P0 §5）。兩件事，全部以 {@code @Primary} 換掉同型的正式 Bean——<b>不換全域的 {@code Clock}</b>（JWT 與限流都吃它）：
 * <ul>
 *   <li>可切換的研究寫入權杖（{@link SwitchableEndpoints}）：預設委派給正式實作（{@code application-test.yml} 的假權杖，研究寫入面預設啟用）；測試可臨時改成「未設」
 *       （驗 backend 端的 503 {@code research_write_disabled}、一個請求都不發）或「與 Bridge 不符」（驗 Bridge 的 403 {@code research_write_forbidden}）。</li>
 *   <li>可縮短的讀取逾時（{@link SiWriteSeam.ReadTimeoutCap}）：預設不縮；造逾時的 AT 設 1 秒，免得等滿 30 秒。</li>
 * </ul>
 */
@TestConfiguration(proxyBeanMethods = false)
public class ResearchSeam {

    @Bean
    @Primary
    SwitchableEndpoints switchableResearchEndpoints(SettingValues settings, BridgeProperties properties) {
        return new SwitchableEndpoints(settings, properties);
    }

    @Bean
    @Primary
    SiWriteSeam.ReadTimeoutCap researchReadTimeoutCap() {
        return new SiWriteSeam.ReadTimeoutCap();
    }

    /** 研究寫入權杖可臨時覆寫的 {@link BridgeEndpoints}；{@link #reset()} 回到正式實作。 */
    public static final class SwitchableEndpoints extends BridgeEndpoints {

        private volatile boolean unset;
        private volatile String override;

        SwitchableEndpoints(SettingValues settings, BridgeProperties properties) {
            super(settings, properties);
        }

        /** backend 沒設研究寫入權杖。 */
        public void tokenUnset() {
            this.unset = true;
        }

        /** backend 附的權杖與 Bridge 的不符。 */
        public void tokenWrong() {
            this.override = "mock-bridge-research-WRONG-token-for-tests-0123456789";
        }

        public void reset() {
            this.unset = false;
            this.override = null;
        }

        @Override
        public Optional<String> researchWriteToken() {
            if (unset) {
                return Optional.empty();
            }
            return override != null ? Optional.of(override) : super.researchWriteToken();
        }
    }
}
