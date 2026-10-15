package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiError;
import com.aisdlc.console.adapter.in.web.dto.ApiError.FieldError;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ForbiddenException;
import com.aisdlc.console.domain.exception.IllegalStateTransitionException;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.PayloadTooLargeException;
import com.aisdlc.console.domain.exception.RateLimitedException;
import com.aisdlc.console.domain.exception.UnauthorizedException;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.UnsupportedFormatException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violation;
import com.aisdlc.console.domain.model.imports.GateError;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;

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

    // ── Phase 3～6 新增的例外對映 ───────────────────────────────────────────────

    @Test
    void theNewDomainExceptionsMapToTheirContractStatuses() {
        assertThat(handler.handleDomain(new UnprocessableException("m", "r", Map.of())).getStatusCode().value())
                .isEqualTo(422);
        assertThat(handler.handleDomain(new PayloadTooLargeException("m", "r", Map.of())).getStatusCode().value())
                .isEqualTo(413);
        assertThat(handler.handleDomain(new UnsupportedFormatException("m", "r", Map.of())).getStatusCode().value())
                .isEqualTo(415);
        assertThat(handler.handleDomain(new RateLimitedException(100, 60, 17)).getStatusCode().value())
                .isEqualTo(429);
        assertThat(handler.handleDomain(new UpstreamException.Unavailable("m")).getStatusCode().value())
                .as("連線失敗").isEqualTo(502);
        assertThat(handler.handleDomain(new UpstreamException.Failure("m", Map.of("bridgeStatus", 500)))
                .getStatusCode().value()).as("Bridge 5xx").isEqualTo(502);
        assertThat(handler.handleDomain(new UpstreamException.TimedOut("m")).getStatusCode().value())
                .as("讀取逾時").isEqualTo(504);
    }

    @Test
    void theUpstreamExceptionsCarryTheDocumentedReasonConstants() {
        assertThat(handler.handleDomain(new UpstreamException.Unavailable("x")).getBody().reason())
                .isEqualTo("引擎橋接服務無法連線");
        assertThat(handler.handleDomain(new UpstreamException.TimedOut("x")).getBody().reason())
                .isEqualTo("引擎橋接服務逾時");
        ApiError failure = handler.handleDomain(new UpstreamException.Failure("x",
                Map.of("bridgeStatus", 500, "bridgeReason", "spawn_failed"))).getBody();
        assertThat(failure.reason()).isEqualTo("引擎橋接服務錯誤");
        assertThat(failure.details()).containsEntry("bridgeStatus", 500).containsEntry("bridgeReason", "spawn_failed");
    }

    @Test
    void aRateLimitedResponseCarriesTheLimitWindowAndRetryAfter() {
        ApiError body = handler.handleDomain(new RateLimitedException(100, 60, 17)).getBody();
        assertThat(body).isNotNull();
        assertThat(body.code()).isEqualTo(429);
        assertThat(body.reason()).isEqualTo("超過每分鐘 100 次請求上限");
        assertThat(body.details()).containsEntry("limit", 100).containsEntry("windowSeconds", 60)
                .containsEntry("retryAfterSeconds", 17L);
    }

    @Test
    void boundedGateErrorsAreListedAllAtOnceWithTheirGateDetailAndLocation() {
        UnprocessableException ex = new UnprocessableException("解析結果未通過有界閘（3 項）", "解析結果未通過有界閘",
                List.of(new GateError("empty_prompt", "任務「x」的描述為空", "goals[0].tasks[1].description"),
                        new GateError("max_steps", "任務數 25 超過上限 24", "goals[0].tasks"),
                        new GateError("brain_failed", "模型輸出不是合法 JSON", null)),
                List.of(new Violation("specDir", "規格不合法")), Map.of("path", "LLM"));

        ApiError body = handler.handleDomain(ex).getBody();

        assertThat(body).isNotNull();
        assertThat(body.errors()).hasSize(4);
        assertThat(body.errors().get(0)).isEqualTo(new FieldError("goals[0].tasks[1].description", "任務「x」的描述為空",
                "empty_prompt", "任務「x」的描述為空", "goals[0].tasks[1].description"));
        assertThat(body.errors().get(1).gate()).isEqualTo("max_steps");
        assertThat(body.errors().get(2)).as("沒有位置的閘：field 退回閘名稱、不帶 location")
                .isEqualTo(new FieldError("brain_failed", "模型輸出不是合法 JSON", "brain_failed", "模型輸出不是合法 JSON",
                        null));
        assertThat(body.errors().get(3)).as("一般欄位違規附在閘之後").isEqualTo(new FieldError("specDir", "規格不合法"));
        assertThat(body.details()).containsEntry("path", "LLM");
    }

    @Test
    void aMultipartSizeFailureIsA413WithTheReasonOfTheEndpointThatWasCalled() {
        ApiError upload = handler.handleUploadTooLarge(new MaxUploadSizeExceededException(10_485_760L),
                new MockHttpServletRequest("POST", "/api/v1/import/upload")).getBody();
        assertThat(upload).isNotNull();
        assertThat(upload.code()).isEqualTo(413);
        assertThat(upload.reason()).isEqualTo("檔案超過 10MB 上限");
        assertThat(upload.details()).containsEntry("limitBytes", 10_485_760);

        ApiError settings = handler.handleUploadTooLarge(new MaxUploadSizeExceededException(1_048_576L),
                new MockHttpServletRequest("POST", "/api/v1/settings/import")).getBody();
        assertThat(settings).isNotNull();
        assertThat(settings.code()).isEqualTo(413);
        assertThat(settings.reason()).isEqualTo("設定檔超過 1MB 上限");
        assertThat(settings.details()).containsEntry("limitBytes", 1_048_576);
    }

    @Test
    void aMissingFilePartIsA400WithTheDocumentedReasonAndNamesThePart() {
        ResponseEntity<ApiError> response = handler.handleMissingPart(new MissingServletRequestPartException("file"));

        assertThat(response.getStatusCode().value()).isEqualTo(400);
        ApiError body = response.getBody();
        assertThat(body).isNotNull();
        assertThat(body.reason()).isEqualTo("未提供檔案");
        assertThat(body.errors()).extracting(FieldError::field).containsExactly("file");
    }
}
