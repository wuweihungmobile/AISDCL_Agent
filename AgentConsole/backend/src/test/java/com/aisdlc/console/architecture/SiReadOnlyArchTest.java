package com.aisdlc.console.architecture;

import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.SiConsoleWriteQueries;
import com.aisdlc.console.application.port.out.SiConsoleWriteRepository;
import com.aisdlc.console.application.service.SiConsoleWriteService;
import com.aisdlc.console.application.service.SiMirrorQueryService;
import com.aisdlc.console.application.service.SiReconcileService;
import com.aisdlc.console.domain.model.si.SiExport;
import com.tngtech.archunit.core.domain.JavaAccess;
import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.domain.JavaMethod;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.lang.ArchRule;
import org.junit.jupiter.api.Test;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestMapping;

import java.io.IOException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SelfImproving 寫入面的結構鎖（TCS-SelfImprovingMirror-P1b R7、R10；TCS-SelfImprovingDecide-P2b AT-935-3-1、AT-950-8-2）。
 * 為什麼用 ArchUnit：P1b 的前提是「Console 對 SelfImproving 零寫入」；P2b 把它改寫為「帳本只有根層 CLI 能寫，Console 只產生並落地經簽章的稽核 JSON」——
 * 行為面由整合測試覆蓋（DELETE、PUT、PATCH 一律 403／405），這裡鎖<b>結構</b>：日後有人加了第五個 POST、加了刪除映射、在 {@code AgentBridge}
 * 上多開一個 {@code si} 起頭的呼叫、或讓別的類別碰寫入埠與稽核表，編譯得過、整合測試也許沒測到，但這支會在最便宜的地方先紅。
 */
class SiReadOnlyArchTest {

    private static final String WEB = "com.aisdlc.console.adapter.in.web";
    private static final String TABLE = "si_console_writes";

    private static JavaClasses mainClasses() {
        return new ClassFileImporter().withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importPackages("com.aisdlc.console");
    }

    /** 對 {@code target} 型別的任何存取（方法呼叫、方法參照、建構子呼叫、欄位存取）的起點類別簡名。 */
    private static Set<String> accessorsOf(JavaClasses classes, Class<?> target, java.util.function.Predicate<JavaAccess<?>> filter) {
        return classes.stream().flatMap(c -> c.getAccessesFromSelf().stream())
                .filter(a -> a.getTargetOwner().getName().equals(target.getName())).filter(filter)
                .map(a -> a.getOriginOwner().getSimpleName()).collect(Collectors.toCollection(TreeSet::new));
    }

    // ── AT-935-3-1：映射、AgentBridge 的 si 方法、寫入只經 SiConsoleWriteService ────────────────────────

    @Test
    void AT_935_3_1_siControllersHaveSevenGetsAndFourPostsAndOnlyTheWriteServiceTouchesTheWritePorts() {
        JavaClasses classes = mainClasses();
        // Si*Controller：Si 之後不接小寫字母（SignoffController 是別的功能，不在這條鎖的範圍）
        List<JavaClass> controllers = classes.stream()
                .filter(c -> c.getPackageName().equals(WEB) && c.getSimpleName().matches("Si(?![a-z]).*Controller")).toList();
        assertThat(controllers).as("防反空轉：至少有 SiController").extracting(JavaClass::getSimpleName).contains("SiController");

        for (JavaClass controller : controllers) {
            controller.tryGetAnnotationOfType(RequestMapping.class)
                    .ifPresent(mapping -> assertThat(mapping.method()).as("%s 的 @RequestMapping 不得帶 method", controller.getName())
                            .isEmpty());
            for (JavaMethod method : controller.getMethods()) {
                String label = controller.getSimpleName() + "." + method.getName();
                assertThat(method.isAnnotatedWith(PutMapping.class)).as("%s 不得有 @PutMapping", label).isFalse();
                assertThat(method.isAnnotatedWith(PatchMapping.class)).as("%s 不得有 @PatchMapping", label).isFalse();
                assertThat(method.isAnnotatedWith(DeleteMapping.class)).as("%s 不得有 @DeleteMapping", label).isFalse();
                method.tryGetAnnotationOfType(RequestMapping.class)
                        .ifPresent(mapping -> assertThat(mapping.method()).as("%s 的 @RequestMapping 不得帶 method", label).isEmpty());
            }
        }
        List<JavaMethod> methods = controllers.stream().flatMap(c -> c.getMethods().stream()).toList();
        assertThat(methods.stream().filter(m -> m.isAnnotatedWith(GetMapping.class)).count())
                .as("恰七個 @GetMapping（status、observations、events、proposals、proposals/{id}、runs、console-writes）").isEqualTo(7);
        assertThat(methods.stream().filter(m -> m.isAnnotatedWith(PostMapping.class)).count())
                .as("恰四個 @PostMapping（decide、observations、close、validate）").isEqualTo(4);

        JavaClass bridge = classes.get(AgentBridge.class);
        List<JavaMethod> siMethods = bridge.getMethods().stream().filter(m -> m.getName().matches("si[A-Z].*")).toList();
        assertThat(siMethods).as("AgentBridge 上名稱以 si 接大寫字母起頭的方法恰五個").extracting(JavaMethod::getName)
                .containsExactlyInAnyOrder("siExport", "siWriteDecide", "siWriteObservation", "siWriteObservationClose",
                        "siValidateObservation");
        JavaMethod siExport = siMethods.stream().filter(m -> m.getName().equals("siExport")).findFirst().orElseThrow();
        assertThat(siExport.getRawParameterTypes()).extracting(JavaClass::getName)
                .containsExactly(String.class.getName(), Integer.class.getName(), Integer.class.getName(), String.class.getName(),
                        String.class.getName(), String.class.getName());
        assertThat(siExport.getRawReturnType().getName()).isEqualTo(SiExport.class.getName());

        // 呼叫（或以方法參照取用）三個 siWrite… 的類別只有 SiConsoleWriteService；寫入埠、對帳讀埠各只有一個使用者
        assertThat(accessorsOf(classes, AgentBridge.class, a -> a.getTarget().getName().startsWith("siWrite")))
                .as("只有 SiConsoleWriteService 呼叫 siWrite…").containsExactly(SiConsoleWriteService.class.getSimpleName());
        assertThat(accessorsOf(classes, SiConsoleWriteRepository.class, a -> true))
                .as("只有 SiConsoleWriteService 使用寫入埠（實作它的 JDBC 配接器不算使用者）")
                .containsExactly(SiConsoleWriteService.class.getSimpleName());
        assertThat(accessorsOf(classes, SiConsoleWriteQueries.class, a -> true)).as("只有 SiReconcileService 使用對帳讀埠")
                .containsExactly(SiReconcileService.class.getSimpleName());
        assertThat(accessorsOf(classes, AgentBridge.class, a -> a.getTarget().getName().equals("siValidateObservation")))
                .as("預檢只經 SiConsoleWriteService").containsExactly(SiConsoleWriteService.class.getSimpleName());

        // 唯讀鏡像不依賴任何寫入埠，也只呼叫 siExport
        JavaClass mirror = classes.get(SiMirrorQueryService.class);
        assertThat(mirror.getDirectDependenciesFromSelf().stream().map(d -> d.getTargetClass().getName()).toList())
                .as("SiMirrorQueryService 不依賴任何寫入埠").doesNotContain(SiConsoleWriteRepository.class.getName(),
                        SiConsoleWriteQueries.class.getName());
        assertThat(mirror.getAccessesFromSelf().stream().filter(a -> a.getTargetOwner().getName().equals(AgentBridge.class.getName()))
                .map(a -> a.getTarget().getName()).collect(Collectors.toSet())).containsExactly("siExport");

        // 既有的分層規則（A1～A6 與兩條落點規則）在加入 SI 類別後仍全綠：同一批類別、同一組規則，由本 AT 一併驗
        Map<String, ArchRule> existing = Map.of(
                "A1", ArchitectureRulesTest.A1_domain_is_pure_java,
                "A2", ArchitectureRulesTest.A2_application_depends_only_on_domain,
                "A3", ArchitectureRulesTest.A3_inbound_adapters_do_not_reach_outbound_or_infrastructure,
                "A4", ArchitectureRulesTest.A4_outbound_adapters_do_not_depend_on_inbound,
                "A5", ArchitectureRulesTest.A5_nothing_inside_depends_on_infrastructure,
                "A6", ArchitectureRulesTest.A6_top_level_packages_are_free_of_cycles,
                "JPA", ArchitectureRulesTest.jpa_entities_live_only_in_infrastructure_persistence,
                "WEB", ArchitectureRulesTest.controllers_live_only_in_inbound_web_adapter);
        existing.forEach((name, rule) -> rule.check(classes));
    }

    // ── AT-950-8-2：表的寫入面只有三條 ───────────────────────────────────────────────────────────────

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

    @Test
    void AT_950_8_2_theTableIsReachedByOneAdapterThroughThreeWritePathsAndNothingElse() throws IOException {
        Path root = Path.of("src", "main", "java");
        Map<String, String> sources;
        try (Stream<Path> files = Files.walk(root)) {
            sources = files.filter(p -> p.toString().endsWith(".java")).collect(Collectors.toMap(
                    p -> root.relativize(p).toString().replace('\\', '/'), p -> {
                        try {
                            return stripComments(Files.readString(p, StandardCharsets.UTF_8));
                        } catch (IOException e) {
                            throw new java.io.UncheckedIOException(e);
                        }
                    }));
        }
        String adapterPath = "com/aisdlc/console/adapter/out/persistence/SiConsoleWriteAdapter.java";
        List<String> touching = sources.entrySet().stream().filter(e -> e.getValue().contains(TABLE)).map(Map.Entry::getKey).sorted().toList();
        assertThat(touching).as("存取表的類別（註解之外的原始碼提及）只有一個 persistence adapter").containsExactly(adapterPath);

        String adapter = sources.get(adapterPath);
        assertThat(count(adapter, "(?is)insert\\s+into\\s+console\\." + TABLE + "\\b")).as("INSERT 恰一條").isEqualTo(1);
        Matcher update = Pattern.compile("(?is)update\\s+console\\." + TABLE + "\\s+set\\s+(\\w+)\\s*=").matcher(adapter);
        assertThat(update.find()).as("UPDATE 恰一條").isTrue();
        assertThat(update.group(1)).as("唯一的 UPDATE 只設 subject_id").isEqualTo("subject_id");
        assertThat(update.find()).as("沒有第二條 UPDATE").isFalse();
        assertThat(count(adapter, "(?is)delete\\s+from\\s+console\\." + TABLE + "\\s+where\\s+audit_ref\\s*=")).as("DELETE 恰一條且按 audit_ref")
                .isEqualTo(1);
        assertThat(adapter.toLowerCase(java.util.Locale.ROOT)).as("沒有 TRUNCATE 或其他 DML")
                .doesNotContain("truncate").doesNotContain("merge into").doesNotContain("on conflict").doesNotContain("upsert");
        assertThat(count(adapter, "(?is)\\b(insert|update|delete)\\b[^;\"]*console\\." + TABLE)).as("DML 敘述總數").isEqualTo(3);

        Set<String> repositoryMethods = methodNames(SiConsoleWriteRepository.class);
        Set<String> queryMethods = methodNames(SiConsoleWriteQueries.class);
        assertThat(repositoryMethods).as("寫入埠的方法").containsExactlyInAnyOrder("insert", "deleteByAuditRef");
        assertThat(queryMethods).as("讀埠的方法：回填與唯讀查詢").containsExactlyInAnyOrder("findRecent", "findExistingAuditRefs",
                "findObsAddRefsWithoutSubject", "fillSubjectId");
        Set<String> all = new TreeSet<>(repositoryMethods);
        all.addAll(queryMethods);
        assertThat(all).as("兩個埠的方法只有 insert、deleteByAuditRef、fillSubjectId 與 find… 的唯讀查詢")
                .allSatisfy(name -> assertThat(name.equals("insert") || name.equals("deleteByAuditRef") || name.equals("fillSubjectId")
                        || name.startsWith("find")).isTrue());
    }

    private static int count(String text, String regex) {
        Matcher matcher = Pattern.compile(regex).matcher(text);
        int count = 0;
        while (matcher.find()) {
            count++;
        }
        return count;
    }

    private static Set<String> methodNames(Class<?> port) {
        return Arrays.stream(port.getDeclaredMethods()).map(Method::getName).collect(Collectors.toCollection(TreeSet::new));
    }
}
