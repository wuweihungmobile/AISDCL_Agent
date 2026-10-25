package com.aisdlc.console.application.service;

import com.aisdlc.console.domain.model.si.SiAuditKeyRing;
import com.aisdlc.console.domain.model.si.SiCloseCommand;
import com.aisdlc.console.domain.model.si.SiDecideCommand;
import com.aisdlc.console.domain.model.si.SiObservationCommand;
import com.aisdlc.console.domain.model.si.SiWriteKind;
import org.springframework.stereotype.Component;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.HexFormat;
import java.util.Locale;

/**
 * 稽核 JSON 的組裝與簽章（TCS-SelfImprovingDecide-P2b W7、W8；位元組契約以根層 {@code consoleaudit.py} 為準）。
 *
 * <p><b>簽什麼</b>：{@code body} 是緊湊 JSON 文字，鍵序與鍵集合依表 M-D、M-O、M-C；HMAC-SHA256(金鑰, {@code body} 的 UTF-8 位元組)，
 * <b>簽 body 字串本身、不重新序列化</b>；金鑰＝環中<b>第一把</b>的 UTF-8 位元組（不做 base64 解碼）；{@code key_id}＝sha256(金鑰) 前 8 碼小寫十六進位。
 * 外層檔恰七鍵、序固定（{@code schema_rev、kind、audit_ref、subject、body、key_id、mac}），緊湊、UTF-8 無 BOM、無結尾換行；
 * <b>檔位元組＝backend 送出的請求本文＝Bridge 落檔位元組＝{@code audit_sha256} 的對象</b>。
 *
 * <p><b>時間</b>：{@code time}＝時鐘現在、截到秒、樣式 {@code yyyy-MM-dd'T'HH:mm:ss} 接 {@code xxx}（UTC 為 {@code +00:00}，
 * <b>絕不輸出 {@code Z}</b>：根層 CLI 先於 MAC 以 AUDIT-TIME-FORMAT 拒收 {@code Z}）。
 *
 * <p>🔴 金鑰值只在 {@link #sign} 的區域變數裡短暫存在：不進例外訊息、日誌與回傳值（{@link SignedAudit} 不含金鑰）。
 */
@Component
public class SiAuditSigner {

    /** 稽核 JSON 的 {@code schema_rev}（根層 CLI 只收 1）。 */
    public static final int SCHEMA_REV = 1;
    /** Console 寫入者的角色：恆為 ADMIN（K=1 掌舵者；PRD AC-SI-35-4）。 */
    public static final String ROLE = "ADMIN";

    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssxxx", Locale.ROOT);
    private static final String HMAC = "HmacSHA256";

    private final Clock clock;

    public SiAuditSigner(Clock clock) {
        this.clock = clock;
    }

    /**
     * 簽好的稽核 JSON。
     *
     * @param kind   外層 {@code kind}
     * @param subject 外層 {@code subject}（obs-add 為 {@code null}）
     * @param body   被簽章的 body 字串（逐字）
     * @param keyId  金鑰 sha256 前 8 碼
     * @param mac    HMAC-SHA256 小寫十六進位
     * @param file   外層檔全文（請求本文；Bridge 落檔的位元組＝它的 UTF-8）
     */
    public record SignedAudit(SiWriteKind kind, String auditRef, String subject, String body, String keyId, String mac,
                              String file) {

        /** 外層檔的 UTF-8 位元組。 */
        public byte[] fileBytes() {
            return file.getBytes(StandardCharsets.UTF_8);
        }

        /** {@code audit_sha256}：外層檔位元組的 {@code sha256:} 加 64 位小寫十六進位。 */
        public String fileSha256() {
            return "sha256:" + HexFormat.of().formatHex(digest(fileBytes()));
        }
    }

    /** 時鐘現在、截到秒（毫秒被截斷、不四捨五入），偏移取時鐘的時區。 */
    public OffsetDateTime now() {
        return OffsetDateTime.now(clock).truncatedTo(ChronoUnit.SECONDS);
    }

    /** {@code yyyy-MM-ddTHH:mm:ss±HH:MM}：UTC 為 {@code +00:00}，絕不是 {@code Z}。 */
    public static String formatTime(OffsetDateTime time) {
        return time.truncatedTo(ChronoUnit.SECONDS).format(TIME);
    }

    // ── body 組裝（鍵序固定：W7、表 M-D／M-O／M-C）──────────────────────────────────────────

    /** 決定的 body：{@code …,time,(prop|run),[digest],dkind,[reason_class],[reason],flags}；{@code flags} 恆在。 */
    public String decideBody(String auditRef, String user, String time, SiDecideCommand command) {
        SiAuditJson json = header(auditRef, SiWriteKind.DECIDE, user, time)
                .string("resume".equals(command.dkind()) ? "run" : "prop", command.subject());
        if (command.digest() != null) {
            json.string("digest", command.digest());
        }
        json.string("dkind", command.dkind());
        if (command.reasonClass() != null) {
            json.string("reason_class", command.reasonClass());
        }
        if (command.reason() != null) {
            json.string("reason", command.reason());
        }
        return json.stringArray("flags", command.flags()).end();
    }

    /**
     * 新增觀察的 body：{@code …,time,context,symptom,evidence,category,severity,face,[exposure],external_derived,[corrects]}。
     * {@code auditRef} 為 {@code null}＝<b>未簽</b>的預檢 body（無 {@code audit_ref}；不帶 {@code mac}、{@code key_id}）。
     */
    public String observationBody(String auditRef, String user, String time, SiObservationCommand command) {
        SiAuditJson json = header(auditRef, SiWriteKind.OBS_ADD, user, time).string("context", command.context())
                .string("symptom", command.symptom()).string("evidence", command.evidence())
                .string("category", command.category()).string("severity", command.severity()).string("face", command.face());
        if (command.exposure() != null) {
            json.string("exposure", command.exposure());
        }
        json.bool("external_derived", command.externalDerived());
        if (command.corrects() != null) {
            json.string("corrects", command.corrects());
        }
        return json.end();
    }

    /** 關閉觀察的 body：{@code …,time,obs_id,disposition}。 */
    public String closeBody(String auditRef, String user, String time, SiCloseCommand command) {
        return header(auditRef, SiWriteKind.OBS_CLOSE, user, time).string("obs_id", command.obsId())
                .string("disposition", command.disposition()).end();
    }

    private static SiAuditJson header(String auditRef, SiWriteKind kind, String user, String time) {
        SiAuditJson json = new SiAuditJson().number("schema_rev", SCHEMA_REV);
        if (auditRef != null) {
            json.string("audit_ref", auditRef);
        }
        return json.string("kind", kind.wire()).string("user", user).string("role", ROLE).string("time", time);
    }

    // ── 簽章與外層檔 ────────────────────────────────────────────────────────────────────

    /**
     * 簽 {@code body}（環中第一把金鑰）並組外層檔。環是空的丟 {@link IllegalStateException}（呼叫端本來就該先檢查停用）。
     *
     * @param subject decide＝PROP 號（resume 為 RUN 號）、obs-close＝OBS 號、obs-add＝{@code null}；須等於 body 的 {@code prop}／{@code run}／{@code obs_id}
     */
    public SignedAudit sign(SiWriteKind kind, String auditRef, String subject, String body, SiAuditKeyRing keys) {
        byte[] key = keys.signingKey().getBytes(StandardCharsets.UTF_8);
        String mac = HexFormat.of().formatHex(hmac(key, body.getBytes(StandardCharsets.UTF_8)));
        String keyId = HexFormat.of().formatHex(digest(key)).substring(0, 8);
        String file = new SiAuditJson().number("schema_rev", SCHEMA_REV).string("kind", kind.wire())
                .string("audit_ref", auditRef).nullableString("subject", subject).string("body", body)
                .string("key_id", keyId).string("mac", mac).end();
        return new SignedAudit(kind, auditRef, subject, body, keyId, mac, file);
    }

    private static byte[] hmac(byte[] key, byte[] message) {
        try {
            Mac mac = Mac.getInstance(HMAC);
            mac.init(new SecretKeySpec(key, HMAC));
            return mac.doFinal(message);
        } catch (GeneralSecurityException e) {
            // HmacSHA256 是每個 JRE 必備的演算法；金鑰是非空位元組。走到這裡是環境壞了，不是輸入問題。
            throw new IllegalStateException("無法計算 HMAC-SHA256：" + e.getClass().getSimpleName(), e);
        }
    }

    private static byte[] digest(byte[] bytes) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(bytes);
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("無法計算 SHA-256：" + e.getClass().getSimpleName(), e);
        }
    }
}
