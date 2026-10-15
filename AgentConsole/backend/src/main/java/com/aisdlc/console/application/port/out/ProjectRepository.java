package com.aisdlc.console.application.port.out;

import com.aisdlc.console.application.port.in.ManageProjectUseCase.ListQuery;
import com.aisdlc.console.application.port.in.ManageProjectUseCase.ProjectCounts;
import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.domain.model.project.Project;

import java.util.Collection;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/** 專案儲存埠。除特別註明（{@link #findIncludingDeletedForUpdate}、{@link #search} 的 deleted 篩選）外，查詢一律排除已軟刪除（is_deleted=true）的列。 */
public interface ProjectRepository {

    Project save(Project project);

    Optional<Project> findById(UUID id);

    /** 取專案並鎖列（SELECT … FOR UPDATE），用來序列化「會影響整張專案圖」的操作（依賴／重排）。 */
    Optional<Project> findByIdForUpdate(UUID id);

    /**
     * <b>含已軟刪除者</b>並鎖列（復原用，契約 §1.6.1）：回 empty 才是「沒有這個 id 或已被清除排程實體刪除」。
     * 這是本埠唯一會回已軟刪除專案的 by-id 查詢。
     */
    Optional<Project> findIncludingDeletedForUpdate(UUID id);

    /** 專案列表；{@code query.deleted()} 為 true 時<b>只列軟刪除的專案</b>，否則只列未軟刪除者。 */
    PageResult<Project> search(ListQuery query);

    /** 各專案的目標／任務計數；沒有任何目標的專案以 ZERO 補齊。 */
    Map<UUID, ProjectCounts> countsFor(Collection<UUID> projectIds);
}
