package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.SecretCipher;
import com.aisdlc.console.application.port.out.SystemConfigRepository;
import com.aisdlc.console.domain.model.config.SystemConfig;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

/**
 * 研究分流用的 GitHub token 來源（D-98）：後端設定鍵 {@code research.github_token}（{@code system_configs} 的加密列、預設空；<b>不加 DDL</b>）。只在
 * {@code route} 且 {@code createGithub=true} 時由 {@link ResearchRouteService} 讀取，放進該次 Bridge 請求本文的 {@code github_token}（單次、只在記憶體；
 * Bridge 只經子行程環境 {@code GH_TOKEN} 傳給 {@code gh}）。🔴 明文絕不進日誌、回應 DTO、稽核列、{@code details} 或任何 {@code toString()}。
 *
 * <p>沒有這一列（部署未種子）或值為空＝回 empty：console-api 不預先阻擋，由 Bridge 的 {@code GH_REPO_CREATE} 步驟失敗並說明（AT-961-6-8）。
 */
@Component
class ResearchGithubTokenSource {

    static final String CATEGORY = "research";
    static final String KEY = "github_token";

    private final SystemConfigRepository configs;
    private final SecretCipher cipher;

    ResearchGithubTokenSource(SystemConfigRepository configs, SecretCipher cipher) {
        this.configs = configs;
        this.cipher = cipher;
    }

    /** 解密後的 token；沒有列或沒有值＝empty。 */
    @Transactional(readOnly = true)
    Optional<String> token() {
        return configs.find(CATEGORY, KEY).filter(SystemConfig::hasValue).map(config -> cipher.decrypt(config.value())).filter(value -> !value.isBlank());
    }
}
