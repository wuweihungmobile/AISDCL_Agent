package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violation;
import com.aisdlc.console.domain.exception.Violations;
import com.aisdlc.console.domain.service.SddFreezeRules.Checked;
import org.junit.jupiter.api.Test;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 核准凍結請求的值規則（契約 §1.10.2「Request」）。為什麼重要：這些規則是 Console 在「呼叫任何 Bridge 之前」唯一能擋的東西——
 * 理由不得靜默截斷（它會寫進 FSM 稽核）、docs 不得是絕對路徑或跑出專案根（Bridge 是第二道，不是第一道）、已綁定的規格檔必須在 docs 內
 * （否則核准人凍結的不是匯入時看的那份）；違規一律累積成 400 並指名欄位。
 */
class SddFreezeRulesTest {

    private static final String ROOT = "/work/proj";
    private static final String DIGEST = "sha256:" + "a".repeat(64);
    private static final List<String> DOCS = List.of("docs/TCS-A.md");

    private static Checked ok(String reason, String stage, List<String> docs, Map<String, String> digests, String specFile) {
        Violations v = new Violations();
        Checked checked = SddFreezeRules.check(v, reason, stage, docs, digests, ROOT, specFile);
        v.throwIfAny();
        return checked;
    }

    private static List<String> fields(String reason, String stage, List<String> docs, Map<String, String> digests,
                                       String specFile) {
        try {
            ok(reason, stage, docs, digests, specFile);
        } catch (ValidationException e) {
            return e.violations().stream().map(Violation::field).toList();
        }
        return List.of();
    }

    // ── reason ────────────────────────────────────────────────────────────────

    @Test
    void theReasonIsStrippedAndTakenVerbatimOtherwise() {
        assertThat(ok("  規格已核准  ", null, DOCS, null, null).reason()).isEqualTo("規格已核准");
        assertThat(ok("x".repeat(500), null, DOCS, null, null).reason()).hasSize(500);
    }

    @Test
    void aBlankLongOrControlCharReasonIsRejectedNeverTruncated() {
        assertThat(fields(null, null, DOCS, null, null)).containsExactly("reason");
        assertThat(fields("   ", null, DOCS, null, null)).containsExactly("reason");
        assertThat(fields("x".repeat(501), null, DOCS, null, null)).containsExactly("reason");
        assertThat(fields("第一行\n第二行", null, DOCS, null, null)).containsExactly("reason");
        assertThat(fields("a\tb", null, DOCS, null, null)).containsExactly("reason");
        assertThat(fields("  " + "x".repeat(501) + "  ", null, DOCS, null, null)).as("strip 後仍超過").containsExactly("reason");
    }

    // ── stage ─────────────────────────────────────────────────────────────────

    @Test
    void theStageIsOptionalAndFollowsTheDocumentedPattern() {
        assertThat(ok("r", null, DOCS, null, null).stage()).isNull();
        assertThat(ok("r", "Stage-1.a_b", DOCS, null, null).stage()).isEqualTo("Stage-1.a_b");
        assertThat(ok("r", "x".repeat(64), DOCS, null, null).stage()).hasSize(64);
        for (String bad : List.of("", "bad stage", "階段", "x".repeat(65), "a/b")) {
            assertThat(fields("r", bad, DOCS, null, null)).as(bad).containsExactly("stage");
        }
    }

    // ── docs ──────────────────────────────────────────────────────────────────

    @Test
    void docsAreNormalizedToRelativePosixPaths() {
        Checked checked = ok("r", null, List.of("./docs//a.md", "docs\\sub\\b.md", "c.md"), null, null);

        assertThat(checked.docs()).containsExactly("docs/a.md", "docs/sub/b.md", "c.md");
    }

    @Test
    void absoluteTraversalBlankAndControlCharacterPathsAreRejectedPerEntry() {
        for (String bad : List.of("/etc/passwd", "C:\\Windows\\x.md", "c:/x.md", "\\\\server\\share\\x.md", "../x.md",
                "a/../../b.md", "docs/..", "", "   ", ".", "./", "a\nb.md", "x".repeat(501))) {
            assertThat(fields("r", null, List.of("docs/ok.md", bad), null, null)).as("[" + bad + "]")
                    .containsExactly("docs[1]");
        }
        assertThat(fields("r", null, Collections.singletonList(null), null, null)).containsExactly("docs[0]");
    }

    @Test
    void theListMustHaveOneToTwentyEntries() {
        assertThat(fields("r", null, List.of(), null, null)).containsExactly("docs");
        assertThat(fields("r", null, Collections.nCopies(21, "a.md"), null, null)).containsExactly("docs");
        assertThat(ok("r", null, Collections.nCopies(20, "a.md"), null, null).docs()).hasSize(20);
    }

    @Test
    void omittedDocsDefaultToTheBoundSpecFileRelativeToTheRoot() {
        assertThat(ok("r", null, null, null, ROOT + "/docs/TCS-Bound.md").docs()).containsExactly("docs/TCS-Bound.md");
        assertThat(ok("r", null, null, null, ROOT + "//docs\\TCS-Bound.md").docs()).as("分隔符不拘")
                .containsExactly("docs/TCS-Bound.md");
    }

    @Test
    void omittedDocsWithoutAUsableSpecFileIsAnErrorOnDocs() {
        assertThat(fields("r", null, null, null, null)).as("專案沒有規格檔").containsExactly("docs");
        assertThat(fields("r", null, null, null, "/elsewhere/TCS.md")).as("規格檔不在專案根之下").containsExactly("docs");
        assertThat(fields("r", null, null, null, ROOT)).as("規格檔就是專案根本身：沒有相對路徑").containsExactly("docs");
    }

    @Test
    void aBoundSpecFileMustBeAmongTheGivenDocsInAnySpelling() {
        String bound = ROOT + "/docs/TCS-Bound.md";

        assertThat(ok("r", null, List.of("x.md", "./docs/TCS-Bound.md"), null, bound).docs())
                .containsExactly("x.md", "docs/TCS-Bound.md");
        assertThat(ok("r", null, List.of("docs\\TCS-Bound.md"), null, bound).docs()).containsExactly("docs/TCS-Bound.md");
        assertThat(fields("r", null, List.of("docs/other.md"), null, bound)).containsExactly("docs");
        assertThat(fields("r", null, List.of("docs/other.md"), null, "/elsewhere/TCS.md")).as("規格檔在根之外：永遠不含")
                .containsExactly("docs");
    }

    @Test
    void aWindowsStyleRootComparesCaseInsensitively() {
        Violations v = new Violations();
        Checked checked = SddFreezeRules.check(v, "r", null, null, null, "D:\\Work\\Proj", "d:/work/proj/Docs/TCS.md");
        v.throwIfAny();

        assertThat(checked.docs()).containsExactly("Docs/TCS.md");
        Violations other = new Violations();
        SddFreezeRules.check(other, "r", null, List.of("docs/tcs.md"), null, "D:\\Work\\Proj", "d:/work/proj/Docs/TCS.md");
        other.throwIfAny();
    }

    // ── expectedDigests ───────────────────────────────────────────────────────

    @Test
    void expectedDigestsAreOptionalAndKeysAreNormalizedLikeDocs() {
        assertThat(ok("r", null, DOCS, null, null).expectedDigests()).isNull();
        assertThat(ok("r", null, DOCS, Map.of(), null).expectedDigests()).as("空映射＝不比對").isNull();

        Map<String, String> digests = new LinkedHashMap<>();
        digests.put("./docs/TCS-A.md", DIGEST);

        assertThat(ok("r", null, DOCS, digests, null).expectedDigests()).containsOnly(Map.entry("docs/TCS-A.md", DIGEST));
    }

    @Test
    void aDigestKeyOutsideDocsOrABadDigestValueIsRejectedOnExpectedDigests() {
        assertThat(fields("r", null, DOCS, Map.of("docs/other.md", DIGEST), null)).containsExactly("expectedDigests");
        for (String bad : List.of("sha256:NOT-HEX", "sha256:" + "A".repeat(64), "sha256:" + "a".repeat(63), "md5:abc", "")) {
            assertThat(fields("r", null, DOCS, Map.of("docs/TCS-A.md", bad), null)).as(bad)
                    .containsExactly("expectedDigests");
        }
        Map<String, String> nullValue = new LinkedHashMap<>();
        nullValue.put("docs/TCS-A.md", null);
        assertThat(fields("r", null, DOCS, nullValue, null)).containsExactly("expectedDigests");
        assertThat(fields("r", null, DOCS, Map.of("/abs.md", DIGEST), null)).as("鍵本身不合法").containsExactly("expectedDigests");
    }

    // ── 累積 ──────────────────────────────────────────────────────────────────

    @Test
    void severalProblemsAreReportedTogetherInFieldOrder() {
        assertThat(fields("  ", "bad stage", List.of("/abs"), Map.of("x.md", DIGEST), null))
                .containsExactly("reason", "stage", "docs[0]");
        assertThat(fields("r", null, List.of("/abs"), Map.of("x.md", "nope"), null)).as("docs 不合時摘要的格式仍會檢查")
                .containsExactly("docs[0]", "expectedDigests");
    }
}
