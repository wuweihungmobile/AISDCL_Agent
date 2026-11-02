package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.engine.SddFsmState;

import java.util.Map;
import java.util.UUID;

/**
 * Engine Bridge 研究面 {@code /research/*} 的出站埠（API 契約 §2；ADR-003 D4、ADR-XPLAT-017；TCS-ResearchToPRD-P0 D5）。Bridge 是 {@code console.research_*} 的
 * <b>唯一寫入者</b>：console-api 只轉送寫入請求（本文與回應一律 Bridge 的 snake_case 形狀，由服務層與 DTO 對映），讀取走 {@code ResearchProjectReadPort} 等 JDBC 唯讀埠。
 *
 * <p>共通規則（實作 {@code BridgeHttpAdapter}）：每個請求帶 {@code X-Trace-Id}；<b>寫入呼叫</b>另附 {@code X-Bridge-Token}（{@code console.bridge.research-write-token}；
 * backend 沒設權杖就不發出請求、直接丟 503 {@code research_write_disabled}）；連線 2 秒、POST／PUT／PATCH 讀取逾時 30 秒、<b>寫入一律不重試</b>。
 * 錯誤約定：Bridge 4xx 與明確拒絕的 503（{@code research_write_disabled}、{@code research_requires_db}、{@code db_blocked}）以
 * {@link AgentBridge.BridgeRejectedException} 丟出；連線失敗、讀取逾時與 {@code init_failed}／{@code not_implemented} 這類 Bridge 回報的上游失敗以
 * {@code ResearchBridgeException} 丟出（reason 分別為 {@code bridge_unreachable}、{@code bridge_timeout}、Bridge 的 reason 原樣）；其餘 5xx、2xx 但本文不是預期形狀為
 * {@code UpstreamException.Failure}。
 */
public interface ResearchBridge {

    /** 單一閘的重試計數（{@code retry_gates}：{@code current_count}、{@code entries}）。 */
    record GateCount(int currentCount, int entries) {
    }

    /** 外環 FSM 視圖：既有 {@link SddFsmState} 原樣，加 Bridge 投影的同級鍵 {@code retry_gates}（各閘分項；D-59(4)；缺鍵＝空 map）。 */
    record ResearchFsm(SddFsmState state, Map<String, GateCount> gates) {

        public ResearchFsm {
            gates = gates == null ? Map.of() : Map.copyOf(gates);
        }
    }

    /**
     * backend 是否設了研究寫入權杖（{@code console.bridge.research-write-token}）：沒設＝研究寫入面整個停用。呼叫端（{@code ResearchCommandService}）在輸入閘之前先問，
     * 沒設就直接 503 {@code research_write_disabled}（契約 §0.2 第 3 列先於第 5 列），一個請求都不發。
     */
    boolean writeEnabled();

    /** {@code GET /research/capabilities}（無 DSN 仍 200）：Bridge 的 snake_case 本文原樣。 */
    Map<String, Object> capabilities();

    /** {@code GET /research/allowlist}：Bridge 的本文原樣（{@code {items:[…], effective:{…}}}，亦容忍裸陣列：以 {@code items} 鍵包成物件）。 */
    Map<String, Object> allowlist();

    /** {@code GET /sdd/fsm/{fsmProject}?root=}：外環 FSM 視圖（唯讀；連線 2 秒、讀取 3 秒、不重試）。 */
    ResearchFsm fsm(String fsmProject, String root);

    /** {@code POST /research/projects}（201）。 */
    Map<String, Object> createProject(Map<String, Object> body);

    /** {@code POST /research/projects/{id}/stages/{stage}:start}（202）。 */
    Map<String, Object> startStage(UUID researchId, String stage, Map<String, Object> body);

    /** {@code PUT /research/projects/{id}/prd}（201）。 */
    Map<String, Object> savePrd(UUID researchId, Map<String, Object> body);

    /** {@code POST /research/projects/{id}:approve-baseline}（200；僅 ADMIN 端點會呼叫）。 */
    Map<String, Object> approve(UUID researchId, Map<String, Object> body);

    /** {@code POST /research/projects/{id}:return}（200；僅 ADMIN 端點會呼叫）。 */
    Map<String, Object> returnPrd(UUID researchId, Map<String, Object> body);

    /** {@code POST /research/projects/{id}:<verb>}，{@code verb} 為 {@code cancel}｜{@code reconcile}｜{@code archive}｜{@code restore}（200）。 */
    Map<String, Object> action(UUID researchId, String verb, Map<String, Object> body);

    /** {@code POST /research/projects/{id}:reinit}（200）：本文 {@code {}}＝重試初始化；{@code {generation:"next", reason, decided_by}}＝換世代。 */
    Map<String, Object> reinit(UUID researchId, Map<String, Object> body);

    /** {@code POST /research/allowlist}（201）。 */
    Map<String, Object> addAllowlistEntry(Map<String, Object> body);

    /** {@code PATCH /research/allowlist/{id}}（200）：本文 {@code {enabled, disabled_by?}}；{@code entryId} 原樣嚴格 percent-encode 成單一路徑段。 */
    Map<String, Object> patchAllowlistEntry(String entryId, Map<String, Object> body);
}
