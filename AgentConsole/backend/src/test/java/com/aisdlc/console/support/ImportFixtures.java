package com.aisdlc.console.support;

import tools.jackson.databind.json.JsonMapper;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 匯入整合測試的夾具產生器：假 chat-completions 的回應、三層草案樹、假 Bridge 的回應本文（契約 §5 E2E-01、§3.3）。
 * 一律以 Map 組出再序列化，避免手寫轉義。
 */
public final class ImportFixtures {

    private static final JsonMapper JSON = JsonMapper.builder().build();

    private ImportFixtures() {
    }

    // ── 任務／目標／樹 ─────────────────────────────────────────────────────────

    public static Map<String, Object> task(String name, String description, String passCriteria) {
        Map<String, Object> task = new LinkedHashMap<>();
        task.put("name", name);
        task.put("description", description);
        task.put("passCriteria", passCriteria);
        return task;
    }

    /** {@code [T<n>_DONE]} 風格的任務（與契約夾具同形）。 */
    public static Map<String, Object> doneTask(String name, int n) {
        return task(name, "請輸出 [T" + n + "_DONE]", "輸出含 [T" + n + "_DONE]");
    }

    public static Map<String, Object> goal(String key, String name, List<String> dependsOn,
                                           List<Map<String, Object>> tasks) {
        Map<String, Object> goal = new LinkedHashMap<>();
        goal.put("key", key);
        goal.put("name", name);
        goal.put("description", "");
        goal.put("passCriteria", name + "完成");
        goal.put("dependsOn", dependsOn);
        goal.put("tasks", tasks);
        return goal;
    }

    /** 三層樹 JSON（只有 {@code project} 與 {@code goals}，與模型輸出同形）。 */
    public static String treeJson(String projectName, List<Map<String, Object>> goals) {
        Map<String, Object> project = new LinkedHashMap<>();
        project.put("name", projectName);
        project.put("executionPath", "/ignored");
        project.put("passCriteria", "全部目標完成");
        project.put("description", "由 BRD 匯入");
        Map<String, Object> tree = new LinkedHashMap<>();
        tree.put("project", project);
        tree.put("goals", goals);
        return JSON.writeValueAsString(tree);
    }

    /** E2E-01 的 S-OK 樹：g1（初始化、設定）→ g2（實作）。 */
    public static String okTree() {
        return treeJson("E2E 匯入專案", List.of(
                goal("g1", "基礎", List.of(), List.of(doneTask("初始化", 1), doneTask("設定", 2))),
                goal("g2", "核心", List.of("g1"), List.of(doneTask("實作", 3)))));
    }

    /** 單一目標含 {@code count} 個任務（用來湊 max_steps 閘）。 */
    public static String treeWithTaskCount(int count) {
        List<Map<String, Object>> tasks = new ArrayList<>();
        for (int i = 1; i <= count; i++) {
            tasks.add(doneTask("任務 " + i, i));
        }
        return treeJson("E2E 匯入專案", List.of(goal("g1", "基礎", List.of(), tasks)));
    }

    // ── chat-completions 回應 ─────────────────────────────────────────────────

    /** 一個 200 的 chat-completions 回應本文，{@code content} 是模型輸出的字串（通常是 {@link #okTree()}）。 */
    public static String chatCompletion(String content) {
        Map<String, Object> message = new LinkedHashMap<>();
        message.put("role", "assistant");
        message.put("content", content);
        Map<String, Object> choice = new LinkedHashMap<>();
        choice.put("index", 0);
        choice.put("finish_reason", "stop");
        choice.put("message", message);
        Map<String, Object> usage = new LinkedHashMap<>();
        usage.put("prompt_tokens", 812);
        usage.put("completion_tokens", 340);
        usage.put("total_tokens", 1152);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("id", "chatcmpl-e2e");
        body.put("object", "chat.completion");
        body.put("model", "e2e-model");
        body.put("choices", List.of(choice));
        body.put("usage", usage);
        return JSON.writeValueAsString(body);
    }

    // ── 假 Bridge 的回應本文 ──────────────────────────────────────────────────

    /** {@code POST /autoclaude/decompose} 的 200 本文。 */
    public static String decomposeResponse(String draftId, String reasoning, List<Map<String, Object>> steps) {
        Map<String, Object> playbook = new LinkedHashMap<>();
        playbook.put("tasks", steps);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("draft_id", draftId);
        body.put("reasoning", reasoning);
        body.put("playbook", playbook);
        return JSON.writeValueAsString(body);
    }

    public static Map<String, Object> decomposeStep(String stepId, String name, String prompt,
                                                    String evaluatorCommand) {
        Map<String, Object> step = new LinkedHashMap<>();
        step.put("step_id", stepId);
        step.put("name", name);
        step.put("prompt", prompt);
        if (evaluatorCommand != null) {
            step.put("evaluator_command", evaluatorCommand);
        }
        return step;
    }

    /** {@code POST /sdd/compile} 的 200 本文：{@code count} 個合約。 */
    public static String sddCompileResponse(String scenario, int count) {
        List<Map<String, Object>> tasks = new ArrayList<>();
        for (int i = 1; i <= count; i++) {
            Map<String, Object> task = new LinkedHashMap<>();
            task.put("step_id", "C" + i);
            task.put("name", "合約 " + i);
            task.put("prompt", "請實作合約 " + i);
            task.put("expected_output_regex", "OK-" + i + "\\d+");
            task.put("evaluator_command", "pytest -q tests/test" + i);
            task.put("weak_regex", false);
            tasks.add(task);
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("scenario", scenario);
        body.put("spec_path", "/spec/cart.yaml");
        body.put("digest", "0123456789abcdef0123456789abcdef");
        body.put("tasks", tasks);
        return JSON.writeValueAsString(body);
    }

    /** Bridge 的錯誤封包（{@code {code,reason,gate?,detail?}}）。 */
    public static String bridgeError(int code, String reason, String gate, String detail) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("code", code);
        body.put("reason", reason);
        if (gate != null) {
            body.put("gate", gate);
        }
        if (detail != null) {
            body.put("detail", detail);
        }
        return JSON.writeValueAsString(body);
    }

    // ── 文件 ─────────────────────────────────────────────────────────────────

    /** 以 {@code # BRD} 與兩個 {@code ##} 標題開頭、≥ 200 字元的 Markdown（確保走路徑 B 而非 C）；{@code marker} 附在尾端。 */
    public static String markdownDocument(String marker) {
        return "# BRD\n\n## 功能需求\n- 使用者可以登入與登出\n- 管理員可以管理帳號\n\n## 非功能需求\n- 回應時間小於兩秒\n"
                + "- 系統需有稽核紀錄\n\n" + "這份文件描述一個小型內部系統的需求，包含登入、帳號管理、稽核與效能目標，"
                + "用來驗證匯入流程能把文件拆成專案、目標與任務三層結構。".repeat(2) + "\n" + (marker == null ? "" : marker);
    }
}
