package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiError;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ForbiddenException;
import com.aisdlc.console.domain.exception.IllegalStateTransitionException;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.UnauthorizedException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violation;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.HttpRequestMethodNotSupportedException;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/** 例外 → HTTP 狀態與 PRD §7.2 錯誤封包的對映（不啟動 Spring，純單元）。 */
class GlobalExceptionHandlerTest {

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler();

    @AfterEach
    void clearMdc() {
        MDC.clear();
    }

    @Test
    void eachDomainExceptionMapsToItsHttpStatus() {
        assertThat(handler.handleDomain(ValidationException.of("f", "m")).getStatusCode().value()).isEqualTo(400);
        assertThat(handler.handleDomain(new UnauthorizedException("m", "r")).getStatusCode().value()).isEqualTo(401);
        assertThat(handler.handleDomain(new ForbiddenException("m", "r")).getStatusCode().value()).isEqualTo(403);
        assertThat(handler.handleDomain(NotFoundException.of("專案", UUID.randomUUID())).getStatusCode().value())
                .isEqualTo(404);
        assertThat(handler.handleDomain(new ConflictException("m", "r")).getStatusCode().value()).isEqualTo(409);
        assertThat(handler.handleDomain(new IllegalStateTransitionException("任務", "A", "B")).getStatusCode()
                .value()).isEqualTo(409);
    }

    @Test
    void validationDetailsReasonAndTraceIdAreCarriedIntoTheBody() {
        MDC.put("traceId", "trace-123");
        ValidationException ex = new ValidationException("Validation failed", "依賴成環",
                List.of(new Violation("dependsOn", "成環"), new Violation("name", "不能為空")),
                Map.of("cycle", List.of("a", "b", "a")));
        ResponseEntity<ApiError> response = handler.handleDomain(ex);
        ApiError body = response.getBody();
        assertThat(body).isNotNull();
        assertThat(response.getHeaders().getContentType()).isEqualTo(MediaType.APPLICATION_JSON);
        assertThat(body.code()).isEqualTo(400);
        assertThat(body.reason()).isEqualTo("依賴成環");
        assertThat(body.errors()).extracting("field").containsExactly("dependsOn", "name");
        assertThat(body.details()).containsEntry("cycle", List.of("a", "b", "a"));
        assertThat(body.traceId()).isEqualTo("trace-123");
        assertThat(body.timestamp()).isNotNull();
    }

    @Test
    void emptyDetailsAndNoReasonAreOmittedFromTheBody() {
        ApiError body = handler.handleDomain(NotFoundException.of("專案", UUID.randomUUID())).getBody();
        assertThat(body).isNotNull();
        assertThat(body.details()).isNull();
        assertThat(body.reason()).isNull();
        assertThat(body.errors()).isEmpty();
    }

    @Test
    void anUnexpectedExceptionIsAGenericFiveHundredThatLeaksNothing() {
        ResponseEntity<ApiError> response = handler.handleOther(
                new IllegalStateException("secret-connection-string=jdbc:postgresql://prod/db password=hunter2"));
        ApiError body = response.getBody();
        assertThat(response.getStatusCode().value()).isEqualTo(500);
        assertThat(body).isNotNull();
        assertThat(body.message()).isEqualTo("Internal server error");
        assertThat(body.toString()).doesNotContain("secret-connection-string").doesNotContain("hunter2");
        assertThat(body.reason()).isNull();
    }

    @Test
    void springMvcHttpExceptionsKeepTheirOwnStatusCode() {
        ResponseEntity<ApiError> response = handler.handleOther(
                new HttpRequestMethodNotSupportedException(HttpMethod.PATCH.name()));
        assertThat(response.getStatusCode().value()).isEqualTo(405);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().message()).isEqualTo("不支援的 HTTP 方法");
    }
}
