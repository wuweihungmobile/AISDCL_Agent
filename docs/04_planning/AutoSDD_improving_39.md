# AutoSDD_improving_39 — B 軌 dogfooding：DEF-19-001 catch coverage 分母正當性（DEF-39-001 escalation-scoped 透明化）

> **軌道①整合迭代 第 39 輪**。本輪主柱＝**B 軌（手腳 AISLDC_SDD framework dogfooding）**。
> 🔴 掌舵者 AskUserQuestion 兩問拍板：(Q1) 主柱＝**B 軌·分母正當性調查**；(Q2) 幅度＝**2–3 W 項**。
> 框架本體改進落 **Copy-on-Evolve `AISDLC_SDD_v0.17/`**（v0.16 凍結唯讀）。
> 北極星對齊：B 流程自治（catch 歸因度量誠實化——把「7/39≈18% 誤導讀數」校正為「escalation-scoped 7/7=100% 天花板達成」，鷹架代謝 ROI 可信退役門檻的度量地基修正）。

---

## §0 本輪定位（防跨軌誤指）

| 項目 | 內容 |
|------|------|
| 軌道 | ① 整合迭代，**B 柱（手腳）** |
| 活標的 | **DEF-19-001**（catch 歸因覆蓋，P3，routed）→ 本輪揭露其更深根因並開 **DEF-39-001** |
| 為何非 C 軌 | C 軌 SD_09 **W1 正式執行輪因 06-26 G0 閘門未開而 blocked**（今 2026-06-18），不啟 W1/不跑 mutmut/不偽造 nightly |
| 為何轉向（非無腦續接線）| **zero-trust 關鍵發現**：fsm_runtime.py 9 個生產 escalation 落點＝7 已接線 + 2 正交無規則，DEF-19-001 沿「1:1 無歧義落點接線」的乾淨候選**已枯竭**，7/39 已達結構天花板（詳 §1） |
| 下一份 | improving_40（按需） |
| 框架版本 | v0.16 → **v0.17**（Copy-on-Evolve） |

---

## §1 階段一：現況重偵察（Zero-Trust Re-Audit，實測）

派 general-purpose agent 重新實測（禁引文件宣稱值），六項基線全綠 HARD GATE PASS：

| 項目 | 實測值 | 判定 |
|------|--------|------|
| AutoClaude `pytest tests/ -q` | **3221 passed / 122 skipped / 0 failed** | ✅ = floor，0 failed |
| `lint-imports` | 8 kept / 0 broken | ✅ |
| `check_loc_budget.py` | violations=0（18506 < 20438） | ✅ |
| `snapshot_sync.py --check` | OK / FRESH | ✅ |
| AISDLC_SDD `ci-gate.sh` | exit 0；v0.01:1478 / v0.16:1605 / scripts:**44** | ✅（scripts 42→44 為增量非退化） |
| 最新框架版 | **v0.16** | ✅ |

### 🔑 候選枯竭實測（本輪轉向的機械證據）

`grep record_escalation\( fsm_runtime.py`（v0.16）＝ **9 個生產 escalation 落點**：

| 落點行 | 規則 | catch 接線 |
|------|------|-----------|
| 249（HUMAN_PENDING timeout） | R-9.7 | ✅ |
| 355（gate retry 耗盡） | R-9.1 | ✅ |
| 416（SPEC_AUDIT 耗盡） | R-9.3 | ✅（improving_38）|
| **515（implementation budget exceeded）** | 無規則 | ⊘ 正交排除 |
| 587（auto_compact per-stage 超限） | R-9.2 | ✅ |
| 1881（sandbox policy_violation） | R-SELF-STRIDE | ✅（improving_38）|
| 2004（monitor violation） | R-9.21 | ✅ |
| 2353（spec_patch per-AC 上限） | R-9.22 | ✅ |
| **2401（spec_patch unable to draft）** | 無規則 | ⊘ 正交排除 |

**9 落點 = 7 已接線 + 2 正交無規則**。DEF-19-001 沿既有範式的乾淨候選已枯竭——剩餘 32 條規則並不在 FSM escalation 落點觸發，強行接線即違反 DEF-18-001「寧缺勿濫」。**故本輪不續接線，改查「分母 39 是否正當」**（掌舵者 Q1）。

---

## §2 階段二：本輪增量設計（3 W 項）

### <Architecture_Design_Review>

1. **架構純潔性**：無 God-object。W-39-2 僅在既有 `rule_fire_telemetry_stats()` 純函式計算內**additive** 加欄位 + 一個 class-level frozenset 常數（SSOT 註冊表）；不新增方法、不改控制流、不碰 transition()。
2. **持久化相容**：零 FSM-STATE 寫入、零新增狀態/轉換、零新增 reachable 邊。純讀 `rule_loader.load_all()` 計算度量。
3. **安全防護網**：不涉 CONDITIONAL 指令生成路徑。
4. **對外 I/O 安全**：不新增 `ToolInvocationPort` 外呼路徑。
5. **零退化**：既有 `catch_attribution_coverage` 三欄位（rules_with_failure_mode / rules_total / attributed_rule_ids）**逐字不變**，只在同 dict 內 additive 加 escalation-scoped 欄位＝既有 stats 消費者零退化。
6. **DEF-18-001 寧缺勿濫**：分母校正**不放寬**接線門檻——正當分母＝具唯一生產 escalation 落點的 7 條（與 attributed 完全吻合），不強塞無落點規則。
7. **紅線**：純度量、**永不 set_maturity**（R-9.20 #11）；不碰 meta⁹/meta-oracle；不提 Token 上限。
8. **防漂移（DEF-05-002/07-001 家族）**：SSOT 註冊表以靜態掃描測試鎖定＝`_record_escalation_catches(...)` 實際接線集合，杜絕未來接線變更忘了同步常數。

### W-39-1 — 39 條規則 catch 可歸因性分類（read-only 調查，確立正當分母）

派 Explore agent 機械分類全部 39 條非 deprecated 規則的守門機制（grep hooks/arch_fitness/formal + 規則語意）：

| 類別 | 規則數 | 是否 catch-可歸因（FSM escalation）|
|------|--------|------------------------------------|
| **(A) FSM escalation 落點** | **7**（R-9.1/9.2/9.3/9.7/9.21/9.22/R-SELF-STRIDE）| ✅ |
| (B) hook 守門（.claude/hooks/）| 3（R-9.4/9.6/9.8）| ✗ |
| (C) lint/arch_fitness/TLC | 3（R-9.5/9.9/9.18）| ✗ |
| (D) meta-loop guard（META_FSM，R-9.24~9.37）| 14 | ✗ |
| (E) manual/advisory/憲法 | 12（R-9.10~9.20 部分/9.23/9.38）| ✗ |
| **合計** | **39** | |

**結論**：真正 catch-可歸因僅 **7** 條；其餘 **32** 條由 hook/lint/TLC/meta-loop/人工守門，**本質非 FSM-escalation catch-可歸因**（catch_count 恆 0 是設計使然、非覆蓋缺口）。實測 `rules_with_failure_mode=7` 且 attributed_ids 精確等於該 7 條 → 證明**分母 39 高估了「catch 應接線範圍」**，escalation-scoped 真實覆蓋＝**7/7=100%**。

### W-39-2 — Copy-on-Evolve v0.17：escalation-scoped 分母透明化（DEF-39-001）

| 項目 | 內容 |
|------|------|
| 落點 | `fsm_runtime.py` — class 常數 `_ESCALATION_ATTRIBUTABLE_RULE_IDS`（7 條 SSOT，置於 `_record_escalation_catches` 前）+ `rule_fire_telemetry_stats()` additive 欄位 |
| 介面 delta（additive）| `catch_attribution_coverage` 加：`escalation_attributable_rule_ids` / `escalation_attributable_total`(=7) / `escalation_scoped_coverage_pct`(=100.0) / `non_escalation_governed_total`(=32) / `denominator_note` |
| 零退化 | 既有三欄位逐字不變（test 鎖定） |
| LOC 影響 | fsm_runtime.py +~25 行（常數 + additive 計算 + dict 欄位 + 註解）；遠低於紅線 |
| `.importlinter` 影響 | 無（同模組內，無新跨層 import） |
| TLC | **免跑**：transition_rules.py + 5 `*.tla`/`.cfg` 對 v0.16 逐位元零差異（Rule 9.18.1 不啟動） |

### W-39-3 — 缺陷帳本：開 DEF-39-001 + 更新 DEF-19-001 天花板達成

- **DEF-39-001（P3，框架指標設計缺陷）**：`catch_attribution_coverage` 分母混淆（39 含 32 條非-escalation 守門規則）→ fixed@improving_39（W-39-2 additive escalation-scoped 透明化）。
- **DEF-19-001**：更新——FSM-escalation catch 接線**達結構天花板 7/7=100%**；剩 32 條非 catch-可歸因（設計使然非缺口）。建議轉「milestone：escalation 機制覆蓋已完成；其他守門機制覆蓋度量另案」，是否正式收尾留 🔴 人工。

### B 軌 SCG 對應（Brownfield dogfooding）

- SCG-0/1（需求/設計凍結）＝本計畫書 §1/§2（活標的＝分母正當性）；SCG-2 架構＝<Architecture_Design_Review>（純度量、零拓樸變更）；SCG-3 契約＝additive 欄位 + SSOT 防漂移契約；SCG-4 實作 PR＝§3；SCG-5 RTM＝§6。
- **回流路徑**：DEF-39-001 屬「框架程式缺陷」。沿用 improving_37/38 dogfooding 慣例以**計畫書為 SCG-0/1 載體 + Copy-on-Evolve v0.17 + 缺陷帳本**（Rule 2/11；非另開 build/planning/active RFC——本輪為 additive 度量透明化、非規格/規則語意變更）。

---

## §3 階段三：實作與雙重驗證

逐項實作即測（開發-編譯-測試循環）：

1. **Copy-on-Evolve**：`scripts/copy_on_evolve.sh AISDLC_SDD_v0.16 AISDLC_SDD_v0.17` → **857 tracked 檔**（git archive 純 tracked，結構性排除 build/reports/ 等 runtime 產物，DEF-38-001）。**動工即補 .gitignore v0.17 block**（DEF-37-001 紀律）。
2. **W-39-2**：`_ESCALATION_ATTRIBUTABLE_RULE_IDS` 常數 + stats additive 欄位。冒煙驗證實測 `rules_total=39 / escalation_attributable=7 / escalation_scoped=100.0% / non_escalation=32`。
3. **新測試** `test_w39_coverage_denominator.py` **6 case 全綠**（0.32s）：
   - `test_escalation_attributable_registry_pins_seven`：正當分母 SSOT＝7 條；
   - `test_real_rules_escalation_scoped_coverage_is_100pct`：真實凍結規則 scoped=100%（天花板達成）；
   - `test_non_escalation_governed_breakdown_is_honest`：32 = 39−7 + note 含 DEF-39-001；
   - `test_legacy_coverage_fields_unchanged_zero_regression`：舊三欄位 7/39 不變；
   - `test_numerator_subset_of_legitimate_denominator`：attributed ⊆ escalation_attributable（DEF-18-001）；
   - **`test_registry_matches_wired_calls_no_drift`**：靜態掃描 `_record_escalation_catches([...])` == 註冊表（防漂移）。

---

## §4 階段四：CI 平價收斂（零退化驗證矩陣，全項實測）

| 檢查 | 命令 | 通過條件（floor=improving_38 實測） | 本輪實測 | 判定 |
|------|------|------|------|------|
| AutoClaude 全套 | `pytest tests/ -q` | ≥ 3221 passed / 0 failed | **3221 / 122 / 0**（未動 AutoClaude） | ✅ |
| 架構契約 | `lint-imports` | 全 kept / 0 broken | 8 kept / 0 broken（階段一基線） | ✅ |
| LOC 分級 | `check_loc_budget.py` | 全過 | violations=0（未動 AutoClaude） | ✅ |
| Snapshot | `snapshot_sync.py --check` | 新鮮 | FRESH（未動 AutoClaude） | ✅ |
| AISDLC_SDD 閘門 | `ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | exit 0；v0.01:1478 / **v0.17:1611** / scripts:44 | ✅ |
| DAL 等價 | equivalence | 三後端等價 | AutoClaude 未動，N/A | ✅ |
| 五軌 TLC | （僅 FSM 變更時） | 5 軌 0 violation | **免跑**：transition_rules.py + 5 `*.tla`/`.cfg` 對 v0.16 逐位元零差異 | ✅ |
| coverage 透明化 | runtime stats | escalation-scoped 揭露 | rules_total=39（不變）+ **escalation_scoped=100%（7/7）** + non_escalation=32 | ✅ |

> - v0.17:1611 = v0.16:1605 + 6 新 W-39 測試。
> - **flaky 排查**：full-suite 偶見 `test_file_lock.py::test_parallel_writes_do_not_lose_increments` FileNotFoundError（tmp 目錄競態）；隔離重跑 v0.16/v0.17 **皆通過**、ci-gate 獨立 process 下 1611 無失敗 → 既有環境性 flaky，**非本輪退化**（本輪僅動 stats 純函式 + 唯讀新測試）。
> - arch_fitness 僅既有 advisory warn（FF-16 GAP-X1/X2），非本輪新增，不阻擋；FF-17 確認 v0.17 自動入閘。

---

## §5 缺陷處置

- **DEF-39-001（P3，新增）→ fixed@improving_39**（W-39-2 escalation-scoped 透明化）。
- **DEF-19-001（P3）→ 進度更新**：FSM-escalation catch 接線達結構天花板 **7/7=100%**（escalation-scoped）；維持 **routed**，但標示「既有機制覆蓋完成、剩 32 條非 catch-可歸因」，是否正式收尾留 🔴 人工。
- **本輪無其他新增缺陷**（gitignore v0.17 block 動工即補，DEF-37-001 紀律未重演）。
- 未推進（維持原狀態）：DEF-32-002 / DEF-01-007 / DEF-01-009 / DEF-17-001（理由見 Defect_Log improving_39 收尾註記）。

---

## §6 RTM（需求可追溯矩陣）

| 需求 | 設計 | 實作 | 驗收 |
|------|------|------|------|
| 確立正當分母（分類調查）| §2 W-39-1 | Explore agent 機械分類 39 條 | 分類彙總表（7 escalation-attributable / 32 非）+ 實測 attributed=7 吻合 |
| escalation-scoped 透明化（DEF-39-001）| §2 W-39-2 | `_ESCALATION_ATTRIBUTABLE_RULE_IDS` + stats additive | `test_real_rules_escalation_scoped_coverage_is_100pct`（100%）/ `test_escalation_attributable_registry_pins_seven` |
| 誠實 breakdown | §2 W-39-2 | non_escalation_governed_total + denominator_note | `test_non_escalation_governed_breakdown_is_honest`（32=39−7, note 含 DEF-39-001）|
| 零退化（既有三欄位）| §2 設計#5 | additive-only | `test_legacy_coverage_fields_unchanged_zero_regression`（7/39 不變）|
| 不放寬接線門檻（DEF-18-001）| §2 設計#6 | numerator ⊆ 正當分母 | `test_numerator_subset_of_legitimate_denominator` |
| SSOT 防漂移 | §2 設計#8 | 靜態掃描接線集合 | `test_registry_matches_wired_calls_no_drift` |

---

## §7 結案證據契約（closure-evidence，反幻覺機械閘門 DEF-20-001）

```yaml
closure-evidence:
  base_sha: 0936eaff83741af9e5359327f803d7314019e2bd  # 本輪所建之上的 HEAD（improving_38 收尾後）
  claimed_commits:
    - 41560b5b9c17c8cb8a209698e909b3041d4a65fa
  claimed_tag: v2026.06.18-37
  pytest:
    autoclaude: "3221 passed / 122 skipped / 0 failed（未動）"
    aisdlc_sdd_v0_17: "1611 passed / 4 skipped / 0 failed"
    scripts_tests: "44 passed"
  ci_gate: "exit 0; v0.01:1478 / v0.17:1611 / scripts:44"
  catch_coverage: "rules_total=39（不變）; escalation_scoped=100% (7/7); non_escalation=32"
  tlc: "N/A — transition_rules.py + 5 *.tla/.cfg 對 v0.16 逐位元零差異"
```
