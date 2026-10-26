package com.aisdlc.console.architecture;

import com.aisdlc.console.application.service.IssuePriorityService;
import com.aisdlc.console.domain.exception.ErrorReasons;
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
 * 議題中心 reason 的雙向鎖（TCS-IssueCenter-20261027 R-IC-61、D-C5、B-24；AT-IC-07-9-2、AT-IC-07-9-E-1 的後端半）。
 * 為什麼重要：{@code issue_not_rankable} 的中文訊息要在三處逐字相同——契約表、前端 {@code ISSUE_REASONS}、後端 409 的 {@code message}——只要有一處差一個字，
 * 畫面就會對使用者說出與契約不同的話；它刻意<b>不進</b> {@code reasons.ts}（那個檔與 P3-6 附錄 B 雙向鎖，動它會連動凍結契約），所以這道鎖是它唯一的守衛。
 * 後端的鎖：{@link ErrorReasons} 的 {@code ISSUE_} 前綴常數集合與契約表的 reason 欄雙向相等，409 的訊息常數與表的「中文訊息」欄逐字相同；
 * {@code IssueApiIT} 另以本類別的解析函式驗 409 的實際本文。
 *
 * <p>契約表的解析規則（B-24）：以標題 {@code issue 類 reason 表} 起頭的<b>第一張</b>表為準（標題之前的他表、標題之後的第二張表都不影響結果）；欄序固定
 * （{@value #COLUMNS_TEXT}），欄序對調、多一列、少一列、訊息差一字都使比對回報問題。
 */
public class IssueReasonsContractTest {

    static final String COLUMNS_TEXT = "reason｜狀態碼｜details｜中文訊息｜意義";
    public static final List<String> COLUMNS = List.of("reason", "狀態碼", "details", "中文訊息", "意義");
    private static final Pattern HEADING = Pattern.compile("^#{1,6}\\s*issue 類 reason 表");

    // ── 契約表的解析與比對（純函式；IssueApiIT 也用）──────────────────────────────────────────

    /** 契約檔相對 backend 專案目錄（Gradle 測試的工作目錄）的位置。 */
    public static Path contractPath() {
        return Path.of("..", "docs", "02_architecture", "API_Contract_IssueCenter.md");
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
    }

    /** 解析標題後的第一張表；找不到標題或表就丟 {@link IllegalStateException}（鎖不得因缺表而空過）。 */
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
            throw new IllegalStateException("找不到標題「issue 類 reason 表」");
        }
        int start = -1;
        for (int i = heading + 1; i < lines.length; i++) {
            if (lines[i].startsWith("|")) {
                start = i;
                break;
            }
        }
        if (start < 0) {
            throw new IllegalStateException("標題「issue 類 reason 表」之後沒有表格");
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
     * 契約表對程式碼端的比對：欄序、reason 集合（雙向）、每個 reason 的中文訊息逐字相同。回問題清單（空＝一致）。
     *
     * @param code 程式碼端的 reason → 中文訊息
     */
    public static List<String> problems(Table contract, Map<String, String> code) {
        List<String> problems = new ArrayList<>();
        if (!contract.header().equals(COLUMNS)) {
            problems.add("欄序不符：契約表為 " + contract.header() + "，應為 " + COLUMNS);
        }
        TreeSet<String> onlyInContract = new TreeSet<>(contract.rows().keySet());
        onlyInContract.removeAll(code.keySet());
        TreeSet<String> onlyInCode = new TreeSet<>(code.keySet());
        onlyInCode.removeAll(contract.rows().keySet());
        onlyInContract.forEach(reason -> problems.add("契約表有、程式碼沒有：" + reason));
        onlyInCode.forEach(reason -> problems.add("程式碼有、契約表沒有：" + reason));
        Map<String, String> messages = contract.messages();
        code.forEach((reason, message) -> {
            if (messages.containsKey(reason) && !messages.get(reason).equals(message)) {
                problems.add("中文訊息不符（" + reason + "）：契約表「" + messages.get(reason) + "」，程式碼「" + message + "」");
            }
        });
        return problems;
    }

    // ── 程式碼端 ────────────────────────────────────────────────────────────────────────────

    /** 程式碼端的 identifier → 中文訊息（新增 {@code ISSUE_} 常數而沒補這張表，下面的集合鎖會紅）。 */
    private static final Map<String, String> MESSAGES_BY_IDENTIFIER = Map.of(
            "ISSUE_NOT_RANKABLE", IssuePriorityService.NOT_RANKABLE_MESSAGE);

    /** {@code ErrorReasons} 的 {@code ISSUE_} 前綴常數：identifier → reason 值。 */
    private static Map<String, String> issueConstants() throws IllegalAccessException {
        Map<String, String> out = new TreeMap<>();
        for (Field field : ErrorReasons.class.getDeclaredFields()) {
            if (field.getName().startsWith("ISSUE_") && Modifier.isStatic(field.getModifiers()) && field.getType() == String.class) {
                out.put(field.getName(), (String) field.get(null));
            }
        }
        return out;
    }

    private static Map<String, String> codeSide() throws IllegalAccessException {
        Map<String, String> constants = issueConstants();
        assertThat(new TreeSet<>(MESSAGES_BY_IDENTIFIER.keySet())).as("identifier 集合：ErrorReasons 的 ISSUE_ 前綴常數與本測試的訊息表雙向相等")
                .isEqualTo(new TreeSet<>(constants.keySet()));
        Map<String, String> byReason = new LinkedHashMap<>();
        constants.forEach((identifier, reason) -> byReason.put(reason, MESSAGES_BY_IDENTIFIER.get(identifier)));
        return byReason;
    }

    @Test
    void AT_IC_07_9_2_theIssueReasonConstantsAndTheContractTableAreEqualBothWaysAndTheMessageIsVerbatim() throws IllegalAccessException {
        Table contract = parse(readContract());

        Map<String, String> code = codeSide();

        assertThat(problems(contract, code)).as("契約表與程式碼端雙向相等").isEmpty();
        assertThat(contract.rows().keySet()).as("防反空轉：契約表至少有一個 reason").isNotEmpty().containsExactly("issue_not_rankable");
        assertThat(code).containsEntry("issue_not_rankable", "此議題目前的狀態不能設定優先順序");
        assertThat(contract.messages().get("issue_not_rankable")).as("契約表的中文訊息").isEqualTo("此議題目前的狀態不能設定優先順序");
        assertThat(ErrorReasons.ISSUE_NOT_RANKABLE).isEqualTo("issue_not_rankable");
    }

    // ── AT-IC-07-9-E-1（後端半）：五種合成契約字串各得預期結果 ─────────────────────────────────────

    private static final String OTHER_TABLE = "| a | b |\n|---|---|\n| x | y |\n";
    private static final String HEADER = "| reason | 狀態碼 | details | 中文訊息 | 意義 |\n|---|---|---|---|---|\n";
    private static final String ROW = "| `issue_not_rankable` | 409 | `id`、`status` | 此議題目前的狀態不能設定優先順序 | 不可排 |\n";
    private static final String HEADING_LINE = "### issue 類 reason 表（C5.1）\n\n";

    private static String doc(String beforeHeading, String table, String afterTable) {
        return "# 契約\n\n" + beforeHeading + HEADING_LINE + table + "\n" + afterTable;
    }

    @Test
    void AT_IC_07_9_E_1_theFourBrokenSyntheticTablesAreFlaggedAndTheDecoyTablesDoNotMatter() throws IllegalAccessException {
        Map<String, String> code = codeSide();
        Map<String, String> broken = new LinkedHashMap<>();
        broken.put("多一列", doc("", HEADER + ROW + "| `issue_extra` | 409 | | 多出的 | x |\n", ""));
        broken.put("少一列", doc("", HEADER, ""));
        broken.put("訊息差一字", doc("", HEADER + ROW.replace("優先順序", "優先順位"), ""));
        broken.put("欄序對調", doc("", "| 狀態碼 | reason | details | 中文訊息 | 意義 |\n|---|---|---|---|---|\n"
                + "| 409 | `issue_not_rankable` | `id`、`status` | 此議題目前的狀態不能設定優先順序 | 不可排 |\n", ""));

        broken.forEach((label, markdown) -> assertThat(problems(parse(markdown), code)).as(label).isNotEmpty());

        String decoys = doc("## 他表\n\n" + OTHER_TABLE + "\n", HEADER + ROW,
                "### 第二張表\n\n| reason | 狀態碼 | details | 中文訊息 | 意義 |\n|---|---|---|---|---|\n| `bogus` | 500 | | 不該被讀到 | x |\n");
        assertThat(problems(parse(decoys), code)).as("標題之前的他表、標題之後的第二張表都不影響結果（只取標題後第一張表）").isEmpty();
    }

    @Test
    void AT_IC_07_9_E_1_aMissingHeadingOrTableFailsLoudlyInsteadOfPassingVacuously() {
        assertThatThrownBy(() -> parse("# 沒有標題\n\n" + HEADER + ROW)).isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> parse("### issue 類 reason 表\n\n沒有表格\n")).isInstanceOf(IllegalStateException.class);
    }
}
