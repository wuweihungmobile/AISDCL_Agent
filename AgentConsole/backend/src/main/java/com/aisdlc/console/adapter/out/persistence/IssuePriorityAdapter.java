package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.IssuePriorityRepository;
import com.aisdlc.console.domain.model.issue.IssuePriority;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 議題優先順序表（{@code console.issue_priority}；TCS-IssueCenter-20261027 R-IC-59、§C6）的 JDBC 實作：<b>整個 backend 唯一存取這張表的類別</b>
 * （ArchUnit 鎖住）。沒有 JPA 實體——列沒有生命週期、用不到實體的髒檢查與合併；寫入敘述恰兩條：UPSERT（單列原子：並發時恰留一列、值完整，後提交者生效）
 * 與 DELETE（列不存在也不是錯），另有一條唯讀 SELECT。不存歷史（變更軌跡在 {@code console.audit_log}）。
 */
@Component
class IssuePriorityAdapter implements IssuePriorityRepository {

    private final JdbcTemplate jdbc;

    IssuePriorityAdapter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Map<String, IssuePriority> findByIssueIds(Collection<String> issueIds) {
        if (issueIds.isEmpty()) {
            return Map.of();
        }
        Object[] ids = issueIds.toArray();
        List<IssuePriority> rows = jdbc.query("select issue_id, rank, note, set_by, set_at from console.issue_priority "
                + "where issue_id = any(?)", ps -> ps.setArray(1, ps.getConnection().createArrayOf("varchar", ids)),
                (rs, n) -> new IssuePriority(rs.getString("issue_id"), rs.getInt("rank"), rs.getString("note"),
                        rs.getString("set_by"), rs.getObject("set_at", OffsetDateTime.class)));
        Map<String, IssuePriority> byId = new LinkedHashMap<>();
        for (IssuePriority row : rows) {
            byId.put(row.issueId(), row);
        }
        return byId;
    }

    @Override
    public void upsert(IssuePriority priority) {
        jdbc.update("insert into console.issue_priority (issue_id, rank, note, set_by, set_at) values (?, ?, ?, ?, ?) "
                + "on conflict (issue_id) do update set rank = excluded.rank, note = excluded.note, "
                + "set_by = excluded.set_by, set_at = excluded.set_at",
                priority.issueId(), priority.rank(), priority.note(), priority.setBy(), priority.setAt());
    }

    @Override
    public void delete(String issueId) {
        jdbc.update("delete from console.issue_priority where issue_id = ?", issueId);
    }
}
