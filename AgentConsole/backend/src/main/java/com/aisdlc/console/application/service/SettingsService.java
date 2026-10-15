package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.application.port.in.SettingsUseCase;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.OutboundHttp;
import com.aisdlc.console.application.port.out.OutboundHttp.HttpResult;
import com.aisdlc.console.application.port.out.OutboundHttp.OutboundIoException;
import com.aisdlc.console.application.port.out.SecretCipher;
import com.aisdlc.console.application.port.out.SystemConfigRepository;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violation;
import com.aisdlc.console.domain.exception.Violations;
import com.aisdlc.console.domain.model.config.ConfigCatalog;
import com.aisdlc.console.domain.model.config.ConfigHistoryEntry;
import com.aisdlc.console.domain.model.config.ConfigSpec;
import com.aisdlc.console.domain.model.config.SystemConfig;
import com.aisdlc.console.domain.service.ConfigValueRules;
import com.aisdlc.console.domain.service.OutboundUrlPolicy;
import com.aisdlc.console.domain.service.OutboundUrlPolicy.Rejected;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 系統參數用例（PRD §5.5、§7.1.8；契約 §1.5）。
 *
 * <p>🔴 安全不變式：加密參數（{@code model.apiKey}、{@code autoclaude.dbDsn}）以 AES-256-GCM 儲存；任何讀取、歷史、
 * 匯出、日誌與錯誤訊息都只出現遮罩（{@code ••••••••}）或佔位（{@code <encrypted>}）；明文只在 ADMIN 的
 * {@code reveal=true} 才回傳，且每次揭露寫審計（只記範圍與次數，不記值）。token_guard 兩鍵
 * （{@code compactThresholdPct}／{@code haltThresholdPct}）永遠成對校驗 {@code halt > compact}（NFR-SEC-05），
 * 校驗與寫入前先鎖兩列（固定順序），避免並發的兩個單鍵更新合起來違規。
 */
@Service
@Transactional
public class SettingsService implements SettingsUseCase {

    /** 匯出時加密參數的佔位值；匯入時遇到它一律略過。 */
    public static final String ENCRYPTED_PLACEHOLDER = "<encrypted>";

    private static final String MODEL = "model";
    private static final String API_URL = "apiUrl";
    private static final String API_KEY = "apiKey";
    private static final int EXPORT_VERSION = 1;
    private static final int MAX_PAGE_SIZE = 100;
    private static final Duration CONNECT_TIMEOUT = Duration.ofSeconds(5);
    private static final int TEST_CONNECTION_MAX_SECONDS = 10;

    private final SystemConfigRepository repository;
    private final SecretCipher cipher;
    private final OutboundUrlPolicy policy;
    private final OutboundHttp outbound;
    private final SettingsReader reader;
    private final Clock clock;
    private final AuditTrail audit;

    public SettingsService(SystemConfigRepository repository, SecretCipher cipher, OutboundUrlPolicy policy,
                           OutboundHttp outbound, SettingsReader reader, Clock clock, AuditTrail audit) {
        this.repository = repository;
        this.cipher = cipher;
        this.policy = policy;
        this.outbound = outbound;
        this.reader = reader;
        this.clock = clock;
        this.audit = audit;
    }

    // ── 讀取 ──────────────────────────────────────────────────────────────────

    @Override
    @Transactional(readOnly = true)
    public Map<String, List<ConfigView>> listAll(boolean reveal) {
        Map<String, List<ConfigView>> byCategory = new LinkedHashMap<>();
        ConfigCatalog.CATEGORIES.forEach(category -> byCategory.put(category, new ArrayList<>()));
        int revealed = 0;
        for (SystemConfig config : sorted(repository.findAll())) {
            byCategory.computeIfAbsent(config.category(), k -> new ArrayList<>()).add(view(config, reveal));
            revealed += reveal && config.encrypted() && config.hasValue() ? 1 : 0;
        }
        auditReveal(reveal, "all", revealed);
        return byCategory;
    }

    @Override
    @Transactional(readOnly = true)
    public List<ConfigView> listCategory(String category, boolean reveal) {
        if (!ConfigCatalog.isCategory(category)) {
            throw new NotFoundException("設定分類不存在：" + category);
        }
        List<ConfigView> views = new ArrayList<>();
        int revealed = 0;
        for (SystemConfig config : sorted(repository.findByCategory(category))) {
            views.add(view(config, reveal));
            revealed += reveal && config.encrypted() && config.hasValue() ? 1 : 0;
        }
        auditReveal(reveal, category, revealed);
        return views;
    }

    // ── 單鍵更新 ──────────────────────────────────────────────────────────────

    @Override
    public ConfigView update(String category, String key, String value, boolean confirm, String actor) {
        SystemConfig current = lockForWrite(category, key);
        ConfigSpec spec = ConfigCatalog.find(category, key).orElse(null);
        // 2. 型別、validationRule、min／max、options
        Optional<ConfigValueRules.Failure> failure = ConfigValueRules.check(current, spec, value);
        if (failure.isPresent()) {
            throw invalid(current, spec, failure.get().message());
        }
        // 3. model.apiUrl：SEC-04 規則 1～5（不做 DNS）
        if (isApiUrl(current)) {
            requireAllowedUrl(value);
        }
        // 4. token_guard 單鍵：讀對端鍵現值
        if (ConfigCatalog.isTokenGuardKey(category, key)) {
            requireTokenGuardOrder(tokenGuardWith(current, value), "value");
        }
        // 5. 加密鍵未帶 confirm=true
        if (current.encrypted() && !confirm) {
            throw new ConflictException("敏感參數 " + current.fullKey() + " 的更新需要二次確認（confirm=true）",
                    ErrorReasons.CONFIG_UPDATE_CONFIRM, Map.of("category", category, "key", key));
        }
        SystemConfig saved = apply(current, value, actor);
        audit.note("settings.update", "settings", current.fullKey());
        return view(saved, false);
    }

    @Override
    public List<ConfigView> updateTokenGuard(int compactThresholdPct, int haltThresholdPct, String actor) {
        SystemConfig compact = lockForWrite(ConfigCatalog.TOKEN_GUARD_CATEGORY, ConfigCatalog.COMPACT_KEY);
        SystemConfig halt = lockForWrite(ConfigCatalog.TOKEN_GUARD_CATEGORY, ConfigCatalog.HALT_KEY);
        Violations v = new Violations();
        if (compactThresholdPct < ConfigCatalog.COMPACT_MIN || compactThresholdPct > ConfigCatalog.COMPACT_MAX) {
            v.add("compactThresholdPct", "compactThresholdPct 必須介於 " + ConfigCatalog.COMPACT_MIN + " 到 "
                    + ConfigCatalog.COMPACT_MAX);
        }
        if (haltThresholdPct < ConfigCatalog.HALT_MIN || haltThresholdPct > ConfigCatalog.HALT_MAX) {
            v.add("haltThresholdPct", "haltThresholdPct 必須介於 " + ConfigCatalog.HALT_MIN + " 到 "
                    + ConfigCatalog.HALT_MAX);
        }
        v.throwIfAny();
        requireTokenGuardOrder(new int[] {compactThresholdPct, haltThresholdPct}, "haltThresholdPct");
        SystemConfig savedCompact = apply(compact, Integer.toString(compactThresholdPct), actor);
        SystemConfig savedHalt = apply(halt, Integer.toString(haltThresholdPct), actor);
        audit.note("settings.tokenGuard", "settings", ConfigCatalog.TOKEN_GUARD_CATEGORY + ".token_guard");
        return List.of(view(savedCompact, false), view(savedHalt, false));
    }

    // ── 重置 ──────────────────────────────────────────────────────────────────

    @Override
    public ConfigView reset(String category, String key, boolean confirm, String actor) {
        SystemConfig current = lockForWrite(category, key);
        if (current.encrypted() && !confirm) {
            throw new ConflictException("敏感參數 " + current.fullKey() + " 的重置需要二次確認（confirm=true）",
                    ErrorReasons.CONFIG_RESET_CONFIRM, Map.of("category", category, "key", key));
        }
        String target = defaultOf(current);
        if (ConfigCatalog.isTokenGuardKey(category, key)) {
            requireTokenGuardOrder(tokenGuardWith(current, target), "value");
        }
        SystemConfig saved = apply(current, target, actor);
        audit.note("settings.reset", "settings", current.fullKey());
        return view(saved, false);
    }

    @Override
    public List<ConfigView> resetCategory(String category, boolean confirm, String actor) {
        if (!ConfigCatalog.isCategory(category)) {
            throw new NotFoundException("設定分類不存在：" + category);
        }
        if (ConfigCatalog.TOKEN_GUARD_CATEGORY.equals(category)) {
            lockTokenGuardPair();
        }
        Map<String, String> targets = new LinkedHashMap<>();
        List<SystemConfig> configs = sorted(repository.findByCategory(category));
        for (SystemConfig config : configs) {
            if (config.encrypted() && !confirm) {
                continue;     // 加密鍵預設略過（要連同重置須 confirm=true）
            }
            targets.put(config.key(), defaultOf(config));
        }
        if (ConfigCatalog.TOKEN_GUARD_CATEGORY.equals(category)) {
            // 以重置後的「最終值」做跨鍵校驗，不滿足則整批不套用
            int compact = Integer.parseInt(targets.getOrDefault(ConfigCatalog.COMPACT_KEY,
                    currentValue(category, ConfigCatalog.COMPACT_KEY)));
            int halt = Integer.parseInt(targets.getOrDefault(ConfigCatalog.HALT_KEY,
                    currentValue(category, ConfigCatalog.HALT_KEY)));
            requireTokenGuardOrder(new int[] {compact, halt}, "value");
        }
        List<ConfigView> result = new ArrayList<>();
        for (SystemConfig config : configs) {
            String target = targets.get(config.key());
            SystemConfig saved = target == null ? config : apply(config, target, actor);
            result.add(view(saved, false));
        }
        audit.note("settings.resetCategory", "settings", category);
        return result;
    }

    // ── 測試連線（SEC-04）─────────────────────────────────────────────────────

    /** 不持有資料庫交易：網路呼叫最長 10 秒，不能佔著連線。 */
    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public ConnectionTestResult testConnection(TestConnectionCommand command, String actor) {
        TestConnectionCommand cmd = command == null ? new TestConnectionCommand(null, null, null) : command;
        SettingsReader.ModelSettings stored = reader.modelSettings();
        String apiUrl = isBlank(cmd.apiUrl()) ? stored.apiUrl() : cmd.apiUrl();
        String apiKey = isBlank(cmd.apiKey()) ? stored.apiKey() : cmd.apiKey();
        String model = isBlank(cmd.model()) ? stored.name() : cmd.model();
        int totalSeconds = Math.max(1, Math.min(stored.timeoutSeconds(), TEST_CONNECTION_MAX_SECONDS));

        String host = null;
        try {
            OutboundUrlPolicy.Target target = policy.checkStatic(apiUrl);
            host = target.host();
            String body = "{\"model\":" + JsonStrings.quote(model) + ",\"messages\":[{\"role\":\"user\","
                    + "\"content\":\"ping\"}],\"max_tokens\":1,\"stream\":false}";
            Map<String, String> headers = new LinkedHashMap<>();
            headers.put("Content-Type", "application/json");
            headers.put("Accept", "application/json");
            headers.put("User-Agent", "aisdlc-console");
            if (!apiKey.isEmpty()) {
                headers.put("Authorization", "Bearer " + apiKey);
            }
            HttpResult http = outbound.postJson(apiUrl, headers, body, CONNECT_TIMEOUT,
                    Duration.ofSeconds(totalSeconds));
            ConnectionTestResult result = outcome(http);
            audit.note("settings.testConnection", "settings", MODEL + ".apiUrl",
                    Map.of("host", target.host(), "success", result.success(), "httpStatus", http.status()));
            return result;
        } catch (Rejected rejected) {
            audit.note("settings.testConnection", "settings", MODEL + ".apiUrl",
                    Map.of("host", rejected.host() == null ? "" : rejected.host(), "success", false,
                            "rejected", rejected.violation().code()));
            throw new UnprocessableException(rejected.getMessage(), ErrorReasons.OUTBOUND_REJECTED,
                    rejected.details());
        } catch (OutboundIoException io) {
            String shownHost = host == null ? "" : host;
            audit.note("settings.testConnection", "settings", MODEL + ".apiUrl",
                    Map.of("host", shownHost, "success", false, "io", io.kind().name()));
            String message = io.kind() == OutboundIoException.Kind.TIMEOUT
                    ? "連線逾時（" + totalSeconds + " 秒）" : "無法連線：" + io.getMessage();
            return new ConnectionTestResult(false, null, message, host, null);
        }
    }

    private static ConnectionTestResult outcome(HttpResult http) {
        int status = http.status();
        boolean success = status >= 200 && status < 300;
        String message;
        if (success) {
            message = "連線成功";
        } else if (status == 401 || status == 403) {
            message = "認證失敗（HTTP " + status + "）";
        } else if (status == 404 || status == 405) {
            message = "端點路徑不存在或不接受 POST（HTTP " + status + "）";
        } else if (status >= 300 && status < 400) {
            message = "目標回應重新導向，已拒絕跟隨（HTTP " + status + "）";
        } else {
            message = "服務回應錯誤（HTTP " + status + "）";
        }
        return new ConnectionTestResult(success, http.latencyMs(), message, http.resolvedHost(), status);
    }

    // ── 歷史 ──────────────────────────────────────────────────────────────────

    @Override
    @Transactional(readOnly = true)
    public PageResult<ConfigHistoryEntry> history(String category, String key, int page, int size) {
        Violations v = new Violations();
        if (page < 0) {
            v.add("page", "page 不可為負數");
        }
        if (size < 1 || size > MAX_PAGE_SIZE) {
            v.add("size", "size 必須介於 1 到 " + MAX_PAGE_SIZE);
        }
        boolean hasCategory = !isBlank(category);
        boolean hasKey = !isBlank(key);
        if (hasKey && !hasCategory) {
            v.add("key", "key 必須與 category 併用");
        }
        v.throwIfAny();
        return repository.history(hasCategory ? category : null, hasKey ? key : null, page, size);
    }

    // ── 匯出入 ────────────────────────────────────────────────────────────────

    @Override
    @Transactional(readOnly = true)
    public ExportedSettings export() {
        List<ExportedItem> items = new ArrayList<>();
        for (SystemConfig config : sorted(repository.findAll())) {
            items.add(new ExportedItem(config.category(), config.key(),
                    config.encrypted() ? ENCRYPTED_PLACEHOLDER : config.value()));
        }
        audit.note("settings.export", "settings", null);
        return new ExportedSettings(EXPORT_VERSION, clock.instant(), items);
    }

    @Override
    public ImportResult importSettings(List<ExportedItem> items, String actor) {
        // 同一個鍵出現多次：以最後一筆為準
        Map<String, ExportedItem> latest = new LinkedHashMap<>();
        for (ExportedItem item : items) {
            latest.put(item.category() + "." + item.key(), item);
        }
        lockTokenGuardPair();

        List<ImportError> errors = new ArrayList<>();
        Map<String, Candidate> candidates = new LinkedHashMap<>();
        int skipped = 0;
        for (ExportedItem item : latest.values()) {
            Optional<SystemConfig> found = repository.findForUpdate(item.category(), item.key());
            if (found.isEmpty()) {
                errors.add(new ImportError(item.category(), item.key(), ErrorReasons.CONFIG_KEY_UNKNOWN));
                continue;
            }
            SystemConfig config = found.get();
            String value = item.value() == null ? "" : item.value();
            if (ENCRYPTED_PLACEHOLDER.equals(value)) {
                skipped++;
                continue;
            }
            if (config.encrypted()) {
                errors.add(new ImportError(item.category(), item.key(), ErrorReasons.CONFIG_UPDATE_CONFIRM));
                continue;
            }
            // C-6（DEF-AC-002）：值與現值相同＝什麼都不會改，計 skipped 並跳過值規則與 allowlist 驗證——
            // 匯出後原樣匯入因此恆為 errors=[]，即使現值的 model.apiUrl 主機不在這個環境的 allowlist。
            if (value.equals(config.value())) {
                skipped++;
                continue;
            }
            ConfigSpec spec = ConfigCatalog.find(config.category(), config.key()).orElse(null);
            if (ConfigValueRules.check(config, spec, value).isPresent()) {
                errors.add(new ImportError(item.category(), item.key(), ErrorReasons.CONFIG_VALUE_INVALID));
                continue;
            }
            if (isApiUrl(config) && !urlAllowed(value)) {
                errors.add(new ImportError(item.category(), item.key(), ErrorReasons.OUTBOUND_REJECTED));
                continue;
            }
            candidates.put(config.fullKey(), new Candidate(config, value));
        }
        rejectTokenGuardViolation(candidates, errors);

        int applied = 0;
        for (Candidate candidate : candidates.values()) {
            apply(candidate.config(), candidate.value(), actor);
            applied++;
        }
        audit.note("settings.import", "settings", null,
                Map.of("applied", applied, "skipped", skipped, "errors", errors.size()));
        return new ImportResult(applied, skipped, errors);
    }

    private record Candidate(SystemConfig config, String value) {
    }

    /** token_guard 兩鍵以合併後的最終值做 halt > compact 校驗：不滿足則兩鍵皆列入 errors 且都不套用。 */
    private void rejectTokenGuardViolation(Map<String, Candidate> candidates, List<ImportError> errors) {
        String compactKey = ConfigCatalog.TOKEN_GUARD_CATEGORY + "." + ConfigCatalog.COMPACT_KEY;
        String haltKey = ConfigCatalog.TOKEN_GUARD_CATEGORY + "." + ConfigCatalog.HALT_KEY;
        Candidate compact = candidates.get(compactKey);
        Candidate halt = candidates.get(haltKey);
        if (compact == null && halt == null) {
            return;
        }
        int compactValue = Integer.parseInt(compact != null ? compact.value()
                : currentValue(ConfigCatalog.TOKEN_GUARD_CATEGORY, ConfigCatalog.COMPACT_KEY));
        int haltValue = Integer.parseInt(halt != null ? halt.value()
                : currentValue(ConfigCatalog.TOKEN_GUARD_CATEGORY, ConfigCatalog.HALT_KEY));
        if (haltValue <= compactValue) {
            candidates.remove(compactKey);
            candidates.remove(haltKey);
            errors.add(new ImportError(ConfigCatalog.TOKEN_GUARD_CATEGORY, ConfigCatalog.COMPACT_KEY,
                    ErrorReasons.TOKEN_GUARD_ORDER));
            errors.add(new ImportError(ConfigCatalog.TOKEN_GUARD_CATEGORY, ConfigCatalog.HALT_KEY,
                    ErrorReasons.TOKEN_GUARD_ORDER));
        }
    }

    // ── 內部 ──────────────────────────────────────────────────────────────────

    /** 寫入：值相同＝不寫歷史（回原值）；否則存值（加密參數先加密）並寫一筆歷史（加密參數的新舊值存遮罩）。 */
    private SystemConfig apply(SystemConfig current, String newValue, String actor) {
        String oldShown;
        String newShown;
        String stored;
        if (current.encrypted()) {
            String currentPlain = current.hasValue() ? cipher.decrypt(current.value()) : "";
            if (currentPlain.equals(newValue)) {
                return current;
            }
            stored = newValue.isEmpty() ? "" : cipher.encrypt(newValue);
            oldShown = ConfigHistoryEntry.MASK;
            newShown = ConfigHistoryEntry.MASK;
        } else {
            if (newValue.equals(current.value())) {
                return current;
            }
            stored = newValue;
            oldShown = current.value();
            newShown = newValue;
        }
        Instant now = clock.instant();
        SystemConfig saved = repository.save(current.withValue(stored, now, actor));
        repository.addHistory(new ConfigHistoryEntry(null, current.id(), current.category(), current.key(),
                oldShown, newShown, now, actor));
        return saved;
    }

    private SystemConfig lockForWrite(String category, String key) {
        if (ConfigCatalog.isTokenGuardKey(category, key)) {
            lockTokenGuardPair();
        }
        return repository.findForUpdate(category, key).orElseThrow(
                () -> new NotFoundException("設定鍵不存在：" + category + "." + key));
    }

    /** 固定順序（compact → halt）鎖兩列，避免並發更新互相死結或合起來違規。 */
    private void lockTokenGuardPair() {
        repository.findForUpdate(ConfigCatalog.TOKEN_GUARD_CATEGORY, ConfigCatalog.COMPACT_KEY);
        repository.findForUpdate(ConfigCatalog.TOKEN_GUARD_CATEGORY, ConfigCatalog.HALT_KEY);
    }

    private String currentValue(String category, String key) {
        return repository.find(category, key).orElseThrow(
                () -> new IllegalStateException("系統參數不存在：" + category + "." + key)).value();
    }

    /** 回傳 {compact, halt}：把 {@code current} 這一鍵換成 {@code newValue} 後的兩鍵值。 */
    private int[] tokenGuardWith(SystemConfig current, String newValue) {
        int compact = Integer.parseInt(ConfigCatalog.COMPACT_KEY.equals(current.key()) ? newValue
                : currentValue(ConfigCatalog.TOKEN_GUARD_CATEGORY, ConfigCatalog.COMPACT_KEY));
        int halt = Integer.parseInt(ConfigCatalog.HALT_KEY.equals(current.key()) ? newValue
                : currentValue(ConfigCatalog.TOKEN_GUARD_CATEGORY, ConfigCatalog.HALT_KEY));
        return new int[] {compact, halt};
    }

    private static void requireTokenGuardOrder(int[] compactAndHalt, String field) {
        int compact = compactAndHalt[0];
        int halt = compactAndHalt[1];
        if (halt <= compact) {
            throw new ValidationException("Token Guard 閾值不合法：halt（" + halt + "）必須大於 compact（" + compact + "）",
                    ErrorReasons.TOKEN_GUARD_ORDER,
                    List.of(new Violation(field, "必須大於 compactThresholdPct")),
                    Map.of("compactThresholdPct", compact, "haltThresholdPct", halt));
        }
    }

    private void requireAllowedUrl(String url) {
        try {
            policy.checkStatic(url);
        } catch (Rejected rejected) {
            throw new ValidationException(rejected.getMessage(), ErrorReasons.OUTBOUND_REJECTED,
                    List.of(new Violation("value", "目標位址未通過 SSRF／allowlist 檢查（" + rejected.violation().code()
                            + "）")), rejected.details());
        }
    }

    private boolean urlAllowed(String url) {
        try {
            policy.checkStatic(url);
            return true;
        } catch (Rejected rejected) {
            return false;
        }
    }

    private static boolean isApiUrl(SystemConfig config) {
        return MODEL.equals(config.category()) && API_URL.equals(config.key());
    }

    private static String defaultOf(SystemConfig config) {
        return config.defaultValue() == null ? "" : config.defaultValue();
    }

    private static ValidationException invalid(SystemConfig config, ConfigSpec spec, String message) {
        Map<String, Object> details = new LinkedHashMap<>();
        details.put("valueType", config.valueType().name());
        if (config.validationRule() != null) {
            details.put("validationRule", config.validationRule());
        }
        if (spec != null && spec.min() != null) {
            details.put("min", spec.min());
        }
        if (spec != null && spec.max() != null) {
            details.put("max", spec.max());
        }
        if (spec != null && !spec.options().isEmpty()) {
            details.put("options", spec.options());
        }
        return new ValidationException("參數 " + config.fullKey() + " 的值不符合型別或驗證規則：" + message,
                ErrorReasons.CONFIG_VALUE_INVALID, List.of(new Violation("value", message)), details);
    }

    private ConfigView view(SystemConfig config, boolean reveal) {
        ConfigSpec spec = ConfigCatalog.find(config.category(), config.key()).orElse(null);
        if (config.encrypted()) {
            String shown = reveal ? (config.hasValue() ? cipher.decrypt(config.value()) : "")
                    : ConfigHistoryEntry.MASK;
            return new ConfigView(config, spec, shown, config.hasValue());
        }
        return new ConfigView(config, spec, config.value(), config.hasValue());
    }

    private void auditReveal(boolean reveal, String scope, int revealed) {
        if (reveal) {
            // 只記範圍與次數，不記值（契約 §1.5）
            audit.event("settings.reveal", Map.of("scope", scope, "count", revealed));
        }
    }

    private static List<SystemConfig> sorted(List<SystemConfig> configs) {
        return configs.stream().sorted(Comparator
                .comparingInt((SystemConfig c) -> ConfigCatalog.orderOf(c.category(), c.key()))
                .thenComparing(SystemConfig::category).thenComparing(SystemConfig::key)).toList();
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }
}
