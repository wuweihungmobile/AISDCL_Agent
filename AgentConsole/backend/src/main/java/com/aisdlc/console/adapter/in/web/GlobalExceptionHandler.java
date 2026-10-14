package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiError;
import com.aisdlc.console.adapter.in.web.dto.ApiError.FieldError;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.DomainException;
import com.aisdlc.console.domain.exception.ForbiddenException;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.UnauthorizedException;
import com.aisdlc.console.domain.exception.ValidationException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.BindingResult;
import org.springframework.web.ErrorResponse;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import tools.jackson.core.JacksonException;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 統一錯誤處理（PRD §7.2 錯誤格式）。整個後端「只有這裡」產生錯誤封包——安全層的 401／403 也是把例外轉成
 * 領域例外後經由 HandlerExceptionResolver 進來（見 RestSecurityHandlers）。
 *
 * <p>對映：驗證失敗 400、未認證 401、權限不足 403、找不到 404、狀態衝突 409、其餘未預期 500（只回通用訊息，
 * 細節只寫日誌並帶 traceId，不洩漏內部資訊）。
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger LOG = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(DomainException.class)
    public ResponseEntity<ApiError> handleDomain(DomainException ex) {
        HttpStatus status = statusOf(ex);
        List<FieldError> errors = ex instanceof ValidationException validation
                ? validation.violations().stream().map(v -> new FieldError(v.field(), v.message())).toList()
                : List.of();
        return respond(status, ex.getMessage(), ex.reason(), errors, ex.details());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiError> handleBeanValidation(MethodArgumentNotValidException ex) {
        BindingResult result = ex.getBindingResult();
        List<FieldError> errors = result.getFieldErrors().stream()
                .map(e -> new FieldError(e.getField(), e.getDefaultMessage() == null ? "不合法" : e.getDefaultMessage()))
                .collect(Collectors.toCollection(java.util.ArrayList::new));
        result.getGlobalErrors().forEach(e -> errors.add(new FieldError(e.getObjectName(),
                e.getDefaultMessage() == null ? "不合法" : e.getDefaultMessage())));
        return respond(HttpStatus.BAD_REQUEST, "Validation failed", null, errors, Map.of());
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ApiError> handleUnreadable(HttpMessageNotReadableException ex) {
        List<FieldError> errors = List.of();
        if (ex.getCause() instanceof JacksonException jackson && !jackson.getPath().isEmpty()) {
            String path = jackson.getPath().stream()
                    .map(ref -> ref.getPropertyName() != null ? ref.getPropertyName() : "[" + ref.getIndex() + "]")
                    .collect(Collectors.joining("."));
            errors = List.of(new FieldError(path, "欄位型別不符或值不合法"));
        }
        return respond(HttpStatus.BAD_REQUEST, "請求本文不是合法的 JSON 或欄位型別不符", "MALFORMED_REQUEST_BODY",
                errors, Map.of());
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ApiError> handleTypeMismatch(MethodArgumentTypeMismatchException ex) {
        String message = "參數 " + ex.getName() + " 的值格式不正確";
        return respond(HttpStatus.BAD_REQUEST, message, null, List.of(new FieldError(ex.getName(), message)),
                Map.of());
    }

    /** 其餘例外：Spring MVC 自己的 HTTP 例外（405／415／404…）保留其狀態碼；真正未預期的才是 500。 */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiError> handleOther(Exception ex) {
        if (ex instanceof ErrorResponse mvc) {
            HttpStatusCode status = mvc.getStatusCode();
            return respond(status, genericMessage(status), mvc.getBody().getDetail(), List.of(), Map.of());
        }
        LOG.error("未預期的例外（traceId={}）", MDC.get("traceId"), ex);
        return respond(HttpStatus.INTERNAL_SERVER_ERROR, "Internal server error", null, List.of(), Map.of());
    }

    private static HttpStatus statusOf(DomainException ex) {
        if (ex instanceof ValidationException) {
            return HttpStatus.BAD_REQUEST;
        }
        if (ex instanceof UnauthorizedException) {
            return HttpStatus.UNAUTHORIZED;
        }
        if (ex instanceof ForbiddenException) {
            return HttpStatus.FORBIDDEN;
        }
        if (ex instanceof NotFoundException) {
            return HttpStatus.NOT_FOUND;
        }
        if (ex instanceof ConflictException) {
            return HttpStatus.CONFLICT;
        }
        return HttpStatus.INTERNAL_SERVER_ERROR;
    }

    private static String genericMessage(HttpStatusCode status) {
        return switch (status.value()) {
            case 400 -> "請求格式錯誤";
            case 404 -> "找不到資源";
            case 405 -> "不支援的 HTTP 方法";
            case 406 -> "不支援要求的回應格式";
            case 415 -> "不支援的 Content-Type";
            default -> HttpStatus.valueOf(status.value()).getReasonPhrase();
        };
    }

    private static ResponseEntity<ApiError> respond(HttpStatusCode status, String message, String reason,
                                                    List<FieldError> errors, Map<String, Object> details) {
        ApiError body = new ApiError(status.value(), message, reason, errors,
                details == null || details.isEmpty() ? null : details, OffsetDateTime.now(), MDC.get("traceId"));
        // 固定 JSON：避免客戶端 Accept 標頭讓「錯誤回應本身」又觸發內容協商失敗。
        return ResponseEntity.status(status).contentType(MediaType.APPLICATION_JSON).body(body);
    }
}
