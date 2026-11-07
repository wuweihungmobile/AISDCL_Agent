package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.research.ResearchP2Views.HealingAttempt;
import com.aisdlc.console.domain.model.research.ResearchP2Views.HealingFacts;

import java.util.List;
import java.util.UUID;

/** 自癒視圖的<b>唯讀</b>埠（{@code v_research_healing_attempts}；excerpt 在配接器內先遮蔽再截尾）。 */
public interface ResearchHealingReadPort {

    /** 研究專案的自癒列，依 run_number、task、step_number 遞增（無 console 專案時由呼叫端略過）。 */
    List<HealingAttempt> attempts(UUID researchId);

    /** retryingSteps（最新 run 內 RETRYING 且其後無同 task 非 RETRYING 列者）與 escalatedTasks（任務 ESCALATED 數）。 */
    HealingFacts facts(UUID consoleProjectId);
}
