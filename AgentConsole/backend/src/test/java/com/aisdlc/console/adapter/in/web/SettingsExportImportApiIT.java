package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 設定匯出入與 SEC-04 儲存時檢查（API-SET-08／09、API-SET-03；契約 §1.5.9、§1.5.10、E2E-09 步驟 12～15）。
 * 為什麼重要：匯出檔會被拿去備份、貼進工單、交給別人——任何一個加密值（含密文）漏進去就是外洩；匯入是「一次改很多鍵」的入口，
 * 逐筆驗證、token_guard 成對校驗與 SSRF allowlist 都不能因為走檔案而被繞過；部分失敗必須逐筆交代原因，而不是全有或全無。
 */
class SettingsExportImportApiIT extends AbstractApiIT {

    private static final String BASE = "/api/v1/settings";
    private static final String INVALID = "參數值不符合型別或驗證規則";
    private static final String GUARD_REASON = "halt_threshold_pct 必須大於 compact_threshold_pct";
    private static final String OUTBOUND = "目標位址未通過 SSRF／allowlist 檢查";

    private static Map<String, Object> item(String category, String key, String value) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("category", category);
        item.put("key", key);
        item.put("value", value);
        return item;
    }

    private static String documentOf(Object version, List<Map<String, Object>> items) {
        Map<String, Object> doc = new LinkedHashMap<>();
        doc.put("version", version);
        doc.put("configs", items);
        return ApiClient.toJson(doc);
    }

    @SafeVarargs
    private static String document(Object version, Map<String, Object>... items) {
        return documentOf(version, List.of(items));
    }

    private Resp importJson(String json) {
        return api.multipart(admin(), BASE + "/import", "file", "settings.json", "application/json",
                json.getBytes(StandardCharsets.UTF_8));
    }

    private String dbValue(String category, String key) {
        return jdbc.queryForObject("select value from console.system_configs where category = ? and key = ?",
                String.class, category, key);
    }

    private int historyCount() {
        return jdbc.queryForObject("select count(*) from console.system_config_history", Integer.class);
    }

    /** 目前匯出檔的全部項目（可原樣改幾個值再匯入）。 */
    private List<Map<String, Object>> exportedItems() {
        Resp export = api.post(admin(), BASE + "/export");
        assertThat(export.status()).isEqualTo(200);
        List<Map<String, Object>> configs = export.read("$.configs");
        return new ArrayList<>(configs);
    }

    // ── 匯出 ─────────────────────────────────────────────────────────────────

    @Test
    void exportIsABareJsonFileWithAllFiftyKeysAndNeverContainsAnEncryptedValue() {
        assertThat(api.put(admin(), BASE + "/model/apiKey", Map.of("value", "sk-export-me", "confirm", true))
                .status()).isEqualTo(200);
        assertThat(api.put(admin(), BASE + "/autoclaude/dbDsn", Map.of("value", "postgresql://u:pw@h/db",
                "confirm", true)).status()).isEqualTo(200);

        Resp export = api.post(admin(), BASE + "/export");

        assertThat(export.status()).isEqualTo(200);
        assertThat(export.header("Content-Type")).startsWith("application/json");
        assertThat(export.header("Content-Disposition")).startsWith("attachment").contains("aisdlc-settings-")
                .endsWith(".json\"");
        assertThat(export.header("Cache-Control")).contains("no-store");
        assertThat(export.<Integer>read("$.version")).isEqualTo(1);
        assertThat(export.<String>read("$.exportedAt")).endsWith("Z");
        assertThat(export.has("$.data")).as("不包 ApiResult 封包，直接是檔案").isFalse();
        assertThat(export.<List<Object>>read("$.configs")).hasSize(50);
        assertThat(export.<List<String>>read("$.configs[?(@.key=='apiKey')].value")).containsExactly("<encrypted>");
        assertThat(export.<List<String>>read("$.configs[?(@.key=='dbDsn')].value")).containsExactly("<encrypted>");
        assertThat(export.body()).doesNotContain("sk-export-me").doesNotContain("postgresql://").doesNotContain("v1:");
        assertThat(export.<List<String>>read("$.configs[?(@.key=='compactThresholdPct')].value"))
                .containsExactly("80");
    }

    @Test
    void exportedDocumentRoundTripsAsAnImportThatChangesNothing() {
        Resp resp = importJson(documentOf(1, exportedItems()));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Integer>read("$.data.applied")).isZero();
        assertThat(resp.<Integer>read("$.data.skipped")).isEqualTo(50);
        assertThat(resp.<List<Object>>read("$.data.errors")).isEmpty();
        assertThat(historyCount()).isZero();
    }

    @Test
    void anUnchangedValueIsSkippedEvenWhenItsHostIsNotOnTheAllowlistButAChangedOneStillIsRejected() {
        // DEF-AC-002（C-6）：e2e 的 allowlist 不含預設的 api.minimax.io——現值的主機不在白名單時，匯出再原樣匯入也不得出現 errors
        jdbc.update("update console.system_configs set value = ? where category = 'model' and key = 'apiUrl'",
                "https://not-listed.example/v1/chat");
        List<Map<String, Object>> items = exportedItems();

        Resp unchanged = importJson(documentOf(1, items));

        assertThat(unchanged.status()).isEqualTo(200);
        assertThat(unchanged.<Integer>read("$.data.applied")).isZero();
        assertThat(unchanged.<Integer>read("$.data.skipped")).as("2 筆加密佔位＋48 筆值未變").isEqualTo(50);
        assertThat(unchanged.<List<Object>>read("$.data.errors")).isEmpty();
        assertThat(historyCount()).isZero();

        items.stream().filter(i -> "apiUrl".equals(i.get("key"))).forEach(i -> i.put("value",
                "https://other-unlisted.example/v1/chat"));
        Resp changed = importJson(documentOf(1, items));

        assertThat(changed.<List<String>>read("$.data.errors[*].key")).containsExactly("apiUrl");
        assertThat(changed.<List<String>>read("$.data.errors[*].reason")).containsExactly(OUTBOUND);
        assertThat(changed.<Integer>read("$.data.applied")).isZero();
        assertThat(changed.<Integer>read("$.data.skipped")).isEqualTo(49);
        assertThat(dbValue("model", "apiUrl")).isEqualTo("https://not-listed.example/v1/chat");
        assertThat(historyCount()).isZero();
    }

    @Test
    void anUnchangedButNowInvalidStoredValueIsSkippedNotReportedAsAnError() {
        // 值規則只判「要寫入的新值」：現值本身即使不符規則（例：升級前的殘值），原樣匯入也只是略過
        jdbc.update("update console.system_configs set value = 'abc' where category = 'agent' and key = 'maxRetries'");

        Resp resp = importJson(documentOf(1, exportedItems()));

        assertThat(resp.<List<Object>>read("$.data.errors")).isEmpty();
        assertThat(resp.<Integer>read("$.data.applied")).isZero();
        assertThat(resp.<Integer>read("$.data.skipped")).isEqualTo(50);
    }

    // ── 匯入：逐筆驗證與套用 ────────────────────────────────────────────────────

    @Test
    void aChangedValueIsAppliedAndTheRestIsSkippedWithOneHistoryRow() {
        List<Map<String, Object>> items = exportedItems();
        items.stream().filter(i -> "refreshIntervalMs".equals(i.get("key"))).forEach(i -> i.put("value", "15000"));

        Resp resp = importJson(documentOf(1, items));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Integer>read("$.data.applied")).isEqualTo(1);
        assertThat(resp.<Integer>read("$.data.skipped")).as("2 筆加密佔位＋47 筆值未變").isEqualTo(49);
        assertThat(resp.<List<Object>>read("$.data.errors")).isEmpty();
        assertThat(dbValue("monitor", "refreshIntervalMs")).isEqualTo("15000");
        assertThat(historyCount()).isEqualTo(1);
        Resp history = api.get(viewer(), BASE + "/history?category=monitor&key=refreshIntervalMs");
        assertThat(history.<String>read("$.data.content[0].oldValue")).isEqualTo("10000");
        assertThat(history.<String>read("$.data.content[0].newValue")).isEqualTo("15000");
        assertThat(history.<String>read("$.data.content[0].changedBy")).isEqualTo("admin");
    }

    @Test
    void anInvalidEntryDoesNotBlockTheValidOnesAndIsReportedWithItsReason() {
        Resp resp = importJson(document(1,
                item("monitor", "refreshIntervalMs", "900"),
                item("agent", "maxRetries", "5"),
                item("agent", "maxConcurrentTasks", "abc"),
                item("model", "provider", "BOGUS")));

        assertThat(resp.status()).as("部分失敗仍是 200").isEqualTo(200);
        assertThat(resp.<Integer>read("$.data.applied")).isEqualTo(1);
        assertThat(resp.<List<String>>read("$.data.errors[*].key")).containsExactly("refreshIntervalMs",
                "maxConcurrentTasks", "provider");
        assertThat(resp.<List<String>>read("$.data.errors[*].reason")).containsOnly(INVALID);
        assertThat(resp.<String>read("$.data.errors[0].category")).isEqualTo("monitor");
        assertThat(dbValue("agent", "maxRetries")).isEqualTo("5");
        assertThat(dbValue("monitor", "refreshIntervalMs")).isEqualTo("10000");
        assertThat(historyCount()).isEqualTo(1);
    }

    @Test
    void anUnknownKeyOrCategoryIsReportedAndTheLastDuplicateWins() {
        Resp resp = importJson(document(1,
                item("agent", "doesNotExist", "1"),
                item("nope", "maxRetries", "1"),
                item("agent", "maxRetries", "4"),
                item("agent", "maxRetries", "6")));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<List<String>>read("$.data.errors[*].reason")).containsOnly("設定鍵不存在");
        assertThat(resp.<List<String>>read("$.data.errors[*].key")).containsExactly("doesNotExist", "maxRetries");
        assertThat(resp.<Integer>read("$.data.applied")).isEqualTo(1);
        assertThat(dbValue("agent", "maxRetries")).as("同一鍵出現多次以最後一筆為準").isEqualTo("6");
        assertThat(historyCount()).isEqualTo(1);
    }

    @Test
    void tokenGuardIsCheckedOnTheMergedFinalValuesAndAViolationAppliesNeitherKey() {
        Resp reversed = importJson(document(1, item("execution", "compactThresholdPct", "90"),
                item("execution", "haltThresholdPct", "80"), item("agent", "maxRetries", "5")));
        assertThat(reversed.status()).isEqualTo(200);
        assertThat(reversed.<List<String>>read("$.data.errors[*].key")).containsExactly("compactThresholdPct",
                "haltThresholdPct");
        assertThat(reversed.<List<String>>read("$.data.errors[*].reason")).containsOnly(GUARD_REASON);
        assertThat(reversed.<Integer>read("$.data.applied")).as("同檔其他合法鍵照常套用").isEqualTo(1);
        assertThat(dbValue("execution", "compactThresholdPct")).isEqualTo("80");
        assertThat(dbValue("execution", "haltThresholdPct")).isEqualTo("90");

        Resp oneSide = importJson(document(1, item("execution", "compactThresholdPct", "95")));
        assertThat(oneSide.<List<String>>read("$.data.errors[*].key")).as("只給一邊時對端以目前值（90）校驗")
                .containsExactly("compactThresholdPct", "haltThresholdPct");
        assertThat(oneSide.<Integer>read("$.data.applied")).isZero();
        assertThat(dbValue("execution", "compactThresholdPct")).isEqualTo("80");

        Resp valid = importJson(document(1, item("execution", "compactThresholdPct", "70"),
                item("execution", "haltThresholdPct", "95")));
        assertThat(valid.<Integer>read("$.data.applied")).isEqualTo(2);
        assertThat(valid.<List<Object>>read("$.data.errors")).isEmpty();
        assertThat(dbValue("execution", "compactThresholdPct")).isEqualTo("70");
        assertThat(dbValue("execution", "haltThresholdPct")).isEqualTo("95");
    }

    @Test
    void encryptedKeysCanNeverBeSetByImportButPlaceholdersAreSkipped() {
        assertThat(api.put(admin(), BASE + "/model/apiKey", Map.of("value", "sk-keep", "confirm", true)).status())
                .isEqualTo(200);
        String before = dbValue("model", "apiKey");
        int historyBefore = historyCount();

        Resp resp = importJson(document(1, item("model", "apiKey", "sk-from-file"),
                item("autoclaude", "dbDsn", "<encrypted>")));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Integer>read("$.data.applied")).isZero();
        assertThat(resp.<Integer>read("$.data.skipped")).isEqualTo(1);
        assertThat(resp.<List<String>>read("$.data.errors[*].key")).containsExactly("apiKey");
        assertThat(resp.<List<String>>read("$.data.errors[*].reason"))
                .containsExactly("敏感參數更新需二次確認（confirm=true）");
        assertThat(dbValue("model", "apiKey")).isEqualTo(before);
        assertThat(historyCount()).isEqualTo(historyBefore);
        assertThat(resp.body()).doesNotContain("sk-from-file").doesNotContain("sk-keep");
    }

    @Test
    void importedApiUrlsGoThroughTheSameAllowlistAsASingleUpdate() {
        Resp resp = importJson(document(1, item("model", "apiUrl", "http://10.0.0.5/v1/chat/completions")));
        assertThat(resp.<List<String>>read("$.data.errors[*].reason")).containsExactly(OUTBOUND);
        assertThat(dbValue("model", "apiUrl")).isEqualTo("https://api.minimax.io/v1/text/chatcompletion_v2");

        Resp ok = importJson(document(1, item("model", "apiUrl", "https://api.minimax.chat/v1/chat/completions")));
        assertThat(ok.<Integer>read("$.data.applied")).isEqualTo(1);
        assertThat(dbValue("model", "apiUrl")).isEqualTo("https://api.minimax.chat/v1/chat/completions");
    }

    @Test
    void anEmptyConfigsArrayIsAValidFileThatDoesNothing() {
        Resp resp = importJson(document(1));
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Integer>read("$.data.applied")).isZero();
        assertThat(resp.<Integer>read("$.data.skipped")).isZero();
    }

    // ── 匯入：檔案層檢查 ────────────────────────────────────────────────────────

    private void assertFormatError(Resp resp, String problem) {
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.<String>read("$.reason")).isEqualTo("設定檔格式錯誤");
        assertThat(resp.<String>read("$.details.problem")).isEqualTo(problem);
        assertThat(resp.<String>read("$.errors[0].field")).isEqualTo("file");
        assertThat(historyCount()).isZero();
    }

    @Test
    void malformedFilesAreRejectedWithTheirSpecificProblemAndChangeNothing() {
        assertFormatError(importJson(document(2, item("agent", "maxRetries", "5"))), "unsupported_version");
        assertFormatError(importJson(document("1", item("agent", "maxRetries", "5"))), "unsupported_version");
        assertFormatError(importJson(document(1.5, item("agent", "maxRetries", "5"))), "unsupported_version");
        assertFormatError(importJson("{\"configs\":[]}"), "unsupported_version");
        assertFormatError(importJson("this is not json"), "invalid_json");
        assertFormatError(importJson("[1,2,3]"), "invalid_json");
        assertFormatError(importJson(""), "invalid_json");
        assertFormatError(importJson("{\"version\":1}"), "missing_configs");
        assertFormatError(importJson("{\"version\":1,\"configs\":{}}"), "missing_configs");
        assertFormatError(importJson("{\"version\":1,\"configs\":[{\"category\":\"agent\",\"key\":\"maxRetries\"}]}"),
                "missing_configs");
        assertFormatError(importJson("{\"version\":1,\"configs\":[\"agent.maxRetries\"]}"), "missing_configs");
        assertFormatError(importJson("{\"version\":1,\"configs\":[{\"category\":\"agent\",\"key\":\"maxRetries\","
                + "\"value\":{\"a\":1}}]}"), "missing_configs");
        assertThat(dbValue("agent", "maxRetries")).isEqualTo("3");
    }

    @Test
    void aFileOverOneMegabyteIsRejectedBeforeItIsParsed() {
        byte[] huge = new byte[2 * 1024 * 1024];
        Arrays.fill(huge, (byte) 'x');
        Resp resp = api.multipart(admin(), BASE + "/import", "file", "settings.json", "application/json", huge);

        assertThat(resp.status()).isEqualTo(413);
        assertThat(resp.<String>read("$.reason")).isEqualTo("設定檔超過 1MB 上限");
        assertThat(resp.<Integer>read("$.details.limitBytes")).isEqualTo(1_048_576);
    }

    @Test
    void onlyJsonFilesAreAccepted() {
        byte[] content = "{\"version\":1,\"configs\":[]}".getBytes(StandardCharsets.UTF_8);
        for (String[] bad : new String[][] {{"settings.txt", "text/plain"}, {"settings.json", "text/plain"},
                {"settings.json", "image/png"}, {"settings", "application/json"}, {"settings.json.exe", "application/json"}}) {
            Resp resp = api.multipart(admin(), BASE + "/import", "file", bad[0], bad[1], content);
            assertThat(resp.status()).as(bad[0] + " " + bad[1]).isEqualTo(415);
            assertThat(resp.<String>read("$.reason")).isEqualTo("只接受 JSON 設定檔");
        }
        for (String[] good : new String[][] {{"settings.json", "application/json"},
                {"SETTINGS.JSON", "application/octet-stream"}, {"s.json", "application/vnd.api+json"}}) {
            assertThat(api.multipart(admin(), BASE + "/import", "file", good[0], good[1], content).status())
                    .as(good[0] + " " + good[1]).isEqualTo(200);
        }
    }

    @Test
    void aRequestWithoutAFilePartIs400() {
        Resp resp = api.multipartWithoutParts(admin(), BASE + "/import");
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.<String>read("$.reason")).isEqualTo("未提供檔案");
    }

    // ── SEC-04：儲存 model.apiUrl 時的 allowlist 檢查 ────────────────────────────

    private Resp putApiUrl(String url) {
        return api.put(admin(), BASE + "/model/apiUrl", Map.of("value", url));
    }

    private void assertRejectedOnSave(String url, String violation) {
        Resp resp = putApiUrl(url);
        assertThat(resp.status()).as(url).isEqualTo(400);
        assertThat(resp.<String>read("$.reason")).as(url).isEqualTo(OUTBOUND);
        assertThat(resp.<String>read("$.details.violation")).as(url).isEqualTo(violation);
        assertThat(resp.<String>read("$.errors[0].field")).isEqualTo("value");
        assertThat(dbValue("model", "apiUrl")).as("被拒絕的值不得入庫")
                .isEqualTo("https://api.minimax.io/v1/text/chatcompletion_v2");
        assertThat(historyCount()).isZero();
    }

    @Test
    void anApiUrlThatPointsAtAnInternalOrUnlistedHostIsRejectedOnSaveWithTheViolationNamed() {
        assertRejectedOnSave("http://10.0.0.5", "private_ip");
        assertRejectedOnSave("http://192.168.1.1/v1", "private_ip");
        assertRejectedOnSave("http://172.16.0.9/v1", "private_ip");
        assertRejectedOnSave("http://100.64.0.1/v1", "private_ip");
        assertRejectedOnSave("http://169.254.169.254/latest/meta-data", "link_local");
        assertRejectedOnSave("http://127.0.0.1:8080/v1/chat/completions", "loopback");
        assertRejectedOnSave("http://[::1]:8080/v1", "loopback");
        assertRejectedOnSave("https://example.com", "not_in_allowlist");
        assertRejectedOnSave("http://localhost.evil.example/v1", "not_in_allowlist");
        assertRejectedOnSave("http://user:your_password_here@api.minimax.io/v1/text/chatcompletion_v2", "userinfo");
        assertRejectedOnSave("http://0x7f.0.0.1/v1", "malformed_url");
        assertRejectedOnSave("http://2130706433/v1", "malformed_url");
        assertRejectedOnSave("http://exämple.com/v1", "malformed_url");
    }

    @Test
    void aRejectedSaveReportsTheHostOnlyWhenItWasParsedAndNeverTheUserinfo() {
        Resp withHost = putApiUrl("http://10.0.0.5/v1");
        assertThat(withHost.<String>read("$.details.host")).isEqualTo("10.0.0.5");

        Resp malformed = putApiUrl("http://0x7f.0.0.1/v1");
        assertThat(malformed.has("$.details.host")).as("host 無法解析時該鍵缺席（details 不輸出 null）").isFalse();

        Resp userinfo = putApiUrl("http://admin:your_password_here@10.0.0.5/v1");
        assertThat(userinfo.body()).doesNotContain("your_password_here");
    }

    @Test
    void aNonHttpUrlFailsTheValueRuleBeforeTheOutboundCheck() {
        Resp resp = putApiUrl("ftp://api.minimax.io/v1/text/chatcompletion_v2");
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.<String>read("$.reason")).isEqualTo(INVALID);
    }

    @Test
    void anAllowlistedHttpsEndpointIsAcceptedAsTheFullEndpointWithoutAnyPathBeingAdded() {
        for (String ok : List.of("https://api.minimax.io/v1/text/chatcompletion_v2", "https://API.MINIMAX.IO/v1/x",
                "https://api.minimax.chat/v1/chat/completions", "http://api.minimax.io:8443/custom/path")) {
            Resp resp = putApiUrl(ok);
            assertThat(resp.status()).as(ok).isEqualTo(200);
            assertThat(resp.<String>read("$.data.value")).as("原樣儲存，後端不補路徑").isEqualTo(ok);
        }
    }
}
