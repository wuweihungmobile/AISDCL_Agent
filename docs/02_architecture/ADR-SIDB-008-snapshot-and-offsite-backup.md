# ADR-SIDB-008：快照與離機備份（PRD 簡稱 SIDB-08）

## 狀態

Accepted（2026-10-31；決定者＝掌舵者 2026-10-27 對 OQ-1 的裁決〔PRD §13.2「全部採建議值」〕，主控依 PRD §9.5 SIDB-08 轉正式；生效階段 P3a）。

## 脈絡

- git 今天是唯一的離機備份與 CI 內容閘的輸入（PRD R-2、R-3）；切換後 DB 是唯一一份。備份面現況：WAL 歸檔約每 60 秒一段、每日 02:30 `pg_dump -Fc`，但離站 repo 是本機單碟 MinIO，同機而非離機（PRD §8.2，`docker/README.md:216-226`、`:491`）。
- 寫入有尖峰：OBS 10-19 單日 144 列、近 7 日 142 列、DEF 近 14 日 40 列（PRD `[C-15]`）；一天不匯出可能丟數十至百餘列。
- git 成本實測可忽略：快照首份 1,123 KiB、其後每份約 1.6 KiB；但須固定單一目錄覆寫，日期目錄會使工作樹每份增加約 2.9 MB（PRD `[C-18]`）。
- 快照同時是鏈的外部錨點（ADR-SIDB-003 的錨點＝快照內鏈頭）與 CI 無 DB 時的內容閘輸入（AC-LD-12-2）。
- 逃生口先例：`AUTOSDD_NET_RATCHET_OFF`（`ledger_closing_guards.py:42-55`）。

## 選項與代價

- 選項 (a)：輪收尾手動匯出。
- 代價：RPO 為數日；依賴人記得；錨點與 CI 內容閘輸入常過期；與「消除手動維護帳本」的目標相違。
- 選項 (b)：快照放固定單一目錄覆寫，加 pre-commit 快照閘。
- 代價：每次 commit 多一道匯出閘（DB 可達且鏈頭落後時擋 commit 並印匯出指令）；DB 不可達時只出聲不擋；需要逃生口環境變數；快照入 git，歷史檔案累積（實測成本可忽略）。
- 選項 (c)：(b) 加每日 `pg_dump -n si`。
- 代價：多一個排程與備份目的地要維運；演練要驗還原到拋棄式庫後 `si check` 全綠；離機的「機」要掌舵者定（本機單碟不算離機）。
- 選項 (d)：不要快照。
- 代價：災難復原只剩 pgBackRest 加真 S3；CI 內容閘改 NE；鏈無外部錨點、快照鏈頭相關閘略過。

## 決定

**舊檔永遠保留**（凍結檔不刪，P4 只退役寫入它們的程式，PRD §6），並採 **(b)＋(c)**（OQ-1 裁決；即選項 (c)，其中含 (b)）：

- **(b)**：快照放固定單一目錄 `docs/06_quality/SelfImproving_Snapshots/`（覆寫；舊版在 git 歷史；標頭宣告為衍生物並含鏈頭）。pre-commit 在「DB 可達且 DB 鏈頭≠快照鏈頭」或「匯出失敗（rc≠0）」時擋 commit 並印匯出指令；DB 不可達只出聲不擋（D-17）；逃生口為環境變數 `AUTOSDD_SNAPSHOT_GATE_OFF=1`，須在 commit 前設置、commit 訊息寫明理由，**不接受 `--no-verify`**。
- **(c)**：再加每日 `pg_dump -n si` 的離機備份；演練＝還原到拋棄式庫後 `si check` 全綠，指令與 rc 入證據檔（AC-LD-12-3）。
- 否決 (a)（RPO 過長）、(d)（拿掉唯一錨點與 CI 內容閘輸入）。
- 快照是 `si db snapshot` 動詞的產物（寫檔，閉包含 `dal_snapshot.py`），**不是** `export` 的 kind；`FileStore` 可直接讀快照目錄（AC-LD-12-1、12-2）。
- 本決定不新增守衛碼：pre-commit 快照閘走既有非守衛面的 git-hooks 機制（PRD §3.4），不碰 `.claude/**`。

## 再開症狀

- 快照鏈頭長期落後 DB 鏈頭：pre-commit 反覆擋 commit 或 `AUTOSDD_SNAPSHOT_GATE_OFF` 被常態使用（逃生口使用紀錄在一個窗口內多次）→ 重評觸發時機與 RPO。
- 快照匯出長期失敗：`si db snapshot` rc≠0 成常態 → 重評快照格式與大小（單一目錄覆寫是否撐得住）。
- 每日 `pg_dump -n si` 排程連續缺席或還原演練 `si check` 紅 → 重評離機備份目的地。
- 快照單一目錄的 git 歷史體積暴增（單份增量遠超約 `1.6 KiB`）→ 重評是否改為只存鏈頭加差異。

## 連動面

- PRD §8.2、§9.5、OQ-1、FR-LD-12（AC-LD-12-1～12-3）、R-2、R-3；D-17（pre-push 在 DB 不可達時不擋）。
- 後續：P3a 的快照匯出／匯入、pre-commit 快照閘、離機備份演練證據檔；P3b 的 `si db flip --check` 驗快照在場與鏈頭相符（G-SIDB-4）。
- 相關 ADR：ADR-SIDB-001（H2 生命週期隔離）、ADR-SIDB-003（錨點）、ADR-SIDB-006（Console 載荷的備份承擔）。
