# ADR-SIDB-006：Console 載體（PRD 簡稱 SIDB-06）

## 狀態

Accepted（2026-10-31；決定者＝主控依 `docs/01_requirements/SelfImproving_Ledger_DB_PRD.md` §9.5 SIDB-06 轉正式；生效階段 P3a，與 ADR-SIDB-001 的 DB 位置連動）。

## 脈絡

- 今天 Console 不直接寫帳本：每次決定、新增觀察、關閉觀察由 backend 簽一份稽核 JSON、經 Bridge 落成稽核檔，再由主機端根層 CLI 驗簽入帳（PRD §2）。Console 側另有同型稽核列 `console.si_console_writes`（`V13__si_console_writes.sql`，列不可改、補償 DELETE 例外）。
- SelfImproving PRD 的 ADR-SI-03′ 把載體定為稽核檔、`audit_sha256` 為稽核檔位元組的 sha256，並否決「CLI 讀 PG」（選項 E）為第二個真相（`SelfImproving_PRD.md:990`、`:792`）。帳本改 DB 後，DB 成為唯一真相，E 的「第二個真相」理由失效（PRD §3.3 第 2 列）。
- 載體≠寫入者的不變式要保留：console-api 對 `si.*` 除請求表 INSERT 外零寫入（AC-LD-09-3）。
- 歷史：repo 內 0 個稽核檔、帶 `audit_sha256` 的事件 4 筆、`carrier=console` 的 OBS 列 2 列（PRD `[C-14]`）。

## 選項與代價

- 選項 A：稽核檔加 Bridge（維持現況）。
- 代價：稽核檔放在家目錄 `console_audit/`，P3b 之後帳本在 DB、載荷卻在檔案，「備份承擔不可丟棄性質」分散在兩處；Bridge 仍是寫入路徑的一環（P4 想移除 Bridge 的 SI 讀寫路由會被卡住）。
- 選項 B：載荷列放 `console.si_console_writes`（P3a 以 Flyway 新版本加 `raw` 欄，保存簽章載荷外層 JSON 原始位元組）。
- 代價：「稽核檔不可丟棄」的性質改由 DB 備份承擔（與 ADR-SIDB-008 連動）；`console.*` 在 Console 專案的卷內，`down -v` 風險與 ADR-SIDB-001 選項 B 同；Flyway 遷移要同批改 Console 側。
- 選項 B′：專屬容器（ADR-SIDB-001 選項 C）時，載荷列放 `si.console_requests`（只准 console-api INSERT，`si_writer` 只 SELECT）。
- 代價：多一張表與一個角色權限組合（它不在 ADR-SIDB-003 的 14 表內，是專屬容器變體）；console-api 要同時連 Console 庫與 `si` 庫。

## 決定

採用**選項 B**；若 ADR-SIDB-001 在 P3 進場前定案為專屬容器，改採**選項 B′**。否決 A（載荷與帳本分處兩個持久層，P4 移除 Bridge 路徑被卡）。

- **旗標** `console.si.write-carrier`，三值：`file`（現況：Bridge 落稽核檔，V13 表照寫）、`dual`（兩者並存，表列含原始位元組欄）、`db`（只寫表列，Bridge 不再落檔）；預設 `file`；回退＝把旗標改回前一值。切換前 `console_pending`（`si status`）必為 0，否則拒切（AC-LD-09-1）。
- **原始位元組與雜湊**：入帳時 `audit_sha256＝sha256(原始位元組)`，語意同今天；位元組存 `console.si_console_writes.raw`（B）或 `si.console_requests.raw`（B′）（AC-LD-09-2）。歷史稽核檔以 `si db import --audit-dir` 匯入 `si.console_audit_files`，雜湊相符可回查，找不到檔者維持今天的 NE。
- **drain**：主機 CLI 自表驗簽入帳，同一 `audit_ref` 跨載體只入帳一次。
- 與既有 AC-SI-33／AC-SI-35 的關係：資格、K=1、HMAC 驗簽等與載體無關者沿用；載體綁定者（稽核檔名安全等）在 P3a 的 TCS 對映表標「取代」並給等價 AC（AC-LD-09-4）。

## 再開症狀

- Console 表被清而尚有未入帳列：`si status` 的 `console_pending` 大於 0 而 `console.si_console_writes` 查無對應 `audit_ref`（例如 `down -v` 之後）→ 重評載體放置與備份頻率。
- 旗標切換後同一 `audit_ref` 被入帳兩次或漏入（`audit_ref` 重複或 `console_pending` 久不歸零）→ 重評 drain 的冪等鍵。
- 專屬容器定案後 `si.console_requests` 與 `console.si_console_writes` 並存造成雙寫路徑歧義 → 重評 B 與 B′ 取一。

## 連動面

- PRD §3.3 第 2 列、PRD `:219`（§9.3 資料模型表的載荷列）、FR-LD-09（AC-LD-09-1～09-4）；上位規格勘誤 E-3（`SelfImproving_PRD.md:990`、`:792`，P3a 套用）。
- 後續：P3a 的 Flyway 新版本（加 `raw` 欄）、Bridge 載體旗標、主機 `decide`／`obs-add`／`obs-close` 自表驗簽；P4 移除 Bridge 的 SI 寫入端點。
- 相關 ADR：ADR-SIDB-001（DB 位置，決定 B 或 B′）、ADR-SIDB-007（連線憑證）、ADR-SIDB-008（備份承擔不可丟棄性質）。
