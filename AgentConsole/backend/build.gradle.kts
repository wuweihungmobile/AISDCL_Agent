import org.gradle.api.tasks.testing.TestDescriptor
import org.gradle.api.tasks.testing.TestListener
import org.gradle.api.tasks.testing.TestResult

plugins {
	java
	jacoco
	checkstyle
	id("org.springframework.boot") version "4.1.1"
	id("io.spring.dependency-management") version "1.1.7"
}

group = "com.aisdlc"
version = "0.0.1-SNAPSHOT"

java {
	toolchain {
		languageVersion = JavaLanguageVersion.of(21)
	}
}

repositories {
	mavenCentral()
}

// 版本集中宣告：Spring Boot BOM 沒管的第三方才在此釘版（springdoc／jjwt／ArchUnit／PDFBox／POI／Bucket4j）。
// Apache HttpClient 5 由 Spring Boot BOM 管理版本，刻意不在此釘（契約附錄 D.4）。
val springdocVersion = "3.1.1"
val jjwtVersion = "0.12.7"
val archunitVersion = "1.5.1"
val pdfboxVersion = "3.0.8"          // Maven Central 現查（2026-10-15）：org.apache.pdfbox:pdfbox 最新 3.x
val poiVersion = "5.5.1"             // Maven Central 現查（2026-10-15）：org.apache.poi:poi-ooxml
val bucket4jVersion = "8.10.1"       // Maven Central 現查（2026-10-15）：com.bucket4j:bucket4j-core 最後一版（後續版本改名為 bucket4j_jdk17-core）

dependencies {
	implementation("org.springframework.boot:spring-boot-starter-actuator")
	implementation("org.springframework.boot:spring-boot-starter-data-jpa")
	implementation("org.springframework.boot:spring-boot-starter-flyway")
	implementation("org.springframework.boot:spring-boot-starter-security")
	implementation("org.springframework.boot:spring-boot-starter-validation")
	implementation("org.springframework.boot:spring-boot-starter-webmvc")
	implementation("org.flywaydb:flyway-database-postgresql")
	runtimeOnly("org.postgresql:postgresql")

	// PRD §12.6.1：Prometheus 抓 /actuator/prometheus
	implementation("io.micrometer:micrometer-registry-prometheus")

	// OpenAPI（NFR-9.4-03）
	implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:$springdocVersion")

	// JWT（ADR-001 D4；HS256）
	implementation("io.jsonwebtoken:jjwt-api:$jjwtVersion")
	runtimeOnly("io.jsonwebtoken:jjwt-impl:$jjwtVersion")
	runtimeOnly("io.jsonwebtoken:jjwt-jackson:$jjwtVersion")

	// Phase 3（契約附錄 D.4；主控核可，除此之外不得新增）：
	implementation("org.apache.pdfbox:pdfbox:$pdfboxVersion")             // 匯入 .pdf 文字擷取
	implementation("org.apache.poi:poi-ooxml:$poiVersion")                // 匯入 .docx 文字擷取
	implementation("com.bucket4j:bucket4j-core:$bucket4jVersion")         // NFR-9.2-06 限流（記憶體）
	implementation("org.apache.httpcomponents.client5:httpclient5")       // SSRF 外呼：自訂 DnsResolver 釘 IP、不跟 redirect

	// v1.4（契約附錄 D.4；主控裁決 D-19，Q6 視同核可）：refresh token 撤銷名單的 Redis 實作（內含 Lettuce 客戶端）；版本由 Spring Boot BOM 管理。
	// 只被撤銷名單使用（限流計數與 SSE 位移不用 Redis，ADR-001 D16／D23）；沒設 spring.data.redis.host 時不會連線。
	implementation("org.springframework.boot:spring-boot-starter-data-redis")

	testImplementation("org.springframework.boot:spring-boot-starter-actuator-test")
	testImplementation("org.springframework.boot:spring-boot-starter-data-jpa-test")
	testImplementation("org.springframework.boot:spring-boot-starter-flyway-test")
	testImplementation("org.springframework.boot:spring-boot-starter-security-test")
	testImplementation("org.springframework.boot:spring-boot-starter-validation-test")
	testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")
	testImplementation("org.springframework.boot:spring-boot-testcontainers")
	testImplementation("org.testcontainers:testcontainers-junit-jupiter")
	testImplementation("org.testcontainers:testcontainers-postgresql")
	testImplementation("com.tngtech.archunit:archunit-junit5:$archunitVersion")
	testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.withType<Test> {
	useJUnitPlatform()
	// 根 CLAUDE.md〈GitHub CI/CD 一律多 CPU 模式〉：測試分 2 個 JVM fork 平行（每 fork 各起一個 Testcontainers PG，
	// 再多會讓 PG 容器數隨核數成長而拖慢；CI runner 4 核實測足夠）。
	maxParallelForks = 2
	// Windows 路徑上限（260 字元）：Gradle 9.8 的 HTML 測試報告為每個測試建一個「<類別全名>/<方法簽章>」的檔案或目錄，
	// 本專案的測試方法名是完整敘述句（常 70～110 字元），加上預設的 build/reports/tests/test 前綴會逼近上限；
	// 根層 tools/tests 的檔案樹掃描一旦走到超過 260 字元的路徑就整批 FileNotFoundError（W7 第二批實際發生）。
	// 報告改放短目錄 build/rt，每個路徑省 17 字元；新增測試仍要守「方法名取短、參數化測試的參數型別取短」。
	// 驗收：Get-ChildItem build -Recurse | ForEach-Object { $_.FullName.Length } | Sort-Object -Descending | Select-Object -First 1 必須 < 240。
	reports.html.outputLocation = layout.buildDirectory.dir("rt")
	finalizedBy(tasks.jacocoTestReport)
	// 測試結束時印一行總計（筆數、成功、失敗、略過），讓 CI 日誌與本機輸出一眼看得到「真的跑了幾支」。
	addTestListener(object : TestListener {
		override fun beforeSuite(suite: TestDescriptor) {}
		override fun beforeTest(testDescriptor: TestDescriptor) {}
		override fun afterTest(testDescriptor: TestDescriptor, result: TestResult) {}
		override fun afterSuite(suite: TestDescriptor, result: TestResult) {
			if (suite.parent == null) {
				println("Test result: ${result.resultType} (${result.testCount} tests, ${result.successfulTestCount} successes, " +
					"${result.failedTestCount} failures, ${result.skippedTestCount} skipped)")
			}
		}
	})
}

// 只產生可執行的 boot jar：PRD §11.4.2 的 Dockerfile 以 `COPY build/libs/*.jar app.jar` 取檔，
// 若同時存在 *-plain.jar 會因「多個來源檔 → 單一目的檔」而建置失敗（實測）。
tasks.named<Jar>("jar") {
	enabled = false
}

// ── Checkstyle（PRD §9.4；寬鬆規則集，規則見 config/checkstyle/checkstyle.xml）──
checkstyle {
	toolVersion = "13.11.0"
	isIgnoreFailures = false
	maxWarnings = 0
}

// ── JaCoCo（PRD §9.4：後端覆蓋率 ≥ 80%）──
jacoco {
	toolVersion = "0.8.15"
}

tasks.jacocoTestReport {
	dependsOn(tasks.test)
	reports {
		xml.required = true
		html.required = true
	}
}

tasks.jacocoTestCoverageVerification {
	dependsOn(tasks.test)
	violationRules {
		rule {
			limit {
				counter = "INSTRUCTION"
				value = "COVEREDRATIO"
				minimum = "0.80".toBigDecimal()
			}
		}
	}
}

tasks.check {
	dependsOn(tasks.jacocoTestCoverageVerification)
}
