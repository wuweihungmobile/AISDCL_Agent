package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.research.ResearchViews.Counts;
import com.aisdlc.console.domain.model.research.ResearchViews.Event;
import com.aisdlc.console.domain.model.research.ResearchViews.EventPage;
import com.aisdlc.console.domain.model.research.ResearchViews.LastReview;
import com.aisdlc.console.domain.model.research.ResearchViews.Project;
import com.aisdlc.console.domain.model.research.ResearchViews.RecordClass;
import com.aisdlc.console.domain.model.research.ResearchViews.RunFact;

import java.util.List;
import java.util.Optional;
import java.util.OptionalLong;
import java.util.UUID;

/**
 * 研究專案、事件帳與記錄完整率的<b>唯讀</b>埠（ADR-003 D4：console-api 對 {@code console.research_*} 零寫入；Bridge 是唯一寫入者）。實作住
 * {@code adapter.out.persistence.research}，只用 {@code JdbcClient}、沒有任何 JPA 實體，原始碼不得出現 INSERT／UPDATE／DELETE（ArchUnit 字串掃描鎖住，AT-960-4-E-1）。
 */
public interface ResearchProjectReadPort {

    /** 研究專案清單（{@code archived=false}＝未封存，{@code true}＝已封存那一份），更新時間新到舊。 */
    List<Project> findAll(boolean archived);

    /** 單筆（含已封存者：封存是軟刪除，歷史仍可讀）。 */
    Optional<Project> findById(UUID id);

    boolean exists(UUID id);

    Counts counts(UUID id);

    /** 最新一個已完成的審查輪（沒有則 empty）。 */
    Optional<LastReview> lastReview(UUID id);

    /** PRD head 版號（沒有任何版本則 empty）。 */
    OptionalLong headPrdVersion(UUID id);

    /** 事件帳一頁：{@code seq > afterSeq}、依 seq 遞增、最多 {@code limit} 筆（呼叫端已夾到 1～500）。 */
    EventPage events(UUID id, long afterSeq, int limit);

    /** 事件帳 {@code seq > afterSeq} 的前 {@code limit} 筆（SSE 尾隨用）。 */
    List<Event> eventsAfter(UUID id, long afterSeq, int limit);

    /** 目前最大的事件 seq（沒有事件＝0）。 */
    long maxEventSeq(UUID id);

    /** 最新 {@code window} 筆事件中最小的 seq（重播視窗的起點）；沒有任何事件則 empty。 */
    OptionalLong replayWindowStart(UUID id, int window);

    /** R1～R14 各類的筆數（PRD §5.1.8；V19 的表在 P0 尚不存在，其類別恆為 0）。 */
    List<RecordClass> recordClasses(UUID id);

    /** 目前 {@code fsmProject} 之下 gate 為 GATE0、decision 為 CHANGES 的決定筆數（D-59(4)：舊世代的鍵不計）。 */
    int humanReturnCount(UUID id, String fsmProject);

    /** 該 Console 專案最新的內環 run 的衍生事實（P1 起分流後才有 Console 專案；沒有 run 則 empty）。 */
    Optional<RunFact> latestRun(UUID consoleProjectId);
}
