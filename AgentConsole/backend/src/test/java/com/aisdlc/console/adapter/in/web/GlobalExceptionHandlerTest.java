package com.aisdlc.console.adapter.in.web;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
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
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.context.request.async.AsyncRequestNotUsableException;
import org.springframework.web.method.annotation.ExceptionHandlerMethodResolver;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/** 例外 → HTTP 狀態與 PRD §7.2 錯誤封包的對映（不啟動 Spring，純單元）。 */
class GlobalExceptionHandlerTest {

    private static final String RUN = "1a28bd6f-14ca-4afb-955e-e66ce2981725";

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler();
    private final Logger handlerLogger = (Logger) LoggerFactory.getLogger(GlobalExceptionHandler.class);
    private final ListAppender<ILoggingEvent> logs = new ListAppender<>();
    private Level levelBefore;

    @BeforeEach
    void captureHandlerLog() {
        levelBefore = handlerLogger.getLevel();
        handlerLogger.setLevel(Level.DEBUG);
        logs.start();
        handlerLogger.addAppender(logs);
    }

    @AfterEach
    void clearMdcAndRestoreLog() {
        MDC.clear();
        handlerLogger.detachAppender(logs);
        logs.stop();
        handlerLogger.setLevel(levelBefore);
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

    // ── 客戶端斷線（DEF-AC-014）──────────────────────────────────────────────────

    private static AsyncRequestNotUsableException clientGone() {
        return new AsyncRequestNotUsableException("Servlet container error notification for disconnected client",
                new IOException("Broken pipe"));
    }

    private static MockHttpServletResponse sseResponse(String traceId) {
        MockHttpServletResponse response = new MockHttpServletResponse();
        response.setContentType("text/event-stream;charset=UTF-8");
        if (traceId != null) {
            response.setHeader("X-Trace-Id", traceId);
        }
        return response;
    }

    /** 到目前為止攔到的日誌事件（處理器的 logger 在每個測試前已開到 DEBUG）。 */
    private List<ILoggingEvent> events() {
        return List.copyOf(logs.list);
    }

    @Test
    void aClientThatLeftIsNotAnErrorAndNothingIsWrittenToTheDeadConnection() {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/stream/executions/" + RUN + "/logs");
        MockHttpServletResponse response = sseResponse("trace-abc");

        handler.handleClientGone(clientGone(), request, response);

        assertThat(response.getContentAsByteArray()).as("不寫任何本文（沒有 ApiError）").isEmpty();
        assertThat(response.getContentType()).as("Content-Type 不被改成 JSON").startsWith("text/event-stream");
        assertThat(events()).hasSize(1).noneMatch(event -> event.getLevel().isGreaterOrEqual(Level.WARN));
        ILoggingEvent line = events().get(0);
        assertThat(line.getLevel()).isEqualTo(Level.DEBUG);
        assertThat(line.getFormattedMessage()).contains("run=" + RUN).contains("traceId=trace-abc")
                .contains("path=/api/v1/stream/executions/" + RUN + "/logs").contains("Broken pipe");
    }

    @Test
    void theDisconnectLineNeverCarriesTheQueryStringOrTheAccessToken() {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/stream/executions/" + RUN + "/metrics");
        request.setQueryString("access_token=SECRET-TOKEN-VALUE");
        request.setParameter("access_token", "SECRET-TOKEN-VALUE");

        handler.handleClientGone(clientGone(), request, sseResponse("t-1"));

        assertThat(events()).singleElement().satisfies(event -> assertThat(event.getFormattedMessage())
                .contains("run=" + RUN).doesNotContain("SECRET-TOKEN-VALUE").doesNotContain("access_token"));
    }

    @Test
    void theTraceIdComesFromTheResponseHeaderThenTheMdcThenADash() {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/stream/executions/" + RUN + "/logs");
        MDC.put("traceId", "from-mdc");

        handler.handleClientGone(clientGone(), request, sseResponse("from-header"));
        handler.handleClientGone(clientGone(), request, sseResponse(null));
        MDC.clear();
        handler.handleClientGone(clientGone(), request, sseResponse(null));

        assertThat(events()).extracting(ILoggingEvent::getFormattedMessage).satisfiesExactly(
                first -> assertThat(first).contains("traceId=from-header"),
                second -> assertThat(second).contains("traceId=from-mdc"),
                third -> assertThat(third).contains("traceId=-"));
    }

    @Test
    void aDisconnectOutsideTheStreamPathsIsJustAsQuietAndSaysThereIsNoRun() {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/monitor/projects/x/report");

        handler.handleClientGone(clientGone(), request, new MockHttpServletResponse());

        assertThat(events()).singleElement().satisfies(event -> {
            assertThat(event.getLevel()).isEqualTo(Level.DEBUG);
            assertThat(event.getFormattedMessage()).contains("run=-").contains("path=/api/v1/monitor/projects/x/report");
        });
    }

    @Test
    void springSendsAClientThatLeftToItsOwnHandlerAndTheRestToHandleOther() {
        ExceptionHandlerMethodResolver resolver = new ExceptionHandlerMethodResolver(GlobalExceptionHandler.class);

        assertThat(resolver.resolveMethodByThrowable(clientGone()).getName()).isEqualTo("handleClientGone");
        assertThat(resolver.resolveMethodByThrowable(new IllegalStateException("boom")).getName())
                .isEqualTo("handleOther");
        assertThat(resolver.resolveMethodByThrowable(new IOException("Broken pipe")).getName())
                .as("沒有被容器包成 AsyncRequestNotUsableException 的 IOException 維持原行為（不猜訊息字樣）")
                .isEqualTo("handleOther");
    }

    @Test
    void aRealUnexpectedExceptionStillLogsOneErrorWithTraceIdAndStack() {
        MDC.put("traceId", "trace-real");

        handler.handleOther(new IllegalStateException("boom"));

        assertThat(events()).singleElement().satisfies(event -> {
            assertThat(event.getLevel()).isEqualTo(Level.ERROR);
            assertThat(event.getFormattedMessage()).isEqualTo("未預期的例外（traceId=trace-real）");
            assertThat(event.getThrowableProxy().getClassName()).isEqualTo("java.lang.IllegalStateException");
        });
    }
}
