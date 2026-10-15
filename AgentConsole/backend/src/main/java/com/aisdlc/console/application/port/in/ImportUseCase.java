package com.aisdlc.console.application.port.in;

import com.aisdlc.console.application.port.in.ManageProjectUseCase.ProjectView;
import com.aisdlc.console.domain.model.imports.ImportRecord;
import com.aisdlc.console.domain.model.imports.ImportSourceType;
import com.aisdlc.console.domain.model.imports.ImportStatus;
import com.aisdlc.console.domain.model.imports.ParseOptions;
import com.aisdlc.console.domain.model.imports.ParseWarning;
import com.aisdlc.console.domain.model.imports.ParsedResult;

import java.util.List;
import java.util.UUID;

/**
 * BRD/PRD 匯入用例（PRD §5.2、§7.1.4；契約 §1.1）。找不到一律 NotFoundException（404）；
 * 狀態不允許 409（reason＝{@code 匯入記錄狀態不允許此操作}）；有界閘 422；Bridge 失敗 502／504。
 */
public interface ImportUseCase {

    /** 列表可排序欄位（契約 §1.1.8：{@code createdAt|status}）。 */
    enum SortField { CREATED_AT, STATUS }

    /**
     * 列表查詢條件。
     *
     * @param fileNameQuery 來源檔名模糊搜尋（不分大小寫；{@code %}／{@code _} 視為字面）；null／空白＝不篩
     * @param status        狀態篩選；null＝不篩
     */
    record ListQuery(String fileNameQuery, ImportStatus status, SortField sortField, boolean ascending, int page,
                     int size) {
    }

    /** parse／editResult 成功的結果：記錄＋非阻擋提示。 */
    record ParseOutcome(ImportRecord record, List<ParseWarning> warnings) {
    }

    ImportRecord upload(String fileName, byte[] content);

    ImportRecord createFromText(String content, String sourceFileName, ImportSourceType sourceType);

    PageResult<ImportRecord> list(ListQuery query);

    ImportRecord get(UUID id);

    ParseOutcome parse(UUID id, ParseOptions options);

    ParseOutcome editResult(UUID id, ParsedResult edited);

    ImportRecord signoff(UUID id, String approver);

    ProjectView confirm(UUID id, String actor);

    ImportRecord reject(UUID id);
}
