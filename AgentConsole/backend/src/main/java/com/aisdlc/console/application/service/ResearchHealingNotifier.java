package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.ResearchBridge;
import com.aisdlc.console.application.port.out.ResearchProjectReadPort;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.Executor;

/**
 * 自癒歷史同步通知（AC-R2P-16-1；D-138 Q-13、D-149#5）。{@code RunConsumers.handle} 在事件交易<b>提交之後、SSE 發佈之前</b>，僅當事件使任務進入
 * RETRYING／FAILED／ESCALATED 時呼叫 {@link #notify(UUID)}：找出該 run 所屬 Console 專案綁定的研究專案（<b>非研究專案＝無操作、Bridge 請求 0</b>），
 * 非同步 best-effort 呼叫 Bridge {@code :healing-sync}（Bridge 不可達或逾時只記一行警告，事件處理與 SSE 不受影響）。
 *
 * <p>成功回應存進<b>記憶體</b>快取（重啟即空；console-api 不寫任何 {@code research_*}），{@code GET …/healing} 只讀 DB 加這份快取、零 Bridge 請求。
 */
@Component
public class ResearchHealingNotifier {

    private static final Logger LOG = LoggerFactory.getLogger(ResearchHealingNotifier.class);

    /** 最近一次成功的同步結果（Bridge 回應的 view_rows、log_lines 與 spec_change 的路徑清單）。 */
    public record Sync(int viewRows, int logLines, List<String> specChangePaths, Instant syncedAt) {
    }

    private final ResearchBridge bridge;
    private final ResearchProjectReadPort researchProjects;
    private final ExecutionRunRepository runs;
    private final Executor async;
    private final ConcurrentMap<UUID, Sync> latest = new ConcurrentHashMap<>();

    @Autowired
    public ResearchHealingNotifier(ResearchBridge bridge, ResearchProjectReadPort researchProjects, ExecutionRunRepository runs) {
        this(bridge, researchProjects, runs, task -> Thread.ofVirtual().name("research-healing-sync").start(task));
    }

    ResearchHealingNotifier(ResearchBridge bridge, ResearchProjectReadPort researchProjects, ExecutionRunRepository runs, Executor async) {
        this.bridge = bridge;
        this.researchProjects = researchProjects;
        this.runs = runs;
        this.async = async;
    }

    /** 通知（永不拋例外）。 */
    public void notify(UUID runId) {
        try {
            Optional<UUID> research = runs.findById(runId).map(ExecutionRun::projectId).flatMap(researchProjects::researchIdOfConsoleProject);
            if (research.isEmpty()) {
                return;
            }
            UUID researchId = research.get();
            async.execute(() -> sync(researchId));
        } catch (RuntimeException e) {
            LOG.warn("自癒同步通知失敗（run={}）：{}", runId, e.getClass().getSimpleName());
        }
    }

    private void sync(UUID researchId) {
        try {
            Map<String, Object> body = bridge.healingSync(researchId, Map.of("requested_by", "system"));
            List<String> paths = new ArrayList<>();
            if (body.get("spec_change") instanceof List<?> items) {
                for (Object item : items) {
                    if (item instanceof Map<?, ?> m && m.get("path") != null) {
                        paths.add(m.get("path").toString());
                    }
                }
            }
            latest.put(researchId, new Sync(number(body.get("view_rows")), number(body.get("log_lines")), List.copyOf(paths), Instant.now()));
        } catch (RuntimeException e) {
            // Bridge 不可達、逾時或拒絕：只記警告（訊息不含任何 token；寫入權杖從不進例外文字）
            LOG.warn("自癒同步（:healing-sync）未成功（research={}）：{}", researchId, e.getClass().getSimpleName());
        }
    }

    /** 該研究專案最近一次成功的同步；沒有＝empty。 */
    public Optional<Sync> latest(UUID researchId) {
        return Optional.ofNullable(latest.get(researchId));
    }

    private static int number(Object value) {
        return value instanceof Number n ? n.intValue() : 0;
    }
}
