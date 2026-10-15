package com.aisdlc.console.application.port.in;

import com.aisdlc.console.application.port.in.ManageGoalUseCase.GoalWithCounts;
import com.aisdlc.console.domain.model.project.NewProject;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import com.aisdlc.console.domain.model.project.ProjectUpdate;

import java.util.List;
import java.util.UUID;

/** 專案管理用例（PRD §5.1.1／§7.1.1）。找不到（含已軟刪除）一律 NotFoundException（404）。 */
public interface ManageProjectUseCase {

    /** 專案下的計數（goals／tasks 皆只算未軟刪）。 */
    record ProjectCounts(int goalsCount, int tasksCount, int tasksDone) {
        public static final ProjectCounts ZERO = new ProjectCounts(0, 0, 0);
    }

    record ProjectView(Project project, ProjectCounts counts) {
    }

    /** 專案詳情：專案＋計數＋目標摘要（依 sortOrder）。 */
    record ProjectDetailView(Project project, ProjectCounts counts, List<GoalWithCounts> goals) {
    }

    /** 列表可排序欄位（PRD 任務書：updatedAt 預設，可 name／status／createdAt）。 */
    enum SortField { NAME, STATUS, CREATED_AT, UPDATED_AT }

    /**
     * 列表查詢條件。
     *
     * @param nameQuery 名稱模糊比對（不分大小寫）；null／空白＝不篩
     * @param status    狀態篩選；null＝不篩
     * @param deleted   true＝<b>只列軟刪除的專案</b>（契約 §1.6.2，C-3；角色限制由 web 層檢查），false＝只列未軟刪除者（原行為）
     */
    record ListQuery(String nameQuery, ProjectStatus status, boolean deleted, SortField sortField, boolean ascending,
                     int page, int size) {
    }

    ProjectView create(NewProject spec, String createdBy);

    PageResult<ProjectView> list(ListQuery query);

    ProjectDetailView get(UUID projectId);

    ProjectView update(UUID projectId, ProjectUpdate update);

    void delete(UUID projectId);

    /**
     * 復原軟刪除的專案與「同一次刪除連帶軟刪」的目標、任務（契約 §1.6.1，C-3）。找不到（沒有這個 id 或已被清除）→ 404；
     * 目前沒被軟刪除 → 409 {@code project_not_deleted}；軟刪除已超過保留期 → 409 {@code restore_window_expired}。
     */
    ProjectDetailView restore(UUID projectId);

    ProjectView signoff(UUID projectId, String approver);
}
