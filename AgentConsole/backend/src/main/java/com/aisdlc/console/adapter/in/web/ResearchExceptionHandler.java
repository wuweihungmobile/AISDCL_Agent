package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiError;
import com.aisdlc.console.domain.exception.ResearchBridgeException;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

/**
 * 研究呼叫的上游失敗（{@link ResearchBridgeException}）→ 502／504（API 契約 §0.2 第 8 列）。研究端點的上游失敗 reason 是英文識別字
 * {@code bridge_unreachable}、{@code bridge_timeout}（既有端點沿用中文常數，{@code GlobalExceptionHandler} 的 {@code statusOf} 也只認
 * {@code UpstreamException}），所以另有這個只管 {@code ResearchController} 的建議器；封包形狀與 {@code GlobalExceptionHandler} 的 {@code respond} 完全相同
 * （{@code {code,message,reason,errors[],details?,timestamp,traceId}}，固定 JSON）。優先於全域處理器，才不會被它的 {@code DomainException} 通用分支吃掉。
 *
 * <p>對映：連線階段失敗＝502、讀取逾時＝504、Bridge 回報的上游失敗（501 {@code not_implemented}、502 {@code init_failed}）＝502（reason 與 details 逐字取自 Bridge）。
 */
@RestControllerAdvice(assignableTypes = {ResearchController.class, ResearchRouteController.class, ResearchGateController.class, ResearchDeliveryController.class,
        ResearchKanbanController.class, ResearchHealingController.class})
@Order(Ordered.HIGHEST_PRECEDENCE)
public class ResearchExceptionHandler {

    @ExceptionHandler(ResearchBridgeException.class)
    public ResponseEntity<ApiError> handleBridge(ResearchBridgeException ex) {
        HttpStatus status = ex.kind() == ResearchBridgeException.Kind.TIMEOUT ? HttpStatus.GATEWAY_TIMEOUT : HttpStatus.BAD_GATEWAY;
        Map<String, Object> details = ex.details().isEmpty() ? null : ex.details();
        ApiError body = new ApiError(status.value(), ex.getMessage(), ex.reason(), List.of(), details, OffsetDateTime.now(), MDC.get("traceId"));
        return ResponseEntity.status(status).contentType(MediaType.APPLICATION_JSON).body(body);
    }
}
