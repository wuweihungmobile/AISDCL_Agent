package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;

import java.util.Map;
import java.util.UUID;

/**
 * SDD 綁定唯一性的「先檢查」（契約 §1.10.5、§0.5 V12 寫入規則④）：同一個 {@code (executionPath, sddProject)} 在未軟刪除的列中只能綁一個專案。
 * Backend 一律先檢查、後寫入（核准凍結第 5 項、編輯綁定、路徑 A 的 confirm 各自在寫入前呼叫這裡）；部分唯一索引是最後的兜底
 * （{@code ProjectRepositoryAdapter#save} 把它的違反轉成同一個 409）。
 */
final class SddBindings {

    private SddBindings() {
    }

    /**
     * 同專案根、同 FSM 專案鍵已有別的未刪除專案綁定 → 409 {@code sdd_binding_conflict}
     * （{@code details={cause:"already_bound_elsewhere", sddProject, holderProjectId}}）。
     *
     * @param sddProject 要綁的鍵；null（用預設）永不衝突
     * @param excluded   不算的專案（正在被寫的那一個；新建專案尚未入庫時傳它自己的新 id）
     */
    static void requireFree(ProjectRepository projects, String executionPath, String sddProject, UUID excluded) {
        if (sddProject == null) {
            return;
        }
        projects.findSddBindingHolder(executionPath, sddProject, excluded).ifPresent(holder -> {
            throw new ConflictException("同一專案根下已有另一個專案綁定了 FSM 專案「" + sddProject + "」",
                    ErrorReasons.SDD_BINDING_CONFLICT, Map.of("cause", "already_bound_elsewhere",
                            "sddProject", sddProject, "holderProjectId", holder.toString()));
        });
    }
}
