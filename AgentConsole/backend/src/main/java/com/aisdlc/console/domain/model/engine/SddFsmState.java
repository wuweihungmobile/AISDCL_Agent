package com.aisdlc.console.domain.model.engine;

import java.util.List;
import java.util.Map;

/**
 * 單一 FSM 專案的狀態（Bridge {@code GET /sdd/fsm/{project}} 的投影；契約 §1.7.1、§3.1.3；D-16）。
 *
 * <p><b>最外層鍵轉 camelCase，巢狀內容原樣</b>（{@code frozenStages[]}、{@code decisionTrace[]}、{@code humanPending.items[]}、
 * {@code retryHistory.last}、{@code rtmCoverage} 保留 FSM 檔的 snake_case 鍵），使「FSM 檔 ↔ API ↔ 畫面」可逐值比對（NFR-OBS-01）。
 * 唯讀：Console 不寫 FSM-STATE（ADR-001 D22）。
 *
 * @param currentState 檔內 {@code current_state}；缺則 null
 * @param updatedAt    檔內 {@code updated_at}（ISO-8601 字串，<b>原樣、不轉型</b>）；缺則 null
 * @param decisionTrace {@code decision_trace} 的尾 5 筆（舊→新），Bridge 已截斷
 * @param rtmCoverage  {@code fsm_state.rtm_coverage}：有就原樣帶出（物件或數值），沒有為 null；現行 FSM-STATE 沒有這個鍵，現況恆為 null
 */
public record SddFsmState(String project, String currentState, Integer currentSprint, String sessionId,
                          String updatedAt, List<Map<String, Object>> frozenStages,
                          List<Map<String, Object>> decisionTrace, String source, HumanPending humanPending,
                          RetryHistory retryHistory, Object rtmCoverage) {

    /**
     * 待人工確認：{@code entered_at} 有值（FSM 正停在人工確認點）→ {@code count=1}、{@code items=[該映射原樣]}；否則 0 與空陣列；
     * 若來源是 list，{@code count}＝筆數、{@code items}＝尾 5 筆。所以 {@code count} 實務上只會是 0 或 1。
     */
    public record HumanPending(int count, List<Map<String, Object>> items) {

        public HumanPending {
            items = items == null ? List.of() : List.copyOf(items);
        }
    }

    /**
     * 重試歷史：{@code count}＝各重試閘 {@code history} 筆數的總和；{@code last}＝全部筆中 {@code date} 最晚者（原樣，另加 {@code gate} 欄＝所屬的閘名）；
     * 沒有任何一筆為 {@code count=0}、{@code last=null}。
     */
    public record RetryHistory(int count, Map<String, Object> last) {
    }

    public SddFsmState {
        frozenStages = frozenStages == null ? List.of() : List.copyOf(frozenStages);
        decisionTrace = decisionTrace == null ? List.of() : List.copyOf(decisionTrace);
        humanPending = humanPending == null ? new HumanPending(0, List.of()) : humanPending;
        retryHistory = retryHistory == null ? new RetryHistory(0, null) : retryHistory;
    }
}
