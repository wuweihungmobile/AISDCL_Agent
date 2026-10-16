package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.RuntimeSettings;
import com.aisdlc.console.domain.model.execution.EngineCapabilities;
import com.aisdlc.console.domain.model.execution.EngineCapabilityState;
import com.aisdlc.console.domain.service.EngineCapabilityPolicy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * 系統參數與自治等級 → Bridge 的 {@code config_overrides} 與 {@code env}，以及該批次的 {@code engineCapabilities}
 * （契約 §3.4.2；{@code API-SET-10}、{@code API-AUT-06}）。每次呼叫都讀資料庫的當下值（「新批次起生效」：已在跑的批次沿用啟動時的值，
 * 引擎設定在 spawn 時物化）；{@code resume}／{@code restore}／審核 {@code APPROVE} 只取 {@code .env()}，因為 Bridge 重啟後請求層 env 會遺失
 * （{@code ENV_LOST}），它們不重算、也不更新 {@code engineCapabilities}。
 *
 * <p>🔴 <b>一致性規則</b>：建立批次時只呼叫一次，回傳值同時用於 {@code execution_runs.engine_capabilities} 的 INSERT 與 Bridge 請求
 * （{@link RunLauncher}）——兩次分開讀設定，設定可能在中間被改，落庫的值就會與實際送出的不符。
 *
 * <p>🔴 機密只走 {@code env}：{@code MINIMAX_API_KEY} 解密後只進 env，絕不進 {@code config_overrides}、日誌或回應
 * （Bridge 的 {@code config_overrides} 也會拒絕 {@code api_key}／{@code db_dsn}）。
 *
 * <p>Brain（{@code minimax.*}）：<b>只在有 {@code model.apiKey} 時送</b>，並顯式送 {@code enable_kernel_brain} 的 {@code true}／{@code false}
 * （磁碟上的引擎設定檔因此永遠看得到有效值）。沒有金鑰一律不送——引擎對「{@code enable_kernel_brain=true} 但沒有金鑰」是啟動即失敗
 * （{@code main.py} 記錯誤後 {@code return 1}），不是忽略。決策表在 {@link EngineCapabilityPolicy}。
 *
 * <p>永不送的鍵：{@code storage}／{@code checkpoint_dir}／{@code log_dir}（Bridge 管控，送了會發 {@code CONFIG_OVERRIDE_IGNORED} 噪音告警）、
 * {@code token_guard.enabled}（不得經 Console 繞過安全收斂，NFR-SEC-05）、{@code autoclaude.dalBackend／dbDsn／dualReadResolution}
 * 與 {@code agent.maxConcurrentTasks}／{@code execution.maxParallelGoals}（STORED_ONLY）、{@code agent.enableSelfEvolution}（已驗證
 * 引擎沒有對應的有效旗標），以及 {@code playbook.max_evolutions}／{@code require_evolution_signoff}（引擎執行路徑上沒有讀者，送了只會
 * 讓人誤以為有演化上限與核可閘）與 {@code playbook.enable_rtm_feedback}／{@code goal_synthesis_enabled}／
 * {@code enable_translation_auto_propose}（對 Console 產生的 playbook 沒有可觀測的效果，或會關掉既有的檢查）。
 */
@Component
public class ConfigMaterializer {

    private static final Logger LOG = LoggerFactory.getLogger(ConfigMaterializer.class);
    private static final Pattern EXTRA_ARG = Pattern.compile("^[A-Za-z0-9_.=:,/@\\-]+$");

    /**
     * 物化結果。
     *
     * @param engineCapabilities 這一次實際送進引擎的能力狀態（落庫與回給前端的就是它）
     */
    public record Materialized(Map<String, Object> configOverrides, Map<String, String> env,
                               EngineCapabilities engineCapabilities) {
    }

    private final SettingsReader settings;
    private final RuntimeSettings runtime;

    public ConfigMaterializer(SettingsReader settings, RuntimeSettings runtime) {
        this.settings = settings;
        this.runtime = runtime;
    }

    /** @param autonomyLevel 本批次的自治等級（1～10）：≥ 6 視為要求自動突變、≥ 7 視為要求自演化（契約 §3.4.2） */
    public Materialized materialize(int autonomyLevel) {
        Map<String, Object> overrides = new LinkedHashMap<>();

        Map<String, Object> claude = new LinkedHashMap<>();
        claude.put("command", settings.value("autoclaude", "claudeCommand"));
        List<String> extraArgs = extraArgs(settings.value("autoclaude", "claudeExtraArgs"));
        if (!extraArgs.isEmpty()) {
            claude.put("extra_args", extraArgs);
        }
        claude.put("continue_flag", settings.value("autoclaude", "claudeContinueFlag"));
        claude.put("encoding", settings.value("autoclaude", "claudeEncoding"));
        overrides.put("claude", claude);

        overrides.put("playbook", Map.of("step_timeout_seconds", settings.intValue("agent", "taskTimeout")));

        Map<String, Object> tokenGuard = new LinkedHashMap<>();
        tokenGuard.put("compact_threshold_pct", settings.intValue("execution", "compactThresholdPct"));
        tokenGuard.put("halt_threshold_pct", settings.intValue("execution", "haltThresholdPct"));
        tokenGuard.put("auto_resume", settings.booleanValue("execution", "autoResume"));
        tokenGuard.put("max_auto_resumes", settings.intValue("execution", "maxAutoResumes"));
        overrides.put("token_guard", tokenGuard);

        Map<String, String> env = new LinkedHashMap<>();
        String apiKey = settings.value("model", "apiKey");
        boolean hasKey = !apiKey.isEmpty();
        EngineCapabilities capabilities = EngineCapabilityPolicy.decide(autonomyLevel,
                settings.booleanValue("agent", "enableAutoMutation"),
                settings.booleanValue("agent", "enableSelfEvolution"),
                settings.booleanValue("model", "enableKernelBrain"), hasKey);
        if (hasKey) {
            Map<String, Object> minimax = new LinkedHashMap<>();
            minimax.put("base_url", settings.value("model", "apiUrl"));
            minimax.put("model", settings.value("model", "name"));
            minimax.put("timeout_seconds", settings.intValue("model", "timeout"));
            // 送出的值與回報的能力同源：有金鑰時 autoMutation 為 ENABLED 若且唯若 enable_kernel_brain 送 true
            minimax.put("enable_kernel_brain", capabilities.autoMutation() == EngineCapabilityState.ENABLED);
            overrides.put("minimax", minimax);
            env.put("MINIMAX_API_KEY", apiKey);
        }
        env.putAll(runtime.mockEnv());
        return new Materialized(overrides, env, capabilities);
    }

    /** {@code autoclaude.claudeExtraArgs} 以空白切成陣列；不符 {@code ^[A-Za-z0-9_.=:,/@\-]+$} 的片段丟棄並記 WARN（設定驗證本應擋下）。 */
    static List<String> extraArgs(String raw) {
        List<String> args = new ArrayList<>();
        if (raw == null || raw.isBlank()) {
            return args;
        }
        for (String token : raw.strip().split("\\s+")) {
            if (EXTRA_ARG.matcher(token).matches()) {
                args.add(token);
            } else {
                LOG.warn("autoclaude.claudeExtraArgs 的片段含不允許的字元，已略過");
            }
        }
        return args;
    }
}
