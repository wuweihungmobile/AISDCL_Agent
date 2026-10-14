-- ============================================================================
-- V2__seed_system_configs.sql — 系統參數預設值種子（ADR-001 D5.2）
-- 來源：PRD §5.5.1.1～§5.5.1.6 六類參數（model／agent／execution／monitor／autoclaude／sdd）。
-- 約定：
--   * category＝PRD 參數名「點」前的分類，key＝點之後的鍵名（例：model.apiKey → ('model','apiKey')）。
--   * 敏感參數（model.apiKey）value_type='ENCRYPTED'、is_encrypted=TRUE、value 為空字串（NOT NULL）。
--   * 🔴 autoclaude.dalBackend 預設 FILE，偏離 PRD §5.5.1.5 的 POSTGRESQL：Engine Bridge 的
--     pause／restore 依賴檔案型 checkpoint（ADR-001 D13）。
--   * validation_rule 本波不填（NULL）；由 Phase 6 的設定 API 與其測試一併定案。
--   * updated_by 為 NULL＝「由種子寫入、尚未被任何使用者修改」。
-- ============================================================================
INSERT INTO system_configs (category, key, value, value_type, default_value, description, is_encrypted) VALUES
-- 5.5.1.1 AI 模型設定 (Model Configuration)
('model', 'provider', 'ANTHROPIC', 'ENUM', 'ANTHROPIC', '模型提供者 (ANTHROPIC / OPENAI / LOCAL / CUSTOM)', FALSE),
('model', 'apiUrl', 'https://api.anthropic.com', 'STRING', 'https://api.anthropic.com', '模型 API 基礎 URL（與 MINIMAX_BASE_URL 同受 SEC-04 domain allowlist 校驗，非自由 URL）', FALSE),
('model', 'apiKey', '', 'ENCRYPTED', '', 'API Key（加密儲存）', TRUE),
('model', 'name', 'claude-sonnet-4-20250514', 'STRING', 'claude-sonnet-4-20250514', '預設模型名稱', FALSE),
('model', 'maxTokensPerRequest', '8192', 'INTEGER', '8192', '單次請求最大 Token 數', FALSE),
('model', 'temperature', '0.3', 'FLOAT', '0.3', '溫度參數', FALSE),
('model', 'topP', '0.9', 'FLOAT', '0.9', 'Top-P 參數', FALSE),
('model', 'timeout', '120', 'INTEGER', '120', '請求逾時秒數', FALSE),
('model', 'rateLimitPerMinute', '60', 'INTEGER', '60', '每分鐘最大請求數', FALSE),
-- 5.5.1.2 Agent 行為設定 (Agent Behavior)
('agent', 'defaultAutonomyLevel', '3', 'INTEGER', '3', '預設自治等級 (1-10)', FALSE),
('agent', 'maxConcurrentTasks', '3', 'INTEGER', '3', '最大並行任務數', FALSE),
('agent', 'taskTimeout', '600', 'INTEGER', '600', '單一任務逾時秒數', FALSE),
('agent', 'maxRetries', '3', 'INTEGER', '3', '預設最大重試次數', FALSE),
('agent', 'retryBackoffMs', '5000', 'INTEGER', '5000', '重試退避毫秒數', FALSE),
('agent', 'retryBackoffMultiplier', '2.0', 'FLOAT', '2.0', '重試退避倍數', FALSE),
('agent', 'checkpointInterval', '5', 'INTEGER', '5', '自動 Checkpoint 間隔（每 N 個任務）', FALSE),
('agent', 'enableAutoMutation', 'false', 'BOOLEAN', 'false', '啟用自動突變（Level 6+）', FALSE),
('agent', 'enableSelfEvolution', 'false', 'BOOLEAN', 'false', '啟用自演化（Level 7+）', FALSE),
-- 5.5.1.3 執行引擎設定 (Execution Engine)
('execution', 'globalTokenBudget', '1000000', 'LONG', '1000000', '全域 Token 預算', FALSE),
('execution', 'tokenBudgetWarningThreshold', '0.8', 'FLOAT', '0.8', 'Token 預算警告閾值 (80%)', FALSE),
('execution', 'maxParallelGoals', '2', 'INTEGER', '2', '最大並行目標數', FALSE),
('execution', 'dagSchedulerStrategy', 'TOPOLOGICAL', 'ENUM', 'TOPOLOGICAL', '排程策略 (TOPOLOGICAL / PRIORITY / SHORTEST_FIRST)', FALSE),
('execution', 'enableRollback', 'true', 'BOOLEAN', 'true', '啟用失敗回滾', FALSE),
('execution', 'logRetentionDays', '90', 'INTEGER', '90', '日誌保留天數', FALSE),
('execution', 'compactThresholdPct', '80', 'INTEGER', '80', 'Token Guard：達此百分比觸發 /compact（對映引擎 compact_threshold_pct）', FALSE),
('execution', 'haltThresholdPct', '90', 'INTEGER', '90', 'Token Guard：達此百分比 checkpoint 收斂（對映 halt_threshold_pct；硬約束 halt > compact，見 NFR-SEC-05）', FALSE),
-- 5.5.1.4 監控告警設定 (Monitoring & Alerting)
('monitor', 'refreshIntervalMs', '3000', 'INTEGER', '3000', '監控儀表板刷新間隔（毫秒）', FALSE),
('monitor', 'alertConsecutiveFailures', '3', 'INTEGER', '3', '連續失敗告警閾值', FALSE),
('monitor', 'alertAgentTimeoutSec', '300', 'INTEGER', '300', 'Agent 無回應告警閾值（秒）', FALSE),
('monitor', 'alertTaskDurationMultiplier', '2.0', 'FLOAT', '2.0', '任務執行過長告警倍數', FALSE),
('monitor', 'enableEmailNotification', 'false', 'BOOLEAN', 'false', '啟用 Email 通知', FALSE),
('monitor', 'notificationEmail', '', 'STRING', '', '通知 Email 地址', FALSE),
-- 5.5.1.5 AutoClaude 橋接設定 (AutoClaude Bridge)
('autoclaude', 'engineUrl', 'http://engine-bridge:8081', 'STRING', 'http://engine-bridge:8081', '單一 Engine Bridge 服務 URL（AutoClaude 路徑前綴 /autoclaude）', FALSE),
('autoclaude', 'healthCheckPath', '/health', 'STRING', '/health', '健康檢查端點', FALSE),
('autoclaude', 'eventBusType', 'INTERNAL', 'ENUM', 'INTERNAL', 'EventBus 類型 (INTERNAL / KAFKA / RABBITMQ)', FALSE),
('autoclaude', 'dalBackend', 'FILE', 'ENUM', 'FILE', 'DAL 後端 (FILE / IN_MEMORY / POSTGRESQL)；預設 FILE：pause／restore 依賴檔案型 checkpoint（ADR-001 D13，偏離 PRD §5.5.1.5 預設 POSTGRESQL）', FALSE),
('autoclaude', 'playbookPath', './playbooks', 'STRING', './playbooks', 'Playbook 儲存路徑', FALSE),
-- 5.5.1.6 AISDLC_SDD 橋接設定 (AISDLC_SDD Bridge)
('sdd', 'engineUrl', 'http://engine-bridge:8081', 'STRING', 'http://engine-bridge:8081', '單一 Engine Bridge 服務 URL（AISDLC_SDD 路徑前綴 /sdd）', FALSE),
('sdd', 'specFormat', 'YAML', 'ENUM', 'YAML', '規格格式 (YAML / JSON / TOML)', FALSE),
('sdd', 'workflowEngine', 'DYNAMIC', 'ENUM', 'DYNAMIC', '工作流引擎 (STATIC / DYNAMIC / ADAPTIVE)', FALSE),
('sdd', 'validationLevel', 'STRICT', 'ENUM', 'STRICT', '驗證等級 (LAX / NORMAL / STRICT)', FALSE);
