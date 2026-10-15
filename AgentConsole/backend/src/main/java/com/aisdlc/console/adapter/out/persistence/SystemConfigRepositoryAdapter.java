package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.application.port.out.SystemConfigRepository;
import com.aisdlc.console.domain.model.config.ConfigHistoryEntry;
import com.aisdlc.console.domain.model.config.ConfigValueType;
import com.aisdlc.console.domain.model.config.SystemConfig;
import com.aisdlc.console.infrastructure.persistence.entity.SystemConfigEntity;
import com.aisdlc.console.infrastructure.persistence.entity.SystemConfigHistoryEntity;
import com.aisdlc.console.infrastructure.persistence.repository.SystemConfigHistoryJpaRepository;
import com.aisdlc.console.infrastructure.persistence.repository.SystemConfigJpaRepository;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.TypedQuery;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** {@link SystemConfigRepository} 的 JPA 實作。 */
@Component
class SystemConfigRepositoryAdapter implements SystemConfigRepository {

    private static final String HISTORY_SELECT = "select h.id, h.configId, c.category, c.configKey, h.oldValue, "
            + "h.newValue, h.changedAt, h.changedBy from SystemConfigHistoryEntity h, SystemConfigEntity c "
            + "where c.id = h.configId";

    private final SystemConfigJpaRepository configs;
    private final SystemConfigHistoryJpaRepository history;

    @PersistenceContext
    private EntityManager em;

    SystemConfigRepositoryAdapter(SystemConfigJpaRepository configs, SystemConfigHistoryJpaRepository history) {
        this.configs = configs;
        this.history = history;
    }

    @Override
    public List<SystemConfig> findAll() {
        return configs.findAll().stream().map(SystemConfigRepositoryAdapter::toDomain).toList();
    }

    @Override
    public List<SystemConfig> findByCategory(String category) {
        return configs.findByCategory(category).stream().map(SystemConfigRepositoryAdapter::toDomain).toList();
    }

    @Override
    public Optional<SystemConfig> find(String category, String key) {
        return configs.findByCategoryAndConfigKey(category, key).map(SystemConfigRepositoryAdapter::toDomain);
    }

    @Override
    public Optional<SystemConfig> findForUpdate(String category, String key) {
        return configs.findForUpdate(category, key).map(SystemConfigRepositoryAdapter::toDomain);
    }

    @Override
    public SystemConfig save(SystemConfig config) {
        SystemConfigEntity entity = configs.findById(config.id()).orElseThrow(
                () -> new IllegalStateException("系統參數不存在：" + config.fullKey()));
        entity.configValue = config.value();
        entity.updatedAt = config.updatedAt();
        entity.updatedBy = config.updatedBy();
        configs.save(entity);
        return config;
    }

    @Override
    public void addHistory(ConfigHistoryEntry entry) {
        SystemConfigHistoryEntity entity = new SystemConfigHistoryEntity();
        entity.id = UUID.randomUUID();
        entity.configId = entry.configId();
        entity.oldValue = entry.oldValue();
        entity.newValue = entry.newValue();
        entity.changedAt = entry.changedAt();
        entity.changedBy = entry.changedBy();
        history.save(entity);
    }

    @Override
    public PageResult<ConfigHistoryEntry> history(String category, String key, int page, int size) {
        List<String> extra = new ArrayList<>();
        if (category != null) {
            extra.add("c.category = :category");
        }
        if (key != null) {
            extra.add("c.configKey = :key");
        }
        String filter = extra.isEmpty() ? "" : " and " + String.join(" and ", extra);
        TypedQuery<Object[]> rows = em.createQuery(HISTORY_SELECT + filter
                + " order by h.changedAt desc, h.id desc", Object[].class);
        TypedQuery<Long> count = em.createQuery("select count(h) from SystemConfigHistoryEntity h, "
                + "SystemConfigEntity c where c.id = h.configId" + filter, Long.class);
        if (category != null) {
            rows.setParameter("category", category);
            count.setParameter("category", category);
        }
        if (key != null) {
            rows.setParameter("key", key);
            count.setParameter("key", key);
        }
        rows.setFirstResult(page * size);
        rows.setMaxResults(size);
        List<ConfigHistoryEntry> content = rows.getResultList().stream().map(row -> new ConfigHistoryEntry(
                (UUID) row[0], (UUID) row[1], (String) row[2], (String) row[3], (String) row[4], (String) row[5],
                (Instant) row[6], (String) row[7])).toList();
        return new PageResult<>(content, page, size, count.getSingleResult());
    }

    private static SystemConfig toDomain(SystemConfigEntity e) {
        return new SystemConfig(e.id, e.category, e.configKey, e.configValue, ConfigValueType.valueOf(e.valueType),
                e.defaultValue, e.description, Boolean.TRUE.equals(e.encrypted), e.validationRule, e.impactNote,
                e.updatedAt, e.updatedBy);
    }
}
