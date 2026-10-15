package com.aisdlc.console.domain.model.config;

/**
 * 參數對引擎的實際效果（誠實標示，Architecture §11.4；契約附錄 C）：
 * ENGINE＝物化進 config_overrides／env／playbook；CONSOLE＝Console 內部使用；
 * STORED_ONLY＝只儲存、不影響引擎（引擎無對應欄位）；UNVERIFIED＝可能對映，尚未驗證。
 */
public enum ConfigEffect {
    ENGINE,
    CONSOLE,
    STORED_ONLY,
    UNVERIFIED
}
