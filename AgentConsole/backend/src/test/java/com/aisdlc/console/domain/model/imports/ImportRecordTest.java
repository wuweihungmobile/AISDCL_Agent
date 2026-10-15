package com.aisdlc.console.domain.model.imports;

import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedGoal;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedProject;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedTask;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.function.Consumer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * 匯入記錄狀態機（API-IMP-10；契約 §1.1 的「動作可用性表」）。為什麼重要：🔴 人工 signoff 硬閘——
 * 沒有簽核就不能落庫；編輯必須撤銷既有簽核；失敗的 parse 不可毀掉使用者先前的編輯內容。
 */
class ImportRecordTest {

    private static final Instant NOW = Instant.parse("2026-10-15T08:00:00Z");

    private static ParsedResult tree(String name, ParsePath path) {
        ParsedTask task = new ParsedTask("任務", "做事", "做完", 0, null, null, null, null, null);
        ParsedGoal goal = new ParsedGoal("g1", "目標", "", "完成", 0, List.of(), List.of(task));
        return new ParsedResult(new ParsedProject(name, "/work/p", "完成", null, 3), List.of(goal), path, "m", 10L,
                null, null, null);
    }

    private static ImportRecord record(ImportStatus status, boolean signedOff) {
        return ImportRecord.restore(UUID.randomUUID(), ImportSourceType.MARKDOWN, "# 文件", "a.md",
                status.hasDraft() ? tree("舊", ParsePath.LLM) : null, status.hasDraft() ? ParsePath.LLM : null, "m",
                10L, status, signedOff, signedOff ? "boss" : null, signedOff ? NOW : null, null, NOW, null);
    }

    private static void assertConflict(Runnable action, String reason, String detailKey, Object detailValue) {
        assertThatThrownBy(action::run).isInstanceOfSatisfying(ConflictException.class, e -> {
            assertThat(e.reason()).isEqualTo(reason);
            assertThat(e.details()).containsEntry(detailKey, detailValue);
        });
    }

    private static void notAllowed(ImportStatus status, boolean signedOff, String action, Consumer<ImportRecord> call) {
        ImportRecord r = record(status, signedOff);
        assertConflict(() -> call.accept(r), ErrorReasons.IMPORT_STATE_NOT_ALLOWED, "action", action);
        assertThat(r.status()).as("失敗不改狀態").isEqualTo(status);
    }

    // ── 建立 ─────────────────────────────────────────────────────────────────

    @Test
    void aNewRecordIsUploadedUnsignedAndHasNoParseResultYet() {
        ImportRecord r = ImportRecord.create(ImportSourceType.PLAIN_TEXT, "內容", null, NOW);
        assertThat(r.status()).isEqualTo(ImportStatus.UPLOADED);
        assertThat(r.signedOff()).isFalse();
        assertThat(r.parsedResult()).isNull();
        assertThat(r.parsePath()).isNull();
        assertThat(r.lastParseErrors()).isNull();
        assertThat(r.projectId()).isNull();
    }

    // ── parse ────────────────────────────────────────────────────────────────

    @Test
    void parseIsAllowedFromUploadedAndFromUnsignedDraftsAndMovesToParsing() {
        for (ImportStatus status : List.of(ImportStatus.UPLOADED, ImportStatus.PARSED, ImportStatus.REVIEWING)) {
            ImportRecord r = record(status, false);
            r.beginParse();
            assertThat(r.status()).as(status.name()).isEqualTo(ImportStatus.PARSING);
        }
    }

    @Test
    void parseChecksRunInTheDocumentedOrderTerminalThenParsingThenSignedOff() {
        notAllowed(ImportStatus.IMPORTED, false, "parse", ImportRecord::beginParse);
        notAllowed(ImportStatus.REJECTED, false, "parse", ImportRecord::beginParse);
        assertConflict(() -> record(ImportStatus.PARSING, false).beginParse(), ErrorReasons.IMPORT_PARSING, "status",
                "PARSING");
        assertConflict(() -> record(ImportStatus.PARSED, true).beginParse(),
                ErrorReasons.IMPORT_SIGNED_OFF_NO_REPARSE, "signedOffBy", "boss");
    }

    @Test
    void beginParseClearsTheLastParseErrors() {
        ImportRecord r = ImportRecord.restore(UUID.randomUUID(), ImportSourceType.MARKDOWN, "x", null, null, null, null,
                null, ImportStatus.UPLOADED, false, null, null, null, NOW,
                List.of(new GateError("max_steps", "太多", "goals")));
        r.beginParse();
        assertThat(r.lastParseErrors()).isNull();
    }

    @Test
    void aSuccessfulParseStoresTheTreeAndServerFieldsAndLeavesTheRecordUnsigned() {
        ImportRecord r = record(ImportStatus.UPLOADED, false);
        r.beginParse();
        r.completeParse(tree("新", ParsePath.DECOMPOSE));
        assertThat(r.status()).isEqualTo(ImportStatus.PARSED);
        assertThat(r.signedOff()).isFalse();
        assertThat(r.parsePath()).isEqualTo(ParsePath.DECOMPOSE);
        assertThat(r.aiModel()).isEqualTo("m");
        assertThat(r.tokenUsed()).isEqualTo(10L);
        assertThat(r.parsedResult().project().name()).isEqualTo("新");
        assertThat(r.lastParseErrors()).isNull();
    }

    @Test
    void aFailedParseReturnsToUploadedKeepsThePreviousTreeAndOnlyGateFailuresStoreErrors() {
        ImportRecord r = record(ImportStatus.PARSED, false);
        ParsedResult before = r.parsedResult();
        r.beginParse();
        r.failParse(List.of(new GateError("cycle", "成環", "goals[0].dependsOn")));
        assertThat(r.status()).isEqualTo(ImportStatus.UPLOADED);
        assertThat(r.parsedResult()).as("使用者的編輯不因一次失敗的重解析而消失").isSameAs(before);
        assertThat(r.parsePath()).isEqualTo(ParsePath.LLM);
        assertThat(r.lastParseErrors()).singleElement().extracting(GateError::gate).isEqualTo("cycle");

        r.beginParse();
        r.failParse(null);
        assertThat(r.status()).isEqualTo(ImportStatus.UPLOADED);
        assertThat(r.lastParseErrors()).as("非閘的失敗不寫").isNull();
    }

    @Test
    void completeAndFailParseRequireTheParsingState() {
        notAllowed(ImportStatus.UPLOADED, false, "parse", r -> r.completeParse(tree("x", ParsePath.LLM)));
        notAllowed(ImportStatus.PARSED, false, "parse", r -> r.failParse(null));
    }

    // ── PUT result ───────────────────────────────────────────────────────────

    @Test
    void editingMovesToReviewingRevokesSignoffAndKeepsTheServerOwnedFields() {
        ImportRecord r = record(ImportStatus.PARSED, true);
        ParsedResult edited = ParsedResult.tree(new ParsedProject("改名", "/work/q", "新標準", null, 5),
                tree("x", null).goals());
        r.editResult(edited);
        assertThat(r.status()).isEqualTo(ImportStatus.REVIEWING);
        assertThat(r.signedOff()).as("編輯撤銷 signoff").isFalse();
        assertThat(r.signedOffBy()).isNull();
        assertThat(r.signedOffAt()).isNull();
        assertThat(r.parsedResult().project().name()).isEqualTo("改名");
        assertThat(r.parsedResult().path()).as("伺服器欄位沿用庫內值").isEqualTo(ParsePath.LLM);
        assertThat(r.parsedResult().aiModel()).isEqualTo("m");
        assertThat(r.parsedResult().tokenUsed()).isEqualTo(10L);
    }

    @Test
    void editingIsOnlyAllowedForDrafts() {
        for (ImportStatus status : List.of(ImportStatus.UPLOADED, ImportStatus.PARSING, ImportStatus.IMPORTED,
                ImportStatus.REJECTED)) {
            notAllowed(status, false, "editResult", r -> r.editResult(tree("x", null)));
            notAllowed(status, false, "editResult", ImportRecord::requireEditAllowed);
        }
    }

    // ── signoff ──────────────────────────────────────────────────────────────

    @Test
    void signoffRequiresANonBlankApproverAndStripsIt() {
        ImportRecord r = record(ImportStatus.PARSED, false);
        for (String blank : new String[] {null, "", "   ", "\t"}) {
            assertThatThrownBy(() -> r.signoff(blank, NOW)).isInstanceOf(ValidationException.class);
        }
        assertThat(r.signedOff()).isFalse();
        r.signoff("  Alice  ", NOW);
        assertThat(r.signedOff()).isTrue();
        assertThat(r.signedOffBy()).isEqualTo("Alice");
        assertThat(r.signedOffAt()).isEqualTo(NOW);
        assertThat(r.status()).as("signoff 只批准、不落庫").isEqualTo(ImportStatus.PARSED);
    }

    @Test
    void signoffIsRefusedTwiceAndOutsideDrafts() {
        ImportRecord signed = record(ImportStatus.REVIEWING, true);
        assertConflict(() -> signed.signoff("x", NOW), ErrorReasons.ALREADY_SIGNED_OFF, "signedOffBy", "boss");
        for (ImportStatus status : List.of(ImportStatus.UPLOADED, ImportStatus.PARSING, ImportStatus.IMPORTED,
                ImportStatus.REJECTED)) {
            notAllowed(status, false, "signoff", r -> r.signoff("x", NOW));
        }
    }

    // ── confirm ──────────────────────────────────────────────────────────────

    @Test
    void confirmNeedsASignedOffDraftOtherwiseItExplainsWhy() {
        assertConflict(() -> record(ImportStatus.PARSED, false).requireConfirmAllowed(),
                ErrorReasons.IMPORT_NOT_SIGNED_OFF, "signedOff", false);
        assertConflict(() -> record(ImportStatus.REVIEWING, false).requireConfirmAllowed(),
                ErrorReasons.IMPORT_NOT_SIGNED_OFF, "status", "REVIEWING");
        for (ImportStatus status : List.of(ImportStatus.UPLOADED, ImportStatus.PARSING, ImportStatus.REJECTED)) {
            notAllowed(status, false, "confirm", ImportRecord::requireConfirmAllowed);
        }
        record(ImportStatus.PARSED, true).requireConfirmAllowed();
    }

    @Test
    void confirmingTwiceTellsTheProjectIdInsteadOfCreatingASecondProject() {
        ImportRecord r = record(ImportStatus.REVIEWING, true);
        UUID project = UUID.randomUUID();
        r.markImported(project);
        assertThat(r.status()).isEqualTo(ImportStatus.IMPORTED);
        assertThat(r.projectId()).isEqualTo(project);
        assertConflict(r::requireConfirmAllowed, ErrorReasons.ALREADY_IMPORTED, "projectId", project.toString());
        assertThatThrownBy(() -> r.markImported(UUID.randomUUID())).isInstanceOf(ConflictException.class);
    }

    // ── reject ───────────────────────────────────────────────────────────────

    @Test
    void rejectIsAllowedFromUploadedAndDraftsButNotWhileParsingOrAfterATerminalState() {
        for (ImportStatus status : List.of(ImportStatus.UPLOADED, ImportStatus.PARSED, ImportStatus.REVIEWING)) {
            ImportRecord r = record(status, false);
            r.reject();
            assertThat(r.status()).isEqualTo(ImportStatus.REJECTED);
        }
        for (ImportStatus status : List.of(ImportStatus.PARSING, ImportStatus.IMPORTED, ImportStatus.REJECTED)) {
            notAllowed(status, false, "reject", ImportRecord::reject);
        }
    }
}
