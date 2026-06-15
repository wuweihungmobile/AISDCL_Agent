# AutoSDD_improving_15 — 第 15 輪迭代（B 軌：流程自治 L3→L4）

> **輪次**：15（**B 軌「流程自治」升級**，按需）
> **日期**：2026-06-15
> **🔴 人類舵手 signoff**：方向「B 軸：流程自治升級（攻瓶頸）」→ scope「核定 W-15-1 接入 auto_recovery 升 B 軸 L4」
> **驅動**：成熟度 rubric SSOT 實測 `L_合體 = min(A,B,C)` 之**唯一瓶頸＝B 軸 L3**（A/C 皆 L4）；本輪攻 B。
> **零退化基線（階段一實測）**：AutoClaude **3112 passed / 122 skipped**；lint 8/0；ci-gate 雙軌 exit 0（v0.01:1478 / v0.05:1499 / scripts/tests:24）；框架最新 **v0.05**。

---

## 1. 階段一：Zero-Trust 重偵察（B 軸成熟度實測）

派獨立 Explore agent 戴 zero-trust 帽實測 B 軸（SDD 流程自治）真實級別，**禁宣稱、引 file:line**：

### 1.1 三軸現級（rubric SSOT `AutoSDD_Maturity_Rubric.md`）
| 軸 | 級別 | 證據 |
|----|------|------|
| C 引擎（AutoClaude） | **L4**（萌 L5） | Minimax CORRECTION 有界重試 + `require_evolution_signoff`（improving_13 補）|
| A 協作（橋接） | **L4 信號** | improving_13/14 多-AC e2e + 拓樸橋接 |
| **B 流程（SDD）** | **L3** | ↓ 見 1.2 |

→ `L_合體 = min = L3`（萌 L4），**唯一瓶頸＝B 軸**。

### 1.2 B 軸卡 L3 的精確根因（實測）
- rubric **L4 判準**＝「自動執行＋自動重試/有界修正，人僅在 escalation 介入」；**L3**＝「每關卡需人確認/修正才前進」。
- 框架**已具 L4 機制骨架**：`tools/fsm_runtime/auto_recovery.py` 完整實作 Rule 9.14 有界 1-shot 自癒（≤3/session、≤1/同因、structural 禁、失敗→ESCALATION_FINAL）+ `diagnostic.py` 分類 + `FSMRuntime.enter_auto_recovery()`（`fsm_runtime.py:533-622`，ESCALATION→AUTO_RECOVERY_ATTEMPT）。
- **斷點（卡 L3 真因）**：`enter_auto_recovery()` **生產碼零呼叫**（grep 僅測試呼叫）。`record_gate_result()`（`fsm_runtime.py:227-258`）達 `escalate=True` 時**直接 `record_escalation()` 停機等人**，從不自動嘗試恢復 → 失敗即停（L3），非自動有界恢復（L4）。
- 紅線全部遵循（HUMAN_PENDING gate、ESCALATION 後不自動恢復屬 Rule 9.14 有界例外、structural 禁、有界 retry 皆在）。

### 1.3 TLA 影響面（決定免五軌 TLC）
- `SDD_FSM.tla:439-441` 已模型化 `T_EnterAutoRecover: state="ESCALATION" → "AUTO_RECOVERY_ATTEMPT"` + `recovery` 計數器（:40）+ `T_AutoRecoverFail`/`T_EscToFinalAtLimit`。
- `_HAPPY_PATH` 已含 `ESCALATION → {AUTO_RECOVERY_ATTEMPT, ESCALATION_FINAL}`（`transition_rules.py:148-151`）。
- → **本輪只改 Python「觸發者」（手動→自動），不新增 reachable 邊、不改狀態宇宙** → 依 Rule 9.18.1 **免五軌 TLC**；既有證明維持有效。

### 1.4 硬閘
AutoClaude 基線 **3112 / 0 failed**（≥上輪、無退化）→ 通過，准進階段二。

---

## 2. 階段二：增量設計（W-15-1）

> **升級槓桿**：把既有 `enter_auto_recovery`（Rule 9.14 有界、TLC 已證有界停機）從「proposal-only / orchestrator 手動觸發」接入 `record_gate_result` 主迴圈，使 gate retry 耗盡時**自動有界恢復**（B L3→L4）。**flag-gated 預設 OFF＝零退化**（同 C 軸 `enable_kernel_brain`/`require_evolution_signoff` 雙前例）。

### 2.1 介面 delta（v0.06，Copy-on-Evolve 自 v0.05）
`tools/fsm_runtime/fsm_runtime.py`：
- `import os`（新）+ module 常數 `_AUTO_RECOVERY_ENV="SDD_ENABLE_AUTO_RECOVERY"` + 純函式 `_auto_recovery_enabled()`（讀環境變數開關，符 SDD 慣例 SDD_PROJECT/SDD_RUN_TLC…；FSMRuntime.__init__ 僅收 state、無 config 物件）。
- `record_gate_result()` escalate 分支：`record_escalation(esc_reason)` 後，`if _auto_recovery_enabled() and self._gate_is_resumable(gate)` → `payload["auto_recovery"] = self.enter_auto_recovery(escalation_reason=(reason or esc_reason), resume_state=gate)`，**try/except fail-closed**（任何例外停在 ESCALATION）。以**實際失敗 reason** 作 diagnose 依據（非 gate-exhaust 格式字串，否則恆判 structural）。
- `_gate_is_resumable(gate)`（staticmethod，新）：預檢 gate ∈ `auto_recovery._GATE_RESUMABLE_TARGETS`，防 enter_auto_recovery 先轉態再於 record_attempt_start raise 致 AUTO_RECOVERY_ATTEMPT 撕裂態。RETRY_LIMITS 4 gate 全在白名單，此為防護。
- `auto_recovery_stats()`（新，純讀）：L4 可量測信號——recovery_success_rate（successes/attempts）、unattended_recovery_rate（successes/escalations）。

### 2.2 LOC 預算落點
fsm_runtime.py 為 runtime facade（非 plugin_entry/data 分級）；新增 ~45 行（3 helper + escalate 分支 wiring + 註解），檔案總行數仍遠低於框架既有規模，無 LOC violation（AutoClaude 側 LOC budget 不涵蓋 SDD 框架；SDD 側 arch_fitness 無逐檔 LOC 硬閘）。

### 2.3 .importlinter 影響
本輪零觸 AutoClaude（`autoclaude/`）→ AutoClaude `.importlinter` 8 contract 不受影響。SDD 框架不在 AutoClaude import-linter 管轄。

### 2.4 checkpoint additive
`auto_recovery_stats` 純讀既有 `recovery_state.history`（record_attempt_outcome 既有 flush），零新增持久化欄位、零 schema 變更。

---

## 3. 階段三：實作與雙重驗證

### 3.1 W-15-1 落地（見 §2.1）
flag OFF 既有 `test_auto_recovery`/`test_transitions`/`test_phase_h` **86 passed 零退化**（編譯+單測，Rule 4）。

### 3.2 閉環自走測試（`tests/test_auto_recovery_wiring.py`，9 case）
| case | 驗證 |
|------|------|
| flag off 停 ESCALATION 無 auto_recovery 鍵 | 零退化（v0.05 行為） |
| flag on transient 自動進 AUTO_RECOVERY_ATTEMPT | L4 自走（不再停等人） |
| 完整閉環 success 回 resume gate + stats | 自走無人工 + L4 信號 |
| structural → ESCALATION_FINAL（含 9.14.3 refusal） | 紅線守界 |
| bounds 耗盡 → ESCALATION_FINAL（9.14.1） | 紅線守界 |
| fail → ESCALATION_FINAL（9.14.4）+ stats | 紅線守界 |
| _gate_is_resumable 涵蓋 4 gate / 拒非白名單 | 防撕裂 |
| 空 session 零率不除零 | 度量穩健 |

### 3.3 B 軌 dogfooding 新發現缺陷 → 即記即修（見 Defect_Log DEF-15-001）
首次真實 v0.06 Copy-on-Evolve 當場揭露 `copy_on_evolve.sh` 缺陷：`tar --exclude build/reports` 誤殺 `FSM-STATE-TEMPLATE.yaml`（state_loader 必需種子模板＝真輸入），致 46+ FSM 測試全紅。**三層修復**：(1) helper 排除後補回模板；(2) `.gitignore` 比照 v0.01 negate 模板使其 tracked（兼修 v0.05 自 improving_11 起的潛在 untracked 缺陷）；(3) `test_copy_on_evolve.py` 加回歸鎖 case。fresh-checkout 模擬（只 tracked + 模板）**1507 passed**（唯 1 FF-17 失敗為 temp-dir 隔離 artifact），證模板為唯一 build/reports 源碼依賴。

---

## 4. 階段四：零退化驗證矩陣（全項實測，2026-06-15）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3112 / 0 failed | **3112 passed / 122 skipped / 0 failed**（103.96s）✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept | **8 kept / 0 broken** ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **violations=0** ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK** ✅ |
| AISDLC_SDD 雙軌 ci-gate | `bash scripts/ci-gate.sh` | exit 0 + arch_fitness<2 | **exit 0**，v0.01:1478 / **v0.06:1508** / scripts/tests:**25**（FF-17 自證 v0.06 入閘）✅ |
| v0.06 not-chaos | `pytest -m "not chaos"` | ≥1499 只增不減 | **1508 passed / 4 skipped**（1499+9）✅ |
| 五軌 TLC | （僅 FSM 變更時） | — | **N/A**（零 `.tla`/`_HAPPY_PATH` 變更，§1.3）|

**突變反偽（§5 審查另有獨立第二輪）**：`_auto_recovery_enabled` 強制 return False → 5 個 flag-on 閉環測試**轉紅**、4 個 flag-off/guard/stats 續綠（wiring 真實生效非空轉），已乾淨還原。

---

## 5. RTM（需求→實作→測試 追溯矩陣）

| AC | 需求 | 實作（file） | 測試 | 狀態 |
|----|------|-------------|------|------|
| AC-15-1 | gate retry 耗盡時，flag on 自動嘗試有界恢復（B L3→L4）| `fsm_runtime.py` record_gate_result escalate 分支 + `_auto_recovery_enabled` | test_flag_on_transient_auto_enters_recovery / test_full_closed_loop_success_resumes_gate | ✅ |
| AC-15-2 | 預設 OFF 零退化（v0.05 行為）| escalate 分支 flag-gated | test_flag_off_stays_escalation_no_auto_recovery / 既有 86 passed / 全套 3112 | ✅ |
| AC-15-3 | 守 Rule 9.14 紅線（structural/bounds/fail → ESCALATION_FINAL，不弱化）| enter_auto_recovery 既有守界 + try/except fail-closed | test_structural/bounds/recovery_fail → FINAL（3 case）| ✅ |
| AC-15-4 | L4 可量測信號 | `auto_recovery_stats()` | test_full_closed_loop（rate=1.0）/ test_recovery_fail（rate=0.0）/ test_stats_empty | ✅ |
| AC-15-5 | 防 resume_state 撕裂態 | `_gate_is_resumable` 預檢 | test_gate_is_resumable_covers_all / test_non_resumable_rejected | ✅ |
| AC-15-6 | 免五軌 TLC（不改狀態宇宙）| 僅改觸發者，TLA `T_EnterAutoRecover` 既存 | EVOLUTION_LOG TLC=N/A + ci-gate offline reachability 綠 | ✅ |
| AC-15-7 | DEF-15-001 三層修（dogfooding）| copy_on_evolve.sh + .gitignore negate + test case | test_preserves_fsm_state_template + fresh-checkout 模擬 1507 | ✅ |

---

## 6. <Architecture_Design_Review>（寫實質 Python 前已輸出，此處覆核）

1. **架構純潔性**：維持。無 God-object；3 helper 為 FSMRuntime 同責任內聚方法（觸發判定/預檢/純讀統計），enter_auto_recovery 既有不動；record_gate_result 仍為 thin gate-dispatch。
2. **持久化相容**：維持。`auto_recovery_stats` 純讀既有 `recovery_state.history`，零新增 checkpoint 欄位、零 schema/DAL 變更；flag OFF 時 state 演化與 v0.05 完全一致。
3. **安全防護網**：**強化**。失敗恢復走既有 Rule 9.14 有界守界（structural 禁、≤3/session、≤1/同因、失敗→ESCALATION_FINAL）；新接線 fail-closed（任何例外停 ESCALATION），預設 OFF 不改紅線；不觸 CONDITIONAL/對外 I/O（純 FSM 狀態轉換）。
4. **對外 I/O 安全**：N/A（零 `ToolInvocationPort`、零網路 I/O；auto_recovery 明載不執行 wait/rerun，留 caller）。

---

## 7. 成熟度結語（誠實，禁虛報躍升）

- **B 軸**：能力面由 L3（失敗即停等人）升至 **L4 信號**——flag-gated 自動有界恢復閉環自走 + L4 可量測信號（recovery_success_rate）已落地並經突變反偽證實非空轉。**誠實限定**：預設 OFF＝預設行為仍 L3（零退化），L4 為**可啟用能力**（同 C 軸 enable_kernel_brain 模式）；真實運行 L4 信號達標（無人工恢復率 ≥X%）須生產環境啟用後累積，本輪交付**能力與測試證據**，未宣稱「運行中已達 L4」。
- **`L_合體`**：A=L4 信號 / B=L4 信號（本輪）/ C=L4 → `min` 仍為 **L4 邊界（萌 L4→趨穩）**；**未虛報躍至 L5**（L5 需自演化/元學習在環上守界，屬後續輪）。三軸首次同處 L4 信號帶，一致性不變式 `A ≤ min(B,C)` 成立。

---

## 8. 結案四件套
1. 本檔 `docs/04_planning/AutoSDD_improving_15.md`
2. `docs/06_quality/AutoSDD_ZeroTrust_Audit_15.md`（多專家審計+複審證據）
3. `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-15-001 新增）
4. 框架 `AISDLC_SDD_v0.06/`（fsm_runtime.py + test_auto_recovery_wiring.py + EVOLUTION_LOG + CHANGELOG + UPGRADE_SOP §2.1/§5）+ 共享 infra（copy_on_evolve.sh / .gitignore / test_copy_on_evolve.py）
