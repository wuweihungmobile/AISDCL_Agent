package com.aisdlc.console.architecture;

import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static com.tngtech.archunit.library.dependencies.SlicesRuleDefinition.slices;

/**
 * Clean Architecture 依賴方向（Architecture §4.2；PRD §4.1）。
 *
 * <p>A1 是任務書指定的最低要求（domain 純 Java）；A2～A6 是 Architecture §4.2 列的其餘規則——現有結構本來就
 * 滿足，直接鎖住，日後新增的 Phase 3～6 程式碼若破壞分層會在這裡紅燈，而不是等到 review 才發現。
 */
@AnalyzeClasses(packages = "com.aisdlc.console", importOptions = ImportOption.DoNotIncludeTests.class)
class ArchitectureRulesTest {

    /** A1：domain 不得依賴 application／adapter／infrastructure，也不得依賴 Spring、JPA 與其他框架。 */
    @ArchTest
    static final ArchRule A1_domain_is_pure_java = noClasses().that().resideInAPackage("..domain..")
            .should().dependOnClassesThat().resideInAnyPackage(
                    "..application..", "..adapter..", "..infrastructure..",
                    "org.springframework..", "jakarta.persistence..", "org.hibernate..", "jakarta.validation..",
                    "com.fasterxml.jackson.databind..", "tools.jackson..", "io.swagger..", "io.jsonwebtoken..")
            .because("domain 是純 Java：不依賴 Spring／JPA／序列化／JWT 等框架（Architecture §4.2 A1）");

    /** A2：application 只依賴 domain 與自身，不得依賴 adapter／infrastructure。 */
    @ArchTest
    static final ArchRule A2_application_depends_only_on_domain = noClasses().that().resideInAPackage("..application..")
            .should().dependOnClassesThat().resideInAnyPackage("..adapter..", "..infrastructure..")
            .because("infrastructure 只經 port.out 由 adapter 實作後注入（A2）");

    /** A3：adapter.in 不得依賴 adapter.out 與 infrastructure。 */
    @ArchTest
    static final ArchRule A3_inbound_adapters_do_not_reach_outbound_or_infrastructure =
            noClasses().that().resideInAPackage("..adapter.in..")
                    .should().dependOnClassesThat().resideInAnyPackage("..adapter.out..", "..infrastructure..")
                    .because("Controller 只能透過 application.port.in 與 domain 工作（A3）");

    /** A4：adapter.out 不得依賴 adapter.in。 */
    @ArchTest
    static final ArchRule A4_outbound_adapters_do_not_depend_on_inbound =
            noClasses().that().resideInAPackage("..adapter.out..")
                    .should().dependOnClassesThat().resideInAPackage("..adapter.in..")
                    .because("輸出介面卡實作 port.out，不認識 Web 層（A4）");

    /** A5：infrastructure 不得被 domain／application 引用（Bean 裝配只在 infrastructure.config）。 */
    @ArchTest
    static final ArchRule A5_nothing_inside_depends_on_infrastructure =
            noClasses().that().resideInAnyPackage("..domain..", "..application..")
                    .should().dependOnClassesThat().resideInAPackage("..infrastructure..")
                    .because("依賴方向由外向內（A5）");

    /** A6：四個頂層套件之間沒有循環依賴。 */
    @ArchTest
    static final ArchRule A6_top_level_packages_are_free_of_cycles = slices()
            .matching("com.aisdlc.console.(*)..").should().beFreeOfCycles();

    /** JPA 實體（資料表映射）只能住在 infrastructure.persistence.entity，domain 模型才是業務真相。 */
    @ArchTest
    static final ArchRule jpa_entities_live_only_in_infrastructure_persistence =
            classes().that().areAnnotatedWith("jakarta.persistence.Entity")
                    .should().resideInAPackage("..infrastructure.persistence.entity..");

    /** REST Controller 只能住在 adapter.in.web。 */
    @ArchTest
    static final ArchRule controllers_live_only_in_inbound_web_adapter =
            classes().that().areAnnotatedWith("org.springframework.web.bind.annotation.RestController")
                    .should().resideInAPackage("..adapter.in.web..");
}
