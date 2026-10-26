package com.aisdlc.console.application.port.in;

import com.aisdlc.console.domain.model.issue.IssuePriority;

import java.util.Map;

/**
 * 議題優先順序的寫入（TCS-IssueCenter-20261027 R-IC-54～R-IC-60、§C4.3、§C4.4）。Console 唯一的議題寫入：<b>不是帳本決定</b>，所以不要求
 * {@code console.si.deciders} 名單；呼叫者的角色（僅 ADMIN）由安全層把關。
 */
public interface IssuePriorityUseCase {

    /**
     * 設定或更新順位（PUT）。{@code body} 是請求本文<b>原樣</b>的 JSON 物件（鍵 {@code rank}、{@code note}）：型別與值域一律在輸入閘一次判完，
     * 所以不能先綁成具型別的物件（否則 {@code rank} 為字串或小數會被框架先擋成 400）。驗證序（先中者定案）：輸入閘 422（{@code invalid_request}，
     * {@code details.violations} 一次全列；Bridge 零呼叫）→取該議題（Bridge 503／502／504、查無 404 {@code si_not_found}）→{@code rankable} 為
     * false 409 {@code issue_not_rankable}→寫入。任何前序失敗都零寫入。
     *
     * @param user 設定者（JWT 帳號）
     * @return 寫入的列（{@code setAt} 為伺服器時間）
     */
    IssuePriority set(String user, String id, Map<String, Object> body);

    /**
     * 清除順位（DELETE）：刪列，列不存在也成功（冪等）。<b>不呼叫 Bridge</b>，所以議題已完成或已不存在時仍清得掉遺留的列。驗證序：輸入閘 422
     * （{@code id} 格式）→刪除。
     */
    void clear(String id);
}
