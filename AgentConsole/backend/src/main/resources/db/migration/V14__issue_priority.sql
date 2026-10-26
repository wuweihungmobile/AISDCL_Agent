-- ============================================================================
-- V14__issue_priority.sql — 議題中心：Console 自有的優先順序表（TCS-IssueCenter-20261027 §C6、R-IC-59；PRD §6.5）
-- 議題本身（觀察、缺陷、提案）住在 SelfImproving 三類帳本，Console 不寫帳本；Console 在議題中心唯一自有的資料就是「掌舵者排的順位」：
-- 一個議題最多一列，列存在＝有順位，沒有「沒有順位的列」（清除＝DELETE，所以 rank、note 都是 NOT NULL，約束放結構層）。
-- ① 順位可重複（沒有唯一鍵）：同順位的議題依顯示序的後續鍵（嚴重度→最後更新→編號）排。
-- ② 不存歷史：變更軌跡在 console.audit_log（AuditLoggingFilter 對每個 PUT／DELETE 留一列）。
-- ③ issue_id 的 CHECK 與 API 的輸入閘同式（OBS-SI-nnn、PROP-SI-nnn、DEF-<族>-<序>）；note 以字元（code point）計長，與輸入閘同口徑。
-- ④ 非「待您決定、待解、進行中」的議題（已完成、延後、候選、觀察中、未歸類）不可設定順位（API 回 409 issue_not_rankable）；議題設定後才轉成
--    那些狀態時，遺留的列留在表中（不顯示、不參與排序），ADMIN 可用 DELETE 清掉。
-- 沒有 JPA 實體（ddl-auto=validate 不檢查本表）：以 JDBC 配接器存取，寫入敘述只有 UPSERT 與 DELETE 兩條。
-- ============================================================================
CREATE TABLE console.issue_priority (
    issue_id VARCHAR(64) PRIMARY KEY CHECK (issue_id ~ '^(OBS-SI-[0-9]{3,}|PROP-SI-[0-9]{3,}|DEF-[0-9]+-[0-9]+)$'),
    rank     INTEGER      NOT NULL CHECK (rank BETWEEN 1 AND 9999),
    note     VARCHAR(200) NOT NULL DEFAULT '',
    set_by   VARCHAR(64)  NOT NULL,
    set_at   TIMESTAMP WITH TIME ZONE NOT NULL
);
