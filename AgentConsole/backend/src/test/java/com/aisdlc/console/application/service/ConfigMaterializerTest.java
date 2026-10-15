package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.RuntimeSettings;
import com.aisdlc.console.application.port.out.SecretCipher;
import com.aisdlc.console.application.service.ConfigMaterializer.Materialized;
import com.aisdlc.console.domain.model.config.ConfigValueType;
import com.aisdlc.console.support.InMemorySystemConfigRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * 系統參數 → Bridge 的 {@code config_overrides}／{@code env}（契約 §3.4.2、NFR-SEC-05）。為什麼重要：這是整個後端唯一把「機密」送出
 * Console 的地方——API Key 若漏進 {@code config_overrides}，就會被 Bridge 寫進 run 目錄的設定檔與日誌；
 * 若把 {@code token_guard.enabled} 也送出去，使用者就能經由系統設定關掉安全收斂。
 */
class ConfigMaterializerTest {

    // 刻意不用 sk- 前綴：根層 pre-commit 機密掃描會把 openai／minimax 形態的字串當真值擋下 commit。
    private static final String SECRET = "your_api_key_here_test_fixture_0123456789";

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

    @SuppressWarnings("unchecked")
    private static Map<String, Object> block(Materialized m, String name) {
        return (Map<String, Object>) m.configOverrides().get(name);
    }

    @Test
    void theApiKeyOnlyTravelsInTheEnvAndNeverInsideTheConfigOverrides() {
        storeApiKey();

        Materialized m = materializer.materialize();

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
        Materialized m = materializer.materialize();

        assertThat(m.configOverrides()).doesNotContainKey("minimax");
        assertThat(m.env()).doesNotContainKey("MINIMAX_API_KEY");
    }

    @Test
    void theEngineIsToldOnlyWhatConsoleOwnsAndTheSafetyGuardCannotBeSwitchedOffThroughSettings() {
        Materialized m = materializer.materialize();

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

        Materialized m = materializer.materialize();

        assertThat(m.env()).containsEntry("MOCK_CLAUDE_DELAY", "0.6").containsEntry("MINIMAX_API_KEY", SECRET);
    }

    @Test
    void everyCallReadsTheCurrentValuesSoANewRunPicksUpEditedSettings() {
        assertThat(block(materializer.materialize(), "token_guard")).containsEntry("halt_threshold_pct", 90);

        repository.set("execution", "haltThresholdPct", "95");
        repository.set("agent", "taskTimeout", "1200");
        Materialized after = materializer.materialize();

        assertThat(block(after, "token_guard")).containsEntry("halt_threshold_pct", 95);
        assertThat(after.configOverrides().get("playbook")).isEqualTo(Map.of("step_timeout_seconds", 1200));
    }

    @Test
    void extraArgsAreSplitOnWhitespaceAndFragmentsWithUnsafeCharactersAreDropped() {
        repository.set("autoclaude", "claudeExtraArgs", "  --model   sonnet --bad;rm $(whoami) --max-turns=3 ");

        Map<String, Object> claude = block(materializer.materialize(), "claude");

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
}
