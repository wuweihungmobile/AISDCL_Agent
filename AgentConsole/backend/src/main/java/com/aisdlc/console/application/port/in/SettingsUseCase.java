package com.aisdlc.console.application.port.in;

import com.aisdlc.console.domain.model.config.ConfigHistoryEntry;
import com.aisdlc.console.domain.model.config.ConfigSpec;
import com.aisdlc.console.domain.model.config.SystemConfig;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * 系統參數用例（PRD §5.5、§7.1.8；契約 §1.5）。讀取一律遮罩加密值（{@code reveal} 另由呼叫端先驗 ADMIN 角色）；
 * 寫入一律需要 ADMIN（角色由安全層擋）。任何失敗都不改任何一個鍵。
 */
public interface SettingsUseCase {

    /**
     * 一個設定鍵的輸出視圖。
     *
     * @param displayValue 加密參數為遮罩字串（或 {@code reveal} 時的明文）；其餘為值本身
     * @param hasValue     加密參數是否已有非空值
     */
    record ConfigView(SystemConfig config, ConfigSpec spec, String displayValue, boolean hasValue) {
    }

    /**
     * 測試連線的請求（全部選填；省略的欄位取已儲存的 model.*）。
     *
     * @param apiKey 僅寫入、不回顯、不寫日誌
     */
    record TestConnectionCommand(String apiUrl, String apiKey, String model) {
    }

    /** 測試連線的結果（只要實際嘗試過連線，成功或失敗都回這個）。 */
    record ConnectionTestResult(boolean success, Long latencyMs, String message, String resolvedHost,
                                Integer httpStatus) {
    }

    /** 匯出文件（契約 §1.5.9；{@code exportedAt} 為 UTC）。 */
    record ExportedSettings(int version, Instant exportedAt, List<ExportedItem> configs) {
    }

    record ExportedItem(String category, String key, String value) {
    }

    record ImportError(String category, String key, String reason) {
    }

    record ImportResult(int applied, int skipped, List<ImportError> errors) {
    }

    /** 全部分類（依 {@code model,agent,execution,monitor,autoclaude,sdd}；分類內依附錄 C）。 */
    Map<String, List<ConfigView>> listAll(boolean reveal);

    /** 單一分類；分類不存在 → NotFoundException。 */
    List<ConfigView> listCategory(String category, boolean reveal);

    ConfigView update(String category, String key, String value, boolean confirm, String actor);

    List<ConfigView> updateTokenGuard(int compactThresholdPct, int haltThresholdPct, String actor);

    ConfigView reset(String category, String key, boolean confirm, String actor);

    List<ConfigView> resetCategory(String category, boolean confirm, String actor);

    ConnectionTestResult testConnection(TestConnectionCommand command, String actor);

    PageResult<ConfigHistoryEntry> history(String category, String key, int page, int size);

    ExportedSettings export();

    /**
     * 匯入設定（契約 §1.5.10）：檔案層的檢查（大小／副檔名／JSON 格式／version）在 Web 層做完，這裡只收解析好的項目。
     * 逐筆驗證（型別／規則／範圍／選項／SEC-04 allowlist）；通過者在同一交易套用並各寫歷史；
     * {@code <encrypted>} 佔位值與值未變者計入 skipped；token_guard 兩鍵以合併後的最終值做跨鍵校驗。
     */
    ImportResult importSettings(List<ExportedItem> items, String actor);
}
