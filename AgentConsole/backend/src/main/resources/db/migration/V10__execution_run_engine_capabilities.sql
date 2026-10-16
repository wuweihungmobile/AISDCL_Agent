-- ============================================================================
-- V10__execution_run_engine_capabilities.sql — W7-BE（契約 §0.5 V10；D-11；§3.4.2）
-- ① execution_runs.engine_capabilities：該批次 spawn 時 Console 送進引擎的能力狀態
--    {"autoMutation":"ENABLED","selfEvolution":"ENABLED"}（值域 ENABLED／OFF／UNAVAILABLE_NO_API_KEY）
--    • 建立批次時與 execution_runs 同一次 INSERT 寫入：值就是 ConfigMaterializer.materialize(autonomyLevel) 回傳的
--      engineCapabilities，與送給 Bridge 的設定來自同一次呼叫（契約 §3.4.2 一致性規則）；之後不再更新
--    • Bridge 不寫；resume／restore 不重算（引擎設定檔 config.yaml 在 spawn 時就凍結）
--    • NULL＝V10 之前建立的批次：當時送了什麼已不可考，不回填、不猜測
-- ② system_configs.impact_note：model.enableKernelBrain、agent.enableAutoMutation、agent.enableSelfEvolution 三個鍵的語意在
--    v1.3 改變，文字取契約附錄 C.1／C.2 逐字（以 (category, key) 對位，不比對舊文字）；其餘鍵不動
-- ============================================================================
ALTER TABLE console.execution_runs ADD COLUMN engine_capabilities JSONB;

UPDATE console.system_configs AS c SET impact_note = v.note
FROM (VALUES
    ('model', 'enableKernelBrain', '有金鑰時，引擎的 Brain 會在步驟失敗且尚有重試次數時先改寫 prompt 再重試；Brain 呼叫失敗則該步驟直接升級。與 agent.enableAutoMutation 及自治等級 ≥6 共用引擎鍵 minimax.enable_kernel_brain（任一為真即開）；沒有金鑰時 Console 不送（送了引擎會啟動失敗）；新批次起生效'),
    ('agent', 'enableAutoMutation', '對映引擎 minimax.enable_kernel_brain（Brain 逐步校正：失敗步驟先改寫 prompt 再重試），與 model.enableKernelBrain 任一為真即開；自治等級 ≥6 一律視為開啟。需要 model.apiKey：沒有金鑰時不送，批次回報 UNAVAILABLE_NO_API_KEY；新批次起生效（§3.4.2）'),
    ('agent', 'enableSelfEvolution', '引擎沒有演化開關：有金鑰時失敗型 ESCALATION 一律由 Brain 產生演化提案，只寫引擎日誌、不套用也不重載（max_evolutions／require_evolution_signoff 在引擎執行路徑上沒有讀者，Console 不送）。本鍵只影響沒有金鑰時批次回報 OFF 或 UNAVAILABLE_NO_API_KEY（§3.4.2；E2E 以 model.apiKey 為空關閉演化，§5.0.2）')
) AS v(category, key, note)
WHERE c.category = v.category AND c.key = v.key;
