package com.aisdlc.minibridge;

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

    @GetMapping("/sdd/fsm")
    ResponseEntity<Object> sddFsmList() {
        bridge.record("GET /sdd/fsm");
        ResponseEntity<Object> forced = injected("sddFsmList");
        if (forced != null) {
            return forced;
        }
        sddDelay();
        if (bridge.sdd.unavailable) {
            return sddUnavailable();
        }
        return ResponseEntity.ok(map("root", bridge.sdd.latest, "projects", List.copyOf(bridge.sdd.projects),
                "errors", List.copyOf(bridge.sdd.errors)));
    }

    @GetMapping("/sdd/fsm/{project}")
    ResponseEntity<Object> sddFsm(@PathVariable String project) {
        bridge.record("GET /sdd/fsm/" + project);
        ResponseEntity<Object> forced = injected("sddFsm");
        if (forced != null) {
            return forced;
        }
        sddDelay();
        if (bridge.sdd.unavailable) {
            return sddUnavailable();
        }
        Map<String, Object> state = bridge.sdd.states.get(project);
        if (!project.matches("^[A-Za-z0-9._-]{1,128}$") || (state == null && !bridge.sdd.unreadable.contains(project))) {
            return error(404, "fsm_not_found", "project", project);
        }
        if (bridge.sdd.unreadable.contains(project)) {
            return error(422, "fsm_state_unreadable", "detail", "while scanning a simple key");
        }
        return ResponseEntity.ok(state);
    }

    @PostMapping("/autoclaude/runs")
    @SuppressWarnings("unchecked")
    ResponseEntity<Object> create(@RequestBody Map<String, Object> body) {
        bridge.record("POST /autoclaude/runs");
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
        return ResponseEntity.status(HttpStatus.CREATED).body(map("run_id", id.toString(), "status", "RUNNING", "pid",
                4242, "workspace", "mini-workspace/" + id, "bridge_instance", bridge.bridgeInstance));
    }

    @PostMapping("/autoclaude/runs/{idAction}")
    ResponseEntity<Object> action(@PathVariable String idAction, @RequestBody(required = false) Map<String, Object> body) {
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
    ResponseEntity<Object> restore(@PathVariable String id, @RequestBody Map<String, Object> body) {
        bridge.record("POST /autoclaude/runs/" + id + "/restore");
        ResponseEntity<Object> forced = injected("restore");
        if (forced != null) {
            return forced;
        }
        MiniRun run = parse(id).map(bridge.runs()::get).orElse(null);
        if (run == null) {
            return error(404, "run_not_found", "run_id", id);
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
