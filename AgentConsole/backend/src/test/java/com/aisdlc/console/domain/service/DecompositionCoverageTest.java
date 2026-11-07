package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.service.DecompositionCoverage.Waiver;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 拆解覆蓋對映的純函式（PRD AC-R2P-14-2、D-121）。為什麼重要：簽核能不能過全看它——誤判「已覆蓋」＝凍結 PRD 的某個 AC 沒有任何任務卻被簽進正式專案；誤判「未覆蓋」＝使用者被無謂擋下。
 * 優先取 Bridge 寫入的覆蓋（console-api 不重算），沒有時才由 covers_ac 自己算；豁免只在理由非空白、且 AC 確實未覆蓋時才有效。
 */
class DecompositionCoverageTest {

    private static Map<String, Object> task(String... covers) {
        Map<String, Object> task = new LinkedHashMap<>();
        task.put("covers_ac", List.of(covers));
        return task;
    }

    private static Map<String, Object> content(Map<String, Object> coverage, List<Map<String, Object>> tasks, List<String> universe) {
        Map<String, Object> content = new LinkedHashMap<>();
        if (coverage != null) {
            content.put("coverage", coverage);
        }
        if (universe != null) {
            content.put("ac_universe", universe);
        }
        content.put("goals", List.of(Map.of("tasks", tasks)));
        return content;
    }

    @Test
    void theBridgeWrittenCoverageIsTakenAsIsAndNoContentMeansAllZero() {
        DecompositionCoverage.Result r = DecompositionCoverage.of(content(Map.of("total", 3, "covered", 2, "uncovered", List.of("AC-3")), List.of(), null));

        assertThat(r.total()).isEqualTo(3);
        assertThat(r.covered()).isEqualTo(2);
        assertThat(r.uncovered()).containsExactly("AC-3");
        assertThat(DecompositionCoverage.of(null)).isEqualTo(new DecompositionCoverage.Result(0, 0, List.of()));
    }

    @Test
    void withoutABridgeCoverageItIsComputedFromTheTasksCoversAcAgainstTheUniverse() {
        DecompositionCoverage.Result r = DecompositionCoverage.of(content(null, List.of(task("AC-1"), task("AC-2", "AC-1")), List.of("AC-1", "AC-2", "AC-3")));

        assertThat(r.total()).isEqualTo(3);
        assertThat(r.covered()).isEqualTo(2);
        assertThat(r.uncovered()).containsExactly("AC-3");
        DecompositionCoverage.Result noUniverse = DecompositionCoverage.of(content(null, List.of(task("AC-1")), null));
        assertThat(noUniverse.uncovered()).as("沒有全集時以已涵蓋者為全集：不可能有未覆蓋").isEmpty();
    }

    @Test
    void aWaiverCountsOnlyWithANonBlankReasonAndBlanksOrUnknownAcsDoNotHideAnything() {
        DecompositionCoverage.Result r = new DecompositionCoverage.Result(3, 1, List.of("AC-2", "AC-3"));

        assertThat(DecompositionCoverage.stillUncovered(r, List.of(new Waiver("AC-2", "本期不做")))).containsExactly("AC-3");
        assertThat(DecompositionCoverage.stillUncovered(r, List.of(new Waiver("AC-2", "  "), new Waiver("AC-9", "不存在的 AC")))).as("空白理由無效；未列入的 AC 被忽略")
                .containsExactly("AC-2", "AC-3");
        assertThat(DecompositionCoverage.stillUncovered(r, List.of(new Waiver("AC-2", "a"), new Waiver("AC-3", "b")))).isEmpty();
        assertThat(DecompositionCoverage.stillUncovered(r, null)).containsExactly("AC-2", "AC-3");
    }
}
