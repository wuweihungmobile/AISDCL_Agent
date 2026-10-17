-- ============================================================================
-- V12__project_sdd_binding.sql — 整合輪 115（契約 §0.5 V12；G-07、D-115-14；ADR-XPLAT-016 §7.2）
-- Console 專案為錨的 SDD 綁定：projects 增三個欄位（皆可 NULL）與一個部分唯一索引。
-- ① sdd_project：FSM 專案鍵。NULL＝「用預設」（專案名）；第一次使用時（核准凍結、路徑 A 的 confirm）寫回 Bridge 回的標準鍵，
--    或由 PUT /projects/{id}/sdd-binding 編輯。
-- ② sdd_spec_dir：規格檔所在目錄（絕對路徑）＝編譯回應 spec_path 的父目錄；與 execution_path 同長度上限。
-- ③ sdd_spec_file：規格檔（絕對路徑）＝編譯回應的 spec_path；NULL＝尚未用路徑 A 匯入規格。
-- 既有專案升級後三欄皆為 NULL：不回填、不猜測。
-- ④ 一個 FSM 專案只對應一個「未軟刪除」的 Console 專案：(execution_path, sdd_project) 在 sdd_project 非空且 is_deleted IS NOT TRUE
--    的列中唯一（is_deleted 是可為 NULL 的布林，所以用 IS NOT TRUE）。Backend 一律「先檢查、後寫入」，這個索引是最後的兜底。
-- 沒有新表、沒有種子；ddl-auto=validate 由 ProjectEntity 的三個新欄位對齊。
-- ============================================================================
ALTER TABLE console.projects
    ADD COLUMN sdd_project   VARCHAR(100),
    ADD COLUMN sdd_spec_dir  VARCHAR(500),
    ADD COLUMN sdd_spec_file VARCHAR(500);

CREATE UNIQUE INDEX ux_projects_sdd_binding
    ON console.projects (execution_path, sdd_project)
    WHERE sdd_project IS NOT NULL AND is_deleted IS NOT TRUE;
