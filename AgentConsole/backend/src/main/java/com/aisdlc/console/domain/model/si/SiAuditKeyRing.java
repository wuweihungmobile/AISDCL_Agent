package com.aisdlc.console.domain.model.si;

import java.util.ArrayList;
import java.util.List;

/**
 * 稽核簽章的金鑰環（TCS-SelfImprovingDecide-P2b W7、W9；格式同根層 {@code AUTOSDD_SI_AUDIT_KEY}）：逗號分隔、各自去前後空白、
 * 空項略過；<b>第一把簽章</b>、其餘保留供輪替（主機環須含全部仍待入帳檔所用的金鑰）。空環＝未設＝寫入面停用。
 *
 * <p>🔴 金鑰值不外洩：{@link #toString()} 只講把數，不含任何金鑰字元（日誌、例外訊息與 {@code details} 都可能順手印出物件）。
 *
 * @param keys 去空白、去空項後的金鑰（保序）
 */
public record SiAuditKeyRing(List<String> keys) {

    /** 未設。 */
    public static final SiAuditKeyRing EMPTY = new SiAuditKeyRing(List.of());

    public SiAuditKeyRing {
        keys = keys == null ? List.of() : List.copyOf(keys);
    }

    /** 解析環字串；{@code null}、空白或全為空項＝{@link #EMPTY}。 */
    public static SiAuditKeyRing parse(String raw) {
        if (raw == null || raw.isBlank()) {
            return EMPTY;
        }
        List<String> keys = new ArrayList<>();
        for (String part : raw.split(",", -1)) {
            String key = part.strip();
            if (!key.isEmpty()) {
                keys.add(key);
            }
        }
        return new SiAuditKeyRing(keys);
    }

    public boolean isEmpty() {
        return keys.isEmpty();
    }

    /** 簽章用的金鑰（環中第一把）；環是空的＝呼叫端沒先檢查停用，丟 {@link IllegalStateException}。 */
    public String signingKey() {
        if (keys.isEmpty()) {
            throw new IllegalStateException("金鑰環是空的：寫入面應已停用，不該走到簽章");
        }
        return keys.get(0);
    }

    @Override
    public String toString() {
        return "SiAuditKeyRing[keys=" + keys.size() + "]";
    }
}
