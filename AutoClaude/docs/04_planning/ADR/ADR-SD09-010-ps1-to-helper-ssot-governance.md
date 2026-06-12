# ADR-SD09-010 — ps1-to-helper SSOT 同構治理（PowerShell 複雜分支 Python helper 化）

| 項目 | 內容 |
|------|------|
| 編號 | ADR-SD09-010 |
| 狀態 | **ACCEPTED v1.0 — 2026-05-25 PM 拍板選項 B（SD_09 W3 Round 14 PM Agent 拍板書；三方研究 100% 共識）** |
| 提出者 | Architect + SA + SD（三方獨立研究 — SD_09 W3 Round 9~11 派工）|
| 提出日期 | 2026-05-25 |
| 對應議題 | SD_09 W3 Round 9 audit P2-R9-1 衍生 backlog（紀律 #4 延伸）|
| 相依 ADR | [ADR-SD09-007](ADR-SD09-007-hook-governance.md)（Hook Governance — 驗證鏡子要被驗證）/ [ADR-SD08-001](ADR-SD08-001-claude-md-budget.md)（LOC tiers）|

---

## 1. 背景

`tools/run_local_nightly.ps1`（626 行）為 SD_09 觀察期 #1/#2/#3 採集主腳本，內含多段複雜 PowerShell 分支邏輯（stderr/JSON 拆分、mutmut counts marker section parsing、container 選擇、drift_log 表存在性 + severity query）。**PowerShell 5.1 難以單元測試**（無原生 mock 框架；pwsh Pester 需額外環境），導致：

- W3 Round 9 audit 派工發現 F2 區塊（ps1:415-441）4 條分支（OK / ALERT / stderr / WARN）邏輯複雜但**零單元測試覆蓋**
- 已建 `tools/ac4_nightly_alert_parser.py`（134 LOC）作為 SSOT 同構樣板 + 16 case unit test（`tests/tools/test_ac4_nightly_alert_parser.py`）
- W3 Round 10 audit P2-R10-1 修復「ps1 line 440 條件 `StartsWith('{') -or StartsWith('[')` 與 helper line 51 拒絕 `[` 起點不一致」→ 證明 SSOT 同構**有實質防迴歸價值**

紀律 #4「驗證鏡子自身要被驗證」原本適用於 hook 與 validator script，本 ADR 延伸至「ps1 複雜分支也要被驗證」。

---

## 2. 三方獨立研究三選項

### 選項 A — 強制規範（≥ 4 分支必拆 helper + pre-commit hook 阻擋）

**規則**：
- 任何新增 / 修改的 ps1 區塊若條件分支數 ≥ 4 → **必須**建立 Python helper SSOT
- Helper 必須 ≥ 4 case unit test（與分支數 1:1 對應）
- ps1 端 inline 呼叫 helper（`python tools/<helper>.py`），**不可重複實作邏輯**
- `tools/hooks/check_ps1_complexity.py` 在 PostToolUse(Edit|Write) 對 `.ps1` 計算分支數，超門檻 exit 2 阻擋

**優點**：紀律 #4 全面落實；無 drift 風險。
**缺點**：(a) PowerShell 分支計數 AST parser 開發成本高；(b) 既有 ps1 改動會頻繁阻擋 → 開發節奏被打斷；(c) 對 trivial 多分支（如 5 個 elseif 的 case mapping）過度治理。

### 選項 B — 建議規範（reviewer 判斷 + checklist）

**規則**：
- ps1 新增 / 修改若涉及「外部工具輸出解析」或「跨工具回流數字」 → **建議**建 helper SSOT
- 提供 `docs/05_development/PS1_Complexity_Checklist.md`（≤ 50 行）供 PR reviewer 對照
- 觸發條件：(1) 解析 JSON / stdout-stderr 混雜；(2) 跨 stage 累計數字需 jsonl 化；(3) bitmask / regex marker section 解析；(4) ≥ 4 條件分支且涉及外部輸入
- Helper 啟用時必須 ≥ 4 case unit test（與本 ADR §2 選項 A 一致）
- 無自動阻擋；reviewer 在 PR comment 標 `requires-ps1-helper` label 觸發

**優點**：彈性高；不打斷既有節奏；契合 ADR-SD09-007 §2.2「opt-in via env」哲學。
**缺點**：依賴 reviewer 紀律；長期可能 drift（如 SD_10/SD_11 接手 reviewer 不知此規範）。

### 選項 C — 完全 helper-driven（重構 ps1 為 thin wrapper + Python 主導）

**規則**：
- 將 ps1 所有業務邏輯抽至 `tools/nightly_pipeline/`（Python module）
- ps1 退化為 ≤ 100 行 thin wrapper（僅做 env 設定 + container bring-up + 呼叫 `python -m tools.nightly_pipeline run`）
- 所有 stage 邏輯（mutation / pg-e2e / perf / drift / observability / cleanup）為 Python class

**LOC 評估**：
- 現 ps1 626 行 → 預估 thin wrapper 80~100 行；新增 `tools/nightly_pipeline/` 約 800~1000 行（含 6 stage + 1 orchestrator）
- 淨增 LOC ~300（但獲得 100% 單元測試可行性）

**風險評估**：
- 🔴 高風險：A- 治理穩定態剛達成（Round 11 首次無 P0/P1）→ 大重構必然引入新缺陷
- 🟠 中風險：Python 跨 Docker container 呼叫的 subprocess 管理比 ps1 native 複雜（如 `docker exec` stdin/stdout 編碼）
- 🟡 低風險：Windows scheduled task / schtasks 入口需同步改（仍呼叫 ps1 wrapper 即可，無破壞）

**估計工時**：≥ 4 PD（W4~W5）；需獨立 sprint 規劃。

---

## 3. 三方獨立立論

### 7.1 Architect 立論（≥ 150 字）

從**系統演化曲線**視角審視：SD_09 W3 Round 11 已達成 production-grade A 穩定態（11 輪 audit 首次無 P0/P1），此時引入**強制阻擋型治理**（選項 A）會破壞「穩定態優先」原則 — 任何新規則須等穩定態驗證 ≥ 30 天後才升級為硬性 gate（對應 ADR-SD08-005 雙軌制哲學）。選項 C「完全重構」違反 ADR-SD07-001 漸進拆解原則（SD_07 W4 已驗證 736 行 `_impl.py` 拆解過程 5 次 audit 才穩定），nightly script 重構同等風險，不應於 SD_09 觀察期啟動。**Architect 建議選項 B**：以「建議 + checklist + reviewer label」的軟治理 + 既有 SSOT 樣板（`ac4_nightly_alert_parser.py`）為示範，W4 後依漂移實況再評估升級為選項 A。同時建議在 §8 候選清單中**僅 W1 必做 1 項**（mutmut counts marker section parsing — 已被 Round 4 P0-AUDIT-R3-3 證實有迴歸風險），其餘漸進。

### 7.2 SA 立論（≥ 150 字）

從**業務需求對齊**視角分析：本 ADR 的業務目標為「降低 nightly 假綠燈污染觀察期取證」，對應紀律 #1（stage rc 區分真實失敗 vs 工具標準回報）+ 紀律 #4（驗證鏡子要被驗證）+ 紀律 #10（fallback 路徑必須可區分）。三條紀律均要求**測試覆蓋**而非「強制重構」。選項 A 過度治理（強制阻擋）會誤傷 trivial 場景如 stage rc 三態 mapping（`if rc=0/-1/2/其他`即 4 分支），但其本質為純函數無 IO，無需 helper 化。選項 C「重構為 Python 主導」會引入新的測試需求（subprocess / docker 整合測試），ROI 低。**SA 建議選項 B**，並補充：(a) checklist 必須含「是否涉及外部工具輸出解析」「是否涉及跨 stage 累計 jsonl」「是否含 regex marker section」三個觸發條件，缺一不建議；(b) 既有 ps1 改動屬 grandfather clause，不溯及既往；(c) W1 必做項以「Round 4 / Round 9 audit 已實證有迴歸風險的分支」為準，**事實驅動**而非預測驅動。

### 7.3 SD 立論（≥ 150 字）

從**技術可行性與測試覆蓋**視角評估：PowerShell 5.1 單元測試生態（Pester 5.x）需獨立安裝且 CI 配置複雜，相比 Python pytest 既有基礎設施（2,532 passed baseline）成本高 10 倍以上。選項 C 雖能 100% 解決測試覆蓋問題，但會引入「Python subprocess + Docker exec」雙重抽象層 — `docker exec autoclaude_pg psql -t -c "SELECT ..."` 改為 `psycopg.connect(dsn).execute(...)` 看似改善，實則繞過 Docker 隔離特性（需開放 PG port 5432 到 host，違反容器最小暴露原則）。選項 A 的 `tools/hooks/check_ps1_complexity.py` 需自實作 PowerShell AST parser（Python 端無成熟 library），開發成本 ≥ 1 PD 且維護成本高。**SD 建議選項 B**：以既有 `ac4_nightly_alert_parser.py` 為「示範樣板」（reference implementation），W1 補建 `mutmut_counts_parser.py`（最高 ROI — 對應 Round 4 P0-AUDIT-R3-3 真實迴歸），W2~W3 評估其他候選；checklist 由 reviewer 在 PR 對照判斷，不引入新工具鏈。

### 7.4 三方共識

**三方一致建議選項 B**（建議規範 + checklist + reviewer label）；W1 必做 1 項（mutmut counts marker section parsing — 既有迴歸實證）；W2~W6 漸進評估。

---

## 4. 候選 ps1 分支盤點（≥ 4 條件分支 + 涉及外部輸出）

| # | 區塊 | 行號 | 分支數 | 觸發條件 | 已有 SSOT helper | W1 必做 | 備註 |
|---|------|------|-------|---------|------------------|--------|------|
| 1 | F2 區塊 ac4 alert parser | 415-441 | 4（OK/ALERT/stderr/WARN）| stderr/JSON 拆分 + ConvertFrom-Json + ready_for_labeled_pr 判定 | ✅ `ac4_nightly_alert_parser.py`（16 case test）| 已完成 | Round 9 P2-R9-1 已修 |
| 2 | mutmut counts marker section | 337-358 | 4（inSection start / end / counts line match / no marker WARN）| Regex `^---\s*mutmut full counts...---\s*$` + 5 type Killed/Survived/... line match + emitted=0 WARN | ❌ 缺 | ✅ **W1 必做** | Round 4 P0-AUDIT-R3-3 已修「regex 過寬」迴歸 → 高 ROI |
| 3 | Container 選擇 + pg_isready retry | 199-246 | 5（docker info / existing 沿用 / 新建 / 30 次 pg_isready retry / lastPgError WARN）| `docker ps --filter` parsing + 30 次 retry exit code | ❌ 缺 | 否（W3 評估）| Round 5 一致性已修 `$script:` 前綴；外部依賴 docker exec 不易 mock |
| 4 | mutation Stage 1 完整 pipeline | 270-359 | 6（DockerOK / validateRc / exitClassifyRc / dockerRc!=0 / log Test-Path / counts emit）| docker rc + validate + classify + counts | 部分（`validate_mutmut_log.py` / `mutmut_exit_code.py`）| 否（W2 評估補頭尾）| 已部分 helper 化；核心 docker run 不易 mock |
| 5 | drift_log 表存在性 + severity query | 511-566 | 5（DockerOK / psqlRc / tableExists / cntRc / n>0 ERROR）| `psql -t -c "SELECT EXISTS..."` parsing + severity count parsing | ❌ 缺 | 否（W3 評估）| Round 3 P1-3 已修 rc 語意；外部 psql exec 不易 mock |
| 6 | END observation progress jsonl count | 607-616 | 4（4 個 jsonl 路徑分別 Count-JsonlLines）| Get-Content + Where-Object Trim filter | ❌ 缺 | 否（純 IO 統計，trivial）| Round 5 P1-2 新增；無迴歸風險 |

**候選總數：6 處**（其中 1 處已完成 SSOT 化、1 處 W1 必做、3 處 W2~W3 評估、1 處 trivial 不需治理）。

---

## 5. W1+ 落地排程

| Wave | 動作 | 對應候選 # |
|------|------|---------|
| **W1（必做）** | 建立 `tools/mutmut_counts_parser.py`（≤ 100 LOC）+ ≥ 6 case unit test（marker section start/end / 5 type counts line / no marker WARN / 偽造 backlog 路徑拒絕）；ps1 line 337-358 改 inline `python tools/mutmut_counts_parser.py mutation_token_guard.log` | #2 |
| **W1（必做）** | 建立 `docs/05_development/PS1_Complexity_Checklist.md`（≤ 50 行）+ 三條觸發條件（外部工具輸出解析 / 跨 stage jsonl / regex marker section）| 治理文件 |
| **W2** | 評估候選 #4 mutation pipeline 頭尾（DockerOK 判斷 + log Test-Path emit）拆 helper 可行性；現已 partial（validate + classify）| #4 |
| **W3** | 評估候選 #3 container 選擇邏輯（建 `tools/docker_container_selector.py` 純函數 — 接 `docker ps` 字串輸出 → 回 (sour=existing|ephemeral)） | #3 |
| **W3** | 評估候選 #5 drift_log severity query parsing（建 `tools/drift_log_query_parser.py` 純函數 — 接 psql `-t -c` 輸出 → 回 (exists, severity_count)） | #5 |
| **W4+** | 依 W1~W3 評估結果決定：(a) 維持選項 B 軟治理；(b) 升級為選項 A 強制阻擋；(c) 啟動選項 C 重構 | — |
| **Backlog NOTE** | tools/run_local_nightly.ps1 含 9 處 `2>&1` PowerShell 5.1 native command redirect（W3 Round 15 audit P2-2）— 對 native exe stderr wrap 成 NativeCommandError 物件，set $?=$false。穩定態下不影響 nightly 行為，但若 W4+ 啟動選項 C 重構，應統一改為分離 stdout/stderr + temp file 模式。屬既有風格，本 W1 不修。 | — |

---

## 6. 風險與緩解

| 風險 | 嚴重 | 緩解 |
|------|------|------|
| Helper 與 ps1 邏輯 drift（修一邊忘另一邊）| 🔴 | helper docstring 強制要求「ps1 行號 + 同步紀律」；參考 `ac4_nightly_alert_parser.py` line 7-13 範例 |
| reviewer 不知此規範（紀律漂移）| 🟠 | `docs/05_development/PS1_Complexity_Checklist.md` 在 PR template 引用 |
| W1 必做 helper 增加 nightly 啟動延遲 | 🟡 | helper 須 ≤ 100 LOC + 純函數 + 啟動 < 50ms（pytest assertion 把關）|
| 既有 ps1 改動誤觸 grandfather clause | 🟡 | checklist 明訂「僅新增 / 邏輯實質變動觸發」；trivial typo / 註釋修改不觸發 |
| 選項 B 長期 drift → SD_10/SD_11 接手不知規範 | 🟠 | W3 末再評估是否升級為選項 A（事實驅動 — 採樣 drift 次數）|

---

## 7. 簽核

| 角色 | 狀態 | 日期 | 摘要 |
|------|------|------|------|
| Architect | ✅ 立論完成 | 2026-05-25 | 建議選項 B；穩定態優先，漸進升級 |
| SA | ✅ 立論完成 | 2026-05-25 | 建議選項 B；事實驅動 W1 必做 1 項 |
| SD | ✅ 立論完成 | 2026-05-25 | 建議選項 B；既有 helper 為示範樣板 |
| PM | 🟡 待拍板 | — | 待 user 簽核選項 A/B/C |

---

## 8. 相關文件

- [ac4_nightly_alert_parser.py](../../tools/ac4_nightly_alert_parser.py) — SSOT 同構樣板（W3 Round 9 已落地）
- [test_ac4_nightly_alert_parser.py](../../tests/tools/test_ac4_nightly_alert_parser.py) — 16 case unit test 示範
- [run_local_nightly.ps1](../../tools/run_local_nightly.ps1) — 對應 ps1 主腳本（626 行；本 ADR 不變動）
- [ADR-SD09-007](ADR-SD09-007-hook-governance.md) — Hook Governance（紀律 #4 SSOT 一致性檢查源頭）
- [ADR-SD08-001](ADR-SD08-001-claude-md-budget.md) — LOC tiers（helper 必須 ≤ 250 plugin_entry）
- [SD09_W3_Round9_NextAction.md](../../05_development/SD09_W3_Round9_NextAction.md) — P2-R9-1 派工源頭

---

**文檔元數據**：v0.1 PROPOSED | 建立 2026-05-25（SD_09 W3 Round 11 收尾派工 — Architect+SA+SD 三方獨立研究）| 待 PM 拍板選項 A/B/C | W1 預計落地 mutmut_counts_parser.py
