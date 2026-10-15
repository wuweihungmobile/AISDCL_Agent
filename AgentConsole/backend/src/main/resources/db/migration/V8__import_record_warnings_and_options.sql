-- ============================================================================
-- V8__import_record_warnings_and_options.sql — W5-BE（契約 §0.5 V8；C-10；QA F1-1／F1-2）
-- 匯入記錄補兩欄：重開記錄（歷史列表、重新整理）時還原黃色解析提示與解析選項。
--   warnings      最近一次成功的 parse／PUT result 的 ParseWarning[]；既有記錄升級後為 []
--   parse_options 最近一次 parse 請求的 ParseOptions（進入 PARSING 時寫入，不論該次成敗）；從未 parse 過為 NULL
-- ============================================================================
ALTER TABLE console.import_records
    ADD COLUMN warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN parse_options JSONB;
