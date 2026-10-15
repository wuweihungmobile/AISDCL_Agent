package com.aisdlc.console.support;

import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.application.port.out.SystemConfigRepository;
import com.aisdlc.console.domain.model.config.ConfigHistoryEntry;
import com.aisdlc.console.domain.model.config.ConfigValueType;
import com.aisdlc.console.domain.model.config.SystemConfig;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/** 單元測試用的記憶體內 {@link SystemConfigRepository}（不需要資料庫）。 */
public final class InMemorySystemConfigRepository implements SystemConfigRepository {

    private final Map<String, SystemConfig> rows = new LinkedHashMap<>();
    private final List<ConfigHistoryEntry> history = new ArrayList<>();

    /** 新增一個非加密鍵。 */
    public InMemorySystemConfigRepository with(String category, String key, ConfigValueType type, String value) {
        rows.put(category + "." + key, new SystemConfig(UUID.randomUUID(), category, key, value, type, value, "d",
                false, null, null, null, null));
        return this;
    }

    /** 新增一個加密鍵（{@code storedValue} 是儲存形式，測試以假 cipher 解密）。 */
    public InMemorySystemConfigRepository withEncrypted(String category, String key, String storedValue) {
        rows.put(category + "." + key, new SystemConfig(UUID.randomUUID(), category, key, storedValue,
                ConfigValueType.ENCRYPTED, "", "d", true, null, null, null, null));
        return this;
    }

    public InMemorySystemConfigRepository set(String category, String key, String value) {
        SystemConfig existing = rows.get(category + "." + key);
        rows.put(category + "." + key, existing.withValue(value, null, null));
        return this;
    }

    @Override
    public List<SystemConfig> findAll() {
        return List.copyOf(rows.values());
    }

    @Override
    public List<SystemConfig> findByCategory(String category) {
        return rows.values().stream().filter(c -> c.category().equals(category)).toList();
    }

    @Override
    public Optional<SystemConfig> find(String category, String key) {
        return Optional.ofNullable(rows.get(category + "." + key));
    }

    @Override
    public Optional<SystemConfig> findForUpdate(String category, String key) {
        return find(category, key);
    }

    @Override
    public SystemConfig save(SystemConfig config) {
        rows.put(config.fullKey(), config);
        return config;
    }

    @Override
    public void addHistory(ConfigHistoryEntry entry) {
        history.add(entry);
    }

    @Override
    public PageResult<ConfigHistoryEntry> history(String category, String key, int page, int size) {
        List<ConfigHistoryEntry> filtered = history.stream()
                .filter(h -> category == null || h.category().equals(category))
                .filter(h -> key == null || h.key().equals(key))
                .sorted(Comparator.comparing(ConfigHistoryEntry::changedAt).reversed()).toList();
        int from = Math.min(filtered.size(), page * size);
        return new PageResult<>(filtered.subList(from, Math.min(filtered.size(), from + size)), page, size,
                filtered.size());
    }

    public List<ConfigHistoryEntry> historyEntries() {
        return List.copyOf(history);
    }
}
