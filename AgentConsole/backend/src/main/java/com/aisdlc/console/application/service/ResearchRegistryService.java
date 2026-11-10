package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;
import com.aisdlc.console.application.port.in.ResearchRegistryUseCase;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.ResearchBridge;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

/**
 * 追蹤來源的用例（API-RP-29；{@link ResearchRegistryUseCase}）。<b>對 {@code console.research_watch_sources} 零寫入</b>：寫入只經 Bridge、恰一次呼叫、不重試；
 * 每個成功的寫入以 {@link AuditTrail#note} 標註（{@code audit_log} 的 {@code entity_type='research_watch_source'}、{@code entity_id=<slug>}；不寫 {@code research_events}：
 * 追蹤來源與 allowlist 一樣是全域資源）。
 */
@Service
public class ResearchRegistryService implements ResearchRegistryUseCase {

    private final ResearchBridge bridge;
    private final AuditTrail audit;

    ResearchRegistryService(ResearchBridge bridge, AuditTrail audit) {
        this.bridge = bridge;
        this.audit = audit;
    }

    @Override
    public List<Map<String, Object>> watchSources() {
        Map<String, Object> body = call(bridge::watchSources);
        List<Map<String, Object>> out = new ArrayList<>();
        if (body.get("items") instanceof List<?> items) {
            for (Object item : items) {
                if (item instanceof Map<?, ?> map) {
                    Map<String, Object> entry = new LinkedHashMap<>();
                    map.forEach((key, value) -> entry.put(String.valueOf(key), value));
                    out.add(entry);
                }
            }
        }
        return out;
    }

    @Override
    public Map<String, Object> addWatchSource(Caller caller, Map<String, Object> request) {
        requireWriteEnabled();
        Map<String, Object> body = new LinkedHashMap<>(ResearchRegistryGates.watchSource(request));
        body.put("added_by", caller.subject());
        Map<String, Object> created = call(() -> bridge.addWatchSource(body));
        audit.note("research.watch_source", "research_watch_source", String.valueOf(created.get("slug")));
        return created;
    }

    @Override
    public Map<String, Object> patchWatchSource(Caller caller, String slug, Map<String, Object> patch) {
        requireWriteEnabled();
        boolean enabled = ResearchInputGates.allowlistPatch(patch);       // 同 allowlist：只准 enabled（布林）一鍵，其餘鍵＝422、條目不變
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("enabled", enabled);
        body.put("disabled_by", caller.subject());
        Map<String, Object> updated = call(() -> bridge.patchWatchSource(slug, body));
        audit.note("research.watch_source", "research_watch_source", updated.get("slug") == null ? slug : updated.get("slug").toString());
        return updated;
    }

    /** 契約 §0.2 第 3 列：backend 沒設研究寫入權杖＝整個寫入面停用，一個請求都不發。 */
    private void requireWriteEnabled() {
        if (!bridge.writeEnabled()) {
            throw new ServiceUnavailableException("backend 沒有設定研究寫入權杖（BRIDGE_RESEARCH_WRITE_TOKEN），研究寫入面已停用",
                    ErrorReasons.RESEARCH_WRITE_DISABLED, Map.of("cause", "bridge_token_unset"));
        }
    }

    /** 恰一次 Bridge 呼叫；Bridge 的 4xx 與明確拒絕的 503 轉成 Console 的領域例外（reason 逐字）。 */
    private static <T> T call(Supplier<T> action) {
        try {
            return action.get();
        } catch (BridgeRejectedException e) {
            throw ResearchBridgeErrors.map(e);
        }
    }
}
