package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.application.port.out.AuditTrail;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import tools.jackson.databind.json.JsonMapper;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * {@link AuditTrail} 的實作：用例把語意標註（{@code action}、{@code entity}）放在<b>目前請求的 request attribute</b>，
 * 由 {@link AuditLoggingFilter} 在請求結束時併入審計日誌行與 {@code audit_log} 列（契約 §0.4 第 5 點）。
 * 沒有目前請求（非 Web 執行緒）時 {@link #note} 靜默略過。
 */
@Component
class RequestAuditTrail implements AuditTrail {

    static final String ATTR_ACTION = "console.audit.action";
    static final String ATTR_ENTITY_TYPE = "console.audit.entityType";
    static final String ATTR_ENTITY_ID = "console.audit.entityId";
    static final String ATTR_EXTRA = "console.audit.extra";

    private static final Logger AUDIT = LoggerFactory.getLogger("audit");
    private static final JsonMapper JSON = JsonMapper.builder().build();

    private final AuditLogWriter writer;

    RequestAuditTrail(AuditLogWriter writer) {
        this.writer = writer;
    }

    @Override
    public void note(String action, String entityType, String entityId) {
        note(action, entityType, entityId, Map.of());
    }

    @Override
    public void note(String action, String entityType, String entityId, Map<String, Object> extra) {
        if (RequestContextHolder.getRequestAttributes() instanceof ServletRequestAttributes attributes) {
            attributes.setAttribute(ATTR_ACTION, action, RequestAttributes.SCOPE_REQUEST);
            attributes.setAttribute(ATTR_ENTITY_TYPE, entityType, RequestAttributes.SCOPE_REQUEST);
            if (entityId != null) {
                attributes.setAttribute(ATTR_ENTITY_ID, entityId, RequestAttributes.SCOPE_REQUEST);
            }
            if (extra != null && !extra.isEmpty()) {
                attributes.setAttribute(ATTR_EXTRA, extra, RequestAttributes.SCOPE_REQUEST);
            }
        }
    }

    /** 獨立事件：輸出一行審計日誌並落庫（{@code GET /settings?reveal=true} 這類「讀取也要留痕」的動作）。 */
    @Override
    public void event(String action, Map<String, Object> details) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        String subject = authentication == null ? null : authentication.getName();
        Map<String, Object> entry = new LinkedHashMap<>();
        entry.put("event", "audit");
        entry.put("action", action);
        entry.put("subject", subject);
        if (details != null && !details.isEmpty()) {
            entry.put("detail", details);
        }
        entry.put("traceId", MDC.get("traceId"));
        AUDIT.info(JSON.writeValueAsString(entry));

        if (RequestContextHolder.getRequestAttributes() instanceof ServletRequestAttributes attributes) {
            String role = AuditLoggingFilter.roleOf(authentication);
            writer.write(new AuditLogWriter.Entry(subject, role, attributes.getRequest().getMethod(),
                    attributes.getRequest().getRequestURI(), action.substring(0, Math.max(0, action.indexOf('.'))),
                    null, 200, MDC.get("traceId")));
        }
    }
}
