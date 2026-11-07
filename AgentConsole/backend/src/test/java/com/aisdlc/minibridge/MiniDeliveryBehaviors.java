package com.aisdlc.minibridge;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static com.aisdlc.minibridge.MiniBridge.map;

/**
 * 迷你 Bridge 的 P2 預設行為（內環閘登錄、交付、追溯表預演、自癒同步；形狀照真 Bridge 的 {@code routers/research_deliver.py}）。與 P1 同體例：預設回成功形狀，
 * 測試以 {@link MiniResearch#next}／{@link MiniResearch#always}（路由鍵＝動詞：{@code gates}、{@code tag}、{@code pr}、{@code traceability-preview}、
 * {@code healing-sync}）覆寫成腳本回應（含 409／422／502 與延遲）。迷你 Bridge 不寫 {@code research_deliveries} 與 {@code research_gate_decisions}。
 */
final class MiniDeliveryBehaviors {

    private MiniDeliveryBehaviors() {
    }

    private static Object flow() {
        return map("step", "deliver", "phase", "DELIVERED", "status", "COMPLETED", "detail", "");
    }

    static MiniResearch.Reply gates(Map<String, Object> body) {
        return new MiniResearch.Reply(200, map("gate_decision_id", body.getOrDefault("decision_id", UUID.randomUUID().toString()), "gate", body.get("gate"),
                "result", body.get("result"), "fsm_state_before", "IMPLEMENTATION", "next_state", "PR_REVIEW", "escalated", false, "flow", flow()));
    }

    static MiniResearch.Reply tag(Map<String, Object> body) {
        String sha = "c".repeat(64);
        return new MiniResearch.Reply(201, map("delivery", map("kind", "RELEASE_TAG", "ref", body.get("tag_name"), "commit_sha", "d".repeat(40), "url", null,
                "rtm_run_id", null, "rtm_report_ref", "03_execution/traceability_matrix.json", "fsm_state_after", "RELEASE_READY", "status", "CREATED", "detail", "",
                "created_by", body.get("approver"),
                "created_at", OffsetDateTime.now().toString(), "snapshot_sha256", sha), "snapshot", map("relPath", "03_execution/traceability_matrix.json", "sha256", sha),
                "flow", flow(), "fsmState", "RELEASE"));
    }

    static MiniResearch.Reply pr(Map<String, Object> body) {
        return new MiniResearch.Reply(201, map("delivery", map("kind", "PULL_REQUEST", "ref", "1", "commit_sha", null, "url", "https://example.invalid/pull/1",
                "status", "CREATED", "created_by", body.get("approver")), "created", true));
    }

    static MiniResearch.Reply traceability() {
        return new MiniResearch.Reply(200, map("rows", List.of(), "totals", map("acTotal", 0, "covered", 0, "uncovered", 0, "frTotal", 0), "rtm", null,
                "generatedAt", OffsetDateTime.now().toString()));
    }

    static MiniResearch.Reply healingSync() {
        return new MiniResearch.Reply(200, map("view_rows", 0, "log_lines", 0, "appended", 0, "spec_change", List.of()));
    }
}
