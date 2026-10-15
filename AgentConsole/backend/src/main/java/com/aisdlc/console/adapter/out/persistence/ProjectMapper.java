package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.infrastructure.persistence.entity.ProjectEntity;

/** Project（domain）↔ ProjectEntity（JPA）的轉換；DDL 允許 NULL 的欄位在此補回 domain 的預設值。 */
final class ProjectMapper {

    private ProjectMapper() {
    }

    static ProjectEntity toEntity(Project p) {
        ProjectEntity e = new ProjectEntity();
        e.id = p.id();
        e.name = p.name();
        e.executionPath = p.executionPath();
        e.passCriteria = p.passCriteria();
        e.description = p.description();
        e.status = p.status();
        e.autonomyLevel = p.autonomyLevel();
        e.signedOff = p.signedOff();
        e.signedOffBy = p.signedOffBy();
        e.signedOffAt = p.signedOffAt();
        e.deleted = p.deleted();
        e.createdAt = p.createdAt();
        e.updatedAt = p.updatedAt();
        e.createdBy = p.createdBy();
        e.deletedAt = p.deletedAt();
        e.statusBeforeDelete = p.statusBeforeDelete();
        return e;
    }

    static Project toDomain(ProjectEntity e) {
        return Project.restore(e.id, e.name, e.executionPath, e.passCriteria, e.description, e.status,
                e.autonomyLevel == null ? Project.DEFAULT_AUTONOMY_LEVEL : e.autonomyLevel, e.signedOff,
                e.signedOffBy, e.signedOffAt, Boolean.TRUE.equals(e.deleted), e.createdAt, e.updatedAt,
                e.createdBy, e.deletedAt, e.statusBeforeDelete);
    }
}
