package com.aisdlc.console.domain.model.imports;

import java.util.List;
import java.util.Map;

/**
 * 三層草案樹（PRD §5.2.4 輸出 JSON 的超集；契約 §1.1.3）。存於 {@code import_records.parsed_result}（JSONB）。
 *
 * <p>後半的 {@code path／aiModel／tokenUsed／reasoning／draftIds／specDigest} 是<b>伺服器擁有</b>的欄位：
 * {@code PUT /import/{id}/result} 請求帶了也忽略，一律以庫內值為準（{@link #withServerFieldsOf(ParsedResult)}）。
 *
 * @param project   專案層（必填）
 * @param goals     目標陣列；陣列順序即排序
 * @param path      解析路徑
 * @param aiModel   路徑 B：模型回報的名稱
 * @param tokenUsed 路徑 B：{@code usage.total_tokens}
 * @param reasoning 路徑 C：Bridge decompose 的 reasoning
 * @param draftIds  路徑 C：Bridge draft_id 清單（signoff 時逐一 {@code :approve}）
 * @param specDigest 路徑 A：SDD 規格 digest
 */
public record ParsedResult(ParsedProject project, List<ParsedGoal> goals, ParsePath path, String aiModel,
                           Long tokenUsed, String reasoning, List<String> draftIds, String specDigest) {

    /** 只有三層樹、沒有伺服器欄位（編輯請求、LLM 草稿用）。 */
    public static ParsedResult tree(ParsedProject project, List<ParsedGoal> goals) {
        return new ParsedResult(project, goals, null, null, null, null, null, null);
    }

    /** 以本樹的 project／goals 搭配 {@code owner} 的伺服器欄位。 */
    public ParsedResult withServerFieldsOf(ParsedResult owner) {
        return new ParsedResult(project, goals, owner.path, owner.aiModel, owner.tokenUsed, owner.reasoning,
                owner.draftIds, owner.specDigest);
    }

    public ParsedResult withTree(ParsedProject newProject, List<ParsedGoal> newGoals) {
        return new ParsedResult(newProject, newGoals, path, aiModel, tokenUsed, reasoning, draftIds, specDigest);
    }

    public int totalTasks() {
        return goals == null ? 0 : goals.stream().mapToInt(g -> g.tasks() == null ? 0 : g.tasks().size()).sum();
    }

    /**
     * 專案層。
     *
     * @param autonomyLevel 1～10；null 表示沒有指定（落庫時取 3）
     */
    public record ParsedProject(String name, String executionPath, String passCriteria, String description,
                                Integer autonomyLevel) {
    }

    /**
     * 目標層。
     *
     * @param key       樹內唯一的穩定鍵；{@code dependsOn} 引用它
     * @param sortOrder 伺服器依陣列順序重編（0 起連續）
     * @param dependsOn 前置目標的 key；null 視為沒有依賴
     */
    public record ParsedGoal(String key, String name, String description, String passCriteria, int sortOrder,
                             List<String> dependsOn, List<ParsedTask> tasks) {
    }

    /**
     * 任務層。
     *
     * @param passCriteriaSpec 結構化通過標準（JSON 物件；路徑 C 會放 {source, stepId, draftId}）
     * @param maxRetries       0～20；null 落庫時取預設 3
     */
    public record ParsedTask(String name, String description, String passCriteria, int sortOrder,
                             Long estimatedTokens, String evaluatorCommand, String expectedOutputRegex,
                             Map<String, Object> passCriteriaSpec, Integer maxRetries) {
    }
}
