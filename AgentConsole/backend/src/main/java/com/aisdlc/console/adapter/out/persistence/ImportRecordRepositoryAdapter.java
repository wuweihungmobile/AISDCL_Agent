package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.in.ImportUseCase.ListQuery;
import com.aisdlc.console.application.port.in.ImportUseCase.SortField;
import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.application.port.out.ImportRecordRepository;
import com.aisdlc.console.domain.model.imports.ImportRecord;
import com.aisdlc.console.infrastructure.persistence.repository.ImportRecordJpaRepository;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.TypedQuery;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.UUID;

/** {@link ImportRecordRepository} 的 JPA 實作（Entity↔Domain 轉換在 {@link ImportRecordMapper}）。 */
@Component
class ImportRecordRepositoryAdapter implements ImportRecordRepository {

    private static final String SELECT_SUMMARY = "select i.id, i.sourceType, i.sourceFileName, i.status, "
            + "i.signedOff, i.signedOffBy, i.signedOffAt, i.projectId, i.createdAt, i.aiModel, i.tokenUsed, "
            + "i.parsePath, i.lastParseErrors from ImportRecordEntity i";

    private final ImportRecordJpaRepository jpa;

    @PersistenceContext
    private EntityManager em;

    ImportRecordRepositoryAdapter(ImportRecordJpaRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public ImportRecord save(ImportRecord record) {
        jpa.save(ImportRecordMapper.toEntity(record));
        return record;
    }

    @Override
    public Optional<ImportRecord> findById(UUID id) {
        return jpa.findById(id).map(ImportRecordMapper::toDomain);
    }

    @Override
    public Optional<ImportRecord> findByIdForUpdate(UUID id) {
        return jpa.findForUpdate(id).map(ImportRecordMapper::toDomain);
    }

    @Override
    public PageResult<ImportRecord> search(ListQuery query) {
        List<String> clauses = new ArrayList<>();
        if (query.status() != null) {
            clauses.add("i.status = :status");
        }
        boolean hasName = query.fileNameQuery() != null && !query.fileNameQuery().isBlank();
        if (hasName) {
            clauses.add("lower(i.sourceFileName) like :name escape '\\'");
        }
        String where = clauses.isEmpty() ? "" : " where " + String.join(" and ", clauses);
        String direction = query.ascending() ? "asc" : "desc";
        String order = " order by " + (query.sortField() == SortField.STATUS ? "i.status " : "i.createdAt ")
                + direction + ", i.id asc";

        TypedQuery<Object[]> rows = em.createQuery(SELECT_SUMMARY + where + order, Object[].class);
        TypedQuery<Long> count = em.createQuery("select count(i) from ImportRecordEntity i" + where, Long.class);
        if (query.status() != null) {
            rows.setParameter("status", query.status().name());
            count.setParameter("status", query.status().name());
        }
        if (hasName) {
            String pattern = "%" + escapeLike(query.fileNameQuery().strip().toLowerCase(Locale.ROOT)) + "%";
            rows.setParameter("name", pattern);
            count.setParameter("name", pattern);
        }
        rows.setFirstResult(query.page() * query.size());
        rows.setMaxResults(query.size());
        List<ImportRecord> content = rows.getResultList().stream().map(ImportRecordMapper::toSummary).toList();
        return new PageResult<>(content, query.page(), query.size(), count.getSingleResult());
    }

    @Override
    public int resetStaleParsing() {
        return jpa.resetStaleParsing();
    }

    /** 把使用者輸入中的 LIKE 萬用字元（% _）與跳脫字元本身當成字面值。 */
    private static String escapeLike(String raw) {
        return raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_");
    }
}
