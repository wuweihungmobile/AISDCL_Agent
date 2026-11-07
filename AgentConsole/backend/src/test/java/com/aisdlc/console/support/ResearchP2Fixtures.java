package com.aisdlc.console.support;

import com.aisdlc.minibridge.MiniBridge;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.UUID;

/**
 * P2 的內環夾具：一個綁了 Console 專案的研究專案，加任務、run，與迷你 Bridge 上的 FSM 現態與 RTM 報告（以 run id 為鍵）。
 * 為什麼集中：閘登錄、交付（tag、pr）與看板的前置都是「現態＋任務完成＋RTM」三件事的組合，邊界案例（99.99、fullyCovered 為假、現態不對）
 * 若各測試自己拼，三處對「就緒」的理解會悄悄分歧。
 */
public final class ResearchP2Fixtures {

    /** 研究專案、Console 專案、內環鍵與最新 run。 */
    public record Ready(UUID research, UUID console, String sddKey, UUID run) {
    }

    private final JdbcTemplate jdbc;
    private final ResearchP1Fixtures p1;
    private final MiniBridge mini;

    public ResearchP2Fixtures(JdbcTemplate jdbc, MiniBridge mini) {
        this.jdbc = jdbc;
        this.p1 = new ResearchP1Fixtures(jdbc);
        this.mini = mini;
    }

    /** 已綁 Console 專案、最新 run 為 {@code run}、一個 COMPLETED 任務；FSM 與 RTM 尚未注入。 */
    public Ready ready(String slug) {
        UUID research = p1.project(slug + "-" + UUID.randomUUID().toString().substring(0, 6), "UNDECIDED");
        UUID console = UUID.randomUUID();
        String key = "impl-" + console;
        jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria, sdd_project) values (?, ?, ?, '通過', ?)", console, "專案 " + slug,
                "/e2e/" + console, key);
        p1.bind(research, console);
        UUID goal = UUID.randomUUID();
        jdbc.update("insert into console.goals (id, project_id, name, pass_criteria) values (?, ?, '目標', '通過')", goal, console);
        jdbc.update("insert into console.tasks (id, goal_id, name, pass_criteria, status) values (?, ?, '任務', '通過', 'COMPLETED')", UUID.randomUUID(), goal);
        UUID run = UUID.randomUUID();
        jdbc.update("insert into console.execution_runs (id, project_id, run_number, status, autonomy_level, scope) values (?, ?, 1, 'COMPLETED', 4, '{}'::jsonb)", run, console);
        return new Ready(research, console, key, run);
    }

    /** 再加一個指定狀態的任務。 */
    public void task(Ready ready, String status) {
        UUID goal = jdbc.queryForObject("select id from console.goals where project_id = ? limit 1", UUID.class, ready.console());
        jdbc.update("insert into console.tasks (id, goal_id, name, pass_criteria, status) values (?, ?, '另一任務', '通過', ?)", UUID.randomUUID(), goal, status);
    }

    /** 內環現態與 Stage-2 凍結。 */
    public void fsm(Ready ready, String state, boolean stage2Frozen) {
        mini.fsmState(ready.sddKey(), state, stage2Frozen);
    }

    /** 最新 run 的 RTM（以 run id 為鍵）。 */
    public void rtm(Ready ready, boolean fullyCovered, double acPct) {
        mini.rtmFor(ready.run(), fullyCovered, acPct, 5, 5);
    }

    /** 全套就緒：RELEASE_READY、RTM 100 且 fullyCovered、任務全完成。 */
    public Ready releaseReady(String slug) {
        Ready ready = ready(slug);
        fsm(ready, "RELEASE_READY", true);
        rtm(ready, true, 100.0);
        return ready;
    }
}
