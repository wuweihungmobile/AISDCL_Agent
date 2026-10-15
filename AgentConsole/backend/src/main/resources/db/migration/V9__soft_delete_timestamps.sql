-- ============================================================================
-- V9__soft_delete_timestamps.sql — W5-BE（契約 §0.5 V9；C-3；NFR-9.3-04）
-- 軟刪除時間：保留期與復原都需要知道「何時刪的」與「同一次刪除連帶軟刪了哪些」。
--   projects.deleted_at / goals.deleted_at / tasks.deleted_at  軟刪除當下的時間；刪除專案時，專案與它當時仍未刪除的目標、任務
--       在同一交易內寫入同一個值——復原靠「目標／任務的 deleted_at 等於專案的」辨識「同一次刪除連帶軟刪」的列
--   projects.status_before_delete  軟刪除前的專案狀態（軟刪除會把 status 改成 ARCHIVED；復原時還原）
-- 既有的 is_deleted 不動（索引、查詢與 JPA 實體都以它為準）。
-- ============================================================================
ALTER TABLE console.projects ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE,
                             ADD COLUMN status_before_delete VARCHAR(20);
ALTER TABLE console.goals    ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE console.tasks    ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;

-- 升級前已軟刪的列：真正的刪除時間已不可考，以 updated_at 近似（軟刪除當下會更新它；專案刪除連帶軟刪的目標與任務
-- 與專案共用同一個 now，所以三者的近似值仍相等）；status_before_delete 留 NULL（復原時以 signedOff 推：未簽 DRAFT、已簽 READY）
UPDATE console.projects SET deleted_at = updated_at WHERE is_deleted = TRUE AND deleted_at IS NULL;
UPDATE console.goals    SET deleted_at = updated_at WHERE is_deleted = TRUE AND deleted_at IS NULL;
UPDATE console.tasks    SET deleted_at = updated_at WHERE is_deleted = TRUE AND deleted_at IS NULL;

-- 「已刪除」清單與清除排程只看軟刪除的專案：partial index 只收這一小撮
CREATE INDEX idx_projects_deleted_at ON console.projects(deleted_at) WHERE is_deleted = TRUE;
