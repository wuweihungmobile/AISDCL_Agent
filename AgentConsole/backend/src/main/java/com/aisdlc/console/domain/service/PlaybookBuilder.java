package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.model.execution.SddTaskSpec;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.service.ExecutionPlanner.PlannedTask;
import com.aisdlc.console.domain.service.ExecutionPlanner.Plan;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;
import java.util.stream.Collectors;

/**
 * 計畫 → 引擎 Playbook（契約 §3.4.1；Bridge 的 {@code PlaybookIn} 是 {@code extra=forbid}，多送欄位即 422）。純 Java。
 *
 * <p>同時做 execute 驗證表的第 9a～9f 項（皆 422、不呼叫 Bridge）：步驟 prompt 長度、評估指令禁用字元（NFR-SEC-03 第 2 層複驗）、
 * 評估指令可執行檔白名單（附錄 D.3）、{@code expectedOutputRegex} 可編譯、範圍任務數上限 500、{@code maxRetries} 上限 20。
 * 每一項「先掃完全部任務」才換下一項（固定順序，QA 可逐項斷言）。
 */
public final class PlaybookBuilder {

    /** Bridge 單一 playbook 的任務數上限（{@code PlaybookIn.tasks} ≤ 500）。 */
    public static final int MAX_TASKS = 500;
    /** Bridge 的 {@code max_retries} 上限。 */
    public static final int MAX_RETRIES = 20;
    /** 附錄 D.3 的預設可執行檔白名單（可由 {@code console.security.evaluator-allowlist} 覆寫）。 */
    public static final Set<String> DEFAULT_EVALUATOR_ALLOWLIST = Set.of("pytest", "python", "python3", "py", "npm",
            "npx", "node", "pnpm", "yarn", "mvn", "mvnw", "gradle", "gradlew", "java", "dotnet", "go", "cargo",
            "make", "tsc", "eslint", "ruff", "mypy", "git");

    private static final Pattern UNSAFE_PROJECT_CHARS = Pattern.compile("[^A-Za-z0-9._\\-\\u4e00-\\u9fff]");
    private static final int MAX_PROJECT_NAME = 200;

    /**
     * Playbook 的一個任務（欄位名對映 {@code tasks[]}；{@code command} 永不送，引擎 Kernel 路徑對它零消費）。
     *
     * <p>v1.5（契約 §3.4.1 的 SDD 補充）：{@code maintainContext}、{@code specDigest}、{@code weakRegex} 只有 SDD 批次才有值
     * （取自 {@code passCriteriaSpec}），null 一律<b>不送</b>——所以非 SDD 批次的請求本文與 v1.4 逐位元相同。
     */
    public record PlaybookTask(String stepId, String name, String prompt, String expectedOutputRegex,
                               String evaluatorCommand, int maxRetries, String goalTaskId, Boolean maintainContext,
                               String specDigest, Boolean weakRegex) {

        /** 非 SDD 任務（沒有 SDD 欄位）。 */
        public PlaybookTask(String stepId, String name, String prompt, String expectedOutputRegex,
                            String evaluatorCommand, int maxRetries, String goalTaskId) {
            this(stepId, name, prompt, expectedOutputRegex, evaluatorCommand, maxRetries, goalTaskId, null, null, null);
        }

        Map<String, Object> toMap() {
            Map<String, Object> map = new LinkedHashMap<>();
            map.put("step_id", stepId);
            map.put("name", name);
            map.put("prompt", prompt);
            if (expectedOutputRegex != null && !expectedOutputRegex.isBlank()) {
                map.put("expected_output_regex", expectedOutputRegex);
            }
            if (evaluatorCommand != null && !evaluatorCommand.isBlank()) {
                map.put("evaluator_command", evaluatorCommand);
            }
            map.put("max_retries", maxRetries);
            map.put("goal_task_id", goalTaskId);
            if (maintainContext != null) {
                map.put("maintain_context", maintainContext);
            }
            if (specDigest != null && !specDigest.isBlank()) {
                map.put("spec_digest", specDigest);
            }
            if (weakRegex != null) {
                map.put("weak_regex", weakRegex);
            }
            return map;
        }
    }

    public record Playbook(String project, String globalGoal, int maxRetriesPerStep, List<PlaybookTask> tasks) {

        public Playbook {
            tasks = List.copyOf(tasks);
        }

        /** Bridge {@code PlaybookIn} 的 JSON 形狀（{@code version}、{@code project}、{@code global_goal}、{@code global_invariants}、{@code tasks}）。 */
        public Map<String, Object> toMap() {
            Map<String, Object> map = new LinkedHashMap<>();
            map.put("version", "1.0");
            map.put("project", project);
            map.put("global_goal", globalGoal);
            map.put("global_invariants", Map.of("max_retries_per_step", maxRetriesPerStep));
            map.put("tasks", tasks.stream().map(PlaybookTask::toMap).toList());
            return map;
        }
    }

    private PlaybookBuilder() {
    }

    /**
     * @param maxRetriesPerStep  系統參數 {@code agent.maxRetries}（0～20，設定驗證已保證）
     * @param evaluatorAllowlist 評估指令可執行檔白名單（小寫，不含路徑與 .exe／.cmd／.bat）
     */
    public static Playbook build(Project project, Plan plan, int maxRetriesPerStep, Set<String> evaluatorAllowlist) {
        return build(project, plan, maxRetriesPerStep, evaluatorAllowlist, Map.of());
    }

    /**
     * @param sddSpecs SDD 批次（資格成立，{@code SddBatchPolicy.Decision#active}）的任務 id → {@code passCriteriaSpec} 欄位；
     *                 {@code plan} 的 step_id 此時已是 SDD 的 {@code stepId}。非 SDD 批次傳空映射（請求本文與 v1.4 相同）
     */
    public static Playbook build(Project project, Plan plan, int maxRetriesPerStep, Set<String> evaluatorAllowlist,
                                 Map<UUID, SddTaskSpec> sddSpecs) {
        List<PlaybookTask> tasks = new ArrayList<>();
        for (PlannedTask planned : plan.tasks()) {
            Task task = planned.task();
            String prompt = StepPrompt.build(planned.stepId(), task.name(), planned.goal().name(),
                    task.description(), task.passCriteria());
            SddTaskSpec sdd = sddSpecs.get(task.id());
            tasks.add(new PlaybookTask(planned.stepId(), task.name(), prompt, task.expectedOutputRegex(),
                    task.evaluatorCommand(), task.maxRetries(), task.id().toString(),
                    sdd == null ? null : sdd.maintainContext(), sdd == null ? null : sdd.specDigest(),
                    sdd == null ? null : sdd.weakRegex()));
        }
        requirePromptsWithinLimit(plan, tasks);
        requireSafeEvaluators(plan);
        requireAllowedExecutables(plan, evaluatorAllowlist);
        requireCompilableRegexes(plan);
        if (tasks.size() > MAX_TASKS) {
            throw new UnprocessableException("範圍任務數 " + tasks.size() + " 超過單一批次上限 " + MAX_TASKS,
                    ErrorReasons.TOO_MANY_TASKS, Map.of("count", tasks.size(), "limit", MAX_TASKS));
        }
        requireRetriesWithinLimit(plan);
        return new Playbook(sanitizeProjectName(project), project.passCriteria(), maxRetriesPerStep, tasks);
    }

    /** 專案名稱淨化（契約 §3.4.1）：不在 {@code [A-Za-z0-9._\-一-鿿]} 內的字元換成 {@code _}，截到 200 字元；空則 {@code project-<id 前 8 碼>}。 */
    public static String sanitizeProjectName(Project project) {
        String cleaned = UNSAFE_PROJECT_CHARS.matcher(project.name() == null ? "" : project.name()).replaceAll("_");
        if (cleaned.length() > MAX_PROJECT_NAME) {
            cleaned = cleaned.substring(0, MAX_PROJECT_NAME);
        }
        return cleaned.isBlank() ? "project-" + project.id().toString().substring(0, 8) : cleaned;
    }

    /** 評估指令的可執行檔：第一個以空白分隔的 token，去路徑前綴與 .exe／.cmd／.bat 後綴，小寫（附錄 D.3）。 */
    public static String executableOf(String evaluatorCommand) {
        String trimmed = evaluatorCommand == null ? "" : evaluatorCommand.strip();
        if (trimmed.isEmpty()) {
            return "";
        }
        String first = trimmed.split("\\s+", 2)[0];
        int slash = Math.max(first.lastIndexOf('/'), first.lastIndexOf('\\'));
        String name = slash >= 0 ? first.substring(slash + 1) : first;
        String lower = name.toLowerCase(Locale.ROOT);
        for (String suffix : List.of(".exe", ".cmd", ".bat")) {
            if (lower.endsWith(suffix)) {
                return lower.substring(0, lower.length() - suffix.length());
            }
        }
        return lower;
    }

    private static void requirePromptsWithinLimit(Plan plan, List<PlaybookTask> tasks) {
        for (int i = 0; i < tasks.size(); i++) {
            int length = tasks.get(i).prompt().length();
            if (length > StepPrompt.MAX_LENGTH) {
                PlannedTask planned = plan.tasks().get(i);
                throw new UnprocessableException("步驟 " + planned.stepId() + " 的 prompt 長 " + length
                        + " 字元，超過上限 " + StepPrompt.MAX_LENGTH, ErrorReasons.PROMPT_TOO_LONG,
                        Map.of("taskId", planned.task().id().toString(), "stepId", planned.stepId(),
                                "length", length, "limit", StepPrompt.MAX_LENGTH));
            }
        }
    }

    private static void requireSafeEvaluators(Plan plan) {
        for (PlannedTask planned : plan.tasks()) {
            String command = planned.task().evaluatorCommand();
            if (command == null || command.isBlank()) {
                continue;
            }
            List<String> chars = PassCriteriaSanitizer.violationsOf(command).stream().map(String::valueOf)
                    .collect(Collectors.toCollection(ArrayList::new));
            if (command.chars().anyMatch(Character::isISOControl)) {
                chars.add("\\n");
            }
            if (!chars.isEmpty()) {
                throw new UnprocessableException("任務「" + planned.task().name() + "」的評估指令含禁用字元：" + chars,
                        ErrorReasons.EVALUATOR_DENIED_CHARS,
                        Map.of("taskId", planned.task().id().toString(), "chars", List.copyOf(chars)));
            }
        }
    }

    private static void requireAllowedExecutables(Plan plan, Set<String> allowlist) {
        for (PlannedTask planned : plan.tasks()) {
            String command = planned.task().evaluatorCommand();
            if (command == null || command.isBlank()) {
                continue;
            }
            String executable = executableOf(command);
            if (!allowlist.contains(executable)) {
                throw new UnprocessableException("任務「" + planned.task().name() + "」的評估指令可執行檔 "
                        + executable + " 不在白名單", ErrorReasons.EVALUATOR_NOT_ALLOWED,
                        Map.of("taskId", planned.task().id().toString(), "executable", executable));
            }
        }
    }

    private static void requireCompilableRegexes(Plan plan) {
        for (PlannedTask planned : plan.tasks()) {
            String regex = planned.task().expectedOutputRegex();
            if (regex == null || regex.isBlank()) {
                continue;
            }
            try {
                Pattern.compile(regex);
            } catch (PatternSyntaxException e) {
                throw new UnprocessableException("任務「" + planned.task().name() + "」的 expectedOutputRegex 無法編譯："
                        + e.getDescription(), ErrorReasons.REGEX_NOT_COMPILABLE,
                        Map.of("taskId", planned.task().id().toString()));
            }
        }
    }

    private static void requireRetriesWithinLimit(Plan plan) {
        for (PlannedTask planned : plan.tasks()) {
            if (planned.task().maxRetries() > MAX_RETRIES) {
                throw new UnprocessableException("任務「" + planned.task().name() + "」的 maxRetries "
                        + planned.task().maxRetries() + " 超過上限 " + MAX_RETRIES, ErrorReasons.MAX_RETRIES_EXCEEDED,
                        Map.of("taskId", planned.task().id().toString(), "maxRetries", planned.task().maxRetries(),
                                "limit", MAX_RETRIES));
            }
        }
    }
}
