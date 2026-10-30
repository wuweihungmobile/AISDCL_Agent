# ADR-SIDB-005：寫入序列化與配號（PRD 簡稱 SIDB-05）

## 狀態

Accepted（2026-10-31；決定者＝主控依 `docs/01_requirements/SelfImproving_Ledger_DB_PRD.md` §9.5 SIDB-05 轉正式；生效階段分段：配號與 `audit.seq` 自 P1 影子寫入即需〔`audit_chain_guard` 要求 `seq` 連續，ADR-SIDB-003〕，OBS、DEF、事件的配號改走 DB 自 P3a）。取代 SelfImproving PRD 的 ADR-SI-10 在 DB 模式下的作法。

## 脈絡

- 今天事件帳本的寫入序列化在 `tools/lib/selfimproving/evwrite.py:97-136`：獨佔建鎖檔→讀末行→配號→追加。`obs-add`／`obs-close` 存在但只收 Console 載體；缺陷與結構債列沒有動詞，其餘寫入靠人手改檔（PRD §4 觀察 2）。
- 切到 DB 後，多個行程可能同時寫入（Console 載體入帳、主控動詞、併發測試）。AC-LD-05-6 要求：失敗時領域表、audit、讀模型全回滾、零殘列；N≥8 行程×M 筆併發下號碼（OBS、DEF、`audit.seq`）無重複、無缺漏、`seq` 連續、鏈無分叉。
- `si.audit` 的鏈守衛要求 `seq` 連續、`prev_hash` 銜接（ADR-SIDB-003），因此配號洞（`seq` 跳號）會讓整條鏈紅。
- DEF 編號規則（AC-LD-06-3）：取家族 200 下一號、滿 998 開下一族、不入保留帶——這是「取最大值再加一」語意，不是自增。

## 選項與代價

- 選項 A：沿用檔案鎖（`evwrite.py` 的獨佔建檔）。
- 代價：鎖檔在 DB 模式下沒有意義（跨機、跨容器不共享）；持鎖行程崩潰留下殭屍鎖檔需人工清；與「不寫帳本檔、不取檔案鎖」（AC-LD-06-1）直接衝突。
- 選項 B：`pg_advisory_xact_lock` 加鎖內 `max+1`（交易開頭取交易級 advisory lock，鎖內取各編號空間的最大值加一，交易結束自動釋放）。
- 代價：寫入全域序列化，吞吐受單鎖限制（本專案寫入量為每日數十至百餘列，PRD §13.2 OQ-1 的事實，遠低於瓶頸）；要設 `lock_timeout` 避免無限等待；鎖粒度與鎖鍵要統一定義（與 `audit_chain_guard` 同一鎖域，ADR-SIDB-003）。
- 選項 C：identity／sequence（以 PG 的 `GENERATED … AS IDENTITY` 或 SEQUENCE 取號）。
- 代價：sequence 在交易回滾時不回收，會留洞，直接違反 `audit.seq` 連續與「回滾不留洞」；DEF 規則的家族與保留帶語意也不是自增能表達的。

## 決定

採用**選項 B**：所有寫入動詞在單一交易開頭以 `pg_advisory_xact_lock` 取鎖，鎖內以 `max+1` 配號（OBS、DEF、事件 `seq`、`audit.seq` 一律如此），同交易寫領域表、audit 與讀模型，COMMIT 時鎖自動釋放。

- **鎖鍵與隔離層級**：鎖鍵＝`pg_advisory_xact_lock(hashtext('si.audit'))`，與 ADR-SIDB-003 的 `audit_chain_guard` 取同一把（同一連線可重入：動詞先取鎖、觸發器再取不會自鎖）；寫入交易用 `READ COMMITTED`——`REPEATABLE READ` 的快照在取鎖前就已定下，等鎖之後鎖內讀到的 `max` 會是過期值。
- **取鎖逾時**：連線設定 `lock_timeout`（DB 端逾時，不用 `time.sleep` 或 `while True` 輪詢，AC-LD-06-5 的禁字樣）；逾時視為動詞失敗、零寫入、回報可重試。
- **否決選項 C**：回滾留洞，與鏈連續性衝突；否決選項 A：與 DB 模式的語意不合。
- 負控（P1／P3a 的 TCS 逐一落地）：確定性交錯（兩交易交錯取號）與壓力（N 行程併發）兩種。
- 不處理的事：持超級權限者可繞過鎖直接寫（見 ADR-SIDB-003 的誠實劃界）。

## 再開症狀

- 取鎖逾時成常態：寫入動詞日誌中 `lock_timeout` 觸發事件（`canceling statement due to lock timeout`）在一個窗口內重複出現 → 重評鎖粒度（例如分編號空間的鎖）。
- 併發壓力測試出現重複號碼或 `seq` 缺口（`chain.intact` 紅且非旁路寫入）→ 重評鎖鍵與鎖內取號的位置。
- 寫入量成長到單鎖吞吐成瓶頸（寫入動詞單次超過 `1 s` 預算且主因為等鎖）→ 重評序列化策略。

## 連動面

- PRD §9.1、§9.5、AC-LD-05-6、AC-LD-06-1、06-3、06-5；上位規格勘誤 E-2（ADR-SI-10→ADR-SIDB-005；E-2 套用階段 P2，本項生效 P3a）。
- 後續：P1 影子寫入的取鎖與鎖內配號（AC-LD-05-6 屬 P1 出口）及併發負控；P3a 的寫入動詞（`def-*`、`debt-*`、`--carrier operator`）與併發測試；`evwrite.py` 的 DB 模式改接 Store。
- 相關 ADR：ADR-SIDB-003（鏈守衛同一把鎖域）、ADR-SIDB-004（讀模型刷新在同交易內）。
