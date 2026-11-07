package com.aisdlc.console.architecture;

import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static org.assertj.core.api.Assertions.assertThat;

/**
 * 研究面的結構鎖（TCS-ResearchToPRD-P0 AT-960-4-E-1；PRD AC-R2P-02-10；ADR-003 D4）：<b>console-api 對 {@code console.research_*} 零寫入</b>，Bridge 是唯一寫入者。
 * 為什麼用原始碼掃描加 ArchUnit：寫壞了編譯得過、整合測試也許沒測到，卻是資料所有權的承重牆——讀配接器若出現第二個寫入者（哪怕只是一條 UPDATE），
 * 「Bridge 先寫檔、再入庫、事件帳 seq 連續」的保證就不再只由 Bridge 單方維護。掃描函式是純函式（輸入原始碼文字、輸出違規清單）：對真原始碼必須回空、
 * 對合成的違規樣本必須回非空（負控，鎖不得空過）；範圍必須非空（套件被搬走或改名時，掃描不會靜默變成零檔案的假綠）。
 */
class ResearchArchTest {

    private static final String PACKAGE_DIR = "com/aisdlc/console/adapter/out/persistence/research";
    /** 五個寫入類關鍵字，大小寫不分、整字比對（{@code updated_at}、{@code deleted} 這類欄名不是關鍵字）。 */
    private static final Pattern WRITE_WORDS = Pattern.compile("(?i)\\b(insert|update|delete|merge|truncate)\\b");

    // ── 原始碼讀取 ──────────────────────────────────────────────────────────────────────────

    private static Map<String, String> researchPersistenceSources() {
        Path root = Path.of("src", "main", "java", "com", "aisdlc", "console", "adapter", "out", "persistence", "research");
        Map<String, String> out = new TreeMap<>();
        try (Stream<Path> files = Files.walk(root)) {
            for (Path path : files.filter(p -> p.toString().endsWith(".java")).toList()) {
                out.put(PACKAGE_DIR + "/" + root.relativize(path).toString().replace('\\', '/'), Files.readString(path, StandardCharsets.UTF_8));
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return out;
    }

    private static JavaClasses mainClasses() {
        return new ClassFileImporter().withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS).importPackages("com.aisdlc.console");
    }

    // ── 掃描函式（純函式）──────────────────────────────────────────────────────────────────

    /** 原始碼（含註解與字串）中的寫入類關鍵字命中；回「檔名：關鍵字」清單。 */
    static List<String> writeViolations(String file, String source) {
        List<String> out = new ArrayList<>();
        Matcher matcher = WRITE_WORDS.matcher(source);
        while (matcher.find()) {
            out.add(file + "：" + matcher.group().toUpperCase());
        }
        return out;
    }

    // ── AT-960-4-E-1 ───────────────────────────────────────────────────────────────────────

    @Test
    void AT_960_4_E_1_thePersistenceResearchPackageHasZeroWriteStatementsAndTheScanRangeIsNotEmpty() {
        Map<String, String> sources = researchPersistenceSources();

        assertThat(sources).as("掃描範圍非空：四個唯讀配接器與共用的取值小工具").hasSizeGreaterThanOrEqualTo(4);
        assertThat(sources.keySet()).anyMatch(name -> name.endsWith("ResearchProjectReadAdapter.java"))
                .anyMatch(name -> name.endsWith("ResearchEvidenceReadAdapter.java")).anyMatch(name -> name.endsWith("ResearchReviewReadAdapter.java"));
        List<String> violations = new ArrayList<>();
        sources.forEach((name, text) -> violations.addAll(writeViolations(name, text)));
        assertThat(violations).as("INSERT／UPDATE／DELETE／MERGE／TRUNCATE 零命中（原始碼含註解一併掃）").isEmpty();
    }

    @Test
    void AT_960_4_E_1_theScannerHasANegativeControlThatReportsEveryWriteKeywordAndIgnoresColumnNames() {
        assertThat(writeViolations("sample", "jdbc.sql(\"INSERT INTO console.research_events (seq) values (1)\")")).containsExactly("sample：INSERT");
        assertThat(writeViolations("sample", "update console.research_projects set title = 'x'")).containsExactly("sample：UPDATE");
        assertThat(writeViolations("sample", "Delete from t; MERGE into t; truncate t")).containsExactly("sample：DELETE", "sample：MERGE", "sample：TRUNCATE");
        assertThat(writeViolations("sample", "select updated_at, deleted_at from console.research_projects order by updated_at desc"))
                .as("欄名含 update 或 delete 的子字串不是寫入敘述").isEmpty();
    }

    @Test
    void AT_960_4_E_1_thePersistenceResearchPackageDependsOnNoJpaEntityAndReadsOnlyThroughJdbcClient() {
        JavaClasses classes = mainClasses();
        JavaClasses persistence = classes.that(new com.tngtech.archunit.base.DescribedPredicate<JavaClass>("residing in adapter.out.persistence.research") {
            @Override
            public boolean test(JavaClass javaClass) {
                return javaClass.getPackageName().equals("com.aisdlc.console.adapter.out.persistence.research");
            }
        });

        assertThat(persistence).as("套件內有類別").isNotEmpty();
        noClasses().that().resideInAPackage("..adapter.out.persistence.research..")
                .should().dependOnClassesThat().resideInAnyPackage("jakarta.persistence..", "org.hibernate..", "org.springframework.data..",
                        "org.springframework.orm..", "..infrastructure.persistence.entity..", "..infrastructure.persistence.repository..")
                .because("console-api 對 research_* 沒有 JPA 實體，讀取只走 JdbcClient（ADR-003 D4）").check(classes);
        classes().that().resideInAPackage("..adapter.out.persistence.research..").should().notBeAnnotatedWith("jakarta.persistence.Entity")
                .check(classes);
        noClasses().that().resideInAPackage("..adapter.out.persistence.research..")
                .should().dependOnClassesThat().haveFullyQualifiedName("org.springframework.jdbc.core.JdbcTemplate")
                .because("讀取一律經 JdbcClient").check(classes);
        for (String adapter : List.of("ResearchProjectReadAdapter", "ResearchEvidenceReadAdapter", "ResearchReviewReadAdapter")) {
            JavaClass javaClass = classes.get("com.aisdlc.console.adapter.out.persistence.research." + adapter);
            assertThat(javaClass.getDirectDependenciesFromSelf()).as(adapter).anyMatch(
                    dependency -> dependency.getTargetClass().getFullName().equals("org.springframework.jdbc.core.simple.JdbcClient"));
        }
    }

    @Test
    void AT_960_4_E_1_theResearchDomainAndApplicationLayersStayFreeOfFrameworks() {
        JavaClasses classes = mainClasses();
        noClasses().that().resideInAnyPackage("..domain.model.research..", "..domain.service..")
                .should().dependOnClassesThat().resideInAnyPackage("org.springframework..", "jakarta..", "org.hibernate..", "tools.jackson..", "com.fasterxml..",
                        "io.swagger..", "..application..", "..adapter..", "..infrastructure..").check(classes);
        noClasses().that().resideInAPackage("..application..").and().haveSimpleNameStartingWith("Research")
                .should().dependOnClassesThat().resideInAnyPackage("..adapter..", "..infrastructure..").check(classes);
    }

    @Test
    void AT_960_4_E_1_noResearchControllerMapsAnythingButGetPostPutPatchAndNeverDelete() {
        JavaClasses classes = mainClasses();
        noClasses().that().haveSimpleName("ResearchController")
                .should().dependOnClassesThat().haveFullyQualifiedName("org.springframework.web.bind.annotation.DeleteMapping").check(classes);
        classes().that().haveSimpleName("ResearchController").should().beAnnotatedWith("org.springframework.web.bind.annotation.RestController").check(classes);
    }

    @Test
    void AT_961_15_5_theP1ReadAdaptersExistReadOnlyViaJdbcClientAndNoMainSourceWritesAnyV19ResearchTable() throws IOException {
        Map<String, String> sources = researchPersistenceSources();
        for (String adapter : List.of("RouteReadAdapter", "ScrReadAdapter", "DecompositionReadAdapter")) {
            assertThat(sources.keySet()).as("P1 讀配接器 " + adapter).anyMatch(name -> name.endsWith("/" + adapter + ".java"));
            assertThat(sources.entrySet().stream().filter(e -> e.getKey().endsWith("/" + adapter + ".java")).findFirst().orElseThrow().getValue())
                    .contains("JdbcClient").doesNotContain("@Entity").doesNotContain("JdbcTemplate");
        }
        Pattern v19Write = Pattern.compile("(?i)\\b(insert\\s+into|update|delete\\s+from)\\s+console\\.(research_route_decisions|research_route_steps|research_scr|"
                + "research_decompositions|research_deliveries)\\b");
        List<String> hits = new ArrayList<>();
        try (Stream<Path> files = Files.walk(Path.of("src", "main", "java"))) {
            for (Path path : files.filter(p -> p.toString().endsWith(".java")).toList()) {
                if (v19Write.matcher(Files.readString(path, StandardCharsets.UTF_8)).find()) {
                    hits.add(path.toString());
                }
            }
        }
        assertThat(hits).as("console-api 對 V19 五張表的任何寫入語句為 0（只寫自己的 projects 與 audit_log）").isEmpty();
        assertThat(v19Write.matcher("UPDATE console.research_scr set status = 'X'").find()).as("掃描器負控").isTrue();
    }
}
