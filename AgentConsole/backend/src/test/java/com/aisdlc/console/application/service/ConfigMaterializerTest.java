package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.RuntimeSettings;
import com.aisdlc.console.application.port.out.SecretCipher;
import com.aisdlc.console.application.service.ConfigMaterializer.Materialized;
import com.aisdlc.console.domain.model.config.ConfigValueType;
import com.aisdlc.console.domain.model.execution.EngineCapabilities;
import com.aisdlc.console.domain.model.execution.EngineCapabilityState;
import com.aisdlc.console.support.InMemorySystemConfigRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.util.List;
import java.util.Map;

import static com.aisdlc.console.domain.model.execution.EngineCapabilityState.ENABLED;
import static com.aisdlc.console.domain.model.execution.EngineCapabilityState.OFF;
import static com.aisdlc.console.domain.model.execution.EngineCapabilityState.UNAVAILABLE_NO_API_KEY;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * 系統參數與自治等級 → Bridge 的 {@code config_overrides}／{@code env}／{@code engineCapabilities}（契約 §3.4.2、NFR-SEC-05）。
 * 為什麼重要：這是整個後端唯一把「機密」送出 Console 的地方——API Key 若漏進 {@code config_overrides}，就會被 Bridge 寫進 run 目錄的設定檔與日誌；
 * 若把 {@code token_guard.enabled} 也送出去，使用者就能經由系統設定關掉安全收斂；而 {@code enable_kernel_brain=true} 在沒有金鑰時
 * 會讓引擎啟動即失敗、批次一開始就 FAILED，所以「有金鑰才送」與「回報的能力等於實際送出的」兩條規則一旦寫反，使用者看到的是
 * 一個說謊的畫面或一個起不來的批次。
 */
class ConfigMaterializerTest {

    // 刻意不用 sk- 前綴：根層 pre-commit 機密掃描會把 openai／minimax 形態的字串當真值擋下 commit。
    private static final String SECRET = "your_api_key_here_test_fixture_0123456789";

    /** 契約 §3.4.2「永不送」的鍵（任何等級、任何旗標組合都不得出現在 {@code config_overrides}）。 */
    private static final List<String> NEVER_SENT = List.of("max_evolutions", "require_evolution_signoff",
            "enable_rtm_feedback", "goal_synthesis_enabled", "enable_translation_auto_propose");

    private final InMemorySystemConfigRepository repository = new InMemorySystemConfigRepository();
    private final RuntimeSettings runtime = mock(RuntimeSettings.class);
    private final SecretCipher cipher = new SecretCipher() {
        @Override
        public String encrypt(String plainText) {
            return "enc:" + plainText;
        }

        @Override
        public String decrypt(String stored) {
            return stored.substring("enc:".length());
        }
    };
    private ConfigMaterializer materializer;

    @BeforeEach
    void setUp() {
        repository.with("autoclaude", "claudeCommand", ConfigValueType.STRING, "claude")
                .with("autoclaude", "claudeExtraArgs", ConfigValueType.STRING, "")
                .with("autoclaude", "claudeContinueFlag", ConfigValueType.STRING, "--continue")
                .with("autoclaude", "claudeEncoding", ConfigValueType.STRING, "utf-8")
                .with("agent", "taskTimeout", ConfigValueType.INTEGER, "600")
                .with("agent", "enableAutoMutation", ConfigValueType.BOOLEAN, "false")
                .with("agent", "enableSelfEvolution", ConfigValueType.BOOLEAN, "false")
                .with("execution", "compactThresholdPct", ConfigValueType.INTEGER, "80")
                .with("execution", "haltThresholdPct", ConfigValueType.INTEGER, "90")
                .with("execution", "autoResume", ConfigValueType.BOOLEAN, "true")
                .with("execution", "maxAutoResumes", ConfigValueType.INTEGER, "10")
                .withEncrypted("model", "apiKey", "")
                .with("model", "apiUrl", ConfigValueType.STRING, "https://api.minimax.io/v1/text/chatcompletion_v2")
                .with("model", "name", ConfigValueType.STRING, "MiniMax-M2.7")
                .with("model", "timeout", ConfigValueType.INTEGER, "60")
                .with("model", "enableKernelBrain", ConfigValueType.BOOLEAN, "false");
        when(runtime.mockEnv()).thenReturn(Map.of());
        materializer = new ConfigMaterializer(new SettingsReader(repository, cipher), runtime);
    }

    private void storeApiKey() {
        repository.withEncrypted("model", "apiKey", "enc:" + SECRET);
    }

    private void clearApiKey() {
        repository.withEncrypted("model", "apiKey", "");
    }

    private void flags(boolean autoMutation, boolean selfEvolution, boolean kernelBrain) {
        repository.set("agent", "enableAutoMutation", String.valueOf(autoMutation));
        repository.set("agent", "enableSelfEvolution", String.valueOf(selfEvolution));
        repository.set("model", "enableKernelBrain", String.valueOf(kernelBrain));
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> block(Materialized m, String name) {
        return (Map<String, Object>) m.configOverrides().get(name);
    }

    private static EngineCapabilities caps(EngineCapabilityState autoMutation, EngineCapabilityState selfEvolution) {
        return new EngineCapabilities(autoMutation, selfEvolution);
    }

    /** 巢狀 Map／List 內任何一層是否含這個鍵名。 */
    private static boolean containsKeyDeep(Object node, String key) {
        if (node instanceof Map<?, ?> map) {
            return map.containsKey(key) || map.values().stream().anyMatch(v -> containsKeyDeep(v, key));
        }
        if (node instanceof List<?> list) {
            return list.stream().anyMatch(v -> containsKeyDeep(v, key));
        }
        return false;
    }

    // ── 既有規則（機密、安全收斂、只送 Console 擁有的鍵）──────────────────────────────

    @Test
    void theApiKeyOnlyTravelsInTheEnvAndNeverInsideTheConfigOverrides() {
        storeApiKey();

        Materialized m = materializer.materialize(3);

        assertThat(m.env()).containsEntry("MINIMAX_API_KEY", SECRET);
        assertThat(m.configOverrides().toString()).as("機密不得出現在會落地的設定裡").doesNotContain(SECRET)
                .doesNotContain("api_key");
        Map<String, Object> minimax = block(m, "minimax");
        assertThat(minimax).containsEntry("base_url", "https://api.minimax.io/v1/text/chatcompletion_v2")
                .containsEntry("model", "MiniMax-M2.7").containsEntry("timeout_seconds", 60)
                .containsEntry("enable_kernel_brain", false).doesNotContainKey("api_key");
    }

    @Test
    void withoutAnApiKeyThereIsNeitherAMinimaxBlockNorAKeyInTheEnv() {
        Materialized m = materializer.materialize(3);

        assertThat(m.configOverrides()).doesNotContainKey("minimax");
        assertThat(m.env()).doesNotContainKey("MINIMAX_API_KEY");
    }

    @Test
    void theEngineIsToldOnlyWhatConsoleOwnsAndTheSafetyGuardCannotBeSwitchedOffThroughSettings() {
        Materialized m = materializer.materialize(3);

        assertThat(m.configOverrides()).containsOnlyKeys("claude", "playbook", "token_guard");
        assertThat(block(m, "claude")).containsEntry("command", "claude").containsEntry("continue_flag", "--continue")
                .containsEntry("encoding", "utf-8").doesNotContainKey("extra_args");
        assertThat(m.configOverrides().get("playbook")).isEqualTo(Map.of("step_timeout_seconds", 600));
        assertThat(block(m, "token_guard")).containsOnlyKeys("compact_threshold_pct", "halt_threshold_pct",
                "auto_resume", "max_auto_resumes").doesNotContainKey("enabled")
                .containsEntry("compact_threshold_pct", 80).containsEntry("halt_threshold_pct", 90)
                .containsEntry("auto_resume", true).containsEntry("max_auto_resumes", 10);
    }

    @Test
    void theMockEnvOfTheTestProfilesIsMergedIntoTheEnv() {
        storeApiKey();
        when(runtime.mockEnv()).thenReturn(Map.of("MOCK_CLAUDE_DELAY", "0.6"));

        Materialized m = materializer.materialize(3);

        assertThat(m.env()).containsEntry("MOCK_CLAUDE_DELAY", "0.6").containsEntry("MINIMAX_API_KEY", SECRET);
    }

    @Test
    void everyCallReadsTheCurrentValuesSoANewRunPicksUpEditedSettings() {
        assertThat(block(materializer.materialize(3), "token_guard")).containsEntry("halt_threshold_pct", 90);

        repository.set("execution", "haltThresholdPct", "95");
        repository.set("agent", "taskTimeout", "1200");
        Materialized after = materializer.materialize(3);

        assertThat(block(after, "token_guard")).containsEntry("halt_threshold_pct", 95);
        assertThat(after.configOverrides().get("playbook")).isEqualTo(Map.of("step_timeout_seconds", 1200));
    }

    @Test
    void extraArgsAreSplitOnWhitespaceAndFragmentsWithUnsafeCharactersAreDropped() {
        repository.set("autoclaude", "claudeExtraArgs", "  --model   sonnet --bad;rm $(whoami) --max-turns=3 ");

        Map<String, Object> claude = block(materializer.materialize(3), "claude");

        assertThat(claude.get("extra_args")).as("只留白名單字元（設定驗證本應先擋，這裡是第二道）")
                .isEqualTo(List.of("--model", "sonnet", "--max-turns=3"));
    }

    @Test
    void blankExtraArgsGiveNoArguments() {
        assertThat(ConfigMaterializer.extraArgs(null)).isEmpty();
        assertThat(ConfigMaterializer.extraArgs("   ")).isEmpty();
        assertThat(ConfigMaterializer.extraArgs("--flag")).containsExactly("--flag");
        assertThat(ConfigMaterializer.extraArgs("a/b:c,d@e=f")).containsExactly("a/b:c,d@e=f");
        assertThat(ConfigMaterializer.extraArgs("`id` \"quoted\" a|b")).isEmpty();
    }

    // ── D-11：決策表（契約 §3.4.2）──────────────────────────────────────────────────

    /**
     * 決策表 8 列（契約 §3.4.2）：等級 3、{@code agent.enableAutoMutation=false}，所以 {@code brainRequested} 只由
     * {@code model.enableKernelBrain} 決定、{@code effSelfEvolution} 只由 {@code agent.enableSelfEvolution} 決定。
     * {@code kernelBrain} 欄是「有金鑰時送出的 {@code enable_kernel_brain}」；沒有金鑰的列一律不送 {@code minimax.*}。
     */
    @ParameterizedTest(name = "列 {0}：有金鑰={1}、brain={2}、自演化={3} → {4}／{5}")
    @CsvSource({
            "1,true,true,true,ENABLED,ENABLED,true",
            "2,true,true,false,ENABLED,ENABLED,true",
            "3,true,false,true,OFF,ENABLED,false",
            "4,true,false,false,OFF,ENABLED,false",
            "5,false,true,true,UNAVAILABLE_NO_API_KEY,UNAVAILABLE_NO_API_KEY,absent",
            "6,false,true,false,UNAVAILABLE_NO_API_KEY,OFF,absent",
            "7,false,false,true,OFF,UNAVAILABLE_NO_API_KEY,absent",
            "8,false,false,false,OFF,OFF,absent"})
    void theEightRowsOfTheDecisionTableGiveTheDocumentedStatesAndTheMatchingEngineSettings(
            int row, boolean hasKey, boolean brain, boolean selfEvolution, EngineCapabilityState autoMutationState,
            EngineCapabilityState selfEvolutionState, String kernelBrain) {
        flags(false, selfEvolution, brain);
        if (hasKey) {
            storeApiKey();
        }

        Materialized m = materializer.materialize(3);

        assertThat(m.engineCapabilities()).as("列 " + row).isEqualTo(caps(autoMutationState, selfEvolutionState));
        if (hasKey) {
            assertThat(block(m, "minimax")).containsEntry("enable_kernel_brain", Boolean.valueOf(kernelBrain))
                    .containsOnlyKeys("base_url", "model", "timeout_seconds", "enable_kernel_brain");
            assertThat(m.env()).containsEntry("MINIMAX_API_KEY", SECRET);
        } else {
            assertThat(m.configOverrides()).doesNotContainKey("minimax");
            assertThat(m.env()).doesNotContainKey("MINIMAX_API_KEY");
        }
    }

    /**
     * 「等級 × 兩個旗標 × 金鑰」的完整矩陣（契約 §3.4.2；{@code model.enableKernelBrain=false}）。同一類別內每個等級的結果相同，
     * 所以取 {1, 5}（1～5）、6、{7, 10}（7～10）驗邊界。預期值逐列抄自契約，不由程式重算（否則決策函式寫錯時測試會跟著錯）。
     * 注意 7～10 的列：旗標設為 false 關不掉等級的強制開啟（契約 §3.4.2 誠實劃界 2）。
     */
    @ParameterizedTest(name = "等級 {0}、自動突變旗標={1}、自演化旗標={2}")
    @CsvSource({
            // level, autoMutation旗標, selfEvolution旗標, 有金鑰:enable_kernel_brain, 有金鑰:autoMutation, 有金鑰:selfEvolution, 無金鑰:autoMutation, 無金鑰:selfEvolution
            "1,false,false,false,OFF,ENABLED,OFF,OFF",
            "1,false,true,false,OFF,ENABLED,OFF,UNAVAILABLE_NO_API_KEY",
            "1,true,false,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,OFF",
            "1,true,true,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,UNAVAILABLE_NO_API_KEY",
            "5,false,false,false,OFF,ENABLED,OFF,OFF",
            "5,false,true,false,OFF,ENABLED,OFF,UNAVAILABLE_NO_API_KEY",
            "5,true,false,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,OFF",
            "5,true,true,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,UNAVAILABLE_NO_API_KEY",
            "6,false,false,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,OFF",
            "6,false,true,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,UNAVAILABLE_NO_API_KEY",
            "6,true,false,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,OFF",
            "6,true,true,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,UNAVAILABLE_NO_API_KEY",
            "7,false,false,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,UNAVAILABLE_NO_API_KEY",
            "7,false,true,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,UNAVAILABLE_NO_API_KEY",
            "7,true,false,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,UNAVAILABLE_NO_API_KEY",
            "7,true,true,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,UNAVAILABLE_NO_API_KEY",
            "10,false,false,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,UNAVAILABLE_NO_API_KEY",
            "10,false,true,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,UNAVAILABLE_NO_API_KEY",
            "10,true,false,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,UNAVAILABLE_NO_API_KEY",
            "10,true,true,true,ENABLED,ENABLED,UNAVAILABLE_NO_API_KEY,UNAVAILABLE_NO_API_KEY"})
    void theLevelAndFlagMatrixOfTheContractHoldsAtEveryBoundaryWithAndWithoutAKey(
            int level, boolean autoMutation, boolean selfEvolution, boolean keyedKernelBrain,
            EngineCapabilityState keyedAutoMutation, EngineCapabilityState keyedSelfEvolution,
            EngineCapabilityState plainAutoMutation, EngineCapabilityState plainSelfEvolution) {
        flags(autoMutation, selfEvolution, false);

        Materialized plain = materializer.materialize(level);
        assertThat(plain.engineCapabilities()).as("沒有金鑰").isEqualTo(caps(plainAutoMutation, plainSelfEvolution));
        assertThat(plain.configOverrides()).as("沒有金鑰一律不送 minimax.*（送了引擎會啟動失敗）")
                .doesNotContainKey("minimax");
        assertThat(plain.env()).doesNotContainKey("MINIMAX_API_KEY");

        storeApiKey();
        Materialized keyed = materializer.materialize(level);
        assertThat(keyed.engineCapabilities()).as("有金鑰").isEqualTo(caps(keyedAutoMutation, keyedSelfEvolution));
        assertThat(block(keyed, "minimax")).as("有金鑰時顯式送 true 或 false，磁碟上的設定檔永遠看得到有效值")
                .containsEntry("enable_kernel_brain", keyedKernelBrain);
        assertThat(keyed.env()).containsEntry("MINIMAX_API_KEY", SECRET);
    }

    @ParameterizedTest(name = "等級 {0}")
    @CsvSource({"1", "3", "5"})
    void theKernelBrainFlagAloneRequestsTheBrainLikeTheAutoMutationFlagButNeverTheSelfEvolution(int level) {
        flags(false, false, true);

        assertThat(materializer.materialize(level).engineCapabilities()).as("沒有金鑰：有人要求 Brain 但送不出去")
                .isEqualTo(caps(UNAVAILABLE_NO_API_KEY, OFF));
        storeApiKey();
        Materialized keyed = materializer.materialize(level);
        assertThat(keyed.engineCapabilities()).isEqualTo(caps(ENABLED, ENABLED));
        assertThat(block(keyed, "minimax")).containsEntry("enable_kernel_brain", true);

        // 與 agent.enableAutoMutation 共用同一個引擎鍵：兩者任一為真即開，結果與只開其一相同
        flags(true, false, true);
        assertThat(materializer.materialize(level).engineCapabilities()).isEqualTo(caps(ENABLED, ENABLED));
        flags(true, false, false);
        assertThat(materializer.materialize(level).engineCapabilities()).isEqualTo(caps(ENABLED, ENABLED));
    }

    @Test
    void withoutAKeyNothingBrainRelatedIsSentAtLevelTenEvenWithEveryFlagOnBecauseTheEngineWouldFailToStart() {
        flags(true, true, true);

        Materialized m = materializer.materialize(10);

        assertThat(m.configOverrides()).doesNotContainKey("minimax");
        assertThat(m.env()).doesNotContainKey("MINIMAX_API_KEY");
        assertThat(m.engineCapabilities()).isEqualTo(caps(UNAVAILABLE_NO_API_KEY, UNAVAILABLE_NO_API_KEY));
    }

    @Test
    void whatIsReportedIsExactlyWhatWasSentForEveryLevelFlagAndKeyCombination() {
        for (int level = 1; level <= 10; level++) {
            for (int mask = 0; mask < 8; mask++) {
                flags((mask & 1) != 0, (mask & 2) != 0, (mask & 4) != 0);
                for (boolean hasKey : new boolean[] {false, true}) {
                    if (hasKey) {
                        storeApiKey();
                    } else {
                        clearApiKey();
                    }
                    Materialized m = materializer.materialize(level);
                    String label = "等級 " + level + "、旗標 " + mask + "、有金鑰 " + hasKey;
                    if (hasKey) {
                        assertThat(block(m, "minimax").get("enable_kernel_brain")).as(label)
                                .isEqualTo(m.engineCapabilities().autoMutation() == ENABLED);
                        assertThat(m.engineCapabilities().selfEvolution())
                                .as(label + "：引擎沒有演化開關，有金鑰就是 ENABLED").isEqualTo(ENABLED);
                    } else {
                        assertThat(m.configOverrides()).as(label).doesNotContainKey("minimax");
                        assertThat(m.engineCapabilities().autoMutation()).as(label).isNotEqualTo(ENABLED);
                        assertThat(m.engineCapabilities().selfEvolution()).as(label).isNotEqualTo(ENABLED);
                    }
                }
            }
        }
    }

    @Test
    void theInertEvolutionKeysAreNeverSentAndTheApiKeyNeverEntersTheConfigOverridesWhateverTheLevelFlagsAndKey() {
        for (int level = 1; level <= 10; level++) {
            for (int mask = 0; mask < 8; mask++) {
                flags((mask & 1) != 0, (mask & 2) != 0, (mask & 4) != 0);
                for (boolean hasKey : new boolean[] {false, true}) {
                    if (hasKey) {
                        storeApiKey();
                    } else {
                        clearApiKey();
                    }
                    Materialized m = materializer.materialize(level);
                    String label = "等級 " + level + "、旗標 " + mask + "、有金鑰 " + hasKey;
                    for (String key : NEVER_SENT) {
                        assertThat(containsKeyDeep(m.configOverrides(), key)).as(label + "：" + key).isFalse();
                    }
                    assertThat(m.configOverrides().get("playbook")).as(label)
                            .isEqualTo(Map.of("step_timeout_seconds", 600));
                    assertThat(m.configOverrides().keySet()).as(label)
                            .isSubsetOf("claude", "playbook", "token_guard", "minimax");
                    assertThat(block(m, "token_guard")).as(label).doesNotContainKey("enabled");
                    assertThat(m.configOverrides().toString()).as(label).doesNotContain(SECRET).doesNotContain("api_key");
                    assertThat(m.engineCapabilities().toString()).as(label).doesNotContain(SECRET);
                }
            }
        }
    }

    @Test
    void theKeyAndTheFlagsAreReadFreshOnEveryCallSoANewRunNeverReusesAnOlderDecision() {
        flags(false, false, false);
        assertThat(materializer.materialize(3).engineCapabilities()).isEqualTo(caps(OFF, OFF));

        repository.set("agent", "enableAutoMutation", "true");
        assertThat(materializer.materialize(3).engineCapabilities()).isEqualTo(caps(UNAVAILABLE_NO_API_KEY, OFF));

        storeApiKey();
        assertThat(materializer.materialize(3).engineCapabilities()).isEqualTo(caps(ENABLED, ENABLED));

        clearApiKey();
        assertThat(materializer.materialize(3).engineCapabilities()).as("清掉金鑰＝回到沒有 Brain 可用")
                .isEqualTo(caps(UNAVAILABLE_NO_API_KEY, OFF));
    }
}
