# SD_09 W3 Round 20 NextAction — zero-trust audit 防禦升級（R19 修復後再驗證）

| 欄位 | 內容 |
|------|------|
| Round | **R20** |
| 日期 | 2026-05-26 |
| nightly 跑次 | 第 15 跑（手動 20:53） |
| 觸發 | 用戶要求「完全不信任 zero-trust audit 全面驗證和修復方向是否正確」 |
| 派工 | PM 派 Architect+SA+SD+QA 全能 Agent zero-trust audit + Dev 修復 + QA 再驗證 |
| 對應 R19 | R19 P0 修復後第一次「修復後再 audit」雙重防禦 |
| 結論 | **PASS — 無 P0、僅 P1（建議性）+ P2/P3 backlog** |

---

## 1. Audit 範圍與發現

### 1.1 PASS 項目（13 項已驗證落地）

| # | 驗證點 | 證據 |
|---|--------|------|
| 1 | R19 P0 修復閉環 | `logs/nightly_2026-05-26_020001.log:172-174` 02:00 EXCEPTION + 08:08 修復後全綠 |
| 2 | 6 case 靜態鏡子全綠 | `tests/tools/test_run_local_nightly_static.py` 6/6 PASSED in 0.21s |
| 3 | 兩步式拆解落地 | `ps1:427-429`、`ps1:431-433` 同模式 |
| 4 | PATH 補強健壯 | `ps1:63-85` try/catch + idempotent `-notlike` |
| 5 | StrictMode 3.0 啟用 | `ps1:43` `Set-StrictMode -Version 3.0` |
| 6 | mutation bitmask 判定 | `ps1:357-366` 委派 `mutmut_exit_code.py classify` |
| 7 | cache fresh 三處強制 | `.ac4_junit.xml` / `perf_results.json` / `.mutmut-cache + .pytest_cache` |
| 8 | 觀察期 delta 取證可見 | `ps1:677-689` `END observation progress: ... (delta=N; stage=R)` |
| 9 | 取證鏈一致性 | jsonl unique UTC dates 與 progress 完全對齊 |
| 10 | log file lock 防護 | `ps1:103-133` FileShare.ReadWrite + 5 次 retry 指數退避 |
| 11 | Copy-Item latest pointer | `ps1:692-697` try/catch ErrorAction Stop |
| 12 | emit_real 標記 | 後 3 筆均 true；首筆 MISSING 為 R19 前舊紀錄寬鬆通過 |
| 13 | 跨 stage SKIP 對稱 | `ps1:580-636` drift stage Docker 不可用時 SKIP + table_missing 標記 |

### 1.2 FINDING（P1/P2/P3 — 無 P0）

| # | 優先級 | 問題 | 位置 | 修復狀態 |
|---|--------|------|------|---------|
| F1 | P1 | source_sha256 唯一性即時可見性 | nightly END summary | 建議性（未修；R21 backlog）|
| F2 | P2 | `Get-Command python -EA SilentlyContinue` fallback 區塊 | `ps1:431-433` | ✅ 已是兩步式，無需修 |
| F3 | P2 | observability 首筆 emit_real MISSING | `.observability_history.jsonl` | ✅ 紀律 #10 寬鬆通過符合設計 |
| F4 | P2 | **靜態鏡子無「假 PASS 場景」反向驗證** | `test_run_local_nightly_static.py` | ✅ **R20 已修** |
| F5 | P3 | 觀察期 #1 mutation 同日多 run 凍結風險 | `.mutation_history.jsonl` | 觀察性，無需即修 |

---

## 2. R20 主要修復（F4 — 紀律 #4 雙向延伸）

### 2.1 修復內容

`tests/tools/test_run_local_nightly_static.py` 從 6 case → **8 case**：

```python
# 新增 case 7（adversarial）：餵惡意 mock 字串驗證 case 2 regex 真能擋
def test_regex_rejects_malicious_silentlycontinue_full() -> None:
    ...
    for sample in _MALICIOUS_SAMPLES_SILENTLYCONTINUE_FULL:
        assert pattern.search(sample), f"regex 漏抓（紀律 #4 假 PASS 風險）：{sample!r}"

# 新增 case 8（adversarial）：餵惡意 mock 字串驗證 case 3 + case 6 regex 真能擋
def test_regex_rejects_malicious_silentlycontinue_short_and_stop() -> None:
    ...
```

7 個惡意 mock 樣本：
- FULL（3 個）：`(Get-Command alembic.exe -ErrorAction SilentlyContinue).Source` 等
- SHORT（2 個）：`(Get-Command alembic.exe -EA SilentlyContinue).Source` 等
- STOP（2 個）：`(Get-Command alembic.exe -ErrorAction Stop).Source` 等

### 2.2 修復意義

**紀律 #4 雙向延伸**：原 6 case 全為「正向」grep（ps1 不應含 X 模式），可能被「regex 本身寫錯永遠不 match」騙過。R20 加 case 7/8 餵已知惡意樣本反證 regex 真會 match，並隱含驗證「合法兩步式」不誤抓。這是「驗證鏡子自身要被驗證」原則的結構性實現。

---

## 3. 手動 nightly 第 15 跑取證（20:53）

| Stage | 結果 | rc | 說明 |
|-------|------|----|------|
| Docker-PG-bring-up | exit=0 | 0 | Docker daemon 未啟動，正確偵測並 SKIP 下游 |
| mutation-test | SKIP | -1 | Docker 不可用（紀律 #9 一致 SKIP） |
| pg-e2e + AC4 collector | SKIP | -1 | Docker 不可用 |
| perf-baseline | WARN | 2 | samples=7<20 BLOCK→WARN（ADR-SD08-003 §2.6 v1.1）|
| drift_log-scan | SKIP | -1 | Docker 不可用 |
| observability-snapshot | exit=0 | 0 | PASS（emit_real=true）|
| Cleanup | exit=0 | 0 | PASS |

**觀察期進度**：`mutation=5/7 (delta=0; stage=SKIP) ac4=5/14 (delta=0; stage=SKIP) obs=4/30 (delta=0; stage=0) drift=4/30 (delta=0; stage=SKIP)` — 紀律 #13 正確標示「本次未進帳」。

**08:08 跑（schtasks 修復後 Docker 啟動跑）才是真正觀察期 +1 進帳基準**（[logs/nightly_2026-05-26_080228.log](../../logs/nightly_2026-05-26_080228.log)）。

---

## 4. QA 獨立再驗證（zero-trust）

| 驗證項 | 結果 |
|--------|------|
| 8/8 靜態鏡子 case PASS | ✅ |
| pytest 2,587 passed / 122 skipped | ✅（基線 2,585 + 2 = 2,587）|
| adversarial regex 真擋 7 個惡意 mock | ✅ FULL[3/3]、SHORT[2/2]、STOP[2/2] |
| 合法兩步式不誤抓（false positive 驗證） | ✅ |
| R19 修復閉環仍完整 | ✅ |
| importlinter 7 kept / 0 broken | ✅ |
| LOC violations=0 | ✅ |
| CLAUDE.md ≤ 400 行 | ✅（389 行）|
| 無 NOTE(SD_09) 程式碼殘留 | ✅ |

**收斂結論**：**PASS** — R20 audit 修復項目以 zero-trust 心態獨立再驗證後**全項收斂**，無不收斂項目、無架構性問題、無 P0 阻斷。

---

## 5. 4 軸並行狀態（R20 後）

| 軸 | 狀態 | 進度 | 下一步 |
|----|------|------|--------|
| **A 背景觀察期** | 🟢 schtasks 已啟用 | #1=5/7 / #2=5/14 / #3=4/30 | 5/27 02:00 schtasks 第 16 跑（自動）|
| **B W1 前景** | 🟢 100% 完成 | T1-B1/M1-M3/H1 + R16-R20 連 5 輪 audit | — |
| **C PM 拍板** | 🟢 100% 完成 | ADR-008/009/010 全 v1.0 ACCEPTED | — |
| **D W2-W6 預備** | 🟢 100% 完成 | Production_Migration_SOP §4-§5 + trace_id W3C path-b | — |

**剩餘工作**：軸 A 自動跑（5/27~6/24 每日 02:00），零人類介入。觀察期 #1 達標日 2026-06-02、#2 達標日 2026-06-08、#3 達標日 **2026-06-24**。

---

## 6. R21 backlog（建議性，不阻塞 G0）

| # | 優先級 | 項目 | 工作量 |
|---|--------|------|--------|
| 1 | P1 | nightly END summary 加印 `mutation_unique_sha_tail7=N/7` 即時可見性 | 5 分鐘 |
| 2 | P3 | Pester 行為測試（mock Get-Command 回 $null → stage 不 crash） | 1 PD（SD_10 W0）|
| 3 | P3 | emit_real 機制 — pg-e2e fallback record 標記（紀律 #9 對稱）| 1 PD（SD_10 W0）|

---

## 7. 元數據

- 對應 PR / commit：本 commit
- 對應 tag：`v2026.05.26-01`（push 時建立）
- 紀律新增 / 修訂：紀律 #4 雙向延伸落地（無新增條款，僅實作完整化）
- 上一輪：[Round19](SD09_W3_Round19_NextAction.md)（待補檔）
- 下一輪：R21（5/27 02:00 schtasks 第 16 跑 — 軸 A 自動驗證）

**文檔元數據**：v1.0 | 建立 2026-05-26 | SD_09 W3 R20
