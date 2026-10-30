# ADR-SIDB-003：完整性：追加專用、鏈與重放（PRD 簡稱 SIDB-03）

## 狀態

Accepted（2026-10-31；決定者＝主控依 `docs/01_requirements/SelfImproving_Ledger_DB_PRD.md` §9.5 SIDB-03 轉正式，錨點＝快照內鏈頭取自掌舵者 2026-10-27 對 OQ-1 的裁決〔PRD §13.2「全部採建議值」〕）。本 ADR 是 P0 的規格決定與 SQL 草稿；草稿於 P0 以一次性 PG18 容器烟測過（見〈連動面〉），**不是**可直接進 `si/sql/V001__si_init.sql` 的終稿——欄位、枚舉 CHECK 與 canonical JSON 對映由 P1 的 TCS 定稿。

## 脈絡

今天的帳本是 git 內的 Markdown 與 JSONL 檔，完整性保證全部來自 git：誰、何時、改了什麼＝`git log -p`（commit 粒度），事後改寫歷史在 `git diff` 上看得見。PRD 的 P3b 把真相源換成 PG18 的 `si` schema（PRD §1、§9.2），git 這一層保證隨之消失；PRD FR-LD-05 因此要求在 DB 內補回「取代 git 的完整性保證」：

- 追加專用表（`events`、`artifacts`、`audit`、`legacy_rows`、`console_audit_files`）一律不可 UPDATE／DELETE（AC-LD-05-2）。
- 每一張資料表的每一次寫入都必須有同一交易的 audit 列，直接 psql 旁路寫入要在 COMMIT 失敗（AC-LD-05-4）。
- `si.audit` 本身是雜湊鏈：`row_hash＝sha256(prev_hash ‖ canonical(整列))`（AC-LD-05-3）；`si check` 的 `chain.intact` 全鏈重算、`state.replay` 由 audit 影像逐 `seq` 重放出現值（AC-LD-05-5）。
- 誠實劃界（PRD §6）：觸發器、延遲約束、鏈與重放抓得到**非超級權限者**的事後竄改與旁路寫入；持超級權限者或表擁有者可停用觸發器並整鏈重寫，偵測只靠外部錨點。

現況事實（可重核）：Console 側已有同型先例 `AgentConsole/backend/src/main/resources/db/migration/V13__si_console_writes.sql:28-51`（`RETURNS trigger`＋`BEFORE UPDATE`＋`ERRCODE = 'integrity_constraint_violation'`）；根 `.venv` 已有 `psycopg` 3（PRD `[C-11]`）；`sha256()` 為 PG 11 起的核心函式，PG18 容器直接可用（PRD `[C-19]`）。

## 選項與代價

- 選項 A：無（只靠 DB 權限與備份，不加觸發器、鏈、重放）。
- 代價：非擁有者的角色一旦被誤授 UPDATE，或有人用 psql 直接改列，沒有任何事後可見的痕跡；P3b 之後「誰何時改了什麼」只剩應用層自律，等於把 git 的保證白白丟掉，與 PRD 成功標準 (5) 直接衝突。
- 選項 B：追加專用觸發器＋全表延遲約束觸發器（同交易必有 audit 列）＋ `audit` 雜湊鏈＋ `si check` 重放。
- 代價：每次寫入多一筆 audit 與兩個觸發器的開銷（PRD §6 的寫入動詞單次 ≤1 s 預算內，P1 量測）；SQL 草稿與 Python canonical JSON 要雙邊對映（`row_hash` 只由 Python 定義，PG 不重算，見〈決定〉）；自舉順序要逐表列明；擁有者與超級權限者仍可繞過，只能事後偵測。
- 選項 C：選項 B 加外部錨點（把鏈頭另存於 DB 之外的位置，例如快照內鏈頭、外部時間戳服務）。
- 代價：錨點要有地方放與誰來更新；外部時間戳服務是新相依與新機密面；快照內鏈頭則只在快照匯出時才前進，錨點與 DB 之間有時間差（RPO），超級權限者在兩次快照之間的竄改仍可能整鏈重寫而不被發現，只是之後的快照比對會暴露。

## 決定

採用**選項 B 為底線，錨點＝快照內鏈頭**（OQ-1 裁決：快照放固定單一目錄覆寫並帶鏈頭，見 ADR-SIDB-008），即 B 加上不需新相依的那一種錨點；不採外部時間戳服務。理由：

1. 選項 A 與成功標準 (5) 衝突，否決。
2. 選項 B 的代價是可估、可量測的工程成本；它抓得到本 repo 實際會發生的失誤類型（誤授權、旁路 psql、應用層 bug 繞過 audit），這與今天 git 擋得住的失誤類型一致。
3. 選項 C 的外部服務在「單一主力機、離線可用」的前提（OQ-2 裁決）下沒有穩定的持有者；快照內鏈頭已足以讓「超級權限者整鏈重寫」在下一次快照比對時現形，且快照入 git 的邊際成本實測可忽略（PRD `[C-18]`）。**只有出現超級權限竄改的暴露證據時才升級**（見〈再開症狀〉）。

**`audit_chain_guard` 的職責邊界**：它是 `si.audit` 上的 BEFORE INSERT 觸發器，在 advisory lock 內只驗三件事——`seq` 連續（上一筆 `seq`＋1）、`prev_hash` 等於上一筆的 `row_hash`（首筆為 64 個 `0`）、`txid` 等於 `txid_current()`；**不重算 `row_hash`**。理由：`row_hash` 的輸入是 canonical JSON（鍵序、數字與時間的表示），那套規則只由 Python 一處定義；在 PG 內再實作一份就是兩份判準（本 repo 反覆在治的複本型缺陷，見 ADR-SIDB-004 的同型理由）。全鏈重算由 `si check` 的 `chain.intact` 在 Python 側做。

**after_sha 的兩種來源**：可變表存改前改後完整列影像，`after_sha` 必須等於該列自己的 `row_sha256`（Python 以 canonical JSON 算好寫入）；追加專用表不存影像，`after_sha` 是 PG 核心 `sha256()` 對 `to_jsonb(NEW)::text` 的重算值，由 `si.jsonb_sha256()` 單一函式提供，Python 端一律呼叫該函式取值（不自行重現 jsonb 文字化規則；jsonb 內的時間字串受 session `TimeZone` 影響，P1 的 DAL 連線一律設 UTC）。

**角色與權限**：`si_owner` 擁有 schema、表與觸發器（遷移與 `db flip` 專用，平時不連線）；`si_writer` 非擁有者，因此不能 `ALTER TABLE … DISABLE TRIGGER`，且只在三張可變表與三張讀模型表有 UPDATE，沒有任何表有 DELETE 或 TRUNCATE；`si_reader` 只有 SELECT。三個角色在草稿內皆為 NOLOGIN，登入屬性與憑證由運維 SOP 另行以 psql 範本給定（ADR-SIDB-007：密碼不入 SQL 檔、不入 repo）。

**自舉順序**：首次遷移先建 `audit` 與其觸發器，再建其他表與觸發器，最後才有任何受約束表的首筆寫入；`schema_migrations`、`meta`、`import_runs` 三表本身不受「同交易 audit 列」約束（遷移記錄寫入發生在 audit 可用之前，匯入批次是 audit 的上游），由權限與下表的守衛保護。

### SQL 草稿（沿 V13 的形態；以下三個區塊依序餵 `psql -v ON_ERROR_STOP=1`）

```sql
-- 區塊一：角色、schema 與共用函式（以超級使用者執行；角色為叢集級物件，NOLOGIN）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'si_owner') THEN CREATE ROLE si_owner NOLOGIN; END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'si_writer') THEN CREATE ROLE si_writer NOLOGIN; END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'si_reader') THEN CREATE ROLE si_reader NOLOGIN; END IF;
END
$$;

CREATE SCHEMA si AUTHORIZATION si_owner;
SET ROLE si_owner;

-- 追加專用表的 after_sha 來源：PG 核心 sha256() 對列影像 jsonb 文字的重算值（單一函式，Python 只呼叫它）
CREATE FUNCTION si.jsonb_sha256(j jsonb) RETURNS text
    LANGUAGE sql IMMUTABLE AS
$$ SELECT encode(sha256(convert_to(j::text, 'UTF8')), 'hex') $$;

-- 追加專用：任何 UPDATE／DELETE 一律拒絕（沿 V13 的 ERRCODE）
CREATE FUNCTION si.reject_mutation() RETURNS trigger
    LANGUAGE plpgsql AS
$$
BEGIN
    RAISE EXCEPTION 'si.% 為追加專用，不可 %', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$;

-- 全表延遲約束：COMMIT 時同交易（txid）必須有同 tbl、同 row_id 且 after_sha 相符的 audit 列
-- TG_ARGV[0]＝列主鍵欄名；TG_ARGV[1]＝'append'（after_sha＝sha256 重算值）或 'mutable'（after_sha＝列自己的 row_sha256）
CREATE FUNCTION si.require_audit() RETURNS trigger
    LANGUAGE plpgsql AS
$$
DECLARE
    img  jsonb := to_jsonb(NEW);
    rid  text  := img ->> TG_ARGV[0];
    want text;
BEGIN
    IF TG_ARGV[1] = 'append' THEN
        want := si.jsonb_sha256(img);
    ELSE
        want := img ->> 'row_sha256';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM si.audit a
                   WHERE a.txid = txid_current() AND a.tbl = TG_TABLE_NAME
                     AND a.row_id = rid AND a.after_sha = want) THEN
        RAISE EXCEPTION 'si.% 的列 % 缺同交易 audit 列（txid／after_sha 不符）', TG_TABLE_NAME, rid
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NULL;
END;
$$;

-- 鏈守衛：只驗 seq 連續、prev_hash 銜接與 txid；不重算 row_hash（canonical JSON 只由 Python 定義）
CREATE FUNCTION si.audit_chain_guard() RETURNS trigger
    LANGUAGE plpgsql AS
$$
DECLARE
    last_seq  bigint;
    last_hash text;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('si.audit'));
    SELECT seq, row_hash INTO last_seq, last_hash FROM si.audit ORDER BY seq DESC LIMIT 1;
    IF NOT FOUND THEN
        last_seq := 0;
        last_hash := repeat('0', 64);
    END IF;
    IF NEW.seq <> last_seq + 1 THEN
        RAISE EXCEPTION 'si.audit 的 seq 須連續：期望 %，收到 %', last_seq + 1, NEW.seq
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF NEW.prev_hash <> last_hash THEN
        RAISE EXCEPTION 'si.audit 的 prev_hash 與上一筆 row_hash 不銜接（seq %）', NEW.seq
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF NEW.txid <> txid_current() THEN
        RAISE EXCEPTION 'si.audit 的 txid 須等於當前交易（seq %）', NEW.seq
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;

-- 觀察列：只准處置欄由 open 轉終值一次（其餘欄位與 row_sha256 以外不可變）；DELETE 一律拒絕
CREATE FUNCTION si.observation_guard() RETURNS trigger
    LANGUAGE plpgsql AS
$$
BEGIN
    IF TG_OP = 'DELETE'
        OR OLD.disposition <> 'open'
        OR NEW.disposition = 'open'
        OR (to_jsonb(NEW) - 'disposition' - 'row_sha256' - 'raw_line')
           IS DISTINCT FROM (to_jsonb(OLD) - 'disposition' - 'row_sha256' - 'raw_line') THEN
        RAISE EXCEPTION 'si.observations 只准處置欄由 open 轉為終值一次'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
```

```sql
-- 區塊二：十四張表（audit 先於其他受約束表；列欄位為草稿，終稿由 P1 的 TCS 定稿）
CREATE TABLE si.audit (
    seq        bigint PRIMARY KEY,
    txid       bigint NOT NULL,
    at         timestamptz NOT NULL,
    actor      text NOT NULL,
    tbl        text NOT NULL,
    row_id     text NOT NULL,
    op         text NOT NULL CHECK (op IN ('insert', 'update', 'reject', 'import')),
    before     jsonb,
    after      jsonb,
    before_sha text,
    after_sha  text,
    reason     text,
    prev_hash  text NOT NULL CHECK (prev_hash ~ '^[0-9a-f]{64}$'),
    row_hash   text NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$')
);
CREATE INDEX idx_audit_txid_tbl_row ON si.audit (txid, tbl, row_id);

CREATE TABLE si.schema_migrations (
    version    integer PRIMARY KEY,
    filename   text NOT NULL,
    sha256     text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    applied_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE si.meta (
    key        text PRIMARY KEY,
    value      text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE si.import_runs (
    id         bigint PRIMARY KEY,
    started_at timestamptz NOT NULL,
    report     jsonb NOT NULL
);

CREATE TABLE si.events (
    seq        bigint PRIMARY KEY,
    t          timestamptz NOT NULL,
    kind       text NOT NULL,
    "by"       text NOT NULL,
    body       jsonb NOT NULL,
    line_bytes integer NOT NULL CHECK (line_bytes <= 4096),
    raw_line   text NOT NULL
);
CREATE TABLE si.artifacts (
    id      text PRIMARY KEY,
    prop    text NOT NULL,
    name    text NOT NULL CHECK (name ~ '^(r[0-9]+\.md|r[0-9]+\.patch|verify[0-9]+\.json)$'),
    content bytea NOT NULL,
    sha256  text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$')
);
CREATE TABLE si.legacy_rows (
    id        bigint PRIMARY KEY,
    src_file  text NOT NULL,
    src_line  integer NOT NULL,
    raw_line  text NOT NULL,
    reason    text NOT NULL
);
CREATE TABLE si.console_audit_files (
    id        text PRIMARY KEY,
    audit_ref uuid NOT NULL,
    raw       bytea NOT NULL,
    sha256    text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$')
);

CREATE TABLE si.observations (
    id          text PRIMARY KEY,
    num         integer NOT NULL,
    time_raw    text NOT NULL,
    occurred_at timestamptz,
    context     text NOT NULL,
    category    text NOT NULL,
    severity    text NOT NULL,
    disposition text NOT NULL CHECK (disposition <> ''),
    marks       jsonb NOT NULL DEFAULT '{}',
    raw_line    text NOT NULL,
    src_file    text,
    src_line    integer,
    row_sha256  text NOT NULL CHECK (row_sha256 ~ '^[0-9a-f]{64}$')
);
CREATE TABLE si.defects (
    id         text PRIMARY KEY,
    family     text NOT NULL,
    seq        integer NOT NULL,
    status_raw text NOT NULL,
    home       text NOT NULL CHECK (home = 'main' OR home ~ '^archive_[0-9]{2}$'),
    raw_line   text NOT NULL,
    row_sha256 text NOT NULL CHECK (row_sha256 ~ '^[0-9a-f]{64}$')
);
CREATE TABLE si.debt_tracks (
    id         text PRIMARY KEY,
    kind       text NOT NULL CHECK (kind IN ('external', 'structural')),
    def_id     text,
    since      text,
    raw_line   text NOT NULL,
    row_sha256 text NOT NULL CHECK (row_sha256 ~ '^[0-9a-f]{64}$')
);

CREATE TABLE si.issues (
    id      text PRIMARY KEY,
    payload jsonb NOT NULL,
    live    boolean NOT NULL DEFAULT true
);
CREATE TABLE si.export_items (
    kind    text NOT NULL,
    cursor  bigint NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY (kind, cursor)
);
CREATE TABLE si.export_meta (
    key   text PRIMARY KEY,
    value jsonb NOT NULL
);
```

```sql
-- 區塊三：觸發器與權限（仍在 SET ROLE si_owner 之下；最後 RESET ROLE）
CREATE TRIGGER trg_audit_chain BEFORE INSERT ON si.audit
    FOR EACH ROW EXECUTE FUNCTION si.audit_chain_guard();

CREATE TRIGGER trg_audit_append_only BEFORE UPDATE OR DELETE ON si.audit
    FOR EACH ROW EXECUTE FUNCTION si.reject_mutation();
CREATE TRIGGER trg_events_append_only BEFORE UPDATE OR DELETE ON si.events
    FOR EACH ROW EXECUTE FUNCTION si.reject_mutation();
CREATE TRIGGER trg_artifacts_append_only BEFORE UPDATE OR DELETE ON si.artifacts
    FOR EACH ROW EXECUTE FUNCTION si.reject_mutation();
CREATE TRIGGER trg_legacy_rows_append_only BEFORE UPDATE OR DELETE ON si.legacy_rows
    FOR EACH ROW EXECUTE FUNCTION si.reject_mutation();
CREATE TRIGGER trg_console_audit_files_append_only BEFORE UPDATE OR DELETE ON si.console_audit_files
    FOR EACH ROW EXECUTE FUNCTION si.reject_mutation();

CREATE TRIGGER trg_observations_guard BEFORE UPDATE OR DELETE ON si.observations
    FOR EACH ROW EXECUTE FUNCTION si.observation_guard();

CREATE CONSTRAINT TRIGGER trg_events_audit AFTER INSERT ON si.events
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION si.require_audit('seq', 'append');
CREATE CONSTRAINT TRIGGER trg_artifacts_audit AFTER INSERT ON si.artifacts
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION si.require_audit('id', 'append');
CREATE CONSTRAINT TRIGGER trg_legacy_rows_audit AFTER INSERT ON si.legacy_rows
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION si.require_audit('id', 'append');
CREATE CONSTRAINT TRIGGER trg_console_audit_files_audit AFTER INSERT ON si.console_audit_files
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION si.require_audit('id', 'append');
CREATE CONSTRAINT TRIGGER trg_observations_audit AFTER INSERT OR UPDATE ON si.observations
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION si.require_audit('id', 'mutable');
CREATE CONSTRAINT TRIGGER trg_defects_audit AFTER INSERT OR UPDATE ON si.defects
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION si.require_audit('id', 'mutable');
CREATE CONSTRAINT TRIGGER trg_debt_tracks_audit AFTER INSERT OR UPDATE ON si.debt_tracks
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION si.require_audit('id', 'mutable');

REVOKE ALL ON SCHEMA si FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA si FROM PUBLIC;
GRANT USAGE ON SCHEMA si TO si_writer, si_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA si TO si_writer, si_reader;
GRANT INSERT ON ALL TABLES IN SCHEMA si TO si_writer;
GRANT UPDATE ON si.observations, si.defects, si.debt_tracks, si.issues, si.export_items, si.export_meta TO si_writer;
RESET ROLE;
```

### 逐表守衛矩陣（共 14 表，每表恰屬一類；草稿與 PRD §9.3、AC-LD-05-4 逐表相同）

| 表 | 類 | 守衛 |
|---|---|---|
| `si.events` | 追加專用 | BEFORE UPDATE OR DELETE 觸發器 `si.reject_mutation`＋延遲約束 `si.require_audit('seq','append')` |
| `si.artifacts` | 追加專用 | 同上，主鍵欄 `id` |
| `si.audit` | 追加專用 | `si.reject_mutation`＋BEFORE INSERT 的 `audit_chain_guard`；本身是 audit，不另設延遲約束 |
| `si.legacy_rows` | 追加專用 | `si.reject_mutation`＋延遲約束（append） |
| `si.console_audit_files` | 追加專用 | `si.reject_mutation`＋延遲約束（append） |
| `si.observations` | 可變且逐列 audit | `si.observation_guard` 限處置欄由 open 轉終值一次＋延遲約束（mutable，`after_sha` 等於 `NEW.row_sha256`） |
| `si.defects` | 可變且逐列 audit | 延遲約束（mutable）；`si_writer` 無 DELETE |
| `si.debt_tracks` | 可變且逐列 audit | 延遲約束（mutable）；`si_writer` 無 DELETE |
| `si.issues` | 讀模型 | 只准 `si_writer` 於同一交易刷新（UPSERT＋`live` 旗標，不 DELETE）；無觸發器，由 `readmodel.fresh` 重算比對 |
| `si.export_items` | 讀模型 | 同上 |
| `si.export_meta` | 讀模型 | 同上，含 `ledger_head`（ADR-SIDB-004） |
| `si.schema_migrations` | 自舉例外 | 只有 INSERT 權限（遷移記錄先於 audit 可用）；不設同交易 audit 約束 |
| `si.meta` | 自舉例外 | 僅 `si_owner` 與 `db flip` 可改（`si_writer` 無 UPDATE）；不設同交易 audit 約束 |
| `si.import_runs` | 自舉例外 | 只有 INSERT 權限（匯入批次是 audit 的上游）；不設同交易 audit 約束 |

### 烟測摘要（一次性容器；指令與輸出存於審查報告，此處只記判準）

1. 三個區塊依序餵 `psql -v ON_ERROR_STOP=1` 須 rc 0。
2. 正控：`si_writer` 同一交易寫 `defects` 與對應 audit 列、寫 `events` 與對應 audit 列，COMMIT 成功。
3. 負控：(i) `si_writer` 對 `events` UPDATE 被拒（第一道＝權限，訊息含 `events`；表擁有者 `si_owner` 同一 UPDATE 與對 `audit` 的 DELETE 被第二道觸發器拒，訊息含 `si.events`、`si.audit`）；(ii) 對 `defects` INSERT 而無同交易 audit 列，COMMIT 失敗，訊息含 `si.defects`；(iii) `si_writer` 執行 `ALTER TABLE si.events DISABLE TRIGGER ALL` 被拒（非擁有者）；另驗 `seq` 不連續、`si_reader` 寫入、觀察列二次處置皆被拒。
4. 收尾：`DROP SCHEMA si CASCADE` 與 `DROP ROLE` 後 `pg_roles` 無 `si_%`，容器自毀。

誠實劃界：非超級權限者的旁路與竄改被擋；`si_owner`、超級使用者可停用觸發器、對 `audit` 整鏈重寫，只能由快照內鏈頭與 `chain.intact`、`state.replay` 事後偵測；`TRUNCATE` 不觸發列級觸發器，由「角色無 TRUNCATE 權限」擋，擁有者仍可。

## 再開症狀

- 出現超級權限竄改的暴露證據：`si check` 的 `chain.intact` 紅，或 `state.replay` 指出（`tbl`、`row_id`）旁路寫入，且鏈頭與快照內鏈頭不一致，並且**不是**測試語料或探針種子造成（暴露度三取一，見 `docs/06_quality/FiveQuestion_Audit_Protocol/severity.md`）→ 重評選項 C 的外部錨點。
- 寫入動詞單次超過 1 s 的預算且 `audit` 與延遲約束是主因（P1 量測 `si db status` 的 `latency` 與動詞計時）→ 重評全表延遲約束改為抽樣或批次。
- `si.audit` 的 advisory lock 取鎖逾時成常態（`lock_timeout` 觸發，與 ADR-SIDB-005 同一把鎖域）→ 重評鏈守衛的鎖粒度。

## 連動面

- 被連動規格：PRD §9.3、§9.5；AC-LD-05-2～05-5；`AgentConsole/backend/src/main/resources/db/migration/V13__si_console_writes.sql`（同型先例，不改）。
- 後續階段：P1 的 TCS 定稿欄位、枚舉 CHECK（AC-LD-05-1，DB 枚舉與 Python 常數雙向相等）、`si check` 新項 `chain.intact`、`state.replay`、遷移檔 `sql/V001__si_init.sql` 以本草稿為底稿；P3a 的 `si db snapshot` 把鏈頭寫進快照（ADR-SIDB-008）。
- 相關 ADR：ADR-SIDB-001（DB 位置，決定備份與錨點可及性）、ADR-SIDB-005（`audit.seq` 配號鎖）、ADR-SIDB-007（憑證）、ADR-SIDB-008（錨點載體）。
- P0 烟測證據：審查報告 G-P0-7 輸出（一次性容器 `pgvector/pgvector:pg18`，不碰長駐容器）。
