# AutoSDD_improving_63 — B 軌流程自治 L5 加固：鷹架代謝「自動提議退役」活體化

> **軌道**：① 整合迭代｜**本輪柱位**：**B 軌（手腳框架 dogfooding / 流程自治）**｜**下一份**：`AutoSDD_improving_64.md`
> **日期**：2026-06-25｜**驅動器**：`AutoSDD_Iteration_Prompt_Template.md`｜**成熟度量表 SSOT**：`AutoSDD_Maturity_Rubric.md`
> **本輪定位**：B 軸 L5 **加固**（非升級）——維持 `L_合體=L5`，把鷹架代謝「自動提議退役」（scaffold GC auto-propose）由 opt-in 鷹架（預設 OFF）翻為**預設 ON 活體常態**，閉合 arch_fitness FF-16 GAP-X2（「鷹架代謝 GC 從未產退役 ROI 提案」）。鏡像 v0.22 AUTO_RECOVERY / v0.23 SLV_AUTO_PROPOSE / v0.24 fire/catch telemetry 翻環先例。**這是最後一支殘留、仍預設 OFF 的 B 軸 opt-in arm**。
> **框架版本**：Copy-on-Evolve **v0.24 → v0.25**（v0.24 凍結唯讀）
> **🔴 人工 signoff**：掌舵者 AskUserQuestion 裁定「**B 軌 scaffold_gc 翻 ON**」，明確授權翻轉 scaffold GC auto-propose 預設。

---

## §1 上輪繼承（improving_62 結案 + 缺陷帳本）

- **improving_62**（B 軌 L5 加固：fire/catch 遙測活體化）已 commit（`e2e9ff9`），RTM R-62-1~10 全 ✅；閉合 DEF-17-001/DEF-18-001；`L_合體=min(A=L5,B=L5,C=L5)=L5`。
- **缺陷帳本 open/routed 項**（本輪處置）：
  - `DEF-01-007`（P3, cc-switch GUI）：維持 open（環境工具缺裝，非倉內可修；本輪不涉多後端 A/B，不阻擋）。
  - `DEF-01-009`（P3, sdd_governance_plugin LOC watch）：維持 open watch（本輪零擴充該檔，純 SDD 框架側）。
  - `DEF-19-001`（P3, catch 覆蓋）：維持 routed（escalation-scoped 結構天花板議題，非本輪 scope）。
  - `DEF-23-005`（P3, RFC 生命週期自動化）/ `DEF-30-001`（P3, RFC 已決標記標準化）/ `DEF-32-002`（P3, 負向狀態碼）：維持 routed（非本輪 scope）。
  - `DEF-35-001`（P2, goal_synthesis mutmut 目錄）：維持 routed（C 軌 W1，非本輪 B 軌 scope）。
  - `DEF-62-001`（P3, auto_recovery call-site 註解滯後）：維持 routed（他域 doc-lag，非本輪 scope）。
  - 本輪新發現缺陷見 `AutoSDD_Defect_Log.md`（行進中即記）。

## §2 階段一零信任重偵察（實測事實，全部錨定本輪 tool 輸出）

| 項目 | 實測命令 | 結果 | 硬閘 |
|------|---------|------|------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3315 passed / 122 skipped / 0 failed**（124.87s） | ✅ ＝上輪 floor 3315，零退化 |
| (b) 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（195 檔/489 依賴） | ✅ |
| (c) LOC / snapshot / git | `check_loc_budget` / `snapshot_sync --check` / `git status` | **violations=0 / 新鮮 / 工作樹乾淨** | ✅ |
| (d) AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **exit 0**；v0.01:1478 / v0.24:1656 / scripts:129 | ✅ |
| (e) 上輪構件存在性 | 親讀碼複核 | fire/catch/SLV/AUTO_RECOVERY 四 flag 皆預設 ON（`fsm_runtime.py:51-131`）；conftest `_isolate_rule_telemetry_default` 存在 | ✅ |
| (f) 缺陷帳本 open 項 | 讀帳本 | 見 §1（皆 P3，DEF-35-001 P2 屬 C 軌）| ✅ |
| (g) 外部工具依賴 | — | 本輪純 SDD 框架內部碼，無新外部 CLI/服務/訊息平台依賴 | n/a |

**🔴 關鍵發現（階段一實測 vs 記憶/文件）**：親讀 `fsm_runtime.py` 確認**唯一殘留、仍預設 OFF 的 B 軸 opt-in arm 只有 `_scaffold_gc_auto_propose_enabled()`**（`:87-91`，truthy-only）。fire/catch（v0.24）、SLV（v0.23）、AUTO_RECOVERY（v0.22）皆已預設 ON。本輪翻此最後一支。

**🔴 ci-gate arch_fitness 訊號佐證**：v0.24/v0.25 兩版皆 advisory warn **FF-16 GAP-X2「鷹架代謝 GC 從未產退役 ROI 提案（代謝肌肉從未收縮）」**——正是本輪翻環要消除的 advisory，方向與系統現況訊號完全吻合（不阻擋；翻環使機制預設活體，advisory 於實際代謝週期跑過後自然清除）。

**硬閘結論**：基線零退化、零 failed、不低於上輪（3315 ≥ floor 3315；v0.24:1656 ≥ floor 1656）→ **准予進入階段二**。

## §3 三軸成熟度現況 + 本輪定位

| 軸 | 現級 | 證據 |
|----|------|------|
| **A 協作自治** | **L5** | improving_60/61 轉譯策略元學習活體化 + weak_regex 第二信號加固。 |
| **B 流程自治** | **L5** | improving_57 AUTO_RECOVERY 常態化（L3→L4）、improving_59 SLV 自動提議活體化（L4→L5）、improving_62 規則命中遙測活體化（L5 加固）。**本輪加固**：鷹架代謝自動提議退役活體化。 |
| **C 引擎自治** | **L5** | 自演化 wire 進 ESCALATION + 跨 session DAL 元學習。 |

`L_合體 = min(A=L5, B=L5, C=L5) = **L5**`（本輪**維持**，非升級）。

**本輪定位（B→L5 加固，非升級）**：improving_17/W-17-1 已把 `scaffold_gc.run_gc`（依 scaffold_roi 算 ROI、產 RetirementProposal proposed 草案 + Markdown 報告）接入 `enter_scaffold_gc` 主迴圈，但**預設 OFF（opt-in 鷹架）**＝代謝機具齊備卻未活體：進代謝態只記 tracking、不跑 GC（FF-16 GAP-X2 根因）。承接 v0.24 fire/catch 遙測活體化使 `scaffold_roi.fire_count/catch_count` **真實累積**（資料就位、ROI 可算），本輪把代謝翻為**預設 ON 活體常態**——進 SCAFFOLD_GC 態即自動 draft proposed 退役草案，使「鷹架自我代謝」由鷹架升為常態運作，同 B 軌多輪硬化（AUTO_RECOVERY/SLV/telemetry）精神。

> **🔴 誠實邊界（zero-trust 紀律）**：
> 1. **maturity 不變**：本輪是 L5 機制**加固**（代謝由 opt-in→預設常態），`L_合體` 維持 L5，**不宣稱任何升級**。
> 2. **零退化根保證**：①run_gc 只產 proposed RetirementProposal + Markdown 報告、**永不 set_maturity**（active 規則退役仍 🔴 人工，R-9.20 #11）；②fail-closed（run_gc 失敗不阻塞已落定的進態、不偽造報告路徑）；③入口紀律不被 flag 弱化（非 RELEASE 源仍 raise）；④**FSM/`_HAPPY_PATH`/5 `*.tla` 對 v0.24 逐位元零差異**（run_gc 為 enter_scaffold_gc 進態後純 side-effect、零新增 reachable 邊）→ 依 Rule 9.18.1 **免五軌 TLC**。
> 3. **關鍵零退化護欄**：翻 ON 後進 SCAFFOLD_GC 態會落盤 SCAFFOLD-ROI 報告至 `GC_REPORT_DIR`（預設 build/reports/gc/），測試套加 conftest autouse 隔離（`_isolate_scaffold_gc_default`，預設 flag="0"）保護工作區不被測試 side-effect 污染（鏡像既有 telemetry 隔離）；production 出貨仍 ON。
> 4. **誠實 nuance**：翻環使 GC 機制**預設活體**，但 arch_fitness FF-16 GAP-X2 advisory 查的是磁碟上 `build/reports/gc/` 有無實際報告——它會在 production 實際代謝週期跑過後自然清除，本輪**不**為清 advisory 而強行在工作區產 runtime 報告（runtime 產物 gitignored，非本輪入庫物）。

---

## §4 <Architecture_Design_Review>（寫任何實質 Python 前必出）

### 4.1 架構純潔性
- **不創 God-object**：改動全為翻轉 1 個既有布林預設 + 1 個 test fixture + 1 個 wiring 測試對齊，無新類別/職責膨脹。
- **Thin Facade 維持**：`playbook_runner.py` n/a（本輪純 SDD `tools/fsm_runtime/` 側）。
- **邊界**：`_scaffold_gc_auto_propose_enabled()` 仍純讀 env；run_gc 走既有 `scaffold_gc.run_gc`（local import 避 cycle、fail-closed）。零新依賴、零新狀態、零新 sink。

### 4.2 持久化相容
- **無新持久化欄/路徑**：scaffold_roi/fire_count/catch_count 為既有欄；報告落既有 `GC_REPORT_DIR`；翻 flag 只改「是否跑 GC」之預設。
- **FSM-STATE 完全相容**：未動狀態檔 schema；`scaffold_gc_tracking` 既有結構（origin/roi_report_ref/proposals_total/rules_scanned 既有鍵）。

### 4.3 安全防護網
- **無新 shell 指令生成路徑**：run_gc 純讀規則 YAML、算 ROI、寫 Markdown 報告，不生成 evaluator_command、不改轉譯輸出 → CONDITIONAL 三層消毒不需擴充（零新增鏈式攻擊面）。

### 4.4 對外 I/O 安全
- 本輪**無新增 `ToolInvocationPort` 外呼路徑**（純本地 YAML 讀 + Markdown 報告寫，零網路 I/O）→ allowlist/SSRF 攻防 n/a。

### 4.5 L5「有界自演化、人在環上」要件維持（加固後仍守界）
| L5 要件 | 加固後落點 | 守界硬閘 |
|---------|-----------|---------|
| 主動（活體） | scaffold_gc flag 預設 ON（unset→True） | env 可顯式 opt-out（=0），零退化還原 v0.07 |
| 跨 session 持久化 | scaffold_roi/fire_count 累積於 governance R-*.yaml；報告落 build/reports/gc/ | — |
| **元學習（加固）** | fire_count 非零（v0.24 後）→ GC 算 ROI 產資料驅動退役提議 | — |
| 範圍·預算有界 | run_gc 為純計算 + 報告寫盤、無遞迴、提議不自動套用 | — |
| **人工 signoff 守退役** | 只產 proposed 提議，**永不 set_maturity**（R-9.20 #11） | 退役由人工 `set_maturity(reviewed_by=)` |

---

## §5 增量設計（W 項 / 介面 delta / LOC / 契約影響）= SCG-2/SCG-3

**Brownfield SOP**（B 軌）：本計畫＝SCG-0/1；§4 ＝SCG-2；下列契約＝SCG-3。Copy-on-Evolve v0.24→v0.25（官方 `scripts/copy_on_evolve.sh`，git-archive 純 tracked 860 檔 + 自動 bump 版本戳/skills 鏡像 59 檔/.gitignore block）。

### W-63-1 — `_scaffold_gc_auto_propose_enabled()` 預設翻 OFF→ON
`fsm_runtime.py`：由「truthy-only ON」改為「unset→True、顯式 falsy→OFF opt-out」（精確鏡像 `_auto_recovery_enabled`/`_rule_fire_telemetry_enabled`）+ 同步註解（v0.25 翻環脈絡、閉 FF-16 GAP-X2）。

### W-63-2 — conftest 測試隔離護欄（關鍵零退化）
`tools/fsm_runtime/tests/conftest.py`：新增 session autouse fixture `_isolate_scaffold_gc_default`，測試套**預設**把 flag 顯式設 "0"（鏡像既有 `_isolate_rule_telemetry_default`）。**WHY**：翻 ON 後進 SCAFFOLD_GC 態會落盤 SCAFFOLD-ROI 報告至 GC_REPORT_DIR（預設 build/reports/gc/），test_phase_h 的 2 個裸 `enter_scaffold_gc` 測試（未 redirect）若吃預設 ON 會寫穿工作區→髒樹+非確定。隔離後既有測試行為 byte-identical v0.24；wiring 測試以 delenv 覆寫驗 default-ON。

### W-63-3 — wiring 測試對齊新預設
- `test_scaffold_gc_auto_propose_wiring.py`：Case 1「delenv→斷言無 auto_gc」改寫為 `test_default_on_enter_auto_runs_gc`（**default-ON 活體驗收**：delenv 覆寫 conftest → 自動跑 GC + 填 origin=auto/roi_report_ref，以 `_redirect_gc_report` 導向 tmp）；Case 2 改名 `test_explicit_opt_out_pure_tracking_no_auto_gc`（**顯式 opt-out 零退化守**：setenv "0" → 還原 v0.07 純記 tracking）。wiring 測試數不變（9 case）。

### 不需動的部分（scope 收斂證據）
- **FSM 本體零改動** → `transition_rules.py`/`_HAPPY_PATH`/5 `*.tla` 對 v0.24 逐位元零差異（diff exit 0 已驗證）→ **無五軌 TLC**。
- 無新 sink、無新 port、無 alembic、無 AutoClaude 改動（git status 驗零接觸 AutoClaude/）。
- Case 3~8（flag ON 自走 / 報告落盤 / fail-closed / R-9.20 紅線 / 入口紀律 / stats）維持不動（已是 setenv "1" 明確 ON 或 stats 計算，不受預設翻環影響）。

---

## §6 RTM（需求→設計→測試 追溯）

| RTM | 需求 | 設計落點 | 驗證（測試）| 狀態 |
|-----|------|---------|-----------|------|
| R-63-1 | scaffold GC auto-propose 預設 ON、unset 即進態自動跑 GC | W-63-1 | `test_scaffold_gc_auto_propose_wiring.py::test_default_on_enter_auto_runs_gc` | ✅ |
| R-63-2 | 顯式 opt-out（=0）還原 v0.07 只記 tracking（零退化逃生閥）| W-63-1 | `::test_explicit_opt_out_pure_tracking_no_auto_gc` | ✅ |
| R-63-3 | 紅線：GC 永不自動退役 active 規則（永不 set_maturity，R-9.20 #11）| W-63-1 | `::test_red_line_gc_never_auto_retires` | ✅ |
| R-63-4 | fail-closed：run_gc 失敗不阻塞已落定進態、不偽造報告 | W-63-1 | `::test_run_gc_failure_fail_closed` | ✅ |
| R-63-5 | 入口紀律不被 flag 弱化（非 RELEASE 源仍 raise）| W-63-1 | `::test_flag_on_non_release_source_still_raises` | ✅ |
| R-63-6 | 測試套零污染工作區（conftest 隔離）| W-63-2 | test_phase_h 2 裸 enter_scaffold_gc 測試 byte-identical 全綠（隔離生效，build/reports/gc 零洩漏）| ✅ |
| R-63-7 | FSM/`*.tla` 對 v0.24 逐位元零差異 → 免五軌 TLC | §5 | `diff` exit 0（5 `*.tla` + transition_rules.py）| ✅ |
| R-63-8 | 零退化基線 | §7 矩陣 | （見 §7 結案實測）| ✅ |
| R-63-9 | maturity 不變（L5 加固非升級）誠實 | §3 + §4.5 | 三鏡 audit OVERALL PASS，見 `AutoSDD_ZeroTrust_Audit_63.md` | ✅ |

## §7 零退化驗證矩陣（floor = improving_62 §2 實測；通過條件每輪實測，禁寫死）

| 檢查 | 命令 | 通過條件 | 結案實測 |
|------|------|---------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ **3315** passed / 0 failed | **3315 / 0 failed**（零接觸 AutoClaude，git status 驗證）|
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | **violations=0** |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0（pytest not-chaos 全綠 + arch_fitness）| **exit 0**；v0.01:1478 / **v0.25:1656**（＝floor 1656）/ scripts:129 |
| Snapshot/SSOT | ci-gate 內含 FRAMEWORK_STATUS/skill 戳/skills 鏡像 lint | 新鮮 | **全綠**（FRAMEWORK_STATUS 重生新鮮、skill 戳 v0.25、父層 skills 鏡像==v0.25 59 檔、router hook 覆蓋 v0.25、gitignore block v0.25）|
| 五軌 TLC | （僅 FSM 變更時）| **n/a（本輪 FSM/`*.tla` 對 v0.24 逐位元零差異）** | ✅ diff exit 0 |

## §8 缺陷 / 延後

- 行進中框架/工程摩擦發現即記入 `AutoSDD_Defect_Log.md`（DEF-63-NNN）。
- **B 軸 opt-in→default-ON 翻環家族至此收齊**（AUTO_RECOVERY/SLV/fire/catch/scaffold_gc 五支全翻 ON）；下輪 B 軌候選須另尋實質 delta（或 C 軌 SD_09 觀察期）。
- FF-16 GAP-X2 advisory：翻環使機制預設活體，advisory 於 production 實際代謝週期跑過後自然清除（不為清 advisory 強塞 runtime 報告入庫）。
