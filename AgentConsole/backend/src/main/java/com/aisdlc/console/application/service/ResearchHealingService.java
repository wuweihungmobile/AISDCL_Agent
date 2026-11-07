package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ResearchHealingUseCase;
import com.aisdlc.console.application.port.out.ResearchHealingReadPort;
import com.aisdlc.console.application.port.out.ResearchKanbanReadPort;
import com.aisdlc.console.application.port.out.ResearchProjectReadPort;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.model.research.ResearchP2Views.HealingAttempt;
import com.aisdlc.console.domain.model.research.ResearchViews;
import org.springframework.stereotype.Service;

import java.time.ZoneOffset;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/** 自癒歷史讀取（API-RP-27）：DB 視圖（excerpt 已在配接器遮蔽）＋通知器快取；零 Bridge 請求、零寫入。 */
@Service
public class ResearchHealingService implements ResearchHealingUseCase {

    private final ResearchProjectReadPort researchProjects;
    private final ResearchHealingReadPort healing;
    private final ResearchKanbanReadPort kanban;
    private final ResearchHealingNotifier notifier;
    private final SettingsReader settings;

    ResearchHealingService(ResearchProjectReadPort researchProjects, ResearchHealingReadPort healing, ResearchKanbanReadPort kanban,
                           ResearchHealingNotifier notifier, SettingsReader settings) {
        this.researchProjects = researchProjects;
        this.healing = healing;
        this.kanban = kanban;
        this.notifier = notifier;
        this.settings = settings;
    }

    @Override
    public Healing healing(UUID researchId) {
        ResearchViews.Project research = researchProjects.findById(researchId)
                .orElseThrow(() -> new NotFoundException("研究專案不存在：" + researchId, ErrorReasons.RESEARCH_NOT_FOUND, Map.of()));
        int maxRetries = settings.intValue("agent", "maxRetries");
        if (research.consoleProjectId() == null) {
            return new Healing(researchId, List.of(), maxRetries, 0, 0, null, 0, null);
        }
        List<HealingAttempt> attempts = healing.attempts(researchId);
        var facts = healing.facts(research.consoleProjectId());
        Optional<ResearchHealingNotifier.Sync> sync = notifier.latest(researchId);
        boolean drift = sync.map(s -> !s.specChangePaths().isEmpty()).orElse(false);
        UUID latestRun = kanban.latestRunId(research.consoleProjectId()).orElse(null);
        List<Row> rows = attempts.stream().map(a -> new Row(a.runId(), a.taskId(), a.stepNumber(), a.attempt(), a.status(), a.excerpt(), a.occurredAt(),
                a.resolved(), a.escalated(), drift && a.runId().equals(latestRun) && !a.resolved() && isLastOfTask(attempts, a), null, null)).toList();
        int lag = sync.map(s -> Math.max(s.viewRows() - s.logLines(), 0)).orElse(0);
        var syncedThrough = sync.filter(s -> s.logLines() > 0 && !attempts.isEmpty()).map(s -> {
            List<HealingAttempt> ordered = attempts.stream()
                    .sorted(Comparator.comparing(HealingAttempt::occurredAt).thenComparingInt(HealingAttempt::stepNumber)).toList();
            return ordered.get(Math.min(s.logLines(), ordered.size()) - 1).occurredAt();
        }).orElse(null);
        SpecChange specChange = drift ? new SpecChange(sync.get().specChangePaths(), sync.get().syncedAt().atOffset(ZoneOffset.UTC)) : null;
        return new Healing(researchId, rows, maxRetries, facts.retryingSteps(), facts.escalatedTasks(), syncedThrough, lag, specChange);
    }

    private static boolean isLastOfTask(List<HealingAttempt> all, HealingAttempt row) {
        return all.stream().filter(a -> a.runId().equals(row.runId()) && a.taskId().equals(row.taskId()))
                .mapToInt(HealingAttempt::stepNumber).max().orElse(-1) == row.stepNumber();
    }
}
