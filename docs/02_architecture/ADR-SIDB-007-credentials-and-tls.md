# ADR-SIDB-007：憑證與 TLS（PRD 簡稱 SIDB-07）

## 狀態

Accepted（2026-10-31；決定者＝主控依 `docs/01_requirements/SelfImproving_Ledger_DB_PRD.md` §9.5 SIDB-07 與 §13.1 D-5 轉正式；生效階段 P1）。

## 脈絡

- 根層 CLI（`tools/selfimproving.py`）要連 `si` schema 的 DB；它是純標準庫為原則、驅動只准 `dal_pg_conn.py` 延遲 import 的模組（PRD §6）。
- 憑證現況：AgentConsole 把 DB 憑證放在 `AgentConsole/.env`（由 compose 與 backend 讀取）；AutoClaude 的 DB 連線一律強制 TLS（`factory.py:85-100`）；Bridge 以參數化 SQL 連 DB（`engine-bridge/app/db.py:9-10`）。
- 安全要求（PRD §6、AC-LD-01-4）：任何輸出面（stdout、stderr、`si.audit` 各欄、日誌）皆不含密碼；tracked 檔無 DSN／密碼字面（`<YOUR_…>` 佔位符除外）；HMAC 金鑰不入庫。
- 無人值守窗口（`AUTOSDD_UNATTENDED`）與 SessionStart 簡報也會連 DB（AC-LD-07-2），缺憑證要明確而非靜默。

## 選項與代價

- 選項 A：讀 `AgentConsole/.env`（沿用 Console 的 DB 憑證）。
- 代價：把根層 CLI 耦合到 AgentConsole 的設定檔格式與其餘機密（JWT 金鑰、加密金鑰同檔），這正是 D-5 否決本案的理由（不耦合 AgentConsole 設定與其餘機密）；Console 沒起時根層動詞行為不明。
- 選項 B：只認環境變數 `SI_DB_DSN`（不含密碼的連線描述）加 libpq 的 `PGPASSFILE`（密碼放在 libpq 密碼檔）。
- 代價：每台機器要各自設定一次（缺＝fail-loud）；Windows 與 POSIX 的密碼檔位置與權限規則不同（POSIX 要求檔案權限 0600，Windows 無此檢查），需在 SOP 分平台說明。
- 選項 C：把連線資訊放 `params.json` 或 config 檔。
- 代價：`params.json` 任一鍵改動即改變 `params.fingerprint()`（AC-LD-02-6），且該檔 tracked、會入 git，機密面最差；config 檔同樣有誤 commit 風險。

## 決定

採用**選項 B**（D-5）：根層 CLI 只認 `SI_DB_DSN` 與 `PGPASSFILE`，**不讀 `AgentConsole/.env`**；`SI_DB_DSN` 不得含密碼段，密碼由 libpq 密碼檔提供。

- **TLS**：連線參數 `sslmode`——loopback 可用 `prefer`；非 loopback 須 `require` 以上（對齊 AutoClaude 一律強制 TLS 的作法）；`si db status` 顯示實際 `tls` 狀態。
- **否決 A**：耦合 AgentConsole 設定與其餘機密。**否決 C**：會改變指紋且機密入 git；兩者的理由皆寫進本 ADR 供日後查核。
- **缺值行為**：未設 `SI_DB_DSN`＝`file` 模式（今天的行為）；`db` 模式缺 DSN 或密碼＝fail-loud（rc≠0，輸出 `si-db-unavailable: <cause>`，cause 不含密碼）；`shadow` 模式缺憑證不擋、只印一行並標「量不到」。
- **角色**：`si_owner`（遷移與 `flip`）、`si_writer`、`si_reader` 的登入屬性與密碼由 SOP 附的 psql 範本設定，**密碼不入 SQL 遷移檔**（ADR-SIDB-003 草稿的角色為 NOLOGIN）。
- 診斷輸出一律遮罩：DSN 顯示時只列主機、埠、資料庫、角色，不列密碼。

## 再開症狀

- 無人值守窗口缺 env 成常態：`si-db-unavailable` 在無人值守啟動的簡報或動詞輸出中反覆出現（原因為缺 `SI_DB_DSN` 或 `PGPASSFILE`）→ 重評憑證供應方式（例如機器級預設位置）。
- 任何輸出面出現密碼字面（`AC-LD-01-4` 的哨兵字串負控紅，或 `python tools/lib/secret_scan.py` 在 tracked 檔命中 DSN 字面）→ 立即重評遮罩與輸出路徑。
- 非 loopback 連線因 `sslmode` 不足被拒（`sslmode` 錯誤訊息）成為他機演練的常見阻礙 → 重評他機匯入的連線方式。

## 連動面

- PRD §6 安全、AC-LD-01-4、AC-LD-07-1～07-2、D-5；上位規格勘誤 E-5（`SelfImproving_PRD.md:527`，DB 連線只在 `dal_pg_conn.py`，P1 套用）。
- 後續：P1 的 `dal_pg_conn.py`、`si db status`、SOP 的 psql 範本與密碼檔分平台說明；`docs/05_development/` 的 SelfImproving SOP 新節。
- 相關 ADR：ADR-SIDB-001（DB 位置，決定可達性）、ADR-SIDB-003（角色與權限）、ADR-SIDB-004（console-api 的唯讀連線角色，AC-LD-08-6）、ADR-SIDB-006（請求表的 INSERT 角色）。
