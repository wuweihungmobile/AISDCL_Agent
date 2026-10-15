package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.domain.model.imports.GateError;
import com.aisdlc.console.domain.model.imports.ImportRecord;
import com.aisdlc.console.domain.model.imports.ImportSourceType;
import com.aisdlc.console.domain.model.imports.ImportStatus;
import com.aisdlc.console.domain.model.imports.ParsePath;
import com.aisdlc.console.domain.model.imports.ParsedResult;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedGoal;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedProject;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedTask;
import com.aisdlc.console.infrastructure.persistence.entity.ImportRecordEntity;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * ImportRecord ↔ JSONB 的往返（AR-07）。為什麼重要：草案樹與閘違規以 JSON 文字落在 jsonb 欄位；欄位名或結構一變，
 * 已存的記錄就讀不回來——這裡鎖住「寫出去的形狀」與「讀回來的值」。
 */
class ImportRecordMapperTest {

    private static final Instant NOW = Instant.parse("2026-10-15T08:00:00Z");

    private static ParsedResult tree() {
        ParsedTask task = new ParsedTask("實作", "請輸出 [T_DONE]", "輸出含 [T_DONE]", 0, 300L, "pytest -q", "\\[T_DONE\\]",
                Map.of("source", "decompose", "stepId", "s1", "weakRegex", false, "nested", Map.of("n", 1)), 5);
        ParsedGoal goal = new ParsedGoal("g1", "核心", "描述", "完成", 0, List.of("g0"), List.of(task));
        return new ParsedResult(new ParsedProject("專案", "/work/p", "通過", "說明", 4), List.of(goal),
                ParsePath.DECOMPOSE, "MiniMax-M2.7", 1152L, "因為…", List.of("d-1", "d-2"), "abc123");
    }

    @Test
    void aFullyPopulatedRecordSurvivesAnEntityRoundTripIncludingTheJsonColumns() {
        UUID project = UUID.randomUUID();
        ImportRecord original = ImportRecord.restore(UUID.randomUUID(), ImportSourceType.PLAIN_TEXT, "原文", "a.txt",
                tree(), ParsePath.DECOMPOSE, "MiniMax-M2.7", 1152L, ImportStatus.IMPORTED, true, "Alice", NOW, project,
                NOW, List.of(new GateError("max_steps", "太多", "goals[0].tasks"), new GateError("brain_failed", "壞", null)));

        ImportRecordEntity entity = ImportRecordMapper.toEntity(original);
        assertThat(entity.status).isEqualTo("IMPORTED");
        assertThat(entity.sourceType).isEqualTo("PLAIN_TEXT");
        assertThat(entity.parsePath).isEqualTo("DECOMPOSE");
        assertThat(entity.parsedResult).contains("\"project\"").contains("\"goals\"").contains("\"draftIds\"");
        assertThat(entity.lastParseErrors).startsWith("[").contains("max_steps");

        ImportRecord back = ImportRecordMapper.toDomain(entity);
        assertThat(back.id()).isEqualTo(original.id());
        assertThat(back.status()).isEqualTo(ImportStatus.IMPORTED);
        assertThat(back.signedOff()).isTrue();
        assertThat(back.signedOffBy()).isEqualTo("Alice");
        assertThat(back.projectId()).isEqualTo(project);
        assertThat(back.parsePath()).isEqualTo(ParsePath.DECOMPOSE);
        assertThat(back.parsedResult()).isEqualTo(original.parsedResult());
        assertThat(back.lastParseErrors()).isEqualTo(original.lastParseErrors());
        assertThat(back.parsedResult().goals().get(0).tasks().get(0).passCriteriaSpec())
                .containsEntry("source", "decompose").containsEntry("weakRegex", false);
    }

    @Test
    void aRecordWithoutParseResultStoresNullsNotEmptyJson() {
        ImportRecord fresh = ImportRecord.create(ImportSourceType.MARKDOWN, "# 文件", null, NOW);
        ImportRecordEntity entity = ImportRecordMapper.toEntity(fresh);
        assertThat(entity.parsedResult).isNull();
        assertThat(entity.lastParseErrors).isNull();
        assertThat(entity.parsePath).isNull();
        ImportRecord back = ImportRecordMapper.toDomain(entity);
        assertThat(back.parsedResult()).isNull();
        assertThat(back.lastParseErrors()).isNull();
    }

    @Test
    void unknownJsonPropertiesInStoredDataAreIgnoredSoOlderOrNewerRowsStillLoad() {
        ImportRecordEntity entity = ImportRecordMapper.toEntity(
                ImportRecord.restore(UUID.randomUUID(), ImportSourceType.MARKDOWN, "x", null, tree(),
                        ParsePath.LLM, null, null, ImportStatus.PARSED, false, null, null, null, NOW, null));
        entity.parsedResult = entity.parsedResult.replaceFirst("\\{", "{\"futureField\":123,");
        assertThat(ImportRecordMapper.toDomain(entity).parsedResult().project().name()).isEqualTo("專案");
    }

    @Test
    void theListProjectionCarriesNeitherTheSourceNorTheParseResult() {
        UUID id = UUID.randomUUID();
        Object[] row = {id, "MARKDOWN", "a.md", "PARSED", true, "Alice", NOW, null, NOW, "m", 10L, "LLM",
                "[{\"gate\":\"cycle\",\"detail\":\"d\",\"location\":\"l\"}]"};
        ImportRecord summary = ImportRecordMapper.toSummary(row);
        assertThat(summary.id()).isEqualTo(id);
        assertThat(summary.sourceContent()).isNull();
        assertThat(summary.parsedResult()).isNull();
        assertThat(summary.status()).isEqualTo(ImportStatus.PARSED);
        assertThat(summary.parsePath()).isEqualTo(ParsePath.LLM);
        assertThat(summary.lastParseErrors()).singleElement().extracting(GateError::gate).isEqualTo("cycle");
    }
}
