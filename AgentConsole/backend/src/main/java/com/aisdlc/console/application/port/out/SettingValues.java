package com.aisdlc.console.application.port.out;

import java.util.Optional;

/**
 * 系統參數的「非機密、唯讀」查詢埠：給需要讀位址類設定（例：{@code autoclaude.engineUrl}）的出站介面卡用，
 * 不解密、不做任何驗證。需要解密或型別轉換的用例請用 {@code SettingsReader}。
 */
public interface SettingValues {

    /** 鍵的儲存值（不解密）；鍵不存在回 empty。 */
    Optional<String> find(String category, String key);

    /**
     * 只在管理員改過（目前值不等於出廠預設值）時回傳目前值；沒改過或鍵不存在回 empty。
     * 用來讓「環境變數的部署預設」與「設定頁的明示修改」共存：沒人動過設定頁時，以環境變數為準。
     */
    Optional<String> findCustomized(String category, String key);
}
