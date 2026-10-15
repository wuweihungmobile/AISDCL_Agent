package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.application.port.in.ExecutionStreamUseCase;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Frame;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Kind;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Sink;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Subscription;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.headers.Header;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Optional;
import java.util.UUID;

/**
 * 前端 SSE 兩條端點（Phase 4；契約 §2）：{@code /logs}（{@code log}／{@code status-change}／{@code review-request}／{@code alert}）與
 * {@code /metrics}（{@code progress-update}／{@code token-update}／{@code metric-update}）。VIEWER 以上。
 *
 * <p>認證：{@code Authorization: Bearer} 與 {@code ?access_token=} 兩者皆收（{@code JwtAuthenticationFilter}；標頭優先、只收 access token）。
 * 訂閱、重播、去重、佇列、keep-alive 與終態關閉都在 {@link ExecutionStreamUseCase}；本類別只提供把框架寫進 {@link SseEmitter} 的
 * {@link Sink}。第一個框架是 {@code retry:3000}；之後每個事件由 {@code id}、{@code event}、{@code data}（單行緊湊 JSON，缺值的欄位省略）
 * 三個欄位加空行組成；{@code Spring SseEmitter} 輸出不帶冒號後空白，客戶端一律以解析後的欄位處理（契約 §2.1、AR-03）。
 */
@RestController
@RequestMapping("/api/v1/stream")
@Tag(name = "SSE 推送", description = "Phase 4；API-SSE")
public class StreamController {

    private static final Logger LOG = LoggerFactory.getLogger(StreamController.class);
    private static final long RECONNECT_MILLIS = 3000L;
    /** SSE 的 {@code data} 單行緊湊 JSON：沒有值的欄位省略（契約 §2.5、§2.6 的 {@code ?} 欄位）。 */
    private static final JsonMapper JSON = JsonMapper.builder()
            .changeDefaultPropertyInclusion(value -> value.withValueInclusion(JsonInclude.Include.NON_NULL))
            .build();

    private final ExecutionStreamUseCase streams;

    public StreamController(ExecutionStreamUseCase streams) {
        this.streams = streams;
    }

    @GetMapping(path = "/executions/{runId}/logs", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @SecurityRequirement(name = OpenApiNames.BEARER)
    @SecurityRequirement(name = OpenApiNames.QUERY_TOKEN)
    @ApiResponse(responseCode = "200", description = "text/event-stream",
            headers = {
                    @Header(name = "Cache-Control", description = "no-cache, no-store", schema = @Schema(type = "string")),
                    @Header(name = "X-Accel-Buffering", description = "no", schema = @Schema(type = "string"))},
            content = @Content(mediaType = "text/event-stream", schema = @Schema(type = "string",
                    description = "SSE 文字框架；每個事件 id／event／data 三個欄位（單行 JSON；冒號後空白不保證）。")))
    @ApiResponse(responseCode = "204", description = "run 已終態且沒有可重播的事件（結束重連）；沒有本文", content = @Content)
    @Operation(summary = "即時執行日誌（SSE）",
            description = "事件：log、status-change、review-request、alert（data 形狀見 Markdown 契約 §2）。認證：Authorization: Bearer 與 "
                    + "?access_token= 兩者皆收（EventSource 不能帶標頭）；後端任何存取日誌不得輸出含 access_token 的 query string，nginx 的 "
                    + "log_format 須遮罩（契約 §0.7；AR-05）。id: 沿用 Bridge seq；後端自產的事件用 <seq>.<n>。Last-Event-ID 重播未送達事件。"
                    + "每 15 秒無事件送 keep-alive 註解（內容為 keep-alive）。PAUSED 不結束串流；終態後送 status-change 並關閉；"
                    + "重連時若 run 已終態且無事件可重播 → 204（EventSource 收到 204 不再重連）")
    public ResponseEntity<SseEmitter> logs(
            @PathVariable UUID runId,
            @Parameter(description = "最後收到的事件 id（<seq> 或 <seq>.<n>）；伺服器從其後重播",
                    schema = @Schema(type = "string", pattern = "^[0-9]+(\\.[0-9]+)?$"))
            @RequestHeader(name = "Last-Event-ID", required = false) String lastEventId,
            @Parameter(description = "沒有 Last-Event-ID 時，先重播最後 N 則事件再接即時（預設 200；0＝只收之後的新事件）",
                    schema = @Schema(type = "integer", format = "int32", minimum = "0", maximum = "5000",
                            defaultValue = "200"))
            @RequestParam(required = false) Integer tail,
            @Parameter(description = "access token（與 Authorization 標頭擇一）")
            @RequestParam(name = "access_token", required = false) String accessToken) {
        return open(runId, Kind.LOGS, lastEventId, tail);
    }

    @GetMapping(path = "/executions/{runId}/metrics", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @SecurityRequirement(name = OpenApiNames.BEARER)
    @SecurityRequirement(name = OpenApiNames.QUERY_TOKEN)
    @ApiResponse(responseCode = "200", description = "text/event-stream",
            content = @Content(mediaType = "text/event-stream", schema = @Schema(type = "string")))
    @ApiResponse(responseCode = "204",
            description = "run 已終態且沒有可送的事件（Last-Event-ID 已 ≥ <S>.3；結束重連）；沒有本文", content = @Content)
    @Operation(summary = "即時執行指標（SSE）",
            description = "事件：metric-update、token-update、progress-update。三者都是狀態快照（latest-wins）：重連時不重播歷史，伺服器先送各一則"
                    + "最新快照再接即時事件（收斂重播）。三則快照的 id 互異：<S>.1＝progress-update、<S>.2＝token-update、<S>.3＝metric-update"
                    + "（S＝目前最後處理的 Bridge seq）；之後的即時事件 id 嚴格大於 <S>.3。run 已終態時：Last-Event-ID 已 ≥ <S>.3 → 204，"
                    + "否則送終態快照後關閉。其餘認證／keep-alive／框架／終態規則同 /logs")
    public ResponseEntity<SseEmitter> metrics(
            @PathVariable UUID runId,
            @Parameter(description = "最後收到的事件 id（<seq> 或 <seq>.<n>）；伺服器從其後重播",
                    schema = @Schema(type = "string", pattern = "^[0-9]+(\\.[0-9]+)?$"))
            @RequestHeader(name = "Last-Event-ID", required = false) String lastEventId,
            @Parameter(description = "access token（與 Authorization 標頭擇一）")
            @RequestParam(name = "access_token", required = false) String accessToken) {
        return open(runId, Kind.METRICS, lastEventId, null);
    }

    private ResponseEntity<SseEmitter> open(UUID runId, Kind kind, String lastEventId, Integer tail) {
        SseEmitter emitter = new SseEmitter(0L);
        EmitterSink sink = new EmitterSink(emitter);
        sink.retry();
        Optional<Subscription> subscription = streams.open(runId, kind, lastEventId, tail, sink);
        if (subscription.isEmpty()) {
            return ResponseEntity.noContent().build();
        }
        Subscription active = subscription.get();
        emitter.onCompletion(active::close);
        emitter.onTimeout(active::close);
        emitter.onError(error -> active.close());
        return ResponseEntity.ok()
                .contentType(new MediaType("text", "event-stream", StandardCharsets.UTF_8))
                .header(HttpHeaders.CACHE_CONTROL, "no-cache, no-store")
                .header("X-Accel-Buffering", "no")
                .body(emitter);
    }

    /** 把用例的框架寫進 {@link SseEmitter}；寫失敗（客戶端已斷線）回 false，用例即結束該連線。 */
    private static final class EmitterSink implements Sink {

        private final SseEmitter emitter;

        EmitterSink(SseEmitter emitter) {
            this.emitter = emitter;
        }

        /** 第一個框架：{@code retry:3000}（瀏覽器 EventSource 自動重連的等待毫秒）。 */
        void retry() {
            try {
                emitter.send(SseEmitter.event().reconnectTime(RECONNECT_MILLIS));
            } catch (IOException | RuntimeException e) {
                LOG.debug("SSE retry 框架送出失敗：{}", e.toString());
            }
        }

        @Override
        public boolean send(Frame frame) {
            try {
                SseEmitter.SseEventBuilder event = SseEmitter.event();
                if (frame.hasId()) {
                    event.id(frame.id());
                }
                emitter.send(event.name(frame.event()).data(JSON.writeValueAsString(frame.data())));
                return true;
            } catch (IOException | RuntimeException e) {
                LOG.debug("SSE 框架送出失敗（客戶端已斷線？）：{}", e.toString());
                return false;
            }
        }

        @Override
        public boolean comment(String text) {
            try {
                emitter.send(SseEmitter.event().comment(text));
                return true;
            } catch (IOException | RuntimeException e) {
                LOG.debug("SSE keep-alive 送出失敗（客戶端已斷線？）：{}", e.toString());
                return false;
            }
        }

        @Override
        public void close() {
            try {
                emitter.complete();
            } catch (RuntimeException e) {
                LOG.debug("SSE 完成通知失敗：{}", e.toString());
            }
        }
    }
}
