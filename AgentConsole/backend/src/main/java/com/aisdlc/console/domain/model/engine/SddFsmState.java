package com.aisdlc.console.domain.model.engine;

import java.util.List;
import java.util.Map;

/**
 * 單一 FSM 專案的狀態（Bridge {@code GET /sdd/fsm/{project}} 與 {@code :freeze} 成功回應的投影；契約 §1.7.1、§1.10.4、§3.1.3、§3.1.4；
 * D-16、D-115-02）。
 *
 * <p><b>最外層鍵轉 camelCase，巢狀內容原樣</b>（{@code frozenStages[]}、{@code decisionTrace[]}、{@code humanPending.items[]}、
 * {@code retryHistory.last}、{@code rtmCoverage}、{@code escalationHistory[]}、{@code escalationProvenance} 保留 FSM 檔的 snake_case
 * 鍵），使「FSM 檔 ↔ API ↔ 畫面」可逐值比對（NFR-OBS-01）。Console 不直接寫 FSM-STATE：v1.5 唯一的寫入動詞是 Bridge 的 {@code :freeze}，
 * 經 FSMRuntime CLI 子行程完成（ADR-001 D22 由 ADR-XPLAT-016 修訂為「只經 CLI 窄寫」）。
 *
 * <p>v1.5 的五個新欄位皆選填：舊版 Bridge 缺鍵時一律補預設（{@code phase=null}、{@code escalationHistory=[]}、其餘 null），不得因此失敗。
 *
 * @param currentState         檔內 {@code current_state}；缺則 null
 * @param updatedAt            檔內 {@code updated_at}（ISO-8601 字串，<b>原樣、不轉型</b>）；缺則 null
 * @param decisionTrace        {@code decision_trace} 的尾 5 筆（舊→新），Bridge 已截斷
 * @param rtmCoverage          {@code fsm_state.rtm_coverage}：有就原樣帶出（物件或數值），沒有為 null；現行 FSM-STATE 沒有這個鍵，現況恆為 null
 * @param phase                由 {@code current_state} 純函式投影出的階段資訊（契約 §3.1.5）；Bridge 尚未接線或舊版缺鍵為 null
 * @param escalationHistory    {@code escalation_history} 的尾 5 筆（舊→新，原樣）；缺則空
 * @param escalationProvenance {@code escalation_provenance} 原樣；缺或不是映射為 null。🔴 人工恢復後<b>不會被清除</b>，不是現況旗標
 * @param fsmProject           狀態檔名裡<b>淨化後的標準鍵</b>（{@code FSM-STATE-<鍵>.yaml} 的 {@code <鍵>}）；{@code project} 是檔內原名，
 *                             兩者可能不同，不能拿 {@code project} 當鍵；Backend 以它做綁定寫回與唯一性檢查
 * @param recovery             僅 {@code ESCALATION}／{@code ESCALATION_FINAL} 時由 Bridge 回；其餘為 null。Console 原樣顯示，不提供恢復動作
 */
public record SddFsmState(String project, String currentState, Integer currentSprint, String sessionId,
                          String updatedAt, List<Map<String, Object>> frozenStages,
                          List<Map<String, Object>> decisionTrace, String source, HumanPending humanPending,
                          RetryHistory retryHistory, Object rtmCoverage, Phase phase,
                          List<Map<String, Object>> escalationHistory, Map<String, Object> escalationProvenance,
                          String fsmProject, Recovery recovery) {

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

    /**
     * FSM 階段資訊（契約 §3.1.5）：主路徑階段名 {@code INTAKE}～{@code RELEASE}（{@code order} 1～8）；非主路徑為 {@code BLOCKED}、
     * {@code TRANSIENT}、{@code OBSERVATION}、{@code UNKNOWN}（{@code order} 一律 0）。{@code name} 是開放字串：Console 不維護字典，
     * 日後新增的值前端原樣顯示。
     */
    public record Phase(String name, int order, boolean blocking, boolean observation) {
    }

    /**
     * ESCALATION 的恢復指令（ADR-XPLAT-016 §5.3 的模板，由 Bridge 組字；只含路徑與指令、理由欄位留 {@code <人工原因>} 佔位、不含機密）。
     * 恢復只有人、留在 SDD session：Console 與 Bridge 都沒有恢復動詞。
     */
    public record Recovery(String target, String powershell, String posix) {
    }

    public SddFsmState {
        frozenStages = frozenStages == null ? List.of() : List.copyOf(frozenStages);
        decisionTrace = decisionTrace == null ? List.of() : List.copyOf(decisionTrace);
        humanPending = humanPending == null ? new HumanPending(0, List.of()) : humanPending;
        retryHistory = retryHistory == null ? new RetryHistory(0, null) : retryHistory;
        escalationHistory = escalationHistory == null ? List.of() : List.copyOf(escalationHistory);
    }

    /** v1.4 的十一欄（沒有 v1.5 的階段、升級與恢復資訊）：舊版 Bridge 的回應與只關心 v1.4 欄位的呼叫端使用。 */
    @SuppressWarnings("java:S107")
    public SddFsmState(String project, String currentState, Integer currentSprint, String sessionId, String updatedAt,
                       List<Map<String, Object>> frozenStages, List<Map<String, Object>> decisionTrace, String source,
                       HumanPending humanPending, RetryHistory retryHistory, Object rtmCoverage) {
        this(project, currentState, currentSprint, sessionId, updatedAt, frozenStages, decisionTrace, source,
                humanPending, retryHistory, rtmCoverage, null, List.of(), null, null, null);
    }
}
