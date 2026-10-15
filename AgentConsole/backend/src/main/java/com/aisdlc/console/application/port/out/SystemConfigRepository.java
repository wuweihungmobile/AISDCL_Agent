package com.aisdlc.console.application.port.out;

import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.domain.model.config.ConfigHistoryEntry;
import com.aisdlc.console.domain.model.config.SystemConfig;

import java.util.List;
import java.util.Optional;

/** 系統參數與修改歷史儲存埠。 */
public interface SystemConfigRepository {

    List<SystemConfig> findAll();

    List<SystemConfig> findByCategory(String category);

    Optional<SystemConfig> find(String category, String key);

    /** 取鍵並鎖列（SELECT … FOR UPDATE）：token_guard 跨鍵校驗與寫入必須序列化，否則並發的兩個單鍵 PUT 會合起來違規。 */
    Optional<SystemConfig> findForUpdate(String category, String key);

    SystemConfig save(SystemConfig config);

    void addHistory(ConfigHistoryEntry entry);

    /**
     * 歷史（changedAt 由新到舊）；{@code category}／{@code key} 為 null 表示不篩（key 須與 category 併用由用例檢查）。
     */
    PageResult<ConfigHistoryEntry> history(String category, String key, int page, int size);
}
