package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.infrastructure.persistence.entity.GoalEntity;

import java.util.Collection;

/** Goal（domain）↔ GoalEntity（JPA）的轉換；依賴邊由 GoalRepositoryAdapter 另行同步。 */
final class GoalMapper {

    private GoalMapper() {
    }

    static GoalEntity toEntity(Goal g) {
        GoalEntity e = new GoalEntity();
        e.id = g.id();
        e.projectId = g.projectId();
        e.name = g.name();
        e.description = g.description();
        e.passCriteria = g.passCriteria();
        e.sortOrder = g.sortOrder();
        e.status = g.status();
        e.signedOff = g.signedOff();
        e.signedOffBy = g.signedOffBy();
        e.signedOffAt = g.signedOffAt();
        e.deleted = g.deleted();
        e.createdAt = g.createdAt();
        e.updatedAt = g.updatedAt();
        e.deletedAt = g.deletedAt();
        return e;
    }

    static Goal toDomain(GoalEntity e, Collection<java.util.UUID> dependsOn) {
        return Goal.restore(e.id, e.projectId, e.name, e.description, e.passCriteria,
                e.sortOrder == null ? 0 : e.sortOrder, e.status, dependsOn, e.signedOff, e.signedOffBy,
                e.signedOffAt, Boolean.TRUE.equals(e.deleted), e.createdAt, e.updatedAt, e.deletedAt);
    }
}
