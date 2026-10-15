package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;

import java.util.List;

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

    /**
     * PRD §9.2：actuator 只開 health／prometheus（外加 ADMIN 專用的 info）。其餘會洩漏設定、環境變數、堆積內容或能改變行程狀態的端點
     * （env／beans／heapdump／configprops／loggers／threaddump／shutdown…）一個都不能存在：匿名 401、非 ADMIN 403，
     * 連 ADMIN 也是 404（根本沒有被暴露，而不是「有但要權限」）。
     */
    @Test
    void sensitiveActuatorEndpointsAreNotExposedAtAllNotEvenToAnAdmin() {
        for (String endpoint : List.of("env", "beans", "heapdump", "configprops", "loggers", "threaddump", "mappings",
                "metrics", "conditions", "scheduledtasks", "shutdown", "caches", "auditevents", "httpexchanges",
                "flyway", "sessions", "startup", "quartz")) {
            String url = "/actuator/" + endpoint;
            assertThat(api.get(null, url).status()).as("匿名 " + endpoint).isEqualTo(401);
            assertThat(api.get(viewer(), url).status()).as("viewer " + endpoint).isEqualTo(403);
            assertThat(api.get(admin(), url).status()).as("admin " + endpoint).isEqualTo(404);
        }
        assertThat(api.post(admin(), "/actuator/shutdown").status()).as("shutdown 不可用").isIn(404, 405);
    }

    @Test
    void infoIsTheOnlyAdminOnlyActuatorEndpointThatExists() {
        assertThat(api.get(null, "/actuator/info").status()).isEqualTo(401);
        assertThat(api.get(viewer(), "/actuator/info").status()).isEqualTo(403);
        assertThat(api.get(admin(), "/actuator/info").status()).isEqualTo(200);
    }
}
