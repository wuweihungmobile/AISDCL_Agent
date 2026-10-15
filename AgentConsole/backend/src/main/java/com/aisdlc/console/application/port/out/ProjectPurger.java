package com.aisdlc.console.application.port.out;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * 軟刪除專案的實體清除埠（契約 §1.6.5，C-3；ADR-001 D19）。<b>只有專案層級</b>：清掉一個軟刪除的專案連同它的整棵子資料；
 * 在存活專案內單獨軟刪除的目標／任務不在清除範圍（它們隨其專案被清除時才一併實體刪除）。
 */
public interface ProjectPurger {

    /** 已軟刪除（{@code is_deleted}）且 {@code deleted_at} 早於 {@code cutoff} 的專案 id，由舊到新。 */
    List<UUID> findExpired(Instant cutoff);

    /**
     * 實體刪除一個專案與它的整棵子資料：目標、任務、目標依賴、執行批次與其步驟／檢查點／審核項／告警／token 樣本；
     * {@code import_records.project_id} 置 NULL（匯入記錄本身保留）。呼叫端須提供交易（一個專案一個交易）。
     *
     * @return 是否真的刪到專案（已被別人清掉＝false）
     */
    boolean purge(UUID projectId);
}
