package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.in.ManageProjectUseCase.ListQuery;
import com.aisdlc.console.application.port.in.ManageProjectUseCase.ProjectCounts;
import com.aisdlc.console.application.port.in.ManageProjectUseCase.SortField;
import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.task.TaskStatus;
import com.aisdlc.console.infrastructure.persistence.entity.ProjectEntity;
import com.aisdlc.console.infrastructure.persistence.repository.GoalJpaRepository;
import com.aisdlc.console.infrastructure.persistence.repository.KeyedCount;
import com.aisdlc.console.infrastructure.persistence.repository.KeyedTaskCount;
import com.aisdlc.console.infrastructure.persistence.repository.ProjectJpaRepository;
import com.aisdlc.console.infrastructure.persistence.repository.TaskJpaRepository;
import jakarta.persistence.criteria.Predicate;
import org.springframework.core.NestedExceptionUtils;
import org.springframework.dao.DataIntegrityViolationException;
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

    /** SDD 綁定的部分唯一索引名（V12）：寫入撞到它＝兩個未刪除專案認領同一個 {@code (execution_path, sdd_project)}。 */
    private static final String SDD_BINDING_INDEX = "ux_projects_sdd_binding";

    @Override
    public Project save(Project project) {
        try {
            // 立即 flush：索引違反才會在這裡（而不是提交時、離開本方法之後）出現，才轉得成 409
            projects.saveAndFlush(ProjectMapper.toEntity(project));
        } catch (DataIntegrityViolationException e) {
            String cause = NestedExceptionUtils.getMostSpecificCause(e).getMessage();
            if (project.sddProject() != null && cause != null && cause.contains(SDD_BINDING_INDEX)) {
                // 撞索引時交易已被資料庫中止，查不到持有者：holderProjectId 是選填鍵，省略
                throw new ConflictException("這個 FSM 專案已被同一個專案根的另一個專案綁定", ErrorReasons.SDD_BINDING_CONFLICT,
                        Map.of("cause", "already_bound_elsewhere", "sddProject", project.sddProject()));
            }
            throw e;
        }
        return project;
    }

    @Override
    public Optional<UUID> findSddBindingHolder(String executionPath, String sddProject, UUID excludedProjectId) {
        return projects.findSddBindingHolders(executionPath, sddProject, excludedProjectId).stream().findFirst();
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
