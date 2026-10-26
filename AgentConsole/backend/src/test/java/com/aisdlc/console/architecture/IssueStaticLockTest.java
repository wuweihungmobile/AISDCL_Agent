package com.aisdlc.console.architecture;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 議題中心新檔的靜態鎖（TCS-IssueCenter-20261027 R-IC-72、R-IC-73；AT-IC-06-2-4、AT-IC-06-2-E-3、AT-IC-10-3-2）。掃描面只有 {@code src/main/java} 下檔名以
 * {@code Issue} 起頭的 {@code .java} 檔（測試檔與既有 {@code Si*} 檔都不在內）。
 *
 * <p>兩道鎖各守一個「單一真相」：
 * <ul>
 *   <li><b>單一真相</b>：議題的七狀態對照表只住根層 {@code issuemap.py}；後端新檔不得自己持有一份狀態詞清單——判準＝同一個檔不得含 ≥4 個<b>不同</b>的狀態名
 *       （同一個詞出現幾次都只算一個）。詞表<b>現讀</b>黃金檔 {@code si/A.camel.json} 的 {@code issues.legend.statuses[].name}，測試不另抄一份。</li>
 *   <li><b>寫入面</b>：議題中心唯一的寫入是 PUT 優先順序；對 SelfImproving 寫入端點的任何呼叫都不該出現在 {@code Issue*.java}——沒有 {@code siWrite…}／預檢呼叫、
 *       沒有 {@code /si/} 的寫入路徑字面（唯一允許的 {@code /si/} 字面是讀路徑 {@code /si/issues}）、沒有 {@code si decide}、{@code obs-close} 字樣。</li>
 * </ul>
 * 兩個掃描函式都是純函式（輸入原始碼文字、輸出違規清單），自帶負控：違規樣本各回非空、良性樣本回空。
 */
class IssueStaticLockTest {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Pattern WRITE_SHAPES = Pattern.compile(
            "siWrite\\w*|siValidateObservation|postSiDecide|postSiObservation\\w*|/si/(?!issues\\b)|si decide|obs-close|obs-add");

    // ── 掃描函式 ────────────────────────────────────────────────────────────────────────────

    /** 該檔含幾個不同的狀態名；≥4 即違規（回非空清單）。 */
    static List<String> stateKeyViolations(String path, String source, Set<String> words) {
        Set<String> present = new LinkedHashSet<>();
        for (String word : words) {
            if (source.contains(word)) {
                present.add(word);
            }
        }
        List<String> out = new ArrayList<>();
        if (present.size() >= 4) {
            out.add(path + " 含 " + present.size() + " 個不同的狀態名：" + present);
        }
        return out;
    }

    /** 對 SelfImproving 寫入端點的呼叫形跡（{@code /si/issues} 讀路徑不算）。 */
    static List<String> writeCallViolations(String path, String source) {
        List<String> out = new ArrayList<>();
        var matcher = WRITE_SHAPES.matcher(source);
        while (matcher.find()) {
            out.add(path + " 含寫入面形跡：" + matcher.group());
        }
        return out;
    }

    /** 黃金檔的七個狀態名（現讀；不在測試裡另抄）。 */
    static Set<String> statusWords() {
        try (InputStream in = IssueStaticLockTest.class.getResourceAsStream("/si/A.camel.json")) {
            assertThat(in).as("測試資源 si/A.camel.json").isNotNull();
            JsonNode statuses = JSON.readTree(new String(in.readAllBytes(), StandardCharsets.UTF_8)).get("issues").get("legend").get("statuses");
            Set<String> words = new LinkedHashSet<>();
            statuses.forEach(status -> words.add(status.get("name").asString()));
            return words;
        } catch (IOException e) {
            throw new java.io.UncheckedIOException(e);
        }
    }

    /** {@code src/main/java} 下檔名以 {@code Issue} 起頭的 {@code .java} 檔：相對路徑（正斜線）→ 原文（註解不去除：註解裡寫出一份詞表也算持有）。 */
    private static Map<String, String> issueSources() {
        Path root = Path.of("src", "main", "java");
        Map<String, String> sources = new TreeMap<>();
        try (Stream<Path> files = Files.walk(root)) {
            for (Path path : files.filter(p -> p.getFileName().toString().startsWith("Issue") && p.toString().endsWith(".java")).toList()) {
                sources.put(root.relativize(path).toString().replace('\\', '/'), Files.readString(path, StandardCharsets.UTF_8));
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return sources;
    }

    // ── AT-IC-06-2-4 ───────────────────────────────────────────────────────────────────────

    @Test
    void AT_IC_06_2_4_noIssueSourceFileHoldsItsOwnStateWordList() {
        Set<String> words = statusWords();
        Map<String, String> sources = issueSources();

        assertThat(words).as("詞表現讀黃金檔：七個狀態名").hasSize(7);
        assertThat(sources.keySet()).as("防反空轉：掃到議題中心的主程式檔").anyMatch(p -> p.endsWith("/IssueController.java"))
                .anyMatch(p -> p.endsWith("/IssuePriorityService.java")).anyMatch(p -> p.endsWith("/IssuePriorityAdapter.java"));
        List<String> violations = new ArrayList<>();
        sources.forEach((path, text) -> violations.addAll(stateKeyViolations(path, text, words)));
        assertThat(violations).as("Issue*.java 不得含 ≥4 個不同的狀態名").isEmpty();
    }

    // ── AT-IC-06-2-E-3：掃描器自帶負控 ──────────────────────────────────────────────────────

    @Test
    void AT_IC_06_2_E_3_theStateWordScannerFlagsFourDistinctWordsAndOnlyThose() {
        Set<String> words = statusWords();
        List<String> list = List.copyOf(words);

        String fourDistinct = String.join(" ", list.subList(0, 4));
        String threeDistinct = String.join(" ", list.subList(0, 3));
        String oneWordFourTimes = (list.get(0) + " ").repeat(4);

        assertThat(stateKeyViolations("四個不同的詞.java", fourDistinct, words)).as("含 4 個不同狀態名的樣本").isNotEmpty();
        assertThat(stateKeyViolations("全七個.java", String.join(" ", list), words)).as("含全部 7 個").isNotEmpty();
        assertThat(stateKeyViolations("三個不同的詞.java", threeDistinct, words)).as("含 3 個不同狀態名").isEmpty();
        assertThat(stateKeyViolations("同一個詞四次.java", oneWordFourTimes, words)).as("同一個詞重複 4 次不算（不同鍵才算）").isEmpty();
        assertThat(stateKeyViolations("無關.java", "class A { }", words)).isEmpty();
    }

    // ── AT-IC-10-3-2 ───────────────────────────────────────────────────────────────────────

    @Test
    void AT_IC_10_3_2_noIssueSourceFileCallsAnSiWriteEndpoint() {
        List<String> violations = new ArrayList<>();
        issueSources().forEach((path, text) -> violations.addAll(writeCallViolations(path, text)));

        assertThat(violations).as("沒有 siWrite… 呼叫與 /si/ 寫入路徑字面").isEmpty();
    }

    @Test
    void AT_IC_10_3_E_1_theWriteShapeScannerFlagsWriteSamplesAndLetsTheReadPathThrough() {
        for (String bad : List.of("bridge.siWriteDecide(id, audit);", "bridge.siValidateObservation(body);", "\"/si/proposals/x:decide\"",
                "\"/si/observations\"", "\"/si/observations/OBS:close\"", "si decide PROP", "obs-close", "obs-add", "postSiDecide(")) {
            assertThat(writeCallViolations("樣本.java", bad)).as(bad).isNotEmpty();
        }
        for (String good : List.of("\"/si/issues\"", "\"/si/issues/\" + id", "bridge.siExport(\"issues\", null, null, null, null, null);",
                "// Bridge GET /si/issues", "class IssueX { }")) {
            assertThat(writeCallViolations("樣本.java", good)).as(good).isEmpty();
        }
    }
}
