package com.aisdlc.console.application.port.in;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.RunView;

import java.util.List;
import java.util.UUID;

/** 啟動專案執行（契約 §1.2.1）。OPERATOR 以上；驗證順序與錯誤形狀見契約。 */
public interface ExecuteProjectUseCase {

    /**
     * {@code StartExecutionRequest}。全部可省略：等級預設取專案的 {@code autonomyLevel}、預算預設取
     * {@code execution.globalTokenBudget}、範圍預設 {@code ALL}。
     *
     * @param scopeMode {@code ALL}｜{@code SELECTED}（null＝ALL）；原字串交給用例驗證（400 的欄位名要精確）
     */
    record Command(Integer autonomyLevel, Long tokenBudget, String scopeMode, List<UUID> goalIds, List<UUID> taskIds,
                   Long taskTokens, Long goalTokens) {

        public static Command empty() {
            return new Command(null, null, null, null, null, null, null);
        }
    }

    RunView execute(UUID projectId, Command command, String actor);
}
