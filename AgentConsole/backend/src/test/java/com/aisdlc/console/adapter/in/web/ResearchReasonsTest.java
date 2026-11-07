package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.domain.exception.ErrorReasons;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 研究 reason 的四方雙向鎖（TCS-ResearchToPRD-P0 AT-960-5-6）：後端 {@code ErrorReasons} 的 {@code RESEARCH_} 前綴常數、前端 {@code lib/domain/research.ts} 的
 * {@code RESEARCH_REASONS}、契約 API_Contract_ResearchToPRD §0.2 的 reason 表、Architecture §11.1 的研究 reason 表，四處的集合逐字相等。為什麼重要：reason 是前端據以顯示說明與決定可否重試的
 * 機器可讀欄位——後端改了字面而前端、契約沒跟著改，使用者看到的是「未知錯誤」；而 {@code lib/api/reasons.ts} 的 {@code REASONS} 與凍結契約附錄 B 雙向鎖，研究 reason 不得進去
 * （所以它們各住自己的常數）。
 *
 * <p><b>P1 起集合＝三十五個</b>（AT-961-15-4）：P0 的二十二個加 R-2 尾巴四個（{@code compile_failed}、{@code sdd_cli_failed}、{@code fsm_state_unreadable}、{@code invalid_request}；
 * ⚖P1-25——{@code invalid_request} 由區域常數改為 {@code RESEARCH_} 前綴常數）與 P1 新增九個（分流、SCR、拆解）。契約 §0.2 與 Architecture §11.1 的補列屬主控的 RELEASE_READY 勘誤
 * （D-115）：勘誤落地前，兩份文件缺列的 reason 以 {@link #CONTRACT_ERRATUM_PENDING}、{@link #ARCHITECTURE_ERRATUM_PENDING} 具名記錄，並以「缺列集合恰等於名單」雙向鎖住——
 * 勘誤落地後名單必須清空，否則本測試轉紅逼同步（沿本檔沿革的棘輪手法）。
 *
 * <p>P0 集合＝二十二個：P0 契約原列十七個仍有效者，加 Bridge 專屬的五個——{@code allowlist_exists}（409）、{@code init_failed}（502）、{@code not_implemented}（Bridge 501→console-api 502）、
 * {@code digest_mismatch}（422；D-72）、{@code missing_digests}（422；D-72）。{@code invalid_request}（輸入閘，400／422）是區域常數（{@code ResearchInputGates.INVALID_REQUEST}），
 * 不入本集合（先例 SiWriteGates）。
 *
 * <p><b>已退役</b>：P0 契約原列的 {@code spec_digest_changed}（409）被 D-72 的 {@code digest_mismatch}／{@code missing_digests}（422）取代——Bridge 對研究端點不再回它，
 * 所以 {@link #RETIRED_REASONS} 鎖住它不得在任何一處復活（後端常數、前端常數、契約、Architecture 表、OpenAPI 說明）。
 *
 * <p><b>沿革</b>：本測試在契約與前端補列前，曾以「已知待補列」「已被取代」「Architecture 缺口」三組名單明載差異，並設計成補列後轉紅逼同步；2026-11-03 契約〈勘誤記錄〉第 1、2 列、
 * Architecture §11.1 與前端 {@code RESEARCH_REASONS} 同步落地，三組名單已清空並移除（差異消失後留著空名單的斷言永不會紅，不是鎖）。
 */
class ResearchReasonsTest {

    /** TCS §3 AT-960-5-6 的 P0 二十二個 reason（後端、前端、契約、Architecture 四處的集合必須相等）。 */
    private static final Set<String> P0_REASONS = new TreeSet<>(List.of("research_write_disabled", "research_write_forbidden", "research_requires_db",
            "db_blocked", "research_not_found", "slug_in_use", "stage_conflict", "prd_version_conflict", "review_not_passed", "fsm_state_conflict",
            "escalated", "spec_frozen", "layer_unavailable", "sanitization_failed", "terms_ack_required", "bridge_unreachable", "bridge_timeout",
            "allowlist_exists", "init_failed", "not_implemented", "digest_mismatch", "missing_digests"));
    /** R-2 尾巴四個（⚖P1-25；console-api 實際會回的研究 reason，P0 時以區域常數或未列入四方鎖）。 */
    private static final Set<String> P0_TAIL_REASONS = new TreeSet<>(List.of("compile_failed", "sdd_cli_failed", "fsm_state_unreadable", "invalid_request"));
    /** P1 新增九個（分流、SCR、拆解；IFACE §2）。 */
    private static final Set<String> P1_REASONS = new TreeSet<>(List.of("route_unsupported_in_deployment", "branch_exists", "target_not_empty",
            "public_confirmation_required", "route_conflict", "route_step_failed", "scr_open", "scr_limit", "decomposition_stale"));
    /** P1 起的四方鎖集合：22＋4＋9＝35。 */
    private static final Set<String> ALL_REASONS = union(P0_REASONS, P0_TAIL_REASONS, P1_REASONS);
    /** 契約 §0.2 勘誤尚未落地、缺列的 reason（主控 RELEASE_READY 批次補列後清空；D-115）。 */
    private static final Set<String> CONTRACT_ERRATUM_PENDING = new TreeSet<>();
    /** Architecture §11.1 研究 reason 表勘誤尚未落地、缺列的 reason（同上）。 */
    private static final Set<String> ARCHITECTURE_ERRATUM_PENDING = new TreeSet<>();
    /** D-72 取代後退役的 reason：Bridge 對研究端點不再回它，任何一處都不得再列（見類別說明）。 */
    private static final Set<String> RETIRED_REASONS = new TreeSet<>(List.of("spec_digest_changed"));

    @SafeVarargs
    private static Set<String> union(Set<String>... sets) {
        Set<String> out = new TreeSet<>();
        for (Set<String> set : sets) {
            out.addAll(set);
        }
        return out;
    }

    private static String read(String... segments) {
        Path path = Path.of("..", segments);
        try {
            return Files.readString(path, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("讀不到 " + path.toAbsolutePath(), e);
        }
    }

    /** 後端：{@code ErrorReasons} 的 {@code RESEARCH_} 前綴常數值。 */
    private static Set<String> backendReasons() {
        Set<String> out = new TreeSet<>();
        for (Field field : ErrorReasons.class.getDeclaredFields()) {
            if (field.getName().startsWith("RESEARCH_") && Modifier.isStatic(field.getModifiers()) && field.getType() == String.class) {
                try {
                    out.add((String) field.get(null));
                } catch (IllegalAccessException e) {
                    throw new IllegalStateException(e);
                }
            }
        }
        return out;
    }

    /** 前端：{@code RESEARCH_REASONS = { … } as const} 區塊內的字面值。 */
    private static Set<String> frontendReasons() {
        String source = read("frontend", "lib", "domain", "research.ts");
        int start = source.indexOf("export const RESEARCH_REASONS = {");
        assertThat(start).as("前端找不到 RESEARCH_REASONS").isGreaterThanOrEqualTo(0);
        String block = source.substring(start, source.indexOf("} as const;", start));
        Set<String> out = new TreeSet<>();
        Matcher matcher = Pattern.compile(":\\s*\"([a-z_]+)\"").matcher(block);
        while (matcher.find()) {
            out.add(matcher.group(1));
        }
        return out;
    }

    /** Architecture §11.1 的研究 reason 表：{@code `reason`(狀態碼)} 形式的全部項。 */
    private static Map<String, Integer> architectureReasons() {
        String architecture = read("docs", "02_architecture", "Architecture.md");
        int start = architecture.indexOf("**研究 `reason`**");
        assertThat(start).as("Architecture 找不到研究 reason 表").isGreaterThanOrEqualTo(0);
        String line = architecture.substring(start, architecture.indexOf('\n', start));
        Map<String, Integer> out = new LinkedHashMap<>();
        Matcher matcher = Pattern.compile("`([a-z_]+)`\\((\\d{3})\\)").matcher(line);
        while (matcher.find()) {
            out.put(matcher.group(1), Integer.parseInt(matcher.group(2)));
        }
        return out;
    }

    /** OpenAPI 說明文字：研究操作的 403、404、409 與其餘失敗說明（{@link ResearchErrorDocs}）。 */
    private static String documentation() {
        List<String> parts = new ArrayList<>(List.of(ResearchErrorDocs.FORBIDDEN, ResearchErrorDocs.NOT_FOUND));
        parts.addAll(ResearchErrorDocs.CONFLICT.values());
        ResearchErrorDocs.EXTRA.values().forEach(codes -> parts.addAll(codes.values()));
        return String.join("\n", parts);
    }

    @Test
    void AT_960_5_6_theBackendConstantsAreExactlyTheThirtyFiveReasonsOfP0AndP1() {
        assertThat(P0_REASONS).hasSize(22);
        assertThat(P0_TAIL_REASONS).hasSize(4);
        assertThat(P1_REASONS).hasSize(9);
        assertThat(ALL_REASONS).hasSize(35);
        assertThat(backendReasons()).as("後端 ErrorReasons 的 RESEARCH_ 常數（P0 二十二＋R-2 尾巴四＋P1 九）").isEqualTo(ALL_REASONS);
    }

    @Test
    void AT_960_5_6_theFrontendConstantsEqualTheThirtyFiveReasonsAndTheContractAndArchitectureTablesNameEveryP0One() {
        assertThat(frontendReasons()).as("前端 RESEARCH_REASONS").isEqualTo(ALL_REASONS);

        String contract = read("docs", "02_architecture", "API_Contract_ResearchToPRD.md");
        for (String reason : P0_REASONS) {
            assertThat(contract).as("契約提到 reason " + reason).contains("`" + reason + "`");
        }
        Map<String, Integer> architecture = architectureReasons();
        assertThat(architecture.keySet()).as("Architecture §11.1 的研究 reason 表").containsAll(P0_REASONS);
        assertThat(architecture).containsEntry("research_write_disabled", 503).containsEntry("research_write_forbidden", 403)
                .containsEntry("research_not_found", 404).containsEntry("slug_in_use", 409).containsEntry("layer_unavailable", 400)
                .containsEntry("sanitization_failed", 422).containsEntry("terms_ack_required", 422).containsEntry("allowlist_exists", 409)
                .containsEntry("digest_mismatch", 422).containsEntry("missing_digests", 422).containsEntry("bridge_unreachable", 502)
                .containsEntry("init_failed", 502).containsEntry("not_implemented", 502).containsEntry("bridge_timeout", 504);
    }

    @Test
    void AT_961_15_4_theContractAndArchitectureTablesNameEveryOfTheThirtyFiveExceptTheNamedPendingErratum() {
        String contract = read("docs", "02_architecture", "API_Contract_ResearchToPRD.md");
        Set<String> contractMissing = new TreeSet<>();
        for (String reason : ALL_REASONS) {
            if (!contract.contains("`" + reason + "`")) {
                contractMissing.add(reason);
            }
        }
        Map<String, Integer> architecture = architectureReasons();
        Set<String> architectureMissing = new TreeSet<>(ALL_REASONS);
        architectureMissing.removeAll(architecture.keySet());

        assertThat(contractMissing).as("契約 §0.2 缺列的 reason＝名單（勘誤落地後清空名單；缺列者須是 ALL 的子集）").isEqualTo(CONTRACT_ERRATUM_PENDING);
        assertThat(architectureMissing).as("Architecture §11.1 缺列的 reason＝名單（勘誤落地後清空名單）").isEqualTo(ARCHITECTURE_ERRATUM_PENDING);
        assertThat(architecture).as("Architecture 表已列的 P1 reason 的狀態碼").containsEntry("route_conflict", 409).containsEntry("branch_exists", 409)
                .containsEntry("scr_open", 409).containsEntry("scr_limit", 409).containsEntry("decomposition_stale", 409)
                .containsEntry("target_not_empty", 422).containsEntry("public_confirmation_required", 422)
                .containsEntry("route_unsupported_in_deployment", 422);
    }

    @Test
    void AT_961_15_4_everyReasonOfTheThirtyFiveIsNamedInTheOpenApiDescriptionsAndEveryP1ReasonByAtLeastOneP1Operation() {
        String docs = documentation();
        for (String reason : ALL_REASONS) {
            assertThat(docs).as("OpenAPI 說明提到 reason " + reason).contains(reason);
        }
        List<String> p1Operations = new ArrayList<>();
        ResearchErrorDocs.CONFLICT.forEach((key, text) -> {
            if (key.contains("/route") || key.contains("/scr") || key.contains("/decomposition")) {
                p1Operations.add(text);
            }
        });
        ResearchErrorDocs.EXTRA.forEach((key, codes) -> {
            if (key.contains("/route") || key.contains("/scr") || key.contains("/decomposition")) {
                p1Operations.addAll(codes.values());
            }
        });
        String p1Docs = String.join("\n", p1Operations);
        for (String reason : P1_REASONS) {
            assertThat(p1Docs).as("P1 端點的說明提到 P1 reason " + reason).contains(reason);
        }
    }

    @Test
    void AT_960_5_6_everyP0ReasonIsNamedInTheOpenApiDescriptions() {
        String docs = documentation();

        for (String reason : P0_REASONS) {
            assertThat(docs).as("OpenAPI 說明提到 reason " + reason).contains(reason);
        }
    }

    @Test
    void AT_960_5_6_everyResearchNotFoundDescriptionIsMarkedAsAnExceptionToTheOmittedReasonConvention() {
        assertThat(ResearchErrorDocs.NOT_FOUND).contains("research_not_found").contains("「404 的 reason 省略」慣例的例外");
    }

    @Test
    void AT_960_5_6_theReasonRetiredByD72IsNowhereToBeFound() {
        String contract = read("docs", "02_architecture", "API_Contract_ResearchToPRD.md");
        String docs = documentation();
        Set<String> backend = backendReasons();
        Set<String> frontend = frontendReasons();
        Set<String> architecture = architectureReasons().keySet();

        for (String reason : RETIRED_REASONS) {
            assertThat(backend).as("後端常數不再有 " + reason).doesNotContain(reason);
            assertThat(frontend).as("前端 RESEARCH_REASONS 不再有 " + reason).doesNotContain(reason);
            assertThat(architecture).as("Architecture §11.1 的研究 reason 表不再有 " + reason).doesNotContain(reason);
            assertThat(contract).as("契約不再以反引號列 " + reason + "（勘誤記錄可寫「原 " + reason + "」不加反引號）").doesNotContain("`" + reason + "`");
            assertThat(docs).as("OpenAPI 說明不再提到 " + reason + "（說明要照實反映回應）").doesNotContain(reason);
        }
    }

    @Test
    void AT_960_5_6_theResearchReasonsStayOutOfTheSharedReasonsTableOfTheFrozenContract() {
        String shared = read("frontend", "lib", "api", "reasons.ts");
        for (String reason : P0_REASONS) {
            assertThat(shared).as("lib/api/reasons.ts 不含研究 reason " + reason).doesNotContain("\"" + reason + "\"");
        }
    }
}
