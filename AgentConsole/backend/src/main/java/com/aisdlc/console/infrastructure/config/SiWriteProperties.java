package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.domain.model.si.SiAuditKeyRing;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * SelfImproving 寫入載體的程序層設定（{@code console.si.*}；TCS-SelfImprovingDecide-P2b W9）。
 *
 * <p>{@code deciders}（環境變數 {@code CONSOLE_SI_DECIDERS}，逗號清單）：可寫入的帳號名單——去前後空白、去空項、去重、<b>保序</b>；
 * 預設空＝無人可寫；比對＝與 JWT subject 逐字相等、區分大小寫（由用例入口判，這裡只正規化）。
 *
 * <p>{@code auditKey}（{@code CONSOLE_SI_AUDIT_KEY}）：稽核簽章的金鑰環（格式同根層 {@code AUTOSDD_SI_AUDIT_KEY}：逗號分隔、
 * 各自去空白、空項略過；<b>第一把簽章</b>，其餘保留供輪替——主機環須含全部仍待入帳檔所用的金鑰）。空或未設＝寫入面停用；
 * <b>有設而任一把短於 32 字元，或仍是 {@code <…>} 佔位＝啟動即失敗</b>（fail-loud，不靜默退回停用）。Bridge 不持有它。
 *
 * <p>🔴 金鑰值絕不進日誌、錯誤封包或 {@code details}：驗證錯誤訊息只講屬性名、第幾把與長度；{@link #toString()} 只標示有沒有設。
 *
 * @param deciders 正規化後的名單（不會是 null）
 * @param auditKey 去前後空白的環字串；空白＝{@code null}（停用）
 */
@ConfigurationProperties(prefix = "console.si")
public record SiWriteProperties(List<String> deciders, String auditKey) {

    /** 每把簽章金鑰的最短長度（與權杖一致；{@code openssl rand -hex 32} 產出 64 字元）。 */
    public static final int MIN_KEY_CHARS = 32;

    /** {@code <YOUR_CONSOLE_SI_AUDIT_KEY_MIN_32_CHARS>} 這類 {@code .env.example} 佔位。 */
    private static final Pattern PLACEHOLDER = Pattern.compile("^<[^<>]*>$");

    public SiWriteProperties {
        deciders = normalized(deciders);
        auditKey = checkedRing(auditKey);
    }

    /** 簽章金鑰環（未設＝{@link SiAuditKeyRing#EMPTY}）。 */
    public SiAuditKeyRing keyRing() {
        return SiAuditKeyRing.parse(auditKey);
    }

    private static List<String> normalized(List<String> raw) {
        if (raw == null) {
            return List.of();
        }
        Set<String> names = new LinkedHashSet<>();
        for (String name : raw) {
            if (name != null && !name.isBlank()) {
                names.add(name.strip());
            }
        }
        return List.copyOf(names);
    }

    private static String checkedRing(String raw) {
        SiAuditKeyRing ring = SiAuditKeyRing.parse(raw);
        if (ring.isEmpty()) {
            return null;
        }
        List<String> keys = ring.keys();
        for (int i = 0; i < keys.size(); i++) {
            String key = keys.get(i);
            if (PLACEHOLDER.matcher(key).matches()) {
                throw new IllegalArgumentException("console.si.audit-key（環境變數 CONSOLE_SI_AUDIT_KEY）第 " + (i + 1)
                        + " 把金鑰仍是 <…> 佔位，請換成至少 " + MIN_KEY_CHARS
                        + " 字元的隨機值（例：openssl rand -hex 32），或留空以停用 SelfImproving 寫入面");
            }
            if (key.length() < MIN_KEY_CHARS) {
                throw new IllegalArgumentException("console.si.audit-key（環境變數 CONSOLE_SI_AUDIT_KEY）第 " + (i + 1)
                        + " 把金鑰只有 " + key.length() + " 字元，至少需要 " + MIN_KEY_CHARS
                        + " 字元（例：openssl rand -hex 32）；或留空以停用 SelfImproving 寫入面");
            }
        }
        return raw.strip();
    }

    /** 金鑰值不外洩：只標示有沒有設。 */
    @Override
    public String toString() {
        return "SiWriteProperties[deciders=" + deciders + ", auditKey=" + (auditKey == null ? "<unset>" : "<set>") + "]";
    }
}
