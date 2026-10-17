package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.imports.ParsePath;
import com.aisdlc.console.domain.model.imports.ParsedResult;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedGoal;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedProject;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedTask;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.util.List;
import java.util.Map;

/**
 * 三層草案樹的 API 形狀（契約 §1.1；PRD §5.2.4 輸出 JSON 的超集）。請求（{@code PUT /import/{id}/result}）與回應共用。
 *
 * <p>結構性問題（缺必填欄位、型別錯誤、{@code goals}／{@code tasks} 為空、通過標準空白）是 <b>400</b>（Bean Validation）；
 * 任務的 {@code name}／{@code description} 為<b>空白字串</b>則不在這裡擋，交給有界閘 {@code empty_prompt}（422，AR-21）。
 * 伺服器擁有的欄位（{@code path／aiModel／tokenUsed／reasoning／draftIds／specDigest}，以及 v1.5 的
 * {@code specFormatVersion／sddProject／sddSpecDir／sddSpecFile}）請求帶了也忽略。
 */
@Schema(name = "ParsedResult", description = "三層草案樹（專案→目標→任務）；後半的 path／aiModel／… 為伺服器擁有的欄位，請求帶了也忽略")
public record ParsedResultDto(
        @NotNull(message = "project 不可為空") @Valid ParsedProjectDto project,
        @NotEmpty(message = "goals 不可為空") List<@NotNull(message = "目標不可為空") @Valid ParsedGoalDto> goals,
        ParsePath path,
        String aiModel,
        Long tokenUsed,
        String reasoning,
        List<String> draftIds,
        String specDigest,
        @Schema(description = "v1.5：路徑 A 的規格格式版本（Bridge /sdd/compile 的 spec_format_version）；伺服器擁有，只供顯示與稽核")
        String specFormatVersion,
        @Schema(description = "v1.5：路徑 A 通過凍結閘的 FSM 專案的標準鍵（Bridge 回應的 fsm_project）；伺服器擁有；confirm 據此回填專案的 sddProject")
        String sddProject,
        @Schema(description = "v1.5：規格檔所在目錄（絕對路徑）＝Bridge 回應 spec_path 的父目錄；伺服器擁有；confirm 據此回填專案的 sddSpecDir")
        String sddSpecDir,
        @Schema(description = "v1.5：路徑 A 實際採用的規格檔（絕對路徑）＝Bridge 回應的 spec_path；伺服器擁有；confirm 據此回填專案的 sddSpecFile")
        String sddSpecFile) {

    public static ParsedResultDto from(ParsedResult tree) {
        return new ParsedResultDto(ParsedProjectDto.from(tree.project()),
                tree.goals().stream().map(ParsedGoalDto::from).toList(), tree.path(), tree.aiModel(),
                tree.tokenUsed(), tree.reasoning(), tree.draftIds(), tree.specDigest(), tree.specFormatVersion(),
                tree.sddProject(), tree.sddSpecDir(), tree.sddSpecFile());
    }

    /** 轉成 domain（只有三層樹，伺服器欄位忽略）；同時對每個任務的 passCriteriaSpec 套用 NFR-SEC-03 消毒。 */
    public ParsedResult toDomain() {
        return ParsedResult.tree(project.toDomain(), goals.stream().map(ParsedGoalDto::toDomain).toList());
    }

    /** 專案層。 */
    @Schema(name = "ParsedProject")
    public record ParsedProjectDto(
            @NotBlank(message = "專案名稱不能為空") @Size(max = 200, message = "專案名稱長度不可超過 200 字元") String name,
            @NotBlank(message = "執行路徑不能為空") @Size(max = 500, message = "執行路徑長度不可超過 500 字元")
            String executionPath,
            @NotBlank(message = "專案通過標準不能為空") String passCriteria,
            String description,
            @Min(value = 1, message = "自治等級必須介於 1 到 10") @Max(value = 10, message = "自治等級必須介於 1 到 10")
            Integer autonomyLevel) {

        static ParsedProjectDto from(ParsedProject p) {
            return new ParsedProjectDto(p.name(), p.executionPath(), p.passCriteria(), p.description(),
                    p.autonomyLevel());
        }

        ParsedProject toDomain() {
            return new ParsedProject(name, executionPath, passCriteria, description, autonomyLevel);
        }
    }

    /** 目標層：{@code key} 在整棵樹內唯一，{@code dependsOn} 引用其他目標的 key。 */
    @Schema(name = "ParsedGoal")
    public record ParsedGoalDto(
            @NotBlank(message = "目標 key 不能為空") @Size(max = 64, message = "目標 key 長度不可超過 64 字元") String key,
            @NotBlank(message = "目標名稱不能為空") @Size(max = 200, message = "目標名稱長度不可超過 200 字元") String name,
            String description,
            @NotBlank(message = "目標通過標準不能為空") String passCriteria,
            @Schema(description = "伺服器依陣列順序重編（0 起連續）；請求帶了也忽略") Integer sortOrder,
            List<String> dependsOn,
            @NotEmpty(message = "每個目標至少要有一個任務")
            List<@NotNull(message = "任務不可為空") @Valid ParsedTaskDto> tasks) {

        static ParsedGoalDto from(ParsedGoal g) {
            return new ParsedGoalDto(g.key(), g.name(), g.description(), g.passCriteria(), g.sortOrder(),
                    g.dependsOn(), g.tasks().stream().map(ParsedTaskDto::from).toList());
        }

        ParsedGoal toDomain() {
            return new ParsedGoal(key, name, description, passCriteria, sortOrder == null ? 0 : sortOrder,
                    dependsOn == null ? List.of() : dependsOn, tasks.stream().map(ParsedTaskDto::toDomain).toList());
        }
    }

    /**
     * 任務層：{@code name}／{@code description} 缺漏或 null 是 400；<b>空白字串</b>是 422 閘 {@code empty_prompt}。
     */
    @Schema(name = "ParsedTask")
    public record ParsedTaskDto(
            @NotNull(message = "任務名稱不可缺漏") @Size(max = 200, message = "任務名稱長度不可超過 200 字元") String name,
            @NotNull(message = "任務描述不可缺漏") String description,
            @NotBlank(message = "任務通過標準不能為空") String passCriteria,
            @Schema(description = "伺服器依陣列順序重編（0 起連續）；請求帶了也忽略") Integer sortOrder,
            @Min(value = 0, message = "預估 Token 不可為負數") Long estimatedTokens,
            @Size(max = 1000, message = "驗證命令長度不可超過 1000 字元")
            @Schema(description = "NFR-SEC-03：含禁用字元 → 400") String evaluatorCommand,
            @Size(max = 1000, message = "期望輸出正規表示式長度不可超過 1000 字元")
            @Schema(description = "須可編譯，否則 400") String expectedOutputRegex,
            @Schema(description = "結構化通過標準（JSON 物件；路徑 C 會放 {source, stepId, draftId}）")
            Map<String, Object> passCriteriaSpec,
            @Min(value = 0, message = "最大重試次數不可為負數") @Max(value = 20, message = "最大重試次數不可超過 20")
            Integer maxRetries) {

        static ParsedTaskDto from(ParsedTask t) {
            return new ParsedTaskDto(t.name(), t.description(), t.passCriteria(), t.sortOrder(),
                    t.estimatedTokens(), t.evaluatorCommand(), t.expectedOutputRegex(), t.passCriteriaSpec(),
                    t.maxRetries());
        }

        ParsedTask toDomain() {
            PassCriteriaSpecRules.validate(passCriteriaSpec);
            return new ParsedTask(name, description, passCriteria, sortOrder == null ? 0 : sortOrder,
                    estimatedTokens, evaluatorCommand, expectedOutputRegex, passCriteriaSpec, maxRetries);
        }
    }
}
