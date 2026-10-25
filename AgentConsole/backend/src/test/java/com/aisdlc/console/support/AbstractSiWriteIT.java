package com.aisdlc.console.support;

import com.aisdlc.console.domain.model.auth.Role;
import com.aisdlc.console.infrastructure.security.JwtTokenService;
import com.aisdlc.minibridge.MiniBridge;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.TestPropertySource;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * SelfImproving 寫入整合測試的共同基底（TCS-SelfImprovingDecide-P2b §5.4）：沿 {@link AbstractExecutionIT} 的完整 context、真 PostgreSQL 與迷你
 * Bridge，另以 {@link SiWriteSeam} 固定簽章時間、稽核編號與（可切換的）寫入設定，並設 {@code console.si.deciders=admin,ops_admin}、
 * {@code console.si.audit-key=K0}、{@code console.bridge.si-write-token=T0}（寫入面預設啟用）。
 *
 * <p>每個測試開始前：清空 {@code console.si_console_writes}、重設迷你 Bridge 的 SI 夾具、佇列、設定覆寫與讀取逾時。
 */
@Import(SiWriteSeam.class)
@TestPropertySource(properties = {"console.si.deciders=admin,ops_admin", "console.si.audit-key=" + SiWriteSeam.K0,
        "console.bridge.si-write-token=" + SiWriteSeam.T0})
public abstract class AbstractSiWriteIT extends AbstractExecutionIT {

    protected static final String SI = "/api/v1/si";
    protected static final String D0 = "sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c";
    protected static final String PROP = "PROP-SI-004";
    protected static final String RUN = "RUN-SI-001";
    protected static final String OBS = "OBS-SI-005";

    @Autowired
    protected SiWriteSeam.Switchable settings;
    @Autowired
    protected SiWriteSeam.QueueRefs refs;
    @Autowired
    protected SiWriteSeam.ReadTimeoutCap readTimeout;
    @Autowired
    protected JwtTokenService jwt;

    @BeforeEach
    void resetSiWriteFixtures() {
        jdbc.execute("TRUNCATE console.si_console_writes");
        MINI.si.reset();
        settings.reset();
        refs.reset();
        readTimeout.reset();
    }

    @AfterEach
    void restoreSiWriteFixtures() {
        settings.reset();
        refs.reset();
        readTimeout.reset();
        MINI.si.reset();
    }

    /** 以任意帳號名鑄 ADMIN 角色的 access token（名單內外與帳號名值域的案例用；{@link #admin()} 的帳號名是 {@code admin}）。 */
    protected String adminAs(String username) {
        return jwt.issue(username, Role.ADMIN).accessToken();
    }

    protected String roleToken(String username, Role role) {
        return jwt.issue(username, role).accessToken();
    }

    protected ApiClient.Resp post(String token, String path, Object body) {
        return api.post(token, SI + path, body);
    }

    // ── 標準輸入（§5.2 的表 M-D、M-O、M-C）────────────────────────────────────────────────────

    protected static Map<String, Object> map(Object... keyValues) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            out.put((String) keyValues[i], keyValues[i + 1]);
        }
        return out;
    }

    protected static Map<String, Object> approve() {
        return map("dkind", "approve", "digest", D0);
    }

    protected static Map<String, Object> reject() {
        return map("dkind", "reject", "digest", D0, "reason", "證據座標不足，無法判定", "reasonClass", "證據不足");
    }

    /** 表 M-O 的 O1（＝黃金檔 G3 的輸入）。 */
    protected static Map<String, Object> observation() {
        return map("context", "Console・自我進化頁", "symptom", "待入帳徽章在入帳後仍顯示",
                "evidence", "AgentConsole/frontend/components/domain/si/SiView.tsx:88", "category", "bug", "severity", "P3",
                "face", "產品", "externalDerived", false);
    }

    protected static Map<String, Object> closeDecided() {
        return map("terminal", "decided", "text", "夾具關閉");
    }

    /** 九個 dkind 各自的有效請求（表 M-D）：鍵為 dkind。 */
    protected static Map<String, Map<String, Object>> allDecides() {
        Map<String, Map<String, Object>> out = new LinkedHashMap<>();
        out.put("approve", approve());
        out.put("reject", reject());
        out.put("return", map("dkind", "return", "digest", D0, "reason", "改用 M 類", "reasonClass", "工件類別錯"));
        out.put("promote", map("dkind", "promote", "digest", D0));
        out.put("decline-promote", map("dkind", "decline-promote", "digest", D0, "reason", "風險太高", "reasonClass", "風險過高"));
        out.put("rollback", map("dkind", "rollback", "reason", "太慢"));
        out.put("unblock", map("dkind", "unblock"));
        out.put("resume", map("dkind", "resume", "reason", "兩個壞窗已人工檢視"));
        out.put("ack-handoff", map("dkind", "ack-handoff", "digest", D0));
        return out;
    }

    /** 路徑 id：resume 綁 RUN 號，其餘綁 PROP 號。 */
    protected static String idFor(String dkind) {
        return "resume".equals(dkind) ? RUN : PROP;
    }

    // ── 黃金檔與資料庫 ───────────────────────────────────────────────────────────────────────

    /** {@code src/test/resources/si/audit/<name>} 的位元組（Java 正式碼在固定輸入下的輸出；與 Bridge 的副本逐位元組相同）。 */
    protected static byte[] golden(String name) {
        try (InputStream in = AbstractSiWriteIT.class.getResourceAsStream("/si/audit/" + name)) {
            if (in == null) {
                throw new IllegalStateException("找不到黃金檔 si/audit/" + name);
            }
            return in.readAllBytes();
        } catch (IOException e) {
            throw new java.io.UncheckedIOException(e);
        }
    }

    /** §5.3 的稽核編號：{@code ref("a1", 3)}＝{@code a1000000-0000-4000-8000-000000000003}（系列 a1＝黃金檔、b2＝M-D、b3＝M-O、b4＝M-C）。 */
    protected static String ref(String series, int n) {
        return series + "000000-0000-4000-8000-0000000000" + String.format("%02d", n);
    }

    /** 稽核列（依時間、編號排序）；{@code time_utc} 是 UTC 的 {@code yyyy-MM-ddTHH:mm:ssZ} 文字（不經 JDBC 的時間型別轉換）。 */
    protected List<Map<String, Object>> writeRows() {
        return jdbc.queryForList("select audit_ref::text as audit_ref, kind, \"user\", role, "
                + "to_char(\"time\" at time zone 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') as time_utc, subject_id, digest, body, "
                + "key_id, mac from console.si_console_writes order by \"time\", audit_ref");
    }

    /** 直接塞一列稽核列（對帳測試的夾具；body 與 mac 是佔位）。{@code timeIso} 是帶偏移的 ISO 時間。 */
    protected void insertWrite(String auditRef, String kind, String subjectId, String digest, String timeIso) {
        jdbc.update("insert into console.si_console_writes (audit_ref, kind, \"user\", role, \"time\", subject_id, digest, body, "
                + "key_id, mac) values (?::uuid, ?, 'admin', 'ADMIN', ?::timestamptz, ?, ?, ?, 'f076edf0', ?)", auditRef, kind,
                timeIso, subjectId, digest, "{\"fixture\":true}", "0".repeat(64));
    }

    /** Bridge 的 export 物件（snake_case 的外層；對帳掃描只讀 items、truncated、next_since）。 */
    protected static Map<String, Object> export(String kind, List<Map<String, Object>> items, boolean truncated, Integer nextSince) {
        return map("schema_rev", 1, "kind", kind, "generated_at", "2026-10-24T22:30:15+08:00", "head_sha", null, "items", items,
                "next_since", nextSince, "truncated", truncated, "ne", List.of(), "problems", List.of());
    }

    /** 帳本事件項（鍵依根層 events.py：dec 的 prop／run、obs.add 與 obs.close 的 obs；carrier 與 audit_ref 為 Console 載體專有）。 */
    protected static Map<String, Object> event(int seq, String kind, String carrier, String auditRef, String subjectKey, String subject) {
        Map<String, Object> event = map("seq", seq, "t", "2026-10-24T22:30:15+08:00", "kind", kind);
        if (carrier != null) {
            event.put("carrier", carrier);
        }
        if (auditRef != null) {
            event.put("audit_ref", auditRef);
        }
        if (subjectKey != null) {
            event.put(subjectKey, subject);
        }
        return event;
    }

    /** 觀察列（只放對帳要用的鍵：id、marks_kv、line）；{@code auditRef} 為 null＝沒有 Console 標記。 */
    protected static Map<String, Object> observationRow(String id, String carrier, String auditRef, int line) {
        Map<String, Object> marks = map("來源", "人");
        if (carrier != null) {
            marks.put("carrier", carrier);
        }
        if (auditRef != null) {
            marks.put("audit_ref", auditRef);
        }
        return map("id", id, "disposition", "open", "marks_kv", marks, "line", line);
    }

    protected long writeCount() {
        Long count = jdbc.queryForObject("select count(*) from console.si_console_writes", Long.class);
        return count == null ? 0 : count;
    }

    /** 迷你 Bridge 收到的寫入請求本文（UTF-8 文字）。 */
    protected static String receivedText(int index) {
        return MINI.si.writes.get(index).text();
    }

    protected static byte[] receivedBytes(int index) {
        return MINI.si.writes.get(index).raw();
    }

    protected static String utf8(byte[] bytes) {
        return new String(bytes, StandardCharsets.UTF_8);
    }

    protected static MiniBridge.Si bridge() {
        return MINI.si;
    }
}
