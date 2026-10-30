# ADR-SIDB-004：讀模型（PRD 簡稱 SIDB-04）

## 狀態

Accepted（2026-10-31；決定者＝主控依 `docs/01_requirements/SelfImproving_Ledger_DB_PRD.md` §9.5 SIDB-04 轉正式；生效階段 P2，且只在 `console.si.read-source=db` 時）。

## 脈絡

- 議題中心現況：Bridge 每次請求起根層 CLI 子行程讀帳本檔、現場重算，「不快取：每請求重算，帳本是唯一真相源」（`Issue_Center_PRD.md:415`）；SelfImproving PRD 的 ADR-SI-12 選 Bridge 子行程、否決 PG 讀模型為「第二個真相源」（`SelfImproving_PRD.md:999`）。
- 帳本改 DB 之後，console-api 想直讀 DB（P2，PRD §8）。議題的「狀態對照、折疊、問題清單、legend、summary」是一整套判準（`fold.py`、`defs.classify_status`、議題對照表），今天只有 Python 一份。
- 兩語言兩份判準是本 repo 反覆在治的複本型缺陷：任何判準改動都要雙邊同步，且差異靜默。
- 效能目標：db 路徑 p95 ≤ bridge 路徑 p95（AC-LD-08-5）；寫入動詞單次 ≤1 s 含讀模型刷新（PRD §6）。

## 選項與代價

- 選項 A：Java 重實作 fold 與對照表（console-api 自己讀 `si.*` 原始表即時計算）。
- 代價：兩份判準；每次 Python 判準改動都要同步 Java 並跑雙邊差分；與 ADR-SI-12 的否決理由同型；Console 側改動面擴大（Console 側 si／issues 相關碼現有約 25,707 行，PRD `[C-10]`）。
- 選項 B：Python 算、DB 存、Java 只讀（寫入時於同一交易刷新 `si.issues`、`si.export_items`、`si.export_meta`，帶 `ledger_head`）。
- 代價：讀模型是衍生值，可能落後帳本；需要 `ledger_head` 比對與 `READ-MODEL-STALE` 偵測、`readmodel.fresh` 重算比對；寫入動詞多一段刷新，要守 ≤1 s 預算；`Issue_Center_PRD.md:415` 的「不快取」需勘誤。
- 選項 C：保留 Bridge 子行程讀 DB（Bridge 仍經根層 CLI 取數，CLI 改從 DB 讀）。
- 代價：每請求起子行程的延遲與併發上限不變；不達成「console-api 直讀、停 Bridge 仍可看」（PRD P2 出口）；但零新增讀模型、零判準複本，風險最低。

## 決定

採用**選項 B**：判準只活在 Python 一處，Java 側只有唯讀 adapter（只經一個類別、只有 SELECT、連線角色為唯讀角色，AC-LD-08-6）。

- **過期偵測**：讀模型表帶 `ledger_head`（寫入時與 `si.audit` 鏈頭同交易寫入 `si.export_meta`）；console-api 比對 `si.audit` 鏈頭大於讀模型的 `ledger_head` 時，回應 `ne` 含 `READ-MODEL-STALE`，前端明說「資料比帳本舊」（AC-LD-08-3）。`si check` 的 `readmodel.fresh` 另以 Python 重算讀模型逐值比對。
- **預設不變**：`console.si.read-source` 預設 `bridge`，行為與今天相同；`db` 為 P2 起的非預設選項。
- **選項 C 為 P2 退路**：若 B 的刷新使寫入超過預算、或鏈頭常落後，把 `read-source` 改回 `bridge`（一步切回），Bridge 子行程路徑本來就未被移除（P4 才移除）。
- 否決 A：兩份判準的維護成本與靜默差異風險，高於 B 的衍生值落後風險（後者可偵測、前者不可）。

## 再開症狀

- 讀模型刷新使寫入動詞超過 1 s（`si db status` 的 `latency` 或動詞計時 >1000 ms 成常態），或鏈頭常落後（`readmodel.fresh` 紅）→ 退回選項 C（`read-source=bridge`）並重評刷新策略。
- 線上出現 `READ-MODEL-STALE` 在無寫入的穩態不消失 → 重評刷新與 `ledger_head` 寫入是否同交易。
- db 路徑 p95 高於 bridge 路徑 p95（AC-LD-08-5 的比較轉負；觀測於 `GET /api/v1/issues?status=待處理&limit=500` 的 50 次取樣）→ 重評讀模型表結構與索引。

## 連動面

- PRD §3.3 第 4 列、§9.3 讀模型表、AC-LD-08-1～08-6；上位規格勘誤 E-2（ADR-SI-12 被取代關係）、E-6（`Issue_Center_PRD.md:415` 加註；兩案皆備案、P2 套用）。
- 後續：P2 的 `dal_readmodel.py`、console-api adapter、`FILE-DRIFT` 與黃金檔差分；P4 才移除 Bridge 的 SI 讀寫路由。
- 相關 ADR：ADR-SIDB-003（讀模型表只准 `si_writer` 刷新、無逐列 audit，由 `readmodel.fresh` 重算比對）、ADR-SIDB-005（`ledger_head` 與配號鎖）。
