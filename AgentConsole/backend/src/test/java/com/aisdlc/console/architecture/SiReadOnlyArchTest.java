package com.aisdlc.console.architecture;

import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.domain.model.si.SiExport;
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

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SelfImproving 唯讀鏡像的結構鎖（TCS-SelfImprovingMirror-P1b R7、R10；AT-932-2-5）。
 * 為什麼用 ArchUnit：Console 對 SelfImproving 零寫入是 P1b 的前提（掌舵者在 Console 內決定提案屬 P2b、依賴根層 P2 動詞），
 * 行為面由整合測試覆蓋（任何非 GET 回 403／405），這裡鎖<b>結構</b>——日後有人加了寫入映射或在 {@code AgentBridge}
 * 上多開一個 {@code si} 起頭的呼叫，編譯得過、整合測試也許沒測到，但這支會在最便宜的地方先紅。
 */
class SiReadOnlyArchTest {

    private static final String WEB = "com.aisdlc.console.adapter.in.web";

    private static JavaClasses mainClasses() {
        return new ClassFileImporter().withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importPackages("com.aisdlc.console");
    }

    @Test
    void AT_932_2_5_siControllersHaveNoWriteMappingsAndTheBridgePortHasOnlySiExport() {
        JavaClasses classes = mainClasses();
        // Si*Controller：Si 之後不接小寫字母（SignoffController 是別的功能，不在這條鎖的範圍）
        List<JavaClass> controllers = classes.stream()
                .filter(c -> c.getPackageName().equals(WEB) && c.getSimpleName().matches("Si(?![a-z]).*Controller")).toList();
        assertThat(controllers).as("防反空轉：至少有 SiController").extracting(JavaClass::getSimpleName)
                .contains("SiController");

        for (JavaClass controller : controllers) {
            controller.tryGetAnnotationOfType(RequestMapping.class)
                    .ifPresent(mapping -> assertThat(mapping.method()).as("%s 的 @RequestMapping 不得帶 method", controller.getName())
                            .isEmpty());
            for (JavaMethod method : controller.getMethods()) {
                String label = controller.getSimpleName() + "." + method.getName();
                assertThat(method.isAnnotatedWith(PostMapping.class)).as("%s 不得有 @PostMapping", label).isFalse();
                assertThat(method.isAnnotatedWith(PutMapping.class)).as("%s 不得有 @PutMapping", label).isFalse();
                assertThat(method.isAnnotatedWith(PatchMapping.class)).as("%s 不得有 @PatchMapping", label).isFalse();
                assertThat(method.isAnnotatedWith(DeleteMapping.class)).as("%s 不得有 @DeleteMapping", label).isFalse();
                method.tryGetAnnotationOfType(RequestMapping.class)
                        .ifPresent(mapping -> assertThat(mapping.method()).as("%s 的 @RequestMapping 不得帶 method", label)
                                .isEmpty());
            }
        }
        long getMappings = controllers.stream().flatMap(c -> c.getMethods().stream())
                .filter(m -> m.isAnnotatedWith(GetMapping.class)).count();
        assertThat(getMappings).as("SiController 恰六個 @GetMapping（status、observations、events、proposals、proposals/{id}、runs）")
                .isEqualTo(6);

        JavaClass bridge = classes.get(AgentBridge.class);
        List<JavaMethod> siMethods = bridge.getMethods().stream().filter(m -> m.getName().matches("si[A-Z].*")).toList();
        assertThat(siMethods).as("AgentBridge 上名稱以 si 接大寫字母起頭的方法恰為 siExport").hasSize(1);
        JavaMethod siExport = siMethods.get(0);
        assertThat(siExport.getName()).isEqualTo("siExport");
        assertThat(siExport.getRawParameterTypes()).extracting(JavaClass::getName)
                .containsExactly(String.class.getName(), Integer.class.getName(), Integer.class.getName(),
                        String.class.getName());
        assertThat(siExport.getRawReturnType().getName()).isEqualTo(SiExport.class.getName());

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
}
