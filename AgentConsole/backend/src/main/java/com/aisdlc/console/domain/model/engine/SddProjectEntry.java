package com.aisdlc.console.domain.model.engine;

/**
 * FSM 專案清單的一筆（Bridge {@code GET /sdd/fsm} 的 {@code projects[]} 投影；契約 §1.7.1、§3.1.3）。
 * {@code project} 就是 {@code GET /engines/sdd?project=} 吃的鍵，每一筆都點得進去。
 *
 * @param project      檔名 {@code FSM-STATE-<project>.yaml} 中的專案名
 * @param source       檔名
 * @param currentState 檔內 {@code fsm_state.current_state}；缺則 null
 * @param updatedAt    檔內 {@code fsm_state.updated_at}（ISO-8601 字串，原樣、不轉型）；缺則 null
 */
public record SddProjectEntry(String project, String source, String currentState, String updatedAt) {
}
