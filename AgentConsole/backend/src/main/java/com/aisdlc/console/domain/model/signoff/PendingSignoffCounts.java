package com.aisdlc.console.domain.model.signoff;

/**
 * 四種草案各自的待簽核數（契約 §1.8.1；D-18）。<b>{@link #total()} 恆等於通知摘要的 {@code pendingSignoffs}</b>：兩者的述詞由同一處產生
 * （{@code PendingSignoffSql}），清單的 {@code limit} 不影響這裡的任何一個數字。
 */
public record PendingSignoffCounts(int projects, int goals, int tasks, int imports) {

    public int total() {
        return projects + goals + tasks + imports;
    }
}
