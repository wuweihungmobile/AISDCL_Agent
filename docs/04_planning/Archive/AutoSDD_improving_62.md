# AutoSDD_improving_62 — B 軸流程自治 L5 加固：規則命中遙測（fire + catch）活體化

> **軌道**：① 整合迭代｜**本輪柱位**：**B 軌（手腳框架 dogfooding / 流程自治）**｜**下一份**：`AutoSDD_improving_63.md`
> **日期**：2026-06-25｜**驅動器**：`AutoSDD_Iteration_Prompt_Template.md`｜**成熟度量表 SSOT**：`AutoSDD_Maturity_Rubric.md`
> **本輪定位**：B 軸 L5 **加固**（非升級）——維持 `L_合體=L5`，把規則命中遙測（fire/catch）由 opt-in 鷹架（預設 OFF）翻為**預設 ON 活體常態**，閉合 DEF-17-001（fire_count=0）/ DEF-18-001（catch 側）懸置根因。鏡像 v0.22 AUTO_RECOVERY / v0.23 SLV_AUTO_PROPOSE 翻環先例。
> **框架版本**：Copy-on-Evolve **v0.23 → v0.24**（v0.23 凍結唯讀）
> **🔴 人工 signoff**：掌舵者 AskUserQuestion 裁定「**B 軸：telemetry 翻 ON**」，明確授權翻轉 fire/catch 兩 flag 預設。

---

## §1 上輪繼承（improving_61 結案 + 缺陷帳本）

- **improving_61**（A 軌 L5 加固：weak_regex 第二信號併入轉譯元學習）已 commit（`4c39065`），RTM R-61-1~11 全 ✅；`L_合體=min(A=L5,B=L5,C=L5)=L5`。
- **缺陷帳本 open/routed 項**（本輪處置）：
  - `DEF-01-007`（P3, cc-switch GUI）：維持 open（環境工具缺裝，非倉內可修；不阻擋本輪）。
  - `DEF-01-009`（P3, sdd_governance_plugin LOC watch）：維持 open watch（本輪零擴充該檔）。
  - `DEF-17-001`（P3, fire telemetry fire_count=0 歸因）：**本輪由 routed → 實質閉合**（fire 遙測翻預設 ON，fire_count 真實累積）。
  - `DEF-18-001`（P3, catch 側語意未定義）：**本輪由 routed → 實質閉合**（catch 遙測翻預設 ON，on-attribution catch 活體記帳）。
  - `DEF-19-001`（P3, catch 覆蓋）：維持 routed（覆蓋率為 escalation-scoped 結構天花板議題，非本輪 scope）。
  - 本輪新發現缺陷見 `AutoSDD_Defect_Log.md`（行進中即記）。

## §2 階段一零信任重偵察（實測事實，全部錨定本輪 tool 輸出）

| 項目 | 實測命令 | 結果 | 硬閘 |
|------|---------|------|------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3315 passed / 122 skipped / 0 failed**（130.81s） | ✅ ＝上輪 floor 3315，零退化 |
| (b) 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** | ✅ |
| (c) AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **exit 0**；v0.01:1478 / v0.23:1656 / scripts:129 | ✅ |
| (d) 上輪構件存在性 | 讀檔複核 | improving_61 weak_regex 四構件皆存在 | ✅ |
| (e) 缺陷帳本 open 項 | 讀帳本 | 見 §1（皆 P3）| ✅ |
| (f) 外部工具依賴 | — | 本輪純 SDD 框架內部碼，無新外部 CLI/服務/訊息平台依賴 | n/a |

**🔴 zero-trust 糾正（階段一實測 vs Explore 報告）**：Explore agent 誤報 `SDD_ENABLE_AUTO_RECOVERY`/`SDD_ENABLE_SLV_AUTO_PROPOSE` 仍預設 OFF；親讀 `fsm_runtime.py:51-56`/`:72-77` 確認**兩者皆已預設 ON**（v0.22/v0.23 已活體化），commit log 正確。**真正殘留、仍預設 OFF 的 B 軸 opt-in arm 只有三支**：`_rule_fire_telemetry_enabled()`、`_rule_catch_telemetry_enabled()`、`_scaffold_gc_auto_propose_enabled()`。本輪翻前兩支（telemetry）；scaffold GC auto-propose（會實際產退役提議、風險最高）刻意留待後續。

**硬閘結論**：基線零退化、零 failed、不低於上輪（3315 ≥ floor 3315）→ **准予進入階段二**。

## §3 三軸成熟度現況 + 本輪定位

| 軸 | 現級 | 證據 |
|----|------|------|
| **A 協作自治** | **L5** | improving_60/61 轉譯策略元學習活體化 + weak_regex 第二信號加固。 |
| **B 流程自治** | **L5** | improving_57 AUTO_RECOVERY 常態化（L3→L4）、improving_59 SLV 自動提議活體化（L4→L5）。**本輪加固**：規則命中遙測活體化。 |
| **C 引擎自治** | **L5** | 自演化 wire 進 ESCALATION + 跨 session DAL 元學習。 |

`L_合體 = min(A=L5, B=L5, C=L5) = **L5**`（本輪**維持**，非升級）。

**本輪定位（B→L5 加固，非升級）**：improving_18/19 已把 on-watch fire（接 `transition()`）與 on-attribution catch（接 escalation 落點）記帳機具接好，但**預設 OFF（opt-in 鷹架）**＝機具齊備卻未活體：fire 不記 → `scaffold_roi.fire_count` 恆 0（DEF-17-001 根因）→ scaffold GC 無資料驅動退役提議；catch 側同樣懸置（DEF-18-001）。本輪把兩支翻為**預設 ON 活體常態**——進態即記 fire（fire_count 真實累積）、escalation 歸因即記 catch，使「規則自我度量」由鷹架升為常態運作，同 B 軌多輪硬化（AUTO_RECOVERY/SLV）精神。

> **🔴 誠實邊界（zero-trust 紀律）**：
> 1. **maturity 不變**：本輪是 L5 機制**加固**（遙測由 opt-in→預設常態），`L_合體` 維持 L5，**不宣稱任何升級**。
> 2. **零退化根保證**：①只增 fire_count/catch_count、**永不 set_maturity**（active 規則退役仍 🔴 人工，R-9.20 #11）；②fail-closed（記帳失敗不阻塞已落定的轉態/escalation；catch 缺證據不記、不污染 ROI）；③**FSM/`_HAPPY_PATH`/5 `*.tla` 對 v0.23 逐位元零差異**（fire/catch 為 transition/escalation 後純 side-effect、零新增 reachable 邊）→ 依 Rule 9.18.1 **免五軌 TLC**。
> 3. **關鍵零退化護欄**：fire 遙測每次 transition 寫凍結 `governance/rules/`，測試套加 conftest autouse 隔離（預設 flag="0"）保護凍結本體不被測試 side-effect 污染（鏡像既有 meta-ledger 隔離）；production 出貨仍 ON。

---

## §4 <Architecture_Design_Review>（寫任何實質 Python 前必出）

### 4.1 架構純潔性
- **不創 God-object**：改動全為翻轉 2 個既有布林預設 + 1 個 test fixture + 測試斷言對齊，無新類別/職責膨脹。
- **Thin Facade 維持**：`playbook_runner.py` n/a（本輪純 SDD `tools/fsm_runtime/` 側）。
- **邊界**：`_rule_*_telemetry_enabled()` 仍純讀 env；記帳走既有 `rule_loader.record_state_fires/catches`（fail-closed local import 避 cycle）。零新依賴、零新狀態。

### 4.2 持久化相容
- **無新持久化欄/路徑**：fire_count/catch_count 為既有 `scaffold_roi` 欄；翻 flag 只改「是否寫」之預設。
- **FSM-STATE 完全相容**：未動狀態檔 schema。

### 4.3 安全防護網
- **無新 shell 指令生成路徑**：純布林信號 + 純計數記帳，不生成 evaluator_command、不改轉譯輸出 → CONDITIONAL 三層消毒不需擴充（零新增鏈式攻擊面）。

### 4.4 對外 I/O 安全
- 本輪**無新增 `ToolInvocationPort` 外呼路徑**（純本地 YAML 讀寫，零網路 I/O）→ allowlist/SSRF 攻防 n/a。

### 4.5 L5「有界自演化、人在環上」要件維持（加固後仍守界）
| L5 要件 | 加固後落點 | 守界硬閘 |
|---------|-----------|---------|
| 主動（活體） | 兩 telemetry flag 預設 ON（unset→True） | env 可顯式 opt-out（=0），零退化還原 |
| 跨 session 持久化 | fire_count/catch_count 累積於 governance R-*.yaml | — |
| **元學習（加固）** | fire_count 非零 → scaffold GC ROI 有資料；catch_count → propose_graduation 保護有用規則 | — |
| 範圍·預算有界 | 記帳為純計數疊加、無遞迴、無提議自動套用 | — |
| **人工 signoff 守退役** | 只增計數，**永不 set_maturity**（R-9.20 #11） | 退役由人工 `set_maturity(reviewed_by=)` |

---

## §5 增量設計（W 項 / 介面 delta / LOC / 契約影響）= SCG-2/SCG-3

**Brownfield SOP**（B 軌）：本計畫＝SCG-0/1；§4 ＝SCG-2；下列契約＝SCG-3。Copy-on-Evolve v0.23→v0.24（官方 `scripts/copy_on_evolve.sh`，git-archive 純 tracked 860 檔 + 自動 bump 版本戳/skills 鏡像/.gitignore block）。

### W-62-1 — `_rule_fire_telemetry_enabled()` 預設翻 OFF→ON
`fsm_runtime.py`：由「truthy-only ON」改為「unset→True、顯式 falsy→OFF opt-out」（精確鏡像 `_auto_recovery_enabled`/`_slv_auto_propose_enabled`）+ 同步註解（v0.24 翻環脈絡）。

### W-62-2 — `_rule_catch_telemetry_enabled()` 預設翻 OFF→ON
同 W-62-1（catch 側）。

### W-62-3 — conftest 測試隔離護欄（關鍵零退化）
`tools/fsm_runtime/tests/conftest.py`：新增 session autouse fixture `_isolate_rule_telemetry_default`，測試套**預設**把兩 flag 顯式設 "0"（鏡像既有 `_isolate_meta_loop_ledger`）。**WHY**：fire 遙測每次 transition 寫 `RULES_DIR`（凍結 governance/rules/），測試套 7 個裸 transition 測試（test_chaos/test_decision_trace/test_e2e_smoke/test_phase_h/test_timeout_checker/test_trajectory_predictor）若吃預設 ON 會寫穿凍結本體→髒樹+非確定。隔離後既有測試行為 byte-identical v0.23；wiring 測試以 delenv 覆寫驗 default-ON。

### W-62-4 — wiring 測試對齊新預設
- `test_rule_fire/catch_telemetry_wiring.py`：Case 1「delenv→斷言不記」改寫為 **default-ON 活體驗收**（delenv 覆寫 conftest → 記 fire/catch）；Case 2 為**顯式 opt-out 零退化守**（setenv "0" → 不記）。
- `test_w20/w37/w38_catch_wiring.py`：5 個 `*_flag_off_zero_regression` 測試由 `delenv` 改顯式 `setenv("0")`（翻環後 OFF 以 opt-out 表達；測試名仍準確）。

### 不需動的部分（scope 收斂證據）
- **FSM 本體零改動** → `transition_rules.py`/`_HAPPY_PATH`/5 `*.tla` 對 v0.23 逐位元零差異（已 diff 驗證）→ **無五軌 TLC**。
- `scaffold_gc_auto_propose` 維持預設 OFF（風險最高、會實際產退役提議，留後續輪）。
- 無新 sink、無新 port、無 alembic、無 AutoClaude 改動（git status 驗零接觸 AutoClaude/）。

---

## §6 RTM（需求→設計→測試 追溯）

| RTM | 需求 | 設計落點 | 驗證（測試）| 狀態 |
|-----|------|---------|-----------|------|
| R-62-1 | fire telemetry 預設 ON、unset 即記 on-watch fire | W-62-1 | `test_rule_fire_telemetry_wiring.py::test_default_on_transition_records_fire` | ✅ |
| R-62-2 | catch telemetry 預設 ON、unset 即記 on-attribution catch | W-62-2 | `test_rule_catch_telemetry_wiring.py::test_default_on_records_catch` | ✅ |
| R-62-3 | 顯式 opt-out（=0）還原 v0.08/v0.09 不記（零退化逃生閥）| W-62-1/2 | `::test_explicit_opt_out_records_no_fire`、`::test_explicit_opt_out_records_no_catch` | ✅ |
| R-62-4 | 紅線：遙測永不 set_maturity（退役仍人工，R-9.20 #11）| W-62-1/2 | fire `::test_red_line_telemetry_never_set_maturity`、catch `::test_red_line_catch_never_set_maturity` | ✅ |
| R-62-5 | fail-closed：記帳失敗不阻塞已落定轉態/escalation | W-62-1/2 | fire `::test_telemetry_failure_fail_closed`、catch `::test_fail_closed_catch_failure_does_not_raise` | ✅ |
| R-62-6 | 測試套零污染凍結 governance（conftest 隔離）| W-62-3 | 7 裸 transition 測試 byte-identical 全綠（隔離生效）| ✅ |
| R-62-7 | 既有 catch wiring（w20/w37/w38）零退化（opt-out 表達 OFF）| W-62-4 | `test_w20/w37/w38_catch_wiring.py` 全綠 | ✅ |
| R-62-8 | FSM/`*.tla` 對 v0.23 逐位元零差異 → 免五軌 TLC | §5 | `diff` exit 0（5 `*.tla` + transition_rules.py）| ✅ |
| R-62-9 | 零退化基線 | §7 矩陣 | （見 §7 結案實測）| ✅ |
| R-62-10 | maturity 不變（L5 加固非升級）誠實 | §3 + §4.5 | 三鏡 audit OVERALL PASS，見 `AutoSDD_ZeroTrust_Audit_62.md` | ✅ |

## §7 零退化驗證矩陣（floor = improving_61 §2 實測；通過條件每輪實測，禁寫死）

| 檢查 | 命令 | 通過條件 | 結案實測 |
|------|------|---------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ **3315** passed / 0 failed | **3315 / 0 failed**（零接觸 AutoClaude，git status 驗證）|
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | **8 kept / 0 broken** |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0（pytest not-chaos 全綠 + arch_fitness）| **exit 0**；v0.01:1478 / **v0.24:1656**（≥floor 1656）/ scripts:129 |
| Snapshot/SSOT | ci-gate 內含 FRAMEWORK_STATUS/skill 戳/skills 鏡像 lint | 新鮮 | **全綠**（FRAMEWORK_STATUS 新鮮、skill 戳 v0.24、父層 skills 鏡像==v0.24 59 檔、router hook 覆蓋 v0.24、gitignore block v0.24）|
| 五軌 TLC | （僅 FSM 變更時）| **n/a（本輪 FSM/`*.tla` 對 v0.23 逐位元零差異）** | ✅ diff exit 0 |

## §8 缺陷 / 延後

- 行進中框架/工程摩擦發現即記入 `AutoSDD_Defect_Log.md`（DEF-62-NNN）。
- `scaffold_gc_auto_propose` 維持預設 OFF＝**刻意延後**（會實際產退役提議、需更謹慎的人在環上設計）＝後續輪候選，非缺陷。
- DEF-19-001（catch 覆蓋率天花板）為 escalation-scoped 結構議題，非本輪 telemetry 翻環 scope。
