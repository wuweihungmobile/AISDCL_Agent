package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.SiReconcileUseCase;
import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.SiConsoleWriteQueries;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.model.si.SiConsoleWriteSummary;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;

/**
 * Console 稽核列與 SelfImproving 帳本的對帳（TCS-SelfImprovingDecide-P2b W14；{@link SiReconcileUseCase} 載明語意）。
 *
 * <p>對 Bridge <b>永遠只送 GET</b>（{@code siExport}）；對資料庫唯一的寫入是 {@link SiConsoleWriteQueries#fillSubjectId}（回填 obs-add 稽核列的
 * {@code subject_id}，冪等）。Bridge 任何失敗都不拋給呼叫端：回 {@code NOT-EVALUABLE}、{@code items} 照回——稽核列本身永遠讀得到。
 */
@Service
public class SiReconcileService implements SiReconcileUseCase {

    private static final Logger LOG = LoggerFactory.getLogger(SiReconcileService.class);

    /** 每頁筆數與頁數上限（觀察列與事件各自；超限＝{@code scan_cap_exceeded}）。 */
    static final int PAGE_SIZE = 500;
    static final int PAGE_CAP = 20;

    private static final Pattern OBS_ID = Pattern.compile("OBS-SI-[0-9]{3,}");
    /** {@code si_console_writes.subject_id} 的欄寬。 */
    private static final int SUBJECT_MAX = 64;

    private final SiConsoleWriteQueries queries;
    private final AgentBridge bridge;

    public SiReconcileService(SiConsoleWriteQueries queries, AgentBridge bridge) {
        this.queries = queries;
        this.bridge = bridge;
    }

    /** 帳本掃描的結果：哪些 {@code audit_ref} 已入帳、觀察列標記的 ref→新列號、帳本中 carrier 為 console 的項（事件側在前、觀察列側在後、依 ref 去重）。 */
    private record Ledger(Set<String> ingested, Map<String, String> obsIdByRef, Map<String, Orphan> consoleEntries) {
    }

    /** 掃描頁數超過上限，或帳本說還有下一頁卻沒給游標。 */
    private static final class ScanCapExceeded extends RuntimeException {

        private static final long serialVersionUID = 1L;

        ScanCapExceeded() {
            super("帳本頁數超過上限");
        }
    }

    @Override
    public ConsoleWrites consoleWrites(Integer limit) {
        int size = limit == null ? DEFAULT_LIMIT : limit;
        if (size < 1 || size > MAX_LIMIT) {
            throw ValidationException.of("limit", "limit 須為 1～" + MAX_LIMIT + " 的整數");
        }
        Ledger ledger = null;
        String notEvaluable = null;
        try {
            ledger = scan();
        } catch (ScanCapExceeded e) {
            notEvaluable = "scan_cap_exceeded";
        } catch (BridgeRejectedException e) {
            notEvaluable = "si_unavailable";
        } catch (UpstreamException.Unavailable e) {
            notEvaluable = "bridge_unreachable";
        } catch (UpstreamException.TimedOut e) {
            notEvaluable = "bridge_timeout";
        } catch (UpstreamException e) {
            notEvaluable = "si_unavailable";
        }
        int backfilled = 0;
        List<Orphan> orphans = null;
        if (ledger != null) {
            backfilled = backfill(ledger);
            orphans = orphans(ledger);
        }
        // 回填之後才讀列：回應裡的 subjectId 就是填好的值
        List<SiConsoleWriteSummary> rows = queries.findRecent(size + 1);
        boolean truncated = rows.size() > size;
        List<Item> items = new ArrayList<>();
        for (SiConsoleWriteSummary row : rows.subList(0, Math.min(size, rows.size()))) {
            String ref = row.auditRef().toString();
            items.add(new Item(ref, row.kind().wire(), row.user(), row.role(), row.time(), row.subjectId(), row.digest(),
                    row.keyId(), ledger == null ? null : ledger.ingested().contains(ref)));
        }
        Reconcile reconcile = ledger != null ? new Reconcile(STATUS_OK, null, backfilled)
                : new Reconcile(STATUS_NOT_EVALUABLE, notEvaluable, 0);
        return new ConsoleWrites(items, truncated, orphans, reconcile);
    }

    // ── 帳本掃描 ────────────────────────────────────────────────────────────────────────────

    private Ledger scan() {
        Set<String> ingested = new HashSet<>();
        Map<String, String> obsIdByRef = new LinkedHashMap<>();
        Map<String, Orphan> consoleEntries = new LinkedHashMap<>();
        for (Map<String, Object> event : pages("events")) {
            String kind = text(event.get("kind"));
            String ref = text(event.get("audit_ref"));
            if (ref == null || ref.isBlank() || kind == null) {
                continue;
            }
            String wire = switch (kind) {
                case "dec" -> "decide";
                case "obs.add" -> "obs-add";
                case "obs.close" -> "obs-close";
                default -> null;
            };
            if (wire == null) {
                continue;
            }
            ingested.add(ref);
            if ("console".equals(event.get("carrier"))) {
                String subject = "decide".equals(wire) ? firstText(event.get("prop"), event.get("run")) : text(event.get("obs"));
                consoleEntries.putIfAbsent(ref, new Orphan(ref, wire, subject));
            }
        }
        for (Map<String, Object> row : pages("observations")) {
            if (!(row.get("marks_kv") instanceof Map<?, ?> marks)) {
                continue;                                   // 壞列沒有 marks_kv
            }
            String ref = text(marks.get("audit_ref"));
            if (ref == null || ref.isBlank()) {
                continue;
            }
            ingested.add(ref);
            String id = text(row.get("id"));
            if (id != null) {
                obsIdByRef.putIfAbsent(ref, id);
            }
            if ("console".equals(marks.get("carrier"))) {
                consoleEntries.putIfAbsent(ref, new Orphan(ref, "obs-add", id));
            }
        }
        return new Ledger(ingested, obsIdByRef, consoleEntries);
    }

    /** 一個 kind 的全部項目：依游標分頁取、每頁 {@value #PAGE_SIZE} 筆、上限 {@value #PAGE_CAP} 頁。 */
    private List<Map<String, Object>> pages(String kind) {
        List<Map<String, Object>> all = new ArrayList<>();
        Integer since = null;
        for (int page = 0; page < PAGE_CAP; page++) {
            Map<String, Object> raw = bridge.siExport(kind, since, PAGE_SIZE, null).raw();
            if (raw.get("items") instanceof List<?> items) {
                for (Object item : items) {
                    if (item instanceof Map<?, ?> map) {
                        all.add(stringKeyed(map));
                    }
                }
            }
            if (!Boolean.TRUE.equals(raw.get("truncated"))) {
                return all;
            }
            if (!(raw.get("next_since") instanceof Number next)) {
                throw new ScanCapExceeded();                // 說還有下一頁卻沒有游標：無從確認帳本是否讀完
            }
            since = next.intValue();
        }
        throw new ScanCapExceeded();
    }

    private static Map<String, Object> stringKeyed(Map<?, ?> map) {
        Map<String, Object> out = new LinkedHashMap<>();
        map.forEach((key, value) -> out.put(String.valueOf(key), value));
        return out;
    }

    // ── 回填與 orphan ─────────────────────────────────────────────────────────────────────────

    /** obs-add 稽核列的 {@code subject_id} 由 NULL 填入帳本的新列號（冪等）；只填格式合格的列號。 */
    private int backfill(Ledger ledger) {
        int filled = 0;
        for (UUID ref : queries.findObsAddRefsWithoutSubject()) {
            String obsId = ledger.obsIdByRef().get(ref.toString());
            if (obsId != null && obsId.length() <= SUBJECT_MAX && OBS_ID.matcher(obsId).matches()) {
                filled += queries.fillSubjectId(ref, obsId);
            }
        }
        if (filled > 0) {
            LOG.info("SelfImproving 對帳：回填 {} 筆 obs-add 稽核列的 subject_id", filled);
        }
        return filled;
    }

    /** 帳本有 carrier 為 console 的項、表內卻沒有對應列。 */
    private List<Orphan> orphans(Ledger ledger) {
        Set<UUID> candidates = new HashSet<>();
        for (String ref : ledger.consoleEntries().keySet()) {
            uuidOrNull(ref).ifPresent(candidates::add);
        }
        Set<UUID> existing = queries.findExistingAuditRefs(candidates);
        List<Orphan> orphans = new ArrayList<>();
        for (Orphan entry : ledger.consoleEntries().values()) {
            if (uuidOrNull(entry.auditRef()).map(existing::contains).orElse(false)) {
                continue;
            }
            orphans.add(entry);
        }
        return orphans;
    }

    private static Optional<UUID> uuidOrNull(String ref) {
        try {
            return Optional.of(UUID.fromString(ref));
        } catch (IllegalArgumentException e) {
            return Optional.empty();
        }
    }

    private static String text(Object value) {
        return value instanceof String s ? s : null;
    }

    private static String firstText(Object first, Object second) {
        String a = text(first);
        return a != null ? a : text(second);
    }
}
