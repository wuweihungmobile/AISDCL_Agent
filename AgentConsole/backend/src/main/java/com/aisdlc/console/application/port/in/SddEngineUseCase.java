package com.aisdlc.console.application.port.in;

import com.aisdlc.console.domain.model.engine.SddEngineStatus;

/** AISDLC_SDD 引擎狀態查詢（API-ENG-01；契約 §1.7.1；D-16）：Console 對 FSM 狀態的唯一消費點，只讀。 */
public interface SddEngineUseCase {

    /**
     * 依序查 Bridge 的 {@code /sdd/version}、{@code /sdd/fsm}，帶了 {@code project} 再查 {@code /sdd/fsm/{project}}；任一失敗即短路。
     * <b>引擎不可用也回結果</b>（{@code available=false}＋{@code reason}，不丟例外）。
     *
     * @param project FSM 專案名；null＝不查單一專案（{@code fsm=null}）。非 null 須符合 {@code ^[A-Za-z0-9._-]{1,128}$}，否則
     *                {@code ValidationException}（{@code errors[0].field=project}，HTTP 400）
     */
    SddEngineStatus status(String project);
}
