package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.SecretCipher;
import com.aisdlc.console.application.port.out.SystemConfigRepository;
import com.aisdlc.console.domain.model.config.SystemConfig;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * 系統參數的「讀取 API」（給其他用例用：匯入路徑 B 讀 model.*；W3-B2 的 {@code ConfigMaterializer} 讀 agent.*／execution.*
 * 等並物化給 Bridge）。每次呼叫都讀資料庫的<b>當下值</b>（設定改了立即生效，契約附錄 C 的「新批次起生效」由呼叫端的時機決定）。
 *
 * <p>加密參數一律回<b>解密後的明文</b>（只在記憶體；呼叫端不得寫日誌或放進回應）——這是全後端唯一的解密入口之一
 * （另一個是 ADMIN 的 {@code reveal=true}，在 {@link SettingsService}）。
 */
@Component
public class SettingsReader {

    private final SystemConfigRepository repository;
    private final SecretCipher cipher;

    public SettingsReader(SystemConfigRepository repository, SecretCipher cipher) {
        this.repository = repository;
        this.cipher = cipher;
    }

    /** 匯入路徑 B 與測試連線需要的 model.* 設定（皆為呼叫當下的值）。 */
    public record ModelSettings(String apiUrl, String apiKey, String name, int timeoutSeconds, double temperature,
                                double topP, int maxTokensPerRequest, boolean enableKernelBrain) {
    }

    /** 鍵的值（加密參數為明文；沒有值的加密參數為空字串）。鍵不存在丟 {@link IllegalStateException}（種子由 Flyway 保證）。 */
    @Transactional(readOnly = true)
    public String value(String category, String key) {
        SystemConfig config = repository.find(category, key).orElseThrow(
                () -> new IllegalStateException("系統參數不存在：" + category + "." + key));
        return plain(config);
    }

    @Transactional(readOnly = true)
    public int intValue(String category, String key) {
        return Integer.parseInt(value(category, key));
    }

    @Transactional(readOnly = true)
    public long longValue(String category, String key) {
        return Long.parseLong(value(category, key));
    }

    @Transactional(readOnly = true)
    public double doubleValue(String category, String key) {
        return Double.parseDouble(value(category, key));
    }

    @Transactional(readOnly = true)
    public boolean booleanValue(String category, String key) {
        return Boolean.parseBoolean(value(category, key));
    }

    @Transactional(readOnly = true)
    public ModelSettings modelSettings() {
        return new ModelSettings(value("model", "apiUrl"), value("model", "apiKey"), value("model", "name"),
                intValue("model", "timeout"), doubleValue("model", "temperature"), doubleValue("model", "topP"),
                intValue("model", "maxTokensPerRequest"), booleanValue("model", "enableKernelBrain"));
    }

    String plain(SystemConfig config) {
        if (config.encrypted() && config.hasValue()) {
            return cipher.decrypt(config.value());
        }
        return config.value() == null ? "" : config.value();
    }
}
