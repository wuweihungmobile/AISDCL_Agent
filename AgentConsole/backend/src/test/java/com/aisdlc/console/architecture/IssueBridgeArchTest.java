package com.aisdlc.console.architecture;

import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.domain.model.si.SiExport;
import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.domain.JavaMethod;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import org.junit.jupiter.api.Test;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestMapping;

import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 議題中心對 {@code AgentBridge} 的結構鎖（TCS-IssueCenter-20261027 R-IC-51、R-IC-53；AT-IC-07-6-1、AT-IC-07-6-E-1）。
 * 為什麼用 ArchUnit：{@code siExport} 多了 {@code status}、{@code source} 兩個參數，議題中心又新增一批 {@code Issue*} 類別——日後有人在
 * {@code AgentBridge} 上多開一個 {@code si} 起頭的呼叫、讓議題類別去碰三個稽核檔落地的寫入呼叫、或把議題端點命名成 {@code Si*Controller} 而悄悄改了
 * SelfImproving 那組「七個 GET、四個 POST、沒有 PUT／PATCH／DELETE」的計數，編譯得過、整合測試也許沒測到，但這支會在最便宜的地方先紅。
 */
class IssueBridgeArchTest {

    private static final String WEB = "com.aisdlc.console.adapter.in.web";

    private static JavaClasses mainClasses() {
        return new ClassFileImporter().withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importPackages("com.aisdlc.console");
    }

    @Test
    void AT_IC_07_6_1_agentBridgeKeepsFiveSiMethodsWithASixParameterSiExportAndTheSiControllersKeepTheirCounts() {
        JavaClasses classes = mainClasses();
        JavaClass bridge = classes.get(AgentBridge.class);
        List<JavaMethod> siMethods = bridge.getMethods().stream().filter(m -> m.getName().matches("si[A-Z].*")).toList();
        assertThat(siMethods).as("AgentBridge 上名稱以 si 接大寫字母起頭的方法仍恰五個").extracting(JavaMethod::getName)
                .containsExactlyInAnyOrder("siExport", "siWriteDecide", "siWriteObservation", "siWriteObservationClose",
                        "siValidateObservation");
        JavaMethod siExport = siMethods.stream().filter(m -> m.getName().equals("siExport")).findFirst().orElseThrow();
        assertThat(siExport.getRawParameterTypes()).as("siExport(kind, since, limit, id, status, source)").extracting(JavaClass::getName)
                .containsExactly(String.class.getName(), Integer.class.getName(), Integer.class.getName(), String.class.getName(),
                        String.class.getName(), String.class.getName());
        assertThat(siExport.getRawReturnType().getName()).isEqualTo(SiExport.class.getName());

        List<JavaClass> siControllers = classes.stream()
                .filter(c -> c.getPackageName().equals(WEB) && c.getSimpleName().matches("Si(?![a-z]).*Controller")).toList();
        assertThat(siControllers).as("防反空轉：至少有 SiController").extracting(JavaClass::getSimpleName).contains("SiController");
        List<JavaMethod> methods = siControllers.stream().flatMap(c -> c.getMethods().stream()).toList();
        assertThat(methods.stream().filter(m -> m.isAnnotatedWith(GetMapping.class)).count()).as("SiController 的 GET 仍恰七個").isEqualTo(7);
        assertThat(methods.stream().filter(m -> m.isAnnotatedWith(PostMapping.class)).count()).as("SiController 的 POST 仍恰四個").isEqualTo(4);
        for (JavaMethod method : methods) {
            assertThat(method.isAnnotatedWith(PutMapping.class) || method.isAnnotatedWith(PatchMapping.class)
                    || method.isAnnotatedWith(DeleteMapping.class)).as("%s 沒有 PUT／PATCH／DELETE 映射", method.getFullName()).isFalse();
        }
    }

    @Test
    void AT_IC_07_6_E_1_issueClassesCallOnlySiExportOnAgentBridgeAndTheControllerIsNotAnSiController() {
        JavaClasses classes = mainClasses();
        List<JavaClass> issueClasses = classes.stream().filter(c -> c.getSimpleName().startsWith("Issue")
                && c.getPackageName().startsWith("com.aisdlc.console")).toList();
        assertThat(issueClasses).as("防反空轉：議題中心的主程式類別都在").extracting(JavaClass::getSimpleName).contains("IssueController",
                "IssueQueryService", "IssuePriorityService", "IssuePriorityAdapter");

        Set<String> called = issueClasses.stream().flatMap(c -> c.getAccessesFromSelf().stream())
                .filter(access -> access.getTargetOwner().getName().equals(AgentBridge.class.getName()))
                .map(access -> access.getTarget().getName()).collect(Collectors.toCollection(TreeSet::new));
        assertThat(called).as("Issue* 類別呼叫 AgentBridge 的方法只有 siExport（沒有任何稽核檔落地或預檢的呼叫）").containsExactly("siExport");

        JavaClass controller = classes.get("com.aisdlc.console.adapter.in.web.IssueController");
        assertThat(controller.getSimpleName().matches("Si(?![a-z]).*Controller")).as("IssueController 的名稱不符 Si*Controller，不受那組計數鎖").isFalse();
        controller.tryGetAnnotationOfType(RequestMapping.class).ifPresent(mapping -> assertThat(mapping.method())
                .as("@RequestMapping 不帶 method").isEmpty());
        assertThat(controller.getMethods().stream().filter(m -> m.isAnnotatedWith(PostMapping.class) || m.isAnnotatedWith(PatchMapping.class)).count())
                .as("議題中心沒有 POST、PATCH 映射").isZero();
    }
}
