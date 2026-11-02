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
 * 研究 reason 的三方雙向鎖（TCS-ResearchToPRD-P0 AT-960-5-6；契約 API_Contract_ResearchToPRD §0.2、Architecture §11.1 的研究 reason 表、前端 {@code lib/domain/research.ts} 的
 * {@code RESEARCH_REASONS}）。為什麼重要：reason 是前端據以顯示說明與決定可否重試的機器可讀欄位——後端改了字面而前端、契約沒跟著改，使用者看到的是「未知錯誤」；
 * 而 {@code lib/api/reasons.ts} 的 {@code REASONS} 與凍結契約附錄 B 雙向鎖，研究 reason 不得進去（所以它們各住自己的常數）。
 *
 * <p><b>已知待補列</b>：PKG-BR-A 的 Bridge 新增三個 reason——{@code allowlist_exists}（409）、{@code init_failed}（502）、{@code not_implemented}（501→502）——
 * 契約 §0.2／§3 與前端常數尚未列入（勘誤候選「契約 §3 reason 清單補列」）。它們已在後端 {@code ErrorReasons} 與 OpenAPI 說明，所以本測試把它們明載在 {@link #PENDING_ERRATUM}：
 * 後端集合＝P0 十八個＋這三個；契約與前端兩處的集合＝十八個。契約與前端補列之後，本名單必須清空（否則第 {@code AT_960_5_6_pendingReasonsAreStillMissing…} 條轉紅，逼著同步）。
 */
class ResearchReasonsTest {

    /** TCS §3 AT-960-5-6 的 P0 十八個 reason（三處集合必須相等）。 */
    private static final Set<String> P0_REASONS = new TreeSet<>(List.of("research_write_disabled", "research_write_forbidden", "research_requires_db",
            "db_blocked", "research_not_found", "slug_in_use", "stage_conflict", "prd_version_conflict", "review_not_passed", "spec_digest_changed",
            "fsm_state_conflict", "escalated", "spec_frozen", "layer_unavailable", "sanitization_failed", "terms_ack_required", "bridge_unreachable",
            "bridge_timeout"));
    /** Bridge 專屬、契約與前端尚未列入的三個 reason（見類別說明）。 */
    private static final Set<String> PENDING_ERRATUM = new TreeSet<>(List.of("allowlist_exists", "init_failed", "not_implemented"));
    /**
     * Architecture §11.1 的研究 reason 表目前沒有列的兩個 P0 reason（502、504 的連線類失敗；契約 §0.2 第 8 列有）——已知的文件缺口、勘誤候選：
     * 該表是「依端點的業務失敗」清單，連線類失敗沒有進去。補進 Architecture 後本名單必須清空。
     */
    private static final Set<String> ARCHITECTURE_GAP = new TreeSet<>(List.of("bridge_unreachable", "bridge_timeout"));

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
    void AT_960_5_6_theBackendConstantsAreTheEighteenP0ReasonsPlusTheThreeKnownPendingBridgeReasons() {
        Set<String> backend = backendReasons();

        assertThat(P0_REASONS).hasSize(18);
        assertThat(backend).containsAll(P0_REASONS).containsAll(PENDING_ERRATUM);
        Set<String> extra = new TreeSet<>(backend);
        extra.removeAll(P0_REASONS);
        assertThat(extra).as("後端的 RESEARCH_ 常數除十八個 P0 reason 外，只有已知待補列的三個").isEqualTo(PENDING_ERRATUM);
    }

    @Test
    void AT_960_5_6_theFrontendConstantsAndTheContractTableEqualTheEighteenP0Reasons() {
        assertThat(frontendReasons()).as("前端 RESEARCH_REASONS").isEqualTo(P0_REASONS);

        String contract = read("docs", "02_architecture", "API_Contract_ResearchToPRD.md");
        for (String reason : P0_REASONS) {
            assertThat(contract).as("契約提到 reason " + reason).contains("`" + reason + "`");
        }
        Map<String, Integer> architecture = architectureReasons();
        Set<String> inArchitecture = new TreeSet<>(P0_REASONS);
        inArchitecture.removeAll(ARCHITECTURE_GAP);
        assertThat(architecture.keySet()).as("Architecture §11.1 的研究 reason 表（缺 bridge_unreachable、bridge_timeout 是已知的文件缺口，勘誤候選）")
                .containsAll(inArchitecture);
        assertThat(architecture.keySet()).as("缺口名單只在還缺時才列：補進 Architecture 之後要從 ARCHITECTURE_GAP 移除").doesNotContainAnyElementsOf(ARCHITECTURE_GAP);
        assertThat(architecture).containsEntry("research_write_disabled", 503).containsEntry("research_write_forbidden", 403)
                .containsEntry("research_not_found", 404).containsEntry("slug_in_use", 409).containsEntry("layer_unavailable", 400)
                .containsEntry("sanitization_failed", 422).containsEntry("terms_ack_required", 422);
    }

    @Test
    void AT_960_5_6_everyP0ReasonAndEveryPendingReasonIsNamedInTheOpenApiDescriptions() {
        String docs = documentation();

        for (String reason : P0_REASONS) {
            assertThat(docs).as("OpenAPI 說明提到 reason " + reason).contains(reason);
        }
        for (String reason : PENDING_ERRATUM) {
            assertThat(docs).as("OpenAPI 說明提到 Bridge 專屬 reason " + reason).contains(reason);
        }
    }

    @Test
    void AT_960_5_6_everyResearchNotFoundDescriptionIsMarkedAsAnExceptionToTheOmittedReasonConvention() {
        assertThat(ResearchErrorDocs.NOT_FOUND).contains("research_not_found").contains("「404 的 reason 省略」慣例的例外");
    }

    @Test
    void AT_960_5_6_thePendingReasonsAreStillMissingFromTheContractAndTheFrontendSoThisListMustShrinkWhenTheErratumLands() {
        String contract = read("docs", "02_architecture", "API_Contract_ResearchToPRD.md");
        for (String reason : PENDING_ERRATUM) {
            boolean inContract = contract.contains("`" + reason + "`");
            boolean inFrontend = frontendReasons().contains(reason);
            assertThat(inContract || inFrontend).as("%s 已進契約或前端：把它從 PENDING_ERRATUM 移到 P0_REASONS（三處同改）", reason).isFalse();
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
