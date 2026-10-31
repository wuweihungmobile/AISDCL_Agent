package com.aisdlc.console.architecture;

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

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 備份功能的結構鎖（TCS-SysAdminBackup-20261027 R-BK-12、R-BK-17、R-BK-22、R-BK-36、R-BK-55、R-BK-57、R-BK-58、R-BK-14；BA 載具七個 AT：
 * AT-BK-04-3-E-2、04-6-E-1、06-8-E-1、10-1-E-1、10-3-2、10-3-E-2、10-4-3；SCG-4 二審另補 AT-BK-10-4-S-1，TCS 無此編號、勘誤納入）。為什麼用 ArchUnit 與原始碼掃描：
 * 這幾件事「寫壞了編譯得過、整合測試也許沒測到」，
 * 卻都是資料或安全的承重牆——服務層若偷用系統時鐘或 JVM 預設時區，逾期判定就隨機器而變；{@code backup_jobs} 若出現第二個寫入者或無條件 UPDATE，
 * 單工與對帳的「只有一方生效」保證就破功；{@code POST /sysadmin/**} 的 ADMIN 規則若排在通用規則之後，OPERATOR 就能觸發備份；console-api 若出現行程啟動或網路呼叫，
 * 控制面「只有檔案 I/O」的信任邊界就破了；日誌若把例外文字原樣寫出，連線字串與檔案內容就繞過遮罩進了集中式日誌。掃描函式是純函式（輸入原始碼文字、輸出違規清單）：
 * 對真原始碼必須回空、對合成的違規樣本必須回非空（各 AT 的負控，鎖不得空過）。
 */
class BackupArchTest {

    private static final String ADAPTER = "com/aisdlc/console/adapter/out/persistence/BackupJobAdapter.java";
    private static final String WAL_ADAPTER = "com/aisdlc/console/adapter/out/persistence/WalArchiveStatsAdapter.java";
    private static final String CONTROLLER = "com/aisdlc/console/adapter/in/web/BackupController.java";
    private static final String SECURITY = "com/aisdlc/console/infrastructure/config/SecurityConfig.java";

    // 日誌行的例外外洩掃描（AT-BK-10-4-S-1）所用的樣式
    private static final Pattern LOG_CALL = Pattern.compile("\\b(?:LOG|LOGGER|log|logger)\\s*\\.\\s*(?:trace|debug|info|warn|error)\\s*\\(");
    private static final Pattern MASK_CALL = Pattern.compile("BackupMasker\\s*\\.\\s*mask\\s*\\(");
    private static final Pattern EXCEPTION_TEXT = Pattern.compile("\\.\\s*(?:toString|getMessage|getLocalizedMessage)\\s*\\(");
    private static final Pattern CATCH_PARAMETER = Pattern.compile("\\bcatch\\s*\\(([^)]*)\\)");
    private static final Pattern EXCEPTION_DECLARATION = Pattern.compile("\\b\\w*(?:Exception|Error|Throwable)\\s+(\\w+)\\s*[,;)=:?&|]");

    // ── 原始碼讀取（去註解；沿 IssuePriorityArchTest 的做法）─────────────────────────────────

    private static Map<String, String> mainSources() {
        Path root = Path.of("src", "main", "java");
        Map<String, String> out = new TreeMap<>();
        try (Stream<Path> files = Files.walk(root)) {
            for (Path path : files.filter(p -> p.toString().endsWith(".java")).toList()) {
                out.put(root.relativize(path).toString().replace('\\', '/'),
                        stripComments(Files.readString(path, StandardCharsets.UTF_8)));
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return out;
    }

    /** {@code src/main/resources} 下的設定與遷移檔（原文，不去註解）。 */
    private static Map<String, String> mainResources() {
        Path root = Path.of("src", "main", "resources");
        Map<String, String> out = new TreeMap<>();
        try (Stream<Path> files = Files.walk(root)) {
            for (Path path : files.filter(p -> p.toString().endsWith(".yml") || p.toString().endsWith(".sql")
                    || p.toString().endsWith(".properties")).toList()) {
                out.put(root.relativize(path).toString().replace('\\', '/'), Files.readString(path, StandardCharsets.UTF_8));
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

    private static int count(String text, String regex) {
        Matcher matcher = Pattern.compile(regex).matcher(text);
        int count = 0;
        while (matcher.find()) {
            count++;
        }
        return count;
    }

    private static JavaClasses mainClasses() {
        return new ClassFileImporter().withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS).importPackages("com.aisdlc.console");
    }

    // ── 掃描函式（純函式）──────────────────────────────────────────────────────────────────────

    /** 備份服務層與 domain 的時間與時區來源：禁止一切「現在」與 JVM 預設時區的靜態呼叫（時間取自 {@code BackupClock}、時區取自 {@code schedule.json.tz}）。 */
    static List<String> timeSourceViolations(String strippedSource) {
        List<String> banned = List.of("Instant\\.now\\(", "LocalDateTime\\.now\\(", "ZonedDateTime\\.now\\(", "OffsetDateTime\\.now\\(",
                "LocalDate\\.now\\(", "System\\.currentTimeMillis\\(", "System\\.nanoTime\\(", "Clock\\.systemUTC\\(",
                "Clock\\.systemDefaultZone\\(", "ZoneId\\.systemDefault\\(", "TimeZone\\.getDefault\\(");
        List<String> out = new ArrayList<>();
        for (String regex : banned) {
            if (count(strippedSource, regex) > 0) {
                out.add("不得呼叫 " + regex.replace("\\", ""));
            }
        }
        return out;
    }

    /** 歸檔統計視圖的讀取：恰一條唯讀 SELECT、沒有寫入敘述與其他 pg_ 系統函式，且該視圖只出現在這一個類別。 */
    static List<String> walArchiveViolations(String strippedAdapter, Map<String, String> allSources) {
        List<String> out = new ArrayList<>();
        int selects = count(strippedAdapter, "(?i)\"\\s*select\\s");
        int fromView = count(strippedAdapter, "(?is)\\bselect\\b[^;\"]*\\bfrom\\s+pg_stat_archiver\\b");
        if (selects != 1 || fromView != 1) {
            out.add("SQL 敘述必須恰一條且為 SELECT … FROM pg_stat_archiver：select=" + selects + "、from=" + fromView);
        }
        for (String banned : List.of("insert\\s", "update\\s", "delete\\s", "truncate\\s", "alter\\s", "drop\\s")) {
            if (count(strippedAdapter, "(?i)\"\\s*" + banned) > 0 || count(strippedAdapter, "(?i)\\b" + banned + "[a-z_.]+\\s+(set|into|from|table)\\b") > 0) {
                out.add("不得出現寫入敘述：" + banned.trim());
            }
        }
        if (count(strippedAdapter, "(?i)\\bpg_(?!stat_archiver\\b)[a-z_]+\\s*\\(") > 0) {
            out.add("不得呼叫 pg_ 系統函式");
        }
        List<String> users = allSources.entrySet().stream().filter(e -> e.getValue().contains("pg_stat_archiver")).map(Map.Entry::getKey).sorted().toList();
        if (!users.equals(List.of(WAL_ADAPTER))) {
            out.add("pg_stat_archiver 只能出現在 " + WAL_ADAPTER + "，實際：" + users);
        }
        return out;
    }

    /** 工作表配接器的寫入敘述：每一條 UPDATE 都帶「仍在進行中」的條件子句；沒有 DELETE、TRUNCATE。 */
    static List<String> updateViolations(String strippedAdapter) {
        List<String> out = new ArrayList<>();
        Matcher updates = Pattern.compile("(?is)update\\s+console\\.backup_jobs\\b[^;]*;").matcher(strippedAdapter);
        int total = 0;
        while (updates.find()) {
            total++;
            String statement = updates.group();
            if (!Pattern.compile("(?is)status\\s*=\\s*'QUEUED'|status\\s+in\\s*\\(\\s*'QUEUED'\\s*,\\s*'RUNNING'\\s*\\)").matcher(statement).find()) {
                out.add("UPDATE 缺「status 仍在進行中」的條件子句：" + statement.strip());
            }
        }
        if (total != 3) {
            out.add("條件式 UPDATE 必須恰三條（markRunningIfQueued、markTerminalIfActive、markExpiredIfQueued）：" + total);
        }
        if (count(strippedAdapter, "(?i)delete\\s+from") > 0 || count(strippedAdapter, "(?i)truncate\\s") > 0) {
            out.add("不得有 DELETE、TRUNCATE");
        }
        if (count(strippedAdapter, "(?is)insert\\s+into\\s+console\\.backup_jobs\\b") != 1) {
            out.add("INSERT 必須恰一條");
        }
        return out;
    }

    /** {@code backup_jobs} 只被一個 persistence adapter 觸及。 */
    static List<String> tableAccessViolations(Map<String, String> strippedSources) {
        List<String> touching = strippedSources.entrySet().stream().filter(e -> e.getValue().contains("backup_jobs")).map(Map.Entry::getKey).sorted().toList();
        List<String> out = new ArrayList<>();
        if (!touching.equals(List.of(ADAPTER))) {
            out.add("存取 backup_jobs 的類別必須恰為 " + ADAPTER + "，實際：" + touching);
        }
        return out;
    }

    /** SecurityConfig：POST sysadmin 規則恰一次，且排在通用 {@code /api/v1/**} 規則之前（先中者定案）。 */
    static List<String> securityOrderViolations(String strippedSecurity) {
        List<String> out = new ArrayList<>();
        String rule = "requestMatchers(HttpMethod.POST, \"/api/v1/sysadmin/**\").hasRole(\"ADMIN\")";
        int occurrences = count(strippedSecurity, Pattern.quote(rule));
        if (occurrences != 1) {
            out.add("POST /api/v1/sysadmin/** 的 ADMIN 規則必須恰出現一次：" + occurrences);
        }
        Matcher generic = Pattern.compile("requestMatchers\\(\"/api/v1/\\*\\*\"\\)").matcher(strippedSecurity);
        int genericAt = generic.find() ? generic.start() : -1;
        int ruleAt = strippedSecurity.indexOf(rule);
        if (genericAt < 0) {
            out.add("找不到通用的 requestMatchers(\"/api/v1/**\") 規則（鎖不得空過）");
        } else if (ruleAt >= 0 && ruleAt > genericAt) {
            out.add("POST /api/v1/sysadmin/** 規則必須在通用 /api/v1/** 規則之前（否則 OPERATOR 通過安全層）");
        }
        return out;
    }

    /** 控制器的映射：恰三個 {@code @GetMapping}、一個 {@code @PostMapping}；沒有 PUT、PATCH、DELETE，沒有帶 method 的 {@code @RequestMapping}。 */
    static List<String> mappingViolations(String strippedController) {
        List<String> out = new ArrayList<>();
        int gets = count(strippedController, "@GetMapping\\b");
        int posts = count(strippedController, "@PostMapping\\b");
        if (gets != 3) {
            out.add("@GetMapping 必須恰三個（總覽、工作清單、單筆）：" + gets);
        }
        if (posts != 1) {
            out.add("@PostMapping 必須恰一個：" + posts);
        }
        for (String banned : List.of("@PutMapping", "@PatchMapping", "@DeleteMapping")) {
            if (strippedController.contains(banned)) {
                out.add("不得有 " + banned);
            }
        }
        if (count(strippedController, "@RequestMapping\\s*\\([^)]*method\\s*=") > 0) {
            out.add("不得有帶 method 的 @RequestMapping");
        }
        return out;
    }

    /** backup 相關類別：沒有機密環境變數名、行程啟動、網路呼叫（console-api 對 sidecar 只有檔案 I/O）。 */
    static List<String> trustBoundaryViolations(String strippedSource) {
        List<String> banned = List.of("PGBACKREST_CIPHER_PASS", "AWS_SECRET_ACCESS_KEY", "MC_HOST", "docker.sock", "ProcessBuilder",
                "Runtime.getRuntime().exec", "java.net.http", "HttpClient", "RestTemplate", "RestClient", "WebClient", "HttpURLConnection",
                "new Socket(", "java.net.Socket");
        List<String> out = new ArrayList<>();
        for (String text : banned) {
            if (strippedSource.contains(text)) {
                out.add("不得出現 " + text);
            }
        }
        return out;
    }

    private static boolean isBackupRelated(String path) {
        String file = path.substring(path.lastIndexOf('/') + 1);
        return path.contains("/backup/") || file.contains("Backup") || file.startsWith("WalArchive");
    }

    /** 一個 LOG 呼叫：text＝原文（空白收斂，供失敗訊息點名站點）；arguments＝括號內的參數文字（字串常值的內容已遮成空白），括號不成對時為 null。 */
    record LogCall(String text, String arguments) {
    }

    /** 把字串與字元常值的內容換成空白（長度不變、引號保留）：之後的字樣與括號比對不會被常值裡的文字誤導。 */
    private static String blankLiterals(String source) {
        StringBuilder out = new StringBuilder(source);
        int i = 0;
        int n = source.length();
        while (i < n) {
            char c = source.charAt(i);
            if (c == '"' || c == '\'') {
                int j = i + 1;
                while (j < n && source.charAt(j) != c) {
                    int step = source.charAt(j) == '\\' ? 2 : 1;
                    for (int k = j; k < Math.min(n, j + step); k++) {
                        out.setCharAt(k, ' ');
                    }
                    j += step;
                }
                i = j + 1;
            } else {
                i++;
            }
        }
        return out.toString();
    }

    /** from（左括號之後）起對應的右括號位置；不成對回 -1。傳入的必須是 {@code blankLiterals} 之後的文字。 */
    private static int closingParenthesis(String code, int from) {
        int depth = 1;
        for (int i = from; i < code.length(); i++) {
            char c = code.charAt(i);
            if (c == '(') {
                depth++;
            } else if (c == ')') {
                depth--;
                if (depth == 0) {
                    return i;
                }
            }
        }
        return -1;
    }

    /** 去掉所有 {@code BackupMasker.mask(…)} 群組（含巢狀括號）；剩下的才是「沒經過遮罩就進日誌」的部分。傳入 {@code blankLiterals} 之後的文字。 */
    private static String withoutMasked(String code) {
        StringBuilder out = new StringBuilder();
        Matcher mask = MASK_CALL.matcher(code);
        int from = 0;
        while (mask.find(from)) {
            int close = closingParenthesis(code, mask.end());
            out.append(code, from, mask.start()).append(' ');
            if (close < 0) {
                return out.toString();
            }
            from = close + 1;
        }
        return out.append(code, from, code.length()).toString();
    }

    /** 宣告為例外的變數名：catch 參數，以及型別名以 Exception／Error／Throwable 結尾的參數、區域變數與樣式變數。傳入 {@code blankLiterals} 之後的文字。 */
    private static List<String> exceptionVariableNames(String code) {
        List<String> names = new ArrayList<>();
        Matcher caught = CATCH_PARAMETER.matcher(code);
        while (caught.find()) {
            String[] parts = caught.group(1).trim().split("\\s+");
            names.add(parts[parts.length - 1]);
        }
        Matcher declared = EXCEPTION_DECLARATION.matcher(code);
        while (declared.find()) {
            names.add(declared.group(1));
        }
        return names.stream().distinct().toList();
    }

    /** 原始碼（已去註解）裡所有的 {@code LOG.<level>(…)} 呼叫（logger 變數名認 LOG、LOGGER、log、logger；level 認 trace／debug／info／warn／error）。 */
    static List<LogCall> logCalls(String strippedSource) {
        String code = blankLiterals(strippedSource);
        List<LogCall> out = new ArrayList<>();
        Matcher call = LOG_CALL.matcher(code);
        while (call.find()) {
            int close = closingParenthesis(code, call.end());
            int end = close < 0 ? strippedSource.length() : close + 1;
            out.add(new LogCall(strippedSource.substring(call.start(), end).replaceAll("\\s+", " "),
                    close < 0 ? null : code.substring(call.end(), close)));
        }
        return out;
    }

    /**
     * backup 相關類別的日誌行不得外洩例外文字（R-BK-58 的日誌面）：每個 LOG 呼叫在去掉所有 {@code BackupMasker.mask(…)} 群組之後，參數裡不得還剩
     * {@code .toString()}／{@code .getMessage()}／{@code .getLocalizedMessage()}（不分接收者），也不得直接帶例外變數（SLF4J 會把它的訊息與堆疊整份印出）；
     * 括號不成對、解析不了的呼叫同樣回報（掃描不得默默略過讀不懂的東西）。
     */
    static List<String> logLeakViolations(String strippedSource) {
        List<String> exceptionNames = exceptionVariableNames(blankLiterals(strippedSource));
        List<String> out = new ArrayList<>();
        for (LogCall call : logCalls(strippedSource)) {
            if (call.arguments() == null) {
                out.add("LOG 呼叫的括號不成對、無法檢查：" + call.text());
                continue;
            }
            String unmasked = withoutMasked(call.arguments());
            boolean carriesText = EXCEPTION_TEXT.matcher(unmasked).find();
            boolean carriesThrowable = exceptionNames.stream()
                    .anyMatch(name -> Pattern.compile("\\b" + Pattern.quote(name) + "\\b").matcher(unmasked).find());
            if (carriesText || carriesThrowable) {
                out.add("例外沒經 BackupMasker.mask 就進了日誌：" + call.text());
            }
        }
        return out;
    }

    // ── AT-BK-04-3-E-2 ────────────────────────────────────────────────────────────────────────

    @Test
    void AT_BK_04_3_E_2_theBackupServicesAndDomainTakeTimeOnlyFromTheInjectedClockAndZoneOnlyFromTheSchedule() {
        Map<String, String> sources = mainSources();
        Map<String, String> scanned = new TreeMap<>();
        sources.forEach((path, text) -> {
            if (path.startsWith("com/aisdlc/console/application/service/Backup") || path.startsWith("com/aisdlc/console/domain/model/backup/")) {
                scanned.put(path, text);
            }
        });
        assertThat(scanned.keySet()).as("防反空轉：掃描到 BackupCron、BackupOverdue、BackupQueryService、BackupJobService、BackupJobReconciler 與 domain 的遮罩")
                .contains("com/aisdlc/console/application/service/BackupCron.java", "com/aisdlc/console/application/service/BackupOverdue.java",
                        "com/aisdlc/console/application/service/BackupQueryService.java", "com/aisdlc/console/application/service/BackupJobService.java",
                        "com/aisdlc/console/application/service/BackupJobReconciler.java", "com/aisdlc/console/domain/model/backup/BackupMasker.java");
        scanned.forEach((path, text) -> assertThat(timeSourceViolations(text)).as(path).isEmpty());

        // 負控：每一種禁用呼叫的合成樣本都回非空
        for (String bad : List.of("Instant.now()", "LocalDateTime.now()", "ZonedDateTime.now()", "OffsetDateTime.now()", "System.currentTimeMillis()",
                "Clock.systemUTC()", "Clock.systemDefaultZone()", "ZoneId.systemDefault()", "TimeZone.getDefault()")) {
            assertThat(timeSourceViolations("class X { Object o = " + bad + "; }")).as("合成樣本 " + bad).isNotEmpty();
        }
        assertThat(timeSourceViolations("class X { Instant t = clock.instant(); ZoneId z = ZoneId.of(tz); }")).isEmpty();
    }

    // ── AT-BK-04-6-E-1 ────────────────────────────────────────────────────────────────────────

    @Test
    void AT_BK_04_6_E_1_theWalArchiveReadIsOneReadOnlySelectInOneClass() {
        Map<String, String> sources = mainSources();
        assertThat(sources).as("防反空轉").containsKey(WAL_ADAPTER);
        assertThat(walArchiveViolations(sources.get(WAL_ADAPTER), sources)).isEmpty();

        String adapter = sources.get(WAL_ADAPTER);
        assertThat(walArchiveViolations(adapter.replace("from pg_stat_archiver\"", "from pg_stat_archiver\"; String second = \"select 1 from dual\""), sources))
                .as("第二條敘述").isNotEmpty();
        assertThat(walArchiveViolations(adapter.replace("select failed_count", "update pg_stat_archiver set failed_count"), sources))
                .as("UPDATE").isNotEmpty();
        Map<String, String> twoUsers = new TreeMap<>(sources);
        twoUsers.put("com/aisdlc/console/adapter/out/persistence/Other.java", "class Other { String q = \"select 1 from pg_stat_archiver\"; }");
        assertThat(walArchiveViolations(adapter, twoUsers)).as("第二個存取該視圖的類別").isNotEmpty();
        Map<String, String> none = new TreeMap<>(sources);
        none.remove(WAL_ADAPTER);
        assertThat(walArchiveViolations("class A { }", none)).as("沒有任何類別存取該視圖同樣是違規").isNotEmpty();
    }

    // ── AT-BK-06-8-E-1 ────────────────────────────────────────────────────────────────────────

    @Test
    void AT_BK_06_8_E_1_everyUpdateOfTheJobTableIsConditionalAndThereIsNoDeleteOrTruncate() {
        Map<String, String> sources = mainSources();
        assertThat(sources).as("防反空轉").containsKey(ADAPTER);
        assertThat(updateViolations(sources.get(ADAPTER))).isEmpty();

        String adapter = sources.get(ADAPTER);
        assertThat(updateViolations(adapter.replace(" and status = 'QUEUED'\", at(finishedAt), id)", "\", at(finishedAt), id)")))
                .as("少條件子句的 UPDATE").isNotEmpty();
        assertThat(updateViolations(adapter + "\n\"delete from console.backup_jobs\";")).as("DELETE").isNotEmpty();
        assertThat(updateViolations(adapter + "\n\"truncate console.backup_jobs\";")).as("TRUNCATE").isNotEmpty();
        assertThat(updateViolations(adapter + "\n\"update console.backup_jobs set detail = '';\"")).as("第四條無條件 UPDATE").isNotEmpty();
    }

    // ── AT-BK-10-1-E-1 ────────────────────────────────────────────────────────────────────────

    @Test
    void AT_BK_10_1_E_1_theJobTableHasNoJpaEntityAndIsTouchedByOneJdbcAdapterOnly() {
        Map<String, String> sources = mainSources();
        assertThat(tableAccessViolations(sources)).isEmpty();
        assertThat(sources.get(ADAPTER)).as("以 JDBC 存取（不經 JPA）").contains("JdbcTemplate").doesNotContain("EntityManager").doesNotContain("JpaRepository");

        JavaClasses classes = mainClasses();
        assertThat(classes.stream().filter(c -> c.getSimpleName().startsWith("Backup")).toList()).as("防反空轉：有 Backup* 類別").isNotEmpty();
        for (JavaClass type : classes) {
            // 其他功能有自己的 @Entity；這裡鎖的是「沒有任何實體對映 backup_jobs」——表名只出現在 JDBC 配接器（tableAccessViolations），且 Backup* 類別不是實體
            if (type.getSimpleName().startsWith("Backup")) {
                assertThat(type.isAnnotatedWith("jakarta.persistence.Entity")).as("%s 不得是 @Entity", type.getName()).isFalse();
                assertThat(type.getSimpleName()).as("沒有名為 Backup*Entity 的類別").doesNotEndWith("Entity");
            }
        }
        assertThat(classes.stream().filter(c -> c.isAnnotatedWith("jakarta.persistence.Entity")).map(JavaClass::getSimpleName).toList())
                .as("防反空轉：掃得到既有的 @Entity（鎖在對真類別群上跑，不是空集合）").isNotEmpty().noneMatch(name -> name.startsWith("Backup"));

        Map<String, String> twoReaders = new TreeMap<>(sources);
        twoReaders.put("com/aisdlc/console/adapter/out/persistence/Another.java", "class Another { String q = \"select * from console.backup_jobs\"; }");
        assertThat(tableAccessViolations(twoReaders)).as("第二個存取該表的類別").isNotEmpty();
        Map<String, String> noReader = new TreeMap<>(sources);
        noReader.remove(ADAPTER);
        assertThat(tableAccessViolations(noReader)).as("沒有任何類別存取該表同樣是違規").isNotEmpty();
    }

    // ── AT-BK-10-3-2 ──────────────────────────────────────────────────────────────────────────

    @Test
    void AT_BK_10_3_2_thePostSysadminAdminRuleIsDeclaredExactlyOnceAheadOfTheGenericRule() {
        Map<String, String> sources = mainSources();
        assertThat(sources).as("防反空轉").containsKey(SECURITY);
        assertThat(securityOrderViolations(sources.get(SECURITY))).isEmpty();

        String security = sources.get(SECURITY);
        String rule = ".requestMatchers(HttpMethod.POST, \"/api/v1/sysadmin/**\").hasRole(\"ADMIN\")";
        String generic = ".requestMatchers(\"/api/v1/**\").hasAnyRole(\"OPERATOR\", \"ADMIN\")";
        assertThat(security).contains(rule).contains(generic);
        assertThat(securityOrderViolations(security.replace(rule, "").replace(generic, generic + "\n" + rule)))
                .as("兩列互換（規則排在通用規則之後）").isNotEmpty();
        assertThat(securityOrderViolations(security.replace(rule, ""))).as("缺該規則").isNotEmpty();
        assertThat(securityOrderViolations(security + "\n" + rule)).as("規則出現兩次").isNotEmpty();
    }

    // ── AT-BK-10-3-E-2 ────────────────────────────────────────────────────────────────────────

    @Test
    void AT_BK_10_3_E_2_theControllerHasThreeGetsAndOnePostAndNoWriteMappingsBesides() {
        Map<String, String> sources = mainSources();
        assertThat(sources).as("防反空轉").containsKey(CONTROLLER);
        assertThat(mappingViolations(sources.get(CONTROLLER))).isEmpty();

        JavaClass controller = mainClasses().get("com.aisdlc.console.adapter.in.web.BackupController");
        List<JavaMethod> methods = controller.getMethods().stream().toList();
        assertThat(methods.stream().filter(m -> m.isAnnotatedWith(GetMapping.class)).count()).as("ArchUnit：@GetMapping 恰三個").isEqualTo(3);
        assertThat(methods.stream().filter(m -> m.isAnnotatedWith(PostMapping.class)).count()).as("ArchUnit：@PostMapping 恰一個").isEqualTo(1);
        for (JavaMethod method : methods) {
            assertThat(method.isAnnotatedWith(PutMapping.class)).as(method.getName()).isFalse();
            assertThat(method.isAnnotatedWith(PatchMapping.class)).as(method.getName()).isFalse();
            assertThat(method.isAnnotatedWith(DeleteMapping.class)).as(method.getName()).isFalse();
            method.tryGetAnnotationOfType(RequestMapping.class).ifPresent(mapping -> assertThat(mapping.method()).as(method.getName()).isEmpty());
        }

        String controllerSource = sources.get(CONTROLLER);
        assertThat(mappingViolations(controllerSource + "\n@PutMapping(\"/backups/retention\")")).as("多一個 @PutMapping").isNotEmpty();
        assertThat(mappingViolations(controllerSource.replace("@PostMapping(\"/backups/jobs\")", ""))).as("少一個 @PostMapping").isNotEmpty();
        assertThat(mappingViolations(controllerSource + "\n@DeleteMapping")).as("多一個 @DeleteMapping").isNotEmpty();
        assertThat(mappingViolations(controllerSource + "\n@RequestMapping(method = RequestMethod.PUT)")).as("帶 method 的 @RequestMapping").isNotEmpty();
    }

    // ── AT-BK-10-4-3 ──────────────────────────────────────────────────────────────────────────

    @Test
    void AT_BK_10_4_3_theBackupClassesHaveNoSecretsNoProcessStartAndNoNetworkCalls() {
        Map<String, String> sources = mainSources();
        Map<String, String> backup = new TreeMap<>();
        sources.forEach((path, text) -> {
            if (isBackupRelated(path)) {
                backup.put(path, text);
            }
        });
        assertThat(backup.size()).as("防反空轉：Backup* 類別數").isGreaterThanOrEqualTo(20);
        backup.forEach((path, text) -> assertThat(trustBoundaryViolations(text)).as(path).isEmpty());
        // 全部主程式碼與資源：機密的環境變數名與 docker.sock 不得出現在 backup 相關類別之外的任何設定
        mainResources().forEach((path, text) -> {
            for (String banned : List.of("PGBACKREST_CIPHER_PASS", "AWS_SECRET_ACCESS_KEY", "MC_HOST", "docker.sock")) {
                assertThat(text).as(path).doesNotContain(banned);
            }
        });

        for (String bad : List.of("PGBACKREST_CIPHER_PASS", "AWS_SECRET_ACCESS_KEY", "MC_HOST", "docker.sock", "new ProcessBuilder(cmd)",
                "Runtime.getRuntime().exec(cmd)", "java.net.http.HttpClient", "new RestTemplate()")) {
            assertThat(trustBoundaryViolations("class X { Object o = \"" + bad + "\"; " + bad + " }")).as("合成樣本 " + bad).isNotEmpty();
        }
        assertThat(trustBoundaryViolations("class X { Path p = Files.createTempFile(); }")).isEmpty();
    }

    // ── AT-BK-10-4-S-1 ────────────────────────────────────────────────────────────────────────

    /**
     * AT-BK-10-4-S-1（TCS 無此編號的補 AT，SCG-4 勘誤納入；對應 AC-BK-10-4／R-BK-58 的「任何日誌行不含機密」）。測試類型：ArchUnit 同檔的原始碼掃描（BA 載具）。
     *
     * <p>WHY（SCG-4 二審 R2-01）：一審 F3 只把八處資料庫例外日誌改成經 {@code BackupMasker.mask}，二審實查另有十處（{@code BackupJobService}、
     * {@code BackupJobReconciler}、{@code BackupQueryService}、{@code FileBackupControlAdapter}）仍把 {@code e.toString()}／{@code e.getMessage()}
     * 直接寫進日誌——例外訊息可能夾帶被解析內容的片段、檔案路徑或連線字串，集中式日誌就成了遮罩的旁路。逐處補行為測試是「再漏一處就再補一次」，
     * 所以改成結構鎖，任何新的或被還原的站點一律轉紅。
     *
     * <p>掃描範圍＝{@code isBackupRelated}（路徑含 /backup/、檔名含 Backup、或檔名以 WalArchive 起頭；與 AT-BK-10-4-3 同一判準），現況有 LOG 呼叫的是
     * 上述四個類別；範圍外的類別（含全域例外處理器）不在此鎖，所以既有非 backup 類別不會被牽連。判準：每個 {@code LOG.<level>(…)} 呼叫在去掉所有
     * {@code BackupMasker.mask(…)} 群組之後，參數裡不得還剩 {@code .toString()}／{@code .getMessage()}／{@code .getLocalizedMessage()}（不分接收者：
     * 免得「這個是不是例外」變成人工判斷），也不得直接帶例外變數（catch 參數與型別名以 Exception／Error／Throwable 結尾的變數）。
     * 誠實劃界：只看 LOG 呼叫的參數文字——先存進區域變數再傳入、或經其他輔助方法再傳入的例外文字掃不到；也不涵蓋 {@code printStackTrace}
     * 與 SLF4J 的 fluent API（backup 類別現況皆不用）。
     *
     * <p>判定指令：{@code .\gradlew.bat test --tests "*BackupArchTest.AT_BK_10_4_S_1_*"}。負控：各種違規寫法的合成樣本必須回非空、合規寫法必須回空。
     */
    @Test
    void AT_BK_10_4_S_1_everyBackupLogCallThatCarriesAnExceptionMasksItWithBackupMaskerFirst() {
        Map<String, String> scanned = new TreeMap<>();
        mainSources().forEach((path, text) -> {
            if (isBackupRelated(path)) {
                scanned.put(path, text);
            }
        });
        assertThat(scanned.keySet()).as("防反空轉：有 LOG 呼叫的四個類別都在掃描範圍")
                .contains("com/aisdlc/console/application/service/BackupJobService.java", "com/aisdlc/console/application/service/BackupJobReconciler.java",
                        "com/aisdlc/console/application/service/BackupQueryService.java", "com/aisdlc/console/adapter/out/control/FileBackupControlAdapter.java");
        List<String> violations = new ArrayList<>();
        scanned.forEach((path, text) -> logLeakViolations(text).forEach(violation -> violations.add(path + "：" + violation)));
        assertThat(violations).as("backup 相關類別的 LOG 呼叫不得讓例外文字繞過 BackupMasker（一次列出全部站點）").isEmpty();
        // 防反空轉（違規為空時才有意義，所以排在違規斷言之後：真有外洩站點時，失敗訊息先點名站點）：掃描器真的認得出這些呼叫
        List<LogCall> calls = scanned.values().stream().flatMap(text -> logCalls(text).stream()).toList();
        assertThat(calls.size()).as("防反空轉：掃到的 LOG 呼叫數（下限＝現況 21）").isGreaterThanOrEqualTo(21);
        assertThat(calls.stream().filter(call -> call.arguments() != null && EXCEPTION_TEXT.matcher(call.arguments()).find()).count())
                .as("防反空轉：其中帶例外文字的呼叫數（下限＝現況 18）").isGreaterThanOrEqualTo(18);

        // 負控：各種違規寫法的合成樣本都回非空（catch 內的 e、方法參數的 cause 兩種例外變數來源）
        String inCatch = "class X { void f() { try { run(); } catch (IOException e) { %s } } }";
        for (String bad : List.of("LOG.warn(\"x {}\", e.toString());", "LOG.warn(\"x {}\", e.getMessage());", "LOG.warn(\"x\", e);",
                "LOG.warn(\"x {} {}\", id, e.toString());", "LOG.warn(\"x {}\", String.valueOf(e));",
                "LOG.error(\"x {} {}\", BackupMasker.mask(e.toString()), e.getMessage());", "log.info(\"x {}\", e.getLocalizedMessage());",
                "LOG.info(\"p {}\", path.toString());")) {
            assertThat(logLeakViolations(inCatch.formatted(bad))).as("違規樣本 " + bad).isNotEmpty();
        }
        assertThat(logLeakViolations(inCatch.formatted("LOG.warn(\"x {}\", BackupMasker.mask(e.toString());"))).as("括號不成對：讀不懂也要回報").isNotEmpty();
        for (String bad : List.of("LOG.warn(\"x {}\", cause.toString());", "LOG.warn(\"x\", cause);")) {
            assertThat(logLeakViolations("class X { static void f(RuntimeException cause) { " + bad + " } }")).as("違規樣本 " + bad).isNotEmpty();
        }
        assertThat(logLeakViolations("class X { void f() { try { run(); } catch (SchemaProblem p) { LOG.warn(\"x\", p); } } }"))
                .as("型別名不像例外的 catch 參數（BackupQueryService 的 SchemaProblem 就是這型）直接進日誌").isNotEmpty();
        // 合規樣本都回空（遮罩群組含巢狀括號；不含例外的日誌；字串常值裡寫到 e.toString() 不算）
        for (String good : List.of("LOG.warn(\"x {}\", BackupMasker.mask(e.toString()));", "LOG.warn(\"x {} {}\", id, BackupMasker.mask(e.getMessage()));",
                "LOG.warn(\"x {}\", BackupMasker.mask(String.valueOf(e)));", "LOG.info(\"不含例外的日誌 {}\", removed);",
                "LOG.warn(\"字串裡寫 e.toString() 與 e 都不算：{}\", id);")) {
            assertThat(logLeakViolations(inCatch.formatted(good))).as("合規樣本 " + good).isEmpty();
        }
    }
}
