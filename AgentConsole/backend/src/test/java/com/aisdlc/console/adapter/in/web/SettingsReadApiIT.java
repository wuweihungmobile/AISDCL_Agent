package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.domain.model.config.ConfigCatalog;
import com.aisdlc.console.domain.model.config.ConfigSpec;
import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.AppendixCImpactNotes;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 系統參數的讀取與驗證（API-SET-01／02／03；契約 §1.5.1～§1.5.3、附錄 C）。為什麼重要：50 個鍵的型別、範圍、預設與
 * 影響範圍提示是前端設定頁的唯一資料來源——程式內目錄（ConfigCatalog）與資料庫（V2＋V5）只要有一個鍵對不上，
 * 設定頁就會顯示錯的範圍或放行會讓引擎壞掉的值；範圍邊界（含「剛好超出一格」）一併逐鍵鎖住。
 */
class SettingsReadApiIT extends AbstractApiIT {

    private static final String BASE = "/api/v1/settings";
    private static final List<String> CATEGORIES = List.of("model", "agent", "execution", "monitor", "autoclaude", "sdd");

    private static Map<String, Object> config(Resp resp, String category, String key) {
        List<Map<String, Object>> found = resp.read("$.data." + category + "[?(@.key=='" + key + "')]");
        assertThat(found).as(category + "." + key).hasSize(1);
        return found.get(0);
    }

    private Resp put(String category, String key, String value) {
        return api.put(admin(), BASE + "/" + category + "/" + key, Map.of("value", value));
    }

    /** JSON 數字（Integer／Long／Double）與目錄的 BigDecimal 以數值相等比較（不計 scale）；目錄沒有就必須是 null。 */
    private static void assertSameNumber(Object actual, BigDecimal expected, String label) {
        if (expected == null) {
            assertThat(actual).as(label).isNull();
            return;
        }
        assertThat(actual).as(label).isNotNull();
        assertThat(new BigDecimal(String.valueOf(actual))).as(label).isEqualByComparingTo(expected);
    }

    // ── 分類與順序 ─────────────────────────────────────────────────────────────

    @Test
    void anyRoleSeesFiftyKeysInSixCategoriesWithTheDocumentedCountsAndOrder() {
        for (String token : List.of(viewer(), operator(), admin())) {
            Resp resp = api.get(token, BASE);
            assertThat(resp.status()).isEqualTo(200);
            String body = resp.body();
            int[] positions = CATEGORIES.stream().mapToInt(c -> body.indexOf("\"" + c + "\":[")).toArray();
            assertThat(positions).as("分類在回應中的出現順序").doesNotContain(-1).isSorted();
            assertThat(CATEGORIES.stream().map(c -> resp.<List<Object>>read("$.data." + c).size()).toList())
                    .containsExactly(10, 9, 10, 6, 11, 4);
        }
    }

    @Test
    void theKeysInsideEachCategoryFollowTheAppendixOrder() {
        Resp resp = api.get(viewer(), BASE);
        for (String category : CATEGORIES) {
            List<String> expected = ConfigCatalog.all().stream().filter(s -> s.category().equals(category))
                    .map(ConfigSpec::key).toList();
            assertThat(resp.<List<String>>read("$.data." + category + "[*].key")).as(category).isEqualTo(expected);
        }
    }

    @Test
    void theProgramCatalogAndTheDatabaseDescribeExactlyTheSameFiftyKeysKeyForKey() {
        Resp resp = api.get(viewer(), BASE);
        Set<String> fromApi = new LinkedHashSet<>();
        for (String category : CATEGORIES) {
            List<Map<String, Object>> items = resp.read("$.data." + category);
            for (Map<String, Object> item : items) {
                String key = (String) item.get("key");
                String full = category + "." + key;
                fromApi.add(full);
                ConfigSpec spec = ConfigCatalog.find(category, key)
                        .orElseThrow(() -> new AssertionError("資料庫有目錄沒有的鍵：" + full));
                assertThat(item.get("effect")).as(full + " effect").isEqualTo(spec.effect().name());
                assertSameNumber(item.get("min"), spec.min(), full + " min");
                assertSameNumber(item.get("max"), spec.max(), full + " max");
                Object options = item.get("options");
                assertThat(options == null ? List.of() : options).as(full + " options").isEqualTo(spec.options());
            }
        }
        Set<String> catalog = new LinkedHashSet<>();
        ConfigCatalog.all().forEach(s -> catalog.add(s.fullKey()));
        assertThat(fromApi).hasSize(50).isEqualTo(catalog);
    }

    @Test
    void everyKeyCarriesItsDescriptionRuleImpactNoteAndEffect() {
        Resp resp = api.get(viewer(), BASE);
        for (String category : CATEGORIES) {
            List<Map<String, Object>> items = resp.read("$.data." + category);
            for (Map<String, Object> item : items) {
                String full = category + "." + item.get("key");
                assertThat(item.get("description")).as(full + " description").asString().isNotBlank();
                assertThat(item.get("validationRule")).as(full + " validationRule").asString().isNotBlank();
                assertThat(item.get("impactNote")).as(full + " impactNote（US-S-08）").asString().isNotBlank();
                assertThat(item.get("effect")).as(full + " effect").isNotNull();
                assertThat(item.get("defaultValue")).as(full + " defaultValue").isNotNull();
                assertThat(item.get("updatedBy")).as(full + " 種子尚未被任何人改過").isNull();
            }
        }
    }

    /**
     * v1.3（D-11；附錄 C.1／C.2）：三個語意改變的鍵，從 API 看到的 {@code effect} 與 {@code impactNote} 就是契約寫的——前端設定頁的小標籤
     * 與寫入前的確認對話框只讀這兩個欄位。{@code effect} 說謊（例如把沒有開關的演化旗標標成 ENGINE），使用者就會以為關掉旗標能關掉
     * 引擎的行為；{@code impactNote} 沒更新，就還是 v1.2 的「Console 不送任何引擎設定」。
     */
    @Test
    void theThreeEngineFlagsShowTheirV13EffectAndTheVerbatimImpactNoteOfAppendixC() {
        Resp resp = api.get(viewer(), BASE);

        assertThat(config(resp, "model", "enableKernelBrain")).containsEntry("effect", "ENGINE")
                .containsEntry("impactNote", AppendixCImpactNotes.ENABLE_KERNEL_BRAIN);
        assertThat(config(resp, "agent", "enableAutoMutation")).containsEntry("effect", "ENGINE")
                .containsEntry("impactNote", AppendixCImpactNotes.ENABLE_AUTO_MUTATION);
        assertThat(config(resp, "agent", "enableSelfEvolution")).containsEntry("effect", "STORED_ONLY")
                .containsEntry("impactNote", AppendixCImpactNotes.ENABLE_SELF_EVOLUTION);
        assertThat(resp.<List<String>>read("$.data.*[?(@.effect=='UNVERIFIED')].key"))
                .as("UNVERIFIED 只剩 sdd 的三個鍵").containsExactlyInAnyOrder("specFormat", "workflowEngine",
                        "validationLevel");
    }

    /**
     * v1.4（D-17；附錄 C.5；E2E-16 第 1 列）：健康探測路徑的種子預設是深度探針 {@code /health/deep}，注意事項逐字等於契約。
     * 為什麼重要：舊預設 {@code /health} 只回答「Bridge 行程活著」，Bridge 裡資料庫或引擎載入壞了，Console 仍顯示引擎正常；預設值與說明
     * 沒有一起改，設定頁就會對著新的預設講舊的故事。
     */
    @Test
    void theHealthProbePathDefaultsToTheDeepProbeWithNoteC5() {
        Resp resp = api.get(viewer(), BASE);

        assertThat(config(resp, "autoclaude", "healthCheckPath")).containsEntry("value", "/health/deep")
                .containsEntry("defaultValue", "/health/deep")
                .containsEntry("impactNote", AppendixCImpactNotes.HEALTH_CHECK_PATH);
    }

    @Test
    void theSeededDefaultsFollowTheCorrectedValuesOfTheContract() {
        Resp resp = api.get(viewer(), BASE);

        Map<String, Object> compact = config(resp, "execution", "compactThresholdPct");
        assertThat(compact).containsEntry("value", "80").containsEntry("effect", "ENGINE");
        assertSameNumber(compact.get("min"), new BigDecimal("1"), "compact min");
        assertSameNumber(compact.get("max"), new BigDecimal("99"), "compact max");

        assertThat(config(resp, "model", "apiUrl")).containsEntry("defaultValue",
                "https://api.minimax.io/v1/text/chatcompletion_v2");
        assertThat(config(resp, "model", "name")).containsEntry("defaultValue", "MiniMax-M2.7");

        Map<String, Object> refresh = config(resp, "monitor", "refreshIntervalMs");
        assertThat(refresh).containsEntry("value", "10000").containsEntry("defaultValue", "10000");
        assertSameNumber(refresh.get("min"), new BigDecimal("10000"), "輪詢地板 10 秒（AR-06）");

        assertThat(config(resp, "autoclaude", "dalBackend")).containsEntry("value", "FILE");
        assertThat(config(resp, "execution", "autoResume")).containsEntry("value", "true");
        assertThat(config(resp, "execution", "maxAutoResumes")).containsEntry("value", "10");
        assertThat(config(resp, "model", "enableKernelBrain")).containsEntry("value", "false");
        assertThat(config(resp, "autoclaude", "claudeCommand")).containsEntry("value", "claude");
        assertThat(config(resp, "autoclaude", "claudeContinueFlag")).containsEntry("value", "--continue");
        assertThat(config(resp, "autoclaude", "claudeEncoding")).containsEntry("value", "utf-8");
        assertThat(config(resp, "autoclaude", "dualReadResolution")).containsEntry("value", "yaml_wins");
    }

    @Test
    void anEncryptedKeyIsAlwaysMaskedAndReportsWhetherItHasAValue() {
        Resp resp = api.get(viewer(), BASE);
        for (String[] key : new String[][] {{"model", "apiKey"}, {"autoclaude", "dbDsn"}}) {
            Map<String, Object> item = config(resp, key[0], key[1]);
            assertThat(item).containsEntry("value", "••••••••").containsEntry("isEncrypted", true)
                    .containsEntry("hasValue", false).containsEntry("valueType", "ENCRYPTED");
            assertThat(item).as("欄位名必須是 isEncrypted，不是 encrypted").doesNotContainKey("encrypted");
        }
        assertThat(config(resp, "model", "name")).containsEntry("isEncrypted", false).containsEntry("hasValue", true);
    }

    // ── 單一分類 ───────────────────────────────────────────────────────────────

    @Test
    void aSingleCategoryReturnsItsKeysAndAnUnknownCategoryIs404() {
        Resp resp = api.get(viewer(), BASE + "/monitor");
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<List<String>>read("$.data[*].key")).containsExactly("refreshIntervalMs",
                "alertConsecutiveFailures", "alertAgentTimeoutSec", "alertTaskDurationMultiplier",
                "enableEmailNotification", "notificationEmail");

        Resp missing = api.get(viewer(), BASE + "/nonexistent");
        assertThat(missing.status()).isEqualTo(404);
        assertThat(missing.<String>read("$.traceId")).isEqualTo(missing.header("X-Trace-Id"));
    }

    @Test
    void anonymousRequestsAreRejected() {
        assertThat(api.get(null, BASE).status()).isEqualTo(401);
        assertThat(api.get(null, BASE + "/model").status()).isEqualTo(401);
    }

    // ── 單鍵更新：型別、規則、範圍 ──────────────────────────────────────────────

    @Test
    void everyNumericKeyAcceptsItsDocumentedMinAndMaxAndRejectsOneStepOutside() {
        Resp listing = api.get(viewer(), BASE);
        int checked = 0;
        for (ConfigSpec spec : ConfigCatalog.all()) {
            boolean skipped = spec.min() == null || spec.max() == null
                    || ConfigCatalog.isTokenGuardKey(spec.category(), spec.key());
            if (skipped) {
                continue;
            }
            String type = (String) config(listing, spec.category(), spec.key()).get("valueType");
            boolean integral = type.equals("INTEGER") || type.equals("LONG");
            BigDecimal step = integral ? BigDecimal.ONE : new BigDecimal("0.01");
            String full = spec.fullKey();

            assertThat(put(spec.category(), spec.key(), spec.min().toPlainString()).status())
                    .as(full + " = min").isEqualTo(200);
            assertThat(put(spec.category(), spec.key(), spec.max().toPlainString()).status())
                    .as(full + " = max").isEqualTo(200);
            Resp below = put(spec.category(), spec.key(), spec.min().subtract(step).toPlainString());
            assertThat(below.status()).as(full + " = min - 1 格").isEqualTo(400);
            assertThat(below.<String>read("$.reason")).isEqualTo("參數值不符合型別或驗證規則");
            assertThat(put(spec.category(), spec.key(), spec.max().add(step).toPlainString()).status())
                    .as(full + " = max + 1 格").isEqualTo(400);
            checked++;
        }
        assertThat(checked).as("掃到的數值鍵數（model 5＋agent 7＋execution 5（含 globalTokenBudget）＋monitor 4）").isEqualTo(21);
    }

    @Test
    void globalTokenBudgetsDocumentedMaxIsTheLargestValueItsValidationRuleAccepts() {
        // B1-1（契約 v1.2）：目錄的 max 曾是 1000000000000（13 位），而 validation_rule {0,11} 最多容許 12 位——
        // GET /settings 報的 max 比實際接受的大 1，依文件填 max 的客戶端會被 400 擋下
        Resp listing = api.get(viewer(), BASE);
        assertThat(((Number) config(listing, "execution", "globalTokenBudget").get("max")).longValue())
                .isEqualTo(999_999_999_999L);
        assertThat(put("execution", "globalTokenBudget", "999999999999").status()).isEqualTo(200);
        assertThat(put("execution", "globalTokenBudget", "1").status()).isEqualTo(200);
        assertThat(put("execution", "globalTokenBudget", "0").status()).isEqualTo(400);
        assertThat(put("execution", "globalTokenBudget", "1000000000000").status()).isEqualTo(400);
    }

    @Test
    void everyEnumKeyAcceptsItsOptionsAndRejectsAnythingElseIncludingTheWrongCase() {
        Resp listing = api.get(viewer(), BASE);
        int checked = 0;
        for (ConfigSpec spec : ConfigCatalog.all()) {
            if (spec.options().isEmpty()) {
                continue;
            }
            assertThat(config(listing, spec.category(), spec.key())).containsEntry("valueType", "ENUM");
            for (String option : spec.options()) {
                assertThat(put(spec.category(), spec.key(), option).status()).as(spec.fullKey() + "=" + option)
                        .isEqualTo(200);
            }
            String first = spec.options().get(0);
            String wrongCase = first.equals(first.toLowerCase(Locale.ROOT)) ? first.toUpperCase(Locale.ROOT)
                    : first.toLowerCase(Locale.ROOT);
            Resp bad = put(spec.category(), spec.key(), wrongCase);
            assertThat(bad.status()).as(spec.fullKey() + "=" + wrongCase).isEqualTo(400);
            assertThat(bad.<String>read("$.errors[0].field")).isEqualTo("value");
            assertThat(put(spec.category(), spec.key(), "NOT_AN_OPTION").status()).isEqualTo(400);
            checked++;
        }
        assertThat(checked).isEqualTo(8);
    }

    @Test
    void booleanKeysOnlyTakeLowerCaseTrueOrFalse() {
        List<String> booleans = new ArrayList<>();
        Resp listing = api.get(viewer(), BASE);
        for (String category : CATEGORIES) {
            List<Map<String, Object>> items = listing.read("$.data." + category);
            items.stream().filter(i -> "BOOLEAN".equals(i.get("valueType")))
                    .forEach(i -> booleans.add(category + "/" + i.get("key")));
        }
        assertThat(booleans).hasSize(6);
        for (String path : booleans) {
            String[] parts = path.split("/");
            assertThat(put(parts[0], parts[1], "true").status()).as(path).isEqualTo(200);
            assertThat(put(parts[0], parts[1], "false").status()).as(path).isEqualTo(200);
            for (String bad : List.of("yes", "TRUE", "1", "")) {
                assertThat(put(parts[0], parts[1], bad).status()).as(path + "=" + bad).isEqualTo(400);
            }
        }
    }

    @Test
    void numbersMustBeWrittenCanonicallyAndNonNumbersAreRejectedWithTheFieldNamed() {
        for (String bad : List.of("abc", "", " 80", "80 ", "08", "1e2", "8.5", "+5", "0x10")) {
            Resp resp = put("execution", "logRetentionDays", bad);
            assertThat(resp.status()).as("logRetentionDays='" + bad + "'").isEqualTo(400);
            assertThat(resp.<String>read("$.reason")).isEqualTo("參數值不符合型別或驗證規則");
            assertThat(resp.<String>read("$.errors[0].field")).isEqualTo("value");
        }
        assertThat(put("model", "temperature", "abc").status()).isEqualTo(400);
        assertThat(put("model", "temperature", "1.").status()).isEqualTo(400);
        assertThat(put("model", "temperature", "0.75").status()).isEqualTo(200);
    }

    @Test
    void stringKeysAreCheckedAgainstTheirRulesIncludingTheCliCommandWithoutSpaces() {
        assertThat(put("autoclaude", "claudeCommand",
                "C:\\work\\repo\\.venv\\Scripts\\aisdlc-mock-claude.exe").status())
                .as("Windows 絕對路徑（反斜線、冒號、點、.exe）").isEqualTo(200);
        assertThat(put("autoclaude", "claudeCommand", "/usr/local/bin/aisdlc-mock-claude").status()).isEqualTo(200);
        Resp spaced = put("autoclaude", "claudeCommand", "C:\\Program Files\\x\\claude.exe");
        assertThat(spaced.status()).as("路徑含空白：引擎不對 claude.command 做 shlex 切分").isEqualTo(400);
        assertThat(spaced.<String>read("$.reason")).isEqualTo("參數值不符合型別或驗證規則");

        assertThat(put("autoclaude", "claudeContinueFlag", "--resume").status()).isEqualTo(200);
        assertThat(put("autoclaude", "claudeContinueFlag", "resume").status()).isEqualTo(400);
        assertThat(put("autoclaude", "claudeEncoding", "cp950").status()).isEqualTo(200);
        assertThat(put("autoclaude", "claudeEncoding", "bad encoding").status()).isEqualTo(400);
        assertThat(put("autoclaude", "claudeExtraArgs", "--model sonnet --verbose").status()).isEqualTo(200);
        assertThat(put("autoclaude", "claudeExtraArgs", "--x; rm -rf /").status()).isEqualTo(400);
        assertThat(put("autoclaude", "engineUrl", "http://engine-bridge:8081").status()).isEqualTo(200);
        assertThat(put("autoclaude", "engineUrl", "ftp://engine-bridge").status()).isEqualTo(400);
        assertThat(put("autoclaude", "healthCheckPath", "/health").status()).isEqualTo(200);
        assertThat(put("autoclaude", "healthCheckPath", "/health/deep").status()).as("新的種子預設本身通過驗證")
                .isEqualTo(200);
        assertThat(put("autoclaude", "healthCheckPath", "health").status()).isEqualTo(400);
        assertThat(put("monitor", "notificationEmail", "ops@example.com").status()).isEqualTo(200);
        assertThat(put("monitor", "notificationEmail", "").status()).as("空字串＝沒有設定").isEqualTo(200);
        assertThat(put("monitor", "notificationEmail", "not-an-email").status()).isEqualTo(400);
        assertThat(put("model", "name", "MiniMax-M2.7").status()).isEqualTo(200);
        assertThat(put("model", "name", "bad name!").status()).isEqualTo(400);
    }

    @Test
    void anUnknownKeyIs404BeforeAnyValueCheck() {
        assertThat(put("model", "nonexistent", "x").status()).isEqualTo(404);
        assertThat(put("nonexistent", "name", "x").status()).isEqualTo(404);
    }

    @Test
    void aBodyWithoutValueOrWithATooLongValueIs400() {
        Resp missing = api.put(admin(), BASE + "/model/name", Map.of("confirm", true));
        assertThat(missing.status()).isEqualTo(400);
        assertThat(missing.<String>read("$.errors[0].field")).isEqualTo("value");

        Resp tooLong = put("model", "name", "a".repeat(4001));
        assertThat(tooLong.status()).isEqualTo(400);
        assertThat(tooLong.<String>read("$.errors[0].field")).isEqualTo("value");
    }

    @Test
    void aSuccessfulUpdateRecordsWhoChangedItAndWhenAndReturnsTheNewView() {
        Resp resp = put("agent", "maxRetries", "5");
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.value")).isEqualTo("5");
        assertThat(resp.<String>read("$.data.updatedBy")).isEqualTo("admin");
        assertThat(resp.<String>read("$.data.updatedAt")).isNotBlank();
        assertThat(resp.<String>read("$.data.defaultValue")).isEqualTo("3");

        Resp reread = api.get(viewer(), BASE + "/agent");
        assertThat(reread.<List<Map<String, Object>>>read("$.data[?(@.key=='maxRetries')]").get(0))
                .containsEntry("value", "5").containsEntry("updatedBy", "admin");
    }
}
