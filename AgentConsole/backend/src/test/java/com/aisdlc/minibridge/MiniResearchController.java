package com.aisdlc.minibridge;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Pattern;

import static com.aisdlc.minibridge.MiniBridge.map;

/**
 * 迷你 Bridge 的研究面 HTTP（路徑、狀態碼與錯誤封包對照真 Bridge 的 {@code routers/research.py}）。預設行為與可腳本化的旋鈕見 {@link MiniResearch}；
 * 專案、PRD 版本與封存狀態直接寫進共用的 PostgreSQL（迷你 Bridge 是研究表的唯一寫入者）。
 */
@RestController
class MiniResearchController {

    private static final Pattern REDDIT = Pattern.compile("(^|\\.)(reddit\\.com|redd\\.it)$");

    private final MiniResearch research;

    MiniResearchController(MiniResearch research) {
        this.research = research;
    }

    private static ResponseEntity<Object> reply(MiniResearch.Reply reply) {
        return ResponseEntity.status(reply.status()).contentType(MediaType.APPLICATION_JSON).body(reply.body());
    }

    private static ResponseEntity<Object> error(int status, String reason, Object... extra) {
        return reply(MiniResearch.Reply.error(status, reason, extra));
    }

    private static ResponseEntity<Object> json(int status, Map<String, Object> body) {
        return ResponseEntity.status(status).contentType(MediaType.APPLICATION_JSON).body(body);
    }

    /** 記錄請求並套用共通旋鈕（延遲）。 */
    private void arrive(HttpServletRequest http, Map<String, Object> body) {
        research.record(new MiniResearch.Call(http.getMethod(), http.getRequestURI(), http.getHeader("X-Bridge-Token"), http.getHeader("X-Trace-Id"),
                body == null ? Map.of() : body));
        long delay = research.delayMillis;
        if (delay > 0) {
            try {
                Thread.sleep(delay);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
    }

    /** 寫入端點的共同閘：權杖（未設 503、不符 403）→ 資料庫（503）。 */
    private ResponseEntity<Object> writeGate(HttpServletRequest http) {
        String configured = research.writeToken;
        if (configured == null) {
            return error(503, "research_write_disabled", "detail", "BRIDGE_RESEARCH_WRITE_TOKEN 未設");
        }
        if (!configured.equals(http.getHeader("X-Bridge-Token"))) {
            return error(403, "research_write_forbidden");
        }
        if (!research.db) {
            return error(503, "research_requires_db");
        }
        return null;
    }

    private static String text(Object value) {
        return value == null ? null : value.toString();
    }

    private static Map<String, Object> flow(String step, String phase, String status) {
        return map("step", step, "phase", phase, "status", status, "detail", "");
    }

    // ── 讀取 ─────────────────────────────────────────────────────────────────────────────

    @GetMapping("/research/capabilities")
    ResponseEntity<Object> capabilities(HttpServletRequest http) {
        arrive(http, null);
        MiniResearch.Reply scripted = research.script("capabilities");
        return scripted != null ? reply(scripted) : json(200, research.capabilitiesBody());
    }

    @GetMapping("/research/allowlist")
    ResponseEntity<Object> allowlistList(HttpServletRequest http) {
        arrive(http, null);
        MiniResearch.Reply scripted = research.script("allowlist.list");
        if (scripted != null) {
            return reply(scripted);
        }
        return research.db ? json(200, research.allowlistBody()) : error(503, "research_requires_db");
    }

    // ── allowlist 寫入 ───────────────────────────────────────────────────────────────────

    @PostMapping("/research/allowlist")
    ResponseEntity<Object> allowlistAdd(HttpServletRequest http, @RequestBody Map<String, Object> body) {
        arrive(http, body);
        MiniResearch.Reply scripted = research.script("allowlist.add");
        if (scripted != null) {
            return reply(scripted);
        }
        ResponseEntity<Object> denied = writeGate(http);
        if (denied != null) {
            return denied;
        }
        String host = text(body.get("host"));
        boolean acknowledged = Boolean.TRUE.equals(body.get("tos_acknowledged"));
        if (host != null && REDDIT.matcher(host).find() && !acknowledged) {
            return error(422, "terms_ack_required", "detail", "Reddit 須先確認條款");
        }
        boolean exists = research.allowlist.stream().anyMatch(e -> e.get("host").equals(host) && e.get("list_kind").equals(body.get("list_kind")));
        if (exists) {
            return error(409, "allowlist_exists", "details", map("host", host));
        }
        Map<String, Object> entry = map("id", UUID.randomUUID().toString(), "list_kind", body.get("list_kind"), "host", host, "layer", body.get("layer"),
                "purpose", body.getOrDefault("purpose", ""), "tos_note", body.getOrDefault("tos_note", ""),
                "min_interval_seconds", body.getOrDefault("min_interval_seconds", 3), "enabled", true, "tos_acknowledged", acknowledged,
                "added_by", body.get("added_by"), "added_at", "2026-11-02T10:00:00+00:00", "disabled_by", null, "disabled_at", null, "source", "ADMIN");
        research.allowlist.add(entry);
        return json(201, entry);
    }

    @PatchMapping("/research/allowlist/{entryId}")
    ResponseEntity<Object> allowlistPatch(HttpServletRequest http, @PathVariable String entryId, @RequestBody Map<String, Object> body) {
        arrive(http, body);
        MiniResearch.Reply scripted = research.script("allowlist.patch");
        if (scripted != null) {
            return reply(scripted);
        }
        ResponseEntity<Object> denied = writeGate(http);
        if (denied != null) {
            return denied;
        }
        Map<String, Object> entry = research.allowlist.stream().filter(e -> e.get("id").equals(entryId)).findFirst().orElse(null);
        if (entry == null) {
            return error(404, "research_not_found", "entry_id", entryId);
        }
        boolean onlyEnabled = body.keySet().stream().allMatch(key -> "enabled".equals(key) || "disabled_by".equals(key));
        if (!onlyEnabled || !(body.get("enabled") instanceof Boolean)) {
            return error(422, "invalid_request", "violations", List.of(map("field", "enabled", "rule", "extra_forbidden", "message", "只准 enabled")));
        }
        entry.put("enabled", body.get("enabled"));
        entry.put("disabled_by", Boolean.TRUE.equals(body.get("enabled")) ? null : body.get("disabled_by"));
        return json(200, entry);
    }

    // ── 專案 ─────────────────────────────────────────────────────────────────────────────

    @PostMapping("/research/projects")
    ResponseEntity<Object> create(HttpServletRequest http, @RequestBody Map<String, Object> body) {
        arrive(http, body);
        MiniResearch.Reply scripted = research.script("create");
        if (scripted != null) {
            return reply(scripted);
        }
        ResponseEntity<Object> denied = writeGate(http);
        if (denied != null) {
            return denied;
        }
        UUID id = UUID.fromString(text(body.get("research_id")));
        String slug = text(body.get("slug"));
        @SuppressWarnings("unchecked")
        Map<String, Object> scope = (Map<String, Object>) body.getOrDefault("scope", Map.of());
        String workspace = "/research-root/" + slug;
        try {
            research.jdbc().update("insert into console.research_projects (id, slug, title, topic, scope, depth_level, target_scope, workspace_path, "
                    + "fsm_project, fsm_state_dir, created_by) values (?, ?, ?, ?, ?::jsonb, ?, ?, ?, ?, ?, ?)", id, slug, text(body.get("title")),
                    text(body.get("topic")), MiniBridge.JSON.writeValueAsString(scope), body.getOrDefault("depth_level", "STANDARD"),
                    scope.getOrDefault("target_scope_hint", "UNDECIDED"), workspace, "research-" + slug, workspace + "/build/reports/fsm",
                    text(body.get("created_by")));
        } catch (DuplicateKeyException e) {
            return error(409, "slug_in_use", "details", map("slug", slug));
        }
        research.event(id, 1, "research.step", map("flowStep", "topic", "flowPhase", "INGESTED", "flowStatus", "IDLE", "flowDetail", ""));
        String rpNo = research.jdbc().queryForObject("select rp_no from console.research_projects where id = ?", String.class, id);
        return json(201, map("research_id", id.toString(), "rp_no", rpNo, "workspace_path", workspace, "fsm_project", "research-" + slug,
                "flow", flow("topic", "INGESTED", "IDLE")));
    }

    @PutMapping("/research/projects/{id}/prd")
    ResponseEntity<Object> prd(HttpServletRequest http, @PathVariable String id, @RequestBody Map<String, Object> body) {
        arrive(http, body);
        MiniResearch.Reply scripted = research.script("prd");
        if (scripted != null) {
            return reply(scripted);
        }
        ResponseEntity<Object> denied = writeGate(http);
        if (denied != null) {
            return denied;
        }
        UUID researchId = UUID.fromString(id);
        Integer head = research.jdbc().queryForObject("select coalesce(max(version_no), 0) from console.research_prd_versions where research_id = ?",
                Integer.class, researchId);
        int headNo = head == null ? 0 : head;
        if (!Integer.valueOf(headNo).equals(body.get("base_version"))) {
            return error(409, "prd_version_conflict", "details", map("headVersion", headNo));
        }
        int versionNo = headNo + 1;
        String semver = "v0." + versionNo + ".0-draft";
        String content = text(body.get("content"));
        int bytes = content.getBytes(StandardCharsets.UTF_8).length;
        String digest = sha256(content);
        research.jdbc().update("insert into console.research_prd_versions (research_id, version_no, semver, kind, author_kind, author, parent_version_no, content, "
                + "rel_path, sha256, bytes, change_summary) values (?, ?, ?, 'DRAFT', 'HUMAN', ?, ?, ?, ?, ?, ?, ?)", researchId, versionNo, semver,
                text(body.get("author")), headNo == 0 ? null : headNo, content, "01_specs/PRD-" + semver + ".md", digest, bytes,
                text(body.getOrDefault("change_summary", "")));
        return json(201, map("version_no", versionNo, "semver", semver, "sha256", digest, "bytes", bytes));
    }

    @PostMapping("/research/projects/{id}/stages/{stageAction}")
    ResponseEntity<Object> stage(HttpServletRequest http, @PathVariable String id, @PathVariable String stageAction,
                                 @RequestBody Map<String, Object> body) {
        arrive(http, body);
        String stage = stageAction.contains(":") ? stageAction.substring(0, stageAction.indexOf(':')) : stageAction;
        MiniResearch.Reply scripted = research.script("stage:" + stage, "stage");
        if (scripted != null) {
            return reply(scripted);
        }
        ResponseEntity<Object> denied = writeGate(http);
        if (denied != null) {
            return denied;
        }
        if (research.stageRace && research.arriveAtRace() > 1) {
            return error(409, "stage_conflict", "details", map("activeStageRunId", UUID.randomUUID().toString(), "activeStage", "RESEARCH"));
        }
        return json(202, map("stage_run_id", UUID.randomUUID().toString(), "engine_run_id", UUID.randomUUID().toString(),
                "flow", flow("topic", "RESEARCHING", "RUNNING")));
    }

    /** {@code /research/projects/{id}:<動詞>}：approve-baseline｜return｜cancel｜reconcile｜archive｜restore｜reinit。 */
    @PostMapping("/research/projects/{idAction}")
    ResponseEntity<Object> action(HttpServletRequest http, @PathVariable String idAction, @RequestBody(required = false) Map<String, Object> body) {
        arrive(http, body);
        int colon = idAction.indexOf(':');
        if (colon < 0) {
            return error(404, "research_not_found");
        }
        String verb = idAction.substring(colon + 1);
        String route = switch (verb) {
            case "approve-baseline" -> "approve";
            default -> verb;
        };
        boolean next = body != null && "next".equals(body.get("generation"));
        MiniResearch.Reply scripted = research.script(next ? new String[] {route + ":next", route} : new String[] {route});
        if (scripted != null) {
            return reply(scripted);
        }
        ResponseEntity<Object> denied = writeGate(http);
        if (denied != null) {
            return denied;
        }
        UUID id = UUID.fromString(idAction.substring(0, colon));
        return switch (verb) {
            case "approve-baseline" -> json(200, map("gate_decision_id", UUID.randomUUID().toString(), "stage", "Gate-0",
                    "spec_doc_digests", body == null ? Map.of() : body.getOrDefault("expected_digests", Map.of()), "fsm_state", "SPEC_FROZEN",
                    "audit_trace_id", http.getHeader("X-Trace-Id")));
            case "return" -> json(200, map("gate_decision_id", UUID.randomUUID().toString(), "fsm_retry_count", 1, "escalated", false));
            case "cancel" -> json(200, map("stopped_run_id", null, "flow", flow("topic", "RESEARCHING", "CANCELLED")));
            case "reconcile" -> json(200, map("consistent", true, "checks", List.of(map("name", "files", "status", "ok"))));
            case "archive" -> {
                research.jdbc().update("update console.research_projects set archived_at = now(), updated_at = now() where id = ?", id);
                yield json(200, map("flow", flow("topic", "INGESTED", "IDLE"), "archived", true));
            }
            case "restore" -> {
                research.jdbc().update("update console.research_projects set archived_at = null, updated_at = now() where id = ?", id);
                yield json(200, map("flow", flow("topic", "INGESTED", "IDLE"), "archived", false));
            }
            case "reinit" -> {
                Map<String, Object> result = new LinkedHashMap<>(map("flow", flow("studio", "REVISING", "IDLE")));
                if (next) {
                    result.put("fsm_project", "research-demo-g2");
                    result.put("fsm_generation", 2);
                    result.put("gate_decision_id", UUID.randomUUID().toString());
                }
                yield json(200, result);
            }
            default -> error(404, "research_not_found");
        };
    }

    private static String sha256(String content) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(content.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
