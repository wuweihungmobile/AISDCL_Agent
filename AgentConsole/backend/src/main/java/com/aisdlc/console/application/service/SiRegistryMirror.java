package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.SiMirrorUseCase;
import com.aisdlc.console.domain.exception.UpstreamException;
import org.springframework.stereotype.Component;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * SelfImproving 鏡像中「研究來源登記」的讀取（研究來源單一化 W-R6 序 5、W-R7）：最新已入帳的登記（{@code status.items[0].research_registry}）、已入帳的 {@code audit_ref} 集合
 * （{@code research.registry} 事件，沿 {@code SiReconcileService} 的分頁掃描與上限）與抓取上限（{@code status.items[0].research_fetch_max}）。
 *
 * <p>只經 {@link SiMirrorUseCase}（唯讀鏡像；本類別不直接呼叫 Bridge）。<b>讀不到一律拋 {@link Unreadable}</b>（帶 {@code cause}）——絕不把「讀不到」當成「從未同步」：
 * {@code research_registry} 鍵缺席（根層尚未升版）也是讀不到，只有值為明確的 {@code null} 才是「從未同步」。
 */
@Component
class SiRegistryMirror {

    /** 讀不到鏡像；{@code cause} 取值同狀態端點的 {@code unknownCause}：{@code scan_cap_exceeded}｜{@code si_unavailable}｜{@code bridge_unreachable}｜{@code bridge_timeout}。 */
    static final class Unreadable extends RuntimeException {

        private static final long serialVersionUID = 1L;

        private final String cause;

        Unreadable(String cause, String message) {
            super(message);
            this.cause = cause;
        }

        String cause() {
            return cause;
        }
    }

    /** 最新已入帳的登記：{@code auditRef}、{@code registrySha256}。 */
    record Ingested(String auditRef, String registrySha256) {
    }

    /**
     * @param latest         最新已入帳的登記；{@code null}＝從未同步（鏡像明確回 null）
     * @param ingestedRefs   {@code research.registry} 事件的 {@code audit_ref} 集合（已入帳）
     * @param researchFetchMax {@code status.items[0].research_fetch_max}：只有正整數才轉，其餘 {@code null}
     */
    record Mirror(Ingested latest, Set<String> ingestedRefs, Integer researchFetchMax) {
    }

    private final SiMirrorUseCase mirror;

    SiRegistryMirror(SiMirrorUseCase mirror) {
        this.mirror = mirror;
    }

    Mirror read() {
        try {
            Map<String, Object> first = firstStatusItem(mirror.status().raw());
            return new Mirror(latestOf(first), ingestedRefs(), fetchMaxOf(first.get("research_fetch_max")));
        } catch (Unreadable e) {
            throw e;
        } catch (UpstreamException.Unavailable e) {
            throw new Unreadable("bridge_unreachable", "連不上 Engine Bridge");
        } catch (UpstreamException.TimedOut e) {
            throw new Unreadable("bridge_timeout", "讀取 SelfImproving 鏡像逾時");
        } catch (RuntimeException e) {
            // 含 si_unavailable（Bridge 明確回報資料面不可用）、其他 4xx／5xx 與本文形狀不符：一律「讀不到」，不降級
            throw new Unreadable("si_unavailable", "SelfImproving 鏡像不可用：" + e.getClass().getSimpleName());
        }
    }

    private static Map<String, Object> firstStatusItem(Map<String, Object> raw) {
        if (raw.get("items") instanceof List<?> items && !items.isEmpty() && items.get(0) instanceof Map<?, ?> map) {
            Map<String, Object> out = new java.util.LinkedHashMap<>();
            map.forEach((key, value) -> out.put(String.valueOf(key), value));
            return out;
        }
        throw new Unreadable("si_unavailable", "status.items[0] 缺席或不是物件");
    }

    /** {@code research_registry}：鍵缺席＝讀不到；{@code null}＝從未同步；物件＝取 {@code audit_ref} 與 {@code registry_sha256}（缺一＝讀不到）。 */
    private static Ingested latestOf(Map<String, Object> first) {
        if (!first.containsKey("research_registry")) {
            throw new Unreadable("si_unavailable", "status.items[0].research_registry 缺鍵（根層尚未升版）");
        }
        Object value = first.get("research_registry");
        if (value == null) {
            return null;
        }
        if (value instanceof Map<?, ?> map && map.get("audit_ref") instanceof String ref && map.get("registry_sha256") instanceof String sha) {
            return new Ingested(ref, sha);
        }
        throw new Unreadable("si_unavailable", "status.items[0].research_registry 不是 {audit_ref, registry_sha256} 物件");
    }

    private static Integer fetchMaxOf(Object value) {
        if (value instanceof Integer || value instanceof Long || value instanceof Short || value instanceof Byte) {
            long number = ((Number) value).longValue();
            if (number >= 1 && number <= Integer.MAX_VALUE) {
                return (int) number;
            }
        }
        return null;
    }

    /** 全部 {@code research.registry} 事件的 {@code audit_ref}：依游標分頁、每頁 {@value SiReconcileService#PAGE_SIZE} 筆、上限 {@value SiReconcileService#PAGE_CAP} 頁。 */
    private Set<String> ingestedRefs() {
        Set<String> refs = new HashSet<>();
        Integer since = null;
        for (int page = 0; page < SiReconcileService.PAGE_CAP; page++) {
            Map<String, Object> raw = mirror.events(since, SiReconcileService.PAGE_SIZE).raw();
            if (raw.get("items") instanceof List<?> items) {
                for (Object item : items) {
                    if (item instanceof Map<?, ?> event && "research.registry".equals(event.get("kind")) && event.get("audit_ref") instanceof String ref
                            && !ref.isBlank()) {
                        refs.add(ref);
                    }
                }
            }
            if (!Boolean.TRUE.equals(raw.get("truncated"))) {
                return refs;
            }
            if (!(raw.get("next_since") instanceof Number next)) {
                throw new Unreadable("scan_cap_exceeded", "帳本說還有下一頁卻沒有游標");
            }
            since = next.intValue();
        }
        throw new Unreadable("scan_cap_exceeded", "帳本頁數超過上限");
    }
}
