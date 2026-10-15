package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.SettingValues;
import com.aisdlc.console.infrastructure.persistence.repository.SystemConfigJpaRepository;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.Objects;
import java.util.Optional;

/** {@link SettingValues} 的 JPA 實作：每次讀資料庫的當下值（設定改了立即生效）。 */
@Component
class SettingValuesAdapter implements SettingValues {

    private final SystemConfigJpaRepository configs;

    SettingValuesAdapter(SystemConfigJpaRepository configs) {
        this.configs = configs;
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<String> find(String category, String key) {
        return configs.findByCategoryAndConfigKey(category, key).map(entity -> entity.configValue);
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<String> findCustomized(String category, String key) {
        return configs.findByCategoryAndConfigKey(category, key)
                .filter(entity -> !Objects.equals(entity.configValue, entity.defaultValue))
                .map(entity -> entity.configValue);
    }
}
