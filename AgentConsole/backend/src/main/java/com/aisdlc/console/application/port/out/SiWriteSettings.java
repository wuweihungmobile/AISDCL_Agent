package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.si.SiAuditKeyRing;

import java.util.List;

/**
 * SelfImproving 寫入載體的程序層設定（TCS-SelfImprovingDecide-P2b W9）。application 層不認得 {@code infrastructure}，所以名單、
 * 金鑰環與權杖狀態經這支埠取值（實作：{@code SiWriteSettingsAdapter}，由 {@code console.si.*} 與 {@code console.bridge.si-write-token}
 * 轉出）。每次呼叫都重新取值：設定來源改變，下一個請求就用新值（測試以可切換的實作驗閘門序）。
 *
 * <p><b>寫入面啟用＝金鑰環與 Bridge 寫入權杖皆有設</b>（{@link #deciders()} 可空：空名單只代表沒有人有資格）。
 * 權杖值只有 Bridge 出站介面卡持有，application 層永遠看不到它——這裡只回有沒有設。
 */
public interface SiWriteSettings {

    /** 可寫入的帳號名單（去空白、去重、保序）；比對須與 JWT subject 逐字相等、區分大小寫。預設空＝無人可寫。 */
    List<String> deciders();

    /** 稽核簽章金鑰環（第一把簽章）；空＝未設。 */
    SiAuditKeyRing keyRing();

    /** backend 是否設定了 Bridge 的 SelfImproving 寫入權杖（{@code console.bridge.si-write-token}）。 */
    boolean bridgeWriteTokenConfigured();
}
