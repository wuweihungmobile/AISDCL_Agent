# AutoSDD_improving_37 — B 軌 dogfooding：DEF-19-001 catch 歸因覆蓋 4/39 → 5/39（R-9.7）

> 驅動器：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`（軌道① 整合迭代範本）。
> 凍結來源續 improving_36（C 軌 SD_09 W1 前置必修 DEF-35-001 fixed，tag v2026.06.18-34）。

---

## 0. 本輪定位與防跨軌誤指

| 項目 | 內容 |
|------|------|
| **本輪主柱** | **B 軌（手腳 AISLDC_SDD framework dogfooding / 缺陷漸進清償）** |
| **🔴 掌舵者 signoff** | ① 主柱定調＝B 軌（AskUserQuestion 第一問，於「A 軌 DEF-32-002 / B 軌 DEF-23-005 或 DEF-19-001 / 暫不開輪 / C 軌 Agent Console」中選 **B 軌**）；② 推進幅度＝「+2（R-9.7+R-9.9）」（第二問），授權「R-9.9 驗出歧義則降 +1」 |
| **下一份** | improving_38（按需；建議：06-26 G0 開後轉 C 軌 SD_09 W1 正式執行輪，或續 DEF-19-001 catch 漸進） |
| **框架版本** | v0.14 → **v0.15**（Copy-on-Evolve；改動全落凍結本體 governance/rules + tools/fsm_runtime + .claude/hooks） |
| **zero-trust 校正** | 掌舵者提供的「DEF-23-005 或 DEF-19-001」中，**DEF-23-005 經親驗已 `fixed@improving_30`**（總表第 67 行），本輪實際活標的＝DEF-19-001 |

---

## 1. 階段一：現況重偵察（Zero-Trust Re-Audit，硬閘通過）

三路並行 Explore/general-purpose agent 實測，所有後續設計只錨定本節事實：

| 檢查 | 命令 | 實測 | 判定 |
|------|------|------|------|
| AutoClaude 全套 | `pytest tests/ -q` | **3221 passed / 122 skipped / 0 failed**（110.93s） | ✅ = 上輪 floor 3221、0 failed |
| 架構契約 | `lint-imports` | 8 kept / 0 broken | ✅ |
| LOC 分級 | `check_loc_budget.py` | violations=0 | ✅ |
| Snapshot | `snapshot_sync.py --check` | OK 新鮮 | ✅ |
| AISDLC_SDD 閘門 | `ci-gate.sh` | exit 0；v0.01:1478 / v0.14:1593 / scripts:42；arch_fitness 0 fail / 3 advisory warn | ✅ 全綠 |

**硬閘通過**：基線 ≥ 3221 passed 且 0 failed，准進階段二。

**缺陷帳本 open/routed 複驗**：DEF-23-005 已 fixed@improving_30（含 ci-gate 實跑輸出「✅ RFC 生命週期 lint」佐證掛載——糾正偵察 agent 因只看前 120 行的「待確認」誤判）；DEF-19-001 維持 routed 4/39。

### DEF-19-001 程式碼定位（實測 file:line）
- coverage 計算：`fsm_runtime.py:1752` `attributed_rule_ids = sorted(r.id for r in rules if r.failure_mode)`。
- 既有 4/39 接線：R-9.1（gate-retry，`:344`）、R-9.2（auto_compact，`:571`）、R-9.21（monitor，`:1984`）、R-9.22（spec_patch，`:2335`），皆 `_record_escalation_catches([...])`（def `:222`，flag-gated `SDD_ENABLE_RULE_CATCH_TELEMETRY` 預設 OFF）。
- active 規則總數＝39。

---

## 2. 階段二：增量設計（W-37-1）

### <Architecture_Design_Review>
1. **架構純潔性**：不創 God-object；新增 ~12 行 thin 方法 `escalate_human_pending_timeout`，與 `trigger_auto_compact`/`enter_spec_patch_proposal` 同層同範式（catch 接在 record_escalation 落點）。hook 由 inline `record_escalation` 改委派該方法＝控制流收斂。
2. **持久化相容**：純記帳（catch_count 只增），無 FSM 狀態副作用、零新增 reachable 邊、不碰 `*.tla`；flag 預設 OFF＝行為逐字同 v0.14。免五軌 TLC（Rule 9.18.1 不啟動）。
3. **安全防護網**：不涉 CONDITIONAL／shell；fail-closed（記帳失敗不回滾已落定 escalation）。
4. **對外 I/O 安全**：不新增 `ToolInvocationPort` 外呼路徑，N/A。

### 2.1 W-37-1 設計（介面 delta）
| 構件 | 變更 | 性質 |
|------|------|------|
| `governance/rules/R-9.7-precise-halt-m1.yaml` | 補 `failure_mode` 欄位，**明文僅涵蓋 9.7.2**（HUMAN_PENDING 逾時 ≥168h） | additive |
| `tools/fsm_runtime/fsm_runtime.py` | 新增 `escalate_human_pending_timeout(reason=...)`：record_escalation + flag-gated `_record_escalation_catches(["R-9.7"])` | additive 方法 |
| `.claude/hooks/session_start.py` | ACT-023 逾時 ESCALATION 分支 inline `rt.state.record_escalation(reason)` → 委派 `rt.escalate_human_pending_timeout(reason=reason)` | 1 行 surgical（行為等價＋flag-gated catch） |
| `tools/fsm_runtime/tests/test_w37_catch_wiring.py` | 新增 4 case | 新測試檔 |
| `AISDLC_SDD/.gitignore` | 新增 v0.15 runtime 產物排除 block（共享 infra，免 Copy-on-Evolve） | additive |

### 2.2 無歧義映射紀律（DEF-18-001 核心）
- R-9.7 的 `failure_mode` **只描述 9.7.2**；明文排除 **9.7.3**（AUTO_COMPACT per-stage 超限）——其 escalate 落點（`trigger_auto_compact`）歸 **R-9.2**，杜絕雙重歸因。
- 守門測試 `test_r97_not_attributed_on_auto_compact_overflow` 鎖死：走 9.7.3 路徑時只 R-9.2 catch+1、R-9.7 恆 0。

### 2.3 R-9.9 降級（誠實 scope，Rule 12）
親驗 R-9.9 **無唯一生產 escalation 落點**：
- state_loader 損毀路徑為 `raise ValueError`（:313）/`FileNotFoundError`（:318），**不呼叫 record_escalation**；.bak 可用則靜默恢復。
- chaos_runner 的 ~20+ record_escalation（:1454~1706+）屬**測試載具**模擬其他規則的失敗模式，歸 R-9.9 即類別錯誤雙重歸因。

R-9.9 本質為「chaos 驗收有界停機」之 meta 性質，非帶唯一落點的 runtime 失敗模式 → 依 DEF-18-001 寧缺勿濫**不接**（掌舵者預授權 fallback）。本輪淨增 **4/39 → 5/39**。

---

## 3. 階段三：實作與雙重驗證

- Copy-on-Evolve：`git archive HEAD:AISDLC_SDD/AISDLC_SDD_v0.14` 匯出 **855 tracked 檔**（零 runtime cruft、build/reports 未帶入、FSM 種子模板於 tools/fsm_runtime/templates/ 保留）。
- v0.15 bootstrap 基線（改動前）＝ **1593 / 4 / 0**（= v0.14，複製健全）。
- 新測試單跑：`test_w37_catch_wiring.py` **4 passed**（含非重疊守門）。
- v0.15 全套（改動後）：**1597 passed / 4 skipped / 0 failed**（1593 + 4，只增不減；coverage 4→5 無既有測試硬編而破）。

---

## 4. 階段四：CI 平價收斂（零退化矩陣）

| 檢查 | 命令 | 通過條件（floor=improving_36 實測） | 本輪實測 | 判定 |
|------|------|-----------------|---------|------|
| AutoClaude 全套 | `pytest tests/ -q` | ≥ 3221 / 0 failed | 3221/122/0（階段一；AutoClaude 本輪零觸碰，`git status --porcelain AutoClaude`=0） | ✅ |
| 架構契約 | `lint-imports` | 全 kept / 0 broken | 8/0（階段一，未動） | ✅ |
| LOC 分級 | `check_loc_budget.py` | 全過 | violations=0（階段一，未動） | ✅ |
| Snapshot | `snapshot_sync.py --check` | 新鮮 | OK（階段一） | ✅ |
| AISDLC_SDD 閘門 | `ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | exit pass；v0.01:1478 / **v0.15:1597** / scripts:42；FF-17 動態納入 v0.15；arch_fitness advisory only | ✅ |
| DAL 等價 | — | 三後端等價 | N/A（未動 AutoClaude DAL） | N/A |
| 五軌 TLC | 僅 FSM 變更時 | 五軌 0 violation | N/A（`transition_rules.py`+5 `*.tla`/`.cfg` 對 v0.14 逐位元零差異） | N/A |
| 潔淨度 | `git add -A -n` | 無 runtime/stale 入庫 | cruft=0；would-add=856（855 archived + 1 新測試）；.gitignore v0.15 block 已補 | ✅ |

---

## 5. 缺陷處置

| 缺陷 | 處置 |
|------|------|
| **DEF-19-001**（catch 漸進覆蓋） | **進度更新：4/39 → 5/39**（W-37-1 接 R-9.7·9.7.2）；維持 **routed**（剩 34 規則續漸進；生產全面啟用退役前須提升覆蓋率至可接受門檻） |
| **DEF-37-001**（新增，P3，routed） | Copy-on-Evolve 新版 `.gitignore` block 缺漏無自動偵測——本輪建 v0.15 後 ci-gate 跑出 11 筆 runtime 產物入 would-add，須手動補 v0.15 block 才潔淨。屬 DEF-23-005 deferred 的「gitignore block 缺漏偵測」部分之具體復發。routed B 軌未來輪（可於 `rfc_lifecycle_lint`/ci-gate 增「最新版缺 gitignore block 即 warn」） |
| 其餘 open/routed | DEF-32-002（A 軌刻意 scope）、DEF-01-007（cc-switch 環境缺裝）、DEF-01-009（LOC watch，本輪零動 sdd_governance_plugin）、DEF-17-001（遙測 routed）：本輪未動，維持原狀態 |

---

## 6. RTM（需求可追溯矩陣）

| 需求 | 設計 | 實作 | 驗證 |
|------|------|------|------|
| DEF-19-001 catch 覆蓋 +1（R-9.7·9.7.2） | §2.1 escalate_human_pending_timeout + R-9.7 failure_mode | `fsm_runtime.py` 方法 / `R-9.7.yaml` / `session_start.py` 委派 | `test_w37_catch_wiring.py::test_r97_catch_on_human_pending_timeout_flag_on`（catch+1） |
| 零退化（flag OFF 行為同 v0.14） | flag-gated 純記帳 | `_record_escalation_catches` flag 守門 | `::test_r97_catch_flag_off_zero_regression`（catch 0） |
| 無歧義映射（不雙重歸因 9.7.3） | §2.2 failure_mode 僅 9.7.2 | R-9.7 yaml 明文排除 | `::test_r97_not_attributed_on_auto_compact_overflow`（R-9.2=1, R-9.7=0） |
| 凍結本體自描述 failure_mode | §2.1 | R-9.7 yaml | `::test_real_rule_r97_has_failure_mode` |

---

## 7. 結案

W-37-1 完成；DEF-19-001 推進 4/39 → 5/39；R-9.9 誠實降級；新增 DEF-37-001 入帳。零退化矩陣全項 PASS／N/A（無退化、契約 kept、TLC 不觸發）。多專家 zero-trust 審查見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_37.md`。
