package com.aisdlc.console.application.port.out;

import com.aisdlc.console.application.port.in.ManageProjectUseCase.ListQuery;
import com.aisdlc.console.application.port.in.ManageProjectUseCase.ProjectCounts;
import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.domain.model.project.Project;

import java.util.Collection;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/** 專案儲存埠。除特別註明外，查詢一律排除已軟刪除（is_deleted=true）的列。 */
public interface ProjectRepository {

    Project save(Project project);

    Optional<Project> findById(UUID id);

    /** 取專案並鎖列（SELECT … FOR UPDATE），用來序列化「會影響整張專案圖」的操作（依賴／重排）。 */
    Optional<Project> findByIdForUpdate(UUID id);

    PageResult<Project> search(ListQuery query);

    /** 各專案的目標／任務計數；沒有任何目標的專案以 ZERO 補齊。 */
    Map<UUID, ProjectCounts> countsFor(Collection<UUID> projectIds);
}
