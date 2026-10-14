package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/** 健康檢查與 Prometheus 指標端點（API-HLT-01／02；compose healthcheck、Prometheus 抓取目標）。 */
class ActuatorIT extends AbstractApiIT {

    @Test
    void healthIsUpWithoutATokenAndHidesComponentDetails() {
        Resp health = api.get(null, "/actuator/health");
        assertThat(health.status()).isEqualTo(200);
        assertThat(health.<String>read("$.status")).isEqualTo("UP");
        assertThat(health.has("$.components")).as("匿名不可看到資料庫等元件細節").isFalse();
    }

    @Test
    void livenessAndReadinessProbesAreExposed() {
        assertThat(api.get(null, "/actuator/health/liveness").<String>read("$.status")).isEqualTo("UP");
        assertThat(api.get(null, "/actuator/health/readiness").<String>read("$.status")).isEqualTo("UP");
    }

    @Test
    void prometheusExposesJvmDatabasePoolAndHttpMetricsWithoutAToken() {
        api.get(admin(), "/api/v1/projects");
        Resp prometheus = api.get(null, "/actuator/prometheus");
        assertThat(prometheus.status()).isEqualTo(200);
        assertThat(prometheus.body())
                .contains("jvm_memory_used_bytes")
                .contains("hikaricp_connections")
                .contains("http_server_requests_seconds_count");
    }
}
