package com.aisdlc.console.domain.model.issue;

import java.time.OffsetDateTime;

/**
 * 議題中心的優先順序（{@code console.issue_priority} 的一列；TCS-IssueCenter-20261027 R-IC-54～R-IC-60、§C6）：掌舵者對某個議題排的順位。
 * 這是 Console 在議題中心<b>唯一自有的資料</b>——議題本身在 SelfImproving 帳本，Console 不寫帳本。
 *
 * <p>一個議題最多一列；列存在＝有順位（清除順位＝刪列，所以沒有「沒有順位的列」）。順位可重複，不存歷史（變更軌跡在 {@code console.audit_log}）。
 *
 * @param issueId 議題編號（{@code OBS-SI-nnn}、{@code PROP-SI-nnn}、{@code DEF-<族>-<序>}）
 * @param rank    順位（整數 1～9999；1 最先）
 * @param note    備註（可為空字串；至多 200 個字元〔code point〕，不含控制字元）
 * @param setBy   設定者（JWT 帳號）
 * @param setAt   設定時間（伺服器時間，帶 offset）
 */
public record IssuePriority(String issueId, int rank, String note, String setBy, OffsetDateTime setAt) {
}
