# AutoSDD_improving_02 — AISDLC-SDD × AutoClaude 深度整合執行計畫（第 2 輪）

> **版本**：02（第二輪迭代）
> **日期**：2026-06-13
> **作者**：Dr. Alan（L5 自治系統與微核心架構總監）
> **狀態**：✅ **已凍結**（2026-06-13 🔴 人工確認：使用者於本日 session 明示「確認凍結，啟動 W1」，W1 准予啟動）。
> **絕對前提**：零退化（Zero-Regression）— AutoClaude 基線 **3060 passed / 122 skipped**（2026-06-13 本機實測 98.42s，**非引用文件數字**；Improving_012 在軌道③ 將 01 輪收尾 2843 推進至 3060）；AISDLC_SDD `ci-gate.sh` 必須全綠。
> **本輪選定範圍**：演化型（FSM/TLC）。**W1** = `AUTOCLAUDE_DELEGATED` 觀察態落地（improving_01 §6 Phase Z 提案）→ Copy-on-Evolve **v0.03** + `SDD_FSM.tla` 同步 + 五軌 TLC 全綠；**W2** = DEF-01-004（ci.yml pg-e2e cron 過濾）。

---

## 0. 階段一 Zero-Trust 重偵察實測事實基線（2026-06-13，非文件宣稱）

本計畫所有設計皆錨定下列**已實測事實**（出處：2026-06-13 親自實測 + 逐檔開檔複驗）：

| # | 事實 | 證據位置 | 對設計的影響 |
|---|------|---------|------------|
| F1 | AutoClaude 全套 = **3060 passed / 122 skipped / 0 failed**（98.42s） | 本機 `python -m pytest tests/ -q` | 本輪零退化 floor = 3060（禁寫死） |
| F2 | `lint-imports` = **8 kept / 0 broken**（01 輪為 7，Improving_012 增 `IKbMetricStore` 隔離契約 +1） | `PYTHONUTF8=1 lint-imports` | 架構紅線，以實際 8 條為準、不寫死 |
| F3 | AISDLC_SDD `ci-gate.sh` = **全數通過**（exit 0；arch_fitness 僅 advisory warn 不阻擋） | `bash scripts/ci-gate.sh` | B 軌基線綠 |
| F4 | `check_loc_budget` violations=0；`snapshot_sync --check` 新鮮 | 本機實測 | 既有紅線無欠帳 |
| F5 | 01 構件全部存在（spec_source / sdd_to_playbook_adapter / sdd_governance_plugin / sdd_compile / error_classifier） | 存在性掃描 | 01 交付未腐爛 |
| F6 | `_HAPPY_PATH` 觀測態落地模式：① `_HAPPY_PATH` 加 key（僅出邊）② `OBSERVATION_STATES` frozenset 加成員 ③ **不**改來源態出邊集（入口走 runtime `enter_xxx()`）④ 不入 `_EMERGENCY_TARGETS` | `transition_rules.py:101`（EVALUATOR_AUDIT key 僅出邊）、`:214-229`（OBSERVATION_STATES）、`:59-60`（EXECUTION_EVALUATION 出邊集**不含** EVALUATOR_AUDIT） | W1 落地的精確模式範本 |
| F7 | `AUTOCLAUDE_DELEGATED` 現況**不存在**於 `_HAPPY_PATH` / `OBSERVATION_STATES` / `SDD_FSM.tla` | grep 三檔 0 命中（v0.02） | W1 為真缺口 |
| F8 | `.tla` 結構錨點：`HappyStates`(L50)、`ObservationStates`(L65，15 員含 AUTO_RECOVERY_ATTEMPT)、`EmergencyStates`(L83)、`Terminals`(L91)、`States`(L97)、`Next`(L516)、`Fairness`(L600) | `formal/SDD_FSM.tla` | W1 .tla 同步落點 |
| F9 | py `OBSERVATION_STATES`（14 員）與 .tla `ObservationStates`（15 員）為既有非對稱（.tla 多列 AUTO_RECOVERY_ATTEMPT）；**非本輪缺陷**，記為偵察事實避免誤判 | `transition_rules.py:214-229` vs `SDD_FSM.tla:65-81` | 不在本輪修補範圍；新增 AUTOCLAUDE_DELEGATED 須在兩處皆登記以免擴大非對稱 |
| F10 | 五軌 TLC 由 `tlc_runner.py --module {SDD_FSM,META_FSM,FLEET_FSM,COMPOSITION_FSM,OPTIMIZATION_FSM}` 驅動；ci-gate.sh 迴圈呼叫 | `tlc_runner.py:90-94` | W1 (c) 驗證載體 |
| F11 | `ID_REGISTRY.yaml` next_free：**act=172 / rule="9.39"** | `governance/ID_REGISTRY.yaml:23-25` | AUTOCLAUDE_DELEGATED 取 **ACT-172**；本輪不需新 R-rule（state 受 R-9.18 既有規則治理） |
| F12 | DEF-01-004 仍重現：`ci.yml:189` pg-e2e `if: github.event_name == 'schedule' \|\| workflow_dispatch`，無 `github.event.schedule` cron 過濾；對照 perf-baseline(:442)、mutation(:279) 皆有過濾 | `.github/workflows/ci.yml:189,279,442` | W2 缺口屬實 |
| F13 | v0.02 已凍結（releases/CHANGELOG `[v0.02] 2026-06-12`，Copy-on-Evolve 自 v0.01）；`AUTOCLAUDE_DELEGATED` 維持提案 | `AISDLC_SDD_v0.02/releases/CHANGELOG.md`、`EVOLUTION_LOG.md` | 本輪 FSM 演化落 **v0.03**（複製 v0.02） |

**硬閘判定**：F1 基線 0 failed 且 3060 ≥ 上輪收尾 2843 → **通過，准進階段二**。

**繼承缺陷處置（見 §7）**：DEF-01-004（本輪 W2 修）、DEF-01-007（cc-switch，環境工具，續 watch）、DEF-01-008（main.py brain 注入，本輪不取、續 routed）、DEF-01-009（plugin 250 行 watch，本輪不擴充該檔、無觸發）。

---

## 1. `<Architecture_Design_Review>`（寫任何實質程式前強制自我檢核）

> 本輪 W1 主體為 **AISDLC_SDD 框架側 FSM 演化**（v0.03），W2 為 CI YAML 單檔。AutoClaude 微核心側**零程式碼改動**，故四問以「不破壞既有架構」為核心。

### 1.1 架構純潔性 — 是否創造 God-object？Thin Facade 是否維持？

**否，且維持。** W1 完全落在 AISDLC_SDD `tools/fsm_runtime/` 與 `formal/`，與 AutoClaude 微核心（`core/`/`plugins/`/`playbook_runner.py`）**零交集**——`playbook_runner.py` 一行不改、不新增任何 plugin/port/adapter。`AUTOCLAUDE_DELEGATED` 落地採 F6 既有觀測態加法式模式（`transition_rules._HAPPY_PATH` 加單一 key + `OBSERVATION_STATES` 加單一成員 + `fsm_runtime.enter_autoclaude_delegated()` 比照既有 `enter_evaluator_audit()` forced-transition），不新增類別、不改既有狀態語意，無 God-object。

### 1.2 持久化相容 — 新狀態是否 additive？DAL 三後端零停機是否維持？

**是，且維持。** W1 不觸碰 AutoClaude `PlaybookCheckpoint`／DAL 三後端（FSM 狀態持久化走 AISDLC_SDD 自有 `state_loader` 的 `FSM-STATE-{project}.yaml`，與 AutoClaude checkpoint 為兩套獨立機制）。`AUTOCLAUDE_DELEGATED` 是 FSM 狀態字串，純加法寫入 `_HAPPY_PATH`/`OBSERVATION_STATES`/`.tla` 集合——舊狀態檔載入時不受影響（無此狀態的專案 decision_trace 不變）。AutoClaude 側 `sdd_governance` 欄位 schema **零改動**。

### 1.3 安全防護網 — CONDITIONAL 白名單能否攔截鏈式攻擊向量？

**N/A 且零弱化。** 本輪不新增任何「從文件生成指令」的路徑（W1 是 FSM 狀態集合擴充，W2 是 CI 觸發條件），CONDITIONAL 三層防禦（白名單 regex + 黑名單字元 + shell=False/shlex）與 adapter `_sanitize` **一行不改**。新增的觀測態為**非阻塞**（`OBSERVATION_STATES`，`assert_tool_allowed` 以 `_EMERGENCY_TARGETS` 為 deny 清單，新觀測態不入 deny），不放寬任何既有 deny。

### 1.4 對外 I/O 安全 — 本輪是否新增 `ToolInvocationPort` 外呼路徑？

**否。** W1/W2 皆不新增任何 Web/HTTP/訊息外呼路徑，`ToolInvocationPort` 零觸碰，allowlist 預設 deny 不受影響，無 SSRF 攻擊面變化。

**結論：四項檢核全數自洽，無架構衝突，准予進入設計細節。**

---

## 2. W1 設計 — `AUTOCLAUDE_DELEGATED` 觀察態落地（Copy-on-Evolve v0.03）

### 2.1 語意與 FSM 邊界

`AUTOCLAUDE_DELEGATED` = 「IMPLEMENTATION 期間，SDD 把實作子任務委派給 AutoClaude playbook 引擎執行」的**非阻塞觀測態**。對齊 improving_01 §6 與 BRIDGE.md §5 落地前置條件：

- **入邊**：自 `IMPLEMENTATION` 經 runtime `enter_autoclaude_delegated()`（forced-transition，比照 `enter_evaluator_audit()`；**不**改 IMPLEMENTATION 的 `_HAPPY_PATH` 出邊集——符合 F6 觀測態入口慣例）。
- **出邊**：`{IMPLEMENTATION, ESCALATION}`——
  - `delegation_done` → `IMPLEMENTATION`（委派完成，帶回 resume，沿用 JumpKeep 記 resume_state 模式）；
  - `delegation_failed` → `ESCALATION`（AutoClaude 側演化亦失敗 / 越閘 → 升級，ESCALATION 屬 `_EMERGENCY_TARGETS` 恆允許）。
- **不變量**：`AUTOCLAUDE_DELEGATED ∈ OBSERVATION_STATES`、`∉ Terminals`、`∉ _EMERGENCY_TARGETS`（守 Rule 9.18.4 ObservationStates ∩ Terminals = ∅）。

### 2.2 三處同步 delta（缺一不可，Rule 9.18.1 雙源紀律）

**(a) `transition_rules.py`（v0.03）**

```python
# _HAPPY_PATH 新增 key（僅出邊；入口走 runtime enter_*，故不改 IMPLEMENTATION 出邊集）
"AUTOCLAUDE_DELEGATED": {"IMPLEMENTATION", "ESCALATION"},   # ACT-172

# OBSERVATION_STATES frozenset 新增成員
"AUTOCLAUDE_DELEGATED",   # ACT-172 SDD→AutoClaude 委派執行觀測態（Phase Z 落地）
```

**(b) `fsm_runtime.py`（v0.03）** — 新增 `enter_autoclaude_delegated(resume_state)`，比照既有 `enter_evaluator_audit()` 的 forced-transition + decision_trace 記錄機制（實作期開檔對齊精確簽名與 resume 寫法）。

**(c) `formal/SDD_FSM.tla`（v0.03）** — 四點同步：
1. `ObservationStates`（L65）集合加 `"AUTOCLAUDE_DELEGATED"  \* Phase Z / ACT-172`；
2. 入口 action `T_EnterAutoclaudeDelegated == state = "IMPLEMENTATION" /\ state' = "AUTOCLAUDE_DELEGATED" /\ ...`（JumpKeep 記 resume）；
3. 出口 `T_AutoDelegToImpl == JumpKeep("AUTOCLAUDE_DELEGATED", "IMPLEMENTATION")`、`T_AutoDelegToEsc == Move("AUTOCLAUDE_DELEGATED", "ESCALATION")`；
4. 加入 `Next ==`（L516）disjunction；
5. **Fairness**（L600）：新 2-cycle `IMPLEMENTATION ↔ AUTOCLAUDE_DELEGATED` 須加 `SF_vars(T_AutoDelegToImpl)` 保證離開觀測態（比照 L127 `SPEC_PATCH_PROPOSAL↔EXPERIMENT_REPLAY` 2-cycle 由 `SF_vars(T_SpecPatchToHuman)` 破環之先例），確保 `EventuallyTerminal` liveness 不被新增 detour 破壞。

### 2.3 一致性測試衝擊分析

- 既有測試若斷言「`_HAPPY_PATH` 鍵集 == `.tla` HappyStates」「`OBSERVATION_STATES` 計數」「狀態總數」者，將因加法翻牌（合法），須同步更新並標 `# additive: ACT-172`。實作期先 `grep -rn "OBSERVATION_STATES\|len(_HAPPY_PATH)\|HappyStates"` 鎖定全部 pin 測試逐一翻牌（非為過測而改測，附 ACT 追溯）。
- `arch_fitness` reachability BFS：新觀測態須自 IMPLEMENTATION 可達且有離開邊（已滿足），離線 reachability 隨 pytest 驗證。

### 2.4 v0.03 Copy-on-Evolve 落版

1. `robocopy AISDLC_SDD_v0.02 AISDLC_SDD_v0.03`（v0.02 凍結唯讀不動）。
2. 於 **v0.03** 施作 2.2 三處 delta。
3. `EVOLUTION_LOG.md` 新增 `v0.02 → v0.03` 五欄列（delta 清單含 ACT-172；**TLC 證據**附五軌 `TLC_DISTINCT/GENERATED/DEPTH` 實跑輸出；回退指引）。
4. `releases/CHANGELOG.md` 新增 `[v0.03]` 段。
5. `ID_REGISTRY.yaml`：登記 ACT-172、next_free 推進 act=173（rule 維持 9.39，本輪不取新 rule）。
6. `SDD_FSM_ENGINE.md` 狀態轉換表加 `AUTOCLAUDE_DELEGATED` 列（入/出邊文件化，對齊 2.1）。
7. 根層 `AISDLC_SDD_INIT.md` 等版本計數同步（若有狀態/版本宣稱）。

---

## 3. W2 設計 — DEF-01-004 ci.yml pg-e2e cron 過濾

**問題**（F12）：`ci.yml:189` pg-e2e-nightly 的 `if` 未以 `github.event.schedule` 過濾，致 02:00 與 03:00 兩條 cron 皆觸發 pg-e2e，每晚雙跑（隱性成本）。

**修正**（對齊 perf-baseline :442 / mutation :279 既有過濾模式，將 pg-e2e 綁定至 02:00 nightly cron）：

```yaml
# ci.yml:189 (pg-e2e-nightly)
if: >-
  (github.event_name == 'schedule' && github.event.schedule == '0 2 * * *')
  || github.event_name == 'workflow_dispatch'
```

**驗證**：本機無法觸發 GitHub cron，故以 (a) YAML 語法 lint（`python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`）+ (b) 與 :279/:442 過濾字串並列比對確認語意一致 + (c) 文件化於 DEF-01-004 fixed 證據。屬 CI 設定修正，不影響 pytest 基線。

---

## 4. 階段四 — CI 平價與五軌形式化驗證

### 4.1 五軌 TLC（W1 觸發形式化義務，Rule 9.18.1）

W1 修改 `_HAPPY_PATH` + `SDD_FSM.tla` → **必跑五軌 TLC 全綠**（須於 `AISDLC_SDD/AISDLC_SDD_v0.03/` 目錄下執行，`tools.fsm_runtime` 為該目錄根的 namespace package）：

```bash
cd AISDLC_SDD/AISDLC_SDD_v0.03
for m in SDD_FSM META_FSM FLEET_FSM COMPOSITION_FSM OPTIMIZATION_FSM; do
  python -m tools.fsm_runtime.tlc_runner --module $m --download
done
# 或 bash scripts/ci-gate.sh --full-tlc（AISDLC_SDD/ 目錄）
```

PR 附五軌各自 `TLC_DISTINCT/GENERATED/DEPTH` 輸出；任一 violation → 停機修復。重點驗證 `EventuallyTerminal`（新 detour 不破有界停機）與 reachability（新觀測態可達且 transient）。

### 4.2 零退化驗證矩陣（本輪 DoD；結構同 improving_01 §5.3，floor 以本輪實測為準）

| 檢查 | 命令 | 通過條件 |
|------|------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **≥ 3060 passed / 0 failed**（floor=F1 實測，禁寫死；W1/W2 不動 AutoClaude 程式碼，預期持平 3060） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken（實際 8 條，不寫死） |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | pytest not-chaos 全綠 + arch_fitness exit<2（v0.03） |
| DAL 等價 | equivalence job | 三後端等價（本輪未動 checkpoint，預期持平） |
| **五軌 TLC（W1 FSM 變更，本輪必跑）** | `bash scripts/ci-gate.sh --full-tlc`（或 4.1 迴圈） | 五軌 0 violation + `EventuallyTerminal`/reachability 通過 |

---

## 5. RTM（本計畫自身的需求追溯矩陣）

| 需求 | 落點 | 驗證 |
|------|------|------|
| AUTOCLAUDE_DELEGATED 入/出邊符合 improving_01 §6 / BRIDGE §5 | §2.1-2.2 | `transition_rules` 測試 + .tla 結構 |
| 觀測態三處同步（py/runtime/.tla）一致 | §2.2 (a)(b)(c) | 一致性 pin 測試翻牌 + TLC |
| Rule 9.18.4 ObservationStates ∩ Terminals = ∅ | §2.1 不變量 | TLC invariant |
| EventuallyTerminal 不被新 detour 破壞 | §2.2 (c).5 Fairness | 五軌 TLC liveness |
| Copy-on-Evolve v0.03（v0.02 凍結） | §2.4 | v0.02 grep 零汙染 + EVOLUTION_LOG/CHANGELOG |
| DEF-01-004 cron 雙跑修正 | §3 | YAML lint + :279/:442 並列比對 |
| 零退化 | 全篇 additive；AutoClaude 零改 | 3060 passed 基線持平 |

---

## 6. 實作順序（每支完成立即驗證，絕不累積）

> B 軌 Brownfield：本計畫即 SCG-0/1 載體；§2 介面/邊界 = SCG-2 素材；§2.2 三處 delta 契約 = SCG-3；v0.03 落版過 SCG-4；§4.2 矩陣 = SCG-5 RTM。行進中框架摩擦即記入 `AutoSDD_Defect_Log.md`（DEF-02-xxx）。

- **W1-a** `robocopy` v0.02 → v0.03（v0.02 凍結驗證：v0.02 git 無改動）。
- **W1-b** v0.03 `transition_rules.py` 加 `_HAPPY_PATH` key + `OBSERVATION_STATES` 成員 → 跑 `transition_rules` 相關單測。
- **W1-c** v0.03 `fsm_runtime.py` 加 `enter_autoclaude_delegated()`（開檔對齊 `enter_evaluator_audit` 簽名）→ 跑 fsm_runtime 單測。
- **W1-d** v0.03 `SDD_FSM.tla` 五點同步（§2.2 c）→ **五軌 TLC 全綠**（§4.1）。
- **W1-e** 一致性 pin 測試翻牌（§2.3）+ `SDD_FSM_ENGINE.md` 狀態表 + EVOLUTION_LOG/CHANGELOG/ID_REGISTRY/INIT 計數 → `ci-gate.sh`（v0.03）全綠。
- **W2** `ci.yml:189` cron 過濾 → YAML lint + 並列比對。
- **收斂**：跑 §4.2 矩陣全項，任一紅 → 停機修復。

每個 W 結束跑對應驗證；W1-d 五軌 TLC 為本輪形式化硬閘。

---

## 7. 缺陷帳本本輪處置（對照 §0 繼承）

| 缺陷 | 本輪處置 |
|------|---------|
| DEF-01-004（P3, routed） | **本輪 W2 修**（§3）→ 完成後改 `fixed@improving_02` 附證據 |
| DEF-01-007（P3, open） | cc-switch 環境工具未裝，本輪不涉 A/B 驗收，續 `open`（watch） |
| DEF-01-008（P1, routed） | main.py brain 注入評估——本輪選定演化型未取，**續 `routed`**（候選下輪） |
| DEF-01-009（P3, open watch） | 本輪不擴充 `sdd_governance_plugin.py`，無觸發 250 行紅線，續 `watch` |
| 本輪新發現 | 行進中即記 DEF-02-xxx（發現即記、絕不累積） |

---

## 8. 🔴 人工確認凍結點

本文件為 SCG-0/1 規格載體。**實作（W1-a）啟動前，須由人類明示確認本計畫凍結**（B 軌紅線：HUMAN_PENDING 不可自動跳過）。凍結後依 §6 實作順序執行，全程套 §4.2 零退化矩陣，收尾走多專家 Zero-Trust 審查閉環。

*待確認事項：是否同意本輪範圍（W1 AUTOCLAUDE_DELEGATED v0.03 + 五軌 TLC、W2 cron 過濾）與 floor=3060 凍結？*
