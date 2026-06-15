# AutoSDD_improving_19 — B 軌「鷹架代謝」L4→L5 信號：catch 側契約定義並接入

> **軌道①整合迭代第 19 輪**（驅動器＝`AutoSDD_Iteration_Prompt_Template.md`）。
> **本輪柱**：**B 軌（手腳 AISLDC_SDD dogfooding）** — 閉合「鷹架代謝」對偶閉環的 catch 側。
> **下一份**：improving_20（按需，待舵手 signoff）。
> **凍結來源框架版本**：`AISDLC_SDD_v0.09` → 演化為 **`AISDLC_SDD_v0.10`**（Copy-on-Evolve）。
> **🔴 人工 signoff**：① 方向「主推 B 軌 catch 側契約」；② SCG-2「否決時序匹配、採顯式可歸因 + fail-closed，本輪只真接 R-9.1/R-9.21 確定路徑」。

---

## 0. 北極星對齊與防混淆

- **北極星**：catch 側是 16→17→18→19 對偶閉環的「最後一哩」——16 接「增」(SLV 自演化)、17 接「減·決策」(run_gc)、18 接「減·遙測 fire 側」、**本輪 19 接「catch 側」完成 ROI 雙側信號**。
- **三軸成熟度（rubric `L_合體=min(A,B,C)`）**：本輪推進 **B 軸**（流程自治 L4→L5 信號），交付「L5 catch 遙測能力 + 證據」；flag 預設 OFF＝**運行仍 L4**（未虛報運行已達 L5、未躍報 L_合體）。A/C 軸本輪未動，維持各自現級。
- **防跨軌**：本輪在 **B 柱**；下一份 `improving_20`。未誤指子專案 `SDD_improving_Automation_NN`（軌道②）。

---

## 1. 階段一：Zero-Trust 重偵察（實測事實，後續設計只錨定此）

### 1.1 基線硬閘（全守住，無觸發）
| 檢查 | 實測 | floor（v18） | 判定 |
|------|------|------|------|
| AutoClaude `pytest -q` | 3112 passed / 0 failed / 122 skipped | 3112 | ✅ 持平 |
| `lint-imports` | 8 kept / 0 broken | 8 kept | ✅ |
| `check_loc_budget.py` | violations=0（total=17794/cap=20438） | 全過 | ✅ |
| `snapshot_sync.py --check` | 新鮮 | 新鮮 | ✅ |
| AISLDC_SDD `ci-gate.sh` | exit 0（v0.01:1478 / v0.09:1534 / scripts:25） | exit 0 | ✅ |
| arch_fitness | fail=0 / warn=3（FF-5、FF-16 GAP-X1、**FF-16 GAP-X2**） | fail=0 | ✅（advisory） |

### 1.2 catch 側現況（偵察證據）
- W-18 構件確證存在且測試覆蓋：`record_state_fires`、`rule_fire_telemetry_stats`、flag gate。
- `Rule.scaffold_roi` 早有預留 `catch_count`；`roi()=catch/fire`（fire=0 回 1.0）。`record_fire(rule_id,*,caught)` 簽名有 `caught` 但**全框架無任何路徑以 caught=True 呼叫**。
- `catch_side_wired=False` 硬編。**核心張力**：catch 側**無既有 FSM 錨點**——框架既有攔截（ESCALATION/guard/hook）全是「系統違反約束」，非「規則守望的失敗模式真被攔下」。
- **arch_fitness FF-16 GAP-X2 仍 warn**：印證 GC 因 catch_count 恆 0 → ROI 無意義 → 仍無有效退役提議。

### 1.3 attribution 可行性（決定「真接 vs 半接」）
- **無現成可歸因來源**：`escalation_history.trigger_reason` 純文字無結構化 rule_id；`record_state_fires` 回傳的 rule_id 清單被呼叫端遺棄；R-*.yaml 無 failure_mode 欄。
- **關鍵架構發現**：`record_escalation()` 直接設 `current=ESCALATION` **繞過 transition()** → catch 記帳不能只接 transition()（會漏 gate_fail 主路徑）。

---

## 2. 階段二：增量設計 + SCG-2 裁決

### 2.1 🔴 設計分歧裁決（否決偵察 agent 的省成本推薦）
偵察推薦 **時序匹配（last_fired_rules）** 為省成本主路徑。**否決**，理由直指 DEF-18-001 紅線：時序鄰近 ≠ 因果歸因——一條規則 fire 後隨即 ESCALATION，未必是該規則攔到問題，正中「擅自映射污染 ROI、比不做更糟」陷阱。

**採「顯式可歸因 + fail-closed」**。**catch 契約（W-19 定義，閉合 DEF-18-001）= 三要件齊備才 `catch_count+1`**：
1. 規則自描述守望的 `failure_mode`（非空）；
2. 對應攔截事件（ESCALATION / MONITOR_VIOLATION）真實發生；
3. 該事件結構化攜帶此 rule_id（呼叫端明確歸因）。

缺任一 → fail-closed 不記（寧缺勿濫）。**真接錨點**（避免重蹈 DEF-17-001 半接）：`gate retry 耗盡 → R-9.1`（無歧義映射）、`monitor 破壞 → R-9.21`。

### 2.2 <Architecture_Design_Review>
1. **架構純潔性**：`record_state_catches` 與 `record_state_fires` 對偶同層 helper，不擴張 transition() 為業務中樞（仍 thin）。無 God-object。
2. **持久化相容**：`failure_mode`/`attributed`/`total_catches`/`catch_attribution_coverage` 全 **additive**；舊狀態/規則向後相容（欄缺=空）。**識別並解決持久化陷阱**：`_write_rule` 條件寫回 failure_mode（非空才寫），否則 round-trip 會對全部舊規則插入空欄、污染凍結本體。
3. **安全防護網**：本輪無「從文件生成指令」新路徑，CONDITIONAL 三層防禦不受影響。
4. **對外 I/O 安全**：本輪無 `ToolInvocationPort` 外呼路徑，N/A。
5. **零退化/TLC**：新 flag 預設 OFF=逐字同 v0.09；catch 記帳是 record_escalation 已落定後的非轉態 side-effect → `transition_rules.py` + 5 `*.tla` 對 v0.09 **逐位元零差異** → 免五軌 TLC（依 Rule 9.18.1）。

---

## 3. 階段三：實作順序與 RTM

| W 項 | 內容 | 檔案 | 驗收（TC） |
|------|------|------|-----------|
| **W-19-1** | `Rule.failure_mode` schema additive + `_load_rule_file` 讀取 + `_write_rule` 條件寫回（持久化陷阱解法）+ R-9.1/R-9.21 補 failure_mode | `v0.10/tools/fsm_runtime/rule_loader.py`、`governance/rules/R-9.1*.yaml`、`R-9.21*.yaml` | catch Case 10（fire round-trip 不抹 failure_mode）、編譯驗證（R-9.1/9.21 非空、餘空） |
| **W-19-2** | `record_state_catches(attributed_rule_ids)` helper（fail-closed）+ 新 flag `SDD_ENABLE_RULE_CATCH_TELEMETRY` + `_record_escalation_catches` 接入兩 `record_escalation` 呼叫點（R-9.1/R-9.21） | `v0.10/tools/fsm_runtime/rule_loader.py`、`fsm_runtime.py` | catch Case 1-9（flag off 零退化 / helper 真記 / monitor 整合 / fail-closed / R-9.20 紅線 / 要件①/ 寧缺勿濫 / 子集語意） |
| **W-19-3** | `rule_fire_telemetry_stats` 翻 `catch_side_wired=True` + `total_catches` + `catch_attribution_coverage`（誠實揭露覆蓋率） | `v0.10/tools/fsm_runtime/fsm_runtime.py` | catch Case 11（coverage 揭露）、fire Case 7 同步斷言 |
| **DEF-19-002 修** | 版本偵測 glob `v0.0*` 在 v0.10 失效 → 雙 glob 修復（共享 infra ci-gate.sh + test + v0.10 arch_fitness） | `scripts/ci-gate.sh`、`scripts/tests/test_ci_gate_version_resolution.py`、`v0.10/tools/arch_fitness/arch_fitness.py` | dry-run 偵測 v0.10、雙軌 ci-gate exit 0、FF-17 測試 5 passed |

**紅線守界**：`record_state_catches` 只增 catch_count、**永不 set_maturity**（R-9.20 #11）；catch_count>0 是 `propose_graduation` 保護有用規則不被誤退役的依據（補實 FF-16 GAP-X2 資料缺口）。

---

## 4. 階段四：CI 平價收斂（零退化驗證矩陣全項）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `pytest tests/ -q` | ≥3112 / 0 failed | **3112**（git 證 AutoClaude 零改動，沿用階段一）✅ |
| 架構契約 | `lint-imports` | 全 kept | 8 kept（未動）✅ |
| LOC 分級 | `check_loc_budget.py` | 全過 | violations=0（未動）✅ |
| Snapshot | `snapshot_sync.py --check` | 新鮮 | 新鮮（未動）✅ |
| AISLDC_SDD 閘門 | `ci-gate.sh` | exit 0 | **exit 0，v0.01:1478 / v0.10:1545 / scripts:25**（v0.10 入閘）✅ |
| DAL 等價 | equivalence | 三後端等價 | AutoClaude 未動 ✅ |
| 五軌 TLC | （僅 FSM 變更時） | 0 violation | 免（逐位元零差異）✅ |

> file_lock flaky 註記：`test_file_lock.py::test_parallel_writes_do_not_lose_increments` 於某次 ci-gate 跑出 Windows O_EXCL 並行檔案鎖 PermissionError；單獨重跑 3 次全 3 passed、且本輪未碰 file_lock.py（逐位元複製自 v0.09）→ 確認環境 flaky、非退化。重跑 ci-gate 全綠。

---

## 5. 缺陷分流（本輪）

- **DEF-18-001**：routed → **fixed@v0.10**（catch 側契約定義並接入；覆蓋面殘留衍生 DEF-19-001）。
- **DEF-19-001**（P3, routed）：catch 歸因目前僅覆蓋 2/39 規則，餘漸進補強（coverage 程式內誠實揭露）。
- **DEF-19-002**（P2, **fixed@v0.10 + 共享 infra**）：版本偵測 glob `v0.0*` 在 v0.10 失效；雙 glob 修復；dry-run + 雙軌 ci-gate 實證 v0.10 入閘。

---

## 6. 成熟度誠實

交付 **B 軸「L5 catch 遙測能力 + 證據」**：catch 契約定義、兩確定路徑真接、ROI 雙側信號、覆蓋率誠實揭露。**flag 預設 OFF＝運行仍 L4**——未虛報運行已達 L5、未躍報 `L_合體`（維持 L4 信號邊界）。catch 覆蓋 2/39＝刻意保守（寧缺勿濫），餘漸進補強（DEF-19-001）。

---

## 7. 多專家 Zero-Trust 三鏡審查

見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_19.md`。
