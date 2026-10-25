-- ============================================================================
-- V13__si_console_writes.sql — SelfImproving P2b：Console 自己的稽核列（TCS-SelfImprovingDecide-P2b W11、W13；PRD §9.3）
-- Console 不直接寫 SelfImproving 帳本：每次決定、新增觀察、關閉觀察都由 backend 簽一份稽核 JSON、經 Bridge 落檔，再由主機端根層
-- CLI 驗簽入帳。本表是 Console 這一側的同型稽核列（與帳本互相對帳：有列而帳本沒有＝待入帳；帳本有而本表沒有＝紅色警示）。
-- ① 寫入順序：簽章 → INSERT 本表 → 呼叫 Bridge（寧可有列無檔、不要有檔無列）；Bridge 明確拒絕或確定未送達時補償 DELETE，
--    結果不明（讀取逾時、送出後連線重設、2xx 本文無法解析）時保留列。
-- ② 列不可改：BEFORE UPDATE 觸發器拒絕任何欄位變動；唯一例外是 subject_id 由 NULL 填值（obs-add 的新列號要入帳後才知道，
--    對帳讀面回填；PRD 只要求不可改，本表以此例外類推）。DELETE 允許（補償路徑）。
-- ③ body 是簽章的對象（逐字）；mac 是 HMAC-SHA256 小寫十六進位；金鑰本身永遠不入庫，只有 key_id（金鑰 sha256 前 8 碼）。
--    key_id 與 mac 另以正規表示式約束長度與字元：CHAR(n) 會把較短的值補空白而不報錯，光靠欄位型別擋不住「長度不符」。
-- 沒有 JPA 實體（ddl-auto=validate 不檢查本表）：以 JDBC 配接器存取。
-- ============================================================================
CREATE TABLE console.si_console_writes (
    audit_ref  UUID PRIMARY KEY,
    kind       VARCHAR(12) NOT NULL CHECK (kind IN ('decide', 'obs-add', 'obs-close')),
    "user"     VARCHAR(64) NOT NULL,
    role       VARCHAR(20) NOT NULL,
    "time"     TIMESTAMP WITH TIME ZONE NOT NULL,
    subject_id VARCHAR(64),
    digest     VARCHAR(71),
    body       TEXT NOT NULL,
    key_id     CHAR(8) NOT NULL CHECK (key_id ~ '^[0-9a-f]{8}$'),
    mac        CHAR(64) NOT NULL CHECK (mac ~ '^[0-9a-f]{64}$')
);

CREATE INDEX idx_si_console_writes_time ON console.si_console_writes ("time");

CREATE FUNCTION console.si_console_writes_guard() RETURNS trigger
    LANGUAGE plpgsql AS
$$
BEGIN
    IF NEW.audit_ref IS DISTINCT FROM OLD.audit_ref
        OR NEW.kind IS DISTINCT FROM OLD.kind
        OR NEW."user" IS DISTINCT FROM OLD."user"
        OR NEW.role IS DISTINCT FROM OLD.role
        OR NEW."time" IS DISTINCT FROM OLD."time"
        OR NEW.digest IS DISTINCT FROM OLD.digest
        OR NEW.body IS DISTINCT FROM OLD.body
        OR NEW.key_id IS DISTINCT FROM OLD.key_id
        OR NEW.mac IS DISTINCT FROM OLD.mac
        OR (OLD.subject_id IS NOT NULL AND NEW.subject_id IS DISTINCT FROM OLD.subject_id) THEN
        RAISE EXCEPTION 'console.si_console_writes 的列不可改（只有 subject_id 可由 NULL 填值）'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_si_console_writes_guard
    BEFORE UPDATE ON console.si_console_writes
    FOR EACH ROW EXECUTE FUNCTION console.si_console_writes_guard();
