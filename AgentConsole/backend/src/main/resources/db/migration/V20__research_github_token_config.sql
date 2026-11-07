-- V20__research_github_token_config.sql — 研究分流的 GitHub token 設定鍵（D-98、D-132）
-- 只種一列：category=research、key=github_token；敏感參數（value_type='ENCRYPTED'、is_encrypted=TRUE、value 為空字串，沿 V2 的 model.apiKey 體例）。
-- 由 ADMIN 經設定頁寫入；console-api 只在分流確認（軌道 B 且 createGithub=true）時讀取，放進該次 Bridge 請求本文，不入任何回應、日誌與稽核。
-- 不改 V1～V19；沒有新表、沒有新欄位。
INSERT INTO console.system_configs (category, key, value, value_type, default_value, description, is_encrypted, validation_rule, impact_note) VALUES
('research', 'github_token', '', 'ENCRYPTED', '', 'GitHub token（加密儲存；研究分流軌道 B 建立遠端庫時使用）', TRUE, '^.{0,255}$',
 '加密儲存；只在研究分流確認（軌道 B 且 createGithub=true）時由 console-api 放進該次 Bridge 請求，Bridge 只經子行程環境 GH_TOKEN 傳給 gh；留空＝不帶 token，由 Bridge 的建庫步驟失敗並說明');
