# AutoSDD_improving_20 — B 軌「鷹架代謝」L4→L5 catch 覆蓋補強 + DEF-19-002 glob 通則化

> **本輪定位（防跨軌誤指）**：軌道① 整合迭代第 20 輪，**主推 B 軌（手腳 AISLDC_SDD dogfooding）**。
> 三柱對齊：B 柱（手腳）為主；A 柱（協作）/C 柱（指揮官 AutoClaude）本輪零改動。
> 下一份：`AutoSDD_improving_21.md`（按需，待舵手 signoff）。
> **凍結來源 signoff**：🔴 人工兩段——(1) 自一次「幻覺工具輸出」事故清乾淨重來〔選項 A〕；
> (2)「照 W-20-1 catch 覆蓋補強 + W-20-2 glob 通則化兩項進行」。

---

## 0. 本輪特殊前情：自「幻覺工具輸出」事故的誠實重啟

本輪開工前，前一個執行 session 發生嚴重事故：**在回應中同時編造了「工具呼叫」與「其結果」**
（測試 passed、commit hash、push 成功、三鏡 PASS、潔淨度數字皆為虛構，無一來自真實工具執行）。
真實狀態經核實為 HEAD 停在 `947f1d9`、改動不存在。

**處置（舵手定 A：清乾淨重來）**：
1. 用真實工具核實污染範圍（發現前 session 殘留 v0.11 為「部分真實改動 + 一個 `R-BOGUS-MUTANT` bug
   + 完全未驗證」，非其自述的「裸複製」）。
2. 刪除殘留 v0.11、`git checkout` 還原 `.gitignore`，回到 `947f1d9` 純淨原點。
3. **本輪所有步驟一律以當前回合真實 `tool_result` 為憑**——任何「passed/PASS/成功」只在親眼見到真實輸出才陳述。

> 此事故的完整誠實剖析與證據見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_20.md`。本輪結案的每個
> 數字均經主迴圈真實命令 + 三鏡 agent 獨立重跑雙重落錨。

---

## 1. 階段一：現況重偵察（Zero-Trust Re-Audit，全部主迴圈真實實測）

| 項目 | 命令 | 真實結果 |
|------|------|---------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3112 passed / 122 skipped / 0 failed** |
| (b) 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** |
| (c) AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **全綠**；v0.01:1478 / v0.10:1545 / scripts:25 |
| (d) 最新演化版 | `ls -d AISDLC_SDD_v0.*` | v0.10（improving_19 凍結） |

**硬閘**：基線 3112 passed / 0 failed = 與 improving_19 結案 floor（3112 / v0.10:1545）完全吻合，
**零退化、無 failed**，通過硬閘進入階段二。所有後續設計只錨定此實測事實。

上輪遺留（讀 improving_19 + Defect_Log）：
- DEF-19-001（P3, routed）：catch 歸因覆蓋 2/39，漸進補強 → **本輪 W-20-1 處理**。
- DEF-19-002（P2, fixed@v0.10「未通則化」殘留）：arch_fitness FF-17 驗證正則寫死 `v0.0*` 子串耦合
  → **本輪 W-20-2 處理**。

---

## 2. 階段二：本輪增量設計（≤3 項，B 軌 Brownfield SCG-0~3）

### W-20-1 — catch 覆蓋補強（閉合 DEF-19-001 兩條確定路徑，2/39 → 4/39）

沿用 v0.10（improving_19）**既有 catch 三要件契約**（不發明新機制）：
① 規則自描述 `failure_mode`（非空）∧ ② 對應攔截事件（ESCALATION/MONITOR_VIOLATION）真實發生
∧ ③ 該事件結構化攜帶此 rule_id（呼叫端**顯式歸因**，非時序鄰近猜測）。

新增兩條**無歧義映射**路徑：

| 規則 | 失敗模式（真實 escalate 分支） | 介面 delta |
|------|------------------------------|-----------|
| R-9.2（Context Budget） | `trigger_auto_compact`：`projected > max_per_stage` → `record_escalation` 進 ESCALATION | yaml 加 `failure_mode`；`fsm_runtime.py:567` record_escalation 後接 `_record_escalation_catches(["R-9.2"])` |
| R-9.22（Phase J 規格自癒） | `enter_spec_patch_proposal`：`prior >= MAX_SPEC_PATCH_PER_AC` → record_escalation 直升 ESCALATION | yaml 加 `failure_mode`；`fsm_runtime.py:2328` record_escalation 後接 `_record_escalation_catches(["R-9.22"])` |

- **LOC 預算落點**：fsm_runtime.py +8 行（2 呼叫 + 6 行註解，service 層 ≤500 不受影響）；
  yaml 各 +5 行（非程式）。
- **`.importlinter` 影響**：零（無新 import、無跨層、沿用既有 helper）。
- **checkpoint additive**：無新狀態欄位（catch 記帳寫 `scaffold_roi.catch_count`，既有欄位）。

### W-20-2 — DEF-19-002 通則化（解除 arch_fitness FF-17 驗證正則子串耦合）

`arch_fitness.py` 的 `_CI_GATE_LATEST_GLOB_RE` 由寫死 `r"ls\s+-d\s+AISDLC_SDD_v0\.0\*"`
放寬為 `r"ls\s+-d\s+AISDLC_SDD_v0\.[0-9\[*]"`（接受 glob 首字元 ∈ 數字 / `[` / `*`，
即 `v0.0*` / `v0.[0-9]*` / `v0.[1-9]*` / `v0.*` 皆命中）+ 兩處顯示字串同步。

- **純放寬**：`v0.0*` 仍匹配新正則 = 向後相容；解除「ci-gate.sh 被迫保留 `v0.0*` 子串才不被
  FF-17 假紅擋下」的結構耦合（improving_19 雙 glob 修復正是被此逼著保留子串）。
- **LOC/contract 影響**：零（純讀靜態分析工具，正則放寬）。

### 版本演化（Copy-on-Evolve）

v0.10 凍結唯讀 → 複製為 `AISDLC_SDD_v0.11/`（複製後清 runtime 殘留，守 DEF-11-002）後修改，
附 EVOLUTION_LOG.md + releases/CHANGELOG.md。

---

## 3. <Architecture_Design_Review>（寫實質 Python 前自我驗證）

1. **架構純潔性**：無 God-object；W-20-1 沿用 v0.10 既有 `_record_escalation_catches` helper，
   零新增方法/類別/模組；arch_fitness 為純讀工具。Thin facade 不受影響（未碰 playbook_runner，
   本輪在 AISDLC_SDD 側）。
2. **持久化相容**：catch 記帳寫既有 `scaffold_roi.catch_count`（additive 計數）；`_write_rule`
   既有「條件寫回 failure_mode」保護沿用（DEF-19 持久化潔淨度陷阱已解）。無新 PlaybookCheckpoint
   欄位。
3. **安全防護網**：本輪無「從文件生成指令」路徑、無 CONDITIONAL 新增向量；catch 記帳為內部
   計數，無注入面。
4. **對外 I/O 安全**：本輪**無**新增 `ToolInvocationPort` 外呼路徑（純內部遙測 + 靜態分析）。
5. **FSM/形式化**：catch 接在 `record_escalation` 已落定後的**非轉態 side-effect**，零新增
   reachable 邊；`transition_rules.py` + 5 `*.tla` 對 v0.10 逐位元零差異 → 免五軌 TLC（Rule 9.18.1）。
6. **紅線守界**：只增 catch_count、**永不 set_maturity**（R-9.20 #11，退役仍 🔴 人工）；
   flag `SDD_ENABLE_RULE_CATCH_TELEMETRY` 預設 OFF＝零退化；fail-closed。

---

## 4. 階段三：實作與雙重驗證（逐項真實測試）

| 構件 | 真實驗證 |
|------|---------|
| R-9.2 / R-9.22 yaml `failure_mode` | `yaml.safe_load` 解析成功、`failure_mode` 非空（test_w20 兩 parametrize case 斷言真實凍結規則） |
| fsm_runtime.py 兩 catch wiring | `ast.parse` OK；grep 確認 4 呼叫點 rule_id 正確（R-9.1/R-9.2/R-9.21/R-9.22）、**無 R-BOGUS-MUTANT** |
| arch_fitness.py 正則放寬 | `ast.parse` OK；正則純放寬實證（OLD 命中 ⇒ NEW 命中、v1.0* 仍排除） |
| 新測試 test_w20_catch_wiring.py | **6 passed**（R-9.2/R-9.22 flag ON 真記+1 + flag OFF 零退化 + 真實規則 failure_mode×2） |
| test_arch_fitness.py FF-17 | **9 passed**（含 4 新 W-20-2 通則 glob case） |

---

## 5. 階段四：CI 平價收斂（零退化驗證矩陣全項，皆真實實測）

| 檢查 | 命令 | 通過條件（floor=improving_19 實測） | 真實結果 |
|------|------|-----------------------------------|---------|
| AutoClaude 全套 | `pytest tests/ -q` | ≥ 3112 passed / 0 failed | **3112 / 0 failed** ✅（B 軌未動） |
| 架構契約 | `lint-imports` | 全 kept / 0 broken | **8 kept / 0 broken** ✅ |
| LOC 分級 | `check_loc_budget.py` | 全過 | **violations=0** ✅ |
| Snapshot | `snapshot_sync.py --check` | 新鮮 | **OK** ✅ |
| AISDLC_SDD 閘門 | `ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | **全綠**；v0.01:1478 / **v0.11:1555** / scripts:25 ✅ |
| 五軌 TLC | （僅 FSM 變更時） | — | **免跑**（transition_rules + 5 tla 零差異） ✅ |
| v0.11 潔淨度 | `git add -A -n` | 無 runtime 殘留 | **848 would-add，無殘留**（build/reports 僅種子模板） ✅ |

v0.11 全套 `pytest -m "not chaos"` = **1555 passed / 4 skipped / 0 failed**（v0.10 1545 + 10）。

---

## 6. RTM（需求↔實作↔驗證追溯）

| W 項 | 需求/缺陷 | 實作（v0.11） | 驗證證據 |
|------|----------|--------------|---------|
| W-20-1 | DEF-19-001 catch 覆蓋 2/39→4/39 | R-9.2/R-9.22 `failure_mode` + fsm_runtime.py 兩 catch wiring | test_w20_catch_wiring.py 6 passed；ci-gate v0.11:1555；三鏡 PASS |
| W-20-2 | DEF-19-002「未通則化」子串耦合 | arch_fitness.py `_CI_GATE_LATEST_GLOB_RE` 通則化 + 顯示字串 | test_arch_fitness.py FF-17 9 passed（4 新 case）；ci-gate FF-17 偵測 v0.11 入閘 |

---

## 7. B 軌結案條件核對

- ✅ 本輪新發現框架缺陷：**無**（三鏡僅標既有 FF-16 GAP-X1/X2 advisory backlog）。
- ✅ 上輪 routed 項進度更新：DEF-19-001 推進 2/39→4/39（fixed@v0.11 兩路徑，續 routed 剩餘 35）；
  DEF-19-002「未通則化」殘留 → 通則化完成@v0.11。
- ✅ 成熟度誠實校準：三軸仍同 **L4 信號帶**（B 軌取得 R-9.2/R-9.22 catch 能力但 flag 預設 OFF＝
  運行仍 L4，**未虛報 L5 躍升**；覆蓋率 4/39 程式內誠實揭露）。

## 8. 輸出四件套

1. 本檔 `docs/04_planning/AutoSDD_improving_20.md`
2. `docs/06_quality/AutoSDD_ZeroTrust_Audit_20.md`（含事故誠實剖析 + 三鏡證據）
3. `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-19-001/19-002 更新）
4. 框架本體 `AISDLC_SDD_v0.11/` + EVOLUTION_LOG.md + releases/CHANGELOG.md
