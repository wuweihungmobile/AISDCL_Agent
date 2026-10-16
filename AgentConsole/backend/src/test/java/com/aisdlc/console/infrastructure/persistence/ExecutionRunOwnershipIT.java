package com.aisdlc.console.infrastructure.persistence;

import com.aisdlc.console.infrastructure.persistence.entity.ExecutionRunEntity;
import com.aisdlc.console.support.AbstractIntegrationTest;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * execution_runs 的欄位級寫入分工（ADR-001 D10；Architecture §7.1；PRD §0.2.2「狀態真相單一」）。
 *
 * <p>為什麼要有這支測試：Engine Bridge 與 console-api 會同時碰同一列。若 console 的實體日後被不小心加上
 * 可更新的 Bridge 欄位，兩邊就會互相覆寫（雙寫漂移）。這裡用真 PostgreSQL 證明三件事：
 * ① console 建立列時不寫 Bridge 欄位（status 取 DDL 預設 INITIALIZING）；
 * ② Bridge 之後的寫入 console 讀得到；
 * ③ console 端即使修改實體欄位再 flush，也不會把 Bridge 的值（或任何已建立欄位）蓋回去。
 */
class ExecutionRunOwnershipIT extends AbstractIntegrationTest {

    @PersistenceContext
    EntityManager em;

    @Autowired
    TransactionTemplate tx;

    @Autowired
    JdbcTemplate jdbc;

    private UUID projectId;
    private UUID runId;

    @BeforeEach
    void insertProject() {
        projectId = UUID.randomUUID();
        runId = UUID.randomUUID();
        jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria) values (?,?,?,?)",
                projectId, "ownership", "/x", "c");
    }

    @AfterEach
    void cleanUp() {
        jdbc.update("delete from console.execution_runs where project_id = ?", projectId);
        jdbc.update("delete from console.projects where id = ?", projectId);
    }

    @Test
    void consoleCreatesTheRowWithoutTouchingBridgeColumns() {
        createRunFromConsole();

        Map<String, Object> row = jdbc.queryForMap("select * from console.execution_runs where id = ?", runId);
        assertThat(row.get("status")).as("DDL 預設值，不是 console 顯式寫入").isEqualTo("INITIALIZING");
        assertThat(row.get("total_tokens_used")).isEqualTo(0L);
        assertThat(row.get("subprocess_pid")).isNull();
        assertThat(row.get("bridge_instance")).isNull();
        assertThat(row.get("advisory_lock_key")).isNull();
        assertThat(row.get("completed_at")).isNull();
        assertThat(row.get("run_number")).isEqualTo(1);
        assertThat(row.get("token_budget")).isEqualTo(1000L);
        assertThat(row.get("scope").toString()).contains("ALL");
        // String 欄位以 @JdbcTypeCode(JSON) 映射：必須存成 jsonb「物件」，不是被引號包起來的 JSON 字串。
        assertThat(jdbc.queryForObject("select jsonb_typeof(scope) from console.execution_runs where id = ?",
                String.class, runId)).isEqualTo("object");
        assertThat(jdbc.queryForObject("select jsonb_typeof(dag) from console.execution_runs where id = ?",
                String.class, runId)).isEqualTo("object");
        // V10：能力狀態是 console 在建立時寫的欄位（同一次 INSERT），同樣必須是 jsonb 物件
        assertThat(jdbc.queryForObject("select jsonb_typeof(engine_capabilities) from console.execution_runs "
                + "where id = ?", String.class, runId)).isEqualTo("object");
        assertThat(jdbc.queryForObject("select engine_capabilities->>'autoMutation' from console.execution_runs "
                + "where id = ?", String.class, runId)).isEqualTo("ENABLED");
    }

    @Test
    void bridgeWritesAreVisibleToConsoleAndNeverOverwrittenByConsoleFlushes() {
        createRunFromConsole();
        // 模擬 Bridge：只更新它擁有的欄位。
        jdbc.update("update console.execution_runs set status = 'RUNNING', subprocess_pid = 4242, "
                + "bridge_instance = 'bridge-a', advisory_lock_key = 77, total_tokens_used = 500 where id = ?", runId);

        tx.executeWithoutResult(status -> {
            ExecutionRunEntity entity = em.find(ExecutionRunEntity.class, runId);
            assertThat(entity.status).isEqualTo("RUNNING");
            assertThat(entity.subprocessPid).isEqualTo(4242);
            assertThat(entity.bridgeInstance).isEqualTo("bridge-a");
            assertThat(entity.advisoryLockKey).isEqualTo(77L);
            assertThat(entity.totalTokensUsed).isEqualTo(500L);

            // console 端「竄改」所有欄位後 flush：Hibernate 不得為這些欄位產生 UPDATE。
            entity.status = "FAILED";
            entity.subprocessPid = 1;
            entity.bridgeInstance = "console-overwrite";
            entity.advisoryLockKey = 1L;
            entity.totalTokensUsed = 1L;
            entity.completedAt = Instant.now();
            entity.tokenBudget = 1L;
            entity.autonomyLevel = 10;
            entity.engineCapabilities = "{\"autoMutation\":\"OFF\",\"selfEvolution\":\"OFF\"}";
            em.flush();
        });

        Map<String, Object> row = jdbc.queryForMap("select * from console.execution_runs where id = ?", runId);
        assertThat(row.get("status")).isEqualTo("RUNNING");
        assertThat(row.get("subprocess_pid")).isEqualTo(4242);
        assertThat(row.get("bridge_instance")).isEqualTo("bridge-a");
        assertThat(row.get("advisory_lock_key")).isEqualTo(77L);
        assertThat(row.get("total_tokens_used")).isEqualTo(500L);
        assertThat(row.get("completed_at")).as("Bridge 才會寫 completed_at").isNull();
        assertThat(row.get("token_budget")).as("建立後 console 也不再改這些欄位").isEqualTo(1000L);
        assertThat(row.get("autonomy_level")).isEqualTo(3);
        assertThat(jdbc.queryForObject("select engine_capabilities->>'autoMutation' from console.execution_runs "
                + "where id = ?", String.class, runId)).as("能力狀態只在建立時寫一次（updatable=false），之後不再被 JPA 回寫")
                .isEqualTo("ENABLED");
    }

    private void createRunFromConsole() {
        tx.executeWithoutResult(status -> {
            ExecutionRunEntity entity = new ExecutionRunEntity();
            entity.id = runId;
            entity.projectId = projectId;
            entity.runNumber = 1;
            entity.autonomyLevel = 3;
            entity.scope = "{\"mode\":\"ALL\",\"goalIds\":[],\"taskIds\":[]}";
            entity.tokenBudget = 1000L;
            entity.dag = "{\"nodes\":[],\"edges\":[]}";
            entity.startedAt = Instant.now();
            entity.engineCapabilities = "{\"autoMutation\":\"ENABLED\",\"selfEvolution\":\"ENABLED\"}";
            em.persist(entity);
        });
    }
}
