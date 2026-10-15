-- ============================================================================
-- V5__seed_engine_configs.sql — Phase 3／6 補強（契約 §0.5；Architecture §11.4 的 V5 補充鍵）
-- ① 新增九個引擎對映鍵（autoclaude 六個、model 一個、execution 兩個）；加上來自附錄 C 的 validation_rule 與 impact_note
-- ② 為全部 50 個鍵補 validation_rule（V2 本波不填，留給 Phase 6）
-- ③ system_configs.impact_note（US-S-08 影響範圍提示）
-- ④ import_records.parse_path／last_parse_errors（AR-07：解析路徑與「最近一次被有界閘拒絕」的原因各有專屬欄位）
-- ⑤ 預設值校正（AR-06、AR-09）：只在值仍等於舊預設時才改，不覆蓋管理員改過的值
-- 🔴 唯一真相源＝契約附錄 C；正規表示式為 Java 語意、對完整字串比對（ConfigValueRules 以 Pattern.matches 套用）。
--    PostgreSQL 的 standard_conforming_strings 預設為 on，字串內的反斜線是字面值，不需加倍。
-- ============================================================================

-- ── ③④ 新欄位 ───────────────────────────────────────────────────────────────
ALTER TABLE console.system_configs ADD COLUMN impact_note VARCHAR(500);

ALTER TABLE console.import_records
    ADD COLUMN parse_path VARCHAR(20),          -- SDD／LLM／DECOMPOSE；第一次成功解析後才有值
    ADD COLUMN last_parse_errors JSONB;         -- GateError[]；僅「被有界閘拒絕」時寫入，成功解析後清為 NULL

-- ── ① 九個新鍵 ──────────────────────────────────────────────────────────────
INSERT INTO console.system_configs (category, key, value, value_type, default_value, description, is_encrypted) VALUES
('autoclaude', 'claudeCommand', 'claude', 'STRING', 'claude', 'Claude CLI 指令（對映引擎 claude.command；不可含空白）', FALSE),
('autoclaude', 'claudeExtraArgs', '', 'STRING', '', 'Claude CLI 額外參數（以空白分隔；對映引擎 claude.extra_args）', FALSE),
('autoclaude', 'claudeContinueFlag', '--continue', 'STRING', '--continue', 'Claude CLI 續跑旗標（對映引擎 claude.continue_flag）', FALSE),
('autoclaude', 'claudeEncoding', 'utf-8', 'STRING', 'utf-8', 'Claude CLI 輸出編碼（對映引擎 claude.encoding）', FALSE),
('autoclaude', 'dbDsn', '', 'ENCRYPTED', '', 'AutoClaude 資料庫連線字串（加密儲存；環境變數 AUTOCLAUDE_DB_DSN）', TRUE),
('autoclaude', 'dualReadResolution', 'yaml_wins', 'ENUM', 'yaml_wins', 'Dual 讀取衝突解決 (yaml_wins / db_wins / fail_loud；對映引擎 storage.dual_read_resolution)', FALSE),
('model', 'enableKernelBrain', 'false', 'BOOLEAN', 'false', '啟用 Kernel Brain（對映引擎 minimax.enable_kernel_brain）', FALSE),
('execution', 'autoResume', 'true', 'BOOLEAN', 'true', 'Token halt 後自動續跑（對映引擎 token_guard.auto_resume）', FALSE),
('execution', 'maxAutoResumes', '10', 'INTEGER', '10', '單次 playbook 最多自動恢復次數（對映引擎 token_guard.max_auto_resumes）', FALSE);

-- ── ② 全部 50 個鍵的 validation_rule（附錄 C）────────────────────────────────
UPDATE console.system_configs AS c SET validation_rule = v.rule
FROM (VALUES
    ('model', 'provider', '^(ANTHROPIC|OPENAI|LOCAL|CUSTOM)$'),
    ('model', 'apiUrl', '^https?://[^\s/?#][^\s]*$'),
    ('model', 'apiKey', '^.{0,512}$'),
    ('model', 'name', '^[A-Za-z0-9._:/\-]{1,100}$'),
    ('model', 'maxTokensPerRequest', '^[1-9][0-9]{0,5}$'),
    ('model', 'temperature', '^[0-9](\.[0-9]+)?$'),
    ('model', 'topP', '^[01](\.[0-9]+)?$'),
    ('model', 'timeout', '^[1-9][0-9]{0,2}$'),
    ('model', 'rateLimitPerMinute', '^[1-9][0-9]{0,4}$'),
    ('model', 'enableKernelBrain', '^(true|false)$'),
    ('agent', 'defaultAutonomyLevel', '^([1-9]|10)$'),
    ('agent', 'maxConcurrentTasks', '^[1-9][0-9]?$'),
    ('agent', 'taskTimeout', '^[1-9][0-9]{1,4}$'),
    ('agent', 'maxRetries', '^([0-9]|1[0-9]|20)$'),
    ('agent', 'retryBackoffMs', '^[0-9]{1,7}$'),
    ('agent', 'retryBackoffMultiplier', '^([1-9]|10)(\.[0-9]+)?$'),
    ('agent', 'checkpointInterval', '^[1-9][0-9]{0,3}$'),
    ('agent', 'enableAutoMutation', '^(true|false)$'),
    ('agent', 'enableSelfEvolution', '^(true|false)$'),
    ('execution', 'globalTokenBudget', '^[1-9][0-9]{0,11}$'),
    ('execution', 'tokenBudgetWarningThreshold', '^0\.[0-9]{1,2}$'),
    ('execution', 'maxParallelGoals', '^([1-9]|1[0-6])$'),
    ('execution', 'dagSchedulerStrategy', '^(TOPOLOGICAL|PRIORITY|SHORTEST_FIRST)$'),
    ('execution', 'enableRollback', '^(true|false)$'),
    ('execution', 'logRetentionDays', '^[1-9][0-9]{0,3}$'),
    ('execution', 'compactThresholdPct', '^([1-9]|[1-9][0-9])$'),
    ('execution', 'haltThresholdPct', '^([2-9]|[1-9][0-9]|100)$'),
    ('execution', 'autoResume', '^(true|false)$'),
    ('execution', 'maxAutoResumes', '^([1-9]|[1-9][0-9]|100)$'),
    ('monitor', 'refreshIntervalMs', '^(1[0-9]{4}|[2-5][0-9]{4}|60000)$'),
    ('monitor', 'alertConsecutiveFailures', '^([2-9]|1[0-9]|20)$'),
    ('monitor', 'alertAgentTimeoutSec', '^[0-9]{2,5}$'),
    ('monitor', 'alertTaskDurationMultiplier', '^([1-9]|1[0-9]|20)(\.[0-9]+)?$'),
    ('monitor', 'enableEmailNotification', '^(true|false)$'),
    ('monitor', 'notificationEmail', '^$|^[^@\s]+@[^@\s]+\.[^@\s]+$'),
    ('autoclaude', 'engineUrl', '^https?://[A-Za-z0-9.\-]+(:[0-9]{1,5})?/?$'),
    ('autoclaude', 'healthCheckPath', '^/[A-Za-z0-9_\-./]*$'),
    ('autoclaude', 'eventBusType', '^(INTERNAL|KAFKA|RABBITMQ)$'),
    ('autoclaude', 'dalBackend', '^(FILE|IN_MEMORY|POSTGRESQL)$'),
    ('autoclaude', 'playbookPath', '^.{1,500}$'),
    ('autoclaude', 'claudeCommand', '^[A-Za-z0-9_.\-/\\:]{1,200}$'),
    ('autoclaude', 'claudeExtraArgs', '^[A-Za-z0-9_.=:,/@\- ]{0,500}$'),
    ('autoclaude', 'claudeContinueFlag', '^--[A-Za-z0-9\-]{1,60}$'),
    ('autoclaude', 'claudeEncoding', '^[A-Za-z0-9_\-]{1,30}$'),
    ('autoclaude', 'dbDsn', '^.{0,512}$'),
    ('autoclaude', 'dualReadResolution', '^(yaml_wins|db_wins|fail_loud)$'),
    ('sdd', 'engineUrl', '^https?://[A-Za-z0-9.\-]+(:[0-9]{1,5})?/?$'),
    ('sdd', 'specFormat', '^(YAML|JSON|TOML)$'),
    ('sdd', 'workflowEngine', '^(STATIC|DYNAMIC|ADAPTIVE)$'),
    ('sdd', 'validationLevel', '^(LAX|NORMAL|STRICT)$')
) AS v(category, key, rule)
WHERE c.category = v.category AND c.key = v.key;

-- ── ② impact_note（US-S-08；附錄 C 有影響提示者一併寫入，任務書點名的 8 個關鍵鍵為最低要求）────────
UPDATE console.system_configs AS c SET impact_note = v.note
FROM (VALUES
    ('model', 'provider', '僅為 Console 抽象層欄位；引擎是 MiniMax＋Claude CLI 雙腦，不會依此切換'),
    ('model', 'apiUrl', '須填完整的 chat-completions 端點 URL（後端不補路徑）；原樣當引擎 minimax.base_url，也用於匯入解析（路徑 B）與測試連線；host 須同時在 Console 與 Bridge 的 allowlist 內；新批次起生效'),
    ('model', 'apiKey', '加密儲存；新批次起使用新金鑰；留空＝不再帶 MiniMax 設定（引擎不建 Brain，AI 演化提案停用）'),
    ('model', 'name', '新批次起生效；也用於匯入解析'),
    ('model', 'maxTokensPerRequest', '只影響匯入解析（路徑 B）的 max_tokens；引擎無對應欄位'),
    ('model', 'temperature', '只影響匯入解析（路徑 B）'),
    ('model', 'topP', '只影響匯入解析（路徑 B）'),
    ('model', 'timeout', '引擎 minimax.timeout_seconds 與匯入解析逾時；測試連線上限 10 秒；經 nginx 部署時建議 ≤ 150（nginx 對匯入的讀取逾時為 180 秒）'),
    ('model', 'rateLimitPerMinute', '目前不影響任何呼叫'),
    ('model', 'enableKernelBrain', '開啟後引擎的 Brain 可改寫失敗步驟並可能觸發升級；新批次起生效'),
    ('agent', 'defaultAutonomyLevel', '只改之後匯入與執行表單的預設值，不改動既有專案'),
    ('agent', 'maxConcurrentTasks', '引擎序列執行，目前不生效（Architecture L-1）'),
    ('agent', 'taskTimeout', '新批次的單步逾時（秒）；同時是「任務執行過長」告警門檻的基準（×monitor.alertTaskDurationMultiplier）'),
    ('agent', 'maxRetries', '新批次的預設最大重試次數（每個任務自己的 maxRetries 優先）'),
    ('agent', 'retryBackoffMs', '引擎無對應欄位'),
    ('agent', 'retryBackoffMultiplier', '引擎無對應欄位'),
    ('agent', 'checkpointInterval', 'Bridge 於每個步驟邊界自行記錄歷史快照，此值不生效'),
    ('agent', 'enableAutoMutation', '引擎沒有對應的設定鍵，Console 不送任何引擎設定（行為同 Level 5；Level 6+ 的語意待引擎支援）'),
    ('agent', 'enableSelfEvolution', '同上（Level 7+）；引擎的 AI 演化提案只由 MINIMAX_API_KEY 的有無決定，與本鍵無關（E2E 以 model.apiKey 為空關閉演化）'),
    ('execution', 'globalTokenBudget', '新批次的預設 Token 預算；不改動既有批次'),
    ('execution', 'tokenBudgetWarningThreshold', '即時生效於進行中的批次（告警每次評估時讀取）'),
    ('execution', 'maxParallelGoals', '引擎序列執行，目前不生效'),
    ('execution', 'dagSchedulerStrategy', '影響新批次同層目標的排序'),
    ('execution', 'enableRollback', '引擎無對應欄位'),
    ('execution', 'logRetentionDays', '日誌與 Bridge 工作區的保留天數（清理排程依此）'),
    ('execution', 'compactThresholdPct', 'Token Guard：context 達此百分比觸發 /compact；新批次起生效；不得經 Console 提高上限以繞過安全收斂（NFR-SEC-05）'),
    ('execution', 'haltThresholdPct', 'Token Guard：context 達此百分比儲存 checkpoint 並停機；新批次起生效'),
    ('execution', 'autoResume', 'halt 後引擎是否等待並自動續跑（會讓 run 長時間維持 RUNNING）；新批次起生效'),
    ('execution', 'maxAutoResumes', '單次 playbook 最多自動恢復次數；新批次起生效'),
    ('monitor', 'refreshIntervalMs', '前端輪詢間隔（通知摘要、監控儀表板）；下限 10 秒：同一使用者的所有頁面共用每分鐘 100 次的限流額度'),
    ('monitor', 'alertConsecutiveFailures', '「連續任務失敗」告警門檻；即時生效'),
    ('monitor', 'alertAgentTimeoutSec', '「Agent 無回應」告警門檻（秒）；即時生效'),
    ('monitor', 'alertTaskDurationMultiplier', '「執行時間過長」＝agent.taskTimeout × 此倍數；即時生效'),
    ('monitor', 'enableEmailNotification', '目前沒有郵件發送功能，只儲存'),
    ('monitor', 'notificationEmail', '目前沒有郵件發送功能，只儲存'),
    ('autoclaude', 'engineUrl', '所有 Bridge 呼叫改走新位址；填錯會讓執行與監控失效'),
    ('autoclaude', 'healthCheckPath', 'Bridge 健康探測路徑（Agent 可用率、頂列連線燈）'),
    ('autoclaude', 'eventBusType', '引擎只有 INTERNAL'),
    ('autoclaude', 'dalBackend', 'Bridge 固定用檔案型 checkpoint（yaml_only），此值不生效（ADR-001 D13）'),
    ('autoclaude', 'playbookPath', 'Bridge 自行管理 playbook 檔，不生效'),
    ('autoclaude', 'claudeCommand', '新批次起生效；E2E 設為 mock claude 的絕對路徑（Windows：<REPO_ROOT>\.venv\Scripts\aisdlc-mock-claude.exe），不依賴 Bridge 行程的 PATH；填錯會讓每個步驟在第一秒失敗'),
    ('autoclaude', 'claudeExtraArgs', '新批次起生效'),
    ('autoclaude', 'claudeContinueFlag', '新批次起生效'),
    ('autoclaude', 'claudeEncoding', '新批次起生效'),
    ('autoclaude', 'dbDsn', 'Bridge 固定 yaml_only，不生效'),
    ('autoclaude', 'dualReadResolution', 'Bridge 固定 yaml_only，不生效'),
    ('sdd', 'engineUrl', '匯入路徑 A 的 /sdd/compile 位址'),
    ('sdd', 'specFormat', '與 /sdd/compile 行為的對映尚未驗證'),
    ('sdd', 'workflowEngine', '與 /sdd/compile 行為的對映尚未驗證'),
    ('sdd', 'validationLevel', '與 /sdd/compile 行為的對映尚未驗證')
) AS v(category, key, note)
WHERE c.category = v.category AND c.key = v.key;

-- ── ⑤ 預設值校正 ────────────────────────────────────────────────────────────
-- model.apiUrl 改為「完整的 chat-completions 端點」（AR-09）：預設取引擎自己的預設（AutoClaude/autoclaude/utils/config.py
-- 的 MinimaxConfig.base_url），否則種子預設（Anthropic 網域）一設金鑰就會被 Bridge 以 outbound_not_allowed 拒絕。
UPDATE console.system_configs SET value = 'https://api.minimax.io/v1/text/chatcompletion_v2'
 WHERE category = 'model' AND key = 'apiUrl' AND value = 'https://api.anthropic.com';
UPDATE console.system_configs SET default_value = 'https://api.minimax.io/v1/text/chatcompletion_v2'
 WHERE category = 'model' AND key = 'apiUrl' AND default_value = 'https://api.anthropic.com';
UPDATE console.system_configs SET description = '模型 API 完整端點 URL（chat-completions；後端不補路徑；與引擎 minimax.base_url 同義，受 SEC-04 domain allowlist 校驗，非自由 URL）'
 WHERE category = 'model' AND key = 'apiUrl';

-- model.name：舊預設 claude-sonnet-4-20250514 → MiniMax-M2.7（引擎 MinimaxConfig.model；與上面成對）
UPDATE console.system_configs SET value = 'MiniMax-M2.7'
 WHERE category = 'model' AND key = 'name' AND value = 'claude-sonnet-4-20250514';
UPDATE console.system_configs SET default_value = 'MiniMax-M2.7'
 WHERE category = 'model' AND key = 'name' AND default_value = 'claude-sonnet-4-20250514';

-- monitor.refreshIntervalMs：舊預設 3000 → 10000（輪詢地板 10 秒；同一使用者所有頁面共用每分鐘 100 次限流，AR-06）
UPDATE console.system_configs SET value = '10000'
 WHERE category = 'monitor' AND key = 'refreshIntervalMs' AND value = '3000';
UPDATE console.system_configs SET default_value = '10000'
 WHERE category = 'monitor' AND key = 'refreshIntervalMs' AND default_value = '3000';
