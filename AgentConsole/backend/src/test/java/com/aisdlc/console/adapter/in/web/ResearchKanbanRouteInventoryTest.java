package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractResearchIT;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.servlet.mvc.method.RequestMappingInfo;
import org.springframework.web.servlet.mvc.method.annotation.RequestMappingHandlerMapping;

import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 看板路由盤點（AT-962-10-E-1）。為什麼重要：看板只是投影，不得變成第二套執行控制——一旦研究路徑下長出 execute／pause／resume／cancel／stop／restore／review，
 * 內環的守衛（簽核、SCR 唯讀、stale 拆解）就被繞過。以 {@code RequestMappingHandlerMapping} 的實際路由為準，不靠原始碼字串。
 */
class ResearchKanbanRouteInventoryTest extends AbstractResearchIT {

    private static final Pattern FORBIDDEN = Pattern.compile("(?i)(execute|pause|resume|stop)");
    private static final Set<String> P2_PATHS = Set.of("kanban", "gates", "healing", "delivery", "delivery/tag", "delivery/pr", "delivery/traceability");

    @Autowired
    @org.springframework.beans.factory.annotation.Qualifier("requestMappingHandlerMapping")
    private RequestMappingHandlerMapping mapping;

    private List<String> researchPaths() {
        return mapping.getHandlerMethods().keySet().stream().flatMap(info -> patterns(info).stream())
                .filter(p -> p.startsWith("/api/v1/research/")).distinct().sorted().toList();
    }

    private static Set<String> patterns(RequestMappingInfo info) {
        return info.getPathPatternsCondition() == null ? Set.of()
                : new TreeSet<>(info.getPathPatternsCondition().getPatterns().stream().map(p -> p.getPatternString()).toList());
    }

    /** 掃描函式（純）：回含禁用片段的路徑。 */
    static List<String> violations(List<String> paths) {
        return paths.stream().filter(p -> FORBIDDEN.matcher(p.replaceFirst("^/api/v1/research/", "")).find()).toList();
    }

    @Test
    void AT_962_10_E_1_noResearchRouteCarriesAnExecutionRunControlSegmentAndTheP2AdditionsAreExactlySeven() {
        List<String> paths = researchPaths();
        assertThat(paths).as("盤點範圍非空").isNotEmpty();
        assertThat(violations(paths)).as("研究路徑沒有 execute／pause／resume／stop 片段（cancel、restore 是 P0 起即有的研究專案生命週期端點，不是 run 控制）").isEmpty();
        assertThat(paths.stream().filter(p -> P2_PATHS.stream().anyMatch(s -> p.endsWith("/" + s)))).as("P2 新路徑一律不含 cancel／restore／review 片段")
                .noneMatch(p -> Pattern.compile("(?i)(cancel|restore|review)").matcher(p).find());
        String prefix = "/api/v1/research/projects/{id}/";
        Set<String> found = new TreeSet<>(P2_PATHS.stream().filter(p -> paths.contains(prefix + p)).toList());
        assertThat(found).as("P2 新增路徑恰為七條").isEqualTo(new TreeSet<>(P2_PATHS));
        assertThat(violations(List.of("/api/v1/research/projects/{id}/execute"))).as("負控夾具被判違規").hasSize(1);
        assertThat(violations(List.of("/api/v1/research/projects/{id}/kanban"))).isEmpty();
    }
}
