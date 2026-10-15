package com.aisdlc.console.application.port.out;

import com.aisdlc.console.application.port.in.ImportUseCase.ListQuery;
import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.domain.model.imports.ImportRecord;

import java.util.Optional;
import java.util.UUID;

/** 匯入記錄儲存埠（匯入記錄沒有軟刪除：REJECTED／IMPORTED 為終態，列表仍可見）。 */
public interface ImportRecordRepository {

    ImportRecord save(ImportRecord record);

    Optional<ImportRecord> findById(UUID id);

    /** 取記錄並鎖列（SELECT … FOR UPDATE）：序列化同一筆的並發 parse／signoff／confirm。 */
    Optional<ImportRecord> findByIdForUpdate(UUID id);

    /** 列表（不含 sourceContent／parsedResult 的語意由 DTO 層決定；這裡回完整聚合）。 */
    PageResult<ImportRecord> search(ListQuery query);

    /**
     * 啟動復原：把殘留的 PARSING 一律退回 UPLOADED。parse 是同步呼叫（持有 PARSING 的請求執行緒隨行程消失），
     * 重啟後不可能還有解析在進行；不處理的話該筆會永遠卡在 PARSING（parse／reject 皆 409）。回傳受影響筆數。
     */
    int resetStaleParsing();
}
