package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ResearchRouteUseCase.RouteInput;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violation;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * 分流請求的輸入閘（API 契約 §1.2；TCS-ResearchToPRD-P1 §5.1 值域常數、AT-961-14-1／14-E-1）。<b>不把明知會被拒的請求送到 Bridge</b>：格式違規回 <b>400</b>
 * （{@code errors[]} 欄位級，與 {@code details.violations[{field,rule,message}]}），「分流軌道與 PRD target_scope 不同而缺理由」回 <b>422</b>
 * {@code invalid_request}（規則 {@code scope_differs_reason_required}）。Bridge 另有自己的一份驗證（{@code route.validate_request}，防禦縱深），兩者的值域常數同一份
 * （{@code BRANCH_PATTERN}、{@code REPO_NAME_PATTERN}、{@code PROJECT_NAME_PATTERN}、{@code OWNER_PATTERN}、{@code scope_differs_reason} 1～200 字）；
 * Bridge 專屬的規則（落點清單、範本登記表、git ref 細則、{@code public_confirmation_required}）不在這裡複製。
 */
public final class ResearchRouteGates {

    public static final Pattern BRANCH_PATTERN = Pattern.compile("^feature/[a-z0-9-]{1,40}$");
    public static final Pattern REPO_NAME_PATTERN = Pattern.compile("^[a-z][a-z0-9-]{1,38}$");
    public static final Pattern PROJECT_NAME_PATTERN = Pattern.compile("^[a-z][a-z0-9-]{1,61}$");
    public static final Pattern OWNER_PATTERN = Pattern.compile("^[A-Za-z0-9][A-Za-z0-9-]{0,38}$");
    public static final int SCOPE_DIFFERS_REASON_MAX = 200;
    public static final Set<String> TRACKS = Set.of("A", "B");
    public static final Set<String> VISIBILITIES = Set.of("PUBLIC", "PRIVATE");
    /** 落點目標清單（D-100；固定四值，擴充＝改落點 SSOT 與 DDL CHECK）。 */
    public static final Set<String> PLACEMENT_TARGETS = Set.of("autoclaude", "agentconsole", "sdd", "monorepo");
    private static final Pattern TEMPLATE_PATTERN = Pattern.compile("^[A-Za-z0-9_-]{1,40}$");
    /** 分流軌道對應的 PRD target_scope（軌道 A＝模組、軌道 B＝獨立專案；與 Bridge 的 {@code _SCOPE_FOR_TRACK} 同一對映）。 */
    private static final Map<String, String> SCOPE_FOR_TRACK = Map.of("A", "AISDLC_MODULE", "B", "STANDALONE_PROJECT");
    private static final String SCOPE_RULE = "scope_differs_reason_required";

    private ResearchRouteGates() {
    }

    /** 分軌道與 PRD 目標範圍是否不同（只有 target_scope 為兩個已決值之一、且與軌道對應值不同才算；UNDECIDED 不算）。 */
    public static boolean scopeDiffers(String track, String targetScope) {
        return SCOPE_FOR_TRACK.containsValue(targetScope) && !SCOPE_FOR_TRACK.getOrDefault(track, "").equals(targetScope);
    }

    /**
     * 驗請求並轉成 Bridge 的 snake_case 本文（只含請求有給的鍵；{@code console_project_id}、{@code approver}、{@code github_token} 由服務層另加）。
     *
     * @param targetScope 研究專案的 {@code target_scope}（判斷分流是否與 PRD 不同）
     */
    public static Map<String, Object> bridgeBody(RouteInput in, String targetScope) {
        Check check = new Check();
        String track = in.track();
        if (track == null) {
            check.add("track", "required", "track 為必填（A 或 B）");
        } else if (!TRACKS.contains(track)) {
            check.add("track", "invalid_track", "track 只准 A 或 B");
        }
        if ("A".equals(track)) {
            if (in.targetModule() != null && !PLACEMENT_TARGETS.contains(in.targetModule())) {
                check.add("targetModule", "unknown_target_module", "targetModule 只准 " + String.join("、", new java.util.TreeSet<>(PLACEMENT_TARGETS)));
            }
            pattern(check, "branchName", in.branchName(), BRANCH_PATTERN, "branch_name_pattern", "branchName 須符合 ^feature/[a-z0-9-]{1,40}$");
            if (in.baseRef() != null && (in.baseRef().isBlank() || in.baseRef().length() > 200)) {
                check.add("baseRef", "git_ref", "baseRef 須為 1～200 字的 git ref");
            }
        } else if ("B".equals(track)) {
            if (in.projectName() == null) {
                check.add("projectName", "required", "projectName 為必填");
            } else {
                pattern(check, "projectName", in.projectName(), PROJECT_NAME_PATTERN, "project_name_pattern", "projectName 須符合 ^[a-z][a-z0-9-]{1,61}$");
            }
            if (in.stackTemplate() == null) {
                check.add("stackTemplate", "required", "stackTemplate 為必填");
            } else {
                pattern(check, "stackTemplate", in.stackTemplate(), TEMPLATE_PATTERN, "template_pattern", "stackTemplate 只准英數、底線與連字號（1～40 字）");
            }
            pattern(check, "repoName", in.repoName(), REPO_NAME_PATTERN, "repo_name_pattern", "repoName 須符合 ^[a-z][a-z0-9-]{1,38}$");
            pattern(check, "owner", in.owner(), OWNER_PATTERN, "owner_pattern", "owner 須符合 ^[A-Za-z0-9][A-Za-z0-9-]{0,38}$");
        }
        if (in.visibility() != null) {
            if (!VISIBILITIES.contains(in.visibility())) {
                check.add("visibility", "invalid_visibility", "visibility 只准 PRIVATE 或 PUBLIC");
            } else if ("PUBLIC".equals(in.visibility()) && "A".equals(track)) {
                check.add("visibility", "public_requires_track_b", "軌道 A 不接受 PUBLIC");
            }
        }
        String reason = in.scopeDiffersReason();
        if (reason != null && (reason.isBlank() || reason.codePointCount(0, reason.length()) > SCOPE_DIFFERS_REASON_MAX)) {
            check.add("scopeDiffersReason", "max_length", "scopeDiffersReason 須為 1～" + SCOPE_DIFFERS_REASON_MAX + " 字");
        }
        if (!check.violations.isEmpty()) {
            throw check.validation();
        }
        if (track != null && scopeDiffers(track, targetScope) && reason == null) {
            Check differs = new Check();
            differs.add("scopeDiffersReason", SCOPE_RULE, "分流軌道與 PRD 的目標範圍（" + targetScope + "）不同，須填 1～" + SCOPE_DIFFERS_REASON_MAX + " 字的理由");
            throw differs.unprocessable();
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("track", track);
        put(body, "target_module", in.targetModule());
        put(body, "branch_name", in.branchName());
        put(body, "base_ref", in.baseRef());
        put(body, "project_name", in.projectName());
        put(body, "stack_template", in.stackTemplate());
        put(body, "repo_name", in.repoName());
        put(body, "owner", in.owner());
        put(body, "visibility", in.visibility());
        put(body, "confirm_repo_name", in.confirmRepoName());
        put(body, "create_github", in.createGithub());
        put(body, "ci", in.ci());
        put(body, "docker_compose", in.dockerCompose());
        put(body, "scope_differs_reason", reason);
        return body;
    }

    private static void put(Map<String, Object> body, String key, Object value) {
        if (value != null) {
            body.put(key, value);
        }
    }

    private static void pattern(Check check, String field, String value, Pattern pattern, String rule, String message) {
        if (value != null && !pattern.matcher(value).matches()) {
            check.add(field, rule, message);
        }
    }

    /** 收集違規、一次丟出（與 {@code ResearchInputGates} 同一形狀：{@code errors[]} 加 {@code details.violations[{field,rule,message}]}）。 */
    static final class Check {

        final List<Violation> violations = new ArrayList<>();
        private final List<Map<String, Object>> items = new ArrayList<>();

        void add(String field, String rule, String message) {
            violations.add(new Violation(field, message));
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("field", field);
            item.put("rule", rule);
            item.put("message", message);
            items.add(item);
        }

        ValidationException validation() {
            return new ValidationException("請求欄位未通過檢查（" + violations.size() + " 項）", ErrorReasons.RESEARCH_INVALID_REQUEST, violations,
                    Map.of("violations", items));
        }

        UnprocessableException unprocessable() {
            return new UnprocessableException("請求欄位未通過檢查（" + violations.size() + " 項）", ErrorReasons.RESEARCH_INVALID_REQUEST, List.of(), violations,
                    Map.of("violations", items));
        }
    }
}
