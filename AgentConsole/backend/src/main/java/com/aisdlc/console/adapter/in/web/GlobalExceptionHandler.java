package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiError;
import com.aisdlc.console.adapter.in.web.dto.ApiError.FieldError;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.DomainException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ForbiddenException;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.NotImplementedYetException;
import com.aisdlc.console.domain.exception.PayloadTooLargeException;
import com.aisdlc.console.domain.exception.RateLimitedException;
import com.aisdlc.console.domain.exception.UnauthorizedException;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.UnsupportedFormatException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.exception.ValidationException;
import jakarta.servlet.http.HttpServletRequest;
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
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;
import tools.jackson.core.JacksonException;

import java.time.OffsetDateTime;
import java.util.ArrayList;
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
        return respond(status, ex.getMessage(), ex.reason(), errorsOf(ex), ex.details());
    }

    /** 上傳超過 Spring multipart 上限（10MB／請求 11MB）：設定檔匯入與匯入檔案各有專屬 reason（契約 §1.1.1、§1.5.10）。 */
    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ResponseEntity<ApiError> handleUploadTooLarge(MaxUploadSizeExceededException ex,
                                                         HttpServletRequest request) {
        boolean settingsFile = request.getRequestURI().startsWith("/api/v1/settings/import");
        return handleDomain(settingsFile
                ? new PayloadTooLargeException("設定檔超過 1MB 上限", ErrorReasons.SETTINGS_FILE_TOO_LARGE,
                        Map.of("limitBytes", 1_048_576))
                : new PayloadTooLargeException("檔案超過 10MB 上限", ErrorReasons.FILE_TOO_LARGE,
                        Map.of("limitBytes", 10_485_760)));
    }

    /** multipart 缺少 {@code file} 部件。 */
    @ExceptionHandler(MissingServletRequestPartException.class)
    public ResponseEntity<ApiError> handleMissingPart(MissingServletRequestPartException ex) {
        String message = "請求缺少檔案部件 " + ex.getRequestPartName();
        return respond(HttpStatus.BAD_REQUEST, message, ErrorReasons.FILE_MISSING,
                List.of(new FieldError(ex.getRequestPartName(), message)), Map.of());
    }

    /** {@link ValidationException} 帶欄位違規；{@link UnprocessableException} 另帶有界閘違規（一次列出全部，不截斷）。 */
    private static List<FieldError> errorsOf(DomainException ex) {
        if (ex instanceof ValidationException validation) {
            return validation.violations().stream().map(v -> new FieldError(v.field(), v.message())).toList();
        }
        if (ex instanceof UnprocessableException unprocessable) {
            List<FieldError> errors = new ArrayList<>(unprocessable.gateErrors().stream()
                    .map(FieldError::ofGate).toList());
            unprocessable.violations().forEach(v -> errors.add(new FieldError(v.field(), v.message())));
            return errors;
        }
        return List.of();
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiError> handleBeanValidation(MethodArgumentNotValidException ex) {
        BindingResult result = ex.getBindingResult();
        List<FieldError> errors = result.getFieldErrors().stream()
                .map(e -> new FieldError(e.getField(), e.getDefaultMessage() == null ? "不合法" : e.getDefaultMessage()))
                .collect(Collectors.toCollection(ArrayList::new));
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
        if (ex instanceof UnprocessableException) {
            return HttpStatus.UNPROCESSABLE_CONTENT;
        }
        if (ex instanceof PayloadTooLargeException) {
            return HttpStatus.CONTENT_TOO_LARGE;
        }
        if (ex instanceof UnsupportedFormatException) {
            return HttpStatus.UNSUPPORTED_MEDIA_TYPE;
        }
        if (ex instanceof RateLimitedException) {
            return HttpStatus.TOO_MANY_REQUESTS;
        }
        if (ex instanceof NotImplementedYetException) {
            return HttpStatus.NOT_IMPLEMENTED;
        }
        if (ex instanceof UpstreamException.TimedOut) {
            return HttpStatus.GATEWAY_TIMEOUT;
        }
        if (ex instanceof UpstreamException) {
            return HttpStatus.BAD_GATEWAY;
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
