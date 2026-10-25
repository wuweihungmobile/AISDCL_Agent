package com.aisdlc.minibridge;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static com.aisdlc.minibridge.MiniBridge.JSON;
import static com.aisdlc.minibridge.MiniBridge.map;

/** 迷你 Bridge 的 HTTP 面（路徑、狀態碼與錯誤封包 {@code {code,reason,…}} 對照 {@code routers/autoclaude.py}）。 */
@RestController
class MiniBridgeController {

    private final MiniBridge bridge;

    MiniBridgeController(MiniBridge bridge) {
        this.bridge = bridge;
    }

    private static ResponseEntity<Object> error(int status, String reason, Object... extra) {
        Map<String, Object> body = map("code", status, "reason", reason);
        for (int i = 0; i < extra.length; i += 2) {
            body.put((String) extra[i], extra[i + 1]);
        }
        return ResponseEntity.status(status).contentType(MediaType.APPLICATION_JSON).body(body);
    }

    /** 由 {@link #stream} 這類回傳 {@code SseEmitter} 的端點丟出，轉成與其他端點相同的錯誤封包。 */
    static final class MiniError extends RuntimeException {

        private static final long serialVersionUID = 1L;

        private final int status;
        private final transient Map<String, Object> body;

        MiniError(int status, Map<String, Object> body) {
            super("mini bridge error " + status);
            this.status = status;
            this.body = body;
        }
    }

    @org.springframework.web.bind.annotation.ExceptionHandler(MiniError.class)
    ResponseEntity<Object> onError(MiniError e) {
        return ResponseEntity.status(e.status).contentType(MediaType.APPLICATION_JSON).body(e.body);
    }

    private ResponseEntity<Object> injected(String route) {
        MiniBridge.Injected next = bridge.takeInjected(route);
        if (next == null) {
            return null;
        }
        return ResponseEntity.status(next.status()).contentType(MediaType.APPLICATION_JSON).body(next.body());
    }

    private static Optional<UUID> parse(String raw) {
        try {
            return Optional.of(UUID.fromString(raw));
        } catch (IllegalArgumentException e) {
            return Optional.empty();
        }
    }

    @GetMapping("/health")
    Map<String, Object> health() {
        bridge.record("GET /health");
        return map("status", "ok", "bridge_instance", bridge.bridgeInstance);
    }

    /**
     * 深度探針（契約 §3.1.1；對照 {@code app/health.py} 的 {@code deep_health}）：五項檢查，前四項任一失敗＝503 {@code degraded}
     * 並附頂層 {@code reason}；第五項 {@code sdd} 只當資訊，失敗時整體仍是 200（主控裁決 Q4）。
     */
    @GetMapping("/health/deep")
    ResponseEntity<Object> deepHealth() {
        bridge.record("GET /health/deep");
        ResponseEntity<Object> forced = injected("deepHealth");
        if (forced != null) {
            return forced;
        }
        Map<String, Object> checks = new java.util.LinkedHashMap<>();
        checks.put("git", map("ok", true, "version", "git version 2.39.5"));
        checks.put("autoclaude", map("ok", true, "version", "mini"));
        checks.put("workspace", map("ok", true));
        checks.put("db", map("ok", null));
        checks.put("sdd", map("ok", true, "latest", bridge.sdd.latest));
        switch (bridge.deepHealthMode) {
            case DEGRADED -> {
                checks.put("git", map("ok", false, "reason", "找不到 git 執行檔"));
                return ResponseEntity.status(503).contentType(MediaType.APPLICATION_JSON)
                        .body(map("status", "degraded", "reason", "git: 找不到 git 執行檔", "checks", checks));
            }
            case SDD_NOT_OK -> checks.put("sdd", map("ok", false, "latest", null, "reason", "SDD_ROOT 不是目錄：sdd"));
            default -> {
                // HEALTHY：五項都通過
            }
        }
        return ResponseEntity.ok(map("status", "ok", "checks", checks));
    }

    // ── /sdd/*：AISDLC_SDD 唯讀查詢（契約 §3.1.3；對照 routers/sdd.py）─────────────────────────────

    private ResponseEntity<Object> sddUnavailable() {
        return error(503, "sdd_unavailable", "detail", "找不到 AISDLC_SDD 目錄；請設定 SDD_ROOT（Docker 需掛載）");
    }

    private void sddDelay() {
        long delay = bridge.sdd.delayMillis;
        if (delay > 0) {
            try {
                Thread.sleep(delay);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
    }

    @GetMapping("/sdd/version")
    ResponseEntity<Object> sddVersion() {
        bridge.record("GET /sdd/version");
        ResponseEntity<Object> forced = injected("sddVersion");
        if (forced != null) {
            return forced;
        }
        sddDelay();
        if (bridge.sdd.unavailable) {
            return sddUnavailable();
        }
        return ResponseEntity.ok(map("latest", bridge.sdd.latest, "root", bridge.sdd.root));
    }

    /** 帶 {@code root} 的讀取：不合 allowlist／不存在的根 → 422 {@code sanitization_failed}（契約 §3.1.4 (a)）；沒有問題回 null。 */
    private ResponseEntity<Object> rootGate(String root) {
        if (root != null && bridge.sdd.rejectedRoots.contains(root)) {
            return error(422, "sanitization_failed", "violations", List.of(map("field", "root", "rule",
                    "outside_allowlist", "message", "專案根不在允許的根目錄內")));
        }
        return null;
    }

    @GetMapping("/sdd/fsm")
    ResponseEntity<Object> sddFsmList(@RequestParam(required = false) String root) {
        bridge.record("GET /sdd/fsm");
        bridge.sdd.rootsSeen.add(new MiniBridge.Sdd.RootSeen("GET /sdd/fsm", root));
        ResponseEntity<Object> forced = injected("sddFsmList");
        if (forced != null) {
            return forced;
        }
        sddDelay();
        if (bridge.sdd.unavailable) {
            return sddUnavailable();
        }
        ResponseEntity<Object> rejected = rootGate(root);
        if (rejected != null) {
            return rejected;
        }
        boolean emptyRoot = root != null && bridge.sdd.emptyRoots.contains(root);
        return ResponseEntity.ok(map("root", bridge.sdd.latest,
                "projects", emptyRoot ? List.of() : List.copyOf(bridge.sdd.projects),
                "errors", emptyRoot ? List.of() : List.copyOf(bridge.sdd.errors)));
    }

    @GetMapping("/sdd/fsm/{project}")
    ResponseEntity<Object> sddFsm(@PathVariable String project, @RequestParam(required = false) String root) {
        bridge.record("GET /sdd/fsm/" + project);
        bridge.sdd.rootsSeen.add(new MiniBridge.Sdd.RootSeen("GET /sdd/fsm/" + project, root));
        ResponseEntity<Object> forced = injected("sddFsm");
        if (forced != null) {
            return forced;
        }
        sddDelay();
        if (bridge.sdd.unavailable) {
            return sddUnavailable();
        }
        ResponseEntity<Object> rejected = rootGate(root);
        if (rejected != null) {
            return rejected;
        }
        // v1.5：專案名先過淨化鏡像，傳原名與傳標準鍵等價（契約 §3.1.4 (b)）
        String key = MiniBridge.canonical(project);
        boolean emptyRoot = root != null && bridge.sdd.emptyRoots.contains(root);
        boolean unreadable = !emptyRoot && bridge.sdd.unreadable.contains(key);
        Map<String, Object> state = emptyRoot ? null : bridge.sdd.states.get(key);
        if (unreadable) {
            return error(422, "fsm_state_unreadable", "detail", "while scanning a simple key");
        }
        if (state == null) {
            return error(404, "fsm_not_found", "project", project);
        }
        return ResponseEntity.ok(state);
    }

    // ── /si/*：SelfImproving 唯讀鏡像（TCS-SelfImprovingMirror-P1b §5.3；對照 routers/si.py）─────────────────────

    /**
     * 六個路由共用的回應邏輯。記錄：{@code MINI.requests()} 記 {@code GET /si/<路徑>}（路徑為解碼後、不含查詢字串）；{@code si.seen} 記
     * <b>原始</b> URI 與查詢字串。失敗旋鈕的優先序：逾時延遲 → 503 → 500 → 純文字 → 陣列 → 422 → 404（單筆）→ 回放 {@code si.payloads}。
     */
    private ResponseEntity<Object> si(HttpServletRequest http, String logged, String payloadKey, String id) {
        bridge.record("GET " + logged);
        bridge.si.seen.add(new MiniBridge.Si.Seen(http.getRequestURI(), http.getQueryString()));
        long delay = bridge.si.delayMillis;
        if (delay > 0) {
            try {
                Thread.sleep(delay);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        if (!bridge.si.unavailable.isEmpty()) {
            return error(503, "si_unavailable", "cause", bridge.si.unavailable.get("cause"), "detail",
                    bridge.si.unavailable.get("detail"));
        }
        if (bridge.si.status500) {
            return error(500, "internal_error");
        }
        if (bridge.si.garbage != null) {
            return ResponseEntity.ok().contentType(MediaType.TEXT_PLAIN).body(bridge.si.garbage);
        }
        if (bridge.si.arrayBody) {
            return ResponseEntity.ok().contentType(MediaType.APPLICATION_JSON).body(List.of(1, 2, 3));
        }
        if (!bridge.si.invalid.isEmpty()) {
            return error(422, "invalid_request", "violations", bridge.si.invalid);
        }
        Map<String, Object> payload = id != null && bridge.si.notFoundIds.contains(id) ? null
                : bridge.si.payloads.get(payloadKey);
        if (payload == null && id != null) {
            return error(404, "si_not_found", "id", id);
        }
        return payload == null ? error(404, "not_found") : ResponseEntity.ok(payload);
    }

    @GetMapping("/si/status")
    ResponseEntity<Object> siStatus(HttpServletRequest http) {
        return si(http, "/si/status", "status", null);
    }

    @GetMapping("/si/observations")
    ResponseEntity<Object> siObservations(HttpServletRequest http) {
        return si(http, "/si/observations", "observations", null);
    }

    @GetMapping("/si/events")
    ResponseEntity<Object> siEvents(HttpServletRequest http) {
        return si(http, "/si/events", "events", null);
    }

    @GetMapping("/si/proposals")
    ResponseEntity<Object> siProposals(HttpServletRequest http) {
        return si(http, "/si/proposals", "proposals", null);
    }

    @GetMapping("/si/proposals/{id}")
    ResponseEntity<Object> siProposal(HttpServletRequest http, @PathVariable String id) {
        return si(http, "/si/proposals/" + id, "proposal:" + id, id);
    }

    @GetMapping("/si/runs")
    ResponseEntity<Object> siRuns(HttpServletRequest http) {
        return si(http, "/si/runs", "runs", null);
    }

    // ── /si/*：P2b 稽核檔落地與預檢（TCS-SelfImprovingDecide-P2b §5.4；對照 routers/si.py 的三個寫入 POST 與 :validate）────────

    private static boolean looksLikeJson(String body) {
        String t = body.stripLeading();
        return t.startsWith("{") || t.startsWith("[");
    }

    private static ResponseEntity<Object> reply(MiniBridge.Si.WriteReply reply) {
        MediaType type = looksLikeJson(reply.body()) ? MediaType.APPLICATION_JSON : MediaType.TEXT_PLAIN;
        return ResponseEntity.status(reply.status()).contentType(type).body(reply.body());
    }

    /** 請求本文裡的 {@code audit_ref}（預設成功回應原樣回報它）；本文不是 JSON 物件或沒有該鍵時為 null。 */
    private static String auditRefOf(byte[] raw) {
        try {
            Object parsed = JSON.readValue(raw, Object.class);
            return parsed instanceof Map<?, ?> map && map.get("audit_ref") instanceof String ref ? ref : null;
        } catch (RuntimeException e) {
            return null;
        }
    }

    /**
     * 寫入端點的共同邏輯：記錄（{@code MINI.requests()} 記 {@code POST /si/<解碼後路徑>}；{@code si.writes} 記原始路徑、權杖標頭與本文位元組）→
     * 回呼 {@code si.onWrite}（收到請求的當下）→ 延遲 → 回應（{@code si.writeReply} 覆蓋，否則 201 回報請求本文的 {@code audit_ref}）。
     * 迷你 Bridge 不驗權杖（真 Bridge 的 403／503 以 {@code si.writeReply} 模擬），只忠實記下 backend 附了什麼。
     */
    private ResponseEntity<Object> siWrite(HttpServletRequest http, String logged, String token, byte[] raw, boolean validate) {
        bridge.record("POST " + logged);
        bridge.recordToken("POST " + logged, token);
        MiniBridge.Si.Write write = new MiniBridge.Si.Write(http.getRequestURI(), token, raw);
        bridge.si.writes.add(write);
        java.util.function.Consumer<MiniBridge.Si.Write> hook = bridge.si.onWrite;
        if (hook != null) {
            hook.accept(write);
        }
        long delay = bridge.si.writeDelayMillis;
        if (delay > 0) {
            try {
                Thread.sleep(delay);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        if (validate) {
            MiniBridge.Si.WriteReply failure = bridge.si.validateFailure;
            return failure != null ? reply(failure) : ResponseEntity.ok(bridge.si.validateReply);
        }
        MiniBridge.Si.WriteReply custom = bridge.si.writeReply;
        if (custom != null) {
            return reply(custom);
        }
        String ref = auditRefOf(raw);
        Map<String, Object> ack = map("audit_ref", ref, "stored", true);
        return ResponseEntity.status(201).contentType(MediaType.APPLICATION_JSON).body(ack);
    }

    @PostMapping("/si/proposals/{idAction}")
    ResponseEntity<Object> siDecide(HttpServletRequest http, @PathVariable String idAction, @RequestBody byte[] raw,
                                    @RequestHeader(value = "X-Bridge-Token", required = false) String token) {
        return idAction.endsWith(":decide") ? siWrite(http, "/si/proposals/" + idAction, token, raw, false)
                : error(404, "not_found");
    }

    @PostMapping("/si/observations")
    ResponseEntity<Object> siObservationAdd(HttpServletRequest http, @RequestBody byte[] raw,
                                            @RequestHeader(value = "X-Bridge-Token", required = false) String token) {
        return siWrite(http, "/si/observations", token, raw, false);
    }

    @PostMapping("/si/observations/{idAction}")
    ResponseEntity<Object> siObservationClose(HttpServletRequest http, @PathVariable String idAction, @RequestBody byte[] raw,
                                              @RequestHeader(value = "X-Bridge-Token", required = false) String token) {
        return idAction.endsWith(":close") ? siWrite(http, "/si/observations/" + idAction, token, raw, false)
                : error(404, "not_found");
    }

    @PostMapping("/si/{segment}")
    ResponseEntity<Object> siValidate(HttpServletRequest http, @PathVariable String segment, @RequestBody byte[] raw,
                                      @RequestHeader(value = "X-Bridge-Token", required = false) String token) {
        return "observations:validate".equals(segment) ? siWrite(http, "/si/observations:validate", token, raw, true)
                : error(404, "not_found");
    }

    // ── 寫入面（契約 §3.1.4 (d)、共通規則 2）：權杖、:freeze、RTM ──────────────────────────────────

    /**
     * 權杖閘（共通規則 2）：Bridge 沒設權杖 → 503 {@code sdd_write_disabled}；標頭缺漏或不符 → 403 {@code sdd_write_forbidden}
     * （缺與錯同一個 reason）；通過回 null。
     */
    private ResponseEntity<Object> tokenGate(String token) {
        String expected = bridge.sdd.writeToken;
        if (expected == null) {
            return error(503, "sdd_write_disabled", "detail", "Bridge 沒有設定 BRIDGE_SDD_WRITE_TOKEN：SDD 寫入面停用");
        }
        if (token == null || !expected.equals(token)) {
            return error(403, "sdd_write_forbidden");
        }
        return null;
    }

    private static boolean isSddRun(MiniRun run) {
        return run.request.get("sdd") != null;
    }

    private static ResponseEntity<Object> invalidArgument(String detail) {
        return error(422, "sdd_invalid_argument", "detail", detail);
    }

    /** {@code POST /sdd/fsm/{project}:freeze}：檢查順序同契約（本文格式 → 權杖 → 清理 → root → 專案 → docs → 前置狀態 → 摘要 → 寫入）。 */
    @PostMapping("/sdd/fsm/{projectAction}")
    @SuppressWarnings("unchecked")
    ResponseEntity<Object> sddFreeze(@PathVariable String projectAction, @RequestBody Map<String, Object> body,
                                     @RequestHeader(value = "X-Bridge-Token", required = false) String token) {
        bridge.record("POST /sdd/fsm/" + projectAction);
        int colon = projectAction.lastIndexOf(':');
        if (colon < 0 || !"freeze".equals(projectAction.substring(colon + 1))) {
            return error(404, "not_found");
        }
        String project = projectAction.substring(0, colon);
        bridge.sdd.freezes.add(new MiniBridge.Sdd.Freeze(project, token, MiniBridge.copy(body)));
        ResponseEntity<Object> denied = tokenGate(token);
        if (denied != null) {
            return denied;
        }
        ResponseEntity<Object> forced = injected("freeze");
        if (forced != null) {
            return forced;
        }
        sddDelay();
        String approver = (String) body.get("approver");
        String reason = (String) body.get("reason");
        if (approver == null || approver.isBlank() || approver.length() > 100 || approver.contains(";")) {
            return invalidArgument("approver 須為 1～100 字元且不含 ;");
        }
        if (reason == null || reason.strip().isEmpty() || reason.strip().length() > 500) {
            return invalidArgument("reason 須為 1～500 字元");
        }
        String root = (String) body.get("root");
        ResponseEntity<Object> rejected = rootGate(root);
        if (rejected != null) {
            return rejected;
        }
        String key = MiniBridge.canonical(project);
        Map<String, Object> state = bridge.sdd.states.get(key);
        if (state == null) {
            return error(404, "fsm_not_found", "project", project);
        }
        if (bridge.sdd.unreadable.contains(key)) {
            return error(422, "fsm_state_unreadable", "detail", "while scanning a simple key");
        }
        List<String> docs = (List<String>) body.get("docs");
        ResponseEntity<Object> badDocs = checkDocs(docs);
        if (badDocs != null) {
            return badDocs;
        }
        synchronized (state) {
            if (!"HUMAN_PENDING".equals(state.get("current_state"))) {
                return error(409, "fsm_state_conflict", "detail", map("current_state", state.get("current_state"),
                        "expected_state", "HUMAN_PENDING"));
            }
            Map<String, Object> expected = (Map<String, Object>) body.get("expected_digests");
            if (expected != null) {
                for (Map.Entry<String, Object> entry : expected.entrySet()) {
                    if (!docs.contains(entry.getKey())) {
                        return error(422, "sanitization_failed", "violations", List.of(map("field", "expected_digests",
                                "rule", "not_in_docs", "message", entry.getKey())));
                    }
                    String current = currentDigest(entry.getKey());
                    if (!current.equals(entry.getValue())) {
                        return error(409, "spec_digest_changed", "detail", map("pair", "expected_vs_file", "doc",
                                entry.getKey(), "expected_digest", entry.getValue(), "current_digest", current));
                    }
                }
            }
            return ResponseEntity.ok(freezeState(state, body, docs, approver, reason, key));
        }
    }

    private String currentDigest(String doc) {
        return bridge.sdd.docDigests.getOrDefault(doc, MiniBridge.digestOf(doc));
    }

    private ResponseEntity<Object> checkDocs(List<String> docs) {
        if (docs == null || docs.isEmpty() || docs.size() > 20) {
            return error(422, "invalid_request", "violations", List.of(map("field", "docs", "rule", "size", "message",
                    "docs 須為 1～20 項")));
        }
        List<Map<String, Object>> violations = new java.util.ArrayList<>();
        java.util.Set<String> seen = new java.util.HashSet<>();
        for (int i = 0; i < docs.size(); i++) {
            String doc = docs.get(i);
            String rule = null;
            if (doc == null || doc.isBlank()) {
                rule = "invalid";
            } else if (doc.startsWith("/") || doc.matches("^[A-Za-z]:.*") || doc.startsWith("\\")) {
                rule = "absolute";
            } else if (java.util.Arrays.asList(doc.split("[/\\\\]")).contains("..")) {
                rule = "contains_dotdot";
            } else if (!seen.add(doc)) {
                rule = "duplicate";
            } else if (bridge.sdd.missingDocs.contains(doc)) {
                rule = "not_found";
            }
            if (rule != null) {
                violations.add(map("field", "docs[" + i + "]", "rule", rule, "message", String.valueOf(doc)));
            }
        }
        if (violations.isEmpty() && docs.stream().noneMatch(MiniBridgeController::isTcs)) {
            violations.add(map("field", "docs", "rule", "missing_tcs", "message", "docs 不含 TCS 規格檔"));
        }
        return violations.isEmpty() ? null : error(422, "sanitization_failed", "violations", violations);
    }

    private static boolean isTcs(String doc) {
        String name = doc.substring(doc.lastIndexOf('/') + 1).toUpperCase(java.util.Locale.ROOT);
        return name.startsWith("TEST-CONTRACT-SPEC-") || name.startsWith("TCS-");
    }

    /** 凍結成功的狀態變化（契約 §3.1.4 (d)「FSM 側的效果」）與回應（同 GET 加 {@code stage}、{@code spec_doc_digests}）。 */
    @SuppressWarnings("unchecked")
    private Map<String, Object> freezeState(Map<String, Object> state, Map<String, Object> body, List<String> docs,
                                            String approver, String reason, String key) {
        List<Map<String, Object>> stages = new java.util.ArrayList<>((List<Map<String, Object>>) state.get("frozen_stages"));
        String stage = body.get("stage") instanceof String s && !s.isBlank() ? s : "Stage-" + (stages.size() + 1);
        Map<String, Object> digests = new java.util.LinkedHashMap<>();
        docs.forEach(doc -> digests.put(doc, currentDigest(doc)));
        String now = MiniBridge.now();
        stages.add(map("stage", stage, "frozen_at", now, "spec_docs", List.copyOf(docs), "spec_doc_digests", digests,
                "approved_by", approver));
        List<Map<String, Object>> trace = new java.util.ArrayList<>((List<Map<String, Object>>) state.get("decision_trace"));
        trace.add(map("ts", now, "from", "HUMAN_PENDING", "to", "SPEC_FROZEN", "reason",
                "console-freeze approver=" + approver + "; reason=" + reason.strip(), "spec_refs", List.copyOf(docs),
                "agents_consulted", List.of(), "trigger", "spec_frozen"));
        state.put("frozen_stages", stages);
        state.put("decision_trace", trace.subList(Math.max(0, trace.size() - 5), trace.size()));
        state.put("current_state", "SPEC_FROZEN");
        state.put("updated_at", now);
        state.put("phase", MiniBridge.phaseOf("SPEC_FROZEN"));
        state.put("human_pending", map("count", 0, "items", List.of()));
        bridge.sdd.projects.stream().filter(p -> key.equals(p.get("project"))).findFirst().ifPresent(p -> {
            p.put("current_state", "SPEC_FROZEN");
            p.put("updated_at", now);
        });
        Map<String, Object> out = new java.util.LinkedHashMap<>(state);
        out.put("stage", stage);
        out.put("spec_doc_digests", digests);
        return out;
    }

    /** {@code GET /autoclaude/runs/{id}/rtm}（契約 §3.1.4 (f)；唯讀、不需權杖）。 */
    @GetMapping("/autoclaude/runs/{id}/rtm")
    ResponseEntity<Object> rtm(@PathVariable String id) {
        bridge.record("GET /autoclaude/runs/" + id + "/rtm");
        ResponseEntity<Object> forced = injected("rtm");
        if (forced != null) {
            return forced;
        }
        MiniRun run = parse(id).map(bridge.runs()::get).orElse(null);
        if (run == null) {
            return error(404, "run_not_found", "run_id", id);
        }
        if (bridge.sdd.rtmUnreadable.contains(run.id)) {
            return error(422, "rtm_unreadable", "detail", "RTM 報告缺 summary");
        }
        Map<String, Object> report = bridge.sdd.rtmReports.get(run.id);
        if (report == null) {
            return error(404, "rtm_not_found", "run_id", id);
        }
        Map<String, Object> out = new java.util.LinkedHashMap<>(report);
        out.put("advisory", true);
        return ResponseEntity.ok(out);
    }

    @PostMapping("/autoclaude/runs")
    @SuppressWarnings("unchecked")
    ResponseEntity<Object> create(@RequestBody Map<String, Object> body,
                                  @RequestHeader(value = "X-Bridge-Token", required = false) String token) {
        bridge.record("POST /autoclaude/runs");
        boolean sdd = body.get("sdd") != null;
        if (sdd) {
            // 共通規則 2：帶 sdd 的建立要權杖，檢查先於一切（沒有 sdd 的請求行為與 v1.4 完全相同，不看權杖）
            ResponseEntity<Object> denied = tokenGate(token);
            if (denied != null) {
                return denied;
            }
        }
        ResponseEntity<Object> forced = injected("start");
        if (forced != null) {
            return forced;
        }
        UUID id = UUID.fromString((String) body.get("run_id"));
        if (bridge.runs().containsKey(id)) {
            return error(409, "run_exists", "run_id", id.toString());
        }
        String project = (String) body.get("project");
        String path = (String) body.get("execution_path");
        Map<String, Object> playbook = (Map<String, Object>) body.get("playbook");
        List<MiniRun.Step> steps = MiniBridge.stepsOf(playbook);
        if (steps.isEmpty()) {
            return error(422, "invalid_request", "violations", List.of(map("field", "playbook.tasks", "rule",
                    "too_short", "message", "至少要有一個任務")));
        }
        String lockKey = project + "|" + path;
        UUID holder = bridge.acquireLock(lockKey, id);
        if (holder != null) {
            return error(409, "advisory_lock_held", "holder_run_id", holder.toString());
        }
        MiniRun run = new MiniRun(bridge, id, project, path, lockKey, steps, MiniBridge.copy(body));
        bridge.runs().put(id, run);
        run.start();
        Map<String, Object> created = map("run_id", id.toString(), "status", "RUNNING", "pid", 4242, "workspace",
                "mini-workspace/" + id, "bridge_instance", bridge.bridgeInstance);
        if (sdd && !bridge.sdd.createWarnings.isEmpty()) {
            created.put("warnings", List.copyOf(bridge.sdd.createWarnings));
        }
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @PostMapping("/autoclaude/runs/{idAction}")
    ResponseEntity<Object> action(@PathVariable String idAction, @RequestBody(required = false) Map<String, Object> body,
                                  @RequestHeader(value = "X-Bridge-Token", required = false) String token) {
        bridge.record("POST /autoclaude/runs/" + idAction);
        int colon = idAction.indexOf(':');
        if (colon < 0) {
            return error(404, "not_found");
        }
        String rawId = idAction.substring(0, colon);
        String verb = idAction.substring(colon + 1);
        ResponseEntity<Object> forced = injected(verb);
        if (forced != null) {
            return forced;
        }
        MiniRun run = parse(rawId).map(bridge.runs()::get).orElse(null);
        if (run == null) {
            return error(404, "run_not_found", "run_id", rawId);
        }
        if ("resume".equals(verb) && isSddRun(run)) {
            // D-115-18：SDD run 的 :resume 也要權杖（先查到 run 才知道它帶不帶 sdd）；缺／錯回 503／403，run 狀態不變
            ResponseEntity<Object> denied = tokenGate(token);
            if (denied != null) {
                return denied;
            }
        }
        Optional<String> result = switch (verb) {
            case "pause" -> run.pause();
            case "resume" -> run.resume();
            case "stop" -> run.stop();
            default -> Optional.of("unknown_verb");
        };
        if (result.isEmpty()) {
            return error(409, "invalid_state", "run_id", rawId, "status", run.status(), "detail",
                    "狀態 " + run.status() + " 不允許 " + verb);
        }
        return ResponseEntity.status(202).body(map("status", result.get()));
    }

    @PostMapping("/autoclaude/runs/{id}/restore")
    ResponseEntity<Object> restore(@PathVariable String id, @RequestBody Map<String, Object> body,
                                   @RequestHeader(value = "X-Bridge-Token", required = false) String token) {
        bridge.record("POST /autoclaude/runs/" + id + "/restore");
        ResponseEntity<Object> forced = injected("restore");
        if (forced != null) {
            return forced;
        }
        MiniRun run = parse(id).map(bridge.runs()::get).orElse(null);
        if (run == null) {
            return error(404, "run_not_found", "run_id", id);
        }
        if (isSddRun(run)) {
            ResponseEntity<Object> denied = tokenGate(token);
            if (denied != null) {
                return denied;
            }
        }
        UUID checkpointId = UUID.fromString((String) body.get("checkpoint_id"));
        Optional<String> result = run.restore(checkpointId);
        if (result.isEmpty()) {
            return error(409, "invalid_state", "run_id", id, "status", run.status(), "detail",
                    "狀態 " + run.status() + " 不允許 restore");
        }
        String reason = result.get();
        if (reason.equals("checkpoint_not_found")) {
            return error(404, "checkpoint_not_found", "checkpoint_id", checkpointId.toString());
        }
        if (reason.startsWith("advisory_lock_held")) {
            return error(409, "advisory_lock_held", "holder_run_id", reason.substring(reason.indexOf(':') + 1));
        }
        return ResponseEntity.status(202).body(map("status", "RUNNING"));
    }

    @GetMapping("/autoclaude/runs/{id}")
    ResponseEntity<Object> get(@PathVariable String id) {
        bridge.record("GET /autoclaude/runs/" + id);
        ResponseEntity<Object> forced = injected("getRun");
        if (forced != null) {
            return forced;
        }
        MiniRun run = parse(id).map(bridge.runs()::get).orElse(null);
        if (run == null) {
            return error(404, "run_not_found", "run_id", id);
        }
        return ResponseEntity.ok(run.snapshot());
    }

    @GetMapping("/autoclaude/runs/{id}/events")
    ResponseEntity<Object> events(@PathVariable String id, @RequestParam(defaultValue = "0") int after,
                                  @RequestParam(defaultValue = "500") int limit) {
        bridge.record("GET /autoclaude/runs/" + id + "/events?after=" + after);
        ResponseEntity<Object> forced = injected("events");
        if (forced != null) {
            return forced;
        }
        MiniRun run = parse(id).map(bridge.runs()::get).orElse(null);
        if (run == null) {
            return error(404, "run_not_found", "run_id", id);
        }
        return ResponseEntity.ok(run.eventsAfter(after, limit));
    }

    @GetMapping("/autoclaude/runs/{id}/checkpoints")
    ResponseEntity<Object> checkpoints(@PathVariable String id) {
        bridge.record("GET /autoclaude/runs/" + id + "/checkpoints");
        MiniRun run = parse(id).map(bridge.runs()::get).orElse(null);
        if (run == null) {
            return error(404, "run_not_found", "run_id", id);
        }
        List<Map<String, Object>> out;
        synchronized (run) {
            out = run.checkpoints.stream().map(c -> map("checkpoint_id", c.id().toString(), "name", c.name(),
                    "created_at", c.createdAt().toString(), "step_idx", c.stepIdx(), "step_id", c.stepId(),
                    "is_automatic", true)).toList();
        }
        return ResponseEntity.ok(out);
    }

    @GetMapping(value = "/autoclaude/runs/{id}/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    SseEmitter stream(@PathVariable String id, @RequestParam(defaultValue = "0") int after,
                      @RequestHeader(value = "Last-Event-ID", required = false) String lastEventId) {
        bridge.record("GET /autoclaude/runs/" + id + "/stream?after=" + after);
        MiniBridge.Injected forced = bridge.takeInjected("stream");
        if (forced != null) {
            throw new MiniError(forced.status(), forced.body());
        }
        MiniRun run = parse(id).map(bridge.runs()::get).orElse(null);
        if (run == null) {
            throw new MiniError(404, map("code", 404, "reason", "run_not_found", "run_id", id));
        }
        int cursor = after;
        if (lastEventId != null && lastEventId.matches("[0-9]+")) {
            cursor = Math.max(cursor, Integer.parseInt(lastEventId));
        }
        SseEmitter emitter = new SseEmitter(0L);
        int startCursor = cursor;
        int generation = bridge.generation();
        bridge.streamOpened();
        Thread.ofVirtual().name("mini-sse-" + id).start(() -> pump(run, emitter, startCursor, generation));
        return emitter;
    }

    /** 逐則送出游標之後的事件；run 終態且游標追上時結束；PAUSED 不結束；{@code dropStreams()} 粗暴切斷。 */
    private void pump(MiniRun run, SseEmitter emitter, int startCursor, int generation) {
        int cursor = startCursor;
        long lastSent = System.currentTimeMillis();
        try {
            emitter.send(SseEmitter.event().reconnectTime(3000));
            while (true) {
                if (bridge.generation() != generation) {
                    emitter.completeWithError(new IOException("dropped by test"));
                    return;
                }
                List<Map<String, Object>> batch = run.eventsAfter(cursor, 200);
                if (!batch.isEmpty()) {
                    for (Map<String, Object> envelope : batch) {
                        Map<String, Object> data = new java.util.LinkedHashMap<>(envelope);
                        String event = (String) data.remove("event");
                        int seq = ((Number) envelope.get("seq")).intValue();
                        emitter.send(SseEmitter.event().id(Integer.toString(seq)).name(event)
                                .data(JSON.writeValueAsString(data)));
                        cursor = seq;
                    }
                    lastSent = System.currentTimeMillis();
                    continue;
                }
                if (run.terminal()) {
                    emitter.complete();
                    return;
                }
                run.awaitEvents(cursor, 100);
                if (System.currentTimeMillis() - lastSent >= bridge.keepAliveMillis) {
                    emitter.send(SseEmitter.event().comment("keep-alive"));
                    lastSent = System.currentTimeMillis();
                }
            }
        } catch (IOException | IllegalStateException e) {
            // 客戶端斷線
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            bridge.streamClosed();
        }
    }
}
