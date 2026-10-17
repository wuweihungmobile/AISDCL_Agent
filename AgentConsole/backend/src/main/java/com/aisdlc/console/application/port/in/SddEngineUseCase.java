package com.aisdlc.console.application.port.in;

import com.aisdlc.console.domain.model.engine.SddEngineStatus;

import java.util.UUID;

/** AISDLC_SDD 引擎狀態查詢（API-ENG-01、API-ENG-02；契約 §1.7.1、§1.10.4；D-16、D-115-02）：Console 對 FSM 狀態的唯一消費點，只讀。 */
public interface SddEngineUseCase {

    /**
     * 依序查 Bridge 的 {@code /sdd/version}、{@code /sdd/fsm}，有要查的專案時再查 {@code /sdd/fsm/{project}}；任一失敗即短路。
     * <b>引擎不可用也回結果</b>（{@code available=false}＋{@code reason}，不丟例外）。
     *
     * @param project   FSM 專案名的有效值（可以是原名，Console 不淨化）；null＝沒指定。非 null 須 1～200 字元且不含控制字元，否則
     *                  {@code ValidationException}（{@code errors[0].field=project}，HTTP 400；先於 {@code projectId} 的 404 檢查）
     * @param projectId v1.5：帶了＝讀「該 Console 專案」的 FSM：{@code root}＝該專案的 {@code executionPath}，{@code project} 省略時取
     *                  專案的有效 FSM 專案；專案不存在或已軟刪除 → {@code NotFoundException}（404）；null＝v1.4 行為（讀 Bridge 預設的狀態目錄）
     */
    SddEngineStatus status(String project, UUID projectId);
}
