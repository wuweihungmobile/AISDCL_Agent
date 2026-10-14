package com.aisdlc.console.support;

import java.util.LinkedHashMap;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * API 整合測試共同基底：每個測試前清空業務資料（TRUNCATE projects CASCADE；system_configs 種子不動），
 * 並備好三個角色的 access token（以 backend/README.md 載明的開發預設密碼走真實登入端點取得，整個 JVM 只登入一次）。
 */
public abstract class AbstractApiIT extends AbstractIntegrationTest {

    @Autowired
    protected MockMvc mvc;

    @Autowired
    protected JdbcTemplate jdbc;

    protected ApiClient api;

    private static volatile Map<String, String> tokens;

    @BeforeEach
    void resetDataAndPrepareClient() {
        api = new ApiClient(mvc);
        jdbc.execute("TRUNCATE console.projects CASCADE");
        if (tokens == null) {
            synchronized (AbstractApiIT.class) {
                if (tokens == null) {
                    tokens = Map.of(
                            "admin", loginToken("admin", "Admin#Dev2026"),
                            "operator", loginToken("operator", "Operator#Dev2026"),
                            "viewer", loginToken("viewer", "Viewer#Dev2026"));
                }
            }
        }
    }

    private String loginToken(String username, String password) {
        ApiClient.Resp resp = api.post(null, "/api/v1/auth/login", Map.of("username", username, "password", password));
        if (resp.status() != 200) {
            throw new IllegalStateException("登入 " + username + " 失敗：" + resp.status() + " " + resp.body());
        }
        return resp.read("$.data.accessToken");
    }

    protected String admin() {
        return tokens.get("admin");
    }

    protected String operator() {
        return tokens.get("operator");
    }

    protected String viewer() {
        return tokens.get("viewer");
    }

    // ---- 快速建資料（一律走真實 API，以 operator 身分）----

    protected String createProject(String name) {
        return createProject(Map.of("name", name, "executionPath", "/work/" + name.replace(' ', '-'),
                "passCriteria", "- 全部通過"));
    }

    protected String createProject(Map<String, Object> body) {
        ApiClient.Resp resp = api.post(operator(), "/api/v1/projects", body);
        if (resp.status() != 201) {
            throw new IllegalStateException("建立專案失敗：" + resp.status() + " " + resp.body());
        }
        return resp.id();
    }

    protected String createGoal(String projectId, String name, String... dependsOn) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("name", name);
        body.put("passCriteria", "- 完成 " + name);
        if (dependsOn.length > 0) {
            body.put("dependsOn", List.of(dependsOn));
        }
        ApiClient.Resp resp = api.post(operator(), "/api/v1/projects/" + projectId + "/goals", body);
        if (resp.status() != 201) {
            throw new IllegalStateException("建立目標失敗：" + resp.status() + " " + resp.body());
        }
        return resp.id();
    }

    protected String createTask(String goalId, String name) {
        ApiClient.Resp resp = api.post(operator(), "/api/v1/goals/" + goalId + "/tasks",
                Map.of("name", name, "passCriteria", "- 完成 " + name));
        if (resp.status() != 201) {
            throw new IllegalStateException("建立任務失敗：" + resp.status() + " " + resp.body());
        }
        return resp.id();
    }

    /** 直接改資料庫的任務狀態（模擬執行引擎事件；Phase 2 還沒有會改狀態的 API）。 */
    protected void setTaskStatus(String taskId, String status) {
        jdbc.update("update console.tasks set status = ? where id = ?", status, UUID.fromString(taskId));
    }

    protected void setProjectStatus(String projectId, String status) {
        jdbc.update("update console.projects set status = ? where id = ?", status, UUID.fromString(projectId));
    }

    protected List<String> uuids(String... ids) {
        return new ArrayList<>(List.of(ids));
    }
}
