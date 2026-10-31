package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.SiConsoleWriteQueries;
import com.aisdlc.console.application.port.out.SiConsoleWriteRepository;
import com.aisdlc.console.domain.model.si.SiConsoleWrite;
import com.aisdlc.console.domain.model.si.SiConsoleWriteSummary;
import com.aisdlc.console.domain.model.si.SiWriteKind;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Console 稽核列（{@code console.si_console_writes}；TCS-SelfImprovingDecide-P2b W11、W13、W14；TCS-SelfImprovingDecideDedupe W-D2）的 JDBC 實作：<b>整個 backend
 * 唯一存取這張表的類別</b>（ArchUnit 與原始碼掃描鎖住）。沒有 JPA 實體——列不可改，用不到實體的髒檢查與合併；寫入面只有三條：新增、補償刪除、
 * {@code subject_id} 回填（資料庫觸發器擋掉其餘任何欄位變動）。查詢不選整欄 {@code body} 與 {@code mac}，只以 {@link #DKIND} 表達式取出 {@code body} 內的
 * {@code dkind}（不改 Flyway、不加欄）。
 */
@Component
class SiConsoleWriteAdapter implements SiConsoleWriteRepository, SiConsoleWriteQueries {

    /**
     * 決定動詞：取自稽核列 {@code body}（TEXT；{@code SiAuditSigner} 自己產生的合法 JSON）的 {@code dkind} 鍵，且只對 {@code kind='decide'} 的列取——
     * 非 decide 列恆為 null（{@code case} 保護，不對它們做 JSON 轉型）；body 沒有 {@code dkind} 鍵的 decide 列也為 null。重送閘與對帳讀面共用這一個表達式，
     * 兩邊對「同一決定」的判斷才不會分歧。
     */
    private static final String DKIND = "case when kind = 'decide' then (body::jsonb)->>'dkind' end";

    /** 對帳讀面的投影：既有八欄加 {@link #DKIND}（別名 dkind）；不選整欄 body 與 mac。 */
    private static final String SUMMARY_COLUMNS = "audit_ref, kind, " + DKIND + " as dkind, \"user\", role, \"time\", subject_id, digest, key_id";

    private static final RowMapper<SiConsoleWriteSummary> SUMMARY = (rs, n) -> {
        OffsetDateTime time = rs.getObject("time", OffsetDateTime.class);
        SiWriteKind kind = SiWriteKind.fromWire(rs.getString("kind")).orElseThrow(
                () -> new IllegalStateException("資料庫有未知的 kind（CHECK 約束應已擋下）"));
        return new SiConsoleWriteSummary(JdbcSupport.uuid(rs, "audit_ref"), kind, rs.getString("dkind"), rs.getString("user"),
                rs.getString("role"), time, rs.getString("subject_id"), rs.getString("digest"), rs.getString("key_id"));
    };

    private final JdbcTemplate jdbc;

    SiConsoleWriteAdapter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public void insert(SiConsoleWrite row) {
        jdbc.update("insert into console.si_console_writes (audit_ref, kind, \"user\", role, \"time\", subject_id, digest, "
                + "body, key_id, mac) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", row.auditRef(), row.kind().wire(), row.user(),
                row.role(), row.time(), row.subjectId(), row.digest(), row.body(), row.keyId(), row.mac());
    }

    @Override
    public boolean deleteByAuditRef(UUID auditRef) {
        return jdbc.update("delete from console.si_console_writes where audit_ref = ?", auditRef) > 0;
    }

    @Override
    public List<UUID> findDecideAuditRefs(String subject, String digest, String dkind) {
        if (subject == null || digest == null || dkind == null) {
            return List.of();                               // 沒有卡面 digest 的動詞不受重送閘：不提供 null 比對
        }
        return jdbc.query("select audit_ref from console.si_console_writes where kind = 'decide' and subject_id = ? and digest = ? "
                + "and (" + DKIND + ") = ? order by \"time\" asc, audit_ref asc", (rs, n) -> JdbcSupport.uuid(rs, "audit_ref"),
                subject, digest, dkind);
    }

    @Override
    public List<SiConsoleWriteSummary> findRecent(int limit) {
        return jdbc.query("select " + SUMMARY_COLUMNS + " from console.si_console_writes order by \"time\" desc, audit_ref asc limit ?",
                SUMMARY, limit);
    }

    @Override
    public List<SiConsoleWriteSummary> findDecideRows() {
        return jdbc.query("select " + SUMMARY_COLUMNS + " from console.si_console_writes where kind = 'decide' "
                + "order by \"time\" asc, audit_ref asc", SUMMARY);
    }

    @Override
    public Set<UUID> findExistingAuditRefs(Collection<UUID> candidates) {
        if (candidates.isEmpty()) {
            return Set.of();
        }
        Object[] refs = candidates.toArray();
        List<UUID> found = jdbc.query("select audit_ref from console.si_console_writes where audit_ref = any(?)",
                ps -> ps.setArray(1, ps.getConnection().createArrayOf("uuid", refs)),
                (rs, n) -> JdbcSupport.uuid(rs, "audit_ref"));
        return new LinkedHashSet<>(found);
    }

    @Override
    public Set<UUID> findObsAddRefsWithoutSubject() {
        List<UUID> found = jdbc.query("select audit_ref from console.si_console_writes "
                + "where kind = 'obs-add' and subject_id is null", (rs, n) -> JdbcSupport.uuid(rs, "audit_ref"));
        return new LinkedHashSet<>(found);
    }

    @Override
    public int fillSubjectId(UUID auditRef, String subjectId) {
        return jdbc.update("update console.si_console_writes set subject_id = ? "
                + "where audit_ref = ? and subject_id is null and kind = 'obs-add'", subjectId, auditRef);
    }
}
