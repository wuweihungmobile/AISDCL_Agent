# AutoSDD_improving_16 — 第 16 輪迭代（B 軌：規則自演化 meta-loop L4→L5）

> **輪次**：16（**B 軌「規則自演化」L5 信號**，按需）
> **日期**：2026-06-15
> **🔴 人類舵手 signoff（兩段）**：① 方向＝「B 軌→L5 規則自演化 meta-loop」；② scope＝「Block-1 + Block-3（自動提議 ＋ 自動採納守門）」。Block-2（`trust_level` 升級）維持 🔴 人工＝**守界**。
> **驅動**：成熟度 rubric SSOT `L_合體 = min(A,B,C)`；三軸 improving_15 後**首次同處 L4 信號帶**（A=L4／B=L4／C=L4），無單一瓶頸 → 本輪起 L4→L5 戰役，攻 B 軸（規則自演化）。
> **零退化基線（階段一實測，2026-06-15）**：AutoClaude **3112 passed / 122 skipped / 0 failed**（104.91s）；lint **8 kept / 0 broken**；ci-gate 雙軌 **exit 0**（v0.01:1478 / v0.06:1508 / scripts/tests:25）；框架最新 **v0.06**。
> **XAI Turn 疊加**：本輪 B 軌觸及 meta⁸（`meta_halt` ChurnBounded/GraduationRatchet 良基終止、`operator_recursion_genesis` well-founded ranking）→ 疊加「首席 AI 自動化架構師」可解釋性視角。driver instance：**ACT-028-L5 / R-9.24（規則自演化在環上守界）**。

---

## 1. 階段一：Zero-Trust 重偵察（B 軸 L5 機制實測）

派獨立 Explore agent 戴 zero-trust 帽實測 B 軸「規則自演化 meta-loop」真實級別，**禁宣稱、引 file:line**。

### 1.1 三軸現級（rubric SSOT `AutoSDD_Maturity_Rubric.md`）
| 軸 | 級別 | 證據 |
|----|------|------|
| C 引擎（AutoClaude） | **L4**（萌 L5） | Minimax CORRECTION 有界重試 + `require_evolution_signoff`（improving_13）|
| A 協作（橋接） | **L4 信號** | improving_13/14 多-AC e2e + meta⁸ 拓樸橋接 |
| **B 流程（SDD）** | **L4 信號** | improving_15 auto_recovery 接入主迴圈（flag-gated）|

→ `L_合體 = min = L4`（萌 L5）。**三軸首次同處 L4，無單一瓶頸** → 本輪起 L4→L5 戰役（須三軸同升趨穩，本輪攻 B）。

### 1.2 B 軸卡 L4→L5 的精確根因（實測，鏡像 improving_15 auto_recovery 模式）
rubric **L5 判準**＝「**自演化／元學習在環上守界**」：系統能自動從失敗中學習、提出規則修正、有界地納入，人僅在守界閘介入。對比 L4＝有界自動重試/修正但**規則本身不演化**。

框架**已具 L5 機制全套骨架**，但**生產碼零自動觸發（proposal-only）**——與 improving_15 的 `auto_recovery` 逐字鏡像：
- **SLV 合成器**：`slv_generator.propose_slv_from_fpl()`（[slv_generator.py:263](../../AISDLC_SDD/AISDLC_SDD_v0.06/tools/fsm_runtime/slv_generator.py)）—— 從 FPL 合成 `trust_level: proposed` 草案規則。**呼叫點實測：FSM 主迴圈零呼叫**，僅 CLI（`slv_generator.py:501`）＋ 測試 ×4。
- **學習層狀態機**：`enter_learning_commit()`（[fsm_runtime.py:797](../../AISDLC_SDD/AISDLC_SDD_v0.06/tools/fsm_runtime/fsm_runtime.py)）／`exit_learning_commit()`（:844）—— **生產碼零自動觸發**，僅測試呼叫。
- **採納守門（Block-3，已存在）**：`exit_learning_commit("approved")` 採納前**已**經 `_record_learning_rule_adoption`（:953）→ `meta_halt_monitor` ChurnBounded/GraduationRatchet 守門，違反導 ESCALATION（[fsm_runtime.py:927-941](../../AISDLC_SDD/AISDLC_SDD_v0.06/tools/fsm_runtime/fsm_runtime.py)）。**Block-3 守門已內建**。
- **採納紅線（Block-2，已守）**：`exit_learning_commit("approved")` 強制 `trust_level=verified` ∧ `reviewed_by` 非空（[fsm_runtime.py:896-905](../../AISDLC_SDD/AISDLC_SDD_v0.06/tools/fsm_runtime/fsm_runtime.py)），對應 R-9.11「proposed 規則永不自動升級」。

**斷點（卡 L4，精確 file:line）**：`exit_production_behavioral_signal("learn")`（[fsm_runtime.py:2204](../../AISDLC_SDD/AISDLC_SDD_v0.06/tools/fsm_runtime/fsm_runtime.py)）`learn → LEARNING_COMMIT (divergence accumulated into FPL draft)` —— **只 `self.transition("LEARNING_COMMIT")`，不 draft SLV、不填 `learning_commit_tracking`**。後果有二：
1. 即使系統因發布後行為漂移自動進 LEARNING_COMMIT，**仍須人手動跑 `/slv-generator propose <fpl_id>`** 才有草案 → 迴圈不自走 = L4。
2. learn 路徑未填 `learning_commit_tracking.proposed_rule_path`，致後續 `exit_learning_commit("approved")` 因 [fsm_runtime.py:874-878](../../AISDLC_SDD/AISDLC_SDD_v0.06/tools/fsm_runtime/fsm_runtime.py) raise（learn→approve 鏈本身斷裂的潛在缺陷，見 §3.3 DEF-16-001）。

### 1.3 紅線對齊（三斷點 vs B 軌紅線）
| 斷點 | 處置 | 紅線 |
|------|------|------|
| ① SLV proposal 未自動觸發 | **本輪接入（W-16-1）** | 草案維持 `trust_level: proposed`（R-9.11），不違反 |
| ② trust_level proposed→verified | **維持 🔴 人工**（不動） | R-9.11／R-9.20「proposed 永不自動升級」＝rubric「L5 在環上**守界**」之守界本身 |
| ③ 採納守門 | **已內建，本輪補 L5 可量測信號 + XAI 良基終止可解釋性（W-16-2）** | R-9.24 meta_halt ChurnBounded/GraduationRatchet（不弱化）|

### 1.4 TLA 影響面（決定免五軌 TLC）
- 觸發點 `exit_production_behavioral_signal` **既有 happy-path 轉換** `PRODUCTION_BEHAVIORAL_SIGNAL → LEARNING_COMMIT`（learn 分支既有、測試已綠 ⇒ 邊已在 `_HAPPY_PATH` 與 `*.tla`）。
- 本輪 W-16-1 **只在轉態之後加 side-effect**（draft proposed 規則 + 填 tracking），**零新增 reachable 邊、零狀態宇宙變更、零 `_HAPPY_PATH`/`*.tla` 變更** → 依 Rule 9.18.1 **免五軌 TLC**（比 improving_15 更強：連觸發者狀態邊都不動，純加非轉態 side-effect）。W-16-2 為純讀度量，零轉換。
- 結案前以 `diff v0.06 v0.07` 之 `transition_rules.py` + 全 5 `*.tla` **逐位元零差異** 佐證。

### 1.5 硬閘
AutoClaude 基線 **3112 / 0 failed**（＝floor，無退化）→ **通過**，准進階段二。

---

## 2. 階段二：增量設計（W-16-1 + W-16-2）

> **升級槓桿**：把既有 `propose_slv_from_fpl`（合成 proposed 草案，R-9.11 守界）從「proposal-only / 手動 CLI」**接入 `exit_production_behavioral_signal("learn")` 主迴圈**，使行為漂移累積成 FPL 後**自動 draft 候選規則待人審**（B L4→L5 信號）。**flag-gated 預設 OFF＝零退化**（同 improving_15 `SDD_ENABLE_AUTO_RECOVERY`、C 軸 `enable_kernel_brain`/`require_evolution_signoff` 三前例）。

### 2.1 介面 delta（v0.07，Copy-on-Evolve 自 v0.06）

`tools/fsm_runtime/fsm_runtime.py`（凍結本體 → 走 Copy-on-Evolve）：

**W-16-1 — Block-1 自動提議接入**：
- module 常數 `_SLV_AUTO_PROPOSE_ENV = "SDD_ENABLE_SLV_AUTO_PROPOSE"` + 純函式 `_slv_auto_propose_enabled()`（讀環境變數開關，符 SDD 慣例 `SDD_ENABLE_AUTO_RECOVERY`/`SDD_PROJECT`/`SDD_RUN_TLC`…；FSMRuntime.__init__ 無 config 物件，沿用 improving_15 env-flag 慣例）。
- 新 staticmethod `_auto_draft_slv(fpl_id) -> dict`（純合成，不轉態）：`load_fpl_entry(fpl_id)` → `propose_slv_from_fpl(fpl)` → `write_rule_candidate(cand)`（落 `trust_level: proposed`）→ 回 `{slv_id, rule_path, trust_level:"proposed"}`。**fail-closed**：FPL 缺/合成失敗/落盤失敗一律 raise（呼叫端據此標記不 draft、不偽造）。
- `exit_production_behavioral_signal()` 新增 optional `fpl_id: Optional[str] = None`；**learn 分支**轉態到 LEARNING_COMMIT **後**：`if decision=="learn" and _slv_auto_propose_enabled() and fpl_id:` → **try** `_auto_draft_slv(fpl_id)` → 把 `{fpl_id, proposed_slv_id, proposed_rule_path, review_status:"pending", entered_from:"PRODUCTION_BEHAVIORAL_SIGNAL"}` 寫入 `learning_commit_tracking`（鏡像 `enter_learning_commit` 的 tracking setup，**同時順帶修 §3.3 DEF-16-001 鏈斷裂**）+ `result["auto_slv"] = {...}`；**except** → `result["auto_slv"] = {"proposed": False, "error": ...}`，**停在 LEARNING_COMMIT 不偽造草案**（fail-closed，紅線：人仍可手動 propose）。
- 預設 OFF（flag 未設）或 `fpl_id` 缺 → learn 分支行為**逐字同 v0.06**（純轉態）＝零退化。

**W-16-2 — Block-3 L5 可量測信號 + XAI 良基終止可解釋性**：
- 新 method `learning_loop_stats() -> dict`（純讀，零副作用、零轉態）：自既有 `learning_commit_tracking.proposals_history` + meta-loop ledger 計算 L5 信號——`auto_proposed`（auto_slv 成功數）、`human_approved`、`auto_adopted`（approved ∧ meta_halt 放行）、`churn_blocked`（meta_halt 攔截導 ESCALATION 數）、`unattended_proposal_rate`（auto_proposed / 漂移事件）。**度量穩健**：零事件不除零（回 0.0）。
- XAI Turn：`learning_loop_stats()` 額外輸出 `termination_certificate` 區塊——把 `meta_halt` 的 ChurnBounded（每指紋 churn ≤ `churn_max()` clamp[1,5] 預設 2）與 GraduationRatchet（單調棘輪）狀態，轉成人類舵手可一眼看懂的「良基終止證書」摘要（鏡像既有 R-9.37 拓樸儀表板的良基 ranking 呈現原則，**純讀、不渲染大圖、不碰 meta-oracle**）。

### 2.2 LOC 預算落點
`fsm_runtime.py` 為 runtime facade（非 plugin_entry/data 分級）；W-16-1 ~35 行（1 helper + learn 分支 wiring + flag 純函式）、W-16-2 ~30 行（1 純讀 method）。AutoClaude 側 LOC budget 不涵蓋 SDD 框架；SDD 側 `arch_fitness` 無逐檔 LOC 硬閘。檔案總行數仍遠低於框架既有規模，無 LOC violation。

### 2.3 .importlinter 影響
本輪零觸 AutoClaude（`autoclaude/`）→ AutoClaude `.importlinter` 8 contract 不受影響。SDD 框架不在 AutoClaude import-linter 管轄。

### 2.4 checkpoint additive
W-16-1 寫 `learning_commit_tracking`（既有 dict，improving_15 前即存在；新增鍵為 additive）；W-16-2 純讀既有 `proposals_history` + ledger，零新增持久化欄位、零 schema 變更。DAL 三後端不涉（SDD 框架自有 `save_state`）。

---

## 3. 階段三：實作與雙重驗證

### 3.1 W-16-1 落地（見 §2.1）
flag OFF 既有 `test_production_behavioral`/`test_learning_commit`/`test_slv_generator` 零退化（編譯 + 單測，Rule 4）。

### 3.2 閉環自走測試（`tests/test_slv_auto_propose_wiring.py`，預估 9 case）
| case | 驗證 |
|------|------|
| flag off + learn 純轉態 LEARNING_COMMIT 無 auto_slv 鍵 | 零退化（v0.06 行為） |
| flag off + 有 fpl_id 仍純轉態 | flag 為唯一開關 |
| flag on + learn + fpl_id → auto draft proposed + 填 tracking | L5 自走（不再需手動 CLI） |
| flag on + draft 後 `exit_learning_commit("approved")` 鏈通（先人工升 verified）| 紅線守界：人 verify 後鏈閉合 |
| flag on + 未升 verified 即 approve → raise | Block-2 紅線（proposed 不自動採納） |
| flag on + FPL 不存在 → fail-closed 停 LEARNING_COMMIT 無偽造 | fail-closed |
| flag on + 合成失敗（FPL 缺 qualifier）→ fail-closed | fail-closed |
| draft 規則 trust_level 恆 proposed + reviewed_by null | R-9.11 守界 |
| learning_loop_stats 零事件不除零 + 有事件正確計數 | L5 信號度量穩健（W-16-2）|

### 3.3 B 軌 dogfooding 新發現缺陷 → 即記即修
**DEF-16-001（P2，本輪即修）**：`exit_production_behavioral_signal("learn")` 轉 LEARNING_COMMIT 但**不填 `learning_commit_tracking`**，致 learn→`exit_learning_commit("approved")` 因缺 `proposed_rule_path` 在 [fsm_runtime.py:874-878](../../AISDLC_SDD/AISDLC_SDD_v0.06/tools/fsm_runtime/fsm_runtime.py) raise ValueError ＝ **learn 採納鏈結構性斷裂**。本輪 W-16-1 接入 auto-draft 時順帶填 tracking 即修復（判為完成 W-16-1 必要部分，非新 scope）；flag OFF 時仍維持 v0.06 行為（斷裂留存但與 v0.06 一致、零退化），flag ON 時鏈閉合。詳見 Defect_Log。

### 3.4 Copy-on-Evolve v0.06 → v0.07
用共享 infra `scripts/copy_on_evolve.sh`（improving_12 建、improving_15 dogfood 硬化）；`.gitignore` 比照既有 negate FSM-STATE-TEMPLATE.yaml（DEF-15-001 已固化）；`EVOLUTION_LOG.md` + `releases/CHANGELOG.md` v0.07 段；`arch_fitness` FF-17 自證 v0.07 入閘。

---

## 4. 階段四：零退化驗證矩陣（全項實測，待執行）

| 檢查 | 命令 | 通過條件 |
|------|------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3112 / 0 failed（floor 持平，本輪零觸 AutoClaude） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | 雙軌 exit 0（v0.01 + v0.07 + scripts/tests）|
| 五軌 TLC | N/A（§1.4：零 `_HAPPY_PATH`/`*.tla` 變更，diff 逐位元零差異佐證）| — |

---

## 5. <Architecture_Design_Review>（寫實質 Python 前必輸出）

1. **架構純潔性**：W-16-1 為 `fsm_runtime.py` runtime facade 既有方法的 additive 分支 + 1 staticmethod helper，**無 God-object**；不新增狀態、不改轉換圖。`propose_slv_from_fpl`/`write_rule_candidate` 既有純函式，wiring 只「呼叫」不「重寫」（鏡像 improving_15 接入 `enter_auto_recovery` 模式）。Thin Facade 維持。
2. **持久化相容**：`learning_commit_tracking` 為既有 dict，新增鍵 additive 寫入；W-16-2 純讀。SDD `save_state` 既有路徑，零 schema 變更。AutoClaude DAL 三後端不涉。
3. **安全防護網（CONDITIONAL）**：本輪零新增「從文件生成指令」路徑；SLV 草案是 YAML 規則資料（`trust_level: proposed`），非可執行指令，不經 CONDITIONAL 消毒路徑。
4. **對外 I/O 安全**：本輪零新增 `ToolInvocationPort` 外呼路徑（純框架內 FSM + 本地 YAML 落盤）。N/A。
5. **紅線守界專章（B 軌）**：① 草案恆 `trust_level: proposed`（R-9.11）；② `trust_level` 升 verified 維持 🔴 人工（不動 `exit_learning_commit` 的 verified 強制檢查）；③ 採納經 `meta_halt_monitor` ChurnBounded/GraduationRatchet（R-9.24，不弱化）；④ fail-closed：auto-draft 任何失敗停在 LEARNING_COMMIT 不偽造；⑤ flag 預設 OFF 零退化；⑥ 免五軌 TLC 有 diff 逐位元零差異硬證據。

---

## 6. XAI Turn 藍圖 + GitHub Issue 規格草案（driver instance：ACT-028-L5 / R-9.24）

<thinking>
**可解釋性轉向深度推理**：B 軸規則自演化 meta-loop 的「良基終止」不在 operator-genesis 的呼叫圖 rank，而在 **meta_halt 的 ChurnBounded（每指紋再採納 churn ≤ `churn_max()` clamp[1,5] 預設 2）＋ GraduationRatchet（單調棘輪：退役指紋無 capability-delta 不得 re-adopt）**——這正是「自演化在環上守界」的良基測度：churn 計數器嚴格有界遞減 ⟹ add↔retire 抖動不可能無限。人類舵手須一眼看懂「這條規則被自動提議、我審了、採納時 churn 還剩多少額度、會不會 A→B→A 震盪」。

**漏洞挖掘**：① 認知超載——auto-draft 大量 proposed 規則淹沒人類審批佇列 → 須折疊/批次/critical-path（標 churn 將耗盡的指紋）。② 狀態漂移四源一致——(1) TLA `meta_halt` INVARIANT、(2) `meta_halt_monitor.py` 執行邏輯、(3) `learning_loop_stats` 渲染、(4) `FSM-STATE.yaml` `learning_commit_tracking` 真相，杜絕「畫的採納證書跟跑的 churn 帳本不一樣」。③ 視覺欺騙——`learning_loop_stats` 的 termination_certificate 須獨立從 ledger 重算 churn，不盲信標籤（鏡像 improving_14 adapter digest 重算防偽）。
</thinking>

- **儀表板架構與資料流**：`learning_loop_stats()`（W-16-2，純讀）→ 輸出 `{proposals, adoption_rates, termination_certificate}`；termination_certificate 自 meta-loop ledger **獨立重算** churn/graduation（不盲信），對齊既有 R-9.37 拓樸儀表板「AST 同構純投影」原則。
- **視覺化與降維**：Markdown 表 + 每指紋 churn 階梯（剩餘額度），⛔ 標 churn 將觸頂（將被導 ESCALATION）之指紋＝critical path；有界截斷 + 分頁（防 proposed 規則洪流 token 爆炸）。
- **TLA 不變量擴充評估**：**沿用既有** `meta_halt` ChurnBounded/GraduationRatchet INVARIANT（補 META_FSM 不增軌），**無需新 `VisualizationBounded` 證明**（本輪僅純讀統計，不渲染遞迴大圖；若未來擴為互動儀表板再評估）。
- **完整 DoD**：(技術) W-16-1 auto-draft flag-gated + fail-closed + 9 case 綠；(形式化同構) diff v0.06↔v0.07 `*.tla` 逐位元零差異 + `learning_loop_stats` churn 重算與 ledger 一致；(Token 預算稽核) 純讀統計零渲染大圖；(UI/UX 審批) termination_certificate 人類舵手可一眼判讀 churn 剩餘額度與震盪風險 → 供 steersman signoff。

> **GitHub Issue 規格草案**（供掌舵者 signoff）：標題「[L5/B-axis] Wire SLV auto-propose into LEARNING_COMMIT main loop with bounded self-evolution + human gate」；Labels：`maturity:L5`、`track:B`、`xai-turn`、`red-line:human-gate`；DoD 如上；驗收＝flag ON 端到端「漂移→auto-draft proposed→人 verify→meta_halt 守門採納」鏈閉合，flag OFF 零退化。

---

## 7. RTM（需求追溯矩陣）

| W 項 | 需求（rubric/北極星） | 介面 delta | 測試 | 紅線 |
|------|----------------------|-----------|------|------|
| W-16-1 | B L4→L5：規則自演化自動提議在環（§北極星2 圖靈完備閉環）| `_slv_auto_propose_enabled` + `_auto_draft_slv` + `exit_production_behavioral_signal(fpl_id=)` learn 分支 | test_slv_auto_propose_wiring 1-8 | R-9.11 proposed 守界 + fail-closed + flag OFF 零退化 |
| W-16-2 | L5「在環上守界」可量測信號 + XAI 良基終止可解釋 | `learning_loop_stats()` | test_slv_auto_propose_wiring 9 | R-9.24 meta_halt 不弱化、純讀不碰 meta-oracle |
| DEF-16-001 | learn 採納鏈結構性斷裂（即修）| W-16-1 填 tracking 順帶修 | case 4（learn→approve 鏈通）| 同 W-16-1 |

---

## 8. 成熟度誠實聲明（zero-trust，沿用 improving_15 紀律）

本輪交付 B 軸「**L5 能力 ＋ 測試證據**」：flag 預設 **OFF ＝ 預設仍 L4**（零退化）、L5 為**可啟用能力**、**運行達標須生產啟用 `SDD_ENABLE_SLV_AUTO_PROPOSE` 後累積** auto-draft→人 verify→採納 的真實證據。**不虛報運行已達 L5、不躍報 `L_合體` 升級**——`L_合體` 維持 **L4 信號邊界**（A/B/C 皆 L4；B 取得 L5 信號但需三軸同升 + 運行累積方推 `min` 上移）。Block-2（trust_level 人工升級）為**永久守界**，非待移除的過渡——「L5 在環上守界」的守界本身即人類掌舵點。
