package com.aisdlc.console.application.service;

import com.aisdlc.console.domain.model.imports.ParseOptions;
import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AgentBridge.DecomposeRequest;
import com.aisdlc.console.application.port.out.AgentBridge.DecomposeResult;
import com.aisdlc.console.application.port.out.AgentBridge.DraftStep;
import com.aisdlc.console.application.port.out.AgentBridge.SddCompileResult;
import com.aisdlc.console.application.port.out.AgentBridge.SddTask;
import com.aisdlc.console.application.port.out.LlmClient;
import com.aisdlc.console.application.port.out.LlmClient.LlmException;
import com.aisdlc.console.application.port.out.LlmClient.LlmRequest;
import com.aisdlc.console.application.port.out.LlmClient.LlmResult;
import com.aisdlc.console.application.port.out.SecretCipher;
import com.aisdlc.console.application.service.ImportParser.Draft;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.model.config.ConfigValueType;
import com.aisdlc.console.domain.model.imports.GateError;
import com.aisdlc.console.domain.model.imports.ImportRecord;
import com.aisdlc.console.domain.model.imports.ImportSourceType;
import com.aisdlc.console.domain.model.imports.ParsePath;
import com.aisdlc.console.domain.model.imports.ParseWarning;
import com.aisdlc.console.domain.model.imports.ParsedResult;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedGoal;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedProject;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedTask;
import com.aisdlc.console.domain.service.OutboundUrlPolicy;
import com.aisdlc.console.support.InMemorySystemConfigRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 匯入解析的三條路徑與選擇規則（契約 §3.3）。為什麼重要：路徑選擇決定「資料送去哪裡」——規格存在卻被拒絕時必須 fail-closed
 * （不可退回 LLM 瞎猜，PRD §0.4 的凍結硬閘）；高階目標才走 Bridge、文件走 LLM；
 * 路徑轉換不得悄悄丟資訊（被清空的指令與 regex 要有警告）。
 */
class ImportParserTest {

    private static final String EXEC_PATH = "/work/proj";

    private final AgentBridge bridge = mock(AgentBridge.class);
    private final LlmClient llm = mock(LlmClient.class);
    private final InMemorySystemConfigRepository config = new InMemorySystemConfigRepository();
    private ImportParser parser;

    @BeforeEach
    void setUp() {
        config.with("model", "apiUrl", ConfigValueType.STRING, "https://api.minimax.io/v1/text/chatcompletion_v2")
                .withEncrypted("model", "apiKey", "enc:sk-test")
                .with("model", "name", ConfigValueType.STRING, "MiniMax-M2.7")
                .with("model", "timeout", ConfigValueType.INTEGER, "120")
                .with("model", "temperature", ConfigValueType.FLOAT, "0.3")
                .with("model", "topP", ConfigValueType.FLOAT, "0.9")
                .with("model", "maxTokensPerRequest", ConfigValueType.INTEGER, "8192")
                .with("model", "enableKernelBrain", ConfigValueType.BOOLEAN, "false");
        SecretCipher cipher = new SecretCipher() {
            @Override
            public String encrypt(String plainText) {
                return "enc:" + plainText;
            }

            @Override
            public String decrypt(String stored) {
                return stored.substring("enc:".length());
            }
        };
        parser = new ImportParser(bridge, llm, new SettingsReader(config, cipher),
                new OutboundUrlPolicy(List.of("api.minimax.io"), false), 120_000);
    }

    private static ImportRecord record(ImportSourceType type, String content) {
        return ImportRecord.create(type, content, "doc.md", Instant.parse("2026-10-15T08:00:00Z"));
    }

    private static ParseOptions options(String specDir) {
        return new ParseOptions(EXEC_PATH, 3, "盡量少於 5 個任務", specDir);
    }

    private static BridgeRejectedException rejected(int status, String reason, String detail) {
        return new BridgeRejectedException(status, reason, null, detail, List.of(),
                Map.of("code", status, "reason", reason));
    }

    private static final String MARKDOWN_DOC = "# BRD\n\n## 功能\n- 登入\n- 註冊\n" + "說明文字。".repeat(60);

    // ── 路徑選擇 ─────────────────────────────────────────────────────────────

    @Test
    void anExplicitSpecDirGoesStraightToPathAWithoutProbingTheExecutionPath() {
        when(bridge.sddCompile("/spec/frozen")).thenReturn(compiled(2));
        Draft draft = parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options("/spec/frozen"));

        assertThat(draft.result().path()).isEqualTo(ParsePath.SDD);
        verify(bridge).sddCompile("/spec/frozen");
        verify(bridge, never()).sddCompile(EXEC_PATH);
        verify(llm, never()).generate(any());
    }

    @Test
    void withoutASpecDirTheExecutionPathIsProbedAndAFrozenSpecWinsOverEverythingElse() {
        when(bridge.sddCompile(EXEC_PATH)).thenReturn(compiled(3));
        Draft draft = parser.parse(record(ImportSourceType.PLAIN_TEXT, "做一個待辦清單"), options(null));
        assertThat(draft.result().path()).as("即使內容很短（本來會走 C）也以規格為準").isEqualTo(ParsePath.SDD);
        verify(bridge, never()).decompose(any(), any());
    }

    @Test
    void noSpecFoundFallsThroughToDecomposeForShortPlainTextAndToLlmOtherwise() {
        doThrow(rejected(422, "spec_not_found", "沒有規格")).when(bridge).sddCompile(EXEC_PATH);
        when(bridge.decompose(any(), any())).thenReturn(decomposed(2));
        assertThat(parser.parse(record(ImportSourceType.PLAIN_TEXT, "做一個待辦清單"), options(null)).result().path())
                .isEqualTo(ParsePath.DECOMPOSE);

        when(llm.generate(any())).thenReturn(new LlmResult(llmDraft(), 10L, "m"));
        assertThat(parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options(null)).result().path())
                .isEqualTo(ParsePath.LLM);
    }

    @Test
    void aSanitizationFailureOnTheProbeAlsoMeansNoSpec() {
        doThrow(rejected(422, "sanitization_failed", null)).when(bridge).sddCompile(EXEC_PATH);
        when(bridge.decompose(any(), any())).thenReturn(decomposed(1));
        assertThat(parser.parse(record(ImportSourceType.PLAIN_TEXT, "短目標"), options(null)).result().path())
                .isEqualTo(ParsePath.DECOMPOSE);
    }

    @Test
    void aSpecThatExistsButIsRejectedFailsClosedInsteadOfFallingBackToTheLlm() {
        for (String reason : List.of("spec_not_frozen", "spec_tainted", "spec_format_version_unsupported",
                "spec_ambiguous")) {
            doThrow(rejected(422, reason, "規格有問題：" + reason)).when(bridge).sddCompile(EXEC_PATH);
            assertThatThrownBy(() -> parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options(null)))
                    .isInstanceOfSatisfying(UnprocessableException.class, e -> {
                        assertThat(e.reason()).isEqualTo(ErrorReasons.SDD_SPEC_REJECTED);
                        assertThat(e.details()).containsEntry("bridgeReason", reason).containsKey("detail");
                        assertThat(e.violations()).singleElement()
                                .satisfies(v -> assertThat(v.field()).isEqualTo("specDir"));
                    });
        }
        verify(llm, never()).generate(any());
        verify(bridge, never()).decompose(any(), any());
    }

    @Test
    void anUnreachableOrFailingBridgeDuringTheProbeIsSkippedNotFatal() {
        when(llm.generate(any())).thenReturn(new LlmResult(llmDraft(), 10L, "m"));

        doThrow(new UpstreamException.Unavailable("down")).when(bridge).sddCompile(EXEC_PATH);
        assertThat(parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options(null)).result().path())
                .isEqualTo(ParsePath.LLM);

        doThrow(new UpstreamException.TimedOut("slow")).when(bridge).sddCompile(EXEC_PATH);
        assertThat(parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options(null)).result().path())
                .isEqualTo(ParsePath.LLM);

        doThrow(new UpstreamException.Failure("500", Map.of("bridgeStatus", 500))).when(bridge)
                .sddCompile(EXEC_PATH);
        assertThat(parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options(null)).result().path())
                .isEqualTo(ParsePath.LLM);

        doThrow(rejected(400, "bad_request", null)).when(bridge).sddCompile(EXEC_PATH);
        assertThat(parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options(null)).result().path())
                .as("非預期的 4xx 同樣略過路徑 A").isEqualTo(ParsePath.LLM);
    }

    @Test
    void withAnExplicitSpecDirEveryBridgeFailureIsReportedIncludingSpecNotFound() {
        doThrow(rejected(422, "spec_not_found", "找不到規格")).when(bridge).sddCompile("/spec");
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.MARKDOWN, "x"), options("/spec")))
                .isInstanceOfSatisfying(UnprocessableException.class,
                        e -> assertThat(e.details()).containsEntry("bridgeReason", "spec_not_found"));

        doThrow(rejected(422, "sanitization_failed", null)).when(bridge).sddCompile("/spec");
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.MARKDOWN, "x"), options("/spec")))
                .isInstanceOfSatisfying(UnprocessableException.class,
                        e -> assertThat(e.details()).containsEntry("bridgeReason", "sanitization_failed")
                                .containsKey("detail"));

        doThrow(new UpstreamException.Unavailable("down")).when(bridge).sddCompile("/spec");
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.MARKDOWN, "x"), options("/spec")))
                .isInstanceOf(UpstreamException.Unavailable.class);

        doThrow(rejected(404, "nope", null)).when(bridge).sddCompile("/spec");
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.MARKDOWN, "x"), options("/spec")))
                .isInstanceOf(UpstreamException.Failure.class);
    }

    @Test
    void theHighLevelGoalRuleNeedsPlainTextUnderTwoThousandCharsAndNoMarkdownHeading() {
        assertThat(ImportParser.isHighLevelGoal(record(ImportSourceType.PLAIN_TEXT, "做一個待辦清單"))).isTrue();
        assertThat(ImportParser.isHighLevelGoal(record(ImportSourceType.PLAIN_TEXT, "a".repeat(1999)))).isTrue();
        assertThat(ImportParser.isHighLevelGoal(record(ImportSourceType.PLAIN_TEXT, "a".repeat(2000)))).isFalse();
        assertThat(ImportParser.isHighLevelGoal(record(ImportSourceType.PLAIN_TEXT, "# 標題\n內容"))).isFalse();
        assertThat(ImportParser.isHighLevelGoal(record(ImportSourceType.PLAIN_TEXT, "前言\n   ### 縮排標題\n內容")))
                .as("標題行最多縮排 3 個空白").isFalse();
        assertThat(ImportParser.isHighLevelGoal(record(ImportSourceType.PLAIN_TEXT, "前言\n    # 四個空白不是標題")))
                .as("縮排 4 個空白是程式碼區塊、不是標題").isTrue();
        assertThat(ImportParser.isHighLevelGoal(record(ImportSourceType.PLAIN_TEXT, "#hashtag 沒有空白")))
                .as("# 後要有空白或 tab").isTrue();
        assertThat(ImportParser.isHighLevelGoal(record(ImportSourceType.MARKDOWN, "短")))
                .as("MARKDOWN／PDF／DOCX 一律不走 C").isFalse();
        assertThat(ImportParser.isHighLevelGoal(record(ImportSourceType.PDF, "短"))).isFalse();
        assertThat(ImportParser.isHighLevelGoal(record(ImportSourceType.DOCX, "短"))).isFalse();
        assertThat(ImportParser.isHighLevelGoal(record(ImportSourceType.PLAIN_TEXT, "  " + "a".repeat(1990) + "  ")))
                .as("以 strip 後的長度判斷").isTrue();
    }

    // ── 路徑 A：規格 → 目標切分 ───────────────────────────────────────────────

    private static SddCompileResult compiled(int taskCount) {
        List<SddTask> tasks = new ArrayList<>();
        for (int i = 1; i <= taskCount; i++) {
            tasks.add(new SddTask("C" + i, "合約 " + i, "請實作合約 " + i, "OK-" + i + "\\d+", "pytest -q tests/test" + i, i % 2 == 0));
        }
        return new SddCompileResult("購物車", "/spec/cart.yaml", "0123456789abcdef0123", tasks);
    }

    @Test
    void thirtyContractsAreSplitIntoTwentyFourPlusSixWithAChainOfDependencies() {
        when(bridge.sddCompile("/spec")).thenReturn(compiled(30));
        ParsedResult result = parser.parse(record(ImportSourceType.MARKDOWN, "x"), options("/spec")).result();

        assertThat(result.goals()).hasSize(2);
        ParsedGoal first = result.goals().get(0);
        ParsedGoal second = result.goals().get(1);
        assertThat(first.key()).isEqualTo("g1");
        assertThat(first.name()).isEqualTo("購物車（第 1 批）");
        assertThat(first.tasks()).hasSize(24);
        assertThat(first.dependsOn()).isEmpty();
        assertThat(first.passCriteria()).isEqualTo("全部 24 個合約的驗收標準通過");
        assertThat(second.key()).isEqualTo("g2");
        assertThat(second.name()).isEqualTo("購物車（第 2 批）");
        assertThat(second.tasks()).hasSize(6);
        assertThat(second.dependsOn()).containsExactly("g1");
        assertThat(second.sortOrder()).isEqualTo(1);
        assertThat(second.tasks().get(0).name()).as("保持編譯順序").isEqualTo("合約 25");
    }

    @Test
    void aSingleBatchKeepsThePlainScenarioNameAndTheProjectFieldsComeFromTheSpecAndTheOptions() {
        when(bridge.sddCompile("/spec")).thenReturn(compiled(3));
        ParsedResult result = parser.parse(record(ImportSourceType.MARKDOWN, "x"), options("/spec")).result();

        assertThat(result.goals()).singleElement().satisfies(g -> assertThat(g.name()).isEqualTo("購物車"));
        ParsedProject project = result.project();
        assertThat(project.name()).isEqualTo("購物車");
        assertThat(project.executionPath()).as("一律取自 ParseOptions").isEqualTo(EXEC_PATH);
        assertThat(project.autonomyLevel()).isEqualTo(3);
        assertThat(project.passCriteria()).isEqualTo("規格「購物車」的全部合約驗收通過");
        assertThat(project.description()).isEqualTo("由凍結 SDD 規格匯入（/spec/cart.yaml；digest 0123456789ab）");
        assertThat(result.specDigest()).isEqualTo("0123456789abcdef0123");
        assertThat(result.aiModel()).isNull();
        assertThat(result.tokenUsed()).isNull();
    }

    @Test
    void sddTasksCarryTheirPromptRegexCommandAndTheStructuredPassCriteriaSpec() {
        when(bridge.sddCompile("/spec")).thenReturn(compiled(2));
        List<ParsedTask> tasks = parser.parse(record(ImportSourceType.MARKDOWN, "x"), options("/spec")).result()
                .goals().get(0).tasks();

        ParsedTask t1 = tasks.get(0);
        assertThat(t1.description()).isEqualTo("請實作合約 1");
        assertThat(t1.passCriteria()).isEqualTo("輸出符合 OK-1\\d+");
        assertThat(t1.expectedOutputRegex()).isEqualTo("OK-1\\d+");
        assertThat(t1.evaluatorCommand()).isEqualTo("pytest -q tests/test1");
        assertThat(t1.passCriteriaSpec()).containsEntry("source", "sdd").containsEntry("stepId", "C1")
                .containsEntry("specDigest", "0123456789abcdef0123").containsEntry("weakRegex", false);
        assertThat(tasks.get(1).passCriteriaSpec()).containsEntry("weakRegex", true);
    }

    @Test
    void anUncompilableRegexAndAnUnsafeCommandAreDroppedWithWarningsNotSilently() {
        SddCompileResult dirty = new SddCompileResult("S", "/s.yaml", "d", List.of(
                new SddTask("C1", "壞 regex", "做事", "([", "pytest -q", false),
                new SddTask("C2", "壞指令", "做事", null, "pytest; rm -rf /", false),
                new SddTask("C3", "沒有 regex", "做事", null, null, false)));
        when(bridge.sddCompile("/spec")).thenReturn(dirty);

        Draft draft = parser.parse(record(ImportSourceType.MARKDOWN, "x"), options("/spec"));
        List<ParsedTask> tasks = draft.result().goals().get(0).tasks();

        assertThat(tasks.get(0).expectedOutputRegex()).isNull();
        assertThat(tasks.get(0).passCriteria()).isEqualTo("規格合約 C1 的驗收標準");
        assertThat(tasks.get(1).evaluatorCommand()).isNull();
        assertThat(tasks.get(2).passCriteria()).isEqualTo("規格合約 C3 的驗收標準");
        assertThat(draft.warnings()).extracting(ParseWarning::code).containsExactly("regex_dropped",
                "evaluator_command_dropped");
        assertThat(draft.warnings()).extracting(ParseWarning::location).containsExactly("goals[0].tasks[0]",
                "goals[0].tasks[1]");
    }

    @Test
    void aSpecThatCompilesToNoTasksIsRejectedInsteadOfCreatingAnEmptyDraft() {
        when(bridge.sddCompile("/spec")).thenReturn(new SddCompileResult("S", "/s", "d", List.of()));
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.MARKDOWN, "x"), options("/spec")))
                .isInstanceOfSatisfying(UnprocessableException.class,
                        e -> assertThat(e.details()).containsEntry("bridgeReason", "no_tasks"));
    }

    @Test
    void aBlankScenarioFallsBackToTheLastSegmentOfTheExecutionPath() {
        when(bridge.sddCompile("/spec")).thenReturn(new SddCompileResult("  ", "/s", "d",
                List.of(new SddTask("C1", "n", "p", null, null, false))));
        ParseOptions windowsPath = new ParseOptions("C:\\work\\my-proj\\", 3, null, "/spec");
        assertThat(parser.parse(record(ImportSourceType.MARKDOWN, "x"), windowsPath).result().project().name())
                .isEqualTo("my-proj");
    }

    // ── 路徑 C：decompose ────────────────────────────────────────────────────

    private static DecomposeResult decomposed(int steps) {
        List<DraftStep> list = new ArrayList<>();
        for (int i = 1; i <= steps; i++) {
            list.add(new DraftStep("s" + i, "步驟 " + i, "請做第 " + i + " 步", i == 1 ? "pytest -q" : null));
        }
        return new DecomposeResult("draft-1", "先拆再做", list);
    }

    @Test
    void decomposeBuildsOneGoalWithOnePassCriteriaPlaceholderWarningPerStepWithoutACommand() {
        when(bridge.decompose(any(), any())).thenReturn(decomposed(2));
        Draft draft = parser.parse(record(ImportSourceType.PLAIN_TEXT, "做一個待辦清單\n要能新增與刪除"), options(null));

        ParsedResult result = draft.result();
        assertThat(result.path()).isEqualTo(ParsePath.DECOMPOSE);
        assertThat(result.draftIds()).containsExactly("draft-1");
        assertThat(result.reasoning()).isEqualTo("先拆再做");
        assertThat(result.project().name()).isEqualTo("做一個待辦清單");
        assertThat(result.project().passCriteria()).isEqualTo("做一個待辦清單\n要能新增與刪除");
        assertThat(result.project().description()).isEqualTo("先拆再做");
        assertThat(result.project().executionPath()).isEqualTo(EXEC_PATH);
        assertThat(result.goals()).singleElement().satisfies(g -> {
            assertThat(g.key()).isEqualTo("g1");
            assertThat(g.passCriteria()).isEqualTo("拆解出的全部步驟依序完成");
            assertThat(g.tasks()).hasSize(2);
            assertThat(g.tasks().get(0).passCriteria()).isEqualTo("評估指令通過");
            assertThat(g.tasks().get(0).evaluatorCommand()).isEqualTo("pytest -q");
            assertThat(g.tasks().get(1).passCriteria()).isEqualTo(ParseWarning.PASSCRITERIA_PLACEHOLDER_TEXT);
            assertThat(g.tasks().get(1).passCriteriaSpec()).containsEntry("source", "decompose")
                    .containsEntry("stepId", "s2").containsEntry("draftId", "draft-1");
        });
        assertThat(draft.warnings()).singleElement().satisfies(w -> {
            assertThat(w.code()).isEqualTo("passcriteria_placeholder");
            assertThat(w.location()).isEqualTo("goals[0].tasks[1]");
        });
    }

    @Test
    void decomposeSendsTheGoalTrimmedWithTheMiniMaxOverridesOnlyWhenAKeyIsConfiguredAndAReadTimeoutOfTimeoutPlusFifteen() {
        when(bridge.decompose(any(), any())).thenReturn(decomposed(1));
        parser.parse(record(ImportSourceType.PLAIN_TEXT, "  做一個待辦清單  "), options(null));

        ArgumentCaptor<DecomposeRequest> request = ArgumentCaptor.forClass(DecomposeRequest.class);
        ArgumentCaptor<Duration> timeout = ArgumentCaptor.forClass(Duration.class);
        verify(bridge).decompose(request.capture(), timeout.capture());
        assertThat(request.getValue().goal()).isEqualTo("做一個待辦清單");
        assertThat(request.getValue().context()).isEqualTo("盡量少於 5 個任務");
        assertThat(request.getValue().maxSteps()).isEqualTo(24);
        assertThat(request.getValue().minimaxOverrides()).containsEntry("base_url",
                "https://api.minimax.io/v1/text/chatcompletion_v2").containsEntry("model", "MiniMax-M2.7")
                .containsEntry("timeout_seconds", 120);
        assertThat(timeout.getValue()).isEqualTo(Duration.ofSeconds(135));

        config.withEncrypted("model", "apiKey", "");
        parser.parse(record(ImportSourceType.PLAIN_TEXT, "做一個待辦清單"), options(null));
        ArgumentCaptor<DecomposeRequest> second = ArgumentCaptor.forClass(DecomposeRequest.class);
        verify(bridge, times(2)).decompose(second.capture(), any());
        assertThat(second.getAllValues().get(1).minimaxOverrides()).as("沒有金鑰就不送 minimax 區段").isNull();
    }

    @Test
    void aDecompositionWithoutAnyStepIsBrainFailedBecauseAGoalNeedsAtLeastOneTask() {
        when(bridge.decompose(any(), any())).thenReturn(new DecomposeResult("draft-1", "沒有步驟", List.of()));
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.PLAIN_TEXT, "做一個待辦清單"), options(null)))
                .isInstanceOfSatisfying(UnprocessableException.class, e -> {
                    assertThat(e.reason()).isEqualTo(ErrorReasons.IMPORT_GATE_REJECTED);
                    assertThat(e.gateErrors()).singleElement().satisfies(g -> {
                        assertThat(g.gate()).isEqualTo("brain_failed");
                        assertThat(g.detail()).contains("no_steps");
                        assertThat(g.location()).isNull();
                    });
                    assertThat(e.details()).containsEntry("path", "DECOMPOSE");
                });

        when(bridge.decompose(any(), any())).thenReturn(new DecomposeResult("draft-2", "沒有步驟", null));
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.PLAIN_TEXT, "做一個待辦清單"), options(null)))
                .isInstanceOfSatisfying(UnprocessableException.class,
                        e -> assertThat(e.gateErrors()).extracting(GateError::gate).containsExactly("brain_failed"));
    }

    @Test
    void theProjectNameComesFromTheFirstNonBlankLineClippedToSixtyCharacters() {
        when(bridge.decompose(any(), any())).thenReturn(decomposed(1));
        String longLine = "目".repeat(100);
        ParsedResult result = parser.parse(record(ImportSourceType.PLAIN_TEXT, "\n\n" + longLine + "\n第二行"),
                options(null)).result();
        assertThat(result.project().name()).hasSize(60);
    }

    @Test
    void aBridgeGateRejectionBecomesAGateErrorWithoutALocation() {
        when(bridge.decompose(any(), any())).thenThrow(new BridgeRejectedException(422, "too_many_steps", "max_steps",
                "拆出 30 步超過上限", List.of(), Map.of()));
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.PLAIN_TEXT, "短目標"), options(null)))
                .isInstanceOfSatisfying(UnprocessableException.class, e -> {
                    assertThat(e.reason()).isEqualTo(ErrorReasons.IMPORT_GATE_REJECTED);
                    assertThat(e.gateErrors()).singleElement().satisfies(g -> {
                        assertThat(g.gate()).isEqualTo("max_steps");
                        assertThat(g.detail()).isEqualTo("拆出 30 步超過上限");
                        assertThat(g.location()).isNull();
                    });
                    assertThat(e.details()).containsEntry("path", "DECOMPOSE");
                });
    }

    @Test
    void aBridgeBrainUnsupportedRejectionPassesThroughAsAGateAndOtherFailuresMapAsDocumented() {
        doThrow(new BridgeRejectedException(422, "brain_unsupported", "brain_unsupported",
                "無法建立 Brain：缺少 MINIMAX_API_KEY", List.of(), Map.of())).when(bridge).decompose(any(), any());
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.PLAIN_TEXT, "短"), options(null)))
                .isInstanceOfSatisfying(UnprocessableException.class, e -> assertThat(e.gateErrors())
                        .extracting(GateError::gate).containsExactly("brain_unsupported"));

        doThrow(new BridgeRejectedException(422, "invalid_request", null, null,
                List.of(Map.of("field", "goal", "message", "太長")), Map.of("reason", "invalid_request")))
                .when(bridge).decompose(any(), any());
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.PLAIN_TEXT, "短"), options(null)))
                .isInstanceOfSatisfying(UnprocessableException.class, e -> {
                    assertThat(e.reason()).isEqualTo(ErrorReasons.BRIDGE_REJECTED);
                    assertThat(e.details()).containsEntry("bridgeReason", "invalid_request").containsKey("violations");
                });

        doThrow(new BridgeRejectedException(409, "weird", null, null, List.of(), Map.of())).when(bridge)
                .decompose(any(), any());
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.PLAIN_TEXT, "短"), options(null)))
                .isInstanceOf(UpstreamException.Failure.class);

        doThrow(new UpstreamException.TimedOut("slow")).when(bridge).decompose(any(), any());
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.PLAIN_TEXT, "短"), options(null)))
                .isInstanceOf(UpstreamException.TimedOut.class);
    }

    // ── 路徑 B：LLM ──────────────────────────────────────────────────────────

    private static ParsedResult llmDraft() {
        ParsedTask t1 = new ParsedTask("初始化", "請輸出 [T1_DONE]", "輸出含 [T1_DONE]", 7, null, null, null, null, null);
        ParsedTask t2 = new ParsedTask("設定", "請輸出 [T2_DONE]", null, 9, 50L, null, null, null, null);
        ParsedGoal g1 = new ParsedGoal(null, "基礎", "", "基礎完成", 5, null, List.of(t1, t2));
        ParsedGoal g2 = new ParsedGoal("  ", "核心", "", null, 5, List.of("g1"), List.of(t1));
        return ParsedResult.tree(new ParsedProject("AI 命名", "/ignored", null, "說明", 9), List.of(g1, g2));
    }

    @Test
    void llmDraftsAreNormalizedKeysFilledPlaceholdersWarnedAndTheOptionsOverrideTheModelsSuggestions() {
        when(llm.generate(any())).thenReturn(new LlmResult(llmDraft(), 1152L, "e2e-model"));
        Draft draft = parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options(null));

        ParsedResult result = draft.result();
        assertThat(result.path()).isEqualTo(ParsePath.LLM);
        assertThat(result.aiModel()).isEqualTo("e2e-model");
        assertThat(result.tokenUsed()).isEqualTo(1152L);
        assertThat(result.project().name()).isEqualTo("AI 命名");
        assertThat(result.project().executionPath()).as("LLM 的建議被丟棄").isEqualTo(EXEC_PATH);
        assertThat(result.project().autonomyLevel()).isEqualTo(3);
        assertThat(result.goals()).extracting(ParsedGoal::key).containsExactly("g1", "g2");
        assertThat(result.goals()).extracting(ParsedGoal::sortOrder).containsExactly(0, 1);
        assertThat(result.goals().get(0).tasks()).extracting(ParsedTask::sortOrder).containsExactly(0, 1);
        assertThat(result.goals().get(0).dependsOn()).isEmpty();
        assertThat(result.goals().get(1).dependsOn()).containsExactly("g1");
        assertThat(result.goals().get(0).tasks().get(1).passCriteria())
                .isEqualTo(ParseWarning.PASSCRITERIA_PLACEHOLDER_TEXT);
        assertThat(result.goals().get(1).passCriteria()).isEqualTo(ParseWarning.PASSCRITERIA_PLACEHOLDER_TEXT);
        assertThat(result.project().passCriteria()).isEqualTo(ParseWarning.PASSCRITERIA_PLACEHOLDER_TEXT);
        assertThat(draft.warnings()).extracting(ParseWarning::code).containsOnly("passcriteria_placeholder");
        assertThat(draft.warnings()).extracting(ParseWarning::location).containsExactlyInAnyOrder("project",
                "goals[1]", "goals[0].tasks[1]");
    }

    @Test
    void theModelNameFallsBackToTheConfiguredNameWhenTheAnswerHasNone() {
        when(llm.generate(any())).thenReturn(new LlmResult(llmDraft(), null, null));
        ParsedResult result = parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options(null)).result();
        assertThat(result.aiModel()).isEqualTo("MiniMax-M2.7");
        assertThat(result.tokenUsed()).isNull();
    }

    @Test
    void theLlmRequestUsesTheStoredSettingsAndTheDocumentedTemplate() {
        when(llm.generate(any())).thenReturn(new LlmResult(llmDraft(), 1L, "m"));
        parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), new ParseOptions(EXEC_PATH, 5, "  ", null));

        ArgumentCaptor<LlmRequest> captor = ArgumentCaptor.forClass(LlmRequest.class);
        verify(llm).generate(captor.capture());
        LlmRequest request = captor.getValue();
        assertThat(request.apiUrl()).isEqualTo("https://api.minimax.io/v1/text/chatcompletion_v2");
        assertThat(request.apiKey()).as("解密後的金鑰").isEqualTo("sk-test");
        assertThat(request.model()).isEqualTo("MiniMax-M2.7");
        assertThat(request.timeoutSeconds()).isEqualTo(120);
        assertThat(request.temperature()).isEqualTo(0.3);
        assertThat(request.topP()).isEqualTo(0.9);
        assertThat(request.maxTokens()).isEqualTo(8192);
        assertThat(request.systemMessage()).startsWith("你是一位資深的軟體架構師。只輸出一個 JSON 物件")
                .contains("最多 24 個目標、每個目標最多 24 個任務");
        assertThat(request.userMessage()).contains("自治等級: 5\n補充說明: （無）\n\n---\n需求文件內容:\n# BRD");
    }

    @Test
    void theUserMessageTemplateIsAssembledVerbatimAndDocumentPlaceholdersAreNotExpanded() {
        String message = ImportParser.userMessage(3, "盡量少於 5 個任務", "文件含 {autonomyLevel} 與 {additionalPrompt}");
        assertThat(message).isEqualTo("你是一位資深的軟體架構師。請分析以下需求文件，並將其拆解為三層結構：\n\n"
                + "1. **專案 (Project)**：整體專案名稱、執行路徑建議、通過標準、說明描述\n"
                + "2. **目標 (Goal)**：專案下的主要里程碑或功能模組，含說明描述與通過標準\n"
                + "3. **任務 (Task)**：目標下的具體可執行開發任務，含說明描述與通過標準\n\n"
                + "自治等級: 3\n補充說明: 盡量少於 5 個任務\n\n---\n需求文件內容:\n"
                + "文件含 {autonomyLevel} 與 {additionalPrompt}\n---\n\n請以 JSON 格式輸出結果。");
    }

    @Test
    void withoutAnApiKeyTheLlmPathIsBrainUnsupportedAndNothingIsSent() {
        config.withEncrypted("model", "apiKey", "");
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options(null)))
                .isInstanceOfSatisfying(UnprocessableException.class, e -> {
                    assertThat(e.gateErrors()).singleElement().satisfies(g -> {
                        assertThat(g.gate()).isEqualTo("brain_unsupported");
                        assertThat(g.detail()).contains("model.apiKey");
                    });
                    assertThat(e.details()).containsEntry("path", "LLM");
                });
        verify(llm, never()).generate(any());
    }

    @Test
    void anApiUrlThatFailsTheStaticSsrfRulesIsBrainUnsupportedAndNothingIsSent() {
        config.set("model", "apiUrl", "http://10.0.0.5/v1/chat");
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options(null)))
                .isInstanceOfSatisfying(UnprocessableException.class, e -> assertThat(e.gateErrors()
                        .get(0).detail()).isEqualTo("模型位址未通過 SSRF／allowlist 檢查（private_ip）"));
        config.set("model", "apiUrl", "https://example.com/v1");
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options(null)))
                .isInstanceOfSatisfying(UnprocessableException.class, e -> assertThat(e.gateErrors()
                        .get(0).detail()).contains("not_in_allowlist"));
        verify(llm, never()).generate(any());
    }

    @Test
    void aDocumentThatIsTooLongNeverReachesTheModel() {
        String huge = "# 文件\n" + "字".repeat(120_000);
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.MARKDOWN, huge), options(null)))
                .isInstanceOfSatisfying(UnprocessableException.class, e -> assertThat(e.gateErrors())
                        .singleElement().satisfies(g -> {
                            assertThat(g.gate()).isEqualTo("prompt_too_long");
                            assertThat(g.location()).isEqualTo("sourceContent");
                            assertThat(g.detail()).startsWith("文件過長：").endsWith("，上限 120000");
                        }));
        verify(llm, never()).generate(any());
    }

    @Test
    void llmFailuresMapToBrainGatesByKind() {
        doThrow(new LlmException(LlmException.Kind.FAILED, "模型輸出不是合法 JSON：x")).when(llm).generate(any());
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options(null)))
                .isInstanceOfSatisfying(UnprocessableException.class, e -> assertThat(e.gateErrors())
                        .singleElement().satisfies(g -> {
                            assertThat(g.gate()).isEqualTo("brain_failed");
                            assertThat(g.detail()).isEqualTo("模型輸出不是合法 JSON：x");
                        }));
        doThrow(new LlmException(LlmException.Kind.UNSUPPORTED, "模型位址未通過檢查")).when(llm).generate(any());
        assertThatThrownBy(() -> parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options(null)))
                .isInstanceOfSatisfying(UnprocessableException.class, e -> assertThat(e.gateErrors())
                        .extracting(GateError::gate).containsExactly("brain_unsupported"));
    }

    @Test
    void aMissingProjectNameFallsBackToTheFileNameWithoutExtension() {
        ParsedResult noName = ParsedResult.tree(new ParsedProject(null, null, "標準", null, null),
                List.of(new ParsedGoal("g1", "G", "", "c", 0, List.of(),
                        List.of(new ParsedTask("T", "d", "c", 0, null, null, null, null, null)))));
        when(llm.generate(any())).thenReturn(new LlmResult(noName, 1L, "m"));
        ParsedResult result = parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options(null)).result();
        assertThat(result.project().name()).isEqualTo("doc");
    }

    @Test
    void theParserNeverCallsTheBridgeForPathBBeyondTheProbe() {
        when(bridge.sddCompile(EXEC_PATH)).thenThrow(rejected(422, "spec_not_found", null));
        when(llm.generate(any())).thenReturn(new LlmResult(llmDraft(), 1L, "m"));
        parser.parse(record(ImportSourceType.MARKDOWN, MARKDOWN_DOC), options(null));
        verify(bridge).sddCompile(EXEC_PATH);
        verify(bridge, never()).decompose(any(), any());
        verify(bridge, never()).approveDraft(anyString(), anyString());
        verify(bridge, never()).sddCompile(eq("/other"));
    }
}
