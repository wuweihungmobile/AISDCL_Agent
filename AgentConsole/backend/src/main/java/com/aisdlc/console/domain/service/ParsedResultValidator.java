package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.imports.GateError;
import com.aisdlc.console.domain.model.imports.ParsedResult;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedGoal;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedTask;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 三道有界閘與 {@code prompt_too_long}（契約 §3.3.5；US-I-10「完整顯示、不截斷、不修剪」）。
 *
 * <p>三條解析路徑（SDD／LLM／DECOMPOSE）與 {@code PUT /import/{id}/result} 共用本類別，<b>不信任上游</b>：
 * 無論 Bridge 或 LLM 宣稱已驗過，後端一律重新過閘。在樹層級<b>一次列出全部違規</b>，順序固定：
 * <ol>
 *   <li>{@code empty_prompt}：任務 name／description 去空白後為空（欄位缺漏為 400 結構問題，不在這裡）；</li>
 *   <li>{@code max_steps}：目標數 &gt; 24、或任一目標的任務數 &gt; 24（硬上限；只准下調不准上調）；</li>
 *   <li>{@code cycle}：目標依賴不是 DAG（Kahn 排序失敗、自依賴、引用不存在的 key、目標 key 重複）；</li>
 *   <li>{@code prompt_too_long}：任務依 {@link StepPrompt} 樣板組出的 prompt 超過 20,000 字元。</li>
 * </ol>
 * 同一道閘內依樹的位置排序。本類別不修改輸入樹，也不截斷、不修剪。
 */
public final class ParsedResultValidator {

    /** 每個目標任務數與目標數的硬上限（對映引擎 {@code MAX_DECOMPOSITION_STEPS}）。 */
    public static final int HARD_MAX_STEPS = 24;

    private final int maxSteps;

    public ParsedResultValidator() {
        this(HARD_MAX_STEPS);
    }

    /** @param maxSteps 可下調不可上調：超過 {@link #HARD_MAX_STEPS} 的值一律夾回 24。 */
    public ParsedResultValidator(int maxSteps) {
        this.maxSteps = Math.max(1, Math.min(maxSteps, HARD_MAX_STEPS));
    }

    public int maxSteps() {
        return maxSteps;
    }

    /** 回傳全部違規（空清單＝通過）。 */
    public List<GateError> validate(ParsedResult tree) {
        List<GateError> errors = new ArrayList<>();
        List<ParsedGoal> goals = tree.goals() == null ? List.of() : tree.goals();
        checkEmptyPrompts(goals, errors);
        checkMaxSteps(goals, errors);
        checkCycles(goals, errors);
        checkPromptLengths(goals, errors);
        return errors;
    }

    // ── 1. empty_prompt ──────────────────────────────────────────────────────

    private static void checkEmptyPrompts(List<ParsedGoal> goals, List<GateError> errors) {
        for (int i = 0; i < goals.size(); i++) {
            List<ParsedTask> tasks = tasksOf(goals.get(i));
            for (int j = 0; j < tasks.size(); j++) {
                ParsedTask task = tasks.get(j);
                String where = "goals[" + i + "].tasks[" + j + "]";
                if (isBlank(task.name())) {
                    errors.add(new GateError(GateError.EMPTY_PROMPT,
                            "任務「（未命名）」的名稱為空（" + where + "）", where + ".name"));
                }
                if (isBlank(task.description())) {
                    errors.add(new GateError(GateError.EMPTY_PROMPT,
                            "任務「" + labelOf(task) + "」的描述為空（" + where + "）", where + ".description"));
                }
            }
        }
    }

    // ── 2. max_steps ─────────────────────────────────────────────────────────

    private void checkMaxSteps(List<ParsedGoal> goals, List<GateError> errors) {
        if (goals.size() > maxSteps) {
            errors.add(new GateError(GateError.MAX_STEPS,
                    "目標數 " + goals.size() + " 超過上限 " + maxSteps + "（不截斷、不修剪）", "goals"));
        }
        for (int i = 0; i < goals.size(); i++) {
            int count = tasksOf(goals.get(i)).size();
            if (count > maxSteps) {
                errors.add(new GateError(GateError.MAX_STEPS,
                        "目標「" + goalLabel(goals.get(i)) + "」的任務數 " + count + " 超過上限 " + maxSteps
                                + "（不截斷、不修剪）", "goals[" + i + "].tasks"));
            }
        }
    }

    // ── 3. cycle ─────────────────────────────────────────────────────────────

    private static void checkCycles(List<ParsedGoal> goals, List<GateError> errors) {
        Map<String, Integer> indexByKey = new LinkedHashMap<>();
        for (int i = 0; i < goals.size(); i++) {
            String key = goals.get(i).key();
            if (key == null || key.isBlank()) {
                continue;
            }
            if (indexByKey.putIfAbsent(key, i) != null) {
                errors.add(new GateError(GateError.CYCLE, "目標 key 重複：" + key, "goals[" + i + "].key"));
            }
        }
        Map<String, Set<String>> dependsOn = new LinkedHashMap<>();
        for (int i = 0; i < goals.size(); i++) {
            ParsedGoal goal = goals.get(i);
            String key = goal.key();
            if (key == null || key.isBlank() || indexByKey.get(key) != i) {
                continue;
            }
            Set<String> deps = new LinkedHashSet<>();
            for (String dependency : goal.dependsOn() == null ? List.<String>of() : goal.dependsOn()) {
                String where = "goals[" + i + "].dependsOn";
                if (dependency == null || !indexByKey.containsKey(dependency)) {
                    errors.add(new GateError(GateError.CYCLE, "目標「" + goalLabel(goal)
                            + "」依賴不存在的目標 key：" + dependency, where));
                } else if (dependency.equals(key)) {
                    errors.add(new GateError(GateError.CYCLE, "目標「" + goalLabel(goal) + "」不可依賴自己", where));
                } else {
                    deps.add(dependency);
                }
            }
            dependsOn.put(key, deps);
        }
        List<String> cycle = findCycle(dependsOn);
        if (!cycle.isEmpty()) {
            List<String> names = new ArrayList<>();
            for (String key : cycle) {
                names.add(goalLabel(goals.get(indexByKey.get(key))));
            }
            errors.add(new GateError(GateError.CYCLE, "目標依賴成環：" + String.join(" -> ", names),
                    "goals[" + indexByKey.get(cycle.get(0)) + "].dependsOn"));
        }
    }

    /**
     * Kahn 排序後的殘餘節點必含環：沿「殘餘的前置依賴」一路走，必在有限步內回到走過的節點，那一段即環路
     * （首尾同一個 key）。無環回空清單。
     */
    static List<String> findCycle(Map<String, Set<String>> dependsOn) {
        Map<String, Integer> indegree = new LinkedHashMap<>();
        Map<String, List<String>> dependents = new HashMap<>();
        for (Map.Entry<String, Set<String>> entry : dependsOn.entrySet()) {
            indegree.put(entry.getKey(), entry.getValue().size());
            for (String dependency : entry.getValue()) {
                dependents.computeIfAbsent(dependency, k -> new ArrayList<>()).add(entry.getKey());
            }
        }
        Deque<String> ready = new ArrayDeque<>();
        indegree.forEach((node, degree) -> {
            if (degree == 0) {
                ready.add(node);
            }
        });
        Set<String> remaining = new LinkedHashSet<>(dependsOn.keySet());
        while (!ready.isEmpty()) {
            String node = ready.poll();
            remaining.remove(node);
            for (String dependent : dependents.getOrDefault(node, List.of())) {
                if (indegree.merge(dependent, -1, Integer::sum) == 0) {
                    ready.add(dependent);
                }
            }
        }
        if (remaining.isEmpty()) {
            return List.of();
        }
        Map<String, Integer> position = new HashMap<>();
        List<String> path = new ArrayList<>();
        String current = remaining.iterator().next();
        while (!position.containsKey(current)) {
            position.put(current, path.size());
            path.add(current);
            String next = null;
            for (String dependency : dependsOn.get(current)) {
                if (remaining.contains(dependency)) {
                    next = dependency;
                    break;
                }
            }
            current = next;
        }
        List<String> cycle = new ArrayList<>(path.subList(position.get(current), path.size()));
        cycle.add(current);
        return cycle;
    }

    // ── 4. prompt_too_long ───────────────────────────────────────────────────

    private static void checkPromptLengths(List<ParsedGoal> goals, List<GateError> errors) {
        for (int i = 0; i < goals.size(); i++) {
            ParsedGoal goal = goals.get(i);
            List<ParsedTask> tasks = tasksOf(goal);
            for (int j = 0; j < tasks.size(); j++) {
                ParsedTask task = tasks.get(j);
                // 匯入階段還沒有批次範圍，stepId 以位置（G<目標序>-T<任務序>）估算；執行階段的第 9a 項才是權威檢查。
                String prompt = StepPrompt.build("G" + (i + 1) + "-T" + (j + 1), task.name(), goal.name(),
                        task.description(), task.passCriteria());
                if (prompt.length() > StepPrompt.MAX_LENGTH) {
                    errors.add(new GateError(GateError.PROMPT_TOO_LONG,
                            "任務「" + labelOf(task) + "」的 prompt 長度 " + prompt.length() + " 超過上限 "
                                    + StepPrompt.MAX_LENGTH, "goals[" + i + "].tasks[" + j + "]"));
                }
            }
        }
    }

    // ── 共用 ─────────────────────────────────────────────────────────────────

    private static List<ParsedTask> tasksOf(ParsedGoal goal) {
        return goal.tasks() == null ? List.of() : goal.tasks();
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private static String labelOf(ParsedTask task) {
        return isBlank(task.name()) ? "（未命名）" : task.name().strip();
    }

    private static String goalLabel(ParsedGoal goal) {
        if (!isBlank(goal.name())) {
            return goal.name().strip();
        }
        return isBlank(goal.key()) ? "（未命名）" : goal.key();
    }
}
