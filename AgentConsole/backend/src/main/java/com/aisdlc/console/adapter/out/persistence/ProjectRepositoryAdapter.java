package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.in.ManageProjectUseCase.ListQuery;
import com.aisdlc.console.application.port.in.ManageProjectUseCase.ProjectCounts;
import com.aisdlc.console.application.port.in.ManageProjectUseCase.SortField;
import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.task.TaskStatus;
import com.aisdlc.console.infrastructure.persistence.entity.ProjectEntity;
import com.aisdlc.console.infrastructure.persistence.repository.GoalJpaRepository;
import com.aisdlc.console.infrastructure.persistence.repository.KeyedCount;
import com.aisdlc.console.infrastructure.persistence.repository.KeyedTaskCount;
import com.aisdlc.console.infrastructure.persistence.repository.ProjectJpaRepository;
import com.aisdlc.console.infrastructure.persistence.repository.TaskJpaRepository;
import jakarta.persistence.criteria.Predicate;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/** {@link ProjectRepository} 的 JPA 實作（Entity↔Domain 轉換在 {@link ProjectMapper}）。 */
@Component
class ProjectRepositoryAdapter implements ProjectRepository {

    private final ProjectJpaRepository projects;
    private final GoalJpaRepository goals;
    private final TaskJpaRepository tasks;

    ProjectRepositoryAdapter(ProjectJpaRepository projects, GoalJpaRepository goals, TaskJpaRepository tasks) {
        this.projects = projects;
        this.goals = goals;
        this.tasks = tasks;
    }

    @Override
    public Project save(Project project) {
        projects.save(ProjectMapper.toEntity(project));
        return project;
    }

    @Override
    public Optional<Project> findById(UUID id) {
        return projects.findByIdAndDeletedFalse(id).map(ProjectMapper::toDomain);
    }

    @Override
    public Optional<Project> findByIdForUpdate(UUID id) {
        return projects.findActiveByIdForUpdate(id).map(ProjectMapper::toDomain);
    }

    @Override
    public Optional<Project> findIncludingDeletedForUpdate(UUID id) {
        return projects.findAnyByIdForUpdate(id).map(ProjectMapper::toDomain);
    }

    @Override
    public PageResult<Project> search(ListQuery query) {
        Sort.Direction direction = query.ascending() ? Sort.Direction.ASC : Sort.Direction.DESC;
        Sort sort = Sort.by(direction, sortProperty(query.sortField())).and(Sort.by(Sort.Direction.ASC, "id"));
        Page<ProjectEntity> page = projects.findAll(specification(query),
                PageRequest.of(query.page(), query.size(), sort));
        return new PageResult<>(page.getContent().stream().map(ProjectMapper::toDomain).toList(),
                query.page(), query.size(), page.getTotalElements());
    }

    @Override
    public Map<UUID, ProjectCounts> countsFor(Collection<UUID> projectIds) {
        Map<UUID, ProjectCounts> result = new HashMap<>();
        if (projectIds.isEmpty()) {
            return result;
        }
        Map<UUID, Long> goalCounts = new HashMap<>();
        for (KeyedCount row : goals.countByProjects(projectIds)) {
            goalCounts.put(row.key(), row.count());
        }
        Map<UUID, KeyedTaskCount> taskCounts = new HashMap<>();
        for (KeyedTaskCount row : tasks.countByProjects(projectIds, TaskStatus.COMPLETED)) {
            taskCounts.put(row.key(), row);
        }
        for (UUID id : projectIds) {
            KeyedTaskCount t = taskCounts.get(id);
            result.put(id, new ProjectCounts(goalCounts.getOrDefault(id, 0L).intValue(),
                    t == null ? 0 : t.total().intValue(), t == null ? 0 : t.completed().intValue()));
        }
        return result;
    }

    private static String sortProperty(SortField field) {
        return switch (field) {
            case NAME -> "name";
            case STATUS -> "status";
            case CREATED_AT -> "createdAt";
            case UPDATED_AT -> "updatedAt";
        };
    }

    private static Specification<ProjectEntity> specification(ListQuery query) {
        return (root, criteria, cb) -> {
            List<Predicate> predicates = new ArrayList<>();
            predicates.add(query.deleted() ? cb.isTrue(root.get("deleted")) : cb.isFalse(root.get("deleted")));
            if (query.nameQuery() != null && !query.nameQuery().isBlank()) {
                String pattern = "%" + escapeLike(query.nameQuery().strip().toLowerCase(Locale.ROOT)) + "%";
                predicates.add(cb.like(cb.lower(root.get("name")), pattern, '\\'));
            }
            if (query.status() != null) {
                predicates.add(cb.equal(root.get("status"), query.status()));
            }
            return cb.and(predicates.toArray(new Predicate[0]));
        };
    }

    /** 把使用者輸入中的 LIKE 萬用字元（% _）與跳脫字元本身當成字面值。 */
    private static String escapeLike(String raw) {
        return raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_");
    }
}
