package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 系統參數的寫入（API-SET-03／04／05／07；契約 §1.5.3～§1.5.8、E2E-09）。為什麼重要：這裡守住三條安全不變式——
 * ① Token Guard 兩個閾值永遠成對滿足 halt &gt; compact，且任何失敗都不改任何一個鍵（NFR-SEC-05）；
 * ② 敏感參數在資料庫是密文、在任何回應／歷史／日誌都只有遮罩，明文只給 ADMIN 的 reveal 並留審計（NFR-SEC-04／9.2）；
 * ③ 只有 ADMIN 能改設定。每一條都要「失敗後資料庫沒動」的證據，而不只是狀態碼。
 */
@ExtendWith(OutputCaptureExtension.class)
class SettingsWriteApiIT extends AbstractApiIT {

    private static final String BASE = "/api/v1/settings";
    private static final String GUARD_REASON = "halt_threshold_pct 必須大於 compact_threshold_pct";
    private static final String MASK = "••••••••";
    private static final String CONFIRM_REASON = "敏感參數更新需二次確認（confirm=true）";

    private Resp put(String category, String key, String value) {
        return api.put(admin(), BASE + "/" + category + "/" + key, Map.of("value", value));
    }

    private Resp putSecret(String key, String value) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("value", value);
        body.put("confirm", true);
        return api.put(admin(), BASE + "/model/" + key, body);
    }

    private Resp tokenGuard(Object compact, Object halt) {
        Map<String, Object> body = new LinkedHashMap<>();
        if (compact != null) {
            body.put("compactThresholdPct", compact);
        }
        if (halt != null) {
            body.put("haltThresholdPct", halt);
        }
        return api.put(admin(), BASE + "/execution/token-guard", body);
    }

    private String dbValue(String category, String key) {
        return jdbc.queryForObject("select value from console.system_configs where category = ? and key = ?",
                String.class, category, key);
    }

    private int historyCount() {
        return jdbc.queryForObject("select count(*) from console.system_config_history", Integer.class);
    }

    private int historyCount(String category, String key) {
        return jdbc.queryForObject("select count(*) from console.system_config_history h join "
                + "console.system_configs c on c.id = h.config_id where c.category = ? and c.key = ?",
                Integer.class, category, key);
    }

    private void assertGuardUntouched() {
        assertThat(dbValue("execution", "compactThresholdPct")).isEqualTo("80");
        assertThat(dbValue("execution", "haltThresholdPct")).isEqualTo("90");
        assertThat(historyCount()).as("失敗不得留下任何歷史").isZero();
    }

    private static void assertGuardRejection(Resp resp) {
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.<String>read("$.reason")).isEqualTo(GUARD_REASON);
    }

    // ── Token Guard（NFR-SEC-05）──────────────────────────────────────────────

    @Test
    void aReversedOrEqualPairIsRejectedWithThePrdReasonAndNothingChanges() {
        Resp reversed = tokenGuard(90, 80);
        assertGuardRejection(reversed);
        assertThat(reversed.<String>read("$.errors[0].field")).isEqualTo("haltThresholdPct");
        assertThat(reversed.<Integer>read("$.details.compactThresholdPct")).isEqualTo(90);
        assertThat(reversed.<Integer>read("$.details.haltThresholdPct")).isEqualTo(80);
        assertGuardUntouched();

        assertGuardRejection(tokenGuard(80, 80));
        assertGuardRejection(tokenGuard(99, 99));
        assertGuardRejection(tokenGuard(70, 70));
        assertGuardUntouched();
    }

    @Test
    void outOfRangeOrMissingValuesAreBeanValidationErrorsWithoutTheGuardReason() {
        Resp overMax = tokenGuard(100, 100);
        assertThat(overMax.status()).isEqualTo(400);
        assertThat(overMax.has("$.reason")).as("範圍違規不是 halt>compact 的 reason").isFalse();
        assertThat(overMax.<String>read("$.errors[0].field")).isEqualTo("compactThresholdPct");

        assertThat(tokenGuard(0, 50).<String>read("$.errors[0].field")).isEqualTo("compactThresholdPct");
        assertThat(tokenGuard(50, 101).<String>read("$.errors[0].field")).isEqualTo("haltThresholdPct");
        assertThat(tokenGuard(50, 1).<String>read("$.errors[0].field")).isEqualTo("haltThresholdPct");
        assertThat(tokenGuard(70, null).<String>read("$.errors[0].field")).isEqualTo("haltThresholdPct");
        assertThat(tokenGuard(null, 95).<String>read("$.errors[0].field")).isEqualTo("compactThresholdPct");
        assertThat(api.put(admin(), BASE + "/execution/token-guard", Map.of("compactThresholdPct", "abc",
                "haltThresholdPct", 90)).status()).isEqualTo(400);
        assertGuardUntouched();
    }

    @Test
    void aValidPairUpdatesBothKeysAtomicallyAndWritesOneHistoryRowEach() {
        Resp resp = tokenGuard(70, 95);
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<List<String>>read("$.data[*].key")).containsExactly("compactThresholdPct",
                "haltThresholdPct");
        assertThat(resp.<List<String>>read("$.data[*].value")).containsExactly("70", "95");
        assertThat(dbValue("execution", "compactThresholdPct")).isEqualTo("70");
        assertThat(dbValue("execution", "haltThresholdPct")).isEqualTo("95");

        Resp compact = api.get(viewer(), BASE + "/history?category=execution&key=compactThresholdPct");
        assertThat(compact.<Integer>read("$.data.totalElements")).isEqualTo(1);
        assertThat(compact.<String>read("$.data.content[0].oldValue")).isEqualTo("80");
        assertThat(compact.<String>read("$.data.content[0].newValue")).isEqualTo("70");
        assertThat(compact.<String>read("$.data.content[0].changedBy")).isEqualTo("admin");
        Resp halt = api.get(viewer(), BASE + "/history?category=execution&key=haltThresholdPct");
        assertThat(halt.<String>read("$.data.content[0].oldValue")).isEqualTo("90");
        assertThat(halt.<String>read("$.data.content[0].newValue")).isEqualTo("95");

        assertThat(tokenGuard(70, 95).status()).as("同值再送一次").isEqualTo(200);
        assertThat(historyCount()).as("值沒變就不寫歷史").isEqualTo(2);
    }

    @Test
    void singleKeyUpdatesAreCrossCheckedAgainstTheOtherKeysCurrentValue() {
        assertThat(tokenGuard(70, 95).status()).isEqualTo(200);
        int historyBefore = historyCount();

        assertGuardRejection(put("execution", "haltThresholdPct", "60"));
        assertGuardRejection(put("execution", "haltThresholdPct", "70"));
        assertGuardRejection(put("execution", "compactThresholdPct", "96"));
        assertGuardRejection(put("execution", "compactThresholdPct", "95"));
        assertThat(dbValue("execution", "compactThresholdPct")).isEqualTo("70");
        assertThat(dbValue("execution", "haltThresholdPct")).isEqualTo("95");
        assertThat(historyCount()).isEqualTo(historyBefore);

        assertThat(put("execution", "compactThresholdPct", "94").status()).isEqualTo(200);
        assertThat(put("execution", "haltThresholdPct", "96").status()).isEqualTo(200);
    }

    @Test
    void aMalformedSingleGuardValueIsAValueErrorNotAGuardError() {
        Resp resp = put("execution", "compactThresholdPct", "abc");
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.<String>read("$.reason")).isEqualTo("參數值不符合型別或驗證規則");
        assertThat(resp.<String>read("$.errors[0].field")).isEqualTo("value");
    }

    @Test
    void resettingOneKeyOfThePairIsCheckedAgainstTheOtherAndEverySuccessWritesHistory() {
        assertThat(tokenGuard(70, 75).status()).isEqualTo(200);

        Resp blocked = api.post(admin(), BASE + "/execution/compactThresholdPct/reset");
        assertGuardRejection(blocked);
        assertThat(dbValue("execution", "compactThresholdPct")).as("預設 80 不小於目前 halt 75，不可重置").isEqualTo("70");

        Resp haltReset = api.post(admin(), BASE + "/execution/haltThresholdPct/reset");
        assertThat(haltReset.status()).isEqualTo(200);
        assertThat(haltReset.<String>read("$.data.value")).isEqualTo("90");

        Resp compactReset = api.post(admin(), BASE + "/execution/compactThresholdPct/reset");
        assertThat(compactReset.status()).isEqualTo(200);
        assertThat(compactReset.<String>read("$.data.value")).isEqualTo("80");

        assertThat(historyCount("execution", "compactThresholdPct")).isEqualTo(2);
        assertThat(historyCount("execution", "haltThresholdPct")).isEqualTo(2);
    }

    @Test
    void concurrentSingleKeyUpdatesCannotTogetherViolateTheOrdering() throws Exception {
        assertThat(tokenGuard(50, 60).status()).isEqualTo(200);
        // 起點 compact=50、halt=60。「halt→55」單獨看合法（55 > 50），「compact→58」單獨看也合法（58 < 60），
        // 但兩個都套用會變成 compact=58、halt=55 違規：鎖列＋序列化保證其中一個讀到對方的新值而被擋。
        Resp[] results = new Resp[2];
        Thread first = new Thread(() -> results[0] = put("execution", "haltThresholdPct", "55"));
        Thread second = new Thread(() -> results[1] = put("execution", "compactThresholdPct", "58"));
        first.start();
        second.start();
        first.join();
        second.join();

        int compact = Integer.parseInt(dbValue("execution", "compactThresholdPct"));
        int halt = Integer.parseInt(dbValue("execution", "haltThresholdPct"));
        assertThat(halt).as("不論誰先到，最終狀態必須滿足 halt > compact（compact=%d halt=%d）", compact, halt)
                .isGreaterThan(compact);
        List<Integer> statuses = List.of(results[0].status(), results[1].status());
        assertThat(statuses).as("至少一個成功、且沒有任何 5xx").allMatch(s -> s == 200 || s == 400).contains(200);
    }

    @Test
    void resettingACategoryRestoresEveryDefaultInOneTransaction() {
        assertThat(tokenGuard(50, 60).status()).isEqualTo(200);
        assertThat(put("execution", "logRetentionDays", "30").status()).isEqualTo(200);
        int before = historyCount();

        Resp resp = api.post(admin(), BASE + "/execution/reset");
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<List<Object>>read("$.data")).hasSize(10);
        List<Map<String, Object>> items = resp.read("$.data");
        for (Map<String, Object> item : items) {
            assertThat(item.get("value")).as("execution." + item.get("key")).isEqualTo(item.get("defaultValue"));
        }
        assertThat(historyCount()).as("三個被改過的鍵各寫一筆歷史").isEqualTo(before + 3);
        assertThat(dbValue("execution", "compactThresholdPct")).isEqualTo("80");
        assertThat(dbValue("execution", "haltThresholdPct")).isEqualTo("90");

        assertThat(api.post(admin(), BASE + "/nonexistent/reset").status()).isEqualTo(404);
        assertThat(api.post(admin(), BASE + "/execution/nonexistent/reset").status()).isEqualTo(404);
    }

    // ── 敏感參數（NFR-SEC-04／9.2）────────────────────────────────────────────

    @Test
    void anEncryptedUpdateNeedsConfirmationAndOnlyEverShowsTheMask(CapturedOutput output) {
        Resp unconfirmed = api.put(admin(), BASE + "/model/apiKey", Map.of("value", "sk-new"));
        assertThat(unconfirmed.status()).isEqualTo(409);
        assertThat(unconfirmed.<String>read("$.reason")).isEqualTo(CONFIRM_REASON);
        assertThat(dbValue("model", "apiKey")).isEmpty();
        assertThat(historyCount()).isZero();
        Map<String, Object> explicitFalse = new LinkedHashMap<>();
        explicitFalse.put("value", "sk-new");
        explicitFalse.put("confirm", false);
        assertThat(api.put(admin(), BASE + "/model/apiKey", explicitFalse).status()).isEqualTo(409);

        Resp confirmed = putSecret("apiKey", "sk-new");
        assertThat(confirmed.status()).isEqualTo(200);
        assertThat(confirmed.<String>read("$.data.value")).isEqualTo(MASK);
        assertThat(confirmed.<Boolean>read("$.data.hasValue")).isTrue();
        assertThat(confirmed.<Boolean>read("$.data.isEncrypted")).isTrue();
        assertThat(confirmed.body()).doesNotContain("sk-new");

        String stored = dbValue("model", "apiKey");
        assertThat(stored).as("資料庫存的是 v1:<iv>:<密文>").startsWith("v1:").doesNotContain("sk-new");

        Resp history = api.get(viewer(), BASE + "/history?category=model&key=apiKey");
        assertThat(history.<Integer>read("$.data.totalElements")).isEqualTo(1);
        assertThat(history.<String>read("$.data.content[0].oldValue")).isEqualTo(MASK);
        assertThat(history.<String>read("$.data.content[0].newValue")).isEqualTo(MASK);
        assertThat(history.body()).doesNotContain("sk-new");

        assertThat(putSecret("apiKey", "sk-new").status()).as("同值再送").isEqualTo(200);
        assertThat(historyCount("model", "apiKey")).as("同值不寫歷史").isEqualTo(1);
        assertThat(dbValue("model", "apiKey")).as("同值不重新加密").isEqualTo(stored);

        assertThat(putSecret("apiKey", "sk-other").status()).isEqualTo(200);
        assertThat(historyCount("model", "apiKey")).isEqualTo(2);
        assertThat(dbValue("model", "apiKey")).isNotEqualTo(stored);

        assertThat(output.getAll()).as("日誌不得出現金鑰明文").doesNotContain("sk-new").doesNotContain("sk-other");
        assertThat(api.get(viewer(), BASE).body()).doesNotContain("sk-new").doesNotContain("sk-other");
    }

    @Test
    void clearingAnEncryptedKeyNeedsConfirmationToo() {
        assertThat(putSecret("apiKey", "sk-new").status()).isEqualTo(200);
        assertThat(api.put(admin(), BASE + "/model/apiKey", Map.of("value", "")).status()).isEqualTo(409);

        Resp cleared = putSecret("apiKey", "");
        assertThat(cleared.status()).isEqualTo(200);
        assertThat(cleared.<Boolean>read("$.data.hasValue")).isFalse();
        assertThat(dbValue("model", "apiKey")).isEmpty();

        assertThat(putSecret("apiKey", "x".repeat(513)).status()).as("加密參數長度上限 512").isEqualTo(400);
        assertThat(putSecret("apiKey", "x".repeat(512)).status()).isEqualTo(200);
    }

    @Test
    void theOtherEncryptedKeyBehavesTheSameWay() {
        Resp resp = api.put(admin(), BASE + "/autoclaude/dbDsn", Map.of("value", "postgresql://u:p@h/db",
                "confirm", true));
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.value")).isEqualTo(MASK);
        assertThat(dbValue("autoclaude", "dbDsn")).startsWith("v1:").doesNotContain("postgresql");
    }

    @Test
    void revealIsAdminOnlyReturnsPlaintextAndIsAuditedWithoutTheValue(CapturedOutput output) {
        assertThat(putSecret("apiKey", "sk-reveal-me").status()).isEqualTo(200);

        for (String token : List.of(operator(), viewer())) {
            for (String url : List.of(BASE + "/model?reveal=true", BASE + "?reveal=true")) {
                Resp denied = api.get(token, url);
                assertThat(denied.status()).as(url).isEqualTo(403);
                assertThat(denied.<String>read("$.reason")).isEqualTo("僅 ADMIN 可揭露敏感參數");
                assertThat(denied.body()).doesNotContain("sk-reveal-me");
            }
            Resp masked = api.get(token, BASE + "/model");
            assertThat(masked.status()).isEqualTo(200);
            assertThat(masked.<List<String>>read("$.data[?(@.key=='apiKey')].value")).containsExactly(MASK);
        }

        Resp revealed = api.get(admin(), BASE + "/model?reveal=true");
        assertThat(revealed.status()).isEqualTo(200);
        assertThat(revealed.<List<String>>read("$.data[?(@.key=='apiKey')].value")).containsExactly("sk-reveal-me");
        assertThat(revealed.<List<String>>read("$.data[?(@.key=='name')].value")).containsExactly("MiniMax-M2.7");

        Resp all = api.get(admin(), BASE + "?reveal=true");
        assertThat(all.<List<String>>read("$.data.model[?(@.key=='apiKey')].value")).containsExactly("sk-reveal-me");
        assertThat(all.<List<String>>read("$.data.autoclaude[?(@.key=='dbDsn')].value")).containsExactly("");

        Resp notRevealed = api.get(admin(), BASE + "/model?reveal=false");
        assertThat(notRevealed.<List<String>>read("$.data[?(@.key=='apiKey')].value")).containsExactly(MASK);

        List<String> auditLines = output.getAll().lines().filter(l -> l.contains("\"action\":\"settings.reveal\""))
                .toList();
        assertThat(auditLines).as("兩次揭露各一行審計").hasSize(2);
        assertThat(auditLines).allSatisfy(line -> assertThat(line).doesNotContain("sk-reveal-me")
                .contains("\"subject\":\"admin\""));
        assertThat(jdbc.queryForObject("select count(*) from console.audit_log where subject = 'admin' and "
                + "method = 'GET' and entity_type = 'settings'", Integer.class)).isEqualTo(2);
    }

    // ── 角色 ─────────────────────────────────────────────────────────────────

    @Test
    void onlyAdminMayWriteAnythingUnderSettings() {
        Map<String, Object> value = Map.of("value", "5");
        for (String token : List.of(operator(), viewer())) {
            assertThat(api.put(token, BASE + "/agent/maxRetries", value).status()).isEqualTo(403);
            assertThat(api.put(token, BASE + "/execution/token-guard",
                    Map.of("compactThresholdPct", 70, "haltThresholdPct", 95)).status()).isEqualTo(403);
            assertThat(api.post(token, BASE + "/agent/maxRetries/reset").status()).isEqualTo(403);
            assertThat(api.post(token, BASE + "/agent/reset").status()).isEqualTo(403);
            assertThat(api.post(token, BASE + "/export").status()).isEqualTo(403);
            assertThat(api.multipart(token, BASE + "/import", "file", "s.json", "application/json",
                    "{\"version\":1,\"configs\":[]}".getBytes(StandardCharsets.UTF_8)).status()).isEqualTo(403);
            Resp denied = api.post(token, BASE + "/test-connection", Map.of());
            assertThat(denied.status()).isEqualTo(403);
            assertThat(denied.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");

            assertThat(api.get(token, BASE).status()).isEqualTo(200);
            assertThat(api.get(token, BASE + "/agent").status()).isEqualTo(200);
            assertThat(api.get(token, BASE + "/history").status()).isEqualTo(200);
        }
        assertThat(api.put(null, BASE + "/agent/maxRetries", value).status()).isEqualTo(401);
        assertThat(dbValue("agent", "maxRetries")).isEqualTo("3");
        assertThat(historyCount()).isZero();
    }

    // ── 歷史 ─────────────────────────────────────────────────────────────────

    @Test
    void historyIsPagedNewestFirstAndFilterableByCategoryAndKey() {
        for (int halt : new int[] {91, 92, 93, 94}) {
            assertThat(put("execution", "haltThresholdPct", Integer.toString(halt)).status()).isEqualTo(200);
        }
        assertThat(put("agent", "maxRetries", "7").status()).isEqualTo(200);

        Resp page0 = api.get(viewer(), BASE + "/history?category=execution&key=haltThresholdPct&page=0&size=2");
        assertThat(page0.status()).isEqualTo(200);
        assertThat(page0.<Integer>read("$.data.totalElements")).isEqualTo(4);
        assertThat(page0.<Integer>read("$.data.totalPages")).isEqualTo(2);
        assertThat(page0.<List<String>>read("$.data.content[*].newValue")).containsExactly("94", "93");
        List<String> times = page0.read("$.data.content[*].changedAt");
        assertThat(Instant.parse(times.get(0))).isAfterOrEqualTo(Instant.parse(times.get(1)));
        assertThat(api.get(viewer(), BASE + "/history?category=execution&key=haltThresholdPct&page=1&size=2")
                .<List<String>>read("$.data.content[*].newValue")).containsExactly("92", "91");

        assertThat(api.get(viewer(), BASE + "/history?category=agent").<Integer>read("$.data.totalElements"))
                .isEqualTo(1);
        assertThat(api.get(viewer(), BASE + "/history").<Integer>read("$.data.totalElements")).isEqualTo(5);
        assertThat(api.get(viewer(), BASE + "/history?category=agent").<String>read("$.data.content[0].category"))
                .isEqualTo("agent");
        assertThat(api.get(viewer(), BASE + "/history?category=agent").<String>read("$.data.content[0].key"))
                .isEqualTo("maxRetries");
    }

    @Test
    void historyRejectsAKeyWithoutACategoryAndBadPaging() {
        Resp noCategory = api.get(viewer(), BASE + "/history?key=haltThresholdPct");
        assertThat(noCategory.status()).isEqualTo(400);
        assertThat(noCategory.<String>read("$.errors[0].field")).isEqualTo("key");
        assertThat(api.get(viewer(), BASE + "/history?size=0").status()).isEqualTo(400);
        assertThat(api.get(viewer(), BASE + "/history?size=101").status()).isEqualTo(400);
        assertThat(api.get(viewer(), BASE + "/history?page=-1").status()).isEqualTo(400);
        assertThat(api.get(viewer(), BASE + "/history?size=100").status()).isEqualTo(200);
        assertThat(api.get(null, BASE + "/history").status()).isEqualTo(401);
    }

    @Test
    void everyWriteLeavesOneStructuredAuditRowWithoutTheValue() {
        assertThat(put("agent", "maxRetries", "9").status()).isEqualTo(200);
        List<Map<String, Object>> rows = jdbc.queryForList("select subject, role, method, path, entity_type, "
                + "entity_id, http_status from console.audit_log where path = '/api/v1/settings/agent/maxRetries'");
        assertThat(rows).hasSize(1);
        Map<String, Object> row = rows.get(0);
        assertThat(row).containsEntry("subject", "admin").containsEntry("role", "ADMIN")
                .containsEntry("method", "PUT").containsEntry("entity_type", "settings")
                .containsEntry("entity_id", "agent.maxRetries").containsEntry("http_status", 200);

        List<String> columns = jdbc.queryForList("select column_name from information_schema.columns where "
                + "table_schema = 'console' and table_name = 'audit_log'", String.class);
        assertThat(columns).as("審計表只有「誰、對什麼、結果如何」，沒有任何放請求本文或參數值的欄位")
                .containsExactlyInAnyOrder("id", "occurred_at", "subject", "role", "method", "path", "entity_type",
                        "entity_id", "http_status", "trace_id");
    }
}
