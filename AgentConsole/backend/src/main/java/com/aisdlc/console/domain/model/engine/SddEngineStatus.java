package com.aisdlc.console.domain.model.engine;

import java.time.Instant;
import java.util.List;

/**
 * AISDLC_SDD 引擎現在的狀態（契約 §1.7.1；D-16）。<b>引擎不可用也是一個狀態、不是一次失敗</b>：這支查詢回報的是「引擎現在怎麼樣」，
 * 前端據此畫「不可用」而不是錯誤頁，所以 Bridge 不可達、503 都轉成 {@code available=false}＋{@code reason}（沿用「Bridge 不可達回 200」的慣例）。
 *
 * @param available {@code GET /sdd/version} 與 {@code GET /sdd/fsm} 都成功為 true；任一失敗為 false
 * @param reason    見 {@link SddEngineReason}；{@code available=true} 且沒有問題時為 null
 * @param version   {@code GET /sdd/version} 失敗時為 null
 * @param projects  {@code available=false} 時為空；{@code available=true} 而為空＝SDD 目錄存在但還沒有任何 FSM 狀態檔（正常狀態）
 * @param fsm       帶了 {@code project} 且取得時有值；其餘為 null
 * @param checkedAt console-api 處理這次請求的時間
 */
public record SddEngineStatus(boolean available, SddEngineReason reason, SddVersion version,
                              List<SddProjectEntry> projects, SddFsmState fsm, Instant checkedAt) {

    public SddEngineStatus {
        projects = projects == null ? List.of() : List.copyOf(projects);
    }
}
