package com.aisdlc.console.application.port.in;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;
import com.aisdlc.console.domain.model.research.ResearchRouteViews.Decomposition;
import com.aisdlc.console.domain.service.DecompositionCoverage;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * 拆解用例（API-RP-16；PRD FR-R2P-14；D-94、D-113、D-120）：觸發（OPERATOR 以上；Bridge {@code :decompose} 同步、讀逾時 330 秒）、讀取有效拆解（VIEWER 以上、JDBC 唯讀）、
 * 簽核（OPERATOR 以上；<b>先走既有 import／signoff 路徑</b>落為正式專案目標任務，再呼 Bridge {@code :decomposition-signoff}）。
 */
public interface ResearchDecompositionUseCase {

    /** 一條豁免（請求本文）：AC 編號與人工理由。 */
    record WaiverInput(String ac, String reason) {
    }

    /** 拆解的讀模型：列、覆蓋（{@link DecompositionCoverage}）、豁免、目標任務樹與 stale 旗標。 */
    record View(Decomposition decomposition, DecompositionCoverage.Result coverage, List<DecompositionCoverage.Waiver> waivers,
                List<Map<String, Object>> goals, boolean stale) {
    }

    /** 有效拆解（D-120）；沒有拆解＝empty（API 回 200 的 {@code null}）。研究專案不存在丟 404。 */
    Optional<View> current(UUID researchId);

    /** 觸發拆解（{@code usIds} 選填：只拆指定的 US；null 或空＝全部）：回 Bridge 的本文（snake_case：{@code decomposition_id}、{@code status}、{@code tasks_count}、{@code coverage}）。 */
    Map<String, Object> trigger(Caller caller, UUID researchId, List<String> usIds);

    /** 簽核：成功回簽核後自 DB 重讀的有效拆解。approver 取 JWT subject（空白＝400）。 */
    View signoff(Caller caller, UUID researchId, List<WaiverInput> waivers);
}
