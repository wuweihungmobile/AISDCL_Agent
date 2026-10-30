# ADR-SIDB-002：DAL 與模式（PRD 簡稱 SIDB-02）

## 狀態

Accepted（2026-10-31；決定者＝主控依 `docs/01_requirements/SelfImproving_Ledger_DB_PRD.md` §9.5 SIDB-02 與 D-4、D-18 轉正式）。

## 脈絡

- 根層 CLI 要在「有 DB」與「沒 DB」兩種環境都能跑：每台機器、每次 CI 都要讀的東西不能依賴 DB（PRD §3.2、AC-LD-11-1）。
- 讀取介面窄：`LEDGER_REL`／`PROPOSALS_REL` 在 `tools/` 共 65 處／28 檔，其中 SI 套件 20 檔 45 處（PRD §4 觀察 1）；加一道 Store 縫即可換儲存而不重寫判準。
- 先例：AutoClaude 的 `yaml_only`／`both`／`db_only` 三模式（`factory.py:267-294`、`dual_state_repository.py:102-134`）。
- 測試分層（AC-LD-02-1、11-1～11-4）：Mem、File 契約測試住 `tools/tests`、不 skip；PG 契約測試需要真資料庫。行數棘輪只數 `tools/tests/*.py` 的測試行（`test_adr_xplat001_c1c2_lock.py:554,595`），一次性例外名冊上限已滿（PRD §8.3）；PG 專屬測試若放 `tools/tests` 會進 skip 政策與棘輪的管轄。
- 模式不得放 `params.json`：`params.fingerprint()` 雜湊協定目錄所有檔，多一個鍵就改變判準版本（PRD §9.2、AC-LD-02-6）。

## 選項與代價

- 選項 A：只做 Pg（單一 PG 後端，測試也一律連 DB）。
- 代價：沒有 PG 的機器與 CI（windows／macos compat）整批跑不了 SI 測試；「無 PG 也能跑」被打破；既有 SI 測試 24,896 行的夾具要全改。
- 選項 B：Mem＋File＋Pg＋影子（三後端加 `file`／`shadow`／`db` 三模式）。
- 代價：要寫並維護三個後端與一份契約基類（同一組種子、三處斷言數相等）；影子寫要處理 DB 不可用的降級；新增 14 支 `dal_*.py` 檔（PRD §9.4 逐檔：Store 與模式解析 3、File／Mem 後端 5、PG 後端 6）；契約測試的行數與棘輪稅需預算（PRD §8.3）。
- 選項 C：在 B 之外另加 SQLite 後端。
- 代價：雙 SQL 方言；SQLite 沒有 `timestamptz`、`jsonb`、觸發器語意與 advisory lock 的對等物，保真度差，等於測一個不會上線的後端；Mem 已滿足「無 PG 也能跑」。

## 決定

採用**選項 B**（AutoClaude 先例）；**否決 C**（雙 SQL 方言、保真度差，D-4）；否決 A（破壞離線可跑）。

- **模式解析（執行期，非 params 鍵）**：先看程式碼常數 `LEDGER_TRUTH`（預設 `file`，只在 P3b 切換 commit 改為 `db`）；`SI_DB_DSN` 有設且 `--repo` 即 CLI 自身所在 checkout 根時，把 `file` 升為 `shadow`；環境變數 `SI_LEDGER_STORE` 僅供測試與彩排覆寫（AC-LD-02-2）。三值意義：`file`＝今天；`shadow`＝檔仍是真相、DB 影子並對帳；`db`＝DB 是真相，DB 不可用即 fail-loud、不讀任何帳本檔。解析與庫內 `si.meta.truth` 不一致＝`MODE-MISMATCH`（AC-LD-02-3）。
- **PG 契約測試放兄弟目錄 `tools/tests_pg/`，記為可見決定**：行數棘輪視 `tools/tests` 的子目錄為繞道（`test_adr_xplat001_c1c2_lock.py:4491-4496`），兄弟目錄同型，是稅的緩解而非規避；`tools/tests_pg/*.py` **仍受 LOC 分級**（只有名為 `tests` 的目錄豁免，`AutoClaude/tools/check_loc_budget.py:296`；落 `guardrail_cli`，單檔 ≤750 斷言行），因此拆成多檔、每階段 ≤4 檔；不受行數棘輪、skip 政策與「全世界沒跑過」判準管轄（AC-LD-11-1、11-4）。Root_Layout §2 已先加對應兩格（P0 交付項 D1：`PG 專屬契約測試`、`套件內 SQL 遷移資料目錄`）。
- Mem 與 File 契約測試留在 `tools/tests`、不 skip；PG 部分由 CI 新工作 `si-pg-contract` 把關（自帶收集數下限，缺 DSN 時 `SI_TEST_PG_REQUIRED=1` 失敗而非略過）。

## 再開症狀

- `si-pg-contract` 在 CI 長期跑不起來（連續失敗或收集數低於下限），導致 PG 契約實際上無人把關 → 重評測試落點與 CI 服務容器做法。
- 行數棘輪收緊到涵蓋兄弟目錄（`test_adr_xplat001_c1c2_lock.py` 的掃描範圍改成含 `tools/tests_pg`）→ 重評放兄弟目錄的取捨，改回備選剖面。
- `tools/tests_pg/` 單檔逼近 `guardrail_cli` 的 `750` 斷言行上限，或每階段新檔數逼近 `≤4` → 重評拆檔策略。

## 連動面

- PRD §8.3、§9.2、§9.4、D-4、D-18；AC-LD-02-1～02-5、11-1～11-4；TCS P0 §5.3（掃描器普查與 `tools/tests_pg/` 管轄）。
- 後續：P1 交付 `dal_*.py` 與 `tools/tests_pg/`、CI `si-pg-contract`；能力登記新增 `dbr`／`dbw`（`test_selfimproving_capability.py` 同步鎖，P1 的 TCS 列明）。
- 相關 ADR：ADR-SIDB-001（DB 位置）、ADR-SIDB-007（連線憑證與 `SI_DB_DSN`）。
