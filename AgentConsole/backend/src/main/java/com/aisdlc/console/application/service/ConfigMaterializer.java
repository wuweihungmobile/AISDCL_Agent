package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.RuntimeSettings;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * 系統參數 → Bridge 的 {@code config_overrides} 與 {@code env}（契約 §3.4.2；{@code API-SET-10}）。每次呼叫都讀資料庫的當下值
 * （「新批次起生效」：已在跑的批次沿用啟動時的值，引擎設定在 spawn 時物化）；{@code resume}／{@code restore} 也重新物化並帶上 env，
 * 因為 Bridge 重啟後請求層 env 會遺失（{@code ENV_LOST}）。
 *
 * <p>🔴 機密只走 {@code env}：{@code MINIMAX_API_KEY} 解密後只進 env，絕不進 {@code config_overrides}、日誌或回應
 * （Bridge 的 {@code config_overrides} 也會拒絕 {@code api_key}／{@code db_dsn}）。
 * 不送的鍵：{@code storage}／{@code checkpoint_dir}／{@code log_dir}（Bridge 管控，送了會發 {@code CONFIG_OVERRIDE_IGNORED} 噪音告警）、
 * {@code token_guard.enabled}（不得經 Console 繞過安全收斂，NFR-SEC-05）、{@code autoclaude.dalBackend／dbDsn／dualReadResolution}
 * 與 {@code agent.maxConcurrentTasks}／{@code execution.maxParallelGoals}（STORED_ONLY）、{@code agent.enableAutoMutation／enableSelfEvolution}（UNVERIFIED）。
 */
@Component
public class ConfigMaterializer {

    private static final Logger LOG = LoggerFactory.getLogger(ConfigMaterializer.class);
    private static final Pattern EXTRA_ARG = Pattern.compile("^[A-Za-z0-9_.=:,/@\\-]+$");

    /** 物化結果。 */
    public record Materialized(Map<String, Object> configOverrides, Map<String, String> env) {
    }

    private final SettingsReader settings;
    private final RuntimeSettings runtime;

    public ConfigMaterializer(SettingsReader settings, RuntimeSettings runtime) {
        this.settings = settings;
        this.runtime = runtime;
    }

    public Materialized materialize() {
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
        if (!apiKey.isEmpty()) {
            // 沒有金鑰引擎本來就用不到 Brain，所以只在有金鑰時才送 minimax.*（E2E 的「關閉演化」也是這樣做，契約 D-58）
            Map<String, Object> minimax = new LinkedHashMap<>();
            minimax.put("base_url", settings.value("model", "apiUrl"));
            minimax.put("model", settings.value("model", "name"));
            minimax.put("timeout_seconds", settings.intValue("model", "timeout"));
            minimax.put("enable_kernel_brain", settings.booleanValue("model", "enableKernelBrain"));
            overrides.put("minimax", minimax);
            env.put("MINIMAX_API_KEY", apiKey);
        }
        env.putAll(runtime.mockEnv());
        return new Materialized(overrides, env);
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
