# AutoSDD_improving_38 — B 軌 dogfooding：DEF-19-001 catch 歸因覆蓋 5/39 → 7/39

> **軌道①整合迭代 第 38 輪**。本輪主柱＝**B 軌（手腳 AISLDC_SDD framework dogfooding）**。
> 🔴 掌舵者 AskUserQuestion 兩問拍板：(Q1) 主柱＝**B 軌續 DEF-19-001**；(Q2) 幅度＝**2–3 W 項**。
> 框架本體改進落 **Copy-on-Evolve `AISDLC_SDD_v0.16/`**（v0.15 凍結唯讀）。
> 北極星對齊：B 流程自治（SDD catch 歸因覆蓋率漸進補強，鷹架代謝 ROI 雙側信號朝可信退役門檻邁進）。

---

## §0 本輪定位（防跨軌誤指）

| 項目 | 內容 |
|------|------|
| 軌道 | ① 整合迭代，**B 柱（手腳）** |
| 活標的 | **DEF-19-001**（catch 歸因覆蓋漸進補強，P3，routed） |
| 為何非 C 軌 | C 軌 SD_09 **W1 正式執行輪因 06-26 G0 閘門未開而 blocked**（今 2026-06-18），不啟 W1/不跑 mutmut/不偽造 nightly |
| 下一份 | improving_39（按需） |
| 框架版本 | v0.15 → **v0.16**（Copy-on-Evolve） |

---

## §1 階段一：現況重偵察（Zero-Trust Re-Audit，實測）

派 Explore agent 重新實測（禁引文件宣稱值）：

| 項目 | 實測值 | 判定 |
|------|--------|------|
| AutoClaude `pytest tests/ -q` | **3221 passed / 122 skipped / 0 failed** | ✅ HARD GATE PASS（= floor，0 failed） |
| `lint-imports` | 8 kept / 0 broken | ✅ |
| `check_loc_budget.py` | violations=0（18506 < 20438） | ✅ |
| `snapshot_sync.py --check` | FRESH | ✅ |
| AISDLC_SDD `ci-gate.sh` | exit 0；v0.01:1478 / v0.15:1597 / scripts:42 | ✅ |
| 最新框架版 | **v0.15** | ✅ |
| DEF-19-001 | routed，catch 覆蓋 **5/39**（剩 34，活標的重現） | ✅ |

已接線 5 條：R-9.1 / R-9.2 / R-9.7(9.7.2) / R-9.21 / R-9.22。核心機制 [fsm_runtime.py:222](../../AISDLC_SDD/AISDLC_SDD_v0.16/tools/fsm_runtime/fsm_runtime.py) `_record_escalation_catches()`、coverage 計算於 :1766（`rules_with_failure_mode / rules_total`）。

**生產 escalation 落點全盤點**（fsm_runtime.py，8 個 `record_escalation`）：

| 落點 | 規則 | 狀態 |
|------|------|------|
| line 249（HUMAN_PENDING timeout） | R-9.7 | ✅ 已接線 |
| line 358（gate retry 耗盡） | R-9.1 | ✅ 已接線 |
| **line 416（SPEC_AUDIT 耗盡）** | **R-9.3** | ❌ 缺 failure_mode → **本輪 W-38-2** |
| line 509（implementation budget exceeded） | 無規則 | 正交、不接（明文排除） |
| line 585（auto_compact per-stage 超限） | R-9.2 | ✅ 已接線 |
| **line 1875（sandbox policy_violation）** | **R-SELF-STRIDE** | ❌ 缺 failure_mode → **本輪 W-38-1** |
| line 1998（monitor violation） | R-9.21 | ✅ 已接線 |
| line 2349（spec_patch per-AC 上限） | R-9.22 | ✅ 已接線 |

> **盤點校正**：偵察 agent 初判「無乾淨候選」（因 R-9.3/R-SELF-STRIDE 缺 failure_mode）——但「缺 failure_mode」正是 improving_37 對 R-9.7 所補的工，非排除理由。親驗確認兩條皆有**唯一生產落點**且可定義**無歧義 failure_mode**。

---

## §2 階段二：本輪增量設計（2 W 項，5/39 → 7/39）

### <Architecture_Design_Review>

1. **架構純潔性**：無 God-object。catch 接線沿用既有 helper `_record_escalation_catches()`，於既有 `record_escalation` 呼叫點疊加，不新增方法、不改控制流。
2. **持久化相容**：catch 記帳僅 `scaffold_roi.catch_count += 1`（既有 additive 欄位），不寫 FSM-STATE、不新增狀態/轉換、零新增 reachable 邊。
3. **安全防護網**：本輪不涉 CONDITIONAL 指令生成路徑（純規則 yaml + escalation 記帳）。
4. **對外 I/O 安全**：本輪不新增 `ToolInvocationPort` 外呼路徑。
5. **零退化開關**：flag `SDD_ENABLE_RULE_CATCH_TELEMETRY` 預設 OFF＝行為逐位元同 v0.15；`_record_escalation_catches` fail-closed（記帳失敗不阻塞已落定 escalation）。
6. **DEF-18-001 寧缺勿濫**：只接「唯一生產落點 + 可定義 failure_mode + 無雙重歸因」；R-9.3 的 failure_mode 明文排除正交落點（同 R-9.7「僅 9.7.2」範式）。
7. **紅線**：只增 catch_count、**永不 set_maturity**（R-9.20 #11，退役仍 🔴 人工）；不碰 meta⁹/meta-oracle；不提 Token 上限。

### W-38-1 — R-SELF-STRIDE catch 接線（5/39 → 6/39）

| 項目 | 內容 |
|------|------|
| 落點 | [fsm_runtime.py:1875](../../AISDLC_SDD/AISDLC_SDD_v0.16/tools/fsm_runtime/fsm_runtime.py) `exit_sandbox_hardening_gate` 的 `verdict=="policy_violation"` 分支 |
| 介面 delta | `R-SELF-STRIDE.yaml` 補 `failure_mode`；該分支 `record_escalation` 後接 `_record_escalation_catches(["R-SELF-STRIDE"])` |
| 無歧義論證 | **唯一生產落點**（`verdict=="pass"` 轉 EXECUTION_EVALUATION、不 escalate 不歸因）；與既有 5 條零交集（無人觸碰 SANDBOX_HARDENING_GATE） |
| LOC 影響 | +1 行呼叫 + 註解；fsm_runtime.py 仍遠低於紅線 |
| `.importlinter` 影響 | 無（同模組內，無新跨層 import） |

### W-38-2 — R-9.3 catch 接線（6/39 → 7/39）

| 項目 | 內容 |
|------|------|
| 落點 | [fsm_runtime.py:416](../../AISDLC_SDD/AISDLC_SDD_v0.16/tools/fsm_runtime/fsm_runtime.py) `record_spec_audit` 的 `spec_audit_count ≥ SPEC_AUDIT_MAX_PER_STAGE` 分支 |
| 介面 delta | `R-9.3-logical-consistency-guard.yaml` 補 `failure_mode`；該分支 `record_escalation` 後接 `_record_escalation_catches(["R-9.3"])` |
| 無歧義論證 | failure_mode **明文僅涵蓋 record_spec_audit SPEC_AUDIT 耗盡落點**，排除 (a) line 509 implementation-budget-exceeded 直接 escalate（正交、無規則承載）、(b) R-9.1 gate-retry 落點（line 358），杜絕雙重歸因 |
| LOC 影響 | +1 行呼叫 + 註解 |
| `.importlinter` 影響 | 無 |

### B 軌 SCG 對應（Brownfield dogfooding）

- SCG-0/1（需求/設計凍結）＝本計畫書 §1/§2；SCG-2 架構＝<Architecture_Design_Review>（純記帳、零拓樸變更）；SCG-3 契約＝catch 三要件契約（沿用 improving_19/20/37）；SCG-4 實作 PR＝§3；SCG-5 RTM＝§6。

---

## §3 階段三：實作與雙重驗證

逐項實作即測（開發-編譯-測試循環）：

1. **Copy-on-Evolve**：`scripts/copy_on_evolve.sh AISDLC_SDD_v0.15 AISDLC_SDD_v0.16` → 856 tracked 檔、零 runtime cruft、FSM 種子模板在位（`git add -A -n` would-add 856 零殘留）。
2. **W-38-1**：R-SELF-STRIDE.yaml + fsm_runtime.py line 1875 接線。
3. **W-38-2**：R-9.3 yaml + fsm_runtime.py line 416 接線。
4. **新測試** `test_w38_catch_wiring.py` **8 case 全綠**（0.31s）：
   - R-SELF-STRIDE：flag ON catch+1 / flag OFF 零退化 / **非重疊守門：verdict=pass 不歸因**；
   - R-9.3：flag ON catch+1 / flag OFF 零退化 / **非重疊守門：implementation-budget-exceeded 落點不歸因 R-9.3**；
   - 真實凍結 R-SELF-STRIDE / R-9.3 各具非空 failure_mode。
5. **coverage 實測**：`rule_fire_telemetry_stats().safety_certificate.catch_attribution_coverage` = **7 / 39**（5→7）。

---

## §4 階段四：CI 平價收斂（零退化驗證矩陣，全項實測）

| 檢查 | 命令 | 通過條件（floor=improving_37 實測） | 本輪實測 | 判定 |
|------|------|------|------|------|
| AutoClaude 全套 | `pytest tests/ -q` | ≥ 3221 passed / 0 failed | **3221 / 122 / 0** | ✅ |
| 架構契約 | `lint-imports` | 全 kept / 0 broken | 8 kept / 0 broken（AutoClaude 未動，階段一基線） | ✅ |
| LOC 分級 | `check_loc_budget.py` | 全過 | violations=0（AutoClaude 未動） | ✅ |
| Snapshot | `snapshot_sync.py --check` | 新鮮 | FRESH（AutoClaude 未動） | ✅ |
| AISDLC_SDD 閘門 | `ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | exit 0；v0.01:1478 / **v0.16:1605** / scripts:42 | ✅ |
| DAL 等價 | equivalence | 三後端等價 | AutoClaude 未動，N/A 變更 | ✅ |
| 五軌 TLC | （僅 FSM 變更時） | 5 軌 0 violation | **免跑**：`transition_rules.py`+5 `*.tla`/`.cfg` 對 v0.15 逐位元零差異（Rule 9.18.1 不啟動） | ✅ |
| catch coverage | runtime stats | 5/39 → 7/39 | **7 / 39** | ✅ |

> arch_fitness 僅既有 advisory warn（FF-16 GAP-X1 元迴圈接地 / GAP-X2 GC 從未退役），非本輪新增，不阻擋。

---

## §5 缺陷處置

- **DEF-19-001（P3）→ 進度更新 5/39 → 7/39**，維持 **routed**（剩 32 規則續漸進）。
- **本輪無新增缺陷**（DEF-37-001 gitignore block 動工即補 v0.16 block，未漏）。
- 未推進（維持原狀態）：DEF-32-002 / DEF-01-007 / DEF-01-009 / DEF-17-001（理由見 Defect_Log improving_38 收尾註記）。

---

## §6 RTM（需求可追溯矩陣）

| 需求 | 設計 | 實作 | 驗收 |
|------|------|------|------|
| DEF-19-001 catch +1（R-SELF-STRIDE） | §2 W-38-1 | R-SELF-STRIDE.yaml `failure_mode` + fsm_runtime.py:1875 catch | `test_w38_catch_wiring.py::test_rselfstride_catch_on_policy_violation_flag_on`（catch+1） |
| 零退化（flag OFF＝v0.15） | §2 設計#5 | flag-gated catch | `test_rselfstride_catch_flag_off_zero_regression` |
| 非重疊守門（R-SELF-STRIDE） | §2 W-38-1 無歧義論證 | verdict=pass 不接線 | `test_rselfstride_not_attributed_on_sandbox_pass` |
| DEF-19-001 catch +1（R-9.3） | §2 W-38-2 | R-9.3.yaml `failure_mode` + fsm_runtime.py:416 catch | `test_r93_catch_on_spec_audit_exhaustion_flag_on`（catch+1） |
| 零退化（flag OFF） | §2 設計#5 | flag-gated catch | `test_r93_catch_flag_off_zero_regression` |
| 非重疊守門（R-9.3 雙排除） | §2 W-38-2 無歧義論證 | implementation-budget 落點不接線 | `test_r93_not_attributed_on_implementation_budget_exceeded` |
| 真實規則具 failure_mode | §2 DEF-18-001 要件① | 凍結 yaml | `test_real_rule_rselfstride_has_failure_mode` / `test_real_rule_r93_has_failure_mode` |

---

## §7 結案證據契約（closure-evidence，反幻覺機械閘門 DEF-20-001）

```yaml
closure-evidence:
  base_sha: 376a5119deee3aa88bba7dc07cd19f024b0ccb4e
  claimed_commits:
    - 376a5119deee3aa88bba7dc07cd19f024b0ccb4e
  claimed_tag: v2026.06.18-36
  pytest:
    autoclaude: "3221 passed / 122 skipped / 0 failed"
    aisdlc_sdd_v0_16: "1605 passed / 4 skipped / 0 failed"
    scripts_tests: "42 passed"
  ci_gate: "exit 0; v0.01:1478 / v0.16:1605 / scripts:42"
  catch_coverage: "7/39"
  tlc: "N/A — transition_rules.py + 5 *.tla/.cfg 對 v0.15 逐位元零差異"
```
