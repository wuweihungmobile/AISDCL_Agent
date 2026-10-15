package com.aisdlc.console.infrastructure.config;

import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.boot.test.context.ConfigDataApplicationContextInitializer;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.boot.tomcat.autoconfigure.TomcatServerProperties;

import java.util.List;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * docker profile 的可信代理設定（契約附錄 D.2；QA O-20；C-16）。為什麼重要：Tomcat 的 {@code RemoteIpValve} 預設信任「所有私網位址」——
 * 主機（Docker 閘道）或內網客戶端進來的請求也是私網位址，其自填的 {@code X-Forwarded-For} 就被採信、換掉未認證限流的桶（連打 101 次都不會 429）。
 * 所以 docker profile 把可信代理縮成 compose 的固定子網（.2～.254；.1 是閘道＝主機端進來的位址，刻意排除），並可由 {@code CONSOLE_INTERNAL_PROXIES} 覆寫。
 * 這裡驗「設定檔真的載入了正確的值、Spring Boot 的 Tomcat 屬性綁得到它」，Tomcat 實際行為由全棧 e2e 驗。
 */
class DockerProfileProxiesTest {

    private static final String PROPERTY = "server.tomcat.remoteip.internal-proxies";

    private static ApplicationContextRunner runnerFor(String profile) {
        return new ApplicationContextRunner().withInitializer(new ConfigDataApplicationContextInitializer())
                .withPropertyValues("spring.profiles.active=" + profile);
    }

    @Test
    void theDefaultTrustsOnlyTheComposeSubnetFromDotTwoToDotTwoFiftyFour() {
        runnerFor("docker").run(context -> {
            Pattern trusted = Pattern.compile(context.getEnvironment().getProperty(PROPERTY));

            for (String ip : List.of("172.31.250.2", "172.31.250.9", "172.31.250.10", "172.31.250.99", "172.31.250.100",
                    "172.31.250.199", "172.31.250.200", "172.31.250.249", "172.31.250.250", "172.31.250.254")) {
                assertThat(trusted.matcher(ip).matches()).as(ip + " 在 compose 子網內（nginx 所在）").isTrue();
            }
            for (String ip : List.of("172.31.250.1", "172.31.250.0", "172.31.250.255", "172.31.250.256", "172.31.250.02",
                    "172.31.251.2", "172.31.25.2", "172.30.250.2", "10.0.0.5", "192.168.1.50", "127.0.0.1", "172.16.0.2",
                    "0:0:0:0:0:0:0:1", "::1")) {
                assertThat(trusted.matcher(ip).matches()).as(ip + " 不可信（閘道＝主機端、其他私網、loopback 一律不信）").isFalse();
            }
        });
    }

    @Test
    void theEnvironmentVariableOverridesTheDefault() {
        runnerFor("docker").withSystemProperties("CONSOLE_INTERNAL_PROXIES=10\\.77\\.5\\.(?:[2-9]|[1-9]\\d)").run(context -> {
            assertThat(context.getEnvironment().getProperty(PROPERTY)).isEqualTo("10\\.77\\.5\\.(?:[2-9]|[1-9]\\d)");
            assertThat(Pattern.matches(context.getEnvironment().getProperty(PROPERTY), "10.77.5.12")).isTrue();
            assertThat(Pattern.matches(context.getEnvironment().getProperty(PROPERTY), "172.31.250.2")).isFalse();
        });
    }

    @Test
    void springBootsTomcatPropertiesBindTheValueToTheRemoteIpValvesInternalProxies() {
        runnerFor("docker").run(context -> {
            TomcatServerProperties tomcat = Binder.get(context.getEnvironment())
                    .bind("server.tomcat", TomcatServerProperties.class).get();

            assertThat(tomcat.getRemoteip().getInternalProxies())
                    .isEqualTo("172\\.31\\.250\\.(?:[2-9]|[1-9]\\d|1\\d\\d|2[0-4]\\d|25[0-4])");
        });
    }

    @Test
    void onlyTheDockerProfileNarrowsTheProxiesTheOtherProfilesKeepTomcatsDefault() {
        // e2e／本機：測試 client 在 loopback，需要 Tomcat 預設（含 loopback）才會採信它轉送的 X-Forwarded-For；
        // production 直連（forward-headers-strategy=none）沒有 RemoteIpValve，這個值本來就不會被用到
        for (String profile : List.of("e2e", "test", "default")) {
            runnerFor(profile).run(context -> assertThat(context.getEnvironment().getProperty(PROPERTY))
                    .as("profile=" + profile).isNull());
        }
    }
}
