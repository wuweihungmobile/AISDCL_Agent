package com.aisdlc.console.architecture;

import com.aisdlc.console.application.service.BackupJobService;
import com.aisdlc.console.application.service.BackupQueryService;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.model.backup.BackupJobReason;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * backup 類 reason 的雙向鎖（TCS-SysAdminBackup-20261027 R-BK-60、B-24；AT-BK-06-5-4、AT-BK-06-5-E-2 的後端半）。為什麼重要：十三個 reason 的中文訊息要在三處逐字相同——
 * 契約表、前端 {@code BACKUP_REASONS}、後端（五個 API 錯誤的 {@code message} 與八個工作理由列舉）——只要有一處差一個字，畫面就會對掌舵者說出與契約不同的話；
 * 它們刻意<b>不進</b> {@code reasons.ts}（那個檔與 P3-6 附錄 B 雙向鎖，動它會連動凍結契約），所以這道鎖是唯一的守衛。
 * 後端的鎖：{@link ErrorReasons} 的 {@code BACKUP_} 前綴常數集合與契約表「狀態碼」欄為數字的列<b>雙向相等</b>（恰五個）、{@link BackupJobReason} 的值集合與
 * 狀態碼欄為「—」的列雙向相等（恰八個）、每個 reason 的中文訊息與表的「中文訊息」欄逐字相同；{@code BackupApiIT} 另以本類別的解析函式驗 400、404、409、503 的實際本文。
 *
 * <p>契約表的解析規則（B-24；同議題中心）：以標題 {@code backup 類 reason 表} 起頭的<b>第一張</b>表為準（標題之前的他表、標題之後的第二張表都不影響結果）；欄序固定
 * （{@value #COLUMNS_TEXT}），欄序對調、多一列、少一列、訊息差一字都使比對回報問題；找不到標題或表就丟 {@link IllegalStateException}（鎖不得因缺表而空過）。
 */
public class BackupReasonsContractTest {

    static final String COLUMNS_TEXT = "reason｜狀態碼｜details｜中文訊息｜意義";
    public static final List<String> COLUMNS = List.of("reason", "狀態碼", "details", "中文訊息", "意義");
    private static final Pattern HEADING = Pattern.compile("^#{1,6}\\s*backup 類 reason 表");

    // ── 契約表的解析與比對（純函式；BackupApiIT 也用）──────────────────────────────────────────

    /** 契約檔相對 backend 專案目錄（Gradle 測試的工作目錄）的位置。 */
    public static Path contractPath() {
        return Path.of("..", "docs", "02_architecture", "API_Contract_SysAdminBackup.md");
    }

    public static String readContract() {
        try {
            return Files.readString(contractPath(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new java.io.UncheckedIOException("讀不到契約檔 " + contractPath().toAbsolutePath().normalize(), e);
        }
    }

    /** 解析後的表：標題列的欄名與每列（reason → 列的全部欄）。 */
    public record Table(List<String> header, Map<String, List<String>> rows) {

        /** reason → 中文訊息（第四欄）。 */
        public Map<String, String> messages() {
            Map<String, String> out = new LinkedHashMap<>();
            rows.forEach((reason, cells) -> out.put(reason, cells.size() > 3 ? cells.get(3) : ""));
            return out;
        }

        /** 狀態碼欄為數字者（API 錯誤 reason）：reason → 狀態碼文字。 */
        public Map<String, String> apiStatuses() {
            Map<String, String> out = new TreeMap<>();
            rows.forEach((reason, cells) -> {
                String status = cells.size() > 1 ? cells.get(1) : "";
                if (status.matches("[0-9]+")) {
                    out.put(reason, status);
                }
            });
            return out;
        }

        /** 狀態碼欄為「—」者（工作理由）的 reason 集合。 */
        public TreeSet<String> jobReasons() {
            TreeSet<String> out = new TreeSet<>(rows.keySet());
            out.removeAll(apiStatuses().keySet());
            return out;
        }
    }

    /** 解析標題後的第一張表；找不到標題或表就丟 {@link IllegalStateException}。 */
    public static Table parse(String markdown) {
        String[] lines = markdown.split("\r?\n", -1);
        int heading = -1;
        for (int i = 0; i < lines.length; i++) {
            if (HEADING.matcher(lines[i]).find()) {
                heading = i;
                break;
            }
        }
        if (heading < 0) {
            throw new IllegalStateException("找不到標題「backup 類 reason 表」");
        }
        int start = -1;
        for (int i = heading + 1; i < lines.length; i++) {
            if (lines[i].startsWith("|")) {
                start = i;
                break;
            }
        }
        if (start < 0) {
            throw new IllegalStateException("標題「backup 類 reason 表」之後沒有表格");
        }
        List<List<String>> tableRows = new ArrayList<>();
        for (int i = start; i < lines.length && lines[i].startsWith("|"); i++) {
            tableRows.add(cells(lines[i]));
        }
        if (tableRows.size() < 2) {
            throw new IllegalStateException("表格缺標題列或分隔列");
        }
        Map<String, List<String>> rows = new LinkedHashMap<>();
        for (List<String> row : tableRows.subList(2, tableRows.size())) {
            rows.put(stripCode(row.get(0)), row);
        }
        return new Table(tableRows.get(0), rows);
    }

    /** 一列的各欄（去頭尾 {@code |}、逐欄去空白；欄內以 {@code \|} 跳脫的豎線保留成 {@code |}）。 */
    private static List<String> cells(String line) {
        String body = line.strip();
        body = body.substring(1, body.endsWith("|") ? body.length() - 1 : body.length());
        List<String> out = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        for (int i = 0; i < body.length(); i++) {
            char c = body.charAt(i);
            if (c == '\\' && i + 1 < body.length() && body.charAt(i + 1) == '|') {
                current.append('|');
                i++;
            } else if (c == '|') {
                out.add(current.toString().strip());
                current.setLength(0);
            } else {
                current.append(c);
            }
        }
        out.add(current.toString().strip());
        return out;
    }

    private static String stripCode(String cell) {
        Matcher matcher = Pattern.compile("^`(.*)`$").matcher(cell);
        return matcher.matches() ? matcher.group(1) : cell;
    }

    /**
     * 契約表對程式碼端的比對：欄序、API reason 集合與狀態碼（雙向）、工作理由集合（雙向）、每個 reason 的中文訊息逐字相同。回問題清單（空＝一致）。
     *
     * @param api 程式碼端的 API 錯誤：reason → 中文訊息
     * @param job 程式碼端的工作理由：reason → 中文訊息
     */
    public static List<String> problems(Table contract, Map<String, String> api, Map<String, Integer> apiStatus, Map<String, String> job) {
        List<String> problems = new ArrayList<>();
        if (!contract.header().equals(COLUMNS)) {
            problems.add("欄序不符：契約表為 " + contract.header() + "，應為 " + COLUMNS);
        }
        Map<String, String> contractApi = contract.apiStatuses();
        compareSets("API 錯誤 reason", new TreeSet<>(contractApi.keySet()), new TreeSet<>(api.keySet()), problems);
        compareSets("工作理由", contract.jobReasons(), new TreeSet<>(job.keySet()), problems);
        Map<String, String> messages = contract.messages();
        Map<String, String> expected = new LinkedHashMap<>(api);
        expected.putAll(job);
        expected.forEach((reason, message) -> {
            if (messages.containsKey(reason) && !messages.get(reason).equals(message)) {
                problems.add("中文訊息不符（" + reason + "）：契約表「" + messages.get(reason) + "」，程式碼「" + message + "」");
            }
        });
        apiStatus.forEach((reason, status) -> {
            if (contractApi.containsKey(reason) && !contractApi.get(reason).equals(String.valueOf(status))) {
                problems.add("狀態碼不符（" + reason + "）：契約表 " + contractApi.get(reason) + "，程式碼 " + status);
            }
        });
        return problems;
    }

    private static void compareSets(String what, TreeSet<String> inContract, TreeSet<String> inCode, List<String> problems) {
        TreeSet<String> onlyInContract = new TreeSet<>(inContract);
        onlyInContract.removeAll(inCode);
        TreeSet<String> onlyInCode = new TreeSet<>(inCode);
        onlyInCode.removeAll(inContract);
        onlyInContract.forEach(reason -> problems.add(what + "：契約表有、程式碼沒有：" + reason));
        onlyInCode.forEach(reason -> problems.add(what + "：程式碼有、契約表沒有：" + reason));
    }

    // ── 程式碼端 ────────────────────────────────────────────────────────────────────────────

    /** 程式碼端的 identifier → 中文訊息（新增 {@code BACKUP_} 常數而沒補這張表，下面的集合鎖會紅）。 */
    private static final Map<String, String> MESSAGES_BY_IDENTIFIER = Map.of(
            "BACKUP_CONTROL_UNAVAILABLE", BackupJobService.CONTROL_UNAVAILABLE_MESSAGE,
            "BACKUP_CONFIRM_REQUIRED", BackupJobService.CONFIRM_REQUIRED_MESSAGE,
            "BACKUP_JOB_IN_PROGRESS", BackupJobService.IN_PROGRESS_MESSAGE,
            "BACKUP_TOO_FREQUENT", BackupJobService.TOO_FREQUENT_MESSAGE,
            "BACKUP_JOB_NOT_FOUND", BackupQueryService.JOB_NOT_FOUND_MESSAGE);

    /** 各 API 錯誤的 HTTP 狀態碼（契約 C3.4 的驗證序表與〈backup 類 reason 表〉的狀態碼欄）。 */
    private static final Map<String, Integer> STATUS_BY_IDENTIFIER = Map.of(
            "BACKUP_CONTROL_UNAVAILABLE", 503, "BACKUP_CONFIRM_REQUIRED", 400, "BACKUP_JOB_IN_PROGRESS", 409,
            "BACKUP_TOO_FREQUENT", 409, "BACKUP_JOB_NOT_FOUND", 404);

    /** {@code ErrorReasons} 的 {@code BACKUP_} 前綴常數：identifier → reason 值。 */
    private static Map<String, String> backupConstants() throws IllegalAccessException {
        Map<String, String> out = new TreeMap<>();
        for (Field field : ErrorReasons.class.getDeclaredFields()) {
            if (field.getName().startsWith("BACKUP_") && Modifier.isStatic(field.getModifiers()) && field.getType() == String.class) {
                out.put(field.getName(), (String) field.get(null));
            }
        }
        return out;
    }

    /** reason → 中文訊息（API 錯誤）。 */
    public static Map<String, String> apiMessages() throws IllegalAccessException {
        Map<String, String> constants = backupConstants();
        assertThat(new TreeSet<>(MESSAGES_BY_IDENTIFIER.keySet())).as("identifier 集合：ErrorReasons 的 BACKUP_ 前綴常數與本測試的訊息表雙向相等")
                .isEqualTo(new TreeSet<>(constants.keySet()));
        Map<String, String> byReason = new LinkedHashMap<>();
        constants.forEach((identifier, reason) -> byReason.put(reason, MESSAGES_BY_IDENTIFIER.get(identifier)));
        return byReason;
    }

    private static Map<String, Integer> apiStatuses() throws IllegalAccessException {
        Map<String, Integer> byReason = new LinkedHashMap<>();
        backupConstants().forEach((identifier, reason) -> byReason.put(reason, STATUS_BY_IDENTIFIER.get(identifier)));
        return byReason;
    }

    /** 同 {@link #apiMessages()}，但把受檢的反射例外包成未檢查例外（整合測試的斷言用）。 */
    public static Map<String, String> apiMessagesUnchecked() {
        try {
            return apiMessages();
        } catch (IllegalAccessException e) {
            throw new IllegalStateException(e);
        }
    }

    /** reason → 中文訊息（工作理由列舉）。 */
    public static Map<String, String> jobMessages() {
        Map<String, String> out = new LinkedHashMap<>();
        for (BackupJobReason reason : BackupJobReason.values()) {
            out.put(reason.value(), reason.message());
        }
        return out;
    }

    @Test
    void AT_BK_06_5_4_theApiReasonConstantsTheJobReasonEnumAndTheContractTableAreEqualBothWaysAndMessagesVerbatim() throws IllegalAccessException {
        Table contract = parse(readContract());

        assertThat(problems(contract, apiMessages(), apiStatuses(), jobMessages())).as("契約表與程式碼端雙向相等").isEmpty();

        assertThat(contract.rows().keySet()).as("防反空轉：契約表恰十三列").hasSize(13);
        assertThat(contract.apiStatuses().keySet()).as("狀態碼欄為數字者恰五個").containsExactlyInAnyOrder("backup_control_unavailable",
                "backup_confirm_required", "backup_job_in_progress", "backup_too_frequent", "backup_job_not_found");
        assertThat(contract.jobReasons()).as("狀態碼欄為「—」者恰八個").containsExactly("busy", "control_write_failed", "expired", "interrupted",
                "lock_timeout", "rejected_invalid", "script_failed", "timeout");
        assertThat(apiMessages()).as("五個 API 錯誤").hasSize(5);
        assertThat(jobMessages()).as("八個工作理由").hasSize(8);
        assertThat(contract.messages().get("busy")).isEqualTo("排程工作執行中，稍後再試");
        assertThat(jobMessages().get("busy")).isEqualTo("排程工作執行中，稍後再試");
        assertThat(ErrorReasons.BACKUP_JOB_NOT_FOUND).isEqualTo("backup_job_not_found");
        assertThat(contract.rows().containsKey("invalid_request")).as("invalid_request 以區域常數持有、不入表").isFalse();
    }

    // ── AT-BK-06-5-E-2（後端半）：合成契約字串的負控 ──────────────────────────────────────────

    private static final String OTHER_TABLE = "| a | b |\n|---|---|\n| x | y |\n";
    private static final String HEADER = "| reason | 狀態碼 | details | 中文訊息 | 意義 |\n|---|---|---|---|---|\n";
    private static final String HEADING_LINE = "### backup 類 reason 表\n\n";

    /** 與真實契約表等價的十三列（用來造「少一列、多一列、差一字」的變體）。 */
    private static String rows() throws IllegalAccessException {
        StringBuilder out = new StringBuilder();
        Map<String, String> api = apiMessages();
        Map<String, Integer> statuses = apiStatuses();
        api.forEach((reason, message) -> out.append("| `").append(reason).append("` | ").append(statuses.get(reason)).append(" | — | ")
                .append(message).append(" | 意義 |\n"));
        jobMessages().forEach((reason, message) -> out.append("| `").append(reason).append("` | — | — | ").append(message).append(" | 意義 |\n"));
        return out.toString();
    }

    private static String doc(String beforeHeading, String table, String afterTable) {
        return "# 契約\n\n" + beforeHeading + HEADING_LINE + table + "\n" + afterTable;
    }

    @Test
    void AT_BK_06_5_E_2_theBrokenSyntheticTablesAreFlaggedAndTheDecoyTablesDoNotMatter() throws IllegalAccessException {
        Map<String, String> api = apiMessages();
        Map<String, Integer> statuses = apiStatuses();
        Map<String, String> job = jobMessages();
        String good = HEADER + rows();
        assertThat(problems(parse(doc("", good, "")), api, statuses, job)).as("合成的好表本身與真程式碼一致").isEmpty();

        Map<String, String> broken = new LinkedHashMap<>();
        broken.put("(a) 多一列", doc("", good + "| `backup_extra` | 409 | — | 多出的 | x |\n", ""));
        broken.put("(b) 少一列", doc("", good.replace("| `busy` | — | — | 排程工作執行中，稍後再試 | 意義 |\n", ""), ""));
        broken.put("(c) 訊息差一字", doc("", good.replace("備份控制面目前無法使用", "備份控制面目前無法運用"), ""));
        broken.put("(d) 欄序對調", doc("", good.replace("| reason | 狀態碼 |", "| 狀態碼 | reason |"), ""));
        broken.put("(c2) 工作理由訊息差一字", doc("", good.replace("請求逾時未被執行", "請求逾時沒被執行"), ""));
        broken.put("(c3) 狀態碼不符", doc("", good.replace("| `backup_job_not_found` | 404 |", "| `backup_job_not_found` | 422 |"), ""));
        broken.forEach((label, markdown) -> assertThat(problems(parse(markdown), api, statuses, job)).as(label).isNotEmpty());

        String decoys = doc("## 他表\n\n" + OTHER_TABLE + "\n", good,
                "### 第二張表\n\n| reason | 狀態碼 | details | 中文訊息 | 意義 |\n|---|---|---|---|---|\n| `bogus` | 500 | — | 不該被讀到 | x |\n");
        assertThat(problems(parse(decoys), api, statuses, job)).as("(e) 標題之前的他表、標題之後的第二張表都不影響結果（只取標題後第一張表）").isEmpty();
    }

    @Test
    void AT_BK_06_5_E_2_aMissingHeadingOrTableFailsLoudlyInsteadOfPassingVacuously() {
        assertThatThrownBy(() -> parse("# 沒有標題\n\n" + HEADER)).as("(f) 沒有標題").isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> parse("### backup 類 reason 表\n\n沒有表格\n")).as("(g) 標題之後沒有表格").isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> parse("### backup 類 reason 表\n\n| a |\n")).as("表格缺分隔列").isInstanceOf(IllegalStateException.class);
    }
}
