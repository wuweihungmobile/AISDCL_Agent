package com.aisdlc.console.application.port.in;

import com.aisdlc.console.application.port.out.ResearchBridge.ResearchFsm;
import com.aisdlc.console.domain.model.research.ResearchViews.Counts;
import com.aisdlc.console.domain.model.research.ResearchViews.EventPage;
import com.aisdlc.console.domain.model.research.ResearchViews.LastReview;
import com.aisdlc.console.domain.model.research.ResearchViews.Matrix;
import com.aisdlc.console.domain.model.research.ResearchViews.PrdVersion;
import com.aisdlc.console.domain.model.research.ResearchViews.Project;
import com.aisdlc.console.domain.model.research.ResearchViews.RecordClass;
import com.aisdlc.console.domain.model.research.ResearchViews.Round;
import com.aisdlc.console.domain.model.research.ResearchViews.Source;
import com.aisdlc.console.domain.service.ResearchFlowPolicy.Flow;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * 研究到規格的讀取用例（API 契約 §1.1 的全部 GET；ADR-003 D4）：研究專案、事件、來源與證據、PRD 版本、審查輪、記錄完整率都是 JDBC 唯讀 {@code console.research_*}；
 * 只有能力探針、allowlist 與 FSM 視圖轉 Bridge 的唯讀端點。{@code {id}} 不存在丟 {@code NotFoundException}（reason {@code research_not_found}）。
 */
public interface ResearchQueryUseCase {

    /** 詳情：研究列加五個計數、PRD head、最新審查輪與流程脊（{@code flow}；{@code ResearchFlowPolicy} 計算、不落 DB）。 */
    record ProjectDetail(Project project, Counts counts, Integer headPrdVersion, LastReview lastReview, Flow flow) {
    }

    /** FSM 視圖（API-RP-13）：Bridge 的 FSM 視圖加目前世代的 Gate 0 人工退回筆數（console-api 讀 DB 計得）。 */
    record FsmView(ResearchFsm fsm, int humanReturnCount) {
    }

    /** 記錄完整率（API-RP-19）：{@code missing} 為筆數 0 且不屬允許為 0（R10、R12）的類別 id。 */
    record RecordsAudit(List<RecordClass> classes, List<String> missing) {
    }

    List<Project> projects(boolean archived);

    ProjectDetail detail(UUID id);

    /** {@code afterSeq} 缺＝0；{@code limit} 缺＝100，並夾到 1～500。 */
    EventPage events(UUID id, Long afterSeq, Integer limit);

    List<Source> sources(UUID id);

    /**
     * {@code matrixVersion} 缺＝最新版；尚無任何矩陣版本（剛建立、尚未研究）回<b>空矩陣</b>（{@code matrixVersion=0}、無項目），讓證據頁顯示「尚無證據」而不是錯誤；
     * 指定的 {@code matrixVersion} 不存在回 404 {@code research_not_found}。
     */
    Matrix evidence(UUID id, Integer matrixVersion);

    List<PrdVersion> prdVersions(UUID id);

    PrdVersion prdVersion(UUID id, int versionNo);

    List<Round> rounds(UUID id);

    /** {@code roundNo} 指向沒有列的輪（進行中、取消、無效輸出）回 404 {@code research_not_found}（D-57）。 */
    Round round(UUID id, int roundNo);

    FsmView fsm(UUID id);

    RecordsAudit recordsAudit(UUID id);

    /** Bridge 能力探針的 snake_case 本文（快取 30 秒；無 DSN 仍 200，{@code db:false}）。 */
    Map<String, Object> capabilities();

    /** Bridge allowlist 的條目（snake_case；含 {@code source}＝ENV 的部署基底與 ADMIN 條目）。 */
    List<Map<String, Object>> allowlist();

    /** Web 層是否啟用（取自能力探針的快取）；探針取不到（Bridge 不可達、本文缺鍵）＝empty，由 Bridge 入口自己擋。 */
    Optional<Boolean> webLayerEnabled();
}
