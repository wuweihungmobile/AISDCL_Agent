package com.aisdlc.console.application.port.in;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * 備份頁的唯讀查詢（TCS-SysAdminBackup-20261027 §C3.1～§C3.3；API-BK-01～03）。{@code admin}＝呼叫者是 ADMIN：只有 ADMIN 看得到輸出尾段
 * （{@code detailTail}、{@code detail}）與觸發者（{@code requestedBy}）；非 ADMIN 的這些欄位為 null 或缺席（R-BK-21）。
 */
public interface BackupQueryUseCase {

    /**
     * 備份總覽（{@code GET /backups}）：{@code data} 的保序 Map（camelCase；鍵序固定）。控制面未設定、匯出檔不可讀、schema 不符時資料區塊全為 null 並以
     * {@code control.reason} 說明（<b>不當成「沒有備份」</b>）；個別來源失敗只降級該區塊並加 {@code control.warnings}。
     */
    Map<String, Object> overview(boolean admin);

    /** 一筆工作（{@code GET /backups/jobs} 的 {@code items[]}、單筆端點的 {@code data}）。時間為 UTC 的瞬間；耗時為秒。 */
    record JobView(String id, String type, String status, Instant requestedAt, Instant startedAt, Instant finishedAt,
                   Integer durationSeconds, Integer exitCode, String reason, String requestedBy, String detail) {
    }

    /** 工作紀錄的一頁；{@code nextBefore} 是續取游標（尚有更多時為本頁最後一筆的 requestedAt，否則 null）。 */
    record JobPageView(List<JobView> items, Instant nextBefore) {
    }

    /**
     * 工作紀錄（{@code GET /backups/jobs?limit=&before=}）：參數以字串收，非法一律 422 {@code invalid_request}
     * （{@code limit} 預設 20、1～100；{@code before} 為 ISO-8601 瞬間，嚴格小於 requested_at）。
     */
    JobPageView jobs(String limit, String before, boolean admin);

    /** 單筆工作（{@code GET /backups/jobs/{id}}）；查無或 id 不是 UUID 一律 404 {@code backup_job_not_found}。 */
    JobView job(String id, boolean admin);
}
