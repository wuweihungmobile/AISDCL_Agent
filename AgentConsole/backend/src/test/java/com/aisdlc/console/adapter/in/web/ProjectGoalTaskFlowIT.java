package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 任務書指定的「三層 CRUD 全流程」驗收情境：建專案 → 建兩個目標（含依賴）→ 建任務 → 列表計數正確 →
 * signoff → 軟刪連帶。一個測試走完整條路，每一步都用「前一步產生的真實 id」，不預先塞資料。
 */
class ProjectGoalTaskFlowIT extends AbstractApiIT {

    @Test
    void projectGoalTaskLifecycleEndToEnd() {
        // 1. 建專案（手動建立：DRAFT、已 signoff）
        Resp project = api.post(operator(), "/api/v1/projects", Map.of(
                "name", "AISDLC Core Platform", "executionPath", "/work/aisdlc-core",
                "passCriteria", "- 單元測試通過率 >= 95%", "description", "## 概述"));
        assertThat(project.status()).isEqualTo(201);
        String projectId = project.id();

        // 2. 建兩個目標：第二個依賴第一個；另建一個草案目標備後面 signoff
        String foundation = api.post(operator(), "/api/v1/projects/" + projectId + "/goals",
                Map.of("name", "建立基礎架構", "passCriteria", "- 骨架可編譯")).id();
        Resp core = api.post(operator(), "/api/v1/projects/" + projectId + "/goals",
                Map.of("name", "實作核心模組", "passCriteria", "- 核心測試通過", "dependsOn", List.of(foundation)));
        assertThat(core.status()).isEqualTo(201);
        String coreId = core.id();
        String draftGoal = api.post(operator(), "/api/v1/projects/" + projectId + "/goals",
                Map.of("name", "草案目標", "passCriteria", "- 待審", "draft", true)).id();

        // 3. 建任務（兩個掛在 core、一個草案任務掛在 foundation）
        String t1 = api.post(operator(), "/api/v1/goals/" + coreId + "/tasks",
                Map.of("name", "建立 Domain Model", "passCriteria", "- 編譯通過", "evaluatorCommand", "pytest -q")).id();
        api.post(operator(), "/api/v1/goals/" + coreId + "/tasks",
                Map.of("name", "實作 Repository", "passCriteria", "- 測試通過"));
        String draftTask = api.post(operator(), "/api/v1/goals/" + foundation + "/tasks",
                Map.of("name", "草案任務", "passCriteria", "- 待審", "draft", true)).id();

        // 4. 列表計數正確（把 t1 標成完成，模擬引擎事件）
        setTaskStatus(t1, "COMPLETED");
        Resp list = api.get(viewer(), "/api/v1/projects");
        assertThat(list.<Integer>read("$.data.content[0].goalsCount")).isEqualTo(3);
        assertThat(list.<Integer>read("$.data.content[0].tasksCount")).isEqualTo(3);
        assertThat(list.<Integer>read("$.data.content[0].tasksDone")).isEqualTo(1);

        Resp detail = api.get(viewer(), "/api/v1/projects/" + projectId);
        assertThat(detail.<List<String>>read("$.data.goals[*].name"))
                .containsExactly("建立基礎架構", "實作核心模組", "草案目標");
        assertThat(detail.<List<Integer>>read("$.data.goals[*].taskCount")).containsExactly(1, 2, 0);
        Resp goalDetail = api.get(viewer(), "/api/v1/goals/" + coreId);
        assertThat(goalDetail.<List<String>>read("$.data.dependsOn")).containsExactly(foundation);
        assertThat(goalDetail.<Double>read("$.data.completionRatio")).isEqualTo(0.5);

        // 5. signoff：草案目標與草案任務（缺 approver → 400；補上 → 成功）
        assertThat(api.post(operator(), "/api/v1/goals/" + draftGoal + "/signoff", Map.of()).status()).isEqualTo(400);
        assertThat(api.post(operator(), "/api/v1/goals/" + draftGoal + "/signoff", Map.of("approver", "Alice"))
                .<Boolean>read("$.data.signedOff")).isTrue();
        assertThat(api.post(operator(), "/api/v1/tasks/" + draftTask + "/signoff", Map.of("approver", "Alice"))
                .<String>read("$.data.signedOffBy")).isEqualTo("Alice");

        // 6. 依賴防環：foundation 反過來依賴 core 必須被擋，且不留痕
        assertThat(api.put(operator(), "/api/v1/goals/" + foundation, Map.of("dependsOn", List.of(coreId)))
                .<String>read("$.reason")).isEqualTo("依賴成環");

        // 7. 軟刪專案 → 目標、任務連帶軟刪；資料列仍在（可稽核）
        assertThat(api.delete(operator(), "/api/v1/projects/" + projectId).status()).isEqualTo(204);
        assertThat(api.get(viewer(), "/api/v1/projects/" + projectId).status()).isEqualTo(404);
        assertThat(api.get(viewer(), "/api/v1/goals/" + coreId).status()).isEqualTo(404);
        assertThat(api.get(viewer(), "/api/v1/tasks/" + t1).status()).isEqualTo(404);
        assertThat(jdbc.queryForObject("select count(*) from console.goals where project_id = ? and is_deleted",
                Integer.class, UUID.fromString(projectId))).isEqualTo(3);
        assertThat(jdbc.queryForObject("select count(*) from console.tasks t join console.goals g on t.goal_id = g.id "
                + "where g.project_id = ? and t.is_deleted", Integer.class, UUID.fromString(projectId))).isEqualTo(3);
        assertThat(api.get(viewer(), "/api/v1/projects").<Integer>read("$.data.totalElements")).isZero();
    }
}
