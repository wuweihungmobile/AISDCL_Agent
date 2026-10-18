# SCG-4 PR Review 報告 — WebhookSender（TD-1：ESCALATION 的 Webhook 發送，DF-A）

**審查日期**: 2026-10-18　**審查者**: 整合輪 116 W3 QA（未參與規格撰寫與實作；規格作者＝W2 SA、實作者＝真 haiku 經 Bridge 委派，三方不同）
**審查範圍**: `AutoClaude/autoclaude/utils/webhook_sender.py`（新，135 行）、`AutoClaude/autoclaude/utils/notifier.py`（改，+17／-7）、`AutoClaude/tests/utils/test_webhook_sender.py`（新，503 行）；commit `306dbb2a`
**基準規格**: `AutoClaude/docs/03_testing/contracts/TCS-WebhookSender-20261018.md`（Stage-2 凍結摘要 `sha256:2d473454…cec8cf`，當回合重算相符）　**FSM 鍵**: `autoclaude-webhook`
**證據總檔**: `docs/06_quality/AutoSDD_ZeroTrust_Audit_116.md`（§2.1 本審查全表、§3 閘門、§4 發現）

### A. FRD 功能規格一致性

| AC-ID | 驗收標準（摘要） | 實作座標 | 測試座標（`tests/utils/test_webhook_sender.py`） | 結論 |
|-------|------------------|----------|-----------------------------------------------|------|
| AC-001-1 | 2xx 即成功、POST JSON、frozen、`timeout_s` 傳進 httpx | `webhook_sender.py:26-31、113-127` | AT-001-1-1 `:23-62`：200／201／204 逐一比對結果物件、方法、URL、JSON 本文、content-type；逾時只斷言 `read` 鍵 | Pass（P01、P06、P07 見必修） |
| AC-001-2 | 非 https、空值、無主機、非字串、解析拋 ValueError 皆不發送 | `:42-51、93-95` | AT-001-2-1 `:65-93`：12 個壞位址（含 `https://[::1`）、handler 零呼叫 | Pass |
| AC-001-3 | 5xx／網路錯重試、退避 0.5 起倍增封頂 8、3xx／4xx 不重試、終局取最後一次 | `:118-135` | AT-001-3-1 `:96-129`；AT-001-3-2 `:132-194`（五情境含混合失敗序列）；AT-001-3-E-1 `:197-240`（帶 Location 的 302 與主機斷言、400／401／404／429、`max_attempts=1`） | Pass |
| AC-001-4 | 永不拋例外；BaseException 原樣傳播 | `:99-103、121-123` | AT-001-4-E-1 `:243-316`：RuntimeError 不重試、六種壞 payload、十種壞參數、`_Stop(BaseException)` | Pass（P02 見必修） |
| AC-001-5 | 日誌只印遮罩後 scheme＋hostname，error 不含其餘 | `:34-39、76-79、94-110` | AT-001-5-1 `:319-416`：四次呼叫、DEBUG 筆數與 `attempt=n/m`、WARNING 筆數、七個標記字串 | Pass（P03、P08、P09 見必修） |
| AC-001-6 | `notify_escalation` 以四鍵 payload 呼叫一次、結果只寫日誌；空位址行為逐字不變 | `notifier.py:67-81` | AT-001-6-1 `:419-472`；AT-001-6-2 `:475-503`（naive 時間戳斷言） | Pass（P04、P05 見必修） |

### B. Contract 一致性
不適用（出站 client，無對外 HTTP 端點）；契約＝函式簽名。實測 `send_webhook(url, payload, *, timeout_s=5.0, max_attempts=3, transport=None, sleep=None)` 與 `WebhookResult(ok, status, attempts, error)` 與 TCS 一致。

### C. Business Invariants
不適用（無 INVARIANT-SPEC）。R12 不變量（空位址行為逐字不變、alert log 的 naive 時間戳）由 AT-001-6-2 與根層 `_NAIVE_TS_PERSIST_DEBT` 鎖保護，兩者當回合皆綠。

### D. RTM 覆蓋率確認
AC 6／6、AT 9／9 皆有測試函式（`RTM-WebhookSender.md`）；引擎 `RTM-COVERAGE-autoclaude-webhook.yaml`＝AT 9／9、AC 6／6、`unmapped_at_ids=[]`（與操作員副本 sha256 相同）。R1～R12 逐條皆被至少一個 AT 觸及（NFR-001-8 對映表當回合逐條核對屬實）。

### E. 審查證據（全文與命令在證據總檔）
| 項目 | 結果（當回合親跑） |
|------|------------------|
| 整檔單跑（`-p no:xdist -o addopts=`，設 `AUTOCLAUDE_NO_PG_AUTODETECT=1`） | rc 0；9 支通過、1.80 秒（NFR-001-3 要求 < 5 秒） |
| AutoClaude 全套（`-n 8 --dist loadgroup`，PG 注入） | rc 0；5889 通過、7 略過、46.99 秒。🔴 第一次誤設逃生變數跑全套：rc 1（`tests/tools/test_local_ci_gate.py::test_conftest_is_where_the_autodetect_is_wired` 因環境變數而紅），已用正確形態重跑，見 §4 P4 |
| lint-imports／ruff 三檔／check_loc_budget | 9 kept、0 broken／ruff 三檔全數無違規／rc 0（總 18625、分級與絕對違規 0） |
| 覆蓋率（隔離於 scratch 的 coverage 7.6.1，未裝進根 `.venv`） | `webhook_sender.py` 74 述句漏 0、22 分支部分 0＝行 100%、分支 100%（NFR-001-8 要求 ≥ 80%） |
| 突變檢驗（記憶體內改寫，repo 零改動） | 50 個突變：核心 40 個全數被殺（每個至少一個 AT 轉紅）；R 條文導出的探針 10 個存活（見必修 F-01） |
| 範圍守衛 | `git show --stat 306dbb2a` 恰三檔；haiku 執行窗（13:04～13:14）repo 內含 gitignored 的改動檔恰五個＝三白名單檔＋兩個 FSM 狀態檔（Bridge 經 CLI 寫）；越界 0。提交內容與操作員執行後副本逐位元組相同 |
| NFR 靜態項 | NFR-001-1 只 import 標準庫與 httpx；-2 模組 135 行；-4 測試無 `httpx.get`／socket／`time.sleep`；-6 無 skip／xfail／平台分支，`read_text` 帶 encoding，假 URL 皆 example.com 子網域 |

**根因複驗（RC-1，DEF-200-550）**：`context_pct_from_claude_json` 舊算法取頂層 `usage` 跨回合累計；操作員 9 步表 `a2_step_usage_table.txt` 的舊估法在步 5-1 為 100.0%（1,792,905）、步 6-1 為 100.0%（1,177,597）、步 4-e-1 為 82.8%，新法（`usage.iterations[-1]`）全為 10.0%～14.7%。成立；修法有 5 支真實夾具測試，缺 `iterations` 時退回累計（見 §4 P4）。
**StepTracker 遮罩觀察（DEF-AC-038）**：引擎日誌遮罩把步 5-1 啟動行的 `u5er:p4ss@` 改成 `u5er:***@`，Bridge 以 prompt 子字串比對步驟而漏配；事件缺 5-1 的 STARTED／COMPLETED、4-e-1 被標 attempt 2、終局 `STEP_TRACKING_GAP`。**不影響** RTM（來自引擎 YAML）與 FSM（`terminal_decision` 只看 run 終態）；影響 Console 時間軸與失敗歸屬。P3，不在本輪修。

### 審查結論

| 項目 | 狀態 |
|------|------|
| FRD 功能規格 | Pass（0 項不符） |
| Contract 一致性 | N/A |
| Invariants 保護 | Pass |
| RTM 覆蓋率 | 100%（AC 6／6、AT 9／9） |
| 測試強度（突變） | **Fail**：10 個由 R 條文導出的探針存活（F-01，P2） |

**SCG-4 建議**: [需修正後再審查]

### 必修項目（Fail 項）

| 編號 | 問題 | 需修正內容（只動 `tests/utils/test_webhook_sender.py`，不需改 TCS） | 對應規格 |
|------|------|----------------------------------------------------------------------|----------|
| F-01（P2） | oracle 無鑑別力：下列 10 個存活突變體不會讓任何 AT 轉紅 | P01：`:58` 後加 `assert timeouts[0] == {"connect": 2.5, "read": 2.5, "write": 2.5, "pool": 2.5}`；P06：AT-001-1-1 追加 `timeout_s=3`（int）呼叫須成功且 `read` 為 3；P07：AT-001-1-1 追加 `[f.name for f in dataclasses.fields(WebhookResult)] == ["ok", "status", "attempts", "error"]`；P02a／P02b：`:301` 後追加 `send_webhook("http://x.example.com/", None, max_attempts=0, …)` 須回 `invalid_url`、`send_webhook(URL, None, max_attempts=0, …)` 須回 `invalid_payload`，handler 零呼叫；P03：`:371` 後追加 `assert "attempts=3" in warnings[0].getMessage()`；P08：把第四次呼叫的 payload 改為 `{"x": object(), "leak-me-42": 1}`（仍不可序列化），既有標記斷言即可咬住；P09：AT-001-5-1 追加第五次呼叫（`secret_url`、`max_attempts=0`）斷言恰 1 筆含 `invalid_argument` 的 WARNING、全文不含七個標記；P04：AT-001-6-1 `:454` 後追加 `utcoffset() == timedelta(0)`；P05：AT-001-6-1 的 `send_webhook` 替身改為函式，在被呼叫當下斷言 `escalation_alert.log` 已存在 | R4、R3（順序）、R9、R10、AC-001-1、AC-001-5、AC-001-6 |
| F-05（P3） | `webhook_sender.py:1-8` 模組 docstring 寫「目前實作 AT-001-1-1…」的開發進度敘述，完工後不實 | 改為說明用途（出站 POST、有界重試、永不拋例外、日誌遮罩）的 docstring；程式不動 | NFR-001 可維護性（文字） |

註：P04 的斷言僅在機器時區非 UTC 時可咬住該突變（UTC 的 CI 上錯誤實作與正解同值）。按任務書字面「存活突變＝P2」；F-01 內 P02、P03、P06、P07 影響面小（只影響雙重違規時的錯誤碼、日誌欄位、型別接受面、欄位順序），若主控裁量降為 P3，修法同為追加斷言。P09 最重（任何人日後在 `invalid_argument` 路徑把 URL 寫進日誌，現有測試都不會紅）。

### 二審（2026-10-18；HEAD `90d911e4`）

**本節取代**上方「審查結論」表的「測試強度（突變）｜Fail」一列、「SCG-4 建議：[需修正後再審查]」與「必修項目」兩列（F-01、F-05）；一審原文保留不改。

| 項目 | 狀態 |
|------|------|
| FRD 功能規格 | Pass（0 項不符） |
| Contract 一致性 | N/A |
| Invariants 保護 | Pass |
| RTM 覆蓋率 | 100%（AC 6／6、AT 9／9） |
| 測試強度（突變） | **Pass**：50 個突變全數被殺（核心 40、探針 10） |

**SCG-4 建議**: [通過]

**F-01（P2）已結案**：`322e1351` 只動 `tests/utils/test_webhook_sender.py`（+68／−4）。逐行複核：既有斷言刪除 0、弱化 0；被移除的 4 行是匯入放寬、第四次呼叫的 payload 加一個標記鍵（仍不可序列化）、註解「四次」改「五次」、`side_effect=outcomes` 改成回傳同樣兩個結果的函式 `fake_send`（`notifier.py:75` 對 `send_webhook` 沒有 try／except，替身內的斷言失敗會直接外拋）；測試函式名稱不變。一審的 10 個存活者全數轉紅（座標為 `90d911e4` 版）：

| 突變 | 轉紅的測試與座標 |
|------|----------------|
| P01 | AT-001-1-1 `:59` 四鍵全等 2.5 |
| P06 | AT-001-1-1 `:61-64` `timeout_s=3`（int）正例 |
| P07 | AT-001-1-1 `:66-72` 欄位順序 |
| P02a、P02b | AT-001-4-E-1 `:317-333` 組合壞輸入的驗證順序 |
| P03 | AT-001-5-1 `:404` 終局 WARNING 含 `attempts=3` |
| P08 | AT-001-5-1 `:433` payload 加標記鍵，配 `:465-467` 標記迴圈 |
| P09 | AT-001-5-1 `:446-462` 第五次呼叫，配 `:465-467` |
| P04 | AT-001-6-1 `:517-518` `utcoffset() == timedelta(0)`（本機 UTC+8 才咬得住；UTC 的 CI 上與正解同值） |
| P05 | AT-001-6-1 `:489-500` 替身在被呼叫當下斷言 `escalation_alert.log` 已存在且行數相符 |

**F-05（P3）已結案**：`1c802e92` 只改模組 docstring——兩版去掉 docstring 後 AST 相同、行數 136／136、差異只在第 2 行與第 4～7 行。兩處文字面落差列 P4（不擋閘）：F-10 第 6 行「任何例外都收進 `WebhookResult`、永不拋出」偏廣（程式只攔 `Exception`，`BaseException` 照常上拋）；F-11 第 7 行遮罩清單漏列「路徑」（程式與測試都涵蓋路徑）。

**證據**（當回合親跑）：突變在 `322e1351` 與 `90d911e4` 兩個 commit 皆 50／50 全殺（`git archive` 匯出樹量測，不吃工作樹）；整檔單跑 rc 0、9 支通過、1 個警告、0.45 秒；ruff 五個相關檔無違規；FSM `autoclaude-webhook`：`IMPLEMENTATION → PR_REVIEW → RTM_VERIFY → RELEASE_READY`。全文見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_116.md` §9。
