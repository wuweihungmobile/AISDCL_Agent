package com.aisdlc.console.architecture;

import com.aisdlc.console.application.port.out.IssuePriorityRepository;
import com.aisdlc.console.application.service.IssuePriorityService;
import com.tngtech.archunit.core.domain.JavaAccess;
import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.domain.JavaMethod;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import org.junit.jupiter.api.Test;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PutMapping;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 優先順序表的寫入面結構鎖（TCS-IssueCenter-20261027 R-IC-53、R-IC-59、B-18 的結構半；AT-IC-09-8-1、AT-IC-09-8-E-1）。
 * 為什麼用 ArchUnit 與原始碼掃描：{@code console.issue_priority} 是 Console 在議題中心唯一自有的資料，它的寫入面要小到可以一眼審——資料庫端恰兩條寫入敘述
 * （UPSERT、DELETE；沒有獨立的 UPDATE）、只有一個 persistence adapter 觸及該表、{@code IssueController} 恰一個 {@code @PutMapping} 與一個
 * {@code @DeleteMapping}、只有 {@code IssuePriorityService} 呼叫寫入埠的方法。日後有人加了第三條敘述、第二個存取該表的類別或第二個寫入映射，編譯得過、整合測試
 * 也許沒測到，但這支會先紅。掃描函式是純函式（輸入原始碼文字、輸出違規清單），對真原始碼必須回空、對合成的違規樣本必須回非空（AT-IC-09-8-E-1 的負控）。
 */
class IssuePriorityArchTest {

    private static final String TABLE = "issue_priority";
    private static final String ADAPTER = "com/aisdlc/console/adapter/out/persistence/IssuePriorityAdapter.java";
    private static final String CONTROLLER = "com/aisdlc/console/adapter/in/web/IssueController.java";

    // ── 原始碼讀取（去註解；SiReadOnlyArchTest 自帶同義的私有版本，沿用這個做法）─────────────────────────

    private static Map<String, String> mainSources() {
        Path root = Path.of("src", "main", "java");
        Map<String, String> out = new TreeMap<>();
        try (Stream<Path> files = Files.walk(root)) {
            for (Path path : files.filter(p -> p.toString().endsWith(".java")).toList()) {
                out.put(root.relativize(path).toString().replace('\\', '/'), stripComments(Files.readString(path, StandardCharsets.UTF_8)));
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return out;
    }

    /** 去掉 Java 的行註解與區塊註解（字串字面值內的 {@code //} 不算註解）。 */
    private static String stripComments(String source) {
        StringBuilder out = new StringBuilder();
        int i = 0;
        int n = source.length();
        while (i < n) {
            char c = source.charAt(i);
            if (c == '"') {
                int j = i + 1;
                while (j < n && source.charAt(j) != '"') {
                    j += source.charAt(j) == '\\' ? 2 : 1;
                }
                out.append(source, i, Math.min(n, j + 1));
                i = j + 1;
            } else if (c == '/' && i + 1 < n && source.charAt(i + 1) == '/') {
                while (i < n && source.charAt(i) != '\n') {
                    i++;
                }
            } else if (c == '/' && i + 1 < n && source.charAt(i + 1) == '*') {
                int end = source.indexOf("*/", i + 2);
                i = end < 0 ? n : end + 2;
            } else {
                out.append(c);
                i++;
            }
        }
        return out.toString();
    }
    // ── 掃描函式（純函式）──────────────────────────────────────────────────────────────────────

    /** 存取表的類別（註解之外的原始碼提及）必須恰為那一個 persistence adapter。 */
    static List<String> tableAccessViolations(Map<String, String> strippedSources) {
        List<String> touching = strippedSources.entrySet().stream().filter(e -> e.getValue().contains(TABLE)).map(Map.Entry::getKey).sorted().toList();
        List<String> out = new ArrayList<>();
        if (!touching.equals(List.of(ADAPTER))) {
            out.add("存取 " + TABLE + " 的類別必須恰為 " + ADAPTER + "，實際：" + touching);
        }
        return out;
    }

    private static int count(String text, String regex) {
        Matcher matcher = Pattern.compile(regex).matcher(text);
        int count = 0;
        while (matcher.find()) {
            count++;
        }
        return count;
    }

    /** 配接器的資料庫敘述：寫入恰兩條（UPSERT＝帶 ON CONFLICT 的 INSERT、DELETE），沒有獨立的 UPDATE、TRUNCATE、MERGE，另有唯讀 SELECT。 */
    static List<String> dmlViolations(String strippedAdapter) {
        List<String> out = new ArrayList<>();
        String table = "console\\." + TABLE;
        int inserts = count(strippedAdapter, "(?is)\\binsert\\s+into\\s+" + table + "\\b");
        int upserts = count(strippedAdapter, "(?is)\\binsert\\s+into\\s+" + table + "\\b.*?\\bon\\s+conflict\\s*\\(\\s*issue_id\\s*\\)\\s*do\\s+update\\s+set\\b");
        int updates = count(strippedAdapter, "(?is)\\bupdate\\s+" + table + "\\b");
        int deletes = count(strippedAdapter, "(?is)\\bdelete\\s+from\\s+" + table + "\\b");
        int selects = count(strippedAdapter, "(?is)\\bselect\\b[^;\"]*\\bfrom\\s+" + table + "\\b");
        if (inserts != 1 || upserts != 1) {
            out.add("INSERT（UPSERT）必須恰一條且帶 on conflict (issue_id) do update：insert=" + inserts + "、upsert=" + upserts);
        }
        if (updates != 0) {
            out.add("不得有獨立的 UPDATE 敘述（只有 UPSERT 的 do update）：" + updates);
        }
        if (deletes != 1) {
            out.add("DELETE 必須恰一條：" + deletes);
        }
        if (selects < 1) {
            out.add("必須有唯讀 SELECT：" + selects);
        }
        String lower = strippedAdapter.toLowerCase(java.util.Locale.ROOT);
        for (String banned : List.of("truncate", "merge into", "drop table", "alter table")) {
            if (lower.contains(banned)) {
                out.add("不得出現 " + banned);
            }
        }
        int dml = count(strippedAdapter, "(?is)\\b(insert\\s+into|update|delete\\s+from)\\s+" + table + "\\b");
        if (dml != 2) {
            out.add("寫入敘述總數必須恰為 2（UPSERT、DELETE）：" + dml);
        }
        return out;
    }

    /** 控制器的映射：恰一個 {@code @PutMapping}、一個 {@code @DeleteMapping}，沒有 {@code @PostMapping}、{@code @PatchMapping}。 */
    static List<String> mappingViolations(String strippedController) {
        List<String> out = new ArrayList<>();
        int puts = count(strippedController, "@PutMapping\\b");
        int deletes = count(strippedController, "@DeleteMapping\\b");
        if (puts != 1) {
            out.add("@PutMapping 必須恰一個：" + puts);
        }
        if (deletes != 1) {
            out.add("@DeleteMapping 必須恰一個：" + deletes);
        }
        for (String banned : List.of("@PostMapping", "@PatchMapping")) {
            if (strippedController.contains(banned)) {
                out.add("不得有 " + banned);
            }
        }
        return out;
    }

    // ── AT-IC-09-8-1：真原始碼與真類別都合規 ──────────────────────────────────────────────────

    @Test
    void AT_IC_09_8_1_theTableIsReachedByOneAdapterThroughTwoWritePathsAndTheControllerHasOnePutAndOneDelete() {
        Map<String, String> sources = mainSources();
        assertThat(sources).as("防反空轉：掃描到配接器與控制器").containsKeys(ADAPTER, CONTROLLER);

        assertThat(tableAccessViolations(sources)).as("只有一個 persistence adapter 觸及該表").isEmpty();
        assertThat(dmlViolations(sources.get(ADAPTER))).as("寫入敘述恰兩條（UPSERT、DELETE），另有唯讀 SELECT").isEmpty();
        assertThat(mappingViolations(sources.get(CONTROLLER))).as("恰一個 @PutMapping 與一個 @DeleteMapping").isEmpty();

        JavaClasses classes = new ClassFileImporter().withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importPackages("com.aisdlc.console");
        JavaClass controller = classes.get("com.aisdlc.console.adapter.in.web.IssueController");
        List<JavaMethod> methods = controller.getMethods().stream().toList();
        assertThat(methods.stream().filter(m -> m.isAnnotatedWith(PutMapping.class)).count()).as("ArchUnit：@PutMapping 恰一個").isEqualTo(1);
        assertThat(methods.stream().filter(m -> m.isAnnotatedWith(DeleteMapping.class)).count()).as("ArchUnit：@DeleteMapping 恰一個").isEqualTo(1);

        Set<String> portMethods = Arrays.stream(IssuePriorityRepository.class.getDeclaredMethods()).map(Method::getName)
                .collect(Collectors.toCollection(TreeSet::new));
        assertThat(portMethods).as("寫入埠的方法").containsExactlyInAnyOrder("findByIssueIds", "upsert", "delete");
        Set<String> writers = classes.stream().flatMap(c -> c.getAccessesFromSelf().stream())
                .filter(a -> a.getTargetOwner().getName().equals(IssuePriorityRepository.class.getName()))
                .filter(a -> a.getTarget().getName().equals("upsert") || a.getTarget().getName().equals("delete"))
                .map(JavaAccess::getOriginOwner).map(JavaClass::getSimpleName).collect(Collectors.toCollection(TreeSet::new));
        assertThat(writers).as("只有 IssuePriorityService 呼叫 upsert、delete").containsExactly(IssuePriorityService.class.getSimpleName());
    }

    // ── AT-IC-09-8-E-1：掃描器自帶負控 ──────────────────────────────────────────────────────

    @Test
    void AT_IC_09_8_E_1_theScannersFlagAThirdWriteStatementASecondAdapterAndASecondPutMapping() {
        Map<String, String> sources = mainSources();
        String adapter = sources.get(ADAPTER);
        String controller = sources.get(CONTROLLER);

        String thirdStatement = adapter.replace("@Override\n    public void delete(", "public void rename(String a) {\n"
                + "        jdbc.update(\"update console.issue_priority set note = ? where issue_id = ?\", a, a);\n    }\n\n"
                + "    @Override\n    public void delete(");
        assertThat(thirdStatement).as("負控樣本必須真的改了原始碼").isNotEqualTo(adapter);
        assertThat(dmlViolations(thirdStatement)).as("第三條寫入敘述（UPDATE）").isNotEmpty();
        assertThat(dmlViolations(adapter.replace("on conflict (issue_id) do update set", "on conflict do nothing --")))
                .as("UPSERT 被改成沒有 do update").isNotEmpty();
        assertThat(dmlViolations(adapter + "\n\"truncate table console.issue_priority\"")).as("TRUNCATE").isNotEmpty();

        Map<String, String> twoAdapters = new java.util.TreeMap<>(sources);
        twoAdapters.put("com/aisdlc/console/adapter/out/persistence/AnotherAdapter.java",
                "class AnotherAdapter { String q = \"select * from console.issue_priority\"; }");
        assertThat(tableAccessViolations(twoAdapters)).as("第二個存取該表的類別").isNotEmpty();
        Map<String, String> noAdapter = new java.util.TreeMap<>(sources);
        noAdapter.remove(ADAPTER);
        assertThat(tableAccessViolations(noAdapter)).as("沒有任何類別存取該表同樣是違規（鎖不得空過）").isNotEmpty();

        String twoPuts = controller.replace("@DeleteMapping(\"/{id}/priority\")", "@PutMapping(\"/{id}/other\")\n    @DeleteMapping(\"/{id}/priority\")");
        assertThat(twoPuts).isNotEqualTo(controller);
        assertThat(mappingViolations(twoPuts)).as("第二個 @PutMapping").isNotEmpty();
        assertThat(mappingViolations(controller + "\n@PostMapping")).as("多一個 @PostMapping").isNotEmpty();
        assertThat(mappingViolations(controller.replace("@DeleteMapping(\"/{id}/priority\")", ""))).as("少一個 @DeleteMapping").isNotEmpty();
    }
}
