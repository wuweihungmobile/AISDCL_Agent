# AutoSDD_improving_23 — B 軌 XAI 深化：meta⁸ 互遞迴呼叫圖 Folding 降維補完

> **軌道①整合迭代 第 23 輪**｜**柱：B（手腳 AISLDC_SDD dogfooding）**｜驅動器＝`AutoSDD_Iteration_Prompt_Template.md`
> **本輪定位**：XAI Turn 疊加（首席 AI 自動化架構師視角）。Phase Y 視覺化儀表板頭部已於 v0.13 完成式，本輪鎖定其 **blueprint 列入、§D 收官以 pagination 替代而靜默未交付的 Folding 降維子項**。
> **建立日期**：2026-06-17｜**Copy-on-Evolve**：v0.13（凍結）→ **v0.14**

---

## §0 防混淆對齊（動工前鐵律）

| 項目 | 本輪裁定 |
|------|---------|
| 軌道 | ① 整合迭代（根層 `docs/04_planning/AutoSDD_improving_NN.md`，唯一驅動器）；**非** 子專案 `SDD_improving_Automation_NN`（軌道②，下游帳本） |
| 柱 | **B 軌**（手腳 AISLDC_SDD dogfooding）；XAI Turn 疊加 |
| 上輪 | improving_22 結案（commit `1e283bb`+`4d171be`，tag `v2026.06.17-19`，v0.13） |
| 本輪 work item | **W-23-1：Folding/鏈塌縮降維補完（隸屬既有 R-9.37 PY-3，不取新 ACT/Rule）** |
| 下一份 | improving_24（按需） |

**為何不取新 ACT/Rule（W-23-1 的編號裁定）**：Folding 是 R-9.37 `VisualizationBounded` PY-3「降維」緊語意之內的既有機制補完（非新機制類別），且 PY-2 拓樸防偽稽核已涵蓋「畫的圖 == 跑的圖」治理。沿用 **_27 / DEF-20-001 前例**（additive 改動、既有規則涵蓋即不開新 R-9.x，避免牽動 RULES_INDEX/ID_REGISTRY 取號 + Rule 2 簡約）。ID_REGISTRY `next_free`（act 173 / rule 9.39）**不動** → `test_id_registry_next_free_advanced_phase_y` 零退化。模板「driver instance 自動編號」於本輪正確解＝**無需新號**（folding 落在 R-9.37 既有 envelope）。

---

## §1 階段一 Zero-Trust 重偵察結論（實測，floor 採上輪實測值）

| 偵察軸 | 實測 | vs floor | 判定 |
|--------|------|----------|------|
| AutoClaude `pytest tests/ -q` | 3112 passed / 122 skipped / 0 failed | = 3112 | ✅ |
| `lint-imports` | 8 kept / 0 broken | = 8 | ✅ |
| `check_loc_budget` | violations=0（17794/20438） | — | ✅ |
| `snapshot_sync --check` | OK 新鮮 | — | ✅ |
| `ci-gate.sh`（AISLDC_SDD） | v0.01:1478 / v0.13:1580 / scripts:27、arch_fitness fail=0 exit0 | 全持平 | ✅ |
| v0.13=最新 + EVOLUTION_LOG 末條=improving_22 | 確認（DEF-12-002 / DEF-15-001深 / DEF-22-001） | — | ✅ |
| 構件真偽（FSM 模板 tracked 位 / cross_version_guard / closure-evidence） | 全真實且測試覆蓋 | — | ✅ |

**硬閘**：未觸發（基線零退化）。

### 階段一新揭缺陷（已入帳，見 Defect_Log）
- **DEF-23-001（P3，文檔 vs 實況）**：v0.13 CHANGELOG 宣稱 `test_cross_version_guard.py`「25→27 case」，單檔實測僅 10 函式 / 10 passed、無 parametrize；測試本身真實全綠，僅計數口徑不一致。
- **DEF-23-002（P3，流程漂移）**：`SDD_improving_Automation_26.md`（Phase Y，§D 已收官）與 `_27.md`（closure_evidence，§6 標「決策後 archive」）**兩份已完成 RFC 滯留 `build/planning/active/`**，違反框架自身「active=待決 / archive=已決」生命週期。

---

## §2 重大 Zero-Trust 發現（重新定範依據）

`SDD_improving_Automation_26.md §D（2026-06-06 收官）`白紙黑字：**Phase Y / ACT-159~161 / R-9.37 整套視覺化儀表板已交付結案**（`recursion_topology_view` 三視圖 + PY-2 拓樸防偽 + `guard_visualization_bounded` + `render_recursion_topology_dashboard` + chaos 兩 FLAP + R-9.37 治理 + ID 翻牌 + QA 兩輪對抗稽核全修復）。

**故模板〈XAI Turn〉範例 driver（ACT-159/R-9.37「建儀表板」）其字面標的在 v0.13 已完成式**；本輪拒絕重做已結案工作，重新定範至其**真實 delta**＝Folding 降維（`_26.md §A.4.2` + DoD §A.9 第一技術勾選明列「critical path + folding + bounded truncation + pagination」，但 v0.13 實作只交付 truncation+pagination；live `TopoNode` 無 `folded` 欄、`render_mermaid` 無 subgraph 塌縮、`test_phase_y` 零 `fold/SCC/subgraph` 測試 → 證實 Folding 為**列入未交付子項**；EVOLUTION_LOG/CHANGELOG/archive 均無「有意 de-scope」紀錄）。

---

## §3 <Architecture_Design_Review>（寫實質 Python 前自我驗證）

**1. 架構純潔性**：Folding 是 `recursion_topology_view` 內純函式轉換 `fold_topology(view)->view'`，同層同紀律（deterministic / 零 LLM / 零外網 / 零 FSM-STATE / 零 churn / 不 import generator·oracle）。無 God-object；`steersman_renderer`/`meta_halt_monitor` 簽章不變。

**2. 持久化相容**：不碰 PlaybookCheckpoint/DAL/FSM-STATE。`RenderBudget.fold_enabled` 與 `TopoNode.folded/folds` 皆 frozen dataclass **additive 帶預設**，**預設 OFF＝v0.13 逐位元行為** → golden/isomorphic 測試零退化。

**3. 安全防護網（核心張力解法）**：Folding 故意「畫得比真圖簡單」＝ PY-2 要攔的視覺欺騙。解法＝**可稽核的誠實收縮**：超節點 `folds=[成員 id]` 公開申報，`verify_topology_consistency` 擴充五道 fold 稽核（見 §5.3）使 folding 成為**可驗證無損的分組**，與 PY-2 反欺騙相容且更強（新增「假折疊／折疊藏 critical」防護）。

**4. 對外 I/O 安全**：不新增 `ToolInvocationPort` 外呼（純記憶體投影、零 HTTP，守 OPEN-10.6 / OPEN-Y.1）。N/A。

**FSM/TLA 影響＝零**：`VisualizationBounded==churn<=MAX_CHURN` 不受影響（read-only 不 churn）→ `_HAPPY_PATH`/`*.tla` 零修改 → **五軌 TLC 免觸發**。

---

## §4 SCG-0/1：需求凍結（Brownfield 增強）

| ID | 需求 | 驗收標準（AC） |
|----|------|----------------|
| **F-23-1** | 大/深呼叫圖在 render budget 內以 Folding 收縮「結構無趣的線性鏈」，降低人類認知超載 | AC-23-1-1：fold_enabled 時，連續 in-deg==1∧out-deg==1 且非 kept-node 的鏈塌縮為單一 `[+k more]` 超節點；AC-23-1-2：entry / critical(max-fuel) / 分支 / 匯聚 / sink / fuel 歸零邊界節點**永不被折疊** |
| **F-23-2** | Folding 為**可稽核誠實收縮**，不得成為視覺欺騙破口 | AC-23-2-1：超節點公開 `folds=[成員]`；AC-23-2-2：`verify_topology_consistency` 五道 fold 稽核（f1~f5，§5.3）全過才放行；AC-23-2-3：假折疊（非真鏈／rank 非遞減／折疊藏 entry·critical／丟節點／偽邊界）→ `TopologyConsistencyError` fail-closed |
| **F-23-3** | 零退化：預設行為 == v0.13 | AC-23-3-1：`SDD_VIZ_FOLD` 預設 OFF；AC-23-3-2：fold OFF 時全 v0.13 既有 `test_phase_y` 測試逐項續綠 |
| **NFR-23-1** | 有界停機（PY-3 不破） | fold 轉換零 while／零自呼叫；輸出仍 ≤ char_budget；10⁶ 節點仍有界 |
| **NFR-23-2** | 紅線守恆 | 不碰 meta⁹/meta-oracle、不提 Token 上限、不破五軌 TLC、不增第六軌/狀態變數 |

🔴 **人工確認點（HUMAN_PENDING）**：SCG-0/1 需求凍結需掌舵者 signoff（本計畫書即載體）。

---

## §5 SCG-2/3：設計與契約

### 5.1 資料模型 delta（additive）
```
RenderBudget += fold_enabled: bool = False          # 讀 SDD_VIZ_FOLD（"1"/"true" 開；預設關）
            += fold_min:     int  = 3               # 鏈塌縮最小長度門檻（讀 SDD_VIZ_FOLD_MIN，clamp）
TopoNode    += folded: bool = False                 # 是否為折疊超節點
            += folds:  Tuple[int, ...] = ()          # 被收縮的成員 id（鏈序；空=非超節點）
```

### 5.2 Folding 演算法（純函式 `fold_topology(view) -> TopologyView`）
1. 在窗格內計每節點 in-degree / out-degree（僅窗內邊）。
2. 定義 **kept-node**＝ entry ∨ critical(max-fuel) ∨ out-deg≠1 ∨ in-deg≠1 ∨ 未訪問(fuel 歸零) ∨ sink。
3. 掃描極大「內部鏈」：連續節點皆 in-deg==1∧out-deg==1∧非 kept-node，且逐對為真實呼叫邊。
4. 每條長度 ≥ `SDD_VIZ_FOLD_MIN`(預設 3) 的內部鏈 → 塌縮為一個 folded 超節點（id＝鏈首成員、`folds`＝鏈成員、base＝`[+k more]`、rank＝鏈首 rank、fuel_consumed＝成員和、calls＝鏈尾出邊）；鏈首前驅邊與鏈尾後繼邊接到 kept 鄰居。
5. fold OFF 或無合格鏈 → 原 view 原樣返回（零行為改變）。
> 確定性（rank 升序、id 序 tie-break）、零遞迴、O(window)。

### 5.3 PY-2 fold-aware 稽核（`verify_topology_consistency` 擴充五道）
對每個 `folded==True` 的渲染節點，獨立從 `op_dict` 重算驗證：
- **f1 真鏈**：`folds` 逐對 (a,b) 滿足 b ∈ calls_by_id[a]（真實呼叫邊）。
- **f2 良基**：鏈上 rank 嚴格遞減（不破良基測度）。
- **f3 不藏要角**：verify 端硬擋 `folds` 含 entry（`m == entry` → raise）；**critical(max-fuel) 與分支/匯聚/sink/source 由 f1 的「窗內 in==1∧out==1」結構約束天然排除**（這些要角 degree≠1，且 fold_topology 生成端 `_is_kept` 亦含 critical 永不折），故被折疊者必為結構無趣的內部鏈節點。
- **f4 真實大小誠實（窗格錨定強化）**：`{可見未折疊 id} ∪ {全部 folds 成員}` == 權威窗格全集（nothing dropped；沿用既有 a0/a1 窗格錨定，只是把「顯示集」改為「顯示集含折疊展開」）。
- **f5 邊界忠實**：超節點申報的入/出邊 == 鏈在真相圖的首尾邊界邊。
> 任一不過 → `TopologyConsistencyError` → MFSM_ESCALATION（fail-closed）。fold OFF 時 `folds` 皆空，五道恆過 ⇒ v0.13 既有稽核行為逐位元不變。

### 5.4 渲染 delta
`render_mermaid`：folded 超節點以專屬 `classDef fold`（虛線群組樣式）渲染為 `[[+k more · r=hi..lo]]`，標示收縮成員數與 rank 範圍；非 folded 路徑零變更。`render_json`：node dict additive 輸出 `folded`/`folds`（既有 round-trip 測試不依賴精確 dict，無退化）。

### 5.5 guard / chaos
- `guard_visualization_bounded`：簽章與三段 fail-closed 邏輯**不變**，透過既有 `verify_topology_consistency` 呼叫自動獲得 f1~f5 fold 稽核（folding 降節點數 → budget 更易過）。
- chaos：新增 `VISUALIZATION_FOLD_DRIFT_FLAP` + `_visualization_fold_drift_flap_is_bounded`（假折疊注入必攔，bounded_ratio 計入）；既有 `test_chaos_registers_visualization_flaps` 為 membership 斷言，新增第三 fault 不破。

---

## §6 RTM（需求追溯矩陣）

> RTM 測試名以**實作落地名為準**（SA-SD 鏡複審校正命名 drift，DEF-05-002/07-001 家族；實作 11 個 `test_fold_*` + 2 個 chaos fold ≥ 原規劃 9 項，覆蓋更全）。

| AC | 設計 | 測試（test_phase_y.py 實際落地名） | 驗證 |
|----|------|------------------------------|------|
| AC-23-1-1 | §5.2 鏈塌縮 | `test_fold_collapses_linear_chain` | pytest |
| AC-23-1-2 | §5.2 kept-node | `test_fold_never_folds_entry_critical_branch_sink` | pytest |
| AC-23-2-1/2 | §5.3 f1~f5 誠實收縮 | `test_fold_honest_render_passes_verify_and_guard` | pytest |
| AC-23-2-3 | §5.3 fail-closed（f1 吞非內部節點 / f3 藏 entry / f4 丟成員 / 商圖杜撰邊） | `test_fold_forgery_includes_noninterior_node_rejected` / `test_fold_forgery_hides_entry_rejected` / `test_fold_forgery_drops_member_rejected` / `test_fold_forgery_fabricated_quotient_edge_rejected` | pytest |
| AC-23-2-3 | §5.5 chaos fold-drift | `test_chaos_registers_fold_drift_flap` / `test_chaos_fold_drift_flap_is_bounded` | pytest + chaos |
| AC-23-3-1/2 | §5.1 flag-OFF | `test_fold_off_is_default_v013_behavior` / `test_fold_env_knob_truthy_and_clamped` + 既有 37 Phase Y 測試續綠 | pytest 全套 |
| NFR-23-1 | §5.2/5.3 有界 | `test_fold_million_node_graph_still_bounded` / `test_fold_topology_no_while_no_recursion` | pytest |
| NFR-23-2 | §3 紅線 | 既有 `test_no_sixth_formal_track_phase_y` / `test_meta_fsm_variables_unchanged_no_new_state_phase_y` 續綠；五軌免觸發 | pytest |

---

## §7 紅線守恆檢核

| 紅線 | 本輪 | 證據 |
|------|------|------|
| 不碰 meta⁹ / meta-oracle | ✅ | folding 純投影 read-only，零 generator/oracle import（AST 斷言續綠） |
| 不提 Token 預算上限 | ✅ | 沿用 RenderBudget clamp；folding 只降不升節點數 |
| 不破五軌 TLC | ✅ | `*.tla`/`_HAPPY_PATH` 零修改 → 免觸發 |
| 不增第六軌 / 狀態變數 | ✅ | `<<mstate,churn,cap>>` 不變 |
| 視覺化不寫 FSM-STATE / 不 churn | ✅ | read-only 純觀察者 |
| 凍結本體禁改（Copy-on-Evolve） | ✅ | 改動落 v0.14；v0.13 唯讀凍結 |
| PY-2 拓樸防偽不弱化 | ✅ | fold-aware 五道**強化**而非弱化 |

---

## §8 實作順序（階段三）

1. Copy-on-Evolve v0.13 → v0.14（排除 __pycache__ / build/reports 運行產物；`git add -A -n` dry-run 審 would-add）。
2. v0.14 `recursion_topology_view.py`：RenderBudget.fold_enabled + TopoNode.folded/folds + `fold_topology()` + render_mermaid fold 渲染 + render_json additive。
3. v0.14 `recursion_topology_view.py`：`verify_topology_consistency` 擴充 f1~f5（fold OFF 恆過）。
4. v0.14 `chaos_runner.py`：`VISUALIZATION_FOLD_DRIFT_FLAP` + bounded 檢查。
5. v0.14 `tests/test_phase_y.py`：新增 §6 RTM 測試；**每寫一支立即 pytest 單測**（開發-編譯-測試循環）。
6. 階段四 CI 平價：v0.14 ci-gate（pytest not-chaos + arch_fitness）、AutoClaude 全套零退化、lint-imports、五軌免觸發查核。
7. 修 DEF-23-002（archive _26/_27）、DEF-23-001（CHANGELOG 口徑）；EVOLUTION_LOG + CHANGELOG v0.14。
8. 多專家 Zero-Trust 審查閉環全 PASS → 結案四件套。

---

## §9 結案契約（closure-evidence，收官回填）

> 兩段式 closure（同 improving_22）：commit A（主體 `cd3d4c45`）+ tag `v2026.06.17-20`，本契約於 commit B 回填。
> 廉價層（git 事實）：`claimed_commits`/`claimed_tag` 可由 post-commit hook 就 repo 真實狀態重推導 → VERIFIED。
> 昂貴層（pytest/ci-gate floors）：`base_sha != HEAD`（回填後 HEAD=commit B）→ 設計上 fail-closed 標 INCONCLUSIVE（誠實，不假綠）。

```yaml
closure-evidence:
  round: 23
  track: B
  base_sha: cd3d4c450ed2c20fe3128d2eba211a98d38fbeac
  claimed_commits:
    - cd3d4c450ed2c20fe3128d2eba211a98d38fbeac   # commit A（W-23-1 主體 + 四件套）
  claimed_tag: v2026.06.17-20
  observed:
    autoclaude_pytest: "3112 passed / 122 skipped / 0 failed"
    aisldc_ci_gate: "v0.01:1478 / v0.14:1593 / scripts:27 (arch_fitness fail=0)"
    aisldc_chaos: "34 passed (bounded_ratio==1.0, incl VISUALIZATION_FOLD_DRIFT_FLAP)"
    lint_imports: "8 kept / 0 broken"
    five_track_tlc: "N/A (formal *.tla/*.cfg v0.13↔v0.14 逐位元零差異 → 免觸發)"
    cleanliness: "git add -A -n v0.14 = 853 would-add, 零 runtime 漏網"
  audit: docs/06_quality/AutoSDD_ZeroTrust_Audit_23.md   # 三鏡全 OVERALL PASS + 突變回歸鎖驗證
```
