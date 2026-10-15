package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.UUID;

/**
 * 專案有進行中批次時，不可刪除它的目標或任務（C-8，QA O-05；契約 §1.6.3）。理由：批次進行中刪除「尚未開始」的目標／任務，
 * 批次仍照原 playbook 跑完，結果與畫面對不上。進行中＝批次狀態 {@code INITIALIZING}／{@code RUNNING}／{@code PAUSED}。
 *
 * <p>檢查順序由呼叫端保證：404 → 本守門（{@code project_executing}）→ 既有的「RUNNING 狀態的任務不可刪除」
 * （兩者並存時先回前者，因為它涵蓋更廣）。
 */
@Component
public class RunInProgressGuard {

    private final ExecutionRunRepository runs;

    public RunInProgressGuard(ExecutionRunRepository runs) {
        this.runs = runs;
    }

    /** 專案有進行中批次就丟 409 {@code project_executing}（details＝{@code {projectId, runId}}）；{@code what} 是「目標」或「任務」。 */
    void requireNoRunInProgress(UUID projectId, String what) {
        runs.findInProgressRunId(projectId).ifPresent(runId -> {
            throw new ConflictException("專案有進行中的執行批次，不可刪除" + what, ErrorReasons.PROJECT_RUN_IN_PROGRESS,
                    Map.of("projectId", projectId.toString(), "runId", runId.toString()));
        });
    }
}
