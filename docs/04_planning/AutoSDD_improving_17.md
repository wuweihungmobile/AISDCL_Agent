# AutoSDD_improving_17 — 第 17 輪迭代（B 軌：鷹架代謝 GC「自動提議退役」L4→L5）

> **輪次**：17（**B 軌「鷹架代謝」L5 信號**，按需）
> **日期**：2026-06-16
> **🔴 人類舵手 signoff（兩段）**：① 放行＝「開跑 improving_17」；② 方向＝「主推 B 軌；W-17-1 GC 接主迴圈（A 主）+ W-17-2 scaffold_gc_stats XAI（C 輔）」。退役 `set_maturity(reviewed_by=)` 維持 🔴 人工＝**守界**。
> **驅動**：成熟度 rubric SSOT `L_合體 = min(A,B,C)`；improving_16 後三軸仍同處 **L4 信號帶**（B 取 L5 能力但 flag 預設 OFF＝運行仍 L4）。本輪續攻 B 軸，接「自演化的收縮側」。
> **零退化基線（階段一實測，2026-06-16）**：AutoClaude **3112 passed / 122 skipped / 0 failed**（106.27s）；lint **8 kept / 0 broken**；LOC violations=0；snapshot 新鮮；ci-gate 雙軌 **exit 0**（v0.01:1478 / v0.07:1517 / scripts/tests:25）；框架最新 **v0.07**。
> **XAI Turn 疊加**：本輪 B 軌觸及 meta 自演化「在環上守界」（Rule 9.20 鷹架代謝、`scaffold_roi` ROI 棘輪）→ 疊加「首席 AI 自動化架構師」可解釋性視角。driver instance：**ACT-055 / R-9.20（鷹架代謝在環上守界）**。

---

## 1. 階段一：Zero-Trust 重偵察（B 軸代謝機制實測）

派獨立 Explore agent 戴 zero-trust 帽實測 B 軸「鷹架代謝 GC」真實級別，**禁宣稱、引 file:line**。

### 1.1 三軸現級（rubric SSOT `AutoSDD_Maturity_Rubric.md`）
| 軸 | 級別 | 證據 |
|----|------|------|
| C 引擎（AutoClaude） | **L4**（萌 L5） | Minimax CORRECTION 有界重試 + `require_evolution_signoff` |
| A 協作（橋接） | **L4 信號** | improving_13/14 多-AC e2e + meta⁸ 拓樸橋接 |
| **B 流程（SDD）** | **L4 信號** | improving_16 SLV auto-propose 接主迴圈（flag-gated，預設 OFF＝運行仍 L4）|

→ `L_合體 = min = L4`（萌 L5）。三軸同處 L4 → 續 L4→L5 戰役，本輪攻 B 軸「代謝收縮側」。

### 1.2 B 軸代謝卡 L4→L5 的精確根因（實測，鏡像 improving_16 模式）
improving_16 接了「規則自演化—**自動提議新增**（SLV proposed）」＝自演化的「增」側。一個圖靈完備的閉環若**只能增、不能減**必單調膨脹——arch_fitness `FF-16` advisory 正揭示「**鷹架代謝 GC 從未產出退役 ROI 提案（GAP-X2 代謝肌肉從未收縮）**；Rule 9.20『大膽移除冗餘鷹架』寫進憲法卻從未行使」。本輪接其對偶＝「鷹架代謝—**自動提議退役**（SCAFFOLD-ROI proposed）」。

框架**已具代謝機制全套骨架**，但**生產碼零自動觸發**——與 improving_16 接入前 SLV 斷點逐字鏡像：
- **GC 計算層（已存在、完整）**：`scaffold_gc.run_gc()`（[scaffold_gc.py:124](../../AISDLC_SDD/AISDLC_SDD_v0.07/tools/fsm_runtime/scaffold_gc.py)）→ `compute_proposals()`（:52）算每條規則 ROI（catch/fire）並產 `RetirementProposal`，落 `build/reports/gc/SCAFFOLD-ROI-{date}.md`（:140）。**呼叫點實測：FSM 主迴圈零呼叫，僅測試 ×2**（test_phase_h / test_phase_j）。
- **代謝狀態機（已存在）**：`enter_scaffold_gc()`（[fsm_runtime.py:1495](../../AISDLC_SDD/AISDLC_SDD_v0.07/tools/fsm_runtime/fsm_runtime.py)）/ `exit_scaffold_gc()`（:1530），RELEASE→SCAFFOLD_GC→RELEASE/SPEC_DRAFTING，happy-path 既有、TLA 四源一致（H-001 修）。
- **退役紅線（Block-2，已守）**：`run_gc` 只產 `RetirementProposal` + 報告，**永不呼叫 `set_maturity`**；退役須人工 `rule_loader.set_maturity(reviewed_by=)`（[scaffold_gc.py:10-11](../../AISDLC_SDD/AISDLC_SDD_v0.07/tools/fsm_runtime/scaffold_gc.py) 安全約束），對應 R-9.20 絕對禁令 #11「自動退役 active 規則而不經 set_maturity(reviewed_by=)」。
- **ROI 計數基座（已存在）**：`rule_loader.record_fire()`（:134）填 fire/catch/false_positive 三整數，永久化回 YAML；FF-9 實測 39 條 active 規則 scaffold_roi 計數齊備（aggregate fire=0，待 runtime 累積）。

**斷點（卡 L4，精確 file:line）**：`enter_scaffold_gc()`（[fsm_runtime.py:1495](../../AISDLC_SDD/AISDLC_SDD_v0.07/tools/fsm_runtime/fsm_runtime.py)）轉態到 SCAFFOLD_GC 時**只 `setdefault("scaffold_gc_tracking")` 記 entered_at/resume_state，從不呼叫 `run_gc()` 實算 ROI 提案**。後果：即使系統週期性進 SCAFFOLD_GC observation 態，**仍須人手動跑 GC** 才有 SCAFFOLD-ROI 報告 → `build/reports/gc/` 恆空、Rule 9.20.5 從未行使 = 代謝肌肉從未收縮 = L4。

### 1.3 紅線對齊（斷點 vs B 軌紅線）
| 斷點 | 處置 | 紅線 |
|------|------|------|
| ① GC 提議未自動觸發 | **本輪接入（W-17-1）** | `run_gc` 只產提議、永不退役，不違反 |
| ② active 規則退役（set_maturity） | **維持 🔴 人工**（不動） | R-9.20 #11「自動退役 active 規則而不經 set_maturity(reviewed_by=)」＝rubric「L5 在環上**守界**」之守界本身 |
| ③ ROI 提議可解釋 | **本輪補 L5 可量測信號 + XAI 安全證書（W-17-2）** | 純讀、不碰 meta-oracle（GC 是 ROI 統計層非生成器）|

### 1.4 TLA 影響面（決定免五軌 TLC）
- 觸發點 `enter_scaffold_gc` 為既有顯式入口（顯式設 `self.state.current`，bypass happy-path，因 RELEASE 為 terminal）；其 RELEASE→SCAFFOLD_GC→RELEASE 邊已在 `_HAPPY_PATH` 與 `*.tla`（H-001 四源一致）。
- 本輪 W-17-1 **只在進態之後加 side-effect**（呼叫既有 `run_gc` + 記 report 路徑），**零新增 reachable 邊、零狀態宇宙變更、零 `_HAPPY_PATH`/`*.tla` 變更** → 依 Rule 9.18.1 **免五軌 TLC**（與 improving_16 同強度：純加非轉態 side-effect）。W-17-2 為純讀度量，零轉換。
- 結案前以 `diff v0.07 v0.08` 之 `transition_rules.py` + 全 5 `*.tla` **逐位元零差異** 佐證。

### 1.5 硬閘
AutoClaude 基線 **3112 / 0 failed**（＝floor，無退化）→ **通過**，准進階段二。✅（實測完成 2026-06-16）

---

## 2. 階段二：增量設計（W-17-1 + W-17-2）

> **升級槓桿**：把既有 `scaffold_gc.run_gc()`（產 `RetirementProposal` proposed 提議，R-9.20 守界）從「測試-only / 手動」**接入 `enter_scaffold_gc()` 主迴圈**，使系統進代謝態時**自動算 ROI 並產 SCAFFOLD-ROI 退役提議待人審**（B L4→L5 信號）。**flag-gated 預設 OFF＝零退化**（鏡像 improving_16 `SDD_ENABLE_SLV_AUTO_PROPOSE`、improving_15 `SDD_ENABLE_AUTO_RECOVERY` 三前例）。

### 2.1 介面 delta（v0.08，Copy-on-Evolve 自 v0.07）

`tools/fsm_runtime/fsm_runtime.py`（凍結本體 → 走 Copy-on-Evolve）：

**W-17-1 — 代謝提議接入主迴圈**：
- module 常數 `_SCAFFOLD_GC_AUTO_PROPOSE_ENV = "SDD_ENABLE_SCAFFOLD_GC_AUTO_PROPOSE"` + 純函式 `_scaffold_gc_auto_propose_enabled()`（讀環境變數開關，鏡像 `_slv_auto_propose_enabled`，符 SDD env-flag 慣例）。
- `enter_scaffold_gc()` 進態 SCAFFOLD_GC **後**（設完 tracking、save_state **前**）：`if _scaffold_gc_auto_propose_enabled():` → **try** `from . import scaffold_gc; res = scaffold_gc.run_gc(self.state, today=<utc date>)` → 把 `{report_path, proposals_total, rules_scanned}` 寫入 `scaffold_gc_tracking`（`origin:"auto"`）→ 回傳 dict 加 `auto_gc` 區塊；**except** → `tracking["auto_gc"] = {"proposed": False, "error": ...}`，**進態仍成功、不偽造報告路徑**（fail-closed，紅線：人仍可手動跑 GC）。
- `today` 由 caller 注入 UTC 日期字串（避免 `Date.now` 不確定性，沿用 `run_gc(today=)` 既有契約）。
- 預設 OFF（flag 未設）→ `enter_scaffold_gc` 行為**逐字同 v0.07**（只記 tracking、不算 GC）＝零退化。
- **紅線**：`run_gc` 內部只 `compute_proposals` + 寫 Markdown，**零 `set_maturity` 呼叫**（退役維持人工 gate，R-9.20 #11 不弱化）。

**W-17-2 — L5 可量測信號 + XAI 安全證書**：
- 新 method `scaffold_gc_stats() -> dict`（純讀，零副作用、零轉態）：自既有 `scaffold_gc_tracking` + `scaffold_gc.compute_proposals()` 重算 ROI 提議，輸出 `{proposals_total, by_transition（active→audit-only→deprecated 各計數）, roi_ladder（依 ROI 升冪、標最該退役者）, last_report_ref}`。**度量穩健**：零提議不除零（回空清單 / 0）。
- XAI Turn：額外輸出 `safety_certificate` 區塊——`{auto_retire: False, human_gate: "rule_loader.set_maturity(reviewed_by=...)", well_founded: "GC 僅提議、永不自動退役 active 規則；退役單調經人工 review，ROI 棘輪不回震"}`，讓人類舵手一眼看懂「代謝在環上守界」（鏡像 W-16-2 `termination_certificate` 呈現原則，**純讀、不渲染大圖、不碰 meta-oracle**）。

### 2.2 LOC 預算落點
`fsm_runtime.py` 為 runtime facade（非 plugin_entry/data 分級）；W-17-1 ~25 行（1 flag 純函式 + enter_scaffold_gc additive 分支）、W-17-2 ~25 行（1 純讀 method）。AutoClaude 側 LOC budget 不涵蓋 SDD 框架；SDD `arch_fitness` 無逐檔 LOC 硬閘。無 LOC violation。

### 2.3 .importlinter 影響
本輪零觸 AutoClaude（`autoclaude/`）→ AutoClaude `.importlinter` 8 contract 不受影響。SDD 框架不在 AutoClaude import-linter 管轄。`scaffold_gc` local import（鏡像 `_auto_draft_slv` 的 `from . import slv_generator` 慣例）避免 top-level cycle。

### 2.4 checkpoint additive
W-17-1 寫 `scaffold_gc_tracking`（既有 dict，:1510 已 setdefault；新增 `report_path`/`proposals_total`/`origin`/`auto_gc` 鍵為 additive）；W-17-2 純讀。零新增持久化 schema、零 DAL 涉及（SDD 框架自有 `save_state`）。

---

## 3. 階段三：實作與雙重驗證

### 3.1 W-17-1 落地（見 §2.1）
flag OFF 既有 `test_phase_h` / `test_scaffold_gc`（若有）/ `test_transitions` 零退化（編譯 + 單測，Rule 4）。

### 3.2 閉環自走測試（`tests/test_scaffold_gc_auto_propose_wiring.py`，預估 8 case）
| case | 驗證 |
|------|------|
| flag off + enter_scaffold_gc → 純記 tracking 無 auto_gc 鍵 | 零退化（v0.07 行為） |
| flag on + enter_scaffold_gc → auto run_gc + 填 report_path/proposals_total | L5 自走（不再需手動跑 GC） |
| flag on + run_gc 產提議 → 報告檔實際落盤 build/reports/gc/ | SCAFFOLD-ROI 真實產出 |
| flag on + run_gc 內部失敗（注入）→ fail-closed：進態成功 + auto_gc.proposed=False | fail-closed |
| flag on + 提議恆 proposed、零 set_maturity 呼叫（spy/mock 驗證）| R-9.20 #11 紅線守界 |
| enter_scaffold_gc 非 RELEASE 源仍 raise（flag on 不放寬入口）| 入口紀律不被 flag 弱化 |
| scaffold_gc_stats 零提議不除零 + roi_ladder 升冪正確 | L5 信號度量穩健（W-17-2）|
| scaffold_gc_stats.safety_certificate.auto_retire == False 恆真 | XAI 守界證書（W-17-2）|

### 3.3 B 軌 dogfooding 新發現缺陷 → 即記即修
行進中發現的框架摩擦/缺陷一律即記入 `docs/06_quality/AutoSDD_Defect_Log.md` 並分流（見 🐶 自我迭代模式）。預期候選：`enter_scaffold_gc` 入口僅 RELEASE，週期性自動觸發需排程器（與 SLV 同屬「需外部排程觸發 observation 態」家族）；實作中確認。

### 3.4 Copy-on-Evolve v0.07 → v0.08
用共享 infra `scripts/copy_on_evolve.sh`（improving_12 建、improving_15 硬化保留 FSM-STATE-TEMPLATE.yaml）；`.gitignore` 比照既有 negate idiom 補 v0.08 區塊（DEF-15-001 已固化）；`EVOLUTION_LOG.md` + `releases/CHANGELOG.md` v0.08 段；`arch_fitness` FF-17 自證 v0.08 入閘。

---

## 4. 階段四：零退化驗證矩陣（全項實測，待執行）

| 檢查 | 命令 | 通過條件 |
|------|------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3112 / 0 failed（floor 持平，本輪零觸 AutoClaude） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | 雙軌 exit 0（v0.01 + v0.08 + scripts/tests）|
| 五軌 TLC | N/A（§1.4：零 `_HAPPY_PATH`/`*.tla` 變更，diff 逐位元零差異佐證）| — |

---

## 5. <Architecture_Design_Review>

1. **架構純潔性**：W-17-1＝`enter_scaffold_gc` 既有方法的 additive flag 分支 + 呼叫既有 `run_gc`（不重寫）；W-17-2＝1 個純讀 method。**無 God-object**、零新狀態、零新 FSM 邊。Thin Facade 維持。
2. **持久化相容**：`scaffold_gc_tracking` 既有 dict，新增鍵 additive；W-17-2 純讀。SDD `save_state` 既有路徑，零 schema 變更。AutoClaude DAL 三後端不涉。
3. **安全防護網（CONDITIONAL）**：本輪零新增「從文件生成指令」路徑；SCAFFOLD-ROI 是 Markdown 報告 + `RetirementProposal` 資料，非可執行指令。N/A。
4. **對外 I/O 安全**：本輪零新增 `ToolInvocationPort` 外呼路徑（純框架內 FSM + 本地 Markdown 落盤）。N/A。
5. **紅線守界專章（B 軌）**：① `run_gc` 只產提議、**永不呼叫 `set_maturity`**——退役維持 🔴 人工（R-9.20 #11 不弱化）；② 提議天然恆 proposed；③ fail-closed：`run_gc` 任何失敗不阻塞進態、不偽造報告路徑；④ flag 預設 OFF 零退化；⑤ 不碰 meta-oracle（GC 是 ROI 統計層）；⑥ 免五軌 TLC（diff 逐位元零差異硬證據）。

---

## 6. XAI Turn 藍圖 + GitHub Issue 規格草案（driver instance：ACT-055 / R-9.20）

<thinking>
**可解釋性轉向深度推理**：鷹架代謝的「良基終止」不在算子呼叫圖 rank，而在 **ROI 棘輪的單調性**——退役只能 active→audit-only→deprecated 單向降級，且每次降級須人工 `set_maturity(reviewed_by=)`，故 add↔retire 抖動被「人工 gate + 單調降級」雙重夾住。人類舵手須一眼看懂「哪條鷹架被提議退役、ROI 多低、退役了會不會反而漏接問題（catch_count）」。

**漏洞挖掘**：① 認知超載——一次 GC 可能提議大量退役淹沒審批佇列 → roi_ladder 升冪 + 標最該退役者（ROI 最低）＝critical path。② 狀態漂移四源一致——(1) Rule 9.20 憲法、(2) `scaffold_gc.run_gc` 執行邏輯、(3) `scaffold_gc_stats` 渲染、(4) `scaffold_gc_tracking` 狀態真相，杜絕「畫的退役提議跟跑的 ROI 帳本不一樣」。③ 視覺欺騙——`scaffold_gc_stats` 須從 `compute_proposals` 獨立重算 ROI，不盲信 tracking 標籤（鏡像 improving_14 adapter digest 重算防偽）。
</thinking>

- **儀表板架構與資料流**：`scaffold_gc_stats()`（W-17-2，純讀）→ 輸出 `{proposals_total, by_transition, roi_ladder, safety_certificate}`；ROI 自 `compute_proposals` **獨立重算**（不盲信 tracking），對齊 R-9.37「AST 同構純投影」原則。
- **視覺化與降維**：Markdown 表 + ROI 升冪階梯，⛔ 標 ROI=0（從不 catch）之鷹架＝最該退役 critical path；有界截斷 + 分頁（防大量提議 token 爆炸）。
- **TLA 不變量擴充評估**：**沿用既有** SCAFFOLD_GC happy-path + R-9.20 守界，**無需新 `VisualizationBounded` 證明**（本輪僅純讀統計，不渲染遞迴大圖）。
- **完整 DoD**：(技術) W-17-1 auto-GC flag-gated + fail-closed + 8 case 綠；(形式化同構) diff v0.07↔v0.08 `*.tla` 逐位元零差異 + `scaffold_gc_stats` ROI 重算與 tracking 一致；(Token 預算稽核) 純讀統計零渲染大圖；(UI/UX 審批) safety_certificate 人類舵手可一眼判讀「永不自動退役」守界 → 供 steersman signoff。

> **GitHub Issue 規格草案**（供掌舵者 signoff）：標題「[L5/B-axis] Wire scaffold-GC auto-propose into SCAFFOLD_GC main loop with retirement-by-proposal-only + human gate」；Labels：`maturity:L5`、`track:B`、`xai-turn`、`red-line:human-gate`；DoD 如上；驗收＝flag ON 端到端「進代謝態→auto run_gc→SCAFFOLD-ROI proposed→人工 set_maturity 退役」鏈閉合，flag OFF 零退化。

---

## 7. RTM（需求追溯矩陣）

| W 項 | 需求（rubric/北極星） | 介面 delta | 測試 | 紅線 |
|------|----------------------|-----------|------|------|
| W-17-1 | B L4→L5：鷹架代謝自動提議退役在環（§北極星2 圖靈完備閉環的收縮側）| `_scaffold_gc_auto_propose_enabled` + `enter_scaffold_gc` flag 分支呼叫 `run_gc` | test_scaffold_gc_auto_propose_wiring 1-6 | R-9.20 #11 退役人工 gate + fail-closed + flag OFF 零退化 |
| W-17-2 | L5「在環上守界」可量測信號 + XAI 安全證書可解釋 | `scaffold_gc_stats()` | test_scaffold_gc_auto_propose_wiring 7-8 | R-9.20 不弱化、純讀不碰 meta-oracle |

---

## 8. 成熟度誠實聲明（zero-trust，沿用 improving_16 紀律）

本輪交付 B 軸「**L5 能力 ＋ 測試證據**」：flag 預設 **OFF ＝ 預設仍 L4**（零退化）、L5 為**可啟用能力**、**運行達標須生產啟用 `SDD_ENABLE_SCAFFOLD_GC_AUTO_PROPOSE` 後累積** 進代謝態→auto run_gc→人工退役 的真實證據（且需 `record_fire` 累積足量 runtime ROI 資料才有非空提議）。**不虛報運行已達 L5、不躍報 `L_合體` 升級**——`L_合體` 維持 **L4 信號邊界**（A/B/C 皆 L4；B 取得 L5「收縮側」信號但需三軸同升 + 運行累積方推 `min` 上移）。Block-2（active 規則退役經人工 `set_maturity`）為**永久守界**，非待移除的過渡——「L5 在環上守界」的守界本身即人類掌舵點。
