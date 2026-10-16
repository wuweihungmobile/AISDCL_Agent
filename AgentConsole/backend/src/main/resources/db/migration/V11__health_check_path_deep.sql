-- ============================================================================
-- V11__health_check_path_deep.sql — W7-BE（契約 §0.5 V11；D-17；§3.1）
-- console-api 的 Bridge 探測環改打深度探針 /health/deep（git、autoclaude 匯入、工作區可寫、DB；淺層 /health 在引擎壞了時照回 200）：
-- ① 預設值 /health → /health/deep：只在值仍等於舊預設 /health 時才改（不覆蓋管理員改過的值；寫法同 V5 的 ⑤）；
--    value 與 default_value 各自判斷。沒有新欄位、沒有新表，ddl-auto=validate 不受影響。
--    取捨（與 V5 ⑤ 相同）：管理員「刻意」把值設成 /health 的既有部署也會被改成 /health/deep——資料庫分不出刻意與沒動過；
--    要保留淺探測，升級後把值改回 /health（附錄 C.5 的驗證規則允許）。
-- ② impact_note：文字取契約附錄 C.5 healthCheckPath 的 impactNote 逐字（以 (category, key) 對位，不比對舊文字）。
-- ============================================================================
UPDATE console.system_configs SET value = '/health/deep'
 WHERE category = 'autoclaude' AND key = 'healthCheckPath' AND value = '/health';
UPDATE console.system_configs SET default_value = '/health/deep'
 WHERE category = 'autoclaude' AND key = 'healthCheckPath' AND default_value = '/health';
UPDATE console.system_configs SET impact_note = 'Bridge 健康探測路徑（Agent 可用率、頂列連線燈）；預設 /health/deep：Bridge 行程可達但引擎自檢未通過（503）也算失敗，改回 /health 只檢查行程是否存活'
 WHERE category = 'autoclaude' AND key = 'healthCheckPath';
