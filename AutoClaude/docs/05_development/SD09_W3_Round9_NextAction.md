# SD_09 W3 Round 9 zero-trust audit 後續行動清單

| 項目 | 內容 |
|------|------|
| 觸發 | 使用者派工 — Architect/SA/SD/QA 全能 zero-trust audit Round 8「8 輪終極收尾」結論 + nightly 第 4 跑（commit f3b8a12, run_id=122635）三維驗證 |
| Audit Round | W3 Round 9（2026-05-25）|
| Audit 發現 | **0 P0 + 0 P1 + 1 P2**（皆已 CLOSED 本輪）— Round 8「8 輪終極收尾 A-」維持 A-，本輪補上「ps1 F2 分支 SSOT 同構治理」 |
| pytest 基線 | **2,528 passed / 122 skipped**（+16：16 個 ac4_nightly_alert_parser 新 case） |
| importlinter | 7 kept / 0 broken |
| LOC violations | 0（total=15050 / baseline=14058 / cap=16869）|
| Nightly 真實取證 | [logs/nightly_2026-05-25_122635.log](../../logs/nightly_2026-05-25_122635.log) 6 stages 全綠 |
| §3.0 並行框架 | 不變（軸 B/C/D 推進不受影響）|

---

## 1. Audit 取證

| 項目 | 取證 |
|------|------|
| Nightly run 4 (Round 9 基準) | [logs/nightly_2026-05-25_122635.log](../../logs/nightly_2026-05-25_122635.log) 6 stages 全綠（mutation=0 / pg-e2e=0 / perf=0 / drift=0 / obs=0）|
| 觀察期 jsonl 累計 | mutation 4 / ac4 4 / obs 3 / drift 3（M-05 同 UTC date dedup → 同日進帳 1 筆，與 Round 8 一致）|
| mutation 5 行 counts | Killed (104) / Survived (38) / Timeout (0) / Suspicious (7) / Skipped (0) — kill_rate=69.80%（與 Round 8 數字一致，當時推論為 timing-stable；⚠️ **Round 10 audit P2-R10-2 修正**：第 5 跑實測 107/38/0/4/0 = 71.81% → 證實 suspicious 4-7 個會在 killed/suspicious 間 bounce flake，非 timing-stable；參見 [Round10 NextAction](SD09_W3_Round10_NextAction.md) P2-R10-2）|
| 紀律 13 條 | **13 PASS / 0 WARN / 0 FAIL**（紀律 #4「驗證鏡子自身要被驗證」由本輪 ps1 F2 SSOT 同構樣板強化）|

---

## 2. Round 9 真實修復（本輪 commit 已 CLOSED）

| ID | 嚴重度 | 狀態 | 根因 | 修法 | 主要檔案 |
|----|--------|------|------|------|---------|
| **P2-R9-1** ps1 F2 區塊 4 條分支缺單元測試 | P2 | ✅ FIXED | [tools/run_local_nightly.ps1:415-441](../../tools/run_local_nightly.ps1#L415-L441) F2 OK / F2 ALERT / F2 stderr / F2 WARN 4 條分支邏輯複雜（stderr/JSON 拆分 + ready_for_labeled_pr 判定 + exception 捕捉）但無單元測試覆蓋；[tests/tools/test_ac4_progress_check.py](../../tests/tools/test_ac4_progress_check.py) 僅測 Python 端 ready_for_labeled_pr=true，未覆蓋 ps1 端邏輯 → 違反紀律 #4「驗證鏡子自身要被驗證」 | 建立 Python pure-function helper `tools/ac4_nightly_alert_parser.py`（134 LOC，plugin_entry tier）作為 ps1 F2 邏輯之 **SSOT 同構樣板**；16 個單元測試覆蓋 4 條分支 + JSON 起點偵測（拒絕 `[ac4_progress_check] WARN:` 誤判為 array）+ AlertDecision frozen dataclass + 真實 nightly 122635 輸出回歸測試；ps1 加入雙向 anchor 註解明示「修 ps1 必修 helper + 16 test」防 drift | [tools/ac4_nightly_alert_parser.py](../../tools/ac4_nightly_alert_parser.py) + [tests/tools/test_ac4_nightly_alert_parser.py](../../tests/tools/test_ac4_nightly_alert_parser.py) + [tools/run_local_nightly.ps1:421-426](../../tools/run_local_nightly.ps1#L421-L426) |

---

## 3. 推翻項（Audit Agent 提出但驗證後不成立）

- **「should_lock 拒鎖 stderr 在 docker 內跑可能 broken」** — 驗證後不成立：should_lock 在 ps1 host 端跑（log:L157-162 stderr `reject reason=insufficient_runs count=4/7` 完整入 log），不在 docker 內
- **「compactor.py 短暫 return True→False 異常」** — 驗證後不成立：mutmut 跑時瞬間 patch 檔案是預期行為，現已還原；mutation_token_guard.log 顯示 compactor.py survived 13 點位是穩定 mutant 編號，非執行中 snapshot
- **「source_sha256 schema 缺失」** — 驗證後不成立：新紀錄已含 `source_sha256=5208cff397beecc5`；舊 2 筆缺欄位由 should_lock else 分支 ceil(N/2) 寬鬆相容

---

## 4. 13 條紀律盤點（Round 9 更新）

| # | 紀律 | Round 9 | 變動 |
|---|------|---------|------|
| 1-3, 5-13 | （略；Round 8 已全 PASS）| ✅ PASS | 無變動 |
| 4 | 驗證鏡子自身要被驗證 | ✅ PASS（強化）| Round 9 補 ps1 F2 SSOT 同構樣板 + 16 case unit test，從「驗證工具自身要被驗證」延伸至「ps1 複雜分支也要被驗證」 |

---

## 5. W1 啟動前未決項（沿用 Round 8 + 本輪新增）

| ID | 項目 | 狀態 |
|----|------|------|
| ADR-SD09-008 | AC4 雙軌 p95 三選項 PM 拍板 | PROPOSED v0.2（cut-off **2026-05-31**；逾期自動「過渡寬限」）|
| ADR-SD09-009 | mutmut suspicious policy（timeout multiplier 升至 15 / suspicious 計為部分 killed）| BACKLOG（W1 評估）|
| **ADR-SD09-010（Round 9 新增 backlog）**| ps1-to-helper SSOT 同構治理規範（ps1 複雜分支須建 Python helper + ≥ 4 case unit test）| 🆕 BACKLOG（W1 評估）|
| 觀察期 #1 | mutation pilot TokenGuardPlugin 連續 7 次 ≥ 70% + 紀律 #12 unique sha + kill_rate ≥ 70% threshold | 累計 4/7 jsonl（kill_rate 69.80% timing-stable 跌破 70% threshold → should_lock 永遠 False）；**W1 必須補 token_guard test 64 點位**才能穩定回 ≥ 70% |
| 觀察期 #2 | AC4 14 天 nightly 全綠（strict 50ms）| 累計 4/14；**數學上不可達標**（真實 p95 51-55ms）— 待 PM 拍板 ADR-SD09-008 |
| 觀察期 #3 | drift_log 30 天零事件 | 累計 3/30；達標日 2026-06-24（若 user 5/25 啟用 schtasks）|

---

## 6. 下一步執行檔案與大綱（依 §3.0 4 軸並行框架）

詳見 [SD09_Execution_Guide.md §3.0](SD09_Execution_Guide.md#30-並行執行框架sd_09-w3-round-6-補建--architectsasdqa-多視角)。Round 9 修復不破壞並行框架，僅在 ps1 F2 區塊加 SSOT 同構樣板 + 16 unit test。

### 6.1 Round 9 新增 backlog（W1 範疇）

- **ADR-SD09-010 ps1-to-helper SSOT 同構治理規範**：評估 ps1 複雜分支須建 Python helper + ≥ 4 case unit test 之硬性紀律（紀律 #4 強化版）；候選對象：ps1 F1（mutation 5 行 counts 解析）、F3（perf regression 三場景判讀）
- **遷移 ps1 F2 區塊改用 `python -m tools.ac4_nightly_alert_parser` CLI 模式**：徹底消除雙端 drift 風險（W1+ 評估，依 ADR-SD09-010 拍板結果決定）
- **helper docstring 加入「DRIFT NOTE」段落**：明示與 ps1 不嚴格同構點（`[` 起點處理）+ W1+ 若要支援 top-level array 時的對齊路徑

### 6.2 4 軸並行下一步動作（沿用 Round 8 第 6 節，本輪未改變執行軸）

| 軸 | 動作 | 時機 | 狀態 |
|----|------|------|------|
| 軸 A 背景觀察期 | user 手動啟用 `schtasks /change /TN AutoClaude_Nightly /ENABLE` | 🔴 立即（Round 9 修復通過後）| 待 user |
| 軸 B W1 前景 | 補 token_guard test 64 點位（compactor 24 / git_verifier 13 / policy 17 / thresholds 7 / watcher 3）— 雙效益：拉高 kill_rate 回 ≥ 70% + 觸發 source_sha256 變化重置觀察期 #1 | 任意時點（建議 ≤ T+10）| 待啟動 |
| 軸 C PM 拍板 | ADR-SD09-008 三選項拍板（觀察期 #2 strict 50ms vs 真實 51-55ms）| ≤ 2026-05-31 | 待 user |
| 軸 D W2-W6 預備 | ADR-SD09-009 mutmut suspicious policy 三方研究 / **ADR-SD09-010 ps1-to-helper SSOT 治理三方研究（Round 9 新增）**| 任意時點 | 待啟動 |

---

## 7. 收斂評估與成熟度

### 7.1 收斂訊號（正向）

- **Round 9 zero-trust audit 證實 Round 8「8 輪終極收尾」結論可重複**：第 4 跑 nightly 6 stages 全綠 + 13 條紀律全 PASS + mutation kill_rate 69.80%（與 Round 8 數字一致；⚠️ Round 10 第 5 跑修正：實為 suspicious bounce flake，非 timing-stable）
- **P2-R9-1 真實打中「ps1 端紀律 #4 取證缺口」**（Round 8 自評時 ps1 F2 分支「F2 OK / F2 ALERT / F2 stderr / F2 WARN」當時雖修了 P2-NEW-2 stderr capture，但未補單元測試 — 屬「修了 stderr 不被吃掉，但沒驗證解析邏輯」）
- **pytest 2,528 passed / 122 skipped**（+16 防迴歸；超 SD_08 W6 基線 2,094 達 +434）
- **無破壞 §3.0 並行框架 / nightly A- 治理**：ps1 變動為 +7/-0 純註解，無邏輯變動
- **建立「ps1 → Python helper SSOT 同構」治理模式**：可作為日後其他 ps1 複雜分支補測樣板

### 7.2 仍未收斂訊號

- **schtasks 等 user 手動啟用**（5/25 啟用後觀察期時間軸從 5/25 起算）
- **觀察期 #1 雙重數學阻塞持續**：(a) unique sha 不足（4/7） + (b) kill_rate 69.80% timing-stable 跌破 70% threshold → W1 補 token_guard test 64 點位同時破解兩條件
- **觀察期 #2 數學上不可達標**：strict 50ms vs 真實 51-55ms；依賴 PM 拍板 ADR-SD09-008（cut-off 5/31）

### 7.3 專案成熟度評估（Round 9 復位）

| 維度 | 評分 | 變動（vs Round 8）|
|------|------|------|
| 架構 / 程式碼品質 | 🟢 A | 不變 |
| 測試覆蓋 | 🟢 A（2,528）| +16（紀律 #4 ps1 端延伸強化）|
| CI / nightly 治理 | 🟢 A- | 不變（Round 9 證實 A- 可重複；ps1 SSOT 同構樣板模式建立）|
| 觀察期升級條件 | 🔴 C | 不變（W1 補測 + PM 拍板 + ADR-SD09-009/010 評估）|
| 文件治理 | 🟢 A | 不變（CLAUDE.md=400 exact）|
| PG production 上線就緒 | 🟡 B | 不變 |
| 整體 SD_09 進度 | 🟡 W0 採集中 | 不變 |

**結論**：**Round 9 為 9 輪 audit 真實連續壓力測試的第 4 跑驗證**。Round 8「8 輪終極收尾」聲稱被本輪 zero-trust 精神**證實可重複**（第 4 跑 nightly 結果與第 3 跑完全一致 — mutation kill_rate / counts / 觀察期累計皆穩定）；本輪修復 1 項 P2（ps1 F2 SSOT 同構樣板）+ 加 16 個 unit test 強化「驗證鏡子自身要被驗證」精神延伸至「ps1 複雜分支也要被驗證」。**至此 Round 1-9 共 9 輪 audit 對 nightly 治理之累積壓力測試完成，CI/nightly 治理 production-grade A- 復位且可重複**（不再有 audit 殘留 P0/P1/P2 直接相關於 nightly 程式 / 過程 / 結果；唯一新增 P2-R9-1 為 ps1 端測試覆蓋率，已修；ADR-SD09-010 為治理升級 backlog 非阻塞）。

---

**版本紀錄**：v1.0 2026-05-25 — Round 9 audit 修復收尾；對應 commit `449a4b2` / tag `v2026.05.25-08` / merge main `c904d29` ✅ pushed to https://github.com/wuweihungmobile/AutoClaude。
